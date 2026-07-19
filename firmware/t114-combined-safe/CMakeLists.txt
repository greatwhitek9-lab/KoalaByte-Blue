cmake_minimum_required(VERSION 3.20.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(koalabyte_t114_combined_safe)

target_sources(app PRIVATE
  src/display_power_init.c
  src/main.c
  src/loading_display.c
)

set(KOALABYTE_BOOT_SPLASH_ASSET
  ${CMAKE_CURRENT_SOURCE_DIR}/assets/killerkoala-bootsplash-240x135.rgb565be
)
set(KOALABYTE_BOOT_SPLASH_INCLUDE
  ${ZEPHYR_BINARY_DIR}/include/generated/killerkoala_boot_splash_rgb565.inc
)
generate_inc_file_for_target(
  app
  ${KOALABYTE_BOOT_SPLASH_ASSET}
  ${KOALABYTE_BOOT_SPLASH_INCLUDE}
)

if(DEFINED KOALABYTE_GNSS_UART_LABEL)
  target_compile_definitions(app PRIVATE KOALABYTE_GNSS_UART_LABEL="${KOALABYTE_GNSS_UART_LABEL}")
endif()
