"""
screen_leaderboard.py  –  Records & Leaderboard (full-window, tabbed).

y=0        ┌──────────────────────────────────────────────────────────┐
           │▓▓▓▓▓ Cascadia — Records ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│ title (24)
y=24       ├──────────────────────────────────────────────────────────┤
y=30       │  [Leaderboard]  [Recent Games]           [Close]         │ tab row (34)
y=64       ├──────────────────────────────────────────────────────────┤ col headers
y=84       │  scrollable list rows …                                   │
           │                                                          │
y=H-24     ├──────────────────────────────────────────────────────────┤
           │  status bar                                              │
y=H        └──────────────────────────────────────────────────────────┘
"""
import pygame
from cascadia.constants import WINDOW_WIDTH as W, WINDOW_HEIGHT as H, COLORS
from cascadia.utils import bevel_rect, fill_bevel_rect, draw_title_bar, draw_text
from cascadia.gui.resources import get_font, get_title_font
from cascadia.gui.widgets import Button
from cascadia.database import get_leaderboard, get_recent_games, get_game_results, init_db

TITLE_H  = 24
TAB_Y    = 30       # top of tab-button row
TAB_H    = 30       # height of tab buttons
HDR_Y    = TAB_Y + TAB_H + 6   # column-header row y
LIST_Y   = HDR_Y + 20          # first data row
STATUS_H = 22
LIST_BOT = H - STATUS_H - 4    # bottom of scrollable area
ROW_H    = 22


