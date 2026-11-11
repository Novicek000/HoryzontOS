"""Exercise copy subprocess output without mounting or changing a disk."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class CopySystem(unittest.TestCase):
    def run_copy(self, rc):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = root / 'rsync'
            fake.write_text('#!' + sys.executable + '\nimport sys\n'
                            'print("usr/lib/lang_ext", flush=True)\n'
                            'sys.stderr.write("diagnostic " * 20000 + "FINAL ERROR\\n")\n'
                            'sys.stderr.flush()\n'
                            f'sys.exit({rc})\n')
            fake.chmod(0o755)
            code = '''
import os
from horyzontos.common import install
install.SYSIMAGE = os.environ['TARGET']
try:
    install.copy_system(lambda f, n: None)
except RuntimeError as e:
    print(e)
    raise SystemExit(3)
print('COPY COMPLETE')
'''
            return subprocess.run([sys.executable, '-c', code], cwd=REPO,
                                  env=dict(os.environ, PATH=tmp + ':' + os.environ['PATH'],
                                           TARGET=tmp + '/target', HORYZONTOS_SOURCE=tmp + '/source'),
                                  capture_output=True, text=True, timeout=5)

    def test_large_stderr_does_not_block_success(self):
        result = self.run_copy(0)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('COPY COMPLETE', result.stdout)

    def test_large_stderr_reports_copy_failure(self):
        result = self.run_copy(23)
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn('FINAL ERROR', result.stdout)
        self.assertIn('23', result.stdout)


if __name__ == '__main__':
    unittest.main()
