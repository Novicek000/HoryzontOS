"""Strony okna instalatora (część graficzna, po pierwszym ponownym uruchomieniu)."""
import random
import re
import string
import time
import unicodedata

from PySide6.QtCore import QDate, QDateTime, QLocale, Qt, QTime, QTimer
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDateEdit, QGridLayout, QGroupBox,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton,
                               QRadioButton, QTimeEdit, QVBoxLayout, QWidget)

from .. import i18n
from ..i18n import T
from ..ui import look
from ..ui.classic import Page, classic_dialog, message
from . import data, tasks


def icon_label(name, size=32):
    l = QLabel()
    l.setPixmap(look.pixmap(name, size))
    l.setFixedSize(size + 4, size + 4)
    l.setAlignment(Qt.AlignTop | Qt.AlignLeft)
    return l


def locale_entry(code):
    return next((l for l in data.LOCALES if l[0] == code), data.LOCALES[0])


def kb_entry(layout, variant=""):
    return next((k for k in data.KEYBOARDS if k[0] == layout and k[1] == variant),
                next((k for k in data.KEYBOARDS if k[0] == layout), data.KEYBOARDS[0]))


# --------------------------------------------------------------------------- opcje regionalne
class RegionalPage(Page):
    icon = "regional"

    def __init__(self, wizard):
        super().__init__(wizard)
        self.title = T("Opcje regionalne i językowe", "Regional and Language Options")
        self.subtitle = T("Możesz dostosować system HoryzontOS do różnych regionów i języków.",
                          "You can customize HoryzontOS for different regions and languages.")
        s = wizard.settings
        s.setdefault("locale", "pl_PL.UTF-8" if i18n.lang() == "pl" else "en_US.UTF-8")
        kb = locale_entry(s["locale"])[5]
        s.setdefault("kb", [kb, ""])
        self.l1 = QLabel()
        self.l1.setWordWrap(True)
        self.body.addWidget(self.l1)
        row = QHBoxLayout()
        row.addStretch(1)
        b1 = QPushButton(T("&Dostosuj...", "&Customize..."))
        b1.setFixedSize(85, 23)
        b1.clicked.connect(self.customize)
        row.addWidget(b1)
        self.body.addLayout(row)
        self.body.addSpacing(10)
        self.l2 = QLabel()
        self.l2.setWordWrap(True)
        self.body.addWidget(self.l2)
        row = QHBoxLayout()
        row.addStretch(1)
        b2 = QPushButton(T("&Szczegóły...", "D&etails..."))
        b2.setFixedSize(85, 23)
        b2.clicked.connect(self.details)
        row.addWidget(b2)
        self.body.addLayout(row)
        self.body.addStretch(1)
        self.refresh()

    def refresh(self):
        s = self.wizard.settings
        loc = locale_entry(s["locale"])
        kb = kb_entry(*s["kb"])
        pl = i18n.lang() == "pl"
        self.l1.setText(T(
            "Opcje regionalne i standardy określają sposób wyświetlania liczb, walut, dat i godzin. Określają też "
            f"język systemu. Opcje regionalne i standardy są ustawione na: {loc[1]}, a lokalizacja na: {loc[3]}.\n\n"
            "Aby zmienić te ustawienia, kliknij przycisk Dostosuj.",
            "The Regional and Language Options settings determine how numbers, currencies, dates and times are "
            f"displayed, and the language of the system. Standards and formats are set to {loc[2]}, and the location "
            f"is set to {loc[4]}.\n\nTo change these settings, click Customize."))
        self.l2.setText(T(
            "Ustawienia wprowadzania tekstu umożliwiają wprowadzanie tekstu w wielu różnych językach przy użyciu "
            f"różnych układów klawiatury. Domyślnym układem klawiatury jest: {kb[2]}.\n\n"
            "Aby wyświetlić lub zmienić bieżącą konfigurację, kliknij przycisk Szczegóły.",
            "Text Input Languages allow you to enter text in many different languages using a variety of keyboard "
            f"layouts. Your default keyboard layout is {kb[3]}.\n\nTo view or change your current configuration, "
            "click Details."))

    def customize(self):
        s = self.wizard.settings
        combo = QComboBox()

        def build(lay, frame):
            lay.addWidget(QLabel(T("Wybierz język i format liczb, walut, dat i godzin:",
                                   "Select the language and the format of numbers, currencies, dates and times:")))
            for l in data.LOCALES:
                combo.addItem(l[1] if i18n.lang() == "pl" else l[2], l[0])
            combo.setCurrentIndex(max(0, combo.findData(s["locale"])))
            combo.setMinimumWidth(300)
            lay.addWidget(combo)
            ex = QLabel()
            lay.addWidget(ex)

            def upd():
                loc = QLocale(combo.currentData().split(".")[0])
                ex.setText(T("Przykłady:", "Samples:") + "\n" +
                           T("Liczba: ", "Number: ") + loc.toString(123456789.00, "f", 2) + "\n" +
                           T("Waluta: ", "Currency: ") + loc.toCurrencyString(123456789.00) + "\n" +
                           T("Data: ", "Date: ") + loc.toString(QDate.currentDate(), QLocale.LongFormat))
            combo.currentIndexChanged.connect(upd)
            upd()
        if classic_dialog(self, T("Opcje regionalne i językowe", "Regional and Language Options"), build):
            s["locale"] = combo.currentData()
            s["kb"] = [locale_entry(s["locale"])[5], ""]
            tz = locale_entry(s["locale"])[6]
            s["tz"] = tz
            self.refresh()

    def details(self):
        s = self.wizard.settings
        combo = QComboBox()

        def build(lay, frame):
            lay.addWidget(QLabel(T("Domyślny układ klawiatury używany po uruchomieniu komputera:",
                                   "Default keyboard layout used when you start your computer:")))
            for k in data.KEYBOARDS:
                combo.addItem(k[2] if i18n.lang() == "pl" else k[3], (k[0], k[1]))
            cur = tuple(s["kb"])
            for i in range(combo.count()):
                if tuple(combo.itemData(i)) == cur:
                    combo.setCurrentIndex(i)
            combo.setMinimumWidth(300)
            lay.addWidget(combo)
            test = QLineEdit()
            test.setPlaceholderText(T("Miejsce do wypróbowania klawiatury", "Type here to test"))
            lay.addWidget(test)
        if classic_dialog(self, T("Usługi tekstowe i języki wprowadzania", "Text Services and Input Languages"), build):
            s["kb"] = list(combo.currentData())
            self.refresh()


