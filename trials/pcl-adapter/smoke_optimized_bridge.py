"""Load the local bridge through real Fabric/Minecraft in a temporary worldless directory."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

from install_pcl import applies, maven_path
from optimized_bridge import ADAPTER, INSTANCE, selected_bridge


def smoke() -> None:
    instance_name = INSTANCE.name
    minecraft = INSTANCE.parents[1]
    profile = json.loads((INSTANCE / (instance_name + ".json")).read_bytes())
    scratch = ADAPTER / "smoke" / time.strftime("%Y%m%d-%H%M%S")
    scratch.mkdir(parents=True)
    mods = scratch / "mods"
    mods.mkdir()
    artifact, filename, checksum = selected_bridge()
    (ADAPTER / "smoke-evidence.json").write_text(json.dumps({
        "passed": False, "jarSha256": checksum, "state": "startup check pending", "liveGameplayTested": False
    }, indent=2), encoding="utf-8")
    shutil.copy2(artifact, mods / filename)
    for api in (INSTANCE / "mods").glob("fabric-api-*.jar"):
        shutil.copy2(api, mods / api.name)
    shutil.copytree(INSTANCE / "config", scratch / "config")
    (scratch / "options.txt").write_text("maxFps:30\nfullscreen:false\n", encoding="utf-8")
    paths = []
    for library in profile["libraries"]:
        if not applies(library):
            continue
        item = library.get("downloads", {}).get("artifact")
        path = minecraft / "libraries" / (item["path"] if item else maven_path(library["name"]))
        if not path.is_file():
            raise FileNotFoundError(path)
        paths.append(str(path))
        classifier = library.get("natives", {}).get("windows")
        if classifier:
            native = library["downloads"]["classifiers"][classifier.replace("${arch}", "64")]
            paths.append(str(minecraft / "libraries" / native["path"]))
    paths.append(str(INSTANCE / (instance_name + ".jar")))
    native_dir = str(INSTANCE / (instance_name + "-natives"))
    offline = bytearray(__import__("hashlib").md5(b"OfflinePlayer:Steve").digest())
    offline[6] = (offline[6] & 15) | 48
    offline[8] = (offline[8] & 63) | 128
    command = [str(INSTANCE / "java/bin/java.exe"), "-Xmx2G", "--enable-native-access=ALL-UNNAMED",
               "-Djava.library.path=" + native_dir, "-Dorg.lwjgl.librarypath=" + native_dir,
               "-cp", os.pathsep.join(paths), profile["mainClass"],
               "--username", "Steve", "--uuid", uuid.UUID(bytes=bytes(offline)).hex,
               "--accessToken", "0", "--version", instance_name, "--versionType", "release",
               "--gameDir", str(scratch), "--assetsDir", str(minecraft / "assets"),
               "--assetIndex", profile["assetIndex"]["id"], "--width", "854", "--height", "480"]
    env = os.environ.copy()
    env["ELDENCRAFT_AUTO_WORLD"] = "0"
    env["ELDENCRAFT_CREATE_WORLD"] = "0"
    for key in ("ELDENCRAFT_DATA_DIR", "ELDENCRAFT_CAMPAIGN_CONFIG", "ELDENCRAFT_CAMPAIGN_DIR"):
        env.pop(key, None)
    output = scratch / "console.log"
    with output.open("w", encoding="utf-8") as stream:
        process = subprocess.Popen(command, cwd=scratch, env=env, stdout=stream, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 120
            ready = False
            while time.monotonic() < deadline:
                text = output.read_text(encoding="utf-8", errors="replace")
                if "Mixin apply failed" in text or "Exception in thread" in text or process.poll() is not None:
                    raise RuntimeError("Minecraft smoke startup failed (exit=" + str(process.poll()) + "); see " + str(output))
                if "OpenAL initialized" in text and "EldenCraft shared-memory and GPU bridge ready" in text:
                    ready = True
                    time.sleep(5)
                    break
                time.sleep(1)
            if not ready:
                raise TimeoutError("Minecraft smoke startup timed out; see " + str(output))
            text = output.read_text(encoding="utf-8", errors="replace")
            if process.poll() is not None or "Mixin apply failed" in text or "Exception in thread" in text:
                raise RuntimeError("Minecraft exited after initialization; see " + str(output))
            result = {"passed": True, "jarSha256": checksum, "log": str(output),
                      "scope": "Real Fabric/Minecraft client startup and Mixin loading; automatic world opening disabled",
                      "liveGameplayTested": False}
            (ADAPTER / "smoke-evidence.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps(result, indent=2), flush=True)
        finally:
            # There is no world or save in this temporary client. Release the test process only.
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=15)


if __name__ == "__main__":
    smoke()
