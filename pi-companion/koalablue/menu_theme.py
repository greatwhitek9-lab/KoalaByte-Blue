from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass
from typing import Any, Optional, Tuple

Color = Tuple[int, int, int]


@dataclass(frozen=True)
class JungleMenuTheme:
    """KoalaByte Blue menu styling.

    The theme approximates a large rounded adventure/jungle title look using
    system fonts. No third-party font files are bundled in the repo.
    """

    title: str = "KoalaByte Blue"
    font_family: str = "cooperblack,arialroundedmsbold,dejavusans"
    item_font_family: str = "cooperblack,arialroundedmsbold,dejavusans"
    border_style: str = "eucalyptus_branches"
    background: Color = (2, 8, 8)
    bark: Color = (73, 58, 34)
    bark_highlight: Color = (123, 94, 50)
    leaf: Color = (93, 168, 112)
    leaf_dark: Color = (34, 95, 62)
    leaf_glow: Color = (152, 225, 168)
    title_fill: Color = (143, 221, 103)
    title_outline: Color = (28, 67, 38)
    item_fill: Color = (245, 236, 158)
    item_outline: Color = (31, 84, 44)
    item_shadow: Color = (9, 30, 20)
    selected_fill: Color = (190, 246, 124)
    selected_outline: Color = (49, 170, 82)
    selected_glow: Color = (123, 245, 144)
    disabled_fill: Color = (112, 119, 104)
    blue_accent: Color = (70, 170, 255)


DEFAULT_JUNGLE_MENU_THEME = JungleMenuTheme()
_TERMINAL_BRANCH = "🌿"


def render_terminal_jungle_menu(menu: Any, theme: JungleMenuTheme = DEFAULT_JUNGLE_MENU_THEME) -> str:
    """Render a terminal-safe preview of the grouped jungle menu theme."""

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
        if selected and item.description:
            desc = f"     {item.description}"
            lines.append(f"  {desc:<70}")
    lines.append(top)
    lines.append("Buttons: B1 menu | B2 prev/back | B3 select/hold shutdown | B4 next | B5 up | B6 down")
    lines.append("Touch: drag/scroll through eucalyptus branches | long press to select")
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


