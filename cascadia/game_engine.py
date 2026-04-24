"""
game_engine.py - Central game state machine for Cascadia.

Manages turn flow, the market, the supply decks, and all legal-move logic.
The GUI layer calls methods on GameEngine; it never mutates state directly.

Turn phases:
    SETUP        -> initial tile placement
    SELECT_PAIR  -> player picks one of 4 tile/token pairs from market
    PLACE_TILE   -> player places the chosen tile on their board
    PLACE_TOKEN  -> player places (or discards) the chosen token
    END_TURN     -> bookkeeping, advance player
    GAME_OVER    -> scoring
"""

from __future__ import annotations
import random
from enum import Enum, auto
from typing import List, Dict, Tuple, Optional

from cascadia.models   import HexTile, WildlifeToken, Player
from cascadia.tile_factory import build_tile_deck, build_token_deck, build_starter_wedge
from cascadia.scoring  import score_player, ScoreBreakdown
from cascadia.constants import (
    WILDLIFE, HABITATS, MARKET_SIZE, TURNS_PER_GAME,
    OVERPOPULATION_MAX, NUM_PLAYERS_MIN, NUM_PLAYERS_MAX,
)


class Phase(Enum):
    SETUP        = auto()
    SELECT_PAIR  = auto()
    PLACE_TILE   = auto()
    PLACE_TOKEN  = auto()
    NATURE_ACTION = auto()
    END_TURN     = auto()
    GAME_OVER    = auto()


