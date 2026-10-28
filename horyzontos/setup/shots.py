"""Zrzuty ekranów graficznej części instalatora i pierwszego uruchomienia (testy)."""
import os

os.environ.setdefault("HORYZONTOS_DRYRUN", "1")


def run(what, out, size, keys):
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtCore import QEvent, QPoint, Qt, QTimer
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from ..ui import look
    app = QApplication([])
    look.setup_qapp(app, etch=(what == "gui"))
    if what == "gui":
        from .gui import GuiSetup
        w = GuiSetup()
    else:
        from ..oobe.app import Oobe
        w = Oobe()
    w.resize(*size)
    w.show()
    w.start()
    os.makedirs(out, exist_ok=True)
    steps = [s.strip() for s in keys.split(",") if s.strip()]

    def focus_target():
        return app.focusWidget() or w

    def nxt():
        if not steps:
            app.quit()
            return
        s = steps.pop(0)
        delay = 200
        if s.startswith("W") and s[1:].isdigit():
            delay = int(s[1:])
        # następny krok planujemy przed wykonaniem bieżącego (okienka modalne mają własną pętlę zdarzeń)
        QTimer.singleShot(delay, nxt)
        if s.startswith("W"):
            return
        if s.startswith("S:"):
            w.grab().save(os.path.join(out, s[2:] + ".png"))
        elif s.startswith("T:"):
            QTest.keyClicks(focus_target(), s[2:])
        elif s == "NEXT":
            (w.wiz.next if what == "gui" else w.next).click()
        elif s == "BACK":
            (w.wiz.back if what == "gui" else w.back).click()
        elif s == "SKIP":
            w.skipb.click()
        elif s == "TAB":
            QTest.keyClick(focus_target(), Qt.Key_Tab)
        elif s == "ENTER":
            QTest.keyClick(focus_target(), Qt.Key_Return)
        elif s.startswith("CLICK:"):
            # CLICK:nazwa_przycisku (tekst bez &)
            from PySide6.QtWidgets import QAbstractButton
            name = s[6:]
            for b in w.findChildren(QAbstractButton):
                if b.isVisible() and b.text().replace("&", "") == name:
                    b.click()
                    break
        elif s.startswith("CHECK:"):
            from PySide6.QtWidgets import QAbstractButton
            name = s[6:]
            for b in w.findChildren(QAbstractButton):
                if b.isVisible() and b.text().replace("&", "").startswith(name):
                    b.setChecked(not b.isChecked())
                    break
    QTimer.singleShot(500, nxt)
    QTimer.singleShot(900000, app.quit)
    app.exec()
