"""
models.py - Core data models for Cascadia.
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Set
from cascadia.constants import HABITATS, WILDLIFE


def hex_neighbors(q: int, r: int) -> List[Tuple[int, int]]:
    directions = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]
    return [(q + dq, r + dr) for dq, dr in directions]


@dataclass
class HexTile:
    """
    One hexagonal landscape tile.

    rotation  – 0-5, rotates the dual-habitat split display.
                Pure cosmetic for single-habitat tiles; for dual-habitat tiles
                it controls which half faces which direction visually.
                Does NOT affect gameplay (accepts/habitats don't change).
    """
    tile_id:    str
    habitats:   List[str]
    accepts:    Set[str]
    keystone:   bool = False
    token:      Optional["WildlifeToken"] = None
    q:          int = 0
    r:          int = 0
    is_starter: bool = False
    rotation:   int = 0        # 0-5 in steps of 60°

    def rotate_cw(self):
        """Rotate tile 60° clockwise."""
        self.rotation = (self.rotation + 1) % 6

    def rotate_ccw(self):
        """Rotate tile 60° counter-clockwise."""
        self.rotation = (self.rotation - 1) % 6

    def can_accept(self, wildlife_type: str) -> bool:
        return self.token is None and wildlife_type in self.accepts

    def place_token(self, token: "WildlifeToken") -> bool:
        if not self.can_accept(token.wildlife_type):
            return False
        self.token = token
        return True

    def remove_token(self) -> Optional["WildlifeToken"]:
        t = self.token
        self.token = None
        return t

    def primary_habitat(self) -> str:
        return self.habitats[0]

    def __hash__(self):
        return hash(self.tile_id)

    def __eq__(self, other):
        return isinstance(other, HexTile) and self.tile_id == other.tile_id


@dataclass
class WildlifeToken:
    token_id:     str
    wildlife_type: str

    def __hash__(self):
        return hash(self.token_id)

    def __eq__(self, other):
        return isinstance(other, WildlifeToken) and self.token_id == other.token_id


class Player:
    def __init__(self, player_id: int, name: str, color: Tuple[int, int, int]):
        self.player_id    = player_id
        self.name         = name
        self.color        = color
        self.board: Dict[Tuple[int, int], HexTile] = {}
        self.nature_tokens: int = 1
        self.score: int = 0

    def add_tile(self, tile: HexTile, q: int, r: int) -> bool:
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

    def spend_nature_token(self) -> bool:
        if self.nature_tokens > 0:
            self.nature_tokens -= 1
            return True
        return False

    def gain_nature_token(self):
        self.nature_tokens += 1

    def __repr__(self):
        return f"Player({self.player_id}, {self.name!r}, board={len(self.board)} tiles)"
