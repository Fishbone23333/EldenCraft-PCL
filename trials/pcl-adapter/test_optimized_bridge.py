import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import optimized_bridge as bridge


class OptimizedBridgeIntegrityTests(unittest.TestCase):
    def test_corrupt_custom_artifact_is_rejected_before_replacing_installed_mod(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            adapter = root / "adapter"
            artifacts = adapter / "patches"
            artifacts.mkdir(parents=True)
            (artifacts / "new.jar").write_bytes(b"corrupt")
            (artifacts / "manifest.json").write_text(json.dumps({"file": "new.jar", "sha256": hashlib.sha256(b"correct").hexdigest()}))
            instance = root / "instance"
            (instance / "mods").mkdir(parents=True)
            (instance / ".ma-eldencraft-pcl").touch()
            old = instance / "mods/eldencraft-bridge-0.25.5.jar"
            old.write_bytes(b"working original")
            with patch.object(bridge, "ADAPTER", adapter):
                with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                    bridge.install_bridge(instance)
            self.assertEqual(old.read_bytes(), b"working original")

    def test_reinstall_keeps_one_verified_mod_and_preserves_original_backup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            instance = root / "instance"
            (instance / "mods").mkdir(parents=True)
            (instance / ".ma-eldencraft-pcl").touch()
            old = instance / "mods/eldencraft-bridge-0.25.5.jar"
            old.write_bytes(b"original")
            artifact = root / "source.jar"
            artifact.write_bytes(b"patched")
            digest = hashlib.sha256(b"patched").hexdigest()
            with patch.object(bridge, "DATA", root / "data"), patch.object(bridge, "selected_bridge", return_value=(artifact, "eldencraft-bridge-0.25.5-pcl.2.jar", digest)):
                installed = bridge.install_bridge(instance)
                bridge.install_bridge(instance)
            self.assertEqual(len(list((instance / "mods").glob("*.jar"))), 1)
            self.assertEqual(Path(installed["bridge"]).read_bytes(), b"patched")
            self.assertEqual((Path(installed["backup"]) / old.name).read_bytes(), b"original")

    def test_unmarked_instance_is_never_modified(self):
        with tempfile.TemporaryDirectory() as temporary:
            instance = Path(temporary)
            with patch.object(bridge, "selected_bridge") as selection:
                with self.assertRaisesRegex(RuntimeError, "unmarked"):
                    bridge.install_bridge(instance)
                selection.assert_not_called()
            self.assertEqual(list(instance.iterdir()), [])
