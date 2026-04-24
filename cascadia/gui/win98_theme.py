"""
win98_theme.py - Windows 98 / classic desktop colour palette and draw primitives.

Everything in the game UI uses these values so the look is consistent.
"""

import pygame
from typing import Tuple

# ── Classic Win98 system colours ──────────────────────────────────────────────
W = {
    "desktop":        (0,   128, 128),   # teal desktop
    "face":           (212, 208, 200),   # button / panel face (grey)
    "face_light":     (236, 233, 216),   # lighter panel variant
    "highlight":      (10,  36,  106),   # title bar active (dark blue)
    "highlight_text": (255, 255, 255),   # title bar text
    "inactive_title": (128, 128, 128),   # inactive title bar
    "btn_shadow":     (128, 128, 128),   # dark border half
    "btn_dark":       (64,  64,  64),    # darkest border
    "btn_light":      (255, 255, 255),   # light border half
    "btn_face":       (212, 208, 200),   # normal button face
    "btn_face_down":  (192, 192, 192),   # pressed button face
    "btn_text":       (0,   0,   0),     # button label
    "btn_disabled":   (128, 128, 128),   # greyed out label
    "window_bg":      (255, 255, 255),   # client area white
    "menu_bg":        (212, 208, 200),
    "text":           (0,   0,   0),
    "text_disabled":  (128, 128, 128),
    "select_bg":      (10,  36,  106),
    "select_text":    (255, 255, 255),
    "tooltip_bg":     (255, 255, 225),
    "tooltip_border": (0,   0,   0),

    # habitat / wildlife kept from original (used on hex tiles)
    "forest":         (100, 160,  80),
    "wetland":        (70,  160, 120),
    "mountain":       (140, 150, 170),
    "prairie":        (200, 185,  80),
    "river":          (80,  160, 210),
    "bear":           (140,  90,  40),
    "elk":            (180, 140,  60),
    "salmon":         (220, 100,  70),
    "hawk":           (200, 170,  50),
    "fox":            (210, 100,  30),
}


# ── Raised / sunken bevel (the hallmark of Win9x UI) ─────────────────────────

def draw_raised(surface: pygame.Surface, rect: pygame.Rect, width: int = 2):
    """Draw a raised bevel (button normal state)."""
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    for i in range(width):
        # top-left: bright
        pygame.draw.line(surface, W["btn_light"],  (x+i, y+i), (x+w-1-i, y+i))
        pygame.draw.line(surface, W["btn_light"],  (x+i, y+i), (x+i, y+h-1-i))
        # bottom-right: dark
        pygame.draw.line(surface, W["btn_dark"],   (x+i, y+h-1-i), (x+w-1-i, y+h-1-i))
        pygame.draw.line(surface, W["btn_dark"],   (x+w-1-i, y+i), (x+w-1-i, y+h-1-i))
        # inner shadow
        pygame.draw.line(surface, W["btn_shadow"], (x+1+i, y+1+i), (x+w-2-i, y+1+i))
        pygame.draw.line(surface, W["btn_shadow"], (x+1+i, y+1+i), (x+1+i, y+h-2-i))


def draw_sunken(surface: pygame.Surface, rect: pygame.Rect, width: int = 2):
    """Draw a sunken bevel (pressed button / input field)."""
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    for i in range(width):
        pygame.draw.line(surface, W["btn_dark"],   (x+i, y+i), (x+w-1-i, y+i))
        pygame.draw.line(surface, W["btn_dark"],   (x+i, y+i), (x+i, y+h-1-i))
        pygame.draw.line(surface, W["btn_shadow"], (x+1+i, y+1+i), (x+w-2-i, y+1+i))
        pygame.draw.line(surface, W["btn_shadow"], (x+1+i, y+1+i), (x+1+i, y+h-2-i))
        pygame.draw.line(surface, W["btn_light"],  (x+i, y+h-1-i), (x+w-1-i, y+h-1-i))
        pygame.draw.line(surface, W["btn_light"],  (x+w-1-i, y+i), (x+w-1-i, y+h-1-i))


def draw_field(surface: pygame.Surface, rect: pygame.Rect):
    """Draw a text-field / list-box style sunken border (thinner)."""
    pygame.draw.rect(surface, W["window_bg"], rect)
    draw_sunken(surface, rect, width=1)


