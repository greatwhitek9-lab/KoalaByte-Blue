#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/display.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/byteorder.h>
#include <zephyr/sys/printk.h>
#include <zephyr/sys/util.h>

#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/*
 * Continuous original-art mouth renderer.
 *
 * The approved KillerKoala smile is the only source texture. Animation is
 * generated procedurally on every tick by articulating the grin, mouth cavity,
 * lower jaw, cheeks, and fangs. No still expression bitmap is selected at
 * runtime. Every tick submits a complete 240x135 RGB565 frame from a dedicated
 * thread so the autonomous idle motion does not depend on the Pi or USB input.
 */

#define DISPLAY_NODE DT_CHOSEN(zephyr_display)
#define TFT_WIDTH 240
#define TFT_HEIGHT 135
#define ORIGINAL_FRAME_BYTES 64800
#define MOTION_TICK_MS 42
#define MOTION_THREAD_STACK 3072
#define MOTION_THREAD_PRIORITY 7
#define RENDER_HEARTBEAT_FRAMES 72U

/* Coordinates measured against the approved 240x135 artwork. */
#define WARP_X0 38
#define WARP_X1 202
#define WARP_Y0 68
#define WARP_Y1 132
#define MOUTH_CENTER_X 120
#define MOUTH_BASE_Y 84
#define MOUTH_HALF_WIDTH 82
#define INNER_MOUTH_RGB565 0x0000U

static const struct device *const motion_display = DEVICE_DT_GET(DISPLAY_NODE);
static uint16_t motion_framebuffer[TFT_WIDTH * TFT_HEIGHT] __aligned(4);

static const uint8_t original_killerkoala_face_rgb565_be[] __aligned(4) = {
#include "killerkoala_cyber_mouth_smile_rgb565.inc"
};
BUILD_ASSERT(sizeof(original_killerkoala_face_rgb565_be) == ORIGINAL_FRAME_BYTES,
             "Original KillerKoala face must be exactly 240x135 RGB565");
BUILD_ASSERT(sizeof(motion_framebuffer) == ORIGINAL_FRAME_BYTES,
             "T114 animation framebuffer must be exactly 240x135 RGB565");

/* Base display functions from loading_display.c after CMake symbol routing. */
void koala_base_render_menu_status(const char *message);
void koala_base_render_koalagotchi_action(const char *action_title,
                                          uint8_t frame_index);

static K_MUTEX_DEFINE(motion_mutex);
static K_SEM_DEFINE(motion_wake_sem, 0, 1);

static bool motion_active;
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
static uint32_t rendered_frames;
static uint32_t changed_pixels;
static uint32_t frame_signature;
static int last_display_rc;

static int integer_abs(int value)
{
    return value < 0 ? -value : value;
}

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

/* Values are continuous deformation targets, never bitmap frame IDs. */
static struct texture_pose pose_for_id(uint8_t pose)
{
    switch (pose) {
    case 1: /* happy/open */
        return (struct texture_pose){8, 7, 0, 2};
    case 2: /* bite */
        return (struct texture_pose){13, 1, 0, -1};
    case 3: /* snarl */
        return (struct texture_pose){9, -7, 3, 5};
    case 4: /* asymmetric grin */
        return (struct texture_pose){6, 6, 7, 2};
    default: /* relaxed smile */
        return (struct texture_pose){0, 3, 0, 0};
    }
}

static int lerp_pose_value(int from, int to, uint8_t amount)
{
    return from + (((to - from) * (int)amount) / 255);
}

static struct texture_pose lerp_pose(struct texture_pose from,
                                     struct texture_pose to,
                                     uint8_t amount)
{
    return (struct texture_pose){
        lerp_pose_value(from.open, to.open, amount),
        lerp_pose_value(from.curl, to.curl, amount),
        lerp_pose_value(from.asymmetry, to.asymmetry, amount),
        lerp_pose_value(from.width, to.width, amount),
    };
}