# --------------------------------------------------------------------------- personalizacja
class PersonalizePage(Page):
    icon = "user"

    def __init__(self, wizard):
        super().__init__(wizard)
        self.title = T("Personalizuj oprogramowanie", "Personalize Your Software")
        self.subtitle = T("Instalator użyje informacji o Tobie do personalizacji oprogramowania systemu HoryzontOS.",
                          "Setup uses the information you provide about yourself to personalize your HoryzontOS "
                          "software.")
        row = QHBoxLayout()
        row.addWidget(icon_label("users", 40))
        row.addSpacing(10)
        l = QLabel(T("Wpisz swoje imię i nazwisko oraz nazwę firmy lub organizacji.",
                     "Type your full name and the name of your company or organization."))
        l.setWordWrap(True)
        row.addWidget(l, 1)
        self.body.addLayout(row)
        self.body.addSpacing(16)
        g = QGridLayout()
        g.setContentsMargins(50, 0, 30, 0)
        g.setHorizontalSpacing(12)
        self.name = QLineEdit()
        self.org = QLineEdit()
        for e in (self.name, self.org):
            e.setMaxLength(60)
        g.addWidget(QLabel(T("&Imię i nazwisko:", "Na&me:")), 0, 0)
        g.addWidget(self.name, 0, 1)
        g.addWidget(QLabel(T("&Organizacja:", "&Organization:")), 1, 0)
        g.addWidget(self.org, 1, 1)
        g.itemAtPosition(0, 0).widget().setBuddy(self.name)
        g.itemAtPosition(1, 0).widget().setBuddy(self.org)
        self.body.addLayout(g)
        self.body.addStretch(1)

    def on_enter(self):
        self.name.setFocus()

    def validate(self):
        n = self.name.text().strip()
        if not n:
            message(self, T("Instalator systemu HoryzontOS", "HoryzontOS Setup"),
                    T("Musisz podać swoje imię i nazwisko, aby kontynuować.", "You must type your name to continue."))
            self.name.setFocus()
            return False
        self.wizard.settings["owner"] = n
        self.wizard.settings["org"] = self.org.text().strip()
        return True