class LeaderboardScreen:
    def __init__(self, on_back):
        self.on_back = on_back
        init_db()

        self._tf  = get_title_font(16)
        self._hf  = get_font(14, bold=True)
        self._bf  = get_font(13)
        self._smf = get_font(12)

        self._tab            = 0
        self._scroll         = 0
        self._selected_game  = None
        self._detail_rows    = []

        # Tab buttons
        self._btn_tab0 = Button(pygame.Rect(6,      TAB_Y, 130, TAB_H), "Leaderboard",  lambda: self._set_tab(0))
        self._btn_tab1 = Button(pygame.Rect(140,    TAB_Y, 130, TAB_H), "Recent Games", lambda: self._set_tab(1))
        self._btn_back = Button(pygame.Rect(W - 116, TAB_Y, 110, TAB_H), "Close",       on_back)

        self._leaderboard = []
        self._recent      = []
        self._refresh()

    def _set_tab(self, t):
        self._tab           = t
        self._scroll        = 0
        self._selected_game = None

    def _refresh(self):
        try:
            self._leaderboard = get_leaderboard(30)
            self._recent      = get_recent_games(40)
        except Exception:
            self._leaderboard = []
            self._recent      = []

    def _visible_rows(self):
        return max(1, (LIST_BOT - LIST_Y) // ROW_H)

    def handle_event(self, event):
        self._btn_tab0.handle_event(event)
        self._btn_tab1.handle_event(event)
        self._btn_back.handle_event(event)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.on_back()

        if event.type == pygame.MOUSEWHEEL:
            self._scroll = max(0, self._scroll - event.y)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if LIST_Y <= my <= LIST_BOT:
                row_i = (my - LIST_Y) // ROW_H + self._scroll
                if self._tab == 1 and 0 <= row_i < len(self._recent):
                    game = self._recent[row_i]
                    if self._selected_game and self._selected_game["id"] == game["id"]:
                        self._selected_game = None   # toggle off
                    else:
                        self._selected_game = game
                        try:
                            self._detail_rows = get_game_results(game["id"])
                        except Exception:
                            self._detail_rows = []

    def update(self, dt): pass

    def draw(self, surface):
        surface.fill(COLORS["bg_panel"])

        # Title bar
        tb = pygame.Rect(0, 0, W, TITLE_H)
        draw_title_bar(surface, tb, "Cascadia — Records & Leaderboard", self._tf)

        # Status bar
        sb = pygame.Rect(0, H - STATUS_H, W, STATUS_H)
        pygame.draw.rect(surface, COLORS["bg_panel"], sb)
        bevel_rect(surface, sb, raised=False, width=1)
        draw_text(surface, "Scroll with mouse wheel   |   ESC to close",
                  self._smf, COLORS["text_muted"], 8, H - STATUS_H + 5)

        # Separator below title bar
        pygame.draw.line(surface, COLORS["bevel_shadow"], (0, TITLE_H), (W, TITLE_H))

        # Tab row background
        pygame.draw.rect(surface, COLORS["bg_panel"],
                         pygame.Rect(0, TAB_Y - 2, W, TAB_H + 8))

        # Tab buttons — draw inactive ones raised, active one sunken
        for i, btn in enumerate([self._btn_tab0, self._btn_tab1]):
            # Draw background manually so active looks pressed
            pygame.draw.rect(surface, COLORS["bg_panel"], btn.rect)
            bevel_rect(surface, btn.rect,
                       raised=(i != self._tab), width=2)
            draw_text(surface, btn.label, self._bf, COLORS["text_dark"],
                      btn.rect.centerx,
                      btn.rect.centery - self._bf.get_height() // 2,
                      align="center")

        self._btn_back.draw(surface)

        # Horizontal rule below tabs
        rule_y = TAB_Y + TAB_H + 4
        pygame.draw.line(surface, COLORS["bevel_shadow"], (0, rule_y), (W, rule_y))
        pygame.draw.line(surface, COLORS["bevel_light"],  (0, rule_y + 1), (W, rule_y + 1))

        if self._tab == 0:
            self._draw_leaderboard(surface)
        else:
            if self._selected_game:
                self._draw_detail(surface)
            else:
                self._draw_recent(surface)

    # ── Leaderboard tab ───────────────────────────────────────────────────────
    def _draw_leaderboard(self, surface):
        COL = [8, 50, 210, 310, 400, 510, 630]
        hdrs = ["#", "Player", "Games", "Wins", "Best Score", "Avg Score"]
        for i, h in enumerate(hdrs):
            draw_text(surface, h, self._bf, COLORS["text_dark"], COL[i], HDR_Y)
        pygame.draw.line(surface, COLORS["bevel_shadow"],
                         (4, HDR_Y + 18), (W - 4, HDR_Y + 18))

        if not self._leaderboard:
            draw_text(surface, "No games recorded yet — play a game first!",
                      self._bf, COLORS["text_muted"], W // 2, LIST_Y + 40, align="center")
            return

        vis = self._visible_rows()
        for i, row in enumerate(self._leaderboard[self._scroll:self._scroll + vis]):
            ry   = LIST_Y + i * ROW_H
            rank = i + self._scroll + 1
            col  = (180, 140, 0) if rank == 1 else COLORS["text_dark"]
            if ry + ROW_H > LIST_BOT:
                break
            if rank <= 3:
                pygame.draw.rect(surface, (240, 240, 200) if rank == 1 else (245, 245, 245),
                                 pygame.Rect(0, ry, W, ROW_H))
            vals = [str(rank), row.get("player_name","?"),
                    str(row.get("games_played",0)), str(row.get("wins",0)),
                    str(row.get("best_score",0)),   str(row.get("avg_score",0))]
            for j, v in enumerate(vals):
                draw_text(surface, v, self._bf, col, COL[j], ry + 3)

    # ── Recent Games tab ──────────────────────────────────────────────────────
    def _draw_recent(self, surface):
        COL  = [8, 60, 210, 290, 370, 490]
        hdrs = ["#", "Date", "Players", "Turns", "Winner", "Score"]
        for i, h in enumerate(hdrs):
            draw_text(surface, h, self._bf, COLORS["text_dark"], COL[i], HDR_Y)
        pygame.draw.line(surface, COLORS["bevel_shadow"],
                         (4, HDR_Y + 18), (W - 4, HDR_Y + 18))

        if not self._recent:
            draw_text(surface, "No games recorded yet.",
                      self._bf, COLORS["text_muted"], W // 2, LIST_Y + 40, align="center")
            return

        vis = self._visible_rows()
        mx, my = pygame.mouse.get_pos()
        for i, game in enumerate(self._recent[self._scroll:self._scroll + vis]):
            ry = LIST_Y + i * ROW_H
            if ry + ROW_H > LIST_BOT:
                break
            row_rect = pygame.Rect(0, ry, W, ROW_H)
            if row_rect.collidepoint(mx, my):
                pygame.draw.rect(surface, (220, 230, 255), row_rect)
            vals = [str(game.get("id","?")),
                    game.get("played_at","")[:16],
                    str(game.get("num_players","?")),
                    str(game.get("num_turns","?")),
                    game.get("winner_name","?"),
                    str(game.get("winner_score","?"))]
            for j, v in enumerate(vals):
                draw_text(surface, v, self._bf, COLORS["text_dark"], COL[j], ry + 3)

        draw_text(surface, "Click a row to see full score breakdown.",
                  self._smf, COLORS["text_muted"], 8, LIST_BOT - 16)

    # ── Game detail ───────────────────────────────────────────────────────────
    def _draw_detail(self, surface):
        g = self._selected_game
        draw_text(surface,
                  f"Game #{g['id']}  •  {g.get('played_at','')[:16]}  •  "
                  f"{g['num_players']} players, {g['num_turns']} turns",
                  self._bf, COLORS["text_dark"], 8, HDR_Y)

        COL  = [8, 180, 250, 310, 370, 430, 500, 570, 650]
        hdrs = ["Player","Bear","Elk","Salmon","Hawk","Fox","Habitat","Nature","TOTAL"]
        hy   = HDR_Y + 22
        for i, h in enumerate(hdrs):
            draw_text(surface, h, self._smf, COLORS["text_muted"], COL[i], hy)
        pygame.draw.line(surface, COLORS["bevel_shadow"],
                         (4, hy + 16), (W - 4, hy + 16))

        ry = hy + 20
        for row in self._detail_rows:
            is_win = row.get("is_winner")
            if is_win:
                pygame.draw.rect(surface, (210, 230, 255), pygame.Rect(0, ry, W, ROW_H))
            col = COLORS["highlight"] if is_win else COLORS["text_dark"]
            ws  = [row.get("player_name","?"),
                   str(row.get("bear_score",0)), str(row.get("elk_score",0)),
                   str(row.get("salmon_score",0)), str(row.get("hawk_score",0)),
                   str(row.get("fox_score",0)), str(row.get("habitat_score",0)),
                   str(row.get("nature_tokens",0)), str(row.get("total_score",0))]
            for i, v in enumerate(ws):
                draw_text(surface, v, self._bf, col, COL[i], ry + 2)
            ry += ROW_H

        ry += 12
        draw_text(surface, "Click a row in Recent Games to see another game.",
                  self._smf, COLORS["text_muted"], 8, ry)

        # "Back to list" inline button
        back = Button(pygame.Rect(8, ry + 20, 160, 28), "<  Back to list",
                      lambda: setattr(self, "_selected_game", None))
        back.draw(surface)
        back.handle_event(pygame.event.Event(pygame.NOEVENT))