static uint8_t smoothstep_u8(uint32_t elapsed, uint32_t duration)
{
    if (duration == 0U || elapsed >= duration) {
        return UINT8_MAX;
    }
    uint32_t x = (elapsed * 255U) / duration;
    uint32_t eased = (x * x * ((3U * 255U) - (2U * x)) + 32512U) /
                     65025U;
    return (uint8_t)MIN(eased, 255U);
}

static struct texture_pose blended_pose_target(void)
{
    return lerp_pose(pose_for_id(motion_from_pose),
                     pose_for_id(motion_to_pose), motion_pose_blend);
}

static struct texture_pose autonomous_idle_pose(int64_t now)
{
    /*
     * An approximately ten-second loop starts moving immediately after boot:
     * smile -> smirk -> smile -> bite -> smile -> snarl -> smile.
     */
    static const struct texture_pose poses[] = {
        {0, 3, 0, 0},   /* smile */
        {6, 7, 7, 2},   /* smirk */
        {1, 3, 0, 0},   /* smile */
        {12, 1, 0, -1}, /* bite */
        {1, 3, 0, 0},   /* smile */
        {9, -7, 3, 5},  /* snarl */
        {0, 3, 0, 0},   /* smile */
    };
    static const uint16_t segment_ms[] = {
        1600, 1100, 1800, 900, 1700, 900, 2000,
    };
    uint32_t cycle_ms = 0U;

    for (size_t index = 0; index < ARRAY_SIZE(segment_ms); index++) {
        cycle_ms += segment_ms[index];
    }

    uint32_t phase = (uint32_t)(now % cycle_ms);
    for (size_t index = 0; index < ARRAY_SIZE(segment_ms); index++) {
        uint32_t duration = segment_ms[index];
        if (phase < duration) {
            size_t next = (index + 1U) % ARRAY_SIZE(poses);
            return lerp_pose(poses[index], poses[next],
                             smoothstep_u8(phase, duration));
        }
        phase -= duration;
    }
    return poses[0];
}

static void update_motion_targets(const char *state, int64_t now)
{
    const char *resolved = state && state[0] ? state : "idle";
    bool idle = !strcmp(resolved, "idle") || !strcmp(resolved, "listening");
    struct texture_pose pose = idle ? autonomous_idle_pose(now) :
                                      blended_pose_target();
    int target_open = pose.open;
    int target_curl = pose.curl;
    int target_asymmetry = pose.asymmetry;
    int target_width = pose.width;

    if (!strcmp(resolved, "speaking")) {
        /* Irregular overlapping envelopes produce syllables and short pauses. */
        target_open = 4 + triangle_wave(now, 277, 9) +
                      triangle_wave(now + 83, 167, 5) +
                      triangle_wave(now + 211, 431, 3);
        target_curl = 2 + signed_triangle(now + 41, 719, 3);
        target_asymmetry = signed_triangle(now + 97, 1049, 3);
        target_width = 1 + signed_triangle(now, 607, 2);
    } else if (!strcmp(resolved, "wake") ||
               !strcmp(resolved, "thinking")) {
        target_open = 5 + triangle_wave(now, 1350, 5);
        target_curl = pose.curl + signed_triangle(now, 2100, 2);
        target_asymmetry = pose.asymmetry + signed_triangle(now, 1250, 3);
        target_width = pose.width + 1;
    } else if (!strcmp(resolved, "success")) {
        target_open = 2 + triangle_wave(now, 2200, 3);
        target_curl = MAX(pose.curl, 8);
        target_asymmetry = signed_triangle(now, 3900, 1);
        target_width = MAX(pose.width, 3);
    } else if (!strcmp(resolved, "error") ||
               !strcmp(resolved, "angry")) {
        target_open = 10 + triangle_wave(now, 760, 5);
        target_curl = -8;
        target_asymmetry = pose.asymmetry + signed_triangle(now, 1100, 4);
        target_width = 6;
    } else if (idle) {
        target_open = pose.open + triangle_wave(now, 3100, 2);
        target_curl = pose.curl + signed_triangle(now, 5100, 1);
        target_asymmetry = pose.asymmetry +
                           signed_triangle(now + 400, 4300, 1);
        target_width = pose.width + signed_triangle(now, 6200, 1);
    }

    current_open = approach(current_open, CLAMP(target_open, 0, 23), 3);
    current_curl = approach(current_curl, CLAMP(target_curl, -9, 10), 1);
    current_asymmetry = approach(current_asymmetry,
                                 CLAMP(target_asymmetry, -9, 9), 1);
    current_width = approach(current_width, CLAMP(target_width, -3, 7), 1);
}

