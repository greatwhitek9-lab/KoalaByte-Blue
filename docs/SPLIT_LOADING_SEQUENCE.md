# KillerKoala Split Loading Sequence

During an executable menu action, KoalaByte Blue divides the loading UI between the two display boards.

## Heltec T114 onboard TFT

The T114 renders the jungle/Jumanji-style loading banner one letter at a time:

```text
<< L >>
<< LO >>
<< LOA >>
<< LOAD >>
<< LOADI >>
<< LOADIN >>
<< LOADING >>
```

The sequence repeats until the selected action finishes. The T114 combined-safe firmware uses the board's onboard 135x240 ST7789 display and a dark-jungle, eucalyptus-leaf, and gold-border treatment.

## ESP32-S3 DualEye

The DualEye remains in KillerKoala AI-eye mode during the same loading period:

- left eye remains ultraviolet/purple;
- right eye remains cyber green;
- the cyber eyes use the active pulse animation;
- the Heltec loading text is not drawn over the eyes.

## Transport

The Raspberry Pi emits two separate USB CDC payloads for each loading frame:

```text
Heltec T114          -> display_mode: jungle_loading_banner
ESP32-S3 DualEye     -> display_mode: ai_eyes, animation: pulse
```

Serial control lines remain inactive while the ports open, preventing common ESP32 DTR/RTS auto-reset circuits from interrupting the loading animation. A missing display or serial-port failure is non-fatal and does not stop the selected menu action.

## Validation

Static validation:

```bash
cd ~/KoalaByte-Blue
PYTHONPATH=pi-companion python3 scripts/check_killerkoala_loading_face.py
PYTHONPATH=pi-companion python3 scripts/check_killerkoala_face_mouth_sync.py
```

Connected-hardware test:

```bash
PYTHONPATH=pi-companion python3 scripts/check_killerkoala_face_mouth_sync.py \
  --emit-loading-test --strict-ports
```

The connected test sends `<< LOAD >>` to the T114 and an eyes-only pulsing payload to the DualEye.

## Firmware update

This feature changes the T114 combined-safe firmware. Put the T114 into the `HT-n5262` UF2 bootloader and run the current one-shot installer:

```bash
bash koalabyte-install.sh --heltec-uf2-first
```
