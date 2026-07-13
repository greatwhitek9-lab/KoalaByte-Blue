#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/init.h>

#if DT_NODE_EXISTS(DT_ALIAS(vext_control))
static const struct gpio_dt_spec early_vext_control = GPIO_DT_SPEC_GET(DT_ALIAS(vext_control), gpios);
#endif
#if DT_NODE_EXISTS(DT_ALIAS(tft_en))
static const struct gpio_dt_spec early_tft_enable = GPIO_DT_SPEC_GET(DT_ALIAS(tft_en), gpios);
#endif
#if DT_NODE_EXISTS(DT_ALIAS(tft_led_en))
static const struct gpio_dt_spec early_tft_backlight = GPIO_DT_SPEC_GET(DT_ALIAS(tft_led_en), gpios);
#endif

static int enable_pin(const struct gpio_dt_spec *spec)
{
    if (!spec || !spec->port || !device_is_ready(spec->port)) {
        return 0;
    }
    return gpio_pin_configure_dt(spec, GPIO_OUTPUT_ACTIVE);
}

static int koalabyte_t114_display_power_init(void)
{
    int rc = 0;

#if DT_NODE_EXISTS(DT_ALIAS(vext_control))
    rc = enable_pin(&early_vext_control);
    if (rc != 0) {
        return rc;
    }
#endif
#if DT_NODE_EXISTS(DT_ALIAS(tft_en))
    rc = enable_pin(&early_tft_enable);
    if (rc != 0) {
        return rc;
    }
#endif
#if DT_NODE_EXISTS(DT_ALIAS(tft_led_en))
    rc = enable_pin(&early_tft_backlight);
    if (rc != 0) {
        return rc;
    }
#endif

    return 0;
}

/* The ST7789 display driver initializes at CONFIG_DISPLAY_INIT_PRIORITY (85).
 * Run after GPIO devices are ready but before the display driver probes the panel.
 */
SYS_INIT(koalabyte_t114_display_power_init, POST_KERNEL, 70);
