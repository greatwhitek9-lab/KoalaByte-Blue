from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional

from .esp32_dualeye_local_first_bridge import (
    ESP32DualEyeVoiceBridge as _LocalFirstBridge,
    ESP32DualEyeVoiceEvent,
    default_esp32_port,
)
from .killerkoala_face_bridge import KOALAGOTCHI_DISPLAY_COMMANDS
from .killerkoala_voice_control import (
    ParsedVoiceCommand,
    VoiceMenuAction,
    execute_module,
    parse_voice_command,
)

_MENU_NAVIGATION_IDS = {
    "k1_main_menu",
    "k2_back",
    "k3_select",
    "k4_forward",
    "k5_up",
    "k6_down",
}
_FAILURE_STATUS_TOKENS = ("FAILED", "BLOCKED", "SKIPPED")
_ERROR_STATUS_TOKENS = ("ERROR", "FAULT", "EXCEPTION")


class ESP32DualEyeVoiceBridge(_LocalFirstBridge):
    """Local-first bridge with a transactional Koalagotchi display lifecycle.

    Action display remains latched until execution returns and the XP state has
    been written. Explicit Koalagotchi display actions remain open until a menu
    navigation/exit event. Faults remain alarmed until an explicit clear event.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.failure_state_path = Path(
            os.getenv(
                "KOALABYTE_KOALAGOTCHI_FAILURE_STATE",
                str(self.xp_path.parent / "koalagotchi_failure_state.json"),
            )
        )
        self.angry_threshold = max(
            2, int(os.getenv("KOALABYTE_KOALAGOTCHI_ANGRY_THRESHOLD", "3"))
        )
        self._failure_streak = self._load_failure_streak()
        self._persistent_koalagotchi_mode = False
        self._active_error = False

    def _load_failure_streak(self) -> int:
        try:
            payload = json.loads(self.failure_state_path.read_text(encoding="utf-8"))
            return max(0, int(payload.get("consecutive_failures", 0)))
        except Exception:
            return 0

    def _save_failure_state(
        self,
        *,
        status: str,
        action: str = "",
        message: str = "",
    ) -> None:
        payload = {
            "consecutive_failures": self._failure_streak,
            "angry_threshold": self.angry_threshold,
            "status": status,
            "action": " ".join(str(action).split())[:96],
            "message": " ".join(str(message).split())[:160],
            "active_error": self._active_error,
            "persistent_koalagotchi_mode": self._persistent_koalagotchi_mode,
            "updated_at": time.time(),
        }
        self.failure_state_path.parent.mkdir(parents=True, exist_ok=True)
        self.failure_state_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )

    def _record_success(self, action: str, message: str = "") -> None:
        self._failure_streak = 0
        self._save_failure_state(status="success", action=action, message=message)

    def _record_failed_attempt(self, action: str, message: str) -> str:
        self._failure_streak += 1
        state = (
            "angry"
            if self._failure_streak >= self.angry_threshold
            else "disappointed"
        )
        self._save_failure_state(status=state, action=action, message=message)
        return state

    def _emit_latched_state(self, state: str, message: str = "") -> None:
        # The T114 lifecycle wrapper ignores the legacy 30-second timeout for
        # these states and waits for an explicit completion/clear transition.
        self._fanout_face(state, message, duration_ms=30000)

    def clear_koalagotchi_error(self, message: str = "error cleared") -> None:
        self._active_error = False
        self._emit_latched_state("error_clear", message)
        self._save_failure_state(status="error_cleared", message=message)

    def exit_koalagotchi_mode(self, message: str = "Koalagotchi mode closed") -> None:
        self._persistent_koalagotchi_mode = False
        self._emit_latched_state("koalagotchi_exit", message)
        self._save_failure_state(status="mode_closed", message=message)

    @staticmethod
    def _status_and_message(result_data: Dict[str, Any], label: str) -> tuple[str, str]:
        status = str(result_data.get("status") or "error")
        message = str(
            result_data.get("companion_line")
            or result_data.get("message")
            or result_data.get("error")
            or (f"{label} complete" if status == "success" else f"{label} failed")
        )
        return status, message

    @staticmethod
    def _is_error_result(status: str, result_data: Dict[str, Any]) -> bool:
        upper = status.upper()
        return bool(result_data.get("error")) or any(
            token in upper for token in _ERROR_STATUS_TOKENS
        )

    @staticmethod
    def _is_failed_result(status: str) -> bool:
        upper = status.upper()
        return any(token in upper for token in _FAILURE_STATUS_TOKENS)

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
        if status == "success":
            self._active_error = False
            self._record_success(action, message)
            if persistent_command:
                self._persistent_koalagotchi_mode = True
                self._emit_latched_state("koalagotchi_mode", action or "KOALAGOTCHI")
                return "koalagotchi_mode"
            self._persistent_koalagotchi_mode = False
            self._emit_latched_state(
                "action_complete", f"{action} complete; XP state logged"
            )
            return "action_complete"

        if self._is_error_result(status, data):
            self._active_error = True
            self._emit_latched_state("alarmed", message or f"{action} error")
            self._save_failure_state(status="alarmed", action=action, message=message)
            return "alarmed"

        state = self._record_failed_attempt(action, message)
        self._emit_latched_state(state, message or f"{action} failed")
        return state

    def _execute_exact_with_xp(
        self,
        event: ESP32DualEyeVoiceEvent,
        command_id: str,
        label: str,
        group: str,
        menu_name: str,
    ) -> Dict[str, Any]:
        phrase = event.phrase.strip() or f"killerkoala launch {label}"
        parsed = ParsedVoiceCommand(
            raw_phrase=phrase,
            normalized_phrase=" ".join(phrase.lower().split()),
            wake_word_detected=True,
            module_key=f"menu:{command_id}",
            menu_action=VoiceMenuAction(
                command=command_id,
                label=label,
                group=group,
                aliases=[label, command_id],
            ),
        )

        self._persistent_koalagotchi_mode = False
        self._emit_latched_state("action", label)
        result = execute_module(
            parsed,
            output_dir=self.output_dir,
            xp_path=self.xp_path,
        )
        result_data = asdict(result)
        status, message = self._status_and_message(result_data, label)
        persistent_command = command_id in KOALAGOTCHI_DISPLAY_COMMANDS
        display_state = self._show_post_execution_state(
            status=status,
            action=label,
            message=message,
            persistent_command=persistent_command,
            result_data=result_data,
        )

        result_payload = {
            "type": "pi_execution_result",
            "request_id": event.request_id,
            "status": status,
            "message": message,
            "action": label,
            "voice_request": True,
            "command_id": command_id,
            "menu_name": menu_name,
            "xp_state_logged": True,
            "xp_before": result_data.get("xp_before"),
            "xp_after": result_data.get("xp_after"),
            "xp_reward": result_data.get("xp_reward"),
            "failure_streak": self._failure_streak,
            "koalagotchi_display_state": display_state,
            "persistent_koalagotchi_mode": self._persistent_koalagotchi_mode,
            "result": result_data,
        }
        self._write_json(result_payload)
        self._play_response(message, "pi-execution")
        return {"event": asdict(event), "result": result_data}

    def _route_exact_catalog_command(
        self, event: ESP32DualEyeVoiceEvent
    ) -> Optional[Dict[str, Any]]:
        command_id = str(event.payload.get("command_id") or "").strip()
        if not command_id:
            return None

        label = str(event.payload.get("menu_label") or command_id).strip()
        group = str(event.payload.get("menu_group") or "System / Companion").strip()
        menu_name = str(event.payload.get("menu_name") or "main").strip()

        if command_id in _MENU_NAVIGATION_IDS or command_id.startswith("submenu:"):
            if self._persistent_koalagotchi_mode:
                self.exit_koalagotchi_mode("menu navigation requested")
            return super()._route_exact_catalog_command(event)

        return self._execute_exact_with_xp(
            event, command_id, label, group, menu_name
        )

    def _route_phrase(self, event: ESP32DualEyeVoiceEvent) -> Dict[str, Any]:
        if str(event.payload.get("command_id") or "").strip():
            exact = self._route_exact_catalog_command(event)
            if exact is not None:
                return exact

        parsed = parse_voice_command(event.phrase, require_wake_word=True)
        action_started = parsed.menu_action is not None or parsed.module_key is not None
        action_label = (
            parsed.menu_action.label
            if parsed.menu_action is not None
            else (parsed.module_key or "KillerKoala request")
        )
        command = parsed.menu_action.command if parsed.menu_action is not None else ""
        persistent_command = command in KOALAGOTCHI_DISPLAY_COMMANDS

        if action_started:
            self._persistent_koalagotchi_mode = False
            self._emit_latched_state("action", action_label)

        routed = super()._route_phrase(event)
        result_data = routed.get("result", {}) if isinstance(routed, dict) else {}
        if not isinstance(result_data, dict) or not action_started:
            return routed

        status, message = self._status_and_message(result_data, action_label)
        display_state = self._show_post_execution_state(
            status=status,
            action=action_label,
            message=message,
            persistent_command=persistent_command,
            result_data=result_data,
        )
        routed["koalagotchi_display_state"] = display_state
        routed["failure_streak"] = self._failure_streak
        routed["persistent_koalagotchi_mode"] = self._persistent_koalagotchi_mode
        return routed

    def handle_payload(
        self, payload: Dict[str, Any]
    ) -> Optional[ESP32DualEyeVoiceEvent]:
        payload_type = str(payload.get("type") or "").strip().lower()
        status = str(payload.get("status") or "").strip().lower()
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
        } or status in {"cleared", "resolved", "recovered"}:
            self.clear_koalagotchi_error(message)
            return None

        if payload_type in {
            "display_fault",
            "audio_fault",
            "system_fault",
            "error",
        } or any(token in status for token in ("error", "fault")):
            self._active_error = True
            self._emit_latched_state("alarmed", message)
            self._save_failure_state(status="alarmed", message=message)

        return super().handle_payload(payload)


__all__ = [
    "ESP32DualEyeVoiceBridge",
    "ESP32DualEyeVoiceEvent",
    "default_esp32_port",
]
