"""
utils.py - Drawing utilities.
Includes Win98-style 3-D bevel helpers, hex math, and text utilities.
"""

from __future__ import annotations
import math
from typing import Tuple, List
import pygame
from cascadia.constants import HEX_SIZE, HEX_SPACING, COLORS

SQRT3 = math.sqrt(3)


# ── Hex grid math ─────────────────────────────────────────────────────────────

def hex_to_pixel(q, r, origin_x, origin_y):
    size = HEX_SIZE + HEX_SPACING
    x = origin_x + size * (3 / 2 * q)
    y = origin_y + size * (SQRT3 / 2 * q + SQRT3 * r)
    return (x, y)


def pixel_to_hex(px, py, origin_x, origin_y):
    size = HEX_SIZE + HEX_SPACING
    q_frac = (2 / 3 * (px - origin_x)) / size
    r_frac = (-1 / 3 * (px - origin_x) + SQRT3 / 3 * (py - origin_y)) / size
    return axial_round(q_frac, r_frac)


def axial_round(q, r):
    s = -q - r
    qi, ri, si = round(q), round(r), round(s)
    dq, dr, ds = abs(qi - q), abs(ri - r), abs(si - s)
    if dq > dr and dq > ds:
        qi = -ri - si
    elif dr > ds:
        ri = -qi - si
    return (int(qi), int(ri))


def hex_corners(cx, cy, size=None):
    if size is None:
        size = HEX_SIZE
    return [
        (cx + size * math.cos(math.radians(60 * i)),
         cy + size * math.sin(math.radians(60 * i)))
        for i in range(6)
    ]


# ── Win98 3-D bevel ───────────────────────────────────────────────────────────

def bevel_rect(surface, rect, raised=True, width=2):
    """Classic Win98 chiselled border."""
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    light  = COLORS["bevel_light"]
    mid    = COLORS["bevel_mid"]
    shadow = COLORS["bevel_shadow"]
    dark   = COLORS["bevel_dark"]

    if raised:
        seqs = [(light, dark), (mid, shadow)]
    else:
        seqs = [(dark, light), (shadow, mid)]

    for i in range(min(width, 2)):
        tl, br = seqs[i]
        pygame.draw.line(surface, tl, (x+i,     y+i),     (x+w-2-i, y+i))
        pygame.draw.line(surface, tl, (x+i,     y+i),     (x+i,     y+h-2-i))
        pygame.draw.line(surface, br, (x+i,     y+h-1-i), (x+w-1-i, y+h-1-i))
        pygame.draw.line(surface, br, (x+w-1-i, y+i),     (x+w-1-i, y+h-1-i))


def fill_bevel_rect(surface, rect, raised=True, fill=None):
    f = fill or COLORS["bg_panel"]
    pygame.draw.rect(surface, f, rect)
    bevel_rect(surface, rect, raised=raised)


def draw_title_bar(surface, rect, title, font, active=True):
    col = COLORS["titlebar_active"] if active else COLORS["border"]
    pygame.draw.rect(surface, col, rect)
    txt = font.render(title, True, COLORS["titlebar_text"])
    surface.blit(txt, (rect.x + 6, rect.y + (rect.height - txt.get_height()) // 2))


def draw_window(surface, rect, title, title_font, title_h=22):
    """Full Win98 window: outer bevel + title bar + client area."""
    fill_bevel_rect(surface, rect, raised=True)
    title_rect = pygame.Rect(rect.x + 2, rect.y + 2, rect.width - 4, title_h)
    draw_title_bar(surface, title_rect, title, title_font)
    client = pygame.Rect(rect.x + 2, rect.y + 2 + title_h,
                         rect.width - 4, rect.height - 4 - title_h)
    pygame.draw.rect(surface, COLORS["bg_panel"], client)
    return client


# ── Generic helpers ────────────────────────────────────────────────────────────

def draw_hex(surface, color, cx, cy, size=None, border_color=None,
             border_width=2, alpha=255):
    if size is None:
        size = HEX_SIZE
    corners = [tuple(map(int, c)) for c in hex_corners(cx, cy, size)]
    if alpha < 255:
        s = pygame.Surface((size * 2 + 4, size * 2 + 4), pygame.SRCALPHA)
        shifted = [(x - int(cx) + size + 2, y - int(cy) + size + 2)
                   for x, y in corners]
        pygame.draw.polygon(s, (*color, alpha), shifted)
        surface.blit(s, (int(cx) - size - 2, int(cy) - size - 2))
    else:
        pygame.draw.polygon(surface, color, corners)
        if border_color:
            pygame.draw.polygon(surface, border_color, corners, border_width)


def draw_text(surface, text, font, color, x, y, align="left", max_width=None):
    if max_width:
        text = truncate_text(text, font, max_width)
    surf = font.render(text, True, color)
    if align == "center":
        x -= surf.get_width() // 2
    elif align == "right":
        x -= surf.get_width()
    surface.blit(surf, (x, y))
    return surf.get_width()


def draw_rounded_rect(surface, color, rect, radius=0,
                      border_color=None, border_width=1, alpha=255):
    """Compat shim – Win98 uses plain rects."""
    if alpha < 255:
        s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, alpha), s.get_rect())
        surface.blit(s, (rect.x, rect.y))
    else:
        pygame.draw.rect(surface, color, rect)
    if border_color:
        pygame.draw.rect(surface, border_color, rect, border_width)


def draw_circle_token(surface, color, cx, cy, radius, label="",
                      font=None, text_color=(0, 0, 0), border_color=None):
    pygame.draw.circle(surface, color, (int(cx), int(cy)), radius)
    if border_color:
        pygame.draw.circle(surface, border_color, (int(cx), int(cy)), radius, 2)
    if label and font:
        txt = font.render(label, True, text_color)
        surface.blit(txt, (int(cx) - txt.get_width() // 2,
                           int(cy) - txt.get_height() // 2))


def truncate_text(text, font, max_width):
    if font.size(text)[0] <= max_width:
        return text
    while text and font.size(text + "...")[0] > max_width:
        text = text[:-1]
    return text + "..."


def wrap_text(text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def darken(color, factor=0.7):
    return tuple(int(c * factor) for c in color)

def lighten(color, factor=1.3):
    return tuple(min(255, int(c * factor)) for c in color)

def blend_color(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))
