from __future__ import annotations

import math
import os
import textwrap
import time
from dataclasses import dataclass
from typing import Any, Iterable, Optional, Tuple

Color = Tuple[int, int, int]


@dataclass(frozen=True)
class JungleMenuTheme:
    """KoalaByte Blue menu styling.

    The visual target is a chunky jungle-adventure handheld firmware look:
    dark cyber-canopy background, oversized carved title text, yellow-green
    menu typography, orange action accents, and bright selected rows.
    No third-party font files are bundled in the repo.
    """

    title: str = "KOALABYTE BLUE"
    font_family: str = "cooperblack,arialroundedmsbold,arialblack,dejavusanscondensed,dejavusans"
    item_font_family: str = "cooperblack,arialroundedmsbold,arialblack,dejavusanscondensed,dejavusans"
    border_style: str = "jungle_adventure_eucalyptus_branch_and_leaf_border"
    background: Color = (2, 9, 8)
    background_2: Color = (4, 22, 13)
    bark: Color = (85, 61, 28)
    bark_highlight: Color = (184, 132, 54)
    leaf: Color = (71, 188, 83)
    leaf_dark: Color = (18, 92, 42)
    leaf_glow: Color = (184, 255, 107)
    title_fill: Color = (255, 214, 62)
    title_inner: Color = (202, 255, 81)
    title_outline: Color = (18, 76, 29)
    title_shadow: Color = (3, 17, 7)
    item_fill: Color = (242, 225, 91)
    item_outline: Color = (35, 125, 45)
    item_shadow: Color = (4, 27, 12)
    selected_fill: Color = (201, 255, 88)
    selected_outline: Color = (255, 175, 49)
    selected_glow: Color = (83, 255, 104)
    disabled_fill: Color = (113, 123, 91)
    blue_accent: Color = (62, 207, 255)
    boomerang_accent: Color = (255, 177, 60)


DEFAULT_JUNGLE_MENU_THEME = JungleMenuTheme()
_TERMINAL_BRANCH = "🌿"
_MODE_BADGES = {
    "eucalyptus_mode": "EUCALYPTUS MODE // Koalagotchi BLE canopy screen",
    "boomerang": "BOOMERANG MODE // Camera-awareness logbook",
}

GRAPHICAL_LABEL_MAX_LINES = 1
GRAPHICAL_DESCRIPTION_MAX_LINES = 2
TERMINAL_LABEL_WIDTH = 68
TERMINAL_DESCRIPTION_WIDTH = 64


def _mode_badge(command: str) -> str:
    return _MODE_BADGES.get(command, "")


def _terminal_fit(text: str, width: int, suffix: str = "…") -> str:
    text = str(text)
    if len(text) <= width:
        return text
    if width <= len(suffix):
        return suffix[:width]
    return text[: width - len(suffix)].rstrip() + suffix


