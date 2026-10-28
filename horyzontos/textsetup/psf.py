"""Czytnik czcionek konsoli PSF1/PSF2 (z tablicą Unicode) — do rysowania ekranów „trybu tekstowego”."""
import gzip
import struct


class PSFFont:
    def __init__(self, path):
        with open(path, "rb") as f:
            data = f.read()
        if data[:2] == b"\x1f\x8b":
            data = gzip.decompress(data)
        self.glyphs = []
        self.map = {}
        if data[:2] == b"\x36\x04":                       # PSF1
            mode, charsize = data[2], data[3]
            n = 512 if mode & 1 else 256
            self.w, self.h = 8, charsize
            off = 4
            for i in range(n):
                self.glyphs.append(data[off + i * charsize: off + (i + 1) * charsize])
            if mode & 2:                                  # tablica Unicode (UCS-2)
                pos = off + n * charsize
                g = 0
                while g < n and pos + 1 < len(data):
                    v, = struct.unpack_from("<H", data, pos)
                    pos += 2
                    if v == 0xFFFF:
                        g += 1
                    elif v == 0xFFFE:
                        continue
                    else:
                        self.map.setdefault(chr(v), g)
            else:
                for i in range(n):
                    self.map.setdefault(chr(i), i)
        elif data[:4] == b"\x72\xb5\x4a\x86":             # PSF2
            _, _, hsize, flags, n, charsize, h, w = struct.unpack_from("<IIIIIIII", data, 0)
            self.w, self.h = w, h
            for i in range(n):
                self.glyphs.append(data[hsize + i * charsize: hsize + (i + 1) * charsize])
            if flags & 1:
                pos = hsize + n * charsize
                g = 0
                buf = bytearray()
                while g < n and pos < len(data):
                    b = data[pos]
                    pos += 1
                    if b == 0xFF:
                        self._seq(buf, g)
                        buf = bytearray()
                        g += 1
                    elif b == 0xFE:
                        self._seq(buf, g)
                        buf = bytearray()
                        # sekwencje łączone pomijamy
                        while pos < len(data) and data[pos] != 0xFF:
                            pos += 1
                    else:
                        buf.append(b)
            else:
                for i in range(n):
                    self.map.setdefault(chr(i), i)
        else:
            raise ValueError("to nie jest czcionka PSF: " + path)
        self.row_bytes = (self.w + 7) // 8

    def _seq(self, buf, g):
        try:
            for ch in bytes(buf).decode("utf-8"):
                self.map.setdefault(ch, g)
        except UnicodeDecodeError:
            pass

    def has(self, ch):
        return ch in self.map

    def bitmap(self, ch):
        """Lista wierszy (int) dla znaku albo None."""
        g = self.map.get(ch)
        if g is None:
            return None
        data = self.glyphs[g]
        rb = self.row_bytes
        return [int.from_bytes(data[r * rb:(r + 1) * rb], "big") for r in range(self.h)]
