from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts import builtin_guard


def args(out_dir: Path, **overrides: object) -> argparse.Namespace:
    defaults = {
        "image": [], "mask": None, "prompt": "A modern public library", "locked_subject": "",
        "style": "", "edit_area": "", "keep_text": "", "extra": "", "avoid": "",
        "aspect_ratio": "auto", "resolution": "2K", "size": None,
        "out_dir": out_dir, "prefix": "test",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class BuiltinGuardTests(unittest.TestCase):
    def test_generation_prepares_keyless_job(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            result = builtin_guard.prepare(args(Path(folder)))
            self.assertFalse(result["api_key_required"])
            self.assertEqual(result["target_aspect_ratio"], "16:9")
            self.assertFalse(result["resolution_guaranteed"])
            self.assertIn("public library", Path(result["prompt_file"]).read_text())

    def test_edit_uses_primary_image_ratio_and_locks_building(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "input.png"
            Image.new("RGB", (1200, 800)).save(source)
            result = builtin_guard.prepare(args(Path(folder), image=[source], prompt="", style="daylight", locked_subject="Two floors, seven windows"))
            self.assertEqual(result["target_aspect_ratio"], "3:2")
            self.assertIn("Two floors, seven windows", Path(result["prompt_file"]).read_text())

    def test_edit_requires_constraints(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "input.png"
            Image.new("RGB", (100, 100)).save(source)
            with self.assertRaisesRegex(ValueError, "locked-subject"):
                builtin_guard.prepare(args(Path(folder), image=[source]))

    def test_existing_job_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            options = args(Path(folder))
            builtin_guard.prepare(options)
            with self.assertRaisesRegex(ValueError, "already exists"):
                builtin_guard.prepare(options)

    def test_verify_checks_ratio_and_leaves_semantic_review_pending(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            result = builtin_guard.prepare(args(root))
            image = root / "output.png"
            Image.new("RGB", (1600, 900)).save(image)
            checked = builtin_guard.verify(argparse.Namespace(job=Path(result["job_file"]), output=image))
            self.assertTrue(checked["aspect_ratio_pass"])
            self.assertEqual(checked["semantic_review"], "pending_visual_inspection")
            self.assertEqual(json.loads((root / "test_output_verification.json").read_text())["width"], 1600)

    def test_verify_flags_wrong_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            result = builtin_guard.prepare(args(root))
            image = root / "square.png"
            Image.new("RGB", (1024, 1024)).save(image)
            checked = builtin_guard.verify(argparse.Namespace(job=Path(result["job_file"]), output=image))
            self.assertFalse(checked["aspect_ratio_pass"])

    def test_multiple_references_and_mask_are_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, reference, mask = (root / name for name in ("source.png", "reference.png", "mask.png"))
            for path in (source, reference):
                Image.new("RGB", (1200, 800)).save(path)
            Image.new("RGBA", (1200, 800), (255, 255, 255, 0)).save(mask)
            result = builtin_guard.prepare(args(root, image=[source, reference], mask=mask, style="daylight", locked_subject="Three floors", keep_text="LIBRARY"))
            self.assertEqual(len(result["images"]), 2)
            self.assertEqual(result["mask_reference"], str(mask.resolve()))
            self.assertIn("LIBRARY", Path(result["prompt_file"]).read_text())

    def test_prefix_cannot_escape_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as folder, self.assertRaisesRegex(ValueError, "prefix"):
            builtin_guard.prepare(args(Path(folder), prefix="../outside"))

    def test_original_gpt_size_constraints_are_preserved(self) -> None:
        self.assertEqual(builtin_guard.parse_pixel_size("1536x864"), (1536, 864))
        builtin_guard.validate_gpt_size(1536, 864)
        with self.assertRaisesRegex(ValueError, "multiples of 16"):
            builtin_guard.validate_gpt_size(1600, 900)
        with self.assertRaisesRegex(ValueError, "positive"):
            builtin_guard.parse_pixel_size("0x864")


if __name__ == "__main__":
    unittest.main()
