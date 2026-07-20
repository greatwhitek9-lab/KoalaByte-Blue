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
 * Runtime display layer for the Heltec T114.
 *
 * The supplied cyber-mouth artwork remains the full-screen base image. Only the
 * muzzle/mouth region is redrawn procedurally, preserving the existing design
 * while replacing full-frame picture swaps with continuous geometry changes.
 * Menu and action states use the existing Koalagotchi renderer and are animated
 * locally until the Pi/ESP32 returns the display to the mouth state.
 */

#define PROC_X 20
#define PROC_Y 35
#define PROC_W 200
#define PROC_H 88
#define KOALA_ANIMATION_MS 95
#define KOALA_ERROR_ALARM_MS 180

#define DISPLAY_NODE DT_CHOSEN(zephyr_display)
static const struct device *const procedural_display = DEVICE_DT_GET(DISPLAY_NODE);
static uint16_t procedural_frame[PROC_W * PROC_H];

struct mouth_pose {
    int jaw;
    int curl;
    int asymmetry;
    int snarl;
    int teeth;
    int tongue;
};

enum procedural_mode {
    PROC_MODE_MOUTH = 0,
    PROC_MODE_MENU_KOALAGOTCHI,
    PROC_MODE_ACTION_KOALAGOTCHI,
    PROC_MODE_ERROR,
};

static K_MUTEX_DEFINE(procedural_render_mutex);
static enum procedural_mode procedural_mode = PROC_MODE_MOUTH;
static bool base_art_dirty = true;
static bool error_banner_phase;
static char active_message[96] = "KILLERKOALA";
static uint8_t active_from_frame;
static uint8_t active_to_frame;
static uint8_t active_blend;
static uint8_t koalagotchi_frame;

void __real_render_killerkoala_mouth(const char *state, const char *message,
                                     uint8_t from_frame_index,
                                     uint8_t to_frame_index,
                                     uint8_t blend_amount);
void __real_render_menu_status(const char *message);
void __real_render_koalagotchi_action(const char *action_title,
                                      uint8_t frame_index);

static uint16_t rgb565_be(uint8_t red, uint8_t green, uint8_t blue)
{
    uint16_t value = (uint16_t)(((red & 0xf8U) << 8) |
                                ((green & 0xfcU) << 3) |
                                (blue >> 3));
    return sys_cpu_to_be16(value);
}

static void proc_set_pixel(int x, int y, uint16_t color)
{
    if (x < 0 || y < 0 || x >= PROC_W || y >= PROC_H) {
        return;
    }
    procedural_frame[(y * PROC_W) + x] = color;
}

static void proc_fill_rect(int x, int y, int width, int height, uint16_t color)
{
    int x0 = MAX(x, 0);
    int y0 = MAX(y, 0);
    int x1 = MIN(x + width, PROC_W);
    int y1 = MIN(y + height, PROC_H);
    for (int row = y0; row < y1; row++) {
        for (int col = x0; col < x1; col++) {
            proc_set_pixel(col, row, color);
        }
    }
}

static void proc_fill_ellipse(int cx, int cy, int rx, int ry, uint16_t color)
{
    if (rx <= 0 || ry <= 0) {
        return;
    }
    int64_t rx2 = (int64_t)rx * rx;
    int64_t ry2 = (int64_t)ry * ry;
    int64_t limit = rx2 * ry2;
    for (int y = -ry; y <= ry; y++) {
        int64_t y_term = (int64_t)y * y * rx2;
        for (int x = -rx; x <= rx; x++) {
            if (((int64_t)x * x * ry2) + y_term <= limit) {
                proc_set_pixel(cx + x, cy + y, color);
            }
        }
    }
}

static void proc_draw_line(int x0, int y0, int x1, int y1, int thickness,
                           uint16_t color)
{
    int dx = abs(x1 - x0);
    int sx = x0 < x1 ? 1 : -1;
    int dy = -abs(y1 - y0);
    int sy = y0 < y1 ? 1 : -1;
    int err = dx + dy;
    for (;;) {
        proc_fill_ellipse(x0, y0, MAX(1, thickness), MAX(1, thickness), color);
        if (x0 == x1 && y0 == y1) {
            break;
        }
        int twice = err * 2;
        if (twice >= dy) {
            err += dy;
            x0 += sx;
        }
        if (twice <= dx) {
            err += dx;
            y0 += sy;
        }
    }
}

