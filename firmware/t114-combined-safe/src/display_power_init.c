#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/init.h>

/*
 * The current Heltec T114 board definition exposes VEXT, TFT power, and TFT
 * backlight through aliases whose child nodes do not carry an explicit status.
 * When an application overlay disables the board_controls parent for an older
 * Zephyr/NCS compatibility build, each child still individually defaults to
 * status = "okay". Checking only the child therefore still expands invalid
 * GPIO_DT_SPEC_GET() macros.
 *
 * Gate each specification on both the child and its parent. This keeps normal
 * display-power initialization on native board definitions, while completely
 * compiling it out when the compatibility overlay disables board_controls.
 */
#define KOALABYTE_CONTROL_NODE_USABLE(node_id) \
    (DT_NODE_HAS_STATUS(node_id, okay) && \
     DT_NODE_HAS_STATUS(DT_PARENT(node_id), okay))

#if KOALABYTE_CONTROL_NODE_USABLE(DT_ALIAS(vext_control))
#define KOALABYTE_HAS_VEXT_CONTROL 1
static const struct gpio_dt_spec early_vext_control =
    GPIO_DT_SPEC_GET(DT_ALIAS(vext_control), gpios);
#else
#define KOALABYTE_HAS_VEXT_CONTROL 0
#endif

#if KOALABYTE_CONTROL_NODE_USABLE(DT_ALIAS(tft_en))
#define KOALABYTE_HAS_TFT_ENABLE 1
static const struct gpio_dt_spec early_tft_enable =
    GPIO_DT_SPEC_GET(DT_ALIAS(tft_en), gpios);
#else
#define KOALABYTE_HAS_TFT_ENABLE 0
#endif

#if KOALABYTE_CONTROL_NODE_USABLE(DT_ALIAS(tft_led_en))
#define KOALABYTE_HAS_TFT_BACKLIGHT 1
static const struct gpio_dt_spec early_tft_backlight =
    GPIO_DT_SPEC_GET(DT_ALIAS(tft_led_en), gpios);
#else
#define KOALABYTE_HAS_TFT_BACKLIGHT 0
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

#if KOALABYTE_HAS_VEXT_CONTROL
    rc = enable_pin(&early_vext_control);
    if (rc != 0) {
        return rc;
    }
#endif
#if KOALABYTE_HAS_TFT_ENABLE
    rc = enable_pin(&early_tft_enable);
    if (rc != 0) {
        return rc;
    }
#endif
#if KOALABYTE_HAS_TFT_BACKLIGHT
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
