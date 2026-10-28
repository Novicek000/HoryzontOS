#!/bin/bash
# Budowanie obrazu ISO systemu HoryzontOS.
#
# Uruchamiaj jako root na Fedorze 43 (albo w kontenerze fedora:43 z --privileged), np.:
#   sudo ./build/build.sh                    # wszystko: system plików, konfiguracja, squashfs, ISO
#   sudo ./build/build.sh configure squash iso   # tylko wybrane etapy (rootfs musi już istnieć)
#   sudo ./build/build.sh code squash iso        # tylko nowe pliki instalatora/konfiguratora
#
# Zmienne:
#   WORK=/var/tmp/horyzontos-build    katalog roboczy (potrzeba ~15 GB)
#   OUT=./out                         gdzie zapisać ISO
#   DESKTOP_SRC / LOGON_SRC           lokalne kopie HoryzontDesktop / HoryzontLogon
#                                     (domyślnie pobierane z GitHuba, gałąź main)
#   RELEASEVER=43                     wersja Fedory
#   HORYZONTOS_VERSION=1.1.0          numer wersji HoryzontOS (domyślnie z pliku VERSION)
set -euo pipefail
umask 022

SRC="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${WORK:-/var/tmp/horyzontos-build}"
OUT="${OUT:-$SRC/out}"
RELEASEVER="${RELEASEVER:-$(cat "$SRC/FEDORA_VERSION" 2>/dev/null || echo 43)}"
ROOT="$WORK/rootfs"
ISO="$WORK/iso"
# HORYZONTOS_VERSION — numer wersji HoryzontOS (domyślnie z pliku VERSION)
VERSION="${HORYZONTOS_VERSION:-$(cat "$SRC/VERSION")}"
case "$VERSION" in *[!A-Za-z0-9.+_-]*|"") echo "Nieprawidłowy numer wersji: $VERSION" >&2; exit 1;; esac
case "$RELEASEVER" in *[!0-9]*|"") [ "$RELEASEVER" = rawhide ] || { echo "Nieprawidłowa wersja Fedory: $RELEASEVER" >&2; exit 1; };; esac
LABEL="HORYZONTOS"
ISONAME="HoryzontOS-$VERSION-x86_64.iso"

say() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" = 0 ] || die "Uruchom jako root."

STAGES="${*:-deps rootfs configure squash iso}"

host_deps() {
    say "Narzędzia do budowania"
    dnf -y install --skip-unavailable squashfs-tools xorriso grub2-tools grub2-tools-extra grub2-pc-modules \
        grub2-efi-x64 grub2-efi-x64-modules shim-x64 dosfstools mtools policycoreutils git rsync \
        python3-pyside6 qt6-qtsvg >/dev/null
}

mount_chroot() {
    for d in proc sys dev dev/pts run; do mkdir -p "$ROOT/$d"; done
    mountpoint -q "$ROOT/proc" || mount -t proc proc "$ROOT/proc"
    mountpoint -q "$ROOT/sys" || mount -t sysfs sys "$ROOT/sys"
    mountpoint -q "$ROOT/dev" || mount --bind /dev "$ROOT/dev"
    mountpoint -q "$ROOT/dev/pts" || mount --bind /dev/pts "$ROOT/dev/pts"
    mountpoint -q "$ROOT/run" || mount -t tmpfs tmpfs "$ROOT/run"
}

umount_chroot() {
    mountpoint -q "$ROOT/etc/pki" && umount "$ROOT/etc/pki" || true
    for d in run dev/pts dev sys proc; do
        mountpoint -q "$ROOT/$d" && umount -l "$ROOT/$d" || true
    done
}
trap umount_chroot EXIT

PROXYENV=""
in_root() { chroot "$ROOT" /usr/bin/env -i HOME=/root PATH=/usr/sbin:/usr/bin:/sbin:/bin LANG=C.UTF-8 TERM=dumb $PROXYENV "$@"; }

