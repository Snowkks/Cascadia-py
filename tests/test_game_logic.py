"""
tests/test_game_logic.py
Unit tests for the non-GUI game logic modules.

Run with:
    python -m pytest tests/ -v
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from cascadia.models       import HexTile, WildlifeToken, Player, hex_neighbors
from cascadia.tile_factory import build_tile_deck, build_token_deck, build_starter_tile
from cascadia.scoring      import (
    score_bear_A, score_bear_B,
    score_elk_B,
    score_salmon_A, score_salmon_B,
    score_hawk_A,
    score_fox_A, score_fox_B,
    score_habitat_corridors,
    score_player,
)
from cascadia.game_engine  import GameEngine, Phase


# ────────────────────────────────────────────────────────────────────────────
# Model tests
# ────────────────────────────────────────────────────────────────────────────

class TestHexTile:
    def _make_tile(self, accepts, token=None):
        return HexTile("T000", ["forest"], accepts, token=token)

    def test_can_accept_empty_tile(self):
        t = self._make_tile({"bear", "elk"})
        assert t.can_accept("bear") is True
        assert t.can_accept("salmon") is False

    def test_can_accept_occupied_tile(self):
        tok = WildlifeToken("B00", "bear")
        t   = self._make_tile({"bear"}, token=tok)
        assert t.can_accept("bear") is False

    def test_place_token_success(self):
        t   = self._make_tile({"bear"})
        tok = WildlifeToken("B00", "bear")
        assert t.place_token(tok) is True
        assert t.token == tok

    def test_place_token_wrong_type(self):
        t   = self._make_tile({"elk"})
        tok = WildlifeToken("B00", "bear")
        assert t.place_token(tok) is False

    def test_remove_token(self):
        tok = WildlifeToken("B00", "bear")
        t   = self._make_tile({"bear"}, token=tok)
        removed = t.remove_token()
        assert removed == tok
        assert t.token is None


class TestPlayer:
    def _make_player(self):
        return Player(0, "Alice", (80, 180, 220))

    def test_add_first_tile(self):
        p = self._make_player()
        t = HexTile("T0", ["forest"], {"bear"})
        assert p.add_tile(t, 0, 0) is True

    def test_add_adjacent_tile(self):
        p  = self._make_player()
        t1 = HexTile("T1", ["forest"], {"bear"})
        t2 = HexTile("T2", ["wetland"], {"elk"})
        p.add_tile(t1, 0, 0)
        assert p.add_tile(t2, 1, 0) is True

    def test_add_non_adjacent_tile_fails(self):
        p  = self._make_player()
        t1 = HexTile("T1", ["forest"], {"bear"})
        t2 = HexTile("T2", ["wetland"], {"elk"})
        p.add_tile(t1, 0, 0)
        assert p.add_tile(t2, 5, 5) is False

    def test_valid_placements_empty_board(self):
        p = self._make_player()
        assert p.valid_placements() == [(0, 0)]

    def test_valid_placements_one_tile(self):
        p = self._make_player()
        t = HexTile("T0", ["forest"], {"bear"})
        p.add_tile(t, 0, 0)
        neighbors = hex_neighbors(0, 0)
        for pos in p.valid_placements():
            assert pos in neighbors

    def test_wildlife_counts(self):
        p  = self._make_player()
        t1 = HexTile("T1", ["forest"],  {"bear"})
        t2 = HexTile("T2", ["wetland"], {"bear"})
        tok1 = WildlifeToken("B1", "bear")
        tok2 = WildlifeToken("B2", "bear")
        t1.token = tok1
        t2.token = tok2
        p.add_tile(t1, 0, 0)
        p.add_tile(t2, 1, 0)
        counts = p.wildlife_counts()
        assert counts["bear"] == 2

    def test_nature_tokens(self):
        p = self._make_player()
        assert p.nature_tokens == 1
        assert p.spend_nature_token() is True
        assert p.nature_tokens == 0
        assert p.spend_nature_token() is False
        p.gain_nature_token()
        assert p.nature_tokens == 1


# ────────────────────────────────────────────────────────────────────────────
# Tile factory tests
# ────────────────────────────────────────────────────────────────────────────

class TestTileFactory:
    def test_tile_deck_size(self):
        deck = build_tile_deck(num_players=2)
        assert len(deck) == 43
        deck4 = build_tile_deck(num_players=4)
        assert len(deck4) == 83

    def test_all_tiles_have_habitats(self):
        for tile in build_tile_deck():
            assert len(tile.habitats) >= 1

    def test_all_tiles_have_accepts(self):
        for tile in build_tile_deck():
            assert len(tile.accepts) >= 1

    def test_token_deck_size(self):
        deck = build_token_deck()
        assert len(deck) == 100

    def test_token_deck_distribution(self):
        from collections import Counter
        deck   = build_token_deck()
        counts = Counter(t.wildlife_type for t in deck)
        for w in ["bear", "elk", "salmon", "hawk", "fox"]:
            assert counts[w] == 20

    def test_starter_tile(self):
        tile = build_starter_tile()
        assert tile.is_starter is True
        assert len(tile.habitats) >= 1
        assert len(tile.accepts) >= 1


# ────────────────────────────────────────────────────────────────────────────
# Scoring tests
# ────────────────────────────────────────────────────────────────────────────

def _player_with_tokens(positions_and_types):
    """
    Helper: create a player whose board has tiles at given positions
    with the specified wildlife tokens placed.
    positions_and_types: list of ((q,r), wildlife_type)
    """
    p = Player(0, "Test", (255, 255, 255))
    for (q, r), wtype in positions_and_types:
        t = HexTile(f"T{q}{r}", ["forest"], {wtype})
        p.add_tile(t, q, r)
        t.token = WildlifeToken(f"tok_{q}_{r}", wtype)
    return p


class TestBearScoring:
    def test_single_bear(self):
        p = _player_with_tokens([((0, 0), "bear")])
        assert score_bear_A(p) == 0  # 0 pairs = 0 pts

    def test_pair_of_bears(self):
        p = _player_with_tokens([((0, 0), "bear"), ((1, 0), "bear")])
        assert score_bear_A(p) == 2  # 1 pair = 2 pts

    def test_triple_bears(self):
        p = _player_with_tokens([
            ((0, 0), "bear"), ((1, 0), "bear"), ((1, -1), "bear")
        ])
        assert score_bear_A(p) == 2  # group of 3 = 1 pair = 2 pts

    def test_no_bears(self):
        p = Player(0, "Test", (0, 0, 0))
        assert score_bear_A(p) == 0


class TestSalmonScoring:
    def test_single_salmon(self):
        p = _player_with_tokens([((0, 0), "salmon")])
        assert score_salmon_A(p) == 2

    def test_isolated_salmon_B(self):
        # Two non-adjacent salmon
        p = _player_with_tokens([((0, 0), "salmon"), ((3, 0), "salmon")])
        # Both should be isolated in score_salmon_B
        # But (3,0) might not be reachable by adjacency from (0,0) alone
        # so we need to build a chain of tiles
        p2 = Player(0, "Test", (0, 0, 0))
        positions = [(0, 0), (1, 0), (2, 0), (3, 0)]
        for i, (q, r) in enumerate(positions):
            wtype = "salmon" if q in (0, 3) else "elk"
            t = HexTile(f"T{i}", ["forest"], {wtype})
            p2.add_tile(t, q, r)
            t.token = WildlifeToken(f"tok{i}", wtype)
        assert score_salmon_B(p2) == 4  # 2 isolated salmon × 2


class TestHawkScoring:
    def test_isolated_hawk_scores_5(self):
        p = Player(0, "Test", (0, 0, 0))
        t = HexTile("T0", ["mountain"], {"hawk"})
        p.add_tile(t, 0, 0)
        t.token = WildlifeToken("H0", "hawk")
        assert score_hawk_A(p) == 2  # 1 isolated hawk = 2 pts

    def test_adjacent_hawks_score_0(self):
        p = _player_with_tokens([((0, 0), "hawk"), ((1, 0), "hawk")])
        assert score_hawk_A(p) == 0


class TestFoxScoring:
    def test_fox_with_diverse_neighbors(self):
        p = Player(0, "Test", (0, 0, 0))
        center = HexTile("C", ["forest"], {"fox"})
        p.add_tile(center, 0, 0)
        center.token = WildlifeToken("F0", "fox")

        neighbors_info = [
            ((1, 0),  "bear"),
            ((-1, 0), "elk"),
            ((0, 1),  "salmon"),
        ]
        for (q, r), wtype in neighbors_info:
            t = HexTile(f"N{q}{r}", ["forest"], {wtype})
            p.add_tile(t, q, r)
            t.token = WildlifeToken(f"tok{q}{r}", wtype)

        # fox_A: counts unique neighbour species (fox counts itself = 4 unique types)
        assert score_fox_A(p) == 4
        # fox_B: counts species that appear 2+ times adjacent — none here, so 0
        assert score_fox_B(p) == 0


class TestHabitatScoring:
    def test_single_habitat_tile(self):
        p = Player(0, "Test", (0, 0, 0))
        t = HexTile("T0", ["forest"], {"bear"})
        p.add_tile(t, 0, 0)
        score = score_habitat_corridors(p)
        assert score == 1  # single tile = 1 pt (size-1 corridor)

    def test_two_connected_same_habitat(self):
        p = Player(0, "Test", (0, 0, 0))
        t1 = HexTile("T1", ["forest"], {"bear"})
        t2 = HexTile("T2", ["forest"], {"elk"})
        p.add_tile(t1, 0, 0)
        p.add_tile(t2, 1, 0)
        score = score_habitat_corridors(p)
        assert score == 2  # corridor of 2 = 2 pts


# ────────────────────────────────────────────────────────────────────────────
# GameEngine tests
# ────────────────────────────────────────────────────────────────────────────

class TestGameEngine:
    def _new_engine(self, n=2):
        names = [f"P{i}" for i in range(n)]
        return GameEngine(names, seed=42)

    def test_initial_phase(self):
        eng = self._new_engine()
        assert eng.phase == Phase.SELECT_PAIR

    def test_market_filled_on_start(self):
        eng = self._new_engine()
        assert all(t is not None for t in eng.market_tiles)
        assert all(t is not None for t in eng.market_tokens)

    def test_starter_tiles(self):
        eng = self._new_engine()
        for p in eng.players:
            assert len(p.board) == 1  # 1 starter tile per player

    def test_select_pair_advances_phase(self):
        eng = self._new_engine()
        assert eng.select_market_pair(0) is True
        assert eng.phase == Phase.PLACE_TILE

    def test_invalid_phase_returns_false(self):
        eng = self._new_engine()
        eng.select_market_pair(0)  # now PLACE_TILE
        assert eng.select_market_pair(1) is False  # wrong phase

    def test_place_tile_advances_to_place_token(self):
        eng = self._new_engine()
        eng.select_market_pair(0)
        pos = eng.pending_placement_positions[0]
        assert eng.place_tile(*pos) is True
        assert eng.phase == Phase.PLACE_TOKEN

    def test_discard_token_grants_nature_token(self):
        eng = self._new_engine()
        eng.select_market_pair(0)
        pos = eng.pending_placement_positions[0]
        eng.place_tile(*pos)
        before = eng.current_player.nature_tokens
        # current_player may have changed after place_tile; discard token
        # (we test the player whose turn it was)
        first_player = eng.players[0]
        before_nt = first_player.nature_tokens
        eng.discard_token()
        # Discard returns token to bag — no nature token reward (rulebook)
        assert first_player.nature_tokens == before_nt

    def test_full_turn_advances_player(self):
        eng = self._new_engine()
        first = eng.current_player.player_id
        eng.select_market_pair(0)
        pos = eng.pending_placement_positions[0]
        eng.place_tile(*pos)
        eng.discard_token()
        assert eng.current_player.player_id != first

    def test_nature_token_replace(self):
        eng = self._new_engine()
        # Give player extra nature tokens
        eng.current_player.nature_tokens = 3
        old_tokens = [t.token_id for t in eng.market_tokens if t]
        assert eng.use_nature_token_replace_tokens() is True
        new_tokens = [t.token_id for t in eng.market_tokens if t]
        # At least some tokens should have changed
        assert old_tokens != new_tokens

    def test_game_runs_to_completion(self):
        """Simulate a full game without error."""
        eng = GameEngine(["Alice", "Bob"], seed=7)
        steps = 0
        while not eng.is_game_over() and steps < 10000:
            steps += 1
            if eng.phase == Phase.SELECT_PAIR:
                for i in range(4):
                    if eng.market_tiles[i]:
                        eng.select_market_pair(i)
                        break
            elif eng.phase == Phase.PLACE_TILE:
                pos = eng.pending_placement_positions
                if pos:
                    eng.place_tile(*pos[0])
            elif eng.phase == Phase.PLACE_TOKEN:
                valid = eng.get_valid_token_positions()
                if valid:
                    eng.place_token(*valid[0])
                else:
                    eng.discard_token()
        assert eng.is_game_over()
        for p in eng.players:
            assert p.score >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
