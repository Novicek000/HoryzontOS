"""Tło graficznej części instalatora: ciemnoniebieskie pasy, logo, lista etapów po lewej,
szacowany czas, pasek postępu bieżącej czynności i plansze informacyjne."""
import time

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

from ..i18n import T
from ..ui import look

TOP = 52
BOTTOM = 46
LEFT = 186
DIALOG_W, DIALOG_H = 500, 395


def steps():
    return [T("Zbieranie informacji", "Collecting information"),
            T("Aktualizacja dynamiczna", "Dynamic Update"),
            T("Przygotowywanie instalacji", "Preparing installation"),
            T("Instalowanie systemu HoryzontOS", "Installing HoryzontOS"),
            T("Finalizowanie instalacji", "Finalizing installation")]


def boards():
    return [
        ("logo", T("Witamy w systemie HoryzontOS", "Welcome to HoryzontOS"),
         T("HoryzontOS łączy znajomy, klasyczny pulpit z nowoczesnym systemem Fedora Linux. Przycisk Start, "
           "pasek zadań, Mój komputer i Panel sterowania są tam, gdzie się ich spodziewasz — a pod spodem "
           "pracuje szybki i bezpieczny system.",
           "HoryzontOS combines a familiar, classic desktop with modern Fedora Linux. The Start button, the "
           "taskbar, My Computer and Control Panel are right where you expect them — with a fast and secure "
           "system underneath.")),
        ("updates", T("Zawsze aktualny", "Always up to date"),
         T("Horyzont Updates dba o aktualizacje systemu, programów oraz samego pulpitu i ekranu powitalnego. "
           "Możesz instalować je automatycznie albo tylko otrzymywać powiadomienia.",
           "Horyzont Updates keeps the system, your programs, the desktop and the welcome screen up to date. "
           "Install updates automatically or just get notified.")),
        ("programs", T("Programy od razu po instalacji", "Programs right after installation"),
         T("Kalkulator, Paint, WordPad, Notatnik, Saper, Pasjans, Odtwarzacz multimediów i przeglądarka Firefox "
           "czekają w menu Start. Tysiące kolejnych programów zainstalujesz z repozytoriów Fedory i Flathub.",
           "Calculator, Paint, WordPad, Notepad, Minesweeper, Solitaire, Media Player and the Firefox browser are "
           "waiting in the Start menu. Thousands more are available from Fedora and Flathub.")),
        ("network_wireless", T("W sieci w kilka chwil", "Online in moments"),
         T("Połącz się z siecią Wi-Fi albo przewodową jeszcze podczas pierwszej konfiguracji — system pobierze "
           "wtedy od razu najnowsze aktualizacje.",
           "Connect to Wi-Fi or a wired network during first-time setup and the system will download the latest "
           "updates right away.")),
        ("security", T("Bezpieczny z założenia", "Secure by design"),
         T("Zapora sieciowa, SELinux i oddzielne konta użytkowników chronią Twoje pliki. Zadania administracyjne "
           "wymagają potwierdzenia hasłem.",
           "A firewall, SELinux and separate user accounts protect your files. Administrative tasks require "
           "password confirmation.")),
        ("users", T("Każdy ma swój pulpit", "Everyone gets their own desktop"),
         T("Utwórz osobne konto dla każdego domownika. Ekran powitalny pokaże wszystkich użytkowników, a każdy "
           "będzie miał własne tapety, ustawienia i dokumenty.",
           "Create a separate account for everyone in the family. The welcome screen lists all users and each "
           "gets their own wallpaper, settings and documents.")),
    ]


