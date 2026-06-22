# Greatwhite Wireshark / tshark wrapper

Greatwhite is a KoalaByte Blue helper for authorized lab packet review with Wireshark/tshark.

It is designed for bounded local captures and offline summaries. It does not enable monitor mode, does not transmit packets, and requires explicit acknowledgement before capture.

## Install dependencies

```bash
bash scripts/setup_system_packages.sh
```

This installs `tshark`, `wireshark-common`, and related system tools when available on apt-based systems.

## Status

```bash
python3 scripts/run_gw.py status
```

## List interfaces

```bash
python3 scripts/run_gw.py interfaces
```

Choose only an owned/authorized lab interface.

## Bounded capture

```bash
python3 scripts/run_gw.py capture \
  --interface wlan0 \
  --duration-seconds 30 \
  --confirm-owned-lab
```

With a capture filter:

```bash
python3 scripts/run_gw.py capture \
  --interface wlan0 \
  --duration-seconds 30 \
  --capture-filter "host 192.168.1.10" \
  --confirm-owned-lab
```

Capture duration is capped by the helper.

## Summarize a pcap

```bash
python3 scripts/run_gw.py summary logs/greatwhite/example.pcapng
```

## nRF Sniffer BLE host-side setup

Nordic's nRF Sniffer for Bluetooth LE package is proprietary. This repository does not redistribute it.

Provide a locally downloaded Nordic package:

```bash
NRF_SNIFFER_ZIP=/path/to/nrf_sniffer_for_bluetooth_le.zip \
  bash scripts/setup_nrf_sniffer_ble.sh
```

Or use an already extracted directory:

```bash
NRF_SNIFFER_DIR=/path/to/extracted/nrf_sniffer \
  bash scripts/setup_nrf_sniffer_ble.sh
```

Check status:

```bash
bash scripts/setup_nrf_sniffer_ble.sh --check-only
python3 scripts/run_gw.py nrf-sniffer-status
```

## Output

Greatwhite writes artifacts under:

```text
logs/greatwhite/
logs/nrf_sniffer_ble_status.json
```

## Safety boundaries

- Use only on interfaces and networks you own or are authorized to test.
- Capture requires `--confirm-owned-lab`.
- The helper does not enable monitor mode.
- The helper does not transmit packets.
- nRF Sniffer firmware flashing is a separate intentional action because it replaces the selected nRF52840 profile.
