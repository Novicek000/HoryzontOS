"""Tekstowa część instalatora HoryzontOS (uruchamiana z płyty / pendrive'a).

Ekrany: ładowanie → powitanie → umowa licencyjna → lista partycji (tworzenie / usuwanie) → formatowanie →
kopiowanie plików → przygotowanie pierwszego uruchomienia → ponowne uruchomienie komputera."""
import os
import sys
import threading
import time
import traceback

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from .. import i18n
from ..common import disks, install
from ..i18n import T
from .screen import BLACK, BLUE, GRAY, RED, WHITE, YELLOW, TextView

EXIT_REBOOT, EXIT_QUIT, EXIT_CONSOLE = 0, 3, 10

LOG = "/tmp/horyzontos-install.log"


def wrap(text, width):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for w in para.split(" "):
            if not cur:
                cur = w
            elif len(cur) + 1 + len(w) <= width:
                cur += " " + w
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


class Screen:
    status = ""
    status_right = ""

    def __init__(self, app):
        self.app = app

    @property
    def g(self):
        return self.app.grid

    def enter(self):
        pass

    def draw(self):
        pass

    def key(self, k, txt):
        pass

    def tick(self):
        """Wywoływane co 100 ms (animacje, postęp)."""
        return False

    # --- pomocnicze
    def header(self):
        t = T("Instalator systemu HoryzontOS", "HoryzontOS Setup")
        self.g.put(1, 1, t)
        self.g.put(0, 2, "═" * (len(t) + 3))

    def para(self, x, y, text, fg=GRAY, width=None):
        width = width or min(70 - x, self.g.cols - x - 2)
        for line in wrap(text, width):
            self.g.put(x, y, line, fg)
            y += 1
        return y

    def bullet(self, y, text, x=6):
        self.g.put(x, y, "•")
        return self.para(x + 3, y, text, width=min(54 - x, self.g.cols - x - 5))


# ====================================================================== ekrany
class LoadingScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.status = T("Instalator sprawdza konfigurację sprzętu komputera...",
                        "Setup is inspecting your computer's hardware configuration...")
        self.done = False

    def enter(self):
        def work():
            try:
                self.app.disks = disks.scan()
            except Exception as e:
                disks.log("błąd skanowania:", traceback.format_exc())
                self.app.disks = []
            self.done = True
        threading.Thread(target=work, daemon=True).start()
        self.t0 = time.monotonic()

    def draw(self):
        g = self.g
        t = T("Instalator systemu HoryzontOS", "HoryzontOS Setup")
        g.put(1, 1, t)
        g.put(0, 2, "═" * (len(t) + 3))

    def tick(self):
        if self.done and time.monotonic() - self.t0 > 1.5:
            self.app.go(WelcomeScreen(self.app))
        return False


class WelcomeScreen(Screen):
    status = property(lambda s: T("  ENTER=Kontynuuj  R=Napraw  F3=Zakończ", "  ENTER=Continue  R=Repair  F3=Quit"))

    def draw(self):
        self.header()
        y = self.para(3, 4, T("Witamy w Instalatorze.", "Welcome to Setup."), WHITE)
        y = self.para(3, y + 1, T("Ta część programu Instalator przygotowuje system HoryzontOS do uruchomienia "
                                  "na tym komputerze.",
                                  "This portion of the Setup program prepares HoryzontOS to run on your computer."))
        y = self.bullet(y + 2, T("Aby zainstalować teraz system HoryzontOS, naciśnij klawisz ENTER.",
                                 "To set up HoryzontOS now, press ENTER."))
        y = self.bullet(y + 1, T("Aby naprawić zainstalowany system HoryzontOS przy użyciu Konsoli "
                                 "odzyskiwania (wiersza poleceń administratora), naciśnij klawisz R.",
                                 "To repair a HoryzontOS installation using Recovery Console (an administrator "
                                 "command prompt), press R."))
        self.bullet(y + 1, T("Aby zakończyć pracę Instalatora bez instalowania systemu HoryzontOS, naciśnij "
                             "klawisz F3.", "To quit Setup without installing HoryzontOS, press F3."))

    def key(self, k, txt):
        if k == "ENTER":
            self.app.go(LicenseScreen(self.app))
        elif k == "R":
            self.app.finish(EXIT_CONSOLE)
        elif k == "F3":
            self.app.go(QuitScreen(self.app, self))


