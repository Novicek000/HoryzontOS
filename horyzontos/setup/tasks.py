"""Zmiany w systemie wykonywane przez graficzną część instalatora i pierwsze uruchomienie (jako root).

HORYZONTOS_DRYRUN=1 — tylko zapis do dziennika (testy, podgląd)."""
import glob
import json
import os
import random
import re
import shutil
import subprocess
import time
import unicodedata

STATE = "/var/lib/horyzontos"
LOGFILE = "/var/log/horyzontos-setup.log"
ETC = "/etc/horyzontos"
DRY = bool(os.environ.get("HORYZONTOS_DRYRUN"))
HORYZONT_DIRS = ["/usr/local/share/horyzont", "/usr/share/horyzont"]
AGENT_CANDS = ["/usr/local/libexec/horyzont/update-agent", "/usr/libexec/horyzont/update-agent"]
GREETER_CFG_CANDS = ["/usr/local/bin/horyzont-greeter-config", "/usr/bin/horyzont-greeter-config"]


def log(*a):
    line = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    try:
        with open(LOGFILE if not DRY else "/tmp/horyzontos-setup-dry.log", "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def sh(args, check=False, input=None, timeout=None, env=None):
    log("$", " ".join(args) if isinstance(args, list) else args)
    if DRY:
        return subprocess.CompletedProcess(args, 0, "", "")
    try:
        p = subprocess.run(args, capture_output=True, text=True, input=input, timeout=timeout, env=env)
    except (OSError, subprocess.TimeoutExpired) as e:
        log("  błąd:", e)
        return subprocess.CompletedProcess(args, 127, "", str(e))
    if p.returncode != 0:
        log("  kod", p.returncode, (p.stderr or p.stdout).strip()[-1500:])
    if check and p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip()[-400:] or f"{args[0]}: kod {p.returncode}")
    return p


def write(path, text, mode=0o644):
    log("zapis", path)
    if DRY:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(tmp, mode)
    os.replace(tmp, path)
    if os.path.exists("/usr/sbin/restorecon"):
        subprocess.run(["/usr/sbin/restorecon", "-F", path], capture_output=True)


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {} if default is None else default


def save_settings(key, values):
    """Ustawienia konfiguratora zapisywane między etapami (/var/lib/horyzontos/settings.json)."""
    path = os.path.join(STATE, "settings.json")
    d = read_json(path)
    d[key] = values
    if not DRY:
        os.makedirs(STATE, exist_ok=True)
    write(path, json.dumps(d, indent=1, ensure_ascii=False), 0o600)


def load_settings():
    return read_json(os.path.join(STATE, "settings.json"))


def stage():
    try:
        with open(os.path.join(STATE, "stage")) as f:
            return f.read().strip()
    except OSError:
        return ""


def set_stage(s):
    if s:
        write(os.path.join(STATE, "stage"), s + "\n")
    else:
        log("koniec konfiguracji — usuwam znacznik etapu")
        if not DRY:
            try:
                os.remove(os.path.join(STATE, "stage"))
            except OSError:
                pass


# ===================================================================== etap 2 (instalator graficzny)
def apply_locale(locale, kb_layout, kb_variant, console_map):
    write("/etc/locale.conf", f'LANG="{locale}"\n')
    vc = f'KEYMAP="{console_map}"\nFONT="eurlatgr"\nXKBLAYOUT="{kb_layout}"\n'
    if kb_variant:
        vc += f'XKBVARIANT="{kb_variant}"\n'
    write("/etc/vconsole.conf", vc)
    x = ('Section "InputClass"\n        Identifier "system-keyboard"\n        MatchIsKeyboard "on"\n'
         f'        Option "XkbLayout" "{kb_layout}"\n')
    if kb_variant:
        x += f'        Option "XkbVariant" "{kb_variant}"\n'
    x += "EndSection\n"
    write("/etc/X11/xorg.conf.d/00-keyboard.conf", x)


def apply_hostname(name):
    write("/etc/hostname", name + "\n")
    sh(["hostnamectl", "set-hostname", name])


