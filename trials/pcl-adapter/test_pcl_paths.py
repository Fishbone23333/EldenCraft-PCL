import json
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
            root = Path(folder)
            values = self.load_paths(root, {"pcl_root": "Launcher", "data_root": "Data"})
            self.assertEqual(values["PCL"], root / "Launcher")
            self.assertEqual(values["DATA"], root / "Data")
            self.assertEqual(values["RELEASE"], root / "trials/EldenCraft-0.25.5")
            self.assertEqual(values["INSTANCE"], root / "Launcher/.minecraft/versions" / values["NAME"])

    def test_absolute_paths_are_not_rebased(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            values = self.load_paths(root / "repo", {"pcl_root": str(root / "launcher"),
                "release_root": str(root / "official"), "data_root": str(root / "runtime")})
            self.assertEqual(values["PCL"], root / "launcher")
            self.assertEqual(values["RELEASE"], root / "official")
            self.assertEqual(values["DATA"], root / "runtime")

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
            self.assertTrue(updated["hud"]["enemyBar"]["enabled"])
            self.assertEqual(updated["progression"], original["progression"])
            self.assertEqual(len(list(data_root.glob("*.bak"))), 1)
            self.assertEqual(json.loads(next(data_root.glob("*.bak")).read_bytes()), original)
