from __future__ import annotations

import argparse
import json
import math
import os
import signal
import time
from pathlib import Path
from typing import Any, Mapping, Optional

from .hdmi_display_state import (
    DEFAULT_STATE_ROOT,
    compose_scene,
    display_mode_status,
    hdmi_connected,
    read_channel_snapshots,
    read_display_mode,
    set_display_mode,
    submit_menu_command,
)
from .runtime_log_hardening import atomic_write_json


DEFAULT_STATUS_PATH = DEFAULT_STATE_ROOT / "hdmi_display_status.json"
PURPLE = (165, 75, 255)
GREEN = (50, 255, 113)
ORANGE = (255, 173, 49)
PALE = (231, 255, 181)
INK = (2, 8, 9)


def _desktop_runtime_dir() -> Path:
    uid = os.getuid() if hasattr(os, "getuid") else 0
    configured = os.getenv("XDG_RUNTIME_DIR", "").strip()
    return Path(configured) if configured else Path(f"/run/user/{uid}")


def _wayland_socket(runtime_dir: Path) -> Optional[Path]:
    configured = os.getenv("WAYLAND_DISPLAY", "").strip()
    candidates: list[Path] = []
    if configured:
        value = Path(configured)
        candidates.append(value if value.is_absolute() else runtime_dir / value)
    candidates.extend(
        path
        for path in sorted(runtime_dir.glob("wayland-*"))
        if not path.name.endswith(".lock")
    )
    return next((path for path in candidates if path.is_socket()), None)


def desktop_session_available() -> bool:
    runtime_dir = _desktop_runtime_dir()
    return bool(
        _wayland_socket(runtime_dir)
        or (os.getenv("DISPLAY") and Path("/tmp/.X11-unix").exists())
        or Path("/tmp/.X11-unix/X0").exists()
    )


def desktop_session_expected() -> bool:
    policy = os.getenv("KOALABYTE_PI_DESKTOP", "auto").strip().lower()
    if policy in {"0", "false", "no", "off", "lite", "kms"}:
        return False
    if policy in {"1", "true", "yes", "on", "desktop"}:
        return True
    if desktop_session_available():
        return True
    display_manager = Path("/etc/systemd/system/display-manager.service")
    return display_manager.exists() or display_manager.is_symlink()


