"""
Cascadia – Digital Board Game
Entry point. Run:  python main.py
                   python main.py --wayland   (native Wayland, may have click offsets)
"""
import sys
import os

# Parse --wayland flag before anything else
if "--wayland" in sys.argv:
    os.environ["CASCADIA_WAYLAND"] = "1"
    sys.argv.remove("--wayland")

# Project root on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
pygame.init()

from cascadia.gui.app import CascadiaApp

def main():
    app = CascadiaApp()
    app.run()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
