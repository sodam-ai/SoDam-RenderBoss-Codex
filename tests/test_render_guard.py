from __future__ import annotations

import argparse
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from PIL import Image


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "render_guard.py"
SPEC = importlib.util.spec_from_file_location("render_guard", SCRIPT_PATH)
assert SPEC and SPEC.loader
render_guard = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = render_guard
SPEC.loader.exec_module(render_guard)


class GeometryTests(unittest.TestCase):
    def test_nearest_common_ratios(self) -> None:
        self.assertEqual(render_guard.nearest_aspect_ratio(1536, 1024), "3:2")
        self.assertEqual(render_guard.nearest_aspect_ratio(1920, 1080), "16:9")
        self.assertEqual(render_guard.nearest_aspect_ratio(1024, 1536), "2:3")
        self.assertEqual(render_guard.nearest_aspect_ratio(2048, 2048), "1:1")

    def test_default_geometry_is_2k_and_matches_source_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "source.png"
            Image.new("RGB", (1536, 1024), "white").save(image_path)
            args = argparse.Namespace(
                image=[image_path],
                aspect_ratio="auto",
                resolution="2K",
                size=None,
            )

            geometry = render_guard.resolve_output_geometry(args)

        self.assertEqual(geometry.aspect_ratio, "3:2")
        self.assertEqual(geometry.resolution, "2K")
        self.assertEqual(geometry.gpt_size, "2528x1696")

    def test_explicit_aspect_ratio_overrides_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "source.png"
            Image.new("RGB", (1536, 1024), "white").save(image_path)
            args = argparse.Namespace(
                image=[image_path],
                aspect_ratio="16:9",
                resolution="2K",
                size=None,
            )

            geometry = render_guard.resolve_output_geometry(args)

        self.assertEqual(geometry.aspect_ratio, "16:9")
        self.assertEqual(geometry.gpt_size, "2752x1536")
        self.assertEqual(geometry.selection_reason, "explicit --aspect-ratio")

    def test_legacy_size_is_validated_and_drives_gpt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "source.png"
            Image.new("RGB", (1024, 1024), "white").save(image_path)
            args = argparse.Namespace(
                image=[image_path],
                aspect_ratio="auto",
                resolution="2K",
                size="1536x1024",
            )

            geometry = render_guard.resolve_output_geometry(args)

        self.assertEqual(geometry.aspect_ratio, "3:2")
        self.assertEqual(geometry.gpt_size, "1536x1024")

    def test_invalid_gpt_size_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "multiples of 16"):
            render_guard.validate_gpt_size(1000, 1000)

    def test_all_shared_official_sizes_are_valid_for_gpt(self) -> None:
        for sizes in render_guard.OFFICIAL_OUTPUT_DIMENSIONS.values():
            for width, height in sizes.values():
                render_guard.validate_gpt_size(width, height)

    def test_gemini_config_uses_official_response_format(self) -> None:
        geometry = render_guard.OutputGeometry(
            source_width=1536,
            source_height=1024,
            aspect_ratio="3:2",
            resolution="2K",
            gpt_size="2528x1696",
            selection_reason="test",
        )

        config = render_guard.gemini_generation_config(geometry)

        self.assertEqual(config["responseFormat"]["image"]["aspectRatio"], "3:2")
        self.assertEqual(config["responseFormat"]["image"]["imageSize"], "2K")

    def test_gemini_gateway_config_uses_image_config(self) -> None:
        geometry = render_guard.OutputGeometry(
            source_width=1536,
            source_height=1024,
            aspect_ratio="3:2",
            resolution="2K",
            gpt_size="2528x1696",
            selection_reason="test",
        )

        config = render_guard.gemini_generation_config_for_mode(geometry, "image-config")

        self.assertEqual(config["imageConfig"]["aspectRatio"], "3:2")
        self.assertEqual(config["imageConfig"]["imageSize"], "2K")
        self.assertNotIn("responseFormat", config)

    def test_gemini_geometry_mode_depends_on_endpoint(self) -> None:
        self.assertEqual(
            render_guard.resolve_gemini_geometry_mode(
                "https://generativelanguage.googleapis.com",
                "auto",
            ),
            "response-format",
        )
        self.assertEqual(
            render_guard.resolve_gemini_geometry_mode(
                "https://api.iiiiitoken.com",
                "auto",
            ),
            "image-config",
        )

    def test_generated_aspect_ratio_is_enforced(self) -> None:
        geometry = render_guard.OutputGeometry(
            source_width=1536,
            source_height=1024,
            aspect_ratio="3:2",
            resolution="2K",
            gpt_size="2528x1696",
            selection_reason="test",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            valid_path = Path(temp_dir) / "valid.png"
            invalid_path = Path(temp_dir) / "invalid.png"
            Image.new("RGB", (2528, 1696), "white").save(valid_path)
            Image.new("RGB", (2048, 2048), "white").save(invalid_path)

            self.assertEqual(
                render_guard.validate_generated_aspect_ratio(valid_path, geometry, "Test"),
                (2528, 1696),
            )
            with self.assertRaisesRegex(ValueError, "instead of the requested 3:2"):
                render_guard.validate_generated_aspect_ratio(invalid_path, geometry, "Test")


class GptStreamTests(unittest.TestCase):
    class FakeResponse:
        def __init__(self, lines: list[str]) -> None:
            self.lines = lines

        def iter_lines(self, decode_unicode: bool = False) -> Any:
            del decode_unicode
            return iter(self.lines)

    def test_parses_image_edit_sse_events(self) -> None:
        response = self.FakeResponse(
            [
                "event: image_edit.partial_image",
                'data: {"type":"image_edit.partial_image","b64_json":"partial","partial_image_index":0}',
                "",
                "event: image_edit.completed",
                'data: {"type":"image_edit.completed","b64_json":"final"}',
                "",
            ]
        )

        events = list(render_guard.iter_gpt_stream_events(response))

        self.assertEqual(
            [event_type for event_type, _ in events],
            ["image_edit.partial_image", "image_edit.completed"],
        )
        self.assertEqual(events[0][1]["partial_image_index"], 0)

    def test_parses_non_streaming_json_fallback(self) -> None:
        response = self.FakeResponse(['{"data":[{"b64_json":"final"}]}'])

        events = list(render_guard.iter_gpt_stream_events(response))

        self.assertEqual(events, [("", {"data": [{"b64_json": "final"}]})])

    def test_uses_sse_event_name_when_payload_has_no_type(self) -> None:
        response = self.FakeResponse(
            [
                "event: image_edit.completed",
                'data: {"b64_json":"final"}',
                "",
            ]
        )

        events = list(render_guard.iter_gpt_stream_events(response))

        self.assertEqual(events[0][0], "image_edit.completed")


if __name__ == "__main__":
    unittest.main()
