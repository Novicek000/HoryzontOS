"""Dyski i partycje dla instalatora: odczyt (sfdisk, blkid), tworzenie, usuwanie i formatowanie.

Wszystkie rozmiary w bajtach; w interfejsie pokazujemy MB (= MiB), jak klasyczny instalator."""
import glob
import json
import os
import re
import subprocess
import tempfile
import time

MiB = 1024 * 1024
ALIGN = MiB
ESP_SIZE = 600 * MiB
BIOSBOOT_SIZE = 1 * MiB

GPT_ESP = "C12A7328-F81F-11D2-BA4B-00A0C93EC93B"
GPT_LINUX = "0FC63DAF-8483-4772-8E79-3D69D8477DE4"
GPT_BIOSBOOT = "21686148-6453-6F6E-744E-656564454649"
GPT_MSDATA = "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7"
GPT_MSR = "E3C9E316-0B5C-4DB8-817D-F92DF00215AE"
GPT_WINRE = "DE94BBA4-06D1-4D40-A16A-BFD50179D6AC"
GPT_SWAP = "0657FD6D-A4AB-43C4-84E5-0933C84B4F4F"
DOS_EXTENDED = {"5", "f", "85"}

FS_NAMES = {
    "btrfs": "Btrfs", "ext4": "ext4", "ext3": "ext3", "ext2": "ext2", "xfs": "XFS", "ntfs": "NTFS",
    "vfat": "FAT32", "exfat": "exFAT", "swap": "swap", "crypto_LUKS": "LUKS", "LVM2_member": "LVM",
    "linux_raid_member": "RAID", "iso9660": "CD", "f2fs": "F2FS", "zfs_member": "ZFS", "hfsplus": "HFS+",
    "apfs": "APFS",
}

LOG = None


def log(*a):
    line = " ".join(str(x) for x in a)
    if LOG:
        try:
            with open(LOG, "a") as f:
                f.write(time.strftime("%H:%M:%S ") + line + "\n")
        except OSError:
            pass


def run(args, check=True, input=None, timeout=None):
    log("$", " ".join(args))
    p = subprocess.run(args, input=input, capture_output=True, text=True, timeout=timeout)
    if p.stdout.strip():
        log(p.stdout.strip()[-3000:])
    if p.stderr.strip():
        log("stderr:", p.stderr.strip()[-3000:])
    if check and p.returncode != 0:
        raise RuntimeError(f"{args[0]}: {(p.stderr or p.stdout).strip()[-400:]}")
    return p


def is_uefi():
    if os.environ.get("HORYZONTOS_FIRMWARE"):
        return os.environ["HORYZONTOS_FIRMWARE"].lower() == "uefi"
    return os.path.isdir("/sys/firmware/efi")


