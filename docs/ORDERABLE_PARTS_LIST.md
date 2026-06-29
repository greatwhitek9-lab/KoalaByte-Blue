# KoalaByte Blue V2 Heltec Edition Orderable Parts List

This production update uses a **PIFFA-style 50000 mAh USB portable power bank 22.5 W class** as the main power source, uses the **Heltec Mesh Node T114 onboard nRF52840** as the primary BLE board, and uses one **8 independent key button module** for the front-panel K1-K8 controls.

## Best buying strategy

- Buy critical electronics and power parts from PiShop.us, Waveshare, DigiKey, Amazon brand storefronts, and authorized distributors.
- Buy the USB portable power bank from a reputable seller and use only its normal regulated USB output.
- Buy commodity cables, standoffs, acrylic, and strain relief from reputable Amazon brand storefronts or McMaster-Carr.
- Avoid no-name SD cards, suspiciously cheap Raspberry Pi listings, ambiguous USB-to-CAN clones, charge-only USB cables, and loose-cell lithium builds.

## Exact order list

| Component | Exact model | Model / part number | Qty | Reliable source | Cheapest acceptable source | Target price | Notes |
|---|---|---|---:|---|---|---:|---|
| Main SBC | Raspberry Pi 3 Model B+ | SC0073 / PiShop SKU 9001 / UPC 5060214370165 | 1 | PiShop.us, CanaKit, Micro Center | PiShop.us when in stock | $35-$60 | Core Linux computer. Power through micro-USB from the USB power bank. |
| Dual-eye UI / mic board | Waveshare ESP32-S3-DualEye-LCD-1.28 | ESP32-S3-DualEye-LCD-1.28 | 1 | Waveshare official store | Waveshare official AliExpress store | $28-$40 | Face, eyes, UI, mic front-end, serial companion bridge, and secondary local BLE node. |
| Primary BLE / LoRa radio board | Heltec Mesh Node T114 | Heltec Mesh Node T114 Rev. 2.0 / HT-N5262 class board | 1 | Heltec official store, authorized Heltec resellers | Reputable Heltec listing only | varies | Main BLE board for the Heltec Edition. Onboard nRF52840 is the primary BLE source; onboard SX1262 provides LoRa radio capability. |
| USB portable power bank | PIFFA-style Portable Charger Power Bank 50000 mAh 22.5 W class | 50000 mAh 22.5 W USB output power bank | 1 | Amazon listing or reputable equivalent | Same or better rated bank | varies | Main simplified power source. Replaces 18650 cells, BMS, fuse, switch, buck converter, and PD trigger. |
| Pi power cable | Short USB-A or USB-C to micro-USB power cable | Quality low-resistance cable | 1 | Anker, StarTech, CanaKit, Amazon direct | Short quality cable only | $5-$10 | Powers Raspberry Pi 3B+ from the power bank. Use the shortest reliable cable possible. |
| ESP32 USB-C data cable | Short USB-A or USB-C to USB-C data cable | Data-capable cable | 1 | Anker, UGREEN, Amazon direct | Data-capable cable only | $6-$12 | Connects ESP32-S3 DualEye to Pi or powered USB hub. |
| Heltec T114 USB-C data cable | Short USB-A or USB-C to USB-C data cable | Data-capable cable | 1 | Anker, UGREEN, Amazon direct | Data-capable cable only | $6-$12 | Connects the Heltec T114 to the Pi or powered USB hub for primary BLE serial. |
| Optional powered USB hub | Sabrent 4-Port USB hub with switches or equivalent | HB-UM43 or equivalent | 0-1 | Amazon/Sabrent | Amazon | $10-$20 | Use if Pi USB power or enumeration becomes unstable with multiple modules. |
| InnoMaker USB-to-CAN kit | InnoMaker USB to CAN Converter for Raspberry Pi 5/4/Pi3B+/Pi3/Pi Zero(W)/Jetson Nano/Tinker Board/SBCs | InnoMaker USB to CAN Converter kit | 0-1 | InnoMaker/Amazon listing or authorized seller | Same exact listing only | varies | Optional Koala Kan Kommander adapter. Use as SocketCAN `can0` on Linux where supported. Mount internally or in a side/rear service bay. |
| microSD card | SanDisk High Endurance microSDXC 64GB | SDSQQNR-064G-GN6IA | 1 | Amazon direct, B&H, Best Buy | Amazon direct, not marketplace clones | $8-$13 | Pi OS, logs, reports. |
| Speaker | Adafruit Mini Metal Speaker w/ Wires, 8 ohm 0.5W | Adafruit Product ID 1890 | 1 | Adafruit or DigiKey | DigiKey if Adafruit out of stock | $1.95-$5 | Small output speaker for alerts/voice path. |
| Front-panel buttons | GODIYMODULES 2PCS 8 Independent Key Button Touch Button Module | MOD-ST034-1 / ASIN B0FH9C88DJ | 1 module used; listing includes 2 | Amazon listing or reputable equivalent | Same K1-K8 independent-key board | varies | Replaces six loose 4-pin tactile buttons. Use K1-K6 for menu controls, K7 Power On/Off, and K8 Reset / Reboot. Wire VCC to Pi 3.3V only, GND to Pi GND, K1-K8 to GPIO. |
| 8-key front button bezel | KoalaByte Blue front button bezel for K1-K8 module | RevA7/RevA25 8-key bezel | 1 | 3D print from production/case files | Local print | varies | Aligns the single 8-key board across the enclosure front. |
| Mechanical hardware | M2.5 nylon/brass standoff assortment kit | M2.5 assorted 6/10/15/20/25mm kit | 1 kit | Amazon, McMaster-Carr | Amazon assortment kit | $7-$12 | Layer spacing and open-frame stack. |
| Frame plates | 3mm black cast acrylic sheet / custom cut plates | 85x55mm to 90x65mm plates, 3mm acrylic | 1 set | Ponoko, SendCutSend, local makerspace | Amazon acrylic sheet + drill template | $8-$25 | Mechanical mounting plates; no PCB. |
| Cable management | 3M Dual Lock or adhesive cable tie mounts | 3M Dual Lock SJ3550 or generic mounts | 1 set | Amazon, McMaster-Carr | Amazon | $5-$10 | Strain relief and wire control. |
| ESP32 2.4 GHz antenna | 2.4 GHz Wi-Fi/Bluetooth antenna with IPEX1/U.FL-compatible pigtail | Match the ESP32-S3 DualEye connector | 1 | Waveshare docs, DigiKey, Mouser, reputable RF seller | Same frequency/connector only | varies | Use only for the ESP32-S3 DualEye Wi-Fi/Bluetooth path. |
| Heltec LoRa antenna | Frequency-matched LoRa antenna for your region | Match the Heltec T114 antenna connector and legal band | 1 | Heltec official store, DigiKey, Mouser, reputable RF seller | Same connector/frequency only | varies | Required for Heltec SX1262 LoRa work. Use the correct regional frequency and connector. |
| Optional USB mic fallback | UGREEN USB external sound card | CM108-style USB audio adapter | 0-1 | Amazon/UGREEN | Amazon | $8-$12 | Fallback if DualEye mic mapping is not complete. |

