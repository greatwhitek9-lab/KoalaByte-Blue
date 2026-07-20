#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/display.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/byteorder.h>
#include <zephyr/sys/printk.h>
#include <zephyr/sys/util.h>

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/*
 * Continuous original-art mouth renderer.
 *
 * The user-approved smile artwork is the only runtime texture. The face is
 * never replaced by procedural lips/teeth and never cycled through pose stills.
 * A bounded inverse warp moves the original muzzle, lips, jaw, teeth, and
 * purple/lime shading as one textured surface. This keeps every feature aligned
 * and inside the 240x135 frame.
 */

#define DISPLAY_NODE DT_CHOSEN(zephyr_display)
#define TFT_WIDTH 240
#define TFT_HEIGHT 135
#define ORIGINAL_FRAME_BYTES 64800
#define MOTION_TICK_MS 42

#define WARP_X0 18
#define WARP_X1 221
#define WARP_Y0 42
#define WARP_Y1 130
#define WARP_WIDTH (WARP_X1 - WARP_X0 + 1)
#define WARP_HEIGHT (WARP_Y1 - WARP_Y0 + 1)
#define MOUTH_CENTER_X 120
#define MOUTH_PIVOT_Y 84
#define MOUTH_HALF_WIDTH 102

static const struct device *const motion_display = DEVICE_DT_GET(DISPLAY_NODE);
static uint16_t warp_pixels[WARP_WIDTH * WARP_HEIGHT];

static const uint8_t original_killerkoala_face_rgb565_be[] __aligned(4) = {
#include "killerkoala_cyber_mouth_smile_rgb565.inc"
};
BUILD_ASSERT(sizeof(original_killerkoala_face_rgb565_be) == ORIGINAL_FRAME_BYTES,
             "Original KillerKoala face must be exactly 240x135 RGB565");

/* Base display functions from loading_display.c after CMake symbol routing. */
void koala_base_render_menu_status(const char *message);
void koala_base_render_koalagotchi_action(const char *action_title,
                                          uint8_t frame_index);

static K_MUTEX_DEFINE(motion_mutex);
static bool motion_active;
static bool base_art_dirty = true;
static bool renderer_announced;
static char motion_state[24] = "idle";
static char motion_message[72] = "KILLERKOALA";
static int current_open;
static int current_curl;
static int current_asymmetry;
static int current_width;
static uint8_t motion_from_pose;
static uint8_t motion_to_pose;
static uint8_t motion_pose_blend;

static void motion_work_handler(struct k_work *work);
K_WORK_DELAYABLE_DEFINE(motion_work, motion_work_handler);

static int triangle_wave(int64_t now, int period_ms, int amplitude)
{
    int phase = (int)(now % period_ms);
    int half = MAX(period_ms / 2, 1);
    int ramp = phase <= half ? phase : period_ms - phase;
    return (ramp * amplitude) / half;
}

static int signed_triangle(int64_t now, int period_ms, int amplitude)
{
    return triangle_wave(now, period_ms, amplitude * 2) - amplitude;
}

static int approach(int current, int target, int maximum_step)
{
    int delta = target - current;
    if (delta > maximum_step) {
        return current + maximum_step;
    }
    if (delta < -maximum_step) {
        return current - maximum_step;
    }
    return target;
}

static uint16_t source_pixel(int x, int y)
{
    x = CLAMP(x, 0, TFT_WIDTH - 1);
    y = CLAMP(y, 0, TFT_HEIGHT - 1);
    size_t offset = ((size_t)y * TFT_WIDTH + (size_t)x) * 2U;
    uint16_t pixel;
    memcpy(&pixel, &original_killerkoala_face_rgb565_be[offset],
           sizeof(pixel));
    return pixel;
}

static uint16_t blend_pixel(uint16_t original_be, uint16_t warped_be,
                            uint8_t amount)
{
    uint16_t original = sys_be16_to_cpu(original_be);
    uint16_t warped = sys_be16_to_cpu(warped_be);
    uint16_t inverse = 255U - amount;
    uint16_t red = (uint16_t)(((((original >> 11) & 0x1fU) * inverse) +
                               (((warped >> 11) & 0x1fU) * amount) + 127U) /
                              255U);
    uint16_t green = (uint16_t)(((((original >> 5) & 0x3fU) * inverse) +
                                 (((warped >> 5) & 0x3fU) * amount) + 127U) /
                                255U);
    uint16_t blue = (uint16_t)((((original & 0x1fU) * inverse) +
                                ((warped & 0x1fU) * amount) + 127U) /
                               255U);
    return sys_cpu_to_be16((uint16_t)((red << 11) | (green << 5) | blue));
}

struct texture_pose {
    int open;
    int curl;
    int asymmetry;
    int width;
};

static struct texture_pose pose_for_id(uint8_t pose)
{
    switch (pose) {
    case 1: /* happy/open */
        return (struct texture_pose){6, 8, 0, 2};
    case 2: /* bite */
        return (struct texture_pose){10, 1, 0, -1};
    case 3: /* snarl */
        return (struct texture_pose){8, -7, 2, 4};
    case 4: /* sideways grin */
        return (struct texture_pose){4, 4, 7, 2};
    default: /* smile */
        return (struct texture_pose){2, 4, 0, 0};
    }
}

