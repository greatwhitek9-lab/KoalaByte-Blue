# Raspberry Pi HDMI Display Switch

KoalaByte Blue can use a monitor connected to the Raspberry Pi as an additional synchronized display. The HDMI compositor shows the KillerKoala eyes and animated mouth, the current menu, Koalagotchi action/status scenes, speech motion, and the purple/green error alarm.

The same HDMI output can be released back to Raspberry Pi OS at any time. Switching only changes the HDMI presentation layer: voice recognition, K1-K8, menu actions, ESP32-S3, Heltec T114, BLE, music, AI, and the other Pi services keep running.

| Mode | HDMI output | Background runtime |
|---|---|---|
| `koalabyte` | Fullscreen KoalaByte eyes, mouth, menu, Koalagotchi, and alarms | All services continue |
| `desktop` | Raspberry Pi OS desktop, or the Linux console on Pi OS Lite | All services continue |

The default is `koalabyte`. With no connected HDMI monitor, the compositor stays active but idle and the original headless behavior is unchanged.

## Switch the display

Use any of these control surfaces:

| Control | Show Raspberry Pi OS | Show KoalaByte Blue |
|---|---|---|
| Voice | `killerkoala show Pi OS on HDMI` | `killerkoala show KoalaByte on HDMI` |
| KoalaByte menu | System / Companion → Show Pi OS on HDMI | System / Companion → Show KoalaByte on HDMI |
| HDMI UI | Press `F12` or select the **PI OS** button | Use voice, the Pi OS launcher, the ESP32/T114 menu, or the CLI |
| Raspberry Pi OS application menu | Select **Toggle KoalaByte HDMI** | Select **Toggle KoalaByte HDMI** again |
| CLI | `scripts/set_hdmi_display_mode.py desktop` | `scripts/set_hdmi_display_mode.py koalabyte` |

The complete CLI commands are:

```bash
cd ~/KoalaByte-Blue
./pi-companion/.venv/bin/python scripts/set_hdmi_display_mode.py desktop
./pi-companion/.venv/bin/python scripts/set_hdmi_display_mode.py koalabyte
./pi-companion/.venv/bin/python scripts/set_hdmi_display_mode.py toggle
./pi-companion/.venv/bin/python scripts/set_hdmi_display_mode.py status
```

The selected mode is persistent across service restarts and reboots in `logs/hdmi/display_mode.json`.

On Raspberry Pi OS Lite, `desktop` releases fullscreen DRM/KMS and reveals the normal console because Lite does not include a graphical desktop. Install a supported Raspberry Pi OS desktop if a windowed desktop is required.

## HDMI controls

While the KoalaByte HDMI view is visible:

- Arrow keys or WASD navigate the shared menu.
- Enter selects; M returns to the main menu; Escape goes back.
- Mouse wheel or touch scrolls.
- A long press selects a menu row.
- A double-tap reopens the main menu from the face.
- F12 or the **PI OS** button releases HDMI to Raspberry Pi OS.

Keyboard and touch input are written to a local command queue. `koalabyte-menu.service` remains the sole menu/action owner and dispatches those requests through the same path used by K1-K8. The HDMI process never opens the ESP32 or Heltec serial port.

## Installation and service

The canonical installer sets up the compositor, hardware groups, persistent state directories, boot service, and Raspberry Pi OS application-menu launcher:

```bash
KOALABYTE_SERVICE_USER="$(whoami)" bash one-shot-install.sh
```

The service is safe on both desktop and Lite images:

```bash
systemctl status koalabyte-hdmi.service --no-pager -l
journalctl -u koalabyte-hdmi.service -n 100 --no-pager
```

It prefers an existing Wayland or X11 session. If a display manager is enabled, the service waits for that user session instead of seizing DRM during desktop startup. On Pi OS Lite, where no display manager is enabled, it uses SDL DRM/KMS directly. Disconnecting HDMI closes the renderer and leaves the rest of KoalaByte running; reconnecting it restores the selected mode automatically.

## Configuration

`koalabyte-hdmi.service` uses automatic connector detection by default:

| Environment value | Behavior |
|---|---|
| `KOALABYTE_HDMI=auto` | Render only when HDMI or an active graphical display is detected |
| `KOALABYTE_HDMI=on` | Force the compositor on |
| `KOALABYTE_HDMI=off` | Keep the optional compositor idle |
| `KOALABYTE_PI_DESKTOP=on` | Wait for a graphical user session before rendering |
| `KOALABYTE_PI_DESKTOP=off` | Treat the host as Lite and permit direct DRM/KMS |
| `KOALABYTE_SDL_VIDEODRIVER=kmsdrm` | Override SDL backend selection when no desktop session exists |
| `KOALABYTE_HDMI_WINDOWED=1` | Use a resizable development window instead of fullscreen |
| `KOALABYTE_HDMI_STATE_HZ=12` | Set sanitized state polling rate while animation remains at the configured FPS |

After changing the systemd environment, run `sudo systemctl daemon-reload` and restart `koalabyte-hdmi.service`.

## Verify and troubleshoot

These checks do not open the display or touch either board serial port:

```bash
cd ~/KoalaByte-Blue
PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python scripts/check_hdmi_display.py
PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python scripts/run_hdmi_display.py --check
PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python scripts/run_hdmi_display.py --once
cat logs/hdmi/hdmi_display_status.json
```

Expected contract marker:

```text
HDMI_DISPLAY_CONTRACT_PASS
```

If HDMI is connected but blank, check that the service user belongs to `video`, `render`, and `input` where those groups exist, then reboot once after the first install so the new memberships take effect. The hardware doctor reports the detected connector, selected display mode, compositor status, and group membership.

## Runtime ownership

The compositor is deliberately a one-way state consumer:

- Menu state comes from `koalabyte-menu.service`.
- Face, speech, action, Koalagotchi, and error producers publish sanitized local snapshots.
- Credentials, protected keyboard values, and audio buffers are not copied into HDMI state.
- Keyboard/touch requests are queued back to the Pi-owned menu.
- ESP32 and Heltec serial ownership remains with the existing voice and BLE services.

This preserves voice and every existing command surface while adding HDMI as an optional presentation layer.
