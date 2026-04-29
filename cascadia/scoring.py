"""
scoring.py - Official Cascadia scoring engine (all A/B/C/D cards).

Rules source: Cascadia rulebook (official).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Set
from cascadia.models import Player, HexTile, hex_neighbors
from cascadia.constants import WILDLIFE, HABITATS


@dataclass
class ScoreBreakdown:
    wildlife_scores:    Dict[str, int] = field(default_factory=dict)
    habitat_score:      int = 0
    habitat_majority:   int = 0
    nature_token_score: int = 0
    total:              int = 0

    def compute_total(self):
        self.total = (
            sum(self.wildlife_scores.values())
            + self.habitat_score
            + self.habitat_majority
            + self.nature_token_score
        )
        return self.total


# ── Connectivity helpers ───────────────────────────────────────────────────────

def _token_positions(player: Player, wildlife_type: str) -> Set[Tuple[int,int]]:
    return {(q,r) for (q,r), tile in player.board.items()
            if tile.token and tile.token.wildlife_type == wildlife_type}


def _connected_groups(player: Player, wildlife_type: str) -> List[List[Tuple[int,int]]]:
    """Return list of connected groups as lists of (q,r) positions."""
    positions = _token_positions(player, wildlife_type)
    visited, groups = set(), []
    for pos in positions:
        if pos in visited:
            continue
        group, stack = [], [pos]
        while stack:
            cur = stack.pop()
            if cur in visited: continue
            visited.add(cur)
            group.append(cur)
            for n in hex_neighbors(*cur):
                if n in positions and n not in visited:
                    stack.append(n)
        groups.append(group)
    return groups


def _group_sizes(player: Player, wildlife_type: str) -> List[int]:
    return sorted([len(g) for g in _connected_groups(player, wildlife_type)], reverse=True)


# ── BEAR scoring ───────────────────────────────────────────────────────────────
# Rule: groups of bears may NOT be adjacent to each other.
# Each group must be exactly the sizes shown to score.

def _bear_groups_valid(player: Player) -> List[int]:
    """
    Return valid bear group sizes.
    Two groups may not be adjacent — if they are, they're actually one group.
    (Adjacency constraint enforced by the connectivity: any touching bears
    are already one group by definition of _connected_groups.)
    """
    return _group_sizes(player, "bear")


def score_bear_A(player: Player) -> int:
    """Score an increasing number of points based on total number of PAIRS of bears.
    Bear pairs table: 1=2, 2=5, 3=9, 4=13 (each additional pair +4)."""
    sizes = _bear_groups_valid(player)
    pairs = sum(s // 2 for s in sizes)
    table = {0:0, 1:2, 2:5, 3:9, 4:13, 5:17, 6:21}
    return table.get(min(pairs, 6), 21 + (pairs-6)*4)


def score_bear_B(player: Player) -> int:
    """Score 10 points for each group of exactly 3 bears."""
    return sum(10 for s in _bear_groups_valid(player) if s == 3)


def score_bear_C(player: Player) -> int:
    """Score for groups 1-3, plus 3pt bonus for having one of each size."""
    sizes = _bear_groups_valid(player)
    table = {1: 2, 2: 4, 3: 7}
    score = sum(table.get(s, 0) for s in sizes)
    if any(s == 1 for s in sizes) and any(s == 2 for s in sizes) and any(s == 3 for s in sizes):
        score += 3
    return score


def score_bear_D(player: Player) -> int:
    """Score for groups of size 2, 3, and 4."""
    sizes = _bear_groups_valid(player)
    table = {2: 4, 3: 7, 4: 10}
    return sum(table.get(s, 0) for s in sizes)


# ── ELK scoring ────────────────────────────────────────────────────────────────
# Rule: elk may be adjacent to each other, each elk scores once.

def _straight_lines(player: Player) -> List[int]:
    """Find all straight-line runs of elk (flat-side to flat-side in hex grid)."""
    positions = _token_positions(player, "elk")
    directions = [(1, 0), (0, 1), (1, -1)]  # 3 axis directions
    counted: Set[frozenset] = set()
    runs = []
    for pos in positions:
        for d in directions:
            prev = (pos[0] - d[0], pos[1] - d[1])
            if prev in positions:
                continue  # not the start of this run
            run = []
            cur = pos
            while cur in positions:
                run.append(cur)
                cur = (cur[0] + d[0], cur[1] + d[1])
            if len(run) >= 1:
                runs.append(len(run))
    return runs


def score_elk_A(player: Player) -> int:
    """Score for groups in straight lines. Table: 2=5, 3=9, 4=13, 5=18."""
    table = {1: 2, 2: 5, 3: 9, 4: 13, 5: 18}
    return sum(table.get(min(r, 5), 18) for r in _straight_lines(player))


def score_elk_B(player: Player) -> int:
    """Score for groups in specific shapes (V-shape / wedge of 3, row of 3+).
    Simplified: pairs = 3pts, triples = 7pts, 4+ = 11pts."""
    sizes = _group_sizes(player, "elk")
    table = {1: 0, 2: 3, 3: 7, 4: 11}
    return sum(table.get(min(s, 4), 11) for s in sizes)


def score_elk_C(player: Player) -> int:
    """Score for each contiguous group by size: 1=1, 2=3, 3=5, 4=7, 5=10, 6+=14."""
    sizes = _group_sizes(player, "elk")
    table = {1:1, 2:3, 3:5, 4:7, 5:10, 6:14}
    return sum(table.get(min(s, 6), 14) for s in sizes)


def score_elk_D(player: Player) -> int:
    """Score for circular formations (each elk touches exactly 2 others)."""
    positions = _token_positions(player, "elk")
    score = 0
    for group in _connected_groups(player, "elk"):
        if len(group) < 3:
            continue
        # Check if every elk in group has exactly 2 elk neighbors
        is_ring = all(
            sum(1 for n in hex_neighbors(*pos) if n in set(group)) == 2
            for pos in group
        )
        if is_ring:
            ring_table = {3:7, 4:9, 5:12, 6:15}
            score += ring_table.get(len(group), 15)
    return score


# ── SALMON scoring ─────────────────────────────────────────────────────────────
# Rule: a run = adjacent salmon where each salmon touches ≤ 2 others.
# Runs may not touch other runs.

def _salmon_runs(player: Player) -> List[List[Tuple[int,int]]]:
    """
    Find valid salmon runs: connected groups where each salmon has ≤ 2 neighbors.
    Groups where any salmon has 3+ neighbors are invalid (not runs).
    """
    positions = _token_positions(player, "salmon")
    groups = _connected_groups(player, "salmon")
    valid_runs = []
    for group in groups:
        group_set = set(group)
        # Each salmon in this group must have ≤ 2 salmon neighbors
        if all(sum(1 for n in hex_neighbors(*pos) if n in group_set) <= 2
               for pos in group):
            valid_runs.append(group)
    return valid_runs


def score_salmon_A(player: Player) -> int:
    """Score each run by size, max 7. Table: 1=2, 2=4, 3=7, 4=11, 5=15, 6=20, 7=25."""
    table = {1:2, 2:4, 3:7, 4:11, 5:15, 6:20, 7:25}
    return sum(table.get(min(len(r), 7), 25) for r in _salmon_runs(player))


def score_salmon_B(player: Player) -> int:
    """Score each run by size, max 5. Table: 1=2, 2=4, 3=7, 4=11, 5=17."""
    table = {1:2, 2:4, 3:7, 4:11, 5:17}
    return sum(table.get(min(len(r), 5), 17) for r in _salmon_runs(player))


def score_salmon_C(player: Player) -> int:
    """Score runs of size 3-5 only. Table: 3=7, 4=11, 5=17."""
    table = {3:7, 4:11, 5:17}
    return sum(table.get(min(len(r), 5), 0) for r in _salmon_runs(player)
               if 3 <= len(r) <= 5)


def score_salmon_D(player: Player) -> int:
    """Each run scores 1pt per salmon in run + 1pt per adjacent non-salmon token."""
    score = 0
    positions = _token_positions(player, "salmon")
    for run in _salmon_runs(player):
        run_pts = len(run)
        adj_tokens = set()
        for pos in run:
            for n in hex_neighbors(*pos):
                if n not in positions:
                    ntile = player.board.get(n)
                    if ntile and ntile.token:
                        adj_tokens.add(n)
        run_pts += len(adj_tokens)
        score += run_pts
    return score


# ── HAWK scoring ───────────────────────────────────────────────────────────────

def _hawk_has_los(pos: Tuple[int,int], other: Tuple[int,int],
                  all_hawks: Set[Tuple[int,int]]) -> bool:
    """True if pos has an unobstructed line of sight to other (no hawk between)."""
    directions = [(1,0),(-1,0),(0,1),(0,-1),(1,-1),(-1,1)]
    for d in directions:
        cur = (pos[0]+d[0], pos[1]+d[1])
        found_other = False
        while cur != pos:
            if cur == other:
                found_other = True
                break
            if cur in all_hawks:
                break
            cur = (cur[0]+d[0], cur[1]+d[1])
        if found_other:
            return True
    return False


def score_hawk_A(player: Player) -> int:
    """Increasing points for each hawk NOT adjacent to any other hawk.
    Table: 1=2, 2=5, 3=8, 4=11, ..."""
    positions = _token_positions(player, "hawk")
    isolated = sum(1 for pos in positions
                   if not any(n in positions for n in hex_neighbors(*pos)))
    table = {0:0, 1:2, 2:5, 3:8, 4:11, 5:14}
    return table.get(min(isolated, 5), 14 + (isolated-5)*3)


def score_hawk_B(player: Player) -> int:
    """Isolated hawk AND has line of sight to another hawk."""
    positions = _token_positions(player, "hawk")
    score = 0
    isolated_with_los = []
    for pos in positions:
        if any(n in positions for n in hex_neighbors(*pos)):
            continue  # not isolated
        # Check LOS to any other hawk
        for other in positions:
            if other == pos: continue
            if _hawk_has_los(pos, other, positions):
                isolated_with_los.append(pos)
                break
    n = len(isolated_with_los)
    table = {0:0, 1:3, 2:7, 3:12, 4:17, 5:22}
    return table.get(min(n, 5), 22 + (n-5)*5)


def score_hawk_C(player: Player) -> int:
    """3 points for each line of sight between two hawks."""
    positions = _token_positions(player, "hawk")
    directions = [(1,0),(0,1),(1,-1)]
    score = 0
    counted: Set[frozenset] = set()
    for pos in positions:
        for d in directions:
            cur = (pos[0]+d[0], pos[1]+d[1])
            while True:
                if cur in positions:
                    pair = frozenset([pos, cur])
                    if pair not in counted:
                        counted.add(pair)
                        score += 3
                    break
                if cur not in {(q,r) for (q,r) in player.board}:
                    break
                cur = (cur[0]+d[0], cur[1]+d[1])
    return score


def score_hawk_D(player: Player) -> int:
    """Score pairs of hawks by unique animal types between them (not hawks).
    Table by unique types: 0=0, 1=1, 2=3, 3=5, 4=7."""
    positions = list(_token_positions(player, "hawk"))
    if len(positions) < 2:
        return 0
    # Greedy pairing: pair each hawk with best available partner
    paired: Set[int] = set()
    score = 0
    type_table = {0:0, 1:1, 2:3, 3:5, 4:7}
    # Calculate unique types between each pair
    pairs_scored = []
    for i, pos_a in enumerate(positions):
        for j, pos_b in enumerate(positions):
            if j <= i: continue
            between_types: Set[str] = set()
            # Check tiles between the two hawks in all 6 directions
            for d in [(1,0),(-1,0),(0,1),(0,-1),(1,-1),(-1,1)]:
                cur = (pos_a[0]+d[0], pos_a[1]+d[1])
                tiles_between = []
                while cur in player.board and cur != pos_b:
                    tile = player.board[cur]
                    if tile.token and tile.token.wildlife_type != "hawk":
                        between_types.add(tile.token.wildlife_type)
                    cur = (cur[0]+d[0], cur[1]+d[1])
            pairs_scored.append((i, j, type_table.get(min(len(between_types),4), 7)))
    # Sort by score descending, greedy pair
    pairs_scored.sort(key=lambda x: -x[2])
    for i, j, pts in pairs_scored:
        if i not in paired and j not in paired:
            paired.add(i); paired.add(j)
            score += pts
    return score


# ── FOX scoring ────────────────────────────────────────────────────────────────

def score_fox_A(player: Player) -> int:
    """Each fox scores increasing pts by unique adjacent species (including foxes).
    Table: 0=0, 1=1, 2=2, 3=4, 4=7."""
    table = {0:0, 1:1, 2:2, 3:4, 4:7}
    score = 0
    for (q,r), tile in player.board.items():
        if not (tile.token and tile.token.wildlife_type == "fox"):
            continue
        adj_types: Set[str] = set()
        for nq, nr in hex_neighbors(q, r):
            nt = player.board.get((nq, nr))
            if nt and nt.token:
                adj_types.add(nt.token.wildlife_type)
        score += table.get(min(len(adj_types), 4), 7)
    return score


def score_fox_B(player: Player) -> int:
    """Each fox scores by number of unique animal PAIRS adjacent (not fox pairs).
    Pairs don't need to be adjacent to each other.
    Table: 0=0, 1=1, 2=3, 3=5, 4=7."""
    table = {0:0, 1:1, 2:3, 3:5, 4:7}
    score = 0
    for (q,r), tile in player.board.items():
        if not (tile.token and tile.token.wildlife_type == "fox"):
            continue
        # Count unique non-fox species that appear at least twice adjacent
        adj_counts: Dict[str, int] = {}
        for nq, nr in hex_neighbors(q, r):
            nt = player.board.get((nq, nr))
            if nt and nt.token and nt.token.wildlife_type != "fox":
                w = nt.token.wildlife_type
                adj_counts[w] = adj_counts.get(w, 0) + 1
        pairs = sum(1 for cnt in adj_counts.values() if cnt >= 2)
        score += table.get(min(pairs, 4), 7)
    return score


def score_fox_C(player: Player) -> int:
    """Each fox scores by most abundant adjacent non-fox species.
    Table: 0=0, 1=1, 2=3, 3=5, 4=7."""
    table = {0:0, 1:1, 2:3, 3:5, 4:7}
    score = 0
    for (q,r), tile in player.board.items():
        if not (tile.token and tile.token.wildlife_type == "fox"):
            continue
        adj_counts: Dict[str, int] = {}
        for nq, nr in hex_neighbors(q, r):
            nt = player.board.get((nq, nr))
            if nt and nt.token and nt.token.wildlife_type != "fox":
                w = nt.token.wildlife_type
                adj_counts[w] = adj_counts.get(w, 0) + 1
        most = max(adj_counts.values(), default=0)
        score += table.get(min(most, 4), 7)
    return score


def score_fox_D(player: Player) -> int:
    """Score fox PAIRS by unique animal pairs adjacent to the pair (8 adjacent tiles).
    Table: 0=0, 1=2, 2=5, 3=8, 4=11."""
    table = {0:0, 1:2, 2:5, 3:8, 4:11}
    positions = list(_token_positions(player, "fox"))
    paired: Set[int] = set()
    score  = 0
    # Find adjacent fox pairs
    for i, pos_a in enumerate(positions):
        if i in paired: continue
        best_j, best_pts = -1, -1
        for j, pos_b in enumerate(positions):
            if j <= i or j in paired: continue
            if pos_b not in hex_neighbors(*pos_a): continue
            # Count unique non-fox pairs adjacent to the combined 8 tiles
            adj = set(hex_neighbors(*pos_a)) | set(hex_neighbors(*pos_b))
            adj -= {pos_a, pos_b}
            adj_counts: Dict[str,int] = {}
            for n in adj:
                nt = player.board.get(n)
                if nt and nt.token and nt.token.wildlife_type != "fox":
                    w = nt.token.wildlife_type
                    adj_counts[w] = adj_counts.get(w, 0) + 1
            pairs = sum(1 for cnt in adj_counts.values() if cnt >= 2)
            pts   = table.get(min(pairs, 4), 11)
            if pts > best_pts:
                best_pts, best_j = pts, j
        if best_j >= 0:
            paired.add(i); paired.add(best_j)
            score += best_pts
        else:
            # Unpaired fox: score as card A
            (q,r) = pos_a
            adj_types: Set[str] = set()
            for nq,nr in hex_neighbors(q,r):
                nt = player.board.get((nq,nr))
                if nt and nt.token and nt.token.wildlife_type != "fox":
                    adj_types.add(nt.token.wildlife_type)
            score += {0:0,1:1,2:2,3:4,4:7}.get(min(len(adj_types),4), 7)
    return score


# ── Habitat corridor scoring ──────────────────────────────────────────────────
# Rulebook: largest contiguous area = 1 pt per tile in that group.
# Plus majority bonuses between players.

def _largest_corridor(player: Player, habitat: str) -> int:
    """Return the size of the largest connected corridor of this habitat."""
    habitat_pos = {
        (q,r) for (q,r), tile in player.board.items()
        if habitat in tile.habitats
    }
    if not habitat_pos:
        return 0
    visited, best = set(), 0
    for start in habitat_pos:
        if start in visited: continue
        group, stack = [], [start]
        while stack:
            cur = stack.pop()
            if cur in visited: continue
            visited.add(cur); group.append(cur)
            for n in hex_neighbors(*cur):
                if n in habitat_pos and n not in visited:
                    stack.append(n)
        best = max(best, len(group))
    return best


def score_habitat_corridors(player: Player) -> int:
    """1 pt per tile in each player's largest corridor per habitat."""
    return sum(_largest_corridor(player, h) for h in HABITATS)


