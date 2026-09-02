#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/display.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/byteorder.h>
#include <zephyr/sys/printk.h>
#include <zephyr/sys/util.h>

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "loading_display.h"

/*
 * Stateful overlay for the canonical centered Koalagotchi renderer.
 *
 * The base renderer owns the full 240x135 cyber-jungle scene. This layer keeps
 * its artwork intact while replacing the synthetic mood telemetry with the
 * real shared Koalagotchi health/mood state and adding expression cues to the
 * centered character. It draws only after the base frame has been flushed, so
 * it cannot reactivate the independent mouth animation thread.
 */

#define DISPLAY_NODE DT_CHOSEN(zephyr_display)
#define HUD_WIDTH 240
#define HUD_HEIGHT 135
#define HUD_SCRATCH_PIXELS (52 * 23)

static const struct device *const hud_display = DEVICE_DT_GET(DISPLAY_NODE);
static uint16_t hud_scratch[HUD_SCRATCH_PIXELS];
static K_MUTEX_DEFINE(hud_state_mutex);
static K_MUTEX_DEFINE(hud_draw_mutex);

static int hud_health = 75;
static int hud_progress = -1;
static char hud_mood[16] = "CALM";
static char hud_expression[16] = "SMILE";
static bool hud_announced;

struct hud_state_snapshot {
    int health;
    int progress;
    char mood[16];
    char expression[16];
};

/* Base canonical renderer, renamed source-locally by CMake. */
void koala_centered_render_koalagotchi_action_base(const char *action_title,
                                                    uint8_t frame_index);

static uint16_t hud_rgb565(uint8_t red, uint8_t green, uint8_t blue)
{
    uint16_t value = (uint16_t)(((red & 0xf8U) << 8) |
                                ((green & 0xfcU) << 3) |
                                (blue >> 3));
    return sys_cpu_to_be16(value);
}

static bool hud_contains_ci(const char *text, const char *needle)
{
    if (!text || !needle || !needle[0]) {
        return false;
    }
    size_t needle_len = strlen(needle);
    for (size_t i = 0; text[i]; i++) {
        size_t j = 0;
        while (j < needle_len && text[i + j]) {
            char a = text[i + j];
            char b = needle[j];
            if (a >= 'a' && a <= 'z') a = (char)(a - 'a' + 'A');
            if (b >= 'a' && b <= 'z') b = (char)(b - 'a' + 'A');
            if (a != b) {
                break;
            }
            j++;
        }
        if (j == needle_len) {
            return true;
        }
    }
    return false;
}

static void hud_copy_token(char *dst, size_t dst_len, const char *src,
                           const char *fallback)
{
    const char *value = (src && src[0]) ? src : fallback;
    size_t out = 0;

    if (!dst || dst_len == 0) {
        return;
    }
    for (size_t i = 0; value && value[i] && out + 1 < dst_len; i++) {
        char ch = value[i];
        if (ch >= 'a' && ch <= 'z') {
            ch = (char)(ch - 'a' + 'A');
        }
        if ((ch >= 'A' && ch <= 'Z') || (ch >= '0' && ch <= '9')) {
            dst[out++] = ch;
        } else if ((ch == ' ' || ch == '-' || ch == '_') && out > 0 &&
                   dst[out - 1] != ' ') {
            dst[out++] = ' ';
        }
    }
    while (out > 0 && dst[out - 1] == ' ') {
        out--;
    }
    dst[out] = '\0';
    if (out == 0) {
        snprintf(dst, dst_len, "%s", fallback ? fallback : "");
    }
}

void koala_centered_set_status(int health, const char *mood,
                               const char *expression)
{
    bool announce = false;

    k_mutex_lock(&hud_state_mutex, K_FOREVER);
    hud_health = CLAMP(health, 0, 100);
    hud_copy_token(hud_mood, sizeof(hud_mood), mood, "CALM");
    hud_copy_token(hud_expression, sizeof(hud_expression), expression, "SMILE");
    if (!hud_announced) {
        hud_announced = true;
        announce = true;
    }
    k_mutex_unlock(&hud_state_mutex);

    if (announce) {
        printk("{\"type\":\"t114_koalagotchi_hud\",\"renderer\":\"canonical_centered\",\"contract\":\"stateful_koalagotchi_hud_v2\",\"health_mood_expression\":true,\"center_locked\":true}\n");
    }
}

