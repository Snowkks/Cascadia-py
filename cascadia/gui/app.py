"""
app.py - Application loop with F11 fullscreen toggle.

All game logic draws to a fixed 1280x800 virtual surface.
That surface is then scaled to fill the real window/screen.
Mouse events are remapped from real pixels back to virtual coords
so click detection always works regardless of window size.
"""
import os, sys

if os.environ.get("WAYLAND_DISPLAY"):
    os.environ.setdefault("SDL_VIDEODRIVER", "x11")
    os.environ.setdefault("DISPLAY", os.environ.get("DISPLAY", ":0"))

import pygame
from cascadia.constants import WINDOW_WIDTH as VW, WINDOW_HEIGHT as VH, FPS
from cascadia.game_engine import GameEngine
from cascadia.database import init_db, save_game_result


class CascadiaApp:
    def __init__(self):
        pygame.display.set_caption("Cascadia  —  F11: fullscreen  |  ESC: back")

        self._fullscreen = False
        self._real = pygame.display.set_mode((VW, VH), pygame.RESIZABLE)

        # Virtual surface — always 1280×800, all drawing goes here
        self._virt = pygame.Surface((VW, VH))

        self.clock = pygame.time.Clock()
        init_db()
        self._screen = None
        self._goto_menu()

    # ── Fullscreen toggle ──────────────────────────────────────────────────────

    def _toggle_fullscreen(self):
        self._fullscreen = not self._fullscreen
        if self._fullscreen:
            self._real = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self._real = pygame.display.set_mode((VW, VH), pygame.RESIZABLE)

    # ── Mouse coord remapping ─────────────────────────────────────────────────
    # Translate real-window pixels → virtual 1280×800 coords.

    def _remap(self, pos):
        rw, rh = self._real.get_size()
        # Letterbox: find the largest 16:10 rect centred in real window
        scale   = min(rw / VW, rh / VH)
        draw_w  = int(VW * scale)
        draw_h  = int(VH * scale)
        off_x   = (rw - draw_w) // 2
        off_y   = (rh - draw_h) // 2
        vx = int((pos[0] - off_x) / scale)
        vy = int((pos[1] - off_y) / scale)
        return (vx, vy)

    def _patch_event(self, event):
        """Return a new event with mouse coords remapped to virtual space."""
        rw, rh = self._real.get_size()
        if rw == VW and rh == VH:
            return event   # no remapping needed

        if event.type == pygame.MOUSEBUTTONDOWN:
            return pygame.event.Event(event.type,
                pos=self._remap(event.pos), button=event.button)
        if event.type == pygame.MOUSEBUTTONUP:
            return pygame.event.Event(event.type,
                pos=self._remap(event.pos), button=event.button)
        if event.type == pygame.MOUSEMOTION:
            rx, ry   = self._remap(event.pos)
            rw2, rh2 = self._real.get_size()
            scale = min(rw2 / VW, rh2 / VH)
            rel   = (int(event.rel[0] / scale), int(event.rel[1] / scale))
            return pygame.event.Event(event.type,
                pos=(rx, ry), rel=rel, buttons=event.buttons)
        return event

    # ── Drawing ───────────────────────────────────────────────────────────────

    def _blit_virtual(self):
        """Scale virtual surface to real window with letterboxing."""
        rw, rh  = self._real.get_size()
        scale   = min(rw / VW, rh / VH)
        draw_w  = int(VW * scale)
        draw_h  = int(VH * scale)
        off_x   = (rw - draw_w) // 2
        off_y   = (rh - draw_h) // 2

        self._real.fill((0, 0, 0))   # letterbox bars

        if scale == 1.0:
            self._real.blit(self._virt, (off_x, off_y))
        else:
            scaled = pygame.transform.smoothscale(self._virt, (draw_w, draw_h))
            self._real.blit(scaled, (off_x, off_y))

    # ── Also remap pygame.mouse.get_pos() used inside widgets ─────────────────

    def _patch_mouse(self):
        """
        pygame.mouse.get_pos() is called inside widgets for hover detection.
        We monkey-patch it to always return virtual coords during draw/update.
        """
        real_pos = pygame.mouse.get_pos()
        virtual_pos = self._remap(real_pos)
        pygame.mouse._real_get_pos = getattr(pygame.mouse, '_real_get_pos',
                                              pygame.mouse.get_pos)
        pygame.mouse.get_pos = lambda: virtual_pos

    def _unpatch_mouse(self):
        if hasattr(pygame.mouse, '_real_get_pos'):
            pygame.mouse.get_pos = pygame.mouse._real_get_pos

    # ── Screen navigation ─────────────────────────────────────────────────────

    def _goto_menu(self):
        from cascadia.gui.screen_menu import MenuScreen
        self._screen = MenuScreen(self._goto_setup, self._goto_leaderboard, self._quit)

    def _goto_setup(self):
        from cascadia.gui.screen_setup import SetupScreen
        self._screen = SetupScreen(self._start_game, self._goto_menu)

    def _start_game(self, names):
        from cascadia.gui.screen_game import GameScreen
        self._screen = GameScreen(GameEngine(names), self._on_game_over, self._goto_menu)

    def _on_game_over(self, engine):
        try:
            save_game_result(engine.players, engine.scores,
                             engine.scoring_cards, engine.turns_taken)
        except Exception as e:
            print(f"[WARN] save failed: {e}")

    def _goto_leaderboard(self):
        from cascadia.gui.screen_leaderboard import LeaderboardScreen
        self._screen = LeaderboardScreen(self._goto_menu)

    def _quit(self):
        pygame.quit(); sys.exit()

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        from cascadia.gui.screen_game        import GameScreen
        from cascadia.gui.screen_setup       import SetupScreen
        from cascadia.gui.screen_leaderboard import LeaderboardScreen

        while True:
            self.clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._quit()

                # F11 or Alt+Enter → toggle fullscreen
                if event.type == pygame.KEYDOWN:
                    if (event.key == pygame.K_F11 or
                            (event.key == pygame.K_RETURN and
                             event.mod & pygame.KMOD_ALT)):
                        self._toggle_fullscreen()
                        continue

                    if event.key == pygame.K_ESCAPE:
                        if isinstance(self._screen, (GameScreen, SetupScreen,
                                                      LeaderboardScreen)):
                            self._goto_menu()
                        continue

                # Remap mouse coords before passing to screen
                patched = self._patch_event(event)
                if self._screen:
                    self._screen.handle_event(patched)

            if self._screen:
                self._screen.update()
                self._patch_mouse()
                self._screen.draw(self._virt)
                self._unpatch_mouse()
                self._blit_virtual()

            pygame.display.flip()