def score_habitat_majority(players: List[Player]) -> Dict[int, int]:
    """
    Majority bonuses per habitat:
      2 players: 2pts to largest, 1pt each if tied
      3-4 players: 3pts for largest, 1pt for second, ties split
    Returns dict: player_id -> bonus pts
    """
    bonuses: Dict[int, int] = {p.player_id: 0 for p in players}
    n = len(players)

    for habitat in HABITATS:
        sizes = [(p.player_id, _largest_corridor(p, habitat)) for p in players]
        sizes.sort(key=lambda x: -x[1])
        max_size = sizes[0][1]
        if max_size == 0:
            continue

        if n == 2:
            first_group = [pid for pid, s in sizes if s == max_size]
            if len(first_group) == 1:
                bonuses[first_group[0]] += 2
                # second place
                second = [pid for pid, s in sizes if s < max_size]
                if second:
                    bonuses[second[0]] += 1
            else:
                for pid in first_group:
                    bonuses[pid] += 1  # tied: 1pt each
        else:
            # 3-4 players
            first_group = [pid for pid, s in sizes if s == max_size]
            if len(first_group) == 1:
                bonuses[first_group[0]] += 3
                second_sizes = [s for _, s in sizes if s < max_size]
                if second_sizes:
                    second_max = max(second_sizes)
                    second_group = [pid for pid, s in sizes if s == second_max]
                    for pid in second_group:
                        bonuses[pid] += 1
            elif len(first_group) == 2:
                for pid in first_group:
                    bonuses[pid] += 2  # split 3+1 = 2 each? rulebook says split
            else:
                for pid in first_group:
                    bonuses[pid] += 1

    return bonuses


