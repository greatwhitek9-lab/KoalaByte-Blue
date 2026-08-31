#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/display.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/byteorder.h>
#include <zephyr/sys/util.h>

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "loading_display.h"

/*
 * Outer lifecycle wrapper for the T114 display renderers.
 *
 * The continuous single-texture mouth renderer owns idle and speaking motion.
 * This wrapper owns display lifetime and Koalagotchi emotion/alarm overlays:
 *   - executing actions remain visible until action_complete/xp_logged
 *   - explicit Koalagotchi mode remains visible until koalagotchi_exit
 *   - failed attempts latch disappointed, then angry after repeated failures
 *   - active errors latch an alerted Koalagotchi over flashing cyber purple and
 *     green background panels while keeping the character visible
 *   - error state only clears on an explicit error_clear command
 */

#define KOALAGOTCHI_FRAME_MS 95
#define KOALAGOTCHI_ALARM_MS 180
#define DISPLAY_NODE DT_CHOSEN(zephyr_display)
#define DISPLAY_WIDTH 240
#define DISPLAY_HEIGHT 135
#define OVERLAY_MAX_PIXELS (DISPLAY_WIDTH * 32)

static const struct device *const lifecycle_display = DEVICE_DT_GET(DISPLAY_NODE);
static uint16_t overlay_pixels[OVERLAY_MAX_PIXELS];

enum koalagotchi_latch_mode {
    KOALAGOTCHI_LATCH_NONE = 0,
    KOALAGOTCHI_LATCH_ACTION,
    KOALAGOTCHI_LATCH_PERSISTENT,
    KOALAGOTCHI_LATCH_DISAPPOINTED,
    KOALAGOTCHI_LATCH_ANGRY,
    KOALAGOTCHI_LATCH_ALARMED,
};

static K_MUTEX_DEFINE(lifecycle_mutex);
static enum koalagotchi_latch_mode latch_mode = KOALAGOTCHI_LATCH_NONE;
static bool resume_persistent_after_alarm;
static bool alarm_green_phase;
static uint8_t lifecycle_frame;
static char lifecycle_message[96] = "KOALAGOTCHI";

/* Renamed at compile time from the existing display wrapper. */
void koala_inner_render_killerkoala_mouth(const char *state,
                                          const char *message,
                                          uint8_t from_frame_index,
                                          uint8_t to_frame_index,
                                          uint8_t blend_amount);
void koala_inner_render_menu_status(const char *message);
void koala_inner_render_koalagotchi_action(const char *action_title,
                                           uint8_t frame_index);

/* Mouth renderer action entry stops its dedicated 42 ms animation thread. */
void koala_original_render_koalagotchi_action(const char *action_title,
                                               uint8_t frame_index);

/* Linker --wrap real targets from loading_display.c. */
void __real_render_killerkoala_mouth(const char *state, const char *message,
                                     uint8_t from_frame_index,
                                     uint8_t to_frame_index,
                                     uint8_t blend_amount);
void __real_render_menu_status(const char *message);
void __real_render_koalagotchi_action(const char *action_title,
                                      uint8_t frame_index);

static uint16_t lifecycle_rgb565_be(uint8_t red, uint8_t green, uint8_t blue)
{
    uint16_t value = (uint16_t)(((red & 0xf8U) << 8) |
                                ((green & 0xfcU) << 3) |
                                (blue >> 3));
    return sys_cpu_to_be16(value);
}

static void overlay_rect(int x, int y, int width, int height, uint16_t color)
{
    if (!device_is_ready(lifecycle_display) || width <= 0 || height <= 0 ||
        x < 0 || y < 0 || x + width > DISPLAY_WIDTH ||
        y + height > DISPLAY_HEIGHT) {
        return;
    }

    size_t pixels = (size_t)width * (size_t)height;
    if (pixels > ARRAY_SIZE(overlay_pixels)) {
        return;
    }
    for (size_t index = 0; index < pixels; index++) {
        overlay_pixels[index] = color;
    }

    const struct display_buffer_descriptor descriptor = {
        .buf_size = pixels * sizeof(uint16_t),
        .width = (uint16_t)width,
        .height = (uint16_t)height,
        .pitch = (uint16_t)width,
    };
    (void)display_write(lifecycle_display, (uint16_t)x, (uint16_t)y,
                        &descriptor, overlay_pixels);
}

