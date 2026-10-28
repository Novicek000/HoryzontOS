"""Pierwsze uruchomienie (po instalacji): okno pełnoekranowe ze stronami i dolnym paskiem przycisków."""
import os
import threading
import time

from PySide6.QtCore import QRect, QTimer, Qt, QUrl
from PySide6.QtWidgets import QApplication, QLabel, QStackedWidget, QWidget

from ..i18n import T
from ..setup import tasks
from ..ui import look
from . import pages as P
from .frame import BOT_H, TOP_H, ArrowButton, OobeBackground, SpeakerButton

MUSIC = "/usr/share/sounds/horyzontos/oobe.wav"


class Oobe(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HoryzontOS")
        self.scale = 1.0
        self.choices = {}
        self.online = False
        self.bg = OobeBackground(self)
        self.stack = QStackedWidget(self)
        self.stack.setStyleSheet(P.stylesheet())
        self.back = ArrowButton(T("&Wstecz", "&Back"), "left", self)
        self.skipb = ArrowButton(T("&Pomiń", "&Skip"), "none", self)
        self.next = ArrowButton(T("&Dalej", "&Next"), "right", self)
        for b in (self.back, self.skipb, self.next):
            b.setFont(look.font(15, True))
        self.back.clicked.connect(self.go_back)
        self.next.clicked.connect(lambda: self.go_next())
        self.skipb.clicked.connect(self.skip_page)
        self.speaker = SpeakerButton(self)
        self.speaker.toggled.connect(self._music_toggle)
        self.foot = QLabel("", self)
        self.foot.setFont(look.font(12))
        self.foot.setStyleSheet("color: #cfdcff")
        self.pages = [P.IntroPage(self), P.WelcomePage(self), P.AutoUpdatesPage(self),
                      P.NetChoicePage(self), P.NetworkPage(self), P.EthernetPage(self),
                      P.ThirdPartyPage(self), P.UpdatePage(self), P.UsersPage(self), P.FinishPage(self)]
        for pg in self.pages:
            pg.apply_fonts(1.0)
            self.stack.addWidget(pg)
        self.history = []
        self._music = None
        self._finishing = False

    def resizeEvent(self, e):
        w, h = self.width(), self.height()
        self.bg.setGeometry(self.rect())
        top, bot = int(h * TOP_H), int(h * BOT_H)
        mx = int(w * 0.11)
        self.stack.setGeometry(QRect(mx, top + int(h * 0.07), w - 2 * mx, h - top - bot - int(h * 0.1)))
        by = h - bot + (bot - 36) // 2
        x = w - 40
        for b in (self.next, self.skipb, self.back):
            b.adjustSize()
            sw = b.sizeHint().width()
            x -= sw
            b.setGeometry(x, by, sw, 36)
            x -= 22
        self.speaker.move(24, by + 3)
        self.foot.setGeometry(64, by, w // 2, 36)

    # ------------------------------------------------------------ muzyka
    def start_music(self):
        if not os.path.exists(MUSIC) or os.environ.get("HORYZONTOS_NO_MUSIC"):
            self.speaker.hide()
            return
        try:
            from PySide6.QtMultimedia import QSoundEffect
            s = QSoundEffect(self)
            s.setSource(QUrl.fromLocalFile(MUSIC))
            s.setLoopCount(-2)   # QSoundEffect::Infinite (PySide6 6.10 wymaga liczby)
            s.setVolume(0.45)
            s.play()
            self._music = s
        except Exception as ex:
            tasks.log("muzyka:", ex)
            self.speaker.hide()

    def _music_toggle(self, on):
        if self._music:
            self._music.setMuted(not on)

    # ------------------------------------------------------------ nawigacja
    def start(self):
        self.show_page(0)
        QTimer.singleShot(300, self.start_music)

    def current(self):
        return self.stack.currentWidget()

    def show_page(self, i):
        pg = self.pages[i]
        self.bg.show_logo = not isinstance(pg, P.IntroPage)
        self.bg.update()
        self.stack.setCurrentWidget(pg)
        pg.on_enter()
        self.refresh_buttons()
        if pg.focusWidget() is None:
            self.next.setFocus()

    def refresh_buttons(self):
        pg = self.current()
        intro = isinstance(pg, P.IntroPage)
        busy = pg.busy() or self._finishing
        for b in (self.back, self.next, self.skipb):
            b.setVisible(not intro)
        self.back.setVisible(not intro and pg.show_back and bool(self.history))
        self.skipb.setVisible(not intro and pg.can_skip and not (isinstance(pg, P.UpdatePage) and pg.state == "done"))
        self.next.setText(pg.next_text or T("&Dalej", "&Next"))
        self.next.setEnabled(not busy)
        self.back.setEnabled(not busy)
        self.skipb.setEnabled(not busy)
        self.resizeEvent(None)

    def go_next(self, force=False):
        pg = self.current()
        if not force:
            if pg.busy() or not pg.validate():
                self.refresh_buttons()
                return
        i = self.pages.index(pg)
        if i == len(self.pages) - 1:
            self.finish()
            return
        j = i + 1
        while j < len(self.pages) - 1 and self.pages[j].skip():
            j += 1
        if not isinstance(pg, P.IntroPage):
            self.history.append(i)
        self.show_page(j)

    def skip_page(self):
        pg = self.current()
        if hasattr(pg, "on_skip"):
            pg.on_skip()
        i = self.pages.index(pg)
        j = i + 1
        while j < len(self.pages) - 1 and self.pages[j].skip():
            j += 1
        self.history.append(i)
        self.show_page(j)

    def go_back(self):
        if self.history:
            self.show_page(self.history.pop())

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter) and self.next.isVisible() and self.next.isEnabled():
            self.go_next()
        else:
            super().keyPressEvent(e)

    # ------------------------------------------------------------ zakończenie
    def finish(self):
        self._finishing = True
        self.refresh_buttons()
        pg = self.current()
        pg.summary.setText(T("Proszę czekać, trwa zapisywanie ustawień i tworzenie kont...",
                             "Please wait while your settings are saved and accounts are created..."))
        c = self.choices

        def work():
            try:
                tasks.configure_updates(c.get("auto_updates", True))
                tp = c.get("third_party", {})
                upd = next(p for p in self.pages if isinstance(p, P.UpdatePage))
                if any(tp.values()) and upd.state != "done":
                    # bez aktualizacji (offline albo pominięte) — włączamy to, co da się włączyć
                    tasks.enable_third_party(tp.get("fedora"), tp.get("rpmfusion") and self.online,
                                             tp.get("flathub") and self.online, tp.get("codecs") and self.online,
                                             lambda l: None)
                created = tasks.create_users(c.get("users", []))
                tasks.finish_setup(created)
            except Exception as ex:
                import traceback
                tasks.log("BŁĄD zakończenia:", traceback.format_exc())
            self._done = True
        self._done = False
        threading.Thread(target=work, daemon=True).start()

        def check():
            if not self._done:
                QTimer.singleShot(300, check)
                return
            if self._music:
                self._music.stop()
            QApplication.instance().exit(0)
        QTimer.singleShot(500, check)