def suggest_hostname(owner, org):
    src = (org or owner or "HORYZONT").strip()
    s = unicodedata.normalize("NFKD", src.replace("ł", "l").replace("Ł", "L"))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^A-Za-z0-9]", "", s.split()[0] if s.split() else s).upper()[:7] or "HORYZONT"
    tail = "".join(random.choice("0123456789ABCDEF") for _ in range(8))
    return f"{s}-{tail}"


HOST_RE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


class ComputerPage(Page):
    icon = "computer"

    def __init__(self, wizard):
        super().__init__(wizard)
        self.title = T("Nazwa komputera i hasło administratora", "Computer Name and Administrator Password")
        self.subtitle = T("Musisz podać nazwę i hasło administratora dla tego komputera.",
                          "You must provide a name and an Administrator password for your computer.")
        row = QHBoxLayout()
        row.addWidget(icon_label("computer", 36), 0, Qt.AlignTop)
        row.addSpacing(8)
        col = QVBoxLayout()
        l = QLabel(T("Instalator zasugerował nazwę dla tego komputera. Jeśli ten komputer jest w sieci, administrator "
                     "sieci może podać Ci nazwę, której należy użyć.",
                     "Setup has suggested a name for your computer. If your computer is on a network, your network "
                     "administrator can tell you what name to use."))
        l.setWordWrap(True)
        col.addWidget(l)
        r2 = QHBoxLayout()
        lab = QLabel(T("&Nazwa komputera:", "Co&mputer name:"))
        self.host = QLineEdit()
        self.host.setMaxLength(63)
        lab.setBuddy(self.host)
        r2.addWidget(lab)
        r2.addWidget(self.host, 1)
        col.addLayout(r2)
        row.addLayout(col, 1)
        self.body.addLayout(row)
        self.body.addSpacing(12)
        row = QHBoxLayout()
        row.addWidget(icon_label("key", 36), 0, Qt.AlignTop)
        row.addSpacing(8)
        col = QVBoxLayout()
        l = QLabel(T("Instalator utworzy konto użytkownika o nazwie root (Administrator). Tego konta należy używać, "
                     "gdy wymagany jest pełny dostęp do komputera. Jeśli pozostawisz pole hasła puste, konto zostanie "
                     "zablokowane, a zadania administracyjne wykonasz z poziomu swojego konta.",
                     "Setup creates a user account called root (Administrator). You use this account when you need "
                     "full access to your computer. If you leave the password empty, the account is locked and you "
                     "perform administrative tasks from your own account."))
        l.setWordWrap(True)
        col.addWidget(l)
        g = QGridLayout()
        self.pw1 = QLineEdit()
        self.pw2 = QLineEdit()
        for e in (self.pw1, self.pw2):
            e.setEchoMode(QLineEdit.Password)
        a = QLabel(T("&Hasło administratora:", "Administrator &password:"))
        b = QLabel(T("&Potwierdź hasło:", "&Confirm password:"))
        a.setBuddy(self.pw1)
        b.setBuddy(self.pw2)
        g.addWidget(a, 0, 0)
        g.addWidget(self.pw1, 0, 1)
        g.addWidget(b, 1, 0)
        g.addWidget(self.pw2, 1, 1)
        col.addLayout(g)
        row.addLayout(col, 1)
        self.body.addLayout(row)
        self.body.addStretch(1)

    def on_enter(self):
        s = self.wizard.settings
        if not self.host.text():
            self.host.setText(s.get("hostname") or suggest_hostname(s.get("owner", ""), s.get("org", "")))

    def validate(self):
        h = self.host.text().strip()
        title = T("Instalator systemu HoryzontOS", "HoryzontOS Setup")
        if not HOST_RE.match(h):
            message(self, title, T("Nazwa komputera może zawierać tylko litery (bez polskich znaków), cyfry i łączniki "
                                   "(-), nie może zaczynać się ani kończyć łącznikiem i może mieć najwyżej 63 znaki.",
                                   "The computer name may contain only letters, numbers and hyphens (-), must not "
                                   "start or end with a hyphen and can be at most 63 characters long."))
            self.host.setFocus()
            return False
        if self.pw1.text() != self.pw2.text():
            message(self, title, T("Wpisane hasła nie są zgodne. Wpisz hasło administratora ponownie w obu polach.",
                                   "The passwords you typed do not match. Please type the Administrator password "
                                   "again in both boxes."))
            self.pw1.clear()
            self.pw2.clear()
            self.pw1.setFocus()
            return False
        self.wizard.settings["hostname"] = h
        self.wizard.settings["rootpw"] = self.pw1.text()
        return True