def render_terminal_jungle_menu(menu: Any, theme: JungleMenuTheme = DEFAULT_JUNGLE_MENU_THEME) -> str:
    """Render a terminal-safe preview of the jungle/eucalyptus menu theme."""

    if hasattr(menu, "check_idle_timeout"):
        menu.check_idle_timeout()
    if getattr(menu, "display_mode", "menu") != "menu":
        title = "KILLERKOALA AI FACE"
        message = str(getattr(menu, "face_message", "KillerKoala is watching the canopy"))
        state = str(getattr(menu, "face_state", "idle"))
        width = 74
        top = f"{_TERMINAL_BRANCH}" + "═" * (width - 2) + f"{_TERMINAL_BRANCH}"
        return "\n".join([
            top,
            title.center(width),
            f"  STATE: {_terminal_fit(state.upper(), 54)}  ".center(width),
            top,
            f"🌿 {_terminal_fit(message, 68):<68} 🌿",
            "  Press B1/Menu or double-tap touchscreen to reopen the menu.  ".center(width),
            top,
        ])

    visible = menu.visible_items()
    total = len(menu.items)
    selected_group = getattr(menu, "selected_group", getattr(menu.selected_item, "group", "System / Companion"))
    width = 74
    top = f"{_TERMINAL_BRANCH}" + "═" * (width - 2) + f"{_TERMINAL_BRANCH}"
    title = f"  {_terminal_fit(theme.title, width - 4)}  "
    header = title.center(width)
    sub = f"  {_terminal_fit(str(selected_group).upper(), 48)}  ({menu.selected_index + 1}/{total})  ".center(width)
    lines = [top, header, sub, top]
    previous_group: Optional[str] = None
    for absolute_index, item in visible:
        group = getattr(item, "group", "System / Companion")
        if group != previous_group:
            group_label = f"  [{_terminal_fit(group, 58)}]  "
            lines.append(group_label.center(width))
            previous_group = group
        selected = absolute_index == menu.selected_index
        marker = "➤" if selected else " "
        left_leaf = "🌿" if selected else " "
        right_leaf = "🌿" if selected else " "
        disabled = " [locked]" if not item.enabled else ""
        label = _terminal_fit(f"{marker} {absolute_index + 1:02d}. {item.label}{disabled}", TERMINAL_LABEL_WIDTH)
        lines.append(f"{left_leaf} {label:<68} {right_leaf}")
        if selected:
            badge = _mode_badge(getattr(item, "command", ""))
            if badge:
                lines.append(f"  {_terminal_fit('     ' + badge, 70):<70}")
            if item.description:
                wrapped = textwrap.wrap(str(item.description), width=TERMINAL_DESCRIPTION_WIDTH)[:2]
                for desc in wrapped:
                    lines.append(f"  {_terminal_fit('     ' + desc, 70):<70}")
    lines.append(top)
    lines.append(_terminal_fit("Buttons: B1 menu | B2 prev/back | B3 select/hold shutdown | B4 next | B5 up | B6 down", width))
    lines.append(_terminal_fit("Touch: drag/scroll through eucalyptus branches | long press to select", width))
    return "\n".join(lines)


def render_terminal_eucalyptus_card(title: str, rows: Iterable[str], subtitle: str = "THAT’S NOT A KNIFE", theme: JungleMenuTheme = DEFAULT_JUNGLE_MENU_THEME) -> str:
    """Render a terminal-safe status card in the same chunky menu style."""

    width = 74
    top = f"{_TERMINAL_BRANCH}" + "═" * (width - 2) + f"{_TERMINAL_BRANCH}"
    lines = [top]
    lines.append(f"  {_terminal_fit(theme.title, width - 4)}  ".center(width))
    lines.append(f"  {_terminal_fit(subtitle.upper(), width - 4)}  ".center(width))
    style = f"style: jungle cyber menu | border: {theme.border_style}"
    lines.append(f"  {_terminal_fit(style, width - 4)}  ".center(width))
    lines.append(top)
    lines.append(f"🌿 {_terminal_fit(title, 68):<68} 🌿")
    for row in rows:
        for line in textwrap.wrap(str(row), width=68) or [""]:
            lines.append(f"  {_terminal_fit(line, 70):<70}")
    lines.append(top)
    return "\n".join(lines)


class JungleMenuUnavailable(RuntimeError):
    pass


def _import_pygame():
    try:
        import pygame  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on Pi display environment
        raise JungleMenuUnavailable(f"pygame unavailable: {exc}") from exc
    return pygame


def _pick_font(pygame: Any, family_csv: str, size: int, bold: bool = True):
    available = {name.lower().replace(" ", "") for name in pygame.font.get_fonts()}
    for name in [part.strip() for part in family_csv.split(",") if part.strip()]:
        key = name.lower().replace(" ", "")
        if key in available:
            return pygame.font.SysFont(name, size, bold=bold)
    return pygame.font.SysFont("dejavusans", size, bold=bold)


def _fit_text_for_width(font: Any, text: str, max_width: int, suffix: str = "…") -> str:
    text = str(text).strip()
    if not text:
        return ""
    if font.size(text)[0] <= max_width:
        return text
    if max_width <= 0 or font.size(suffix)[0] > max_width:
        return ""
    low = 0
    high = len(text)
    best = ""
    while low <= high:
        mid = (low + high) // 2
        candidate = text[:mid].rstrip() + suffix
        if font.size(candidate)[0] <= max_width:
            best = candidate
            low = mid + 1
        else:
            high = mid - 1
    return best or suffix


