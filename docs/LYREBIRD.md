# Lyrebird music player

Lyrebird is KoalaByte Blue's Raspberry Pi-owned music player. The product name is **Lyrebird**; the underlying playback engine remains **Mopidy** so the existing service, JSON-RPC API, media backends, and installer contracts remain stable.

## Ownership and signal flow

- **Raspberry Pi:** installs and runs `mopidy.service`, owns the queue, music library, internet-radio presets, volume, playback state, and audio output.
- **ESP32-S3 DualEye:** sends menu or voice actions to the Pi. In Lyrebird browsing screens, the active song or station is shown on the left display while the scrollable list remains on the right display.
- **Heltec T114:** shows the persistent Koalagotchi `DANCE` animation while Lyrebird is playing and exits the dance state when playback is paused or stopped.
- **KillerKoala speech:** pauses active music before speech and resumes it afterward.

No music decoder or copyrighted audio is embedded in the ESP32 or T114 firmware. Tracks, queues, radio streams, and decoding remain Pi-owned.

## Installation

The canonical one-shot installs Lyrebird unless music setup is explicitly skipped:

```bash
bash one-shot-install.sh
```

For a first deployment where music must be treated as mandatory:

```bash
STRICT_MOPIDY_PLAYER=1 bash one-shot-install.sh
```

Check the installed service and local API:

```bash
systemctl status mopidy.service --no-pager
curl -fsS -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"core.playback.get_state"}' \
  http://127.0.0.1:6680/mopidy/rpc
cat logs/music_player/mopidy_setup_status.json
```

## Uploaded songs

Copy supported audio files into:

```text
/srv/koalabyte-music
```

Lyrebird recursively discovers supported files, including MP3, FLAC, Ogg, AAC, M4A, Opus, WMA, AIFF, and WAV. Subdirectories are displayed as part of the song label.

Open:

```text
Lyrebird → Uploaded Songs
```

The list is rebuilt when the submenu opens. Use **Refresh Uploaded Songs** after copying files, or run:

```bash
sudo mopidyctl local scan
```

The complete discovered song collection is placed into the Mopidy queue when a song is selected, allowing next and previous controls to move through the uploaded library.

## Internet radio presets

Edit the private Pi configuration:

```text
/etc/koalabyte-blue/music.json
```

Example:

```json
{
  "engine": "mopidy",
  "rpc_url": "http://127.0.0.1:6680/mopidy/rpc",
  "radio_presets": {
    "Bush Radio": "https://example.invalid/direct-stream.ogg"
  }
}
```

Use a direct audio-stream URL, not a normal station web page. Do not commit credentials or authenticated stream URLs.

Open:

```text
Lyrebird → Radio Stations
```

Configured stations appear as a scrollable list. Selecting a station creates a queue containing all configured stations so next and previous controls can move through them.

## Menu and button controls

Lyrebird follows the standard KoalaByte menu layout and status lifecycle.

- **K5 / Up:** scroll up through songs, stations, or Lyrebird controls.
- **K6 / Down:** scroll down.
- **K3 / Enter:** play the highlighted song or station. When the highlighted item is already active, K3/Enter toggles Play/Pause.
- **K4 / Right / Forward:** play the next queued song or station.
- **K2 / Left / Back once:** restart the current song or stream from its beginning when supported.
- **K2 twice within 0.75 seconds:** play the previous queued song or station.
- **K1 / Menu:** return to the main canopy.
- **Touch long-press:** equivalent to K3 selection.
- **Touch drag:** scroll the visible list.

Explicit menu rows remain available for status, now playing, play/resume, pause, toggle, stop, next, previous, volume, library refresh, and configuration.

## Display behavior

While a Lyrebird list is open:

- The **ESP32-S3 left display** shows `Playing: <song or station>` or `Paused: <song or station>`.
- The **ESP32-S3 right display** shows up to six visible list rows with the current highlight, position, and scroll window.
- The **Heltec T114** shows Koalagotchi in the persistent `DANCE` animation while playback is active.
- Pausing or stopping Lyrebird sends a Koalagotchi mode-exit state to the T114.

This uses the existing menu and face synchronization protocol; it does not require a new flash layout or separate display transport.

## Stable internal commands

The existing commands remain stable:

```text
music_status
music_now_playing
music_play
music_pause
music_toggle
music_next
music_previous
music_stop
music_volume_up
music_volume_down
music_refresh_library
music_config_status
music_preset:<preset-name>
```

Lyrebird also adds runtime commands for uploaded files and restart behavior:

```text
music_song:<generated-file-id>
music_restart
```

Because KillerKoala voice routing derives aliases from visible menu labels and internal commands, commands such as `killerkoala lyrebird play`, `killerkoala lyrebird pause`, and `killerkoala music next` route to the same Pi actions. Song filenames and private station names remain runtime-generated menu entries rather than fixed firmware assets.

## Audio behavior

Mopidy uses a software mixer and the Pi's selected audio sink. The one-shot audio configuration chooses the preferred external output when available. During KillerKoala speech, active Lyrebird playback is paused before TTS begins and resumed after TTS completes.

## Failure behavior

If Mopidy or its localhost RPC endpoint is unavailable, the command returns `MUSIC_PLAYER_ERROR`. That status participates in KoalaByte Blue's normal synchronized error lifecycle instead of silently pretending playback succeeded.

The default installer uses soft-fail behavior so a temporary package-repository outage does not prevent the rest of KoalaByte Blue from installing. Use `STRICT_MOPIDY_PLAYER=1` when Lyrebird availability must be a hard installation requirement.
