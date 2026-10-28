"""Uruchomienie graficznej części instalatora albo pierwszego uruchomienia, zależnie od etapu."""
import os
import sys

from PySide6.QtWidgets import QApplication

from .. import i18n
from ..ui import look
from . import tasks


def main(cmd, argv):
    window = "--window" in argv
    st = tasks.stage()
    if cmd == "gui-setup":
        st = "setup"
    elif cmd == "oobe":
        st = "oobe"
    if st not in ("setup", "oobe"):
        print("HoryzontOS: konfiguracja jest już zakończona.")
        return 0
    app = QApplication(sys.argv[:1])
    app.setApplicationName("horyzontos-setup")
    app.setDesktopFileName("horyzontos-setup")
    look.setup_qapp(app, etch=(st == "setup"))
    if st == "setup":
        from .gui import GuiSetup
        w = GuiSetup()
    else:
        from ..oobe.app import Oobe
        w = Oobe()
    if window:
        w.resize(800, 600)
        w.show()
    else:
        w.showFullScreen()
    w.start()
    return app.exec()
