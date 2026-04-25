# resources.py - compatibility shim, real fonts are in ui.py
from cascadia.gui.ui import font as _f
def get_font(size, bold=False, italic=False): return _f(size, bold)
def get_title_font(size): return _f(size, bold=True)
WILDLIFE_ASCII = {"bear":"BR","elk":"EL","salmon":"SA","hawk":"HK","fox":"FX"}
HABITAT_LABELS = {"forest":"FOR","wetland":"WET","mountain":"MTN","prairie":"PRA","river":"RIV"}
