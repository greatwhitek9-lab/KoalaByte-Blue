#!/usr/bin/env python3
"""Run Heltec T114 nRF52840 BlueZ HCI wrapper actions."""

from koalablue.t114_bluez import run_cli

if __name__ == "__main__":
    raise SystemExit(run_cli())
