"""Shared, account-free paths for the portable PCL adapter."""
from __future__ import annotations

import json
import os
from pathlib import Path

ADAPTER = Path(__file__).resolve().parent
REPO = ADAPTER.parents[1]
TRIALS = ADAPTER.parent
NAME = "EldenCraft-26.3-Fabric-0.19.5"
SETTINGS = ADAPTER / "local.json"
settings = json.loads(SETTINGS.read_bytes()) if SETTINGS.is_file() else {}


def configured_path(key: str, fallback: Path) -> Path:
    path = Path(settings.get(key) or fallback)
    return (path if path.is_absolute() else REPO / path).resolve()


PCL = configured_path("pcl_root", Path(os.environ.get("ELDENCRAFT_PCL_ROOT", "D:/PCL")))
DATA = configured_path("data_root", TRIALS / "EldenCraftData")
RELEASE = configured_path("release_root", TRIALS / "EldenCraft-0.25.5")
MC = PCL / ".minecraft"
INSTANCE = MC / "versions" / NAME
