"""Compare untouched evidence crops with a fresh render of the original source PDF."""
import argparse
from pathlib import Path

from PIL import Image, ImageChops
import pymupdf as fitz
from project import load, local, save, sha


def verify(root):
    checked, errors = [], []
    for key, asset in load(root / "assets.json", {}).items():
        if asset.get("kind") != "evidence":
            continue
        try:
            path = local(root, asset["path"])
            source = local(root, asset.get("source_path", "source/paper.pdf"))
            if asset["sha256"] != sha(path) or asset["source_sha256"] != sha(source):
                raise ValueError("source or crop hash changed")
            if asset.get("pymupdf_version", fitz.VersionBind) != fitz.VersionBind:
                raise ValueError("PDF renderer version changed; use the recorded version or inspect and deliberately re-extract the asset")
            with fitz.open(source) as doc:
                scale = asset["dpi"] / 72
                pix = doc[asset["page"] - 1].get_pixmap(matrix=fitz.Matrix(scale, scale), clip=fitz.Rect(asset["rect"]), alpha=False)
                expected = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            with Image.open(path) as image:
                actual = image.convert("RGB")
                if actual.size != expected.size or ImageChops.difference(actual, expected).getbbox() is not None:
                    raise ValueError("pixels differ from the recorded original crop")
            checked.append(key)
        except (KeyError, ValueError, OSError, IndexError) as exc:
            errors.append(f"{key}: {exc}")
    result = {"status": "FAIL" if errors else "PASS", "checked_assets": checked, "errors": errors, "scope": "Full crop pixel fidelity only; scientific panel selection still needs visual review."}
    save(root / "qa/source_pixels.json", result)
    print(f"{result['status']}: {len(checked)} original crops verified; {len(errors)} errors")
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    raise SystemExit(verify(parser.parse_args().workspace.resolve()))
