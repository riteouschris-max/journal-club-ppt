"""Behavioral checks on isolated fixtures; never touch a user's paper project."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from PIL import Image
from audit import audit
from check_environment import clean_env, find_font, inspect
from project import crop, init, load, save, sha
from render_deck import changes, record_export
from verify_source_pixels import verify
import run


class PortabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="journal-club-isolated-")
        cls.base = Path(cls.temp.name)
        cls.fixture = cls.base / "中文 fixture"
        subprocess.run([sys.executable, str(ROOT / "scripts/make_demo.py"), "--workspace", str(cls.fixture), "--build-only"], check=True, env=clean_env(), capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.root = self.base / self._testMethodName
        shutil.copytree(self.fixture, self.root)
        self.sink = contextlib.redirect_stdout(io.StringIO())
        self.sink.__enter__()

    def tearDown(self):
        self.sink.__exit__(None, None, None)

    def test_dependency_isolation(self):
        report = inspect()
        self.assertTrue(report["can_build"])
        self.assertEqual(report["other_skills_required"], [])
        for package in report["packages"].values():
            self.assertTrue(Path(package["location"]).is_relative_to(Path(sys.prefix)))

    def test_cache_reuse_and_original_fidelity(self):
        before_text = (self.root / "cache/text/page-001.txt").stat().st_mtime_ns
        before_crop = (self.root / "assets/concept_panels.png").stat().st_mtime_ns
        init(self.root, self.root / "source/paper.pdf")
        crop(self.root, self.root / "crops.json")
        self.assertEqual(before_text, (self.root / "cache/text/page-001.txt").stat().st_mtime_ns)
        self.assertEqual(before_crop, (self.root / "assets/concept_panels.png").stat().st_mtime_ns)
        self.assertEqual(verify(self.root), 0)

    def test_pixel_tampering_with_updated_hash_is_rejected(self):
        asset_path = self.root / "assets/concept_panels.png"
        with Image.open(asset_path) as original:
            altered = original.copy()
        altered.putpixel((15, 15), (0, 255, 0))
        altered.save(asset_path)
        assets = load(self.root / "assets.json")
        assets["concept_panels"]["sha256"] = sha(asset_path)
        save(self.root / "assets.json", assets)
        self.assertEqual(verify(self.root), 1)
        self.assertTrue(load(self.root / "qa/source_pixels.json")["errors"])

    def test_single_slide_change_is_incremental(self):
        deck = load(self.root / "deck.json")
        deck["slides"][2]["blocks"][0]["body"] += "补充实验解释。"
        save(self.root / "deck.json", deck)
        self.assertEqual(changes(self.root)["pages"], [3])

    def test_locked_claim_is_rejected(self):
        audit(self.root, snapshot=True)
        deck = load(self.root / "deck.json")
        deck["slides"][2]["core"] = "Changed claim"
        save(self.root / "deck.json", deck)
        self.assertEqual(audit(self.root), 1)
        self.assertTrue(any("Locked slide" in error for error in load(self.root / "qa/report.json")["errors"]))

    def test_missing_panel_mapping_is_rejected(self):
        save(self.root / "figure_inventory.json", [])
        self.assertEqual(audit(self.root), 1)
        self.assertIn("Figure inventory missing", load(self.root / "qa/report.json")["errors"])

    def test_missing_renderer_records_partial_completion(self):
        report = inspect()
        report["renderer"] = None
        with patch.object(run, "inspect", return_value=report), patch.object(sys, "argv", ["run.py", "finish", "--workspace", str(self.root)]):
            self.assertEqual(run.main(), 2)
        self.assertTrue((self.root / "build/deck.pptx").exists())
        self.assertFalse((self.root / "output/deck.pdf").exists())
        self.assertEqual(load(self.root / "state.json")["phase"], "pending_export")

    def test_external_pdf_cannot_bind_to_changed_pptx(self):
        with self.assertRaisesRegex(ValueError, "PPTX changed"):
            record_export(self.root, self.root / "source/paper.pdf", "incorrect-hash")

    def test_invalid_explicit_font_is_not_silently_replaced(self):
        self.assertIsNone(find_font(str(self.root / "missing.otf")))

    def test_installer_preserves_custom_files_and_backs_up_updates(self):
        destination = self.root / "installed skill"
        env = clean_env()
        env["CODEX_HOME"] = str(self.root / "isolated codex")
        command = [sys.executable, str(ROOT / "install.py"), "--destination", str(destination), "--no-setup"]
        subprocess.run(command, check=True, env=env, capture_output=True)
        (destination / "custom.txt").write_text("user content", encoding="utf-8")
        subprocess.run(command, check=True, env=env, capture_output=True)
        self.assertEqual((destination / "custom.txt").read_text(), "user content")
        backups = list((Path(env["CODEX_HOME"]) / "skill-backups").glob("journal-club-ppt-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "custom.txt").read_text(), "user content")

    def test_installer_refuses_unrelated_nonempty_destination(self):
        destination = self.root / "unrelated"
        destination.mkdir()
        (destination / "document.txt").write_text("keep", encoding="utf-8")
        result = subprocess.run([sys.executable, str(ROOT / "install.py"), "--destination", str(destination), "--no-setup"], env=clean_env(), capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((destination / "document.txt").read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
