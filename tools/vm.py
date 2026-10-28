#!/usr/bin/env python3
"""Sterowanie maszyną wirtualną QEMU do testów instalatora (QMP).

  vm.py start ISO DISK [--uefi] [--mem 3072] [--boot d|c]   uruchomienie w tle
  vm.py shot PLIK.png                                        zrzut ekranu
  vm.py key ret | key ctrl-alt-delete | key f8              klawisze (nazwy QEMU, kilka naraz: ctrl-alt-f2)
  vm.py type "tekst"                                          wpisanie tekstu (US, + polskie przez AltGr)
  vm.py click X Y [W H]                                       klik myszą (współrzędne ekranu W×H)
  vm.py eject                                                 wysunięcie płyty
  vm.py quit                                                  zatrzymanie
Zmienna VMDIR (domyślnie /build/vm) — gniazdo QMP, log konsoli szeregowej.
"""
import json
import os
import socket
import subprocess
import sys
import time

VMDIR = os.environ.get("VMDIR", "/build/vm")
SOCK = os.path.join(VMDIR, "qmp.sock")


def qmp(cmd, args=None):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(SOCK)
    f = s.makefile("rw")
    f.readline()
    f.write(json.dumps({"execute": "qmp_capabilities"}) + "\n")
    f.flush()
    f.readline()
    msg = {"execute": cmd}
    if args:
        msg["arguments"] = args
    f.write(json.dumps(msg) + "\n")
    f.flush()
    while True:
        line = f.readline()
        if not line:
            return None
        r = json.loads(line)
        if "return" in r or "error" in r:
            s.close()
            return r


def start(argv):
    iso, disk = argv[0], argv[1]
    uefi = "--uefi" in argv
    mem = "3072"
    boot = "d"
    for i, a in enumerate(argv):
        if a == "--mem":
            mem = argv[i + 1]
        if a == "--boot":
            boot = argv[i + 1]
    os.makedirs(VMDIR, exist_ok=True)
    if os.path.exists(SOCK):
        os.remove(SOCK)
    args = ["qemu-system-x86_64", "-machine", "q35", "-accel", "tcg,thread=multi", "-cpu", "max", "-smp", "2",
            "-m", mem, "-vga", "std", "-display", "none", "-qmp", f"unix:{SOCK},server=on,wait=off",
            "-serial", f"file:{VMDIR}/serial.log", "-device", "qemu-xhci", "-device", "usb-tablet",
            "-device", "ahci,id=ahci",
            "-drive", f"id=hd0,file={disk},if=none,format=qcow2,cache=unsafe", "-device", "ide-hd,drive=hd0,bus=ahci.0",
            "-drive", f"id=cd0,file={iso},if=none,media=cdrom,readonly=on", "-device", "ide-cd,drive=cd0,bus=ahci.1",
            "-netdev", "user,id=n0", "-device", "e1000,netdev=n0",
            "-boot", f"order={boot}c,menu=off", "-rtc", "base=localtime"]
    if uefi:
        code = "/usr/share/edk2/ovmf/OVMF_CODE.fd"
        vars_ = os.path.join(VMDIR, "OVMF_VARS.fd")
        if not os.path.exists(vars_):
            subprocess.run(["cp", "/usr/share/edk2/ovmf/OVMF_VARS.fd", vars_])
        args += ["-drive", f"if=pflash,format=raw,readonly=on,file={code}",
                 "-drive", f"if=pflash,format=raw,file={vars_}"]
    with open(os.path.join(VMDIR, "qemu.log"), "w") as log:
        subprocess.Popen(args, stdout=log, stderr=log, start_new_session=True)
    for _ in range(50):
        if os.path.exists(SOCK):
            break
        time.sleep(0.2)
    print("uruchomiono")


def shot(path):
    tmp = os.path.join(VMDIR, "shot.ppm")
    r = qmp("screendump", {"filename": tmp})
    if r and "error" in r:
        print(r)
        return
    from PIL import Image
    Image.open(tmp).save(path)
    print(path)


KEYS = {" ": "spc", "\n": "ret", ".": "dot", ",": "comma", "-": "minus", "/": "slash", ":": "shift-semicolon",
        "_": "shift-minus", "@": "shift-2", "!": "shift-1", "'": "apostrophe", ";": "semicolon", "=": "equal",
        "(": "shift-9", ")": "shift-0", "?": "shift-slash"}
PL = {"ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ź": "x", "ż": "z"}


def keys_for(ch):
    if ch in KEYS:
        return KEYS[ch].split("-")
    if ch.lower() in PL:
        base = PL[ch.lower()]
        return ["alt_r"] + (["shift"] if ch.isupper() else []) + [base]
    if ch.isupper():
        return ["shift", ch.lower()]
    return [ch]


def send(keys):
    qmp("send-key", {"keys": [{"type": "qcode", "data": k} for k in keys], "hold-time": 60})


def main():
    cmd, argv = sys.argv[1], sys.argv[2:]
    if cmd == "start":
        start(argv)
    elif cmd == "shot":
        shot(argv[0])
    elif cmd == "key":
        for k in argv:
            send(k.split("-"))
            time.sleep(0.15)
    elif cmd == "type":
        for ch in " ".join(argv):
            send(keys_for(ch))
            time.sleep(0.06)
    elif cmd == "click":
        x, y = int(argv[0]), int(argv[1])
        w, h = (int(argv[2]), int(argv[3])) if len(argv) > 3 else (1024, 768)
        ax, ay = int(x * 32767 / w), int(y * 32767 / h)
        qmp("input-send-event", {"events": [{"type": "abs", "data": {"axis": "x", "value": ax}},
                                            {"type": "abs", "data": {"axis": "y", "value": ay}}]})
        time.sleep(0.1)
        for down in (True, False):
            qmp("input-send-event", {"events": [{"type": "btn", "data": {"down": down, "button": "left"}}]})
            time.sleep(0.08)
    elif cmd == "eject":
        print(qmp("eject", {"id": "cd0", "force": True}))
    elif cmd == "quit":
        print(qmp("quit"))
    elif cmd == "raw":
        print(qmp(argv[0], json.loads(argv[1]) if len(argv) > 1 else None))


if __name__ == "__main__":
    main()
