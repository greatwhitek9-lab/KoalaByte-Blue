#include "loading_display.h"

#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/display.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/byteorder.h>
#include <zephyr/sys/util.h>

#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#define TFT_WIDTH 240
#define TFT_HEIGHT 135
#define GLYPH_WIDTH 4
#define GLYPH_HEIGHT 7
#define GLYPH_SCALE 2
#define GLYPH_CELL_WIDTH 10
#define KILLERKOALA_MOUTH_TEXT_FREE 1
#define KILLERKOALA_CYBER_MOUTH_FRAME_BYTES 64800

#define DISPLAY_NODE DT_CHOSEN(zephyr_display)

static const struct device *const display_dev = DEVICE_DT_GET(DISPLAY_NODE);

/*
 * Use the stable T114 v2 GPIO numbers instead of board_controls aliases.
 * This keeps the native ST7789 renderer usable with the NCS v2.9 board
 * backport while display_power_init.c asserts the same pins before probe.
 */
#define KOALABYTE_GPIO0_NODE DT_NODELABEL(gpio0)
#define KOALABYTE_VEXT_CONTROL_PIN 21
#define KOALABYTE_TFT_ENABLE_PIN 3
#define KOALABYTE_TFT_BACKLIGHT_PIN 15

static const struct device *const koalabyte_gpio0 =
    DEVICE_DT_GET(KOALABYTE_GPIO0_NODE);

static uint16_t framebuffer[TFT_WIDTH * TFT_HEIGHT];
static const uint8_t killerkoala_boot_splash_rgb565_be[] = {
#include "killerkoala_boot_splash_rgb565.inc"
};
BUILD_ASSERT(sizeof(killerkoala_boot_splash_rgb565_be) == sizeof(framebuffer),
             "KillerKoala boot splash must be exactly 240x135 RGB565");
static const uint8_t killerkoala_cyber_mouth_smile_rgb565_be[] = {
#include "killerkoala_cyber_mouth_smile_rgb565.inc"
};
static const uint8_t killerkoala_cyber_mouth_happy_rgb565_be[] = {
#include "killerkoala_cyber_mouth_happy_rgb565.inc"
};
static const uint8_t killerkoala_cyber_mouth_bite_rgb565_be[] = {
#include "killerkoala_cyber_mouth_bite_rgb565.inc"
};
static const uint8_t killerkoala_cyber_mouth_snarl_rgb565_be[] = {
#include "killerkoala_cyber_mouth_snarl_rgb565.inc"
};
static const uint8_t killerkoala_cyber_mouth_sideways_grin_rgb565_be[] = {
#include "killerkoala_cyber_mouth_sideways_grin_rgb565.inc"
};
#define ASSERT_MOUTH_FRAME(name)                                                \
    BUILD_ASSERT(sizeof(name) == KILLERKOALA_CYBER_MOUTH_FRAME_BYTES,          \
                 "KillerKoala cyber mouth frame must be exactly 240x135 RGB565")
ASSERT_MOUTH_FRAME(killerkoala_cyber_mouth_smile_rgb565_be);
ASSERT_MOUTH_FRAME(killerkoala_cyber_mouth_happy_rgb565_be);
ASSERT_MOUTH_FRAME(killerkoala_cyber_mouth_bite_rgb565_be);
ASSERT_MOUTH_FRAME(killerkoala_cyber_mouth_snarl_rgb565_be);
ASSERT_MOUTH_FRAME(killerkoala_cyber_mouth_sideways_grin_rgb565_be);
static bool display_ready_flag;

static uint16_t rgb565(uint8_t red, uint8_t green, uint8_t blue)
{
    uint16_t value = (uint16_t)(((red & 0xf8U) << 8) | ((green & 0xfcU) << 3) | (blue >> 3));
    return sys_cpu_to_be16(value);
}

static void set_pixel(int x, int y, uint16_t color)
{
    if (x < 0 || y < 0 || x >= TFT_WIDTH || y >= TFT_HEIGHT) {
        return;
    }
    framebuffer[(y * TFT_WIDTH) + x] = color;
}