def apply_timezone(tz):
    zi = "/usr/share/zoneinfo/" + tz
    if not DRY and not os.path.exists(zi):
        log("brak strefy", tz)
        return
    log("strefa", tz)
    if not DRY:
        try:
            os.remove("/etc/localtime")
        except OSError:
            pass
        os.symlink("../usr/share/zoneinfo/" + tz, "/etc/localtime")
    sh(["timedatectl", "set-timezone", tz])


def apply_datetime(epoch):
    """Ustawia zegar, gdy użytkownik zmienił datę/godzinę (różnica > 2 min)."""
    if abs(epoch - time.time()) < 120:
        return
    sh(["date", "-s", "@%d" % int(epoch)])
    sh(["hwclock", "--systohc", "--utc"])


def apply_root_password(pw):
    if pw:
        sh(["chpasswd"], input=f"root:{pw}\n")
        sh(["passwd", "-u", "root"])
    else:
        sh(["passwd", "-l", "root"])


def apply_owner(name, org, workgroup):
    write(os.path.join(ETC, "owner.json"), json.dumps({"name": name, "organization": org, "workgroup": workgroup},
                                                      indent=1, ensure_ascii=False))
    smb = "/etc/samba/smb.conf"
    if os.path.exists(smb) and workgroup:
        try:
            text = open(smb).read()
            text2 = re.sub(r"(?im)^(\s*workgroup\s*=).*$", r"\1 " + workgroup, text)
            if text2 != text:
                write(smb, text2)
        except OSError:
            pass


def ethernet_devices():
    out = subprocess.run(["nmcli", "-t", "-f", "DEVICE,TYPE", "device"], capture_output=True, text=True).stdout \
        if shutil.which("nmcli") else ""
    return [l.split(":")[0] for l in out.splitlines() if l.endswith(":ethernet")]


def apply_network(net, activate=True):
    """net = {"mode": "typical"} albo {"mode": "custom", "device":…, "ipv4": "auto"|"manual", "address", "prefix",
    "gateway", "dns": [..], "avahi": bool}"""
    if not net or net.get("mode") != "custom":
        return
    if net.get("avahi") is False:
        sh(["systemctl", "disable", "--now", "avahi-daemon.service", "avahi-daemon.socket"])
    dev = net.get("device")
    if not dev:
        return
    name = f"Połączenie lokalne ({dev})"
    sh(["nmcli", "connection", "delete", name])
    args = ["nmcli", "connection", "add", "type", "ethernet", "ifname", dev, "con-name", name]
    if net.get("ipv4") == "manual" and net.get("address"):
        args += ["ipv4.method", "manual", "ipv4.addresses", f"{net['address']}/{net.get('prefix', 24)}"]
        if net.get("gateway"):
            args += ["ipv4.gateway", net["gateway"]]
    else:
        args += ["ipv4.method", "auto"]
    if net.get("dns"):
        args += ["ipv4.dns", " ".join(net["dns"]), "ipv4.ignore-auto-dns", "yes"]
    sh(args)
    if activate:
        sh(["nmcli", "connection", "up", name])


def register_components(step):
    """„Rejestrowanie składników” — odświeżenie pamięci podręcznych systemu."""
    for name, args in (("fonts", ["fc-cache", "-s"]),
                       ("mime", ["update-mime-database", "/usr/share/mime"]),
                       ("schemas", ["glib-compile-schemas", "/usr/share/glib-2.0/schemas"]),
                       ("ld", ["ldconfig"])):
        step(name)
        if shutil.which(args[0]):
            sh(args, timeout=300)
    # programy z Flatpaka (Firefox): przy budowaniu obrazu Flatpak nie mógł odświeżyć tych pamięci podręcznych
    fx = "/var/lib/flatpak/exports/share"
    if os.path.isdir(os.path.join(fx, "applications")) and shutil.which("update-desktop-database"):
        sh(["update-desktop-database", "-q", os.path.join(fx, "applications")], timeout=120)
    if os.path.isdir(os.path.join(fx, "mime")) and shutil.which("update-mime-database"):
        sh(["update-mime-database", os.path.join(fx, "mime")], timeout=120)
    for d in glob.glob("/usr/share/icons/*/") + glob.glob(os.path.join(fx, "icons", "*/")):
        if os.path.exists(os.path.join(d, "index.theme")) and shutil.which("gtk-update-icon-cache"):
            sh(["gtk-update-icon-cache", "-q", "-f", d], timeout=120)