# ── Main scoring function ─────────────────────────────────────────────────────

SCORING_CARDS = {
    "bear_A": score_bear_A, "bear_B": score_bear_B,
    "bear_C": score_bear_C, "bear_D": score_bear_D,
    "elk_A":  score_elk_A,  "elk_B":  score_elk_B,
    "elk_C":  score_elk_C,  "elk_D":  score_elk_D,
    "salmon_A": score_salmon_A, "salmon_B": score_salmon_B,
    "salmon_C": score_salmon_C, "salmon_D": score_salmon_D,
    "hawk_A": score_hawk_A, "hawk_B": score_hawk_B,
    "hawk_C": score_hawk_C, "hawk_D": score_hawk_D,
    "fox_A":  score_fox_A,  "fox_B":  score_fox_B,
    "fox_C":  score_fox_C,  "fox_D":  score_fox_D,
}


def score_player(player: Player, scoring_cards: Dict[str, str]) -> ScoreBreakdown:
    bd = ScoreBreakdown()
    for wildlife in WILDLIFE:
        variant  = scoring_cards.get(wildlife, "A")
        fn       = SCORING_CARDS.get(f"{wildlife}_{variant}")
        bd.wildlife_scores[wildlife] = fn(player) if fn else 0
    bd.habitat_score      = score_habitat_corridors(player)
    bd.nature_token_score = player.nature_tokens
    bd.compute_total()
    return bd


