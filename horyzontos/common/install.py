"""Kopiowanie systemu na dysk i przygotowanie go do pierwszego uruchomienia (etap tekstowy instalatora)."""
import json
import os
import re
import shutil
import subprocess
import tempfile
import time

from . import disks
from .disks import log, run

SYSIMAGE = "/mnt/sysimage"
SRCMNT = "/run/horyzontos/source"
LIVE = "/run/initramfs/live"
STATE_DIR = "/var/lib/horyzontos"


class Plan:
    def __init__(self, root, fstype, lang="pl"):
        self.root = root                 # Region partycji systemowej
        self.fstype = fstype             # btrfs | ext4 | xfs
        self.lang = lang
        self.uefi = disks.is_uefi()
        self.disk = root.disk
        self.esp = root.disk.esp() if self.uefi else None
        self.kver = None
        self.root_uuid = ""
        self.esp_uuid = ""


# ------------------------------------------------------------------ źródło (system z płyty)
def source_dir():
    """Katalog z czystym systemem do skopiowania (zamontowany squashfs z płyty)."""
    if os.environ.get("HORYZONTOS_SOURCE"):
        return os.environ["HORYZONTOS_SOURCE"]
    if os.path.isdir(os.path.join(SRCMNT, "usr")):
        return SRCMNT
    img = os.path.join(LIVE, "LiveOS", "squashfs.img")
    if os.path.exists(img):
        os.makedirs(SRCMNT, exist_ok=True)
        run(["mount", "-t", "squashfs", "-o", "ro,loop", img, SRCMNT])
        nested = os.path.join(SRCMNT, "LiveOS", "rootfs.img")
        if os.path.exists(nested):
            os.makedirs(SRCMNT + "-root", exist_ok=True)
            run(["mount", "-o", "ro,loop", nested, SRCMNT + "-root"])
            return SRCMNT + "-root"
        return SRCMNT
    for d in ("/run/rootfsbase", "/run/initramfs/squashfs"):
        if os.path.isdir(os.path.join(d, "usr")):
            return d
    raise RuntimeError("Nie znaleziono obrazu systemu (LiveOS/squashfs.img) na płycie.")


def file_count():
    for p in (os.path.join(LIVE, "LiveOS", "filecount"), os.environ.get("HORYZONTOS_FILECOUNT", "")):
        try:
            with open(p) as f:
                return max(1, int(f.read().strip()))
        except (OSError, ValueError):
            pass
    return 150000


def system_size():
    """Ile miejsca zajmuje system po rozpakowaniu (bajty)."""
    for p in (os.path.join(LIVE, "LiveOS", "rootsize"), os.environ.get("HORYZONTOS_ROOTSIZE", "")):
        try:
            with open(p) as f:
                return int(f.read().strip())
        except (OSError, ValueError):
            pass
    return 5 * 1024 * disks.MiB


def min_partition_size():
    return disks.align_up(system_size() + 4 * 1024 * disks.MiB, 1024 * disks.MiB)


# ------------------------------------------------------------------ montowanie
def _blkid_uuid(path):
    return subprocess.run(["blkid", "-s", "UUID", "-o", "value", path], capture_output=True,
                          text=True).stdout.strip()


def mount_target(plan):
    os.makedirs(SYSIMAGE, exist_ok=True)
    unmount_target()
    p = plan.root.path
    plan.root_uuid = _blkid_uuid(p)
    if plan.fstype == "btrfs":
        run(["mount", "-o", "compress=zstd:1", p, SYSIMAGE])
        for sv in ("root", "home"):
            if not os.path.isdir(os.path.join(SYSIMAGE, sv)):
                run(["btrfs", "subvolume", "create", os.path.join(SYSIMAGE, sv)])
        run(["umount", SYSIMAGE])
        run(["mount", "-o", "subvol=root,compress=zstd:1", p, SYSIMAGE])
        os.makedirs(os.path.join(SYSIMAGE, "home"), exist_ok=True)
        run(["mount", "-o", "subvol=home,compress=zstd:1", p, os.path.join(SYSIMAGE, "home")])
    else:
        run(["mount", p, SYSIMAGE])
    if plan.uefi:
        if not plan.esp:
            raise RuntimeError("no-esp")
        if not plan.esp.fstype:
            run(["mkfs.fat", "-F", "32", "-n", "EFI", plan.esp.path])
        disks.unmount_all(plan.esp.path)
        plan.esp_uuid = _blkid_uuid(plan.esp.path)
        os.makedirs(os.path.join(SYSIMAGE, "boot", "efi"), exist_ok=True)
        run(["mount", "-o", "umask=0077,shortname=winnt", plan.esp.path, os.path.join(SYSIMAGE, "boot", "efi")])