# --------------------------------------------------------------------------- data i godzina
class _Clock(QTimeEdit):
    """Pole godziny, które samo „tyka”, dopóki użytkownik go nie zmieni."""

    def __init__(self):
        super().__init__()
        self.setDisplayFormat("HH:mm:ss")
        self.setTime(QTime.currentTime())
        self.touched = False
        self.timeChanged.connect(self._ch)
        self._internal = False
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(1000)

    def _ch(self, *_):
        if not self._internal:
            self.touched = True

    def _tick(self):
        if not self.touched and not self.hasFocus():
            self._internal = True
            self.setTime(QTime.currentTime())
            self._internal = False


class DateTimePage(Page):
    icon = "datetime"

    def __init__(self, wizard):
        super().__init__(wizard)
        self.title = T("Ustawienia daty i godziny", "Date and Time Settings")
        self.subtitle = T("Ustaw poprawną datę i godzinę na komputerze z systemem HoryzontOS.",
                          "Set the correct date and time for your HoryzontOS computer.")
        g1 = QGroupBox(T("Da&ta i godzina", "Da&te & Time"))
        r = QHBoxLayout(g1)
        r.addWidget(icon_label("datetime", 36))
        self.date = QDateEdit(QDate.currentDate())
        self.date.setCalendarPopup(True)
        self.date.setDisplayFormat("d   MMMM   yyyy")
        self.date.setLocale(QLocale(QLocale.Polish if i18n.lang() == "pl" else QLocale.English))
        self.date.setMinimumWidth(190)
        r.addWidget(self.date, 1)
        r.addSpacing(30)
        self.clock = _Clock()
        self.clock.setMinimumWidth(110)
        r.addWidget(self.clock)
        self.body.addWidget(g1)
        self.body.addSpacing(6)
        g2 = QGroupBox(T("&Strefa czasowa", "Time &Zone"))
        v = QVBoxLayout(g2)
        r = QHBoxLayout()
        r.addWidget(icon_label("regional", 36))
        self.zone = QComboBox()
        self.zone.setMaxVisibleItems(16)
        for e in data.TIMEZONES:
            self.zone.addItem(data.tz_label(e, i18n.lang()), e[3])
        r.addWidget(self.zone, 1)
        v.addLayout(r)
        self.dst = QCheckBox(T("&Automatycznie uwzględnij zmiany czasu", "&Automatically adjust clock for daylight "
                               "saving changes"))
        self.dst.setChecked(True)
        r2 = QHBoxLayout()
        r2.addSpacing(42)
        r2.addWidget(self.dst)
        r2.addStretch(1)
        v.addLayout(r2)
        self.body.addWidget(g2)
        self.body.addStretch(1)

    def on_enter(self):
        s = self.wizard.settings
        tz = s.get("tz") or ("Europe/Warsaw" if i18n.lang() == "pl" else "Europe/London")
        i = self.zone.findData(tz)
        self.zone.setCurrentIndex(i if i >= 0 else self.zone.findData("Europe/Warsaw"))

    def validate(self):
        s = self.wizard.settings
        e = data.TIMEZONES[self.zone.currentIndex()]
        tz = e[3]
        if not self.dst.isChecked():
            tz = data.fixed_zone(e[0]) or tz
        s["tz"] = e[3]
        s["tz_apply"] = tz
        if self.clock.touched or self.date.date() != QDate.currentDate():
            dt = QDateTime(self.date.date(), self.clock.time())
            s["datetime"] = dt.toSecsSinceEpoch()
        else:
            s.pop("datetime", None)
        return True