class GameEngine:
    """
    Manages all Cascadia game logic.

    Attributes:
        players          List of Player objects
        current_idx      Index into players of whose turn it is
        phase            Current Phase enum value
        market_tiles     4 face-up HexTile objects
        market_tokens    4 face-up WildlifeToken objects (paired by index)
        selected_pair    Index (0-3) of the chosen market pair, or None
        selected_tile    The HexTile chosen from market
        selected_token   The WildlifeToken chosen from market
        turns_taken      How many full turns have completed
        scoring_cards    Dict: wildlife -> variant ("A"/"B")
        scores           Final ScoreBreakdown per player (after game over)
        log              List of human-readable event strings
    """

    def __init__(self, player_names: List[str], seed: int = None):
        if not (NUM_PLAYERS_MIN <= len(player_names) <= NUM_PLAYERS_MAX):
            raise ValueError(f"Need {NUM_PLAYERS_MIN}-{NUM_PLAYERS_MAX} players.")

        self.rng = random.Random(seed)

        # Build decks
        self._tile_deck  = build_tile_deck(self.rng)
        self._token_deck = build_token_deck(self.rng)

        # Create players
        player_colors = [
            (80, 180, 220), (220, 120, 60), (180, 80, 200), (80, 200, 130)
        ]
        self.players: List[Player] = []
        for i, name in enumerate(player_names):
            p = Player(i, name, player_colors[i % len(player_colors)])
            self.players.append(p)

        # Scoring cards – randomly pick A or B for each wildlife
        self.scoring_cards: Dict[str, str] = {
            w: self.rng.choice(["A", "B"]) for w in WILDLIFE
        }

        # Market
        self.market_tiles:  List[Optional[HexTile]]     = [None] * MARKET_SIZE
        self.market_tokens: List[Optional[WildlifeToken]] = [None] * MARKET_SIZE

        # Turn tracking
        self.current_idx   = 0
        self.turns_taken   = 0
        self.total_turns   = TURNS_PER_GAME * len(self.players)

        # Selection state
        self.selected_pair:  Optional[int]          = None
        self.selected_tile:  Optional[HexTile]       = None
        self.selected_token: Optional[WildlifeToken] = None
        self.pending_placement_positions: List[Tuple[int,int]] = []

        # Results
        self.scores: Dict[int, ScoreBreakdown] = {}
        self.log:    List[str] = []

        # Phase
        self.phase = Phase.SETUP
        self._setup_game()

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _setup_game(self):
        """Give each player starter tiles and fill the initial market."""
        for player in self.players:
            wedge = build_starter_wedge(self.rng)
            for tile in wedge:
                player.board[(tile.q, tile.r)] = tile

        self._fill_market()
        self.phase = Phase.SELECT_PAIR
        self._log(f"Game started with {len(self.players)} players.")
        self._log(f"Scoring cards: {self.scoring_cards}")

    def _fill_market(self):
        """Refill any empty market slots from the decks."""
        for i in range(MARKET_SIZE):
            if self.market_tiles[i] is None:
                self.market_tiles[i] = self._draw_tile()
            if self.market_tokens[i] is None:
                self.market_tokens[i] = self._draw_token()
        self._check_overpopulation()

    def _draw_tile(self) -> Optional[HexTile]:
        return self._tile_deck.pop(0) if self._tile_deck else None

    def _draw_token(self) -> Optional[WildlifeToken]:
        return self._token_deck.pop(0) if self._token_deck else None

    def _check_overpopulation(self):
        """If 3+ tokens of same type show in market, wipe and replace them."""
        for _ in range(10):  # safety limit
            counts: Dict[str, List[int]] = {}
            for i, tok in enumerate(self.market_tokens):
                if tok:
                    counts.setdefault(tok.wildlife_type, []).append(i)
            over = [indices for indices in counts.values()
                    if len(indices) >= OVERPOPULATION_MAX]
            if not over:
                break
            for indices in over:
                for i in indices:
                    # return token to bottom of deck
                    if self.market_tokens[i]:
                        self._token_deck.append(self.market_tokens[i])
                        self.market_tokens[i] = None
                self._log("Overpopulation! Tokens returned and redrawn.")
            # refill
            for i in range(MARKET_SIZE):
                if self.market_tokens[i] is None:
                    self.market_tokens[i] = self._draw_token()

    # ── Public action API ─────────────────────────────────────────────────────

    @property
    def current_player(self) -> Player:
        return self.players[self.current_idx]

    def select_market_pair(self, index: int) -> bool:
        """
        Phase: SELECT_PAIR
        Player picks one of the 4 tile/token market pairs.
        Returns True if successful.
        """
        if self.phase != Phase.SELECT_PAIR:
            return False
        if not (0 <= index < MARKET_SIZE):
            return False
        if self.market_tiles[index] is None:
            return False

        self.selected_pair  = index
        self.selected_tile  = self.market_tiles[index]
        self.selected_token = self.market_tokens[index]

        # Remove from market
        self.market_tiles[index]  = None
        self.market_tokens[index] = None

        self.phase = Phase.PLACE_TILE
        self.pending_placement_positions = self.current_player.valid_placements()
        self._log(
            f"{self.current_player.name} selected pair {index}: "
            f"tile={self.selected_tile.habitats}, token={self.selected_token.wildlife_type if self.selected_token else 'none'}"
        )
        return True

    def place_tile(self, q: int, r: int) -> bool:
        """
        Phase: PLACE_TILE
        Place the selected tile at grid position (q, r).
        Returns True if successful.
        """
        if self.phase != Phase.PLACE_TILE:
            return False
        if (q, r) not in self.pending_placement_positions:
            return False
        if not self.current_player.add_tile(self.selected_tile, q, r):
            return False

        self.phase = Phase.PLACE_TOKEN
        self._log(f"{self.current_player.name} placed tile at ({q},{r})")
        return True

    def place_token(self, q: int, r: int) -> bool:
        """
        Phase: PLACE_TOKEN
        Place the selected token onto a tile at (q, r) on the current player's board.
        (q, r) must be a tile that accepts this token type.
        Returns True if successful.
        """
        if self.phase != Phase.PLACE_TOKEN:
            return False
        if self.selected_token is None:
            # No token drawn – skip to end turn
            self._advance_turn()
            return True

        tile = self.current_player.get_tile_at(q, r)
        if tile is None or not tile.can_accept(self.selected_token.wildlife_type):
            return False

        tile.place_token(self.selected_token)
        self._log(
            f"{self.current_player.name} placed {self.selected_token.wildlife_type} token at ({q},{r})"
        )
        self._advance_turn()
        return True

    def discard_token(self) -> bool:
        """
        Phase: PLACE_TOKEN
        Discard the selected token and gain a nature token.
        """
        if self.phase != Phase.PLACE_TOKEN:
            return False
        if self.selected_token is None:
            self._advance_turn()
            return True
        self.current_player.gain_nature_token()
        self._log(
            f"{self.current_player.name} discarded {self.selected_token.wildlife_type} "
            f"token for a nature token."
        )
        self._advance_turn()
        return True

    def use_nature_token_replace_tokens(self) -> bool:
        """
        Spend a nature token to replace all 4 market tokens.
        Can be used before SELECT_PAIR.
        """
        if self.phase != Phase.SELECT_PAIR:
            return False
        if not self.current_player.spend_nature_token():
            return False
        for i in range(MARKET_SIZE):
            if self.market_tokens[i]:
                self._token_deck.append(self.market_tokens[i])
            self.market_tokens[i] = self._draw_token()
        self._check_overpopulation()
        self._log(f"{self.current_player.name} spent a nature token to replace all tokens.")
        return True

    def use_nature_token_pick_freely(self, tile_idx: int, token_idx: int) -> bool:
        """
        Spend a nature token to pick any tile from one slot and any token from another.
        """
        if self.phase != Phase.SELECT_PAIR:
            return False
        if not (0 <= tile_idx < MARKET_SIZE and 0 <= token_idx < MARKET_SIZE):
            return False
        if self.market_tiles[tile_idx] is None or self.market_tokens[token_idx] is None:
            return False
        if not self.current_player.spend_nature_token():
            return False

        self.selected_tile  = self.market_tiles[tile_idx]
        self.selected_token = self.market_tokens[token_idx]
        self.market_tiles[tile_idx]   = None
        self.market_tokens[token_idx] = None

        self.phase = Phase.PLACE_TILE
        self.pending_placement_positions = self.current_player.valid_placements()
        self._log(
            f"{self.current_player.name} used nature token: tile slot {tile_idx}, "
            f"token slot {token_idx}."
        )
        return True

    # ── Turn advancement ──────────────────────────────────────────────────────

    def _advance_turn(self):
        """Clean up selection state, refill market, and move to next player."""
        self.selected_pair  = None
        self.selected_tile  = None
        self.selected_token = None
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
        self.phase = Phase.GAME_OVER
        for player in self.players:
            self.scores[player.player_id] = score_player(player, self.scoring_cards)
            player.score = self.scores[player.player_id].total
        winner = max(self.players, key=lambda p: p.score)
        self._log(f"Game over! Winner: {winner.name} with {winner.score} pts.")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _log(self, msg: str):
        self.log.append(msg)
        if len(self.log) > 200:
            self.log = self.log[-200:]

    def get_valid_token_positions(self) -> List[Tuple[int, int]]:
        """Return board positions where the selected token can be placed."""
        if self.selected_token is None:
            return []
        return [
            (q, r) for (q, r), tile in self.current_player.board.items()
            if tile.can_accept(self.selected_token.wildlife_type)
        ]

    def turns_remaining(self) -> int:
        return max(0, self.total_turns - self.turns_taken)

    def is_game_over(self) -> bool:
        return self.phase == Phase.GAME_OVER