def draw_title_bar(
    surface: pygame.Surface,
    rect: pygame.Rect,
    title: str,
    font: pygame.font.Font,
    active: bool = True,
):
    """Draw a classic Win98 title bar with gradient-like solid colour."""
    colour = W["highlight"] if active else W["inactive_title"]
    pygame.draw.rect(surface, colour, rect)
    txt = font.render(title, True, W["highlight_text"])
    surface.blit(txt, (rect.x + 6, rect.y + (rect.height - txt.get_height()) // 2))


def draw_window(
    surface: pygame.Surface,
    rect: pygame.Rect,
    title: str,
    font: pygame.font.Font,
    title_h: int = 22,
):
    """Draw a complete Win98 window frame (title bar + client area)."""
    # Outer raised bevel
    draw_raised(surface, rect)
    # Fill face colour
    inner = rect.inflate(-4, -4)
    pygame.draw.rect(surface, W["face"], inner)
    # Title bar
    title_rect = pygame.Rect(rect.x + 2, rect.y + 2, rect.width - 4, title_h)
    draw_title_bar(surface, title_rect, title, font)
    # Client area (white)
    client = pygame.Rect(rect.x + 4, rect.y + 2 + title_h, rect.width - 8, rect.height - 6 - title_h)
    pygame.draw.rect(surface, W["face_light"], client)
    return client   # caller can use this as their drawing area


def draw_groupbox(
    surface: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    font: pygame.font.Font,
):
    """Draw a Win98 group box (labelled sunken rectangle)."""
    lbl_surf = font.render(f" {label} ", True, W["text"])
    lbl_w    = lbl_surf.get_width()
    # Top line with gap for label
    top_y = rect.y + font.get_height() // 2
    pygame.draw.line(surface, W["btn_shadow"], (rect.x, top_y), (rect.x + 8, top_y))
    pygame.draw.line(surface, W["btn_shadow"], (rect.x + 8 + lbl_w, top_y),
                     (rect.right, top_y))
    pygame.draw.line(surface, W["btn_light"],  (rect.x + 1, top_y + 1), (rect.x + 8, top_y + 1))
    pygame.draw.line(surface, W["btn_light"],  (rect.x + 8 + lbl_w, top_y + 1),
                     (rect.right - 1, top_y + 1))
    # Other 3 sides
    pygame.draw.line(surface, W["btn_shadow"], (rect.x, top_y),       (rect.x,      rect.bottom))
    pygame.draw.line(surface, W["btn_shadow"], (rect.x, rect.bottom),  (rect.right,  rect.bottom))
    pygame.draw.line(surface, W["btn_shadow"], (rect.right, top_y),    (rect.right,  rect.bottom))
    pygame.draw.line(surface, W["btn_light"],  (rect.x + 1, top_y + 1), (rect.x + 1, rect.bottom - 1))
    pygame.draw.line(surface, W["btn_light"],  (rect.x + 1, rect.bottom - 1), (rect.right - 1, rect.bottom - 1))
    pygame.draw.line(surface, W["btn_light"],  (rect.right - 1, top_y + 1),   (rect.right - 1, rect.bottom - 1))
    # Label
    surface.blit(lbl_surf, (rect.x + 9, rect.y))


def draw_separator(surface: pygame.Surface, x1: int, y: int, x2: int):
    """Horizontal Win98 separator line (two pixels)."""
    pygame.draw.line(surface, W["btn_shadow"], (x1, y),     (x2, y))
    pygame.draw.line(surface, W["btn_light"],  (x1, y + 1), (x2, y + 1))


def draw_progress_bar(
    surface: pygame.Surface,
    rect: pygame.Rect,
    value: float,     # 0.0 – 1.0
    label: str = "",
    font: pygame.font.Font = None,
):
    """Win98 style segmented progress bar."""
    draw_sunken(surface, rect, width=1)
    inner = rect.inflate(-2, -2)
    fill_w = int(inner.width * max(0.0, min(1.0, value)))
    seg_w  = 8
    for sx in range(0, fill_w, seg_w + 2):
        seg = pygame.Rect(inner.x + sx, inner.y, min(seg_w, fill_w - sx), inner.height)
        pygame.draw.rect(surface, W["highlight"], seg)
    if label and font:
        txt = font.render(label, True, W["text"])
        surface.blit(txt, (rect.centerx - txt.get_width() // 2,
                           rect.centery - txt.get_height() // 2))
