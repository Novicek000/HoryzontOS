"""Klasyczne okno kreatora instalatora: pasek tytułu z gradientem, biały nagłówek z ikoną,
strony i przyciski „< Wstecz” / „Dalej >” na dole."""
from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QStackedWidget,
                               QVBoxLayout, QWidget)

from ..i18n import T
from . import look

TITLE_H = 18
HEADER_H = 58


class Page(QWidget):
    """Strona kreatora. Podklasy ustawiają title/subtitle/icon i budują self.body (QVBoxLayout)."""

    title = ""
    subtitle = ""
    icon = "wizard"

    def __init__(self, wizard):
        super().__init__()
        self.wizard = wizard
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(24, 14, 24, 8)
        self.body.setSpacing(8)

    def on_enter(self):
        pass

    def validate(self):
        """Wywoływane po „Dalej”. False = zostań na stronie."""
        return True

    def can_back(self):
        return True

    # pomocnicze
    def label(self, text, wrap=True, bold=False):
        l = QLabel(text)
        l.setWordWrap(wrap)
        if bold:
            l.setFont(look.font(11, bold=True))
        self.body.addWidget(l)
        return l


class _TitleBar(QWidget):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.text = text
        self.setFixedHeight(TITLE_H)

    def paintEvent(self, e):
        p = QPainter(self)
        r = QRectF(self.rect())
        p.fillRect(r, look.hgrad(r, [(0, look.TITLE_A), (1, look.TITLE_B)]))
        p.setFont(look.font(11, bold=True))
        p.setPen(QColor("#ffffff"))
        p.drawText(r.adjusted(3, 0, -24, 0), Qt.AlignVCenter | Qt.AlignLeft, self.text)
        # przycisk zamknięcia (nieaktywny, jak w instalatorze)
        b = QRectF(r.right() - 18, 2, 16, 14)
        p.fillRect(b, QColor(look.FACE))
        p.setPen(QColor("#ffffff"))
        p.drawLine(b.topLeft(), b.topRight())
        p.drawLine(b.topLeft(), b.bottomLeft())
        p.setPen(QColor("#404040"))
        p.drawLine(b.bottomLeft(), b.bottomRight())
        p.drawLine(b.topRight(), b.bottomRight())
        p.setPen(QColor("#808080"))
        p.drawLine(b.bottomLeft() + QPointF(1, -1), b.bottomRight() + QPointF(-1, -1))
        p.drawLine(b.topRight() + QPointF(-1, 1), b.bottomRight() + QPointF(-1, -1))
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor("#ffffff"), 1.6)
        p.setPen(pen)
        c = b.center() + QPointF(1, 1)
        p.drawLine(c + QPointF(-3.5, -3), c + QPointF(3.5, 3))
        p.drawLine(c + QPointF(3.5, -3), c + QPointF(-3.5, 3))
        pen.setColor(QColor("#808080"))
        p.setPen(pen)
        c = b.center()
        p.drawLine(c + QPointF(-3.5, -3), c + QPointF(3.5, 3))
        p.drawLine(c + QPointF(3.5, -3), c + QPointF(-3.5, 3))


