"""
app.py - Top-level application class for Cascadia.

Owns the pygame window, the main event loop, and all screen instances.
Acts as a simple screen router.
"""

from __future__ import annotations
import pygame
import sys
from typing import Optional, List

from cascadia.constants import WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, FPS, COLORS
from cascadia.game_engine import GameEngine
from cascadia.database import init_db, save_game_result
from cascadia.gui.screen_menu        import MenuScreen
from cascadia.gui.screen_setup       import SetupScreen
from cascadia.gui.screen_game        import GameScreen
from cascadia.gui.screen_leaderboard import LeaderboardScreen


class CascadiaApp:
    """
    Central application object. Call .run() to start the event loop.

    Screens are lazily created and swapped via _switch_to_*.
    """

    def __init__(self):
        pygame.display.set_caption(WINDOW_TITLE)
        self.screen = pygame.display.set_mode(
            (WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE
        )
        # Off-screen surface always drawn at the canonical resolution
        self._virtual = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock  = pygame.time.Clock()

        # Ensure DB is ready
        init_db()

        # Build initial screen
        self._current_screen = None
        self._switch_to_menu()

    # ── Screen transitions ─────────────────────────────────────────────────────

    def _switch_to_menu(self):
        self._current_screen = MenuScreen(
            on_new_game    = self._switch_to_setup,
            on_leaderboard = self._switch_to_leaderboard,
            on_quit        = self._quit,
        )

    def _switch_to_setup(self):
        self._current_screen = SetupScreen(
            on_start = self._start_game,
            on_back  = self._switch_to_menu,
        )

    def _start_game(self, player_names: List[str]):
        try:
            engine = GameEngine(player_names)
        except Exception as e:
            print(f"[ERROR] Could not create game: {e}")
            self._switch_to_menu()
            return

        self._current_screen = GameScreen(
            engine       = engine,
            on_game_over = self._on_game_over,
            on_menu      = self._switch_to_menu,
        )

    def _on_game_over(self, engine: GameEngine):
        """Save results to DB and stay on the game screen (overlay shown)."""
        try:
            save_game_result(
                players      = engine.players,
                scores       = engine.scores,
                scoring_cards = engine.scoring_cards,
                turns_taken  = engine.turns_taken,
            )
        except Exception as e:
            print(f"[WARN] Could not save game result: {e}")

    def _switch_to_leaderboard(self):
        self._current_screen = LeaderboardScreen(
            on_back = self._switch_to_menu,
        )

    def _quit(self):
        pygame.quit()
        sys.exit()

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0   # seconds since last frame

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._quit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if isinstance(self._current_screen, GameScreen):
                        self._switch_to_menu()
                    elif isinstance(self._current_screen, (SetupScreen, LeaderboardScreen)):
                        self._switch_to_menu()

                # ── Remap mouse coords to virtual 1280×800 space ──────────
                event = self._remap_event(event)
                if self._current_screen:
                    self._current_screen.handle_event(event)

            if self._current_screen:
                self._current_screen.update(dt)
                self._draw_frame()

            pygame.display.flip()

    def _draw_frame(self):
        """Draw to the virtual surface then scale to the real window."""
        self._virtual.fill((0, 0, 0))
        self._current_screen.draw(self._virtual)
        actual_w = self.screen.get_width()
        actual_h = self.screen.get_height()
        if actual_w != WINDOW_WIDTH or actual_h != WINDOW_HEIGHT:
            scaled = pygame.transform.scale(self._virtual, (actual_w, actual_h))
            self.screen.blit(scaled, (0, 0))
        else:
            self.screen.blit(self._virtual, (0, 0))

    def _remap_event(self, event: pygame.event.Event) -> pygame.event.Event:
        """
        Translate mouse positions from real window pixels to the
        virtual 1280×800 coordinate space so all collision checks work
        regardless of actual window size.
        """
        actual_w = self.screen.get_width()
        actual_h = self.screen.get_height()
        if actual_w == WINDOW_WIDTH and actual_h == WINDOW_HEIGHT:
            return event

        sx = WINDOW_WIDTH  / actual_w
        sy = WINDOW_HEIGHT / actual_h

        if event.type in (pygame.MOUSEMOTION,):
            x = int(event.pos[0] * sx)
            y = int(event.pos[1] * sy)
            rel = (int(event.rel[0] * sx), int(event.rel[1] * sy))
            return pygame.event.Event(event.type,
                                      pos=(x, y), rel=rel, buttons=event.buttons)

        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            x = int(event.pos[0] * sx)
            y = int(event.pos[1] * sy)
            return pygame.event.Event(event.type,
                                      pos=(x, y), button=event.button)

        return event