static void overlay_alarm_background(bool green_phase)
{
    uint16_t purple = lifecycle_rgb565_be(177, 71, 255);
    uint16_t green = lifecycle_rgb565_be(70, 255, 112);
    uint16_t active = green_phase ? green : purple;
    uint16_t opposite = green_phase ? purple : green;

    /*
     * Flash the background around, rather than over, the moving Koalagotchi.
     * The protected center window keeps the character, eyes, and alert pose
     * visible while the large edge panels alternate purple and green.
     */
    overlay_rect(0, 0, DISPLAY_WIDTH, 24, active);
    overlay_rect(0, DISPLAY_HEIGHT - 24, DISPLAY_WIDTH, 24, opposite);
    overlay_rect(0, 24, 22, DISPLAY_HEIGHT - 48, opposite);
    overlay_rect(DISPLAY_WIDTH - 22, 24, 22, DISPLAY_HEIGHT - 48, active);

    for (int x = 24; x < DISPLAY_WIDTH - 24; x += 32) {
        overlay_rect(x, 0, 16, 7, opposite);
        overlay_rect(x + 16, DISPLAY_HEIGHT - 7, 16, 7, active);
    }
}

static void overlay_alarm_border(bool green_phase)
{
    uint16_t purple = lifecycle_rgb565_be(177, 71, 255);
    uint16_t green = lifecycle_rgb565_be(70, 255, 112);
    uint16_t white = lifecycle_rgb565_be(245, 248, 240);
    uint16_t active = green_phase ? green : purple;
    uint16_t opposite = green_phase ? purple : green;

    overlay_rect(0, 0, DISPLAY_WIDTH, 7, active);
    overlay_rect(0, DISPLAY_HEIGHT - 7, DISPLAY_WIDTH, 7, opposite);
    overlay_rect(0, 7, 7, DISPLAY_HEIGHT - 14, active);
    overlay_rect(DISPLAY_WIDTH - 7, 7, 7, DISPLAY_HEIGHT - 14, opposite);

    overlay_rect(112, 3, 7, 12, white);
    overlay_rect(112, 17, 7, 6, active);
}

static void koalagotchi_position(uint8_t frame, int *x, int *y)
{
    int phase = frame % 8U;
    int travel = phase <= 4 ? phase : 8 - phase;
    *x = 58 + (travel * 30);
    *y = 65 + ((phase & 1) ? 2 : 0);
}

static void overlay_disappointed(uint8_t frame)
{
    uint16_t purple = lifecycle_rgb565_be(177, 71, 255);
    uint16_t green = lifecycle_rgb565_be(70, 255, 112);
    uint16_t dark = lifecycle_rgb565_be(8, 10, 12);
    int x;
    int y;
    koalagotchi_position(frame, &x, &y);

    /* Drooped brows, downturned mouth, and a small tear. */
    overlay_rect(MAX(0, x - 16), MAX(0, y - 15), 11, 3, purple);
    overlay_rect(MIN(DISPLAY_WIDTH - 11, x + 5), MAX(0, y - 15), 11, 3, green);
    overlay_rect(MAX(0, x - 8), MIN(DISPLAY_HEIGHT - 3, y + 15), 16, 3, dark);
    overlay_rect(MAX(0, x - 12), MIN(DISPLAY_HEIGHT - 5, y + 12), 5, 3, purple);
    overlay_rect(MIN(DISPLAY_WIDTH - 5, x + 7), MIN(DISPLAY_HEIGHT - 5, y + 12), 5, 3, green);
    overlay_rect(MAX(0, x - 12), MIN(DISPLAY_HEIGHT - 9, y + 1), 3, 8, purple);
}

