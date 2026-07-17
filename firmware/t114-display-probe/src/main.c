#include "loading_display.h"

#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>
#include <zephyr/usb/usb_device.h>

#include <errno.h>
#include <stdbool.h>
#include <stdint.h>

#define LED0_NODE DT_ALIAS(led0)

#if !DT_NODE_HAS_STATUS(LED0_NODE, okay)
#error "Heltec T114 display probe requires the led0 alias"
#endif

static const struct gpio_dt_spec status_led =
    GPIO_DT_SPEC_GET(LED0_NODE, gpios);

int main(void)
{
    int led_rc;
    int usb_rc;
    bool display_ready;
    bool led_on = false;
    uint32_t heartbeat = 0;

    led_rc = gpio_is_ready_dt(&status_led)
                 ? gpio_pin_configure_dt(&status_led, GPIO_OUTPUT_INACTIVE)
                 : -ENODEV;

    usb_rc = usb_enable(NULL);
    k_sleep(K_MSEC(1200));

    display_ready = loading_display_init();

    printk("{\"type\":\"t114_display_probe\",\"stage\":\"started\","
           "\"profile\":\"usb_led_st7789_only\","
           "\"display\":true,\"bluetooth\":false,"
           "\"gnss\":false,\"lora\":false,"
           "\"led_rc\":%d,\"usb_rc\":%d,"
           "\"display_ready\":%s}\n",
           led_rc, usb_rc, display_ready ? "true" : "false");

    while (true) {
        if (led_rc == 0) {
            led_on = !led_on;
            (void)gpio_pin_set_dt(&status_led, led_on ? 1 : 0);
        }

        printk("{\"type\":\"t114_display_probe\","
               "\"stage\":\"heartbeat\",\"count\":%u,"
               "\"uptime_ms\":%lld,\"display_ready\":%s}\n",
               heartbeat++, (long long)k_uptime_get(),
               loading_display_ready() ? "true" : "false");

        k_sleep(K_SECONDS(1));
    }

    return 0;
}
