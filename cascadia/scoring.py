"""
scoring.py - Scoring engine for Cascadia.

Implements wildlife scoring cards (A and B variants for each animal)
and habitat corridor scoring.

Public API:
    score_player(player, scoring_cards) -> ScoreBreakdown
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from cascadia.models import Player, HexTile, hex_neighbors
from cascadia.constants import WILDLIFE, HABITATS


# ── Score breakdown ────────────────────────────────────────────────────────────

@dataclass
class ScoreBreakdown:
    wildlife_scores: Dict[str, int] = field(default_factory=dict)
    habitat_score:   int = 0
    nature_token_score: int = 0
    total: int = 0

    def compute_total(self):
        self.total = (
            sum(self.wildlife_scores.values())
            + self.habitat_score
            + self.nature_token_score
        )
        return self.total


# ── Connectivity helpers ───────────────────────────────────────────────────────

def _connected_groups(player: Player, wildlife_type: str) -> List[List[HexTile]]:
    """Return list of connected groups of tiles bearing the given wildlife."""
    token_tiles = {
        (q, r): tile
        for (q, r), tile in player.board.items()
        if tile.token and tile.token.wildlife_type == wildlife_type
    }
    visited = set()
    groups  = []

    for pos in token_tiles:
        if pos in visited:
            continue
        group  = []
        stack  = [pos]
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            group.append(token_tiles[cur])
            for npos in hex_neighbors(*cur):
                if npos in token_tiles and npos not in visited:
                    stack.append(npos)
        groups.append(group)
    return groups


def _largest_group_size(player: Player, wildlife_type: str) -> int:
    groups = _connected_groups(player, wildlife_type)
    return max((len(g) for g in groups), default=0)


def _group_sizes(player: Player, wildlife_type: str) -> List[int]:
    return sorted([len(g) for g in _connected_groups(player, wildlife_type)], reverse=True)


# ── Wildlife scoring cards ────────────────────────────────────────────────────
# Each function takes a Player and returns an integer score.

# ─ Bear ───────────────────────────────────────────────────────────────────────

def score_bear_A(player: Player) -> int:
    """Score based on groups of exactly 1, 2, or 3 bears."""
    sizes = _group_sizes(player, "bear")
    points = {1: 2, 2: 5, 3: 8}
    return sum(points.get(s, 10) for s in sizes)


def score_bear_B(player: Player) -> int:
    """Score for isolated bears (no adjacent bears); bigger groups score less."""
    sizes = _group_sizes(player, "bear")
    table = {1: 4, 2: 3, 3: 2}
    return sum(table.get(s, 0) * s for s in sizes)


# ─ Elk ────────────────────────────────────────────────────────────────────────

def score_elk_A(player: Player) -> int:
    """Largest single line (run) of elk."""
    # Find longest run in any direction for each group
    all_tiles = {
        (q, r): tile
        for (q, r), tile in player.board.items()
        if tile.token and tile.token.wildlife_type == "elk"
    }
    if not all_tiles:
        return 0

    points_table = {1: 2, 2: 5, 3: 9, 4: 13, 5: 18}

    def longest_run_from(start, direction):
        length = 0
        pos = start
        while pos in all_tiles:
            length += 1
            pos = (pos[0] + direction[0], pos[1] + direction[1])
        return length

    directions = [(1, 0), (0, 1), (1, -1)]
    max_run = 0
    visited_in_runs: set = set()

    runs = []
    for pos in all_tiles:
        for d in directions:
            # only start a run from the 'first' cell in that direction
            prev = (pos[0] - d[0], pos[1] - d[1])
            if prev not in all_tiles:
                length = longest_run_from(pos, d)
                runs.append(length)

    # Score each run
    return sum(points_table.get(min(r, 5), 18) for r in runs if r > 0)


def score_elk_B(player: Player) -> int:
    """Pairs of adjacent elk score 3 pts each."""
    counted_pairs = 0
    all_pos = {
        (q, r)
        for (q, r), tile in player.board.items()
        if tile.token and tile.token.wildlife_type == "elk"
    }
    counted: set = set()
    for pos in all_pos:
        for npos in hex_neighbors(*pos):
            if npos in all_pos and frozenset([pos, npos]) not in counted:
                counted.add(frozenset([pos, npos]))
                counted_pairs += 1
    return counted_pairs * 3


# ─ Salmon ─────────────────────────────────────────────────────────────────────

def score_salmon_A(player: Player) -> int:
    """Score the longest contiguous run of salmon."""
    all_pos = {
        (q, r)
        for (q, r), tile in player.board.items()
        if tile.token and tile.token.wildlife_type == "salmon"
    }
    if not all_pos:
        return 0

    # BFS to find connected groups, score longest
    visited = set()
    sizes = []
    for start in all_pos:
        if start in visited:
            continue
        group, stack = [], [start]
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            group.append(cur)
            for n in hex_neighbors(*cur):
                if n in all_pos and n not in visited:
                    stack.append(n)
        sizes.append(len(group))

    table = {1: 2, 2: 4, 3: 7, 4: 11, 5: 15, 6: 20}
    return sum(table.get(min(s, 6), 20) for s in sizes)


def score_salmon_B(player: Player) -> int:
    """Score for salmon not adjacent to same species."""
    isolated = 0
    all_pos = {
        (q, r)
        for (q, r), tile in player.board.items()
        if tile.token and tile.token.wildlife_type == "salmon"
    }
    for pos in all_pos:
        if not any(n in all_pos for n in hex_neighbors(*pos)):
            isolated += 1
    return isolated * 3


# ─ Hawk ───────────────────────────────────────────────────────────────────────

def score_hawk_A(player: Player) -> int:
    """Each hawk that is not adjacent to any other hawk scores 5 pts."""
    all_pos = {
        (q, r)
        for (q, r), tile in player.board.items()
        if tile.token and tile.token.wildlife_type == "hawk"
    }
    score = 0
    for pos in all_pos:
        if not any(n in all_pos for n in hex_neighbors(*pos)):
            score += 5
    return score


def score_hawk_B(player: Player) -> int:
    """Hawks in a 'vision line' (unobstructed straight line)."""
    # Simpler: score 3 per hawk with at least one adjacent hawk in any line
    all_pos = {
        (q, r)
        for (q, r), tile in player.board.items()
        if tile.token and tile.token.wildlife_type == "hawk"
    }
    score = 0
    for pos in all_pos:
        score += 2  # base
        # bonus for each adjacency
        adj = sum(1 for n in hex_neighbors(*pos) if n in all_pos)
        score += adj
    return score


# ─ Fox ────────────────────────────────────────────────────────────────────────

def score_fox_A(player: Player) -> int:
    """Each fox scores 1 pt per unique wildlife type adjacent to it."""
    score = 0
    for (q, r), tile in player.board.items():
        if not (tile.token and tile.token.wildlife_type == "fox"):
            continue
        adjacent_types = set()
        for nq, nr in hex_neighbors(q, r):
            ntile = player.board.get((nq, nr))
            if ntile and ntile.token and ntile.token.wildlife_type != "fox":
                adjacent_types.add(ntile.token.wildlife_type)
        score += len(adjacent_types)
    return score


def score_fox_B(player: Player) -> int:
    """Each fox scores 1 pt per adjacent wildlife token of ANY type."""
    score = 0
    for (q, r), tile in player.board.items():
        if not (tile.token and tile.token.wildlife_type == "fox"):
            continue
        adj = sum(
            1 for nq, nr in hex_neighbors(q, r)
            if player.board.get((nq, nr)) and player.board[(nq, nr)].token
        )
        score += adj
    return score


# ── Habitat corridor scoring ──────────────────────────────────────────────────

def score_habitat_corridors(player: Player) -> int:
    """
    Score the largest contiguous corridor for each habitat type.
    Points per corridor size: 1=0, 2=1, 3=2, 4=4, 5=6, 6=9, 7+= +2 each
    """
    corridor_table = {1: 0, 2: 1, 3: 2, 4: 4, 5: 6}
    total = 0

    for habitat in HABITATS:
        habitat_pos = {
            (q, r)
            for (q, r), tile in player.board.items()
            if habitat in tile.habitats
        }
        if not habitat_pos:
            continue

        # find connected groups
        visited = set()
        sizes = []
        for start in habitat_pos:
            if start in visited:
                continue
            group, stack = [], [start]
            while stack:
                cur = stack.pop()
                if cur in visited:
                    continue
                visited.add(cur)
                group.append(cur)
                for n in hex_neighbors(*cur):
                    if n in habitat_pos and n not in visited:
                        stack.append(n)
            sizes.append(len(group))

        largest = max(sizes)
        pts = corridor_table.get(largest, 6 + (largest - 5) * 2)
        total += pts

    return total


# ── Scoring card registry ─────────────────────────────────────────────────────

SCORING_CARDS = {
    "bear_A":   score_bear_A,
    "bear_B":   score_bear_B,
    "elk_A":    score_elk_A,
    "elk_B":    score_elk_B,
    "salmon_A": score_salmon_A,
    "salmon_B": score_salmon_B,
    "hawk_A":   score_hawk_A,
    "hawk_B":   score_hawk_B,
    "fox_A":    score_fox_A,
    "fox_B":    score_fox_B,
}


# ── Main scoring function ─────────────────────────────────────────────────────

def score_player(player: Player, scoring_cards: Dict[str, str]) -> ScoreBreakdown:
    """
    Score a player using the selected scoring card for each wildlife.

    Args:
        player:        The Player instance to score.
        scoring_cards: Dict mapping wildlife_type -> variant ("A" or "B").

    Returns:
        ScoreBreakdown with per-species, habitat, and nature token scores.
    """
    breakdown = ScoreBreakdown()

    for wildlife in WILDLIFE:
        variant  = scoring_cards.get(wildlife, "A")
        card_key = f"{wildlife}_{variant}"
        fn       = SCORING_CARDS.get(card_key)
        if fn:
            breakdown.wildlife_scores[wildlife] = fn(player)
        else:
            breakdown.wildlife_scores[wildlife] = 0

    breakdown.habitat_score      = score_habitat_corridors(player)
    breakdown.nature_token_score = player.nature_tokens  # leftover tokens = 1 pt each
    breakdown.compute_total()

    return breakdown
