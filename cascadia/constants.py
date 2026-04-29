"""
constants.py - Game-wide constants and configuration values.
"""

# ── Window ────────────────────────────────────────────────────────────────────
WINDOW_WIDTH  = 1280
WINDOW_HEIGHT = 800
WINDOW_TITLE  = "Cascadia"
FPS           = 60

# ── Tile geometry ─────────────────────────────────────────────────────────────
HEX_SIZE      = 44
HEX_SPACING   = 2

# ── Habitat types ─────────────────────────────────────────────────────────────
HABITATS = ["forest", "wetland", "mountain", "prairie", "river"]

# ── Wildlife types ────────────────────────────────────────────────────────────
WILDLIFE = ["bear", "elk", "salmon", "hawk", "fox"]

# ── Win98 / classic Windows colour palette ────────────────────────────────────
COLORS = {
    # Window chrome
    "bg_dark":         (58,  110, 165),   # Win98 desktop teal-blue
    "bg_panel":        (212, 208, 200),   # window face gray
    "bg_card":         (212, 208, 200),
    "titlebar_active": (0,   0,   128),
    "titlebar_text":   (255, 255, 255),
    "white":           (255, 255, 255),
    "black":           (0,   0,   0),

    # 3-D bevel
    "bevel_light":     (255, 255, 255),
    "bevel_mid":       (212, 208, 200),
    "bevel_shadow":    (128, 128, 128),
    "bevel_dark":      (64,  64,  64),

    # Habitats
    "forest":          (80,  130,  60),
    "wetland":         (60,  130, 100),
    "mountain":        (110, 110, 130),
    "prairie":         (170, 155,  55),
    "river":           (60,  120, 180),

    # Wildlife
    "bear":            (139,  90,  43),
    "elk":             (160, 130,  50),
    "salmon":          (210,  85,  65),
    "hawk":            (170, 140,  40),
    "fox":             (200,  85,  20),

    # UI states
    "gold":            (180, 140,  20),
    "highlight":       (0,   0,   128),
    "hover":           (49,  106, 197),
    "disabled":        (128, 128, 128),
    "danger":          (160,  20,  20),
    "selected":        (0,    0,  128),
    "text_dark":       (0,    0,   0),
    "text_light":      (0,    0,   0),
    "text_muted":      (80,   80,  80),
    "border":          (128, 128, 128),
    "listbox_sel":     (0,   0,   128),
}

# ── Scoring cards ─────────────────────────────────────────────────────────────
SCORING_VARIANTS = {
    "bear":   ["A", "B", "C", "D"],
    "elk":    ["A", "B", "C", "D"],
    "salmon": ["A", "B", "C", "D"],
    "hawk":   ["A", "B", "C", "D"],
    "fox":    ["A", "B", "C", "D"],
}

# ── Game parameters ───────────────────────────────────────────────────────────
NUM_PLAYERS_MIN     = 2
NUM_PLAYERS_MAX     = 4
STARTER_TILES       = 3
MARKET_SIZE         = 4
TURNS_PER_GAME      = 20
OVERPOPULATION_MAX  = 3
PINE_CONE_COUNT     = 1

# ── Paths ─────────────────────────────────────────────────────────────────────
import os
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR   = os.path.join(BASE_DIR, "data")
SAVES_DIR  = os.path.join(BASE_DIR, "saves")
DB_PATH    = os.path.join(DATA_DIR, "cascadia.db")
