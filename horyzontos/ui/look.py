"""Wspólny wygląd graficznych części instalatora: czcionki, klasyczna paleta, ikony Horyzontu."""
import glob
import os
import sys

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QIcon, QLinearGradient, QPainter, QPainterPath,
                           QPalette, QPen, QPixmap, QRadialGradient)
from PySide6.QtWidgets import QApplication, QStyleFactory

# kolory klasycznego okna dialogowego
FACE = "#d4d0c8"
TITLE_A = "#0a246a"
TITLE_B = "#a6caf0"
SETUP_BAND = "#00309c"
SETUP_BG = "#4b6ed6"

_family = None


def family():
    global _family
    if _family:
        return _family
    fams = set(QFontDatabase.families())
    if "Tahoma" not in fams:
        for d in ("/usr/share/wine/fonts", "/usr/share/fonts/wine-tahoma-fonts", "/usr/share/fonts/wine-tahoma",
                  "/usr/local/share/fonts"):
            for f in glob.glob(os.path.join(d, "[Tt]ahoma*.ttf")):
                QFontDatabase.addApplicationFont(f)
        fams = set(QFontDatabase.families())
    for c in ("Tahoma", "DejaVu Sans", "Noto Sans", "Liberation Sans"):
        if c in fams:
            _family = c
            return c
    _family = "Sans Serif"
    return _family


def font(px, bold=False, italic=False, fam=None):
    f = QFont(fam or family())
    f.setPixelSize(max(6, int(round(px))))
    f.setBold(bold)
    f.setItalic(italic)
    return f


def title_family():
    """Czcionka dużych nagłówków (pierwsze uruchomienie)."""
    fams = set(QFontDatabase.families())
    for c in ("Franklin Gothic Medium", "Trebuchet MS", "Liberation Sans", "Noto Sans", "DejaVu Sans"):
        if c in fams:
            return c
    return family()


def classic_palette():
    p = QPalette()
    face = QColor(FACE)
    p.setColor(QPalette.Window, face)
    p.setColor(QPalette.Button, face)
    p.setColor(QPalette.Base, QColor("#ffffff"))
    p.setColor(QPalette.AlternateBase, QColor("#f4f3ee"))
    p.setColor(QPalette.WindowText, QColor("#000000"))
    p.setColor(QPalette.ButtonText, QColor("#000000"))
    p.setColor(QPalette.Text, QColor("#000000"))
    p.setColor(QPalette.Light, QColor("#ffffff"))
    p.setColor(QPalette.Midlight, QColor(FACE))
    p.setColor(QPalette.Mid, QColor("#808080"))
    p.setColor(QPalette.Dark, QColor("#808080"))
    p.setColor(QPalette.Shadow, QColor("#404040"))
    p.setColor(QPalette.Highlight, QColor(TITLE_A))
    p.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    p.setColor(QPalette.ToolTipBase, QColor("#ffffe1"))
    p.setColor(QPalette.ToolTipText, QColor("#000000"))
    for role in (QPalette.WindowText, QPalette.ButtonText, QPalette.Text):
        p.setColor(QPalette.Disabled, role, QColor("#808080"))
    p.setColor(QPalette.Disabled, QPalette.Base, face)
    return p


def setup_qapp(app):
    st = QStyleFactory.create("Windows")
    if st:
        app.setStyle(st)
    app.setPalette(classic_palette())
    app.setFont(font(11))


# ------------------------------------------------------------------ ikony Horyzontu
_icons = None


def _horyzont_icons():
    global _icons
    if _icons is not None:
        return _icons
    _icons = False
    cands = [os.environ.get("HORYZONT_SRC", ""), "/usr/local/share/horyzont", "/usr/share/horyzont",
             "/repos/horyzontdesktop", os.path.expanduser("~/novicek000/horyzontdesktop")]
    for c in cands:
        if c and os.path.isdir(os.path.join(c, "horyzont", "theme")):
            if c not in sys.path:
                sys.path.append(c)
            try:
                from horyzont.theme import icons as I
                _icons = I
            except Exception:
                _icons = False
            break
    return _icons


