"""Język interfejsu: polski (domyślnie) albo angielski.

Wybór: zmienna HORYZONTOS_LANG, parametr jądra horyzontos.lang=en, plik stanu instalacji, LANG."""
import os

_lang = None


def lang():
    global _lang
    if _lang:
        return _lang
    v = os.environ.get("HORYZONTOS_LANG", "")
    if not v:
        try:
            with open("/proc/cmdline") as f:
                for a in f.read().split():
                    if a.startswith("horyzontos.lang="):
                        v = a.split("=", 1)[1]
        except OSError:
            pass
    if not v:
        try:
            import json
            with open("/var/lib/horyzontos/install.json") as f:
                v = json.load(f).get("lang", "")
        except (OSError, ValueError):
            pass
    if not v:
        v = os.environ.get("LANG", "pl")
    _lang = "en" if v.lower().startswith("en") else "pl"
    return _lang


def set_lang(v):
    global _lang
    _lang = "en" if str(v).lower().startswith("en") else "pl"


def T(pl, en=None):
    """Tekst w bieżącym języku."""
    if lang() == "en" and en is not None:
        return en
    return pl
