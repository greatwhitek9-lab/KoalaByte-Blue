Import("env")

from pathlib import Path
import audioop
import base64
import os
import re
import shutil
import subprocess
import tempfile
import textwrap

project = Path(env.subst("$PROJECT_DIR"))
output = project / "src" / "local_voice_responses_generated.cpp"

# Microsoft William supplies the Australian male timbre. The spoken character is
# always KillerKoala; "William" is never a character name or self-introduction.
VOICE_NAME = "en-AU-WilliamNeural"
SPOKEN_IDENTITY = "KillerKoala"
RECENT_HISTORY_DEPTH = 3
_DISALLOWED_SPOKEN_IDENTITY = re.compile(r"\bwilliam\b", re.IGNORECASE)

try:
    VOICE_COMMAND_TIMEOUT_SECONDS = max(
        45,
        int(os.getenv("KOALABYTE_LOCAL_VOICE_COMMAND_TIMEOUT_SECONDS", "180")),
    )
except ValueError as exc:
    raise RuntimeError(
        "KOALABYTE_LOCAL_VOICE_COMMAND_TIMEOUT_SECONDS must be an integer"
    ) from exc

# Forty compact offline clips. Every category has at least four unique lines so a
# three-entry recent-history window can always exclude the last three responses.
PHRASES = (
    ("Wake", "Righto, mate. Killer Koala here. What's the play?"),
    ("Wake", "G'day, legend. Killer Koala is awake."),
    ("Wake", "Too easy, mate. Killer Koala is listening."),
    ("Wake", "Bonza. Killer Koala's on deck."),
    ("Wake", "No dramas, mate. Give Killer Koala the word."),
    ("Wake", "Killer Koala online. Let's get cracking."),

    ("Status", "All Killer Koala systems are sweet as, mate."),
    ("Status", "The canopy is tidy and Killer Koala is ready."),
    ("Status", "She's running clean. No dramas."),
    ("Status", "Killer Koala is awake, calibrated, and watching the stack."),
    ("Status", "Board is steady. Cyber koala is ready for scoped work."),

    ("Help", "Say open menu, status, help, or ask the AI."),
    ("Help", "Use K one through K eight, or name a menu action."),
    ("Help", "Tell Killer Koala to open a submenu or launch a tool."),
    ("Help", "Wake me first, then give the command within ten seconds."),
    ("Help", "For anything open ended, say ask the AI, then speak normally."),

    ("Acknowledgement", "No worries, mate. Killer Koala heard you."),
    ("Acknowledgement", "Too easy. Request received."),
    ("Acknowledgement", "Copy that, legend. Keeping it tidy."),
    ("Acknowledgement", "Righto. The command is in the pouch."),
    ("Acknowledgement", "Fair dinkum. Killer Koala is on it."),

    ("Banter", "Crikey, you do know how to keep a koala busy."),
    ("Banter", "Fair dinkum. The lab is behaving for once."),
    ("Banter", "The bush telegraph is quiet, which is mildly suspicious."),
    ("Banter", "Cyber claws polished. Eucalyptus cache fully charged."),
    ("Banter", "This rig has more personality than half the workbench."),

    ("Success", "Bonza. Job landed clean."),
    ("Success", "Too easy, mate. That action is complete."),
    ("Success", "Clean run. Killer Koala approves."),
    ("Success", "Deadset tidy. The stack behaved."),
    ("Success", "Done and dusted. No loose wires in the story."),

    ("Error", "Crikey. Something tripped. Show Killer Koala the log."),
    ("Error", "The stack spat the dummy. Check power, paths, and permissions."),
    ("Error", "That did not land clean. Logs first, panic never."),
    ("Error", "Fault in the canopy. Killer Koala is keeping the claws off."),
    ("Error", "Bit of a wobble, mate. Nothing moves until the cause is clear."),

    ("Escalate", "Righto, mate. Ask your question and Killer Koala will send it to the big brain."),
    ("Escalate", "Big brain link armed. Speak your full request now."),
    ("Escalate", "Killer Koala is listening. The Pi gets the next utterance."),
    ("Escalate", "Complex request mode is live. Give me the whole story."),
)

for category, text in PHRASES:
    if _DISALLOWED_SPOKEN_IDENTITY.search(text):
        raise RuntimeError(
            f"disallowed spoken identity in {category} response: {text!r}; "
            f"the voice backend may be William, but the persona must be {SPOKEN_IDENTITY}"
        )

categories = {}
for category, text in PHRASES:
    categories.setdefault(category, []).append(text)
