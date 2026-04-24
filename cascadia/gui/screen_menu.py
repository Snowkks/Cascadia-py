"""
screen_menu.py  –  Main menu.

Window (centred, 300×260):
  y+0   ┌─────────────────────────────┐  ← outer raised bevel
  y+2   │▓▓▓▓▓ CASCADIA ▓▓▓▓▓▓▓▓▓▓▓▓│  ← title bar (24px)
  y+26  ├─────────────────────────────┤
  y+36  │   CASCADIA  (big text)      │
  y+60  │   subtitle                  │
  y+80  │──────────────────────────── │  ← separator
  y+96  │  [ New Game ]               │
  y+140 │  [ Leaderboard ]            │
  y+184 │  [ Quit ]                   │
  y+228 │  v1.0 text                  │
  y+250 └─────────────────────────────┘
"""
import pygame
from cascadia.constants import WINDOW_WIDTH as W, WINDOW_HEIGHT as H, COLORS
from cascadia.utils import bevel_rect, fill_bevel_rect, draw_title_bar, draw_text
from cascadia.gui.resources import get_font, get_title_font
from cascadia.gui.widgets import Button

WIN_W = 300
WIN_H = 260
TITLE_H = 24


class MenuScreen:
    def __init__(self, on_new_game, on_leaderboard, on_quit):
        # Window top-left
        self._wx = (W - WIN_W) // 2
        self._wy = (H - WIN_H) // 2
        wx, wy = self._wx, self._wy

        # Content starts below title bar + 2px bevel
        cy = wy + 2 + TITLE_H   # = wy + 26

        self._tf  = get_title_font(16)
        self._big = get_title_font(26)
        self._sub = get_font(13)
        self._sm  = get_font(12)

        # Buttons — centred inside the window
        bx = wx + (WIN_W - 220) // 2
        bw, bh = 220, 34
        self._btns = [
            Button(pygame.Rect(bx, cy + 70,  bw, bh), "New Game",    on_new_game),
            Button(pygame.Rect(bx, cy + 114, bw, bh), "Leaderboard", on_leaderboard),
            Button(pygame.Rect(bx, cy + 158, bw, bh), "Quit",        on_quit),
        ]

    def handle_event(self, event):
        for b in self._btns: b.handle_event(event)

    def update(self, dt): pass

    def draw(self, surface):
        surface.fill(COLORS["bg_dark"])
        wx, wy = self._wx, self._wy

        # Outer window bevel + face
        win_rect = pygame.Rect(wx, wy, WIN_W, WIN_H)
        fill_bevel_rect(surface, win_rect, raised=True)

        # Title bar
        tb = pygame.Rect(wx + 2, wy + 2, WIN_W - 4, TITLE_H)
        draw_title_bar(surface, tb, "Cascadia", self._tf)

        # Client area background
        client = pygame.Rect(wx + 2, wy + 2 + TITLE_H,
                             WIN_W - 4, WIN_H - 4 - TITLE_H)
        pygame.draw.rect(surface, COLORS["bg_panel"], client)

        # Content starts here
        cy = wy + 2 + TITLE_H
        cx = wx + WIN_W // 2

        # Big title
        draw_text(surface, "CASCADIA", self._big, COLORS["text_dark"],
                  cx, cy + 10, align="center")
        draw_text(surface, "Pacific Northwest Wilderness", self._sub,
                  COLORS["text_muted"], cx, cy + 44, align="center")

        # Separator
        sep_y = cy + 64
        pygame.draw.line(surface, COLORS["bevel_shadow"],
                         (wx + 10, sep_y), (wx + WIN_W - 10, sep_y))
        pygame.draw.line(surface, COLORS["bevel_light"],
                         (wx + 10, sep_y + 1), (wx + WIN_W - 10, sep_y + 1))

        # Buttons
        for b in self._btns:
            b.draw(surface)

        # Version
        draw_text(surface, "Digital Edition v1.0", self._sm,
                  COLORS["text_muted"], cx, wy + WIN_H - 18, align="center")
