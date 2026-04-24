"""
screen_game.py - Main gameplay screen, Win98 MDI-style layout.

Layout:
  ┌─────────────────────────────────────────────────────────────────────┐
  │ Title bar                                                           │
  ├──────────────────┬──────────────────────────┬───────────────────────┤
  │  LEFT PANEL      │     BOARD (hex grid)     │   RIGHT PANEL         │
  │  Turn / Players  │                          │   Market              │
  │  Scoring cards   │   [pan with RMB/drag]    │   Event log           │
  │  Nature tokens   │                          │   Action buttons      │
  ├──────────────────┴──────────────────────────┴───────────────────────┤
  │ Status bar                                                          │
  └─────────────────────────────────────────────────────────────────────┘
"""
import pygame
from typing import Optional, Tuple, List
from cascadia.constants import (WINDOW_WIDTH, WINDOW_HEIGHT, COLORS,
                                 HEX_SIZE, MARKET_SIZE)
from cascadia.game_engine import GameEngine, Phase
from cascadia.utils import (bevel_rect, fill_bevel_rect, draw_window,
                             draw_title_bar, hex_to_pixel, pixel_to_hex,
                             draw_text, draw_circle_token)
from cascadia.gui.resources import get_font, get_title_font, WILDLIFE_ASCII, HABITAT_LABELS
from cascadia.gui.widgets import Button, GroupBox, HexCell, ScrollLog, Tooltip

# ── Layout ────────────────────────────────────────────────────────────────────
TITLE_H   = 24
STATUS_H  = 22
LEFT_W    = 210
RIGHT_W   = 230
BOARD_X   = LEFT_W
BOARD_W   = WINDOW_WIDTH - LEFT_W - RIGHT_W
BOARD_CX  = BOARD_X + BOARD_W // 2
BOARD_CY  = TITLE_H + (WINDOW_HEIGHT - TITLE_H - STATUS_H) // 2