def configure_sdl_environment() -> dict[str, str]:
    """Select an existing Pi desktop session, otherwise leave SDL to use DRM/KMS."""

    selected: dict[str, str] = {}
    runtime_dir = _desktop_runtime_dir()
    wayland = _wayland_socket(runtime_dir)
    managed_driver = os.getenv("KOALABYTE_SDL_DRIVER_MANAGED") == "1"
    if wayland is not None:
        if managed_driver:
            os.environ.pop("SDL_VIDEODRIVER", None)
            os.environ.pop("KOALABYTE_SDL_DRIVER_MANAGED", None)
        os.environ["XDG_RUNTIME_DIR"] = str(wayland.parent)
        os.environ["WAYLAND_DISPLAY"] = wayland.name
    elif Path("/tmp/.X11-unix/X0").exists():
        if managed_driver:
            os.environ.pop("SDL_VIDEODRIVER", None)
            os.environ.pop("KOALABYTE_SDL_DRIVER_MANAGED", None)
        os.environ.setdefault("DISPLAY", ":0")
    elif not os.getenv("SDL_VIDEODRIVER"):
        preferred = os.getenv("KOALABYTE_SDL_VIDEODRIVER", "kmsdrm").strip()
        if preferred and preferred.lower() != "auto":
            os.environ["SDL_VIDEODRIVER"] = preferred
            os.environ["KOALABYTE_SDL_DRIVER_MANAGED"] = "1"

    for name in ("DISPLAY", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR", "SDL_VIDEODRIVER"):
        value = os.getenv(name)
        if value:
            selected[name] = value
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    return selected


def _hex_color(value: Any, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    text = str(value or "").strip().lstrip("#")
    if len(text) != 6:
        return fallback
    try:
        return tuple(int(text[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return fallback


def _payload(record: Mapping[str, Any], name: str) -> dict[str, Any]:
    value = record.get(name, {})
    return dict(value) if isinstance(value, Mapping) else {}


class PygameHDMICompositor:
    """Read-only HDMI surface; commands are queued for the Pi-owned menu service."""

    def __init__(self, *, state_root: str | Path | None = None, fps: int = 30) -> None:
        try:
            import pygame  # type: ignore
        except Exception as exc:  # pragma: no cover - depends on Pi image
            raise RuntimeError(f"pygame unavailable: {exc}") from exc
        self.pygame = pygame
        self.state_root = Path(state_root) if state_root is not None else None
        self.fps = max(15, min(int(fps), 60))
        self.screen: Any = None
        self.clock: Any = None
        self.fonts: dict[str, Any] = {}
        self._mouse_down: Optional[tuple[int, int, float]] = None
        self._last_tap_at = 0.0
        self._pi_os_button: Any = None
        self._menu_rows: list[tuple[Any, int]] = []
        self._background_surface: Any = None

    def open(self) -> None:
        pygame = self.pygame
        # Display/font only: never initialize pygame.mixer or compete with the
        # Pi-owned voice and music audio paths.
        pygame.display.init()
        pygame.font.init()
        windowed = os.getenv("KOALABYTE_HDMI_WINDOWED", "0").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if windowed:
            width = max(640, int(os.getenv("KOALABYTE_HDMI_WIDTH", "1280")))
            height = max(360, int(os.getenv("KOALABYTE_HDMI_HEIGHT", "720")))
            self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        else:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.display.set_caption("KoalaByte Blue HDMI")
        pygame.mouse.set_visible(True)
        self.clock = pygame.time.Clock()
        self._build_fonts()
        self._build_background()

    def close(self) -> None:
        if self.screen is None:
            return
        try:
            self.pygame.display.quit()
        finally:
            self.screen = None
            self.clock = None
            self.fonts = {}
            self._background_surface = None

    def _build_fonts(self) -> None:
        assert self.screen is not None
        w, h = self.screen.get_size()
        base = max(14, min(w, h) // 34)
        family = "dejavusanscondensed"
        self.fonts = {
            "tiny": self.pygame.font.SysFont(family, max(13, int(base * 0.66)), bold=True),
            "small": self.pygame.font.SysFont(family, max(16, int(base * 0.82)), bold=True),
            "body": self.pygame.font.SysFont(family, max(20, int(base * 1.05)), bold=True),
            "menu": self.pygame.font.SysFont(family, max(22, int(base * 1.25)), bold=True),
            "title": self.pygame.font.SysFont(family, max(32, int(base * 1.85)), bold=True),
        }

    def _text(self, text: str, font_name: str, color: tuple[int, int, int]) -> Any:
        return self.fonts[font_name].render(str(text), True, color)

    def _fit(self, text: str, font_name: str, width: int) -> str:
        font = self.fonts[font_name]
        clean = " ".join(str(text or "").split())
        if font.size(clean)[0] <= width:
            return clean
        suffix = "…"
        low, high, best = 0, len(clean), suffix
        while low <= high:
            mid = (low + high) // 2
            candidate = clean[:mid].rstrip() + suffix
            if font.size(candidate)[0] <= width:
                best = candidate
                low = mid + 1
            else:
                high = mid - 1
        return best

    def _queue(self, command: str, source: str = "hdmi-keyboard") -> None:
        submit_menu_command(command, source=source, root=self.state_root)

    def _queue_row_focus(self, target_index: int, scene: Mapping[str, Any]) -> None:
        menu = _payload(scene, "menu")
        current = int(menu.get("selected_index") or 0)
        total = max(1, int(menu.get("total_items") or 1))
        target = max(0, min(int(target_index), total - 1))
        forward = (target - current) % total
        backward = (current - target) % total
        command = "down" if forward <= backward else "up"
        for _ in range(min(forward, backward)):
            self._queue(command, "hdmi-touch")

    def handle_events(self, scene: Mapping[str, Any]) -> None:
        pygame = self.pygame
        keyboard_mode = str(_payload(scene, "menu").get("display_mode") or "") == "keyboard"
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                set_display_mode("desktop", source="hdmi-window-close", root=self.state_root)
                continue
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F12:
                    set_display_mode("desktop", source="hdmi-f12", root=self.state_root)
                    continue
                mapping = {
                    pygame.K_UP: "up",
                    pygame.K_w: "up",
                    pygame.K_DOWN: "down",
                    pygame.K_s: "down",
                    pygame.K_LEFT: "move_left",
                    pygame.K_a: "move_left",
                    pygame.K_RIGHT: "move_right",
                    pygame.K_d: "move_right",
                    pygame.K_RETURN: "select",
                    pygame.K_KP_ENTER: "select",
                    pygame.K_SPACE: "select" if not keyboard_mode else "space",
                    pygame.K_m: "main_menu",
                    pygame.K_ESCAPE: "back",
                    pygame.K_BACKSPACE: "backspace",
                    pygame.K_DELETE: "backspace",
                }
                command = mapping.get(event.key)
                if command:
                    self._queue(command)
                elif keyboard_mode:
                    text = getattr(event, "unicode", "") or ""
                    if text and text.isprintable():
                        self._queue(f"keyboard key {text[0]}")
            if event.type == pygame.MOUSEWHEEL:
                self._queue("up" if event.y > 0 else "down", "hdmi-touch")
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._mouse_down = (int(event.pos[0]), int(event.pos[1]), time.monotonic())
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                down = self._mouse_down
                self._mouse_down = None
                if down is None:
                    continue
                x, y = int(event.pos[0]), int(event.pos[1])
                held = time.monotonic() - down[2]
                if self._pi_os_button is not None and self._pi_os_button.collidepoint(x, y):
                    set_display_mode("desktop", source="hdmi-touch-button", root=self.state_root)
                    continue
                selected_row = next(
                    (index for rect, index in self._menu_rows if rect.collidepoint(x, y)),
                    None,
                )
                if selected_row is not None:
                    self._queue_row_focus(selected_row, scene)
                    if held >= 0.75:
                        self._queue("select", "hdmi-touch-long-press")
                    continue
                now = time.monotonic()
                if now - self._last_tap_at <= 0.45:
                    self._queue("main_menu", "hdmi-touch-double-tap")
                    self._last_tap_at = 0.0
                else:
                    self._last_tap_at = now

    def _build_background(self) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        w, h = screen.get_size()
        background = pygame.Surface((w, h))
        for y in range(h):
            t = y / max(1, h - 1)
            color = (2, max(8, int(18 + 24 * t)), max(9, int(16 + 14 * t)))
            pygame.draw.line(background, color, (0, y), (w, y))
        grid = max(36, w // 30)
        for x in range(0, w, grid):
            pygame.draw.line(background, (8, 49, 37), (x, 0), (x, h), 1)
        for y in range(0, h, grid):
            pygame.draw.line(background, (8, 49, 37), (0, y), (w, y), 1)
        self._background_surface = background

    def _background(self, now: float) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        if (
            self._background_surface is None
            or self._background_surface.get_size() != screen.get_size()
        ):
            self._build_fonts()
            self._build_background()
        screen.blit(self._background_surface, (0, 0))
        w, h = screen.get_size()
        scan_y = int((now * 42.0) % max(1, h))
        pygame.draw.line(screen, (12, 68, 46), (0, scan_y), (w, scan_y), 2)

    def _header(self, scene: Mapping[str, Any]) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        w, h = screen.get_size()
        title = self._text("KOALABYTE BLUE", "title", PALE)
        screen.blit(title, (max(24, int(w * 0.035)), max(14, int(h * 0.022))))
        view = str(scene.get("view") or "face").replace("_", " ").upper()
        badge = pygame.Rect(int(w * 0.38), int(h * 0.034), int(w * 0.22), max(34, int(h * 0.052)))
        pygame.draw.rect(screen, (12, 67, 39), badge, border_radius=badge.height // 2)
        pygame.draw.rect(screen, ORANGE, badge, 2, border_radius=badge.height // 2)
        text = self._text(self._fit(view, "small", badge.width - 24), "small", GREEN)
        screen.blit(text, text.get_rect(center=badge.center))
        self._pi_os_button = pygame.Rect(int(w * 0.79), int(h * 0.025), int(w * 0.18), max(42, int(h * 0.066)))
        pygame.draw.rect(screen, (44, 21, 61), self._pi_os_button, border_radius=self._pi_os_button.height // 2)
        pygame.draw.rect(screen, PURPLE, self._pi_os_button, 3, border_radius=self._pi_os_button.height // 2)
        label = self._text("PI OS  •  F12", "small", PALE)
        screen.blit(label, label.get_rect(center=self._pi_os_button.center))

    def _eyes(self, rect: Any, scene: Mapping[str, Any], now: float) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        face = _payload(scene, "face")
        error = _payload(scene, "error")
        state = str((error if scene.get("error_active") else face).get("state") or "idle").lower()
        left_color = _hex_color(face.get("left_eye"), PURPLE)
        right_color = _hex_color(face.get("right_eye"), GREEN)
        angry = state in {"alarmed", "angry", "error", "failed", "fault", "snarl"}
        thinking = state in {"listening", "thinking", "wake"}
        blink = abs(math.sin(now * 0.54 + 0.7)) > 0.985
        eye_h = max(10, int(rect.height * (0.10 if blink else 0.44)))
        eye_w = int(rect.width * 0.25)
        centers = [
            (int(rect.left + rect.width * 0.31), rect.centery),
            (int(rect.left + rect.width * 0.69), rect.centery),
        ]
        colors = [left_color, right_color]
        for index, (center, color) in enumerate(zip(centers, colors)):
            cx, cy = center
            glow = pygame.Rect(0, 0, eye_w + 28, eye_h + 28)
            glow.center = center
            pygame.draw.ellipse(screen, tuple(max(0, channel // 4) for channel in color), glow)
            socket = pygame.Rect(0, 0, eye_w + 12, eye_h + 12)
            socket.center = center
            pygame.draw.ellipse(screen, (20, 27, 28), socket)
            eye = pygame.Rect(0, 0, eye_w, eye_h)
            eye.center = center
            pygame.draw.ellipse(screen, color, eye)
            pygame.draw.ellipse(screen, PALE, eye, max(2, eye_h // 18))
            if not blink:
                gaze_x = int(math.sin(now * 0.72 + index * 0.9) * eye_w * 0.09)
                gaze_y = int(math.cos(now * 0.51) * eye_h * 0.06)
                pupil_r = max(8, int(eye_h * (0.19 if thinking else 0.23)))
                pygame.draw.circle(screen, INK, (cx + gaze_x, cy + gaze_y), pupil_r)
                pygame.draw.circle(screen, PALE, (cx + gaze_x - pupil_r // 3, cy + gaze_y - pupil_r // 3), max(2, pupil_r // 5))
            brow_y = int(cy - eye_h * 0.72 - 12)
            brow_span = int(eye_w * 0.45)
            tilt = int(eye_h * (0.32 if angry else -0.08 if thinking else 0.04))
            if index == 0:
                start = (cx - brow_span, brow_y - tilt)
                end = (cx + brow_span, brow_y + tilt)
            else:
                start = (cx - brow_span, brow_y + tilt)
                end = (cx + brow_span, brow_y - tilt)
            pygame.draw.line(screen, (112, 124, 126), start, end, max(7, eye_h // 10))
            for fur_index in range(9):
                angle = math.pi * (fur_index / 8.0)
                fx = cx + int(math.cos(angle) * (eye_w * 0.62))
                fy = cy - int(math.sin(angle) * (eye_h * 0.88))
                pygame.draw.line(screen, (75, 86, 87), (fx, fy), (fx + int(math.cos(angle) * 14), fy - int(math.sin(angle) * 14)), 3)

    def _mouth(self, rect: Any, scene: Mapping[str, Any], now: float) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        face = _payload(scene, "face")
        koala = _payload(scene, "koalagotchi")
        state = str(face.get("state") or "idle").lower()
        expression = str(
            koala.get("expression")
            or face.get("mouth_expression")
            or ("snarl" if state in {"error", "alarmed", "failed"} else "smile")
        ).lower()
        speaking = bool(scene.get("speech_active")) or state == "speaking"
        if speaking:
            motion = 0.5 + 0.27 * math.sin(now * 12.7) + 0.16 * math.sin(now * 7.1 + 1.4)
            openness = max(0.12, min(0.92, motion))
        elif expression == "bite":
            openness = 0.34 + 0.08 * math.sin(now * 4.0)
        elif expression == "snarl":
            openness = 0.24
        else:
            openness = 0.12 + 0.025 * math.sin(now * 1.8)
        mouth_w = int(rect.width * (0.57 if expression != "sideways_grin" else 0.63))
        mouth_h = max(18, int(rect.height * (0.18 + 0.58 * openness)))
        mouth = pygame.Rect(0, 0, mouth_w, mouth_h)
        mouth.center = (rect.centerx + (int(rect.width * 0.04) if expression == "sideways_grin" else 0), rect.centery)
        shadow = mouth.inflate(28, 22)
        pygame.draw.ellipse(screen, (35, 8, 31), shadow)
        pygame.draw.ellipse(screen, (101, 25, 77), mouth)
        pygame.draw.ellipse(screen, PURPLE if expression == "snarl" else ORANGE, mouth, max(4, mouth_h // 10))
        inner = mouth.inflate(-max(12, mouth_w // 14), -max(8, mouth_h // 5))
        pygame.draw.ellipse(screen, (14, 3, 12), inner)
        if mouth_h > 30:
            tooth_h = max(5, int(mouth_h * (0.26 if expression == "snarl" else 0.18)))
            tooth = pygame.Rect(inner.left + 8, inner.top + 3, inner.width - 16, tooth_h)
            pygame.draw.rect(screen, PALE, tooth, border_radius=max(3, tooth_h // 3))
            for x in range(tooth.left + tooth.width // 6, tooth.right, max(8, tooth.width // 6)):
                pygame.draw.line(screen, (118, 128, 109), (x, tooth.top), (x, tooth.bottom), 1)
        if expression in {"smile", "sideways_grin"} and not speaking:
            pygame.draw.arc(screen, GREEN, mouth.inflate(20, 4), 0.08, math.pi - 0.08, 4)

    def _menu(self, rect: Any, scene: Mapping[str, Any]) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        menu = _payload(scene, "menu")
        pygame.draw.rect(screen, (7, 43, 26), rect, border_radius=24)
        pygame.draw.rect(screen, ORANGE, rect, 3, border_radius=24)
        title = str(menu.get("menu_title") or "MAIN CANOPY").upper()
        heading = self._text(self._fit(title, "menu", rect.width - 40), "menu", PALE)
        screen.blit(heading, heading.get_rect(center=(rect.centerx, rect.top + 32)))
        rows = menu.get("visible_items") if isinstance(menu.get("visible_items"), list) else []
        if not rows:
            rows = [
                {
                    "index": int(menu.get("selected_index") or 0),
                    "position": int(menu.get("selected_position") or 1),
                    "label": str(menu.get("selected_label") or "Menu ready"),
                    "selected": True,
                    "enabled": bool(menu.get("selected_enabled", True)),
                }
            ]
        self._menu_rows = []
        available = rect.height - 78
        row_h = max(42, min(78, available // max(1, len(rows))))
        for row_number, item in enumerate(rows):
            if not isinstance(item, Mapping):
                continue
            row_rect = pygame.Rect(rect.left + 24, rect.top + 58 + row_number * row_h, rect.width - 48, row_h - 8)
            selected = bool(item.get("selected"))
            enabled = bool(item.get("enabled", True))
            fill = (35, 91, 43) if selected else (10, 55, 32)
            if not enabled:
                fill = (38, 44, 42)
            pygame.draw.rect(screen, fill, row_rect, border_radius=row_rect.height // 2)
            pygame.draw.rect(screen, GREEN if selected else (61, 116, 73), row_rect, 3 if selected else 1, border_radius=row_rect.height // 2)
            position = int(item.get("position") or int(item.get("index") or 0) + 1)
            label = f"{position:02d}. {item.get('label') or 'Menu item'}"
            label = self._fit(label, "body", row_rect.width - 42)
            surface = self._text(label, "body", PALE if enabled else (139, 151, 144))
            screen.blit(surface, (row_rect.left + 20, row_rect.centery - surface.get_height() // 2))
            self._menu_rows.append((row_rect, int(item.get("index") or position - 1)))

    def _koalagotchi(self, rect: Any, scene: Mapping[str, Any], now: float) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        koala = _payload(scene, "koalagotchi")
        action = _payload(scene, "action")
        pygame.draw.rect(screen, (7, 39, 29), rect, border_radius=26)
        pygame.draw.rect(screen, GREEN, rect, 3, border_radius=26)
        branch_y = int(rect.top + rect.height * 0.63)
        pygame.draw.line(screen, (73, 43, 21), (rect.left + 32, branch_y), (rect.right - 32, branch_y), max(14, rect.height // 16))
        pygame.draw.line(screen, (161, 113, 55), (rect.left + 32, branch_y - 4), (rect.right - 32, branch_y - 4), 4)
        travel = max(1, rect.width - 190)
        x = rect.left + 95 + int((0.5 + 0.5 * math.sin(now * 0.65)) * travel)
        y = branch_y - max(38, rect.height // 8)
        scale = max(24, min(rect.width, rect.height) // 10)
        fur = (143, 153, 155)
        dark = (71, 80, 82)
        pygame.draw.circle(screen, dark, (x - scale, y - scale), int(scale * 0.62))
        pygame.draw.circle(screen, dark, (x + scale, y - scale), int(scale * 0.62))
        pygame.draw.circle(screen, (210, 157, 180), (x - scale, y - scale), int(scale * 0.34))
        pygame.draw.circle(screen, (210, 157, 180), (x + scale, y - scale), int(scale * 0.34))
        pygame.draw.circle(screen, fur, (x, y), scale)
        eye_color = ORANGE if str(koala.get("expression") or "") == "snarl" else GREEN
        pygame.draw.circle(screen, eye_color, (x - scale // 3, y - scale // 6), max(3, scale // 9))
        pygame.draw.circle(screen, eye_color, (x + scale // 3, y - scale // 6), max(3, scale // 9))
        pygame.draw.ellipse(screen, INK, pygame.Rect(x - scale // 5, y, scale * 2 // 5, scale // 3))
        title = str(action.get("selected_label") or action.get("action_title") or "KOALAGOTCHI")
        heading = self._text(self._fit(title.upper(), "menu", rect.width - 50), "menu", PALE)
        screen.blit(heading, heading.get_rect(center=(rect.centerx, rect.top + 30)))
        raw_contentment = koala.get("contentment")
        if raw_contentment is None:
            raw_contentment = koala.get("health")
        try:
            contentment = max(0, min(100, int(75 if raw_contentment is None else raw_contentment)))
        except (TypeError, ValueError):
            contentment = 75
        bar_back = pygame.Rect(rect.left + 36, rect.bottom - 54, rect.width - 72, 22)
        pygame.draw.rect(screen, (25, 67, 42), bar_back, border_radius=11)
        bar = bar_back.copy()
        bar.width = int(bar_back.width * contentment / 100)
        pygame.draw.rect(screen, GREEN, bar, border_radius=11)
        mood = str(koala.get("mood") or "patrolling the canopy")
        caption = self._text(self._fit(f"{contentment}%  •  {mood}", "small", rect.width - 80), "small", PALE)
        screen.blit(caption, caption.get_rect(center=(rect.centerx, rect.bottom - 16)))

    def _message(self, scene: Mapping[str, Any]) -> str:
        for name in ("error", "action", "face"):
            payload = _payload(scene, name)
            text = payload.get("message") or payload.get("selected_label") or payload.get("action_title")
            if text:
                return str(text)
        return "KillerKoala online"

    def draw(self, scene: Mapping[str, Any]) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        now = time.monotonic()
        self._background(now)
        self._header(scene)
        w, h = screen.get_size()
        view = str(scene.get("view") or "face")
        self._menu_rows = []

        if view == "menu":
            self._eyes(pygame.Rect(int(w * 0.05), int(h * 0.11), int(w * 0.90), int(h * 0.22)), scene, now)
            self._menu(pygame.Rect(int(w * 0.10), int(h * 0.32), int(w * 0.80), int(h * 0.49)), scene)
            self._mouth(pygame.Rect(int(w * 0.22), int(h * 0.82), int(w * 0.56), int(h * 0.15)), scene, now)
        elif view in {"action", "koalagotchi"}:
            self._eyes(pygame.Rect(int(w * 0.08), int(h * 0.12), int(w * 0.84), int(h * 0.20)), scene, now)
            self._koalagotchi(pygame.Rect(int(w * 0.09), int(h * 0.33), int(w * 0.82), int(h * 0.44)), scene, now)
            self._mouth(pygame.Rect(int(w * 0.22), int(h * 0.78), int(w * 0.56), int(h * 0.18)), scene, now)
        else:
            self._eyes(pygame.Rect(int(w * 0.04), int(h * 0.14), int(w * 0.92), int(h * 0.42)), scene, now)
            self._mouth(pygame.Rect(int(w * 0.16), int(h * 0.57), int(w * 0.68), int(h * 0.30)), scene, now)
            self._koalagotchi(pygame.Rect(int(w * 0.72), int(h * 0.73), int(w * 0.25), int(h * 0.20)), scene, now)

        message = self._fit(self._message(scene), "small", int(w * 0.68))
        status = self._text(message, "small", PALE)
        screen.blit(status, status.get_rect(center=(w // 2, int(h * 0.955))))

        if scene.get("error_active"):
            flash = PURPLE if int(now * 6) % 2 == 0 else GREEN
            overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            overlay.fill((*flash, 54))
            screen.blit(overlay, (0, 0))
            pygame.draw.rect(screen, flash, pygame.Rect(8, 8, w - 16, h - 16), max(8, min(w, h) // 45), border_radius=22)
            alarm = self._text("KILLERKOALA ALARM", "title", PALE)
            screen.blit(alarm, alarm.get_rect(center=(w // 2, int(h * 0.11))))

        pygame.display.flip()
        if self.clock is not None:
            self.clock.tick(self.fps)


class HDMIDisplayService:
    def __init__(
        self,
        *,
        state_root: str | Path | None = None,
        status_path: str | Path = DEFAULT_STATUS_PATH,
        fps: int = 30,
    ) -> None:
        self.state_root = Path(state_root) if state_root is not None else None
        self.status_path = Path(status_path)
        self.fps = fps
        self.renderer: Optional[PygameHDMICompositor] = None
        self.stop_requested = False
        self._last_status: tuple[str, str] | None = None
        self._last_status_at = 0.0
        try:
            state_hz = float(os.getenv("KOALABYTE_HDMI_STATE_HZ", "12"))
        except ValueError:
            state_hz = 12.0
        self.state_poll_seconds = 1.0 / max(2.0, min(state_hz, 30.0))

    def _status(self, status: str, **extra: Any) -> None:
        now = time.time()
        if (
            self._last_status is not None
            and self._last_status[0] == status
            and now - self._last_status_at < 2.0
        ):
            return
        mode = read_display_mode(root=self.state_root)
        signature = (status, mode)
        payload = {
            "status": status,
            "mode": mode,
            "read_only_renderer": True,
            "voice_commands_preserved": True,
            "gpio_k1_k8_preserved": True,
            "keyboard_touch_commands_queued_to_menu_owner": True,
            "serial_ports_opened": False,
            "updated_at": now,
            **extra,
        }
        atomic_write_json(self.status_path, payload)
        self._last_status = signature
        self._last_status_at = now

    def _close_renderer(self) -> None:
        if self.renderer is not None:
            self.renderer.close()
            self.renderer = None

    def run(self) -> int:
        def stop_handler(_signum: int, _frame: object) -> None:
            self.stop_requested = True

        signal.signal(signal.SIGINT, stop_handler)
        signal.signal(signal.SIGTERM, stop_handler)
        sdl = configure_sdl_environment()
        self._status("HDMI_DISPLAY_STARTING", sdl_environment=sdl)
        mode = read_display_mode(root=self.state_root)
        next_mode_poll = 0.0
        snapshots: dict[str, dict[str, Any]] = {}
        next_state_poll = 0.0
        connected = False
        next_connector_poll = 0.0

        while not self.stop_requested:
            monotonic_now = time.monotonic()
            if monotonic_now >= next_mode_poll:
                mode = read_display_mode(root=self.state_root)
                next_mode_poll = monotonic_now + 0.10
            if monotonic_now >= next_connector_poll:
                connected = hdmi_connected()
                next_connector_poll = monotonic_now + 0.50
            if mode == "desktop":
                self._close_renderer()
                self._status("PI_OS_VISIBLE", hdmi_connected=connected)
                time.sleep(0.25)
                continue
            if not connected:
                self._close_renderer()
                self._status("HDMI_NOT_CONNECTED", hdmi_connected=False)
                time.sleep(1.0)
                continue
            if (
                self.renderer is None
                and desktop_session_expected()
                and not desktop_session_available()
            ):
                # Do not seize DRM/KMS while an enabled display manager is
                # starting. Once its user session appears, render fullscreen
                # inside that session so desktop mode can reveal Pi OS cleanly.
                self._close_renderer()
                self._status(
                    "HDMI_WAITING_FOR_DESKTOP_SESSION",
                    hdmi_connected=True,
                )
                time.sleep(1.0)
                continue
            try:
                if self.renderer is None:
                    # A desktop session may have appeared after boot or after a
                    # period in Pi OS mode, so choose Wayland/X11/KMS again.
                    sdl = configure_sdl_environment()
                    self.renderer = PygameHDMICompositor(
                        state_root=self.state_root,
                        fps=self.fps,
                    )
                    self.renderer.open()
                if monotonic_now >= next_state_poll:
                    snapshots = read_channel_snapshots(root=self.state_root)
                    next_state_poll = monotonic_now + self.state_poll_seconds
                scene = compose_scene(snapshots, mode=mode)
                self.renderer.handle_events(scene)
                self.renderer.draw(scene)
                self._status(
                    "KOALABYTE_HDMI_VISIBLE",
                    hdmi_connected=True,
                    scene_view=scene.get("view"),
                    sdl_environment=sdl,
                )
            except Exception as exc:  # pragma: no cover - hardware/session dependent
                self._close_renderer()
                self._status(
                    "HDMI_RENDER_RETRY",
                    hdmi_connected=True,
                    error=str(exc),
                    sdl_environment=sdl,
                )
                time.sleep(2.0)

        self._close_renderer()
        self._status("HDMI_DISPLAY_STOPPED")
        return 0


def run_cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the read-only KoalaByte Blue HDMI compositor"
    )
    parser.add_argument("--state-dir", default=None)
    parser.add_argument("--status-path", default=str(DEFAULT_STATUS_PATH))
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--windowed", action="store_true")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Print HDMI/mode/state readiness without opening a display",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Print the composed scene once without opening a display",
    )
    args = parser.parse_args(argv)
    if args.windowed:
        os.environ["KOALABYTE_HDMI_WINDOWED"] = "1"
    root = Path(args.state_dir) if args.state_dir else None
    if args.check:
        payload = {
            **display_mode_status(root=root),
            "hdmi_connected": hdmi_connected(),
            "sdl_environment": configure_sdl_environment(),
            "snapshot_channels": sorted(read_channel_snapshots(root=root)),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.once:
        scene = compose_scene(
            read_channel_snapshots(root=root),
            mode=read_display_mode(root=root),
        )
        print(json.dumps(scene, indent=2, sort_keys=True))
        return 0
    return HDMIDisplayService(
        state_root=root,
        status_path=args.status_path,
        fps=args.fps,
    ).run()


__all__ = [
    "DEFAULT_STATUS_PATH",
    "HDMIDisplayService",
    "PygameHDMICompositor",
    "configure_sdl_environment",
    "desktop_session_available",
    "desktop_session_expected",
    "run_cli",
]