stage_rootfs() {
    say "Instalowanie pakietów Fedory $RELEASEVER do $ROOT"
    rm -rf "$ROOT"
    mkdir -p "$ROOT"
    local req="" opt=""
    while read -r line; do
        line="${line%%#*}"; line="$(echo "$line" | xargs)"
        [ -z "$line" ] && continue
        case "$line" in
            \?*) opt="$opt ${line#\?}";;
            *) req="$req $line";;
        esac
    done < "$SRC/build/packages.txt"
    local common=(--installroot="$ROOT" --releasever="$RELEASEVER" --use-host-config -y
                  --setopt=install_weak_deps=False --setopt=tsflags=nodocs --setopt=keepcache=True)
    # tsflags=nodocs zostawia strony man poza obrazem; dokumentacja licencji zostaje
    dnf install "${common[@]}" $req
    say "Pakiety opcjonalne"
    dnf install "${common[@]}" --skip-unavailable $opt || true
    for p in $opt; do rpm --root "$ROOT" -q "$p" >/dev/null 2>&1 || echo "   (pominięty: $p)"; done
}

install_horyzont_component() {
    # $1 = nazwa repozytorium na GitHubie, $2 = lokalna kopia (opcjonalnie), $3 = argumenty install.sh
    local repo="$1" local_src="$2"; shift 2
    local dst="$ROOT/var/tmp/$repo"
    rm -rf "$dst"
    if [ -n "$local_src" ] && [ -d "$local_src" ]; then
        cp -r "$local_src" "$dst"
        rm -rf "$dst/.git"
    else
        git clone -q --depth 1 "https://github.com/Novicek000/$repo" "$dst"
        rm -rf "$dst/.git"
    fi
    in_root bash -c "cd /var/tmp/$repo && ./install.sh $*" | sed 's/^/   /'
    rm -rf "$dst"
}

