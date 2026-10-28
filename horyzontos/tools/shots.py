"""Zrzuty ekranów do testów i porównań (Qt offscreen).

python3 -m horyzontos shot textsetup OUTDIR --size 640x480 --fake [--uefi] --keys "W1500,S:welcome,ENTER,S:license"
  Kroki: Wnnn = czekaj nnn ms, S:nazwa = zrzut, inne = klawisz (ENTER, ESC, F8, DOWN, C, D, L, F, 1, ...),
         T:tekst = wpisz tekst.
"""
import os
import sys

FAKE_SIZE = 40960 * 1024 * 1024


def fake_disks(variant):
    from ..common import disks as D
    MiB = D.MiB

    def scan(probe_usage=True):
        d = D.Disk(0, "/dev/sda", FAKE_SIZE, "QEMU HARDDISK", "sata")
        if variant == "windows":
            d.pttype = "dos"
            r = D.Region(d, "part", MiB, 20002 * MiB, 1, "/dev/sda1", "7", "")
            r.fstype, r.label, r.used, r.osname = "ntfs", "", 2017 * MiB, "Windows"
            d.parts = [r]
        D._regions(d)
        return [d]

    def create(disk, free, size, with_boot=True):
        if disk.pttype is None:
            disk.pttype = "gpt" if D.is_uefi() else "dos"
        start = D.align_up(free.start)
        n = len(disk.parts) + 1
        newp = []
        for kind, sz in D.boot_needs(disk):
            r = D.Region(disk, "part", start, sz, n, f"/dev/sda{n}", D._ptype(disk, kind), "")
            r.fstype = "vfat" if kind == "esp" else ""
            newp.append(r)
            start += sz
            n += 1
        size = D.align_down(min(size, D.align_down(free.end) - start))
        r = D.Region(disk, "part", start, size, n, f"/dev/sda{n}", D._ptype(disk, "linux"), "")
        r.created_here = True
        newp.append(r)
        disk.parts.extend(newp)
        D._regions(disk)
        return r.path

    def delete(region):
        region.disk.parts.remove(region)
        D._regions(region.disk)

    D.scan = scan
    D.create_partition = create
    D.delete_partition = delete
    D.unmount_all = lambda p: None
    D.mkfs = lambda p, fs, label="HoryzontOS": __import__("time").sleep(1.5)

    from ..common import install as I
    import time

    def copy(progress, cancelled=lambda: False):
        names = ["vmlinuz", "libQt6Core.so.6", "labwc", "firefox", "python3.14", "horyzont", "greetd"]
        for i in range(60):
            progress(i / 60, names[i % len(names)])
            time.sleep(0.05)
        progress(1, "")
    I.mount_target = lambda plan: None
    I.copy_system = copy
    I.configure = lambda plan, step: time.sleep(1.0)
    I.unmount_target = lambda: None
    I.system_size = lambda: 5200 * MiB


def run_textsetup(out, size, keys, fake, uefi):
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["HORYZONTOS_FIRMWARE"] = "uefi" if uefi else "bios"
    if fake:
        fake_disks(fake)
    from PySide6.QtCore import QEvent, Qt, QTimer
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication
    from ..textsetup import app as A
    A.LOG = "/tmp/horyzontos-shot.log"
    qa = QApplication([])
    w = A.SetupApp()
    W, H = size
    w.resize(W, H)
    w.show()
    w.go(A.LoadingScreen(w))
    os.makedirs(out, exist_ok=True)
    steps = [s.strip() for s in keys.split(",") if s.strip()]
    keymap = {"ENTER": Qt.Key_Return, "ESC": Qt.Key_Escape, "UP": Qt.Key_Up, "DOWN": Qt.Key_Down,
              "PGDN": Qt.Key_PageDown, "PGUP": Qt.Key_PageUp, "BACKSPACE": Qt.Key_Backspace}

    def send(name, text=""):
        if name in keymap:
            k = keymap[name]
        elif name.startswith("F") and name[1:].isdigit():
            k = Qt.Key_F1 + int(name[1:]) - 1
        else:
            k = ord(name.upper()[0])
            text = text or name.lower()
        w.keyPressEvent(QKeyEvent(QEvent.KeyPress, k, Qt.NoModifier, text))

    def nxt():
        if not steps:
            qa.quit()
            return
        s = steps.pop(0)
        delay = 150
        if s.startswith("W") and s[1:].isdigit():
            delay = int(s[1:])
        elif s.startswith("S:"):
            w._blink = True
            img = w.render_image().scaled(W, H)
            img.save(os.path.join(out, s[2:] + ".png"))
            with open(os.path.join(out, s[2:] + ".txt"), "w") as f:
                f.write(w.grid.text())
        elif s.startswith("T:"):
            for ch in s[2:]:
                send(ch, ch)
        else:
            send(s)
        QTimer.singleShot(delay, nxt)
    QTimer.singleShot(300, nxt)
    QTimer.singleShot(600000, qa.quit)
    qa.exec()


def main(argv):
    what = argv[0]
    out = argv[1]
    size = (640, 480)
    keys = ""
    fake = None
    uefi = False
    i = 2
    while i < len(argv):
        a = argv[i]
        if a == "--size":
            size = tuple(int(x) for x in argv[i + 1].split("x")); i += 1
        elif a == "--keys":
            keys = argv[i + 1]; i += 1
        elif a == "--fake":
            fake = argv[i + 1]; i += 1
        elif a == "--uefi":
            uefi = True
        i += 1
    if what == "textsetup":
        run_textsetup(out, size, keys, fake, uefi)
    else:
        from ..setup import shots as S
        S.run(what, out, size, keys)
    return 0
