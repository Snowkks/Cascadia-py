"""
Setup screen - new game dialog.

Dialog: x=450, y=200, w=380, h=360
  y+0  : border
  y+2  : title bar h=22
  y+24 : client top  ← cy=0 from here
  cy+8 : "Number of players:" label   [2] [-][+]
  cy+40: hrule
  cy+52: "Player names:" label
  cy+68: P1 label + textbox
  cy+104: P2 label + textbox
  cy+140: P3 label + textbox  (if num>=3)
  cy+176: P4 label + textbox  (if num>=4)
  cy+260: OK  Cancel buttons
  cy+300: hint text
  y+360: border end
"""
import pygame
from cascadia.constants import (WINDOW_WIDTH as W, WINDOW_HEIGHT as H,
                                 NUM_PLAYERS_MIN, NUM_PLAYERS_MAX)
from cascadia.gui.ui import C, bevel, title_bar, hrule, txt, font, Button, TextBox, panel_box

DX, DY, DW, DH = 450, 200, 380, 360
TH = 22


class SetupScreen:
    def __init__(self, on_start, on_back):
        self._on_start = on_start
        self._on_back  = on_back
        self._f_tb  = font(13, bold=True)
        self._f_lbl = font(13)
        self._f_hdr = font(14, bold=True)
        self._f_sm  = font(11)

        self.n = 2   # number of players

        # cy = absolute y of client top
        cy = DY + 2 + TH

        # Spinner: label at cy+8, buttons at same row
        self._btn_minus = Button((DX+220, cy+6,  28, 24), "-", self._dec, 13, True)
        self._btn_plus  = Button((DX+252, cy+6,  28, 24), "+", self._inc, 13, True)

        # 4 name textboxes — always created at fixed positions
        self._boxes = []
        for i in range(NUM_PLAYERS_MAX):
            row_y = cy + 68 + i * 36
            box = TextBox((DX+110, row_y, 240, 26), f"Player {i+1}", fsize=14)
            self._boxes.append(box)
        self._boxes[0].focused = True

        # Buttons at cy+260
        self._btn_ok     = Button((DX+80,  cy+260, 90, 32), "OK",     self._ok,      14, True)
        self._btn_cancel = Button((DX+190, cy+260, 90, 32), "Cancel", on_back,       14)

    def _dec(self):
        if self.n > NUM_PLAYERS_MIN: self.n -= 1
    def _inc(self):
        if self.n < NUM_PLAYERS_MAX: self.n += 1

    def _ok(self):
        names = [self._boxes[i].text.strip() or f"Player {i+1}"
                 for i in range(self.n)]
        self._on_start(names)

    def _focused_idx(self):
        for i, b in enumerate(self._boxes[:self.n]):
            if b.focused: return i
        return 0

    def handle_event(self, ev):
        self._btn_minus.handle(ev)
        self._btn_plus.handle(ev)
        self._btn_ok.handle(ev)
        self._btn_cancel.handle(ev)
        for i in range(self.n):
            self._boxes[i].handle(ev)
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_RETURN:  self._ok()
            elif ev.key == pygame.K_ESCAPE: self._on_back()
            elif ev.key == pygame.K_TAB:
                fi = self._focused_idx()
                for b in self._boxes: b.focused = False
                self._boxes[(fi+1) % self.n].focused = True

    def update(self): pass

    def draw(self, surf):
        surf.fill(C["desktop"])

        dlg = pygame.Rect(DX, DY, DW, DH)
        panel_box(surf, dlg)
        title_bar(surf, pygame.Rect(DX+2, DY+2, DW-4, TH), "New Game", self._f_tb)

        cy = DY + 2 + TH   # absolute client top

        # ── Number of players ──────────────────────────────────────────────
        txt(surf, "Number of players:", self._f_lbl, C["black"], DX+14, cy+10)
        txt(surf, str(self.n),          self._f_hdr, C["black"], DX+200, cy+8)
        self._btn_minus.draw(surf)
        self._btn_plus.draw(surf)

        hrule(surf, cy+40, DX+8, DX+DW-8)

        # ── Player names ───────────────────────────────────────────────────
        txt(surf, "Player names:", self._f_hdr, C["black"], DX+14, cy+52)
        for i in range(self.n):
            row_y = cy + 68 + i * 36
            txt(surf, f"P{i+1}:", self._f_lbl, C["black"], DX+14, row_y+4)
            self._boxes[i].draw(surf)

        hrule(surf, cy+248, DX+8, DX+DW-8)

        # ── Buttons ────────────────────────────────────────────────────────
        self._btn_ok.draw(surf)
        self._btn_cancel.draw(surf)

        txt(surf, "Tab = next field    Enter = OK    Esc = Cancel",
            self._f_sm, C["muted"], DX+DW//2, cy+300, cx=True)
