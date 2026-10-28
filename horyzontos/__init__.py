"""HoryzontOS — instalator, konfigurator i pierwsze uruchomienie systemu."""
import os

def version():
    for p in (os.path.join(os.path.dirname(os.path.dirname(__file__)), "VERSION"),
              "/usr/share/horyzontos/VERSION"):
        try:
            with open(p) as f:
                return f.read().strip()
        except OSError:
            pass
    return "?"
