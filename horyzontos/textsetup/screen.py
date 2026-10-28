"""„Tryb tekstowy” instalatora: siatka znaków rysowana czcionką konsoli VGA (PSF) przez Qt.

Dzięki temu wygląd jest taki sam na każdym ekranie (80×30 znaków jak w klasycznym instalatorze,
na szerszych ekranach więcej kolumn), a polskie litery i ramki zawsze są dostępne."""
import os

from PySide6.QtCore import QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QWidget

from .psf import PSFFont

VGA = ["#000000", "#0000aa", "#00aa00", "#00aaaa", "#aa0000", "#aa00aa", "#aa5500", "#aaaaaa",
       "#555555", "#5555ff", "#55ff55", "#55ffff", "#ff5555", "#ff55ff", "#ffff55", "#ffffff"]
(BLACK, BLUE, GREEN, CYAN, RED, MAGENTA, BROWN, GRAY,
 DGRAY, LBLUE, LGREEN, LCYAN, LRED, LMAGENTA, YELLOW, WHITE) = range(16)

FONT_DIRS = ["/usr/lib/kbd/consolefonts", "/usr/share/kbd/consolefonts",
             os.path.join(os.path.dirname(__file__), "fonts")]
# kolejność: klasyczna czcionka VGA, potem warianty z polskimi literami w tym samym stylu
FONT_CHAIN = ["default8x16.psfu.gz", "lat2-16.psfu.gz", "lat2-sun16.psfu.gz", "eurlatgr.psfu.gz",
              "LatArCyrHeb-16.psfu.gz"]

_fonts = None


def fonts():
    global _fonts
    if _fonts is None:
        _fonts = []
        extra = os.environ.get("HORYZONTOS_FONT_DIR")
        dirs = ([extra] if extra else []) + FONT_DIRS
        for name in FONT_CHAIN:
            for d in dirs:
                p = os.path.join(d, name)
                if os.path.exists(p):
                    try:
                        f = PSFFont(p)
                        if f.w == 8 and f.h == 16:
                            _fonts.append(f)
                    except (OSError, ValueError):
                        pass
                    break
        if not _fonts:
            raise RuntimeError("Brak czcionek konsoli (pakiet kbd).")
    return _fonts


def glyph_bits(ch):
    for f in fonts():
        b = f.bitmap(ch)
        if b is not None:
            return b
    for f in fonts():
        b = f.bitmap("?")
        if b is not None:
            return b
    return [0] * 16


