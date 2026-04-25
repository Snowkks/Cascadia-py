"""
Game screen layout (1280x800, all absolute coordinates):

  x=0        x=220      x=1040     x=1280
  │          │          │          │
  │ LEFT     │  BOARD   │  RIGHT   │
  │ 220px    │  820px   │  240px   │
  │          │          │          │
  y=0  ┌─────┬──────────┬──────────┐
       │Title bar 26px             │
  y=26 ├─────┼──────────┼──────────┤
       │Plyr │          │ Market   │
       │info │  Hex     │ 4 slots  │
       │     │  board   │          │
       │     │  (pan    │ Actions  │
       │     │  RMB)    │          │
       │     │          │ Log      │
  y=774├─────┼──────────┼──────────┤
       │ Status bar 26px           │
  y=800└──────────────────────────-┘
"""
import pygame
from cascadia.constants import (WINDOW_WIDTH as W, WINDOW_HEIGHT as H,
                                 COLORS, HEX_SIZE, MARKET_SIZE)
from cascadia.game_engine import GameEngine, Phase
from cascadia.gui.ui import (C, bevel, title_bar, hrule, txt, font,
                              Button, ScrollList, panel_box)
from cascadia.gui.widgets import HexCell
from cascadia.utils import hex_to_pixel, pixel_to_hex, draw_circle_token

# ── Layout constants ── (change these to tune, they won't overlap)
TH   = 26          # title bar height
STH  = 26          # status bar height
LW   = 220         # left panel width
RW   = 240         # right panel width
BX   = LW          # board left edge
BW   = W - LW - RW # board width  (= 820)
BCX  = BX + BW//2  # board centre x
BCY  = TH + (H - TH - STH)//2  # board centre y

# Right panel x
RX   = W - RW

# Market slots: 4 rows inside right panel
# Each slot: tile card left, token chip right
MK_X     = RX + 6
MK_TW    = RW - 72   # tile card width
MK_TOK_X = RX + RW - 60  # token chip x
MK_TOK_W = 54
MK_SLOT_H= 68        # height of each market row
MK_TOP   = TH + 36  # first slot y (below "Market" header)

# Log below market slots
LOG_Y = MK_TOP + MARKET_SIZE * MK_SLOT_H + 4
LOG_H = H - STH - LOG_Y - 50  # leave room for action buttons above status

# Action button row just above status bar
ACT_Y = H - STH - 46


WILDLIFE_SHORT = {"bear":"BR","elk":"EL","salmon":"SA","hawk":"HK","fox":"FX"}
HABITAT_SHORT  = {"forest":"FOR","wetland":"WET","mountain":"MTN",
                  "prairie":"PRA","river":"RIV"}
W_COLORS = {
    "bear":   (139, 90,  43),
    "elk":    (160,130,  50),
    "salmon": (210, 85,  65),
    "hawk":   (170,140,  40),
    "fox":    (200, 85,  20),
}
H_COLORS = {
    "forest":  (80,130, 60),
    "wetland": (60,130,100),
    "mountain":(110,110,130),
    "prairie": (170,155, 55),
    "river":   (60,120,180),
}


