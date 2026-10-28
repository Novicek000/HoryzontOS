#!/usr/bin/env python3
"""Grafika i dźwięki HoryzontOS generowane przy budowaniu obrazu (wszystko narysowane od nowa):

  • motyw startowy plymouth „horyzont” — czarny ekran, logo i przesuwające się niebieskie bloczki,
  • motywy „horyzont-setup” (PL) i „horyzont-setup-en” — niebieski ekran ładowania instalatora,
  • muzyka pierwszego uruchomienia (oobe.wav), syntetyzowana od zera.

Użycie: make-art.py KATALOG_ROOTFS WERSJA
"""
import array
import math
import os
import random
import sys
import wave

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SRC)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFontMetrics, QImage, QLinearGradient, QPainter, QPen  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


def img(w, h):
    i = QImage(w, h, QImage.Format_ARGB32)
    i.fill(Qt.transparent)
    return i


# ------------------------------------------------------------------ motyw startowy
def boot_theme(root):
    from horyzontos.ui import look
    d = os.path.join(root, "usr/share/plymouth/themes/horyzont")
    os.makedirs(d, exist_ok=True)
    # logo + napis (2× większe niż na ekranie 1024×768 — skrypt je zmniejsza)
    h = 150
    f1 = look.font(h * 0.62, bold=True, fam=look.title_family())
    f2 = look.font(h * 0.62 * 0.55, bold=True, italic=True, fam=look.title_family())
    tw = QFontMetrics(f1).horizontalAdvance("Horyzont") + h * 0.04 + QFontMetrics(f2).horizontalAdvance("OS")
    W = int(h * 1.15 + tw + 20)
    im = img(W, h)
    p = QPainter(im)
    p.setRenderHint(QPainter.Antialiasing)
    look.draw_logo(p, QRectF(0, 0, h, h))
    look.draw_wordmark(p, h * 1.12, h * 0.13, h * 0.62)
    p.end()
    im.save(os.path.join(d, "brand.png"))
    # ramka paska postępu
    bw, bh = 300, 30
    im = img(bw, bh)
    p = QPainter(im)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor("#b0b0b0"), 3))
    p.setBrush(QColor("#000000"))
    p.drawRoundedRect(QRectF(1.5, 1.5, bw - 3, bh - 3), 8, 8)
    p.end()
    im.save(os.path.join(d, "box.png"))
    # bloczek
    im = img(16, 20)
    p = QPainter(im)
    g = QLinearGradient(0, 0, 0, 20)
    g.setColorAt(0, QColor("#a8c4ff"))
    g.setColorAt(0.45, QColor("#3a6ee8"))
    g.setColorAt(1, QColor("#1c3fa8"))
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(g)
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(0, 0, 16, 20), 3, 3)
    p.end()
    im.save(os.path.join(d, "block.png"))
    # podpis na dole
    for name, text in (("footer.png", "Na bazie Fedora Linux"), ("footer-en.png", "Based on Fedora Linux")):
        f = look.font(26)
        w = QFontMetrics(f).horizontalAdvance(text) + 8
        im = img(w, 40)
        p = QPainter(im)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setFont(f)
        p.setPen(QColor("#9a9a9a"))
        p.drawText(QRectF(0, 0, w, 40), Qt.AlignLeft | Qt.AlignVCenter, text)
        p.end()
        im.save(os.path.join(d, name))
    # hasło (dysk zaszyfrowany)
    f = look.font(28)
    text = "Hasło do odblokowania dysku:"
    w = QFontMetrics(f).horizontalAdvance(text) + 8
    im = img(w, 44)
    p = QPainter(im)
    p.setFont(f)
    p.setPen(QColor("#ffffff"))
    p.drawText(QRectF(0, 0, w, 44), Qt.AlignLeft | Qt.AlignVCenter, text)
    p.end()
    im.save(os.path.join(d, "prompt.png"))
    im = img(20, 20)
    p = QPainter(im)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor("#ffffff"))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QRectF(3, 3, 14, 14))
    p.end()
    im.save(os.path.join(d, "bullet.png"))
    with open(os.path.join(d, "horyzont.plymouth"), "w") as f:
        f.write("[Plymouth Theme]\nName=Horyzont\nDescription=Ekran startowy HoryzontOS\nModuleName=script\n\n"
                "[script]\nImageDir=/usr/share/plymouth/themes/horyzont\n"
                "ScriptFile=/usr/share/plymouth/themes/horyzont/horyzont.script\n")
    with open(os.path.join(d, "horyzont.script"), "w") as f:
        f.write(BOOT_SCRIPT)


