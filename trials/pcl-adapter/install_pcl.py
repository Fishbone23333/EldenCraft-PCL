"""Install EldenCraft and the verified local PCL bridge into an isolated instance.

Game metadata/files come from Mojang and Fabric. No account files are read.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
import urllib.request
from optimized_bridge import install_bridge, configure_free_stamina
from pcl_paths import ADAPTER, TRIALS, RELEASE, DATA, MC, NAME, INSTANCE

ROOT = TRIALS
MARKER = INSTANCE / ".ma-eldencraft-pcl"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "MA-EldenCraft-PCL/1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def download(job: tuple[str, Path, str | None, str]) -> bool:
    url, path, expected, algorithm = job
    if path.is_file() and expected and hashlib.new(algorithm, path.read_bytes()).hexdigest() == expected:
        return False
    for attempt in range(4):
        try:
            content = fetch(url)
            if expected and hashlib.new(algorithm, content).hexdigest() != expected:
                raise ValueError(f"Checksum mismatch: {path.name}")
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(path.name + ".ma-download")
            temporary.write_bytes(content)
            os.replace(temporary, path)
            return True
        except Exception:
            if attempt == 3:
                raise
            time.sleep(attempt + 1)
    raise AssertionError("unreachable")


def applies(library: dict) -> bool:
    allowed = not library.get("rules")
    for rule in library.get("rules", []):
        system = rule.get("os", {})
        if system.get("name", "windows") != "windows":
            continue
        if system.get("arch", "x86_64") not in ("x86_64", "amd64"):
            continue
        if rule.get("features"):
            continue
        allowed = rule["action"] == "allow"
    return allowed


def maven_path(name: str) -> str:
    group, artifact, version, *classifier = name.split(":")
    suffix = "-" + classifier[0] if classifier else ""
    return f"{group.replace('.', '/')}/{artifact}/{version}/{artifact}-{version}{suffix}.jar"


def install() -> None:
    if INSTANCE.exists() and not MARKER.is_file():
        raise RuntimeError(f"Refusing to overwrite unrelated instance: {INSTANCE}")
    INSTANCE.mkdir(parents=True, exist_ok=True)
    MARKER.write_text("SocketByte/EldenCraft v0.25.5; MC 26.3; Fabric 0.19.5\n", encoding="utf-8")
    manifest = json.loads(fetch("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"))
    version = next(v for v in manifest["versions"] if v["id"] == "26.3")
    metadata_bytes = fetch(version["url"])
    if hashlib.sha1(metadata_bytes).hexdigest() != version["sha1"]:
        raise ValueError("Minecraft metadata checksum mismatch")
    base = json.loads(metadata_bytes)
    fabric = json.loads(fetch("https://meta.fabricmc.net/v2/versions/loader/26.3/0.19.5/profile/json"))
    if fabric["inheritsFrom"] != "26.3" or base["javaVersion"]["majorVersion"] != 25:
        raise ValueError("Unexpected game/Java profile")
    base["id"] = NAME
    base["clientVersion"] = "26.3"
    base["mainClass"] = fabric["mainClass"]
    for kind in ("game", "jvm"):
        base["arguments"][kind].extend(fabric["arguments"].get(kind, []))
    overrides = {lib["name"].split(":")[:2][0] + ":" + lib["name"].split(":")[1] for lib in fabric["libraries"]}
    base["libraries"] = [lib for lib in base["libraries"] if ":".join(lib["name"].split(":")[:2]) not in overrides] + fabric["libraries"]
    base["arguments"]["jvm"].append("-Djava.net.preferIPv4Stack=true")
    jobs = []
    client = base["downloads"]["client"]
    jobs.append((client["url"], INSTANCE / (NAME + ".jar"), client["sha1"], "sha1"))
    for lib in base["libraries"]:
        if not applies(lib):
            continue
        artifact = lib.get("downloads", {}).get("artifact")
        if artifact:
            jobs.append((artifact["url"], MC / "libraries" / artifact["path"], artifact["sha1"], "sha1"))
        else:
            path = maven_path(lib["name"])
            url = lib.get("url", "https://libraries.minecraft.net/").rstrip("/") + "/" + path
            sha = lib.get("sha256") or lib.get("sha1") or fetch(url + ".sha1").decode().strip().split()[0]
            jobs.append((url, MC / "libraries" / path, sha, "sha256" if lib.get("sha256") else "sha1"))
        classifier = lib.get("natives", {}).get("windows")
        if classifier:
            native = lib["downloads"]["classifiers"][classifier.replace("${arch}", "64")]
            jobs.append((native["url"], MC / "libraries" / native["path"], native["sha1"], "sha1"))
    index = base["assetIndex"]
    index_path = MC / "assets" / "indexes" / (index["id"] + ".json")
    download((index["url"], index_path, index["sha1"], "sha1"))
    assets = json.loads(index_path.read_bytes())["objects"]
    for sha in {v["hash"] for v in assets.values()}:
        jobs.append((f"https://resources.download.minecraft.net/{sha[:2]}/{sha}", MC / "assets" / "objects" / sha[:2] / sha, sha, "sha1"))
    if base.get("logging", {}).get("client"):
        log = base["logging"]["client"]["file"]
        jobs.append((log["url"], MC / "assets" / "log_configs" / log["id"], log["sha1"], "sha1"))
    print(f"Checking/downloading {len(jobs)} official game, library and asset files", flush=True)
    changed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
        for count, updated in enumerate(pool.map(download, jobs), 1):
            changed += updated
            if count % 250 == 0:
                print(f"Verified {count}/{len(jobs)} ({changed} downloaded)", flush=True)
    (INSTANCE / (NAME + ".json")).write_text(json.dumps(base, indent=2), encoding="utf-8")
    mods = INSTANCE / "mods"
    mods.mkdir(exist_ok=True)
    bridge = install_bridge(INSTANCE)
    configure_free_stamina()
    deps = json.loads((RELEASE / "config" / "windows-release.json").read_bytes())
    api = deps["minecraft"]["fabric_api"]
    download((api["url"], mods / f"fabric-api-{api['version']}.jar", api["sha256"], "sha256"))
    config = INSTANCE / "config"
    config.mkdir(exist_ok=True)
    link = {"config": str(DATA / "campaign.json"), "directory": str(DATA / "runtime" / "data" / "campaign")}
    (config / "eldencraft-campaign-link.json").write_text(json.dumps(link, indent=2), encoding="utf-8")
    pcl = INSTANCE / "PCL"
    pcl.mkdir(exist_ok=True)
    settings = pcl / "Setup.ini"
    if not settings.exists():
        settings.write_text("VersionArgumentIndieV2:True\nVersionArgumentJavaV2:2\n", encoding="utf-8-sig")
    java_source = DATA / "tools" / "java-25.0.4.1+1" / "jdk-25.0.4.1+1-jre"
    java_dest = INSTANCE / "java"
    if not java_dest.exists():
        shutil.copytree(java_source, java_dest)
    (INSTANCE / "options.txt").write_text("autoJump:false\npauseOnLostFocus:false\nfullscreen:false\nrenderDistance:8\nsimulationDistance:5\nmaxFps:60\n", encoding="utf-8") if not (INSTANCE / "options.txt").exists() else None
    evidence = {"upstream": "https://github.com/SocketByte/EldenCraft/releases/tag/v0.25.5", "instance": str(INSTANCE), "verifiedFiles": len(jobs), "downloadedFiles": changed, "libraries": len(base["libraries"]), "bridgeSha256": bridge["sha256"], "bridge": bridge["bridge"]}
    (ROOT / "pcl-adapter" / "install-evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2), flush=True)


if __name__ == "__main__":
    install()
