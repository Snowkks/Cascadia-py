"""
screen_setup.py - Win98-style new game setup dialog.
"""
import pygame
from cascadia.constants import (WINDOW_WIDTH, WINDOW_HEIGHT, COLORS,
                                 NUM_PLAYERS_MIN, NUM_PLAYERS_MAX)
from cascadia.utils import (bevel_rect, fill_bevel_rect, draw_window, draw_text)
from cascadia.gui.resources import get_font, get_title_font
from cascadia.gui.widgets import Button, TextInput, GroupBox, Label


class SetupScreen:
    def __init__(self, on_start, on_back):
        self.on_start = on_start
        self.on_back  = on_back

        self._title_f = get_title_font(18)
        self._body_f  = get_font(14)
        self._lbl_f   = get_font(13)

        self.num_players = 2
        self._inputs = [
            TextInput(pygame.Rect(0, 0, 220, 24), f"Player {i+1}", font_size=14)
            for i in range(NUM_PLAYERS_MAX)
        ]

        win_w, win_h = 400, 420
        self._win_rect = pygame.Rect(
            (WINDOW_WIDTH  - win_w) // 2,
            (WINDOW_HEIGHT - win_h) // 2,
            win_w, win_h,
        )

        wx = self._win_rect.x
        wy = self._win_rect.y

        # Player count spinner
        spin_y = wy + 68
        self._btn_minus = Button(pygame.Rect(wx + 200, spin_y, 28, 24), "-", self._dec)
        self._btn_plus  = Button(pygame.Rect(wx + 232, spin_y, 28, 24), "+", self._inc)

        # Name input positions (filled in _layout)
        self._layout()

        btn_y = wy + win_h - 54
        self._btn_ok   = Button(pygame.Rect(wx + 80,  btn_y, 100, 30), "OK",     self._do_start)
        self._btn_cancel = Button(pygame.Rect(wx + 200, btn_y, 100, 30), "Cancel", on_back)

    def _layout(self):
        wx = self._win_rect.x
        wy = self._win_rect.y
        for i, inp in enumerate(self._inputs):
            inp.rect = pygame.Rect(wx + 140, wy + 110 + i * 36, 220, 24)

    def _dec(self):
        if self.num_players > NUM_PLAYERS_MIN:
            self.num_players -= 1

    def _inc(self):
        if self.num_players < NUM_PLAYERS_MAX:
            self.num_players += 1

    def _do_start(self):
        names = []
        for i in range(self.num_players):
            n = self._inputs[i].text.strip() or f"Player {i+1}"
            names.append(n)
        self.on_start(names)

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
                focused = next((i for i, inp in enumerate(self._inputs[:self.num_players])
                                if inp.focused), -1)
                for inp in self._inputs:
                    inp.focused = False
                nxt = (focused + 1) % self.num_players
                self._inputs[nxt].focused = True

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill(COLORS["bg_dark"])
        draw_window(surface, self._win_rect, "New Game", self._title_f, title_h=24)

        wx = self._win_rect.x
        wy = self._win_rect.y

        # Number of players row
        draw_text(surface, "Number of players:", self._body_f,
                  COLORS["text_dark"], wx + 24, wy + 72)
        draw_text(surface, str(self.num_players), self._body_f,
                  COLORS["text_dark"], wx + 172, wy + 72)
        self._btn_minus.draw(surface)
        self._btn_plus.draw(surface)

        # Separator
        pygame.draw.line(surface, COLORS["bevel_shadow"],
                         (wx + 12, wy + 100), (self._win_rect.right - 12, wy + 100))
        pygame.draw.line(surface, COLORS["bevel_light"],
                         (wx + 12, wy + 101), (self._win_rect.right - 12, wy + 101))

        # Name fields
        draw_text(surface, "Player names:", self._body_f,
                  COLORS["text_dark"], wx + 24, wy + 110)
        for i in range(self.num_players):
            draw_text(surface, f"Player {i+1}:", self._lbl_f,
                      COLORS["text_dark"], wx + 30, wy + 114 + i * 36)
            self._inputs[i].draw(surface)

        # Buttons
        self._btn_ok.draw(surface)
        self._btn_cancel.draw(surface)

        # Hint
        draw_text(surface, "Tab = next field    Enter = OK",
                  get_font(13), COLORS["text_muted"],
                  self._win_rect.centerx,
                  self._win_rect.bottom - 16, align="center")