def start_menu_items():
    for d in ("/usr/share/applications", "/usr/local/share/applications"):
        if os.path.isdir(d) and shutil.which("update-desktop-database"):
            sh(["update-desktop-database", "-q", d])


def hardware_scan():
    """„Instalowanie urządzeń”: udev, baza sprzętu, wykrycie karty NVIDIA (do podpowiedzi w konfiguratorze)."""
    sh(["udevadm", "settle", "-t", "60"], timeout=90)
    sh(["systemd-hwdb", "update"], timeout=300)
    # mniejszy initramfs tylko ze sterownikami tego komputera (szybszy start); ogólny zostaje, gdy się nie uda
    kver = os.uname().release
    target = f"/boot/initramfs-{kver}.img"
    if os.path.exists(target) and shutil.which("dracut"):
        tmp = target + ".new"
        p = sh(["dracut", "-f", "--hostonly", "--kver", kver, tmp], timeout=1800)
        if not DRY and p.returncode == 0 and os.path.exists(tmp) and os.path.getsize(tmp) > 4 * 1024 * 1024:
            os.replace(tmp, target)
            log("initramfs dla tego komputera:", os.path.getsize(target) // (1024 * 1024), "MB")
        elif not DRY and os.path.exists(tmp):
            os.remove(tmp)
    info = {"nvidia": False, "wifi": False, "vm": ""}
    try:
        out = subprocess.run(["lspci", "-mm"], capture_output=True, text=True, timeout=20).stdout
        info["nvidia"] = bool(re.search(r'"(VGA|3D)[^"]*" "NVIDIA', out))
    except (OSError, subprocess.TimeoutExpired):
        pass
    info["wifi"] = any(os.path.isdir(os.path.join(n, "wireless")) for n in glob.glob("/sys/class/net/*"))
    try:
        info["vm"] = subprocess.run(["systemd-detect-virt"], capture_output=True, text=True).stdout.strip()
    except OSError:
        pass
    if not DRY:
        os.makedirs(STATE, exist_ok=True)
    write(os.path.join(STATE, "hardware.json"), json.dumps(info))
    return info


def cleanup_temp():
    for p in glob.glob("/var/cache/libdnf5/*") + glob.glob("/var/tmp/horyzont*") + glob.glob("/root/.cache/*"):
        log("usuwanie", p)
        if not DRY:
            shutil.rmtree(p, ignore_errors=True) if os.path.isdir(p) else os.remove(p)


def reboot():
    log("ponowne uruchomienie")
    if not DRY:
        subprocess.Popen(["systemctl", "reboot"])


# ===================================================================== etap 3 (pierwsze uruchomienie)
def online(timeout=4):
    if DRY:
        return os.environ.get("HORYZONTOS_DRY_ONLINE", "1") == "1"
    st = subprocess.run(["nmcli", "-t", "-f", "CONNECTIVITY", "general"], capture_output=True, text=True).stdout.strip() \
        if shutil.which("nmcli") else ""
    if st == "full":
        return True
    import socket
    for host in ("mirrors.fedoraproject.org", "github.com"):
        try:
            socket.create_connection((host, 443), timeout=timeout).close()
            return True
        except OSError:
            continue
    return False


def wired_status():
    """(urządzenie, połączone?) pierwszej karty przewodowej."""
    if DRY:
        return ("enp0s3", os.environ.get("HORYZONTOS_DRY_WIRED", "0") == "1")
    for dev, up in net_devices()["ethernet"]:
        return dev, up
    return None, False


def net_devices():
    """Karty sieciowe: {"wifi": [nazwa…], "ethernet": [(nazwa, połączona?)…]}."""
    if DRY:
        return {"wifi": [] if os.environ.get("HORYZONTOS_DRY_NOWIFI") else ["wlp2s0"],
                "ethernet": [("enp0s3", os.environ.get("HORYZONTOS_DRY_WIRED", "0") == "1")]}
    res = {"wifi": [], "ethernet": []}
    if shutil.which("nmcli"):
        out = subprocess.run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"], capture_output=True,
                             text=True, env=dict(os.environ, LC_ALL="C")).stdout
        for l in out.splitlines():
            parts = l.split(":")
            if len(parts) < 3:
                continue
            if parts[1] == "wifi":
                res["wifi"].append(parts[0])
            elif parts[1] == "ethernet":
                res["ethernet"].append((parts[0], parts[2].startswith("connected")))
    else:
        for n in sorted(glob.glob("/sys/class/net/*")):
            name = os.path.basename(n)
            if os.path.isdir(os.path.join(n, "wireless")):
                res["wifi"].append(name)
            elif os.path.exists(os.path.join(n, "device")):
                try:
                    up = open(os.path.join(n, "carrier")).read().strip() == "1"
                except OSError:
                    up = False
                res["ethernet"].append((name, up))
    return res


