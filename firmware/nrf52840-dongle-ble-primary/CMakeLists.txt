cmake_minimum_required(VERSION 3.20.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(koalabyte_blue_nrf52840_dongle_ble_primary)

target_sources(app PRIVATE src/main.c)