class Grid:
    """Bufor znaków: każda komórka to [znak, kolor_tekstu, kolor_tła]."""

    def __init__(self, cols=80, rows=30):
        self.cols, self.rows = cols, rows
        self.cells = [[" ", GRAY, BLUE] for _ in range(cols * rows)]
        self.cursor = None          # (x, y) migającego kursora albo None

    def clear(self, fg=GRAY, bg=BLUE):
        for c in self.cells:
            c[0], c[1], c[2] = " ", fg, bg
        self.cursor = None

    def put(self, x, y, text, fg=GRAY, bg=BLUE):
        if y < 0 or y >= self.rows:
            return
        for i, ch in enumerate(text):
            xx = x + i
            if 0 <= xx < self.cols:
                c = self.cells[y * self.cols + xx]
                c[0], c[1], c[2] = ch, fg, bg

    def fill(self, x, y, w, h, ch=" ", fg=GRAY, bg=BLUE):
        for yy in range(y, y + h):
            self.put(x, yy, ch * w, fg, bg)

    def box(self, x, y, w, h, fg=GRAY, bg=BLUE, double=False, fill=True):
        if double:
            tl, tr, bl, br, hz, vt = "╔", "╗", "╚", "╝", "═", "║"
        else:
            tl, tr, bl, br, hz, vt = "┌", "┐", "└", "┘", "─", "│"
        self.put(x, y, tl + hz * (w - 2) + tr, fg, bg)
        for yy in range(y + 1, y + h - 1):
            self.put(x, yy, vt, fg, bg)
            if fill:
                self.put(x + 1, yy, " " * (w - 2), fg, bg)
            self.put(x + w - 1, yy, vt, fg, bg)
        self.put(x, y + h - 1, bl + hz * (w - 2) + br, fg, bg)

    def center(self, y, text, fg=GRAY, bg=BLUE, x0=0, width=None):
        width = width or self.cols
        self.put(x0 + max(0, (width - len(text)) // 2), y, text, fg, bg)

    def text(self):
        """Zawartość jako zwykły tekst (do testów)."""
        return "\n".join("".join(self.cells[y * self.cols + x][0] for x in range(self.cols)).rstrip()
                         for y in range(self.rows))


class TextView(QWidget):
    keyPressed = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid = Grid()
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.BlankCursor)
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self._cache = {}
        self._img = None
        self._blink = True
        self._t = QTimer(self)
        self._t.timeout.connect(self._toggle)
        self._t.start(260)
        self.fixed_size = None      # (cols, rows) — wymuszony rozmiar (testy)

    # rozmiar siatki dopasowany do proporcji ekranu: 30 wierszy, 80+ kolumn
    def grid_size_for(self, w, h):
        if self.fixed_size:
            return self.fixed_size
        rows = 30
        if h < 400:
            rows = 25
        cols = int(round(w / max(1, h) * rows * 2))
        return max(80, min(160, cols)), rows

    def resizeEvent(self, e):
        cols, rows = self.grid_size_for(self.width(), self.height())
        if (cols, rows) != (self.grid.cols, self.grid.rows):
            self.grid = Grid(cols, rows)
            self.on_grid_resized()
        super().resizeEvent(e)

    def on_grid_resized(self):
        pass

    def _toggle(self):
        self._blink = not self._blink
        if self.grid.cursor:
            self.update()

    def _glyph(self, ch, fg, bg):
        key = (ch, fg, bg)
        img = self._cache.get(key)
        if img is None:
            bits = glyph_bits(ch)
            f = QColor(VGA[fg]).rgb()
            b = QColor(VGA[bg]).rgb()
            img = QImage(8, 16, QImage.Format_RGB32)
            for y, row in enumerate(bits[:16]):
                for x in range(8):
                    img.setPixel(x, y, f if row & (0x80 >> x) else b)
            self._cache[key] = img
        return img

    def render_image(self):
        g = self.grid
        img = QImage(g.cols * 8, g.rows * 16, QImage.Format_RGB32)
        p = QPainter(img)
        for y in range(g.rows):
            for x in range(g.cols):
                ch, fg, bg = g.cells[y * g.cols + x]
                p.drawImage(x * 8, y * 16, self._glyph(ch, fg, bg))
        if g.cursor and self._blink:
            cx, cy = g.cursor
            if 0 <= cx < g.cols and 0 <= cy < g.rows:
                fg = g.cells[cy * g.cols + cx][1]
                p.fillRect(cx * 8, cy * 16 + 12, 8, 3, QColor(VGA[fg]))
        p.end()
        return img

    def paintEvent(self, e):
        img = self.render_image()
        p = QPainter(self)
        sx = self.width() / img.width()
        sy = self.height() / img.height()
        smooth = abs(sx - round(sx)) > 0.01 or abs(sy - round(sy)) > 0.01
        p.setRenderHint(QPainter.SmoothPixmapTransform, smooth)
        p.drawImage(QRectF(self.rect()), img, QRectF(img.rect()))
        p.end()

    def keyPressEvent(self, e):
        k = e.key()
        names = {Qt.Key_Return: "ENTER", Qt.Key_Enter: "ENTER", Qt.Key_Escape: "ESC", Qt.Key_Up: "UP",
                 Qt.Key_Down: "DOWN", Qt.Key_Left: "LEFT", Qt.Key_Right: "RIGHT", Qt.Key_PageUp: "PGUP",
                 Qt.Key_PageDown: "PGDN", Qt.Key_Home: "HOME", Qt.Key_End: "END", Qt.Key_Backspace: "BACKSPACE",
                 Qt.Key_Delete: "DEL", Qt.Key_Tab: "TAB"}
        if Qt.Key_F1 <= k <= Qt.Key_F12:
            name = f"F{k - Qt.Key_F1 + 1}"
        else:
            name = names.get(k, "")
        txt = e.text() if e.text() and e.text().isprintable() else ""
        if not name and txt:
            name = txt.upper()
        if name:
            self.keyPressed.emit(name, txt)
