import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import optimized_bridge as bridge


class OptimizedBridgeIntegrityTests(unittest.TestCase):
    def test_shipped_mod_and_core_match_the_same_manifest_version(self):
        manifest = json.loads((bridge.ADAPTER / "patches/manifest.json").read_bytes())
        jar, _, _ = bridge.selected_bridge()
        with zipfile.ZipFile(jar) as archive:
            mod = json.loads(archive.read("fabric.mod.json"))
        self.assertEqual(mod["version"], manifest["version"])
        self.assertEqual(manifest["nativeCore"]["sourceVersion"], manifest["version"])
        core = bridge.ADAPTER / "patches" / manifest["nativeCore"]["file"]
        self.assertEqual(hashlib.sha256(core.read_bytes()).hexdigest(), manifest["nativeCore"]["sha256"])

    def test_native_core_is_verified_before_replace_and_backup_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            adapter = root / "adapter"
            artifacts = adapter / "patches"
            artifacts.mkdir(parents=True)
            runtime = root / "data/runtime"
            runtime.mkdir(parents=True)
            target = runtime / "eldencraft_core.dll"
            target.write_bytes(b"working upstream")
            (runtime / "eldencraft.me3").touch()
            artifact = artifacts / target.name
            artifact.write_bytes(b"corrupt")
            manifest = artifacts / "manifest.json"
            digest = hashlib.sha256(b"patched").hexdigest()
            manifest.write_text(json.dumps({"nativeCore": {"file": target.name, "sha256": digest}}))
            with patch.object(bridge, "ADAPTER", adapter), patch.object(bridge, "DATA", root / "data"):
                with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                    bridge.install_native(runtime)
                self.assertEqual(target.read_bytes(), b"working upstream")
                artifact.write_bytes(b"patched")
                installed = bridge.install_native(runtime)
                again = bridge.install_native(runtime)
            self.assertEqual(target.read_bytes(), b"patched")
            self.assertEqual((Path(installed["backup"]) / target.name).read_bytes(), b"working upstream")
            self.assertIsNone(again["backup"])
            self.assertEqual(len(list((root / "data/backups").iterdir())), 1)

    def test_native_manifest_cannot_select_other_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            adapter = Path(temporary)
            (adapter / "patches").mkdir()
            manifest = adapter / "patches/manifest.json"
            with patch.object(bridge, "ADAPTER", adapter):
                for filename in ["../eldencraft_core.dll", "C:/eldencraft_core.dll", "other.dll", "x\\eldencraft_core.dll"]:
                    manifest.write_text(json.dumps({"nativeCore": {"file": filename, "sha256": "0" * 64}}))
                    with self.assertRaisesRegex(ValueError, "filename"):
                        bridge.install_native(adapter / "runtime")

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
