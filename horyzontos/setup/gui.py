"""Graficzna część instalatora (pierwsze uruchomienie z dysku): tło z etapami, okno kreatora,
czynności instalacyjne z paskiem postępu i ponowne uruchomienie."""
import json
import os
import threading
import time
import traceback

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QWidget

from .. import i18n
from ..i18n import T
from ..ui.classic import ClassicWizard
from . import pages2, tasks
from .billboard import Billboard


class GuiSetup(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HoryzontOS Setup")
        self.bb = Billboard(self)
        self.wiz = ClassicWizard(T("Instalator systemu HoryzontOS", "HoryzontOS Setup"), self)
        self.wiz.hide()
        self.settings = tasks.load_settings().get("setup", {})
        self.wiz.settings = self.settings
        self.queue = []
        self._job = None
        self._eta_total = 39
        self._t = QTimer(self)
        self._t.timeout.connect(self._poll)
        self._t.start(100)

    def resizeEvent(self, e):
        self.bb.setGeometry(self.rect())
        self.wiz.setGeometry(self.bb.dialog_rect())

    # ------------------------------------------------------------ przebieg
    def start(self):
        w = self.wiz
        self.queue = [
            ("task", T("Instalowanie urządzeń", "Installing devices"), self.t_devices, 45, 36),
            ("pages", [pages2.RegionalPage, pages2.PersonalizePage, pages2.ComputerPage, pages2.DateTimePage], 33),
            ("task", T("Instalowanie sieci", "Installing network"), self.t_network_detect, 3, 30),
            ("pages", [pages2.NetworkPage, pages2.NetworkComponentsPage, pages2.WorkgroupPage], 29),
            ("task", T("Zapisywanie ustawień systemu", "Saving system settings"), self.t_apply, 6, 22),
            ("step", 4),
            ("task", T("Instalowanie elementów menu Start", "Installing Start menu items"), self.t_menu, 3, 12),
            ("task", T("Rejestrowanie składników", "Registering components"), self.t_register, 25, 9),
            ("task", T("Zapisywanie ustawień", "Saving settings"), self.t_save, 2, 3),
            ("task", T("Usuwanie wszystkich używanych plików tymczasowych", "Removing any temporary files used"),
             self.t_cleanup, 3, 1),
            ("reboot",),
        ]
        self.bb.minutes = self._eta_total
        self._next()

    def _next(self):
        if not self.queue:
            return
        item = self.queue.pop(0)
        kind = item[0]
        if kind == "task":
            _, label, fn, est, eta = item
            self.bb.minutes = eta
            self.bb.show_boards = True
            self.wiz.hide()
            self.bb.set_status(label, 0.0)
            self._run(fn, est)
        elif kind == "pages":
            pages = [cls(self.wiz) for cls in item[1]]
            self.bb.minutes = item[2]
            self.bb.set_status("", None)
            self.bb.show_boards = False
            self.wiz.set_pages(pages)
            self.wiz.on_done = self._pages_done
            self.wiz.setGeometry(self.bb.dialog_rect())
            self.wiz.show()
            self.wiz.raise_()
            self.wiz.start(0)
            self.bb.update()
        elif kind == "step":
            self.bb.current_step = item[1]
            self.bb.update()
            self._next()
        elif kind == "reboot":
            self.bb.set_status(T("Ponowne uruchamianie komputera...", "Restarting the computer..."), None)
            self.bb.minutes = 1
            QTimer.singleShot(2500, self._reboot)

    def _pages_done(self):
        self.wiz.hide()
        tasks.save_settings("setup", self.settings)
        self._next()

    def _run(self, fn, est):
        self._job = {"done": False, "error": None, "t0": time.monotonic(), "est": est, "frac": None}

        def work(job=self._job):
            try:
                fn(job)
            except Exception as e:
                tasks.log("BŁĄD:", traceback.format_exc())
                job["error"] = e
            job["done"] = True
        threading.Thread(target=work, daemon=True).start()

    def _poll(self):
        j = self._job
        if not j:
            return
        el = time.monotonic() - j["t0"]
        frac = j["frac"] if j["frac"] is not None else min(0.97, el / max(0.5, j["est"]))
        if j["done"]:
            if el < 1.2:          # każdy etap widać przynajmniej przez chwilę
                frac = min(1.0, el / 1.2)
                self.bb.set_status(self.bb.status, frac)
                return
            self._job = None
            self.bb.set_status(self.bb.status, 1.0)
            if j["error"]:
                tasks.log("etap zakończony błędem — kontynuuję")
            QTimer.singleShot(250, self._next)
            return
        self.bb.set_status(self.bb.status, frac)

    def _reboot(self):
        tasks.set_stage("oobe")
        tasks.reboot()
        if tasks.DRY:
            from PySide6.QtWidgets import QApplication
            QApplication.instance().quit()

    # ------------------------------------------------------------ czynności
    def t_devices(self, job):
        tasks.hardware_scan()

    def t_network_detect(self, job):
        time.sleep(0.5)

    def t_apply(self, job):
        s = self.settings
        from .data import KEYBOARDS
        loc = s.get("locale", "pl_PL.UTF-8")
        kb = s.get("kb", ["pl", ""])
        cmap = next((k[4] for k in KEYBOARDS if k[0] == kb[0] and k[1] == kb[1]), "us")
        tasks.apply_locale(loc, kb[0], kb[1], cmap)
        job["frac"] = 0.2
        if s.get("hostname"):
            tasks.apply_hostname(s["hostname"])
        if s.get("tz_apply"):
            tasks.apply_timezone(s["tz_apply"])
        if s.get("datetime"):
            tasks.apply_datetime(s["datetime"])
        job["frac"] = 0.5
        tasks.apply_root_password(s.get("rootpw", ""))
        tasks.apply_owner(s.get("owner", ""), s.get("org", ""), s.get("workgroup", ""))
        job["frac"] = 0.7
        tasks.apply_network(s.get("net"))
        # język konfiguratora w następnym etapie: zgodny z wybranymi opcjami regionalnymi
        try:
            path = os.path.join(tasks.STATE, "install.json")
            info = tasks.read_json(path)
            info["lang"] = "en" if loc.startswith("en") else ("pl" if loc.startswith("pl") else info.get("lang", "pl"))
            tasks.write(path, json.dumps(info, indent=1))
        except Exception as e:
            tasks.log("install.json:", e)
        # hasło nie jest potrzebne w kolejnym etapie
        s.pop("rootpw", None)
        tasks.save_settings("setup", s)

    def t_menu(self, job):
        tasks.start_menu_items()

    def t_register(self, job):
        steps = ["fonts", "mime", "schemas", "ld"]

        def step(n):
            if n in steps:
                job["frac"] = (steps.index(n) + 0.5) / len(steps)
        tasks.register_components(step)

    def t_save(self, job):
        tasks.sh(["systemctl", "daemon-reload"])

    def t_cleanup(self, job):
        tasks.cleanup_temp()
