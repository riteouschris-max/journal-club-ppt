"""Install the downloaded bundle, back up prior skill files, then prepare its runtime."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--soffice")
    parser.add_argument("--font-file")
    parser.add_argument("--no-setup", action="store_true")
    parser.add_argument("--demo", type=Path)
    args = parser.parse_args()
    codex_dir = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser().resolve()
    target = (args.destination or codex_dir / "skills/journal-club-ppt").expanduser().resolve()
    files = json.loads((ROOT / "package-files.json").read_text(encoding="utf-8"))
    for name in files:
        source = (ROOT / name).resolve()
        destination = (target / name).resolve()
        if not source.is_relative_to(ROOT) or not destination.is_relative_to(target) or not source.is_file():
            raise ValueError("Invalid package entry: " + name)
    if target != ROOT:
        existing = target / "SKILL.md"
        if target.exists() and any(target.iterdir()):
            if not existing.is_file() or "name: journal-club-ppt" not in existing.read_text(encoding="utf-8-sig"):
                raise ValueError("Destination is not a journal-club-ppt installation; choose an empty directory")
            backup = codex_dir / "skill-backups" / ("journal-club-ppt-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
            shutil.copytree(target, backup, ignore=shutil.ignore_patterns(".venv", ".git", "__pycache__"))
            print("Previous skill files backed up:", backup)
        for name in files:
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, destination)
    print("Installed skill:", target)
    if args.no_setup:
        return 0
    command = [sys.executable, str(target / "setup.py")]
    for option, value in (("--soffice", args.soffice), ("--font-file", args.font_file), ("--demo", args.demo)):
        if value:
            command.extend([option, str(value)])
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONNOUSERSITE="1")
    return subprocess.run(command, env=env).returncode


if __name__ == "__main__":
    raise SystemExit(main())
