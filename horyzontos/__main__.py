"""python3 -m horyzontos <polecenie>

  textsetup [--window]       tekstowa część instalatora (z płyty)
  setup [--window]           graficzna część instalatora / pierwsze uruchomienie (wg /var/lib/horyzontos/stage)
  gui-setup | oobe           wymuszenie etapu (testy, podgląd)
  shot ...                   zrzuty ekranów do testów
"""
import sys


def main():
    argv = sys.argv[1:]
    cmd = argv[0] if argv else ""
    if cmd == "textsetup":
        from .textsetup.app import main as m
        return m(argv[1:])
    if cmd in ("setup", "gui-setup", "oobe"):
        from .setup.main import main as m
        return m(cmd, argv[1:])
    if cmd == "shot":
        from .tools.shots import main as m
        return m(argv[1:])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main() or 0)
