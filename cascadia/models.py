"""
models.py - Core data models for Cascadia.

Classes:
    HexTile     – one landscape hex tile (habitat(s) + accepted wildlife)
    WildlifeToken – a single wildlife token placed on a tile
    Player      – player state (board, tokens, score, nature tokens)
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Set
from cascadia.constants import HABITATS, WILDLIFE


# ── Hex coordinate helpers ────────────────────────────────────────────────────

def hex_neighbors(q: int, r: int) -> List[Tuple[int, int]]:
    """Return the 6 axial-coordinate neighbors of hex (q, r)."""
    directions = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]
    return [(q + dq, r + dr) for dq, dr in directions]


# ── HexTile ───────────────────────────────────────────────────────────────────

@dataclass
class HexTile:
    """
    One hexagonal landscape tile.

    Attributes:
        tile_id       Unique identifier string
        habitats      1 or 2 habitat types this tile contains
        accepts       Set of wildlife types that may be placed here
        keystone      If True, only one wildlife type is accepted (keystone tile)
        token         Wildlife token currently placed (or None)
        q, r          Axial grid coordinates in the player's board
        is_starter    True if this tile is part of the starting wedge
    """
    tile_id:    str
    habitats:   List[str]
    accepts:    Set[str]
    keystone:   bool = False
    token:      Optional["WildlifeToken"] = None
    q:          int = 0
    r:          int = 0
    is_starter: bool = False

    def can_accept(self, wildlife_type: str) -> bool:
        """Return True if this tile has no token and accepts the given wildlife."""
        return self.token is None and wildlife_type in self.accepts

    def place_token(self, token: "WildlifeToken") -> bool:
        """Attempt to place a token. Returns True on success."""
        if not self.can_accept(token.wildlife_type):
            return False
        self.token = token
        return True

    def remove_token(self) -> Optional["WildlifeToken"]:
        """Remove and return the placed token, or None if empty."""
        t = self.token
        self.token = None
        return t

    def primary_habitat(self) -> str:
        return self.habitats[0]

    def __hash__(self):
        return hash(self.tile_id)

    def __eq__(self, other):
        return isinstance(other, HexTile) and self.tile_id == other.tile_id


# ── WildlifeToken ─────────────────────────────────────────────────────────────

@dataclass
class WildlifeToken:
    """
    One wildlife token (bear, elk, salmon, hawk, or fox).

    Attributes:
        token_id      Unique identifier
        wildlife_type One of the 5 wildlife species
    """
    token_id:     str
    wildlife_type: str

    def __hash__(self):
        return hash(self.token_id)

    def __eq__(self, other):
        return isinstance(other, WildlifeToken) and self.token_id == other.token_id


# ── Player ────────────────────────────────────────────────────────────────────

class Player:
    """
    Holds all state for one player.

    Attributes:
        player_id       Integer id (0-based)
        name            Display name
        board           Dict mapping (q, r) -> HexTile
        nature_tokens   Spending currency for special actions
        score           Cached final score
        color           Display colour tuple
    """

    def __init__(self, player_id: int, name: str, color: Tuple[int, int, int]):
        self.player_id    = player_id
        self.name         = name
        self.color        = color
        self.board: Dict[Tuple[int, int], HexTile] = {}
        self.nature_tokens: int = 1
        self.score: int = 0

    # ── board helpers ──────────────────────────────────────────────────────────

    def add_tile(self, tile: HexTile, q: int, r: int) -> bool:
        """
        Place a tile at (q, r) if the cell is empty and adjacent to an
        existing tile (or the board is empty).
        """
        if (q, r) in self.board:
            return False
        if self.board and not self._is_adjacent(q, r):
            return False
        tile.q = q
        tile.r = r
        self.board[(q, r)] = tile
        return True

    def _is_adjacent(self, q: int, r: int) -> bool:
        for nq, nr in hex_neighbors(q, r):
            if (nq, nr) in self.board:
                return True
        return False

    def valid_placements(self) -> List[Tuple[int, int]]:
        """Return all grid cells where a new tile can legally be placed."""
        if not self.board:
            return [(0, 0)]
        candidates: Set[Tuple[int, int]] = set()
        for (q, r) in self.board:
            for nq, nr in hex_neighbors(q, r):
                if (nq, nr) not in self.board:
                    candidates.add((nq, nr))
        return list(candidates)

    def get_tile_at(self, q: int, r: int) -> Optional[HexTile]:
        return self.board.get((q, r))

    def tiles_accepting(self, wildlife_type: str) -> List[HexTile]:
        """Return all tiles on board that can still accept the given wildlife."""
        return [t for t in self.board.values() if t.can_accept(wildlife_type)]

    def placed_tokens(self) -> List[WildlifeToken]:
        return [t.token for t in self.board.values() if t.token is not None]

    def wildlife_counts(self) -> Dict[str, int]:
        counts = {w: 0 for w in WILDLIFE}
        for tok in self.placed_tokens():
            counts[tok.wildlife_type] += 1
        return counts

    def habitat_counts(self) -> Dict[str, int]:
        counts = {h: 0 for h in HABITATS}
        for tile in self.board.values():
            for h in tile.habitats:
                counts[h] += 1
        return counts

    # ── nature token actions ───────────────────────────────────────────────────

    def spend_nature_token(self) -> bool:
        if self.nature_tokens > 0:
            self.nature_tokens -= 1
            return True
        return False

    def gain_nature_token(self):
        self.nature_tokens += 1

    def __repr__(self):
        return f"Player({self.player_id}, {self.name!r}, board={len(self.board)} tiles)"
