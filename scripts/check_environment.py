"""Read-only dependency, renderer, and CJK font checks; no other skill imports."""
from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = {"PyMuPDF": "pymupdf", "Pillow": "PIL", "python-pptx": "pptx", "fonttools": "fontTools"}


def clean_env():
    env = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME"):
        env.pop(key, None)
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONNOUSERSITE="1")
    return env


def configuration():
    file = ROOT / ".runtime.json"
    return json.loads(file.read_text(encoding="utf-8")) if file.exists() else {}


def find_soffice(explicit=None):
    configured = explicit or os.environ.get("JOURNAL_CLUB_SOFFICE") or configuration().get("soffice")
    if configured and Path(configured).is_file():
        return str(Path(configured).resolve())
    # An explicit typo must not silently select a different application.
    if explicit:
        return None
    candidates = [shutil.which("soffice"), shutil.which("libreoffice")]
    if os.name == "nt":
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.environ.get("LOCALAPPDATA")):
            if base:
                candidates.extend([str(Path(base) / "LibreOffice/program/soffice.exe"), str(Path(base) / "Programs/LibreOffice/program/soffice.exe")])
    candidates.extend(["/Applications/LibreOffice.app/Contents/MacOS/soffice", "/usr/bin/soffice", "/usr/bin/libreoffice"])
    return next((str(Path(p).resolve()) for p in candidates if p and Path(p).is_file()), None)


def select_renderer(soffice=None):
    executable = find_soffice(soffice)
    if executable:
        return {"kind": "libreoffice", "executable": executable}
    if soffice:
        return None
    if os.name == "nt":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"PowerPoint.Application\CLSID"):
                powershell = shutil.which("pwsh") or shutil.which("powershell")
                if powershell:
                    return {"kind": "powerpoint", "executable": powershell}
        except OSError:
            pass
    return None


def inspect_font(path, index=0):
    from fontTools.ttLib import TTFont
    font = TTFont(str(path), fontNumber=index, lazy=True)
    try:
        cmap = font.getBestCmap() or {}
        if not all(ord(c) in cmap for c in "研究结果模型对照核心结论补充说明012ABC"):
            return None
        family = font["name"].getDebugName(16) or font["name"].getDebugName(1)
        return {"family": family, "file": str(Path(path).resolve()), "index": index}
    finally:
        font.close()


def find_font(explicit=None):
    configured = explicit or os.environ.get("JOURNAL_CLUB_FONT_FILE") or configuration().get("font_file")
    candidates = [configured] if configured else []
    if not explicit:
        win = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        candidates.extend(str(win / n) for n in ("msyh.ttc", "msyh.ttf", "simhei.ttf"))
        candidates.extend(["/System/Library/Fonts/PingFang.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"])
        for directory in (Path.home() / ".local/share/fonts", Path.home() / "Library/Fonts"):
            candidates.extend(str(directory / n) for n in ("NotoSansCJKsc-Regular.otf", "NotoSansSC-Regular.otf"))
        if shutil.which("fc-match"):
            try:
                result = subprocess.run(["fc-match", "-f", "%{file}", "Noto Sans CJK SC:lang=zh-cn"], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    candidates.append(result.stdout.strip())
            except (OSError, subprocess.TimeoutExpired):
                pass
    for name in dict.fromkeys(candidates):
        if not name or not Path(name).is_file():
            continue
        try:
            result = inspect_font(name)
            if result:
                return result
        except (ImportError, OSError, ValueError, KeyError):
            continue
    return None


def inspect(soffice=None, font_file=None):
    packages = {}
    for distribution, module in PACKAGES.items():
        try:
            imported = importlib.import_module(module)
            packages[distribution] = {"ok": True, "version": importlib.metadata.version(distribution), "location": str(Path(imported.__file__).resolve())}
        except Exception as exc:
            packages[distribution] = {"ok": False, "error": str(exc)}
    python_ok = sys.version_info >= (3, 10)
    font = find_font(font_file) if packages["fonttools"]["ok"] else None
    renderer = select_renderer(soffice)
    can_build = python_ok and all(p["ok"] for p in packages.values()) and font is not None
    return {
        "status": "READY_FOR_RENDER_TEST" if can_build and renderer else "PARTIAL" if can_build else "MISSING_DEPENDENCIES",
        "python": sys.executable, "python_version": sys.version.split()[0], "python_ok": python_ok,
        "packages": packages, "font": font, "renderer": renderer, "soffice": renderer['executable'] if renderer and renderer['kind']=='libreoffice' else None,
        "can_build": can_build, "can_attempt_pdf_export": bool(can_build and renderer),
        "other_skills_required": [],
        "agent_capabilities": {"read_pdf_images": "host must provide", "execute_local_commands": "host must provide", "image_generation": "optional; never inferred from local packages"},
        "next_action": "Run demo, then inspect rendered slides" if can_build and renderer else "See README: install missing packages/font/renderer; do not report final PDF as complete",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--soffice")
    parser.add_argument("--font-file")
    parser.add_argument("--json", action="store_true", help="Print detailed JSON (default output is compact)")
    args = parser.parse_args()
    result = inspect(args.soffice, args.font_file)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["status"])
        print("Python:", result["python"])
        print("Packages:", ", ".join(k + "=" + (v.get("version") or "MISSING") for k, v in result["packages"].items()))
        print("CJK font:", result["font"]["family"] if result["font"] else "MISSING")
        print("PDF renderer:", result["renderer"] or "MISSING")
        print("Other skills required: none. Image generation: host capability, optional.")
    return 0 if result["can_attempt_pdf_export"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