def unmount_target():
    subprocess.run(["umount", "-R", "-l", SYSIMAGE], capture_output=True)


# ------------------------------------------------------------------ kopiowanie
def copy_system(progress, cancelled=lambda: False):
    """Kopiuje system. progress(ułamek, nazwa_pliku)."""
    src = source_dir().rstrip("/") + "/"
    total = file_count()
    args = ["rsync", "-aHAXS", "--numeric-ids", "--out-format=%n",
            "--exclude=/proc/*", "--exclude=/sys/*", "--exclude=/dev/*", "--exclude=/run/*",
            "--exclude=/tmp/*", "--exclude=/boot/efi", "--exclude=/mnt/*", "--exclude=/media/*",
            src, SYSIMAGE + "/"]
    log("$", " ".join(args))
    # Drain diagnostics independently of stdout. A stderr pipe can fill while
    # we wait for the next filename, blocking rsync and the installer forever.
    with tempfile.TemporaryFile() as errors:
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=errors, text=True, bufsize=1,
                             errors="replace")
        n = 0
        last = 0.0
        try:
            for line in p.stdout:
                n += 1
                now = time.monotonic()
                if now - last > 0.05:
                    last = now
                    progress(min(0.995, n / total), os.path.basename(line.rstrip("/\n")) or line.strip())
                if cancelled():
                    p.terminate()
                    break
            rc = p.wait()
        finally:
            p.stdout.close()
            if p.poll() is None:
                p.kill()
                p.wait()
        # Keep the final diagnostic even if rsync reports thousands of errors.
        errors.seek(max(0, errors.tell() - 3000))
        err = errors.read().decode("utf-8", errors="replace")
    if err.strip():
        log("rsync stderr:", err[-3000:])
    # rsync 23/24 = część plików nie przeniesiona / zniknęła — przy obrazie tylko do odczytu to nie powinno wystąpić
    if rc not in (0,):
        raise RuntimeError(f"rsync zakończył się kodem {rc}: {err.strip()[-300:]}")
    # pliki rozruchowe UEFI (na partycji FAT nie ma właścicieli ani uprawnień)
    efi_src = os.path.join(src, "boot", "efi")
    if os.path.isdir(efi_src) and os.path.ismount(os.path.join(SYSIMAGE, "boot", "efi")):
        run(["rsync", "-rt", "--no-o", "--no-g", "--no-p", "--modify-window=2", efi_src + "/",
             os.path.join(SYSIMAGE, "boot", "efi") + "/"])
    for d in ("proc", "sys", "dev", "run", "tmp", "mnt", "media", "boot/efi"):
        os.makedirs(os.path.join(SYSIMAGE, d), exist_ok=True)
    os.chmod(os.path.join(SYSIMAGE, "tmp"), 0o1777)
    progress(1.0, "")
    log(f"skopiowano {n} pozycji (szacunek: {total})")


# ------------------------------------------------------------------ konfiguracja
def _bind():
    for d in ("dev", "proc", "sys", "run"):
        t = os.path.join(SYSIMAGE, d)
        os.makedirs(t, exist_ok=True)
        if not os.path.ismount(t):
            run(["mount", "--rbind", "/" + d, t])
            run(["mount", "--make-rslave", t], check=False)


def _unbind():
    for d in ("run", "sys", "proc", "dev"):
        t = os.path.join(SYSIMAGE, d)
        subprocess.run(["umount", "-R", "-l", t], capture_output=True)


def chroot(*args, check=True):
    return run(["chroot", SYSIMAGE, "/usr/bin/env", "-i", "PATH=/usr/sbin:/usr/bin", "LANG=C.UTF-8",
                "HOME=/root"] + list(args), check=check)


