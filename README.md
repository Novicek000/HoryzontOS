# HoryzontOS

System operacyjny oparty na **Fedora Linux 44** z pulpitem [Horyzont Desktop](https://github.com/Novicek000/HoryzontDesktop)
i ekranem powitalnym [Horyzont Logon](https://github.com/Novicek000/HoryzontLogon) — w układzie i stylu pracy
klasycznego pulpitu z początku lat 2000. Instalator działa i wygląda jak klasyczny instalator systemu z tamtych lat.
Cała grafika, teksty i dźwięki są narysowane / napisane od nowa.

*HoryzontOS is a Fedora 43 based OS with the Horyzont desktop and welcome screen. Its installer looks and works like a
classic early-2000s setup program (blue text-mode phase, graphical phase, first-run wizard). Polish and English.*

## Jak przebiega instalacja

1. **Menu płyty** (GRUB, niebieskie tło): *Zainstaluj system HoryzontOS* / *Install HoryzontOS (English)* /
   sprawdzenie nośnika / tryb podstawowej grafiki. Gdy na dysku jest już HoryzontOS, w menu jest też
   *Uruchom system z dysku twardego*.
2. **Część tekstowa** — niebieski ekran 80×30 znaków z czcionką VGA, szary pasek stanu na dole:
   powitanie (ENTER / R = Konsola odzyskiwania / F3), umowa licencyjna (F8), lista dysków i partycji
   (ENTER instaluj, C utwórz, D usuń + L potwierdź), wybór systemu plików (Btrfs / ext4 / XFS, szybkie lub pełne
   formatowanie), żółty pasek kopiowania plików z nazwą pliku na pasku stanu, czerwone odliczanie do restartu.
   Partycja systemowa EFI (UEFI) albo partycja startowa BIOS (GPT + BIOS) jest dodawana automatycznie.
3. **Część graficzna** (po pierwszym restarcie) — niebieskie tło z etapami po lewej i szacowanym czasem,
   klasyczne okno kreatora: Opcje regionalne i językowe, Personalizuj oprogramowanie, Nazwa komputera i hasło
   administratora (root), Ustawienia daty i godziny, Ustawienia sieciowe (typowe / niestandardowe z właściwościami
   TCP/IP), Grupa robocza; potem „Instalowanie elementów menu Start”, „Rejestrowanie składników”… i restart.
4. **Pierwsze uruchomienie** („Witamy w systemie HoryzontOS”, z muzyką): Aktualizacje automatyczne,
   **Jak ten komputer będzie łączył się z Internetem?** (Wi-Fi / sieć lokalna — kabel Ethernet / *Pomiń*):
   lista sieci Wi-Fi z kluczem sieci i siecią ukrytą albo *Ustawienia sieci lokalnej (LAN)* (adres automatyczny
   lub stały IP, maska, brama, serwery DNS), **repozytoria firm trzecich**
   (repozytoria Fedory: Chrome/NVIDIA/Steam, RPM Fusion, kodeki, Flathub), **aktualizacja systemu, Horyzont Desktop
   i Horyzont Logon** od razu po połączeniu, *Kto będzie używać tego komputera?* (do 5 kont), *Dziękujemy!*.
   Jedno konto bez hasła = automatyczne logowanie (jak w klasycznym systemie); inaczej ekran powitalny.

## Budowanie ISO

Na Fedorze 43 (albo w kontenerze `fedora:43` uruchomionym z `--privileged`):

```bash
sudo ./build/build.sh            # wynik: out/HoryzontOS-<wersja>-x86_64.iso (+ .sha256)
```

Potrzeba ok. 15 GB miejsca i połączenia z Internetem (pakiety Fedory, Horyzont z GitHuba).
Etapy można powtarzać osobno: `sudo ./build/build.sh configure squash iso`; same pliki instalatora:
`sudo ./build/build.sh code squash iso`. Na czas testów szybsza kompresja: `SQUASH_LEVEL=3`.
Lokalne kopie pulpitu i ekranu powitalnego: `DESKTOP_SRC=… LOGON_SRC=… sudo ./build/build.sh`.
Inna wersja Fedory / numer wersji: `RELEASEVER=44 HORYZONTOS_VERSION=1.1.0 sudo ./build/build.sh`.

**GitHub Actions:** zakładka *Actions → Zbuduj ISO → Run workflow* buduje obraz i udostępnia go jako artefakt
(przechowywany 14 dni). W oknie *Run workflow* są pola:
- **Wersja Fedory** (np. `43`, `44`, `rawhide`; domyślnie z pliku `FEDORA_VERSION`),
- **Numer wersji HoryzontOS** (np. `1.1.0`; puste = z pliku `VERSION`) — trafia do nazwy ISO, menu płyty i systemu,
- **Dołącz ISO do istniejącego wydania** (tag, np. `v1.0.0`) — buduje z gałęzi `main` i podmienia ISO w tym wydaniu.

Horyzont Desktop i Horyzont Logon są zawsze pobierane w najnowszej wersji (gałąź `main`), a pakiety Fedory
ze wszystkimi aktualizacjami z dnia budowania. Przy wydaniu (Release) numer wersji bierze się z tagu (`v1.1.0` → `1.1.0`).
Opublikowanie wydania (Release) dołącza ISO do wydania. **Wydanie buduje kod z commitu, na który wskazuje tag** —
przy nowym wydaniu twórz nowy tag (np. `v1.0.1`) z gałęzi `main`, nie wybieraj starego tagu.
Obraz ≥ 2 GiB (limit GitHuba) byłby podzielony na części: `cat HoryzontOS-*.iso.part* > HoryzontOS.iso`.

Nagrywanie na pendrive: `sudo dd if=HoryzontOS-1.0.0-x86_64.iso of=/dev/sdX bs=4M status=progress oflag=sync`
(albo Fedora Media Writer / Ventoy / Rufus w trybie DD). Obraz uruchamia się w trybie BIOS i UEFI (także z Secure Boot).

## Struktura

| Ścieżka | Zawartość |
|---|---|
| `build/build.sh` | budowanie: pakiety (dnf), Horyzont, konfiguracja, squashfs, ISO (GRUB BIOS + shim/GRUB UEFI) |
| `build/packages.txt` | lista pakietów systemu |
| `build/make-art.py` | motywy plymouth (ekran startowy, ekran ładowania instalatora), muzyka powitalna |
| `horyzontos/textsetup/` | tekstowa część instalatora (Qt + czcionka konsoli PSF, działa na linuxfb/DRM) |
| `horyzontos/common/` | dyski i partycje, kopiowanie systemu, GRUB, fstab |
| `horyzontos/setup/` | graficzna część instalatora i czynności systemowe |
| `horyzontos/oobe/` | pierwsze uruchomienie |
| `share/` | usługi systemd, skrypty sesji |
| `tools/vm.py` | testy w QEMU (zrzuty ekranu, klawisze, mysz przez QMP) |

Podgląd w zainstalowanym systemie (bez zmian w systemie):
`HORYZONTOS_DRYRUN=1 horyzontos-setup gui-setup --window` albo `… oobe --window`.

## Licencja

GPL-3.0-or-later. Fedora jest znakiem towarowym Red Hat, Inc.; HoryzontOS nie jest związany z firmą Microsoft
ani z projektem Fedora.
