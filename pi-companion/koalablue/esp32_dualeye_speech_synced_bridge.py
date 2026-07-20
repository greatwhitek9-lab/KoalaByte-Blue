from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

from .ble_event_log import BleEventDeduper, BleEventLog, normalize_ble_event
from .ble_role_coordinator import (
    elect_ble_roles,
    esp32_role_command,
    write_role_status,
)
from .esp32_dualeye_latched_koalagotchi_bridge import (
    ESP32DualEyeVoiceBridge as _LatchedKoalagotchiBridge,
    ESP32DualEyeVoiceEvent,
    default_esp32_port,
)
from .killerkoala_expression import (
    KillerKoalaExpression,
    classify_response_expression,
    expression_for_local_category,
)
from .killerkoala_face_bridge import _resolve_ports, _serial_write


ERROR_DIGS = (
    "Crikey, mate. Even the gum leaves saw that one coming.",
    "Nice work, legend. You found the one branch marked do not sit here.",
    "Bonza move. The machine is judging you, and frankly so am I.",
    "You beauty. Another perfectly avoidable error for the collection.",
    "Mate, the button was innocent until you got involved.",
    "That went about as smoothly as a koala on roller skates.",
    "Outstanding. You turned a simple job into interpretive debugging.",
    "Righto, champion. Next time try the option that is not on fire.",
    "The system survived your contribution. Barely.",
    "Fair dinkum, that error had your fingerprints all over it.",
    "You found the fault path without even reading the map. Impressive.",
    "Good effort, mate. Wrong effort, but definitely effort.",
)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "active"}


