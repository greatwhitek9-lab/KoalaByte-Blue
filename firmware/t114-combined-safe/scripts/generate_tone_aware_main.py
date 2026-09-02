#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"T114 tone source generation expected exactly one {label} anchor, found {count}"
        )
    return text.replace(old, new, 1)


def generate(source: Path, output: Path) -> None:
    text = source.read_text(encoding="utf-8")

    text = replace_once(
        text,
        'static char koalagotchi_mood[48] = "calm";\nstatic uint8_t koalagotchi_frame;\n',
        'static char koalagotchi_mood[48] = "calm";\n'
        'static char speech_tone[24] = "neutral";\n'
        'static char speech_subject[28] = "conversation";\n'
        'static char speech_motion[28] = "natural";\n'
        'static uint8_t speech_intensity = 60;\n'
        'static uint8_t koalagotchi_frame;\n',
        "speech expression state",
    )

    text = replace_once(
        text,
        '''static uint8_t next_speaking_mouth_pose(uint16_t *hold_ms)
{
    static const uint8_t speaking_sequence[] = {
        KOALA_FRAME_HAPPY, KOALA_FRAME_BITE, KOALA_FRAME_HAPPY,
        KOALA_FRAME_SMILE, KOALA_FRAME_HAPPY, KOALA_FRAME_SIDEWAYS_GRIN,
        KOALA_FRAME_HAPPY, KOALA_FRAME_BITE, KOALA_FRAME_SMILE,
        KOALA_FRAME_HAPPY,
    };
    static const uint16_t speaking_holds_ms[] = {
        75, 90, 60, 120, 70, 85, 55, 95, 110, 65,
    };
    uint8_t index = speech_pose_index % ARRAY_SIZE(speaking_sequence);

    *hold_ms = speaking_holds_ms[index];
    speech_pose_index = (uint8_t)((speech_pose_index + 1U) %
                                  ARRAY_SIZE(speaking_sequence));
    return speaking_sequence[index];
}
''',
        '''static uint8_t next_speaking_mouth_pose(uint16_t *hold_ms)
{
    static const uint8_t happy_sequence[] = {
        KOALA_FRAME_HAPPY, KOALA_FRAME_SMILE, KOALA_FRAME_HAPPY,
        KOALA_FRAME_SIDEWAYS_GRIN, KOALA_FRAME_HAPPY, KOALA_FRAME_SMILE,
        KOALA_FRAME_HAPPY, KOALA_FRAME_BITE,
    };
    static const uint8_t focused_sequence[] = {
        KOALA_FRAME_BITE, KOALA_FRAME_HAPPY, KOALA_FRAME_BITE,
        KOALA_FRAME_SMILE, KOALA_FRAME_BITE, KOALA_FRAME_SIDEWAYS_GRIN,
        KOALA_FRAME_BITE, KOALA_FRAME_HAPPY,
    };
    static const uint8_t angry_sequence[] = {
        KOALA_FRAME_SNARL, KOALA_FRAME_BITE, KOALA_FRAME_SNARL,
        KOALA_FRAME_SIDEWAYS_GRIN, KOALA_FRAME_SNARL, KOALA_FRAME_BITE,
        KOALA_FRAME_SNARL, KOALA_FRAME_SNARL,
    };
    static const uint8_t cheeky_sequence[] = {
        KOALA_FRAME_SIDEWAYS_GRIN, KOALA_FRAME_SMILE,
        KOALA_FRAME_SIDEWAYS_GRIN, KOALA_FRAME_HAPPY,
        KOALA_FRAME_SIDEWAYS_GRIN, KOALA_FRAME_BITE,
        KOALA_FRAME_HAPPY, KOALA_FRAME_SIDEWAYS_GRIN,
    };
    static const uint16_t natural_holds_ms[] = {
        78, 92, 62, 118, 72, 86, 58, 98,
    };
    static const uint16_t hard_holds_ms[] = {
        54, 70, 48, 80, 52, 66, 46, 72,
    };
    const uint8_t *sequence = focused_sequence;
    size_t sequence_len = ARRAY_SIZE(focused_sequence);
    const uint16_t *holds = natural_holds_ms;
    size_t hold_len = ARRAY_SIZE(natural_holds_ms);

    if (mouth_expression == KOALA_MOUTH_SMILE) {
        sequence = happy_sequence;
        sequence_len = ARRAY_SIZE(happy_sequence);
    } else if (mouth_expression == KOALA_MOUTH_SNARL) {
        sequence = angry_sequence;
        sequence_len = ARRAY_SIZE(angry_sequence);
        holds = hard_holds_ms;
        hold_len = ARRAY_SIZE(hard_holds_ms);
    } else if (mouth_expression == KOALA_MOUTH_SIDEWAYS_GRIN) {
        sequence = cheeky_sequence;
        sequence_len = ARRAY_SIZE(cheeky_sequence);
    }

    uint8_t index = speech_pose_index % sequence_len;
    *hold_ms = holds[index % hold_len];
    speech_pose_index = (uint8_t)((speech_pose_index + 1U) % sequence_len);
    return sequence[index];
}
''',
        "tone-specific speaking sequence",
    )

    text = replace_once(
        text,
        '''static void emit_mouth_status(void)
{
    printk("{\\"type\\":\\"heltec_mouth_status\\",\\"device\\":\\"heltec-t114\\",\\"source\\":\\"%s\\",\\"transport\\":\\"usb-cdc\\",\\"state\\":\\"%s\\",\\"message\\":\\"%s\\",\\"face_enabled\\":%s,\\"display_ready\\":%s,\\"health\\":%d,\\"mood\\":\\"%s\\",\\"expression\\":\\"%s\\",\\"frame_index\\":%u,\\"from_frame\\":%u,\\"to_frame\\":%u,\\"blend\\":%u,\\"speaking\\":%s,\\"fw\\":\\"%s\\",\\"uptime_ms\\":%lld}\\n",
           KOALA_DEVICE, current_state, current_message, face_enabled ? "true" : "false",
           loading_display_ready() ? "true" : "false", koalagotchi_health,
           koalagotchi_mood, mouth_expression_name(mouth_expression),
           current_mouth_frame(), mouth_from_frame, mouth_to_frame,
           mouth_blend_amount, speaking_active ? "true" : "false", KOALA_FW,
           (long long)(k_uptime_get() - boot_ms));
}
''',
        '''static void emit_mouth_status(void)
{
    printk("{\\"type\\":\\"heltec_mouth_status\\",\\"device\\":\\"heltec-t114\\",\\"source\\":\\"%s\\",\\"transport\\":\\"usb-cdc\\",\\"state\\":\\"%s\\",\\"message\\":\\"%s\\",\\"face_enabled\\":%s,\\"display_ready\\":%s,\\"health\\":%d,\\"mood\\":\\"%s\\",\\"tone\\":\\"%s\\",\\"subject\\":\\"%s\\",\\"speech_motion\\":\\"%s\\",\\"intensity\\":%u,\\"expression\\":\\"%s\\",\\"frame_index\\":%u,\\"from_frame\\":%u,\\"to_frame\\":%u,\\"blend\\":%u,\\"speaking\\":%s,\\"fw\\":\\"%s\\",\\"uptime_ms\\":%lld}\\n",
           KOALA_DEVICE, current_state, current_message, face_enabled ? "true" : "false",
           loading_display_ready() ? "true" : "false", koalagotchi_health,
           koalagotchi_mood, speech_tone, speech_subject, speech_motion,
           speech_intensity, mouth_expression_name(mouth_expression),
           current_mouth_frame(), mouth_from_frame, mouth_to_frame,
           mouth_blend_amount, speaking_active ? "true" : "false", KOALA_FW,
           (long long)(k_uptime_get() - boot_ms));
}
''',
        "mouth status expression metadata",
    )

    text = replace_once(
        text,
        '''    face_enabled = strstr(line, "\\"enabled\\":false") == NULL;
    face_until_ms = now + duration_ms;

    if (strstr(line, "\\"display_mode\\":\\"koalagotchi_action\\"")) {
''',
        '''    face_enabled = strstr(line, "\\"enabled\\":false") == NULL;
    face_until_ms = now + duration_ms;
    if (extract_json_string(line, "tone", value, sizeof(value))) {
        copy_safe(speech_tone, sizeof(speech_tone), value, "neutral");
    }
    if (extract_json_string(line, "subject", value, sizeof(value))) {
        copy_safe(speech_subject, sizeof(speech_subject), value, "conversation");
    }
    if (extract_json_string(line, "speech_motion", value, sizeof(value))) {
        copy_safe(speech_motion, sizeof(speech_motion), value, "natural");
    }
    speech_intensity = (uint8_t)CLAMP(extract_json_int(line, "intensity", speech_intensity), 20, 100);

    if (strstr(line, "\\"display_mode\\":\\"koalagotchi_action\\"")) {
''',
        "face metadata parsing",
    )

    text = replace_once(
        text,
        '''    if (strstr(line, "\\"display_mode\\":\\"koalagotchi_action\\"")) {
        copy_safe(current_state, sizeof(current_state),
                  "koalagotchi_action", "koalagotchi_action");
        koalagotchi_frame =
            (uint8_t)extract_json_int(line, "frame_index", 0);
    } else if (strstr(line, "\\"display_mode\\":\\"jungle_loading_banner\\"")) {
        copy_safe(current_state, sizeof(current_state), "loading", "loading");
    }
''',
        '''    if (strstr(line, "\\"display_mode\\":\\"koalagotchi_action\\"")) {
        char action_title[sizeof(current_message)] = "";
        copy_safe(current_state, sizeof(current_state),
                  "koalagotchi_action", "koalagotchi_action");
        if (!current_message[0] &&
            extract_json_string(line, "action_title", action_title,
                                sizeof(action_title))) {
            copy_safe(current_message, sizeof(current_message), action_title,
                      "EXECUTING");
        }
        koalagotchi_frame =
            (uint8_t)extract_json_int(line, "frame_index", 0);
        koala_centered_set_action_progress(
            extract_json_int(line, "progress", -1));
    } else if (strstr(line, "\\"display_mode\\":\\"jungle_loading_banner\\"")) {
        koala_centered_set_action_progress(-1);
        copy_safe(current_state, sizeof(current_state), "loading", "loading");
    }
''',
        "Koalagotchi action metadata",
    )

    text = replace_once(
        text,
        '''    speaking_active = strcmp(current_state, "speaking") == 0;
    mouth_expression = expression_for_face_state(current_state);
    reset_mouth_animation(now);
''',
        '''    speaking_active = strcmp(current_state, "speaking") == 0;
    char explicit_expression[32] = "";
    (void)extract_json_string(line, "mouth_expression", explicit_expression,
                              sizeof(explicit_expression));
    mouth_expression = explicit_expression[0]
        ? expression_from_koalagotchi(explicit_expression, speech_tone,
                                      koalagotchi_health)
        : expression_for_face_state(current_state);
    reset_mouth_animation(now);
''',
        "face mouth expression selection",
    )

    text = replace_once(
        text,
        '''    mouth_expression = expression_from_koalagotchi(
        expression, koalagotchi_mood, koalagotchi_health);
    face_enabled = true;
''',
        '''    mouth_expression = expression_from_koalagotchi(
        expression, koalagotchi_mood, koalagotchi_health);
    koala_centered_set_status(koalagotchi_health, koalagotchi_mood,
                              mouth_expression_name(mouth_expression));
    face_enabled = true;
''',
        "Koalagotchi HUD status wiring",
    )

    text = replace_once(
        text,
        '''static void handle_speech_command(const char *line)
{
    char message[sizeof(current_message)] = "";
    bool active = json_true(line, "active");
    int64_t now = k_uptime_get();

    (void)extract_json_string(line, "message", message, sizeof(message));
    speaking_active = active;
    face_enabled = true;
    if (active) {
        copy_safe(current_state, sizeof(current_state), "speaking", "speaking");
        copy_safe(current_message, sizeof(current_message), message, "speaking");
        mouth_expression = KOALA_MOUTH_BITE;
        face_until_ms = now + KOALA_SPEECH_FAILSAFE_MS;
    } else {
        copy_safe(current_state, sizeof(current_state), "idle", "idle");
        copy_safe(current_message, sizeof(current_message), "", "");
        mouth_expression = expression_from_koalagotchi(
            NULL, koalagotchi_mood, koalagotchi_health);
        face_until_ms = 0;
    }
    reset_mouth_animation(now);
    render_current_face();
    printk("{\\"type\\":\\"killerkoala_speech_ack\\",\\"device\\":\\"heltec-t114\\",\\"active\\":%s,\\"animation\\":\\"smooth_rgb565_interpolation\\",\\"from_frame\\":%u,\\"to_frame\\":%u}\\n",
           speaking_active ? "true" : "false", mouth_from_frame,
           mouth_to_frame);
}
''',
        '''static void handle_speech_command(const char *line)
{
    char message[sizeof(current_message)] = "";
    char tone[sizeof(speech_tone)] = "neutral";
    char subject[sizeof(speech_subject)] = "conversation";
    char motion[sizeof(speech_motion)] = "natural";
    char expression[32] = "";
    bool active = json_true(line, "active");
    int64_t now = k_uptime_get();

    (void)extract_json_string(line, "message", message, sizeof(message));
    (void)extract_json_string(line, "tone", tone, sizeof(tone));
    (void)extract_json_string(line, "subject", subject, sizeof(subject));
    (void)extract_json_string(line, "speech_motion", motion, sizeof(motion));
    (void)extract_json_string(line, "mouth_expression", expression,
                              sizeof(expression));
    copy_safe(speech_tone, sizeof(speech_tone), tone, "neutral");
    copy_safe(speech_subject, sizeof(speech_subject), subject, "conversation");
    copy_safe(speech_motion, sizeof(speech_motion), motion, "natural");
    speech_intensity = (uint8_t)CLAMP(extract_json_int(line, "intensity", 60), 20, 100);

    speaking_active = active;
    face_enabled = true;
    if (active) {
        copy_safe(current_state, sizeof(current_state), "speaking", "speaking");
        copy_safe(current_message, sizeof(current_message), message, "speaking");
        mouth_expression = expression_from_koalagotchi(
            expression, speech_tone, koalagotchi_health);
        face_until_ms = now + KOALA_SPEECH_FAILSAFE_MS;
    } else {
        copy_safe(current_state, sizeof(current_state), "idle", "idle");
        copy_safe(current_message, sizeof(current_message), "", "");
        mouth_expression = expression_from_koalagotchi(
            NULL, koalagotchi_mood, koalagotchi_health);
        face_until_ms = 0;
    }
    reset_mouth_animation(now);
    render_current_face();
    printk("{\\"type\\":\\"killerkoala_speech_ack\\",\\"device\\":\\"heltec-t114\\",\\"active\\":%s,\\"tone\\":\\"%s\\",\\"subject\\":\\"%s\\",\\"expression\\":\\"%s\\",\\"animation\\":\\"smooth_tone_aware_rgb565_interpolation\\",\\"from_frame\\":%u,\\"to_frame\\":%u}\\n",
           speaking_active ? "true" : "false", speech_tone, speech_subject,
           mouth_expression_name(mouth_expression), mouth_from_frame,
           mouth_to_frame);
}
''',
        "tone-aware speech handler",
    )

    banner = (
        "/* GENERATED FILE - source main.c plus tone-aware KillerKoala speech mouth. */\n"
        "/* Do not edit generated output; edit main.c or this generator. */\n\n"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(banner + text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    generate(Path(args.source), Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
