"""Stable command entrypoint, with an isolated runtime and explicit completion states."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from check_environment import ROOT, clean_env, inspect


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python scripts/run.py doctor|project|build|finish|audit|demo [arguments]")
        return 2
    runtime = ROOT / ".venv"
    python = runtime / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if python.exists() and Path(sys.prefix).resolve() != runtime.resolve():
        return subprocess.run([str(python), str(Path(__file__).resolve()), *args], env=clean_env()).returncode
    command, rest = args[0], args[1:]
    scripts = {"doctor": "check_environment.py", "project": "project.py", "build": "render_deck.py", "audit": "audit.py", "demo": "make_demo.py"}
    if command in scripts:
        extra = ["build", *rest] if command == "build" else rest
        return subprocess.run([sys.executable, str(ROOT / "scripts" / scripts[command]), *extra], env=clean_env()).returncode
    if command != "finish":
        raise ValueError("Unknown command: " + command)
    import argparse
    parser = argparse.ArgumentParser(prog="run.py finish")
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--soffice")
    opts = parser.parse_args(rest)
    root = opts.workspace.resolve()
    status = inspect(opts.soffice)
    if not status["can_build"]:
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 2
    from render_deck import build, export, raster
    from project import load, save, utc
    from audit import audit
    build(root)
    if not status["renderer"]:
        state = load(root / "state.json", {})
        state.update(phase="pending_export", pending=["pdf_export", "visual_review"], next_action="Configure an installed LibreOffice renderer, or export this PPTX with a reliable host tool and record-export", updated_at=utc())
        save(root / "state.json", state)
        print("PPTX_READY_PDF_PENDING: original PPTX preserved; PDF and visual QA are incomplete.")
        return 2
    try:
        export(root, opts.soffice)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        state = load(root / "state.json", {})
        state.update(phase="pending_export", pending=["pdf_export", "visual_review"], next_action="Resolve this renderer error and rerun finish: " + str(exc), updated_at=utc())
        save(root / "state.json", state)
        print("PPTX_READY_PDF_PENDING:", exc)
        return 2
    raster(root, root / "output/deck.pdf")
    result = audit(root)
    # Never mark visual approval merely because automated checks passed.
    print("Inspect output/deck_renders and fix defects before audit --reviewed-pages all.")
    return result


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.CalledProcessError, ImportError) as exc:
        print(f"Command incomplete: {exc}. See README / run setup.py when dependencies are missing.", file=sys.stderr)
        raise SystemExit(1)