static void fill_rect(int x, int y, int width, int height, uint16_t color)
{
    int x_end = MIN(x + width, TFT_WIDTH);
    int y_end = MIN(y + height, TFT_HEIGHT);
    int x_start = MAX(x, 0);
    int y_start = MAX(y, 0);

    for (int row = y_start; row < y_end; row++) {
        for (int col = x_start; col < x_end; col++) {
            set_pixel(col, row, color);
        }
    }
}

static void fill_circle(int center_x, int center_y, int radius,
                        uint16_t color)
{
    int radius_squared = radius * radius;

    for (int y = -radius; y <= radius; y++) {
        for (int x = -radius; x <= radius; x++) {
            if ((x * x) + (y * y) <= radius_squared) {
                set_pixel(center_x + x, center_y + y, color);
            }
        }
    }
}

static void draw_leaf(int center_x, int center_y, uint16_t color)
{
    set_pixel(center_x, center_y - 2, color);
    set_pixel(center_x - 1, center_y - 1, color);
    set_pixel(center_x, center_y - 1, color);
    set_pixel(center_x + 1, center_y - 1, color);
    set_pixel(center_x - 2, center_y, color);
    set_pixel(center_x - 1, center_y, color);
    set_pixel(center_x, center_y, color);
    set_pixel(center_x + 1, center_y, color);
    set_pixel(center_x + 2, center_y, color);
    set_pixel(center_x - 1, center_y + 1, color);
    set_pixel(center_x, center_y + 1, color);
    set_pixel(center_x + 1, center_y + 1, color);
    set_pixel(center_x, center_y + 2, color);
}

static uint32_t glyph_pattern(char ch)
{
    if (ch >= 'a' && ch <= 'z') {
        ch = (char)(ch - ('a' - 'A'));
    }

    switch (ch) {
    case 'A': return 0x699f999U;
    case 'B': return 0xe99e99eU;
    case 'C': return 0x7888887U;
    case 'D': return 0xe99999eU;
    case 'E': return 0xf88e88fU;
    case 'F': return 0xf88e888U;
    case 'G': return 0x788b997U;
    case 'H': return 0x999f999U;
    case 'I': return 0xf22222fU;
    case 'J': return 0x1111996U;
    case 'K': return 0x9ac8ca9U;
    case 'L': return 0x888888fU;
    case 'M': return 0x9ff9999U;
    case 'N': return 0x9ddbb99U;
    case 'O': return 0x6999996U;
    case 'P': return 0xe99e888U;
    case 'Q': return 0x6999ba5U;
    case 'R': return 0xe99ea99U;
    case 'S': return 0x788611eU;
    case 'T': return 0xf222222U;
    case 'U': return 0x9999996U;
    case 'V': return 0x9999962U;
    case 'W': return 0x9999ff9U;
    case 'X': return 0x9962699U;
    case 'Y': return 0x9962222U;
    case 'Z': return 0xf12488fU;
    case '0': return 0x6999996U;
    case '1': return 0x2622227U;
    case '2': return 0x691248fU;
    case '3': return 0xe11611eU;
    case '4': return 0x99f1111U;
    case '5': return 0xf88e11eU;
    case '6': return 0x688e996U;
    case '7': return 0xf124444U;
    case '8': return 0x6996996U;
    case '9': return 0x6997116U;
    case '<': return 0x1248421U;
    case '>': return 0x8421248U;
    case '/': return 0x1122488U;
    case '-': return 0x000f000U;
    case ':': return 0x0200020U;
    case '.': return 0x0000002U;
    case '_': return 0x000000fU;
    case ' ': return 0U;
    default: return 0xe112002U;
    }
}

