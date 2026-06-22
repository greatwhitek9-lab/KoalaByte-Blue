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

    The visual target is the chunky PORKCHOP-like handheld firmware look:
    dark jungle/cyber background, oversized rounded title text, yellow-green
    menu typography, orange action accents, and bright selected rows.
    No third-party font files are bundled in the repo.
    """

    title: str = "KOALABYTE BLUE"
    font_family: str = "cooperblack,arialroundedmsbold,dejavusans"
    item_font_family: str = "cooperblack,arialroundedmsbold,dejavusans"
    border_style: str = "porkchop_style_eucalyptus_branches"
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
    "koala_konnect_t114": "CANOPY KONNECT // T114 USB-HCI vine bridge",
    "koala_konnect_t114_build_only": "CANOPY CHECK // Zephyr trail build only",
    "t114_bluez_controller_check": "T114 VINE HCI // controller-check trail marker",
    "t114_bluez_all_safe": "T114 CANOPY SWEEP // local safe checks only",
    "meshtastic_status": "GUMLEAF MESH // protected status trail",
    "meshtastic_nodes": "BILLABONG NODES // authorized mesh view",
    "greatwhite_status": "GREATWHITE REEF // tshark readiness patrol",
    "greatwhite_interfaces": "INTERFACE LAGOON // choose owned lab waters",
    "nrf_sniffer_check": "SNIFFER NEST // Nordic extcap host-side check",
}


def _mode_badge(command: str) -> str:
    return _MODE_BADGES.get(command, "")


def render_terminal_jungle_menu(menu: Any, theme: JungleMenuTheme = DEFAULT_JUNGLE_MENU_THEME) -> str:
    """Render a terminal-safe preview of the grouped PORKCHOP-style jungle menu."""

    visible = menu.visible_items()
    total = len(menu.items)
    selected_group = getattr(menu, "selected_group", getattr(menu.selected_item, "group", "System / Companion"))
    width = 74
    top = f"{_TERMINAL_BRANCH}" + "═" * (width - 2) + f"{_TERMINAL_BRANCH}"
    title = f"  {theme.title}  "
    header = title.center(width)
    sub = f"  {selected_group.upper()}  ({menu.selected_index + 1}/{total})  ".center(width)
    lines = [top, header, sub, top]
    previous_group: Optional[str] = None
    for absolute_index, item in visible:
        group = getattr(item, "group", "System / Companion")
        if group != previous_group:
            group_label = f"  [{group}]  "
            lines.append(group_label.center(width))
            previous_group = group
        selected = absolute_index == menu.selected_index
        marker = "➤" if selected else " "
        left_leaf = "🌿" if selected else " "
        right_leaf = "🌿" if selected else " "
        disabled = " [locked]" if not item.enabled else ""
        label = f"{marker} {absolute_index + 1:02d}. {item.label}{disabled}"
        lines.append(f"{left_leaf} {label:<68} {right_leaf}")
        if selected:
            badge = _mode_badge(getattr(item, "command", ""))
            if badge:
                lines.append(f"  {'     ' + badge:<70}")
            if item.description:
                for desc in textwrap.wrap(str(item.description), width=64)[:2]:
                    lines.append(f"  {'     ' + desc:<70}")
    lines.append(top)
    lines.append("Buttons: B1 menu | B2 prev/back | B3 select/hold shutdown | B4 next | B5 up | B6 down")
    lines.append("Touch: drag/scroll through eucalyptus branches | long press to select")
    return "\n".join(lines)


def render_terminal_eucalyptus_card(title: str, rows: Iterable[str], subtitle: str = "THAT’S NOT A KNIFE", theme: JungleMenuTheme = DEFAULT_JUNGLE_MENU_THEME) -> str:
    """Render a terminal-safe status card in the same chunky menu style."""

    width = 74
    top = f"{_TERMINAL_BRANCH}" + "═" * (width - 2) + f"{_TERMINAL_BRANCH}"
    lines = [top]
    lines.append(f"  {theme.title}  ".center(width))
    lines.append(f"  {subtitle.upper()}  ".center(width))
    lines.append(f"  style: chunky yellow/green firmware menu | border: {theme.border_style}  ".center(width))
    lines.append(top)
    lines.append(f"🌿 {title[:68]:<68} 🌿")
    for row in rows:
        text = str(row)
        while len(text) > 68:
            lines.append(f"  {text[:68]:<70}")
            text = text[68:]
        lines.append(f"  {text:<70}")
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


def _wrap_for_width(font: Any, text: str, max_width: int, max_lines: int = 2) -> list[str]:
    if not text:
        return []
    lines: list[str] = []
    current = ""
    words = str(text).split()
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if font.size(candidate)[0] <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines:
        used = " ".join(lines)
        if len(used) < len(text):
            last = lines[-1]
            while font.size(last + "…")[0] > max_width and len(last) > 4:
                last = last[:-1]
            lines[-1] = last + "…"
    return lines


class JungleMenuRenderer:
    """Pygame renderer for the KoalaByte Blue PORKCHOP-style grouped menu."""

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
        self._touch_down_y: Optional[int] = None
        self._touch_down_at: Optional[float] = None

    def setup(self) -> None:
        pygame = self.pygame
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        pygame.init()
        flags = pygame.FULLSCREEN if self.fullscreen else 0
        self.screen = pygame.display.set_mode((0, 0), flags) if self.fullscreen else pygame.display.set_mode((self.width, self.height), flags)
        pygame.display.set_caption("KoalaByte Blue Main Menu")
        self.clock = pygame.time.Clock()
        w, h = self.screen.get_size()
        self.title_font = _pick_font(pygame, self.theme.font_family, max(36, min(82, int(w * 0.076))), bold=True)
        self.item_font = _pick_font(pygame, self.theme.item_font_family, max(20, min(44, int(w * 0.039))), bold=True)
        self.group_font = _pick_font(pygame, self.theme.item_font_family, max(18, min(30, int(w * 0.03))), bold=True)
        self.desc_font = pygame.font.SysFont("dejavusans", max(13, min(20, int(w * 0.018))), bold=True)
        self.menu.touch_config.row_height_px = max(76, int(h * 0.145))
        self.menu.visible_rows = max(3, min(5, int((h * 0.62) / self.menu.touch_config.row_height_px)))
        self.menu._clamp_scroll_to_selection()

    def run(self) -> int:
        self.setup()
        pygame = self.pygame
        while True:
            event_result = self._handle_events()
            if event_result == "quit":
                return 0
            self.draw()
            pygame.display.flip()
            self.clock.tick(self.fps)

    def _handle_events(self) -> Optional[str]:
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
        bark = self.theme.bark
        hi = self.theme.bark_highlight
        leaf = self.theme.leaf
        leaf_glow = self.theme.leaf_glow
        for i in range(3):
            pygame.draw.rect(screen, bark if i == 0 else hi, (margin - i * 2, margin - i * 2, w - 2 * margin + i * 4, h - 2 * margin + i * 4), max(2, margin // 5), border_radius=20)
        for i in range(18):
            angle = (i / 18.0) * math.tau
            x = int(w / 2 + math.cos(angle) * (w / 2 - margin * 1.5))
            y = int(h / 2 + math.sin(angle) * (h / 2 - margin * 1.5))
            pygame.draw.ellipse(screen, leaf_darken(leaf, 0.75), (x - 12, y - 6, 24, 12))
            pygame.draw.ellipse(screen, leaf_glow if i % 5 == 0 else leaf, (x - 8, y - 4, 16, 8))

    def _draw_title(self) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        font = self.title_font
        assert font is not None
        w, _h = screen.get_size()
        text = self.theme.title
        surf_shadow = font.render(text, True, self.theme.title_shadow)
        surf_outline = font.render(text, True, self.theme.title_outline)
        surf_fill = font.render(text, True, self.theme.title_fill)
        x = (w - surf_fill.get_width()) // 2
        y = 22
        for dx, dy in [(-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2)]:
            screen.blit(surf_outline, (x + dx, y + dy))
        screen.blit(surf_shadow, (x + 5, y + 6))
        screen.blit(surf_fill, (x, y))
        inner = font.render("BLUE", True, self.theme.title_inner)
        screen.blit(inner, (x + max(0, surf_fill.get_width() - inner.get_width()) // 2, y + int(surf_fill.get_height() * 0.44)))

    def _draw_group_label(self) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        font = self.group_font
        assert font is not None
        w, _h = screen.get_size()
        group = getattr(self.menu.selected_item, "group", "System / Companion")
        label = f"🌿 {group.upper()} 🌿"
        surf = font.render(label, True, self.theme.leaf_glow)
        rect = surf.get_rect(center=(w // 2, 116))
        pygame.draw.rect(screen, (2, 35, 18), rect.inflate(28, 12), border_radius=14)
        pygame.draw.rect(screen, self.theme.selected_outline, rect.inflate(28, 12), 2, border_radius=14)
        screen.blit(surf, rect)

    def _draw_items(self) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        item_font = self.item_font
        desc_font = self.desc_font
        assert item_font is not None and desc_font is not None
        w, h = screen.get_size()
        start_y = 146
        row_h = max(70, int(h * 0.13))
        visible = self.menu.visible_items()
        for absolute_index, item in visible:
            row = absolute_index - self.menu.scroll_offset
            y = start_y + row * row_h
            selected = absolute_index == self.menu.selected_index
            x = max(34, int(w * 0.06))
            width = w - x * 2
            if selected:
                pulse = (math.sin(time.time() * 4) + 1) / 2
                glow = tuple(min(255, int(self.theme.selected_glow[i] * (0.35 + 0.65 * pulse))) for i in range(3))
                pygame.draw.rect(screen, glow, (x - 8, y - 5, width + 16, row_h - 8), border_radius=22)
                pygame.draw.rect(screen, self.theme.selected_outline, (x, y, width, row_h - 16), 4, border_radius=18)
                fill_color = self.theme.selected_fill
            else:
                pygame.draw.rect(screen, (3, 30, 15), (x, y, width, row_h - 16), border_radius=16)
                pygame.draw.rect(screen, self.theme.item_outline, (x, y, width, row_h - 16), 2, border_radius=16)
                fill_color = self.theme.item_fill if item.enabled else self.theme.disabled_fill
            label = f"{absolute_index + 1:02d}  {item.label}"
            shadow = item_font.render(label, True, self.theme.item_shadow)
            surf = item_font.render(label, True, fill_color)
            screen.blit(shadow, (x + 18 + 3, y + 9 + 3))
            screen.blit(surf, (x + 18, y + 9))
            if selected and item.description:
                for idx, desc in enumerate(_wrap_for_width(desc_font, str(item.description), width - 36, max_lines=2)):
                    d = desc_font.render(desc, True, self.theme.blue_accent)
                    screen.blit(d, (x + 22, y + 42 + idx * 20))

    def _draw_footer(self) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        w, h = screen.get_size()
        font = self.desc_font
        assert font is not None
        text = "B1 menu  B2 back  B3 select/hold shutdown  B4 next  B5 up  B6 down  |  Touch: drag canopy / long-press select"
        surf = font.render(text, True, self.theme.leaf_glow)
        screen.blit(surf, ((w - surf.get_width()) // 2, h - 34))


def leaf_darken(color: Color, factor: float) -> Color:
    return tuple(max(0, int(c * factor)) for c in color)  # type: ignore[return-value]


def _selected_quit(event: Any) -> bool:
    return event is not None and getattr(event, "event_type", "") in {"select", "touch_long_press_select"} and getattr(event, "command", "") == "quit"


def main() -> int:
    renderer = JungleMenuRenderer(fullscreen=False)
    return renderer.run()


if __name__ == "__main__":
    raise SystemExit(main())
