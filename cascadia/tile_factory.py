"""
tile_factory.py - Generates and shuffles the full tile and token decks.

The physical Cascadia game ships with:
  • 85 habitat tiles  (various habitat/wildlife combinations)
  • 100 wildlife tokens (20 of each of the 5 species)

This module recreates those decks procedurally so no image assets are
required for the tile data itself.
"""

from __future__ import annotations
import random
import itertools
from typing import List, Tuple
from cascadia.models import HexTile, WildlifeToken
from cascadia.constants import HABITATS, WILDLIFE


# ── Tile blueprints ───────────────────────────────────────────────────────────
# Each entry: (habitats_list, accepts_set, keystone)
# We define ~85 tiles mirroring the real game's distribution.

def _build_tile_blueprints() -> List[Tuple[List[str], set, bool]]:
    blueprints = []

    # Single-habitat tiles (3 accepted wildlife each)
    single_accept_sets = [
        {"bear", "elk", "salmon"},
        {"bear", "elk", "hawk"},
        {"bear", "elk", "fox"},
        {"bear", "salmon", "hawk"},
        {"bear", "salmon", "fox"},
        {"bear", "hawk", "fox"},
        {"elk", "salmon", "hawk"},
        {"elk", "salmon", "fox"},
        {"elk", "hawk", "fox"},
        {"salmon", "hawk", "fox"},
    ]

    for habitat in HABITATS:
        for acc in single_accept_sets:
            blueprints.append(([habitat], acc, False))

    # Dual-habitat tiles (2 accepted wildlife each)
    dual_combos = list(itertools.combinations(HABITATS, 2))
    dual_accept_pairs = [
        {"bear", "elk"},
        {"bear", "salmon"},
        {"bear", "hawk"},
        {"bear", "fox"},
        {"elk", "salmon"},
        {"elk", "hawk"},
        {"elk", "fox"},
        {"salmon", "hawk"},
        {"salmon", "fox"},
        {"hawk", "fox"},
    ]
    for (h1, h2), acc in zip(dual_combos * 4, dual_accept_pairs * 4):
        blueprints.append(([h1, h2], acc, False))

    # Keystone tiles (only 1 accepted wildlife)
    for wildlife in WILDLIFE:
        for habitat in HABITATS:
            blueprints.append(([habitat], {wildlife}, True))

    return blueprints


# ── Public factory functions ──────────────────────────────────────────────────

def build_tile_deck(rng: random.Random = None) -> List[HexTile]:
    """Build, shuffle and return the full tile deck (~85 tiles)."""
    if rng is None:
        rng = random.Random()

    blueprints = _build_tile_blueprints()
    rng.shuffle(blueprints)

    tiles = []
    for i, (habitats, accepts, keystone) in enumerate(blueprints):
        tile = HexTile(
            tile_id  = f"T{i:03d}",
            habitats = list(habitats),
            accepts  = set(accepts),
            keystone = keystone,
        )
        tiles.append(tile)
    return tiles


def build_token_deck(rng: random.Random = None) -> List[WildlifeToken]:
    """Build, shuffle and return the full token deck (20 of each wildlife)."""
    if rng is None:
        rng = random.Random()

    tokens = []
    for wildlife in WILDLIFE:
        for j in range(20):
            tokens.append(WildlifeToken(
                token_id     = f"{wildlife[0].upper()}{j:02d}",
                wildlife_type = wildlife,
            ))
    rng.shuffle(tokens)
    return tokens


def build_starter_wedge(rng: random.Random = None) -> List[HexTile]:
    """
    Build a 3-tile starter wedge for one player.
    The starter tiles always form a pre-connected group; in the digital
    version we simply give each player 3 single-habitat tiles placed at
    fixed offsets and mark them as starters.
    """
    if rng is None:
        rng = random.Random()

    wedge_blueprints = [
        (["forest"],   {"bear", "hawk", "fox"},    False),
        (["wetland"],  {"salmon", "bear", "elk"},  False),
        (["mountain"], {"elk", "hawk", "fox"},     False),
    ]
    rng.shuffle(wedge_blueprints)

    tiles = []
    positions = [(0, 0), (1, -1), (1, 0)]
    for idx, ((habitats, accepts, keystone), pos) in enumerate(
        zip(wedge_blueprints, positions)
    ):
        tile = HexTile(
            tile_id    = f"S{idx}",
            habitats   = list(habitats),
            accepts    = set(accepts),
            keystone   = keystone,
            q          = pos[0],
            r          = pos[1],
            is_starter = True,
        )
        tiles.append(tile)
    return tiles
