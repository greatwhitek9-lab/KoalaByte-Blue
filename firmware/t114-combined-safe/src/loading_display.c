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

static uint8_t glyph_row(char ch, int row)
{
    static const uint8_t glyph_l[GLYPH_HEIGHT] = {0x8, 0x8, 0x8, 0x8, 0x8, 0x8, 0xf};
    static const uint8_t glyph_o[GLYPH_HEIGHT] = {0x6, 0x9, 0x9, 0x9, 0x9, 0x9, 0x6};
    static const uint8_t glyph_a[GLYPH_HEIGHT] = {0x6, 0x9, 0x9, 0xf, 0x9, 0x9, 0x9};
    static const uint8_t glyph_d[GLYPH_HEIGHT] = {0xe, 0x9, 0x9, 0x9, 0x9, 0x9, 0xe};
    static const uint8_t glyph_i[GLYPH_HEIGHT] = {0xf, 0x2, 0x2, 0x2, 0x2, 0x2, 0xf};
    static const uint8_t glyph_n[GLYPH_HEIGHT] = {0x9, 0xd, 0xd, 0xb, 0xb, 0x9, 0x9};
    static const uint8_t glyph_g[GLYPH_HEIGHT] = {0x6, 0x9, 0x8, 0xb, 0x9, 0x9, 0x7};
    static const uint8_t glyph_lt[GLYPH_HEIGHT] = {0x1, 0x2, 0x4, 0x8, 0x4, 0x2, 0x1};
    static const uint8_t glyph_gt[GLYPH_HEIGHT] = {0x8, 0x4, 0x2, 0x1, 0x2, 0x4, 0x8};
    const uint8_t *glyph = NULL;

    switch (ch) {
    case 'L': glyph = glyph_l; break;
    case 'O': glyph = glyph_o; break;
    case 'A': glyph = glyph_a; break;
    case 'D': glyph = glyph_d; break;
    case 'I': glyph = glyph_i; break;
    case 'N': glyph = glyph_n; break;
    case 'G': glyph = glyph_g; break;
    case '<': glyph = glyph_lt; break;
    case '>': glyph = glyph_gt; break;
    case ' ': return 0;
    default: return 0;
    }
    return glyph[row];
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

static void draw_centered_banner(const char *banner, uint16_t color)
{
    size_t length = banner ? strlen(banner) : 0U;
    if (length == 0U) {
        return;
    }
    if (length > 13U) {
        length = 13U;
    }
    int text_width = ((int)length * GLYPH_CELL_WIDTH) - 2;
    int x = MAX((TFT_WIDTH - text_width) / 2, 1);
    int y = (TFT_HEIGHT - (GLYPH_HEIGHT * GLYPH_SCALE)) / 2;

    for (size_t index = 0; index < length; index++) {
        draw_glyph(banner[index], x + ((int)index * GLYPH_CELL_WIDTH), y, color);
    }
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

    const int banner_y =
        (TFT_HEIGHT - (GLYPH_HEIGHT * GLYPH_SCALE)) / 2;
    const int banner_bottom =
        banner_y + (GLYPH_HEIGHT * GLYPH_SCALE);
    const int dot_y = MIN(banner_bottom + 15, TFT_HEIGHT - 10);

    fill_rect(12, MAX(banner_y - 10, 9), TFT_WIDTH - 24, 2, shadow);
    fill_rect(12, MIN(banner_bottom + 7, TFT_HEIGHT - 9),
              TFT_WIDTH - 24, 2, shadow);
    draw_centered_banner(banner, gold);

    int active = loading_letter_count(banner);
    int start_x = (TFT_WIDTH - 61) / 2;
    for (int index = 0; index < 7; index++) {
        uint16_t dot = index < active ? gold : deep_green;
        fill_rect(start_x + (index * 9), dot_y, 5, 5, dot);
        if (index < active) {
            set_pixel(start_x + (index * 9) + 2, dot_y - 1, leaf_green);
        }
    }
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
    const struct display_buffer_descriptor descriptor = {
        .buf_size = sizeof(framebuffer),
        .width = TFT_WIDTH,
        .height = TFT_HEIGHT,
        .pitch = TFT_WIDTH,
    };
    (void)display_write(display_dev, 0, 0, &descriptor, framebuffer);
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
    render_loading_banner("LOADING");
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

void loading_display_end(void)
{
    if (!display_ready_flag) {
        return;
    }
    const uint16_t background = rgb565(2, 18, 8);
    for (size_t index = 0; index < ARRAY_SIZE(framebuffer); index++) {
        framebuffer[index] = background;
    }
    flush_frame();
}