class Billboard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_step = 3
        self.minutes = 30
        self.status = ""
        self.progress = None        # None = bez paska; 0..1
        self.show_boards = True
        self.board = 0
        self._t0 = time.monotonic()
        t = QTimer(self)
        t.timeout.connect(self._rotate)
        t.start(20000)

    def _rotate(self):
        self.board = (self.board + 1) % len(boards())
        self.update()

    def set_status(self, text, progress=None):
        self.status = text
        self.progress = progress
        self.update()

    def dialog_rect(self):
        w, h = self.width(), self.height()
        x = LEFT + max(0, (w - LEFT - DIALOG_W) // 2)
        x = min(x, max(LEFT, w - DIALOG_W - 10))
        y = TOP + max(0, (h - TOP - BOTTOM - DIALOG_H) // 2)
        return QRect(x, y, DIALOG_W, DIALOG_H)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), QColor(look.SETUP_BG))
        # delikatna poświata w środkowej części
        g = QRadialGradient(QPointF(w * 0.62, h * 0.42), max(w, h) * 0.6)
        g.setColorAt(0, QColor(130, 160, 240, 70))
        g.setColorAt(1, QColor(130, 160, 240, 0))
        p.fillRect(QRectF(0, TOP, w, h - TOP - BOTTOM), g)
        band = QColor(look.SETUP_BAND)
        p.fillRect(QRectF(0, 0, w, TOP), band)
        p.fillRect(QRectF(0, h - BOTTOM, w, BOTTOM), band)
        # cienkie jaśniejsze linie na styku pasów
        p.fillRect(QRectF(0, TOP, w, 1), QColor(255, 255, 255, 40))
        p.fillRect(QRectF(0, h - BOTTOM - 1, w, 1), QColor(0, 0, 0, 40))
        # logo
        look.draw_logo(p, QRectF(14, 7, 38, 38))
        look.draw_wordmark(p, 58, 9, 28)
        self._steps(p)
        if self.show_boards:
            self._board(p)

    def _steps(self, p):
        y = TOP + 26
        for i, name in enumerate(steps()):
            cx, cy = 26, y + 8
            done = i < self.current_step
            cur = i == self.current_step
            # pierścień
            p.setPen(QPen(QColor("#ffffff"), 1.4))
            if done:
                p.setBrush(QColor("#ffffff"))
                p.drawEllipse(QPointF(cx, cy), 8, 8)
                gg = QRadialGradient(QPointF(cx - 1.5, cy - 1.5), 6)
                gg.setColorAt(0, QColor("#8ff07f"))
                gg.setColorAt(1, QColor("#1e9a1a"))
                p.setPen(Qt.NoPen)
                p.setBrush(gg)
                p.drawEllipse(QPointF(cx, cy), 5, 5)
            elif cur:
                p.setBrush(QColor("#fff3e2"))
                p.drawEllipse(QPointF(cx, cy), 8, 8)
                p.setPen(QPen(QColor("#e58a2c"), 1.2))
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(QPointF(cx, cy), 6, 6)
            else:
                p.setBrush(QColor("#ffffff"))
                p.drawEllipse(QPointF(cx, cy), 8, 8)
            p.setFont(look.font(12, bold=done or cur))
            p.setPen(QColor("#ff9e3d") if cur else QColor("#ffffff"))
            ly = y - 1
            for line in self._wrap(p, name, LEFT - 48):
                p.drawText(QRect(42, ly, LEFT - 44, 16), Qt.AlignLeft | Qt.AlignVCenter, line)
                ly += 15
            y += 40
        y += 8
        p.setPen(QColor("#ffffff"))
        p.setFont(look.font(12, bold=True))
        if self.minutes is not None:
            txt = T("Instalacja zostanie ukończona za około:", "Setup will complete in approximately:")
            for line in self._wrap(p, txt, LEFT - 22):
                p.drawText(QRect(12, y, LEFT - 12, 16), Qt.AlignLeft | Qt.AlignVCenter, line)
                y += 15
            p.drawText(QRect(36, y, LEFT, 16), Qt.AlignLeft | Qt.AlignVCenter,
                       T(f"{self.minutes} min", f"{self.minutes} minutes"))
        # bieżąca czynność i pasek postępu (lewy dolny róg)
        if self.status:
            hh = self.height()
            p.setFont(look.font(11, bold=False))
            p.setPen(QColor("#ffffff"))
            p.drawText(QRect(12, hh - BOTTOM - 62, LEFT - 16, 30), Qt.AlignLeft | Qt.AlignBottom | Qt.TextWordWrap,
                       self.status)
            if self.progress is not None:
                self._bar(p, QRect(12, hh - BOTTOM - 26, LEFT - 22, 14), self.progress)

    @staticmethod
    def _wrap(p, text, width):
        fm = p.fontMetrics()
        lines, cur = [], ""
        for w in text.split():
            t = (cur + " " + w).strip()
            if fm.horizontalAdvance(t) <= width or not cur:
                cur = t
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    def _bar(self, p, r, frac):
        p.save()
        p.setRenderHint(QPainter.Antialiasing, False)
        p.fillRect(r, QColor("#ffffff"))
        p.setPen(QColor("#808080"))
        p.drawLine(r.topLeft(), r.topRight())
        p.drawLine(r.topLeft(), r.bottomLeft())
        p.setPen(QColor("#ffffff"))
        p.drawLine(r.bottomLeft(), r.bottomRight())
        inner = r.adjusted(2, 2, -1, -1)
        n = int(inner.width() * max(0, min(1, frac)))
        bw, gap = 6, 2
        x = inner.left()
        while x + bw <= inner.left() + n:
            p.fillRect(QRect(x, inner.top(), bw, inner.height()), QColor("#2f9a3a"))
            x += bw + gap
        p.restore()

    def _board(self, p):
        icon, title, text = boards()[self.board]
        w, h = self.width(), self.height()
        area = QRect(LEFT + 40, TOP + 40, w - LEFT - 80, h - TOP - BOTTOM - 80)
        aw = min(area.width(), 560)
        area = QRect(area.left() + (area.width() - aw) // 2, area.top(), aw, area.height())
        y = area.top() + area.height() // 6
        if icon == "logo":
            look.draw_logo(p, QRectF(area.left(), y, 72, 72))
        else:
            p.drawPixmap(QRect(area.left(), y, 72, 72), look.pixmap(icon, 72))
        p.setPen(QColor("#ffffff"))
        p.setFont(look.font(24, bold=True, fam=look.title_family()))
        p.drawText(QRect(area.left() + 92, y + 6, aw - 92, 64), Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, title)
        p.setFont(look.font(14))
        p.setPen(QColor("#eef3ff"))
        p.drawText(QRect(area.left() + 92, y + 84, aw - 92, area.height()), Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap,
                   text)
