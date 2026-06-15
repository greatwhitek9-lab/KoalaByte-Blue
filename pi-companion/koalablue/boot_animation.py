from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass
from typing import Optional, Tuple


Color = Tuple[int, int, int]


@dataclass
class BootAnimationConfig:
    duration_seconds: float = 3.0
    fps: int = 30
    fullscreen: bool = True
    width: int = 800
    height: int = 480
    title: str = "KoalaByte Blue"


class BootSplashUnavailable(RuntimeError):
    pass


def _import_pygame():
    try:
        import pygame  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on Pi display environment
        raise BootSplashUnavailable(f"pygame unavailable: {exc}") from exc
    return pygame


class KoalaByteBootAnimation:
    """Fullscreen Pi companion boot splash.

    Draws a procedural KoalaByte Blue boot screen with pulsing eyes and an
    advancing progress bar. This intentionally avoids binary image assets so the
    splash remains easy to version, install, and tune on the Pi.
    """

    def __init__(self, config: Optional[BootAnimationConfig] = None) -> None:
        self.config = config or BootAnimationConfig()
        self.pygame = _import_pygame()
        self.screen = None
        self.clock = None
        self.font_title = None
        self.font_small = None

    def setup(self) -> None:
        pygame = self.pygame
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        pygame.init()
        flags = pygame.FULLSCREEN if self.config.fullscreen else 0
        if self.config.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), flags)
        else:
            self.screen = pygame.display.set_mode((self.config.width, self.config.height), flags)
        pygame.display.set_caption("KoalaByte Blue Boot")
        self.clock = pygame.time.Clock()
        w, h = self.screen.get_size()
        title_size = max(28, min(72, int(w * 0.058)))
        small_size = max(13, min(24, int(w * 0.018)))
        self.font_title = pygame.font.SysFont("dejavusansmono", title_size, bold=True)
        self.font_small = pygame.font.SysFont("dejavusansmono", small_size)

    def run(self) -> int:
        self.setup()
        pygame = self.pygame
        start = time.monotonic()
        total = max(0.25, self.config.duration_seconds)

        while True:
            elapsed = time.monotonic() - start
            progress = min(1.0, elapsed / total)
            pulse = 0.5 + 0.5 * math.sin(elapsed * math.tau * 2.8)
            self.draw(progress, pulse)
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return 0
                if event.type == pygame.KEYDOWN and event.key in {pygame.K_ESCAPE, pygame.K_q}:
                    return 0

            if progress >= 1.0:
                time.sleep(0.18)
                return 0
            self.clock.tick(self.config.fps)

    def draw(self, progress: float, pulse: float) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        w, h = screen.get_size()
        base = min(w, h)
        cx = w // 2
        cy = int(h * 0.36)

        black: Color = (0, 0, 0)
        face: Color = (6, 8, 12)
        edge: Color = (30, 34, 44)
        nose: Color = (54, 57, 65)
        nose_edge: Color = (118, 120, 132)
        tooth: Color = (185, 188, 202)
        purple: Color = (235, 70, 255)
        purple_dim: Color = (72, 8, 105)
        blue: Color = (70, 170, 255)
        blue_dim: Color = (6, 40, 115)
        text_gray: Color = (120, 122, 136)

        screen.fill(black)

        def sc(v: float) -> int:
            return int(v * base)

        # Koala silhouette.
        ear_r = sc(0.15)
        head_r = sc(0.27)
        pygame.draw.circle(screen, face, (cx - sc(0.32), cy - sc(0.21)), ear_r)
        pygame.draw.circle(screen, face, (cx + sc(0.32), cy - sc(0.21)), ear_r)
        pygame.draw.circle(screen, edge, (cx - sc(0.32), cy - sc(0.21)), ear_r, max(1, sc(0.006)))
        pygame.draw.circle(screen, edge, (cx + sc(0.32), cy - sc(0.21)), ear_r, max(1, sc(0.006)))
        pygame.draw.circle(screen, face, (cx, cy), head_r)
        pygame.draw.circle(screen, edge, (cx, cy), head_r, max(1, sc(0.006)))

        # Brows.
        brow_w = max(2, sc(0.012))
        pygame.draw.line(screen, edge, (cx - sc(0.22), cy - sc(0.12)), (cx - sc(0.04), cy - sc(0.02)), brow_w)
        pygame.draw.line(screen, edge, (cx + sc(0.22), cy - sc(0.12)), (cx + sc(0.04), cy - sc(0.02)), brow_w)

        # Eye glow, left purple and right actually blue.
        eye_r = sc(0.047) + int(pulse * sc(0.017))
        self._glow_circle((cx - sc(0.135), cy - sc(0.035)), eye_r, (255, 226, 255), purple, purple_dim, pulse)
        self._glow_circle((cx + sc(0.135), cy - sc(0.035)), eye_r, (232, 246, 255), blue, blue_dim, pulse)

        # Nose and teeth.
        nose_rect = pygame.Rect(0, 0, sc(0.15), sc(0.22))
        nose_rect.center = (cx, cy + sc(0.11))
        pygame.draw.rect(screen, nose, nose_rect, border_radius=max(8, sc(0.04)))
        pygame.draw.rect(screen, nose_edge, nose_rect, max(1, sc(0.005)), border_radius=max(8, sc(0.04)))

        mouth_y = cy + sc(0.29)
        pygame.draw.polygon(screen, tooth, [(cx - sc(0.09), mouth_y), (cx - sc(0.035), mouth_y - sc(0.04)), (cx - sc(0.01), mouth_y + sc(0.05))])
        pygame.draw.polygon(screen, tooth, [(cx + sc(0.09), mouth_y), (cx + sc(0.035), mouth_y - sc(0.04)), (cx + sc(0.01), mouth_y + sc(0.05))])
        pygame.draw.line(screen, edge, (cx - sc(0.06), mouth_y + sc(0.06)), (cx + sc(0.06), mouth_y + sc(0.06)), max(1, sc(0.006)))

        # Title: KoalaByte purple, Blue true blue.
        title_y = int(h * 0.78)
        self._draw_centered_split_text(cx, title_y, "KoalaByte", purple, "Blue", blue)

        self._draw_progress_bar(progress, purple, blue)

        small = self.font_small.render("B O O T I N G . . .", True, text_gray)
        screen.blit(small, small.get_rect(center=(cx, int(h * 0.94))))

    def _glow_circle(self, center: Tuple[int, int], radius: int, core: Color, mid: Color, outer: Color, pulse: float) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        bloom = int(radius * (1.2 + pulse * 1.8))
        pygame.draw.circle(screen, outer, center, radius + bloom)
        pygame.draw.circle(screen, mid, center, radius + bloom // 2)
        pygame.draw.circle(screen, core, center, radius)
        pygame.draw.circle(screen, (255, 255, 255), (center[0] + radius // 3, center[1] - radius // 3), max(2, radius // 6))

    def _draw_centered_split_text(self, cx: int, y: int, left: str, left_color: Color, right: str, right_color: Color) -> None:
        screen = self.screen
        assert screen is not None
        left_surf = self.font_title.render(left, True, left_color)
        gap = max(14, int(screen.get_width() * 0.018))
        right_surf = self.font_title.render(right, True, right_color)
        total_w = left_surf.get_width() + gap + right_surf.get_width()
        x = cx - total_w // 2
        screen.blit(left_surf, (x, y - left_surf.get_height() // 2))
        screen.blit(right_surf, (x + left_surf.get_width() + gap, y - right_surf.get_height() // 2))

    def _draw_progress_bar(self, progress: float, purple: Color, blue: Color) -> None:
        pygame = self.pygame
        screen = self.screen
        assert screen is not None
        w, h = screen.get_size()
        cx = w // 2
        bar_w = int(w * 0.60)
        y = int(h * 0.865)
        seg_w = max(8, int(w * 0.012))
        gap = max(4, int(w * 0.006))
        count = max(10, bar_w // (seg_w + gap))
        start_x = cx - ((count * seg_w + (count - 1) * gap) // 2)
        lit = int(count * progress)
        dim: Color = (30, 32, 42)

        pygame.draw.line(screen, purple, (start_x - 50, y + seg_w // 2), (start_x - 10, y + seg_w // 2), 1)
        pygame.draw.line(screen, blue, (start_x + count * (seg_w + gap) + 10, y + seg_w // 2), (start_x + count * (seg_w + gap) + 50, y + seg_w // 2), 1)

        for i in range(count):
            color = dim
            if i < lit:
                color = purple if i < count // 2 else blue
            rect = pygame.Rect(start_x + i * (seg_w + gap), y, seg_w, max(4, seg_w // 3))
            pygame.draw.rect(screen, color, rect, border_radius=max(2, rect.height // 2))


def run_boot_splash(config: Optional[BootAnimationConfig] = None) -> int:
    return KoalaByteBootAnimation(config).run()


if __name__ == "__main__":
    raise SystemExit(run_boot_splash())