def ethernet_connect(dev, ipv4="auto", address="", prefix=24, gateway="", dns=()):
    """Połączenie przewodowe (DHCP albo stały adres). Zwraca (ok, komunikat)."""
    net = {"mode": "custom", "device": dev, "ipv4": ipv4, "address": address, "prefix": prefix,
           "gateway": gateway, "dns": [d for d in dns if d]}
    if DRY:
        log("ethernet:", net)
        return True, ""
    apply_network(net, activate=False)
    name = f"Połączenie lokalne ({dev})"
    p = sh(["nmcli", "-w", "30", "connection", "up", name], timeout=45)
    return p.returncode == 0, (p.stderr or p.stdout).strip()


def wifi_list(rescan=True):
    """Lista sieci Wi-Fi: [{ssid, signal, secure, active}] (najsilniejsze pierwsze)."""
    if DRY:
        return [{"ssid": "Dom", "signal": 82, "secure": True, "active": False},
                {"ssid": "Sasiad_5G", "signal": 54, "secure": True, "active": False},
                {"ssid": "Kawiarnia", "signal": 31, "secure": False, "active": False}]
    if not shutil.which("nmcli"):
        return []
    out = subprocess.run(["nmcli", "-t", "-e", "yes", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list",
                          "--rescan", "yes" if rescan else "no"], capture_output=True, text=True, timeout=40).stdout
    nets = {}
    for l in out.splitlines():
        parts = re.split(r"(?<!\\):", l)
        if len(parts) < 4:
            continue
        ssid = parts[1].replace("\\:", ":")
        if not ssid:
            continue
        try:
            sig = int(parts[2])
        except ValueError:
            sig = 0
        e = {"ssid": ssid, "signal": sig, "secure": bool(parts[3].strip() and parts[3].strip() != "--"),
             "active": parts[0].strip() == "*"}
        if ssid not in nets or nets[ssid]["signal"] < sig:
            nets[ssid] = e
    return sorted(nets.values(), key=lambda n: (-n["active"], -n["signal"]))


def wifi_connect(ssid, password, hidden=False):
    args = ["nmcli", "device", "wifi", "connect", ssid]
    if password:
        args += ["password", password]
    if hidden:
        args += ["hidden", "yes"]
    p = sh(args, timeout=60)
    if DRY:
        return True, ""
    return p.returncode == 0, (p.stderr or p.stdout).strip()


def configure_updates(auto):
    agent = next((a for a in AGENT_CANDS if os.path.exists(a)), None)
    s = {"mode": "auto" if auto else "notify", "frequency": "daily", "time": "03:00", "takeover": True,
         "include_flatpak": True, "include_horyzont": True}
    tmp = "/tmp/horyzontos-updates.json"
    if not DRY:
        with open(tmp, "w") as f:
            json.dump(s, f)
    if agent:
        sh([agent, "--configure", tmp])
    else:
        write("/etc/horyzont/updates.json", json.dumps(s))


def run_stream(args, on_line, timeout=7200):
    """Uruchamia polecenie i przekazuje kolejne wiersze wyjścia. Zwraca kod wyjścia."""
    log("$", " ".join(args))
    if DRY:
        for i in range(1, 41):
            time.sleep(0.05)
            on_line(f"[{i:3d}/40] Upgrading pakiet-{i}")
        return 0
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                         errors="replace", env=dict(os.environ, LANG="C.UTF-8", TERM="dumb", NO_COLOR="1"))
    t0 = time.monotonic()
    buf = ""
    while True:
        ch = p.stdout.read(1)
        if not ch:
            break
        if ch in "\r\n":
            if buf.strip():
                on_line(buf.strip())
                if len(buf) < 400:
                    log("  |", buf.strip())
            buf = ""
        else:
            buf += ch
        if time.monotonic() - t0 > timeout:
            p.kill()
            break
    return p.wait()