static uint8_t glyph_row(char ch, int row)
{
    uint32_t pattern = glyph_pattern(ch);
    return (uint8_t)((pattern >> ((GLYPH_HEIGHT - 1 - row) * 4)) & 0x0fU);
}
static void draw_glyph(char ch, int x, int y, uint16_t color)
{
    for (int row = 0; row < GLYPH_HEIGHT; row++) {
        uint8_t bits = glyph_row(ch, row);
        for (int col = 0; col < GLYPH_WIDTH; col++) {
            if ((bits & (1U << (GLYPH_WIDTH - 1 - col))) == 0U) {
                continue;
            }
            fill_rect(
                x + (col * GLYPH_SCALE),
                y + (row * GLYPH_SCALE),
                GLYPH_SCALE,
                GLYPH_SCALE,
                color
            );
        }
    }
}

static void draw_centered_text_at(const char *text, int y, uint16_t color)
{
    size_t length = text ? strlen(text) : 0U;
    if (length == 0U) {
        return;
    }
    if (length > 23U) {
        length = 23U;
    }
    int text_width = ((int)length * GLYPH_CELL_WIDTH) - 2;
    int x = MAX((TFT_WIDTH - text_width) / 2, 1);

    for (size_t index = 0; index < length; index++) {
        draw_glyph(text[index], x + ((int)index * GLYPH_CELL_WIDTH), y, color);
    }
}

static void draw_centered_banner(const char *banner, uint16_t color)
{
    int y = (TFT_HEIGHT - (GLYPH_HEIGHT * GLYPH_SCALE)) / 2;
    draw_centered_text_at(banner, y, color);
}

static int loading_letter_count(const char *banner)
{
    int count = 0;
    if (!banner) {
        return 0;
    }
    for (const char *cursor = banner; *cursor != '\0'; cursor++) {
        if (*cursor >= 'A' && *cursor <= 'Z') {
            count++;
        }
    }
    return MIN(count, 7);
}

static void draw_jungle_frame(const char *banner)
{
    const uint16_t background = rgb565(2, 18, 8);
    const uint16_t deep_green = rgb565(8, 72, 30);
    const uint16_t leaf_green = rgb565(44, 235, 92);
    const uint16_t gold = rgb565(245, 188, 48);
    const uint16_t shadow = rgb565(76, 42, 7);

    for (size_t index = 0; index < ARRAY_SIZE(framebuffer); index++) {
        framebuffer[index] = background;
    }

    fill_rect(0, 0, TFT_WIDTH, 3, gold);
    fill_rect(0, TFT_HEIGHT - 3, TFT_WIDTH, 3, gold);
    fill_rect(0, 0, 3, TFT_HEIGHT, gold);
    fill_rect(TFT_WIDTH - 3, 0, 3, TFT_HEIGHT, gold);

    fill_rect(5, 5, TFT_WIDTH - 10, 2, deep_green);
    fill_rect(5, TFT_HEIGHT - 7, TFT_WIDTH - 10, 2, deep_green);
    fill_rect(5, 5, 2, TFT_HEIGHT - 10, deep_green);
    fill_rect(TFT_WIDTH - 7, 5, 2, TFT_HEIGHT - 10, deep_green);

    for (int y = 18; y < TFT_HEIGHT - 18; y += 28) {
        draw_leaf(7, y, leaf_green);
        draw_leaf(TFT_WIDTH - 8, y + 12, leaf_green);
    }
    for (int x = 18; x < TFT_WIDTH - 18; x += 24) {
        draw_leaf(x, 8, deep_green);
        draw_leaf(x + 10, TFT_HEIGHT - 9, leaf_green);
    }

    fill_rect(8, 44, TFT_WIDTH - 16, 2, shadow);
    fill_rect(8, 87, TFT_WIDTH - 16, 2, shadow);
    draw_centered_banner(banner, gold);

    int active = loading_letter_count(banner);
    int start_x = (TFT_WIDTH - 61) / 2;
    for (int index = 0; index < 7; index++) {
        uint16_t dot = index < active ? gold : deep_green;
        fill_rect(start_x + (index * 9), 103, 5, 5, dot);
        if (index < active) {
            set_pixel(start_x + (index * 9) + 2, 102, leaf_green);
        }
    }
}

