#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/display.h>
#include <zephyr/sys/byteorder.h>
#include <zephyr/sys/util.h>

#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>

#define KOALA_TFT_WIDTH 240
#define KOALA_TFT_HEIGHT 135
#define DISPLAY_NODE DT_CHOSEN(zephyr_display)

static const struct device *const koala_display = DEVICE_DT_GET(DISPLAY_NODE);
static uint16_t koala_framebuffer[KOALA_TFT_WIDTH * KOALA_TFT_HEIGHT];

static uint16_t koala_rgb565(uint8_t red, uint8_t green, uint8_t blue)
{
    uint16_t value = (uint16_t)(((red & 0xf8U) << 8) |
                                ((green & 0xfcU) << 3) |
                                (blue >> 3));
    return sys_cpu_to_be16(value);
}

static void koala_pixel(int x, int y, uint16_t color)
{
    if (x < 0 || y < 0 || x >= KOALA_TFT_WIDTH || y >= KOALA_TFT_HEIGHT) {
        return;
    }
    koala_framebuffer[(y * KOALA_TFT_WIDTH) + x] = color;
}

static void koala_fill_rect(int x, int y, int width, int height, uint16_t color)
{
    int x0 = MAX(0, x);
    int y0 = MAX(0, y);
    int x1 = MIN(KOALA_TFT_WIDTH, x + width);
    int y1 = MIN(KOALA_TFT_HEIGHT, y + height);
    for (int row = y0; row < y1; row++) {
        for (int col = x0; col < x1; col++) {
            koala_pixel(col, row, color);
        }
    }
}

static void koala_fill_circle(int cx, int cy, int radius, uint16_t color)
{
    int rr = radius * radius;
    for (int y = -radius; y <= radius; y++) {
        for (int x = -radius; x <= radius; x++) {
            if ((x * x) + (y * y) <= rr) {
                koala_pixel(cx + x, cy + y, color);
            }
        }
    }
}

static void koala_fill_ellipse(int cx, int cy, int rx, int ry, uint16_t color)
{
    if (rx <= 0 || ry <= 0) {
        return;
    }
    int64_t rx2 = (int64_t)rx * rx;
    int64_t ry2 = (int64_t)ry * ry;
    int64_t limit = rx2 * ry2;
    for (int y = -ry; y <= ry; y++) {
        for (int x = -rx; x <= rx; x++) {
            if (((int64_t)x * x * ry2) + ((int64_t)y * y * rx2) <= limit) {
                koala_pixel(cx + x, cy + y, color);
            }
        }
    }
}

static void koala_draw_leaf(int cx, int cy, uint16_t fill, uint16_t edge)
{
    for (int x = -8; x <= 8; x++) {
        int half = 4 - (ABS(x) / 2);
        if (half < 1) {
            half = 1;
        }
        koala_fill_rect(cx + x, cy - half, 1, (half * 2) + 1, fill);
    }
    koala_fill_rect(cx - 7, cy, 15, 1, edge);
}

static void koala_draw_eye(int cx, int cy, uint16_t neon, bool blink, bool look_left)
{
    const uint16_t black = koala_rgb565(2, 5, 8);
    const uint16_t white = koala_rgb565(245, 248, 250);
    if (blink) {
        koala_fill_rect(cx - 7, cy - 1, 15, 3, neon);
        return;
    }
    koala_fill_ellipse(cx, cy, 9, 7, neon);
    koala_fill_circle(cx + (look_left ? -2 : 2), cy + 1, 3, black);
    koala_fill_rect(cx + (look_left ? -3 : 1), cy - 3, 2, 2, white);
}

static void koala_flush(void)
{
    if (!device_is_ready(koala_display)) {
        return;
    }
    const struct display_buffer_descriptor descriptor = {
        .buf_size = sizeof(koala_framebuffer),
        .width = KOALA_TFT_WIDTH,
        .height = KOALA_TFT_HEIGHT,
        .pitch = KOALA_TFT_WIDTH,
    };
    (void)display_write(koala_display, 0, 0, &descriptor, koala_framebuffer);
}