def fedora_version():
    try:
        out = subprocess.run(["rpm", "-E", "%fedora"], capture_output=True, text=True).stdout.strip()
        return out if out.isdigit() else "43"
    except OSError:
        return "43"


def enable_third_party(fedora_extra, rpmfusion, flathub, codecs, on_line):
    errors = []
    if fedora_extra:
        if shutil.which("fedora-third-party"):
            sh(["fedora-third-party", "enable"])
        else:
            for repo in ("google-chrome", "rpmfusion-nonfree-nvidia-driver", "rpmfusion-nonfree-steam",
                         "copr:copr.fedorainfracloud.org:phracek:PyCharm"):
                sh(["dnf", "config-manager", "setopt", f"{repo}.enabled=1"])
    if rpmfusion:
        v = fedora_version()
        rc = run_stream(["dnf", "install", "-y",
                         f"https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-{v}.noarch.rpm",
                         f"https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-{v}.noarch.rpm"],
                        on_line)
        if rc != 0:
            errors.append("RPM Fusion")
        elif codecs:
            rc = run_stream(["dnf", "install", "-y", "--allowerasing", "--skip-unavailable", "ffmpeg-libs",
                             "gstreamer1-plugin-libav", "gstreamer1-plugins-ugly", "gstreamer1-plugins-bad-freeworld",
                             "libavcodec-freeworld"], on_line)
            if rc != 0:
                errors.append("kodeki")
    if flathub and shutil.which("flatpak"):
        p = sh(["flatpak", "remote-add", "--if-not-exists", "flathub",
                "https://dl.flathub.org/repo/flathub.flatpakrepo"], timeout=120)
        if p.returncode != 0:
            errors.append("Flathub")
    return errors


def horyzont_core():
    import sys
    for d in HORYZONT_DIRS + [os.environ.get("HORYZONT_SRC", "")]:
        if d and os.path.isdir(os.path.join(d, "horyzont")):
            if d not in sys.path:
                sys.path.append(d)
            break
    from horyzont.updates import core
    return core


