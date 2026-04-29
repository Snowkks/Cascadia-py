"""
game_engine.py - Cascadia game state machine.

Fixes per official rulebook:
  • Single starter tile per player (not 3)
  • Tile count per player count (43/63/83)
  • Discard token → return to bag, NO nature token reward
  • Keystone tile: placing matching token → gain 1 Nature Token
  • Habitat majority bonuses scored at end
  • Tie-breaking: most nature tokens, then shared victory
"""
from __future__ import annotations
import random
from enum import Enum, auto
from typing import List, Dict, Tuple, Optional

from cascadia.models   import HexTile, WildlifeToken, Player
from cascadia.tile_factory import build_tile_deck, build_token_deck, build_starter_tile
from cascadia.scoring  import score_player, score_all_players, ScoreBreakdown
from cascadia.constants import (
    WILDLIFE, HABITATS, MARKET_SIZE, TURNS_PER_GAME,
    OVERPOPULATION_MAX, NUM_PLAYERS_MIN, NUM_PLAYERS_MAX,
)


class Phase(Enum):
    SETUP         = auto()
    SELECT_PAIR   = auto()
    PLACE_TILE    = auto()
    PLACE_TOKEN   = auto()
    NATURE_ACTION = auto()
    END_TURN      = auto()
    GAME_OVER     = auto()


