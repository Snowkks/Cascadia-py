"""
tile_factory.py - Generates the tile and token decks.

Tile counts per player count (per rulebook):
  2 players: 43 tiles
  3 players: 63 tiles
  4 players: 83 tiles
  (+20 for each additional player beyond 2)

Starter tile: each player gets exactly 1 starter tile (rulebook p.4)
"""
from __future__ import annotations
import random
import itertools
from typing import List
from cascadia.models import HexTile, WildlifeToken
from cascadia.constants import HABITATS, WILDLIFE

# Tile counts by number of players
TILE_COUNTS = {2: 43, 3: 63, 4: 83}


def _build_tile_blueprints():
    blueprints = []

    # Single-habitat tiles (3 accepted wildlife each)
    single_accept_sets = [
        {"bear", "elk", "salmon"}, {"bear", "elk", "hawk"}, {"bear", "elk", "fox"},
        {"bear", "salmon", "hawk"}, {"bear", "salmon", "fox"}, {"bear", "hawk", "fox"},
        {"elk", "salmon", "hawk"}, {"elk", "salmon", "fox"}, {"elk", "hawk", "fox"},
        {"salmon", "hawk", "fox"},
    ]
    for habitat in HABITATS:
        for acc in single_accept_sets:
            blueprints.append(([habitat], acc, False))

    # Dual-habitat tiles (2 accepted wildlife each)
    dual_combos = list(itertools.combinations(HABITATS, 2))
    dual_accept_pairs = [
        {"bear", "elk"}, {"bear", "salmon"}, {"bear", "hawk"}, {"bear", "fox"},
        {"elk", "salmon"}, {"elk", "hawk"}, {"elk", "fox"},
        {"salmon", "hawk"}, {"salmon", "fox"}, {"hawk", "fox"},
    ]
    for (h1, h2), acc in zip(dual_combos * 4, dual_accept_pairs * 4):
        blueprints.append(([h1, h2], acc, False))

    # Keystone tiles (1 accepted wildlife = keystone)
    for wildlife in WILDLIFE:
        for habitat in HABITATS:
            blueprints.append(([habitat], {wildlife}, True))

    return blueprints


def build_tile_deck(rng: random.Random = None, num_players: int = 2) -> List[HexTile]:
    """Build and shuffle the tile deck, trimmed to the correct count for player count."""
    if rng is None:
        rng = random.Random()

    blueprints = _build_tile_blueprints()
    rng.shuffle(blueprints)

    count = TILE_COUNTS.get(num_players, 83)

    tiles = []
    for i, (habitats, accepts, keystone) in enumerate(blueprints[:count]):
        tile = HexTile(
            tile_id  = f"T{i:03d}",
            habitats = list(habitats),
            accepts  = set(accepts),
            keystone = keystone,
        )
        tiles.append(tile)
    return tiles


def build_token_deck(rng: random.Random = None) -> List[WildlifeToken]:
    """100 tokens total, 20 of each wildlife, shuffled."""
    if rng is None:
        rng = random.Random()
    tokens = []
    for wildlife in WILDLIFE:
        for j in range(20):
            tokens.append(WildlifeToken(
                token_id      = f"{wildlife[0].upper()}{j:02d}",
                wildlife_type = wildlife,
            ))
    rng.shuffle(tokens)
    return tokens


def build_starter_tile(rng: random.Random = None) -> HexTile:
    """
    Each player gets exactly ONE starter tile (rulebook p.4).
    It is placed at (0,0) on their board to begin.
    """
    if rng is None:
        rng = random.Random()

    options = [
        (["forest"],   {"bear", "hawk", "fox"}),
        (["wetland"],  {"salmon", "bear", "elk"}),
        (["mountain"], {"elk", "hawk", "fox"}),
        (["prairie"],  {"elk", "salmon", "bear"}),
        (["river"],    {"salmon", "fox", "hawk"}),
    ]
    habitats, accepts = rng.choice(options)
    return HexTile(
        tile_id    = f"S_{rng.randint(0,9999)}",
        habitats   = list(habitats),
        accepts    = set(accepts),
        keystone   = False,
        q          = 0,
        r          = 0,
        is_starter = True,
    )
