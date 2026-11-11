"""Regresja ścieżek hooków Ventoya (bez uprawnień root).

Opcjonalnie DRACUT_LIB=/ścieżka/dracut-lib.sh uruchamia też skrypty przez
prawdziwą funkcję list_hooks() z dracut; test nie pobiera kodu z sieci.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / "build/dracut/95horyzont-ventoy/module-setup.sh"


class VentoyHooks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "usr/lib/dracut").mkdir(parents=True)
        (self.root / "lib").symlink_to("usr/lib")

    def install_module(self):
        # inst_dir pochodzi normalnie z dracut; tu odtwarzamy budowanie drzewa
        # initramfs, bez instalowania plików na hoście.
        subprocess.run(
            ["bash", "-eu", "-c",
             'initdir="$1"; . "$2"; inst_dir() { mkdir -p "$initdir$1"; }; install',
             "test", str(self.root), str(MODULE)], check=True)

    def inject(self, base):
        for stage, name in [("pre-udev", "99-ventoy-inotifyd-start.sh"),
                            ("initqueue/timeout", "99-ventoy-timeout.sh")]:
            dest = self.root / base / stage / name
            src = self.root / name
            src.write_text(f"echo {name}\n")
            shutil.copyfile(src, dest)

    def test_reproduces_missing_legacy_directory(self):
        with self.assertRaises(FileNotFoundError):
            self.inject("lib/dracut/hooks")

    def test_legacy_ventoy_can_copy_hooks(self):
        self.install_module()
        self.inject("lib/dracut/hooks")
        self.assertTrue((self.root / "usr/lib/dracut/hooks/pre-udev/99-ventoy-inotifyd-start.sh").is_file())

    def test_current_ventoy_can_copy_hooks(self):
        self.install_module()
        self.inject("var/lib/dracut/hooks")
        self.assertTrue((self.root / "var/lib/dracut/hooks/initqueue/timeout/99-ventoy-timeout.sh").is_file())

    def test_existing_dracut_hooks_are_preserved(self):
        saved = []
        for base in ["usr/lib/dracut/hooks", "var/lib/dracut/hooks"]:
            path = self.root / base / "pre-udev/10-existing.sh"
            path.parent.mkdir(parents=True)
            path.write_text("existing dracut hook\n")
            saved.append(path)
        self.install_module()
        for path in saved:
            self.assertEqual(path.read_text(), "existing dracut hook\n")

    def dispatch_with_dracut(self, base):
        source = os.environ.get("DRACUT_LIB")
        if not source:
            self.skipTest("ustaw DRACUT_LIB, aby sprawdzić rzeczywistą funkcję dracut")
        code = Path(source).read_text()
        start = code.index("list_hooks() {")
        end = code.index("\nsource_hook()", start)
        fn = code[start:end]
        for directory in ["/var/lib/dracut/hooks", "/etc/dracut/hooks", "/usr/lib/dracut/hooks"]:
            fn = fn.replace('"' + directory, '"${INITRD}' + directory)
        self.install_module()
        self.inject(base)
        script = fn + '\nfor stage in pre-udev initqueue/timeout; do\n' \
                 'for hook in $(list_hooks "$stage"); do . "$hook"; done\ndone\n'
        result = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                                env=dict(os.environ, INITRD=str(self.root)), check=True)
        self.assertEqual(result.stdout.splitlines(),
                         ["99-ventoy-inotifyd-start.sh", "99-ventoy-timeout.sh"])

    def test_dracut_executes_legacy_injection(self):
        self.dispatch_with_dracut("lib/dracut/hooks")

    def test_dracut_executes_current_injection(self):
        self.dispatch_with_dracut("var/lib/dracut/hooks")


if __name__ == "__main__":
    unittest.main(verbosity=2)