static int lerp_pose_value(int from, int to, uint8_t amount)
{
    return from + (((to - from) * (int)amount) / 255);
}

static struct texture_pose blended_pose_target(void)
{
    struct texture_pose from = pose_for_id(motion_from_pose);
    struct texture_pose to = pose_for_id(motion_to_pose);
    return (struct texture_pose){
        lerp_pose_value(from.open, to.open, motion_pose_blend),
        lerp_pose_value(from.curl, to.curl, motion_pose_blend),
        lerp_pose_value(from.asymmetry, to.asymmetry, motion_pose_blend),
        lerp_pose_value(from.width, to.width, motion_pose_blend),
    };
}

static void update_motion_targets(const char *state, int64_t now)
{
    const char *resolved = state && state[0] ? state : "idle";
    struct texture_pose pose = blended_pose_target();
    int target_open = pose.open;
    int target_curl = pose.curl;
    int target_asymmetry = pose.asymmetry;
    int target_width = pose.width;

    if (!strcmp(resolved, "speaking")) {
        /*
         * Non-harmonic envelopes mimic syllables, consonants, and pauses.
         * There is no repeating open/closed frame pair.
         */
        target_open = MAX(pose.open, 3) + triangle_wave(now, 287, 8) +
                      triangle_wave(now + 83, 173, 5) +
                      triangle_wave(now + 211, 419, 3);
        target_curl = pose.curl + signed_triangle(now + 41, 733, 3);
        target_asymmetry = pose.asymmetry +
                           signed_triangle(now + 97, 1061, 3);
        target_width = pose.width + 2 + signed_triangle(now, 617, 2);
    } else if (!strcmp(resolved, "wake") ||
               !strcmp(resolved, "thinking")) {
        target_open = MAX(pose.open, 4) + triangle_wave(now, 1600, 3);
        target_curl = pose.curl + signed_triangle(now, 2300, 2);
        target_asymmetry = pose.asymmetry + signed_triangle(now, 1400, 3);
        target_width = pose.width + 1;
    } else if (!strcmp(resolved, "success")) {
        target_open = MAX(pose.open, 2) + triangle_wave(now, 2600, 2);
        target_curl = MAX(pose.curl, 8);
        target_asymmetry = pose.asymmetry + signed_triangle(now, 4400, 1);
        target_width = MAX(pose.width, 3);
    } else if (!strcmp(resolved, "error") ||
               !strcmp(resolved, "angry")) {
        target_open = MAX(pose.open, 8) + triangle_wave(now, 900, 3);
        target_curl = MIN(pose.curl, -7);
        target_asymmetry = pose.asymmetry + signed_triangle(now, 1300, 3);
        target_width = MAX(pose.width, 4);
    } else {
        /* Idle pose choreography plus breathing and micro-expression drift. */
        target_open = pose.open + triangle_wave(now, 4300, 2);
        target_curl = pose.curl + signed_triangle(now, 6800, 2);
        target_asymmetry = pose.asymmetry +
                           signed_triangle(now + 400, 5700, 2);
        target_width = pose.width + signed_triangle(now, 7600, 1);
    }

    current_open = approach(current_open, CLAMP(target_open, 0, 23), 2);
    current_curl = approach(current_curl, CLAMP(target_curl, -9, 10), 1);
    current_asymmetry = approach(current_asymmetry,
                                 CLAMP(target_asymmetry, -8, 8), 1);
    current_width = approach(current_width, CLAMP(target_width, -3, 7), 1);
}

static void write_base_art_locked(void)
{
    if (!base_art_dirty || !device_is_ready(motion_display)) {
        return;
    }
    const struct display_buffer_descriptor descriptor = {
        .buf_size = sizeof(original_killerkoala_face_rgb565_be),
        .width = TFT_WIDTH,
        .height = TFT_HEIGHT,
        .pitch = TFT_WIDTH,
    };
    (void)display_write(motion_display, 0, 0, &descriptor,
                        original_killerkoala_face_rgb565_be);
    base_art_dirty = false;
}

