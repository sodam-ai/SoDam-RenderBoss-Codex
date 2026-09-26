#!/usr/bin/env python3
"""Prepare and verify Codex built-in image generation jobs without API calls."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

from PIL import Image, ImageOps

RATIOS = ("1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9")
OUTPUT_DIMENSIONS = {
    "1K": {"1:1": (1024, 1024), "2:3": (848, 1264), "3:2": (1264, 848),
           "3:4": (896, 1200), "4:3": (1200, 896), "4:5": (928, 1152),
           "5:4": (1152, 928), "9:16": (768, 1376), "16:9": (1376, 768),
           "21:9": (1584, 672)},
    "2K": {"1:1": (2048, 2048), "2:3": (1696, 2528), "3:2": (2528, 1696),
           "3:4": (1792, 2400), "4:3": (2400, 1792), "4:5": (1856, 2304),
           "5:4": (2304, 1856), "9:16": (1536, 2752), "16:9": (2752, 1536),
           "21:9": (3168, 1344)},
}


def parse_pixel_size(value: str | None) -> tuple[int, int] | None:
    if value is None or value.lower() == "auto":
        return None
    parts = value.lower().split("x")
    if len(parts) != 2:
        raise ValueError("--size must use WIDTHxHEIGHT, for example 2528x1696")
    try:
        width, height = (int(part) for part in parts)
    except ValueError as exc:
        raise ValueError("--size width and height must be integers") from exc
    if width <= 0 or height <= 0:
        raise ValueError("--size width and height must be positive")
    return width, height


def validate_gpt_size(width: int, height: int) -> None:
    if width > 3840 or height > 3840:
        raise ValueError("GPT image edges must not exceed 3840px")
    if width % 16 or height % 16:
        raise ValueError("GPT image width and height must both be multiples of 16px")
    if max(width, height) / min(width, height) > 3:
        raise ValueError("GPT image long-edge to short-edge ratio must not exceed 3:1")
    if not 655360 <= width * height <= 8294400:
        raise ValueError("GPT image total pixels must be between 655,360 and 8,294,400")


def dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as source:
        return ImageOps.exif_transpose(source).size


def nearest_ratio(width: int, height: int) -> str:
    if width <= 0 or height <= 0:
        raise ValueError("Image dimensions must be positive")
    return min(RATIOS, key=lambda ratio: abs(math.log((width / height) / ratio_value(ratio))))


def ratio_value(ratio: str) -> float:
    width, height = (int(part) for part in ratio.split(":"))
    return width / height


def make_prompt(args: argparse.Namespace, ratio: str) -> str:
    if args.image:
        if not args.locked_subject or not (args.style or args.prompt):
            raise ValueError("Editing requires --locked-subject and --style or --prompt")
        parts = [
            "Use case: sketch-to-render or precise-object-edit.",
            "Edit image 1. Images 2+ are references for style, material, environment, facade details, or requested composition only.",
            f"Locked building subject: {args.locked_subject}",
            f"Requested style and allowed changes: {args.style or args.prompt}",
            "Preserve the building massing, footprint, floor count, roofline, camera view, facade proportions, door and window count, size, and position.",
            "Preserve stairs, ramps, platforms, railings, columns, canopy, balconies, terraces, entrances, and signage unless explicitly requested otherwise.",
            "Change only requested materials, lighting, landscape, pavement, sky, or the named edit area.",
        ]
        if args.mask:
            parts.append("An RGBA mask reference is supplied. Its transparent pixels are editable and its opaque pixels are protected. The local finalizer restores protected source pixels; inspect the edit boundary for seams.")
    else:
        if not (args.prompt or args.style):
            raise ValueError("Generation requires --prompt or --style")
        parts = [
            "Use case: photorealistic architectural visualization.",
            f"Requested image: {args.prompt or args.style}",
            "Keep doors, windows, stairs, ramps, platforms, signs, and entrance logic plausible and buildable. Avoid unreadable signage, distorted perspective, impossible joints, and unintended facade openings.",
        ]
        if args.locked_subject:
            parts.append(f"Subject constraints: {args.locked_subject}")
    for label, value in (
        ("Edit area", args.edit_area),
        ("Visible text or signage, verbatim", args.keep_text),
        ("Additional requirements", args.extra),
        ("Avoid", args.avoid),
    ):
        if value:
            parts.append(f"{label}: {value}")
    if not args.avoid:
        parts.append("Avoid: " + (
            "different building, extra floors, extra or missing windows, changed entrance, changed sign text, new signboards, cartoon style, distorted perspective"
            if args.image else
            "cartoon style, distorted perspective, impossible building geometry, illegible sign text, warped doors or windows"))
    parts.extend([
        f"Target composition: {ratio}. Preserve the primary image framing when editing.",
        f"Requested output resolution: {args.resolution} when supported by the built-in tool.",
        "Produce one photorealistic image.",
    ])
    if getattr(args, "size", None) and args.size.lower() != "auto":
        parts.append(f"Requested exact pixel size: {args.size}; this must be verified after generation.")
    return "\n".join(parts) + "\n"


def prepare(args: argparse.Namespace) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.prefix):
        raise ValueError("--prefix must contain only letters, digits, underscores, or hyphens")
    for path in [*args.image, *([args.mask] if args.mask else [])]:
        if not path.is_file():
            raise ValueError(f"Input image does not exist: {path}")
        dimensions(path)
    if args.mask and not args.image:
        raise ValueError("--mask requires --image")
    if args.mask:
        with Image.open(args.mask) as mask:
            if mask.mode != "RGBA":
                raise ValueError("--mask must be RGBA with transparent editable pixels")
            if mask.size != dimensions(args.image[0]):
                raise ValueError("--mask dimensions must match the primary image")
    size = parse_pixel_size(getattr(args, "size", None))
    if size:
        validate_gpt_size(*size)
    ratio = args.aspect_ratio
    if ratio != "auto":
        if size and nearest_ratio(*size) != ratio:
            raise ValueError("--size and --aspect-ratio describe different output proportions")
        selection_reason = "explicit --aspect-ratio"
    elif size:
        ratio = nearest_ratio(*size)
        selection_reason = f"nearest supported ratio to explicit --size {size[0]}x{size[1]}"
    elif args.image:
        source_size = dimensions(args.image[0])
        ratio = nearest_ratio(*source_size)
        selection_reason = f"nearest supported ratio to primary image {source_size[0]}x{source_size[1]}"
    else:
        ratio = "16:9"
        selection_reason = "default text-to-image landscape 2K 16:9"
    prompt = make_prompt(args, ratio)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    job_path = args.out_dir / f"{args.prefix}_job.json"
    if job_path.exists():
        raise ValueError(f"Job already exists: {job_path}; choose another --prefix")
    prompt_path = args.out_dir / f"{args.prefix}_prompt.txt"
    if prompt_path.exists():
        raise ValueError(f"Prompt already exists: {prompt_path}; choose another --prefix")
    job = {
        "mode": "edit" if args.image else "generation",
        "engine": "Codex built-in image_gen tool",
        "api_key_required": False,
        "images": [str(path.resolve()) for path in args.image],
        "mask_reference": str(args.mask.resolve()) if args.mask else None,
        "target_aspect_ratio": ratio,
        "requested_resolution": args.resolution,
        "requested_size": list(size) if size else None,
        "reference_size": list(OUTPUT_DIMENSIONS[args.resolution][ratio])
            if args.resolution in OUTPUT_DIMENSIONS else None,
        "geometry_selection_reason": selection_reason,
        "resolution_guaranteed": False,
        "prompt_file": str(prompt_path.resolve()),
        "review_status": "pending_generation",
    }
    prompt_path.write_text(prompt, encoding="utf-8")
    job_path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"job_file": str(job_path.resolve()), **job}


def verify(args: argparse.Namespace) -> dict:
    job = json.loads(args.job.read_text(encoding="utf-8"))
    if not args.output.is_file():
        raise ValueError(f"Output image does not exist: {args.output}")
    width, height = dimensions(args.output)
    target = job["target_aspect_ratio"]
    ratio_ok = abs(math.log((width / height) / ratio_value(target))) <= 0.03
    result = {
        "job_file": str(args.job.resolve()),
        "output": str(args.output.resolve()),
        "width": width,
        "height": height,
        "target_aspect_ratio": target,
        "aspect_ratio_pass": ratio_ok,
        "requested_resolution": job["requested_resolution"],
        "resolution_guaranteed": False,
        "semantic_review": "pending_visual_inspection",
    }
    result_path = args.job.with_name(
        args.job.stem.removesuffix("_job") + f"_{args.output.stem}_verification.json"
    )
    if result_path.exists():
        raise ValueError(f"Verification already exists: {result_path}; choose another output filename")
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--verify", action="store_true")
    parser.add_argument("--image", type=Path, nargs="*", default=[])
    parser.add_argument("--mask", type=Path)
    parser.add_argument("--prompt", default="")
    parser.add_argument("--locked-subject", default="")
    parser.add_argument("--style", default="")
    parser.add_argument("--edit-area", default="")
    parser.add_argument("--keep-text", default="")
    parser.add_argument("--extra", default="")
    parser.add_argument("--avoid", default="")
    parser.add_argument("--aspect-ratio", choices=("auto", *RATIOS), default="auto")
    parser.add_argument("--resolution", choices=("native", "1K", "2K"), default="2K")
    parser.add_argument("--out-dir", type=Path, default=Path("outputs/architectural-render-guard"))
    parser.add_argument("--prefix", default="render_guard")
    parser.add_argument("--job", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.prepare:
            result = prepare(args)
        else:
            if not args.job or not args.output:
                raise ValueError("--verify requires --job and --output")
            result = verify(args)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("aspect_ratio_pass", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