def mb(n):
    """Bajty → MB (zaokrąglenie w dół, jak w klasycznym instalatorze)."""
    return int(n // MiB)


def align_up(n, a=ALIGN):
    return (n + a - 1) // a * a


def align_down(n, a=ALIGN):
    return n // a * a


class Region:
    """Wiersz listy: partycja albo obszar niepodzielony."""

    def __init__(self, disk, kind, start, size, number=None, path=None, ptype="", name=""):
        self.disk = disk
        self.kind = kind            # "part" | "free"
        self.start = start
        self.size = size
        self.number = number
        self.path = path
        self.ptype = (ptype or "").upper()
        self.partname = name or ""
        self.fstype = ""
        self.label = ""
        self.uuid = ""
        self.used = None            # zajęte bajty (gdy udało się sprawdzić)
        self.osname = ""
        self.created_here = False   # utworzona w tej sesji instalatora (nowa, surowa)

    @property
    def end(self):
        return self.start + self.size

    @property
    def is_free(self):
        return self.kind == "free"

    @property
    def is_esp(self):
        if self.ptype in (GPT_ESP, "EF"):
            return True
        return False

    @property
    def is_biosboot(self):
        return self.ptype == GPT_BIOSBOOT

    @property
    def is_extended(self):
        return self.disk.pttype == "dos" and self.ptype.lower() in DOS_EXTENDED

    def fs_display(self, T):
        if self.is_free:
            return ""
        if self.is_esp:
            return "FAT32" if self.fstype == "vfat" else (FS_NAMES.get(self.fstype, self.fstype) or T("Nowa (surowa)", "New (raw)"))
        if not self.fstype:
            return T("Nowa (surowa)", "New (raw)")
        return FS_NAMES.get(self.fstype, self.fstype)

    def title(self, T):
        """Nazwa partycji pokazywana na liście."""
        if self.is_esp:
            return T("Partycja systemowa EFI", "EFI system partition")
        if self.is_biosboot:
            return T("Partycja startowa BIOS", "BIOS boot partition")
        if self.ptype == GPT_MSR:
            return T("Partycja zastrzeżona (MSR)", "Reserved partition (MSR)")
        if self.ptype == GPT_WINRE:
            return T("Partycja odzyskiwania", "Recovery partition")
        if self.label:
            return self.label
        if self.partname and self.partname not in ("primary", "logical", "Linux filesystem"):
            return self.partname
        return T(f"Partycja{self.number}", f"Partition{self.number}")


class Disk:
    def __init__(self, index, path, size, model, tran, sector=512):
        self.index = index
        self.path = path
        self.name = os.path.basename(path)
        self.size = size
        self.model = (model or "").strip()
        self.tran = (tran or "").strip()
        self.sector = sector
        self.pttype = None          # "gpt" | "dos" | None
        self.first = MiB
        self.last = size - MiB      # koniec obszaru użytecznego (bajty, wyłącznie)
        self.parts = []
        self.regions = []

    def describe(self, T, model=True):
        bus = {"sata": "SATA", "ata": "ATA", "nvme": "NVMe", "usb": "USB", "scsi": "SCSI", "virtio": "VirtIO",
               "mmc": "MMC", "sas": "SAS", "ide": "IDE"}.get(self.tran.lower(), self.tran.upper() or "?")
        if not self.tran and self.name.startswith("vd"):
            bus = "VirtIO"
        tab = {"gpt": "GPT", "dos": "MBR"}.get(self.pttype or new_label_type())
        model = f", {self.model}" if self.model and model else ""
        return T(f"{mb(self.size)} MB Dysk {self.index} ({self.name}), magistrala {bus}{model} [{tab}]",
                 f"{mb(self.size)} MB Disk {self.index} ({self.name}), bus {bus}{model} [{tab}]")

    def has_esp(self):
        return any(r.is_esp for r in self.parts)

    def esp(self):
        for r in self.parts:
            if r.is_esp:
                return r
        return None

    def has_biosboot(self):
        return any(r.is_biosboot for r in self.parts)

    def primary_count(self):
        return len([p for p in self.parts if p.number and p.number <= 4])


def live_disk():
    """Dysk, z którego uruchomiono płytę instalacyjną (nie pokazujemy go na liście)."""
    try:
        src = subprocess.run(["findmnt", "-n", "-o", "SOURCE", "/run/initramfs/live"],
                             capture_output=True, text=True).stdout.strip()
        if not src:
            return None
        pk = subprocess.run(["lsblk", "-no", "PKNAME", src], capture_output=True, text=True).stdout.strip()
        return "/dev/" + pk.splitlines()[0] if pk else src
    except OSError:
        return None


def _blkid(path):
    info = {}
    try:
        out = subprocess.run(["blkid", "-p", "-o", "export", path], capture_output=True, text=True).stdout
        for line in out.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                info[k] = v
    except OSError:
        pass
    return info


def _usage(region):
    """Zajęte miejsce i rozpoznany system (montowanie tylko do odczytu, gdy to szybkie i bezpieczne)."""
    if region.fstype not in ("ext4", "ext3", "ext2", "xfs", "btrfs", "ntfs", "vfat", "exfat"):
        return
    # partycja już zamontowana — korzystamy z bieżącego punktu montowania
    mnt = subprocess.run(["findmnt", "-n", "-o", "TARGET", "-S", region.path], capture_output=True,
                         text=True).stdout.strip().splitlines()
    tmp = None
    try:
        if mnt:
            target = mnt[0]
        else:
            tmp = tempfile.mkdtemp(prefix="hzprobe")
            opts = "ro,noload" if region.fstype in ("ext4", "ext3") else "ro"
            if region.fstype == "xfs":
                opts = "ro,norecovery"
            if region.fstype == "ntfs":
                fs = "ntfs3"
            else:
                fs = region.fstype
            r = subprocess.run(["mount", "-t", fs, "-o", opts, region.path, tmp], capture_output=True, timeout=20)
            if r.returncode != 0 and region.fstype == "ntfs":
                r = subprocess.run(["mount", "-t", "ntfs-3g", "-o", "ro", region.path, tmp], capture_output=True,
                                   timeout=20)
            if r.returncode != 0:
                return
            target = tmp
        st = os.statvfs(target)
        region.used = (st.f_blocks - st.f_bfree) * st.f_frsize
        if os.path.exists(os.path.join(target, "Windows", "System32")) or \
                os.path.exists(os.path.join(target, "WINDOWS", "system32")):
            region.osname = "Windows"
        elif os.path.exists(os.path.join(target, "EFI", "Microsoft")):
            region.osname = "Windows"
        elif os.path.exists(os.path.join(target, "etc", "os-release")) or \
                os.path.exists(os.path.join(target, "root", "etc", "os-release")):
            region.osname = "Linux"
    except (OSError, subprocess.TimeoutExpired):
        pass
    finally:
        if tmp:
            subprocess.run(["umount", tmp], capture_output=True)
            try:
                os.rmdir(tmp)
            except OSError:
                pass


def scan(probe_usage=True):
    """Lista dysków z partycjami i obszarami niepodzielonymi."""
    try:
        out = subprocess.run(["lsblk", "-J", "-b", "-d", "-o", "PATH,TYPE,SIZE,MODEL,TRAN,RO,LOG-SEC"],
                             capture_output=True, text=True).stdout
        devs = json.loads(out).get("blockdevices", [])
    except (OSError, ValueError):
        devs = []
    skip = live_disk()
    test = [d for d in os.environ.get("HORYZONTOS_TEST_DISKS", "").split(",") if d]
    disks = []
    for d in devs:
        path = d.get("path") or ""
        typ = d.get("type")
        if test:
            if path not in test:
                continue
        else:
            if typ != "disk" or str(d.get("ro")) in ("1", "True", "true"):
                continue
            if re.match(r"/dev/(zram|loop|sr|fd|ram)", path) or path == skip:
                continue
        size = int(d.get("size") or 0)
        if size < 1024 * MiB:
            continue
        disk = Disk(len(disks), path, size, d.get("model"), d.get("tran"), int(d.get("log-sec") or 512))
        read_table(disk, probe_usage)
        disks.append(disk)
    return disks


def read_table(disk, probe_usage=True):
    disk.parts = []
    disk.pttype = None
    disk.first, disk.last = MiB, disk.size - MiB
    try:
        p = subprocess.run(["sfdisk", "-J", disk.path], capture_output=True, text=True)
        tab = json.loads(p.stdout)["partitiontable"] if p.returncode == 0 and p.stdout.strip() else None
    except (OSError, ValueError, KeyError):
        tab = None
    if tab:
        disk.pttype = tab.get("label")
        ss = int(tab.get("sectorsize", disk.sector))
        disk.sector = ss
        if disk.pttype == "gpt":
            disk.first = max(MiB, int(tab.get("firstlba", 2048)) * ss)
            disk.last = (int(tab.get("lastlba", disk.size // ss - 34)) + 1) * ss
        for pt in tab.get("partitions", []):
            node = pt["node"]
            m = re.search(r"(\d+)$", node)
            num = int(m.group(1)) if m else None
            r = Region(disk, "part", int(pt["start"]) * ss, int(pt["size"]) * ss, num, node,
                       pt.get("type", ""), pt.get("name", ""))
            info = _blkid(node)
            r.fstype = info.get("TYPE", "")
            r.label = info.get("LABEL", "")
            r.uuid = info.get("UUID", "")
            disk.parts.append(r)
    else:
        info = _blkid(disk.path)
        if info.get("TYPE"):
            # system plików bez tablicy partycji (np. cały dysk jako jedna partycja) — pokazujemy jako całość
            r = Region(disk, "part", 0, disk.size, 0, disk.path, "", "")
            r.fstype = info.get("TYPE", "")
            r.label = info.get("LABEL", "")
            r.whole = True
            disk.parts.append(r)
    if probe_usage:
        for r in disk.parts:
            _usage(r)
    _regions(disk)


def _regions(disk):
    """Partycje + obszary niepodzielone w kolejności na dysku."""
    items = []
    top = [p for p in disk.parts if not (disk.pttype == "dos" and p.number and p.number > 4)]
    logical = [p for p in disk.parts if disk.pttype == "dos" and p.number and p.number > 4]
    pos = disk.first
    for p in sorted(top, key=lambda r: r.start):
        if p.start - pos >= 4 * MiB:
            items.append(Region(disk, "free", align_up(pos), align_down(p.start) - align_up(pos)))
        if p.is_extended:
            items.extend(sorted(logical, key=lambda r: r.start))
        else:
            items.append(p)
        pos = max(pos, p.end)
    if disk.last - pos >= 4 * MiB and not (disk.parts and getattr(disk.parts[0], "whole", False)):
        items.append(Region(disk, "free", align_up(pos), align_down(disk.last) - align_up(pos)))
    disk.regions = [r for r in items if r.size > 0]


def settle(disk_path):
    subprocess.run(["partx", "-u", disk_path], capture_output=True)
    subprocess.run(["udevadm", "settle", "-t", "10"], capture_output=True)
    time.sleep(0.3)


def boot_needs(disk):
    """Jakie partycje startowe trzeba dodać na tym dysku: lista (typ, rozmiar)."""
    need = []
    if is_uefi():
        if not disk.has_esp():
            need.append(("esp", ESP_SIZE))
    elif disk.pttype == "gpt" and not disk.has_biosboot():
        need.append(("biosboot", BIOSBOOT_SIZE))
    return need


def new_label_type():
    return "gpt" if is_uefi() else "dos"


def _ptype(disk, kind):
    gpt = disk.pttype == "gpt"
    return {"esp": GPT_ESP if gpt else "ef", "biosboot": GPT_BIOSBOOT,
            "linux": GPT_LINUX if gpt else "83"}[kind]


def create_partition(disk, free, size, with_boot=True):
    """Tworzy partycję o rozmiarze `size` w obszarze `free`.
    Gdy na dysku brakuje partycji startowej (EFI / BIOS boot), dodaje ją na początku obszaru.
    Zwraca ścieżkę nowej partycji."""
    if disk.pttype is None:
        label = new_label_type()
        run(["wipefs", "-a", disk.path], check=False)
        run(["sfdisk", "--wipe", "always", disk.path], input=f"label: {label}\n")
        settle(disk.path)
        disk.pttype = "gpt" if label == "gpt" else "dos"
        read_table(disk, False)
        free = [r for r in disk.regions if r.is_free][0]
        size = min(size, free.size)
    start = align_up(free.start)
    end_limit = align_down(free.end)
    lines = []
    if with_boot:
        for kind, sz in boot_needs(disk):
            if disk.pttype == "dos" and disk.primary_count() + len(lines) >= 4:
                raise RuntimeError("no-primary")
            lines.append((start, sz, _ptype(disk, kind), kind))
            start += sz
    size = align_down(min(size, end_limit - start))
    if size < 8 * MiB:
        raise RuntimeError("too-small")
    if disk.pttype == "dos" and disk.primary_count() + len(lines) >= 4:
        raise RuntimeError("no-primary")
    lines.append((start, size, _ptype(disk, "linux"), "linux"))
    ss = disk.sector
    script = "".join(f"start={s // ss}, size={n // ss}, type={t}\n" for s, n, t, _ in lines)
    run(["sfdisk", "--append", "--no-reread", "--wipe-partitions", "always", disk.path], input=script)
    settle(disk.path)
    read_table(disk, False)
    newpath = None
    for s, n, t, kind in lines:
        part = next((p for p in disk.parts if abs(p.start - s) < MiB), None)
        if not part:
            raise RuntimeError("partition not visible after creation")
        part.created_here = True
        run(["wipefs", "-a", part.path], check=False)
        if kind == "esp":
            run(["mkfs.fat", "-F", "32", "-n", "EFI", part.path])
        if kind == "linux":
            newpath = part.path
    settle(disk.path)
    read_table(disk, False)
    return newpath


def delete_partition(region):
    disk = region.disk
    if getattr(region, "whole", False):
        run(["wipefs", "-a", disk.path])
    else:
        run(["sfdisk", "--no-reread", "--delete", disk.path, str(region.number)])
        subprocess.run(["partx", "-d", "--nr", str(region.number), disk.path], capture_output=True)
    settle(disk.path)
    read_table(disk, False)


def find_region(disks, path):
    for d in disks:
        for r in d.regions:
            if r.path == path:
                return r
    return None


def unmount_all(path):
    """Odmontowuje partycję (np. zamontowaną automatycznie) przed formatowaniem/usuwaniem."""
    out = subprocess.run(["findmnt", "-rn", "-o", "TARGET", "-S", path], capture_output=True, text=True).stdout
    for t in sorted(out.split(), reverse=True):
        subprocess.run(["umount", "-l", t], capture_output=True)
    subprocess.run(["swapoff", path], capture_output=True)


def zero_fill(path, progress, cancelled=lambda: False):
    """Pełne formatowanie: zapis zer na całej partycji (z postępem 0..1)."""
    size = int(subprocess.run(["blockdev", "--getsize64", path], capture_output=True, text=True).stdout or 0)
    if size <= 0:
        return
    chunk = 4 * MiB
    buf = bytes(chunk)
    done = 0
    fd = os.open(path, os.O_WRONLY)
    try:
        while done < size and not cancelled():
            n = min(chunk, size - done)
            os.write(fd, buf[:n])
            done += n
            if done % (64 * MiB) == 0 or done == size:
                os.fsync(fd)
                progress(done / size)
    finally:
        os.close(fd)


def mkfs(path, fstype, label="HoryzontOS"):
    unmount_all(path)
    run(["wipefs", "-a", path], check=False)
    if fstype == "btrfs":
        run(["mkfs.btrfs", "-f", "-L", label, path])
    elif fstype == "ext4":
        run(["mkfs.ext4", "-F", "-q", "-L", label, path])
    elif fstype == "xfs":
        run(["mkfs.xfs", "-f", "-q", "-L", label[:12], path])
    else:
        raise ValueError(fstype)