static void build_warp_region_locked(const char *state)
{
    int64_t now = k_uptime_get();
    update_motion_targets(state, now);

    for (int y = WARP_Y0; y <= WARP_Y1; y++) {
        int y_distance = ABS(y - MOUTH_PIVOT_Y);
        int y_extent = y <= MOUTH_PIVOT_Y ?
            (MOUTH_PIVOT_Y - WARP_Y0) : (WARP_Y1 - MOUTH_PIVOT_Y);
        int y_weight = 255 - ((y_distance * 255) / MAX(y_extent, 1));
        y_weight = CLAMP(y_weight, 0, 255);
        y_weight = (y_weight * y_weight) / 255;

        for (int x = WARP_X0; x <= WARP_X1; x++) {
            int dx = x - MOUTH_CENTER_X;
            int x_weight = 255 - ((ABS(dx) * 255) / MOUTH_HALF_WIDTH);
            x_weight = CLAMP(x_weight, 0, 255);
            x_weight = (x_weight * x_weight) / 255;
            int influence = (x_weight * y_weight) / 255;
            int local_open = (current_open * x_weight) / 255;
            int corner_curve = (current_curl * dx * dx) /
                               (MOUTH_HALF_WIDTH * MOUTH_HALF_WIDTH);
            int asym_curve = (current_asymmetry * dx) / MOUTH_HALF_WIDTH;
            int upper_edge = MOUTH_PIVOT_Y - (local_open / 4) -
                             corner_curve - asym_curve;
            int lower_edge = MOUTH_PIVOT_Y + local_open -
                             corner_curve - asym_curve;
            int source_y;

            if (y < upper_edge) {
                source_y = y + ((local_open * influence) / 1020) +
                           corner_curve + asym_curve;
            } else if (y <= lower_edge && lower_edge > upper_edge) {
                /* Stretch only the original center-mouth texture. */
                int gap = MAX(lower_edge - upper_edge, 1);
                source_y = (MOUTH_PIVOT_Y - 2) +
                           (((y - upper_edge) * 4) / gap);
            } else {
                source_y = y - ((local_open * influence) / 255) +
                           corner_curve + asym_curve;
            }

            int scale_q8 = 256 + ((current_width * influence * 3) / 255);
            scale_q8 = MAX(scale_q8, 224);
            int source_x = MOUTH_CENTER_X + ((dx * 256) / scale_q8) -
                           ((current_asymmetry * influence) / 510);
            source_x = CLAMP(source_x, WARP_X0, WARP_X1);
            source_y = CLAMP(source_y, WARP_Y0, WARP_Y1);

            uint16_t original = source_pixel(x, y);
            uint16_t warped = source_pixel(source_x, source_y);
            size_t index = (size_t)(y - WARP_Y0) * WARP_WIDTH +
                           (size_t)(x - WARP_X0);
            warp_pixels[index] = blend_pixel(original, warped,
                                             (uint8_t)influence);
        }
    }
}

static void write_warp_region_locked(void)
{
    if (!device_is_ready(motion_display)) {
        return;
    }
    const struct display_buffer_descriptor descriptor = {
        .buf_size = sizeof(warp_pixels),
        .width = WARP_WIDTH,
        .height = WARP_HEIGHT,
        .pitch = WARP_WIDTH,
    };
    (void)display_write(motion_display, WARP_X0, WARP_Y0, &descriptor,
                        warp_pixels);
}

static void render_motion_locked(void)
{
    write_base_art_locked();
    build_warp_region_locked(motion_state);
    write_warp_region_locked();

    if (!renderer_announced) {
        renderer_announced = true;
        printk("{\"type\":\"t114_renderer\",\"renderer\":\"original_texture_continuous_warp\",\"still_frame_cycle\":false,\"texture\":\"original_killerkoala_smile\",\"tick_ms\":%d}\n",
               MOTION_TICK_MS);
    }
}

static void motion_work_handler(struct k_work *work)
{
    ARG_UNUSED(work);
    k_mutex_lock(&motion_mutex, K_FOREVER);
    if (!motion_active) {
        k_mutex_unlock(&motion_mutex);
        return;
    }
    render_motion_locked();
    (void)k_work_reschedule(&motion_work, K_MSEC(MOTION_TICK_MS));
    k_mutex_unlock(&motion_mutex);
}

static void stop_motion_and_mark_dirty(void)
{
    k_mutex_lock(&motion_mutex, K_FOREVER);
    motion_active = false;
    base_art_dirty = true;
    (void)k_work_cancel_delayable(&motion_work);
    k_mutex_unlock(&motion_mutex);
}

void koala_original_render_killerkoala_mouth(const char *state,
                                              const char *message,
                                              uint8_t from_frame_index,
                                              uint8_t to_frame_index,
                                              uint8_t blend_amount)
{
    k_mutex_lock(&motion_mutex, K_FOREVER);
    bool was_inactive = !motion_active;
    snprintf(motion_state, sizeof(motion_state), "%s",
             state && state[0] ? state : "idle");
    snprintf(motion_message, sizeof(motion_message), "%s",
             message && message[0] ? message : "KILLERKOALA");
    motion_from_pose = from_frame_index % 5U;
    motion_to_pose = to_frame_index % 5U;
    motion_pose_blend = blend_amount;
    motion_active = true;
    if (was_inactive) {
        base_art_dirty = true;
    }
    render_motion_locked();
    (void)k_work_reschedule(&motion_work, K_MSEC(MOTION_TICK_MS));
    k_mutex_unlock(&motion_mutex);
}

void koala_original_render_menu_status(const char *message)
{
    stop_motion_and_mark_dirty();
    koala_base_render_menu_status(message);
}

void koala_original_render_koalagotchi_action(const char *action_title,
                                               uint8_t frame_index)
{
    stop_motion_and_mark_dirty();
    koala_base_render_koalagotchi_action(action_title, frame_index);
}