static void draw_killerkoala_mouth_frame(const char *state,
                                           const char *message,
                                           uint8_t frame_index)
{
    const uint8_t *frame = killerkoala_cyber_mouth_smile_rgb565_be;

    ARG_UNUSED(state);
    ARG_UNUSED(message);

    switch (frame_index) {
    case 1:
        frame = killerkoala_cyber_mouth_happy_rgb565_be;
        break;
    case 2:
        frame = killerkoala_cyber_mouth_bite_rgb565_be;
        break;
    case 3:
        frame = killerkoala_cyber_mouth_snarl_rgb565_be;
        break;
    case 4:
        frame = killerkoala_cyber_mouth_sideways_grin_rgb565_be;
        break;
    default:
        break;
    }

    /* Every expression is a text-free frame with pose-specific neon shadows. */
    memcpy(framebuffer, frame, sizeof(framebuffer));
}

static void draw_koalagotchi_action_frame(uint8_t frame_index)
{
    const uint16_t background = rgb565(2, 14, 8);
    const uint16_t deep_green = rgb565(8, 72, 30);
    const uint16_t leaf_green = rgb565(44, 235, 92);
    const uint16_t gold = rgb565(245, 188, 48);
    const uint16_t fur = rgb565(48, 55, 58);
    const uint16_t fur_light = rgb565(92, 105, 108);
    const uint16_t nose = rgb565(8, 10, 12);
    const uint16_t left_eye = rgb565(202, 82, 255);
    const uint16_t right_eye = rgb565(155, 255, 62);
    int phase = frame_index % 8U;
    int travel = phase <= 4 ? phase : 8 - phase;
    int koala_x = 58 + (travel * 30);
    int koala_y = 65 + ((phase & 1) ? 2 : 0);

    for (size_t index = 0; index < ARRAY_SIZE(framebuffer); index++) {
        framebuffer[index] = background;
    }

    fill_rect(0, 0, TFT_WIDTH, 3, gold);
    fill_rect(0, TFT_HEIGHT - 3, TFT_WIDTH, 3, gold);
    fill_rect(0, 0, 3, TFT_HEIGHT, gold);
    fill_rect(TFT_WIDTH - 3, 0, 3, TFT_HEIGHT, gold);
    draw_centered_text_at("KOALAGOTCHI", 7, gold);

    fill_rect(18, 99, TFT_WIDTH - 36, 6, rgb565(92, 52, 18));
    fill_rect(18, 99, TFT_WIDTH - 36, 2, gold);
    for (int x = 26; x < TFT_WIDTH - 24; x += 34) {
        draw_leaf(x, 96 + ((x / 34) & 1), leaf_green);
    }

    fill_circle(koala_x, koala_y + 22, 20, fur);
    fill_circle(koala_x - 20, koala_y - 13, 13, fur);
    fill_circle(koala_x + 20, koala_y - 13, 13, fur);
    fill_circle(koala_x - 20, koala_y - 13, 7, fur_light);
    fill_circle(koala_x + 20, koala_y - 13, 7, fur_light);
    fill_circle(koala_x, koala_y, 25, fur);

    if (phase == 3 || phase == 7) {
        fill_rect(koala_x - 13, koala_y - 7, 9, 2, left_eye);
        fill_rect(koala_x + 4, koala_y - 7, 9, 2, right_eye);
    } else {
        fill_circle(koala_x - 9, koala_y - 7, 4, left_eye);
        fill_circle(koala_x + 9, koala_y - 7, 4, right_eye);
        set_pixel(koala_x - 8, koala_y - 8, rgb565(255, 255, 255));
        set_pixel(koala_x + 10, koala_y - 8, rgb565(255, 255, 255));
    }

    fill_circle(koala_x, koala_y + 3, 6, nose);
    fill_rect(koala_x - 1, koala_y + 8, 2, 5, nose);
    fill_rect(koala_x - 8, koala_y + 13, 7, 2, gold);
    fill_rect(koala_x + 1, koala_y + 13, 7, 2, gold);

    /* The orbiting boomerang makes each received action frame visibly move. */
    int boomerang_x = 202 - (travel * 5);
    int boomerang_y = 42 + ((phase & 1) ? 8 : 0);
    fill_rect(boomerang_x - 8, boomerang_y, 10, 3, gold);
    fill_rect(boomerang_x, boomerang_y, 3, 10, gold);
    fill_rect(boomerang_x + 2, boomerang_y + 7, 8, 3, gold);

    draw_centered_text_at("PLAYING", 115, leaf_green);
}

