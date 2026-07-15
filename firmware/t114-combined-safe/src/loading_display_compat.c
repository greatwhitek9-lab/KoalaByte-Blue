/*
 * KoalaByte Blue T114 loading-display compatibility backend.
 *
 * NCS v2.9 uses an older Zephyr devicetree model than the current upstream
 * Heltec T114 board definition. The imported board exposes VEXT, TFT enable,
 * and backlight aliases in a form that cannot be consumed safely by the older
 * GPIO devicetree macros.
 *
 * Keep the public loading-display API available while the first-flash build
 * focuses on USB CDC, BLE, GNSS, and UF2 output. A native NCS v2.9 display
 * implementation can replace this file later without changing main.c.
 */

#include "loading_display.h"

bool loading_display_init(void)
{
    return false;
}

bool loading_display_ready(void)
{
    return false;
}

void render_loading_banner(const char *banner)
{
    (void)banner;
}

void loading_display_end(void)
{
}