static uint32_t sparse_frame_signature(void)
{
    uint32_t hash = 2166136261U;

    for (size_t index = 0; index < ARRAY_SIZE(motion_framebuffer);
         index += 97U) {
        hash ^= (uint32_t)sys_be16_to_cpu(motion_framebuffer[index]);
        hash *= 16777619U;
    }
    return hash;
}

static void build_full_frame_locked(void)
{
    int64_t now = k_uptime_get();
    const uint16_t cavity_be = sys_cpu_to_be16(INNER_MOUTH_RGB565);

    update_motion_targets(motion_state, now);
    memcpy(motion_framebuffer, original_killerkoala_face_rgb565_be,
           sizeof(motion_framebuffer));
    changed_pixels = 0U;

    for (int y = WARP_Y0; y <= WARP_Y1; y++) {
        for (int x = WARP_X0; x <= WARP_X1; x++) {
            int dx = x - MOUTH_CENTER_X;
            int abs_dx = integer_abs(dx);
            if (abs_dx > MOUTH_HALF_WIDTH) {
                continue;
            }

            int x_weight = 255 -
                ((abs_dx * 255) / MAX(MOUTH_HALF_WIDTH, 1));
            x_weight = CLAMP(x_weight, 0, 255);
            /* Ease-out keeps the fangs and grin corners visibly articulated. */
            x_weight = (x_weight * (510 - x_weight)) / 255;

            int corner_curve = (current_curl * dx * dx) /
                               (MOUTH_HALF_WIDTH * MOUTH_HALF_WIDTH);
            int asym_curve = (current_asymmetry * dx) / MOUTH_HALF_WIDTH;
            int mouth_line = MOUTH_BASE_Y - corner_curve - asym_curve;
            int local_open = (current_open * x_weight) / 255;

            if (current_open > 0 && x_weight > 20) {
                local_open = MAX(local_open, current_open / 4);
            }

            int cavity_top = mouth_line + 1;
            int cavity_bottom = mouth_line + local_open;
            uint16_t original = source_pixel(x, y);
            uint16_t output = original;

            if (local_open > 1 && y >= cavity_top && y <= cavity_bottom) {
                uint8_t cavity_blend =
                    (y == cavity_top || y == cavity_bottom) ? 184U : 255U;
                output = blend_pixel(original, cavity_be, cavity_blend);
            } else if (y > cavity_bottom) {
                int denominator = MAX(WARP_Y1 - cavity_bottom, 1);
                int fade = 255 -
                    (((y - cavity_bottom) * 255) / denominator);
                fade = CLAMP(fade, 0, 255);
                int jaw_shift = (local_open * fade) / 255;
                int scale_q8 = 256 +
                    ((current_width * x_weight * 4) / 255);
                scale_q8 = MAX(scale_q8, 220);
                int source_x = MOUTH_CENTER_X +
                    ((dx * 256) / scale_q8) -
                    ((current_asymmetry * fade) / 128);
                int source_y = y - jaw_shift;
                source_x = CLAMP(source_x, WARP_X0, WARP_X1);
                source_y = CLAMP(source_y, WARP_Y0, WARP_Y1);
                output = blend_pixel(original, source_pixel(source_x, source_y),
                                     (uint8_t)MAX(fade, 64));
            } else if (y >= mouth_line - 8) {
                int upper_shift = local_open / 5;
                int source_y = CLAMP(y + upper_shift, WARP_Y0, WARP_Y1);
                output = blend_pixel(original, source_pixel(x, source_y),
                                     (uint8_t)MIN(x_weight, 180));
            }

            motion_framebuffer[(size_t)y * TFT_WIDTH + (size_t)x] = output;
            if (output != original) {
                changed_pixels++;
            }
        }
    }

    frame_signature = sparse_frame_signature();
}

