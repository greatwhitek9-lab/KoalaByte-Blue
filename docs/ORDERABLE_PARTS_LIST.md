# KoalaByte Blue Orderable Parts List - RevA4 InnoMaker CAN Update

This production update adds exact models, model numbers, and recommended ordering sources for the KoalaByte Blue physical build.

## Best buying strategy

- Buy critical electronics and power parts from PiShop.us, Waveshare, DigiKey, Pololu, Amazon brand storefronts, and authorized distributors.
- Buy commodity cables, standoffs, acrylic, and strain relief from reputable Amazon brand storefronts or McMaster-Carr.
- Avoid no-name power converters, no-name SD cards, suspiciously cheap Raspberry Pi listings, and ambiguous USB-to-CAN clones.

## Exact order list

| Component | Exact model | Model / part number | Qty | Reliable source | Cheapest acceptable source | Target price | Notes |
|---|---|---|---:|---|---|---:|---|
| Main SBC | Raspberry Pi 3 Model B+ | SC0073 / PiShop SKU 9001 / UPC 5060214370165 | 1 | PiShop.us, CanaKit, Micro Center | PiShop.us when in stock | $35-$60 | Core Linux computer. Use stable 5V rail. |
| Dual-eye UI / mic board | Waveshare ESP32-S3-DualEye-LCD-1.28 | ESP32-S3-DualEye-LCD-1.28 | 1 | Waveshare official store | Waveshare official AliExpress store | $28-$40 | UI, mic front-end, serial companion bridge. |
| BLE dongle | Nordic nRF52840 Dongle | PCA10059 / NRF52840-DONGLE / DigiKey 1490-1073-ND | 1 | DigiKey, Mouser, Newark | DigiKey | $11-$25 | USB BLE research dongle. |
| 5V 5A buck regulator | Pololu 5V, 5A Step-Down Voltage Regulator | D24V50F5 / Pololu item #2851 | 1 | Pololu | Pololu or authorized distributor | $29.95 | Main regulated 5V rail; feed from the 12V PD/QC trigger output or 2S source. |
| USB-C PD/QC 12V trigger board | Seloky USB-C PD Trigger Board Module PD/QC Decoy Fast Charge USB Type-C to 12V | Seloky USB-C to 12V PD/QC decoy trigger module | 1 | Amazon / Seloky listing | Amazon | varies | Use as the USB-C input trigger. Verify 12V output with a multimeter before connecting the buck converter. Do not connect 12V directly to the Pi. |
| InnoMaker USB-to-CAN kit | InnoMaker USB to CAN Converter for Raspberry Pi 5/4/Pi3B+/Pi3/Pi Zero(W)/Jetson Nano/Tinker Board/SBCs | InnoMaker USB to CAN Converter kit | 0-1 | InnoMaker/Amazon listing or authorized seller | Same exact listing only | varies | Optional Koala Kan Kommander adapter. Use as SocketCAN `can0` on Linux where supported. Mount internally or in a side/rear service bay. No circular CAN panel port. |
| microSD card | SanDisk High Endurance microSDXC 64GB | SDSQQNR-064G-GN6IA | 1 | Amazon direct, B&H, Best Buy | Amazon direct, not marketplace clones | $8-$13 | Pi OS, logs, reports. |
| USB-C wall charger | Anker 511 Charger Nano 3, 30W | A2147 | 1 | Anker, Amazon Anker store, Best Buy | Amazon Anker store | $15-$23 | PD source for bench or portable charger input. Must support 12V output for the Seloky trigger board. |
| USB-C PD cable | Anker 333 USB-C to USB-C 100W cable | A8758 | 1 | Anker, Amazon Anker store | Amazon Anker store | $8-$13 | PD cable from charger/power bank to PD trigger. |
| ESP32 USB-C data cable | Anker 310 USB-C to USB-C cable or equivalent data cable | A81E6 or equivalent | 1 | Anker / Amazon Anker store | Amazon | $6-$10 | Use actual data-capable cable. |
| Pi micro-USB cable | StarTech 1m Micro-USB cable | UUSBHAUB1M | 1 | DigiKey, Amazon, CDW | Amazon | $5-$8 | Short, quality cable for Pi power/data path. |
| Speaker | Adafruit Mini Metal Speaker w/ Wires, 8 ohm 0.5W | Adafruit Product ID 1890 | 1 | Adafruit or DigiKey | DigiKey if Adafruit out of stock | $1.95-$5 | Small output speaker for alerts/voice path. |
| Mechanical hardware | M2.5 nylon/brass standoff assortment kit | M2.5 assorted 6/10/15/20/25mm kit | 1 kit | Amazon, McMaster-Carr | Amazon assortment kit | $7-$12 | Layer spacing and open-frame stack. |
| Frame plates | 3mm black cast acrylic sheet / custom cut plates | 85x55mm to 90x65mm plates, 3mm acrylic | 1 set | Ponoko, SendCutSend, local makerspace | Amazon acrylic sheet + drill template | $8-$25 | Mechanical mounting plates; no PCB. |
| 5V rail fuse | Littelfuse 0154005.DR 5A Nano2 Fuse or inline 5A fuse holder | 0154005.DR | 1 | DigiKey, Mouser | Amazon inline fuse holder | $1-$6 | Over-current protection on 5V rail. |
| Output capacitor | Panasonic FR low-ESR electrolytic capacitor 1000uF 10V | EEU-FR1A102 | 1 | DigiKey, Mouser | Amazon capacitor kit, lower confidence | $1-$2 | Place near 5V distribution point. |
| Cable management | 3M Dual Lock or adhesive cable tie mounts | 3M Dual Lock SJ3550 or generic mounts | 1 set | Amazon, McMaster-Carr | Amazon | $5-$10 | Strain relief and wire control. |
| Optional powered USB hub | Sabrent 4-Port USB 3.0 Hub with switches | HB-UM43 | 0-1 | Amazon/Sabrent | Amazon | $10-$15 | Optional if Pi USB power/load is tight. |
| Optional USB mic fallback | UGREEN USB external sound card | CM108-style USB audio adapter | 0-1 | Amazon/UGREEN | Amazon | $8-$12 | Fallback if DualEye mic pin mapping is not complete. |

## Power notes

- Main regulator: Pololu D24V50F5 / Pololu item #2851.
- PD trigger/sink board: Seloky USB-C PD Trigger Board Module PD/QC Decoy Fast Charge USB Type-C to 12V.
- Verify the Seloky trigger board outputs about 12V before connecting it to the buck converter.
- Step the 12V trigger output down to 5V with the Pololu regulator. Do not feed the Raspberry Pi directly from the 12V trigger output.
- Add a 3A-5A fuse and 470uF-1000uF output capacitor near the 5V distribution point.

## Koala Kan Kommander notes

- The InnoMaker USB-to-CAN kit is optional.
- Do not use the older circular CAN panel-port concept.
- Mount the adapter internally or expose it through a rectangular side/rear service bay with strain relief.
- Do not connect CAN_H or CAN_L directly to Raspberry Pi GPIO.
- Production software is passive by default and does not transmit raw CAN frames.

## Approximate total

- Bare-minimum working build: $115-$150 before optional CAN kit.
- Recommended build: $165-$230 before optional CAN kit.
- Fully equipped build: $225-$310 before optional CAN kit and enclosure finishing.
