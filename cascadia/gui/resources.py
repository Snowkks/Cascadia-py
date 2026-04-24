"""
resources.py - Font loading with anti-aliased TTF fonts.

Priority order for font search:
  1. TTF files found on the local filesystem (crisp, anti-aliased)
  2. pygame.font.SysFont by name (usually also TTF on modern systems)
  3. pygame built-in fallback (pixelated — last resort only)

On NixOS the TTF search covers /run/current-system and ~/.nix-profile.
"""

import os
import pygame

_fonts: dict = {}

# ── TTF search paths ──────────────────────────────────────────────────────────
_TTF_SEARCH = [
    # NixOS
    "/run/current-system/sw/share/fonts",
    os.path.expanduser("~/.nix-profile/share/fonts"),
    # Debian/Ubuntu/Arch
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/liberation",
    "/usr/share/fonts/truetype/freefont",
    "/usr/share/fonts/TTF",
    "/usr/share/fonts/truetype",
    # macOS
    "/Library/Fonts",
    "/System/Library/Fonts",
    os.path.expanduser("~/Library/Fonts"),
    # Windows
    r"C:\Windows\Fonts",
]

# Preferred filenames in priority order (regular weight, no italic)
_SANS_FILES = [
    "DejaVuSans.ttf",
    "LiberationSans-Regular.ttf",
    "FreeSans.ttf",
    "Vera.ttf",
    "NotoSans-Regular.ttf",
    "Ubuntu-R.ttf",
    "Roboto-Regular.ttf",
    "Arial.ttf",
    "arial.ttf",
]
_SANS_BOLD_FILES = [
    "DejaVuSans-Bold.ttf",
    "LiberationSans-Bold.ttf",
    "FreeSansBold.ttf",
    "VeraBd.ttf",
    "NotoSans-Bold.ttf",
    "Ubuntu-B.ttf",
    "Roboto-Bold.ttf",
    "ArialBD.ttf",
]
_TITLE_FILES = [
    "DejaVuSans-Bold.ttf",
    "LiberationSans-Bold.ttf",
    "FreeSansBold.ttf",
    "VeraBd.ttf",
]

_path_cache: dict = {}


def _find_ttf(filenames: list) -> str | None:
    """Return the first matching TTF path found on disk."""
    key = tuple(filenames)
    if key in _path_cache:
        return _path_cache[key]

    for directory in _TTF_SEARCH:
        if not os.path.isdir(directory):
            continue
        for root, _, files in os.walk(directory):
            for fname in filenames:
                if fname in files:
                    result = os.path.join(root, fname)
                    _path_cache[key] = result
                    return result

    _path_cache[key] = None
    return None


def _make_font(size: int, bold: bool = False) -> pygame.font.Font:
    """
    Build a pygame.font.Font object that renders with anti-aliasing.
    Falls back gracefully so the game always starts.
    """
    files = _SANS_BOLD_FILES if bold else _SANS_FILES
    path  = _find_ttf(files)

    if path:
        try:
            return pygame.font.Font(path, size)
        except Exception:
            pass

    # SysFont fallback (often still TTF on modern distros)
    sys_names = (["dejavusans", "liberationsans", "freesans", "vera",
                  "tahoma", "arial", "sans"]
                 if not bold else
                 ["dejavusansbold", "liberationsansbold", "freesansbold",
                  "tahoma", "arial", "sans"])
    for name in sys_names:
        try:
            f = pygame.font.SysFont(name, size, bold=bold)
            # SysFont returns a font even if the name isn't found;
            # check it isn't just the bitmap default by testing a glyph
            if f.size("A")[0] > 0:
                return f
        except Exception:
            continue

    # Absolute last resort — pygame built-in (will look pixelated at small sizes)
    return pygame.font.Font(None, size + 4)


# ── Public API ────────────────────────────────────────────────────────────────

def get_font(size: int, bold: bool = False, italic: bool = False) -> pygame.font.Font:
    key = (size, bold, italic)
    if key not in _fonts:
        _fonts[key] = _make_font(size, bold=bold)
    return _fonts[key]


def get_title_font(size: int) -> pygame.font.Font:
    key = ("title", size)
    if key not in _fonts:
        path = _find_ttf(_TITLE_FILES)
        if path:
            try:
                _fonts[key] = pygame.font.Font(path, size)
            except Exception:
                _fonts[key] = _make_font(size, bold=True)
        else:
            _fonts[key] = _make_font(size, bold=True)
    return _fonts[key]


# ── Label maps ────────────────────────────────────────────────────────────────

WILDLIFE_LABELS = {
    "bear": "Bear", "elk": "Elk", "salmon": "Salmon",
    "hawk": "Hawk", "fox": "Fox",
}
WILDLIFE_ASCII = {
    "bear": "BR", "elk": "EL", "salmon": "SA", "hawk": "HK", "fox": "FX",
}
HABITAT_LABELS = {
    "forest": "FOR", "wetland": "WET", "mountain": "MTN",
    "prairie": "PRA", "river":   "RIV",
}