def icon_svg(name):
    I = _horyzont_icons()
    if I:
        try:
            return I.svg_for(name)
        except Exception:
            return None
    return None


_pmcache = {}


def pixmap(name, size, dpr=None):
    """Ikona Horyzontu jako QPixmap (z zapasowym rysunkiem, gdy Horyzontu nie ma)."""
    dpr = dpr or (QApplication.instance().devicePixelRatio() if QApplication.instance() else 1)
    key = (name, size, dpr)
    if key in _pmcache:
        return _pmcache[key]
    from PySide6.QtSvg import QSvgRenderer
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.fill(Qt.transparent)
    svg = icon_svg(name)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    if svg:
        r = QSvgRenderer(QByteArray(svg.encode()))
        r.render(p, QRectF(0, 0, size * dpr, size * dpr))
    else:
        draw_logo(p, QRectF(0, 0, size * dpr, size * dpr)) if name == "logo" else _fallback(p, size * dpr)
    p.end()
    pm.setDevicePixelRatio(dpr)
    _pmcache[key] = pm
    return pm


def _fallback(p, s):
    p.setBrush(QColor("#5b85d8"))
    p.setPen(QPen(QColor("#1d3f8a"), max(1, s / 24)))
    p.drawRoundedRect(QRectF(s * 0.12, s * 0.12, s * 0.76, s * 0.76), s * 0.12, s * 0.12)


def draw_logo(p, rect):
    """Słońce Horyzontu (oryginalne logo) — rysowane bez SVG."""
    import math
    cx, cy = rect.center().x(), rect.center().y()
    r = min(rect.width(), rect.height()) / 2
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor("#ffcf4a"), r * 0.13)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    for i in range(12):
        a = math.pi * 2 * i / 12
        p.drawLine(cx + math.cos(a) * r * 0.62, cy + math.sin(a) * r * 0.62,
                   cx + math.cos(a) * r * 0.98, cy + math.sin(a) * r * 0.98)
    g = QRadialGradient(cx - r * 0.1, cy - r * 0.1, r * 0.6)
    g.setColorAt(0, QColor("#fff6c8"))
    g.setColorAt(0.5, QColor("#ffc13a"))
    g.setColorAt(1, QColor("#e8701c"))
    p.setBrush(g)
    p.setPen(QPen(QColor("#b8501a"), max(0.6, r * 0.04)))
    p.drawEllipse(QRectF(cx - r * 0.5, cy - r * 0.5, r, r))
    p.setPen(QPen(QColor(255, 255, 255, 215), r * 0.07))
    p.drawLine(cx - r * 0.5, cy + r * 0.12, cx + r * 0.5, cy + r * 0.12)
    p.setPen(QPen(QColor(255, 255, 255, 165), r * 0.06))
    p.drawLine(cx - r * 0.42, cy + r * 0.27, cx + r * 0.42, cy + r * 0.27)
    p.restore()


def draw_wordmark(p, x, y, h, color="#ffffff", small=False):
    """Napis „Horyzont” z pomarańczowym „OS” w indeksie górnym. Zwraca szerokość."""
    p.save()
    f = font(h, bold=True, fam=title_family())
    f.setLetterSpacing(QFont.PercentageSpacing, 97)
    p.setFont(f)
    p.setPen(QColor(color))
    fm = p.fontMetrics()
    p.drawText(int(x), int(y + fm.ascent()), "Horyzont")
    w = fm.horizontalAdvance("Horyzont")
    f2 = font(h * 0.55, bold=True, italic=True, fam=title_family())
    p.setFont(f2)
    p.setPen(QColor("#ff9a1f"))
    p.drawText(int(x + w + h * 0.06), int(y + p.fontMetrics().ascent() - h * 0.02), "OS")
    w2 = p.fontMetrics().horizontalAdvance("OS")
    p.restore()
    return w + h * 0.06 + w2


def vgrad(rect, stops):
    g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    for pos, c in stops:
        g.setColorAt(pos, QColor(c))
    return g


def hgrad(rect, stops):
    g = QLinearGradient(rect.topLeft(), rect.topRight())
    for pos, c in stops:
        g.setColorAt(pos, QColor(c))
    return g
