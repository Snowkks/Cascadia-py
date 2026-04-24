"""
screen_setup.py  –  New Game setup dialog.

Window (centred, 380×320):
  wy+0   ┌──────────────────────────────────────┐
  wy+2   │▓▓▓▓▓ New Game ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│  title bar (24px)
  wy+26  ├──────────────────────────────────────┤  client top (cy=0)
  cy+8   │  Number of players:  2  [ - ] [ + ]  │
  cy+44  │─────────────────────────────────────  │  separator
  cy+54  │  Player names:                        │
  cy+72  │    Player 1: [____________________]   │  input 0
  cy+108 │    Player 2: [____________________]   │  input 1
  cy+144 │    Player 3: [____________________]   │  input 2  (shown if num>=3)
  cy+180 │    Player 4: [____________________]   │  input 3  (shown if num>=4)
         │                                       │
  cy+228 │           [  OK  ]  [ Cancel ]        │
  cy+264 │  Tab=next · Enter=OK                  │
  wy+320 └──────────────────────────────────────┘
"""
import pygame
from cascadia.constants import (WINDOW_WIDTH as W, WINDOW_HEIGHT as H,
                                 COLORS, NUM_PLAYERS_MIN, NUM_PLAYERS_MAX)
from cascadia.utils import bevel_rect, fill_bevel_rect, draw_title_bar, draw_text
from cascadia.gui.resources import get_font, get_title_font
from cascadia.gui.widgets import Button, TextInput

WIN_W   = 380
WIN_H   = 320
TITLE_H = 24
PAD     = 8


class SetupScreen:
    def __init__(self, on_start, on_back):
        self.on_start    = on_start
        self.on_back     = on_back
        self.num_players = 2

        self._tf  = get_title_font(16)
        self._bf  = get_font(14)
        self._lf  = get_font(13)
        self._smf = get_font(12)

        # Window rect
        self._wx = (W - WIN_W) // 2
        self._wy = (H - WIN_H) // 2
        wx, wy   = self._wx, self._wy
        # Client top (below title bar + outer bevel)
        self._cy = wy + 2 + TITLE_H   # absolute y of client top

        cy = self._cy   # shorthand

        # Spinner buttons  (row at cy+8)
        self._btn_minus = Button(pygame.Rect(wx + 230, cy + 8,  28, 26), "-", self._dec)
        self._btn_plus  = Button(pygame.Rect(wx + 262, cy + 8,  28, 26), "+", self._inc)

        # Name inputs — 4 rows, each 36px tall, starting at cy+72
        self._inputs = []
        for i in range(NUM_PLAYERS_MAX):
            inp = TextInput(
                pygame.Rect(wx + 130, cy + 72 + i * 36, 220, 26),
                f"Player {i + 1}", font_size=14)
            self._inputs.append(inp)
        self._inputs[0].focused = True   # focus first field by default

        # OK / Cancel
        self._btn_ok     = Button(pygame.Rect(wx + 80,  cy + 262, 90, 30), "OK",     self._do_start)
        self._btn_cancel = Button(pygame.Rect(wx + 190, cy + 262, 90, 30), "Cancel", on_back)

    # ── helpers ───────────────────────────────────────────────────────────────
    def _dec(self):
        if self.num_players > NUM_PLAYERS_MIN:
            self.num_players -= 1

    def _inc(self):
        if self.num_players < NUM_PLAYERS_MAX:
            self.num_players += 1

    def _do_start(self):
        names = [self._inputs[i].text.strip() or f"Player {i+1}"
                 for i in range(self.num_players)]
        self.on_start(names)

    def _focused_idx(self):
        for i, inp in enumerate(self._inputs[:self.num_players]):
            if inp.focused:
                return i
        return -1

    # ── event ─────────────────────────────────────────────────────────────────
    def handle_event(self, event):
        self._btn_minus.handle_event(event)
        self._btn_plus.handle_event(event)
        self._btn_ok.handle_event(event)
        self._btn_cancel.handle_event(event)

        for i in range(self.num_players):
            self._inputs[i].handle_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self._do_start()
            elif event.key == pygame.K_ESCAPE:
                self.on_back()
            elif event.key == pygame.K_TAB:
                cur = self._focused_idx()
                for inp in self._inputs:
                    inp.focused = False
                nxt = (cur + 1) % self.num_players
                self._inputs[nxt].focused = True

    def update(self, dt): pass

    # ── draw ──────────────────────────────────────────────────────────────────
    def draw(self, surface):
        surface.fill(COLORS["bg_dark"])
        wx, wy = self._wx, self._wy
        cy     = self._cy

        # Window chrome
        win_rect = pygame.Rect(wx, wy, WIN_W, WIN_H)
        fill_bevel_rect(surface, win_rect, raised=True)
        tb = pygame.Rect(wx + 2, wy + 2, WIN_W - 4, TITLE_H)
        draw_title_bar(surface, tb, "New Game", self._tf)
        client = pygame.Rect(wx + 2, cy, WIN_W - 4, WIN_H - 4 - TITLE_H)
        pygame.draw.rect(surface, COLORS["bg_panel"], client)

        # ── Number of players row ─────────────────────────────────────────────
        draw_text(surface, "Number of players:", self._bf,
                  COLORS["text_dark"], wx + PAD + 10, cy + 12)
        draw_text(surface, str(self.num_players), self._bf,
                  COLORS["text_dark"], wx + 210, cy + 12)
        self._btn_minus.draw(surface)
        self._btn_plus.draw(surface)

        # ── Separator ─────────────────────────────────────────────────────────
        sep_y = cy + 44
        pygame.draw.line(surface, COLORS["bevel_shadow"],
                         (wx + 10, sep_y), (wx + WIN_W - 10, sep_y))
        pygame.draw.line(surface, COLORS["bevel_light"],
                         (wx + 10, sep_y + 1), (wx + WIN_W - 10, sep_y + 1))

        # ── Player name inputs ────────────────────────────────────────────────
        draw_text(surface, "Player names:", self._bf,
                  COLORS["text_dark"], wx + PAD + 10, cy + 54)
        for i in range(self.num_players):
            draw_text(surface, f"P{i+1}:", self._lf,
                      COLORS["text_dark"], wx + PAD + 10, cy + 77 + i * 36)
            self._inputs[i].draw(surface)

        # ── OK / Cancel ───────────────────────────────────────────────────────
        self._btn_ok.draw(surface)
        self._btn_cancel.draw(surface)

        # ── Hint ──────────────────────────────────────────────────────────────
        draw_text(surface, "Tab = next field   Enter = OK",
                  self._smf, COLORS["text_muted"],
                  wx + WIN_W // 2, cy + WIN_H - TITLE_H - 16, align="center")
