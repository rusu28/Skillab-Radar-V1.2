from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from .env import load_dotenv


def load_config(path: str | Path = "config.yaml") -> dict[str, Any]:
    load_dotenv()
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    config["tracker"]["api"] = os.getenv("TRACKER_API", config["tracker"]["api"]).rstrip("/")
    config["tracker"]["username"] = os.getenv("TRACKER_USERNAME", "event_public")
    config["tracker"]["password"] = os.getenv("TRACKER_PASSWORD", "PublicOnly2026")

    if os.getenv("ESCO_SKILLS_PATH"):
        config["paths"]["esco_skills"] = os.getenv("ESCO_SKILLS_PATH")
    if os.getenv("ESCO_OCCUPATIONS_PATH"):
        config["paths"]["esco_occupations"] = os.getenv("ESCO_OCCUPATIONS_PATH")

    for key in ["cache_dir", "raw_dir", "results_csv_dir", "figures_dir", "provenance_dir"]:
        Path(config["paths"][key]).mkdir(parents=True, exist_ok=True)

    return config
