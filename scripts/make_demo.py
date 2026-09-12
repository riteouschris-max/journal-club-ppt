"""Build a five-slide layout fixture with self-authored diagrams, never research data."""
import argparse
from pathlib import Path

import pymupdf as fitz
from project import SKILL, init, crop, save, load
from render_deck import build, export, raster
from audit import audit
from verify_source_pixels import verify


def source_pdf(path):
    doc = fitz.open()
    page = doc.new_page(width=1000, height=720)
    navy, burgundy, pale = (.094, .208, .290), (.545, .251, .290), (.945, .961, .953)
    page.insert_text((45, 48), "JOURNAL CLUB / LAYOUT DEMONSTRATION", fontsize=23, color=navy)
    page.insert_text((45, 87), "Original-source screenshots, readable explanations, editable slides", fontsize=18, color=navy)
    page.insert_text((45, 122), "Self-authored test fixture. No paper, author, animal, assay, or measured result is represented.", fontsize=14)
    page.draw_line((45, 145), (955, 145), color=burgundy, width=1.5)
    for j, label in enumerate(("A / QUESTION", "B / COMPARISON", "C / INTERPRETATION")):
        x = 45 + j * 310
        page.draw_rect(fitz.Rect(x, 180, x + 285, 415), color=navy, fill=pale, width=1)
        page.insert_text((x + 15, 218), label, fontsize=19, color=navy)
        lines = [("What is being tested?", "Keep the claim bounded."), ("Preserve original labels.", "Keep control groups visible."), ("Describe the observation.", "Explain evidence limits.")][j]
        page.insert_text((x + 15, 285), lines[0], fontsize=15)
        page.insert_text((x + 15, 323), lines[1], fontsize=15)
    page.insert_text((45, 455), "A-C are conceptual layout panels, not experimental data.", fontsize=17, color=burgundy)
    page.draw_rect(fitz.Rect(45, 505, 955, 670), color=navy, fill=pale)
    for j, label in enumerate(("Purpose", "Design", "Observation", "Interpretation")):
        x = 65 + j * 225
        page.insert_text((x, 551), label, fontsize=20, color=navy)
        page.insert_text((x, 593), "Source-linked explanation", fontsize=13)
        if j < 3:
            page.insert_text((x + 192, 552), ">", fontsize=25, color=burgundy)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    doc.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--soffice")
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args()
    root = args.workspace.resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError("Demo needs an empty workspace; it never overwrites an existing paper project")
    root.mkdir(parents=True, exist_ok=True)
    input_file = root / "source/layout-fixture.pdf"
    source_pdf(input_file)
    init(root, input_file)
    crops = [
        {"id": "cover", "page": 1, "rect": [25, 15, 975, 680], "dpi": 220},
        {"id": "concept_panels", "page": 1, "rect": [30, 160, 970, 475], "dpi": 220},
        {"id": "explanation_flow", "page": 1, "rect": [30, 490, 970, 685], "dpi": 220},
    ]
    save(root / "crops.json", crops)
    crop(root, root / "crops.json")
    deck = load(SKILL / "examples/deck.json")
    save(root / "deck.json", deck)
    # These panels belong only to the explicitly labeled layout fixture above.
    save(root / "figure_inventory.json", [
        {"id": "DEMO_A_C", "assets": ["concept_panels"], "critical": True, "verified": True, "disposition": "slide", "slide_ids": ["result-side"], "source_type": "self-authored layout fixture; not research"},
        {"id": "DEMO_FLOW", "assets": ["explanation_flow"], "critical": True, "verified": True, "disposition": "slide", "slide_ids": ["result-wide"], "source_type": "self-authored layout fixture; not research"},
    ])
    build(root)
    if verify(root):
        return 1
    if args.build_only:
        print("DEMO_PPTX_ONLY: PDF rendering and visual review are still pending")
        return 0
    export(root, args.soffice)
    raster(root, root / "output/deck.pdf")
    result = audit(root)
    print("Demo is a layout test, not a test of scientific reading. Inspect all five rendered pages.")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