static void proc_draw_quadratic(int x0, int y0, int cx, int cy,
                                int x1, int y1, int thickness,
                                uint16_t color)
{
    int previous_x = x0;
    int previous_y = y0;
    for (int step = 1; step <= 24; step++) {
        int t = (step * 256) / 24;
        int inverse = 256 - t;
        int x = (inverse * inverse * x0 +
                 2 * inverse * t * cx + t * t * x1) >> 16;
        int y = (inverse * inverse * y0 +
                 2 * inverse * t * cy + t * t * y1) >> 16;
        proc_draw_line(previous_x, previous_y, x, y, thickness, color);
        previous_x = x;
        previous_y = y;
    }
}

static void proc_fill_tooth(int center_x, int top_y, int width, int height,
                            bool points_down, uint16_t color)
{
    for (int row = 0; row < height; row++) {
        int taper = (row * width) / MAX(height, 1);
        int half = MAX(1, (width - taper) / 2);
        int y = points_down ? top_y + row : top_y - row;
        proc_fill_rect(center_x - half, y, half * 2 + 1, 1, color);
    }
}

static int lerp_int(int from, int to, uint8_t amount)
{
    return from + (((to - from) * (int)amount) / 255);
}

static struct mouth_pose pose_for_frame(uint8_t frame)
{
    switch (frame) {
    case 1: /* happy */
        return (struct mouth_pose){82, 92, 0, 0, 118, 72};
    case 2: /* bite */
        return (struct mouth_pose){126, 18, 0, 42, 198, 22};
    case 3: /* snarl */
        return (struct mouth_pose){88, -58, 18, 235, 238, 0};
    case 4: /* sideways grin */
        return (struct mouth_pose){48, 48, 104, 34, 142, 26};
    default: /* smile */
        return (struct mouth_pose){32, 64, 0, 0, 78, 30};
    }
}

static struct mouth_pose blended_pose(uint8_t from_frame, uint8_t to_frame,
                                      uint8_t blend)
{
    struct mouth_pose from = pose_for_frame(from_frame);
    struct mouth_pose to = pose_for_frame(to_frame);
    return (struct mouth_pose){
        lerp_int(from.jaw, to.jaw, blend),
        lerp_int(from.curl, to.curl, blend),
        lerp_int(from.asymmetry, to.asymmetry, blend),
        lerp_int(from.snarl, to.snarl, blend),
        lerp_int(from.teeth, to.teeth, blend),
        lerp_int(from.tongue, to.tongue, blend),
    };
}

static int triangle_wave(int64_t time_ms, int period_ms, int amplitude)
{
    int phase = (int)(time_ms % period_ms);
    int half = period_ms / 2;
    int value = phase <= half ? phase : period_ms - phase;
    return (value * amplitude) / MAX(half, 1);
}

