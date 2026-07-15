#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/init.h>

/*
 * NCS v2.9 predates the upstream Heltec T114 v2 devicetree model.  Its GPIO
 * macros cannot safely consume the board_controls child aliases from the
 * backported board definition, even though the underlying nRF52840 GPIO pins
 * are stable.  Drive the three documented T114 v2 control pins directly so
 * display power is ready before the ST7789 driver probes the panel.
 *
 * Upstream board mapping:
 *   P0.21 VEXT control       active high
 *   P0.03 TFT enable        active low
 *   P0.15 TFT backlight     active low
 */
#define KOALABYTE_GPIO0_NODE DT_NODELABEL(gpio0)
#define KOALABYTE_VEXT_CONTROL_PIN 21
#define KOALABYTE_TFT_ENABLE_PIN 3
#define KOALABYTE_TFT_BACKLIGHT_PIN 15

static const struct device *const koalabyte_gpio0 =
    DEVICE_DT_GET(KOALABYTE_GPIO0_NODE);

static int configure_output(unsigned int pin, int physical_level)
{
    int rc;

    if (!device_is_ready(koalabyte_gpio0)) {
        return -ENODEV;
    }

    rc = gpio_pin_configure(koalabyte_gpio0, pin, GPIO_OUTPUT);
    if (rc != 0) {
        return rc;
    }

    return gpio_pin_set(koalabyte_gpio0, pin, physical_level);
}

static int koalabyte_t114_display_power_init(void)
{
    int rc;

    rc = configure_output(KOALABYTE_VEXT_CONTROL_PIN, 1);
    if (rc != 0) {
        return rc;
    }

    rc = configure_output(KOALABYTE_TFT_ENABLE_PIN, 0);
    if (rc != 0) {
        return rc;
    }

    return configure_output(KOALABYTE_TFT_BACKLIGHT_PIN, 0);
}

/*
 * The ST7789 display driver initializes at CONFIG_DISPLAY_INIT_PRIORITY (85).
 * Run after GPIO devices are ready but before the display driver probes the
 * panel.  Keep the legacy marker names for the no-hardware readiness gate:
 * vext_control, tft_enable, tft_backlight.
 */
SYS_INIT(koalabyte_t114_display_power_init, POST_KERNEL, 70);
