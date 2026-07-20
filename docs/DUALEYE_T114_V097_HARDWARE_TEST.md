# DualEye v0.9.7 and procedural T114 hardware test

## Architecture under test

- ESP32-S3 DualEye: local ESP-SR voice recognition, local menu display, local Australian KillerKoala responses, Wi-Fi/UDP and USB CDC to the Raspberry Pi.
- Heltec T114: USB CDC/serial to the Raspberry Pi, primary BLE controller, primary GNSS, procedural cyber-mouth, and Koalagotchi menu/action display.
- Raspberry Pi: BLE node/peer for the T114, command execution, AI, TTS, and display-state fanout.

The ESP32 Bluetooth controller remains disabled on this hardware profile.

## ESP32 v0.9.7 changes

- ES7210 analog microphone gain: 37.5 dB.
- ES7210 digital microphone gain: +22 dB.
- Complex follow-up threshold: 0.010 RMS.
- ES8311 speaker volume: 74.
- Embedded clips normalized to -12.5 LUFS with a -0.8 dB true-peak ceiling.
- Natural Australian synthesis backend remains `en-AU-WilliamNeural`.
- Spoken identity is always **KillerKoala**; no response introduces itself as William.
- Local phrases include `menu`, `open menu`, `back`, `select`, `forward`, `up`, and `down`.
- K1-K8 and generated catalog commands remain present.
- Main-menu opening and K1-K6 navigation run without the Raspberry Pi.
- Leaf actions still require the Raspberry Pi for execution.

## Heltec procedural display changes

- The existing cyber-mouth artwork remains the full-screen visual base.
- Runtime mouth movement is drawn procedurally over the muzzle region.
- Jaw opening, lip curl, asymmetry, snarl, teeth, tongue, purple/lime lighting, idle motion, and speaking cadence vary continuously.
- Menu states show animated Koalagotchi rather than a text-only menu-status screen.
- Action states show animated Koalagotchi until the state returns to the mouth.
- The six-second KillerKoala boot artwork, BLE, GNSS, USB CDC, and purple/green error alarm remain active.

## Flash order

1. Disconnect the battery from the ESP32-S3 DualEye and flash the v0.9.7 full-flash image over stable USB.
2. Press ESP32 RESET once and allow at least 15 seconds for codec and MultiNet initialization.
3. Flash the Heltec T114 UF2 by double-pressing RST and copying the verified UF2 to the `HT-n5262` drive.
4. Wait at least 15 seconds after the UF2 drive disconnects.
5. Connect the T114 to the Raspberry Pi over USB CDC/serial.
6. Start the Pi companion bridge.

## Standalone ESP32 tests

The following must work with no Raspberry Pi attached:

1. Say `Killer Koala` at normal conversational volume.
2. Confirm the spoken response identifies itself as KillerKoala and is louder without static.
3. After the wake response finishes, say `menu` or `open menu`.
4. Navigate with `down`, `up`, `forward`, `back`, and `select`.
5. Confirm both eyes retain their intended menu layout and return behavior.

The short navigation words are intentionally used as the second stage after the wake response. Complete catalog commands such as `Killer Koala launch Koala Kombat Kruisin` remain registered as one-shot phrases.

Serial diagnostics:

```json
{"type":"local_voice_status_request"}
{"type":"local_voice_test","category":"wake"}
{"type":"local_menu_test","menu_name":"main","selected_index":0}
```

## Integrated Pi and T114 tests

1. Open the menu by voice and confirm animated Koalagotchi appears on the T114.
2. Navigate the ESP32 menu and confirm menu state continues to reach the T114 over Pi USB fanout.
3. Say `Killer Koala launch Koala Kombat Kruisin` and confirm the correct submenu or action route.
4. Select a leaf action and confirm the T114 shows animated Koalagotchi for the complete running interval.
5. Confirm Pi speech drives the procedural mouth continuously and that it settles after speech ends.
6. Trigger a controlled error and confirm the purple/green alarm remains active on both displays.
7. Confirm T114 BLE and GNSS status continue over USB CDC.

## Build validation

The release gate requires:

- ESP32 PlatformIO build, packaging, and artifact upload success.
- Repository CI success for ESP32, Pi dependencies, installer checks, and menu tests.
- T114 NCS/Zephyr build success.
- T114 partition, controller, display, UF2 family, and reset-vector validation success.
- SHA-256 verification of both distributed packages.