static void overlay_angry(uint8_t frame)
{
    uint16_t purple = lifecycle_rgb565_be(210, 62, 255);
    uint16_t green = lifecycle_rgb565_be(70, 255, 112);
    uint16_t dark = lifecycle_rgb565_be(8, 4, 10);
    int x;
    int y;
    koalagotchi_position(frame, &x, &y);

    /* Heavy inward brows and a clenched mouth. */
    for (int step = 0; step < 4; step++) {
        overlay_rect(MAX(0, x - 17 + (step * 3)),
                     MAX(0, y - 18 + (step * 2)), 5, 3, purple);
        overlay_rect(MIN(DISPLAY_WIDTH - 5, x + 12 - (step * 3)),
                     MAX(0, y - 18 + (step * 2)), 5, 3, green);
    }
    overlay_rect(MAX(0, x - 12), MIN(DISPLAY_HEIGHT - 4, y + 13), 24, 4, dark);
    overlay_rect(MAX(0, x - 12), MIN(DISPLAY_HEIGHT - 2, y + 13), 11, 2, purple);
    overlay_rect(MIN(DISPLAY_WIDTH - 11, x + 1), MIN(DISPLAY_HEIGHT - 2, y + 13), 11, 2, green);
}

static void overlay_alerted(uint8_t frame, bool green_phase)
{
    uint16_t purple = lifecycle_rgb565_be(210, 62, 255);
    uint16_t green = lifecycle_rgb565_be(70, 255, 112);
    uint16_t white = lifecycle_rgb565_be(245, 248, 240);
    uint16_t active = green_phase ? green : purple;
    uint16_t opposite = green_phase ? purple : green;
    int x;
    int y;
    koalagotchi_position(frame, &x, &y);

    /* Alerted eyes and tense brows remain attached to the moving Koalagotchi. */
    overlay_angry(frame);
    overlay_rect(MAX(0, x - 14), MAX(0, y - 9), 10, 5, white);
    overlay_rect(MIN(DISPLAY_WIDTH - 10, x + 4), MAX(0, y - 9), 10, 5, white);
    overlay_rect(MAX(0, x - 10), MAX(0, y - 8), 3, 4, active);
    overlay_rect(MIN(DISPLAY_WIDTH - 3, x + 7), MAX(0, y - 8), 3, 4, opposite);

    /* Small alternating cheek indicators read as a cyber warning state. */
    overlay_rect(MAX(0, x - 22), MIN(DISPLAY_HEIGHT - 4, y + 7), 7, 4, active);
    overlay_rect(MIN(DISPLAY_WIDTH - 7, x + 15), MIN(DISPLAY_HEIGHT - 4, y + 7), 7, 4, opposite);
}

static void render_latched_locked(void)
{
    __real_render_koalagotchi_action(lifecycle_message, lifecycle_frame);

    if (latch_mode == KOALAGOTCHI_LATCH_DISAPPOINTED) {
        overlay_disappointed(lifecycle_frame);
    } else if (latch_mode == KOALAGOTCHI_LATCH_ANGRY) {
        overlay_angry(lifecycle_frame);
    } else if (latch_mode == KOALAGOTCHI_LATCH_ALARMED) {
        overlay_alarm_background(alarm_green_phase);
        overlay_alerted(lifecycle_frame, alarm_green_phase);
        overlay_alarm_border(alarm_green_phase);
    }
}

static void lifecycle_work_handler(struct k_work *work);
K_WORK_DELAYABLE_DEFINE(lifecycle_work, lifecycle_work_handler);

static void lifecycle_work_handler(struct k_work *work)
{
    ARG_UNUSED(work);
    int delay_ms;

    k_mutex_lock(&lifecycle_mutex, K_FOREVER);
    if (latch_mode == KOALAGOTCHI_LATCH_NONE) {
        k_mutex_unlock(&lifecycle_mutex);
        return;
    }

    lifecycle_frame = (uint8_t)((lifecycle_frame + 1U) % 8U);
    if (latch_mode == KOALAGOTCHI_LATCH_ALARMED) {
        alarm_green_phase = !alarm_green_phase;
    }
    render_latched_locked();
    delay_ms = latch_mode == KOALAGOTCHI_LATCH_ALARMED ?
        KOALAGOTCHI_ALARM_MS : KOALAGOTCHI_FRAME_MS;
    k_mutex_unlock(&lifecycle_mutex);

    (void)k_work_reschedule(&lifecycle_work, K_MSEC(delay_ms));
}

