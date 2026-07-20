# KoalaByte Blue one-shot firmware bundle

The Pi one-shot install package carries the Pi software plus the exact peripheral
images validated for the same release. The installer must prefer these prebuilt,
hash-checked files and must not rebuild firmware on the Raspberry Pi unless an
explicit source-build override is requested.

## Heltec T114 / HT-n5262

Release image:

- file: `firmware/prebuilt/t114/koalabyte-t114-final-original-mouth-continuous-warp-latched-koalagotchi-right-landscape-ht-n5262.uf2`
- target volume: `HT-n5262`
- UF2 family: `0x239a0071`
- application offset: `0x00026000`
- SHA-256: `c0e0a0d288237c55c629bbc78b8ece19ccaf37bea3356ee07cb206ddaef9d9dd`
- source build commit: `f6ac52c743552821287cf002f599f81e01479441`

The currently hardware-observed boot result is the correct original
purple/green KillerKoala artwork followed by a static face. The linked firmware
contains the continuous-warp and lifecycle code, but idle movement has not been
physically confirmed. This limitation must remain visible in release notes and
must not be reported as a passed animation gate.

When a UF2 copy completes, the bootloader immediately reboots and removes the
volume. Windows may then display `0x80070022` / `ERROR_WRONG_DISK` while Explorer
is finishing the copy. If the board rebooted into the new artwork, that eject
message is not by itself a flash failure. Never format or run CHKDSK on the
bootloader volume.

## ESP32-S3 DualEye

The package must include the v0.9.8 full-flash image produced by the ESP32
PlatformIO workflow under:

`firmware/prebuilt/esp32/koalabyte-esp32-s3-dualeye-v0.9.8-killerkoala-wake-session-full-flash.bin`

Required runtime policy:

- sleeping voice commands are discarded;
- `Killer Koala` or `Hey Killer Koala` opens a 10-second session;
- accepted voice commands refresh the timer;
- K1-K8 and attached-keyboard menu input wake or refresh the same session;
- expiry closes the menu and restores animated koala eyes;
- Pi-generated speech remains on the Pi/JBL speaker path;
- the ESP32 speaker remains for local wake/basic responses.

The final SHA-256 is written into `firmware/prebuilt/manifest.json` by the
release-bundle workflow after the linked firmware image is produced.

## InnoMaker USB2CAN

The InnoMaker adapter keeps its stock firmware. The one-shot installer configures
Linux SocketCAN `can0`, installs `koalabyte-can0.service`, and performs readiness
checks. It does not flash the adapter and does not transmit vehicle CAN traffic
during installation.

## One-shot behavior

1. Install/update the Raspberry Pi companion, Python environment, udev rules,
   services, K1-K8 handling, keyboard handling, audio routing, and AI runtime.
2. Verify the bundled firmware hashes.
3. Flash ESP32 only when explicitly enabled or when the connected firmware is
   identified as older than the bundled wake-session release.
4. Flash T114 only when the `HT-n5262` bootloader volume is present. A normal
   serial connection is not treated as permission to replace the UF2 image.
5. Configure InnoMaker as SocketCAN without adapter firmware replacement.
6. Validate the JBL/selected Pi audio sink and keep Pi-owned speech on that sink.
7. Write machine-readable results under `logs/one_shot/`.
