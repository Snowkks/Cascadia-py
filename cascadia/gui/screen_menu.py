"""
screen_menu.py - Win98-style main menu window.
"""
import pygame
from cascadia.constants import WINDOW_WIDTH, WINDOW_HEIGHT, COLORS
from cascadia.utils import (bevel_rect, fill_bevel_rect, draw_window,
                             draw_text, draw_title_bar)
from cascadia.gui.resources import get_font, get_title_font
from cascadia.gui.widgets import Button


class MenuScreen:
    def __init__(self, on_new_game, on_leaderboard, on_quit):
        self.on_new_game    = on_new_game
        self.on_leaderboard = on_leaderboard
        self.on_quit        = on_quit

        self._title_f = get_title_font(20)
        self._body_f  = get_font(14)
        self._small_f = get_font(13)

        # Centre window
        win_w, win_h = 340, 320
        wx = (WINDOW_WIDTH  - win_w) // 2
        wy = (WINDOW_HEIGHT - win_h) // 2
        self._win_rect = pygame.Rect(wx, wy, win_w, win_h)

        bx  = wx + 50
        bw, bh = 240, 34
        self._buttons = [
            Button(pygame.Rect(bx, wy + 80,  bw, bh), "New Game",    on_new_game),
            Button(pygame.Rect(bx, wy + 130, bw, bh), "Leaderboard", on_leaderboard),
            Button(pygame.Rect(bx, wy + 180, bw, bh), "Quit",        on_quit),
        ]

    def handle_event(self, event):
        for btn in self._buttons:
            btn.handle_event(event)

    def update(self, dt):
        pass

    def draw(self, surface):
        # Desktop background
        surface.fill(COLORS["bg_dark"])

        # Draw window chrome
        draw_window(surface, self._win_rect, "Cascadia", self._title_f, title_h=24)

        # Game title inside window
        cx = self._win_rect.centerx
        ty = self._win_rect.y + 34
        draw_text(surface, "CASCADIA", get_title_font(28),
                  COLORS["text_dark"], cx, ty, align="center")
        draw_text(surface, "Pacific Northwest Wilderness Game",
                  self._small_f, COLORS["text_muted"], cx, ty + 36, align="center")

        # Separator line
        pygame.draw.line(surface, COLORS["bevel_shadow"],
                         (self._win_rect.x + 12, ty + 58),
                         (self._win_rect.right - 12, ty + 58))
        pygame.draw.line(surface, COLORS["bevel_light"],
                         (self._win_rect.x + 12, ty + 59),
                         (self._win_rect.right - 12, ty + 59))

        for btn in self._buttons:
            btn.draw(surface)

        # Status bar at bottom of window
        sb = pygame.Rect(self._win_rect.x + 2,
                         self._win_rect.bottom - 22,
                         self._win_rect.width - 4, 20)
        pygame.draw.rect(surface, COLORS["bg_panel"], sb)
        bevel_rect(surface, sb, raised=False, width=1)
        draw_text(surface, "Digital Edition v1.0", self._small_f,
                  COLORS["text_muted"], sb.x + 6, sb.y + 3)