class QuitScreen(Screen):
    status = property(lambda s: T("  F3=Zakończ  ENTER=Kontynuuj", "  F3=Quit  ENTER=Continue"))

    def __init__(self, app, back):
        super().__init__(app)
        self.back = back

    def draw(self):
        self.back.draw()
        g = self.g
        w = 62
        x = (min(g.cols, 80) - w) // 2
        lines = wrap(T("System HoryzontOS nie jest całkowicie zainstalowany na tym komputerze. Jeśli zakończysz "
                       "pracę Instalatora teraz, trzeba będzie uruchomić go ponownie, aby zainstalować system.",
                       "HoryzontOS is not completely set up on your computer. If you quit Setup now, you will "
                       "need to run Setup again to set up HoryzontOS."), w - 6)
        b1 = wrap("•  " + T("Aby kontynuować pracę Instalatora, naciśnij klawisz ENTER.",
                           "To continue Setup, press ENTER."), w - 9)
        b2 = wrap("•  " + T("Aby zakończyć pracę Instalatora, naciśnij klawisz F3.", "To quit Setup, press F3."), w - 9)
        h = len(lines) + len(b1) + len(b2) + 6
        y = max(4, (g.rows - h) // 2)
        g.box(x, y, w, h, WHITE, GRAY, double=True)
        yy = y + 2
        for ln in lines:
            g.put(x + 3, yy, ln, BLACK, GRAY)
            yy += 1
        yy += 1
        for bl in (b1, b2):
            for i, ln in enumerate(bl):
                g.put(x + 5 + (0 if i == 0 else 3), yy, ln, BLACK, GRAY)
                yy += 1

    def key(self, k, txt):
        if k == "F3":
            self.app.finish(EXIT_QUIT)
        elif k in ("ENTER", "ESC"):
            self.app.go(self.back)


LICENSE_PL = """UMOWA LICENCYJNA SYSTEMU HORYZONTOS

WAŻNE — PRZECZYTAJ UWAŻNIE: Niniejsza Umowa dotyczy systemu operacyjnego HoryzontOS w wersji {ver}, w tym środowiska pulpitu Horyzont Desktop, ekranu powitalnego Horyzont Logon, Instalatora i pozostałych dołączonych programów (dalej „Oprogramowanie”).

1. CZYM JEST HORYZONTOS. HoryzontOS jest zbiorem wolnego oprogramowania opartym na systemie Fedora Linux. Nie jest produktem firmy Microsoft ani projektu Fedora i nie jest przez nie wspierany ani zatwierdzany. Wygląd klasycznego pulpitu został narysowany od nowa — Oprogramowanie nie zawiera grafiki, dźwięków ani kodu systemu Windows.

2. LICENCJE. Każdy składnik Oprogramowania jest udostępniany na warunkach własnej licencji (m.in. GNU GPL, GNU LGPL, MIT, BSD, Apache, Mozilla Public License). Teksty licencji znajdziesz po instalacji w folderze /usr/share/licenses. Niniejsza Umowa nie ogranicza praw, które dają Ci te licencje.

3. CO MOŻESZ ROBIĆ. Możesz instalować Oprogramowanie na dowolnej liczbie komputerów, używać go do dowolnych celów, kopiować je, rozpowszechniać oraz zmieniać, o ile przestrzegasz licencji poszczególnych składników.

4. ZNAKI TOWAROWE. Fedora jest znakiem towarowym firmy Red Hat, Inc. Windows i Windows XP są znakami towarowymi firmy Microsoft Corporation. Pozostałe nazwy należą do ich właścicieli i są użyte wyłącznie w celach informacyjnych.

5. AKTUALIZACJE I OPROGRAMOWANIE FIRM TRZECICH. Po instalacji system może pobierać aktualizacje z repozytoriów Fedory oraz z serwisu GitHub (Horyzont Desktop, Horyzont Logon). Repozytoria firm trzecich (np. RPM Fusion, Flathub, Google Chrome, sterowniki NVIDIA) włączysz tylko wtedy, gdy wybierzesz to w konfiguratorze. Za oprogramowanie z tych źródeł odpowiadają ich autorzy, a jego licencje mogą być inne niż licencje wolnego oprogramowania.

6. BRAK GWARANCJI. OPROGRAMOWANIE JEST DOSTARCZANE „TAKIE, JAKIE JEST”, BEZ JAKIEJKOLWIEK GWARANCJI, WYRAŹNEJ LUB DOROZUMIANEJ, W TYM GWARANCJI PRZYDATNOŚCI HANDLOWEJ LUB PRZYDATNOŚCI DO OKREŚLONEGO CELU. W ŻADNYM WYPADKU AUTORZY NIE PONOSZĄ ODPOWIEDZIALNOŚCI ZA JAKIEKOLWIEK SZKODY, W TYM UTRATĘ DANYCH, WYNIKAJĄCE Z UŻYWANIA OPROGRAMOWANIA, W ZAKRESIE DOZWOLONYM PRZEZ PRAWO.

7. KOPIA ZAPASOWA. Instalacja może usunąć dane z wybranej partycji. Przed kontynuowaniem wykonaj kopię zapasową ważnych plików.

8. KOD ŹRÓDŁOWY. Kod źródłowy HoryzontOS jest dostępny pod adresem github.com/Novicek000/HoryzontOS, a kod składników Fedory — w repozytoriach źródłowych projektu Fedora.

Naciśnięcie klawisza F8 oznacza akceptację warunków niniejszej Umowy."""

LICENSE_EN = """HORYZONTOS LICENSE AGREEMENT

IMPORTANT — READ CAREFULLY: This Agreement covers the HoryzontOS operating system version {ver}, including the Horyzont Desktop environment, the Horyzont Logon welcome screen, Setup and the other included programs (the "Software").

1. WHAT HORYZONTOS IS. HoryzontOS is a collection of free software based on Fedora Linux. It is not a product of Microsoft or of the Fedora Project and is not supported or endorsed by them. The classic desktop look was drawn from scratch — the Software contains no Windows artwork, sounds or code.

2. LICENSES. Each component of the Software is provided under its own license (including the GNU GPL, GNU LGPL, MIT, BSD, Apache and Mozilla Public License). After installation the license texts are in /usr/share/licenses. This Agreement does not limit the rights those licenses give you.

3. WHAT YOU MAY DO. You may install the Software on any number of computers, use it for any purpose, copy, distribute and modify it, provided you follow the licenses of the individual components.

4. TRADEMARKS. Fedora is a trademark of Red Hat, Inc. Windows and Windows XP are trademarks of Microsoft Corporation. Other names belong to their owners and are used for information only.

5. UPDATES AND THIRD-PARTY SOFTWARE. After installation the system can download updates from the Fedora repositories and from GitHub (Horyzont Desktop, Horyzont Logon). Third-party repositories (e.g. RPM Fusion, Flathub, Google Chrome, NVIDIA drivers) are enabled only if you choose so in the setup wizard. Software from those sources is the responsibility of its authors and may be under non-free licenses.

6. NO WARRANTY. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING THE WARRANTIES OF MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE. IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY DAMAGES, INCLUDING LOSS OF DATA, ARISING FROM THE USE OF THE SOFTWARE, TO THE EXTENT PERMITTED BY LAW.

7. BACKUP. Installation may erase the data on the selected partition. Back up your important files before you continue.

8. SOURCE CODE. The HoryzontOS source code is available at github.com/Novicek000/HoryzontOS and the source of the Fedora components in the Fedora Project's source repositories.

Pressing F8 means that you accept the terms of this Agreement."""


class LicenseScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.top = 0
        self.declined = False

    @property
    def status(self):
        if self.declined:
            return T("  F3=Zakończ  ESC=Powrót do umowy", "  F3=Quit  ESC=Back to the agreement")
        return T("  F8=Zgadzam się  ESC=Nie zgadzam się  PAGE DOWN=Następna strona",
                 "  F8=I agree  ESC=I do not agree  PAGE DOWN=Next Page")

    def lines(self):
        from .. import version
        text = T(LICENSE_PL, LICENSE_EN).format(ver=version())
        return wrap(text, self.width() - 4)

    def width(self):
        return min(76, self.g.cols - 4)

    def draw(self):
        g = self.g
        t = T("Umowa licencyjna systemu HoryzontOS", "HoryzontOS Licensing Agreement")
        g.put(1, 1, t)
        g.put(0, 2, "═" * (len(t) + 3))
        if self.declined:
            y = self.para(3, 4, T("Nie zaakceptowano Umowy licencyjnej. Aby zainstalować system HoryzontOS, "
                                  "musisz zaakceptować jej warunki.",
                                  "You did not accept the License Agreement. To set up HoryzontOS you must accept it."))
            y = self.bullet(y + 1, T("Aby zakończyć pracę Instalatora, naciśnij klawisz F3.", "To quit Setup, press F3."))
            self.bullet(y + 1, T("Aby ponownie przeczytać Umowę, naciśnij klawisz ESC.",
                                 "To read the Agreement again, press ESC."))
            return
        w = self.width()
        x = 2
        h = g.rows - 6
        g.box(x, 4, w, h, GRAY, BLUE)
        lines = self.lines()
        vis = h - 2
        for i in range(vis):
            j = self.top + i
            if j < len(lines):
                fg = WHITE if j == 0 else GRAY
                g.put(x + 2, 5 + i, lines[j], fg)

    def key(self, k, txt):
        if self.declined:
            if k == "F3":
                self.app.finish(EXIT_QUIT)
            elif k == "ESC":
                self.declined = False
                self.app.redraw()
            return
        vis = self.g.rows - 8
        n = len(self.lines())
        if k == "F8":
            self.app.go(PartitionScreen(self.app))
        elif k == "ESC":
            self.declined = True
            self.app.redraw()
        elif k in ("PGDN", "DOWN", " "):
            step = vis if k != "DOWN" else 1
            self.top = min(max(0, n - vis), self.top + step)
            self.app.redraw()
        elif k in ("PGUP", "UP"):
            step = vis if k == "PGUP" else 1
            self.top = max(0, self.top - step)
            self.app.redraw()


# ---------------------------------------------------------------------- partycje
def part_line(r, width):
    """Wiersz listy partycji (bez wcięcia dysku)."""
    if r.is_free:
        name = T("Obszar niepodzielony", "Unpartitioned space")
        left = " " * 6 + name
        size = f"{disks.mb(r.size):>8} MB"
        return (left.ljust(width - 30) + size)[:width]
    dev = os.path.basename(r.path) if r.path else ""
    left = f"{dev:<9} {r.title(T)} [{r.fs_display(T)}]"
    size = f"{disks.mb(r.size):>8} MB"
    free = ""
    if r.used is not None:
        free = T(f" ({disks.mb(max(0, r.size - r.used)):>6} MB wolne)", f" ({disks.mb(max(0, r.size - r.used)):>6} MB free)")
    s = left[: width - 30].ljust(width - 30) + size + free
    return s[:width]


class PartitionScreen(Screen):
    def __init__(self, app, select_path=None):
        super().__init__(app)
        self.sel = 0
        self.top = 0
        self.select_path = select_path

    def items(self):
        out = []
        for d in self.app.disks:
            out.append(("disk", d))
            out.append(("blank", None))
            for r in d.regions:
                out.append(("region", r))
            out.append(("blank", None))
        return out

    def selectable(self):
        return [i for i, (k, _) in enumerate(self.items()) if k == "region"]

    def enter(self):
        sel = self.selectable()
        if self.select_path:
            for i in sel:
                if self.items()[i][1].path == self.select_path:
                    self.sel = i
                    break
            else:
                self.sel = sel[0] if sel else 0
        elif sel:
            # domyślnie: pierwszy obszar niepodzielony albo pierwsza partycja
            free = [i for i in sel if self.items()[i][1].is_free]
            self.sel = free[0] if free else sel[0]

    def current(self):
        it = self.items()
        if 0 <= self.sel < len(it) and it[self.sel][0] == "region":
            return it[self.sel][1]
        return None

    @property
    def status(self):
        r = self.current()
        if r is None:
            return T("  F3=Zakończ", "  F3=Quit")
        if r.is_free:
            return T("  ENTER=Instaluj  C=Utwórz partycję  F3=Zakończ", "  ENTER=Install  C=Create Partition  F3=Quit")
        return T("  ENTER=Instaluj  D=Usuń partycję  F3=Zakończ", "  ENTER=Install  D=Delete Partition  F3=Quit")

    def draw(self):
        g = self.g
        self.header()
        y = self.para(3, 4, T("Poniższa lista pokazuje istniejące partycje i obszar niepodzielony na tym komputerze.",
                              "The following list shows the existing partitions and unpartitioned space on this "
                              "computer."))
        y = self.para(3, y + 1, T("Użyj klawiszy STRZAŁKA W GÓRĘ i STRZAŁKA W DÓŁ, aby wybrać element z listy.",
                                  "Use the UP and DOWN ARROW keys to select an item in the list."))
        y = self.bullet(y + 1, T("Aby zainstalować system HoryzontOS na zaznaczonym elemencie, naciśnij klawisz ENTER.",
                                 "To set up HoryzontOS on the selected item, press ENTER."))
        y = self.bullet(y + 1, T("Aby utworzyć partycję w obszarze niepodzielonym, naciśnij klawisz C.",
                                 "To create a partition in the unpartitioned space, press C."))
        y = self.bullet(y + 1, T("Aby usunąć zaznaczoną partycję, naciśnij klawisz D.",
                                 "To delete the selected partition, press D."))
        bx, by = 2, y + 1
        bw = min(g.cols - 4, 78)
        bh = g.rows - by - 2
        g.box(bx, by, bw, bh, GRAY, BLUE)
        items = self.items()
        vis = bh - 2
        if not self.app.disks:
            g.put(bx + 2, by + 1, T("Instalator nie znalazł żadnego dysku twardego.", "Setup did not find any hard disks."),
                  WHITE)
            return
        if self.sel < self.top:
            self.top = self.sel
        if self.sel >= self.top + vis:
            self.top = self.sel - vis + 1
        inner = bw - 4
        for i in range(vis):
            j = self.top + i
            if j >= len(items):
                break
            kind, obj = items[j]
            yy = by + 1 + i
            if kind == "disk":
                g.put(bx + 2, yy, obj.describe(T)[:inner])
            elif kind == "region":
                line = "   " + part_line(obj, inner - 3)
                if j == self.sel:
                    g.put(bx + 1, yy, " " + line.ljust(inner) + " ", BLUE, GRAY)
                else:
                    g.put(bx + 2, yy, line)
        if self.top > 0:
            g.put(bx + bw - 2, by, "↑" if False else "^")
        if self.top + vis < len(items):
            g.put(bx + bw - 2, by + bh - 1, "v")

    def key(self, k, txt):
        sel = self.selectable()
        r = self.current()
        if k in ("UP", "DOWN", "HOME", "END", "PGUP", "PGDN") and sel:
            pos = sel.index(self.sel) if self.sel in sel else 0
            if k == "UP":
                pos = max(0, pos - 1)
            elif k == "DOWN":
                pos = min(len(sel) - 1, pos + 1)
            elif k in ("HOME", "PGUP"):
                pos = 0
            else:
                pos = len(sel) - 1
            self.sel = sel[pos]
            self.app.redraw()
        elif k == "F3":
            self.app.go(QuitScreen(self.app, self))
        elif r is None:
            return
        elif k == "C" and r.is_free:
            self.app.go(CreateScreen(self.app, r))
        elif k == "D" and not r.is_free:
            self.app.go(DeleteScreen(self.app, r))
        elif k == "ENTER":
            self.install_on(r)

    def install_on(self, r):
        app = self.app
        need_min = install.min_partition_size()
        if r.is_free:
            extra = sum(sz for _, sz in disks.boot_needs(r.disk))
            if r.size - extra < need_min:
                app.go(TooSmallScreen(app, r, need_min))
                return

            def work():
                return disks.create_partition(r.disk, r, r.size)
            app.go(BusyScreen(app, T("Instalator tworzy partycję...", "Setup is creating the partition..."), work,
                                lambda path: app.go(FormatScreen(app, disks.find_region(app.disks, path)))))
            return
        if r.is_esp or r.is_biosboot or r.ptype in (disks.GPT_MSR, disks.GPT_WINRE) or r.is_extended:
            app.go(MessageScreen(app, T("Na tej partycji nie można zainstalować systemu HoryzontOS — jest to "
                                          "partycja specjalna, potrzebna do uruchamiania komputera.",
                                          "HoryzontOS cannot be installed on this partition — it is a special "
                                          "partition used to start the computer."), self))
            return
        if r.size < need_min:
            app.go(TooSmallScreen(app, r, need_min))
            return
        need = disks.boot_needs(r.disk)
        if need:
            kind = need[0][0]
            if kind == "esp":
                msg = T("Na tym dysku nie ma partycji systemowej EFI, potrzebnej do uruchomienia systemu na tym "
                        "komputerze. Usuń wybraną partycję i zainstaluj system HoryzontOS w powstałym obszarze "
                        "niepodzielonym — Instalator sam utworzy wtedy partycję systemową EFI.",
                        "This disk has no EFI system partition, which this computer needs to start. Delete the "
                        "selected partition and install HoryzontOS in the resulting unpartitioned space — Setup "
                        "will then create the EFI system partition automatically.")
            else:
                msg = T("Ten dysk używa tablicy partycji GPT, a komputer uruchamia się w trybie BIOS. Potrzebna jest "
                        "mała partycja startowa BIOS. Usuń wybraną partycję i zainstaluj system w powstałym obszarze "
                        "niepodzielonym — Instalator utworzy ją automatycznie.",
                        "This disk uses a GPT partition table and the computer starts in BIOS mode, so a small BIOS "
                        "boot partition is needed. Delete the selected partition and install into the resulting "
                        "unpartitioned space — Setup will create it automatically.")
            app.go(MessageScreen(app, msg, self))
            return
        app.go(FormatScreen(app, r))


class BusyScreen(Screen):
    """Krótka operacja w tle z komunikatem na pasku stanu."""

    def __init__(self, app, message, work, done):
        super().__init__(app)
        self.status = "  " + message
        self.work, self.done_cb = work, done
        self.result = None
        self.error = None
        self.finished = False

    def enter(self):
        def run():
            try:
                self.result = self.work()
            except Exception as e:
                disks.log(traceback.format_exc())
                self.error = e
            self.finished = True
        threading.Thread(target=run, daemon=True).start()

    def draw(self):
        self.header()

    def tick(self):
        if self.finished:
            self.finished = False
            if self.error:
                self.app.go(ErrorScreen(self.app, self.error, recoverable=True))
            else:
                self.done_cb(self.result)
        return False


class MessageScreen(Screen):
    status = property(lambda s: T("  ENTER=Kontynuuj", "  ENTER=Continue"))

    def __init__(self, app, text, back):
        super().__init__(app)
        self.text, self.back = text, back

    def draw(self):
        self.header()
        y = self.para(3, 4, self.text)
        self.bullet(y + 1, T("Aby powrócić do poprzedniego ekranu, naciśnij klawisz ENTER.",
                             "To return to the previous screen, press ENTER."))

    def key(self, k, txt):
        if k in ("ENTER", "ESC"):
            self.app.go(self.back)


class TooSmallScreen(MessageScreen):
    def __init__(self, app, region, need):
        txt = T(f"Wybrany obszar jest za mały dla systemu HoryzontOS. Aby zainstalować system HoryzontOS, partycja "
                f"musi mieć co najmniej {disks.mb(need)} megabajtów (MB) wolnego miejsca.",
                f"The selected area is too small for HoryzontOS. To set up HoryzontOS, the partition must have at "
                f"least {disks.mb(need)} megabytes (MB) of space.")
        super().__init__(app, txt, PartitionScreen(app, region.path))


class CreateScreen(Screen):
    status = property(lambda s: T("  ENTER=Utwórz  ESC=Anuluj", "  ENTER=Create  ESC=Cancel"))

    def __init__(self, app, region):
        super().__init__(app)
        self.r = region
        self.extra = sum(sz for _, sz in disks.boot_needs(region.disk))
        self.maxmb = max(8, disks.mb(region.size - self.extra))
        self.value = str(self.maxmb)
        self.fresh = True

    def draw(self):
        g = self.g
        self.header()
        y = self.para(3, 4, T("Zażądano, aby Instalator utworzył nową partycję na", "You asked Setup to create a new "
                              "partition on") + "\n" + self.r.disk.describe(T, False) + ".")
        y = self.bullet(y + 2, T("Aby utworzyć nową partycję, wpisz niżej rozmiar i naciśnij klawisz ENTER.",
                                 "To create the new partition, enter a size below and press ENTER."))
        y = self.bullet(y + 1, T("Aby powrócić do poprzedniego ekranu nie tworząc partycji, naciśnij klawisz ESC.",
                                 "To go back to the previous screen without creating the partition, press ESC."))
        y += 2
        if self.extra:
            y = self.para(3, y, T(f"Instalator doda też na początku tego obszaru partycję startową "
                                  f"({disks.mb(self.extra)} MB), potrzebną do uruchamiania komputera.",
                                  f"Setup will also add a boot partition ({disks.mb(self.extra)} MB) at the start of "
                                  f"this area, needed to start the computer.")) + 1
        a = T("Minimalny rozmiar nowej partycji to", "The minimum size for the new partition is")
        b = T("Maksymalny rozmiar nowej partycji to", "The maximum size for the new partition is")
        c = T("Utwórz partycję o rozmiarze (w MB):", "Create partition of size (in MB):")
        unit = T("megabajtów (MB).", "megabytes (MB).")
        col = max(len(a), len(b)) + 4
        g.put(3, y, a)
        g.put(3 + col, y, f"{8:>5} {unit}")
        g.put(3, y + 1, b)
        g.put(3 + col, y + 1, f"{self.maxmb:>5} {unit}")
        g.put(3, y + 2, c)
        fx = 3 + len(c) + 2
        g.put(fx, y + 2, self.value.ljust(9), BLACK, GRAY)
        g.cursor = (fx + len(self.value), y + 2)

    def key(self, k, txt):
        if k == "ESC":
            self.app.go(PartitionScreen(self.app, self.r.path))
        elif k == "BACKSPACE":
            self.value = self.value[:-1]
            self.fresh = False
            self.app.redraw()
        elif txt and txt.isdigit():
            if self.fresh:
                self.value = ""
                self.fresh = False
            if len(self.value) < 8:
                self.value += txt
            self.app.redraw()
        elif k == "ENTER":
            try:
                size = int(self.value)
            except ValueError:
                return
            size = max(8, min(size, self.maxmb))
            r = self.r
            app = self.app

            def work():
                return disks.create_partition(r.disk, r, size * disks.MiB + (0 if size < self.maxmb else 0))

            def done(path):
                app.go(PartitionScreen(app, path))
            app.go(BusyScreen(app, T("Instalator tworzy partycję...", "Setup is creating the partition..."), work, done))


class DeleteScreen(Screen):
    def __init__(self, app, region):
        super().__init__(app)
        self.r = region
        self.system_warned = not (region.osname or region.is_esp or region.is_biosboot)

    @property
    def status(self):
        if not self.system_warned:
            return T("  ENTER=Kontynuuj  ESC=Anuluj", "  ENTER=Continue  ESC=Cancel")
        return T("  L=Usuń  ESC=Anuluj", "  L=Delete  ESC=Cancel")

    def desc(self):
        r = self.r
        return (f"{os.path.basename(r.path)}  {r.title(T)} [{r.fs_display(T)}]  {disks.mb(r.size)} MB",
                r.disk.describe(T))

    def draw(self):
        g = self.g
        self.header()
        a, b = self.desc()
        if not self.system_warned:
            if self.r.is_esp:
                what = T("Wybrana partycja jest partycją systemową EFI. Zawiera pliki potrzebne do uruchomienia "
                         "komputera, także innych zainstalowanych systemów operacyjnych.",
                         "The selected partition is the EFI system partition. It contains files needed to start the "
                         "computer, including other installed operating systems.")
            elif self.r.is_biosboot:
                what = T("Wybrana partycja jest partycją startową BIOS.", "The selected partition is a BIOS boot partition.")
            else:
                what = T(f"Wybrana partycja zawiera zainstalowany system operacyjny ({self.r.osname}). Jeśli ją "
                         f"usuniesz, nie będzie można go uruchomić.",
                         f"The selected partition contains an installed operating system ({self.r.osname}). If you "
                         f"delete it, that system will no longer start.")
            y = self.para(3, 4, what)
            y = self.bullet(y + 1, T("Aby mimo to usunąć tę partycję, naciśnij klawisz ENTER. Instalator poprosi o "
                                     "potwierdzenie.", "To delete this partition anyway, press ENTER. Setup will ask "
                                     "for confirmation."))
            self.bullet(y + 1, T("Aby powrócić do poprzedniego ekranu bez usuwania partycji, naciśnij klawisz ESC.",
                                 "To return to the previous screen without deleting the partition, press ESC."))
            return
        y = self.para(3, 4, T("Zażądano usunięcia partycji", "You asked Setup to delete the partition"))
        g.put(6, y + 1, a, WHITE)
        y = self.para(3, y + 3, T("na dysku", "on") + " " + b + ".")
        y = self.bullet(y + 2, T("Aby usunąć tę partycję, naciśnij klawisz L. OSTRZEŻENIE: Wszystkie dane na tej "
                                 "partycji zostaną utracone.",
                                 "To delete this partition, press L. CAUTION: All data on this partition will be lost."))
        self.bullet(y + 1, T("Aby powrócić do poprzedniego ekranu bez usuwania partycji, naciśnij klawisz ESC.",
                             "To return to the previous screen without deleting the partition, press ESC."))

    def key(self, k, txt):
        if k == "ESC":
            self.app.go(PartitionScreen(self.app, self.r.path))
        elif k == "ENTER" and not self.system_warned:
            self.system_warned = True
            self.app.redraw()
        elif k == "L" and self.system_warned:
            r = self.r
            app = self.app

            def work():
                disks.unmount_all(r.path)
                disks.delete_partition(r)
                return None

            def done(_):
                free = next((x for x in r.disk.regions if x.is_free and x.start <= r.start + disks.MiB < x.end), None)
                app.go(PartitionScreen(app, free.path if free and free.path else None))
            app.go(BusyScreen(app, T("Instalator usuwa partycję...", "Setup is deleting the partition..."), work, done))


FS_CHOICES = [("btrfs", True), ("ext4", True), ("xfs", True), ("btrfs", False), ("ext4", False), ("xfs", False)]


class FormatScreen(Screen):
    status = property(lambda s: T("  ENTER=Kontynuuj  ESC=Anuluj", "  ENTER=Continue  ESC=Cancel"))

    def __init__(self, app, region):
        super().__init__(app)
        self.r = region
        self.sel = 0
        self.warn = False

    def draw(self):
        g = self.g
        self.header()
        r = self.r
        if self.warn:
            y = self.para(3, 4, T("OSTRZEŻENIE: Formatowanie tej partycji spowoduje usunięcie wszystkich "
                                  "znajdujących się na niej plików.",
                                  "WARNING: Formatting this partition will destroy all files on it."), WHITE)
            g.put(6, y + 1, f"{os.path.basename(r.path)}  {r.title(T)} [{r.fs_display(T)}]  {disks.mb(r.size)} MB", WHITE)
            y = self.para(3, y + 3, T("na dysku", "on") + " " + r.disk.describe(T) + ".")
            y = self.bullet(y + 2, T("Aby sformatować partycję, naciśnij klawisz F.", "To format the partition, press F."))
            self.bullet(y + 1, T("Aby wybrać inną partycję dla systemu HoryzontOS, naciśnij klawisz ESC.",
                                 "To select a different partition for HoryzontOS, press ESC."))
            return
        if not r.fstype or r.created_here:
            y = self.para(3, 4, T("Wybrana partycja nie jest sformatowana. Instalator sformatuje teraz tę partycję.",
                                  "The partition you selected is not formatted. Setup will now format the partition."))
        else:
            y = self.para(3, 4, T(f"Instalator zainstaluje system HoryzontOS na partycji",
                                  f"Setup will install HoryzontOS on partition"))
            g.put(6, y + 1, f"{os.path.basename(r.path)}  {r.title(T)} [{r.fs_display(T)}]  {disks.mb(r.size)} MB", WHITE)
            y = self.para(3, y + 3, T("na dysku", "on") + " " + r.disk.describe(T) + ".") + 1
            y = self.para(3, y, T("Partycja zostanie sformatowana — wszystkie dane na niej zostaną usunięte.",
                                  "The partition will be formatted — all data on it will be erased."))
        y = self.para(3, y + 1, T("Użyj klawiszy STRZAŁKA W GÓRĘ i STRZAŁKA W DÓŁ, aby wybrać żądany system plików, "
                                  "a następnie naciśnij klawisz ENTER.",
                                  "Use the UP and DOWN ARROW keys to select the file system you want, and then press "
                                  "ENTER."))
        y = self.para(3, y + 1, T("Jeśli chcesz wybrać inną partycję dla systemu HoryzontOS, naciśnij klawisz ESC.",
                                  "If you want to select a different partition for HoryzontOS, press ESC."))
        y += 1
        for i, (fs, quick) in enumerate(FS_CHOICES):
            name = disks.FS_NAMES[fs]
            label = T(f"Formatuj partycję stosując system plików {name}", f"Format the partition using the {name} "
                      f"file system")
            if quick:
                label += T(" (szybkie)", " (Quick)")
            if i == 0:
                label += T("  — zalecane", "  — recommended")
            if i == self.sel:
                g.put(6, y + i, " " + label.ljust(64) + " ", BLUE, GRAY)
            else:
                g.put(7, y + i, label)

    def key(self, k, txt):
        if self.warn:
            if k == "F":
                self.start()
            elif k == "ESC":
                self.app.go(PartitionScreen(self.app, self.r.path))
            return
        if k == "UP":
            self.sel = max(0, self.sel - 1)
            self.app.redraw()
        elif k == "DOWN":
            self.sel = min(len(FS_CHOICES) - 1, self.sel + 1)
            self.app.redraw()
        elif k == "ESC":
            self.app.go(PartitionScreen(self.app, self.r.path))
        elif k == "ENTER":
            if self.r.fstype and not self.r.created_here:
                self.warn = True
                self.app.redraw()
            else:
                self.start()

    def start(self):
        fs, quick = FS_CHOICES[self.sel]
        self.app.go(FormatProgressScreen(self.app, self.r, fs, quick))


def progress_box(g, title, frac, y=None, color=YELLOW):
    w = min(64, g.cols - 8)
    x = (min(g.cols, 80) - w) // 2 if g.cols <= 100 else (g.cols - w) // 2
    h = 7
    y = y if y is not None else (g.rows - h) // 2 + 2
    g.box(x, y, w, h, WHITE, BLUE, double=True)
    g.center(y + 1, title, GRAY, BLUE, x, w)
    g.center(y + 2, f"{int(frac * 100)}%", GRAY, BLUE, x, w)
    bw = w - 6
    g.box(x + 2, y + 3, bw + 2, 3, WHITE, BLUE)
    n = int(round(bw * max(0.0, min(1.0, frac))))
    g.put(x + 3, y + 4, "█" * n, color, BLUE)


class FormatProgressScreen(Screen):
    def __init__(self, app, region, fs, quick):
        super().__init__(app)
        self.r, self.fs, self.quick = region, fs, quick
        self.frac = 0.0
        self.done = False
        self.error = None
        self.status = T("  Proszę czekać...", "  Please wait...")

    def enter(self):
        def work():
            try:
                disks.unmount_all(self.r.path)
                if not self.quick:
                    disks.zero_fill(self.r.path, lambda f: setattr(self, "frac", f * 0.95))
                t0 = time.monotonic()
                th = threading.Thread(target=disks.mkfs, args=(self.r.path, self.fs))
                errs = []

                def mk():
                    try:
                        disks.mkfs(self.r.path, self.fs)
                    except Exception as e:
                        errs.append(e)
                th = threading.Thread(target=mk)
                th.start()
                base = self.frac
                while th.is_alive():
                    time.sleep(0.1)
                    el = time.monotonic() - t0
                    self.frac = base + (0.99 - base) * min(1.0, el / 4.0)
                th.join()
                if errs:
                    raise errs[0]
                self.r.fstype = self.fs
                self.frac = 1.0
                time.sleep(0.4)
            except Exception as e:
                disks.log(traceback.format_exc())
                self.error = e
            self.done = True
        threading.Thread(target=work, daemon=True).start()

    def draw(self):
        g = self.g
        self.header()
        r = self.r
        y = self.para(3, 4, T("Proszę czekać, Instalator formatuje partycję", "Please wait while Setup formats the partition"))
        g.put(6, y + 1, f"{os.path.basename(r.path)}  {r.title(T)} [{T('Nowa (surowa)', 'New (Raw)') if r.created_here or not r.fstype else r.fs_display(T)}]  {disks.mb(r.size)} MB")
        self.para(3, y + 3, T("na dysku", "on") + " " + r.disk.describe(T) + ".")
        progress_box(g, T("Instalator formatuje...", "Setup is formatting..."), self.frac)

    def tick(self):
        if self.done:
            self.done = False
            if self.error:
                self.app.go(ErrorScreen(self.app, self.error, recoverable=True))
            else:
                self.app.go(CopyScreen(self.app, self.r, self.fs))
            return False
        return True


class CopyScreen(Screen):
    def __init__(self, app, region, fs):
        super().__init__(app)
        self.r, self.fs = region, fs
        self.frac = 0.0
        self.name = ""
        self.phase = "copy"
        self.stepname = ""
        self.done = False
        self.error = None

    @property
    def status(self):
        if self.phase == "config":
            return T("  Instalator inicjuje konfigurację systemu HoryzontOS...",
                     "  Setup is initializing your HoryzontOS configuration...")
        if self.phase == "mount":
            return T("  Instalator przygotowuje partycję...", "  Setup is preparing the partition...")
        return ""

    @property
    def status_right(self):
        if self.phase == "copy" and self.name:
            return T("Kopiowanie: ", "Copying: ") + self.name[:24]
        return ""

    def enter(self):
        def work():
            try:
                self.phase = "mount"
                plan = install.Plan(self.r, self.fs, i18n.lang())
                install.mount_target(plan)
                self.phase = "copy"

                def prog(f, n):
                    self.frac, self.name = f, n
                install.copy_system(prog)
                self.phase = "config"
                install.configure(plan, lambda s: setattr(self, "stepname", s))
            except Exception as e:
                disks.log(traceback.format_exc())
                self.error = e
                install.unmount_target()
            self.done = True
        threading.Thread(target=work, daemon=True).start()

    def draw(self):
        g = self.g
        self.header()
        if self.phase != "copy":
            return
        w = min(64, g.cols - 8)
        x = (min(g.cols, 80) - w) // 2
        lines = wrap(T("Proszę czekać, aż Instalator skopiuje pliki do folderów instalacyjnych systemu "
                       "HoryzontOS. Może to potrwać kilka minut.",
                       "Please wait while Setup copies files to the HoryzontOS installation folders. This might "
                       "take several minutes to complete."), w - 6)
        g.box(x, 6, w, len(lines) + 4, WHITE, BLUE, double=True)
        for i, ln in enumerate(lines):
            g.put(x + 3, 8 + i, ln)
        progress_box(g, T("Instalator kopiuje pliki...", "Setup is copying files..."), self.frac, y=8 + len(lines) + 4)

    def tick(self):
        if self.done:
            self.done = False
            if self.error:
                self.app.go(ErrorScreen(self.app, self.error, recoverable=False))
            else:
                self.app.go(RebootScreen(self.app))
            return False
        return True


class RebootScreen(Screen):
    SECONDS = 15
    status = property(lambda s: T("  ENTER=Uruchom ponownie komputer", "  ENTER=Restart Computer"))

    def enter(self):
        self.t0 = time.monotonic()

    def draw(self):
        g = self.g
        self.header()
        y = self.para(3, 4, T("Ta część Instalatora została pomyślnie ukończona.",
                              "This portion of Setup has completed successfully."))
        y = self.para(3, y + 1, T("Jeśli w napędzie jest płyta instalacyjna albo do komputera jest podłączony "
                                  "pendrive z Instalatorem, możesz go teraz wyjąć.",
                                  "If there is a Setup disc in the drive or a Setup USB drive is connected, you can "
                                  "remove it now."))
        y = self.para(3, y + 1, T("Aby ponownie uruchomić komputer, naciśnij klawisz ENTER. Gdy komputer zostanie "
                                  "uruchomiony ponownie, Instalator będzie kontynuował pracę.",
                                  "To restart your computer, press ENTER. When your computer restarts, Setup will "
                                  "continue."))
        left = max(0, self.SECONDS - int(time.monotonic() - self.t0))
        frac = min(1.0, (time.monotonic() - self.t0) / self.SECONDS)
        progress_box(g, T(f"Komputer zostanie uruchomiony ponownie za {left} s...",
                          f"Your computer will reboot in {left} seconds..."), frac, y=y + 3, color=RED)
        # bez procentów w tym oknie
        w = min(64, g.cols - 8)
        x = (min(g.cols, 80) - w) // 2
        g.put(x + 1, y + 5, " " * (w - 2))

    def tick(self):
        if time.monotonic() - self.t0 >= self.SECONDS:
            self.app.finish(EXIT_REBOOT)
            return False
        return True

    def key(self, k, txt):
        if k == "ENTER":
            self.app.finish(EXIT_REBOOT)


class ErrorScreen(Screen):
    def __init__(self, app, error, recoverable):
        super().__init__(app)
        self.error, self.recoverable = error, recoverable

    @property
    def status(self):
        if self.recoverable:
            return T("  ENTER=Powrót do listy partycji  F3=Zakończ", "  ENTER=Back to the partition list  F3=Quit")
        return T("  F3=Zakończ  R=Konsola odzyskiwania", "  F3=Quit  R=Recovery Console")

    def draw(self):
        self.header()
        msg = str(self.error)
        known = {
            "no-primary": T("Na tym dysku nie można utworzyć więcej partycji podstawowych (tablica MBR mieści "
                            "najwyżej cztery). Usuń jedną z istniejących partycji.",
                            "No more primary partitions can be created on this disk (an MBR table holds at most "
                            "four). Delete one of the existing partitions."),
            "too-small": T("Obszar jest za mały, aby utworzyć w nim partycję.", "The area is too small for a partition."),
            "no-esp": T("Brak partycji systemowej EFI na wybranym dysku.", "There is no EFI system partition on the disk."),
        }
        text = known.get(msg) or (T("Instalator nie mógł ukończyć operacji:", "Setup could not complete the operation:")
                                  + "\n\n" + msg)
        y = self.para(3, 4, text, WHITE)
        if not self.recoverable:
            y = self.para(3, y + 1, T("Instalacja nie może być kontynuowana.", "Setup cannot continue."))
        self.para(3, y + 1, T(f"Szczegóły zapisano w pliku {LOG}.", f"Details were saved to {LOG}."))

    def key(self, k, txt):
        if k == "F3":
            self.app.finish(EXIT_QUIT)
        elif k == "ENTER" and self.recoverable:
            app = self.app

            def work():
                app.disks = disks.scan()
            app.go(BusyScreen(app, T("Instalator sprawdza dyski...", "Setup is examining disks..."), work,
                                lambda _: app.go(PartitionScreen(app))))
        elif k == "R" and not self.recoverable:
            self.app.finish(EXIT_CONSOLE)


# ====================================================================== aplikacja
class SetupApp(TextView):
    def __init__(self):
        super().__init__()
        self.disks = []
        self.screen = None
        self.exit_code = None
        self.keyPressed.connect(self._key)
        self._ticker = QTimer(self)
        self._ticker.timeout.connect(self._tick)
        self._ticker.start(100)

    def on_grid_resized(self):
        self.redraw()

    def go(self, screen):
        self.grid.cursor = None
        self.screen = screen
        screen.enter()
        self.redraw()

    def redraw(self):
        g = self.grid
        g.clear()
        if self.screen:
            self.screen.draw()
            g.fill(0, g.rows - 1, g.cols, 1, " ", BLACK, GRAY)
            st = self.screen.status or ""
            g.put(0, g.rows - 1, st[:g.cols], BLACK, GRAY)
            sr = self.screen.status_right or ""
            if sr:
                x = max(len(st) + 2, g.cols - len(sr) - 2)
                g.put(x - 2, g.rows - 1, "│ " + sr, BLACK, GRAY)
        self.update()

    def _key(self, name, txt):
        if self.screen:
            self.screen.key(name, txt)

    def _tick(self):
        if self.screen and self.screen.tick():
            self.redraw()

    def finish(self, code):
        self.exit_code = code
        # skrypt sesji odróżnia zamierzone zakończenie od utraty ekranu (np. zmiana sterownika grafiki)
        try:
            with open(RC_FILE, "w") as f:
                f.write(f"{code}\n")
        except OSError:
            pass
        QApplication.instance().exit(code)


RC_FILE = "/run/horyzontos-textsetup.rc"


def main(argv):
    disks.LOG = LOG
    try:
        os.remove(RC_FILE)
    except OSError:
        pass
    try:
        with open(LOG, "a") as f:
            f.write(f"--- HoryzontOS Setup {time.ctime()}\n")
    except OSError:
        pass
    window = "--window" in argv
    if not window and not os.environ.get("QT_QPA_PLATFORM") and not os.environ.get("WAYLAND_DISPLAY") \
            and not os.environ.get("DISPLAY"):
        os.environ["QT_QPA_PLATFORM"] = "linuxfb"
        os.environ.setdefault("QT_QPA_FB_DRM", "1")
    os.environ.setdefault("QT_QPA_EVDEV_KEYBOARD_PARAMETERS", "grab=1")
    app = QApplication(sys.argv[:1])
    w = SetupApp()
    if window:
        w.resize(960, 720)
        w.show()
    else:
        w.showFullScreen()
    w.go(LoadingScreen(w))
    w.setFocus()
    if not window:
        import subprocess
        QTimer.singleShot(1200, lambda: subprocess.Popen(["plymouth", "quit", "--retain-splash"],
                                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    rc = app.exec()
    return rc if rc is not None else 0