void koala_centered_set_action_progress(int progress_percent)
{
    k_mutex_lock(&hud_state_mutex, K_FOREVER);
    hud_progress = progress_percent < 0 ? -1 : CLAMP(progress_percent, 0, 100);
    k_mutex_unlock(&hud_state_mutex);
}

static void hud_snapshot(struct hud_state_snapshot *snapshot)
{
    if (!snapshot) {
        return;
    }
    k_mutex_lock(&hud_state_mutex, K_FOREVER);
    snapshot->health = hud_health;
    snapshot->progress = hud_progress;
    snprintf(snapshot->mood, sizeof(snapshot->mood), "%s", hud_mood);
    snprintf(snapshot->expression, sizeof(snapshot->expression), "%s",
             hud_expression);
    k_mutex_unlock(&hud_state_mutex);
}

static void hud_rect(int x, int y, int width, int height, uint16_t color)
{
    if (!device_is_ready(hud_display) || width <= 0 || height <= 0 || x < 0 ||
        y < 0 || x + width > HUD_WIDTH || y + height > HUD_HEIGHT) {
        return;
    }
    size_t pixels = (size_t)width * (size_t)height;
    if (pixels > ARRAY_SIZE(hud_scratch)) {
        return;
    }
    for (size_t i = 0; i < pixels; i++) {
        hud_scratch[i] = color;
    }
    const struct display_buffer_descriptor descriptor = {
        .buf_size = pixels * sizeof(uint16_t),
        .width = (uint16_t)width,
        .height = (uint16_t)height,
        .pitch = (uint16_t)width,
    };
    (void)display_write(hud_display, (uint16_t)x, (uint16_t)y,
                        &descriptor, hud_scratch);
}

static bool hud_glyph(char ch, uint8_t rows[5])
{
    if (ch >= 'a' && ch <= 'z') ch = (char)(ch - 'a' + 'A');
    switch (ch) {
    case 'A': { const uint8_t v[5]={2,5,7,5,5}; memcpy(rows,v,5); return true; }
    case 'B': { const uint8_t v[5]={6,5,6,5,6}; memcpy(rows,v,5); return true; }
    case 'C': { const uint8_t v[5]={3,4,4,4,3}; memcpy(rows,v,5); return true; }
    case 'D': { const uint8_t v[5]={6,5,5,5,6}; memcpy(rows,v,5); return true; }
    case 'E': { const uint8_t v[5]={7,4,6,4,7}; memcpy(rows,v,5); return true; }
    case 'F': { const uint8_t v[5]={7,4,6,4,4}; memcpy(rows,v,5); return true; }
    case 'G': { const uint8_t v[5]={3,4,5,5,3}; memcpy(rows,v,5); return true; }
    case 'H': { const uint8_t v[5]={5,5,7,5,5}; memcpy(rows,v,5); return true; }
    case 'I': { const uint8_t v[5]={7,2,2,2,7}; memcpy(rows,v,5); return true; }
    case 'J': { const uint8_t v[5]={1,1,1,5,2}; memcpy(rows,v,5); return true; }
    case 'K': { const uint8_t v[5]={5,5,6,5,5}; memcpy(rows,v,5); return true; }
    case 'L': { const uint8_t v[5]={4,4,4,4,7}; memcpy(rows,v,5); return true; }
    case 'M': { const uint8_t v[5]={5,7,7,5,5}; memcpy(rows,v,5); return true; }
    case 'N': { const uint8_t v[5]={5,7,7,7,5}; memcpy(rows,v,5); return true; }
    case 'O': { const uint8_t v[5]={2,5,5,5,2}; memcpy(rows,v,5); return true; }
    case 'P': { const uint8_t v[5]={6,5,6,4,4}; memcpy(rows,v,5); return true; }
    case 'Q': { const uint8_t v[5]={2,5,5,3,1}; memcpy(rows,v,5); return true; }
    case 'R': { const uint8_t v[5]={6,5,6,5,5}; memcpy(rows,v,5); return true; }
    case 'S': { const uint8_t v[5]={3,4,2,1,6}; memcpy(rows,v,5); return true; }
    case 'T': { const uint8_t v[5]={7,2,2,2,2}; memcpy(rows,v,5); return true; }
    case 'U': { const uint8_t v[5]={5,5,5,5,7}; memcpy(rows,v,5); return true; }
    case 'V': { const uint8_t v[5]={5,5,5,5,2}; memcpy(rows,v,5); return true; }
    case 'W': { const uint8_t v[5]={5,5,7,7,5}; memcpy(rows,v,5); return true; }
    case 'X': { const uint8_t v[5]={5,5,2,5,5}; memcpy(rows,v,5); return true; }
    case 'Y': { const uint8_t v[5]={5,5,2,2,2}; memcpy(rows,v,5); return true; }
    case 'Z': { const uint8_t v[5]={7,1,2,4,7}; memcpy(rows,v,5); return true; }
    case '0': { const uint8_t v[5]={7,5,5,5,7}; memcpy(rows,v,5); return true; }
    case '1': { const uint8_t v[5]={2,6,2,2,7}; memcpy(rows,v,5); return true; }
    case '2': { const uint8_t v[5]={6,1,2,4,7}; memcpy(rows,v,5); return true; }
    case '3': { const uint8_t v[5]={6,1,2,1,6}; memcpy(rows,v,5); return true; }
    case '4': { const uint8_t v[5]={5,5,7,1,1}; memcpy(rows,v,5); return true; }
    case '5': { const uint8_t v[5]={7,4,6,1,6}; memcpy(rows,v,5); return true; }
    case '6': { const uint8_t v[5]={3,4,6,5,2}; memcpy(rows,v,5); return true; }
    case '7': { const uint8_t v[5]={7,1,2,2,2}; memcpy(rows,v,5); return true; }
    case '8': { const uint8_t v[5]={2,5,2,5,2}; memcpy(rows,v,5); return true; }
    case '9': { const uint8_t v[5]={2,5,3,1,6}; memcpy(rows,v,5); return true; }
    case ' ': memset(rows,0,5); return true;
    default: { const uint8_t v[5]={7,1,2,0,2}; memcpy(rows,v,5); return false; }
    }
}