# --------------------------------------------------------------------------- sieć
class NetworkPage(Page):
    icon = "network_conn"

    def __init__(self, wizard):
        super().__init__(wizard)
        self.title = T("Ustawienia sieciowe", "Networking Settings")
        self.subtitle = T("Instalowanie składników sieciowych pozwala połączyć się z innymi komputerami, sieciami "
                          "i Internetem.", "Installing network software allows you to connect to other computers, "
                          "networks, and the Internet.")
        row = QHBoxLayout()
        row.addWidget(icon_label("network_conn", 36), 0, Qt.AlignTop)
        col = QVBoxLayout()
        col.addWidget(QLabel(T("Wybierz, czy chcesz używać ustawień typowych, czy niestandardowych:",
                               "Choose whether to use typical or custom settings:")))
        self.typ = QRadioButton(T("&Ustawienia typowe", "&Typical settings"))
        self.cus = QRadioButton(T("Ustawienia &niestandardowe", "&Custom settings"))
        self.typ.setChecked(True)
        d1 = QLabel(T("Tworzy połączenia sieciowe za pomocą NetworkManagera, odnajdywania urządzeń w sieci lokalnej "
                      "oraz protokołu TCP/IP z automatycznym adresowaniem.",
                      "Creates network connections using NetworkManager, local network discovery, and the TCP/IP "
                      "protocol with automatic addressing."))
        d2 = QLabel(T("Pozwala ręcznie skonfigurować składniki sieciowe (np. stały adres IP).",
                      "Allows you to manually configure networking components (for example a static IP address)."))
        for d in (d1, d2):
            d.setWordWrap(True)
            d.setContentsMargins(20, 0, 0, 6)
        col.addSpacing(6)
        col.addWidget(self.typ)
        col.addWidget(d1)
        col.addWidget(self.cus)
        col.addWidget(d2)
        row.addLayout(col, 1)
        self.body.addLayout(row)
        self.body.addStretch(1)

    def validate(self):
        self.wizard.settings.setdefault("net", {})["mode"] = "custom" if self.cus.isChecked() else "typical"
        return True


