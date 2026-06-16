# KoalaByte Blue Firmware Themes

This folder is the firmware-side theme drop zone for KoalaByte Blue.

Theme packages can include:

```text
splash / boot image references
background image references
menu item styling
font family preference
textbox color
accent colors
```

## Active theme

The primary active firmware theme is:

```text
jungle_jumanji_eucalyptus
```

It uses a jungle/Jumanji-style visual direction with eucalyptus branch borders, bark/gold title coloring, blue KoalaByte Blue accent text, and the left-purple/right-green glowing-eye identity.

The active compile-time firmware colors live in:

```text
firmware/esp32-dualeye/themes/active_theme.h
```

The ESP32 boot animation reads that header at compile time.

## Standard editable theme

The standard editable theme lives in:

```text
firmware/esp32-dualeye/themes/standard/theme.json
```

Users can change:

```text
background
font_family
textbox_color
text_color
accent_color
selected_item_color
```

For firmware builds, keep font files out of the repository unless you own the license. Use system/fallback font names or convert a licensed font to a firmware-safe bitmap/font asset in a separate private build process.

## Jungle font note

The requested KoalaByte Blue poster lettering is approximated in firmware with heavy multi-pass built-in text rendering and in SVG with common fallback families:

```text
Impact, Copperplate, Rockwell Extra Bold, Arial Black, serif
```

No third-party font file is bundled in this repository.

## Custom upload structure

A custom theme should use this layout:

```text
themes/<theme_id>/
  theme.json
  boot_splash.svg
  background.svg
  menu_preview.svg
  README.md
```

Use `active_theme.h` to select compile-time ESP32 color constants. Use `theme.json` for Pi-side or future UI loaders that support runtime theme selection.