BOOT_SCRIPT = r"""// Ekran startowy HoryzontOS: logo na czarnym tle i trzy niebieskie bloczki przesuwające się w ramce.
Window.SetBackgroundTopColor(0, 0, 0);
Window.SetBackgroundBottomColor(0, 0, 0);
W = Window.GetWidth();
H = Window.GetHeight();
s = H / 1536;
if (W / 2048 < s) s = W / 2048;
if (s < 0.25) s = 0.25;

brand_img = Image("brand.png");
brand = Sprite(brand_img.Scale(brand_img.GetWidth() * s * 1.6, brand_img.GetHeight() * s * 1.6));
brand.SetX(W / 2 - brand_img.GetWidth() * s * 0.8);
brand.SetY(H * 0.40 - brand_img.GetHeight() * s * 0.8);

box_img = Image("box.png");
bw = box_img.GetWidth() * s * 1.6;
bh = box_img.GetHeight() * s * 1.6;
box = Sprite(box_img.Scale(bw, bh));
bx = W / 2 - bw / 2;
by = H * 0.66;
box.SetX(bx);
box.SetY(by);

blk_img = Image("block.png");
kw = blk_img.GetWidth() * s * 1.6;
kh = blk_img.GetHeight() * s * 1.6;
blk_scaled = blk_img.Scale(kw, kh);
for (i = 0; i < 3; i++) {
    blocks[i] = Sprite(blk_scaled);
    blocks[i].SetY(by + (bh - kh) / 2);
    blocks[i].SetZ(10);
    blocks[i].SetOpacity(0);
}

foot_img = Image("footer.png");
foot = Sprite(foot_img.Scale(foot_img.GetWidth() * s * 1.6, foot_img.GetHeight() * s * 1.6));
foot.SetX(W * 0.04);
foot.SetY(H - foot_img.GetHeight() * s * 1.6 - H * 0.04);

frame = 0;
fun refresh_callback () {
    frame++;
    span = bw + 3 * (kw + kw / 3) + kw;
    pos = (frame * 2.2 * s * 1.6) % span;
    for (i = 0; i < 3; i++) {
        x = bx + pos - (i + 1) * (kw + kw / 3);
        blocks[i].SetX(x);
        if (x < bx + 4 * s || x + kw > bx + bw - 4 * s)
            blocks[i].SetOpacity(0);
        else
            blocks[i].SetOpacity(1);
    }
}
Plymouth.SetRefreshFunction(refresh_callback);

// --- hasło (np. zaszyfrowany dysk)
prompt_sprite = Sprite();
bullet_img = Image("bullet.png");
fun display_normal_callback () {
    prompt_sprite.SetOpacity(0);
    for (i = 0; bullets[i]; i++) bullets[i].SetOpacity(0);
    box.SetOpacity(1);
}
fun display_password_callback (prompt, nb) {
    box.SetOpacity(0);
    pimg = Image("prompt.png");
    prompt_sprite.SetImage(pimg.Scale(pimg.GetWidth() * s * 1.6, pimg.GetHeight() * s * 1.6));
    prompt_sprite.SetX(W / 2 - pimg.GetWidth() * s * 0.8);
    prompt_sprite.SetY(by - pimg.GetHeight() * s * 1.6);
    prompt_sprite.SetOpacity(1);
    for (i = 0; bullets[i]; i++) bullets[i].SetOpacity(0);
    for (i = 0; i < nb && i < 40; i++) {
        bullets[i] = Sprite(bullet_img.Scale(20 * s * 1.6, 20 * s * 1.6));
        bullets[i].SetX(W / 2 - nb * 11 * s * 1.6 + i * 22 * s * 1.6);
        bullets[i].SetY(by + 10 * s);
        bullets[i].SetOpacity(1);
    }
}
Plymouth.SetDisplayNormalFunction(display_normal_callback);
Plymouth.SetDisplayPasswordFunction(display_password_callback);
"""