def score_all_players(players: List[Player],
                      scoring_cards: Dict[str, str]) -> Dict[int, ScoreBreakdown]:
    """Score all players including majority bonuses."""
    results: Dict[int, ScoreBreakdown] = {}
    for player in players:
        results[player.player_id] = score_player(player, scoring_cards)

    majorities = score_habitat_majority(players)
    for player in players:
        pid = player.player_id
        results[pid].habitat_majority = majorities[pid]
        results[pid].compute_total()
        player.score = results[pid].total

    return results


# ── Scoring card descriptions ─────────────────────────────────────────────────

CARD_DESCRIPTIONS = {
    "bear_A": ("Bear — Card A: Pairs",
        ["Score increasing pts for total bear PAIRS.",
         "Pairs = sum of (group_size ÷ 2) across all groups.",
         "1 pair=2  2 pairs=5  3 pairs=9  4 pairs=13",
         "Groups may NOT touch each other!",
         "Tip: build multiple 2-bear groups."]),
    "bear_B": ("Bear — Card B: Trios",
        ["Score 10 pts for each group of EXACTLY 3 bears.",
         "Groups of 1, 2, 4+ score 0.",
         "Groups may NOT touch each other!",
         "Tip: aim for as many 3-bear groups as possible."]),
    "bear_C": ("Bear — Card C: Variety",
        ["Score for groups sized 1, 2, or 3:",
         "  1 bear = 2 pts   2 bears = 4 pts   3 bears = 7 pts",
         "BONUS: +3 pts if you have at least one of each!",
         "Groups may NOT touch each other!",
         "Tip: build one of each size for the bonus."]),
    "bear_D": ("Bear — Card D: Medium Groups",
        ["Score for groups sized 2, 3, or 4:",
         "  2 bears = 4 pts   3 bears = 7 pts   4 bears = 10 pts",
         "Solo bears and groups of 5+ score 0.",
         "Groups may NOT touch each other!",
         "Tip: build groups of exactly 4 for max points."]),
    "elk_A": ("Elk — Card A: Straight Lines",
        ["Score for elk in straight lines (flat-side to flat-side).",
         "  Line of 2=5  3=9  4=13  5=18",
         "Lines in any orientation. Elk groups may touch.",
         "Tip: align elk in long straight rows!"]),
    "elk_B": ("Elk — Card B: Shapes",
        ["Score for elk in specific formations.",
         "  2 elk=3  3 elk=7  4+ elk=11",
         "Elk groups may touch each other.",
         "Tip: build connected groups of 3-4 elk."]),
    "elk_C": ("Elk — Card C: Any Groups",
        ["Score for any connected elk group by size:",
         "  1=1  2=3  3=5  4=7  5=10  6+=14",
         "Groups can be any shape. Elk may touch.",
         "Tip: one big group scores better than many small ones."]),
    "elk_D": ("Elk — Card D: Circles",
        ["Score for elk in a circular formation.",
         "Every elk must touch exactly 2 others (closed ring).",
         "  3-ring=7  4-ring=9  5-ring=12  6-ring=15",
         "Tip: place elk in a hexagonal ring shape!"]),
    "salmon_A": ("Salmon — Card A: Long Runs",
        ["Score each salmon RUN by size (max 7).",
         "A run = each salmon touches ≤ 2 others.",
         "  1=2  2=4  3=7  4=11  5=15  6=20  7=25",
         "Runs may NOT touch other runs!",
         "Tip: build one long straight run."]),
    "salmon_B": ("Salmon — Card B: Medium Runs",
        ["Score each salmon run by size (max 5).",
         "  1=2  2=4  3=7  4=11  5=17",
         "Runs may NOT touch other runs!",
         "Tip: multiple runs of 3-5 are efficient."]),
    "salmon_C": ("Salmon — Card C: Mid Runs Only",
        ["Only runs of size 3, 4, or 5 score points.",
         "  3=7  4=11  5=17",
         "Size 1, 2, 6+ score NOTHING.",
         "Runs may NOT touch other runs!",
         "Tip: target runs of exactly 3-5 salmon."]),
    "salmon_D": ("Salmon — Card D: Diversity",
        ["Each run scores 1pt per salmon in run,",
         "PLUS 1pt per adjacent non-salmon token.",
         "(Each adjacent tile counted once per run)",
         "Runs may NOT touch other runs!",
         "Tip: place salmon near lots of other animals!"]),
    "hawk_A": ("Hawk — Card A: Solitary",
        ["Score increasing pts per isolated hawk:",
         "  1=2  2=5  3=8  4=11  5=14",
         "Hawks next to other hawks = 0.",
         "Tip: spread hawks far apart, 1 per region."]),
    "hawk_B": ("Hawk — Card B: Solo + Sightline",
        ["Score for hawks that are BOTH:",
         "  isolated (no adjacent hawk) AND",
         "  have line-of-sight to another hawk.",
         "  1=3  2=7  3=12  4=17  5=22",
         "Tip: keep hawks apart but in sight of each other."]),
    "hawk_C": ("Hawk — Card C: Sightlines",
        ["Score 3 pts for each line-of-sight BETWEEN two hawks.",
         "Line of sight = straight hex path, no hawk between.",
         "Same hawk can be in multiple lines.",
         "Tip: place hawks where they can see many others."]),
    "hawk_D": ("Hawk — Card D: Pairs + Diversity",
        ["Pair up hawks, score by unique animal types between them.",
         "  0 types=0  1=1  2=3  3=5  4=7",
         "Each hawk in one pair only.",
         "Tip: pair hawks with diverse animals between them."]),
    "fox_A": ("Fox — Card A: Diverse Neighbours",
        ["Each fox scores by unique adjacent species (incl. foxes):",
         "  0=0  1=1  2=2  3=4  4=7",
         "Tip: surround fox with 3-4 different animal types."]),
    "fox_B": ("Fox — Card B: Animal Pairs",
        ["Each fox scores by unique non-fox species with 2+ adjacent:",
         "  0=0  1=1  2=3  3=5  4=7",
         "Pairs don't need to be next to each other.",
         "Tip: cluster 2+ of the same species near each fox."]),
    "fox_C": ("Fox — Card C: Abundance",
        ["Each fox scores by the MOST COMMON adjacent non-fox species:",
         "  0=0  1=1  2=3  3=5  4=7",
         "Only the single most abundant type counts.",
         "Tip: surround each fox with lots of ONE animal type."]),
    "fox_D": ("Fox — Card D: Fox Pairs",
        ["Score PAIRS of adjacent foxes by unique animal pairs nearby.",
         "(8 combined adjacent tiles scored per fox pair)",
         "  0=0  1=2  2=5  3=8  4=11",
         "Tip: place foxes in adjacent pairs near diverse animals."]),
}

HABITAT_SCORING_DESC = [
    "Habitat Corridors (all players):",
    "Largest connected area per habitat = 1pt/tile.",
    "MAJORITY BONUS (per habitat):",
    "  2p: 2pts for largest, 1pt for second",
    "  3-4p: 3pts for largest, 1pt for second",
    "  Ties: points split evenly.",
]