static bool configure_board_outputs(void)
{
    if (!device_is_ready(koalabyte_gpio0)) {
        return false;
    }

    if (gpio_pin_configure(koalabyte_gpio0, KOALABYTE_VEXT_CONTROL_PIN,
                           GPIO_OUTPUT) != 0 ||
        gpio_pin_set(koalabyte_gpio0, KOALABYTE_VEXT_CONTROL_PIN, 1) != 0 ||
        gpio_pin_configure(koalabyte_gpio0, KOALABYTE_TFT_ENABLE_PIN,
                           GPIO_OUTPUT) != 0 ||
        gpio_pin_set(koalabyte_gpio0, KOALABYTE_TFT_ENABLE_PIN, 0) != 0 ||
        gpio_pin_configure(koalabyte_gpio0, KOALABYTE_TFT_BACKLIGHT_PIN,
                           GPIO_OUTPUT) != 0 ||
        gpio_pin_set(koalabyte_gpio0, KOALABYTE_TFT_BACKLIGHT_PIN, 0) != 0) {
        return false;
    }

    return true;
}

static void flush_frame(void)
{
    if (!display_ready_flag) {
        return;
    }

    /*
     * The ST7789 MADCTL setting owns the right-hand 90-degree rotation.
     * The renderer therefore writes a native 240x135 landscape frame.
     */
    const struct display_buffer_descriptor descriptor = {
        .buf_size = sizeof(framebuffer),
        .width = TFT_WIDTH,
        .height = TFT_HEIGHT,
        .pitch = TFT_WIDTH,
    };

    (void)display_write(display_dev, 0, 0, &descriptor, framebuffer);
}

void render_killerkoala_boot_splash(void)
{
    if (!display_ready_flag) {
        return;
    }

    memcpy(framebuffer, killerkoala_boot_splash_rgb565_be,
           sizeof(framebuffer));
    flush_frame();
}

void render_koalagotchi_action(const char *action_title, uint8_t frame_index)
{
    ARG_UNUSED(action_title);
    if (!display_ready_flag) {
        return;
    }

    draw_koalagotchi_action_frame(frame_index);
    flush_frame();
}

bool loading_display_init(void)
{
    if (!configure_board_outputs()) {
        display_ready_flag = false;
        return false;
    }

    k_sleep(K_MSEC(40));
    if (!device_is_ready(display_dev)) {
        display_ready_flag = false;
        return false;
    }
    if (display_set_pixel_format(display_dev, PIXEL_FORMAT_RGB_565) != 0) {
        display_ready_flag = false;
        return false;
    }
    int rc = display_blanking_off(display_dev);
    if (rc != 0 && rc != -ENOSYS) {
        display_ready_flag = false;
        return false;
    }

    display_ready_flag = true;
    render_killerkoala_boot_splash();
    return true;
}

bool loading_display_ready(void)
{
    return display_ready_flag;
}

void render_loading_banner(const char *banner)
{
    if (!display_ready_flag || !banner || banner[0] == '\0') {
        return;
    }
    draw_jungle_frame(banner);
    flush_frame();
}

void render_killerkoala_mouth(const char *state, const char *message,
                              uint8_t frame_index)
{
    if (!display_ready_flag) {
        return;
    }
    draw_killerkoala_mouth_frame(state, message, frame_index);
    flush_frame();
}

void render_menu_status(const char *message)
{
    if (!display_ready_flag) {
        return;
    }
    draw_jungle_frame(message && message[0] ? message : "MENU");
    flush_frame();
}

void loading_display_end(void)
{
    render_killerkoala_mouth("idle", "KILLERKOALA", 0);
}