# ------------------------------------------------------------------ ekran ładowania instalatora
SETUP_STATUS_PL = ["jądro systemu Linux", "moduły sterowników", "menedżer urządzeń udev", "system plików squashfs",
                   "sterowniki dysków twardych", "sterownik ekranu", "menedżer usług systemd", "Instalator HoryzontOS"]
SETUP_STATUS_EN = ["Linux kernel", "driver modules", "udev device manager", "squashfs file system",
                   "hard disk drivers", "display driver", "systemd service manager", "HoryzontOS Setup"]


def setup_theme(root, lang):
    from horyzontos.textsetup.screen import BLACK, GRAY, Grid, TextView
    os.environ["HORYZONTOS_FONT_DIR"] = os.path.join(root, "usr/lib/kbd/consolefonts")
    name = "horyzont-setup" if lang == "pl" else "horyzont-setup-en"
    d = os.path.join(root, "usr/share/plymouth/themes", name)
    os.makedirs(d, exist_ok=True)
    view = TextView()
    view.fixed_size = (80, 30)
    view.grid = Grid(80, 30)
    title = "Instalator systemu HoryzontOS" if lang == "pl" else "HoryzontOS Setup"
    statuses = SETUP_STATUS_PL if lang == "pl" else SETUP_STATUS_EN
    for i, st in enumerate(statuses):
        g = view.grid
        g.clear()
        g.put(1, 1, title)
        g.put(0, 2, "═" * (len(title) + 3))
        g.fill(0, 29, 80, 1, " ", BLACK, GRAY)
        msg = (f"  Instalator ładuje pliki ({st})..." if lang == "pl" else f"  Setup is loading files ({st})...")
        g.put(0, 29, msg, BLACK, GRAY)
        view.render_image().save(os.path.join(d, f"frame{i}.png"))
    with open(os.path.join(d, name + ".plymouth"), "w") as f:
        f.write(f"[Plymouth Theme]\nName={name}\nDescription=Ekran ładowania Instalatora HoryzontOS\n"
                f"ModuleName=script\n\n[script]\nImageDir=/usr/share/plymouth/themes/{name}\n"
                f"ScriptFile=/usr/share/plymouth/themes/{name}/{name}.script\n")
    with open(os.path.join(d, name + ".script"), "w") as f:
        f.write(SETUP_SCRIPT.replace("@N@", str(len(statuses))))
    return [os.path.join("/usr/share/plymouth/themes", name, fn) for fn in sorted(os.listdir(d))]


SETUP_SCRIPT = r"""// Ekran ładowania Instalatora: niebieski „tryb tekstowy” z paskiem stanu.
Window.SetBackgroundTopColor(0, 0, 0.667);
Window.SetBackgroundBottomColor(0, 0, 0.667);
W = Window.GetWidth();
H = Window.GetHeight();
N = @N@;
for (i = 0; i < N; i++) {
    raw = Image("frame" + i + ".png");
    frames[i] = raw.Scale(W, H);
}
spr = Sprite(frames[0]);
spr.SetX(0);
spr.SetY(0);
t = 0;
cur = 0;
fun refresh_callback () {
    t++;
    n = Math.Int(t / 35);
    if (n >= N) n = N - 1;
    if (n != cur) {
        cur = n;
        spr.SetImage(frames[cur]);
    }
}
Plymouth.SetRefreshFunction(refresh_callback);
"""


