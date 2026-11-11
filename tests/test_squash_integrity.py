"""Build checks must reject damaged payloads and valid images with wrong contents."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

VERIFY = Path(__file__).resolve().parents[1] / 'build/verify-squashfs.sh'


@unittest.skipUnless(all(shutil.which(t) for t in ('mksquashfs', 'unsquashfs', 'rsync')),
                     'requires squashfs-tools and rsync')
class SquashIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        (self.source / 'payload').write_bytes(b'payload test\n' * 2048)
        (self.source / 'link').symlink_to('payload')
        self.image = self.root / 'system.img'
        subprocess.run(['mksquashfs', str(self.source), str(self.image), '-comp', 'gzip',
                        '-noappend', '-no-xattrs', '-no-fragments', '-processors', '1',
                        '-b', '4096', '-quiet', '-no-progress'], check=True,
                       capture_output=True)

    def verify(self):
        return subprocess.run(['bash', str(VERIFY), str(self.image), str(self.source)],
                              capture_output=True, text=True, timeout=20)

    def test_valid_image(self):
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_damaged_data_block(self):
        # The superblock remains valid: checking only unsquashfs -s misses this.
        with self.image.open('r+b') as f:
            f.seek(96)
            f.write(b'\0\0\0\0')
        result = self.verify()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Uszkodzony SquashFS', result.stderr)

    def test_content_mismatch(self):
        (self.source / 'payload').write_bytes(b'changed source')
        result = self.verify()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('różni się', result.stderr)


if __name__ == '__main__':
    unittest.main()
