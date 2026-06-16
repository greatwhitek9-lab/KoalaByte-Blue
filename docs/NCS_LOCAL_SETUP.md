# Local NCS setup

KoalaByte Blue can place the NCS and Zephyr workspace inside the repository working tree on the Raspberry Pi.

Default local paths:

```text
third_party/ncs/
third_party/zephyr-sdk-0.17.0/
```

Populate those paths:

```bash
bash scripts/vendor_nrf_connect_sdk.sh
```

Generated status and environment files:

```text
logs/nrf_connect_sdk_status.json
logs/nrf_connect_sdk_env.sh
```

Manual build environment:

```bash
source logs/nrf_connect_sdk_env.sh
```

The setup script downloads the external workspace into the local working tree during install or cache preparation.