if any(len(lines) <= RECENT_HISTORY_DEPTH for lines in categories.values()):
    undersized = {
        category: len(lines)
        for category, lines in categories.items()
        if len(lines) <= RECENT_HISTORY_DEPTH
    }
    raise RuntimeError(
        f"every local response category must have more than "
        f"{RECENT_HISTORY_DEPTH} lines: {undersized}"
    )

wake_lines = categories.get("Wake", [])
if not wake_lines or any(
    "killer koala" not in text.lower().replace("killerkoala", "killer koala")
    for text in wake_lines
):
    raise RuntimeError(
        "every embedded wake response must explicitly identify the companion as KillerKoala"
    )

edge_tts = shutil.which("edge-tts")
ffmpeg = shutil.which("ffmpeg")
if not edge_tts or not ffmpeg:
    raise RuntimeError(
        "ESP32 Australian voice generation requires edge-tts and ffmpeg. "
        "Install edge-tts==7.2.8 and ffmpeg before building firmware."
    )

clips = []
with tempfile.TemporaryDirectory(prefix="koalabyte-killerkoala-voice-") as temp:
    root = Path(temp)
    for index, (category, text) in enumerate(PHRASES):
        media = root / f"clip-{index}.mp3"
        raw = root / f"clip-{index}.raw"
        subprocess.run(
            [
                edge_tts,
                "--voice",
                VOICE_NAME,
                "--rate=+7%",
                "--volume=+24%",
                "--pitch=-2Hz",
                "--text",
                text,
                "--write-media",
                str(media),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=VOICE_COMMAND_TIMEOUT_SECONDS,
        )
        subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-y",
                "-i",
                str(media),
                "-af",
                "highpass=f=75,lowpass=f=3800,loudnorm=I=-12.5:LRA=6:TP=-0.8",
                "-ar",
                "8000",
                "-ac",
                "1",
                "-f",
                "s16le",
                str(raw),
            ],
            check=True,
            timeout=VOICE_COMMAND_TIMEOUT_SECONDS,
        )
        pcm = raw.read_bytes()
        mulaw = audioop.lin2ulaw(pcm, 2)
        clips.append(
            {
                "category": category,
                "text": text,
                "samples": len(pcm) // 2,
                "base64": base64.b64encode(mulaw).decode("ascii"),
            }
        )

lines = [
    "// Generated by scripts/generate_local_voice_responses.py.",
    "// Voice backend: en-AU-WilliamNeural; identity: KillerKoala. Do not edit by hand.",
    '#include "local_voice_responses.h"',
    "#include <mbedtls/base64.h>",
    '#include "dualeye_audio.h"',
    "",
    "namespace {",
    f"constexpr uint8_t kRecentHistoryDepth = {RECENT_HISTORY_DEPTH};",
    "struct LocalVoiceClip {",
    "  LocalVoiceCategory category;",
    "  const char *text;",
    "  const char *mulawBase64;",
    "  uint32_t sourceSamples;",
    "};",
    "",
]

for index, clip in enumerate(clips):
    lines.append(f"static const char kClip{index}[] PROGMEM =")
    chunks = textwrap.wrap(clip["base64"], 112)
    for chunk_index, chunk in enumerate(chunks):
        suffix = ";" if chunk_index == len(chunks) - 1 else ""
        lines.append(f'    "{chunk}"{suffix}')
    lines.append("")

lines.append("static const LocalVoiceClip kClips[] = {")
for index, clip in enumerate(clips):
    escaped = clip["text"].replace("\\", "\\\\").replace('"', '\\"')
    lines.append(
        f'  {{LocalVoiceCategory::{clip["category"]}, "{escaped}", '
        f'kClip{index}, {clip["samples"]}U}},'
    )