class GameEngine:
    def __init__(self, player_names: List[str], seed: int = None):
        if not (NUM_PLAYERS_MIN <= len(player_names) <= NUM_PLAYERS_MAX):
            raise ValueError(f"Need {NUM_PLAYERS_MIN}-{NUM_PLAYERS_MAX} players.")

        self.rng = random.Random(seed)
        n = len(player_names)

        # Build decks with correct tile count for player count
        self._tile_deck  = build_tile_deck(self.rng, num_players=n)
        self._token_deck = build_token_deck(self.rng)

        # Players
        player_colors = [(80,180,220),(220,120,60),(180,80,200),(80,200,130)]
        self.players: List[Player] = []
        for i, name in enumerate(player_names):
            self.players.append(Player(i, name, player_colors[i % 4]))

        # Scoring cards A/B/C/D
        self.scoring_cards: Dict[str, str] = {
            w: self.rng.choice(["A","B","C","D"]) for w in WILDLIFE
        }

        # Market
        self.market_tiles:  List[Optional[HexTile]]       = [None] * MARKET_SIZE
        self.market_tokens: List[Optional[WildlifeToken]]  = [None] * MARKET_SIZE

        # Turn tracking
        self.current_idx  = 0
        self.turns_taken  = 0
        self.total_turns  = TURNS_PER_GAME * n

        # Selection state
        self.selected_pair:  Optional[int]           = None
        self.selected_tile:  Optional[HexTile]        = None
        self.selected_token: Optional[WildlifeToken]  = None
        self.pending_placement_positions: List[Tuple[int,int]] = []

        # Rotation of the selected tile (0-5)
        self.tile_rotation: int = 0

        # Results
        self.scores: Dict[int, ScoreBreakdown] = {}
        self.winners: List[Player] = []
        self.log: List[str] = []

        self.phase = Phase.SETUP
        self._setup_game()

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _setup_game(self):
        # Each player gets exactly 1 starter tile (rulebook p.4)
        for player in self.players:
            tile = build_starter_tile(self.rng)
            player.board[(0, 0)] = tile

        self._fill_market()
        self.phase = Phase.SELECT_PAIR
        self._log(f"Game started — {len(self.players)} players.")
        cards_str = ", ".join(f"{w.capitalize()}:{v}"
                              for w, v in self.scoring_cards.items())
        self._log(f"Scoring cards: {cards_str}")

    def _fill_market(self):
        for i in range(MARKET_SIZE):
            if self.market_tiles[i]  is None: self.market_tiles[i]  = self._draw_tile()
            if self.market_tokens[i] is None: self.market_tokens[i] = self._draw_token()
        self._check_overpopulation()

    def _draw_tile(self)  -> Optional[HexTile]:
        return self._tile_deck.pop(0)  if self._tile_deck  else None

    def _draw_token(self) -> Optional[WildlifeToken]:
        return self._token_deck.pop(0) if self._token_deck else None

    def _check_overpopulation(self):
        for _ in range(10):
            counts: Dict[str, List[int]] = {}
            for i, tok in enumerate(self.market_tokens):
                if tok: counts.setdefault(tok.wildlife_type, []).append(i)
            over = [idx for idx in counts.values() if len(idx) >= OVERPOPULATION_MAX]
            if not over: break
            for indices in over:
                for i in indices:
                    if self.market_tokens[i]:
                        self._token_deck.append(self.market_tokens[i])
                        self.market_tokens[i] = None
                self._log("Overpopulation — tokens returned to bag.")
            for i in range(MARKET_SIZE):
                if self.market_tokens[i] is None:
                    self.market_tokens[i] = self._draw_token()

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def current_player(self) -> Player:
        return self.players[self.current_idx]

    def select_market_pair(self, index: int) -> bool:
        if self.phase != Phase.SELECT_PAIR: return False
        if not (0 <= index < MARKET_SIZE):  return False
        if self.market_tiles[index] is None: return False

        self.selected_pair  = index
        self.selected_tile  = self.market_tiles[index]
        self.selected_token = self.market_tokens[index]
        self.tile_rotation  = 0   # reset rotation for new tile
        self.market_tiles[index]  = None
        self.market_tokens[index] = None

        self.phase = Phase.PLACE_TILE
        self.pending_placement_positions = self.current_player.valid_placements()
        tok_name = self.selected_token.wildlife_type if self.selected_token else "none"
        self._log(f"{self.current_player.name} picked slot {index+1}: "
                  f"tile={'/'.join(self.selected_tile.habitats)} token={tok_name}")
        return True

    def rotate_selected_tile(self, clockwise: bool = True):
        """Rotate the currently selected (not yet placed) tile."""
        if self.phase != Phase.PLACE_TILE or not self.selected_tile:
            return
        if clockwise:
            self.selected_tile.rotate_cw()
        else:
            self.selected_tile.rotate_ccw()
        self.tile_rotation = self.selected_tile.rotation

    def place_tile(self, q: int, r: int) -> bool:
        if self.phase != Phase.PLACE_TILE: return False
        if (q, r) not in self.pending_placement_positions: return False
        if not self.current_player.add_tile(self.selected_tile, q, r): return False
        self.phase = Phase.PLACE_TOKEN
        self._log(f"{self.current_player.name} placed tile at ({q},{r})")
        return True

    def place_token(self, q: int, r: int) -> bool:
        if self.phase != Phase.PLACE_TOKEN: return False
        if self.selected_token is None:
            self._advance_turn(); return True

        tile = self.current_player.get_tile_at(q, r)
        if tile is None or not tile.can_accept(self.selected_token.wildlife_type):
            return False

        tile.place_token(self.selected_token)
        self._log(f"{self.current_player.name} placed "
                  f"{self.selected_token.wildlife_type} at ({q},{r})")

        # KEYSTONE RULE: placing matching token on keystone tile → gain 1 Nature Token
        if tile.keystone:
            self.current_player.gain_nature_token()
            self._log(f"  ★ Keystone bonus! {self.current_player.name} gains a Nature Token.")

        self._advance_turn()
        return True

    def discard_token(self) -> bool:
        """
        Return selected token to bag. No nature token reward (per rulebook).
        This is used when the player cannot or does not want to place the token.
        """
        if self.phase != Phase.PLACE_TOKEN: return False
        if self.selected_token is not None:
            # Return token to bottom of bag
            self._token_deck.append(self.selected_token)
            self._log(f"{self.current_player.name} returned "
                      f"{self.selected_token.wildlife_type} to the bag.")
        self._advance_turn()
        return True

    def use_nature_token_replace_tokens(self) -> bool:
        """Spend 1 Nature Token to wipe all 4 market tokens."""
        if self.phase != Phase.SELECT_PAIR: return False
        if not self.current_player.spend_nature_token(): return False
        for i in range(MARKET_SIZE):
            if self.market_tokens[i]:
                self._token_deck.append(self.market_tokens[i])
            self.market_tokens[i] = self._draw_token()
        self._check_overpopulation()
        self._log(f"{self.current_player.name} spent a Nature Token — replaced all tokens.")
        return True

    def use_nature_token_pick_freely(self, tile_idx: int, token_idx: int) -> bool:
        """Spend 1 Nature Token to pick tile and token from different slots."""
        if self.phase != Phase.SELECT_PAIR: return False
        if not (0 <= tile_idx < MARKET_SIZE and 0 <= token_idx < MARKET_SIZE): return False
        if self.market_tiles[tile_idx] is None: return False
        if self.market_tokens[token_idx] is None: return False
        if not self.current_player.spend_nature_token(): return False

        self.selected_tile  = self.market_tiles[tile_idx]
        self.selected_token = self.market_tokens[token_idx]
        self.tile_rotation  = 0
        self.market_tiles[tile_idx]   = None
        self.market_tokens[token_idx] = None

        self.phase = Phase.PLACE_TILE
        self.pending_placement_positions = self.current_player.valid_placements()
        self._log(f"{self.current_player.name} used Nature Token: "
                  f"tile slot {tile_idx+1}, token slot {token_idx+1}.")
        return True

    # ── Turn advancement ──────────────────────────────────────────────────────

    def _advance_turn(self):
        self.selected_pair  = None
        self.selected_tile  = None
        self.selected_token = None
        self.tile_rotation  = 0
        self.pending_placement_positions = []

        self.turns_taken += 1
        self._fill_market()

        if self.turns_taken >= self.total_turns or not self._tile_deck:
            self._end_game()
        else:
            self.current_idx = (self.current_idx + 1) % len(self.players)
            self.phase = Phase.SELECT_PAIR
            self._log(f"--- {self.current_player.name}'s turn ---")

    def _end_game(self):
        self.phase  = Phase.GAME_OVER
        self.scores = score_all_players(self.players, self.scoring_cards)

        # Tie-breaking: most nature tokens → shared victory
        top_score = max(p.score for p in self.players)
        tied      = [p for p in self.players if p.score == top_score]
        if len(tied) > 1:
            max_nt   = max(p.nature_tokens for p in tied)
            self.winners = [p for p in tied if p.nature_tokens == max_nt]
        else:
            self.winners = tied

        if len(self.winners) == 1:
            self._log(f"Game over! Winner: {self.winners[0].name} "
                      f"with {self.winners[0].score} pts.")
        else:
            names = " & ".join(w.name for w in self.winners)
            self._log(f"Game over! Shared victory: {names} "
                      f"with {self.winners[0].score} pts.")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _log(self, msg: str):
        self.log.append(msg)
        if len(self.log) > 200:
            self.log = self.log[-200:]

    def get_valid_token_positions(self) -> List[Tuple[int,int]]:
        if self.selected_token is None: return []
        return [(q,r) for (q,r), tile in self.current_player.board.items()
                if tile.can_accept(self.selected_token.wildlife_type)]

    def turns_remaining(self) -> int:
        return max(0, self.total_turns - self.turns_taken)

    def is_game_over(self) -> bool:
        return self.phase == Phase.GAME_OVER
