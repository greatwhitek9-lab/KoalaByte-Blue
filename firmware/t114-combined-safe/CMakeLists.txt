cmake_minimum_required(VERSION 3.20.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(koalabyte_t114_combined_safe)

target_sources(app PRIVATE
  src/display_power_init.c
  src/error_alarm_wrapper.c
  src/koalagotchi_lifecycle_wrapper.c
  src/main.c
  src/loading_display.c
)

# Preserve the existing procedural cyber-mouth implementation as the inner
# renderer. The lifecycle wrapper becomes the public linker --wrap target and
# controls persistent action, Koalagotchi mode, failure emotion, and alarm state.
set_source_files_properties(src/error_alarm_wrapper.c PROPERTIES
  COMPILE_DEFINITIONS
    "__wrap_render_killerkoala_mouth=koala_inner_render_killerkoala_mouth;__wrap_render_menu_status=koala_inner_render_menu_status;__wrap_render_koalagotchi_action=koala_inner_render_koalagotchi_action"
)

target_link_options(app PRIVATE
  -Wl,--wrap=render_killerkoala_mouth
  -Wl,--wrap=render_menu_status
  -Wl,--wrap=render_koalagotchi_action
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

foreach(KOALABYTE_MOUTH_EXPRESSION IN ITEMS
    smile
    happy
    bite
    snarl
    sideways_grin
)
  string(REPLACE "_" "-" KOALABYTE_MOUTH_ASSET_NAME
    ${KOALABYTE_MOUTH_EXPRESSION}
  )
  if(KOALABYTE_MOUTH_EXPRESSION STREQUAL "smile")
    set(KOALABYTE_MOUTH_SHA256 4ac8487889927f12245b7aab18bcbae67a136d435bedfbc12d64b6438b325c0b)
  elseif(KOALABYTE_MOUTH_EXPRESSION STREQUAL "happy")
    set(KOALABYTE_MOUTH_SHA256 16753b3a5ae15a9946c7a519203d181ac4c1d21a121f7de6699497bbc96c4f00)
  elseif(KOALABYTE_MOUTH_EXPRESSION STREQUAL "bite")
    set(KOALABYTE_MOUTH_SHA256 7473bc86850497c03067fce47f3bd2bdf6166ca0ac1cbc14f19dc579adac93cd)
  elseif(KOALABYTE_MOUTH_EXPRESSION STREQUAL "snarl")
    set(KOALABYTE_MOUTH_SHA256 265f944b10b4cab58ee0d84b5e67fbec805a2cd7774829641697a3077f058ed0)
  elseif(KOALABYTE_MOUTH_EXPRESSION STREQUAL "sideways_grin")
    set(KOALABYTE_MOUTH_SHA256 2698c29d589abe9b3582be48f630da71ce0c3051d7656d7f4ba57556fd435e49)
  endif()
  set(KOALABYTE_MOUTH_ASSET_PREFIX
    ${CMAKE_CURRENT_SOURCE_DIR}/assets/killerkoala-cyber-mouth-${KOALABYTE_MOUTH_ASSET_NAME}-240x135.rgb565be.b64
  )
  set(KOALABYTE_MOUTH_DECODED
    ${ZEPHYR_BINARY_DIR}/generated/killerkoala-cyber-mouth-${KOALABYTE_MOUTH_ASSET_NAME}-240x135.rgb565be
  )
  set(KOALABYTE_MOUTH_INCLUDE
    ${ZEPHYR_BINARY_DIR}/include/generated/killerkoala_cyber_mouth_${KOALABYTE_MOUTH_EXPRESSION}_rgb565.inc
  )
  execute_process(
    COMMAND
      ${PYTHON_EXECUTABLE}
      ${CMAKE_CURRENT_SOURCE_DIR}/scripts/decode_base64_asset.py
      --expected-bytes 64800
      --expected-sha256 ${KOALABYTE_MOUTH_SHA256}
      --output ${KOALABYTE_MOUTH_DECODED}
      ${KOALABYTE_MOUTH_ASSET_PREFIX}.part0
      ${KOALABYTE_MOUTH_ASSET_PREFIX}.part1
    RESULT_VARIABLE KOALABYTE_MOUTH_DECODE_RESULT
    ERROR_VARIABLE KOALABYTE_MOUTH_DECODE_ERROR
  )
  if(NOT KOALABYTE_MOUTH_DECODE_RESULT EQUAL 0)
    message(FATAL_ERROR
      "Failed to decode ${KOALABYTE_MOUTH_EXPRESSION} mouth asset: ${KOALABYTE_MOUTH_DECODE_ERROR}"
    )
  endif()
  generate_inc_file_for_target(
    app
    ${KOALABYTE_MOUTH_DECODED}
    ${KOALABYTE_MOUTH_INCLUDE}
  )
endforeach()

if(DEFINED KOALABYTE_GNSS_UART_LABEL)
  target_compile_definitions(app PRIVATE KOALABYTE_GNSS_UART_LABEL="${KOALABYTE_GNSS_UART_LABEL}")
endif()
