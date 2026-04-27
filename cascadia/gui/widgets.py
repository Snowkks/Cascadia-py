"""
widgets.py - Win98-style UI widgets.

All buttons use proper bevel borders and exact rect hit-testing.
No rounded corners, no transparency tricks that break click areas.
"""

from __future__ import annotations
import pygame
from typing import Tuple, Optional, Callable, List
from cascadia.constants import COLORS, HEX_SIZE
from cascadia.utils import (bevel_rect, fill_bevel_rect, draw_hex,
                             draw_text, draw_circle_token, hex_corners, wrap_text)
from cascadia.gui.ui import font as get_font_raw
from cascadia.gui.resources import WILDLIFE_ASCII, HABITAT_LABELS
def get_font(size, bold=False, italic=False): return get_font_raw(size, bold)


# ── Button ────────────────────────────────────────────────────────────────────

class Button:
    """
    Win98-style push button.
    Exact pygame.Rect hit detection — no scaling confusion.
    """
    def __init__(self, rect, label, callback=None,
                 color=None, hover_color=None, text_color=None,
                 font_size=16, disabled=False, radius=0):
        self.rect        = pygame.Rect(rect)   # always a real Rect
        self.label       = label
        self.callback    = callback
        self.disabled    = disabled
        self._pressed    = False
        self._hovered    = False
        self._font       = get_font(font_size, bold=False)

    def handle_event(self, event):
        if self.disabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            self._hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._pressed = True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed = self._pressed
            self._pressed = False
            if was_pressed and self.rect.collidepoint(event.pos):
                if self.callback:
                    self.callback()
                return True
        return False

    def draw(self, surface):
        # Fill
        fill = COLORS["bg_panel"]
        if self.disabled:
            pygame.draw.rect(surface, fill, self.rect)
            bevel_rect(surface, self.rect, raised=True)
            txt_col = COLORS["disabled"]
        else:
            pygame.draw.rect(surface, fill, self.rect)
            bevel_rect(surface, self.rect, raised=not self._pressed)
            txt_col = COLORS["text_dark"]

        # Text — shift 1px when pressed
        ox = 1 if self._pressed else 0
        cx = self.rect.centerx + ox
        cy = self.rect.centery - self._font.get_height() // 2 + ox
        draw_text(surface, self.label, self._font, txt_col, cx, cy, align="center")

        # Focus rectangle when hovered
        if self._hovered and not self.disabled:
            fr = self.rect.inflate(-6, -6)
            pygame.draw.rect(surface, COLORS["text_dark"], fr, 1)

    def set_disabled(self, val):
        self.disabled = val
        if val:
            self._pressed = False


# ── GroupBox ──────────────────────────────────────────────────────────────────

class GroupBox:
    """Win98 group box (labelled sunken border)."""
    def __init__(self, rect, label="", font_size=13):
        self.rect  = pygame.Rect(rect)
        self.label = label
        self._font = get_font(font_size)

    def draw(self, surface):
        r = self.rect
        lw = self._font.size(self.label)[0] + 8 if self.label else 0

        # Sunken bevel, leaving a gap for the label
        inner = pygame.Rect(r.x, r.y + 8, r.width, r.height - 8)
        bevel_rect(surface, inner, raised=False, width=1)

        # Mask the top border behind the label
        if self.label:
            pygame.draw.rect(surface, COLORS["bg_panel"],
                             pygame.Rect(r.x + 8, r.y + 4, lw, 12))
            draw_text(surface, self.label, self._font,
                      COLORS["text_dark"], r.x + 12, r.y + 2)

    @property
    def client(self):
        return pygame.Rect(self.rect.x + 8, self.rect.y + 18,
                           self.rect.width - 16, self.rect.height - 26)


# ── Label ─────────────────────────────────────────────────────────────────────

class Label:
    def __init__(self, x, y, text, font_size=14, color=None, bold=False):
        self.x = x; self.y = y; self.text = text
        self._font  = get_font(font_size, bold=bold)
        self._color = color or COLORS["text_dark"]

    def draw(self, surface):
        draw_text(surface, self.text, self._font, self._color, self.x, self.y)


# ── TextInput ─────────────────────────────────────────────────────────────────