class GameScreen:
    def __init__(self, engine: GameEngine, on_game_over, on_menu):
        self._eng         = engine
        self._on_game_over= on_game_over
        self._on_menu     = on_menu

        self._f_tb  = font(13, bold=True)
        self._f_hdr = font(13, bold=True)
        self._f_row = font(13)
        self._f_sm  = font(11)

        # Board pan state
        self._ox = self._oy = 0
        self._drag = False
        self._drag_start = self._drag_origin = None

        # Nature-pick mode
        self._nat_mode     = False
        self._nat_tile_idx = None

        # Hover
        self._hov_board  = None
        self._hov_market = None

        # Market rects (computed once)
        self._mk_tile_rects  = []
        self._mk_tok_rects   = []
        for i in range(MARKET_SIZE):
            y = MK_TOP + i * MK_SLOT_H
            self._mk_tile_rects.append(pygame.Rect(MK_X, y+4, MK_TW, MK_SLOT_H-8))
            self._mk_tok_rects.append(pygame.Rect(MK_TOK_X, y+12, MK_TOK_W, MK_SLOT_H-24))

        # Log
        self._log  = ScrollList(pygame.Rect(RX+4, LOG_Y, RW-8, LOG_H), fsize=12)
        self._log_n = 0
        for m in engine.log[-40:]: self._log.items.append(m)
        self._log_n = len(engine.log)

        # Action buttons (right panel, above status bar)
        bw2 = (RW-14)//2
        self._btn_discard    = Button((RX+4,       ACT_Y, RW-8,  42), "Discard Token  (+Nature)", self._do_discard, 14, True)
        self._btn_nat_rep    = Button((RX+4,       ACT_Y, bw2,   38), "Replace Tokens",            self._do_nat_rep, 11)
        self._btn_nat_pick   = Button((RX+bw2+10,  ACT_Y, bw2,   38), "Free Pick",                 self._do_nat_pick,11)
        self._btn_menu       = Button((6, H-STH-32, LW-12, 28), "Menu", on_menu, 13)

    # ── helpers ───────────────────────────────────────────────────────────────
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
            self._log.items.append(m)
            if len(self._log.items) > 120:
                self._log.items = self._log.items[-120:]
        self._log_n = len(self._eng.log)
        # auto-scroll to bottom
        vis = self._log._vis()
        self._log._scroll = max(0, len(self._log.items) - vis)

    # ── actions ───────────────────────────────────────────────────────────────
    def _do_discard(self):
        self._eng.discard_token(); self._sync_log()

    def _do_nat_rep(self):
        self._eng.use_nature_token_replace_tokens(); self._sync_log()

    def _do_nat_pick(self):
        if self._eng.current_player.nature_tokens > 0:
            self._nat_mode = True; self._nat_tile_idx = None

    # ── events ────────────────────────────────────────────────────────────────
    def handle_event(self, ev):
        if self._eng.is_game_over():
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                self._on_menu()
            # still handle menu button
            self._btn_menu.handle(ev)
            return

        self._btn_menu.handle(ev)
        self._log.handle(ev)

        phase = self._eng.phase
        nt    = self._eng.current_player.nature_tokens > 0

        self._btn_discard.enabled  = (phase == Phase.PLACE_TOKEN)
        self._btn_nat_rep.enabled  = (phase == Phase.SELECT_PAIR and nt)
        self._btn_nat_pick.enabled = (phase == Phase.SELECT_PAIR and nt)

        self._btn_discard.handle(ev)
        self._btn_nat_rep.handle(ev)
        self._btn_nat_pick.handle(ev)

        if ev.type == pygame.MOUSEMOTION:
            mx, my = ev.pos
            self._hov_board  = self._p2b(mx, my) if self._in_board(mx, my) else None
            self._hov_market = next(
                (i for i in range(MARKET_SIZE)
                 if self._mk_tile_rects[i].collidepoint(ev.pos) or
                    self._mk_tok_rects[i].collidepoint(ev.pos)), None)
            if self._drag and self._drag_start:
                self._ox = self._drag_origin[0] + mx - self._drag_start[0]
                self._oy = self._drag_origin[1] + my - self._drag_start[1]

        if ev.type == pygame.MOUSEBUTTONDOWN:
            if ev.button in (2, 3):
                self._drag        = True
                self._drag_start  = ev.pos
                self._drag_origin = (self._ox, self._oy)
            if ev.button == 1:
                self._on_click(ev.pos)

        if ev.type == pygame.MOUSEBUTTONUP and ev.button in (2, 3):
            self._drag = False

        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self._nat_mode = False

    def _on_click(self, pos):
        eng   = self._eng
        phase = eng.phase
        mx, my = pos

        # ── SELECT_PAIR ──────────────────────────────────────────────────
        if phase == Phase.SELECT_PAIR:
            if self._nat_mode:
                # step 1: pick tile slot
                if self._nat_tile_idx is None:
                    for i in range(MARKET_SIZE):
                        if self._mk_tile_rects[i].collidepoint(pos) and eng.market_tiles[i]:
                            self._nat_tile_idx = i
                            return
                # step 2: pick token slot
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

        # ── PLACE_TILE ───────────────────────────────────────────────────
        elif phase == Phase.PLACE_TILE:
            if self._in_board(mx, my):
                q, r = self._p2b(mx, my)
                if eng.place_tile(q, r): self._sync_log()

        # ── PLACE_TOKEN ──────────────────────────────────────────────────
        elif phase == Phase.PLACE_TOKEN:
            if self._in_board(mx, my):
                q, r = self._p2b(mx, my)
                if eng.place_token(q, r):
                    self._sync_log()
                    if eng.is_game_over(): self._on_game_over(eng)

    # ── update/draw ───────────────────────────────────────────────────────────
    def update(self): pass

    def draw(self, surf):
        surf.fill(C["face"])
        self._draw_title(surf)
        self._draw_status(surf)
        self._draw_left(surf)
        self._draw_board(surf)
        self._draw_right(surf)
        # vertical dividers
        pygame.draw.line(surf, C["gray"],  (LW,   TH), (LW,   H-STH))
        pygame.draw.line(surf, C["white"], (LW+1, TH), (LW+1, H-STH))
        pygame.draw.line(surf, C["gray"],  (RX,   TH), (RX,   H-STH))
        pygame.draw.line(surf, C["white"], (RX+1, TH), (RX+1, H-STH))
        if self._eng.is_game_over():
            self._draw_gameover(surf)

    def _draw_title(self, surf):
        eng = self._eng
        lbl = (f"Cascadia  —  {eng.current_player.name}'s Turn"
               f"   (Turn {eng.turns_taken+1}/{eng.total_turns})")
        title_bar(surf, pygame.Rect(0, 0, W, TH), lbl, self._f_tb)

    def _draw_status(self, surf):
        eng = self._eng
        msgs = {
            Phase.SELECT_PAIR:  "Click a market slot (tile card or token) to select the pair",
            Phase.PLACE_TILE:   "Click a green hex on the board to place your tile",
            Phase.PLACE_TOKEN:  "Click a highlighted tile to place token  —  or use Discard button",
            Phase.GAME_OVER:    "Game over!  Press ESC or click Menu to return.",
        }
        sb = pygame.Rect(0, H-STH, W, STH)
        pygame.draw.rect(surf, C["face"], sb)
        bevel(surf, sb, raised=False)
        msg = msgs.get(eng.phase, "")
        if self._nat_mode:
            msg = ("Step 1: click a TILE card" if self._nat_tile_idx is None
                   else "Step 2: click a TOKEN chip")
        txt(surf, msg, self._f_sm, C["black"], 8, H-STH+7)

    def _draw_left(self, surf):
        eng = self._eng
        pygame.draw.rect(surf, C["face"], pygame.Rect(0, TH, LW, H-TH-STH))

        y = TH + 8
        txt(surf, "Scoring Cards", self._f_hdr, C["black"], 8, y); y += 20
        for w, v in eng.scoring_cards.items():
            col = W_COLORS.get(w, (100,100,100))
            pygame.draw.circle(surf, col, (16, y+7), 6)
            pygame.draw.circle(surf, C["black"], (16, y+7), 6, 1)
            txt(surf, f"{WILDLIFE_SHORT.get(w,w[:2])} — Card {v}",
                self._f_row, C["black"], 26, y)
            y += 18
        y += 4
        hrule(surf, y, 4, LW-4); y += 8

        txt(surf, "Players", self._f_hdr, C["black"], 8, y); y += 20
        for p in eng.players:
            is_cur = (p.player_id == eng.current_player.player_id
                      and not eng.is_game_over())
            row_r  = pygame.Rect(4, y-2, LW-8, 56)

            if is_cur:
                # Bold coloured banner for the active player
                pygame.draw.rect(surf, C["title"], row_r)          # navy fill
                pygame.draw.rect(surf, (100,140,255),
                                 pygame.Rect(4, y-2, 5, 56))       # accent stripe
                name_col  = C["white"]
                extra_col = (180, 200, 255)
                prefix = ">>>"
            else:
                pygame.draw.rect(surf, C["face"], row_r)
                bevel(surf, row_r, raised=True)
                name_col  = C["black"]
                extra_col = C["muted"]
                prefix = "   "

            pygame.draw.circle(surf, p.color,   (22, y+10), 9)
            pygame.draw.circle(surf, C["white"] if is_cur else C["black"],
                               (22, y+10), 9, 1)
            txt(surf, f"{prefix} {p.name}", self._f_hdr, name_col, 34, y)
            txt(surf, f"  Nature tokens: {p.nature_tokens}", self._f_sm, extra_col, 34, y+18)

            # wildlife token counts
            tx = 34
            for w, cnt in p.wildlife_counts().items():
                if cnt:
                    col = W_COLORS.get(w, (100,100,100))
                    pygame.draw.circle(surf, col,                       (tx+5, y+36), 5)
                    pygame.draw.circle(surf, C["white"] if is_cur else C["black"],
                                       (tx+5, y+36), 5, 1)
                    txt(surf, str(cnt), self._f_sm, extra_col, tx+12, y+30)
                    tx += 26
            y += 62
        hrule(surf, y, 4, LW-4); y += 6

        # Tile count
        txt(surf, f"Board: {len(eng.current_player.board)} tiles",
            self._f_sm, C["muted"], 8, y)

        self._btn_menu.draw(surf)

    def _draw_board(self, surf):
        eng   = self._eng
        phase = eng.phase

        board_r = pygame.Rect(BX+2, TH, BW-4, H-TH-STH)
        pygame.draw.rect(surf, (150,150,150), board_r)

        ghost_pos = eng.pending_placement_positions if phase==Phase.PLACE_TILE else []
        tok_pos   = (eng.get_valid_token_positions()
                     if phase==Phase.PLACE_TOKEN and eng.selected_token else [])

        clip = surf.get_clip()
        surf.set_clip(board_r)

        for (q, r), tile in eng.current_player.board.items():
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

        # Phase hint inside board
        phase_hint = {
            Phase.PLACE_TILE:  "Click a green hex to place tile",
            Phase.PLACE_TOKEN: "Click highlighted tile to place token",
        }
        if eng.phase in phase_hint:
            s = self._f_sm.render(phase_hint[eng.phase], True, C["black"])
            bx2 = BCX - s.get_width()//2 - 4
            by2 = TH + 4
            pygame.draw.rect(surf, C["face"],
                             pygame.Rect(bx2-2, by2-2, s.get_width()+12, s.get_height()+4))
            bevel(surf, pygame.Rect(bx2-2, by2-2, s.get_width()+12, s.get_height()+4),
                  raised=True)
            surf.blit(s, (bx2+4, by2))

        txt(surf, "Right-click drag to pan board",
            self._f_sm, (60,60,60), BCX, H-STH-14, cx=True)

    def _draw_right(self, surf):
        eng   = self._eng
        phase = eng.phase
        pygame.draw.rect(surf, C["face"], pygame.Rect(RX, TH, RW, H-TH-STH))

        # "Market" header
        txt(surf, "Market", self._f_hdr, C["black"], RX + RW//2, TH+8, cx=True)
        hrule(surf, TH+26, RX+4, W-4)

        for i in range(MARKET_SIZE):
            tile = eng.market_tiles[i]
            tok  = eng.market_tokens[i]
            tr   = self._mk_tile_rects[i]
            kr   = self._mk_tok_rects[i]

            hov = (self._hov_market == i and phase == Phase.SELECT_PAIR)
            nat_t = (self._nat_mode and self._nat_tile_idx == i)

            # Tile card
            fill = H_COLORS.get(tile.primary_habitat(), (200,200,200)) if tile else C["face"]
            pygame.draw.rect(surf, fill, tr)
            bevel(surf, tr, raised=not (hov or nat_t))

            if tile:
                hab = "/".join(HABITAT_SHORT.get(h,h[:3]) for h in tile.habitats)
                acc = " ".join(WILDLIFE_SHORT.get(w,w[:2]) for w in tile.accepts)
                txt(surf, f"[{i+1}] {hab}", self._f_sm, C["black"], tr.x+4, tr.y+4)
                txt(surf, f"  {acc}",        self._f_sm, (40,40,40),  tr.x+4, tr.y+18)
                if tile.keystone:
                    txt(surf, "KEY", self._f_sm, (120,80,0), tr.x+4, tr.y+32)
            else:
                txt(surf, "(empty)", self._f_sm, C["gray"], tr.x+4, tr.y+16)

            # Token chip
            if tok:
                col = W_COLORS.get(tok.wildlife_type, (150,150,150))
                pygame.draw.rect(surf, col, kr)
                bevel(surf, kr, raised=not hov)
                lbl = WILDLIFE_SHORT.get(tok.wildlife_type, tok.wildlife_type[:2])
                s = self._f_row.render(lbl, True, C["black"])
                surf.blit(s, (kr.x + (kr.w-s.get_width())//2,
                              kr.y + (kr.h-s.get_height())//2))
            else:
                pygame.draw.rect(surf, C["face"], kr)
                bevel(surf, kr, raised=False)

        # Separator above actions
        act_sep = ACT_Y - 6
        hrule(surf, act_sep, RX+4, W-4)

        # Action buttons
        if phase == Phase.PLACE_TOKEN:
            # Amber/yellow discard button — hard to miss
            r = self._btn_discard.rect
            amber      = (210, 140,  0)
            amber_dark = (160, 100,  0)
            amber_lite = (255, 200, 80)
            pygame.draw.rect(surf, amber, r)
            # manual bevel in amber tones
            pygame.draw.line(surf, amber_lite, (r.x,     r.y),     (r.right-2, r.y))
            pygame.draw.line(surf, amber_lite, (r.x,     r.y),     (r.x,       r.bottom-2))
            pygame.draw.line(surf, amber_dark, (r.x,     r.bottom-1), (r.right-1, r.bottom-1))
            pygame.draw.line(surf, amber_dark, (r.right-1, r.y),   (r.right-1, r.bottom-1))
            s = font(14, bold=True).render("Discard Token  (+Nature)", True, C["black"])
            surf.blit(s, (r.x + (r.w - s.get_width())//2,
                          r.y + (r.h - s.get_height())//2))
        elif phase == Phase.SELECT_PAIR and eng.current_player.nature_tokens > 0:
            txt(surf, f"Nature tokens: {eng.current_player.nature_tokens}",
                self._f_sm, C["black"], RX+4, ACT_Y-18)
            self._btn_nat_rep.draw(surf)
            self._btn_nat_pick.draw(surf)

        # Selected pair preview
        if eng.selected_tile:
            py = act_sep - 46
            txt(surf, "Selected:", self._f_sm, C["muted"], RX+4, py)
            hab = "/".join(HABITAT_SHORT.get(h,h[:3]) for h in eng.selected_tile.habitats)
            txt(surf, f"Tile: {hab}", self._f_row, C["black"], RX+4, py+14)
            if eng.selected_token:
                txt(surf, f"Token: {eng.selected_token.wildlife_type}",
                    self._f_row, C["black"], RX+4, py+30)

        # Log
        txt(surf, "Event log:", self._f_sm, C["muted"], RX+4, LOG_Y-16)
        self._log.draw(surf)

    def _draw_gameover(self, surf):
        # Modal centred overlay
        MW, MH = 520, 320
        mx = (W - MW)//2
        my = (H - MH)//2
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0,0,0,140))
        surf.blit(overlay, (0,0))

        panel_box(surf, pygame.Rect(mx, my, MW, MH))
        title_bar(surf, pygame.Rect(mx+2, my+2, MW-4, TH),
                  "Game Over — Final Scores", self._f_hdr)

        y = my + 2 + TH + 10
        for rank, p in enumerate(sorted(self._eng.players, key=lambda x:-x.score)):
            bd  = self._eng.scores.get(p.player_id)
            med = ["1st","2nd","3rd","4th"][rank]
            pygame.draw.circle(surf, p.color,   (mx+18, y+10), 8)
            pygame.draw.circle(surf, C["black"], (mx+18, y+10), 8, 1)
            txt(surf, f"{med}  {p.name}: {p.score} pts",
                self._f_hdr, C["black"], mx+30, y)
            y += 22
            if bd:
                ws = bd.wildlife_scores
                line = (f"  Bear:{ws.get('bear',0)}  Elk:{ws.get('elk',0)}"
                        f"  Salmon:{ws.get('salmon',0)}  Hawk:{ws.get('hawk',0)}"
                        f"  Fox:{ws.get('fox',0)}  Habitat:{bd.habitat_score}"
                        f"  Nature:{bd.nature_token_score}")
                txt(surf, line, self._f_sm, C["muted"], mx+14, y)
                y += 18

        y += 10
        hrule(surf, y, mx+10, mx+MW-10)
        y += 10
        txt(surf, "Press ESC or click Menu to return to main menu.",
            self._f_sm, C["muted"], mx+MW//2, y, cx=True)
