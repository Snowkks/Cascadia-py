"""
Leaderboard screen - full window, two tabs.

Layout (all absolute from y=0):
  y=0  : title bar h=26
  y=26 : tab row h=32   [Leaderboard] [Recent Games]  [Close →]
  y=58 : hrule
  y=66 : column headers
  y=88 : list rows (scrollable)   bottom = H-26
  y=H-26: status bar h=26
"""
import pygame
from cascadia.constants import WINDOW_WIDTH as W, WINDOW_HEIGHT as H
from cascadia.gui.ui import (C, bevel, title_bar, hrule, txt, font,
                              Button, ScrollList, panel_box)
from cascadia.database import get_leaderboard, get_recent_games, get_game_results, init_db

TH   = 26    # title bar
TABH = 32    # tab strip height
HDR_Y = TH + TABH + 8    # column headers y
LST_Y = HDR_Y + 22       # list starts
STH   = 26               # status bar height
LST_H = H - STH - LST_Y  # list height


class LeaderboardScreen:
    def __init__(self, on_back):
        self._on_back = on_back
        self._f_tb  = font(13, bold=True)
        self._f_hdr = font(13, bold=True)
        self._f_row = font(13)
        self._f_sm  = font(11)

        init_db()
        self._tab  = 0
        self._sel_game = None
        self._detail   = []

        self._btn_tab0  = Button((6,        TH+2, 130, TABH-4), "Leaderboard",  lambda: self._set_tab(0), 13)
        self._btn_tab1  = Button((140,      TH+2, 130, TABH-4), "Recent Games", lambda: self._set_tab(1), 13)
        self._btn_close = Button((W-116,    TH+2, 110, TABH-4), "Close",        on_back,                  13)

        self._list = ScrollList(pygame.Rect(4, LST_Y, W-8, LST_H), fsize=13)

        self._lb_data  = []
        self._rg_data  = []
        self._refresh()

    def _set_tab(self, t):
        self._tab = t
        self._sel_game = None
        self._detail   = []
        self._populate()

    def _refresh(self):
        try:
            self._lb_data = get_leaderboard(30)
            self._rg_data = get_recent_games(40)
        except Exception:
            self._lb_data = self._rg_data = []
        self._populate()

    def _populate(self):
        if self._tab == 0:
            rows = []
            for i, r in enumerate(self._lb_data):
                rows.append(
                    f"  {i+1:>2}.  {r['player_name']:<18}"
                    f"  Games:{r['games_played']:>3}"
                    f"  Wins:{r['wins']:>3}"
                    f"  Best:{r['best_score']:>4}"
                    f"  Avg:{r['avg_score']:>6}"
                )
            self._list.items = rows or ["  (No games yet — play one first!)"]
        else:
            rows = []
            for r in self._rg_data:
                rows.append(
                    f"  #{r['id']:<4}"
                    f"  {r['played_at'][:16]}"
                    f"  {r['num_players']}p"
                    f"  {r['num_turns']} turns"
                    f"  Winner: {r['winner_name']} ({r['winner_score']} pts)"
                )
            self._list.items = rows or ["  (No games yet)"]
        self._list._scroll   = 0
        self._list.selected  = -1

    def handle_event(self, ev):
        self._btn_tab0.handle(ev)
        self._btn_tab1.handle(ev)
        self._btn_close.handle(ev)

        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self._on_back()

        clicked = self._list.handle(ev)
        if clicked is not None and self._tab == 1:
            if 0 <= clicked < len(self._rg_data):
                game = self._rg_data[clicked]
                self._sel_game = game
                try:   self._detail = get_game_results(game["id"])
                except: self._detail = []

    def update(self): pass

    def draw(self, surf):
        surf.fill(C["face"])

        # Title bar
        title_bar(surf, pygame.Rect(0, 0, W, TH),
                  "Cascadia — Records & Leaderboard", self._f_tb)

        # Status bar
        pygame.draw.rect(surf, C["face"], pygame.Rect(0, H-STH, W, STH))
        bevel(surf, pygame.Rect(0, H-STH, W, STH), raised=False)
        txt(surf, "Mouse wheel to scroll   |   ESC to close",
            self._f_sm, C["muted"], 8, H-STH+7)

        # Tab strip background
        pygame.draw.rect(surf, C["face"], pygame.Rect(0, TH, W, TABH))
        hrule(surf, TH+TABH, 0, W)

        # Tabs — active looks pressed
        for i, b in enumerate([self._btn_tab0, self._btn_tab1]):
            pygame.draw.rect(surf, C["face"], b.rect)
            bevel(surf, b.rect, raised=(i != self._tab))
            tc = C["black"]
            s  = self._f_row.render(b.label, True, tc)
            surf.blit(s, (b.rect.x + (b.rect.w - s.get_width())//2,
                          b.rect.y + (b.rect.h - s.get_height())//2))
        self._btn_close.draw(surf)

        # Column headers
        if self._tab == 0:
            cols = [("Rank",5),("Player",55),("Games",240),
                    ("Wins",310),("Best",380),("Avg Score",450)]
        else:
            cols = [("#",5),("Date",50),("Players",210),
                    ("Turns",295),("Winner",375),("Score",570)]
        for label, x in cols:
            txt(surf, label, self._f_hdr, C["muted"], x, HDR_Y)
        hrule(surf, HDR_Y+18, 4, W-4)

        # If a recent game is selected, show detail instead of list
        if self._tab == 1 and self._sel_game:
            self._draw_detail(surf)
        else:
            self._list.draw(surf)

    def _draw_detail(self, surf):
        g  = self._sel_game
        ry = LST_Y

        txt(surf, f"Game #{g['id']}  •  {g.get('played_at','')[:16]}  •  "
                  f"{g['num_players']} players, {g['num_turns']} turns",
            self._f_hdr, C["black"], 8, ry)
        ry += 24

        heads = [("Player",8),("Bear",180),("Elk",240),("Salmon",300),
                 ("Hawk",365),("Fox",420),("Habitat",475),("Nature",545),("TOTAL",620)]
        for label, x in heads:
            txt(surf, label, self._f_hdr, C["muted"], x, ry)
        ry += 18
        hrule(surf, ry, 4, W-4)
        ry += 4

        for row in self._detail:
            if row.get("is_winner"):
                pygame.draw.rect(surf, (210, 230, 255),
                                 pygame.Rect(0, ry, W, 22))
            vals = [
                (row.get("player_name","?"), 8),
                (row.get("bear_score",0),    180),
                (row.get("elk_score",0),     240),
                (row.get("salmon_score",0),  300),
                (row.get("hawk_score",0),    365),
                (row.get("fox_score",0),     420),
                (row.get("habitat_score",0), 475),
                (row.get("nature_tokens",0), 545),
                (row.get("total_score",0),   620),
            ]
            tc = C["sel"] if row.get("is_winner") else C["black"]
            for v, x in vals:
                txt(surf, str(v), self._f_row, tc, x, ry+2)
            ry += 22

        ry += 12
        btn_back = Button((8, ry, 160, 28), "< Back to list",
                          lambda: setattr(self, "_sel_game", None), 13)
        btn_back.draw(surf)
        btn_back.handle(pygame.event.Event(pygame.NOEVENT))
