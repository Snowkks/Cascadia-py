"""
Game screen — full rewrite with:
  • Board viewer: tab through each player's board  ([ ] keys or buttons)
  • Scoring card panel: click a card to see full description
  • Detailed end-game score screen with per-rule breakdown
  • Neon green border highlight for token placement
  • Wide right panel (300px) with wrapped event log

Layout (1280×800):
  x=0   x=210  x=980   x=1280
  LEFT  BOARD  RIGHT
  210px  770px  300px

  y=0   Title bar (26px)
  y=26  Content
  y=774 Status bar (26px)
"""
import pygame
from cascadia.constants import (WINDOW_WIDTH as W, WINDOW_HEIGHT as H,
                                 COLORS, HEX_SIZE, MARKET_SIZE)
from cascadia.game_engine import GameEngine, Phase
from cascadia.scoring import CARD_DESCRIPTIONS, HABITAT_SCORING_DESC
from cascadia.gui.ui import (C, bevel, title_bar, hrule, txt, font,
                              Button, ScrollList, panel_box, ConfirmPopup)
from cascadia.gui.widgets import HexCell
from cascadia.utils import hex_to_pixel, pixel_to_hex

# ── Layout ────────────────────────────────────────────────────────────────────
TH    = 26
STH   = 26
LW    = 210
RW    = 300
BX    = LW
BW    = W - LW - RW        # 770
BCX   = BX + BW // 2
BCY   = TH + (H - TH - STH) // 2
RX    = W - RW

MK_X      = RX + 6
MK_TW     = RW - 76
MK_TOK_X  = RX + RW - 68
MK_TOK_W  = 60
MK_SLOT_H = 72
MK_TOP    = TH + 36

LOG_Y = MK_TOP + MARKET_SIZE * MK_SLOT_H + 4
# Preview box height = ~148px, sits above ACT_Y
# Log must end before preview starts
PREVIEW_H = 160   # reserved height for selected tile preview
LOG_H = H - STH - LOG_Y - 50 - PREVIEW_H
ACT_Y = H - STH - 46

W_COLORS = {
    "bear":   (139, 90,  43),
    "elk":    (160,130,  50),
    "salmon": (210, 85,  65),
    "hawk":   (170,140,  40),
    "fox":    (200, 85,  20),
}
H_COLORS = {
    "forest":  ( 80,130, 60),
    "wetland": ( 60,130,100),
    "mountain":(110,110,130),
    "prairie": (170,155, 55),
    "river":   ( 60,120,180),
}
WILDLIFE_SHORT = {"bear":"BR","elk":"EL","salmon":"SA","hawk":"HK","fox":"FX"}
HABITAT_SHORT  = {"forest":"FOR","wetland":"WET","mountain":"MTN",
                  "prairie":"PRA","river":"RIV"}


