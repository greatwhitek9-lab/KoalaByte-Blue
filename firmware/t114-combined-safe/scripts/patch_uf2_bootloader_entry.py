#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"UF2 bootloader patch expected one {label} anchor, found {count}")
    return text.replace(old, new, 1)


def patch(source: Path, output: Path) -> None:
    text = source.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "#include <zephyr/bluetooth/hci.h>\n",
        "#include <zephyr/bluetooth/hci.h>\n"
        "#include <zephyr/sys/reboot.h>\n"
        "#include <nrfx.h>\n",
        "header",
    )
    text = replace_once(
        text,
        "static void handle_line(const char *line)\n{\n",
        "static void enter_uf2_bootloader(void)\n"
        "{\n"
        "    printk(\"{\\\"type\\\":\\\"bootloader_ack\\\",\\\"device\\\":\\\"heltec-t114\\\",\\\"mode\\\":\\\"uf2\\\",\\\"status\\\":\\\"rebooting\\\"}\\n\");\n"
        "    k_msleep(100);\n"
        "    /* Adafruit-compatible nRF52840 UF2 bootloaders use GPREGRET 0x57. */\n"
        "    NRF_POWER->GPREGRET = 0x57;\n"
        "    __DSB();\n"
        "    sys_reboot(SYS_REBOOT_COLD);\n"
        "}\n\n"
        "static void handle_line(const char *line)\n"
        "{\n",
        "handler insertion",
    )
    text = replace_once(
        text,
        "    if (strstr(line, \"\\\"type\\\":\\\"koalagotchi_status\\\"\")) {\n",
        "    if (strstr(line, \"\\\"type\\\":\\\"koalabyte_bootloader\\\"\") ||\n"
        "        strstr(line, \"\\\"type\\\":\\\"bootloader\\\"\") ||\n"
        "        strcmp(line, \"KOALABYTE_BOOTLOADER_UF2\") == 0 ||\n"
        "        strcmp(line, \"REBOOT_UF2\") == 0) {\n"
        "        enter_uf2_bootloader();\n"
        "    } else if (strstr(line, \"\\\"type\\\":\\\"koalagotchi_status\\\"\")) {\n",
        "command routing",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    patch(Path(args.source), Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