class NetworkComponentsPage(Page):
    icon = "network_conn"

    def __init__(self, wizard):
        super().__init__(wizard)
        self.title = T("Składniki sieciowe", "Networking Components")
        self.subtitle = T("Jakie składniki sieciowe mają być używane na tym komputerze?",
                          "What networking components do you want to use on this computer?")
        self.devlab = QLabel()
        self.body.addWidget(self.devlab)
        self.body.addWidget(QLabel(T("Zaznaczone składniki są używane przez to połączenie:",
                                     "Components checked are used by this connection:")))
        self.list = QListWidget()
        self.list.setFixedHeight(84)
        self.items = {}
        for key, pl, en in (("nm", "Klient sieci NetworkManager", "NetworkManager network client"),
                            ("avahi", "Odnajdywanie urządzeń w sieci lokalnej (mDNS)", "Local network discovery (mDNS)"),
                            ("fw", "Zapora sieciowa (firewalld)", "Firewall (firewalld)"),
                            ("ipv4", "Protokół internetowy (TCP/IP)", "Internet Protocol (TCP/IP)")):
            it = QListWidgetItem(T(pl, en))
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked)
            if key in ("nm", "ipv4", "fw"):
                it.setFlags(it.flags() & ~Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.list.addItem(it)
            self.items[key] = it
        self.body.addWidget(self.list)
        row = QHBoxLayout()
        row.addStretch(1)
        self.props = QPushButton(T("&Właściwości", "P&roperties"))
        self.props.setFixedSize(85, 23)
        self.props.clicked.connect(self.properties)
        row.addWidget(self.props)
        self.body.addLayout(row)
        self.desc = QLabel(T("Opis: TCP/IP to domyślny protokół sieci rozległych, który umożliwia komunikację "
                             "w różnych połączonych ze sobą sieciach.",
                             "Description: Transmission Control Protocol/Internet Protocol. The default wide area "
                             "network protocol that provides communication across diverse interconnected networks."))
        self.desc.setWordWrap(True)
        self.body.addWidget(self.desc)
        self.body.addStretch(1)

    def skip(self):
        return self.wizard.settings.get("net", {}).get("mode") != "custom"

    def on_enter(self):
        devs = tasks.ethernet_devices() if not tasks.DRY else ["enp0s3"]
        self.dev = devs[0] if devs else None
        self.devlab.setText(T("Dla urządzenia: ", "For device: ") +
                            (self.dev or T("(nie znaleziono karty sieci przewodowej)", "(no wired network adapter found)")))
        self.props.setEnabled(bool(self.dev))
        self.list.setCurrentItem(self.items["ipv4"])

    def properties(self):
        net = self.wizard.settings.setdefault("net", {})
        auto = QRadioButton(T("&Uzyskaj adres IP automatycznie", "&Obtain an IP address automatically"))
        man = QRadioButton(T("U&żyj następującego adresu IP:", "U&se the following IP address:"))
        ip, mask, gw, dns1, dns2 = (QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit())

        def build(lay, frame):
            lay.addWidget(QLabel(T("Ustawienia protokołu IP mogą być przydzielane automatycznie, jeśli sieć obsługuje "
                                   "tę możliwość. W przeciwnym wypadku uzyskaj ustawienia od administratora sieci.",
                                   "You can get IP settings assigned automatically if your network supports this "
                                   "capability. Otherwise, ask your network administrator for the IP settings."),
                             wordWrap=True))
            lay.addWidget(auto)
            lay.addWidget(man)
            g = QGridLayout()
            g.setContentsMargins(20, 0, 0, 0)
            for i, (lab, w) in enumerate(((T("Adres IP:", "IP address:"), ip),
                                          (T("Maska podsieci:", "Subnet mask:"), mask),
                                          (T("Brama domyślna:", "Default gateway:"), gw),
                                          (T("Preferowany serwer DNS:", "Preferred DNS server:"), dns1),
                                          (T("Alternatywny serwer DNS:", "Alternate DNS server:"), dns2))):
                g.addWidget(QLabel(lab), i, 0)
                w.setFixedWidth(130)
                g.addWidget(w, i, 1)
            lay.addLayout(g)
            (man if net.get("ipv4") == "manual" else auto).setChecked(True)
            ip.setText(net.get("address", ""))
            mask.setText(net.get("mask", "255.255.255.0"))
            gw.setText(net.get("gateway", ""))
            dns = net.get("dns") or []
            dns1.setText(dns[0] if dns else "")
            dns2.setText(dns[1] if len(dns) > 1 else "")

            def en():
                for w in (ip, mask, gw):
                    w.setEnabled(man.isChecked())
            man.toggled.connect(en)
            en()
        if classic_dialog(self, T("Właściwości: Protokół internetowy (TCP/IP)", "Internet Protocol (TCP/IP) Properties"),
                          build):
            net["device"] = self.dev
            net["ipv4"] = "manual" if man.isChecked() else "auto"
            net["address"] = ip.text().strip()
            net["mask"] = mask.text().strip()
            try:
                net["prefix"] = sum(bin(int(x)).count("1") for x in net["mask"].split("."))
            except ValueError:
                net["prefix"] = 24
            net["gateway"] = gw.text().strip()
            net["dns"] = [d for d in (dns1.text().strip(), dns2.text().strip()) if d]

    def validate(self):
        net = self.wizard.settings.setdefault("net", {})
        net["avahi"] = self.items["avahi"].checkState() == Qt.Checked
        net.setdefault("device", self.dev)
        return True


class WorkgroupPage(Page):
    icon = "network"

    def __init__(self, wizard):
        super().__init__(wizard)
        self.title = T("Grupa robocza lub domena komputera", "Workgroup or Computer Domain")
        self.subtitle = T("Grupa robocza jest kolekcją komputerów o tej samej nazwie grupy roboczej.",
                          "A workgroup is a collection of computers that have the same workgroup name.")
        self.body.addWidget(QLabel(T("Czy chcesz, aby ten komputer był członkiem domeny?",
                                     "Do you want this computer to be a member of a domain?")))
        self.body.addWidget(QLabel(T("(Te informacje możesz uzyskać od administratora sieci.)",
                                     "(You may need to obtain this information from your network administrator.)")))
        self.no = QRadioButton(T("&Nie, ten komputer nie jest w sieci lub jest w sieci bez domeny. Ustaw ten komputer "
                                 "jako członka następującej grupy roboczej:", "&No, this computer is not on a network, "
                                 "or is on a network without a domain. Make this computer a member of the following "
                                 "workgroup:"))
        self.no.setStyleSheet("QRadioButton { padding: 2px; }")
        self.no.setChecked(True)
        lab = QLabel(self.no.text().replace("&", ""))
        lab.setWordWrap(True)
        row = QHBoxLayout()
        self.no.setText("")
        row.addWidget(self.no, 0, Qt.AlignTop)
        row.addWidget(lab, 1)
        self.body.addSpacing(6)
        self.body.addLayout(row)
        r2 = QHBoxLayout()
        r2.addSpacing(26)
        self.wg = QLineEdit(T("GRUPA_ROBOCZA", "WORKGROUP"))
        self.wg.setMaxLength(15)
        self.wg.setFixedWidth(200)
        r2.addWidget(self.wg)
        r2.addStretch(1)
        self.body.addLayout(r2)
        self.yes = QRadioButton(T("&Tak, ustaw ten komputer jako członka następującej domeny:",
                                  "&Yes, make this computer a member of the following domain:"))
        self.yes.setEnabled(False)
        self.body.addSpacing(6)
        self.body.addWidget(self.yes)
        r3 = QHBoxLayout()
        r3.addSpacing(26)
        dom = QLineEdit()
        dom.setEnabled(False)
        dom.setFixedWidth(200)
        r3.addWidget(dom)
        r3.addStretch(1)
        self.body.addLayout(r3)
        r4 = QHBoxLayout()
        r4.addSpacing(26)
        n = QLabel(T("(dołączanie do domeny nie jest dostępne podczas instalacji)", "(not available during Setup)"))
        n.setEnabled(False)
        n.setWordWrap(True)
        r4.addWidget(n, 1)
        self.body.addLayout(r4)
        self.body.addStretch(1)

    def validate(self):
        w = re.sub(r"[^A-Za-z0-9_\-]", "", self.wg.text().strip().upper())[:15] or "WORKGROUP"
        self.wizard.settings["workgroup"] = w
        return True