class TextInput:
    """Single-line text entry field with sunken border."""
    def __init__(self, rect, text="", max_len=24, font_size=16):
        self.rect    = pygame.Rect(rect)
        self.text    = text
        self.max_len = max_len
        self._font   = get_font(font_size)
        self.focused = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.focused = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.focused:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.unicode and len(self.text) < self.max_len:
                self.text += event.unicode

    def draw(self, surface):
        # Sunken inset
        pygame.draw.rect(surface, COLORS["white"], self.rect)
        bevel_rect(surface, self.rect, raised=False, width=2)
        # Cursor blink
        display = self.text
        if self.focused and (pygame.time.get_ticks() // 500) % 2 == 0:
            display += "|"
        draw_text(surface, display, self._font, COLORS["text_dark"],
                  self.rect.x + 4, self.rect.y + (self.rect.height - self._font.get_height()) // 2)


# ── ListBox ───────────────────────────────────────────────────────────────────

class ListBox:
    """Simple Win98 list box with selection highlight."""
    def __init__(self, rect, items=None, font_size=14):
        self.rect     = pygame.Rect(rect)
        self.items    = items or []
        self._font    = get_font(font_size)
        self._lh      = self._font.get_height() + 3
        self.selected = -1
        self._scroll  = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                rel_y = event.pos[1] - self.rect.y - 2
                idx   = rel_y // self._lh + self._scroll
                if 0 <= idx < len(self.items):
                    self.selected = idx
        if event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(pygame.mouse.get_pos()):
            vis = (self.rect.height - 4) // self._lh
            self._scroll = max(0, min(self._scroll - event.y,
                                      max(0, len(self.items) - vis)))

    def draw(self, surface):
        pygame.draw.rect(surface, COLORS["white"], self.rect)
        bevel_rect(surface, self.rect, raised=False, width=2)
        clip = surface.get_clip()
        surface.set_clip(self.rect.inflate(-2, -2))
        vis = (self.rect.height - 4) // self._lh
        for i, item in enumerate(self.items[self._scroll:self._scroll + vis]):
            row_y = self.rect.y + 2 + i * self._lh
            row_r = pygame.Rect(self.rect.x + 2, row_y, self.rect.width - 4, self._lh)
            actual_i = i + self._scroll
            if actual_i == self.selected:
                pygame.draw.rect(surface, COLORS["listbox_sel"], row_r)
                txt_col = COLORS["white"]
            else:
                txt_col = COLORS["text_dark"]
            draw_text(surface, str(item), self._font, txt_col,
                      self.rect.x + 6, row_y + 1)
        surface.set_clip(clip)


# ── HexCell ───────────────────────────────────────────────────────────────────

class HexCell:
    def __init__(self, cx, cy, tile=None, size=None,
                 ghost=False, selected=False, highlight=False):
        self.cx        = cx
        self.cy        = cy
        self.tile      = tile
        self.size      = size or HEX_SIZE
        self.ghost     = ghost
        self.selected  = selected
        self.highlight = highlight
        self._font     = get_font(13)
        self._tok_font = get_font(13, bold=True)

    @property
    def _fill_color(self):
        if self.tile is None:
            return COLORS["bg_panel"]
        return COLORS.get(self.tile.primary_habitat(), COLORS["bg_panel"])

    def draw(self, surface):
        if self.ghost:
            draw_hex(surface, (100, 200, 100), self.cx, self.cy, self.size,
                     border_color=(0, 180, 0), border_width=3, alpha=160)
            # "+" in centre of ghost cell
            s = self._font.render("+", True, (0, 100, 0))
            surface.blit(s, (int(self.cx) - s.get_width()//2,
                              int(self.cy) - s.get_height()//2))
            return

        fill   = self._fill_color
        border = (0, 0, 0)
        bw     = 1

        if self.selected:
            border, bw = (0, 0, 180), 3
        elif self.highlight:
            border = (0, 255, 80)   # neon green border only
            bw     = 4
            # no fill change — tile keeps its normal colour

        draw_hex(surface, fill, self.cx, self.cy, self.size,
                 border_color=border, border_width=bw)

        # Second outer neon ring for extra visibility
        if self.highlight:
            draw_hex(surface, fill, self.cx, self.cy, self.size + 4,
                     border_color=(0, 255, 80), border_width=2)

        if self.tile and len(self.tile.habitats) == 2:
            self._draw_dual(surface)

        if self.tile:
            self._draw_tile_info(surface)

    def _draw_tile_info(self, surface):
        cx, cy = int(self.cx), int(self.cy)
        s      = self.size
        f_hab  = get_font(11, bold=True)

        # Habitat label at top of hex
        hab = "/".join(HABITAT_LABELS.get(h, h[:3]) for h in self.tile.habitats)
        draw_text(surface, hab, f_hab, (255, 255, 255), cx, cy - int(s * 0.58), align="center")

        # Yellow dot top-right = keystone tile (only 1 wildlife accepted)
        if self.tile.keystone:
            pygame.draw.circle(surface, (255, 215, 0),
                               (int(cx + s * 0.58), int(cy - s * 0.58)), 5)
            pygame.draw.circle(surface, (0, 0, 0),
                               (int(cx + s * 0.58), int(cy - s * 0.58)), 5, 1)

        if self.tile.token:
            self._draw_token(surface)
        else:
            self._draw_accepted(surface)

    def _draw_token(self, surface):
        tok   = self.tile.token
        color = COLORS.get(tok.wildlife_type, (180, 180, 180))
        cx, cy = int(self.cx), int(self.cy) + 4
        pygame.draw.circle(surface, color,     (cx, cy), 16)
        pygame.draw.circle(surface, (0, 0, 0), (cx, cy), 16, 2)
        f   = get_font(11, bold=True)
        lbl = tok.wildlife_type.capitalize()
        s   = f.render(lbl, True, (0, 0, 0))
        surface.blit(s, (cx - s.get_width()//2, cy - s.get_height()//2))

    def _draw_accepted(self, surface):
        """
        Each accepted wildlife = coloured SQUARE + full name.
        Squares are easier to distinguish than tiny circles.
        """
        accepts = sorted(self.tile.accepts)
        n       = len(accepts)
        cx      = int(self.cx)
        f       = get_font(10)
        lh      = f.get_height() + 2

        total_h = n * lh
        start_y = int(self.cy) + 4 - total_h // 2

        for i, w in enumerate(accepts):
            col  = COLORS.get(w, (150, 150, 150))
            name = w.capitalize()
            y    = start_y + i * lh
            sq_x = cx - 30

            # Coloured square (10×10) — easier to read than a dot
            pygame.draw.rect(surface, col,       (sq_x, y + 1, 10, 10))
            pygame.draw.rect(surface, (0, 0, 0), (sq_x, y + 1, 10, 10), 1)

            s = f.render(name, True, (255, 255, 255))
            surface.blit(s, (sq_x + 13, y))

    def _draw_dual(self, surface):
        """Tint the right half of the hex with the second habitat colour."""
        h2 = COLORS.get(self.tile.habitats[1], (192, 192, 192))
        corners = hex_corners(self.cx, self.cy, self.size)
        right = [corners[5], corners[0], corners[1], corners[2], (self.cx, self.cy)]
        pygame.draw.polygon(surface, h2, [(int(x), int(y)) for x, y in right])
        pygame.draw.polygon(surface, (0, 0, 0),
                            [(int(x), int(y)) for x, y in corners], 1)

    def contains_point(self, px, py):
        return ((px - self.cx) ** 2 + (py - self.cy) ** 2) < (self.size ** 2)


# ── TokenCircle ───────────────────────────────────────────────────────────────

class TokenCircle:
    def __init__(self, cx, cy, wildlife_type, radius=22, selected=False):
        self.cx           = cx
        self.cy           = cy
        self.wildlife_type = wildlife_type
        self.radius       = radius
        self.selected     = selected
        self._font        = get_font(13, bold=True)

    def draw(self, surface):
        color  = COLORS.get(self.wildlife_type, (180, 180, 180))
        border = (0, 0, 128) if self.selected else (0, 0, 0)
        label  = WILDLIFE_ASCII.get(self.wildlife_type, self.wildlife_type[:2].upper())
        if self.selected:
            pygame.draw.circle(surface, (0, 0, 128),
                               (self.cx, self.cy), self.radius + 4, 3)
        draw_circle_token(surface, color, self.cx, self.cy, self.radius,
                          label=label, font=self._font,
                          text_color=(0, 0, 0), border_color=border)

    def contains_point(self, px, py):
        return ((px - self.cx) ** 2 + (py - self.cy) ** 2) < (self.radius ** 2)


# ── ScrollLog ─────────────────────────────────────────────────────────────────

class ScrollLog:
    def __init__(self, rect, max_lines=80):
        self.rect      = pygame.Rect(rect)
        self.max_lines = max_lines
        self.lines     = []
        self.scroll    = 0
        self._font     = get_font(13)
        self._lh       = self._font.get_height() + 2

    def add(self, msg):
        wrapped = wrap_text(msg, self._font, self.rect.width - 8)
        self.lines.extend(wrapped)
        if len(self.lines) > self.max_lines:
            self.lines = self.lines[-self.max_lines:]
        vis = (self.rect.height - 4) // self._lh
        self.scroll = max(0, len(self.lines) - vis)

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(pygame.mouse.get_pos()):
            vis = (self.rect.height - 4) // self._lh
            self.scroll = max(0, min(self.scroll - event.y,
                                     max(0, len(self.lines) - vis)))

    def draw(self, surface):
        pygame.draw.rect(surface, COLORS["white"], self.rect)
        bevel_rect(surface, self.rect, raised=False, width=2)
        clip = surface.get_clip()
        surface.set_clip(self.rect.inflate(-2, -2))
        vis = (self.rect.height - 4) // self._lh
        for i, line in enumerate(self.lines[self.scroll:self.scroll + vis]):
            draw_text(surface, line, self._font, COLORS["text_dark"],
                      self.rect.x + 4, self.rect.y + 2 + i * self._lh)
        surface.set_clip(clip)


# ── Tooltip ───────────────────────────────────────────────────────────────────

class Tooltip:
    def __init__(self):
        self._font = get_font(13)
        self._text = ""
        self._pos  = (0, 0)
        self.visible = False

    def show(self, text, pos):
        self._text   = text
        self._pos    = pos
        self.visible = True

    def hide(self):
        self.visible = False

    def draw(self, surface):
        if not self.visible or not self._text:
            return
        lines = self._text.split("\n")
        w = max(self._font.size(l)[0] for l in lines) + 12
        h = len(lines) * (self._font.get_height() + 2) + 8
        x, y = self._pos[0] + 14, self._pos[1] + 14
        x = min(x, surface.get_width()  - w - 4)
        y = min(y, surface.get_height() - h - 4)
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(surface, (255, 255, 225), rect)
        bevel_rect(surface, rect, raised=True, width=1)
        for i, line in enumerate(lines):
            draw_text(surface, line, self._font, COLORS["text_dark"],
                      x + 6, y + 4 + i * (self._font.get_height() + 2))
