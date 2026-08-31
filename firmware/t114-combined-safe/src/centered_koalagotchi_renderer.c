#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/display.h>
#include <zephyr/sys/byteorder.h>
#include <zephyr/sys/util.h>

#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>

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

static void koala_draw_rect(int x, int y, int width, int height, uint16_t color)
{
    if (width <= 0 || height <= 0) {
        return;
    }
    koala_fill_rect(x, y, width, 1, color);
    koala_fill_rect(x, y + height - 1, width, 1, color);
    koala_fill_rect(x, y, 1, height, color);
    koala_fill_rect(x + width - 1, y, 1, height, color);
}

static void koala_draw_line(int x0, int y0, int x1, int y1, uint16_t color)
{
    int dx = ABS(x1 - x0);
    int sx = x0 < x1 ? 1 : -1;
    int dy = -ABS(y1 - y0);
    int sy = y0 < y1 ? 1 : -1;
    int error = dx + dy;

    while (true) {
        koala_pixel(x0, y0, color);
        if (x0 == x1 && y0 == y1) {
            break;
        }
        int twice = error * 2;
        if (twice >= dy) {
            error += dy;
            x0 += sx;
        }
        if (twice <= dx) {
            error += dx;
            y0 += sy;
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

static void koala_draw_circle(int cx, int cy, int radius, uint16_t color)
{
    int x = radius;
    int y = 0;
    int error = 1 - radius;

    while (x >= y) {
        koala_pixel(cx + x, cy + y, color);
        koala_pixel(cx + y, cy + x, color);
        koala_pixel(cx - y, cy + x, color);
        koala_pixel(cx - x, cy + y, color);
        koala_pixel(cx - x, cy - y, color);
        koala_pixel(cx - y, cy - x, color);
        koala_pixel(cx + y, cy - x, color);
        koala_pixel(cx + x, cy - y, color);
        y++;
        if (error < 0) {
            error += (2 * y) + 1;
        } else {
            x--;
            error += (2 * (y - x)) + 1;
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

static bool koala_glyph(char ch, uint8_t rows[5])
{
    if (ch >= 'a' && ch <= 'z') {
        ch = (char)(ch - 'a' + 'A');
    }

    switch (ch) {
    case 'A': { const uint8_t v[5] = {2, 5, 7, 5, 5}; memcpy(rows, v, 5); return true; }
    case 'B': { const uint8_t v[5] = {6, 5, 6, 5, 6}; memcpy(rows, v, 5); return true; }
    case 'C': { const uint8_t v[5] = {3, 4, 4, 4, 3}; memcpy(rows, v, 5); return true; }
    case 'D': { const uint8_t v[5] = {6, 5, 5, 5, 6}; memcpy(rows, v, 5); return true; }
    case 'E': { const uint8_t v[5] = {7, 4, 6, 4, 7}; memcpy(rows, v, 5); return true; }
    case 'F': { const uint8_t v[5] = {7, 4, 6, 4, 4}; memcpy(rows, v, 5); return true; }
    case 'G': { const uint8_t v[5] = {3, 4, 5, 5, 3}; memcpy(rows, v, 5); return true; }
    case 'H': { const uint8_t v[5] = {5, 5, 7, 5, 5}; memcpy(rows, v, 5); return true; }
    case 'I': { const uint8_t v[5] = {7, 2, 2, 2, 7}; memcpy(rows, v, 5); return true; }
    case 'J': { const uint8_t v[5] = {1, 1, 1, 5, 2}; memcpy(rows, v, 5); return true; }
    case 'K': { const uint8_t v[5] = {5, 5, 6, 5, 5}; memcpy(rows, v, 5); return true; }
    case 'L': { const uint8_t v[5] = {4, 4, 4, 4, 7}; memcpy(rows, v, 5); return true; }
    case 'M': { const uint8_t v[5] = {5, 7, 7, 5, 5}; memcpy(rows, v, 5); return true; }
    case 'N': { const uint8_t v[5] = {5, 7, 7, 7, 5}; memcpy(rows, v, 5); return true; }
    case 'O': { const uint8_t v[5] = {2, 5, 5, 5, 2}; memcpy(rows, v, 5); return true; }
    case 'P': { const uint8_t v[5] = {6, 5, 6, 4, 4}; memcpy(rows, v, 5); return true; }
    case 'Q': { const uint8_t v[5] = {2, 5, 5, 3, 1}; memcpy(rows, v, 5); return true; }
    case 'R': { const uint8_t v[5] = {6, 5, 6, 5, 5}; memcpy(rows, v, 5); return true; }
    case 'S': { const uint8_t v[5] = {3, 4, 2, 1, 6}; memcpy(rows, v, 5); return true; }
    case 'T': { const uint8_t v[5] = {7, 2, 2, 2, 2}; memcpy(rows, v, 5); return true; }
    case 'U': { const uint8_t v[5] = {5, 5, 5, 5, 7}; memcpy(rows, v, 5); return true; }
    case 'V': { const uint8_t v[5] = {5, 5, 5, 5, 2}; memcpy(rows, v, 5); return true; }
    case 'W': { const uint8_t v[5] = {5, 5, 7, 7, 5}; memcpy(rows, v, 5); return true; }
    case 'X': { const uint8_t v[5] = {5, 5, 2, 5, 5}; memcpy(rows, v, 5); return true; }
    case 'Y': { const uint8_t v[5] = {5, 5, 2, 2, 2}; memcpy(rows, v, 5); return true; }
    case 'Z': { const uint8_t v[5] = {7, 1, 2, 4, 7}; memcpy(rows, v, 5); return true; }
    case '0': { const uint8_t v[5] = {7, 5, 5, 5, 7}; memcpy(rows, v, 5); return true; }
    case '1': { const uint8_t v[5] = {2, 6, 2, 2, 7}; memcpy(rows, v, 5); return true; }
    case '2': { const uint8_t v[5] = {6, 1, 2, 4, 7}; memcpy(rows, v, 5); return true; }
    case '3': { const uint8_t v[5] = {6, 1, 2, 1, 6}; memcpy(rows, v, 5); return true; }
    case '4': { const uint8_t v[5] = {5, 5, 7, 1, 1}; memcpy(rows, v, 5); return true; }
    case '5': { const uint8_t v[5] = {7, 4, 6, 1, 6}; memcpy(rows, v, 5); return true; }
    case '6': { const uint8_t v[5] = {3, 4, 6, 5, 2}; memcpy(rows, v, 5); return true; }
    case '7': { const uint8_t v[5] = {7, 1, 2, 2, 2}; memcpy(rows, v, 5); return true; }
    case '8': { const uint8_t v[5] = {2, 5, 2, 5, 2}; memcpy(rows, v, 5); return true; }
    case '9': { const uint8_t v[5] = {2, 5, 3, 1, 6}; memcpy(rows, v, 5); return true; }
    case '-': { const uint8_t v[5] = {0, 0, 7, 0, 0}; memcpy(rows, v, 5); return true; }
    case '_': { const uint8_t v[5] = {0, 0, 0, 0, 7}; memcpy(rows, v, 5); return true; }
    case '/': { const uint8_t v[5] = {1, 1, 2, 4, 4}; memcpy(rows, v, 5); return true; }
    case ':': { const uint8_t v[5] = {0, 2, 0, 2, 0}; memcpy(rows, v, 5); return true; }
    case '+': { const uint8_t v[5] = {0, 2, 7, 2, 0}; memcpy(rows, v, 5); return true; }
    case '.': { const uint8_t v[5] = {0, 0, 0, 0, 2}; memcpy(rows, v, 5); return true; }
    case ' ': memset(rows, 0, 5); return true;
    default: { const uint8_t v[5] = {7, 1, 2, 0, 2}; memcpy(rows, v, 5); return false; }
    }
}

static void koala_draw_char(int x, int y, char ch, uint16_t color, int scale)
{
    uint8_t rows[5];
    (void)koala_glyph(ch, rows);
    scale = MAX(1, scale);

    for (int row = 0; row < 5; row++) {
        for (int col = 0; col < 3; col++) {
            if (rows[row] & (1U << (2 - col))) {
                koala_fill_rect(x + (col * scale), y + (row * scale),
                                scale, scale, color);
            }
        }
    }
}

static void koala_draw_text(int x, int y, const char *text, uint16_t color,
                            int scale, int max_chars)
{
    if (!text || max_chars <= 0) {
        return;
    }

    int cursor = x;
    int advance = (4 * MAX(1, scale));
    for (int i = 0; text[i] && i < max_chars; i++) {
        koala_draw_char(cursor, y, text[i], color, scale);
        cursor += advance;
        if (cursor >= KOALA_TFT_WIDTH - 2) {
            break;
        }
    }
}

static void koala_draw_panel(int x, int y, int width, int height,
                             uint16_t fill, uint16_t edge)
{
    koala_fill_rect(x, y, width, height, fill);
    koala_draw_rect(x, y, width, height, edge);
    if (width > 8 && height > 8) {
        koala_pixel(x + 2, y + 2, edge);
        koala_pixel(x + width - 3, y + 2, edge);
        koala_pixel(x + 2, y + height - 3, edge);
        koala_pixel(x + width - 3, y + height - 3, edge);
    }
}

static void koala_draw_bar(int x, int y, int width, int height, int percent,
                           uint16_t fill, uint16_t track, uint16_t edge)
{
    percent = CLAMP(percent, 0, 100);
    koala_fill_rect(x, y, width, height, track);
    koala_draw_rect(x, y, width, height, edge);
    int inner = MAX(0, width - 2);
    int active = (inner * percent) / 100;
    if (active > 0 && height > 2) {
        koala_fill_rect(x + 1, y + 1, active, height - 2, fill);
    }
}

static void koala_draw_leaf(int cx, int cy, uint16_t fill, uint16_t edge,
                            bool lean_right)
{
    for (int x = -6; x <= 6; x++) {
        int half = 3 - (ABS(x) / 3);
        half = MAX(1, half);
        int skew = lean_right ? (x / 4) : -(x / 4);
        koala_fill_rect(cx + x, cy + skew - half, 1, (half * 2) + 1, fill);
    }
    koala_draw_line(cx - 6, cy + (lean_right ? -1 : 1),
                    cx + 6, cy + (lean_right ? 1 : -1), edge);
}

static void koala_draw_eye(int cx, int cy, uint16_t iris, bool blink,
                           int pupil_offset)
{
    const uint16_t white = koala_rgb565(226, 234, 238);
    const uint16_t black = koala_rgb565(2, 4, 6);

    if (blink) {
        koala_draw_line(cx - 7, cy, cx + 7, cy, iris);
        return;
    }

    koala_fill_ellipse(cx, cy, 8, 6, white);
    koala_fill_circle(cx + pupil_offset, cy, 4, iris);
    koala_fill_circle(cx + pupil_offset, cy, 2, black);
    koala_pixel(cx + pupil_offset - 1, cy - 2, white);
}

static bool koala_contains_ci(const char *text, const char *needle)
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

static int koala_active_footer_key(const char *action_title)
{
    if (koala_contains_ci(action_title, "SCAN")) return 0;
    if (koala_contains_ci(action_title, "PET")) return 1;
    if (koala_contains_ci(action_title, "EUC")) return 2;
    if (koala_contains_ci(action_title, "BOOM")) return 3;
    if (koala_contains_ci(action_title, "LOG")) return 4;
    if (koala_contains_ci(action_title, "BACK")) return 5;
    return 2;
}

static void koala_draw_action_title(int x, int y, const char *action_title,
                                    uint16_t color)
{
    char title[18];
    const char *source = (action_title && action_title[0]) ? action_title : "EUCALYPTUS";
    int out = 0;

    for (int i = 0; source[i] && out < (int)sizeof(title) - 1; i++) {
        char ch = source[i];
        if (ch >= 'a' && ch <= 'z') {
            ch = (char)(ch - 'a' + 'A');
        }
        if ((ch >= 'A' && ch <= 'Z') || (ch >= '0' && ch <= '9')) {
            title[out++] = ch;
        } else if (ch == '-' || ch == '_' || ch == ' ') {
            if (out > 0 && title[out - 1] != ' ') {
                title[out++] = ' ';
            }
        }
    }
    title[out] = '\0';

    if (out == 0) {
        memcpy(title, "EUCALYPTUS", sizeof("EUCALYPTUS"));
    }
    koala_draw_text(x, y, title, color, 1, 17);
}

static void koala_draw_koala(int cx, int cy, uint8_t phase,
                             uint16_t purple, uint16_t green,
                             uint16_t hud_green)
{
    const uint16_t fur = koala_rgb565(157, 166, 174);
    const uint16_t fur_dark = koala_rgb565(91, 101, 111);
    const uint16_t fur_light = koala_rgb565(215, 222, 226);
    const uint16_t black = koala_rgb565(2, 4, 6);
    const uint16_t cyan = koala_rgb565(89, 219, 226);

    static const int8_t bob[8] = {0, -1, -1, 0, 0, 1, 1, 0};
    int yoff = bob[phase & 7U];
    bool blink = (phase == 5U || phase == 6U);
    int pupil = (phase < 4U) ? -1 : ((phase < 8U) ? 0 : 1);

    koala_fill_circle(cx - 23, cy - 20 + yoff, 12, fur_dark);
    koala_fill_circle(cx + 23, cy - 20 + yoff, 12, fur_dark);
    koala_fill_circle(cx - 23, cy - 20 + yoff, 7, fur_light);
    koala_fill_circle(cx + 23, cy - 20 + yoff, 7, fur_light);

    koala_fill_ellipse(cx, cy - 6 + yoff, 28, 25, fur);
    koala_fill_ellipse(cx, cy + 2 + yoff, 21, 15, fur_light);

    koala_draw_line(cx - 16, cy - 15 + yoff,
                    cx - 7, cy - 18 + yoff, black);
    koala_draw_line(cx + 7, cy - 18 + yoff,
                    cx + 16, cy - 15 + yoff, black);

    koala_draw_eye(cx - 10, cy - 7 + yoff, purple, blink, pupil);
    koala_draw_eye(cx + 10, cy - 7 + yoff, green, blink, pupil);

    koala_fill_ellipse(cx, cy + 4 + yoff, 6, 5, black);
    koala_draw_line(cx, cy + 8 + yoff, cx, cy + 12 + yoff, black);
    koala_draw_line(cx, cy + 12 + yoff, cx - 6, cy + 15 + yoff, black);
    koala_draw_line(cx, cy + 12 + yoff, cx + 6, cy + 15 + yoff, black);

    koala_fill_ellipse(cx, cy + 29 + yoff, 19, 18, fur_dark);
    koala_fill_ellipse(cx, cy + 32 + yoff, 11, 13, fur_light);
    koala_fill_circle(cx - 19, cy + 25 + yoff, 7, fur);
    koala_fill_circle(cx + 19, cy + 25 + yoff, 7, fur);

    koala_fill_rect(cx - 10, cy + 17 + yoff, 20, 7, black);
    koala_draw_rect(cx - 10, cy + 17 + yoff, 20, 7, cyan);
    koala_draw_text(cx - 4, cy + 18 + yoff, "KB", hud_green, 1, 2);
}

static void koala_draw_footer(const char *action_title, uint16_t panel,
                              uint16_t edge, uint16_t green, uint16_t yellow,
                              uint16_t white)
{
    static const char *keys[6] = {"F1", "F2", "F3", "F4", "F5", "F6"};
    static const char *labels[6] = {"S", "P", "E", "B", "L", "K"};
    int active = koala_active_footer_key(action_title);

    koala_draw_panel(5, 114, 230, 17, panel, edge);
    for (int i = 0; i < 6; i++) {
        int x = 9 + (i * 38);
        uint16_t button_fill = (i == active) ? koala_rgb565(30, 65, 36) : panel;
        uint16_t button_edge = (i == active) ? green : edge;
        koala_fill_rect(x, 117, 33, 11, button_fill);
        koala_draw_rect(x, 117, 33, 11, button_edge);
        koala_draw_text(x + 3, 120, keys[i], yellow, 1, 2);
        koala_draw_text(x + 20, 120, labels[i], white, 1, 1);
    }
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
    const uint16_t background = koala_rgb565(2, 8, 10);
    const uint16_t panel = koala_rgb565(5, 18, 23);
    const uint16_t panel_alt = koala_rgb565(7, 25, 27);
    const uint16_t green = koala_rgb565(54, 255, 118);
    const uint16_t green_dim = koala_rgb565(22, 111, 65);
    const uint16_t cyan = koala_rgb565(91, 218, 225);
    const uint16_t yellow = koala_rgb565(255, 225, 94);
    const uint16_t purple = koala_rgb565(170, 72, 255);
    const uint16_t white = koala_rgb565(222, 230, 233);
    const uint16_t black = koala_rgb565(2, 4, 6);

    uint8_t phase = frame_index & 15U;
    int pulse = (phase < 8U) ? phase : (15 - phase);

    for (size_t index = 0; index < ARRAY_SIZE(koala_framebuffer); index++) {
        koala_framebuffer[index] = background;
    }

    /* Canonical cyber-jungle HUD frame. Koalagotchi stays fixed at center;
     * only eyes, breathing, radar, leaves, and telemetry pulse. */
    koala_draw_rect(1, 1, 238, 132, green);
    koala_draw_rect(3, 3, 234, 128, green_dim);

    koala_draw_panel(6, 5, 228, 11, panel, green_dim);
    koala_draw_text(10, 8, "KILLERKOALA//KOALAGOTCHI", cyan, 1, 26);
    koala_draw_text(132, 8, "LV18", yellow, 1, 4);
    koala_draw_text(153, 8, "SAFE", green, 1, 4);
    koala_draw_rect(207, 7, 22, 7, white);
    koala_fill_rect(209, 9, 13 + (pulse / 3), 3, green);
    koala_fill_rect(229, 9, 3, 3, white);

    /* Left telemetry stack. */
    koala_draw_panel(6, 20, 52, 23, panel, green_dim);
    koala_draw_text(10, 23, "MOOD", white, 1, 4);
    koala_draw_text(10, 31, "CALM", green, 1, 4);
    koala_draw_bar(34, 31, 19, 5, 72 + pulse, green, black, green_dim);

    koala_draw_panel(6, 47, 52, 23, panel, green_dim);
    koala_draw_text(10, 50, "SIG", white, 1, 3);
    koala_draw_text(10, 58, "BLE", cyan, 1, 3);
    koala_draw_text(37, 58, "03", green, 1, 2);

    koala_draw_panel(6, 74, 52, 35, panel, green_dim);
    koala_draw_text(10, 77, "KOALA", white, 1, 5);
    koala_draw_text(10, 86, "+WATCH", green, 1, 6);
    koala_draw_text(10, 94, "+CLEAN", green, 1, 6);
    koala_draw_text(10, 102, "+XP", yellow, 1, 3);

    /* Right telemetry stack. */
    koala_draw_panel(182, 20, 52, 23, panel, green_dim);
    koala_draw_text(186, 23, "NOISE", white, 1, 5);
    koala_draw_bar(186, 32, 42, 5, 31 + (pulse * 2), green, black, green_dim);

    koala_draw_panel(182, 47, 52, 23, panel, green_dim);
    koala_draw_text(186, 50, "AURA", white, 1, 4);
    koala_draw_text(186, 59, "ON", green, 1, 2);
    koala_draw_bar(203, 59, 25, 5, 83, cyan, black, green_dim);

    koala_draw_panel(182, 74, 52, 35, panel, green_dim);
    koala_draw_text(186, 77, "BLOCK", white, 1, 5);
    koala_draw_text(216, 77, "03", green, 1, 2);
    koala_draw_text(186, 86, "XP", white, 1, 2);
    koala_draw_bar(199, 86, 29, 5, 88, yellow, black, green_dim);
    koala_draw_text(186, 96, "DEF", white, 1, 3);
    koala_draw_text(207, 96, "ON", green, 1, 2);

    /* Center mode card and radar field. */
    koala_draw_panel(64, 20, 112, 18, panel_alt, green);
    koala_draw_text(68, 23, "MODE", white, 1, 4);
    koala_draw_action_title(88, 23, action_title, green);
    koala_draw_text(68, 31, "DEFENSE AURA", cyan, 1, 12);

    int radar_radius = 28 + (pulse / 2);
    koala_draw_circle(120, 67, radar_radius, green_dim);
    koala_draw_circle(120, 67, 38, green_dim);
    koala_draw_circle(120, 67, 48, koala_rgb565(11, 64, 45));
    koala_draw_line(120, 40, 120, 96, koala_rgb565(12, 75, 49));
    koala_draw_line(75, 67, 165, 67, koala_rgb565(12, 75, 49));
    koala_draw_line(120, 67, 147 + (pulse / 2), 50 - (pulse / 3), green);
    koala_fill_circle(120, 67, 2, green);

    koala_draw_leaf(72 + (phase & 1U), 51, green, cyan, true);
    koala_draw_leaf(169 - (phase & 1U), 49, green, cyan, false);
    koala_draw_leaf(74, 87 + (phase & 1U), green_dim, green, false);
    koala_draw_leaf(167, 89 - (phase & 1U), green_dim, green, true);

    koala_draw_koala(120, 66, phase, purple, green, cyan);

    koala_draw_panel(65, 96, 110, 13, panel, green);
    koala_draw_text(69, 100, "KOALA ONLINE", white, 1, 12);
    koala_fill_rect(160, 100, 7, 5, green_dim);
    koala_fill_rect(161, 101, 3 + (pulse / 3), 3, green);

    koala_draw_footer(action_title, panel, green_dim, green, yellow, white);

    koala_flush();
}