static void draw_procedural_mouth_locked(const char *state,
                                         uint8_t from_frame,
                                         uint8_t to_frame,
                                         uint8_t blend)
{
    const uint16_t deep = rgb565_be(3, 5, 8);
    const uint16_t muzzle = rgb565_be(34, 38, 43);
    const uint16_t muzzle_light = rgb565_be(66, 72, 78);
    const uint16_t cavity = rgb565_be(7, 2, 8);
    const uint16_t gum = rgb565_be(86, 15, 42);
    const uint16_t tooth = rgb565_be(236, 240, 225);
    const uint16_t tooth_shadow = rgb565_be(132, 143, 137);
    const uint16_t tongue = rgb565_be(183, 48, 92);
    const uint16_t purple = rgb565_be(177, 71, 255);
    const uint16_t purple_dim = rgb565_be(72, 29, 105);
    const uint16_t green = rgb565_be(70, 255, 112);
    const uint16_t green_dim = rgb565_be(22, 94, 45);
    const uint16_t black = rgb565_be(0, 0, 0);

    struct mouth_pose pose = blended_pose(from_frame, to_frame, blend);
    int64_t now = k_uptime_get();
    bool speaking = state && strcmp(state, "speaking") == 0;
    bool thinking = state && (strcmp(state, "thinking") == 0 ||
                              strcmp(state, "wake") == 0);

    if (speaking) {
        pose.jaw = MIN(230, pose.jaw + triangle_wave(now, 310, 100));
        pose.asymmetry += triangle_wave(now + 80, 720, 22) - 11;
        pose.tongue = MAX(pose.tongue, 42);
    } else {
        pose.jaw = MIN(230, pose.jaw + triangle_wave(now, 3200, 8));
    }
    if (thinking) {
        pose.asymmetry += triangle_wave(now, 1500, 34) - 17;
    }
    if (state && strcmp(state, "error") == 0) {
        pose.snarl = 255;
        pose.teeth = 255;
        pose.curl = -70;
        pose.jaw = MAX(pose.jaw, 96);
    }

    for (int y = 0; y < PROC_H; y++) {
        uint8_t shade = (uint8_t)(5 + ((y * 14) / PROC_H));
        uint16_t background = rgb565_be(shade, shade + 2, shade + 5);
        proc_fill_rect(0, y, PROC_W, 1, background);
    }

    /* Keep the broad cyber-koala muzzle silhouette from the current artwork. */
    proc_fill_ellipse(100, 47, 94, 42, muzzle);
    proc_fill_ellipse(52, 42, 43, 34, muzzle_light);
    proc_fill_ellipse(148, 42, 43, 34, muzzle_light);
    proc_fill_ellipse(100, 31, 72, 25, muzzle);
    proc_fill_rect(8, 65, 184, 18, deep);

    /* Purple-left and lime-right illumination preserve the existing design. */
    proc_draw_quadratic(13, 61, 24, 14, 84, 18, 3, purple_dim);
    proc_draw_quadratic(187, 61, 176, 14, 116, 18, 3, green_dim);
    proc_draw_line(10, 73, 74, 80, 2, purple);
    proc_draw_line(190, 73, 126, 80, 2, green);

    int jaw_height = 10 + ((pose.jaw * 25) / 255);
    int left_corner = 28 + (pose.asymmetry / 7);
    int right_corner = 172 + (pose.asymmetry / 12);
    int upper_center = 41 - (pose.curl / 18);
    int lower_center = 48 + jaw_height + (pose.curl / 22);

    proc_fill_ellipse(100 + (pose.asymmetry / 18), 48 + jaw_height / 2,
                      72, jaw_height + 7, cavity);
    if (pose.snarl > 80) {
        proc_fill_ellipse(100, 45, 68, 10 + (pose.snarl / 32), gum);
    }

    /* Tongue is geometry, not another image frame. */
    if (pose.tongue > 20 && jaw_height > 15) {
        int tongue_y = 55 + jaw_height / 2;
        int tongue_rx = 26 + pose.tongue / 10;
        int tongue_ry = 4 + pose.tongue / 22;
        proc_fill_ellipse(103 + pose.asymmetry / 24, tongue_y,
                          tongue_rx, tongue_ry, tongue);
        proc_draw_line(103, tongue_y - tongue_ry + 1,
                       103, tongue_y + tongue_ry - 2, 1,
                       rgb565_be(110, 24, 60));
    }

    int tooth_count = 5 + (pose.teeth / 62);
    int spacing = 108 / MAX(tooth_count - 1, 1);
    int tooth_height = 5 + pose.teeth / 30;
    for (int index = 0; index < tooth_count; index++) {
        int x = 46 + index * spacing + ((index & 1) ? pose.asymmetry / 40 : 0);
        proc_fill_tooth(x + 1, 47, 10, tooth_height, true, tooth_shadow);
        proc_fill_tooth(x, 46, 9, tooth_height, true, tooth);
        if (jaw_height > 20 && pose.teeth > 105) {
            proc_fill_tooth(x + spacing / 2, 55 + jaw_height,
                            8, MAX(4, tooth_height - 2), false, tooth);
        }
    }

    /* Continuously deform the same upper and lower cyber lips. */
    proc_draw_quadratic(left_corner, 49,
                        66 + pose.asymmetry / 18, upper_center,
                        100, 46 - pose.curl / 26,
                        3, purple);
    proc_draw_quadratic(100, 46 - pose.curl / 26,
                        136 + pose.asymmetry / 22, upper_center,
                        right_corner, 49,
                        3, green);
    proc_draw_quadratic(left_corner, 50,
                        66 + pose.asymmetry / 20, lower_center,
                        100, 55 + jaw_height,
                        3, purple);
    proc_draw_quadratic(100, 55 + jaw_height,
                        136 + pose.asymmetry / 18, lower_center,
                        right_corner, 50,
                        3, green);

    /* Dark lip core and neon specular marks retain the original aggressive look. */
    proc_draw_quadratic(left_corner + 3, 50, 70, 48, 100, 49, 1, black);
    proc_draw_quadratic(100, 49, 132, 48, right_corner - 3, 50, 1, black);
    proc_draw_line(35, 42, 61, 31 - pose.snarl / 30, 2, purple);
    proc_draw_line(165, 42, 139, 31 - pose.snarl / 30, 2, green);
    proc_fill_ellipse(48, 27, 3, 2, purple);
    proc_fill_ellipse(152, 27, 3, 2, green);

    const struct display_buffer_descriptor descriptor = {
        .buf_size = sizeof(procedural_frame),
        .width = PROC_W,
        .height = PROC_H,
        .pitch = PROC_W,
    };
    if (device_is_ready(procedural_display)) {
        (void)display_write(procedural_display, PROC_X, PROC_Y,
                            &descriptor, procedural_frame);
    }
}

