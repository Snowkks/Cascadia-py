"""
screen_leaderboard.py - Win98-style leaderboard / history window.
"""
import pygame
from cascadia.constants import WINDOW_WIDTH, WINDOW_HEIGHT, COLORS
from cascadia.utils import (bevel_rect, fill_bevel_rect, draw_window,
                             draw_title_bar, draw_text)
from cascadia.gui.resources import get_font, get_title_font
from cascadia.gui.widgets import Button, GroupBox, ListBox
from cascadia.database import get_leaderboard, get_recent_games, get_game_results, init_db

TITLE_H  = 24
STATUS_H = 22


class LeaderboardScreen:
    def __init__(self, on_back):
        self.on_back = on_back
        init_db()

        self._tf  = get_title_font(18)
        self._hf  = get_font(14, bold=True)
        self._bf  = get_font(13)
        self._smf = get_font(13)

        self._tab = 0
        self._selected_game = None
        self._detail_rows   = []

        bw = 120
        tab_y = TITLE_H + 6
        self._btn_tab0 = Button(pygame.Rect(8,      tab_y, bw, 28), "Leaderboard", lambda: self._set_tab(0))
        self._btn_tab1 = Button(pygame.Rect(bw + 12, tab_y, bw, 28), "Recent Games", lambda: self._set_tab(1))
        self._btn_back = Button(pygame.Rect(WINDOW_WIDTH - 114, WINDOW_HEIGHT - STATUS_H - 36, 110, 30), "Close", on_back)

        self._leaderboard = []
        self._recent      = []
        self._refresh()

        # List boxes
        content_y = TITLE_H + 44
        content_h = WINDOW_HEIGHT - TITLE_H - STATUS_H - 44 - 44
        self._lb_lb = ListBox(pygame.Rect(8, content_y, WINDOW_WIDTH - 16, content_h), font_size=13)
        self._lb_rg = ListBox(pygame.Rect(8, content_y, WINDOW_WIDTH - 16, content_h), font_size=13)
        self._populate_lists()

    def _set_tab(self, t):
        self._tab = t
        self._selected_game = None
        self._detail_rows   = []

    def _refresh(self):
        try:
            self._leaderboard = get_leaderboard(20)
            self._recent      = get_recent_games(30)
        except Exception:
            self._leaderboard = []
            self._recent      = []

    def _populate_lists(self):
        # Leaderboard entries
        self._lb_lb.items = []
        for rank, row in enumerate(self._leaderboard):
            self._lb_lb.items.append(
                f"  {rank+1}.  {row['player_name']:<18}  "
                f"Games: {row['games_played']}   "
                f"Wins: {row['wins']}   "
                f"Best: {row['best_score']}   "
                f"Avg: {row['avg_score']}"
            )
        if not self._lb_lb.items:
            self._lb_lb.items = ["  (No games recorded yet — play a game first!)"]

        # Recent games entries
        self._lb_rg.items = []
        for row in self._recent:
            self._lb_rg.items.append(
                f"  #{row['id']}  "
                f"{row['played_at'][:16]}   "
                f"{row['num_players']}p  "
                f"{row['num_turns']} turns   "
                f"Winner: {row['winner_name']} ({row['winner_score']} pts)"
            )
        if not self._lb_rg.items:
            self._lb_rg.items = ["  (No games recorded yet)"]

    def handle_event(self, event):
        self._btn_tab0.handle_event(event)
        self._btn_tab1.handle_event(event)
        self._btn_back.handle_event(event)

        if self._tab == 0:
            self._lb_lb.handle_event(event)
        else:
            self._lb_rg.handle_event(event)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                sel = self._lb_rg.selected
                if 0 <= sel < len(self._recent):
                    game = self._recent[sel]
                    self._selected_game = game
                    try:
                        self._detail_rows = get_game_results(game["id"])
                    except Exception:
                        self._detail_rows = []

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.on_back()

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill(COLORS["bg_panel"])

        # Title bar
        tb = pygame.Rect(0, 0, WINDOW_WIDTH, TITLE_H)
        draw_title_bar(surface, tb, "Cascadia — Records & Leaderboard", self._tf)

        # Status bar
        sb = pygame.Rect(0, WINDOW_HEIGHT - STATUS_H, WINDOW_WIDTH, STATUS_H)
        pygame.draw.rect(surface, COLORS["bg_panel"], sb)
        bevel_rect(surface, sb, raised=False, width=1)
        draw_text(surface, "Click a row to see game detail  |  ESC to close",
                  self._smf, COLORS["text_muted"], 8, sb.y + 5)

        # Tab buttons (make active one look pressed)
        self._btn_tab0.draw(surface)
        self._btn_tab1.draw(surface)
        # Draw pressed state for active tab
        active_btn = self._btn_tab0 if self._tab == 0 else self._btn_tab1
        pygame.draw.rect(surface, COLORS["bg_panel"], active_btn.rect)
        bevel_rect(surface, active_btn.rect, raised=False, width=2)
        draw_text(surface, active_btn.label, get_font(13),
                  COLORS["text_dark"], active_btn.rect.centerx,
                  active_btn.rect.centery - get_font(13).get_height() // 2,
                  align="center")

        self._btn_back.draw(surface)

        # Content
        if self._tab == 0:
            self._lb_lb.draw(surface)
        else:
            if self._selected_game:
                self._draw_detail(surface)
            else:
                self._lb_rg.draw(surface)

    def _draw_detail(self, surface):
        g = self._selected_game
        content_y = TITLE_H + 44

        # Header
        draw_text(surface,
                  f"Game #{g['id']}  played {g['played_at'][:16]}  —  {g['num_players']} players, {g['num_turns']} turns",
                  self._bf, COLORS["text_dark"], 12, content_y)
        content_y += 24

        # Column headers
        cols = ["Player", "Bear", "Elk", "Salmon", "Hawk", "Fox", "Habitat", "Nature", "TOTAL"]
        xs   = [12, 160, 210, 260, 320, 370, 420, 490, 570]
        for i, h in enumerate(cols):
            draw_text(surface, h, self._smf, COLORS["text_muted"], xs[i], content_y)
        content_y += 18
        pygame.draw.line(surface, COLORS["bevel_shadow"],
                         (8, content_y), (WINDOW_WIDTH - 8, content_y))
        content_y += 4

        for row in self._detail_rows:
            is_win = row.get("is_winner")
            col    = COLORS["highlight"] if is_win else COLORS["text_dark"]
            if is_win:
                hl = pygame.Rect(8, content_y - 2, WINDOW_WIDTH - 16, 20)
                pygame.draw.rect(surface, (200, 220, 255), hl)

            vals = [
                row.get("player_name", "?"),
                str(row.get("bear_score", 0)),
                str(row.get("elk_score", 0)),
                str(row.get("salmon_score", 0)),
                str(row.get("hawk_score", 0)),
                str(row.get("fox_score", 0)),
                str(row.get("habitat_score", 0)),
                str(row.get("nature_tokens", 0)),
                str(row.get("total_score", 0)),
            ]
            for i, v in enumerate(vals):
                draw_text(surface, v, self._bf, col, xs[i], content_y)
            content_y += 22

        content_y += 12
        draw_text(surface, "Click any row in the list to see another game's detail.",
                  self._smf, COLORS["text_muted"], 12, content_y)
        # Back to list button
        back_btn = Button(pygame.Rect(12, content_y + 20, 160, 28),
                          "<  Back to list",
                          lambda: setattr(self, '_selected_game', None))
        back_btn.draw(surface)
        back_btn.handle_event(pygame.event.Event(pygame.NOEVENT))
