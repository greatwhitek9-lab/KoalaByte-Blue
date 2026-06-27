cmake_minimum_required(VERSION 3.20.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(koalabyte_t114_combined_safe)

target_sources(app PRIVATE src/main.c)

if(DEFINED KOALABYTE_GNSS_UART_LABEL)
  target_compile_definitions(app PRIVATE KOALABYTE_GNSS_UART_LABEL="${KOALABYTE_GNSS_UART_LABEL}")
endif()
