"""
Run this BEFORE main.py to diagnose your display scaling situation.
  python debug_layout.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
pygame.init()

# Print every display/env fact we can gather
print("=== Display Info ===")
print(f"pygame version      : {pygame.version.ver}")
print(f"SDL version         : {'.'.join(str(x) for x in pygame.get_sdl_version())}")

di = pygame.display.Info()
print(f"display.Info w×h    : {di.current_w} × {di.current_h}")

modes = pygame.display.list_modes()
print(f"list_modes (first 3): {modes[:3]}")

# Open a test window and see what we actually get
win = pygame.display.set_mode((1280, 800), pygame.RESIZABLE)
actual = win.get_size()
print(f"\nRequested 1280×800, got: {actual[0]} × {actual[1]}")
print(f"Scale factor (guessed): {actual[0]/1280:.2f} × {actual[1]/800:.2f}")

# Check env variables relevant to Wayland/HiDPI
env_keys = [
    "GDK_SCALE", "GDK_DPI_SCALE", "QT_SCALE_FACTOR",
    "WAYLAND_DISPLAY", "DISPLAY", "XDG_SESSION_TYPE",
    "SDL_VIDEODRIVER", "SDL_SCALE", "WLR_SCALE",
    "XCURSOR_SIZE", "GDK_BACKEND",
]
print("\n=== Relevant env vars ===")
for k in env_keys:
    v = os.environ.get(k)
    if v:
        print(f"  {k}={v}")

pygame.quit()
print("\nPaste this output in the chat so we can set the right fix.")