static void stop_inner_animation(void)
{
    /*
     * Do not send an idle mouth frame here. The mouth renderer owns a dedicated
     * 42 ms thread; sending "idle" keeps that thread active and causes it to
     * overwrite the 95 ms Koalagotchi lifecycle frames. Route through the
     * mouth renderer's action entry instead: it stops motion first, and CMake
     * routes its action draw to the same canonical centered Koalagotchi HUD.
     */
    koala_original_render_koalagotchi_action("KOALAGOTCHI", 0);
}

static void activate_latch(enum koalagotchi_latch_mode mode,
                           const char *message, uint8_t first_frame)
{
    bool alarm_from_persistent;
    (void)k_work_cancel_delayable(&lifecycle_work);
    stop_inner_animation();

    k_mutex_lock(&lifecycle_mutex, K_FOREVER);
    alarm_from_persistent = mode == KOALAGOTCHI_LATCH_ALARMED &&
        latch_mode == KOALAGOTCHI_LATCH_PERSISTENT;
    if (alarm_from_persistent) {
        resume_persistent_after_alarm = true;
    } else if (mode != KOALAGOTCHI_LATCH_ALARMED) {
        resume_persistent_after_alarm = false;
    }
    latch_mode = mode;
    lifecycle_frame = first_frame % 8U;
    alarm_green_phase = false;
    snprintf(lifecycle_message, sizeof(lifecycle_message), "%s",
             message && message[0] ? message :
             (mode == KOALAGOTCHI_LATCH_ACTION ? "EXECUTING" : "KOALAGOTCHI"));
    render_latched_locked();
    k_mutex_unlock(&lifecycle_mutex);

    (void)k_work_reschedule(
        &lifecycle_work,
        K_MSEC(mode == KOALAGOTCHI_LATCH_ALARMED ?
               KOALAGOTCHI_ALARM_MS : KOALAGOTCHI_FRAME_MS));
}

static void clear_latch(void)
{
    (void)k_work_cancel_delayable(&lifecycle_work);
    k_mutex_lock(&lifecycle_mutex, K_FOREVER);
    latch_mode = KOALAGOTCHI_LATCH_NONE;
    resume_persistent_after_alarm = false;
    alarm_green_phase = false;
    k_mutex_unlock(&lifecycle_mutex);
}

static bool latch_blocks_transient_state(void)
{
    return latch_mode == KOALAGOTCHI_LATCH_ACTION ||
           latch_mode == KOALAGOTCHI_LATCH_PERSISTENT ||
           latch_mode == KOALAGOTCHI_LATCH_DISAPPOINTED ||
           latch_mode == KOALAGOTCHI_LATCH_ANGRY ||
           latch_mode == KOALAGOTCHI_LATCH_ALARMED;
}

void __wrap_render_menu_status(const char *message)
{
    k_mutex_lock(&lifecycle_mutex, K_FOREVER);
    bool blocked = latch_mode == KOALAGOTCHI_LATCH_ACTION ||
                   latch_mode == KOALAGOTCHI_LATCH_PERSISTENT ||
                   latch_mode == KOALAGOTCHI_LATCH_ALARMED;
    bool emotion_only = latch_mode == KOALAGOTCHI_LATCH_DISAPPOINTED ||
                        latch_mode == KOALAGOTCHI_LATCH_ANGRY;
    k_mutex_unlock(&lifecycle_mutex);

    if (blocked) {
        return;
    }
    if (emotion_only) {
        clear_latch();
    }
    koala_inner_render_menu_status(message);
}