class GameScreen:
    def __init__(self, engine: GameEngine, on_game_over, on_menu):
        self.engine       = engine
        self.on_game_over = on_game_over
        self.on_menu      = on_menu

        self._tf  = get_title_font(18)
        self._hf  = get_font(14, bold=True)
        self._bf  = get_font(13)
        self._smf = get_font(13)

        # Board pan
        self._offset_x = 0
        self._offset_y = 0
        self._dragging  = False
        self._drag_start  = None
        self._drag_origin = None

        # Hover
        self._hovered_board  = None
        self._hovered_market = None

        # Nature-token free-pick mode
        self._nature_mode     = False
        self._nature_tile_idx = None

        # Market slot rects (right panel)
        self._mk_tile_rects  = []
        self._mk_token_rects = []
        self._build_market_rects()

        # Event log (right panel bottom)
        log_y = TITLE_H + 8 + 4 * 68 + 8
        self._log = ScrollLog(
            pygame.Rect(WINDOW_WIDTH - RIGHT_W + 4, log_y,
                        RIGHT_W - 8, WINDOW_HEIGHT - STATUS_H - log_y - 8)
        )
        for m in engine.log[-30:]:
            self._log.add(m)
        self._log_len = len(engine.log)

        # Buttons
        rx  = WINDOW_WIDTH - RIGHT_W + 4
        bw  = RIGHT_W - 8
        mk_bottom = TITLE_H + 8 + 4 * 68 + 2
        self._btn_discard = Button(
            pygame.Rect(rx, mk_bottom - 36, bw, 30),
            "Discard Token  (+Nature)", self._do_discard, font_size=12)
        self._btn_nat_replace = Button(
            pygame.Rect(rx, mk_bottom - 36, bw // 2 - 2, 30),
            "Replace Tokens", self._do_nature_replace, font_size=11)
        self._btn_nat_pick = Button(
            pygame.Rect(rx + bw // 2 + 2, mk_bottom - 36, bw // 2 - 2, 30),
            "Free Pick", self._do_nature_pick_mode, font_size=11)
        self._btn_menu = Button(
            pygame.Rect(4, WINDOW_HEIGHT - STATUS_H - 30, LEFT_W - 8, 26),
            "Menu", on_menu, font_size=13)

        self._tooltip = Tooltip()

    # ── Market rects ──────────────────────────────────────────────────────────
    def _build_market_rects(self):
        rx   = WINDOW_WIDTH - RIGHT_W + 4
        slot_h = 68
        for i in range(MARKET_SIZE):
            y = TITLE_H + 8 + i * slot_h
            self._mk_tile_rects.append(pygame.Rect(rx, y, RIGHT_W - 62, 60))
            self._mk_token_rects.append(pygame.Rect(WINDOW_WIDTH - 58, y + 8, 50, 44))

    # ── Events ────────────────────────────────────────────────────────────────
    def handle_event(self, event):
        if self.engine.is_game_over():
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.on_menu()
            return

        self._log.handle_event(event)
        self._btn_menu.handle_event(event)

        phase = self.engine.phase
        nt    = self.engine.current_player.nature_tokens > 0

        self._btn_discard.set_disabled(phase != Phase.PLACE_TOKEN)
        self._btn_nat_replace.set_disabled(phase != Phase.SELECT_PAIR or not nt)
        self._btn_nat_pick.set_disabled(phase != Phase.SELECT_PAIR or not nt)

        self._btn_discard.handle_event(event)
        self._btn_nat_replace.handle_event(event)
        self._btn_nat_pick.handle_event(event)

        if event.type == pygame.MOUSEMOTION:
            self._on_motion(event)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._on_click(event.pos)
            elif event.button in (2, 3):
                self._dragging    = True
                self._drag_start  = event.pos
                self._drag_origin = (self._offset_x, self._offset_y)
        if event.type == pygame.MOUSEBUTTONUP and event.button in (2, 3):
            self._dragging = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._nature_mode = False

    def _on_motion(self, event):
        mx, my = event.pos
        if self._dragging and self._drag_start:
            self._offset_x = self._drag_origin[0] + mx - self._drag_start[0]
            self._offset_y = self._drag_origin[1] + my - self._drag_start[1]

        if BOARD_X < mx < BOARD_X + BOARD_W:
            self._hovered_board = self._pixel_to_board(mx, my)
        else:
            self._hovered_board = None

        self._hovered_market = None
        for i in range(MARKET_SIZE):
            if (self._mk_tile_rects[i].collidepoint(mx, my) or
                    self._mk_token_rects[i].collidepoint(mx, my)):
                self._hovered_market = i
                break

        self._tooltip.hide()
        self._update_tooltip(mx, my)

    def _update_tooltip(self, mx, my):
        eng = self.engine
        if self._hovered_board and self._hovered_board in eng.current_player.board:
            t = eng.current_player.board[self._hovered_board]
            lines = [f"Habitats: {', '.join(t.habitats)}",
                     f"Accepts:  {', '.join(t.accepts)}"]
            if t.token:
                lines.append(f"Token: {t.token.wildlife_type}")
            if t.keystone:
                lines.append("* Keystone tile")
            self._tooltip.show("\n".join(lines), (mx, my))
        elif self._hovered_market is not None:
            i  = self._hovered_market
            t  = eng.market_tiles[i]
            tk = eng.market_tokens[i]
            lines = [f"Market slot {i+1}"]
            if t:  lines.append(f"Tile: {', '.join(t.habitats)}")
            if tk: lines.append(f"Token: {tk.wildlife_type}")
            self._tooltip.show("\n".join(lines), (mx, my))

    def _on_click(self, pos):
        mx, my = pos
        eng   = self.engine
        phase = eng.phase

        # ── SELECT_PAIR ──────────────────────────────────────────────────
        if phase == Phase.SELECT_PAIR:
            if self._nature_mode:
                # picking token slot
                for i in range(MARKET_SIZE):
                    if (self._mk_token_rects[i].collidepoint(pos) and
                            eng.market_tokens[i]):
                        eng.use_nature_token_pick_freely(self._nature_tile_idx, i)
                        self._nature_mode = False
                        self._sync_log()
                        return
                # picking tile slot first
                for i in range(MARKET_SIZE):
                    if self._mk_tile_rects[i].collidepoint(pos) and eng.market_tiles[i]:
                        self._nature_tile_idx = i
                        return
                self._nature_mode = False
                return

            for i in range(MARKET_SIZE):
                if (self._mk_tile_rects[i].collidepoint(pos) or
                        self._mk_token_rects[i].collidepoint(pos)):
                    if eng.market_tiles[i]:
                        eng.select_market_pair(i)
                        self._sync_log()
                        return

        # ── PLACE_TILE ───────────────────────────────────────────────────
        elif phase == Phase.PLACE_TILE:
            if BOARD_X < mx < BOARD_X + BOARD_W:
                q, r = self._pixel_to_board(mx, my)
                if eng.place_tile(q, r):
                    self._sync_log()

        # ── PLACE_TOKEN ──────────────────────────────────────────────────
        elif phase == Phase.PLACE_TOKEN:
            if BOARD_X < mx < BOARD_X + BOARD_W:
                q, r = self._pixel_to_board(mx, my)
                if eng.place_token(q, r):
                    self._sync_log()
                    if eng.is_game_over():
                        self.on_game_over(eng)

    def _do_discard(self):
        self.engine.discard_token()
        self._sync_log()

    def _do_nature_replace(self):
        self.engine.use_nature_token_replace_tokens()
        self._sync_log()

    def _do_nature_pick_mode(self):
        if self.engine.current_player.nature_tokens > 0:
            self._nature_mode     = True
            self._nature_tile_idx = None

    def _sync_log(self):
        for m in self.engine.log[self._log_len:]:
            self._log.add(m)
        self._log_len = len(self.engine.log)

    # ── Coordinates ───────────────────────────────────────────────────────────
    def _board_origin(self):
        return (BOARD_CX + self._offset_x, BOARD_CY + self._offset_y)

    def _board_to_pixel(self, q, r):
        ox, oy = self._board_origin()
        return hex_to_pixel(q, r, ox, oy)

    def _pixel_to_board(self, px, py):
        ox, oy = self._board_origin()
        return pixel_to_hex(px, py, ox, oy)

    # ── Update ────────────────────────────────────────────────────────────────
    def update(self, dt):
        pass

    # ── Draw ──────────────────────────────────────────────────────────────────
    def draw(self, surface):
        surface.fill(COLORS["bg_panel"])

        # Title bar
        tb = pygame.Rect(0, 0, WINDOW_WIDTH, TITLE_H)
        draw_title_bar(surface, tb,
                       f"Cascadia  —  {self.engine.current_player.name}'s Turn"
                       f"  (Turn {self.engine.turns_taken + 1} / {self.engine.total_turns})",
                       self._tf, active=True)

        # Status bar
        sb = pygame.Rect(0, WINDOW_HEIGHT - STATUS_H, WINDOW_WIDTH, STATUS_H)
        pygame.draw.rect(surface, COLORS["bg_panel"], sb)
        bevel_rect(surface, sb, raised=False, width=1)
        self._draw_status_text(surface, sb)

        self._draw_left_panel(surface)
        self._draw_board(surface)
        self._draw_right_panel(surface)
        self._draw_dividers(surface)

        self._tooltip.draw(surface)

        if self.engine.is_game_over():
            self._draw_game_over(surface)

    def _draw_dividers(self, surface):
        # Left divider
        pygame.draw.line(surface, COLORS["bevel_shadow"],
                         (LEFT_W, TITLE_H), (LEFT_W, WINDOW_HEIGHT - STATUS_H))
        pygame.draw.line(surface, COLORS["bevel_light"],
                         (LEFT_W + 1, TITLE_H), (LEFT_W + 1, WINDOW_HEIGHT - STATUS_H))
        # Right divider
        rx = WINDOW_WIDTH - RIGHT_W
        pygame.draw.line(surface, COLORS["bevel_shadow"],
                         (rx, TITLE_H), (rx, WINDOW_HEIGHT - STATUS_H))
        pygame.draw.line(surface, COLORS["bevel_light"],
                         (rx + 1, TITLE_H), (rx + 1, WINDOW_HEIGHT - STATUS_H))

    def _draw_status_text(self, surface, sb):
        eng   = self.engine
        phase = eng.phase
        msgs  = {
            Phase.SELECT_PAIR:  "Click a market slot to select a tile/token pair",
            Phase.PLACE_TILE:   "Click a highlighted green hex to place your tile",
            Phase.PLACE_TOKEN:  "Click a highlighted tile to place token — or Discard",
            Phase.GAME_OVER:    "Game over! Press ESC to return to menu.",
        }
        draw_text(surface, msgs.get(phase, ""), self._smf,
                  COLORS["text_dark"], sb.x + 6, sb.y + 5)
        if self._nature_mode and self._nature_tile_idx is None:
            draw_text(surface, "  [Nature: click a TILE slot first]",
                      self._smf, COLORS["highlight"], sb.x + 440, sb.y + 5)
        elif self._nature_mode:
            draw_text(surface, "  [Nature: now click a TOKEN slot]",
                      self._smf, COLORS["highlight"], sb.x + 440, sb.y + 5)

    # ── Left panel ────────────────────────────────────────────────────────────
    def _draw_left_panel(self, surface):
        panel = pygame.Rect(0, TITLE_H, LEFT_W, WINDOW_HEIGHT - TITLE_H - STATUS_H)
        pygame.draw.rect(surface, COLORS["bg_panel"], panel)

        eng = self.engine
        x, y = 8, TITLE_H + 8

        # Scoring cards group
        gc = GroupBox(pygame.Rect(x, y, LEFT_W - 12, 108), "Scoring Cards")
        gc.draw(surface)
        ci = gc.client
        cx2, cy2 = ci.x + 2, ci.y
        for wildlife, variant in eng.scoring_cards.items():
            col = COLORS.get(wildlife, COLORS["text_dark"])
            pygame.draw.circle(surface, col, (cx2 + 6, cy2 + 8), 5)
            draw_text(surface,
                      f"{WILDLIFE_ASCII.get(wildlife, wildlife[:2])} Card {variant}",
                      self._smf, COLORS["text_dark"], cx2 + 14, cy2 + 2)
            cy2 += 18
        y += 116

        # Players group
        gp = GroupBox(pygame.Rect(x, y, LEFT_W - 12,
                                   32 + len(eng.players) * 48), "Players")
        gp.draw(surface)
        pi = gp.client
        px2, py2 = pi.x, pi.y
        for p in eng.players:
            is_cur = (p.player_id == eng.current_player.player_id
                      and not eng.is_game_over())
            if is_cur:
                hl = pygame.Rect(px2 - 2, py2 - 1, gp.rect.width - 12, 46)
                fill_bevel_rect(surface, hl, raised=False)

            # Player colour dot + name
            pygame.draw.circle(surface, p.color, (px2 + 8, py2 + 8), 7)
            pygame.draw.circle(surface, (0, 0, 0), (px2 + 8, py2 + 8), 7, 1)
            prefix = ">" if is_cur else " "
            draw_text(surface, f"{prefix} {p.name}", self._bf,
                      COLORS["text_dark"], px2 + 18, py2 + 2)

            # Nature tokens
            draw_text(surface, f"Nature: {p.nature_tokens}", self._smf,
                      COLORS["text_dark"], px2 + 18, py2 + 18)

            # Wildlife counts
            counts = p.wildlife_counts()
            tx = px2 + 4
            for w, cnt in counts.items():
                if cnt:
                    col = COLORS.get(w, (100, 100, 100))
                    pygame.draw.circle(surface, col, (tx + 5, py2 + 34), 5)
                    draw_text(surface, str(cnt), self._smf,
                              COLORS["text_dark"], tx + 12, py2 + 28)
                    tx += 26
            py2 += 48

        y = gp.rect.bottom + 8

        # Menu button
        self._btn_menu.rect.y = WINDOW_HEIGHT - STATUS_H - 34
        self._btn_menu.draw(surface)

    # ── Board ─────────────────────────────────────────────────────────────────
    def _draw_board(self, surface):
        board_rect = pygame.Rect(BOARD_X + 2, TITLE_H,
                                  BOARD_W - 4, WINDOW_HEIGHT - TITLE_H - STATUS_H)
        pygame.draw.rect(surface, (160, 160, 160), board_rect)

        eng   = self.engine
        phase = eng.phase

        ghost_pos  = eng.pending_placement_positions if phase == Phase.PLACE_TILE else []
        token_pos  = (eng.get_valid_token_positions()
                      if phase == Phase.PLACE_TOKEN and eng.selected_token else [])

        clip = surface.get_clip()
        surface.set_clip(board_rect)

        for (q, r), tile in eng.current_player.board.items():
            cx, cy = self._board_to_pixel(q, r)
            if not (-HEX_SIZE < cx - BOARD_X < BOARD_W + HEX_SIZE and
                    -HEX_SIZE < cy - TITLE_H < board_rect.height + HEX_SIZE):
                continue
            HexCell(cx, cy, tile,
                    highlight=(q, r) in token_pos,
                    selected=(q, r) in [(t.q, t.r) for t in
                              eng.current_player.tiles_accepting(
                                  eng.selected_token.wildlife_type
                                  if eng.selected_token else "")
                              ]).draw(surface)

        for (q, r) in ghost_pos:
            cx, cy = self._board_to_pixel(q, r)
            if (-HEX_SIZE < cx - BOARD_X < BOARD_W + HEX_SIZE and
                    -HEX_SIZE < cy - TITLE_H < board_rect.height + HEX_SIZE):
                HexCell(cx, cy, ghost=True).draw(surface)

        surface.set_clip(clip)

        # Phase label on board
        phase_msgs = {
            Phase.SELECT_PAIR: "Select a market pair  →",
            Phase.PLACE_TILE:  "Click a GREEN hex to place tile",
            Phase.PLACE_TOKEN: "Click a tile to place token",
        }
        msg = phase_msgs.get(phase, "")
        if msg:
            lbl = self._smf.render(msg, True, (0, 0, 0))
            lx  = BOARD_X + (BOARD_W - lbl.get_width()) // 2
            ly  = TITLE_H + 4
            pygame.draw.rect(surface, COLORS["bg_panel"],
                             pygame.Rect(lx - 4, ly - 2, lbl.get_width() + 8, lbl.get_height() + 4))
            bevel_rect(surface, pygame.Rect(lx - 4, ly - 2,
                        lbl.get_width() + 8, lbl.get_height() + 4), raised=True, width=1)
            surface.blit(lbl, (lx, ly))

        draw_text(surface,
                  f"{eng.current_player.name}'s board — {len(eng.current_player.board)} tiles  |  RMB drag to pan",
                  self._smf, (40, 40, 40),
                  BOARD_X + BOARD_W // 2, WINDOW_HEIGHT - STATUS_H - 18, align="center")

    # ── Right panel ───────────────────────────────────────────────────────────
    def _draw_right_panel(self, surface):
        rx = WINDOW_WIDTH - RIGHT_W
        panel = pygame.Rect(rx + 2, TITLE_H, RIGHT_W - 2,
                             WINDOW_HEIGHT - TITLE_H - STATUS_H)
        pygame.draw.rect(surface, COLORS["bg_panel"], panel)

        eng   = self.engine
        phase = eng.phase
        nt    = eng.current_player.nature_tokens

        # "Market" header
        draw_text(surface, "Market", self._hf, COLORS["text_dark"],
                  rx + RIGHT_W // 2, TITLE_H + 6, align="center")

        for i in range(MARKET_SIZE):
            tile = eng.market_tiles[i]
            tok  = eng.market_tokens[i]
            tr   = self._mk_tile_rects[i]
            kr   = self._mk_token_rects[i]
            hov  = (self._hovered_market == i and phase == Phase.SELECT_PAIR)
            nat_sel = self._nature_mode and self._nature_tile_idx == i

            # Tile card
            t_fill = COLORS.get(tile.primary_habitat(),
                                 COLORS["bg_card"]) if tile else COLORS["bg_card"]
            pygame.draw.rect(surface, t_fill, tr)
            if hov or nat_sel:
                bevel_rect(surface, tr, raised=False, width=2)
            else:
                bevel_rect(surface, tr, raised=True, width=2)

            if tile:
                hab = "/".join(HABITAT_LABELS.get(h, h[:3]) for h in tile.habitats)
                acc = " ".join(WILDLIFE_ASCII.get(w, w[:2]) for w in tile.accepts)
                draw_text(surface, f"[{i+1}] {hab}", self._smf,
                          (0, 0, 0), tr.x + 4, tr.y + 4)
                draw_text(surface, f"Accepts: {acc}", self._smf,
                          (30, 30, 30), tr.x + 4, tr.y + 20)
                if tile.keystone:
                    draw_text(surface, "KEY", self._smf,
                              COLORS["gold"], tr.x + 4, tr.y + 36)
            else:
                draw_text(surface, "(empty)", self._smf,
                          COLORS["disabled"], tr.x + 4, tr.y + 20)

            # Token chip
            if tok:
                col = COLORS.get(tok.wildlife_type, (150, 150, 150))
                lbl = WILDLIFE_ASCII.get(tok.wildlife_type, tok.wildlife_type[:2])
                # sunken when hovered (clickable)
                pygame.draw.rect(surface, col, kr)
                if hov:
                    bevel_rect(surface, kr, raised=False, width=2)
                else:
                    bevel_rect(surface, kr, raised=True, width=2)
                draw_text(surface, lbl, self._bf, (0, 0, 0),
                          kr.centerx, kr.centery - self._bf.get_height() // 2,
                          align="center")
            else:
                pygame.draw.rect(surface, COLORS["bg_card"], kr)
                bevel_rect(surface, kr, raised=False, width=1)

        # Action buttons
        if phase == Phase.PLACE_TOKEN:
            self._btn_discard.draw(surface)
        elif phase == Phase.SELECT_PAIR and nt > 0:
            draw_text(surface, f"Nature tokens: {nt}", self._smf,
                      COLORS["text_dark"],
                      self._btn_nat_replace.rect.x,
                      self._btn_nat_replace.rect.y - 16)
            self._btn_nat_replace.draw(surface)
            self._btn_nat_pick.draw(surface)

        # Selected tile preview
        eng2 = self.engine
        if eng2.selected_tile:
            preview_y = self._btn_discard.rect.bottom + 6
            draw_text(surface, "Selected tile:", self._smf, COLORS["text_dark"],
                      WINDOW_WIDTH - RIGHT_W + 4, preview_y)
            hab = "/".join(HABITAT_LABELS.get(h, h[:3]) for h in eng2.selected_tile.habitats)
            draw_text(surface, hab, self._bf, COLORS["text_dark"],
                      WINDOW_WIDTH - RIGHT_W + 4, preview_y + 16)
            if eng2.selected_token:
                draw_text(surface, f"Token: {eng2.selected_token.wildlife_type}",
                          self._bf, COLORS["text_dark"],
                          WINDOW_WIDTH - RIGHT_W + 4, preview_y + 32)

        # Log
        self._log.draw(surface)

    # ── Game over overlay ─────────────────────────────────────────────────────
    def _draw_game_over(self, surface):
        # Modal window
        win_w, win_h = 500, 340
        wr = pygame.Rect((WINDOW_WIDTH - win_w) // 2,
                          (WINDOW_HEIGHT - win_h) // 2, win_w, win_h)
        draw_window(surface, wr, "Game Over — Final Scores", self._tf, title_h=24)

        x, y = wr.x + 16, wr.y + 34

        sorted_p = sorted(self.engine.players, key=lambda p: -p.score)
        medals   = ["1st", "2nd", "3rd", "4th"]
        for rank, player in enumerate(sorted_p):
            bd = self.engine.scores.get(player.player_id)
            pygame.draw.circle(surface, player.color, (x + 8, y + 10), 7)
            draw_text(surface, f"{medals[rank]}  {player.name}: {player.score} pts",
                      self._hf, COLORS["text_dark"], x + 18, y)
            y += 22
            if bd:
                ws   = bd.wildlife_scores
                line = (f"  Bear:{ws.get('bear',0)}  Elk:{ws.get('elk',0)}  "
                        f"Salmon:{ws.get('salmon',0)}  Hawk:{ws.get('hawk',0)}  "
                        f"Fox:{ws.get('fox',0)}  Habitat:{bd.habitat_score}  "
                        f"Nature:{bd.nature_token_score}")
                draw_text(surface, line, self._smf, COLORS["text_muted"], x + 6, y)
                y += 18

        y += 10
        pygame.draw.line(surface, COLORS["bevel_shadow"],
                         (wr.x + 12, y), (wr.right - 12, y))
        y += 10
        draw_text(surface, "Press ESC or click Menu to return to the main menu.",
                  self._smf, COLORS["text_muted"], wr.centerx, y, align="center")
