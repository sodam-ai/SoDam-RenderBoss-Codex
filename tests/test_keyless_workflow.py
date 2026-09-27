from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts import build_local_marketplace, render_guard


def options(folder: Path, **overrides: object) -> argparse.Namespace:
    values = {
        "image": [], "mask": None, "prompt": "One-story clinic", "locked_subject": "",
        "style": "", "edit_area": "", "keep_text": "", "extra": "", "avoid": "",
        "aspect_ratio": "auto", "resolution": "2K", "size": None, "out_dir": folder,
        "prefix": "trial", "attempt": 1, "preview_max_edge": 256,
        "preview_quality": 72, "no_preview": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class KeylessWorkflowTests(unittest.TestCase):
    def test_generation_prepare_and_finish(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            job = render_guard.prepare(options(root))
            self.assertFalse(job["api_key_required"])
            self.assertEqual(job["tool_call"]["referenced_image_paths"], [])
            raw = root / "built_in_result.png"
            Image.new("RGB", (1600, 900), "gray").save(raw)
            result = render_guard.finalize(argparse.Namespace(
                job=Path(job["job_file"]), output=raw, no_preview=False,
                preview_max_edge=256, preview_quality=72))
            self.assertTrue(result["aspect_ratio_pass"])
            self.assertIsNone(result["requested_size_pass"])
            self.assertEqual(result["output_geometry"]["reference_size"], [2752, 1536])
            self.assertTrue(Path(result["outputs"]["gpt"]).is_file())
            self.assertTrue(Path(result["previews"]["gpt"]).is_file())
            self.assertTrue(Path(result["manifest_file"]).is_file())
            self.assertEqual(result["semantic_review"], "pending_visual_inspection")

    def test_edit_references_and_attempts(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            primary, reference = root / "primary.png", root / "reference.png"
            Image.new("RGB", (1200, 800), "white").save(primary)
            Image.new("RGB", (400, 400), "blue").save(reference)
            job = render_guard.prepare(options(root, image=[primary, reference],
                prompt="", style="warm stone", locked_subject="Two floors", attempt=2))
            self.assertEqual(job["target_aspect_ratio"], "3:2")
            self.assertEqual(len(job["input_previews"]), 2)
            self.assertEqual(job["tool_call"]["referenced_image_paths"],
                             [str(primary.resolve()), str(reference.resolve())])
            self.assertIn("attempt2", job["job_file"])
            self.assertIn("Two floors", Path(job["prompt_file"]).read_text())

    def test_finalize_rejects_missing_primary_after_project_move(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            primary = root / "primary.png"
            Image.new("RGB", (1600, 900)).save(primary)
            job = render_guard.prepare(options(root, image=[primary], prompt="",
                style="overcast", locked_subject="Two floors", no_preview=True))
            raw = root / "raw.png"
            Image.new("RGB", (1600, 900)).save(raw)
            primary.rename(root / "moved.png")
            with self.assertRaisesRegex(ValueError, "Input image does not exist"):
                render_guard.finalize(argparse.Namespace(
                    job=Path(job["job_file"]), output=raw, no_preview=True,
                    preview_max_edge=256, preview_quality=72))
            self.assertFalse((root / "trial_attempt1_gpt.png").exists())

    def test_explicit_size_is_checked_against_actual_output(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            job = render_guard.prepare(options(root, size="1536x864"))
            self.assertEqual(job["requested_size"], [1536, 864])
            self.assertEqual(job["target_aspect_ratio"], "16:9")
            raw = root / "raw.png"
            Image.new("RGB", (1600, 900)).save(raw)
            result = render_guard.finalize(argparse.Namespace(
                job=Path(job["job_file"]), output=raw, no_preview=True,
                preview_max_edge=256, preview_quality=72))
            self.assertTrue(result["aspect_ratio_pass"])
            self.assertFalse(result["requested_size_pass"])
            self.assertIn("Output pixel size differs from explicit --size", result["errors"])

    def test_explicit_size_rejects_conflicting_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as folder, self.assertRaisesRegex(ValueError, "different output proportions"):
            render_guard.prepare(options(Path(folder), size="1536x864", aspect_ratio="1:1"))

    def test_cli_reports_size_mismatch_as_failure(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            job = render_guard.prepare(options(root, size="1536x864", no_preview=True))
            raw = root / "raw.png"
            Image.new("RGB", (1600, 900)).save(raw)
            command = [sys.executable, str(Path(render_guard.__file__).resolve()),
                       "--finalize", "--job", job["job_file"], "--output", str(raw),
                       "--no-preview"]
            process = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(process.returncode, 2)
            self.assertFalse(json.loads(process.stdout)["requested_size_pass"])

    def test_preview_only_preserves_geometry_information(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "building.png"
            Image.new("RGB", (1200, 800)).save(source)
            process = subprocess.run([sys.executable, str(Path(render_guard.__file__).resolve()),
                "--preview-only", "--image", str(source), "--out-dir", str(root / "out")],
                capture_output=True, text=True, check=False)
            self.assertEqual(process.returncode, 0, process.stderr)
            result = json.loads(process.stdout)
            self.assertEqual(result["output_geometry"]["aspect_ratio"], "3:2")
            self.assertTrue(Path(result["previews"][str(source)]).is_file())

    def test_preview_only_validates_all_inputs_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "building.png"
            Image.new("RGB", (1200, 800)).save(source)
            out_dir = root / "out"
            process = subprocess.run([
                sys.executable, str(Path(render_guard.__file__).resolve()),
                "--preview-only", "--image", str(source), str(root / "missing.png"),
                "--out-dir", str(out_dir),
            ], capture_output=True, text=True, check=False)
            self.assertEqual(process.returncode, 2)
            self.assertFalse((out_dir / "_previews").exists())

    def test_mask_keeps_unedited_pixels_exact(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            primary, mask, raw = root / "primary.png", root / "mask.png", root / "raw.png"
            Image.new("RGB", (100, 100), "red").save(primary)
            mask_image = Image.new("RGBA", (100, 100), (255, 255, 255, 255))
            for x in range(20, 40):
                for y in range(20, 40):
                    mask_image.putpixel((x, y), (255, 255, 255, 0))
            mask_image.save(mask)
            Image.new("RGB", (100, 100), "blue").save(raw)
            job = render_guard.prepare(options(root, image=[primary], mask=mask,
                prompt="", style="change local area", locked_subject="One floor"))
            result = render_guard.finalize(argparse.Namespace(
                job=Path(job["job_file"]), output=raw, no_preview=True,
                preview_max_edge=256, preview_quality=72))
            with Image.open(result["outputs"]["gpt"]) as image:
                self.assertEqual(image.getpixel((0, 0)), (255, 0, 0, 255))
                self.assertEqual(image.getpixel((30, 30)), (0, 0, 255, 255))
            self.assertTrue(result["mask_applied_locally"])

    def test_mask_resize_does_not_fake_exact_native_size(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            primary, mask, raw = root / "primary.png", root / "mask.png", root / "raw.png"
            Image.new("RGB", (1536, 864), "red").save(primary)
            Image.new("RGBA", (1536, 864), (255, 255, 255, 0)).save(mask)
            Image.new("RGB", (1600, 900), "blue").save(raw)
            job = render_guard.prepare(options(root, image=[primary], mask=mask,
                prompt="", style="change sky", locked_subject="Two floors", size="1536x864",
                no_preview=True))
            result = render_guard.finalize(argparse.Namespace(
                job=Path(job["job_file"]), output=raw, no_preview=True,
                preview_max_edge=256, preview_quality=72))
            self.assertEqual(result["output_dimensions"]["gpt"], {"width": 1536, "height": 864})
            self.assertEqual(result["raw_output_dimensions"], {"width": 1600, "height": 900})
            self.assertFalse(result["requested_size_pass"])

    def test_mask_requires_alpha(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            primary, mask = root / "primary.png", root / "mask.png"
            Image.new("RGB", (100, 100)).save(primary)
            Image.new("RGB", (100, 100)).save(mask)
            with self.assertRaisesRegex(ValueError, "RGBA"):
                render_guard.prepare(options(root, image=[primary], mask=mask,
                    prompt="", style="edit", locked_subject="One floor"))

    def test_final_does_not_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            job = render_guard.prepare(options(root))
            raw = root / "raw.png"
            Image.new("RGB", (1600, 900)).save(raw)
            finish = argparse.Namespace(job=Path(job["job_file"]), output=raw,
                no_preview=True, preview_max_edge=256, preview_quality=72)
            render_guard.finalize(finish)
            with self.assertRaisesRegex(ValueError, "already exists"):
                render_guard.finalize(finish)

    def test_preview_failure_is_recorded_with_output(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            job = render_guard.prepare(options(root, no_preview=True))
            raw = root / "raw.png"
            Image.new("RGB", (1600, 900)).save(raw)
            result = render_guard.finalize(argparse.Namespace(
                job=Path(job["job_file"]), output=raw, no_preview=False,
                preview_max_edge=100, preview_quality=72))
            self.assertTrue(Path(result["outputs"]["gpt"]).is_file())
            self.assertTrue(Path(result["manifest_file"]).is_file())
            self.assertIn("Preview failed", result["errors"][0])

    def test_cli_reports_preview_failure_as_failure(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            job = render_guard.prepare(options(root, no_preview=True))
            raw = root / "raw.png"
            Image.new("RGB", (1600, 900)).save(raw)
            process = subprocess.run([
                sys.executable, str(Path(render_guard.__file__).resolve()),
                "--finalize", "--job", job["job_file"], "--output", str(raw),
                "--preview-max-edge", "100",
            ], capture_output=True, text=True, check=False)
            self.assertEqual(process.returncode, 2)
            result = json.loads(process.stdout)
            self.assertIn("Preview failed", result["errors"][0])
            self.assertTrue(Path(result["manifest_file"]).is_file())

    def test_cli_rejects_malformed_job_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            raw = root / "raw.png"
            Image.new("RGB", (1600, 900)).save(raw)
            job_path = root / "bad_job.json"
            for job, message in (
                ([], "JSON object"),
                ({}, "missing required field"),
                ({"mode": "generation", "images": [], "mask_reference": None,
                  "target_aspect_ratio": "0:0", "requested_resolution": "2K",
                  "prompt_file": "prompt.txt"}, "invalid target aspect ratio"),
            ):
                job_path.write_text(json.dumps(job), encoding="utf-8")
                process = subprocess.run([
                    sys.executable, str(Path(render_guard.__file__).resolve()),
                    "--finalize", "--job", str(job_path), "--output", str(raw),
                    "--no-preview",
                ], capture_output=True, text=True, check=False)
                self.assertEqual(process.returncode, 2)
                self.assertIn(message, process.stderr)
                self.assertNotIn("Traceback", process.stderr)

    def test_mask_rejects_wrong_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            primary, mask = root / "primary.png", root / "mask.png"
            Image.new("RGB", (100, 100)).save(primary)
            Image.new("RGBA", (80, 80), (255, 255, 255, 0)).save(mask)
            with self.assertRaisesRegex(ValueError, "dimensions"):
                render_guard.prepare(options(root, image=[primary], mask=mask,
                    prompt="", style="edit", locked_subject="One floor"))

    def test_committed_marketplace_plugin_matches_sources(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        marketplace = json.loads((repo / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["source"]["source"], "git-subdir")
        self.assertEqual(entry["source"]["path"], "./plugins/architectural-render-guard")
        plugin = repo / "plugins/architectural-render-guard"
        manifest = json.loads((plugin / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(entry["name"], manifest["name"])
        for relative in build_local_marketplace.FILES:
            with self.subTest(relative=relative):
                self.assertEqual((repo / relative).read_bytes(), (plugin / relative).read_bytes())

    def test_local_package_contains_keyless_source_only(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "marketplace"
            repo = Path(__file__).resolve().parents[1]
            result = build_local_marketplace.build(repo, destination)
            marketplace = json.loads((destination / ".agents/plugins/marketplace.json").read_text())
            self.assertEqual(marketplace["plugins"][0]["source"]["source"], "local")
            plugin = Path(result["plugin_root"])
            self.assertTrue((plugin / "scripts/render_guard.py").is_file())
            self.assertFalse((plugin / "outputs").exists())
            with self.assertRaisesRegex(ValueError, "already exists"):
                build_local_marketplace.build(repo, destination)


if __name__ == "__main__":
    unittest.main()