# ------------------------------------------------------------------ muzyka pierwszego uruchomienia
def music(path, seconds=48, rate=22050):
    """Spokojna, zapętlona melodia: miękkie akordy, dzwoneczki i pogłos (bez cudzych nagrań)."""
    rnd = random.Random(2026)
    n = seconds * rate
    out = array.array("f", [0.0]) * n

    def note(m):
        return 440.0 * 2 ** ((m - 69) / 12)

    # akordy: Cmaj9 – Am9 – Fmaj7#11 – G6/9 (po 6 s, dwa razy)
    chords = [[48, 55, 59, 62, 64], [45, 52, 55, 59, 60], [41, 48, 52, 55, 57], [43, 50, 54, 57, 59]]
    seg = 6.0
    for ci in range(8):
        ch = chords[ci % 4]
        t0 = ci * seg
        for m in ch:
            f = note(m)
            amp = 0.055 if m > 50 else 0.07
            start, length = int(t0 * rate), int((seg + 1.5) * rate)
            ph = rnd.random() * 6.28
            for k in range(length):
                i = start + k
                if i >= n:
                    break
                t = k / rate
                env = min(1.0, t / 1.6) * (1.0 if t < seg else max(0.0, 1 - (t - seg) / 1.5))
                w = 2 * math.pi * f * t + ph
                out[i] += amp * env * (math.sin(w) + 0.3 * math.sin(2 * w + 0.4 * math.sin(0.5 * t)) + 0.12 * math.sin(3 * w))
    # dzwoneczki (pentatonika C)
    scale = [72, 74, 76, 79, 81, 84, 86, 88]
    t = 1.5
    while t < seconds - 2:
        m = rnd.choice(scale)
        f = note(m)
        start = int(t * rate)
        length = int(2.6 * rate)
        amp = 0.09 + rnd.random() * 0.05
        for k in range(length):
            i = start + k
            if i >= n:
                break
            tt = k / rate
            env = math.exp(-tt * 2.2) * min(1.0, tt * 200)
            w = 2 * math.pi * f * tt
            out[i] += amp * env * (math.sin(w) + 0.35 * math.sin(2.76 * w) * math.exp(-tt * 4))
        t += rnd.choice([0.75, 0.75, 1.5, 0.375, 1.125])
    # pogłos (trzy opóźnienia ze sprzężeniem) — także „zawija się”, żeby pętla była płynna
    for delay, fb in ((int(0.113 * rate), 0.32), (int(0.229 * rate), 0.25), (int(0.371 * rate), 0.18)):
        for i in range(n):
            out[i] += out[i - delay] * fb
    peak = max(abs(x) for x in out) or 1.0
    pcm = array.array("h", (int(max(-1.0, min(1.0, x / peak * 0.8)) * 32767) for x in out))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())


def main():
    root = sys.argv[1]
    app = QApplication(sys.argv[:1])  # noqa: F841
    boot_theme(root)
    files = setup_theme(root, "pl") + setup_theme(root, "en")
    os.makedirs(os.path.join(root, "etc/dracut.conf.d"), exist_ok=True)
    with open(os.path.join(root, "etc/dracut.conf.d/90-horyzontos.conf"), "w") as f:
        f.write("# Ekrany ładowania Instalatora HoryzontOS (wybierane parametrem plymouth.splash=)\n")
        f.write('install_items+=" ' + " ".join(files) + ' "\n')
    wav = os.path.join(root, "usr/share/sounds/horyzontos/oobe.wav")
    if not os.path.exists(wav):
        music(wav)
    print("   grafika i dźwięki gotowe")


if __name__ == "__main__":
    main()
