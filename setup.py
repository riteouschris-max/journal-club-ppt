"""Prepare this downloaded skill in place; keep dependencies in its own .venv."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
from check_environment import clean_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--soffice", help="Existing LibreOffice executable; no Office installation is performed")
    parser.add_argument("--font-file", help="Installed CJK font file, if detection needs help")
    parser.add_argument("--demo", type=Path, help="Also build and render a small layout demonstration")
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error("Python 3.10 or newer is required")
    runtime = ROOT / ".venv"
    python = runtime / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    env = clean_env()
    if not python.exists():
        print("Creating an isolated runtime for journal-club-ppt...", flush=True)
        subprocess.run([sys.executable, "-m", "venv", str(runtime)], check=True, env=env)
    else:
        # Do not accidentally install into a copied/broken venv or global Python.
        result = subprocess.run([str(python), "-c", "import sys; print(sys.prefix)"], check=True, capture_output=True, text=True, env=env)
        if Path(result.stdout.strip()).resolve() != runtime.resolve():
            raise RuntimeError("Existing .venv points elsewhere. Move it aside and rerun setup.")
    subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(ROOT / "requirements.txt")], check=True, env=env)
    config_path = ROOT / ".runtime.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    for key, value in (("soffice", args.soffice), ("font_file", args.font_file)):
        if value:
            resolved = Path(value).expanduser().resolve()
            if not resolved.is_file():
                parser.error(f"{key} does not exist: {resolved}")
            config[key] = str(resolved)
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    result = subprocess.run([str(python), str(ROOT / "scripts/check_environment.py")], env=env)
    if result.returncode:
        print("Python packages installed. Finish font/renderer setup using README before final delivery.")
        return result.returncode
    if args.demo:
        return subprocess.run([str(python), str(ROOT / "scripts/run.py"), "demo", "--workspace", str(args.demo.resolve())], env=env).returncode
    print("Ready. Invoke $journal-club-ppt with a paper in Codex; setup itself does not write scientific conclusions.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (subprocess.CalledProcessError, OSError, RuntimeError) as exc:
        print(f"Setup did not finish: {exc}", file=sys.stderr)
        raise SystemExit(1)
