"""
Cascadia - Digital Board Game
Main entry point. Run this file to start the game.
"""

import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
from cascadia.gui.app import CascadiaApp


def main():
    pygame.init()
    app = CascadiaApp()
    app.run()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
