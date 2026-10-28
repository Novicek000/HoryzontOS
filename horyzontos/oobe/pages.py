"""Strony pierwszego uruchomienia („Witamy w systemie HoryzontOS”)."""
import json
import os
import threading
import time

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QProgressBar, QPushButton, QRadioButton, QWidget)

from ..i18n import T
from ..setup import tasks
from ..ui import look
from .frame import OobePage

CSS_BASE = """
QRadioButton, QCheckBox { color: white; spacing: 8px; }
QRadioButton:disabled, QCheckBox:disabled { color: #b8c7ee; }
QLabel { color: white; }
QLabel:disabled { color: #b8c7ee; }
QLineEdit { background: white; color: black; border: 1px solid #1d3f8a; padding: 3px; }
QLineEdit:disabled { background: #c9d6f2; color: #5a6b94; border: 1px solid #7f96cc; }
QListWidget { background: white; color: black; border: 1px solid #1d3f8a; }
QListWidget::item { padding: 4px; }
QListWidget::item:selected { background: #316ac5; color: white; }
QPushButton { padding: 3px 14px; }
"""


def _indicators():
    """Pola wyboru i przełączniki w stylu kreatora pierwszego uruchomienia (biały środek, zielony znacznik)."""
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QImage, QLinearGradient, QPainterPath
    d = os.path.join(os.environ.get("XDG_RUNTIME_DIR") or "/tmp", f"horyzontos-ind-{os.getuid()}")
    os.makedirs(d, exist_ok=True)
    css = []
    for kind in ("radio", "check"):
        for state in ("off", "on", "offd", "ond"):
            for sc, suf in ((1, ""), (2, "@2x"), (3, "@3x")):
                n = 13 * sc
                img = QImage(n, n, QImage.Format_ARGB32)
                img.fill(0)
                p = QPainter(img)
                p.setRenderHint(QPainter.Antialiasing)
                p.scale(sc, sc)
                dis = state.endswith("d")
                g = QLinearGradient(0, 0, 13, 13)
                g.setColorAt(0, QColor("#dcdcd7" if not dis else "#e8e8e8"))
                g.setColorAt(1, QColor("#ffffff" if not dis else "#f2f2f2"))
                p.setBrush(g)
                p.setPen(QPen(QColor("#1c5180" if not dis else "#9aa7c0"), 1))
                if kind == "radio":
                    p.drawEllipse(QRectF(0.5, 0.5, 12, 12))
                else:
                    p.drawRect(QRectF(0.5, 0.5, 12, 12))
                if state.startswith("on"):
                    col = QColor("#21a121" if not dis else "#9fc49f")
                    if kind == "radio":
                        rg = QLinearGradient(4, 4, 9, 9)
                        rg.setColorAt(0, QColor("#55d655" if not dis else "#b8d8b8"))
                        rg.setColorAt(1, col)
                        p.setBrush(rg)
                        p.setPen(Qt.NoPen)
                        p.drawEllipse(QRectF(3.5, 3.5, 6, 6))
                    else:
                        path = QPainterPath(QPointF(3, 6.2))
                        path.lineTo(5.4, 8.6)
                        path.lineTo(10, 3.8)
                        p.setPen(QPen(col, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                        p.setBrush(Qt.NoBrush)
                        p.drawPath(path)
                p.end()
                img.save(os.path.join(d, f"{kind}-{state}{suf}.png"))
        w = "QRadioButton" if kind == "radio" else "QCheckBox"
        for sel, st in (("unchecked", "off"), ("checked", "on"), ("unchecked:disabled", "offd"),
                        ("checked:disabled", "ond")):
            css.append(f"{w}::indicator:{sel} {{ image: url({d}/{kind}-{st}.png); width: 13px; height: 13px; }}")
    return "\n".join(css)


def stylesheet():
    try:
        return CSS_BASE + _indicators()
    except Exception as ex:
        tasks.log("wskaźniki:", ex)
        return CSS_BASE


CSS = CSS_BASE


class IntroPage(OobePage):
    """Krótka animacja: wschodzące słońce Horyzontu i napis."""

    show_back = False

    def __init__(self, app):
        super().__init__(app)
        self.t0 = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)

    def on_enter(self):
        self.t0 = time.monotonic()
        self.timer.start(30)
        QTimer.singleShot(4200, self._done)

    def _done(self):
        self.timer.stop()
        if self.app.current() is self:
            self.app.go_next(force=True)

    def paintEvent(self, e):
        if self.t0 is None:
            return
        t = time.monotonic() - self.t0
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        # słońce wschodzi zza linii horyzontu
        k = min(1.0, t / 2.2)
        ease = 1 - (1 - k) ** 3
        size = min(w, h) * 0.32
        cy = h * 0.55 - ease * h * 0.12
        p.setOpacity(min(1.0, t / 1.2))
        look.draw_logo(p, QRectF(w / 2 - size / 2, cy - size / 2, size, size))
        p.setOpacity(1.0)
        if t > 1.8:
            p.setOpacity(min(1.0, (t - 1.8) / 1.0))
            hh = size * 0.30
            from PySide6.QtGui import QFontMetrics
            f1 = look.font(hh, bold=True, fam=look.title_family())
            f2 = look.font(hh * 0.55, bold=True, italic=True, fam=look.title_family())
            tw = QFontMetrics(f1).horizontalAdvance("Horyzont") + hh * 0.06 + QFontMetrics(f2).horizontalAdvance("OS")
            look.draw_wordmark(p, w / 2 - tw / 2, cy + size * 0.58, hh)


class WelcomePage(OobePage):
    show_back = False

    def __init__(self, app):
        super().__init__(app)
        self.set_title(T("Witamy w systemie HoryzontOS", "Welcome to HoryzontOS"))
        self.text(T("Dziękujemy za wybór systemu HoryzontOS. Poświęć kilka minut na przygotowanie komputera do pracy.",
                    "Thank you for choosing HoryzontOS. Let's spend a few minutes setting up your computer."))
        self.text(T("W ciągu następnych kilku minut możesz:", "During the next few minutes you can:"))
        self.text(T("  •  połączyć się z Internetem przez Wi-Fi albo kabel sieciowy,\n"
                    "  •  włączyć repozytoria oprogramowania firm trzecich,\n"
                    "  •  od razu zaktualizować system, pulpit Horyzont i ekran powitalny,\n"
                    "  •  utworzyć konta dla osób, które będą używać tego komputera.",
                    "  •  connect to the Internet over Wi-Fi or a network cable,\n"
                    "  •  enable third-party software repositories,\n"
                    "  •  update the system, the Horyzont desktop and the welcome screen right away,\n"
                    "  •  create accounts for the people who will use this computer."))
        self.content.addStretch(1)
        self.text(T("Aby kontynuować, kliknij przycisk Dalej.", "To continue, click Next."))


class AutoUpdatesPage(OobePage):
    def __init__(self, app):
        super().__init__(app)
        self.set_title(T("Pomóż chronić swój komputer", "Help protect your PC"))
        self.text(T("Aktualizacje automatyczne regularnie pobierają i instalują najnowsze poprawki zabezpieczeń "
                    "i ulepszenia systemu HoryzontOS, programów, pulpitu Horyzont oraz ekranu powitalnego — bez "
                    "Twojego udziału, gdy komputer jest połączony z Internetem.",
                    "Automatic Updates regularly download and install the latest security fixes and improvements for "
                    "HoryzontOS, your programs, the Horyzont desktop and the welcome screen — without any effort "
                    "from you, whenever the computer is online."))
        self.content.addSpacing(8)
        self.auto = QRadioButton(T("Pomóż chronić mój komputer, włączając teraz &Aktualizacje automatyczne",
                                   "Help protect my PC by turning on &Automatic Updates now"))
        self.notify = QRadioButton(T("&Nie teraz — tylko powiadamiaj mnie o dostępnych aktualizacjach",
                                     "&Not right now — just notify me when updates are available"))
        for r in (self.auto, self.notify):
            r.setFont(look.font(14, True))
            self.content.addWidget(r)
        self.auto.setChecked(True)
        self.content.addSpacing(8)
        self.text(T("Ustawienie zmienisz w dowolnej chwili w Panelu sterowania → Horyzont Updates.",
                    "You can change this at any time in Control Panel → Horyzont Updates."), 13)
        self.content.addStretch(1)

    def validate(self):
        self.app.choices["auto_updates"] = self.auto.isChecked()
        return True


class _Bars(QWidget):
    def __init__(self, signal, secure):
        super().__init__()
        self.signal, self.secure = signal, secure
        self.setFixedSize(40, 18)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        n = 1 + min(3, self.signal // 25)
        for i in range(4):
            h = 4 + i * 4
            p.fillRect(QRectF(2 + i * 6, 18 - h, 4, h), QColor("#2f7d32") if i < n else QColor("#b8c2d6"))
        if self.secure:
            p.setPen(QPen(QColor("#806020"), 1.4))
            p.setBrush(Qt.NoBrush)
            p.drawArc(QRectF(29, 3, 7, 8), 0, 180 * 16)
            p.fillRect(QRectF(28, 7, 9, 8), QColor("#d9a520"))


class NetChoicePage(OobePage):
    """„Jak ten komputer będzie łączył się z Internetem?” — Wi-Fi, kabel (Ethernet) albo pominięcie."""
    can_skip = True

    def __init__(self, app):
        super().__init__(app)
        self.set_title(T("Jak ten komputer będzie łączył się z Internetem?",
                         "How will this computer connect to the Internet?"))
        self.text(T("Wybierz sposób połączenia z Internetem. Po połączeniu Instalator może od razu zaktualizować "
                    "system, Horyzont Desktop i ekran powitalny.",
                    "Select how this computer connects to the Internet. Once connected, Setup can update the system, "
                    "Horyzont Desktop and the welcome screen right away."), 14)
        self.group = QButtonGroup(self)
        self.radios = {}
        for key, pl, en, dpl, den in (
                ("wifi", "Sieć &bezprzewodowa (Wi-Fi)", "&Wireless network (Wi-Fi)",
                 "Połączenie bez kabla z routerem lub punktem dostępu. Potrzebny będzie klucz sieci (hasło).",
                 "Connect without a cable to a router or access point. You will need the network key (password)."),
                ("ethernet", "Sieć &lokalna (LAN) — kabel sieciowy (Ethernet)",
                 "&Local area network (LAN) — network cable (Ethernet)",
                 "Komputer jest podłączony kablem do routera, modemu lub sieci w firmie.",
                 "This computer is connected with a cable to a router, modem or an office network."),
                ("skip", "&Pomiń konfigurowanie połączenia z Internetem", "&Skip setting up an Internet connection",
                 "Połączenie skonfigurujesz później, klikając ikonę sieci na pasku zadań. Aktualizacje i część "
                 "repozytoriów nie będą wtedy dostępne podczas konfiguracji.",
                 "You can connect later using the network icon on the taskbar. Updates and some repositories "
                 "will not be available during setup.")):
            rb = QRadioButton(T(pl, en))
            rb.setFont(look.font(14, True))
            self.group.addButton(rb)
            self.content.addWidget(rb)
            d = QLabel(T(dpl, den))
            d.setWordWrap(True)
            d.setFont(look.font(13))
            d.setStyleSheet("color: #e6edff;")
            d.setContentsMargins(30, 0, 0, 6)
            self.content.addWidget(d)
            self.radios[key] = (rb, d)
        self.content.addStretch(1)
        self.status = self.text("", 13, color="#fff2b0")
        self.devs = None
        self._th = None

    def on_enter(self):
        self.status.setText(T("Wykrywanie kart sieciowych...", "Detecting network adapters..."))

        def work():
            self._devs = tasks.net_devices()
            self._on = tasks.online(2)
        self._th = threading.Thread(target=work, daemon=True)
        self._th.start()
        QTimer.singleShot(200, self._check)

    def busy(self):
        return bool(self._th and self._th.is_alive())

    def _check(self):
        if self._th.is_alive():
            QTimer.singleShot(200, self._check)
            return
        first = self.devs is None
        self.devs = self._devs
        self.app.online = self._on
        wifi, eth = self.devs["wifi"], self.devs["ethernet"]
        wired = [d for d, up in eth if up]
        self.radios["wifi"][0].setEnabled(bool(wifi))
        self.radios["ethernet"][0].setEnabled(bool(eth))
        parts = []
        if wifi:
            parts.append(T("Wi-Fi: ", "Wi-Fi: ") + ", ".join(wifi))
        else:
            parts.append(T("nie wykryto karty sieci bezprzewodowej", "no wireless adapter found"))
        if eth:
            parts.append(T("Ethernet: ", "Ethernet: ") + ", ".join(
                d + (T(" (kabel podłączony)", " (cable connected)") if up else "") for d, up in eth))
        else:
            parts.append(T("nie wykryto karty sieci przewodowej", "no wired adapter found"))
        st = T("Wykryte karty sieciowe: ", "Network adapters: ") + ";  ".join(parts)
        if self._on:
            st = T("✓  Komputer jest już połączony z Internetem.  ", "✓  This computer is already connected to "
                   "the Internet.  ") + st
        self.status.setText(st)
        if first or not self.group.checkedButton() or not self.group.checkedButton().isEnabled():
            key = "ethernet" if wired else ("wifi" if wifi else ("ethernet" if eth else "skip"))
            self.radios[key][0].setChecked(True)
        self.app.refresh_buttons()

    def choice(self):
        for k, (rb, _) in self.radios.items():
            if rb.isChecked():
                return k
        return "skip"

    def validate(self):
        self.app.choices["net"] = self.choice()
        return True

    def on_skip(self):
        self.app.choices["net"] = "skip"


class EthernetPage(OobePage):
    """Ustawienia sieci lokalnej (LAN): adres automatyczny albo stały, serwery DNS."""
    can_skip = True

    def __init__(self, app):
        super().__init__(app)
        self.set_title(T("Ustawienia sieci lokalnej (LAN)", "Local Area Network (LAN) settings"))
        self.status = self.text("", 14)
        self.text(T("Większość sieci domowych (router, modem kablowy) przydziela adresy automatycznie. Jeśli "
                    "dostawca Internetu lub administrator sieci podał Ci stały adres IP, wpisz go poniżej.",
                    "Most home networks (router, cable modem) assign addresses automatically. If your ISP or "
                    "network administrator gave you a fixed IP address, type it below."), 13)
        self.ip_auto = QRadioButton(T("Uzyskaj adres IP &automatycznie (zalecane)", "Obtain an IP address "
                                      "&automatically (recommended)"))
        self.ip_man = QRadioButton(T("&Użyj następującego adresu IP:", "U&se the following IP address:"))
        g1 = QButtonGroup(self)
        g1.addButton(self.ip_auto)
        g1.addButton(self.ip_man)
        self.dns_auto = QRadioButton(T("Uzyskaj adres serwera DNS a&utomatycznie", "O&btain DNS server address "
                                       "automatically"))
        self.dns_man = QRadioButton(T("U&żyj następujących adresów serwerów DNS:", "Us&e the following DNS server "
                                      "addresses:"))
        g2 = QButtonGroup(self)
        g2.addButton(self.dns_auto)
        g2.addButton(self.dns_man)
        self.f = {}

        def fields(rows):
            grid = QGridLayout()
            grid.setContentsMargins(30, 0, 0, 0)
            grid.setHorizontalSpacing(14)
            grid.setVerticalSpacing(4)
            for i, (k, t) in enumerate(rows):
                lab = QLabel(t)
                lab.setFont(look.font(13))
                e = QLineEdit()
                e.setFixedWidth(170)
                e.setFont(look.font(13))
                e.setInputMask("")
                lab.setBuddy(e)
                grid.addWidget(lab, i, 0)
                grid.addWidget(e, i, 1)
                self.f[k] = (lab, e)
            grid.setColumnStretch(2, 1)
            return grid
        for rb in (self.ip_auto, self.ip_man, self.dns_auto, self.dns_man):
            rb.setFont(look.font(13, True))
        self.content.addWidget(self.ip_auto)
        self.content.addWidget(self.ip_man)
        self.content.addLayout(fields([("ip", T("Adres IP:", "IP address:")),
                                       ("mask", T("Maska podsieci:", "Subnet mask:")),
                                       ("gw", T("Brama domyślna:", "Default gateway:"))]))
        self.content.addSpacing(6)
        self.content.addWidget(self.dns_auto)
        self.content.addWidget(self.dns_man)
        self.content.addLayout(fields([("dns1", T("Preferowany serwer DNS:", "Preferred DNS server:")),
                                       ("dns2", T("Alternatywny serwer DNS:", "Alternate DNS server:"))]))
        self.content.addStretch(1)
        self.f["mask"][1].setText("255.255.255.0")
        self.ip_auto.toggled.connect(self._en)
        self.dns_auto.toggled.connect(self._en)
        self.ip_auto.setChecked(True)
        self.dns_auto.setChecked(True)
        self._en()
        self.state = "idle"     # idle → applying
        self.dev = None
        self.up = False
        self._poll = QTimer(self)
        self._poll.timeout.connect(self._refresh)

    def skip(self):
        return self.app.choices.get("net") != "ethernet"

    def _en(self, *_):
        man = self.ip_man.isChecked()
        if man:
            # przy stałym adresie serwery DNS trzeba podać (jak w klasycznym oknie TCP/IP)
            self.dns_man.setChecked(True)
        self.dns_auto.setEnabled(not man)
        for k in ("ip", "mask", "gw"):
            for w in self.f[k]:
                w.setEnabled(man)
        for k in ("dns1", "dns2"):
            for w in self.f[k]:
                w.setEnabled(self.dns_man.isChecked())

    def on_enter(self):
        self._refresh()
        self._poll.start(3000)

    def _refresh(self):
        if self.state != "idle":
            return

        def work():
            d = tasks.net_devices()["ethernet"]
            self._r = (d, tasks.online(2))
        th = threading.Thread(target=work, daemon=True)
        th.start()

        def check():
            if th.is_alive():
                QTimer.singleShot(250, check)
                return
            if self.state != "idle":
                return
            eth, on = self._r
            self.dev = next((d for d, up in eth if up), eth[0][0] if eth else None)
            self.up = any(up for _, up in eth)
            self.app.online = on
            if not eth:
                self.status.setText(T("✗  Nie wykryto karty sieci przewodowej.", "✗  No wired network adapter "
                                      "was found."))
            elif on and self.up:
                self.status.setText(T(f"✓  Kabel sieciowy jest podłączony ({self.dev}), komputer ma dostęp do "
                                      "Internetu. Kliknij Dalej.", f"✓  The network cable is connected ({self.dev}) "
                                      "and the computer is online. Click Next."))
            elif self.up:
                self.status.setText(T(f"Kabel sieciowy jest podłączony ({self.dev}), ale nie ma dostępu do "
                                      "Internetu. Sprawdź ustawienia poniżej.", f"The cable is connected "
                                      f"({self.dev}) but there is no Internet access. Check the settings below."))
            else:
                self.status.setText(T(f"Kabel sieciowy nie jest podłączony ({self.dev}). Podłącz kabel do "
                                      "komputera i routera.", f"The network cable is unplugged ({self.dev}). "
                                      "Connect the cable to the computer and the router."))
        QTimer.singleShot(250, check)

    def busy(self):
        return self.state == "applying"

    def _warn(self, text, field=None):
        from ..ui.classic import message
        message(self, T("Ustawienia sieci lokalnej (LAN)", "LAN settings"), text)
        if field:
            self.f[field][1].setFocus()
            self.f[field][1].selectAll()

    def _values(self):
        import ipaddress
        v = {"ipv4": "manual" if self.ip_man.isChecked() else "auto", "address": "", "prefix": 24,
             "gateway": "", "dns": []}
        if self.ip_man.isChecked():
            try:
                ip = ipaddress.IPv4Address(self.f["ip"][1].text().strip())
            except ValueError:
                return self._warn(T("Wpisz prawidłowy adres IP (np. 192.168.1.20).", "Type a valid IP address "
                                    "(e.g. 192.168.1.20)."), "ip")
            try:
                prefix = ipaddress.IPv4Network("0.0.0.0/" + self.f["mask"][1].text().strip()).prefixlen
            except ValueError:
                return self._warn(T("Maska podsieci jest nieprawidłowa (np. 255.255.255.0).", "The subnet mask is "
                                    "invalid (e.g. 255.255.255.0)."), "mask")
            gw = self.f["gw"][1].text().strip()
            if gw:
                try:
                    ipaddress.IPv4Address(gw)
                except ValueError:
                    return self._warn(T("Adres bramy domyślnej jest nieprawidłowy.", "The default gateway is "
                                        "invalid."), "gw")
            v.update(address=str(ip), prefix=prefix, gateway=gw)
        if self.dns_man.isChecked():
            for k in ("dns1", "dns2"):
                t = self.f[k][1].text().strip()
                if not t:
                    continue
                try:
                    ipaddress.ip_address(t)
                except ValueError:
                    return self._warn(T("Adres serwera DNS jest nieprawidłowy.", "The DNS server address is "
                                        "invalid."), k)
                v["dns"].append(t)
            if not v["dns"]:
                return self._warn(T("Wpisz adres co najmniej jednego serwera DNS.", "Type at least one DNS "
                                    "server address."), "dns1")
        return v

    def validate(self):
        if self.state == "applying":
            return False
        if not self.dev:
            self._warn(T("Nie wykryto karty sieci przewodowej. Kliknij Wstecz, aby wybrać inny sposób "
                         "połączenia, albo Pomiń.", "No wired network adapter was found. Click Back to choose "
                         "another connection type, or Skip."))
            return False
        v = self._values()
        if v is None:
            return False
        if v["ipv4"] == "auto" and not v["dns"] and self.up and self.app.online:
            self._poll.stop()
            return True          # już połączono automatycznie — nic do zmiany
        self.state = "applying"
        self._poll.stop()
        self.status.setText(T("Łączenie z siecią lokalną...", "Connecting to the local network..."))
        self.app.refresh_buttons()

        def work():
            ok, err = tasks.ethernet_connect(self.dev, v["ipv4"], v["address"], v["prefix"], v["gateway"],
                                             v["dns"])
            self._res = (ok, err, ok and tasks.online(8))
        th = threading.Thread(target=work, daemon=True)
        th.start()

        def check():
            if th.is_alive():
                QTimer.singleShot(300, check)
                return
            ok, err, on = self._res
            self.state = "idle"
            self.app.online = on
            if on:
                self.app.refresh_buttons()
                self.app.go_next(force=True)
                return
            tasks.log("ethernet:", ok, err)
            self.status.setText("✗  " + (T("Połączono z siecią lokalną, ale nie ma dostępu do Internetu. Sprawdź "
                                           "ustawienia albo kliknij Pomiń.", "Connected to the local network, "
                                           "but there is no Internet access. Check the settings or click Skip.")
                                         if ok else T("Nie udało się połączyć z siecią lokalną. Sprawdź kabel i "
                                                      "ustawienia albo kliknij Pomiń.", "Could not connect to the "
                                                      "local network. Check the cable and settings or click Skip.")))
            self._poll.start(5000)
            self.app.refresh_buttons()
        QTimer.singleShot(300, check)
        return False

    def on_skip(self):
        self._poll.stop()


class NetworkPage(OobePage):
    can_skip = True

    def __init__(self, app):
        super().__init__(app)
        self.set_title(T("Połącz się z siecią bezprzewodową", "Connect to a wireless network"))
        self.status = self.text("", 14)
        self.hint = self.text(T("Wybierz sieć bezprzewodową z listy, wpisz klucz sieci (hasło) i kliknij Połącz. "
                                "Możesz też pominąć ten krok i połączyć się później, klikając ikonę sieci na pasku "
                                "zadań.",
                                "Select a wireless network, type its network key (password) and click Connect. You "
                                "can also skip this step and connect later using the network icon on the taskbar."), 13)
        row = QHBoxLayout()
        self.list = QListWidget()
        self.list.setMinimumHeight(150)
        self.list.setFont(look.font(13))
        self.list.currentRowChanged.connect(self._sel)
        row.addWidget(self.list, 3)
        side = QGridLayout()
        self.pwlab = QLabel(T("Klucz sieci:", "Network key:"))
        self.pw = QLineEdit()
        self.pw.setEchoMode(QLineEdit.Password)
        self.pw.returnPressed.connect(lambda: self.connect_net())
        self.show_pw = QCheckBox(T("Pokaż znaki", "Show characters"))
        self.show_pw.toggled.connect(lambda v: self.pw.setEchoMode(QLineEdit.Normal if v else QLineEdit.Password))
        self.conn = QPushButton(T("&Połącz", "&Connect"))
        # clicked przekazuje stan przycisku (False) — nie może trafić do parametru ssid
        self.conn.clicked.connect(lambda: self.connect_net())
        self.refresh = QPushButton(T("&Odśwież listę", "&Refresh list"))
        self.refresh.clicked.connect(lambda: self.scan(True))
        self.hidden = QPushButton(T("Sieć &ukryta...", "&Hidden network..."))
        self.hidden.clicked.connect(self.hidden_net)
        side.addWidget(self.pwlab, 0, 0)
        side.addWidget(self.pw, 1, 0)
        side.addWidget(self.show_pw, 2, 0)
        side.addWidget(self.conn, 3, 0)
        side.addWidget(self.refresh, 5, 0)
        side.addWidget(self.hidden, 6, 0)
        side.setRowStretch(4, 1)
        row.addSpacing(12)
        row.addLayout(side, 2)
        self.content.addLayout(row, 1)
        self.nets = []
        self.busy_flag = False
        self.wired = False
        self.hidden_ssid = None
        self._poll = QTimer(self)
        self._poll.timeout.connect(self._update_status)

    def on_enter(self):
        self._update_status()
        self._poll.start(3000)
        if not self.nets:
            self.scan(True)

    def _update_status(self):
        def work():
            dev, wired = tasks.wired_status()
            on = tasks.online(2)
            self._st = (dev, wired, on)
        if getattr(self, "_stth", None) and self._stth.is_alive():
            return
        self._stth = threading.Thread(target=work, daemon=True)
        self._stth.start()
        QTimer.singleShot(2500, self._show_status)

    def _show_status(self):
        st = getattr(self, "_st", None)
        if not st or self.busy_flag:
            return
        dev, wired, on = st
        self.wired = wired
        self.app.online = on
        if on and wired:
            self.status.setText(T("✓  Komputer jest połączony z Internetem przez sieć przewodową (Ethernet). Kliknij "
                                  "Dalej.", "✓  This computer is connected to the Internet through a wired (Ethernet) "
                                  "network. Click Next."))
        elif on:
            self.status.setText(T("✓  Komputer jest połączony z Internetem. Kliknij Dalej.",
                                  "✓  This computer is connected to the Internet. Click Next."))
        elif dev:
            self.status.setText(T("Kabel sieciowy nie jest podłączony albo sieć przewodowa nie daje dostępu do "
                                  "Internetu.", "The network cable is unplugged or the wired network has no "
                                  "Internet access."))
        else:
            self.status.setText(T("Komputer nie jest połączony z Internetem.", "This computer is not connected to the "
                                  "Internet."))
        self.app.refresh_buttons()

    def scan(self, rescan):
        self.list.clear()
        it = QListWidgetItem(T("Wyszukiwanie sieci bezprzewodowych...", "Searching for wireless networks..."))
        it.setFlags(Qt.NoItemFlags)
        self.list.addItem(it)

        def work():
            try:
                self._found = tasks.wifi_list(rescan)
            except Exception as e:
                tasks.log("wifi:", e)
                self._found = []
        th = threading.Thread(target=work, daemon=True)
        th.start()

        def check():
            if th.is_alive():
                QTimer.singleShot(300, check)
                return
            self.nets = self._found
            self._fill()
        QTimer.singleShot(300, check)

    def _fill(self):
        self.list.clear()
        if not self.nets:
            it = QListWidgetItem(T("Nie znaleziono sieci bezprzewodowych.", "No wireless networks were found."))
            it.setFlags(Qt.NoItemFlags)
            self.list.addItem(it)
            self._sel(-1)
            return
        for n in self.nets:
            it = QListWidgetItem("      " + n["ssid"] + (T("   (połączono)", "   (connected)") if n["active"] else ""))
            self.list.addItem(it)
            w = QWidget()
            lay = QHBoxLayout(w)
            lay.setContentsMargins(4, 0, 4, 0)
            lay.addStretch(1)
            lay.addWidget(_Bars(n["signal"], n["secure"]))
            w.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.list.setItemWidget(it, w)
        self.list.setCurrentRow(0)

    def _sel(self, row):
        n = self.nets[row] if 0 <= row < len(self.nets) else None
        secure = bool(n and n["secure"])
        for w in (self.pw, self.pwlab, self.show_pw):
            w.setEnabled(secure)
        self.conn.setEnabled(bool(n) and not self.busy_flag)

    def connect_net(self, ssid=None, hidden=False):
        row = self.list.currentRow()
        if not isinstance(ssid, str) or not ssid:
            ssid = None
        if ssid is None:
            if not (0 <= row < len(self.nets)):
                return
            ssid = self.nets[row]["ssid"]
        pw = self.pw.text()
        self.busy_flag = True
        self.conn.setEnabled(False)
        self.status.setText(T(f"Łączenie z siecią „{ssid}”...", f"Connecting to \"{ssid}\"..."))
        self.app.refresh_buttons()

        def work():
            ok, err = tasks.wifi_connect(ssid, pw, hidden)
            on = ok and tasks.online(6)
            self._res = (ok, err, on)
        th = threading.Thread(target=work, daemon=True)
        th.start()

        def check():
            if th.is_alive():
                QTimer.singleShot(300, check)
                return
            ok, err, on = self._res
            self.busy_flag = False
            self.conn.setEnabled(True)
            if ok:
                self.app.online = on
                self.status.setText(T(f"✓  Połączono z siecią „{ssid}”.", f"✓  Connected to \"{ssid}\".") +
                                    ("" if on else T("  (brak dostępu do Internetu)", "  (no Internet access)")))
                self.pw.clear()
                self.scan(False)
            else:
                low = err.lower()
                if "secrets" in low or "password" in low or "802-11-wireless-security" in low:
                    msg = T("Nie udało się połączyć — sprawdź klucz sieci.", "Could not connect — check the network key.")
                else:
                    msg = T("Nie udało się połączyć z siecią.", "Could not connect to the network.")
                self.status.setText("✗  " + msg)
            self.app.refresh_buttons()
        QTimer.singleShot(300, check)

    def hidden_net(self):
        from ..ui.classic import classic_dialog
        e = QLineEdit()

        def build(lay, frame):
            lay.addWidget(QLabel(T("Nazwa sieci (SSID):", "Network name (SSID):"), styleSheet="color:black"))
            lay.addWidget(e)
        if classic_dialog(self, T("Połącz z siecią ukrytą", "Connect to a hidden network"), build) and e.text().strip():
            self.connect_net(e.text().strip(), True)

    def skip(self):
        return self.app.choices.get("net") != "wifi"

    def busy(self):
        return self.busy_flag

    def validate(self):
        self._poll.stop()
        return True

    def on_skip(self):
        self._poll.stop()


class ThirdPartyPage(OobePage):
    def __init__(self, app):
        super().__init__(app)
        self.set_title(T("Repozytoria oprogramowania firm trzecich", "Third-party software repositories"))
        self.text(T("Repozytoria firm trzecich dają dostęp do dodatkowych programów, których nie ma w Fedorze — "
                    "np. przeglądarki Google Chrome, sterowników NVIDIA, Steam, kodeków multimedialnych i aplikacji "
                    "Flatpak. Część z nich nie jest wolnym oprogramowaniem.",
                    "Third-party repositories give access to additional software that is not part of Fedora — "
                    "e.g. Google Chrome, NVIDIA drivers, Steam, multimedia codecs and Flatpak apps. Some of it is "
                    "not free software."))
        self.enable = QCheckBox(T("&Włącz repozytoria oprogramowania firm trzecich", "&Enable third-party software "
                                  "repositories"))
        self.enable.setFont(look.font(14, True))
        self.content.addWidget(self.enable)
        self.subs = []
        for key, pl, en in (
                ("fedora", "Repozytoria firm trzecich udostępniane przez Fedorę (Google Chrome, sterowniki NVIDIA, Steam)",
                 "Third-party repositories provided by Fedora (Google Chrome, NVIDIA drivers, Steam)"),
                ("rpmfusion", "RPM Fusion (darmowe i niewolne pakiety) — wymaga Internetu",
                 "RPM Fusion (free and nonfree packages) — needs the Internet"),
                ("codecs", "Pełne kodeki multimedialne (MP4, H.264, AAC…) z RPM Fusion — wymaga Internetu",
                 "Full multimedia codecs (MP4, H.264, AAC…) from RPM Fusion — needs the Internet")):
            cb = QCheckBox(T(pl, en))
            cb.key = key
            cb.user_set = False
            cb.clicked.connect(lambda _=False, c=cb: setattr(c, "user_set", True))
            cb.setChecked(True)
            cb.setFont(look.font(13))
            row = QHBoxLayout()
            row.addSpacing(28)
            row.addWidget(cb)
            row.addStretch(1)
            self.content.addLayout(row)
            self.subs.append(cb)
        self.nv = self.text("", 13, color="#fff2b0")
        self.enable.toggled.connect(self._en)
        self.enable.setChecked(False)
        self._en(False)
        self.content.addStretch(1)
        self.text(T("Flathub (sklep z aplikacjami Flatpak) jest zawsze włączony — pochodzi z niego przeglądarka Firefox. "
                    "Repozytoria możesz włączyć lub wyłączyć później.",
                    "Flathub (the Flatpak app store) is always enabled — Firefox comes from it. You can enable or "
                    "disable the repositories later."), 13)

    def _en(self, v):
        for cb in self.subs:
            needs_net = cb.key in ("rpmfusion", "codecs")
            cb.setEnabled(v and (self.app.online or not needs_net))
            if needs_net:
                if not self.app.online:
                    cb.setChecked(False)
                elif not cb.user_set:
                    # połączenie pojawiło się dopiero w kreatorze — domyślnie zaznaczone jak pozostałe
                    cb.setChecked(True)

    def on_enter(self):
        self._en(self.enable.isChecked())
        hw = tasks.read_json(os.path.join(tasks.STATE, "hardware.json"))
        if hw.get("nvidia"):
            self.nv.setText(T("Wykryto kartę graficzną NVIDIA. Sterownik firmy NVIDIA zainstalujesz po włączeniu "
                              "repozytoriów (Dodaj lub usuń programy → akmod-nvidia).",
                              "An NVIDIA graphics card was detected. You can install the NVIDIA driver after enabling "
                              "the repositories (Add or Remove Programs → akmod-nvidia)."))

    def validate(self):
        on = self.enable.isChecked()
        self.app.choices["third_party"] = {cb.key: (on and cb.isChecked() and cb.isEnabled()) for cb in self.subs}
        return True


class UpdatePage(OobePage):
    can_skip = True

    def __init__(self, app):
        super().__init__(app)
        self.set_title(T("Aktualizacja systemu", "Update your computer"))
        self.intro = self.text(T("Komputer jest połączony z Internetem. Instalator może teraz pobrać i zainstalować "
                                 "najnowsze aktualizacje. Może to potrwać od kilku do kilkudziesięciu minut, zależnie od "
                                 "szybkości połączenia. Kliknij Dalej, aby rozpocząć, albo Pomiń, aby zrobić to później.",
                                 "This computer is connected to the Internet. Setup can now download and install the "
                                 "latest updates. This may take from a few minutes to over half an hour depending on "
                                 "your connection. Click Next to start, or Skip to do it later."), 14)
        self.rows = {}
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        self.items = [("repos", T("Repozytoria firm trzecich", "Third-party repositories")),
                      ("system", T("System Fedora i programy (także Firefox)", "Fedora system and programs (incl. Firefox)")),
                      ("desktop", T("Horyzont Desktop (pulpit)", "Horyzont Desktop")),
                      ("logon", T("Horyzont Logon (ekran powitalny)", "Horyzont Logon (welcome screen)"))]
        for i, (k, name) in enumerate(self.items):
            mark = QLabel("•")
            mark.setFixedWidth(22)
            mark.setFont(look.font(16, True))
            lab = QLabel(name)
            lab.setFont(look.font(14, True))
            st = QLabel("")
            st.setFont(look.font(13))
            grid.addWidget(mark, i, 0)
            grid.addWidget(lab, i, 1)
            grid.addWidget(st, i, 2)
            self.rows[k] = (mark, lab, st)
        grid.setColumnStretch(2, 1)
        self.content.addSpacing(6)
        self.content.addLayout(grid)
        self.content.addSpacing(10)
        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(18)
        self.bar.setStyleSheet("QProgressBar { background: white; border: 1px solid #1d3f8a; }"
                               "QProgressBar::chunk { background: #3a9a3a; width: 8px; margin: 1px; }")
        self.content.addWidget(self.bar)
        self.detail = self.text("", 12, color="#dfe8ff")
        self.content.addStretch(1)
        self.state = "ready"         # ready → running → done
        self.bar.hide()

    def skip(self):
        return not self.app.online

    def on_enter(self):
        tp = self.app.choices.get("third_party", {})
        self.need_repos = any(tp.values()) if tp else False
        self.rows["repos"][0].setVisible(self.need_repos)
        self.rows["repos"][1].setVisible(self.need_repos)
        self.rows["repos"][2].setVisible(self.need_repos)

    def busy(self):
        return self.state == "running"

    def validate(self):
        if self.state == "done":
            return True
        if self.state == "ready":
            self.start()
        return False

    def _set(self, key, status, mark=None, color="#ffffff"):
        m, l, s = self.rows[key]
        s.setText(status)
        if mark:
            m.setText(mark)
        m.setStyleSheet(f"color: {color};")

    def start(self):
        self.state = "running"
        self.app.refresh_buttons()
        self.bar.show()
        self.intro.setText(T("Trwa pobieranie i instalowanie aktualizacji. Nie wyłączaj komputera.",
                             "Downloading and installing updates. Do not turn off your computer."))
        self.prog = 0.0
        self.line = ""
        self.results = {}
        th = threading.Thread(target=self._work, daemon=True)
        th.start()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(200)

    def _work(self):
        import re
        tp = self.app.choices.get("third_party", {})
        steps = (["repos"] if self.need_repos else []) + ["system", "desktop", "logon"]
        span = 1.0 / len(steps)
        for si, key in enumerate(steps):
            base = si * span
            self.cur = key
            self.prog = base
            try:
                if key == "repos":
                    def ol(l):
                        self.line = l
                    errs = tasks.enable_third_party(tp.get("fedora"), tp.get("rpmfusion"), tp.get("flathub"),
                                                    tp.get("codecs"), ol)
                    self.results[key] = (not errs, ", ".join(errs))
                elif key == "system":
                    def ol(l):
                        self.line = l
                        m = re.search(r"\[\s*(\d+)\s*/\s*(\d+)\s*\]", l)
                        if m and int(m.group(2)) > 0:
                            self.prog = base + span * int(m.group(1)) / int(m.group(2))
                    rc = tasks.run_stream(["dnf", "upgrade", "-y", "--refresh"], ol)
                    # programy z Flatpaka (Firefox z Flathuba)
                    if os.path.exists("/usr/bin/flatpak"):
                        self.line = T("Aktualizowanie programów Flatpak (Firefox)...",
                                      "Updating Flatpak apps (Firefox)...")
                        rc2 = tasks.run_stream(["flatpak", "update", "--system", "-y", "--noninteractive"],
                                               lambda l: setattr(self, "line", l))
                        rc = rc or rc2
                    self.results[key] = (rc == 0, "")
                else:
                    if not hasattr(self, "_hups"):
                        self.line = T("Sprawdzanie dostępnych wersji w serwisie GitHub...",
                                      "Checking for new versions on GitHub...")
                        self._hups = tasks.horyzont_updates()
                    ups = self._hups
                    if ups is None:
                        self.results[key] = (False, "")
                        continue
                    want = "Desktop" if key == "desktop" else "Logon"
                    mine = [(n, u) for n, u in ups if (want in n) or (key == "logon" and ("powitalny" in n.lower() or
                                                                                         "welcome" in n.lower() or
                                                                                         "greeter" in n.lower()))]
                    if not mine:
                        self.results[key] = (True, "latest")
                    else:
                        n, u = mine[0]
                        self.line = T("Pobieranie: ", "Downloading: ") + n

                        def pr(f):
                            self.prog = base + span * 0.6 * f

                        def ol(l):
                            self.line = l
                        ok = tasks.install_horyzont_update(u, pr, ol)
                        self.results[key] = (ok, getattr(u, "new", "") if u else "")
            except Exception as e:
                tasks.log("aktualizacja", key, e)
                self.results[key] = (False, str(e))
        self.prog = 1.0
        self.cur = None

    def _tick(self):
        self.bar.setValue(int(self.prog * 1000))
        self.detail.setText(self.line[:110])
        for key, _ in self.items:
            if key in self.results:
                ok, info = self.results[key]
                if ok:
                    txt = T("aktualne", "up to date") if info == "latest" else (
                        T("zaktualizowano", "updated") + (f" ({info})" if info and info != "latest" else ""))
                    self._set(key, txt, "✓", "#b9ffa8")
                else:
                    self._set(key, T("nie udało się — spróbujesz później w Horyzont Updates",
                                     "failed — you can retry later in Horyzont Updates"), "✗", "#ffb3a8")
            elif getattr(self, "cur", None) == key:
                self._set(key, T("w toku...", "in progress..."), "►", "#ffd27a")
        if getattr(self, "cur", 1) is None and self.prog >= 1.0 and self.state == "running":
            self.state = "done"
            self._timer.stop()
            self.intro.setText(T("Aktualizacja zakończona. Kliknij Dalej.", "Updates finished. Click Next."))
            self.detail.setText("")
            self.app.refresh_buttons()


class UsersPage(OobePage):
    def __init__(self, app):
        super().__init__(app)
        self.set_title(T("Kto będzie używać tego komputera?", "Who will use this computer?"))
        self.text(T("Wpisz imię każdej osoby, która będzie używać tego komputera. System HoryzontOS utworzy osobne "
                    "konto dla każdej z nich, aby każdy miał własny pulpit, dokumenty i ustawienia.",
                    "Type the name of each person who will use this computer. HoryzontOS will create a separate "
                    "account for each person so everyone gets their own desktop, documents and settings."), 14)
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(4)
        self.fields = []
        labels = [T("&Twoje imię:", "&Your name:"), T("&Drugi użytkownik:", "&2nd User:"),
                  T("T&rzeci użytkownik:", "&3rd User:"), T("&Czwarty użytkownik:", "&4th User:"),
                  T("P&iąty użytkownik:", "&5th User:")]
        for i, t in enumerate(labels):
            lab = QLabel(t)
            lab.setFont(look.font(14, i == 0))
            e = QLineEdit()
            e.setMaxLength(40)
            e.setFixedWidth(260)
            e.setFont(look.font(13))
            lab.setBuddy(e)
            grid.addWidget(lab, i, 0)
            grid.addWidget(e, i, 1)
            self.fields.append(e)
        grid.setColumnStretch(2, 1)
        self.content.addLayout(grid)
        self.content.addSpacing(4)
        self.pwinfo = self.text(T("Hasło do Twojego konta (wymagane — potrzebne np. do instalowania programów i sudo):",
                                  "Password for your account (required — needed e.g. to install programs and for sudo):"),
                                13, True)
        pg = QGridLayout()
        pg.setHorizontalSpacing(10)
        pg.setVerticalSpacing(5)
        self.pw1, self.pw2, self.hint = QLineEdit(), QLineEdit(), QLineEdit()
        for e in (self.pw1, self.pw2, self.hint):
            e.setFont(look.font(13))
        self.pw1.setEchoMode(QLineEdit.Password)
        self.pw2.setEchoMode(QLineEdit.Password)
        self.pw1.setFixedWidth(180)
        self.pw2.setFixedWidth(180)
        self.hint.setMaxLength(60)

        def lab(t, buddy):
            l = QLabel(t)
            l.setFont(look.font(13))
            l.setBuddy(buddy)
            return l
        pg.addWidget(lab(T("&Hasło:", "&Password:"), self.pw1), 0, 0)
        pg.addWidget(self.pw1, 0, 1)
        pg.addWidget(lab(T("&Potwierdź hasło:", "C&onfirm:"), self.pw2), 0, 2)
        pg.addWidget(self.pw2, 0, 3)
        pg.addWidget(lab(T("Ws&kazówka:", "Password &hint:"), self.hint), 1, 0)
        pg.addWidget(self.hint, 1, 1, 1, 3)
        pg.setColumnStretch(4, 1)
        pg.setContentsMargins(28, 0, 0, 0)
        self.content.addLayout(pg)
        self.autologin = QCheckBox(T("&Loguj mnie automatycznie po włączeniu komputera (bez wpisywania hasła)",
                                     "&Log me on automatically when the computer starts (without typing the password)"))
        self.autologin.setFont(look.font(13))
        self.content.addWidget(self.autologin)
        self.content.addStretch(1)
        self.text(T("Pierwsze konto jest administratorem. Pozostałe są zwykłymi kontami bez hasła — hasła ustawisz "
                    "później w Panelu sterowania → Konta użytkowników.",
                    "The first account is an administrator. Other accounts are standard accounts without a password — "
                    "set passwords later in Control Panel → User Accounts."), 12)

    def on_enter(self):
        s = tasks.load_settings().get("setup", {})
        if not self.fields[0].text() and s.get("owner"):
            self.fields[0].setText(s["owner"])
        self.fields[0].setFocus()

    def _warn(self, text, focus=None):
        from ..ui.classic import message
        message(self, T("Kto będzie używać tego komputera?", "Who will use this computer?"), text)
        if focus is not None:
            focus.setFocus()
            focus.selectAll()

    def validate(self):
        names = [e.text().strip() for e in self.fields]
        if not names[0]:
            self._warn(T("Musisz wpisać przynajmniej jedno imię, aby kontynuować.",
                         "You must type at least one name to continue."), self.fields[0])
            return False
        seen = set()
        for n in names:
            if not n:
                continue
            if n.lower() in seen:
                self._warn(T(f"Imię „{n}” wpisano więcej niż raz. Każde konto musi mieć inną nazwę.",
                             f"The name \"{n}\" was typed more than once. Each account must have a different name."))
                return False
            if any(c in n for c in ":,\n"):
                self._warn(T("Imię nie może zawierać znaków : ani ,", "A name cannot contain : or ,"))
                return False
            seen.add(n.lower())
        pw = self.pw1.text()
        if not pw:
            self._warn(T("Wpisz hasło do swojego konta. Jest potrzebne do zadań administracyjnych (np. sudo). "
                         "Jeśli nie chcesz go wpisywać przy każdym uruchomieniu, zaznacz logowanie automatyczne.",
                         "Type a password for your account. It is needed for administrative tasks (e.g. sudo). "
                         "If you do not want to type it at every start, select automatic logon."), self.pw1)
            return False
        if pw != self.pw2.text():
            self._warn(T("Wpisane hasła nie są zgodne. Wpisz hasło ponownie w obu polach.",
                         "The passwords do not match. Type the password again in both boxes."), self.pw1)
            self.pw2.clear()
            return False
        hint = self.hint.text().strip()
        if hint and pw.lower() in hint.lower():
            self._warn(T("Wskazówka nie może zawierać hasła — każdy może ją zobaczyć na ekranie powitalnym.",
                         "The hint cannot contain the password — anyone can see it on the welcome screen."),
                       self.hint)
            return False
        users = [{"name": n, "password": pw if i == 0 else "", "hint": hint if i == 0 else ""}
                 for i, n in enumerate([n for n in names if n])]
        self.app.choices["users"] = users
        self.app.choices["autologin"] = self.autologin.isChecked()
        return True


class FinishPage(OobePage):
    show_back = True

    def __init__(self, app):
        super().__init__(app)
        self.next_text = T("&Zakończ", "&Finish")
        self.set_title(T("Dziękujemy!", "Thank you!"))
        self.text(T("Gotowe! Komputer jest przygotowany do pracy z systemem HoryzontOS.",
                    "Congratulations! Your computer is ready to use HoryzontOS."), 16)
        self.summary = self.text("", 14)
        self.content.addStretch(1)
        self.text(T("Aby zakończyć konfigurację i zacząć korzystać z komputera, kliknij przycisk Zakończ.",
                    "To finish setup and start using your computer, click Finish."))

    def on_enter(self):
        c = self.app.choices
        lines = []
        users = c.get("users", [])
        if users:
            lines.append(T("Konta: ", "Accounts: ") + ", ".join(u["name"] for u in users))
        lines.append(T("Logowanie automatyczne: ", "Automatic logon: ") +
                     (T("włączone", "on") if c.get("autologin") else T("wyłączone (ekran powitalny z hasłem)",
                                                                     "off (welcome screen with password)")))
        lines.append(T("Aktualizacje automatyczne: ", "Automatic Updates: ") +
                     (T("włączone", "on") if c.get("auto_updates", True) else T("tylko powiadomienia", "notify only")))
        tp = c.get("third_party", {})
        upd = next((p for p in self.app.pages if isinstance(p, UpdatePage)), None)
        rep = getattr(upd, "results", {}).get("repos") if upd else None
        if not any(tp.values()):
            st = T("wyłączone", "disabled")
        elif rep and not rep[0]:
            st = T("włączone częściowo (część wymaga Internetu — dokończysz w Horyzont Updates)",
                   "partly enabled (some need the Internet — finish in Horyzont Updates)")
        else:
            st = T("włączone", "enabled")
        lines.append(T("Repozytoria firm trzecich: ", "Third-party repositories: ") + st)
        lines.append(T("Internet: ", "Internet: ") + (T("połączono", "connected") if self.app.online else
                                                     T("bez połączenia", "not connected")))
        self.summary.setText("\n".join("  •  " + l for l in lines))