class JungleMenuRenderer:
    """Pygame renderer for the KoalaByte Blue jungle-styled grouped menu."""

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
        self.small_font = None
        self.group_font = None
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
        self.title_font = _pick_font(pygame, self.theme.font_family, max(34, min(78, int(w * 0.073))), bold=True)
        self.item_font = _pick_font(pygame, self.theme.item_font_family, max(24, min(52, int(w * 0.046))), bold=True)
        self.group_font = _pick_font(pygame, self.theme.item_font_family, max(18, min(30, int(w * 0.03))), bold=True)
        self.small_font = pygame.font.SysFont("dejavusans", max(14, min(22, int(w * 0.018))), bold=True)
        self.menu.touch_config.row_height_px = max(64, int(h * 0.13))
        self.menu.visible_rows = max(3, min(6, int((h * 0.60) / self.menu.touch_config.row_height_px)))
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
        screen.fill(self.theme.background)
        self._draw_leafy_border()
        self._draw_title()
        self._draw_group_label()
        self._draw_items()
        self._draw_footer()

    def _draw_leafy_border(self) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        w, h = screen.get_size()
        margin = max(16, int(min(w, h) * 0.035))
        stem_width = max(4, int(min(w, h) * 0.012))
        pygame.draw.line(screen, self.theme.bark, (margin, margin), (w - margin, margin), stem_width)
        pygame.draw.line(screen, self.theme.bark, (margin, h - margin), (w - margin, h - margin), stem_width)
        pygame.draw.line(screen, self.theme.bark, (margin, margin), (margin, h - margin), stem_width)
        pygame.draw.line(screen, self.theme.bark, (w - margin, margin), (w - margin, h - margin), stem_width)
        pygame.draw.line(screen, self.theme.bark_highlight, (margin, margin - 2), (w - margin, margin - 2), 1)
        spacing = max(34, int(w * 0.055))
        for x in range(margin + 18, w - margin, spacing):
            self._leaf((x, margin - 3), 16, -25)
            self._leaf((x + spacing // 3, h - margin + 2), 16, 155)
        spacing_y = max(32, int(h * 0.095))
        for y in range(margin + 22, h - margin, spacing_y):
            self._leaf((margin - 2, y), 16, 65)
            self._leaf((w - margin + 2, y + spacing_y // 3), 16, 245)

    def _leaf(self, center: Tuple[int, int], size: int, angle_deg: float) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        angle = math.radians(angle_deg)
        sx = math.cos(angle) * size * 0.45
        sy = math.sin(angle) * size * 0.45
        rect = pygame.Rect(0, 0, int(size * 1.4), int(size * 0.72))
        rect.center = center
        pygame.draw.ellipse(screen, self.theme.leaf_dark, rect)
        pygame.draw.line(screen, self.theme.leaf_glow, (int(center[0] - sx), int(center[1] - sy)), (int(center[0] + sx), int(center[1] + sy)), 1)
        inner = rect.inflate(-max(2, size // 5), -max(2, size // 5))
        pygame.draw.ellipse(screen, self.theme.leaf, inner)

    def _draw_title(self) -> None:
        screen = self.screen
        assert screen is not None
        w, h = screen.get_size()
        self._bubble_text(self.theme.title, w // 2, int(h * 0.12), self.title_font, self.theme.title_fill, self.theme.title_outline, outline_size=4)

    def _draw_group_label(self) -> None:
        screen = self.screen
        assert screen is not None
        w, h = screen.get_size()
        selected_group = getattr(self.menu, "selected_group", getattr(self.menu.selected_item, "group", "System / Companion"))
        surf = self.group_font.render(selected_group.upper(), True, self.theme.leaf_glow)
        screen.blit(surf, surf.get_rect(center=(w // 2, int(h * 0.205))))

    def _draw_items(self) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        w, h = screen.get_size()
        start_y = int(h * 0.27)
        row_h = self.menu.touch_config.row_height_px
        left = int(w * 0.12)
        right = int(w * 0.88)
        width = right - left
        for row, (absolute_index, item) in enumerate(self.menu.visible_items()):
            y = start_y + row * row_h
            selected = absolute_index == self.menu.selected_index
            rect = pygame.Rect(left, y, width, int(row_h * 0.78))
            fill = self.theme.selected_fill if selected else self.theme.item_fill
            outline_color = self.theme.selected_outline if selected else self.theme.item_outline
            if not item.enabled:
                fill = self.theme.disabled_fill
            if selected:
                glow = rect.inflate(18, 14)
                pygame.draw.rect(screen, self.theme.selected_glow, glow, border_radius=max(20, glow.height // 2), width=3)
                self._leaf((rect.left - 26, rect.centery), 22, 0)
                self._leaf((rect.right + 26, rect.centery), 22, 180)
            pygame.draw.rect(screen, fill, rect, border_radius=max(18, rect.height // 2))
            pygame.draw.rect(screen, outline_color, rect, width=max(3, int(row_h * 0.045)), border_radius=max(18, rect.height // 2))
            label = f"{absolute_index + 1:02d}. {item.label}"
            if not item.enabled:
                label += "  LOCKED"
            text_fill = self.theme.item_outline if selected else self.theme.item_shadow
            self._bubble_text(label, rect.centerx, rect.centery, self.item_font, text_fill, fill, outline_size=2)

    def _draw_footer(self) -> None:
        screen = self.screen
        assert screen is not None
        w, h = screen.get_size()
        footer = "B1 menu  B2 back  B3 select/hold shutdown  B4 next  B5 up  B6 down   |   touch drag / long press"
        surf = self.small_font.render(footer, True, self.theme.leaf_glow)
        screen.blit(surf, surf.get_rect(center=(w // 2, int(h * 0.94))))

    def _bubble_text(self, text: str, x: int, y: int, font: Any, fill: Color, outline_color: Color, outline_size: int = 3) -> None:
        screen = self.screen
        assert screen is not None
        outline_surf = font.render(text, True, outline_color)
        fill_surf = font.render(text, True, fill)
        for dx in range(-outline_size, outline_size + 1):
            for dy in range(-outline_size, outline_size + 1):
                if dx * dx + dy * dy <= outline_size * outline_size:
                    screen.blit(outline_surf, outline_surf.get_rect(center=(x + dx, y + dy)))
        screen.blit(fill_surf, fill_surf.get_rect(center=(x, y)))


def _selected_quit(event: Optional[Any]) -> bool:
    return event is not None and event.event_type in {"select", "touch_long_press_select"} and event.command == "quit"


def run_jungle_menu(*, fullscreen: bool = True, width: int = 800, height: int = 480) -> int:
    return JungleMenuRenderer(fullscreen=fullscreen, width=width, height=height).run()
