"""
screen_game.py  –  Main gameplay screen.

Strict non-overlapping layout (all measurements in one place at the top):

  y=0        ┌────────────────────────────────────────────────────┐
             │  TITLE BAR  (TITLE_H px tall)                      │
  y=TITLE_H  ├──────────┬─────────────────────────┬──────────────┤
             │  LEFT    │        BOARD             │   RIGHT      │
             │  LEFT_W  │  BOARD_W                 │   RIGHT_W    │
             │          │  (fills remaining width) │              │
  y=BOT      ├──────────┴─────────────────────────┴──────────────┤
             │  STATUS BAR  (STATUS_H px tall)                    │
  y=H        └────────────────────────────────────────────────────┘
"""

import pygame
from cascadia.constants import WINDOW_WIDTH as W, WINDOW_HEIGHT as H, COLORS, HEX_SIZE, MARKET_SIZE
from cascadia.game_engine import GameEngine, Phase
from cascadia.utils import bevel_rect, fill_bevel_rect, draw_title_bar, hex_to_pixel, pixel_to_hex, draw_text
from cascadia.gui.resources import get_font, get_title_font, WILDLIFE_ASCII, HABITAT_LABELS
from cascadia.gui.widgets import Button, GroupBox, HexCell, ScrollLog, Tooltip

# ── Layout constants (single source of truth) ─────────────────────────────────
TITLE_H  = 24          # title bar height
STATUS_H = 20          # status bar height
LEFT_W   = 200         # left panel width
RIGHT_W  = 240         # right panel width
CONTENT_TOP = TITLE_H         # y where content area starts
CONTENT_BOT = H - STATUS_H    # y where content area ends
CONTENT_H   = CONTENT_BOT - CONTENT_TOP

BOARD_X  = LEFT_W
BOARD_W  = W - LEFT_W - RIGHT_W
BOARD_CX = BOARD_X + BOARD_W // 2
BOARD_CY = CONTENT_TOP + CONTENT_H // 2

# Right panel x origin
RP_X = W - RIGHT_W
# Pad inside panels
PAD = 6

# Market: 4 slots stacked vertically inside right panel
MK_HEADER_H = 22          # "Market" label height
MK_SLOT_H   = 60          # height of each slot row (tile card + token)
MK_TOP      = CONTENT_TOP + MK_HEADER_H + PAD   # y of first slot
MK_TILE_W   = RIGHT_W - 68  # tile card width inside slot
MK_TOK_W    = 52           # token chip width
MK_BOTTOM   = MK_TOP + MARKET_SIZE * MK_SLOT_H  # y just below last slot

# Action button strip below market
BTN_STRIP_Y = MK_BOTTOM + PAD
BTN_H       = 28

# Log fills remaining vertical space below button strip
LOG_Y  = BTN_STRIP_Y + BTN_H + PAD
LOG_H  = CONTENT_BOT - LOG_Y - PAD