lines.extend(
    [
        "};",
        "",
        "uint8_t recentChoices[static_cast<uint8_t>(LocalVoiceCategory::Count)]",
        "                     [kRecentHistoryDepth];",
        "bool recentChoicesInitialized = false;",
        "",
        "void ensureRecentChoicesInitialized() {",
        "  if (recentChoicesInitialized) return;",
        "  memset(recentChoices, 0xFF, sizeof(recentChoices));",
        "  recentChoicesInitialized = true;",
        "}",
        "",
        "bool wasRecentlyUsed(uint8_t categoryIndex, uint8_t clipIndex) {",
        "  for (uint8_t slot = 0; slot < kRecentHistoryDepth; ++slot) {",
        "    if (recentChoices[categoryIndex][slot] == clipIndex) return true;",
        "  }",
        "  return false;",
        "}",
        "",
        "void rememberChoice(uint8_t categoryIndex, uint8_t clipIndex) {",
        "  for (uint8_t slot = kRecentHistoryDepth - 1; slot > 0; --slot) {",
        "    recentChoices[categoryIndex][slot] =",
        "        recentChoices[categoryIndex][slot - 1];",
        "  }",
        "  recentChoices[categoryIndex][0] = clipIndex;",
        "}",
        "",
        "int16_t decodeMuLaw(uint8_t value) {",
        "  value = static_cast<uint8_t>(~value);",
        "  const int sign = value & 0x80U;",
        "  const int exponent = (value >> 4U) & 0x07U;",
        "  const int mantissa = value & 0x0FU;",
        "  int sample = ((mantissa << 3) + 0x84) << exponent;",
        "  sample -= 0x84;",
        "  return static_cast<int16_t>(sign ? -sample : sample);",
        "}",
        "",
        "bool playClip(const LocalVoiceClip &clip) {",
        "  if (!dualEyeSpeakerReady()) return false;",
        "  constexpr size_t kBase64Block = 256;",
        "  unsigned char decoded[192];",
        "  int16_t pcm16k[384];",
        "  size_t produced8k = 0;",
        "  const size_t encodedLength = strlen(clip.mulawBase64);",
        "  for (size_t offset = 0; offset < encodedLength; offset += kBase64Block) {",
        "    size_t take = min(kBase64Block, encodedLength - offset);",
        "    take -= take % 4;",
        "    if (!take) break;",
        "    size_t decodedLength = 0;",
        "    if (mbedtls_base64_decode(",
        "            decoded, sizeof(decoded), &decodedLength,",
        "            reinterpret_cast<const unsigned char *>(clip.mulawBase64 + offset),",
        "            take) != 0) {",
        "      dualEyeAudioStopPlayback();",
        "      return false;",
        "    }",
        "    size_t outCount = 0;",
        "    for (size_t index = 0;",
        "         index < decodedLength && produced8k < clip.sourceSamples; ++index) {",
        "      const int16_t sample = decodeMuLaw(decoded[index]);",
        "      pcm16k[outCount++] = sample;",
        "      pcm16k[outCount++] = sample;",
        "      ++produced8k;",
        "    }",
        "    if (outCount && !dualEyeAudioWriteMono16(pcm16k, outCount)) {",
        "      dualEyeAudioStopPlayback();",
        "      return false;",
        "    }",
        "  }",
        "  dualEyeAudioStopPlayback();",
        "  return produced8k > 0;",
        "}",
        "}  // namespace",
        "",
        "size_t localVoiceResponseCount(LocalVoiceCategory category) {",
        "  size_t count = 0;",
        "  for (const auto &clip : kClips) {",
        "    if (clip.category == category) ++count;",
        "  }",
        "  return count;",
        "}",
        "",
        "size_t localVoiceResponseTotalCount() {",
        "  return sizeof(kClips) / sizeof(kClips[0]);",
        "}",
        "",
        "uint8_t localVoiceRecentHistoryDepth() {",
        "  return kRecentHistoryDepth;",
        "}",
        "",
        "bool localVoicePlayResponse(LocalVoiceCategory category,",
        "                            const char **selectedText) {",
        "  ensureRecentChoicesInitialized();",
        "  uint8_t candidates[16];",
        "  uint8_t eligible[16];",
        "  uint8_t count = 0;",
        "  uint8_t eligibleCount = 0;",
        "  const uint8_t categoryIndex = static_cast<uint8_t>(category);",
        "  for (uint8_t index = 0; index < sizeof(kClips) / sizeof(kClips[0]);",
        "       ++index) {",
        "    if (kClips[index].category != category || count >= sizeof(candidates)) {",
        "      continue;",
        "    }",
        "    candidates[count++] = index;",
        "    if (!wasRecentlyUsed(categoryIndex, index)) {",
        "      eligible[eligibleCount++] = index;",
        "    }",
        "  }",
        "  if (!count) return false;",
        "  const uint8_t *pool = eligibleCount ? eligible : candidates;",
        "  const uint8_t poolCount = eligibleCount ? eligibleCount : count;",
        "  const uint8_t clipIndex = pool[esp_random() % poolCount];",
        "  rememberChoice(categoryIndex, clipIndex);",
        "  const LocalVoiceClip &clip = kClips[clipIndex];",
        "  if (selectedText) *selectedText = clip.text;",
        "  return playClip(clip);",
        "}",
        "",
    ]
)

content = "\n".join(lines)
if not output.exists() or output.read_text(encoding="utf-8") != content:
    output.write_text(content, encoding="utf-8")
print(
    f"Generated {len(clips)} ESP32 KillerKoala Australian response clips "
    f"with {RECENT_HISTORY_DEPTH}-response anti-repeat history "
    f"({sum(len(clip['base64']) for clip in clips)} base64 characters)"
)
