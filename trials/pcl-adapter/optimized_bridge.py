"""Install the verified local PCL bridge build and free-stamina campaign settings."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
from datetime import datetime
from pcl_paths import INSTANCE, DATA, RELEASE

ADAPTER = Path(__file__).resolve().parent
TRIALS = ADAPTER.parent


def selected_bridge() -> tuple[Path, str, str]:
    manifest = ADAPTER / "patches" / "manifest.json"
    if manifest.is_file():
        data = json.loads(manifest.read_bytes())
        filename = data["file"]
        if Path(filename).name != filename or not filename.endswith(".jar"):
            raise ValueError("Invalid bridge manifest filename")
        artifact = manifest.parent / filename
        expected = data["sha256"]
        if hashlib.sha256(artifact.read_bytes()).hexdigest() != expected:
            raise ValueError("Local bridge artifact checksum mismatch")
        return artifact, filename, expected
    artifact = RELEASE / "payload" / "eldencraft-bridge.jar"
    return artifact, "eldencraft-bridge-0.25.5.jar", hashlib.sha256(artifact.read_bytes()).hexdigest()


def install_bridge(instance: Path = INSTANCE) -> dict:
    if not (instance / ".ma-eldencraft-pcl").is_file():
        raise RuntimeError("Refusing to modify an unmarked PCL instance")
    artifact, filename, expected = selected_bridge()
    mods = instance / "mods"
    mods.mkdir(exist_ok=True)
    backup = DATA / "backups" / ("pcl-optimization-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    for existing in mods.glob("eldencraft-bridge*.jar"):
        if existing.name == filename and hashlib.sha256(existing.read_bytes()).hexdigest() == expected:
            continue
        backup.mkdir(parents=True, exist_ok=True)
        shutil.move(str(existing), str(backup / existing.name))
    target = mods / filename
    if not target.is_file():
        temporary = mods / (filename + ".installing")
        shutil.copy2(artifact, temporary)
        os.replace(temporary, target)
    if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
        raise ValueError("Installed bridge checksum mismatch")
    return {"bridge": str(target), "sha256": expected, "backup": str(backup)}


def install_native(runtime: Path | None = None) -> dict:
    """Verify before replacement; retain upstream payload and the previous core."""
    runtime = runtime or DATA / "runtime"
    manifest = ADAPTER / "patches" / "manifest.json"
    data = json.loads(manifest.read_bytes())["nativeCore"]
    filename = data["file"]
    if filename != "eldencraft_core.dll":
        raise ValueError("Invalid native core manifest filename")
    artifact = manifest.parent / filename
    content = artifact.read_bytes()
    expected = data["sha256"]
    if hashlib.sha256(content).hexdigest() != expected:
        raise ValueError("Local native core artifact checksum mismatch")
    target = runtime / filename
    # The upstream setup owns creation and marking of this isolated runtime.
    if not target.is_file() or not (runtime / "eldencraft.me3").is_file():
        raise RuntimeError("Run setup before installing the native core")
    if hashlib.sha256(target.read_bytes()).hexdigest() == expected:
        return {"nativeCore": str(target), "sha256": expected, "backup": None}
    backup = DATA / "backups" / ("pcl-native-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    backup.mkdir(parents=True)
    shutil.copy2(target, backup / filename)
    temporary = runtime / (filename + ".installing")
    try:
        temporary.write_bytes(content)
        if hashlib.sha256(temporary.read_bytes()).hexdigest() != expected:
            raise ValueError("Staged native core checksum mismatch")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return {"nativeCore": str(target), "sha256": expected, "backup": str(backup)}


def configure_free_stamina() -> str:
    campaign = DATA / "campaign.json"
    original = campaign.read_bytes()
    data = json.loads(original)
    for kind in set(data["stamina"]["costs"]) | {"sword", "axe", "spear", "mace", "bow", "crossbow", "other"}:
        data["stamina"]["costs"][kind] = 0
    data["stamina"].update(guardBase=0, guardPerDamage=0, guardRecovery=0, regenDelaySeconds=0)
    data["hud"]["stamina"]["enabled"] = False
    data["hud"].setdefault("enemyBar", {
        "enabled": False, "width": 88, "height": 7,
        "headOffset": .35, "maxDistance": 32, "showNumbers": True,
    })
    data["hud"]["enemyBar"]["enabled"] = False
    if json.loads(original) != data:
        backup = campaign.with_name("campaign.json.pre-free-stamina-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".bak")
        backup.write_bytes(original)
        temporary = campaign.with_suffix(".pcl.tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, campaign)
    return str(campaign)


if __name__ == "__main__":
    import subprocess
    running = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", "@(Get-Process javaw,eldenring -ErrorAction SilentlyContinue).Count"],
        capture_output=True, text=True, check=True,
    )
    if int(running.stdout.strip() or "0"):
        raise RuntimeError("Close Minecraft and Elden Ring before installing")
    result = install_bridge()
    result["native"] = install_native()
    result["campaign"] = configure_free_stamina()
    print(json.dumps(result, indent=2))