class ESP32DualEyeVoiceBridge(_LatchedKoalagotchiBridge):
    """Local-vocabulary-first speech, BLE failover, and error coordinator.

    The Waveshare owns wake/basic vocabulary and embedded audio. The Pi mirrors
    local speech to the T114 mouth, routes open requests to TinyLlama, elects the
    preferred Pi-or-ESP32 Heltec BLE node, and owns the universal timed error
    lifecycle across both displays and the Pi Australian voice.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._active_expression: Optional[KillerKoalaExpression] = None
        self._ble_role = ""
        self._last_ble_role_check = 0.0
        self._ble_role_interval = max(
            10.0,
            float(os.getenv("KOALABYTE_BLE_ROLE_CHECK_SECONDS", "30")),
        )
        self._ble_log = BleEventLog("logs/ble_nodes")
        self._ble_deduper = BleEventDeduper()

        self._error_sequence_seconds = max(
            3.0,
            float(os.getenv("KILLERKOALA_ERROR_SEQUENCE_SECONDS", "6.5")),
        )
        self._error_alarm_until = 0.0
        self._pending_error_dig = ""
        self._error_dig_history: list[str] = []
        self._error_sequence_path = (
            self.failure_state_path.parent / "killerkoala_error_sequence.json"
        )

    def open(self) -> None:
        super().open()
        self._refresh_ble_role(force=True)

    def _refresh_ble_role(self, *, force: bool = False) -> None:
        now = time.time()
        if not force and now - self._last_ble_role_check < self._ble_role_interval:
            return
        self._last_ble_role_check = now
        election = elect_ble_roles(requested_by="dualeye_voice_bridge")
        write_role_status(election)
        if not force and election.esp32_role == self._ble_role:
            return
        self._ble_role = election.esp32_role
        try:
            self._serial_write_json(esp32_role_command(election))
        except Exception:
            pass

    def read_once(self) -> Optional[ESP32DualEyeVoiceEvent]:
        self._refresh_ble_role()
        self._service_error_sequence()
        event = super().read_once()
        self._service_error_sequence()
        return event

    def _select_error_dig(self, action: str, message: str) -> str:
        recent = set(self._error_dig_history[-6:])
        seed = abs(hash(f"{action}|{message}|{int(time.time() // 3)}"))
        for offset in range(len(ERROR_DIGS)):
            candidate = ERROR_DIGS[(seed + offset) % len(ERROR_DIGS)]
            if candidate not in recent:
                self._error_dig_history.append(candidate)
                self._error_dig_history = self._error_dig_history[-8:]
                return candidate
        candidate = ERROR_DIGS[seed % len(ERROR_DIGS)]
        self._error_dig_history.append(candidate)
        return candidate

    def _write_error_sequence_status(
        self,
        *,
        status: str,
        action: str = "",
        message: str = "",
        dig: str = "",
    ) -> None:
        payload = {
            "status": status,
            "action": " ".join(str(action).split())[:96],
            "message": " ".join(str(message).split())[:160],
            "dig": " ".join(str(dig).split())[:180],
            "alarm_until": self._error_alarm_until,
            "error_sequence_seconds": self._error_sequence_seconds,
            "dualeye": "alert_eyes_with_flashing_cyber_purple_green_background",
            "heltec": "alarmed_koalagotchi_with_flashing_cyber_purple_green_background",
            "completion": "heltec_mouth_then_pi_error_dig",
            "updated_at": time.time(),
        }
        self._error_sequence_path.parent.mkdir(parents=True, exist_ok=True)
        self._error_sequence_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _start_error_sequence(self, action: str, message: str) -> None:
        resolved_action = " ".join(str(action or "KillerKoala action").split())
        resolved_message = " ".join(str(message or "system error").split())
        self._active_error = True
        self._persistent_koalagotchi_mode = False
        self._error_alarm_until = time.time() + self._error_sequence_seconds
        self._pending_error_dig = self._select_error_dig(
            resolved_action,
            resolved_message,
        )
        self._active_expression = classify_response_expression(
            f"error alarm {resolved_message}",
            status="error",
            event="error_alarm_sequence",
            context={"action": resolved_action},
        )
        try:
            self._emit_latched_state("alarmed", resolved_message)
        finally:
            self._active_expression = None
        self._save_failure_state(
            status="alarmed",
            action=resolved_action,
            message=resolved_message,
        )
        self._write_error_sequence_status(
            status="alarm_active",
            action=resolved_action,
            message=resolved_message,
            dig=self._pending_error_dig,
        )

    def _service_error_sequence(self) -> None:
        if not self._active_error or self._error_alarm_until <= 0:
            return
        if time.time() < self._error_alarm_until:
            return

        dig = self._pending_error_dig or self._select_error_dig("error", "")
        self._active_error = False
        self._error_alarm_until = 0.0
        self._pending_error_dig = ""
        self._emit_latched_state("error_clear", "alarm sequence complete")
        self._save_failure_state(status="error_sequence_complete", message=dig)
        self._write_error_sequence_status(status="speaking_dig", dig=dig)

        # The explicit clear returns the T114 to its normal mouth before speech.
        # Pi-owned William TTS then animates that mouth and the DualEye together.
        self._play_response(dig, "pi-error-dig")
        self._fanout_face("idle", "", duration_ms=1000)
        self._write_error_sequence_status(status="complete", dig=dig)

    def _show_post_execution_state(
        self,
        *,
        status: str,
        action: str,
        message: str,
        persistent_command: bool = False,
        result_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        data = result_data or {}
        if self._is_error_result(status, data):
            self._start_error_sequence(action, message)
            return "alarmed"
        return super()._show_post_execution_state(
            status=status,
            action=action,
            message=message,
            persistent_command=persistent_command,
            result_data=data,
        )

    def _expression(
        self,
        state: str,
        message: str,
        *,
        channel: str = "",
    ) -> KillerKoalaExpression:
        if self._active_expression is not None:
            return self._active_expression
        return classify_response_expression(
            message,
            status=state,
            event=channel or state,
            context={"display_state": state, "speech_channel": channel},
        )

    @staticmethod
    def _merge_expression(
        payload: Dict[str, Any], expression: KillerKoalaExpression
    ) -> Dict[str, Any]:
        payload.update(expression.to_payload())
        payload["expression_source"] = "pi_tone_subject_classifier"
        payload["eyes_visible"] = True
        payload["mouth_visible"] = True
        payload["speech_animation"] = True
        payload["alarm_background"] = expression.tone == "error"
        payload["alarm_colors"] = ["#A54BFF", "#32FF71"]
        payload["alarm_flash_ms"] = 180
        return payload

    @staticmethod
    def _fit_t114_line(payload: Dict[str, Any]) -> Dict[str, Any]:
        fitted = dict(payload)
        for optional_key in ("message", "subject", "speech_motion"):
            if len(json.dumps(fitted, separators=(",", ":"))) < 255:
                return fitted
            if optional_key in fitted:
                fitted[optional_key] = ""
        if len(json.dumps(fitted, separators=(",", ":"))) >= 255:
            fitted.pop("message", None)
            fitted.pop("subject", None)
            fitted.pop("speech_motion", None)
        return fitted

    @classmethod
    def _compact_heltec_face(
        cls,
        state: str,
        message: str,
        duration_ms: int,
        expression: KillerKoalaExpression,
    ) -> Dict[str, Any]:
        return cls._fit_t114_line(
            {
                "type": "killerkoala_face",
                "state": str(state or "speaking")[:18],
                "message": " ".join(str(message).split())[:18],
                "duration_ms": max(250, min(int(duration_ms), 30000)),
                "tone": expression.tone[:14],
                "subject": expression.subject[:16],
                "mouth_expression": expression.mouth_expression[:16],
                "speech_motion": expression.speech_motion[:18],
                "intensity": expression.intensity,
            }
        )

    @classmethod
    def _compact_heltec_speech(
        cls,
        active: bool,
        message: str,
        expression: KillerKoalaExpression,
    ) -> Dict[str, Any]:
        return cls._fit_t114_line(
            {
                "type": "killerkoala_speech",
                "active": bool(active),
                "message": " ".join(str(message).split())[:28] if active else "",
                "tone": expression.tone[:14],
                "subject": expression.subject[:16],
                "mouth_expression": expression.mouth_expression[:16],
                "speech_motion": expression.speech_motion[:18],
                "intensity": expression.intensity,
            }
        )

    def _write_heltec(self, payload: Dict[str, Any]) -> None:
        try:
            _, heltec_port = _resolve_ports()
            _serial_write(heltec_port, self.baud, payload)
        except Exception:
            pass

    def _fanout_face(
        self, state: str, message: str = "", duration_ms: int = 5000
    ) -> None:
        expression = self._expression(state, message)
        esp32_payload = self._merge_expression(
            {
                "type": "killerkoala_face",
                "enabled": True,
                "state": state,
                "message": " ".join(str(message).split())[:68],
                "duration_ms": duration_ms,
                "left_eye": expression.left_eye,
                "right_eye": expression.right_eye,
                "brightness": expression.intensity,
                "source": "pi-companion",
                "transport": "pi-fanout",
            },
            expression,
        )
        self._write_json(esp32_payload)
        self._write_heltec(
            self._compact_heltec_face(state, message, duration_ms, expression)
        )

    def _heltec_speech(
        self, active: bool, message: str = "", channel: str = "pi-ai"
    ) -> None:
        expression = self._expression(
            "speaking" if active else "idle", message, channel=channel
        )
        self._write_heltec(
            self._compact_heltec_speech(active, message, expression)
        )

    def _play_response(self, text: str, channel: str) -> None:
        # Exact menu errors are spoken only after the alarm as a KillerKoala dig.
        if self._active_error and channel == "pi-execution" and self._pending_error_dig:
            return
        self._active_expression = classify_response_expression(
            text,
            status="speaking",
            event=channel,
            context={"speaker": "tinyllama_or_pi", "voice": "en-AU-WilliamNeural"},
        )
        try:
            super()._play_response(text, channel)
        finally:
            self._active_expression = None

    def _route_phrase(self, event: ESP32DualEyeVoiceEvent) -> Dict[str, Any]:
        routed = super()._route_phrase(event)
        result = routed.get("result", {}) if isinstance(routed, dict) else {}
        if isinstance(result, dict):
            message = str(
                result.get("companion_line")
                or result.get("message")
                or result.get("error")
                or ""
            )
            status = str(result.get("status") or "")
            expression = classify_response_expression(
                message,
                status=status,
                event="voice_result",
                context={"request_source": event.source},
            )
            routed["speech_expression"] = expression.to_payload()
        return routed

    def _record_esp32_ble_event(self, payload: Dict[str, Any]) -> None:
        normalized_payload = dict(payload)
        normalized_payload["type"] = "ble_adv_seen"
        normalized_payload.setdefault("source", "esp32-s3-dualeye")
        normalized_payload.setdefault("role", self._ble_role or "standby")
        event = normalize_ble_event(
            normalized_payload,
            default_source="esp32-s3-dualeye",
        )
        if self._ble_deduper.should_emit(event):
            self._ble_log.append(event)

    def handle_payload(
        self, payload: Dict[str, Any]
    ) -> Optional[ESP32DualEyeVoiceEvent]:
        payload_type = str(payload.get("type") or "").strip().lower()
        payload_status = str(payload.get("status") or "").strip().lower()
        message = str(
            payload.get("reason")
            or payload.get("message")
            or payload.get("error")
            or payload_type
        )

        if payload_type in {
            "error_clear",
            "killerkoala_error_clear",
            "koalagotchi_error_clear",
        } or payload_status in {"cleared", "resolved", "recovered"}:
            self._active_error = False
            self._error_alarm_until = 0.0
            self._pending_error_dig = ""
            return super().handle_payload(payload)

        if payload_type in {"ble_seen", "ble_adv_seen"}:
            self._record_esp32_ble_event(payload)
            return None
        if payload_type == "ble_role_status":
            role_status = {
                "type": "ble_role_status",
                "reported_role": payload.get("role"),
                "ready": payload.get("ready"),
                "quarantined": payload.get("quarantined"),
                "reason": payload.get("reason"),
                "updated_at": time.time(),
            }
            path = self._ble_log.log_dir / "esp32_ble_role_status.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(role_status, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            if _as_bool(payload.get("quarantined")) or (
                _as_bool(payload.get("requested"))
                and not _as_bool(payload.get("ready"))
                and "insufficient_heap" not in message
            ):
                self._start_error_sequence("ESP32 BLE fallback", message)
            return None

        is_error = (
            payload_type in {
                "display_fault",
                "audio_fault",
                "system_fault",
                "node_error",
                "usb_error",
                "error",
            }
            or payload_type.endswith("_error")
            or any(token in payload_status for token in ("error", "fault", "exception"))
        )
        if is_error:
            self._start_error_sequence(
                str(payload.get("action") or payload_type or "system error"),
                message,
            )
            return None

        if payload_type == "local_speech_state":
            active = _as_bool(payload.get("active"))
            category = str(payload.get("category") or "").strip().lower()
            local_message = str(
                payload.get("message")
                or category
                or "KillerKoala local response"
            ).strip()
            expression = expression_for_local_category(category, local_message)
            self._write_heltec(
                self._compact_heltec_speech(active, local_message, expression)
            )
            return None
        return super().handle_payload(payload)


__all__ = [
    "ESP32DualEyeVoiceBridge",
    "ESP32DualEyeVoiceEvent",
    "default_esp32_port",
]