def _write(rel, text, mode=0o644):
    path = os.path.join(SYSIMAGE, rel.lstrip("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
    try:
        os.chmod(path, mode)
    except OSError:
        pass        # FAT (partycja EFI) nie ma uprawnień uniksowych


def write_fstab(plan):
    lines = ["# /etc/fstab — utworzony przez instalator HoryzontOS", ""]
    u = plan.root_uuid
    if plan.fstype == "btrfs":
        lines.append(f"UUID={u}  /      btrfs  subvol=root,compress=zstd:1  0 0")
        lines.append(f"UUID={u}  /home  btrfs  subvol=home,compress=zstd:1  0 0")
    elif plan.fstype == "ext4":
        lines.append(f"UUID={u}  /      ext4   defaults  1 1")
    else:
        lines.append(f"UUID={u}  /      xfs    defaults  0 0")
    if plan.uefi and plan.esp_uuid:
        lines.append(f"UUID={plan.esp_uuid}  /boot/efi  vfat  umask=0077,shortname=winnt  0 2")
    _write("/etc/fstab", "\n".join(lines) + "\n")


def kernel_version():
    mods = os.path.join(SYSIMAGE, "lib", "modules")
    vers = [v for v in os.listdir(mods) if os.path.exists(os.path.join(mods, v, "vmlinuz"))]
    vers.sort(key=lambda v: [int(x) if x.isdigit() else x for x in re.split(r"[.\-]", v)])
    return vers[-1]


def cmdline(plan):
    opts = f"root=UUID={plan.root_uuid} ro"
    if plan.fstype == "btrfs":
        opts += " rootflags=subvol=root"
    return opts + " rhgb quiet"


def boot_prefix(plan):
    r = chroot("grub2-mkrelpath", "/boot", check=False)
    rel = (r.stdout or "").strip()
    if r.returncode == 0 and rel.startswith("/"):
        return rel.rstrip("/")
    return "/root/boot" if plan.fstype == "btrfs" else "/boot"


def write_bootloader_entries(plan):
    kver = plan.kver = kernel_version()
    mid = open(os.path.join(SYSIMAGE, "etc", "machine-id")).read().strip()
    boot = os.path.join(SYSIMAGE, "boot")
    if not os.path.exists(os.path.join(boot, f"vmlinuz-{kver}")):
        shutil.copy2(os.path.join(SYSIMAGE, "lib", "modules", kver, "vmlinuz"), os.path.join(boot, f"vmlinuz-{kver}"))
    ents = os.path.join(boot, "loader", "entries")
    os.makedirs(ents, exist_ok=True)
    for f in os.listdir(ents):
        os.remove(os.path.join(ents, f))
    opts = cmdline(plan)
    _write("/etc/kernel/cmdline", opts + "\n")
    # bez osobnej partycji /boot ścieżki we wpisie są względem głównego katalogu systemu plików
    # (Btrfs: podwolumin root → /root/boot) — tak samo liczy je kernel-install Fedory (20-grub.install)
    prefix = boot_prefix(plan)
    _write(f"/boot/loader/entries/{mid}-{kver}.conf",
           f"title HoryzontOS ({kver})\nversion {kver}\nlinux {prefix}/vmlinuz-{kver}\n"
           f"initrd {prefix}/initramfs-{kver}.img\noptions {opts}\ngrub_users $grub_users\n"
           f"grub_arg --unrestricted\ngrub_class fedora\n")


def no_grubenv_writes():
    """GRUB nie potrafi zapisywać grubenv na Btrfs („sparse file not allowed” przy każdym starcie).
    Odczyt działa, więc wyłączamy tylko zapisy w skryptach generujących menu. Zamiast save_env zostaje „set”
    (polecenia „true” nie ma w podpisanym GRUB-ie Fedory dla UEFI)."""
    for name in ("08_fallback_counting", "10_reset_boot_success", "12_menu_auto_hide", "14_menu_show_once"):
        path = os.path.join(SYSIMAGE, "etc", "grub.d", name)
        try:
            text = open(path).read()
        except OSError:
            continue
        new = re.sub(r"(?m)^(\s*)save_env (.*)$", r"\1set horyzontos_noop=1  # HoryzontOS: save_env \2 (Btrfs)", text)
        if new != text:
            with open(path, "w") as f:
                f.write(new)


def install_grub(plan, step):
    if plan.fstype == "btrfs":
        no_grubenv_writes()
    chroot("grub2-editenv", "/boot/grub2/grubenv", "create", check=False)
    # menu GRUB-a ukryte (jak w klasycznym systemie); pokazuje się po przytrzymaniu Shift / Esc
    chroot("grub2-editenv", "/boot/grub2/grubenv", "set", "menu_auto_hide=1", "boot_success=1", check=False)
    if plan.uefi:
        rel = chroot("grub2-mkrelpath", "/boot/grub2", check=False).stdout.strip() or "/boot/grub2"
        stub = (f"search --no-floppy --fs-uuid --set=dev {plan.root_uuid}\n"
                f"set prefix=($dev){rel}\nexport $prefix\nconfigfile $prefix/grub.cfg\n")
        _write("/boot/efi/EFI/fedora/grub.cfg", stub, 0o600)
        step("grub-mkconfig")
        chroot("grub2-mkconfig", "-o", "/boot/grub2/grub.cfg")
        # wpis w menu rozruchu UEFI (pierwszy w kolejności)
        efi = "\\EFI\\fedora\\shimx64.efi"
        if not os.environ.get("HORYZONTOS_NO_EFIBOOTMGR"):
            out = run(["efibootmgr"], check=False).stdout
            for m in re.finditer(r"^Boot([0-9A-F]{4})\*?\s+HoryzontOS", out, re.M):
                run(["efibootmgr", "-q", "-b", m.group(1), "-B"], check=False)
            r = run(["efibootmgr", "-q", "-c", "-d", plan.disk.path, "-p", str(plan.esp.number),
                     "-L", "HoryzontOS", "-l", efi], check=False)
            if r.returncode != 0:
                log("efibootmgr nie zadziałał — zostaje ścieżka zapasowa EFI/BOOT/BOOTX64.EFI")
    else:
        step("grub-install")
        chroot("grub2-install", "--target=i386-pc", "--recheck", plan.disk.path)
        step("grub-mkconfig")
        chroot("grub2-mkconfig", "-o", "/boot/grub2/grub.cfg")
    # znacznik dla menu płyty instalacyjnej („Uruchom z dysku twardego”)
    _write("/boot/grub2/horyzontos-installed", time.strftime("%Y-%m-%d %H:%M\n"))


def prepare_first_boot(plan):
    """Po restarcie zamiast ekranu logowania wystartuje graficzna część instalatora."""
    state = os.path.join(SYSIMAGE, STATE_DIR.lstrip("/"))
    os.makedirs(state, exist_ok=True)
    info = {"lang": plan.lang, "fstype": plan.fstype, "uefi": plan.uefi, "disk": plan.disk.path,
            "root": plan.root.path, "installed": time.strftime("%Y-%m-%dT%H:%M:%S"), "kernel": plan.kver}
    with open(os.path.join(state, "install.json"), "w") as f:
        json.dump(info, f, indent=1)
    with open(os.path.join(state, "stage"), "w") as f:
        f.write("setup\n")
    sysd = os.path.join(SYSIMAGE, "etc", "systemd", "system")
    dm = os.path.join(sysd, "display-manager.service")
    if os.path.islink(dm):
        with open(os.path.join(state, "display-manager"), "w") as f:
            f.write(os.readlink(dm) + "\n")
        os.remove(dm)
    wants = os.path.join(sysd, "graphical.target.wants")
    os.makedirs(wants, exist_ok=True)
    link = os.path.join(wants, "horyzontos-setup.service")
    if not os.path.lexists(link):
        os.symlink("/usr/lib/systemd/system/horyzontos-setup.service", link)
    # konsola na tty1 nie może zabierać ekranu konfiguratorowi
    getty = os.path.join(sysd, "getty.target.wants", "getty@tty1.service")
    if os.path.lexists(getty):
        os.remove(getty)
        with open(os.path.join(state, "getty-tty1"), "w") as f:
            f.write("1\n")


def relabel(plan):
    """Etykiety SELinux dla skopiowanego systemu (płyta działa bez SELinuksa)."""
    fc = os.path.join(SYSIMAGE, "etc", "selinux", "targeted", "contexts", "files", "file_contexts")
    if not os.path.exists(fc):
        return
    r = run(["setfiles", "-F", "-r", SYSIMAGE, "-e", os.path.join(SYSIMAGE, "boot", "efi"),
             "-e", os.path.join(SYSIMAGE, "proc"), "-e", os.path.join(SYSIMAGE, "sys"),
             "-e", os.path.join(SYSIMAGE, "dev"), "-e", os.path.join(SYSIMAGE, "run"), fc, SYSIMAGE], check=False)
    if r.returncode != 0:
        log("setfiles nie powiódł się — ponowne etykietowanie przy pierwszym starcie")
        open(os.path.join(SYSIMAGE, ".autorelabel"), "w").close()


def configure(plan, step):
    """Konfiguracja skopiowanego systemu. step(nazwa_kroku) — do paska stanu."""
    step("fstab")
    write_fstab(plan)
    step("machine-id")
    mid = os.path.join(SYSIMAGE, "etc", "machine-id")
    if os.path.exists(mid):
        os.remove(mid)
    run(["systemd-machine-id-setup", "--root=" + SYSIMAGE])
    _bind()
    try:
        step("bootloader")
        write_bootloader_entries(plan)
        install_grub(plan, step)
        step("firstboot")
        prepare_first_boot(plan)
    finally:
        _unbind()
    if disks.LOG and os.path.exists(disks.LOG):
        os.makedirs(os.path.join(SYSIMAGE, "var", "log"), exist_ok=True)
        shutil.copy2(disks.LOG, os.path.join(SYSIMAGE, "var", "log", "horyzontos-install.log"))
    step("selinux")
    relabel(plan)
    step("sync")
    run(["sync"], check=False)
    unmount_target()