install_horyzontos_files() {
    rm -rf "$ROOT/usr/share/horyzontos"
    mkdir -p "$ROOT/usr/share/horyzontos" "$ROOT/usr/libexec/horyzontos"
    cp -r "$SRC/horyzontos" "$ROOT/usr/share/horyzontos/"
    find "$ROOT/usr/share/horyzontos" -name __pycache__ -prune -exec rm -rf {} +
    echo "$VERSION" > "$ROOT/usr/share/horyzontos/VERSION"
    cp -r "$SRC/share/licenses" "$ROOT/usr/share/horyzontos/" 2>/dev/null || true
    install -m755 "$SRC"/share/libexec/* "$ROOT/usr/libexec/horyzontos/"
    install -m644 "$SRC"/share/systemd/* "$ROOT/usr/lib/systemd/system/"
    install -m755 "$SRC/share/bin/horyzontos-setup" "$ROOT/usr/bin/horyzontos-setup"
    mkdir -p "$ROOT/usr/share/sounds/horyzontos"
    cp "$SRC"/share/sounds/* "$ROOT/usr/share/sounds/horyzontos/" 2>/dev/null || true
    in_root python3 -m compileall -q /usr/share/horyzontos >/dev/null || true

    cat > "$ROOT/etc/horyzontos-release" <<EOF
NAME="HoryzontOS"
VERSION="$VERSION"
BASE="Fedora Linux $RELEASEVER"
BUILD_DATE="$(date -u +%Y-%m-%d)"
EOF

}

stage_configure() {
    [ -x "$ROOT/usr/bin/bash" ] || die "Brak systemu plików — najpierw etap rootfs."
    mount_chroot
    cp /etc/resolv.conf "$ROOT/etc/resolv.conf.build" 2>/dev/null || true

    # przy budowaniu za serwerem proxy: dnf w chroot korzysta z certyfikatów i proxy hosta (tylko na czas instalacji)
    if [ -n "${HTTPS_PROXY:-}" ]; then
        mount --bind /etc/pki "$ROOT/etc/pki"
        PROXYENV="HTTPS_PROXY=$HTTPS_PROXY https_proxy=$HTTPS_PROXY"
    fi
    say "Instalowanie Horyzont Desktop"
    install_horyzont_component HoryzontDesktop "${DESKTOP_SRC:-}" ""
    say "Instalowanie Horyzont Logon (ekran powitalny)"
    install_horyzont_component HoryzontLogon "${LOGON_SRC:-}" "--yes"

    if [ -n "$PROXYENV" ]; then umount "$ROOT/etc/pki"; PROXYENV=""; fi

    say "Instalowanie HoryzontOS (instalator, konfigurator, motyw startowy)"
    install_horyzontos_files

    say "Motyw startowy (plymouth) i GRUB"
    python3 "$SRC/build/make-art.py" "$ROOT" "$VERSION"
    in_root plymouth-set-default-theme horyzont >/dev/null 2>&1 || \
        sed -i 's/^Theme=.*/Theme=horyzont/' "$ROOT/etc/plymouth/plymouthd.conf"
    cat > "$ROOT/etc/default/grub" <<'EOF'
GRUB_TIMEOUT=3
GRUB_DISTRIBUTOR="HoryzontOS"
GRUB_DEFAULT=saved
GRUB_DISABLE_SUBMENU=true
GRUB_TERMINAL_OUTPUT="console"
GRUB_CMDLINE_LINUX="rhgb quiet"
GRUB_DISABLE_RECOVERY="true"
GRUB_ENABLE_BLSCFG=true
GRUB_DISABLE_OS_PROBER=false
EOF

    say "Usuwanie zbędnych pakietów i plików"
    in_root rpm -e --nodeps dracut-config-generic dracut-config-rescue >/dev/null 2>&1 || true
    rm -f "$ROOT"/boot/*-rescue-* 2>/dev/null || true
    in_root systemd-hwdb update >/dev/null 2>&1 || true

    say "Ustawienia domyślne systemu"
    echo 'LANG="pl_PL.UTF-8"' > "$ROOT/etc/locale.conf"
    printf 'KEYMAP="pl2"\nFONT="eurlatgr"\n' > "$ROOT/etc/vconsole.conf"
    mkdir -p "$ROOT/etc/X11/xorg.conf.d"
    cat > "$ROOT/etc/X11/xorg.conf.d/00-keyboard.conf" <<'EOF'
Section "InputClass"
        Identifier "system-keyboard"
        MatchIsKeyboard "on"
        Option "XkbLayout" "pl"
EndSection
EOF
    ln -sf ../usr/share/zoneinfo/Europe/Warsaw "$ROOT/etc/localtime"
    echo horyzont > "$ROOT/etc/hostname"
    # Fedora ma zwykle konto root zablokowane; ustawi je (lub nie) instalator
    in_root passwd -l root >/dev/null 2>&1 || true
    # grupy dla pierwszego konta (sudo/pkexec) są w Fedorze w wheel
    in_root systemctl set-default graphical.target
    in_root systemctl enable NetworkManager bluetooth cups.socket firewalld chronyd >/dev/null 2>&1 || true
    in_root systemctl disable horyzontos-setup.service >/dev/null 2>&1 || true
    # flathub jako źródło jest dodawane dopiero w konfiguratorze (repozytoria firm trzecich)
    # dnf: szybsze pobieranie
    grep -q '^max_parallel_downloads' "$ROOT/etc/dnf/dnf.conf" 2>/dev/null || \
        printf 'max_parallel_downloads=10\n' >> "$ROOT/etc/dnf/dnf.conf"

    say "Initramfs (ogólny, z obsługą płyty instalacyjnej)"
    local kver
    kver="$(ls "$ROOT/lib/modules" | sort -V | tail -1)"
    cp "$ROOT/lib/modules/$kver/vmlinuz" "$ROOT/boot/vmlinuz-$kver"
    rm -f "$ROOT"/boot/initramfs-*.img "$ROOT"/boot/loader/entries/*.conf
    # sterowniki nouveau/amdgpu (z ponad 100 MB oprogramowania układowego) ładują się dopiero z systemu na dysku
    in_root dracut -f --no-hostonly --add "dmsquash-live plymouth" --omit "nfs iscsi fcoe multipath" \
        --omit-drivers "nouveau amdgpu radeon" \
        --kver "$kver" "/boot/initramfs-$kver.img" 2>&1 | tail -2
    echo "$kver" > "$WORK/kver"

    say "Sprzątanie"
    rm -f "$ROOT/etc/resolv.conf.build"
    rm -rf "$ROOT"/var/cache/dnf/* "$ROOT"/var/cache/libdnf5/* "$ROOT"/var/lib/dnf/repos/* \
        "$ROOT"/var/log/*.log "$ROOT"/var/tmp/* "$ROOT"/tmp/* "$ROOT"/root/.cache
    find "$ROOT/var/log" -type f -delete 2>/dev/null || true
    rm -f "$ROOT"/etc/ssh/ssh_host_* 2>/dev/null || true
    : > "$ROOT/etc/machine-id"
    rm -f "$ROOT/var/lib/systemd/random-seed" "$ROOT/var/lib/systemd/credential.secret"
    umount_chroot

    say "Etykiety SELinux"
    setfiles -F -r "$ROOT" "$ROOT/etc/selinux/targeted/contexts/files/file_contexts" "$ROOT" 2>&1 | tail -3 || \
        echo "   (nie udało się nadać etykiet — instalator zrobi to sam)"
    # liczba plików — do paska postępu kopiowania w instalatorze
    find "$ROOT" -xdev | wc -l > "$WORK/filecount"
}

stage_code() {
    # tylko pliki HoryzontOS (instalator, konfigurator) — bez ponownej instalacji pakietów
    [ -d "$ROOT/usr/share/horyzontos" ] || die "Brak systemu plików — najpierw etapy rootfs i configure."
    say "Odświeżanie plików HoryzontOS w $ROOT"
    install_horyzontos_files
    setfiles -F -r "$ROOT" "$ROOT/etc/selinux/targeted/contexts/files/file_contexts" \
        "$ROOT/usr/share/horyzontos" "$ROOT/usr/libexec/horyzontos" "$ROOT/usr/lib/systemd/system" \
        "$ROOT/usr/bin/horyzontos-setup" "$ROOT/etc/horyzontos-release" 2>&1 | tail -3 || true
    find "$ROOT" -xdev | wc -l > "$WORK/filecount"
}

stage_squash() {
    say "Tworzenie squashfs (to potrwa)"
    mkdir -p "$ISO/LiveOS"
    rm -f "$ISO/LiveOS/squashfs.img"
    mksquashfs "$ROOT" "$ISO/LiveOS/squashfs.img" -comp zstd -Xcompression-level "${SQUASH_LEVEL:-19}" -b 1M \
        -noappend -xattrs -e proc sys dev run tmp -quiet -progress >/dev/null
    cp "$WORK/filecount" "$ISO/LiveOS/filecount"
    du -sb --exclude=proc --exclude=sys --exclude=dev "$ROOT" | cut -f1 > "$ISO/LiveOS/rootsize"
    du -sh "$ISO/LiveOS/squashfs.img"
}

stage_iso() {
    local kver; kver="$(cat "$WORK/kver")"
    say "Pliki startowe płyty (BIOS + UEFI)"
    rm -rf "$ISO/EFI" "$ISO/boot" "$ISO/images"
    mkdir -p "$ISO/images/pxeboot" "$ISO/EFI/BOOT" "$ISO/boot/grub2/i386-pc" "$ISO/boot/grub2/fonts"
    cp "$ROOT/boot/vmlinuz-$kver" "$ISO/images/pxeboot/vmlinuz"
    cp "$ROOT/boot/initramfs-$kver.img" "$ISO/images/pxeboot/initrd.img"

    # konfiguracja menu (taka sama dla BIOS i UEFI)
    # EXTRA_CMDLINE — dodatkowe parametry jądra (np. do testów: console=ttyS0 systemd.journald.forward_to_console=1)
    local gsed="s/@LABEL@/$LABEL/g; s/@VERSION@/$VERSION/g; s|@EXTRA@|${EXTRA_CMDLINE:-}|g"
    sed "$gsed" "$SRC/build/iso/grub.cfg" > "$ISO/EFI/BOOT/grub.cfg"
    sed "$gsed" "$SRC/build/iso/grub.cfg" > "$ISO/boot/grub2/grub.cfg"
    cp "$ROOT/usr/share/grub/unicode.pf2" "$ISO/boot/grub2/fonts/" 2>/dev/null || true
    cp "$ROOT/usr/share/grub/unicode.pf2" "$ISO/EFI/BOOT/" 2>/dev/null || true
    # motyw menu (wygląd instalatora tekstowego); napisy wstawiane tutaj, żeby plik theme.txt był wspólny
    local th="$ISO/boot/grub2/themes/horyzontos"
    rm -rf "$th"; mkdir -p "$th"
    cp "$SRC"/build/iso/theme/*.png "$th/"
    theme_txt() {  # $1 plik, potem: tytuł, linia1, linia2, linia3, odliczanie, klawisze
        local f="$1"; shift
        sed -e "s|@TITLE@|$1|" -e "s|@L1@|$2|" -e "s|@L2@|$3|" -e "s|@L3@|$4|" -e "s|@TIMEOUT@|$5|" \
            -e "s|@KEYS@|$6|" "$SRC/build/iso/theme/theme.txt" > "$f"
    }
    theme_txt "$th/theme.txt" "Instalator systemu HoryzontOS $VERSION" "Witamy w Instalatorze." \
        "Użyj klawiszy STRZAŁKA W GÓRĘ i STRZAŁKA W DÓŁ, aby wybrać element z listy," \
        "a następnie naciśnij klawisz ENTER.   (English: choose the second item.)" \
        "Instalator zostanie uruchomiony automatycznie za %d s..." \
        "ENTER=Wybierz  E=Edytuj polecenia  C=Wiersz poleceń"

    # UEFI: shim + podpisany GRUB Fedory (działa z Secure Boot)
    cp "$ROOT/boot/efi/EFI/BOOT/BOOTX64.EFI" "$ISO/EFI/BOOT/BOOTX64.EFI"
    cp "$ROOT/boot/efi/EFI/fedora/grubx64.efi" "$ISO/EFI/BOOT/grubx64.efi"
    cp "$ROOT/boot/efi/EFI/fedora/mmx64.efi" "$ISO/EFI/BOOT/mmx64.efi" 2>/dev/null || true
    rm -f "$ISO/images/efiboot.img"
    # rozmiar obrazu FAT wg plików (nowsze wydania Fedory mają większe shim/GRUB) + zapas
    local efikb; efikb=$(( $(du -sk "$ISO/EFI/BOOT" | cut -f1) + 2048 ))
    [ "$efikb" -lt 8192 ] && efikb=8192
    mkfs.msdos -C -n EFIBOOT "$ISO/images/efiboot.img" "$efikb" >/dev/null
    mmd -i "$ISO/images/efiboot.img" ::/EFI ::/EFI/BOOT
    mcopy -i "$ISO/images/efiboot.img" "$ISO"/EFI/BOOT/* ::/EFI/BOOT/

    # BIOS: GRUB i386-pc z El Torito + MBR dla pendrive'ów
    local gm="$ROOT/usr/lib/grub/i386-pc"
    cp "$gm"/*.mod "$gm"/*.lst "$ISO/boot/grub2/i386-pc/"
    grub2-mkimage -d "$gm" -O i386-pc-eltorito -p /boot/grub2 -o "$ISO/boot/grub2/i386-pc/eltorito.img" \
        biosdisk iso9660 part_gpt part_msdos fat ext2 normal search search_label configfile linux \
        gfxterm gfxmenu all_video font echo test sleep ls cat chain reboot halt
    cp "$gm/boot_hybrid.img" "$WORK/boot_hybrid.img"

    say "Tworzenie $ISONAME"
    mkdir -p "$OUT"
    xorriso -as mkisofs -o "$OUT/$ISONAME" -R -J -joliet-long -V "$LABEL" -volset "$LABEL" -iso-level 3 \
        -b boot/grub2/i386-pc/eltorito.img -no-emul-boot -boot-load-size 4 -boot-info-table \
        --grub2-boot-info --grub2-mbr "$WORK/boot_hybrid.img" \
        -eltorito-alt-boot -e images/efiboot.img -no-emul-boot \
        -append_partition 2 0xef "$ISO/images/efiboot.img" -appended_part_as_gpt \
        -graft-points "$ISO" 2>&1 | grep -v "^xorriso : UPDATE" | tail -3
    (cd "$OUT" && sha256sum "$ISONAME" > "$ISONAME.sha256")
    ls -lh "$OUT/$ISONAME"
}

for s in $STAGES; do
    case "$s" in
        deps) host_deps;;
        rootfs) stage_rootfs;;
        configure) stage_configure;;
        code) stage_code;;
        squash) stage_squash;;
        iso) stage_iso;;
        *) die "Nieznany etap: $s";;
    esac
done
say "Gotowe."
