#!/usr/bin/env python3
"""Keyless architectural render workflow around Codex's built-in image tool.

The agent runs image_gen between --prepare and --finalize. This script never
contacts an image API, reads API keys, or invokes Gemini.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import subprocess
import sys
from pathlib import Path

if importlib.util.find_spec("PIL") is None:
    if "--init" in sys.argv and "--no-install" not in sys.argv:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "Pillow>=10,<13"])
    else:
        raise SystemExit("Pillow is missing. Run --init to install it, or install requirements.txt.")

from PIL import Image, ImageOps

try:
    from . import builtin_guard
except ImportError:
    import builtin_guard


PREVIEW_EDGE = 960
PREVIEW_QUALITY = 72


def preview(path: Path, out_dir: Path, name: str, edge: int, quality: int) -> Path:
    if edge < 128 or not 20 <= quality <= 95:
        raise ValueError("Preview edge must be >= 128 and JPEG quality must be 20..95")
    destination = out_dir / "_previews" / f"{name}_preview.jpg"
    if destination.exists():
        raise ValueError(f"Preview already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(path) as file:
        image = ImageOps.exif_transpose(file)
        image.thumbnail((edge, edge), Image.Resampling.LANCZOS)
        if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
            image = Image.alpha_composite(
                Image.new("RGBA", image.size, "white"), image.convert("RGBA")
            ).convert("RGB")
        else:
            image = image.convert("RGB")
        image.save(destination, "JPEG", quality=quality, optimize=True)
    return destination.resolve()


def validate_mask(mask: Path, primary: Path) -> None:
    with Image.open(mask) as file:
        if file.mode != "RGBA":
            raise ValueError("Mask must be RGBA: transparent pixels are editable")
        if file.size != builtin_guard.dimensions(primary):
            raise ValueError("Mask dimensions must match the primary image")


def prepare(args: argparse.Namespace) -> dict:
    if args.attempt < 1:
        raise ValueError("--attempt must be >= 1")
    if not args.no_preview and (args.preview_max_edge < 128 or not 20 <= args.preview_quality <= 95):
        raise ValueError("Preview edge must be >= 128 and JPEG quality must be 20..95")
    if args.mask:
        if not args.image:
            raise ValueError("--mask requires --image")
        validate_mask(args.mask, args.image[0])
        requested_size = builtin_guard.parse_pixel_size(args.size)
        if requested_size and requested_size != builtin_guard.dimensions(args.image[0]):
            raise ValueError("Masked local compositing keeps primary-image dimensions; --size must match the primary image")
    original_prefix = args.prefix
    if not args.no_preview:
        for index in range(1, len(args.image) + 1):
            path = (args.out_dir / "_previews" /
                    f"{original_prefix}_attempt{args.attempt}_input{index}_preview.jpg")
            if path.exists():
                raise ValueError(f"Preview already exists: {path}")
    args.prefix = f"{original_prefix}_attempt{args.attempt}"
    try:
        result = builtin_guard.prepare(args)
    finally:
        args.prefix = original_prefix
    job_path = Path(result["job_file"])
    job = json.loads(job_path.read_text(encoding="utf-8"))
    job["attempt"] = args.attempt
    job["input_previews"] = {}
    if not args.no_preview:
        for index, path in enumerate(args.image, 1):
            item = preview(path, args.out_dir, f"{original_prefix}_attempt{args.attempt}_input{index}",
                           args.preview_max_edge, args.preview_quality)
            job["input_previews"][f"image_{index}"] = str(item)
    job["tool_call"] = {
        "tool": "Codex built-in image_gen",
        "prompt_file": job["prompt_file"],
        "referenced_image_paths": job["images"] +
            ([job["mask_reference"]] if job["mask_reference"] else []),
        "transparent_background": False,
    }
    job_path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"job_file": str(job_path), **job}


def finalize(args: argparse.Namespace) -> dict:
    job = json.loads(args.job.read_text(encoding="utf-8"))
    if not isinstance(job, dict):
        raise TypeError("Job file must contain a JSON object")
    for field in ("mode", "images", "mask_reference", "target_aspect_ratio",
                  "requested_resolution", "prompt_file"):
        if field not in job:
            raise ValueError(f"Job file is missing required field: {field}")
    if job["mode"] not in ("generation", "edit"):
        raise ValueError("Job file has an invalid mode")
    if not isinstance(job["images"], list) or not all(
        isinstance(path, str) for path in job["images"]
    ):
        raise ValueError("Job file images must be a list of paths")
    if job["mode"] == "edit" and not job["images"]:
        raise ValueError("Edit job must include a primary image")
    if job["mask_reference"] is not None and (
        not isinstance(job["mask_reference"], str) or not job["images"]
    ):
        raise ValueError("Job file mask requires a primary image path")
    if job["target_aspect_ratio"] not in builtin_guard.RATIOS:
        raise ValueError("Job file has an invalid target aspect ratio")
    if job["requested_resolution"] not in ("native", "1K", "2K"):
        raise ValueError("Job file has an invalid requested resolution")
    if not isinstance(job["prompt_file"], str):
        raise TypeError("Job file prompt path must be a string")
    requested_size = job.get("requested_size")
    if requested_size is not None and (
        not isinstance(requested_size, list) or len(requested_size) != 2 or
        any(type(edge) is not int or edge <= 0 for edge in requested_size)
    ):
        raise ValueError("Job file requested size must contain two positive integers")
    for image_path in job["images"]:
        source = Path(image_path)
        if not source.is_file():
            raise ValueError(f"Input image does not exist: {source}")
        builtin_guard.dimensions(source)
    if not args.output.is_file():
        raise ValueError(f"Built-in image output does not exist: {args.output}")
    destination = args.job.with_name(args.job.stem.removesuffix("_job") + "_gpt.png")
    manifest_path = args.job.with_name(args.job.stem.removesuffix("_job") + "_manifest.json")
    if destination.exists() or manifest_path.exists():
        raise ValueError("Output or manifest already exists; use a new --attempt")
    preview_target = (destination.parent / "_previews" /
                      f"{destination.stem}_preview.jpg")
    if not args.no_preview and preview_target.exists():
        raise ValueError(f"Preview already exists: {preview_target}")
    with Image.open(args.output) as file:
        generated = ImageOps.exif_transpose(file).convert("RGBA")
    raw_size = generated.size
    mask_applied = False
    if job.get("mask_reference"):
        primary_path = Path(job["images"][0])
        mask_path = Path(job["mask_reference"])
        validate_mask(mask_path, primary_path)
        with Image.open(primary_path) as file:
            primary = ImageOps.exif_transpose(file).convert("RGBA")
        if abs(math.log((raw_size[0] / raw_size[1]) /
                        (primary.width / primary.height))) > 0.03:
            raise ValueError("Masked edit output aspect ratio differs from the primary image")
        with Image.open(mask_path) as file:
            alpha = file.getchannel("A")
        generated = generated.resize(primary.size, Image.Resampling.LANCZOS)
        generated = Image.composite(generated, primary, ImageOps.invert(alpha))
        mask_applied = True
    generated.save(destination, "PNG")
    width, height = generated.size
    ratio = job["target_aspect_ratio"]
    ratio_pass = abs(math.log((width / height) / builtin_guard.ratio_value(ratio))) <= 0.03
    size_pass = list(raw_size) == requested_size if requested_size else None
    result_preview = None
    preview_error = None
    if not args.no_preview:
        try:
            result_preview = preview(destination, destination.parent, destination.stem,
                                     args.preview_max_edge, args.preview_quality)
        except (ValueError, OSError) as exc:
            preview_error = str(exc)
    manifest = {
        "mode": job["mode"],
        "input_images": job["images"],
        "primary_image": job["images"][0] if job["images"] else None,
        "mask": job["mask_reference"],
        "attempt": job.get("attempt", 1),
        "engine": "Codex built-in image_gen",
        "api_key_required": False,
        "output_geometry": {"aspect_ratio": ratio,
                            "resolution_requested": job["requested_resolution"],
                            "resolution_guaranteed": False,
                            "requested_size": requested_size,
                            "reference_size": job.get("reference_size"),
                            "selection_reason": job.get("geometry_selection_reason")},
        "raw_output_dimensions": {"width": raw_size[0], "height": raw_size[1]},
        "output_dimensions": {"gpt": {"width": width, "height": height}},
        "aspect_ratio_pass": ratio_pass,
        "requested_size_pass": size_pass,
        "mask_applied_locally": mask_applied,
        "prompt_file": job["prompt_file"],
        "outputs": {"gpt": str(destination.resolve())},
        "previews": {"gpt": str(result_preview)} if result_preview else {},
        "errors": (["Output aspect ratio differs from target"] if not ratio_pass else []) +
                  (["Output pixel size differs from explicit --size"] if size_pass is False else []) +
                  ([f"Preview failed: {preview_error}"] if preview_error else []),
        "semantic_review": "pending_visual_inspection",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"manifest_file": str(manifest_path.resolve()), **manifest}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    for name in ("init", "list-formats", "preview-only", "prepare", "finalize"):
        actions.add_argument(f"--{name}", action="store_true")
    parser.add_argument("--image", type=Path, nargs="+", default=[])
    parser.add_argument("--mask", type=Path)
    parser.add_argument("--prompt", default="")
    parser.add_argument("--locked-subject", default="")
    parser.add_argument("--style", default="")
    parser.add_argument("--edit-area", default="")
    parser.add_argument("--keep-text", default="")
    parser.add_argument("--extra", default="")
    parser.add_argument("--avoid", default="")
    parser.add_argument("--aspect-ratio", choices=("auto", *builtin_guard.RATIOS), default="auto")
    parser.add_argument("--resolution", choices=("native", "1K", "2K"), default="2K")
    parser.add_argument("--size", default=None, help="Original GPT pixel-size override; checked after built-in generation, not guaranteed")
    parser.add_argument("--out-dir", type=Path, default=Path("outputs/architectural-render-guard"))
    parser.add_argument("--prefix", default="render_guard")
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--preview-max-edge", type=int, default=PREVIEW_EDGE)
    parser.add_argument("--preview-quality", type=int, default=PREVIEW_QUALITY)
    parser.add_argument("--no-preview", action="store_true")
    parser.add_argument("--job", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--no-install", action="store_true")
    args = parser.parse_args()
    try:
        if args.init:
            skill_present = (Path(__file__).resolve().parents[1] /
                             "skills/architectural-render-guard/SKILL.md").is_file()
            result = {"skill_file_exists": skill_present,
                      "pillow_available": True, "api_key_required": False,
                      "image_gen_check": "Agent must confirm built-in image_gen availability",
                      "ok": skill_present}
        elif args.list_formats:
            result = {"default": {"resolution_requested": "2K", "aspect_ratio": "16:9"},
                      "aspect_ratios": list(builtin_guard.RATIOS),
                      "resolutions_requested": ["1K", "2K"],
                      "original_gpt_reference_dimensions": {
                          level: {ratio: f"{width}x{height}"
                                  for ratio, (width, height) in sizes.items()}
                          for level, sizes in builtin_guard.OUTPUT_DIMENSIONS.items()},
                      "native_output_size_guaranteed": False}
        elif args.preview_only:
            if not args.image:
                raise ValueError("--preview-only requires --image")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.prefix):
                raise ValueError("--prefix must contain only letters, digits, underscores, or hyphens")
            if args.preview_max_edge < 128 or not 20 <= args.preview_quality <= 95:
                raise ValueError("Preview edge must be >= 128 and JPEG quality must be 20..95")
            size = builtin_guard.parse_pixel_size(args.size)
            if size:
                builtin_guard.validate_gpt_size(*size)
            for index, path in enumerate(args.image, 1):
                builtin_guard.dimensions(path)
                preview_path = (args.out_dir / "_previews" /
                                f"{args.prefix}_input{index}_preview.jpg")
                if preview_path.exists():
                    raise ValueError(f"Preview already exists: {preview_path}")
            source_size = builtin_guard.dimensions(args.image[0])
            ratio = (args.aspect_ratio if args.aspect_ratio != "auto" else
                     builtin_guard.nearest_ratio(*(size or source_size)))
            if size and args.aspect_ratio != "auto" and builtin_guard.nearest_ratio(*size) != ratio:
                raise ValueError("--size and --aspect-ratio describe different output proportions")
            result = {
                "previews": {str(path): str(preview(path, args.out_dir,
                    f"{args.prefix}_input{i}", args.preview_max_edge,
                    args.preview_quality)) for i, path in enumerate(args.image, 1)},
                "output_geometry": {
                    "source_width": source_size[0], "source_height": source_size[1],
                    "aspect_ratio": ratio, "resolution_requested": args.resolution,
                    "requested_size": list(size) if size else None,
                    "reference_size": list(builtin_guard.OUTPUT_DIMENSIONS[args.resolution][ratio])
                        if args.resolution in builtin_guard.OUTPUT_DIMENSIONS else None,
                    "native_output_size_guaranteed": False,
                },
            }
        elif args.prepare:
            result = prepare(args)
        else:
            if not args.job or not args.output:
                raise ValueError("--finalize requires --job and --output")
            result = finalize(args)
    except (ValueError, OSError, TypeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if (not result.get("errors") and result.get("aspect_ratio_pass", True) and
                 result.get("requested_size_pass") is not False and
                 result.get("ok", True)) else 2


if __name__ == "__main__":
    raise SystemExit(main())
