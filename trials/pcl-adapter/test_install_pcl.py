import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import install_pcl


class InstallIntegrityTests(unittest.TestCase):
    def test_corrupt_cached_file_is_replaced_only_with_verified_content(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'library.jar'
            path.write_bytes(b'corrupted cache')
            payload = b'verified payload'
            with patch.object(install_pcl, 'fetch', return_value=payload):
                install_pcl.download(('https://example.invalid/lib', path, hashlib.sha1(payload).hexdigest(), 'sha1'))
            self.assertEqual(path.read_bytes(), payload)

    def test_bad_download_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'library.jar'
            path.write_bytes(b'existing')
            with patch.object(install_pcl, 'fetch', return_value=b'bad response'), patch.object(install_pcl.time, 'sleep'):
                with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
                    install_pcl.download(('https://example.invalid/lib', path, hashlib.sha1(b'expected').hexdigest(), 'sha1'))
            self.assertEqual(path.read_bytes(), b'existing')
            self.assertFalse(path.with_name(path.name + '.ma-download').exists())

    def test_unrelated_instance_is_rejected_before_download_or_write(self):
        with tempfile.TemporaryDirectory() as folder:
            instance = Path(folder) / 'existing-world'
            instance.mkdir()
            sentinel = instance / 'options.txt'
            sentinel.write_bytes(b'user settings')
            with patch.object(install_pcl, 'INSTANCE', instance), patch.object(install_pcl, 'MARKER', instance / '.ma-eldencraft-pcl'), patch.object(install_pcl, 'fetch') as fetch:
                with self.assertRaisesRegex(RuntimeError, 'unrelated instance'):
                    install_pcl.install()
                fetch.assert_not_called()
            self.assertEqual(sentinel.read_bytes(), b'user settings')
            self.assertEqual(list(instance.iterdir()), [sentinel])


if __name__ == '__main__':
    unittest.main()
