"""
ui.py - Dead-simple UI primitives. No tricks, no scaling.

Every element knows its own pygame.Rect.
Button click = rect.collidepoint(event.pos). That's it.
"""
import pygame

C = {
    "face":    (212, 208, 200),
    "white":   (255, 255, 255),
    "black":   (0,   0,   0),
    "title":   (0,   0,   128),
    "title_t": (255, 255, 255),
    "gray":    (128, 128, 128),
    "dgray":   (64,  64,  64),
    "sel":     (0,   0,   128),
    "sel_t":   (255, 255, 255),
    "hover_bg":(198, 212, 240),
    "muted":   (80,  80,  80),
    "desktop": (58,  110, 165),
}

def _font(size, bold=False):
    """Load the best available font at this size."""
    # Try filesystem TTF first (avoids pixelation on Linux)
    import os
    ttf_dirs = [
        "/usr/share/fonts/truetype/dejavu",
        "/usr/share/fonts/truetype/liberation",
        "/usr/share/fonts/truetype/freefont",
        "/run/current-system/sw/share/fonts",
        os.path.expanduser("~/.nix-profile/share/fonts"),
        "/usr/share/fonts/TTF",
        r"C:\Windows\Fonts",
        "/Library/Fonts",
    ]
    prefer_bold = ["DejaVuSans-Bold.ttf","LiberationSans-Bold.ttf","FreeSansBold.ttf"]
    prefer_reg  = ["DejaVuSans.ttf","LiberationSans-Regular.ttf","FreeSans.ttf"]
    want = prefer_bold if bold else prefer_reg
    for d in ttf_dirs:
        if not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            for name in want:
                if name in files:
                    try:
                        return pygame.font.Font(os.path.join(root, name), size)
                    except Exception:
                        pass
    # SysFont fallback
    for name in (["dejavusansbold","arialbold","sans"] if bold
                 else ["dejavusans","arial","liberationsans","freesans","sans"]):
        try:
            f = pygame.font.SysFont(name, size, bold=bold)
            if f: return f
        except Exception:
            pass
    return pygame.font.Font(None, size + 4)


# ── Module-level font cache ───────────────────────────────────────────────────
_FC = {}
def font(size, bold=False):
    k = (size, bold)
    if k not in _FC:
        _FC[k] = _font(size, bold)
    return _FC[k]


# ── Low-level draw helpers ────────────────────────────────────────────────────
def bevel(surf, rect, raised=True):
    x, y, w, h = rect
    lt = C["white"]  if raised else C["dgray"]
    rb = C["dgray"]  if raised else C["white"]
    m  = C["face"]   if raised else C["gray"]
    rm = C["gray"]   if raised else C["face"]
    pygame.draw.line(surf, lt, (x,     y),     (x+w-2, y))
    pygame.draw.line(surf, lt, (x,     y),     (x,     y+h-2))
    pygame.draw.line(surf, rb, (x,     y+h-1), (x+w-1, y+h-1))
    pygame.draw.line(surf, rb, (x+w-1, y),     (x+w-1, y+h-1))
    pygame.draw.line(surf, m,  (x+1,   y+1),   (x+w-3, y+1))
    pygame.draw.line(surf, m,  (x+1,   y+1),   (x+1,   y+h-3))
    pygame.draw.line(surf, rm, (x+1,   y+h-2), (x+w-2, y+h-2))
    pygame.draw.line(surf, rm, (x+w-2, y+1),   (x+w-2, y+h-2))

def txt(surf, text, fnt, col, x, y, cx=False, right=False):
    s = fnt.render(str(text), True, col)
    if cx:    x -= s.get_width() // 2
    if right: x -= s.get_width()
    surf.blit(s, (x, y))
    return s.get_width()

def hrule(surf, y, x1=0, x2=None, width=1280):
    if x2 is None: x2 = width
    pygame.draw.line(surf, C["gray"],  (x1, y),   (x2, y))
    pygame.draw.line(surf, C["white"], (x1, y+1), (x2, y+1))

def panel_box(surf, rect, sunken=False):
    pygame.draw.rect(surf, C["face"], rect)
    bevel(surf, rect, raised=not sunken)