static void hud_char(int x, int y, char ch, uint16_t color)
{
    uint8_t rows[5];
    (void)hud_glyph(ch, rows);
    for (int row = 0; row < 5; row++) {
        for (int col = 0; col < 3; col++) {
            if (rows[row] & (1U << (2 - col))) {
                hud_rect(x + col, y + row, 1, 1, color);
            }
        }
    }
}

static void hud_text(int x, int y, const char *text, uint16_t color,
                     int max_chars)
{
    if (!text) {
        return;
    }
    for (int i = 0; text[i] && i < max_chars; i++) {
        hud_char(x + (i * 4), y, text[i], color);
    }
}

static const char *hud_mood_code(const char *mood)
{
    if (hud_contains_ci(mood, "ANGR") || hud_contains_ci(mood, "CRANK") ||
        hud_contains_ci(mood, "HOST") || hud_contains_ci(mood, "SNARL")) {
        return "ANGR";
    }
    if (hud_contains_ci(mood, "EAT") || hud_contains_ci(mood, "FEED") ||
        hud_contains_ci(mood, "CHEW")) {
        return "FEED";
    }
    if (hud_contains_ci(mood, "PATROL") || hud_contains_ci(mood, "MISCH") ||
        hud_contains_ci(mood, "BOOM") || hud_contains_ci(mood, "SIDE")) {
        return "MISC";
    }
    if (hud_contains_ci(mood, "SAD") || hud_contains_ci(mood, "DOWN") ||
        hud_contains_ci(mood, "DISAPP")) {
        return "SAD";
    }
    if (hud_contains_ci(mood, "HAPPY") || hud_contains_ci(mood, "EXCIT")) {
        return "HYPE";
    }
    if (hud_contains_ci(mood, "CALM")) {
        return "CALM";
    }
    return mood && mood[0] ? mood : "CALM";
}