## Removed from the main Heltec Edition build

The following older power and control items are no longer part of the current production plan:

- six loose 4-pin tactile buttons
- loose protected 18650 cells
- 2x18650 series holder
- 2S Li-ion BMS/protection wiring
- inline battery fuse holder and blade fuse
- main DC battery switch
- 5 V buck regulator
- USB-C PD/QC trigger board
- raw battery-voltage distribution rails

The separate external Nordic nRF52840 USB Dongle is no longer the default main BLE board for this edition. Keep it only for explicit legacy compatibility tests.

## Power notes

- Power the Pi from the USB power bank regulated output through the Pi 3B+ micro-USB input.
- Use short quality data cables for ESP32-S3 DualEye and Heltec T114.
- If the Pi reports undervoltage or USB devices disconnect, move ESP32/CAN/Heltec accessories to a powered USB hub.
- Do not feed the Pi, ESP32, Heltec T114, 8-key button module, or USB devices from raw lithium battery wiring.
- K7 can request software shutdown while the Pi is running; true power-on from fully off still needs a proper power-control path or the power bank's own control.

## Koala Kan Kommander notes

- The InnoMaker USB-to-CAN kit is optional.
- Do not use the older circular CAN panel-port concept.
- Mount the adapter internally or expose it through a rectangular side/rear service bay with strain relief.
- Do not connect CAN_H or CAN_L directly to Raspberry Pi GPIO.
- Production software is passive by default unless explicitly gated for isolated bench-simulator work.

## Approximate total

- Bare-minimum working build: depends on Raspberry Pi, Heltec T114, button board, and power bank price.
- Recommended build: Raspberry Pi + ESP32-S3 DualEye + Heltec T114 + power bank + short cables + microSD + 8-key button module + frame hardware.
- Fully equipped build: add powered USB hub, speaker, case, ESP32 antenna, Heltec LoRa antenna, and optional InnoMaker USB-to-CAN kit.