def _wrap_for_width(font: Any, text: str, max_width: int, max_lines: int = 2) -> list[str]:
    if not text or max_width <= 0 or max_lines <= 0:
        return []
    words = str(text).split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if font.size(candidate)[0] <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = ""
            if len(lines) >= max_lines:
                break
        if font.size(word)[0] <= max_width:
            current = word
        else:
            lines.append(_fit_text_for_width(font, word, max_width))
            if len(lines) >= max_lines:
                current = ""
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    original_joined = " ".join(words)
    rendered_joined = " ".join(lines)
    if len(lines) == max_lines and len(rendered_joined) < len(original_joined):
        lines[-1] = _fit_text_for_width(font, lines[-1] + " " + original_joined[len(rendered_joined):], max_width)
    return lines[:max_lines]


class JungleMenuRenderer:
    """Pygame renderer for the KoalaByte Blue jungle/eucalyptus grouped menu."""

    def __init__(self, menu: Optional[Any] = None, theme: JungleMenuTheme = DEFAULT_JUNGLE_MENU_THEME, *, fullscreen: bool = True, width: int = 800, height: int = 480, fps: int = 30) -> None:
        if menu is None:
            from .menu_ui import MenuSelectionScreen

            menu = MenuSelectionScreen(visible_rows=5)
        self.menu = menu
        self.theme = theme
        self.fullscreen = fullscreen
        self.width = width
        self.height = height
        self.fps = fps
        self.pygame = _import_pygame()
        self.screen = None
        self.clock = None
        self.title_font = None
        self.item_font = None
        self.desc_font = None
        self.group_font = None
        self.buttons = None
        self._touch_down_y: Optional[int] = None
        self._touch_down_at: Optional[float] = None

    def setup(self) -> None:
        pygame = self.pygame
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        pygame.init()
        flags = pygame.FULLSCREEN if self.fullscreen else 0
        self.screen = pygame.display.set_mode((0, 0), flags) if self.fullscreen else pygame.display.set_mode((self.width, self.height), flags)
        pygame.display.set_caption("KoalaByte Blue Jungle Menu")
        self.clock = pygame.time.Clock()
        w, h = self.screen.get_size()
        self.title_font = _pick_font(pygame, self.theme.font_family, max(34, min(78, int(w * 0.072))), bold=True)
        self.item_font = _pick_font(pygame, self.theme.item_font_family, max(18, min(38, int(w * 0.034))), bold=True)
        self.group_font = _pick_font(pygame, self.theme.item_font_family, max(16, min(28, int(w * 0.028))), bold=True)
        self.desc_font = pygame.font.SysFont("dejavusans", max(12, min(18, int(w * 0.017))), bold=True)
        self.menu.touch_config.row_height_px = max(78, int(h * 0.145))
        self.menu.visible_rows = max(3, min(5, int((h * 0.62) / self.menu.touch_config.row_height_px)))
        self.menu._clamp_scroll_to_selection()
        try:
            from .gpio_buttons import GPIOButtonManager

            self.buttons = GPIOButtonManager()
            self.buttons.start()
        except Exception:
            self.buttons = None

    def run(self) -> int:
        self.setup()
        pygame = self.pygame
        try:
            while True:
                event_result = self._handle_events()
                if event_result == "quit":
                    return 0
                if hasattr(self.menu, "check_idle_timeout"):
                    self.menu.check_idle_timeout()
                self.draw()
                pygame.display.flip()
                self.clock.tick(self.fps)
        finally:
            if self.buttons is not None:
                try:
                    self.buttons.close()
                except Exception:
                    pass

    def _poll_gpio_buttons(self) -> Optional[str]:
        if self.buttons is None or not getattr(self.buttons, "available", False):
            return None
        try:
            button_event = self.buttons.get_event(timeout=0.0)
        except Exception:
            return None
        if button_event is None:
            return None
        menu_event = self.menu.handle_command(button_event.command)
        if _selected_quit(menu_event):
            return "quit"
        return None

    def _handle_events(self) -> Optional[str]:
        button_result = self._poll_gpio_buttons()
        if button_result == "quit":
            return "quit"
        pygame = self.pygame
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                command = {
                    pygame.K_w: "up",
                    pygame.K_UP: "up",
                    pygame.K_s: "down",
                    pygame.K_DOWN: "down",
                    pygame.K_a: "move_left",
                    pygame.K_LEFT: "move_left",
                    pygame.K_d: "move_right",
                    pygame.K_RIGHT: "move_right",
                    pygame.K_RETURN: "select",
                    pygame.K_SPACE: "select",
                    pygame.K_m: "main_menu",
                    pygame.K_ESCAPE: "quit",
                    pygame.K_q: "quit",
                }.get(event.key)
                if command == "quit":
                    return "quit"
                if command:
                    menu_event = self.menu.handle_command(command)
                    if _selected_quit(menu_event):
                        return "quit"
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4:
                    self.menu.handle_command("up")
                elif event.button == 5:
                    self.menu.handle_command("down")
                else:
                    self._touch_down_y = int(event.pos[1])
                    self._touch_down_at = time.time()
                    self.menu.on_touch_down(int(event.pos[1]))
            if event.type == pygame.MOUSEMOTION and self._touch_down_y is not None and event.buttons[0]:
                self.menu.on_touch_move(int(event.pos[1]))
            if event.type == pygame.MOUSEBUTTONUP and self._touch_down_y is not None:
                menu_event = self.menu.on_touch_up(int(event.pos[1]))
                self._touch_down_y = None
                self._touch_down_at = None
                if _selected_quit(menu_event):
                    return "quit"
        return None

    def draw(self) -> None:
        screen = self.screen
        assert screen is not None
        self._draw_background()
        self._draw_leafy_border()
        if getattr(self.menu, "display_mode", "menu") != "menu":
            self._draw_ai_face()
            return
        self._draw_title()
        self._draw_group_label()
        self._draw_items()
        self._draw_footer()

    def _draw_background(self) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        w, h = screen.get_size()
        for y in range(h):
            t = y / max(1, h - 1)
            color = tuple(int(self.theme.background[i] * (1 - t) + self.theme.background_2[i] * t) for i in range(3))
            pygame.draw.line(screen, color, (0, y), (w, y))
        for x in range(0, w, max(24, w // 26)):
            pygame.draw.line(screen, (4, 34, 22), (x, 0), (x, h), 1)
        for y in range(0, h, max(24, h // 16)):
            pygame.draw.line(screen, (4, 34, 22), (0, y), (w, y), 1)

    def _draw_leafy_border(self) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        w, h = screen.get_size()
        margin = max(15, int(min(w, h) * 0.033))
        stem_width = max(5, int(min(w, h) * 0.013))
        pygame.draw.line(screen, self.theme.bark, (margin, margin), (w - margin, margin), stem_width)
        pygame.draw.line(screen, self.theme.bark, (margin, h - margin), (w - margin, h - margin), stem_width)
        pygame.draw.line(screen, self.theme.bark, (margin, margin), (margin, h - margin), stem_width)
        pygame.draw.line(screen, self.theme.bark, (w - margin, margin), (w - margin, h - margin), stem_width)
        pygame.draw.line(screen, self.theme.bark_highlight, (margin, margin - 2), (w - margin, margin - 2), 2)
        spacing = max(36, int(w * 0.06))
        for x in range(margin + 18, w - margin, spacing):
            self._leaf((x, margin - 3), 17, -25)
            self._leaf((x + spacing // 3, h - margin + 2), 17, 155)
        spacing_y = max(34, int(h * 0.095))
        for y in range(margin + 22, h - margin, spacing_y):
            self._leaf((margin - 2, y), 17, 65)
            self._leaf((w - margin + 2, y + spacing_y // 3), 17, 245)

    def _leaf(self, center: Tuple[int, int], size: int, angle_deg: float) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        angle = math.radians(angle_deg)
        sx = math.cos(angle) * size * 0.45
        sy = math.sin(angle) * size * 0.45
        rect = pygame.Rect(0, 0, int(size * 1.45), int(size * 0.78))
        rect.center = center
        pygame.draw.ellipse(screen, self.theme.leaf_dark, rect)
        pygame.draw.line(screen, self.theme.leaf_glow, (int(center[0] - sx), int(center[1] - sy)), (int(center[0] + sx), int(center[1] + sy)), 2)
        inner = rect.inflate(-max(2, size // 5), -max(2, size // 5))
        pygame.draw.ellipse(screen, self.theme.leaf, inner)

    def _draw_ai_face(self) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        assert self.title_font is not None
        assert self.item_font is not None
        assert self.desc_font is not None
        w, h = screen.get_size()
        title = _fit_text_for_width(self.title_font, "KILLERKOALA", int(w * 0.78))
        self._chunky_text(title, w // 2, int(h * 0.18), self.title_font, self.theme.title_fill, self.theme.title_outline, self.theme.title_shadow, outline_size=5)
        state = str(getattr(self.menu, "face_state", "idle")).upper()
        message = str(getattr(self.menu, "face_message", "KillerKoala is watching the canopy"))
        panel = pygame.Rect(int(w * 0.12), int(h * 0.31), int(w * 0.76), int(h * 0.35))
        pygame.draw.rect(screen, (12, 60, 28), panel, border_radius=max(24, panel.height // 4))
        pygame.draw.rect(screen, self.theme.boomerang_accent, panel, 4, border_radius=max(24, panel.height // 4))
        self._leaf((panel.left + 28, panel.top + 28), 24, 45)
        self._leaf((panel.right - 28, panel.bottom - 28), 24, 225)
        state_line = _fit_text_for_width(self.item_font, state, panel.width - 52)
        self._chunky_text(state_line, panel.centerx, panel.top + int(panel.height * 0.35), self.item_font, self.theme.leaf_glow, self.theme.item_outline, self.theme.title_shadow, outline_size=2)
        for idx, line in enumerate(_wrap_for_width(self.desc_font, message, panel.width - 60, max_lines=2)):
            surf = self.desc_font.render(line, True, self.theme.title_fill)
            screen.blit(surf, surf.get_rect(center=(panel.centerx, panel.top + int(panel.height * 0.62) + idx * (self.desc_font.get_height() + 3))))
        hint = _fit_text_for_width(self.desc_font, "B1/Menu or touchscreen double-tap reopens menu", int(w * 0.78))
        surf = self.desc_font.render(hint, True, self.theme.leaf_glow)
        screen.blit(surf, surf.get_rect(center=(w // 2, int(h * 0.78))))

    def _draw_title(self) -> None:
        screen = self.screen
        assert screen is not None
        w, h = screen.get_size()
        assert self.title_font is not None
        assert self.desc_font is not None
        title = _fit_text_for_width(self.title_font, self.theme.title, int(w * 0.82))
        self._chunky_text(title, w // 2, int(h * 0.115), self.title_font, self.theme.title_fill, self.theme.title_outline, self.theme.title_shadow, outline_size=5)
        subtitle = _fit_text_for_width(self.desc_font, "MAIN MENU // JUNGLE CANOPY", int(w * 0.72))
        surf = self.desc_font.render(subtitle, True, self.theme.boomerang_accent)
        screen.blit(surf, surf.get_rect(center=(w // 2, int(h * 0.185))))

    def _draw_group_label(self) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        assert self.group_font is not None
        w, h = screen.get_size()
        selected_group = getattr(self.menu, "selected_group", getattr(self.menu.selected_item, "group", "System / Companion"))
        panel = pygame.Rect(int(w * 0.22), int(h * 0.205), int(w * 0.56), max(28, int(h * 0.055)))
        pygame.draw.rect(screen, (12, 60, 28), panel, border_radius=panel.height // 2)
        pygame.draw.rect(screen, self.theme.boomerang_accent, panel, 3, border_radius=panel.height // 2)
        group_text = _fit_text_for_width(self.group_font, str(selected_group).upper(), panel.width - 28)
        surf = self.group_font.render(group_text, True, self.theme.leaf_glow)
        screen.blit(surf, surf.get_rect(center=panel.center))

    def _draw_items(self) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        assert self.item_font is not None
        assert self.desc_font is not None
        w, h = screen.get_size()
        start_y = int(h * 0.285)
        row_h = self.menu.touch_config.row_height_px
        left = int(w * 0.10)
        right = int(w * 0.90)
        width = right - left
        panel_pad = max(20, int(width * 0.035))
        for row, (absolute_index, item) in enumerate(self.menu.visible_items()):
            y = start_y + row * row_h
            selected = absolute_index == self.menu.selected_index
            command = getattr(item, "command", "")
            is_boomerang = command == "boomerang"
            is_eucalyptus = command == "eucalyptus_mode"
            rect = pygame.Rect(left, y, width, int(row_h * 0.84))
            inner = rect.inflate(-panel_pad, -max(10, int(rect.height * 0.15)))
            fill = self.theme.selected_fill if selected else self.theme.item_fill
            outline_color = self.theme.selected_outline if selected else self.theme.item_outline
            if is_boomerang:
                outline_color = self.theme.boomerang_accent if selected else (167, 94, 28)
            if not item.enabled:
                fill = self.theme.disabled_fill
            if selected:
                glow = rect.inflate(18, 14)
                pygame.draw.rect(screen, self.theme.selected_glow, glow, border_radius=max(20, glow.height // 2), width=3)
                self._leaf((rect.left - 26, rect.centery), 22, 0)
                self._leaf((rect.right + 26, rect.centery), 22, 180)
            pygame.draw.rect(screen, fill, rect, border_radius=max(20, rect.height // 2))
            pygame.draw.rect(screen, outline_color, rect, width=max(3, int(row_h * 0.045)), border_radius=max(20, rect.height // 2))
            label = f"{absolute_index + 1:02d}. {item.label}"
            if not item.enabled:
                label += "  LOCKED"
            if is_eucalyptus:
                label = f"🌿 {label}"
            elif is_boomerang:
                label = f"🪃 {label}"
            label = _fit_text_for_width(self.item_font, label, inner.width)
            text_fill = self.theme.item_outline if selected else self.theme.item_shadow
            label_y = inner.top + int(inner.height * 0.30) if selected else rect.centery
            self._chunky_text(label, rect.centerx, label_y, self.item_font, text_fill, fill, self.theme.title_shadow, outline_size=2)
            if selected:
                badge = _mode_badge(command)
                desc = str(getattr(item, "description", "") or "")
                detail = f"{badge} — {desc}" if badge and desc else (badge or desc)
                max_desc_width = inner.width
                detail_lines = _wrap_for_width(self.desc_font, detail, max_desc_width, max_lines=GRAPHICAL_DESCRIPTION_MAX_LINES)
                first_y = inner.top + int(inner.height * 0.56)
                line_step = self.desc_font.get_height() + 2
                max_y = inner.bottom - self.desc_font.get_height() // 2
                for idx, line in enumerate(detail_lines):
                    center_y = min(first_y + idx * line_step, max_y)
                    line = _fit_text_for_width(self.desc_font, line, max_desc_width)
                    surf = self.desc_font.render(line, True, self.theme.item_shadow)
                    screen.blit(surf, surf.get_rect(center=(rect.centerx, center_y)))

    def _draw_footer(self) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        assert self.desc_font is not None
        w, h = screen.get_size()
        footer = "B1 MENU   B2 BACK   B3 SELECT   B4 NEXT   B5 UP   B6 DOWN"
        rect = pygame.Rect(int(w * 0.13), int(h * 0.91), int(w * 0.74), max(30, int(h * 0.055)))
        pygame.draw.rect(screen, (7, 34, 22), rect, border_radius=rect.height // 2)
        pygame.draw.rect(screen, self.theme.leaf_glow, rect, 2, border_radius=rect.height // 2)
        footer = _fit_text_for_width(self.desc_font, footer, rect.width - 18)
        surf = self.desc_font.render(footer, True, self.theme.leaf_glow)
        screen.blit(surf, surf.get_rect(center=rect.center))

    def _chunky_text(self, text: str, x: int, y: int, font: Any, fill: Color, outline_color: Color, shadow_color: Color, outline_size: int = 3) -> None:
        screen = self.screen
        assert screen is not None
        shadow_surf = font.render(text, True, shadow_color)
        outline_surf = font.render(text, True, outline_color)
        fill_surf = font.render(text, True, fill)
        screen.blit(shadow_surf, shadow_surf.get_rect(center=(x + outline_size + 2, y + outline_size + 3)))
        for dx in range(-outline_size, outline_size + 1):
            for dy in range(-outline_size, outline_size + 1):
                if dx * dx + dy * dy <= outline_size * outline_size:
                    screen.blit(outline_surf, outline_surf.get_rect(center=(x + dx, y + dy)))
        screen.blit(fill_surf, fill_surf.get_rect(center=(x, y)))


def _selected_quit(event: Optional[Any]) -> bool:
    return event is not None and event.event_type in {"select", "touch_long_press_select"} and event.command == "quit"


def run_jungle_menu(*, fullscreen: bool = True, width: int = 800, height: int = 480) -> int:
    return JungleMenuRenderer(fullscreen=fullscreen, width=width, height=height).run()
