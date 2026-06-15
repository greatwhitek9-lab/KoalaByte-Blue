# RevA2 Power Update

This update locks the power-management BOM to exact, orderable parts.

## Added exact parts

| Function | Exact model | Model / item number | Qty | Notes |
|---|---|---:|---:|---|
| Main 5V buck regulator | Pololu 5V, 5A Step-Down Voltage Regulator D24V50F5 | Pololu item #2851 | 1 | Main regulated 5V rail. Input must be above 5V plus dropout; use the Seloky 12V PD/QC trigger output or a verified 2S source. |
| USB-C PD/QC 12V trigger board | Seloky USB-C PD Trigger Board Module PD/QC Decoy Fast Charge USB Type-C to 12V | Seloky USB-C to 12V PD/QC decoy trigger module | 1 | Replaces the prior USB-C PD breakout reference. Verify 12V output with a multimeter before connecting the buck converter. |

## Wiring recommendation

Preferred main power path:

```text
USB-C PD/QC source capable of 12V
  -> Seloky USB-C PD/QC 12V trigger board
  -> Pololu D24V50F5 buck regulator
  -> fused 5V distribution rail
  -> Raspberry Pi / ESP32-S3 DualEye / USB peripherals
```

Do not feed the Pololu D24V50F5 from a 5V PD trigger setting. It is a step-down regulator and needs headroom above 5V. Do not connect the Seloky 12V trigger output directly to the Raspberry Pi or 5V modules.

## Validation

Before connecting electronics:

1. Verify Seloky PD/QC trigger output voltage with a multimeter; expected output is about 12V.
2. Verify Pololu regulator output is 5.05V to 5.15V under dummy load.
3. Add a 3A-5A fuse on the 5V rail.
4. Add 470uF-1000uF electrolytic capacitance near the 5V distribution point.
5. Boot the Pi and confirm no undervoltage warnings.
