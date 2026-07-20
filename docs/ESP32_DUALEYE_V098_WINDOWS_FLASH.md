# ESP32-S3 DualEye v0.9.8 Windows flash

Target: Waveshare ESP32-S3 DualEye 1.28-inch non-touch board with both GC9A01A displays.

Use the GitHub Actions artifact named:

`koalabyte-esp32-s3-dualeye-v0.9.8-killerkoala-wake-session`

The ZIP contains the combined full-flash image, component binaries, SHA-256 list,
build log, validation JSON, a PowerShell flasher, and `README-FLASH.txt`.

## Windows procedure

1. Disconnect the battery from the ESP32-S3 for the first flash.
2. Connect the board directly to the Windows PC with a known USB data cable.
3. Extract the artifact ZIP completely. Do not run the script from inside the ZIP viewer.
4. Open Device Manager and note the ESP32-S3 COM port under **Ports (COM & LPT)**.
5. Open PowerShell in the extracted firmware folder.
6. Run:

   `powershell -ExecutionPolicy Bypass -File .\flash-esp32-dualeye-wake-session.ps1 -Port COM9`

   Replace `COM9` with the actual port.
7. If the board is not detected, hold **BOOT**, tap **RESET**, release **RESET**, then release **BOOT** and rerun the command.
8. Let the script install esptool, identify the ESP32-S3, erase flash, write the image at `0x0`, and verify it.
9. After the completion message, press **RESET** once.
10. Confirm the splash, animated dual koala eyes, and strict wake behavior.

Do not use `-SkipErase` for this release. The full image includes bootloader,
partition table, application, OTA boot metadata, and ESP-SR model data.

## Expected wake behavior

- Ambient commands are discarded while sleeping.
- `Killer Koala` or `Hey Killer Koala` opens a 10-second command session.
- Accepted commands and trusted K1-K8/keyboard input refresh the timer.
- After 10 seconds of inactivity, menus close and animated eyes return.
- Pi-owned speech remains on the Pi/JBL path; the ESP32 speaker handles local wake/basic clips.