static void hud_health_panel(const struct hud_state_snapshot *state)
{
    const uint16_t panel = hud_rgb565(5, 18, 23);
    const uint16_t green = hud_rgb565(54, 255, 118);
    const uint16_t yellow = hud_rgb565(255, 225, 94);
    const uint16_t purple = hud_rgb565(190, 72, 255);
    const uint16_t white = hud_rgb565(222, 230, 233);
    const uint16_t black = hud_rgb565(2, 4, 6);
    uint16_t health_color = state->health >= 60 ? green :
        (state->health >= 30 ? yellow : purple);
    char hp[6];

    /* Preserve the canonical outer panel border at x=6/y=20. */
    hud_rect(7, 21, 50, 21, panel);
    hud_text(10, 23, "MOOD", white, 4);
    hud_text(10, 31, hud_mood_code(state->mood), health_color, 4);

    hud_rect(34, 31, 19, 5, black);
    hud_rect(34, 31, 19, 1, hud_rgb565(22, 111, 65));
    hud_rect(34, 35, 19, 1, hud_rgb565(22, 111, 65));
    hud_rect(34, 31, 1, 5, hud_rgb565(22, 111, 65));
    hud_rect(52, 31, 1, 5, hud_rgb565(22, 111, 65));
    int active = (17 * state->health) / 100;
    if (active > 0) {
        hud_rect(35, 32, active, 3, health_color);
    }

    snprintf(hp, sizeof(hp), "HP%02d", state->health);
    hud_text(10, 37, hp, health_color, 5);
}

static void hud_expression_overlay(const struct hud_state_snapshot *state,
                                   uint8_t frame_index)
{
    const uint16_t purple = hud_rgb565(210, 62, 255);
    const uint16_t green = hud_rgb565(70, 255, 112);
    const uint16_t white = hud_rgb565(245, 248, 240);
    const uint16_t dark = hud_rgb565(4, 5, 7);
    static const int8_t bob[8] = {0, -1, -1, 0, 0, 1, 1, 0};
    int yoff = bob[frame_index & 7U];
    int cx = 120;
    int cy = 66 + yoff;

    if (hud_contains_ci(state->expression, "SNARL") || state->health <= 25) {
        for (int step = 0; step < 4; step++) {
            hud_rect(cx - 17 + (step * 3), cy - 18 + (step * 2), 5, 2,
                     purple);
            hud_rect(cx + 12 - (step * 3), cy - 18 + (step * 2), 5, 2,
                     green);
        }
        hud_rect(cx - 11, cy + 12, 22, 3, dark);
        hud_rect(cx - 10, cy + 12, 9, 1, purple);
        hud_rect(cx + 1, cy + 12, 9, 1, green);
    } else if (hud_contains_ci(state->expression, "BITE")) {
        hud_rect(cx - 9, cy + 10, 18, 7, dark);
        hud_rect(cx - 7, cy + 10, 3, 3, white);
        hud_rect(cx + 4, cy + 10, 3, 3, white);
        hud_rect(cx - 8, cy + 16, 7, 1, purple);
        hud_rect(cx + 1, cy + 16, 7, 1, green);
    } else if (hud_contains_ci(state->expression, "SIDE") ||
               hud_contains_ci(state->expression, "GRIN") ||
               hud_contains_ci(state->expression, "MISCH")) {
        hud_rect(cx - 10, cy + 11, 18, 2, dark);
        hud_rect(cx - 12, cy + 9, 4, 2, purple);
        hud_rect(cx + 8, cy + 12, 4, 2, green);
    }
}

static void hud_progress_strip(const struct hud_state_snapshot *state)
{
    if (state->progress < 0) {
        return;
    }
    const uint16_t panel = hud_rgb565(5, 18, 23);
    const uint16_t green = hud_rgb565(54, 255, 118);
    const uint16_t green_dim = hud_rgb565(22, 111, 65);
    const uint16_t white = hud_rgb565(222, 230, 233);
    const uint16_t black = hud_rgb565(2, 4, 6);
    char pct[5];

    hud_rect(66, 97, 108, 11, panel);
    hud_text(69, 100, "RUN", white, 3);
    snprintf(pct, sizeof(pct), "%03d", state->progress);
    hud_text(85, 100, pct, green, 3);
    hud_rect(102, 100, 65, 5, black);
    hud_rect(102, 100, 65, 1, green_dim);
    hud_rect(102, 104, 65, 1, green_dim);
    int active = (63 * state->progress) / 100;
    if (active > 0) {
        hud_rect(103, 101, active, 3, green);
    }
}

void koala_centered_render_koalagotchi_action(const char *action_title,
                                               uint8_t frame_index)
{
    struct hud_state_snapshot state;

    /* Full canonical frame first; compact telemetry/expression overlays second. */
    koala_centered_render_koalagotchi_action_base(action_title, frame_index);
    hud_snapshot(&state);

    k_mutex_lock(&hud_draw_mutex, K_FOREVER);
    hud_health_panel(&state);
    hud_expression_overlay(&state, frame_index);
    hud_progress_strip(&state);
    k_mutex_unlock(&hud_draw_mutex);
}
