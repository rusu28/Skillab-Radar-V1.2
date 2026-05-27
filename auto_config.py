from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parent
DEFAULT_API = "https://skillab-tracker.csd.auth.gr/api"
DEFAULT_USERNAME = "event_public"
DEFAULT_PASSWORD = "PublicOnly2026"


def candidate_dirs() -> list[Path]:
    home = Path.home()
    dirs = [
        ROOT,
        ROOT / "data",
        ROOT / "data" / "metadata",
        ROOT / "inputs",
        home / "Downloads",
        home / "Desktop",
    ]
    return [path for path in dirs if path.exists()]


def find_file(filename: str) -> Path | None:
    for folder in candidate_dirs():
        direct = folder / filename
        if direct.exists():
            return direct.resolve()
        try:
            matches = list(folder.rglob(filename))
        except OSError:
            matches = []
        if matches:
            return matches[0].resolve()
    return None


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def write_yaml(path: Path, config: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, sort_keys=False, allow_unicode=True)


def write_env(path: Path, values: dict[str, str], overwrite: bool) -> None:
    if path.exists() and not overwrite:
        print(f"[skip] {path.name} already exists. Use --overwrite-env to replace it.")
        return
    lines = [f"{key}={value}" for key, value in values.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[ok] wrote {path}")


def ensure_dirs(config: dict[str, Any]) -> None:
    for key in ["cache_dir", "raw_dir", "results_csv_dir", "figures_dir", "provenance_dir"]:
        path = ROOT / config["paths"][key]
        path.mkdir(parents=True, exist_ok=True)
        print(f"[ok] directory {path.relative_to(ROOT)}")


def install_deps() -> None:
    print("[run] installing requirements.txt")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")])


def smoke_test() -> None:
    print("[run] smoke test")
    imports = ["pandas", "numpy", "requests", "yaml", "matplotlib", "seaborn", "streamlit"]
    missing = []
    for module in imports:
        try:
            __import__(module)
        except Exception:
            missing.append(module)
    if missing:
        print(f"[warn] missing Python modules: {', '.join(missing)}")
        print("       Run: run.bat setup")
    else:
        print("[ok] required Python modules import successfully")

    try:
        from src.config import load_config

        cfg = load_config(ROOT / "config.yaml")
        skills = Path(cfg["paths"]["esco_skills"])
        occupations = Path(cfg["paths"]["esco_occupations"])
        print(f"[ok] config loads. ESCO skills exists={skills.exists()} path={skills}")
        print(f"[ok] config loads. ESCO occupations exists={occupations.exists()} path={occupations}")
    except Exception as exc:
        print(f"[warn] project config smoke test failed: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure SKILLAB Skill Radar after moving the folder to another PC.")
    parser.add_argument("--skills", help="Path to mapping_of_ESCO_skills.xlsx")
    parser.add_argument("--occupations", help="Path to mapping_of_ESCO_occupations.xlsx")
    parser.add_argument("--api", default=os.getenv("TRACKER_API", DEFAULT_API))
    parser.add_argument("--username", default=os.getenv("TRACKER_USERNAME", DEFAULT_USERNAME))
    parser.add_argument("--password", default=os.getenv("TRACKER_PASSWORD", DEFAULT_PASSWORD))
    parser.add_argument("--install-deps", action="store_true", help="Install requirements.txt before smoke test.")
    parser.add_argument("--smoke-test", action="store_true", help="Check imports and config after writing files.")
    parser.add_argument("--overwrite-env", action="store_true", help="Replace existing .env.")
    args = parser.parse_args()

    config_path = ROOT / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config.yaml at {config_path}")

    skills = Path(args.skills).expanduser().resolve() if args.skills else find_file("mapping_of_ESCO_skills.xlsx")
    occupations = Path(args.occupations).expanduser().resolve() if args.occupations else find_file("mapping_of_ESCO_occupations.xlsx")

    if not skills or not skills.exists():
        raise FileNotFoundError(
            "Could not find mapping_of_ESCO_skills.xlsx. "
            "Put it in this folder/Downloads or run: python auto_config.py --skills C:\\path\\mapping_of_ESCO_skills.xlsx"
        )
    if not occupations or not occupations.exists():
        raise FileNotFoundError(
            "Could not find mapping_of_ESCO_occupations.xlsx. "
            "Put it in this folder/Downloads or run: python auto_config.py --occupations C:\\path\\mapping_of_ESCO_occupations.xlsx"
        )

    config = load_yaml(config_path)
    config["tracker"]["api"] = args.api
    config["paths"]["esco_skills"] = str(skills)
    config["paths"]["esco_occupations"] = str(occupations)
    write_yaml(config_path, config)
    print(f"[ok] updated {config_path}")

    write_env(
        ROOT / ".env",
        {
            "TRACKER_API": args.api,
            "TRACKER_USERNAME": args.username,
            "TRACKER_PASSWORD": args.password,
            "ESCO_SKILLS_PATH": str(skills),
            "ESCO_OCCUPATIONS_PATH": str(occupations),
        },
        overwrite=args.overwrite_env,
    )
    ensure_dirs(config)

    if args.install_deps:
        install_deps()
    if args.smoke_test:
        smoke_test()

    print("\nNext commands:")
    print("  run.bat pipeline")
    print("  run.bat dashboard")


if __name__ == "__main__":
    main()
