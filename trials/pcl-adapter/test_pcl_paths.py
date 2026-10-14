import json
import os
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
from unittest.mock import patch

import optimized_bridge


class PortablePathsTests(unittest.TestCase):
    def load_paths(self, root, settings):
        adapter = root / "trials/pcl-adapter"
        adapter.mkdir(parents=True)
        shutil.copy2(Path(__file__).with_name("pcl_paths.py"), adapter / "pcl_paths.py")
        (adapter / "local.json").write_text(json.dumps(settings), encoding="utf-8")
        return runpy.run_path(str(adapter / "pcl_paths.py"))

    def test_relative_paths_follow_repository_including_spaces(self):
        with tempfile.TemporaryDirectory(prefix="EldenCraft PCL ") as folder:
            # Windows TEMP can use an 8.3 alias (RUNNER~1); the adapter resolves it.
            root = Path(folder).resolve()
            values = self.load_paths(root, {"pcl_root": "Launcher", "data_root": "Data"})
            self.assertEqual(values["PCL"], root / "Launcher")
            self.assertEqual(values["DATA"], root / "Data")
            self.assertEqual(values["RELEASE"], root / "trials/EldenCraft-0.25.5")
            self.assertEqual(values["INSTANCE"], root / "Launcher/.minecraft/versions" / values["NAME"])

    def test_absolute_paths_are_not_rebased(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            values = self.load_paths(root / "repo", {"pcl_root": str(root / "launcher"),
                "release_root": str(root / "official"), "data_root": str(root / "runtime")})
            self.assertEqual(values["PCL"], root / "launcher")
            self.assertEqual(values["RELEASE"], root / "official")
            self.assertEqual(values["DATA"], root / "runtime")

    @unittest.skipUnless(os.name == "nt", "Windows short-path aliases")
    def test_windows_short_path_resolves_to_same_configured_folder(self):
        import ctypes
        from ctypes import wintypes

        short_path = ctypes.WinDLL("kernel32", use_last_error=True).GetShortPathNameW
        short_path.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        short_path.restype = wintypes.DWORD
        with tempfile.TemporaryDirectory(prefix="EldenCraft PCL short path ") as folder:
            root = Path(folder).resolve()
            launcher = root / "Launcher Folder"
            launcher.mkdir()
            size = short_path(str(launcher), None, 0)
            self.assertGreater(size, 0, "Windows can obtain configured folder alias")
            buffer = ctypes.create_unicode_buffer(size)
            self.assertGreater(short_path(str(launcher), buffer, size), 0)
            alias = Path(buffer.value)
            if alias == launcher:
                self.skipTest("8.3 aliases disabled on this volume")
            values = self.load_paths(root / "repo", {"pcl_root": str(alias)})
            self.assertEqual(values["PCL"], launcher)
            self.assertTrue(values["PCL"].samefile(alias))

    def test_stamina_migration_preserves_other_rules_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            data_root = Path(folder)
            campaign = data_root / "campaign.json"
            original = {"stamina": {"costs": {"sword": 5}, "guardBase": 7},
                "hud": {"stamina": {"enabled": True}, "bossBar": {"enabled": True}},
                "progression": {"custom": "retained"}}
            campaign.write_text(json.dumps(original), encoding="utf-8")
            with patch.object(optimized_bridge, "DATA", data_root):
                optimized_bridge.configure_free_stamina()
                updated = json.loads(campaign.read_bytes())
                optimized_bridge.configure_free_stamina()
            self.assertTrue(all(v == 0 for v in updated["stamina"]["costs"].values()))
            self.assertEqual(updated["stamina"]["guardBase"], 0)
            self.assertFalse(updated["hud"]["stamina"]["enabled"])
            self.assertFalse(updated["hud"]["enemyBar"]["enabled"])
            self.assertEqual(updated["progression"], original["progression"])
            self.assertEqual(len(list(data_root.glob("*.bak"))), 1)
            self.assertEqual(json.loads(next(data_root.glob("*.bak")).read_bytes()), original)
