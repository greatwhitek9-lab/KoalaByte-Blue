#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time

from koalablue.esp32_dualeye_speech_synced_bridge import (
    ESP32DualEyeVoiceBridge,
    default_esp32_port,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the local-first ESP32-S3 DualEye voice, execution, XP, latched Koalagotchi, and Heltec speech-sync bridge"
    )
    parser.add_argument("--port", default=default_esp32_port())
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--udp-port", type=int, default=42110)
    parser.add_argument("--seconds", type=float, default=20.0)
    parser.add_argument("--once", action="store_true", help="Exit after first routed voice event")
    parser.add_argument("--status-only", action="store_true", help="Request integrated node status then exit after a short read window")
    parser.add_argument("--simulate", default=None, help="Ask ESP32 firmware to emit a simulated voice command phrase")
    parser.add_argument("--wifi-ssid", default=None, help="Provision ESP32 Wi-Fi SSID over USB")
    parser.add_argument("--wifi-password", default="")
    parser.add_argument("--pi-host", default=None, help="Pi LAN address sent to the ESP32 for UDP callbacks")
    args = parser.parse_args()

    provisioning_only = bool(args.wifi_ssid and args.pi_host)
    bridge = ESP32DualEyeVoiceBridge(
        port=args.port,
        baud=args.baud,
        udp_port=args.udp_port,
    )
    if args.status_only:
        bridge.open()
        try:
            for _ in range(8):
                bridge.read_once()
        finally:
            bridge.close()
        payload = {"status": "ESP32_DUALEYE_NODE_STATUS_REQUESTED", "port": args.port, "udp_port": args.udp_port}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if provisioning_only:
        bridge.open()
        try:
            bridge.provision_wifi(args.wifi_ssid, args.wifi_password, args.pi_host, args.udp_port)
            time.sleep(1.0)
        finally:
            bridge.close()
        print(json.dumps({"status": "ESP32_DUALEYE_WIFI_PROVISIONED", "ssid": args.wifi_ssid, "pi_host": args.pi_host, "udp_port": args.udp_port}, indent=2, sort_keys=True))
        return 0

    if args.simulate:
        routed = []
        bridge.open()
        try:
            bridge.simulate_voice_command(args.simulate)
            deadline = time.time() + args.seconds
            while time.time() < deadline:
                event = bridge.read_once()
                if event is None:
                    continue
                routed.append(bridge.route_event(event))
                if args.once or routed:
                    break
        finally:
            bridge.close()
        result = {"status": "ESP32_DUALEYE_INTEGRATED_BRIDGE_COMPLETE", "port": args.port, "udp_port": args.udp_port, "routed_count": len(routed), "routed": routed, "updated_at": time.time()}
    else:
        result = bridge.run(seconds=args.seconds, once=args.once)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