def title_bar(surf, rect, label, fnt):
    pygame.draw.rect(surf, C["title"], rect)
    s = fnt.render(label, True, C["title_t"])
    surf.blit(s, (rect.x + 6, rect.y + (rect.h - s.get_height()) // 2))


# ── Widgets ───────────────────────────────────────────────────────────────────

class Button:
    """Reliable Win98 push button. Click = MOUSEBUTTONUP inside rect."""
    def __init__(self, rect, label, cb=None, fsize=14, bold=False):
        self.rect    = pygame.Rect(rect)
        self.label   = label
        self.cb      = cb
        self._font   = font(fsize, bold)
        self._down   = False   # currently held
        self.enabled = True

    def handle(self, ev):
        if not self.enabled:
            return False
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos):
                self._down = True
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            was = self._down
            self._down = False
            if was and self.rect.collidepoint(ev.pos):
                if self.cb: self.cb()
                return True
        return False

    def draw(self, surf):
        col = C["gray"] if not self.enabled else C["black"]
        pygame.draw.rect(surf, C["face"], self.rect)
        bevel(surf, self.rect, raised=not self._down)
        ox = oy = (1 if self._down else 0)
        s = self._font.render(self.label, True, col)
        surf.blit(s, (
            self.rect.x + (self.rect.w - s.get_width())  // 2 + ox,
            self.rect.y + (self.rect.h - s.get_height()) // 2 + oy,
        ))
        # dotted focus rect on hover
        mx, my = pygame.mouse.get_pos()
        if self.enabled and self.rect.collidepoint(mx, my):
            fr = self.rect.inflate(-6, -6)
            pygame.draw.rect(surf, C["black"], fr, 1)


class TextBox:
    """Single-line sunken text input."""
    def __init__(self, rect, text="", maxlen=22, fsize=14):
        self.rect    = pygame.Rect(rect)
        self.text    = text
        self.maxlen  = maxlen
        self._font   = font(fsize)
        self.focused = False

    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self.focused = self.rect.collidepoint(ev.pos)
        if ev.type == pygame.KEYDOWN and self.focused:
            if   ev.key == pygame.K_BACKSPACE: self.text = self.text[:-1]
            elif ev.unicode and len(self.text) < self.maxlen:
                self.text += ev.unicode

    def draw(self, surf):
        pygame.draw.rect(surf, C["white"], self.rect)
        bevel(surf, self.rect, raised=False)
        display = self.text + ("|" if self.focused and
                               (pygame.time.get_ticks()//500)%2==0 else "")
        s = self._font.render(display, True, C["black"])
        # clip text to box
        clip = surf.get_clip()
        surf.set_clip(self.rect.inflate(-4, -4))
        surf.blit(s, (self.rect.x + 4,
                      self.rect.y + (self.rect.h - s.get_height()) // 2))
        surf.set_clip(clip)


class Label:
    def __init__(self, x, y, text, fsize=13, bold=False, col=None):
        self.x = x; self.y = y; self.text = text
        self._font = font(fsize, bold)
        self._col  = col or C["black"]

    def draw(self, surf):
        txt(surf, self.text, self._font, self._col, self.x, self.y)


class ScrollList:
    """Scrollable list with word-wrapped lines and scroll."""
    PAD = 4

    def __init__(self, rect, items=None, fsize=13):
        self.rect    = pygame.Rect(rect)
        self._font   = font(fsize)
        self._lh     = self._font.get_height() + 3
        self._scroll = 0
        self.selected = -1
        self._raw    = []        # original items added
        self._lines  = []        # word-wrapped display lines
        self._inner_w = self.rect.w - self.PAD * 2 - 4   # usable text width
        for item in (items or []):
            self._add_item(item)

    def _wrap(self, text):
        """Word-wrap a string to fit inside _inner_w."""
        words   = str(text).split()
        lines   = []
        current = ""
        for word in words:
            test = (current + " " + word).strip()
            if self._font.size(test)[0] <= self._inner_w:
                current = test
            else:
                if current:
                    lines.append(current)
                # If single word is too long, truncate it
                while self._font.size(word)[0] > self._inner_w and len(word) > 1:
                    word = word[:-1]
                current = word
        if current:
            lines.append(current)
        return lines or [""]

    def _add_item(self, item):
        self._raw.append(item)
        self._lines.extend(self._wrap(item))

    @property
    def items(self):
        return self._raw

    @items.setter
    def items(self, value):
        self._raw   = []
        self._lines = []
        for v in value:
            self._add_item(v)
        self._scroll = 0

    def append(self, item):
        self._add_item(item)
        # auto-scroll to bottom
        vis = self._vis()
        if len(self._lines) > vis:
            self._scroll = len(self._lines) - vis

    def _vis(self):
        return max(1, (self.rect.h - self.PAD * 2) // self._lh)

    def handle(self, ev):
        if ev.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self._scroll = max(0, min(
                    self._scroll - ev.y,
                    max(0, len(self._lines) - self._vis())))
        return None

    def draw(self, surf):
        # Background + sunken border
        pygame.draw.rect(surf, C["white"], self.rect)
        bevel(surf, self.rect, raised=False)

        # Clip strictly to inner area
        inner = pygame.Rect(
            self.rect.x + 2,
            self.rect.y + 2,
            self.rect.w - 4,
            self.rect.h - 4,
        )
        clip = surf.get_clip()
        surf.set_clip(inner)

        for i, line in enumerate(self._lines[self._scroll:self._scroll + self._vis()]):
            ry = self.rect.y + self.PAD + i * self._lh
            # Render text — already guaranteed to fit in _inner_w by _wrap
            s = self._font.render(line, True, C["black"])
            surf.blit(s, (self.rect.x + self.PAD + 2, ry))

        surf.set_clip(clip)