void __wrap_render_koalagotchi_action(const char *action_title,
                                      uint8_t frame_index)
{
    k_mutex_lock(&lifecycle_mutex, K_FOREVER);
    bool preserve = latch_mode == KOALAGOTCHI_LATCH_PERSISTENT ||
                    latch_mode == KOALAGOTCHI_LATCH_ALARMED;
    k_mutex_unlock(&lifecycle_mutex);
    if (preserve) {
        return;
    }
    activate_latch(KOALAGOTCHI_LATCH_ACTION,
                   action_title && action_title[0] ? action_title : "EXECUTING",
                   frame_index);
}

void __wrap_render_killerkoala_mouth(const char *state, const char *message,
                                     uint8_t from_frame_index,
                                     uint8_t to_frame_index,
                                     uint8_t blend_amount)
{
    const char *resolved = state && state[0] ? state : "idle";

    if (!strcmp(resolved, "action") ||
        !strcmp(resolved, "koalagotchi_action") ||
        !strcmp(resolved, "executing")) {
        activate_latch(KOALAGOTCHI_LATCH_ACTION, message, 0);
        return;
    }
    if (!strcmp(resolved, "koalagotchi_mode") ||
        !strcmp(resolved, "koalagotchi_persistent")) {
        activate_latch(KOALAGOTCHI_LATCH_PERSISTENT, message, 0);
        return;
    }
    if (!strcmp(resolved, "error") || !strcmp(resolved, "alarmed")) {
        activate_latch(KOALAGOTCHI_LATCH_ALARMED,
                       message && message[0] ? message : "ALARM", 0);
        return;
    }
    if (!strcmp(resolved, "disappointed")) {
        activate_latch(KOALAGOTCHI_LATCH_DISAPPOINTED,
                       message && message[0] ? message : "FAILED", 0);
        return;
    }
    if (!strcmp(resolved, "angry")) {
        activate_latch(KOALAGOTCHI_LATCH_ANGRY,
                       message && message[0] ? message : "REPEATED FAILURES", 0);
        return;
    }

    if (!strcmp(resolved, "error_clear") ||
        !strcmp(resolved, "alarm_clear")) {
        k_mutex_lock(&lifecycle_mutex, K_FOREVER);
        bool resume = resume_persistent_after_alarm;
        k_mutex_unlock(&lifecycle_mutex);
        clear_latch();
        if (resume) {
            activate_latch(KOALAGOTCHI_LATCH_PERSISTENT, "KOALAGOTCHI", 0);
        } else {
            koala_inner_render_killerkoala_mouth("idle", "KILLERKOALA",
                                                 0, 0, 0);
        }
        return;
    }

    if (!strcmp(resolved, "koalagotchi_exit") ||
        !strcmp(resolved, "mode_exit") ||
        !strcmp(resolved, "clear_mode")) {
        clear_latch();
        koala_inner_render_killerkoala_mouth("idle", "KILLERKOALA", 0, 0, 0);
        return;
    }

    if (!strcmp(resolved, "action_complete") ||
        !strcmp(resolved, "xp_logged") ||
        !strcmp(resolved, "success")) {
        k_mutex_lock(&lifecycle_mutex, K_FOREVER);
        enum koalagotchi_latch_mode current = latch_mode;
        k_mutex_unlock(&lifecycle_mutex);
        if (current == KOALAGOTCHI_LATCH_ALARMED ||
            current == KOALAGOTCHI_LATCH_PERSISTENT) {
            return;
        }
        clear_latch();
        koala_inner_render_killerkoala_mouth("success", message,
                                             from_frame_index,
                                             to_frame_index, blend_amount);
        return;
    }

    k_mutex_lock(&lifecycle_mutex, K_FOREVER);
    bool blocked = latch_blocks_transient_state();
    k_mutex_unlock(&lifecycle_mutex);
    if (blocked) {
        return;
    }

    koala_inner_render_killerkoala_mouth(resolved, message,
                                         from_frame_index,
                                         to_frame_index, blend_amount);
}