class _Header(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title = ""
        self.subtitle = ""
        self.icon = "wizard"
        self.setFixedHeight(HEADER_H)

    def set(self, title, subtitle, icon):
        self.title, self.subtitle, self.icon = title, subtitle, icon
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        r = self.rect()
        p.fillRect(r, QColor("#ffffff"))
        p.setPen(QColor("#808080"))
        p.drawLine(0, r.height() - 2, r.width(), r.height() - 2)
        p.setPen(QColor("#ffffff"))
        p.drawLine(0, r.height() - 1, r.width(), r.height() - 1)
        p.setPen(QColor("#000000"))
        p.setFont(look.font(11, bold=True))
        p.drawText(QRect(22, 9, r.width() - 110, 16), Qt.AlignLeft | Qt.AlignVCenter, self.title)
        p.setFont(look.font(11))
        p.drawText(QRect(44, 25, r.width() - 120, 30), Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, self.subtitle)
        # ikona w ciemnym kwadracie (jak obrazek kreatora)
        box = QRect(r.width() - 60, 4, 49, 49)
        p.fillRect(box, QColor("#0b1c4a"))
        p.drawPixmap(box.adjusted(4, 4, -4, -4), look.pixmap(self.icon, 41))


class _Etched(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(2)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setPen(QColor("#808080"))
        p.drawLine(0, 0, self.width(), 0)
        p.setPen(QColor("#ffffff"))
        p.drawLine(0, 1, self.width(), 1)


class ClassicWizard(QFrame):
    """Okno kreatora (bez dekoracji systemowych — rysowane samodzielnie)."""

    finished = Signal()

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(0)
        self.titlebar = _TitleBar(title)
        lay.addWidget(self.titlebar)
        lay.addSpacing(1)
        self.header = _Header()
        lay.addWidget(self.header)
        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)
        lay.addWidget(_Etched())
        foot = QHBoxLayout()
        foot.setContentsMargins(10, 10, 10, 10)
        foot.setSpacing(0)
        foot.addStretch(1)
        self.back = QPushButton(T("< &Wstecz", "< &Back"))
        self.next = QPushButton(T("&Dalej >", "&Next >"))
        for b in (self.back, self.next):
            b.setFixedSize(75, 23)
        foot.addWidget(self.back)
        foot.addWidget(self.next)
        lay.addLayout(foot)
        self.back.clicked.connect(self.go_back)
        self.next.clicked.connect(self.go_next)
        self.next.setDefault(True)
        self.pages = []
        self.history = []
        self.on_done = None

    def paintEvent(self, e):
        p = QPainter(self)
        r = self.rect()
        p.fillRect(r, QColor(look.FACE))
        # klasyczna wypukła ramka okna (2 px)
        p.setPen(QColor(look.FACE))
        p.drawLine(0, 0, r.width() - 2, 0)
        p.drawLine(0, 0, 0, r.height() - 2)
        p.setPen(QColor("#ffffff"))
        p.drawLine(1, 1, r.width() - 3, 1)
        p.drawLine(1, 1, 1, r.height() - 3)
        p.setPen(QColor("#808080"))
        p.drawLine(1, r.height() - 2, r.width() - 2, r.height() - 2)
        p.drawLine(r.width() - 2, 1, r.width() - 2, r.height() - 2)
        p.setPen(QColor("#404040"))
        p.drawLine(0, r.height() - 1, r.width() - 1, r.height() - 1)
        p.drawLine(r.width() - 1, 0, r.width() - 1, r.height() - 1)

    def set_pages(self, pages):
        for pg in self.pages:
            self.stack.removeWidget(pg)
        self.pages = pages
        for pg in pages:
            self.stack.addWidget(pg)
        self.history = []

    def show_page(self, idx):
        pg = self.pages[idx]
        self.stack.setCurrentWidget(pg)
        self.header.set(pg.title, pg.subtitle, pg.icon)
        self.back.setEnabled(bool(self.history) and pg.can_back())
        self.next.setFocus()
        self.next.setDefault(True)
        pg.on_enter()

    def current_index(self):
        return self.pages.index(self.stack.currentWidget())

    def keyPressEvent(self, e):
        # Enter w polu tekstowym = przycisk domyślny „Dalej >” (jak w oknach dialogowych)
        if e.key() in (Qt.Key_Return, Qt.Key_Enter) and self.next.isEnabled() and self.next.isVisible():
            self.next.click()
            return
        super().keyPressEvent(e)

    def start(self, idx=0):
        self.history = []
        self.show_page(idx)

    def go_next(self):
        pg = self.stack.currentWidget()
        if not pg.validate():
            return
        idx = self.current_index()
        nxt = idx + 1
        while nxt < len(self.pages) and getattr(self.pages[nxt], "skip", lambda: False)():
            nxt += 1
        if nxt >= len(self.pages):
            if self.on_done:
                self.on_done()
            return
        self.history.append(idx)
        self.show_page(nxt)

    def go_back(self):
        if self.history:
            self.show_page(self.history.pop())

    def retitle(self, text):
        self.titlebar.text = text
        self.titlebar.update()
        self.back.setText(T("< &Wstecz", "< &Back"))
        self.next.setText(T("&Dalej >", "&Next >"))


class ClassicFrame(QFrame):
    """Klasyczne okno z paskiem tytułu (do okien pomocniczych: Dostosuj, Właściwości…)."""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(0)
        self.titlebar = _TitleBar(title)
        lay.addWidget(self.titlebar)
        inner = QWidget()
        self.body = QVBoxLayout(inner)
        self.body.setContentsMargins(11, 11, 11, 11)
        self.body.setSpacing(8)
        lay.addWidget(inner, 1)

    paintEvent = ClassicWizard.paintEvent


class _Overlay(QWidget):
    """Przezroczysta warstwa blokująca okno pod spodem, gdy otwarte jest okienko pomocnicze."""

    def __init__(self, top):
        super().__init__(top)
        self.setGeometry(top.rect())
        self.setAttribute(Qt.WA_NoSystemBackground)

    def paintEvent(self, e):
        pass

    def mousePressEvent(self, e):
        e.accept()


def _run_overlay(parent, frame, default_btn=None):
    """Pokazuje frame na środku okna nadrzędnego i czeka na zamknięcie (lokalna pętla zdarzeń)."""
    from PySide6.QtCore import QEventLoop
    top = parent.window()
    ov = _Overlay(top)
    frame.setParent(ov)
    frame.adjustSize()
    frame.move(top.rect().center() - frame.rect().center())
    ov.show()
    frame.show()
    ov.raise_()
    loop = QEventLoop()
    frame.result = None
    frame._loop = loop
    if default_btn:
        default_btn.setFocus()
    loop.exec()
    ov.hide()
    ov.deleteLater()
    return frame.result


def _close(frame, value):
    frame.result = value
    frame._loop.quit()


def message(parent, title, text, icon="warning"):
    """Proste klasyczne okienko komunikatu (modalne)."""
    frame = ClassicFrame(title)
    row = QHBoxLayout()
    ic = QLabel()
    ic.setPixmap(look.pixmap(icon, 32))
    ic.setAlignment(Qt.AlignTop)
    row.addWidget(ic)
    row.addSpacing(8)
    lab = QLabel(text)
    lab.setWordWrap(True)
    lab.setMinimumWidth(320)
    row.addWidget(lab, 1)
    frame.body.addLayout(row)
    btns = QHBoxLayout()
    btns.addStretch(1)
    ok = QPushButton("OK")
    ok.setFixedSize(75, 23)
    ok.setDefault(True)
    ok.clicked.connect(lambda: _close(frame, True))
    btns.addWidget(ok)
    btns.addStretch(1)
    frame.body.addLayout(btns)
    return _run_overlay(parent, frame, ok)


def classic_dialog(parent, title, build, ok_text="OK", cancel=True):
    """Okno pomocnicze z treścią budowaną przez build(layout, frame). Zwraca True po OK."""
    frame = ClassicFrame(title)
    build(frame.body, frame)
    btns = QHBoxLayout()
    btns.addStretch(1)
    ok = QPushButton(ok_text)
    ok.setFixedSize(75, 23)
    ok.setDefault(True)
    ok.clicked.connect(lambda: _close(frame, True))
    btns.addWidget(ok)
    if cancel:
        c = QPushButton(T("Anuluj", "Cancel"))
        c.setFixedSize(75, 23)
        c.clicked.connect(lambda: _close(frame, False))
        btns.addSpacing(6)
        btns.addWidget(c)
    frame.body.addSpacing(4)
    frame.body.addLayout(btns)
    return bool(_run_overlay(parent, frame, ok))
