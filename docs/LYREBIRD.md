# Lyrebird music player

Lyrebird is KoalaByte Blue's Raspberry Pi-owned music player. The product name is **Lyrebird**; the underlying playback engine remains **Mopidy** so the existing service, JSON-RPC API, media backends, and installer contracts remain stable.

## Ownership and signal flow

- **Raspberry Pi:** installs and runs `mopidy.service`, owns the queue, music library, internet-radio presets, volume, playback state, and audio output.
- **ESP32-S3 DualEye:** sends menu or voice actions to the Pi and displays the selected Lyrebird action through the normal action-status synchronization path.
- **Heltec T114:** displays Koalagotchi/action state through the normal synchronized status path. It does not decode or play music locally.
- **KillerKoala speech:** pauses active music before speech and resumes it afterward.

No music decoder or copyrighted audio is embedded in the ESP32 or T114 firmware. Firmware changes are not required to add tracks or radio presets.

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

## Local music

Copy supported audio files to:

```text
/srv/koalabyte-music
```

Then refresh the library from the Lyrebird menu or run:

```bash
sudo mopidyctl local scan
```

The installer adds common GStreamer codecs, including MP3, AAC, FLAC, Ogg/Vorbis, and other formats supported by the installed plugins.

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

## Controls

Lyrebird exposes these Pi-owned actions:

- status and now-playing information
- play, resume, pause, toggle, and stop
- next and previous track
- software volume up or down in five-percent steps
- local-library refresh
- configured internet-radio presets

The internal commands remain stable for compatibility:

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

Because KillerKoala voice routing derives aliases from visible menu labels and internal commands, commands such as `killerkoala lyrebird play`, `killerkoala lyrebird pause`, and `killerkoala music next` route to the same Pi actions.

## Audio behavior

Mopidy uses a software mixer and the Pi's selected audio sink. The one-shot audio configuration chooses the preferred external output when available. During KillerKoala speech, active Lyrebird playback is paused before TTS begins and resumed after TTS completes.

## Failure behavior

If Mopidy or its localhost RPC endpoint is unavailable, the command returns `MUSIC_PLAYER_ERROR`. That status participates in KoalaByte Blue's normal synchronized error lifecycle instead of silently pretending playback succeeded.

The default installer uses soft-fail behavior so a temporary package-repository outage does not prevent the rest of KoalaByte Blue from installing. Use `STRICT_MOPIDY_PLAYER=1` when Lyrebird availability must be a hard installation requirement.
