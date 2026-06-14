# RevA2 Power Update

This update locks the power-management BOM to exact, orderable parts.

## Added exact parts

| Function | Exact model | Model / item number | Qty | Notes |
|---|---|---:|---:|---|
| Main 5V buck regulator | Pololu 5V, 5A Step-Down Voltage Regulator D24V50F5 | Pololu item #2851 | 1 | Main regulated 5V rail. Input must be above 5V plus dropout; use 9V/12V PD or 2S source. |
| USB-C PD trigger / sink board | Adafruit USB Type C Power Delivery Dummy Breakout - I2C or Fixed - HUSB238 | Product ID 5807 | 1 | Can be configured by jumpers or I2C. 5V/2A mode is suitable for auxiliary/test input, not feeding the 5V buck. |

## Wiring recommendation

Preferred main power path:

```text
USB-C PD source set to 9V or 12V
  -> Adafruit HUSB238 PD trigger board
  -> Pololu D24V50F5 buck regulator
  -> fused 5V distribution rail
  -> Raspberry Pi / ESP32-S3 DualEye / USB peripherals
```

Do not feed the Pololu D24V50F5 from a 5V PD trigger setting. It is a step-down regulator and needs headroom above 5V.

## Validation

Before connecting electronics:

1. Verify PD trigger output voltage with a multimeter.
2. Verify Pololu regulator output is 5.05V to 5.15V under dummy load.
3. Add a 3A-5A fuse on the 5V rail.
4. Add 470uF-1000uF electrolytic capacitance near the 5V distribution point.
5. Boot the Pi and confirm no undervoltage warnings.