static void ensure_base_art_locked(void)
{
    if (!base_art_dirty) {
        return;
    }
    __real_render_killerkoala_mouth("idle", "KILLERKOALA", 0, 0, 0);
    base_art_dirty = false;
}

static void procedural_work_handler(struct k_work *work);
K_WORK_DELAYABLE_DEFINE(procedural_work, procedural_work_handler);

static void procedural_work_handler(struct k_work *work)
{
    ARG_UNUSED(work);
    int delay_ms = 0;

    k_mutex_lock(&procedural_render_mutex, K_FOREVER);
    if (procedural_mode == PROC_MODE_MENU_KOALAGOTCHI ||
        procedural_mode == PROC_MODE_ACTION_KOALAGOTCHI) {
        koalagotchi_frame = (uint8_t)((koalagotchi_frame + 1U) % 8U);
        __real_render_koalagotchi_action(active_message, koalagotchi_frame);
        base_art_dirty = true;
        delay_ms = KOALA_ANIMATION_MS;
    } else if (procedural_mode == PROC_MODE_ERROR) {
        error_banner_phase = !error_banner_phase;
        if (error_banner_phase) {
            __real_render_menu_status("ERROR");
            base_art_dirty = true;
        } else {
            ensure_base_art_locked();
            draw_procedural_mouth_locked("error", active_from_frame,
                                         active_to_frame, active_blend);
        }
        delay_ms = KOALA_ERROR_ALARM_MS;
    }
    k_mutex_unlock(&procedural_render_mutex);

    if (delay_ms > 0) {
        (void)k_work_reschedule(&procedural_work, K_MSEC(delay_ms));
    }
}

static void activate_koalagotchi(enum procedural_mode mode,
                                 const char *message, uint8_t first_frame)
{
    k_mutex_lock(&procedural_render_mutex, K_FOREVER);
    procedural_mode = mode;
    snprintf(active_message, sizeof(active_message), "%s",
             message && message[0] ? message :
             (mode == PROC_MODE_MENU_KOALAGOTCHI ? "MENU" : "PLAYING"));
    koalagotchi_frame = first_frame % 8U;
    error_banner_phase = false;
    __real_render_koalagotchi_action(active_message, koalagotchi_frame);
    base_art_dirty = true;
    k_mutex_unlock(&procedural_render_mutex);
    (void)k_work_reschedule(&procedural_work, K_MSEC(KOALA_ANIMATION_MS));
}

void __wrap_render_menu_status(const char *message)
{
    activate_koalagotchi(PROC_MODE_MENU_KOALAGOTCHI,
                         message && message[0] ? message : "MENU", 0);
}

void __wrap_render_koalagotchi_action(const char *action_title,
                                      uint8_t frame_index)
{
    activate_koalagotchi(PROC_MODE_ACTION_KOALAGOTCHI,
                         action_title && action_title[0] ? action_title : "PLAYING",
                         frame_index);
}

void __wrap_render_killerkoala_mouth(const char *state, const char *message,
                                     uint8_t from_frame_index,
                                     uint8_t to_frame_index,
                                     uint8_t blend_amount)
{
    const char *resolved_state = state && state[0] ? state : "idle";

    if (!strcmp(resolved_state, "menu") ||
        !strcmp(resolved_state, "menu_highlight") ||
        !strcmp(resolved_state, "menu_select")) {
        activate_koalagotchi(PROC_MODE_MENU_KOALAGOTCHI, message, 0);
        return;
    }
    if (!strcmp(resolved_state, "action") ||
        !strcmp(resolved_state, "koalagotchi_action")) {
        activate_koalagotchi(PROC_MODE_ACTION_KOALAGOTCHI, message, 0);
        return;
    }

    bool is_error = strcmp(resolved_state, "error") == 0;
    k_mutex_lock(&procedural_render_mutex, K_FOREVER);
    procedural_mode = is_error ? PROC_MODE_ERROR : PROC_MODE_MOUTH;
    error_banner_phase = false;
    active_from_frame = from_frame_index;
    active_to_frame = to_frame_index;
    active_blend = blend_amount;
    snprintf(active_message, sizeof(active_message), "%s",
             message && message[0] ? message :
             (is_error ? "ERROR" : "KILLERKOALA"));

    if (!is_error) {
        (void)k_work_cancel_delayable(&procedural_work);
    }
    ensure_base_art_locked();
    draw_procedural_mouth_locked(resolved_state, from_frame_index,
                                 to_frame_index, blend_amount);
    k_mutex_unlock(&procedural_render_mutex);

    if (is_error) {
        (void)k_work_reschedule(&procedural_work,
                                K_MSEC(KOALA_ERROR_ALARM_MS));
    }
}