class GameScreen:
    def __init__(self, engine: GameEngine, on_game_over, on_menu):
        self.engine       = engine
        self.on_game_over = on_game_over
        self.on_menu      = on_menu

        self._tf  = get_title_font(16)
        self._hf  = get_font(14, bold=True)
        self._bf  = get_font(13)
        self._smf = get_font(13)

        # Board pan state
        self._ox = self._oy = 0
        self._dragging    = False
        self._drag_start  = None
        self._drag_origin = None

        self._hovered_board  = None
        self._hovered_market = None
        self._nature_mode     = False
        self._nature_tile_idx = None

        # ── Market rects ───────────────────────────────────────────────────
        self._mk_tile_rects  = []
        self._mk_token_rects = []
        for i in range(MARKET_SIZE):
            sy = MK_TOP + i * MK_SLOT_H
            self._mk_tile_rects.append(
                pygame.Rect(RP_X + PAD, sy + 2, MK_TILE_W, MK_SLOT_H - 6))
            self._mk_token_rects.append(
                pygame.Rect(RP_X + PAD + MK_TILE_W + 4, sy + 8, MK_TOK_W, MK_SLOT_H - 18))

        # ── Action buttons (right panel) ───────────────────────────────────
        bx  = RP_X + PAD
        bw  = RIGHT_W - PAD * 2
        bw2 = (bw - 4) // 2

        self._btn_discard = Button(
            pygame.Rect(bx, BTN_STRIP_Y, bw, BTN_H),
            "Discard Token (+Nature)", self._do_discard, font_size=13)

        self._btn_nat_replace = Button(
            pygame.Rect(bx, BTN_STRIP_Y, bw2, BTN_H),
            "Replace Tokens", self._do_nature_replace, font_size=12)
        self._btn_nat_pick = Button(
            pygame.Rect(bx + bw2 + 4, BTN_STRIP_Y, bw2, BTN_H),
            "Free Pick", self._do_nature_pick, font_size=12)

        # ── Event log ──────────────────────────────────────────────────────
        self._log = ScrollLog(pygame.Rect(bx, LOG_Y, bw, LOG_H))
        for m in engine.log[-30:]:
            self._log.add(m)
        self._log_len = len(engine.log)

        # ── Menu button (bottom of left panel) ────────────────────────────
        self._btn_menu = Button(
            pygame.Rect(PAD, CONTENT_BOT - BTN_H - PAD, LEFT_W - PAD * 2, BTN_H),
            "Menu", on_menu, font_size=13)

        self._tooltip = Tooltip()

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
                self._drag_origin = (self._ox, self._oy)
        if event.type == pygame.MOUSEBUTTONUP and event.button in (2, 3):
            self._dragging = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._nature_mode = False

    def _on_motion(self, event):
        mx, my = event.pos
        if self._dragging and self._drag_start:
            self._ox = self._drag_origin[0] + mx - self._drag_start[0]
            self._oy = self._drag_origin[1] + my - self._drag_start[1]

        self._hovered_board  = None
        self._hovered_market = None

        if BOARD_X < mx < BOARD_X + BOARD_W and CONTENT_TOP < my < CONTENT_BOT:
            self._hovered_board = self._px2board(mx, my)

        for i in range(MARKET_SIZE):
            if (self._mk_tile_rects[i].collidepoint(mx, my) or
                    self._mk_token_rects[i].collidepoint(mx, my)):
                self._hovered_market = i
                break

        self._tooltip.hide()
        self._make_tooltip(mx, my)

    def _make_tooltip(self, mx, my):
        eng = self.engine
        if self._hovered_board and self._hovered_board in eng.current_player.board:
            t = eng.current_player.board[self._hovered_board]
            lines = [f"Habitats: {', '.join(t.habitats)}",
                     f"Accepts:  {', '.join(t.accepts)}"]
            if t.token:   lines.append(f"Token: {t.token.wildlife_type}")
            if t.keystone: lines.append("* Keystone tile")
            self._tooltip.show("\n".join(lines), (mx, my))
        elif self._hovered_market is not None:
            i  = self._hovered_market
            tile = eng.market_tiles[i]
            tok  = eng.market_tokens[i]
            lines = [f"Market slot {i+1}"]
            if tile: lines.append(f"Tile: {', '.join(tile.habitats)}")
            if tok:  lines.append(f"Token: {tok.wildlife_type}")
            self._tooltip.show("\n".join(lines), (mx, my))

    def _on_click(self, pos):
        mx, my = pos
        eng   = self.engine
        phase = eng.phase

        if phase == Phase.SELECT_PAIR:
            if self._nature_mode:
                # First click picks tile slot, second picks token slot
                if self._nature_tile_idx is None:
                    for i in range(MARKET_SIZE):
                        if self._mk_tile_rects[i].collidepoint(pos) and eng.market_tiles[i]:
                            self._nature_tile_idx = i
                            return
                else:
                    for i in range(MARKET_SIZE):
                        if self._mk_token_rects[i].collidepoint(pos) and eng.market_tokens[i]:
                            eng.use_nature_token_pick_freely(self._nature_tile_idx, i)
                            self._nature_mode = False
                            self._nature_tile_idx = None
                            self._sync_log()
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

        elif phase == Phase.PLACE_TILE:
            if BOARD_X < mx < BOARD_X + BOARD_W and CONTENT_TOP < my < CONTENT_BOT:
                q, r = self._px2board(mx, my)
                if eng.place_tile(q, r):
                    self._sync_log()

        elif phase == Phase.PLACE_TOKEN:
            if BOARD_X < mx < BOARD_X + BOARD_W and CONTENT_TOP < my < CONTENT_BOT:
                q, r = self._px2board(mx, my)
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

    def _do_nature_pick(self):
        if self.engine.current_player.nature_tokens > 0:
            self._nature_mode     = True
            self._nature_tile_idx = None

    def _sync_log(self):
        for m in self.engine.log[self._log_len:]:
            self._log.add(m)
        self._log_len = len(self.engine.log)

    # ── Coord helpers ─────────────────────────────────────────────────────────
    def _board_origin(self):
        return (BOARD_CX + self._ox, BOARD_CY + self._oy)

    def _board2px(self, q, r):
        ox, oy = self._board_origin()
        return hex_to_pixel(q, r, ox, oy)

    def _px2board(self, px, py):
        ox, oy = self._board_origin()
        return pixel_to_hex(px, py, ox, oy)

    def update(self, dt):
        pass

    # ── Draw ──────────────────────────────────────────────────────────────────
    def draw(self, surface):
        # 1. Background (whole window silver)
        surface.fill(COLORS["bg_panel"])

        # 2. Title bar
        tb = pygame.Rect(0, 0, W, TITLE_H)
        eng = self.engine
        title = (f"Cascadia  —  {eng.current_player.name}'s Turn  "
                 f"(Turn {eng.turns_taken + 1}/{eng.total_turns})")
        draw_title_bar(surface, tb, title, self._tf)

        # 3. Status bar
        sb = pygame.Rect(0, CONTENT_BOT, W, STATUS_H)
        pygame.draw.rect(surface, COLORS["bg_panel"], sb)
        bevel_rect(surface, sb, raised=False, width=1)
        self._draw_status(surface, sb)

        # 4. Vertical dividers between panels
        for dx in [LEFT_W, W - RIGHT_W]:
            pygame.draw.line(surface, COLORS["bevel_shadow"],
                             (dx, CONTENT_TOP), (dx, CONTENT_BOT))
            pygame.draw.line(surface, COLORS["bevel_light"],
                             (dx + 1, CONTENT_TOP), (dx + 1, CONTENT_BOT))

        # 5. Panels (draw in order: left, board, right)
        self._draw_left(surface)
        self._draw_board(surface)
        self._draw_right(surface)

        # 6. Tooltip on top
        self._tooltip.draw(surface)

        # 7. Game-over modal on top of everything
        if eng.is_game_over():
            self._draw_gameover(surface)

    # ── Left panel ────────────────────────────────────────────────────────────
    def _draw_left(self, surface):
        eng = self.engine
        x   = PAD
        y   = CONTENT_TOP + PAD

        # ── Scoring cards group ────────────────────────────────────────────
        gc_h = 14 + len(eng.scoring_cards) * 18 + 6
        gc   = GroupBox(pygame.Rect(x, y, LEFT_W - PAD * 2, gc_h), "Scoring Cards")
        gc.draw(surface)
        ci   = gc.client
        cy   = ci.y
        for wildlife, variant in eng.scoring_cards.items():
            col = COLORS.get(wildlife, COLORS["text_dark"])
            pygame.draw.circle(surface, col, (ci.x + 7, cy + 8), 5)
            pygame.draw.circle(surface, (0,0,0), (ci.x + 7, cy + 8), 5, 1)
            draw_text(surface,
                      f"{WILDLIFE_ASCII.get(wildlife, wildlife[:2])} — Card {variant}",
                      self._smf, COLORS["text_dark"], ci.x + 16, cy + 1)
            cy += 18
        y += gc_h + PAD

        # ── Players group ──────────────────────────────────────────────────
        row_h = 52
        gp_h  = 14 + len(eng.players) * row_h + 4
        gp    = GroupBox(pygame.Rect(x, y, LEFT_W - PAD * 2, gp_h), "Players")
        gp.draw(surface)
        pi = gp.client
        py = pi.y
        for p in eng.players:
            is_cur = (p.player_id == eng.current_player.player_id
                      and not eng.is_game_over())
            if is_cur:
                hl = pygame.Rect(pi.x - 2, py - 1, gp.rect.width - 8, row_h)
                fill_bevel_rect(surface, hl, raised=False)

            # Colour dot + name
            pygame.draw.circle(surface, p.color, (pi.x + 8, py + 9), 7)
            pygame.draw.circle(surface, (0,0,0), (pi.x + 8, py + 9), 7, 1)
            prefix = ">" if is_cur else " "
            draw_text(surface, f"{prefix} {p.name}", self._bf,
                      COLORS["text_dark"], pi.x + 18, py + 2)

            # Nature tokens
            draw_text(surface, f"Nature: {p.nature_tokens}", self._smf,
                      COLORS["text_dark"], pi.x + 18, py + 19)

            # Wildlife token counts on one row
            counts = p.wildlife_counts()
            tx = pi.x + 4
            ty = py + 35
            for w, cnt in counts.items():
                if cnt:
                    col = COLORS.get(w, (120, 120, 120))
                    pygame.draw.circle(surface, col, (tx + 5, ty + 6), 5)
                    pygame.draw.circle(surface, (0,0,0), (tx + 5, ty + 6), 5, 1)
                    draw_text(surface, str(cnt), self._smf,
                              COLORS["text_dark"], tx + 12, ty)
                    tx += 28
            py += row_h
        y += gp_h + PAD

        # ── Menu button ────────────────────────────────────────────────────
        self._btn_menu.draw(surface)

    # ── Board ─────────────────────────────────────────────────────────────────
    def _draw_board(self, surface):
        board_rect = pygame.Rect(BOARD_X + 2, CONTENT_TOP,
                                 BOARD_W - 4, CONTENT_H)
        # Grey board background
        pygame.draw.rect(surface, (168, 168, 168), board_rect)

        eng   = self.engine
        phase = eng.phase

        ghost_pos = (eng.pending_placement_positions
                     if phase == Phase.PLACE_TILE else [])
        token_pos = (eng.get_valid_token_positions()
                     if phase == Phase.PLACE_TOKEN and eng.selected_token else [])

        clip = surface.get_clip()
        surface.set_clip(board_rect)

        for (q, r), tile in eng.current_player.board.items():
            cx, cy = self._board2px(q, r)
            if not (-HEX_SIZE <= cx - BOARD_X <= BOARD_W + HEX_SIZE and
                    -HEX_SIZE <= cy - CONTENT_TOP <= CONTENT_H + HEX_SIZE):
                continue
            is_hl = (q, r) in token_pos
            HexCell(cx, cy, tile, highlight=is_hl).draw(surface)

        for (q, r) in ghost_pos:
            cx, cy = self._board2px(q, r)
            if (-HEX_SIZE <= cx - BOARD_X <= BOARD_W + HEX_SIZE and
                    -HEX_SIZE <= cy - CONTENT_TOP <= CONTENT_H + HEX_SIZE):
                HexCell(cx, cy, ghost=True).draw(surface)

        surface.set_clip(clip)

        # Phase hint label, centred at top of board
        phase_msgs = {
            Phase.SELECT_PAIR: "Select a market pair  (right panel) →",
            Phase.PLACE_TILE:  "Click a green hex to place your tile",
            Phase.PLACE_TOKEN: "Click a highlighted tile to place token",
        }
        msg = phase_msgs.get(phase, "")
        if msg:
            lbl_surf = self._smf.render(msg, True, (0, 0, 0))
            lx = BOARD_X + (BOARD_W - lbl_surf.get_width()) // 2
            ly = CONTENT_TOP + 4
            bg = pygame.Rect(lx - 4, ly - 2,
                             lbl_surf.get_width() + 8, lbl_surf.get_height() + 4)
            pygame.draw.rect(surface, COLORS["bg_panel"], bg)
            bevel_rect(surface, bg, raised=True, width=1)
            surface.blit(lbl_surf, (lx, ly))

        # Pan hint at board bottom
        hint = f"{eng.current_player.name}'s board — {len(eng.current_player.board)} tiles   |   RMB drag to pan"
        draw_text(surface, hint, self._smf, (60, 60, 60),
                  BOARD_X + BOARD_W // 2, CONTENT_BOT - 18, align="center")

        # Nature mode overlay
        if self._nature_mode:
            if self._nature_tile_idx is None:
                nat_msg = "Nature: click a TILE card in the market →"
            else:
                nat_msg = "Nature: now click a TOKEN chip in the market →"
            nm_surf = self._smf.render(nat_msg, True, (0, 0, 128))
            nx = BOARD_X + (BOARD_W - nm_surf.get_width()) // 2
            ny = CONTENT_TOP + 28
            nbg = pygame.Rect(nx - 4, ny - 2, nm_surf.get_width() + 8, nm_surf.get_height() + 4)
            pygame.draw.rect(surface, (255, 255, 200), nbg)
            bevel_rect(surface, nbg, raised=True, width=1)
            surface.blit(nm_surf, (nx, ny))

    # ── Right panel ───────────────────────────────────────────────────────────
    def _draw_right(self, surface):
        eng   = self.engine
        phase = eng.phase
        nt    = eng.current_player.nature_tokens

        # "Market" header
        draw_text(surface, "Market", self._hf, COLORS["text_dark"],
                  RP_X + RIGHT_W // 2, CONTENT_TOP + PAD, align="center")

        # Horizontal rule under header
        rule_y = CONTENT_TOP + MK_HEADER_H
        pygame.draw.line(surface, COLORS["bevel_shadow"],
                         (RP_X + PAD, rule_y), (W - PAD, rule_y))
        pygame.draw.line(surface, COLORS["bevel_light"],
                         (RP_X + PAD, rule_y + 1), (W - PAD, rule_y + 1))

        # Market slots
        for i in range(MARKET_SIZE):
            tile = eng.market_tiles[i]
            tok  = eng.market_tokens[i]
            tr   = self._mk_tile_rects[i]
            kr   = self._mk_token_rects[i]
            hov  = (self._hovered_market == i)

            # ── Tile card ──────────────────────────────────────────────────
            fill_col = (COLORS.get(tile.primary_habitat(), COLORS["bg_card"])
                        if tile else COLORS["bg_card"])
            pygame.draw.rect(surface, fill_col, tr)
            bevel_rect(surface, tr, raised=not (hov and phase == Phase.SELECT_PAIR))

            if tile:
                hab = " / ".join(HABITAT_LABELS.get(h, h[:3]) for h in tile.habitats)
                acc = "  ".join(WILDLIFE_ASCII.get(w, w[:2]) for w in tile.accepts)
                draw_text(surface, f"[{i+1}] {hab}", self._smf, (0, 0, 0),
                          tr.x + 4, tr.y + 4)
                draw_text(surface, acc, self._smf, (50, 50, 50),
                          tr.x + 4, tr.y + 22)
                if tile.keystone:
                    draw_text(surface, "*KEY", self._smf, (140, 100, 0),
                              tr.x + 4, tr.y + 40)
            else:
                draw_text(surface, "(empty)", self._smf, COLORS["disabled"],
                          tr.x + 4, tr.y + 18)

            # ── Token chip ─────────────────────────────────────────────────
            if tok:
                col = COLORS.get(tok.wildlife_type, (160, 160, 160))
                lbl = WILDLIFE_ASCII.get(tok.wildlife_type, tok.wildlife_type[:2])
                pygame.draw.rect(surface, col, kr)
                bevel_rect(surface, kr, raised=not (hov and phase == Phase.SELECT_PAIR))
                draw_text(surface, lbl, self._bf, (0, 0, 0),
                          kr.centerx, kr.centery - self._bf.get_height() // 2,
                          align="center")
            else:
                pygame.draw.rect(surface, COLORS["bg_card"], kr)
                bevel_rect(surface, kr, raised=False, width=1)
                draw_text(surface, "—", self._smf, COLORS["disabled"],
                          kr.centerx, kr.centery - self._smf.get_height() // 2,
                          align="center")

        # ── Action buttons below market ────────────────────────────────────
        if phase == Phase.PLACE_TOKEN:
            self._btn_discard.draw(surface)
        elif phase == Phase.SELECT_PAIR and nt > 0:
            draw_text(surface, f"Nature tokens: {nt}", self._smf,
                      COLORS["text_dark"],
                      RP_X + PAD, BTN_STRIP_Y - 16)
            self._btn_nat_replace.draw(surface)
            self._btn_nat_pick.draw(surface)
        else:
            # Show greyed-out discard so panel doesn't jump around
            self._btn_discard.set_disabled(True)
            self._btn_discard.draw(surface)
            self._btn_discard.set_disabled(phase != Phase.PLACE_TOKEN)

        # ── Selected pair preview ──────────────────────────────────────────
        if eng.selected_tile:
            py = BTN_STRIP_Y + BTN_H + PAD
            draw_text(surface, "Selected:", self._smf, COLORS["text_dark"],
                      RP_X + PAD, py)
            hab = " / ".join(HABITAT_LABELS.get(h, h[:3])
                             for h in eng.selected_tile.habitats)
            draw_text(surface, hab, self._bf, COLORS["text_dark"],
                      RP_X + PAD, py + 16)
            if eng.selected_token:
                draw_text(surface,
                          f"Token: {eng.selected_token.wildlife_type}",
                          self._smf, COLORS["text_dark"],
                          RP_X + PAD, py + 32)

        # ── Log ────────────────────────────────────────────────────────────
        # Label
        draw_text(surface, "Event Log", self._smf, COLORS["text_muted"],
                  RP_X + PAD, LOG_Y - 16)
        self._log.draw(surface)

    # ── Status bar text ───────────────────────────────────────────────────────
    def _draw_status(self, surface, sb):
        phase = self.engine.phase
        msgs = {
            Phase.SELECT_PAIR:  "Click a market tile/token pair to select it",
            Phase.PLACE_TILE:   "Click a green ghost hex on your board to place the tile",
            Phase.PLACE_TOKEN:  "Click a highlighted tile to place token — or use Discard button",
            Phase.GAME_OVER:    "Game Over — Press ESC to return to the main menu",
        }
        draw_text(surface, msgs.get(phase, ""), self._smf,
                  COLORS["text_dark"], sb.x + 6, sb.y + 4)

    # ── Game-over modal ───────────────────────────────────────────────────────
    def _draw_gameover(self, surface):
        # Dim overlay
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 140))
        surface.blit(dim, (0, 0))

        eng    = self.engine
        n_p    = len(eng.players)
        win_w  = 520
        win_h  = 80 + n_p * 56 + 50
        wr     = pygame.Rect((W - win_w) // 2, (H - win_h) // 2, win_w, win_h)

        # Window chrome
        pygame.draw.rect(surface, COLORS["bg_panel"], wr)
        bevel_rect(surface, wr, raised=True)
        tb = pygame.Rect(wr.x + 2, wr.y + 2, wr.width - 4, 22)
        draw_title_bar(surface, tb, "Game Over — Final Scores", self._tf)

        x  = wr.x + 14
        y  = wr.y + 32
        sorted_p = sorted(eng.players, key=lambda p: -p.score)
        medals   = ["1st", "2nd", "3rd", "4th"]

        for rank, player in enumerate(sorted_p):
            bd = eng.scores.get(player.player_id)
            # Colour dot
            pygame.draw.circle(surface, player.color, (x + 8, y + 10), 8)
            pygame.draw.circle(surface, (0, 0, 0), (x + 8, y + 10), 8, 1)
            draw_text(surface,
                      f"{medals[rank]}  {player.name}  —  {player.score} pts",
                      self._hf, COLORS["text_dark"], x + 20, y)
            y += 22
            if bd:
                ws   = bd.wildlife_scores
                line = (f"    Bear:{ws.get('bear',0)}  Elk:{ws.get('elk',0)}  "
                        f"Salmon:{ws.get('salmon',0)}  Hawk:{ws.get('hawk',0)}  "
                        f"Fox:{ws.get('fox',0)}  "
                        f"Habitat:{bd.habitat_score}  Nature:{bd.nature_token_score}")
                draw_text(surface, line, self._smf, COLORS["text_muted"], x + 20, y)
                y += 22
            y += 12

        pygame.draw.line(surface, COLORS["bevel_shadow"],
                         (wr.x + 10, y), (wr.right - 10, y))
        y += 8
        draw_text(surface, "Press ESC or click Menu to return to main menu.",
                  self._smf, COLORS["text_muted"], wr.centerx, y, align="center")