def github_reachable(timeout=15):
    """Czy da się pobrać dane z GitHuba (HTTPS z weryfikacją certyfikatu)?"""
    import urllib.request
    try:
        req = urllib.request.Request("https://api.github.com/rate_limit", headers={"User-Agent": "HoryzontOS"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            r.read(64)
        return True
    except Exception as e:
        log("GitHub niedostępny:", e)
        return False


def horyzont_updates():
    """[(nazwa, Update)] — dostępne nowsze wersje Horyzont Desktop i dodatków (ekran powitalny).
    None, gdy GitHub jest nieosiągalny (sprawdzenie się nie udało)."""
    if DRY:
        return [("Horyzont Desktop", None), ("Horyzont Logon", None)]
    if not github_reachable():
        return None
    core = horyzont_core()
    out = []
    try:
        u = core.check_horyzont(core.default_repo())
        if u:
            out.append(("Horyzont Desktop", u))
    except Exception as e:
        log("sprawdzanie Horyzontu:", e)
    try:
        ups, errs = core.check_components()
        for e in errs:
            log("dodatek:", e)
        for u in ups:
            out.append((u.name, u))
    except Exception as e:
        log("sprawdzanie dodatków:", e)
    return out


def install_horyzont_update(u, progress, on_line):
    if DRY:
        for i in range(10):
            time.sleep(0.05)
            progress(i / 10)
        return True
    core = horyzont_core()
    d = core.download_horyzont(u, progress=lambda pct: progress(pct / 100.0))
    rc = run_stream(["bash", os.path.join(d, "update.sh"), "--yes"], on_line, timeout=3600)
    return rc == 0


def slug_login(name, taken):
    s = unicodedata.normalize("NFKD", name.replace("ł", "l").replace("Ł", "L"))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9]+", "", s.split()[0] if s.split() else s) or "uzytkownik"
    if not s[0].isalpha():
        s = "u" + s
    s = s[:30]
    base, n = s, 2
    while s in taken or s in ("root", "greetd", "admin", "nobody") or _user_exists(s):
        s = f"{base}{n}"
        n += 1
    taken.add(s)
    return s


def _user_exists(login):
    if DRY:
        return False
    import pwd
    try:
        pwd.getpwnam(login)
        return True
    except KeyError:
        return False


AVATARS = ["avatar_kite", "avatar_boat", "avatar_flower", "avatar_cat", "avatar_guitar", "avatar_planet"]


def _avatar_png(login, name):
    """Losowy obrazek konta (jak w klasycznym systemie) — z ikon Horyzontu, do AccountsService."""
    try:
        from PySide6.QtCore import QByteArray, QRectF, Qt
        from PySide6.QtGui import QImage, QPainter
        from PySide6.QtSvg import QSvgRenderer
        from ..ui import look
        svg = look.icon_svg(name)
        if not svg:
            return None
        img = QImage(96, 96, QImage.Format_ARGB32)
        img.fill(Qt.transparent)
        p = QPainter(img)
        QSvgRenderer(QByteArray(svg.encode())).render(p, QRectF(0, 0, 96, 96))
        p.end()
        path = f"/var/lib/AccountsService/icons/{login}"
        if not DRY:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            img.save(path, "PNG")
            subprocess.run(["restorecon", "-F", path], capture_output=True)
        return path
    except Exception as e:
        log("obrazek konta:", e)
        return None


def create_users(users):
    """users = [{"name": "Jan Kowalski", "password": ""}] — pierwsze konto jest administratorem (wheel)."""
    taken = set()
    created = []
    pics = AVATARS[:]
    random.shuffle(pics)
    for i, u in enumerate(users):
        name = u["name"].strip()
        login = slug_login(name, taken)
        args = ["useradd", "-m", "-c", name]
        if i == 0:
            args += ["-G", "wheel"]
        args.append(login)
        sh(args, check=not DRY)
        if u.get("password"):
            sh(["chpasswd"], input=f"{login}:{u['password']}\n")
        else:
            sh(["passwd", "-d", login])
        icon = _avatar_png(login, pics[i % len(pics)])
        hint = (u.get("hint") or "").replace("\n", " ").strip()
        acc = "[User]\n" + (f"Icon={icon}\n" if icon else "") + (f"PasswordHint={hint}\n" if hint else "") + \
            "SystemAccount=false\n"
        write(f"/var/lib/AccountsService/users/{login}", acc, 0o600)
        created.append({"login": login, "name": name, "admin": i == 0, "password": bool(u.get("password"))})
        log("utworzono konto", login)
    if not DRY and created:
        sh(["systemctl", "try-restart", "accounts-daemon.service"])
    return created


def finish_setup(created, autologin=False):
    """Koniec konfiguracji: włącza ekran powitalny (z automatycznym logowaniem pierwszego konta, gdy wybrano)."""
    dm_saved = os.path.join(STATE, "display-manager")
    target = ""
    try:
        target = open(dm_saved).read().strip()
    except OSError:
        pass
    cfg = next((c for c in GREETER_CFG_CANDS if os.path.exists(c)), None)
    if autologin and created and cfg:
        sh([cfg, "autologin", created[0]["login"]])
    if cfg:
        # pod logo ekranu powitalnego nazwa systemu (zamiast „Fedora Linux 43” z os-release)
        sh([cfg, "set", "subtitle", "HoryzontOS"])
        sh([cfg, "enable", "--quiet"])
    elif target:
        link = "/etc/systemd/system/display-manager.service"
        log("przywracanie", link, "->", target)
        if not DRY and not os.path.lexists(link):
            os.symlink(target, link)
    if os.path.exists(os.path.join(STATE, "getty-tty1")):
        sh(["systemctl", "enable", "getty@tty1.service"])
    sh(["systemctl", "disable", "horyzontos-setup.service"])
    wants = "/etc/systemd/system/graphical.target.wants/horyzontos-setup.service"
    if not DRY and os.path.lexists(wants):
        os.remove(wants)
    set_stage("")
    write(os.path.join(STATE, "done"), time.strftime("%Y-%m-%dT%H:%M:%S\n"))