static int write_full_frame_locked(void)
{
    if (!device_is_ready(motion_display)) {
        return -ENODEV;
    }
    const struct display_buffer_descriptor descriptor = {
        .buf_size = sizeof(motion_framebuffer),
        .width = TFT_WIDTH,
        .height = TFT_HEIGHT,
        .pitch = TFT_WIDTH,
    };
    return display_write(motion_display, 0, 0, &descriptor,
                         motion_framebuffer);
}

static void render_motion_locked(void)
{
    build_full_frame_locked();
    last_display_rc = write_full_frame_locked();
    rendered_frames++;

    if (!renderer_announced) {
        renderer_announced = true;
        printk("{\"type\":\"t114_renderer\",\"renderer\":\"original_texture_articulated_jaw_v2\",\"still_frame_cycle\":false,\"texture\":\"original_killerkoala_smile\",\"idle_choreography\":\"smile-smirk-smile-bite-smile-snarl-smile\",\"warp_region\":\"grin-cavity-jaw-cheeks-fangs\",\"refresh\":\"full_frame_dedicated_thread\",\"tick_ms\":%d,\"display_rc\":%d,\"frame_signature\":%u,\"changed_pixels\":%u}\n",
               MOTION_TICK_MS, last_display_rc, frame_signature,
               changed_pixels);
    } else if (last_display_rc != 0 &&
               (rendered_frames <= 3U || rendered_frames % 120U == 0U)) {
        printk("{\"type\":\"t114_renderer_error\",\"renderer\":\"original_texture_articulated_jaw_v2\",\"display_rc\":%d,\"frame\":%u}\n",
               last_display_rc, rendered_frames);
    } else if (rendered_frames % RENDER_HEARTBEAT_FRAMES == 0U) {
        printk("{\"type\":\"t114_renderer_heartbeat\",\"renderer\":\"original_texture_articulated_jaw_v2\",\"frame\":%u,\"display_rc\":%d,\"frame_signature\":%u,\"changed_pixels\":%u,\"open\":%d,\"curl\":%d,\"asymmetry\":%d,\"width\":%d,\"state\":\"%s\"}\n",
               rendered_frames, last_display_rc, frame_signature,
               changed_pixels, current_open, current_curl,
               current_asymmetry, current_width, motion_state);
    }
}

static void motion_thread(void *unused1, void *unused2, void *unused3)
{
    ARG_UNUSED(unused1);
    ARG_UNUSED(unused2);
    ARG_UNUSED(unused3);

    while (true) {
        k_sem_take(&motion_wake_sem, K_FOREVER);
        while (true) {
            k_mutex_lock(&motion_mutex, K_FOREVER);
            if (!motion_active) {
                k_mutex_unlock(&motion_mutex);
                break;
            }
            render_motion_locked();
            k_mutex_unlock(&motion_mutex);
            k_sleep(K_MSEC(MOTION_TICK_MS));
        }
    }
}

K_THREAD_DEFINE(motion_thread_id, MOTION_THREAD_STACK, motion_thread,
                NULL, NULL, NULL, MOTION_THREAD_PRIORITY, 0, 0);

static void stop_motion(void)
{
    k_mutex_lock(&motion_mutex, K_FOREVER);
    motion_active = false;
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
        render_motion_locked();
    }
    k_mutex_unlock(&motion_mutex);

    if (was_inactive) {
        k_sem_give(&motion_wake_sem);
    }
}

void koala_original_render_menu_status(const char *message)
{
    stop_motion();
    koala_base_render_menu_status(message);
}

void koala_original_render_koalagotchi_action(const char *action_title,
                                               uint8_t frame_index)
{
    stop_motion();
    koala_base_render_koalagotchi_action(action_title, frame_index);
}
