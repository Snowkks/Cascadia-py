"""
Menu screen - centred dialog, nothing overlapping.

Pixel layout (all from top of window):
  Desktop fills 1280x800
  Dialog: x=490, y=270, w=300, h=260
    y+0  : raised border
    y+2  : title bar h=22
    y+24 : face begins
    y+34 : "CASCADIA" big text
    y+66 : subtitle
    y+86 : hrule
    y+100: btn New Game    h=34
    y+142: btn Leaderboard h=34
    y+184: btn Quit        h=34
    y+226: version text
    y+258: border end
"""
import pygame
from cascadia.constants import WINDOW_WIDTH as W, WINDOW_HEIGHT as H
from cascadia.gui.ui import C, bevel, title_bar, hrule, txt, font, Button, panel_box

DX, DY, DW, DH = 490, 270, 300, 260
TH = 22   # title bar height


class MenuScreen:
    def __init__(self, on_new_game, on_leaderboard, on_quit):
        self._f_title = font(24, bold=True)
        self._f_sub   = font(13)
        self._f_ver   = font(11)
        self._f_tb    = font(13, bold=True)

        # Client area starts at DY+2+TH = DY+24
        cy = DY + 2 + TH
        bx = DX + (DW - 220) // 2   # centre buttons in dialog

        self._btns = [
            Button((bx, cy+76,  220, 42), "New Game",     on_new_game,    18, True),
            Button((bx, cy+128, 220, 36), "Leaderboard",  on_leaderboard, 16),
            Button((bx, cy+174, 220, 36), "Quit",         on_quit,        16),
        ]

    def handle_event(self, ev):
        for b in self._btns: b.handle(ev)

    def update(self): pass

    def draw(self, surf):
        surf.fill(C["desktop"])

        # Dialog box
        dlg = pygame.Rect(DX, DY, DW, DH)
        panel_box(surf, dlg)
        tb  = pygame.Rect(DX+2, DY+2, DW-4, TH)
        title_bar(surf, tb, "Cascadia", self._f_tb)

        # Client area
        cy = DY + 2 + TH
        cx = DX + DW // 2
        txt(surf, "CASCADIA",       self._f_title, C["black"], cx, cy+10, cx=True)
        txt(surf, "Pacific Northwest Wilderness", self._f_sub, C["muted"], cx, cy+46, cx=True)
        hrule(surf, cy+66, DX+10, DX+DW-10)

        for b in self._btns: b.draw(surf)

        txt(surf, "v1.0  Digital Edition", self._f_ver, C["muted"], cx, DY+DH-20, cx=True)
