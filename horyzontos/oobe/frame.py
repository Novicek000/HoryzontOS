"""Wygląd pierwszego uruchomienia: pełnoekranowe tło z pasami, logo, tytuł strony i przyciski
„Wstecz” / „Pomiń” / „Dalej” z zielonymi strzałkami na dolnym pasku."""
import math
import os

from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF,
                           QRadialGradient)
from PySide6.QtWidgets import QAbstractButton, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..i18n import T
from ..ui import look

BAND = "#00309c"
MID = "#5a7edc"
TOP_H = 0.11
BOT_H = 0.12


def wfont(px, bold=False):
    return look.font(px, bold)


class ArrowButton(QAbstractButton):
    """Napis + zielone kółko ze strzałką (w lewo / w prawo) albo bez strzałki."""

    def __init__(self, text, direction="right", parent=None):
        super().__init__(parent)
        self.setText(text)
        self.direction = direction
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self._hover = False

    def sizeHint(self):
        fm = self.fontMetrics()
        return QSize(fm.horizontalAdvance(self.text().replace("&", "")) + 46, 34)

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        en = self.isEnabled()
        r = self.rect()
        d = 26
        txt = self.text().replace("&", "")
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(txt)
        if self.direction == "left":
            circle = QRectF(2, (r.height() - d) / 2, d, d)
            tx = circle.right() + 8
        else:
            tx = 4
            circle = QRectF(tx + tw + 8, (r.height() - d) / 2, d, d)
        p.setPen(QColor("#ffffff") if en else QColor(255, 255, 255, 110))
        f = p.font()
        f.setUnderline(self._hover and en or self.hasFocus())
        p.setFont(f)
        p.drawText(QRectF(tx, 0, tw + 4, r.height()), Qt.AlignVCenter | Qt.AlignLeft, txt)
        if self.direction in ("left", "right"):
            g = QRadialGradient(circle.center() - QPointF(d * 0.18, d * 0.22), d * 0.7)
            if en:
                g.setColorAt(0, QColor("#c8f7a8"))
                g.setColorAt(0.45, QColor("#4fbf3a"))
                g.setColorAt(1, QColor("#1f7a1c"))
            else:
                g.setColorAt(0, QColor("#c9d3e8"))
                g.setColorAt(1, QColor("#7d8db3"))
            p.setBrush(g)
            p.setPen(QPen(QColor(255, 255, 255, 220), 1.6))
            p.drawEllipse(circle)
            c = circle.center()
            s = d * 0.22
            if self.direction == "right":
                poly = [c + QPointF(-s * 1.1, -s * 0.45), c + QPointF(0, -s * 0.45), c + QPointF(0, -s * 1.15),
                        c + QPointF(s * 1.25, 0), c + QPointF(0, s * 1.15), c + QPointF(0, s * 0.45),
                        c + QPointF(-s * 1.1, s * 0.45)]
            else:
                poly = [c + QPointF(s * 1.1, -s * 0.45), c + QPointF(0, -s * 0.45), c + QPointF(0, -s * 1.15),
                        c + QPointF(-s * 1.25, 0), c + QPointF(0, s * 1.15), c + QPointF(0, s * 0.45),
                        c + QPointF(s * 1.1, s * 0.45)]
            p.setBrush(QColor("#ffffff"))
            p.setPen(Qt.NoPen)
            p.drawPolygon(QPolygonF(poly))

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.click()
        else:
            super().keyPressEvent(e)


class SpeakerButton(QAbstractButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(True)
        self.setFixedSize(30, 30)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(T("Muzyka: włącz / wyłącz", "Music: on / off"))

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor("#ffffff"), 1.5))
        p.setBrush(QColor("#ffffff"))
        body = QPolygonF([QPointF(6, 12), QPointF(11, 12), QPointF(17, 6), QPointF(17, 24), QPointF(11, 18),
                          QPointF(6, 18)])
        p.drawPolygon(body)
        p.setBrush(Qt.NoBrush)
        if self.isChecked():
            p.drawArc(QRectF(14, 9, 8, 12), -60 * 16, 120 * 16)
            p.drawArc(QRectF(14, 5, 13, 20), -60 * 16, 120 * 16)
        else:
            p.setPen(QPen(QColor("#ff8a7a"), 2))
            p.drawLine(QPointF(20, 10), QPointF(27, 20))
            p.drawLine(QPointF(27, 10), QPointF(20, 20))