class GameScreen:
    def __init__(self, engine: GameEngine, on_game_over, on_menu):
        self._eng          = engine
        self._on_game_over = on_game_over
        self._on_menu      = on_menu

        self._f_tb  = font(13, bold=True)
        self._f_hdr = font(13, bold=True)
        self._f_row = font(13)
        self._f_sm  = font(11)

        # Board viewer — which player's board we're looking at
        self._view_idx = 0

        # Keystone bonus flash notification
        self._keystone_flash_timer = 0   # counts down in ms
        self._keystone_flash_name  = ""  # player who got it          # index into engine.players

        # Board pan
        self._ox = self._oy = 0
        self._drag = False
        self._drag_start = self._drag_origin = None

        # Nature-pick mode
        self._nat_mode     = False
        self._nat_tile_idx = None

        # Hover
        self._hov_market = None

        # Scoring card tooltip state
        self._card_hover = None     # wildlife string being hovered

        # Market rects
        self._mk_tile_rects = []
        self._mk_tok_rects  = []
        for i in range(MARKET_SIZE):
            y = MK_TOP + i * MK_SLOT_H
            self._mk_tile_rects.append(pygame.Rect(MK_X, y+4, MK_TW, MK_SLOT_H-8))
            self._mk_tok_rects.append(pygame.Rect(MK_TOK_X, y+12, MK_TOK_W, MK_SLOT_H-24))

        # Event log
        self._log   = ScrollList(pygame.Rect(RX+4, LOG_Y, RW-8, LOG_H), fsize=13)
        self._log_n = 0
        for m in engine.log[-40:]:
            self._log.append(m)
        self._log_n = len(engine.log)

        # Action buttons
        bw2 = (RW - 14) // 2
        self._btn_discard  = Button((RX+4,      ACT_Y, RW-8, 42), "Return Token to Bag", self._do_discard,   14, True)
        self._btn_nat_rep  = Button((RX+4,      ACT_Y, bw2,  38), "Replace Tokens",       self._do_nat_rep,   11)
        self._btn_nat_pick = Button((RX+bw2+10, ACT_Y, bw2,  38), "Free Pick",            self._do_nat_pick,  11)
        self._btn_menu     = Button((6, H-STH-32, LW-12, 28), "Menu", on_menu, 13)

        # Tile rotation buttons — shown during PLACE_TILE phase
        # Placed at bottom of board area
        rot_y = H - STH - 36
        rot_cx = BX + BW // 2
        self._btn_rot_ccw = Button((rot_cx - 80, rot_y, 70, 28), "↺ Rotate", self._do_rot_ccw, 13)
        self._btn_rot_cw  = Button((rot_cx + 10, rot_y, 70, 28), "↻ Rotate", self._do_rot_cw,  13)

        # Triple overpopulation — handled by popup, not a button
        self._wipe_popup = None       # ConfirmPopup instance or None
        self._wipe_dismissed = False   # True once player clicked No this turn

        # btn_wipe3 replaced by popup — dummy button kept so nothing breaks
        self._btn_wipe3 = Button((-999, -999, 1, 1), "", None, 12)

        # Board viewer buttons (left panel, below players)
        self._btn_prev = Button((6,        0, 34, 24), "<", self._prev_board, 13, True)
        self._btn_next = Button((LW-40,    0, 34, 24), ">", self._next_board, 13, True)

    # ── Board viewer ──────────────────────────────────────────────────────────
    def _prev_board(self):
        self._view_idx = (self._view_idx - 1) % len(self._eng.players)
        self._ox = self._oy = 0

    def _next_board(self):
        self._view_idx = (self._view_idx + 1) % len(self._eng.players)
        self._ox = self._oy = 0

    def _viewed_player(self):
        return self._eng.players[self._view_idx]

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _borigin(self):
        return (BCX + self._ox, BCY + self._oy)

    def _b2p(self, q, r):
        ox, oy = self._borigin()
        return hex_to_pixel(q, r, ox, oy)

    def _p2b(self, px, py):
        ox, oy = self._borigin()
        return pixel_to_hex(px, py, ox, oy)

    def _in_board(self, px, py):
        return BX < px < BX + BW and TH < py < H - STH

    def _sync_log(self):
        for m in self._eng.log[self._log_n:]:
            self._log.append(m)
        self._log_n = len(self._eng.log)

    def _sync_view(self):
        """After a turn ends, snap the board view to the new current player."""
        if not self._eng.is_game_over():
            self._view_idx = self._eng.current_idx
            self._ox = self._oy = 0   # reset pan so new board is centred

    # ── Actions ───────────────────────────────────────────────────────────────
    def _do_discard(self):
        self._eng.discard_token()
        self._sync_log()
        self._sync_view()

    def _do_nat_rep(self):
        self._eng.use_nature_token_replace_tokens(); self._sync_log()

    def _do_nat_pick(self):
        if self._eng.current_player.nature_tokens > 0:
            self._nat_mode = True; self._nat_tile_idx = None

    def _do_rot_cw(self):
        self._eng.rotate_selected_tile(clockwise=True)

    def _do_rot_ccw(self):
        self._eng.rotate_selected_tile(clockwise=False)

    def _do_wipe3(self):
        wtype = self._eng.triple_overpop_type
        self._wipe_popup = ConfirmPopup(
            "Overpopulation",
            f"3x {wtype} in market — wipe them? (optional)",
            on_yes=self._confirm_wipe3,
            on_no=self._dismiss_wipe3,
        )

    def _confirm_wipe3(self):
        self._eng.wipe_triple_overpopulation()
        self._sync_log()
        self._wipe_popup = None
        self._wipe_dismissed = False

    def _dismiss_wipe3(self):
        self._wipe_popup = None
        self._wipe_dismissed = True

    # ── Events ────────────────────────────────────────────────────────────────
    def handle_event(self, ev):
        # Modal popup blocks all other input
        if self._wipe_popup and self._wipe_popup.visible:
            self._wipe_popup.handle(ev)
            return

        # Reset dismissed flag when a new turn's SELECT_PAIR phase begins
        if self._eng.phase != Phase.SELECT_PAIR:
            self._wipe_dismissed = False

        # Always allow menu button
        self._btn_menu.handle(ev)

        if self._eng.is_game_over():
            # Handle tab switching on game over screen
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for i, tr in enumerate(getattr(self, '_go_tab_rects', [])):
                    if tr.collidepoint(ev.pos):
                        self._go_tab = i
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                self._on_menu()
            return

        self._log.handle(ev)

        # Board viewer prev/next with [ ] keys
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_LEFTBRACKET:  self._prev_board()
            if ev.key == pygame.K_RIGHTBRACKET: self._next_board()
            if ev.key == pygame.K_ESCAPE:       self._nat_mode = False
            # R = rotate CW, Shift+R = rotate CCW
            if ev.key == pygame.K_r:
                if ev.mod & pygame.KMOD_SHIFT:
                    self._do_rot_ccw()
                else:
                    self._do_rot_cw()

        # Update viewer button positions (y computed at draw time, store refs)
        self._btn_prev.handle(ev)
        self._btn_next.handle(ev)

        # Rotation buttons — only active during PLACE_TILE
        if self._eng.phase == Phase.PLACE_TILE:
            self._btn_rot_cw.handle(ev)
            self._btn_rot_ccw.handle(ev)

        phase = self._eng.phase
        nt    = self._eng.current_player.nature_tokens > 0

        self._btn_discard.enabled  = (phase == Phase.PLACE_TOKEN)
        self._btn_nat_rep.enabled  = (phase == Phase.SELECT_PAIR and nt)
        self._btn_nat_pick.enabled = (phase == Phase.SELECT_PAIR and nt)
        # Auto-show popup when 3-of-same appears in market (once per turn)
        if (phase == Phase.SELECT_PAIR and
                self._eng.triple_overpop_type and
                not self._wipe_dismissed and
                (self._wipe_popup is None or not self._wipe_popup.visible)):
            self._do_wipe3()
        self._btn_discard.handle(ev)
        self._btn_nat_rep.handle(ev)
        self._btn_nat_pick.handle(ev)
        self._btn_wipe3.handle(ev)

        # Card hover detection (left panel scoring card rows)
        if ev.type == pygame.MOUSEMOTION:
            mx, my = ev.pos
            self._card_hover = None
            # Cards are drawn at fixed y positions in left panel — check each
            cy = TH + 8 + 20   # approx where cards start
            for w in self._eng.scoring_cards:
                row_r = pygame.Rect(4, cy, LW-8, 18)
                if row_r.collidepoint(mx, my):
                    self._card_hover = w
                    break
                cy += 18

        if ev.type == pygame.MOUSEMOTION:
            mx, my = ev.pos
            self._hov_market = next(
                (i for i in range(MARKET_SIZE)
                 if self._mk_tile_rects[i].collidepoint(ev.pos) or
                    self._mk_tok_rects[i].collidepoint(ev.pos)), None)
            if self._drag and self._drag_start:
                self._ox = self._drag_origin[0] + mx - self._drag_start[0]
                self._oy = self._drag_origin[1] + my - self._drag_start[1]

        if ev.type == pygame.MOUSEBUTTONDOWN:
            if ev.button in (2, 3):
                self._drag = True
                self._drag_start  = ev.pos
                self._drag_origin = (self._ox, self._oy)
            if ev.button == 1:
                self._on_click(ev.pos)
            # Scroll wheel over board during PLACE_TILE = rotate tile
            if ev.button in (4, 5) and self._eng.phase == Phase.PLACE_TILE:
                mx, my = ev.pos
                if self._in_board(mx, my):
                    self._eng.rotate_selected_tile(clockwise=(ev.button == 5))

        if ev.type == pygame.MOUSEWHEEL:
            # Scroll wheel over board during PLACE_TILE = rotate tile
            if self._eng.phase == Phase.PLACE_TILE:
                mx, my = pygame.mouse.get_pos()
                if self._in_board(mx, my):
                    self._eng.rotate_selected_tile(clockwise=(ev.y < 0))
                    return  # don't also scroll the log

        if ev.type == pygame.MOUSEBUTTONUP and ev.button in (2, 3):
            self._drag = False

    def _on_click(self, pos):
        eng   = self._eng
        phase = eng.phase
        mx, my = pos

        if phase == Phase.SELECT_PAIR:
            if self._nat_mode:
                if self._nat_tile_idx is None:
                    for i in range(MARKET_SIZE):
                        if self._mk_tile_rects[i].collidepoint(pos) and eng.market_tiles[i]:
                            self._nat_tile_idx = i; return
                else:
                    for i in range(MARKET_SIZE):
                        if self._mk_tok_rects[i].collidepoint(pos) and eng.market_tokens[i]:
                            eng.use_nature_token_pick_freely(self._nat_tile_idx, i)
                            self._nat_mode = False; self._nat_tile_idx = None
                            self._sync_log(); return
                return
            for i in range(MARKET_SIZE):
                if (self._mk_tile_rects[i].collidepoint(pos) or
                        self._mk_tok_rects[i].collidepoint(pos)):
                    if eng.market_tiles[i]:
                        eng.select_market_pair(i); self._sync_log(); return

        elif phase == Phase.PLACE_TILE:
            # Only allow placing on the current player's board
            if self._view_idx != eng.current_player.player_id:
                return
            if self._in_board(mx, my):
                q, r = self._p2b(mx, my)
                if eng.place_tile(q, r): self._sync_log()

        elif phase == Phase.PLACE_TOKEN:
            if self._view_idx != eng.current_player.player_id:
                return
            if self._in_board(mx, my):
                q, r = self._p2b(mx, my)
                nt_before = eng.current_player.nature_tokens
                if eng.place_token(q, r):
                    # Check if keystone bonus fired
                    if eng.players[self._eng.players[self._eng.current_idx - 1].player_id
                                   if not eng.is_game_over() else 0].nature_tokens > nt_before:
                        pass  # handled below via log scan
                    self._sync_log()
                    # Flash if keystone bonus appeared in log
                    for msg in reversed(eng.log[-3:]):
                        if "Keystone bonus" in msg:
                            self._keystone_flash_timer = 2500
                            self._keystone_flash_name  = msg
                            break
                    if eng.is_game_over():
                        self._on_game_over(eng)
                    else:
                        self._sync_view()

    # ── Update / Draw ─────────────────────────────────────────────────────────
    def update(self):
        # Tick down keystone flash notification
        if self._keystone_flash_timer > 0:
            self._keystone_flash_timer -= 1000 // 60  # ~60fps

    def draw(self, surf):
        surf.fill(C["face"])
        self._draw_title(surf)
        self._draw_status(surf)
        self._draw_left(surf)
        self._draw_board(surf)
        self._draw_right(surf)

        # Dividers
        pygame.draw.line(surf, C["gray"],  (LW,   TH), (LW,   H-STH))
        pygame.draw.line(surf, C["white"], (LW+1, TH), (LW+1, H-STH))
        pygame.draw.line(surf, C["gray"],  (RX,   TH), (RX,   H-STH))
        pygame.draw.line(surf, C["white"], (RX+1, TH), (RX+1, H-STH))

        # Scoring card popup
        if self._card_hover:
            self._draw_card_popup(surf, self._card_hover)

        # Keystone bonus flash notification
        if self._keystone_flash_timer > 0:
            self._draw_keystone_flash(surf)

        if self._eng.is_game_over():
            self._draw_gameover(surf)

        # Overpopulation popup drawn last (on top of everything)
        if self._wipe_popup and self._wipe_popup.visible:
            self._wipe_popup.draw(surf)

    # ── Title bar ─────────────────────────────────────────────────────────────
    def _draw_title(self, surf):
        eng = self._eng
        if eng.is_game_over():
            lbl = "Cascadia  —  Game Over!"
        else:
            lbl = (f"Cascadia  —  {eng.current_player.name}'s Turn"
                   f"   (Turn {eng.turns_taken+1}/{eng.total_turns})")
        title_bar(surf, pygame.Rect(0, 0, W, TH), lbl, self._f_tb)

    # ── Status bar ────────────────────────────────────────────────────────────
    def _draw_status(self, surf):
        phase = self._eng.phase
        msgs  = {
            Phase.SELECT_PAIR:  "Click a market slot to pick a tile+token pair",
            Phase.PLACE_TILE:   "Click a green hex to place tile  —  scroll wheel to rotate",
            Phase.PLACE_TOKEN:  "Click a glowing tile to place token  —  or Return to Bag (no penalty)",
            Phase.GAME_OVER:    "Game over!  ESC or Menu to return.",
        }
        sb = pygame.Rect(0, H-STH, W, STH)
        pygame.draw.rect(surf, C["face"], sb)
        bevel(surf, sb, raised=False)
        msg = msgs.get(phase, "")
        if self._nat_mode:
            msg = ("Step 1: click a TILE card" if self._nat_tile_idx is None
                   else "Step 2: click a TOKEN chip")

        # Board viewer hint
        vp = self._viewed_player()
        cp = self._eng.current_player
        if not self._eng.is_game_over() and vp.player_id != cp.player_id:
            msg = f"Viewing {vp.name}'s board (read-only)  |  [ ] keys to switch"

        txt(surf, msg, self._f_sm, C["black"], 8, H-STH+7)
        txt(surf, "[ ] = switch board   RMB drag = pan   F11 = fullscreen",
            self._f_sm, C["muted"], W-8, H-STH+7, right=True)

    # ── Left panel ────────────────────────────────────────────────────────────
    def _draw_left(self, surf):
        eng = self._eng
        pygame.draw.rect(surf, C["face"], pygame.Rect(0, TH, LW, H-TH-STH))
        y = TH + 8

        # ── Scoring cards ─────────────────────────────────────────────────
        txt(surf, "Scoring Cards (hover for details):", self._f_sm, C["muted"], 6, y); y += 16
        for w, variant in eng.scoring_cards.items():
            col  = W_COLORS.get(w, (100,100,100))
            key  = f"{w}_{variant}"
            desc = CARD_DESCRIPTIONS.get(key, ("", []))
            row_r = pygame.Rect(4, y, LW-8, 18)
            # Highlight on hover
            if self._card_hover == w:
                pygame.draw.rect(surf, (220, 230, 255), row_r)
                bevel(surf, row_r, raised=False)
            pygame.draw.rect(surf, col,        (8, y+3, 10, 10))
            pygame.draw.rect(surf, C["black"], (8, y+3, 10, 10), 1)
            label = f"{w.capitalize()} — Card {variant}"
            txt(surf, label, self._f_sm, C["black"], 22, y+2)
            y += 18
        y += 4
        hrule(surf, y, 4, LW-4); y += 8

        # ── Players + board viewer ─────────────────────────────────────────
        txt(surf, "Players  ([ ] to view board):", self._f_sm, C["muted"], 6, y); y += 16

        viewer = self._viewed_player()
        cur    = eng.current_player

        for p in eng.players:
            is_cur  = (p.player_id == cur.player_id and not eng.is_game_over())
            is_view = (p.player_id == viewer.player_id)
            row_h   = 58
            row_r   = pygame.Rect(4, y-2, LW-8, row_h)

            if is_cur:
                pygame.draw.rect(surf, C["title"], row_r)
                pygame.draw.rect(surf, (100,140,255), pygame.Rect(4, y-2, 5, row_h))
                nc, sc, mc = C["white"], (180,200,255), (180,200,255)
            elif is_view:
                pygame.draw.rect(surf, (220, 235, 220), row_r)
                bevel(surf, row_r, raised=False)
                nc, sc, mc = C["black"], C["muted"], C["black"]
            else:
                pygame.draw.rect(surf, C["face"], row_r)
                bevel(surf, row_r, raised=True)
                nc, sc, mc = C["black"], C["muted"], C["black"]

            # Colour dot
            pygame.draw.circle(surf, p.color,   (20, y+10), 9)
            pygame.draw.circle(surf, nc,         (20, y+10), 9, 1)

            # Badges
            badges = []
            if is_cur:  badges.append("YOUR TURN")
            if is_view and not is_cur: badges.append("VIEWING")
            badge_str = "  ".join(badges)

            name_str = p.name
            txt(surf, name_str,  self._f_hdr, nc, 33, y)
            if badge_str:
                txt(surf, badge_str, self._f_sm, (255,220,80) if is_cur else (0,100,0),
                    33, y+14)
            # Nature token — show gold if >1 so it's noticeable
            nt_col = (200, 160, 0) if p.nature_tokens > 1 else sc
            txt(surf, f"Nature tokens: {p.nature_tokens}", self._f_sm, nt_col, 33, y+28)

            # Wildlife counts
            tx = 33
            for w, cnt in p.wildlife_counts().items():
                if cnt:
                    col = W_COLORS.get(w, (100,100,100))
                    pygame.draw.rect(surf, col,   (tx, y+41, 10, 10))
                    pygame.draw.rect(surf, nc,    (tx, y+41, 10, 10), 1)
                    txt(surf, str(cnt), self._f_sm, mc, tx+12, y+40)
                    tx += 28
            y += row_h + 2

        # Board viewer buttons (position them below players)
        bvy = y + 4
        self._btn_prev.rect.y = bvy
        self._btn_next.rect.y = bvy
        self._btn_prev.draw(surf)
        self._btn_next.draw(surf)
        cx = LW // 2
        txt(surf, f"Viewing: {viewer.name}", self._f_sm, C["black"], cx, bvy+4, cx=True)
        y = bvy + 32

        self._btn_menu.draw(surf)

    # ── Board ─────────────────────────────────────────────────────────────────
    def _draw_board(self, surf):
        eng     = self._eng
        phase   = eng.phase
        viewer  = self._viewed_player()
        is_cur_board = (viewer.player_id == eng.current_player.player_id)

        board_r = pygame.Rect(BX+2, TH, BW-4, H-TH-STH)

        # Background colour depends on whose board we're viewing
        bg = (145, 145, 145) if is_cur_board else (120, 130, 120)
        pygame.draw.rect(surf, bg, board_r)

        # "Viewing other player" tint banner
        if not is_cur_board:
            banner = pygame.Rect(BX+2, TH, BW-4, 24)
            pygame.draw.rect(surf, (60, 100, 60), banner)
            txt(surf, f"Viewing {viewer.name}'s board  (read-only)  —  press [ ] to switch",
                self._f_sm, (200, 255, 200), BCX, TH+5, cx=True)

        ghost_pos = eng.pending_placement_positions if (phase==Phase.PLACE_TILE and is_cur_board) else []
        tok_pos   = (eng.get_valid_token_positions()
                     if phase==Phase.PLACE_TOKEN and eng.selected_token and is_cur_board else [])

        clip = surf.get_clip()
        surf.set_clip(board_r)

        for (q, r), tile in viewer.board.items():
            cx, cy = self._b2p(q, r)
            if not (BX-HEX_SIZE < cx < BX+BW+HEX_SIZE and
                    TH-HEX_SIZE  < cy < H-STH+HEX_SIZE):
                continue
            HexCell(cx, cy, tile, highlight=(q,r) in tok_pos).draw(surf)

        for (q, r) in ghost_pos:
            cx, cy = self._b2p(q, r)
            if BX-HEX_SIZE < cx < BX+BW+HEX_SIZE:
                HexCell(cx, cy, ghost=True).draw(surf)

        surf.set_clip(clip)

        # Phase hint chip
        if is_cur_board:
            hint = {Phase.PLACE_TILE: "Click a green hex to place tile",
                    Phase.PLACE_TOKEN: "Click glowing tile to place token"}
            if phase in hint:
                s = self._f_sm.render(hint[phase], True, C["black"])
                bx2 = BCX - s.get_width()//2 - 6
                by2 = TH + (28 if not is_cur_board else 4)
                pygame.draw.rect(surf, C["face"],
                                 pygame.Rect(bx2, by2, s.get_width()+12, s.get_height()+4))
                bevel(surf, pygame.Rect(bx2, by2, s.get_width()+12, s.get_height()+4), raised=True)
                surf.blit(s, (bx2+6, by2+2))

        txt(surf, "RMB drag to pan",
            self._f_sm, (60,60,60), BCX, H-STH-14, cx=True)

        # Rotation hint + buttons during PLACE_TILE
        if eng.phase == Phase.PLACE_TILE and is_cur_board:
            rot = eng.tile_rotation
            hint = f"Scroll wheel over board to rotate tile  ({rot*60}°)"
            txt(surf, hint, self._f_sm, (40,40,40), BCX, H-STH-14, cx=True)
            # Keep small buttons as backup
            self._btn_rot_ccw.draw(surf)
            self._btn_rot_cw.draw(surf)

    # ── Right panel ───────────────────────────────────────────────────────────
    def _draw_right(self, surf):
        eng   = self._eng
        phase = eng.phase
        pygame.draw.rect(surf, C["face"], pygame.Rect(RX, TH, RW, H-TH-STH))

        txt(surf, "Market", self._f_hdr, C["black"], RX+RW//2, TH+8, cx=True)
        hrule(surf, TH+26, RX+4, W-4)

        # Overpopulation notice removed from sidebar — handled by popup now
        market_offset = 0

        for i in range(MARKET_SIZE):
            tile = eng.market_tiles[i]
            tok  = eng.market_tokens[i]
            tr   = self._mk_tile_rects[i].move(0, market_offset)
            kr   = self._mk_tok_rects[i].move(0, market_offset)
            hov  = (self._hov_market == i and phase == Phase.SELECT_PAIR)
            nat_t = (self._nat_mode and self._nat_tile_idx == i)

            fill = H_COLORS.get(tile.primary_habitat(), (200,200,200)) if tile else C["face"]
            pygame.draw.rect(surf, fill, tr)
            bevel(surf, tr, raised=not (hov or nat_t))

            if tile:
                hab = "/".join(HABITAT_SHORT.get(h,h[:3]) for h in tile.habitats)
                acc = " ".join(WILDLIFE_SHORT.get(w,w[:2]) for w in sorted(tile.accepts))
                txt(surf, f"[{i+1}] {hab}", self._f_sm, C["black"], tr.x+4, tr.y+4)
                txt(surf, f"  {acc}", self._f_sm, (30,30,30), tr.x+4, tr.y+20)
                if tile.keystone:
                    txt(surf, "KEY", self._f_sm, (120,80,0), tr.x+4, tr.y+36)
            else:
                txt(surf, "(empty)", self._f_sm, C["gray"], tr.x+4, tr.y+20)

            if tok:
                col = W_COLORS.get(tok.wildlife_type, (150,150,150))
                pygame.draw.rect(surf, col, kr)
                bevel(surf, kr, raised=not hov)
                short = WILDLIFE_SHORT.get(tok.wildlife_type, tok.wildlife_type[:2])
                s = font(12, bold=True).render(short, True, C["black"])
                surf.blit(s, (kr.x+(kr.w-s.get_width())//2,
                              kr.y+(kr.h-s.get_height())//2))
            else:
                pygame.draw.rect(surf, C["face"], kr)
                bevel(surf, kr, raised=False)

        # Separator + actions
        hrule(surf, ACT_Y-6, RX+4, W-4)
        if phase == Phase.PLACE_TOKEN:
            r = self._btn_discard.rect
            pygame.draw.rect(surf, (80, 100, 160), r)
            pygame.draw.line(surf, (140,160,220), (r.x, r.y),        (r.right-2, r.y))
            pygame.draw.line(surf, (140,160,220), (r.x, r.y),        (r.x, r.bottom-2))
            pygame.draw.line(surf, (40, 50, 100), (r.x, r.bottom-1), (r.right-1,r.bottom-1))
            pygame.draw.line(surf, (40, 50, 100), (r.right-1,r.y),   (r.right-1,r.bottom-1))
            s = font(13,True).render("Return Token to Bag  (no penalty)", True, (255,255,255))
            surf.blit(s, (r.x+(r.w-s.get_width())//2, r.y+(r.h-s.get_height())//2))

        elif phase == Phase.SELECT_PAIR and eng.current_player.nature_tokens > 0:
            txt(surf, f"Nature tokens: {eng.current_player.nature_tokens}",
                self._f_sm, C["black"], RX+4, ACT_Y-18)
            self._btn_nat_rep.draw(surf)
            self._btn_nat_pick.draw(surf)

        # ── Selected tile visual preview ───────────────────────────────────────
        if eng.selected_tile:
            tile  = eng.selected_tile
            token = eng.selected_token

            # Preview box sits between market slots and the action separator
            prev_size = 52          # hex radius for preview
            prev_cx   = RX + RW//2
            prev_cy   = ACT_Y - prev_size - 28

            # Background box
            box = pygame.Rect(RX+4, prev_cy - prev_size - 10,
                              RW-8, prev_size*2 + 44)
            pygame.draw.rect(surf, (230, 230, 220), box)
            bevel(surf, box, raised=False)

            # Label
            txt(surf, "Selected tile  (scroll to rotate):",
                self._f_sm, C["muted"], prev_cx, box.y+4, cx=True)

            # Draw the actual hex tile at preview size with current rotation
            from cascadia.gui.widgets import HexCell
            cell = HexCell(prev_cx, prev_cy, tile, size=prev_size)
            cell.draw(surf)

            # Token chip next to hex
            if token:
                tok_col = W_COLORS.get(token.wildlife_type, (150,150,150))
                pygame.draw.circle(surf, tok_col,    (prev_cx + prev_size + 22, prev_cy), 18)
                pygame.draw.circle(surf, C["black"], (prev_cx + prev_size + 22, prev_cy), 18, 2)
                lbl = WILDLIFE_SHORT.get(token.wildlife_type, token.wildlife_type[:2])
                s   = font(13, True).render(lbl, True, C["black"])
                surf.blit(s, (prev_cx + prev_size + 22 - s.get_width()//2,
                              prev_cy - s.get_height()//2))
                s2 = font(10).render(token.wildlife_type, True, C["black"])
                surf.blit(s2, (prev_cx + prev_size + 22 - s2.get_width()//2,
                               prev_cy + 20))

            # Rotation arrows below preview
            if phase == Phase.PLACE_TILE:
                self._btn_rot_ccw.rect.y = box.bottom - 30
                self._btn_rot_cw.rect.y  = box.bottom - 30
                self._btn_rot_ccw.draw(surf)
                self._btn_rot_cw.draw(surf)
                txt(surf, f"or scroll over board",
                    self._f_sm, C["muted"], prev_cx, box.bottom - 14, cx=True)

        # Log label + widget
        txt(surf, "Event log:", self._f_sm, C["muted"], RX+4, LOG_Y-16)
        self._log.draw(surf)

    # ── Scoring card popup ────────────────────────────────────────────────────
    def _draw_card_popup(self, surf, wildlife):
        variant = self._eng.scoring_cards.get(wildlife, "A")
        key     = f"{wildlife}_{variant}"
        info    = CARD_DESCRIPTIONS.get(key)
        if not info:
            return
        title_str, lines = info

        f_t = font(13, bold=True)
        f_b = font(12)
        lh  = f_b.get_height() + 3
        pw  = 260
        ph  = 28 + len(lines) * lh + 8

        # Position to the right of the left panel
        px = LW + 8
        py = TH + 30

        # Draw popup window
        popup = pygame.Rect(px, py, pw, ph)
        pygame.draw.rect(surf, (255, 255, 235), popup)
        bevel(surf, popup, raised=True)

        # Coloured title bar
        col = W_COLORS.get(wildlife, (100,100,100))
        pygame.draw.rect(surf, col, pygame.Rect(px+2, py+2, pw-4, 20))
        ts = f_t.render(title_str, True, (255,255,255))
        surf.blit(ts, (px+6, py+3))

        # Description lines
        cy = py + 26
        for line in lines:
            ls = f_b.render(line, True, C["black"])
            surf.blit(ls, (px+6, cy))
            cy += lh

    # ── Keystone flash notification ───────────────────────────────────────────

    def _draw_keystone_flash(self, surf):
        """Show a golden popup briefly when keystone bonus fires."""
        f_big = font(18, bold=True)
        f_sm  = font(13)

        nw, nh = 340, 70
        nx = BCX - nw // 2
        ny = TH + 40

        # Fade alpha based on remaining timer
        alpha = min(255, self._keystone_flash_timer * 2)

        box_surf = pygame.Surface((nw, nh), pygame.SRCALPHA)
        pygame.draw.rect(box_surf, (255, 220, 50, min(alpha, 230)), (0, 0, nw, nh))
        pygame.draw.rect(box_surf, (180, 140, 0, 255), (0, 0, nw, nh), 3)
        surf.blit(box_surf, (nx, ny))

        # Star + text
        pygame.draw.circle(surf, (255,215,0), (nx+28, ny+nh//2), 16)
        pygame.draw.circle(surf, (180,140,0), (nx+28, ny+nh//2), 16, 2)
        star = f_big.render("★", True, (180,100,0))
        surf.blit(star, (nx+28-star.get_width()//2, ny+nh//2-star.get_height()//2))

        s1 = f_big.render("Keystone Bonus!", True, (120, 70, 0))
        s2 = f_sm.render("+1 Nature Token earned", True, (100, 60, 0))
        surf.blit(s1, (nx+52, ny+10))
        surf.blit(s2, (nx+52, ny+34))

    # ── Game over screen ──────────────────────────────────────────────────────
    def _draw_gameover(self, surf):
        # Dim background
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 170))
        surf.blit(dim, (0, 0))

        MW, MH = 760, 540
        mx = (W - MW) // 2
        my = (H - MH) // 2
        panel_box(surf, pygame.Rect(mx, my, MW, MH))
        title_bar(surf, pygame.Rect(mx+2, my+2, MW-4, TH),
                  "Game Over — Final Scores", self._f_hdr)

        # Tab state — stored on self so clicks persist
        if not hasattr(self, '_go_tab'): self._go_tab = 0
        tab_y = my + 2 + TH + 4

        # Draw tab buttons inline
        tab_labels = ["Score Table", "Scoring Cards Explained"]
        tab_rects  = []
        tx = mx + 8
        for i, lbl in enumerate(tab_labels):
            tr = pygame.Rect(tx, tab_y, 200 if i==1 else 110, 24)
            tab_rects.append(tr)
            pygame.draw.rect(surf, C["face"], tr)
            bevel(surf, tr, raised=(i != self._go_tab))
            fc = font(12, bold=(i==self._go_tab))
            s  = fc.render(lbl, True, C["black"])
            surf.blit(s, (tr.x + (tr.w-s.get_width())//2,
                          tr.y + (tr.h-s.get_height())//2))
            tx += tr.w + 4

        # Store tab rects for click handling
        self._go_tab_rects = tab_rects

        content_y = tab_y + 28
        hrule(surf, content_y, mx+4, mx+MW-4)
        content_y += 6

        if self._go_tab == 0:
            self._draw_go_scores(surf, mx, content_y, MW)
        else:
            self._draw_go_cards(surf, mx, content_y, MW, MH, my)

    def _draw_go_scores(self, surf, mx, y, MW):
        eng      = self._eng
        sorted_p = sorted(eng.players, key=lambda p: -p.score)
        medals   = ["1st", "2nd", "3rd", "4th"]

        # Winners announcement
        if len(eng.winners) == 1:
            w_txt = f"Winner: {eng.winners[0].name} with {eng.winners[0].score} pts!"
        else:
            names = " & ".join(w.name for w in eng.winners)
            w_txt = f"Shared Victory: {names}  ({eng.winners[0].score} pts)"
        s = font(16, True).render(w_txt, True, (140, 100, 0))
        surf.blit(s, (mx + MW//2 - s.get_width()//2, y))
        y += 26

        # Tie-break note if needed
        if len(eng.winners) < len([p for p in eng.players
                                    if p.score == eng.winners[0].score]):
            tb = font(11).render("Tie broken by Nature Tokens", True, C["muted"])
            surf.blit(tb, (mx + MW//2 - tb.get_width()//2, y))
        y += 18

        # Score table
        # Columns: Player | Bear | Elk | Salm | Hawk | Fox | Habitat | Majority | Nature | TOTAL
        CX = [mx+16, mx+150, mx+200, mx+252, mx+304, mx+356, mx+408, mx+468, mx+530, mx+598]
        HDRS = ["Player","Bear","Elk","Salm","Hawk","Fox","Habit","Maj","Nature","TOTAL"]
        f_h = font(12, True)
        f_r = font(13)
        for i, h in enumerate(HDRS):
            txt(surf, h, f_h, C["muted"], CX[i], y)
        y += 18
        pygame.draw.line(surf, C["gray"], (mx+8, y), (mx+MW-8, y))
        y += 4

        for rank, p in enumerate(sorted_p):
            bd = eng.scores.get(p.player_id)
            ws = bd.wildlife_scores if bd else {}
            is_win = p in eng.winners
            row = pygame.Rect(mx+4, y-2, MW-8, 24)
            if is_win:
                pygame.draw.rect(surf, (245, 240, 180), row)
            elif rank % 2:
                pygame.draw.rect(surf, (235, 235, 228), row)

            pygame.draw.circle(surf, p.color,   (mx+9, y+9), 7)
            pygame.draw.circle(surf, C["black"], (mx+9, y+9), 7, 1)
            col = (140, 100, 0) if is_win else C["black"]

            vals = [
                f"{medals[rank]}  {p.name}",
                str(ws.get("bear",0)),  str(ws.get("elk",0)),
                str(ws.get("salmon",0)),str(ws.get("hawk",0)),
                str(ws.get("fox",0)),
                str(bd.habitat_score if bd else 0),
                str(bd.habitat_majority if bd else 0),
                str(bd.nature_token_score if bd else 0),
                str(p.score),
            ]
            for i2, v in enumerate(vals):
                f2 = font(13, True) if i2 in (0, 9) else f_r
                txt(surf, v, f2, col, CX[i2], y)
            y += 26

        y += 6
        hrule(surf, y, mx+8, mx+MW-8)
        y += 8
        f_sm = font(11)
        txt(surf, "Habitat: 1pt per tile in largest connected corridor per habitat type.",
            f_sm, C["muted"], mx+14, y); y += 14
        txt(surf, "Majority: bonus pts for having the largest (or 2nd) corridor vs other players.",
            f_sm, C["muted"], mx+14, y); y += 14
        txt(surf, "Nature: 1pt per leftover Nature Token.  Ties broken by most Nature Tokens.",
            f_sm, C["muted"], mx+14, y); y += 20
        txt(surf, "Press ESC or Menu to return to main menu.",
            font(12), C["muted"], mx+MW//2, y, cx=True)

    def _draw_go_cards(self, surf, mx, y, MW, MH, my):
        """One card per row — no columns, so nothing overlaps."""
        f_title = font(13, True)
        f_body  = font(12)
        lh      = f_body.get_height() + 2
        pad     = 10

        for w, variant in self._eng.scoring_cards.items():
            key  = f"{w}_{variant}"
            info = CARD_DESCRIPTIONS.get(key)
            if not info: continue
            title_str, lines = info

            card_h = 22 + len(lines) * lh + 6
            if y + card_h > my + MH - 40:
                break

            # Colour band
            wc = W_COLORS.get(w, (100,100,100))
            pygame.draw.rect(surf, wc, pygame.Rect(mx+pad, y, MW-pad*2, 20))
            pygame.draw.rect(surf, C["black"], pygame.Rect(mx+pad, y, MW-pad*2, 20), 1)
            ts = f_title.render(title_str, True, (255,255,255))
            surf.blit(ts, (mx+pad+6, y+2))
            y += 22

            # Body lines — each on its own row, guaranteed not to overlap
            for line in lines:
                txt(surf, line, f_body, C["black"], mx+pad+10, y)
                y += lh
            y += 6

        y += 4
        txt(surf, "Press ESC or Menu to return to main menu.",
            font(12), C["muted"], mx+MW//2, y, cx=True)