void koala_centered_render_koalagotchi_action(const char *action_title,
                                               uint8_t frame_index)
{
    ARG_UNUSED(action_title);

    const uint16_t background = koala_rgb565(2, 8, 11);
    const uint16_t panel = koala_rgb565(5, 18, 22);
    const uint16_t purple = koala_rgb565(177, 71, 255);
    const uint16_t green = koala_rgb565(70, 255, 112);
    const uint16_t fur = koala_rgb565(105, 116, 126);
    const uint16_t fur_dark = koala_rgb565(55, 64, 72);
    const uint16_t fur_light = koala_rgb565(195, 205, 211);
    const uint16_t muzzle = koala_rgb565(218, 226, 229);
    const uint16_t black = koala_rgb565(3, 5, 7);
    const uint16_t branch = koala_rgb565(93, 52, 20);

    static const int8_t bob[8] = {0, -1, -2, -1, 0, 1, 2, 1};
    uint8_t phase = frame_index % 8U;
    int yoff = bob[phase];
    bool blink = phase == 3U || phase == 7U;
    bool ear_twitch = phase == 1U || phase == 5U;

    for (size_t index = 0; index < ARRAY_SIZE(koala_framebuffer); index++) {
        koala_framebuffer[index] = background;
    }

    /* Cyber jungle frame. The character stays centered; only expression and
     * a tiny breathing/bob motion animate between frames. */
    koala_fill_rect(0, 0, KOALA_TFT_WIDTH, 4, purple);
    koala_fill_rect(0, KOALA_TFT_HEIGHT - 4, KOALA_TFT_WIDTH, 4, green);
    koala_fill_rect(0, 4, 4, KOALA_TFT_HEIGHT - 8, purple);
    koala_fill_rect(KOALA_TFT_WIDTH - 4, 4, 4, KOALA_TFT_HEIGHT - 8, green);
    koala_fill_rect(9, 9, 35, 2, panel);
    koala_fill_rect(KOALA_TFT_WIDTH - 44, 9, 35, 2, panel);

    koala_draw_leaf(22, 23, green, purple);
    koala_draw_leaf(218, 24, purple, green);
    koala_draw_leaf(20, 83, purple, green);
    koala_draw_leaf(220, 82, green, purple);

    /* Branch and body. */
    koala_fill_rect(34, 112, 172, 7, branch);
    koala_fill_rect(34, 112, 172, 2, green);
    koala_fill_ellipse(120, 101 + yoff, 36, 31, fur_dark);
    koala_fill_ellipse(120, 99 + yoff, 28, 27, fur);
    koala_fill_ellipse(120, 108 + yoff, 18, 15, fur_light);

    /* Ears and head. */
    int ear_delta = ear_twitch ? 1 : 0;
    koala_fill_circle(78, 42 + yoff - ear_delta, 23, fur_dark);
    koala_fill_circle(162, 42 + yoff + ear_delta, 23, fur_dark);
    koala_fill_circle(78, 42 + yoff - ear_delta, 13, purple);
    koala_fill_circle(162, 42 + yoff + ear_delta, 13, green);
    koala_fill_circle(78, 42 + yoff - ear_delta, 9, fur_light);
    koala_fill_circle(162, 42 + yoff + ear_delta, 9, fur_light);

    koala_fill_ellipse(120, 58 + yoff, 48, 43, fur);
    koala_fill_ellipse(120, 68 + yoff, 31, 24, muzzle);

    /* Brows remain attached to the face and shift subtly with the phase. */
    int brow = (phase == 2U || phase == 6U) ? 2 : 0;
    koala_fill_rect(91, 42 + yoff + brow, 20, 3, purple);
    koala_fill_rect(129, 42 + yoff + brow, 20, 3, green);

    koala_draw_eye(103, 55 + yoff, purple, blink, true);
    koala_draw_eye(137, 55 + yoff, green, blink, false);

    koala_fill_ellipse(120, 70 + yoff, 11, 8, black);
    koala_fill_rect(119, 77 + yoff, 3, 7, black);

    /* Small asymmetric grin gives it the cyber-Koalagotchi personality
     * without turning the action scene into another text/menu screen. */
    koala_fill_rect(104, 85 + yoff, 15, 2, purple);
    koala_fill_rect(119, 86 + yoff, 18, 2, green);
    if (phase & 1U) {
        koala_fill_rect(134, 84 + yoff, 6, 2, green);
    } else {
        koala_fill_rect(100, 83 + yoff, 6, 2, purple);
    }

    koala_flush();
}