class OobeBackground(QWidget):
    """Tło całego ekranu (pasy, poświata, logo)."""

    show_logo = True

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        top, bot = int(h * TOP_H), int(h * BOT_H)
        mid = QRectF(0, top, w, h - top - bot)
        g = QLinearGradient(mid.topLeft(), mid.bottomLeft())
        g.setColorAt(0, QColor("#6d8fe6"))
        g.setColorAt(1, QColor("#4c70d4"))
        p.fillRect(mid, g)
        rg = QRadialGradient(QPointF(w * 0.18, top + h * 0.06), w * 0.55)
        rg.setColorAt(0, QColor(214, 228, 255, 150))
        rg.setColorAt(0.5, QColor(170, 195, 250, 50))
        rg.setColorAt(1, QColor(150, 180, 245, 0))
        p.fillRect(mid, rg)
        p.fillRect(QRectF(0, 0, w, top), QColor(BAND))
        p.fillRect(QRectF(0, h - bot, w, bot), QColor(BAND))
        # jasne linie na styku pasów
        lg = QLinearGradient(0, 0, w, 0)
        lg.setColorAt(0, QColor(255, 255, 255, 0))
        lg.setColorAt(0.35, QColor(255, 255, 255, 170))
        lg.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillRect(QRectF(0, top - 2, w, 2), lg)
        lg2 = QLinearGradient(0, 0, w, 0)
        lg2.setColorAt(0, QColor(255, 160, 60, 0))
        lg2.setColorAt(0.5, QColor(255, 170, 70, 200))
        lg2.setColorAt(1, QColor(255, 160, 60, 0))
        p.fillRect(QRectF(0, h - bot, w, 2), lg2)
        # logo w prawym górnym rogu części środkowej
        if not self.show_logo:
            return
        lh = max(28, h * 0.05)
        look.draw_logo(p, QRectF(w - lh * 6.4, top + lh * 0.55, lh * 1.25, lh * 1.25))
        look.draw_wordmark(p, w - lh * 5.0, top + lh * 0.6, lh * 0.95)


class OobePage(QWidget):
    """Strona: tytuł + treść. Podklasy wypełniają self.content (QVBoxLayout)."""

    title = ""
    can_skip = False
    next_text = None
    show_back = True

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setAttribute(Qt.WA_TranslucentBackground)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.title_lab = QLabel(self.title)
        self.title_lab.setWordWrap(True)
        self.title_lab.setStyleSheet("color: white;")
        outer.addWidget(self.title_lab)
        outer.addSpacing(14)
        self.content = QVBoxLayout()
        self.content.setSpacing(10)
        outer.addLayout(self.content, 1)

    def set_title(self, t):
        self.title = t
        self.title_lab.setText(t)

    def apply_fonts(self, scale):
        f = look.font(30 * scale, fam=look.title_family())
        self.title_lab.setFont(f)

    def resizeEvent(self, e):
        # tytuł nie może wchodzić pod logo w prawym górnym rogu
        self.title_lab.setMaximumWidth(max(200, int(self.width() * 0.72)))
        super().resizeEvent(e)

    def text(self, t, size=14, bold=False, color="white"):
        l = QLabel(t)
        l.setWordWrap(True)
        l.setFont(look.font(size * self.app.scale, bold))
        l.setStyleSheet(f"color: {color};")
        l.setTextFormat(Qt.PlainText if "<" not in t else Qt.RichText)
        self.content.addWidget(l)
        return l

    # zachowanie
    def on_enter(self):
        pass

    def validate(self):
        return True

    def skip(self):
        return False

    def busy(self):
        return False
