#!/usr/bin/env python3
"""Call GPT and Gemini image-to-image endpoints for guarded architecture renders."""

from __future__ import annotations

import argparse
import base64
import json
import math
import mimetypes
import os
import socket
import sys
import time
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

warnings.filterwarnings("ignore", category=Warning, module="requests")
import requests
from PIL import Image, ImageOps
from urllib3.util import connection as urllib3_connection


DEFAULT_BASE_URL = "https://api.iiiiitoken.com"
DEFAULT_GPT_BASE_URL = "https://ynk-yyds.cc.cd"
DEFAULT_GPT_MODEL = "gpt-image-2"
DEFAULT_GEMINI_MODEL = "gemini-3-pro-image"
PROVIDER_KEY_ENV_NAMES = {
    "gpt": ("ARCH_RENDER_GUARD_GPT_API_KEY",),
    "gemini": ("ARCH_RENDER_GUARD_GEMINI_API_KEY",),
}
DEFAULT_PREVIEW_MAX_EDGE = 960
DEFAULT_PREVIEW_QUALITY = 72
DEFAULT_RESOLUTION = "2K"
DEFAULT_GPT_PARTIAL_IMAGES = 2
SUPPORTED_ASPECT_RATIOS = (
    "1:1",
    "2:3",
    "3:2",
    "3:4",
    "4:3",
    "4:5",
    "5:4",
    "9:16",
    "16:9",
    "21:9",
)
# Gemini 3 Pro Image official output dimensions. The same 1K/2K sizes
# satisfy the documented gpt-image-2 arbitrary-size constraints.
OFFICIAL_OUTPUT_DIMENSIONS = {
    "1K": {
        "1:1": (1024, 1024),
        "2:3": (848, 1264),
        "3:2": (1264, 848),
        "3:4": (896, 1200),
        "4:3": (1200, 896),
        "4:5": (928, 1152),
        "5:4": (1152, 928),
        "9:16": (768, 1376),
        "16:9": (1376, 768),
        "21:9": (1584, 672),
    },
    "2K": {
        "1:1": (2048, 2048),
        "2:3": (1696, 2528),
        "3:2": (2528, 1696),
        "3:4": (1792, 2400),
        "4:3": (2400, 1792),
        "4:5": (1856, 2304),
        "5:4": (2304, 1856),
        "9:16": (1536, 2752),
        "16:9": (2752, 1536),
        "21:9": (3168, 1344),
    },
}
GPT_MAX_EDGE = 3840
GPT_MAX_ASPECT_RATIO = 3.0
GPT_MIN_PIXELS = 655_360
GPT_MAX_PIXELS = 8_294_400


@dataclass(frozen=True)
class OutputGeometry:
    source_width: int
    source_height: int
    aspect_ratio: str
    resolution: str
    gpt_size: str
    selection_reason: str


def force_ipv4() -> None:
    """Restrict urllib3 DNS resolution to IPv4 addresses for every request."""
    urllib3_connection.allowed_gai_family = lambda: socket.AF_INET


def die(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def codex_home() -> Path:
    env_home = os.environ.get("CODEX_HOME")
    if env_home:
        return Path(env_home)
    windows_home = Path("D:/CodexHome")
    if windows_home.exists():
        return windows_home
    return Path.home() / ".codex"


def key_file_path(provider: str) -> Path:
    return codex_home() / "architectural-render-guard" / f"{provider}_api_key.txt"


def read_file_key(provider: str) -> str:
    path = key_file_path(provider)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def read_env_key(provider: str) -> str:
    for name in PROVIDER_KEY_ENV_NAMES[provider]:
        value = os.environ.get(name)
        if value:
            return value.strip()
    return ""


def read_key(provider: str) -> str:
    key = read_file_key(provider) or read_env_key(provider)
    if not key:
        die(
            f"Missing {provider} API key. Save one to {key_file_path(provider)} with "
            f"--save-{provider}-key-stdin, or set one of: "
            f"{', '.join(PROVIDER_KEY_ENV_NAMES[provider])}."
        )
    return key


def has_key(provider: str) -> bool:
    return bool(read_file_key(provider) or read_env_key(provider))


def key_source(provider: str) -> str:
    if read_file_key(provider):
        return f"local file: {key_file_path(provider)}"
    if read_env_key(provider):
        return "environment variable"
    return ""


def save_key_from_stdin(provider: str) -> Path:
    key = sys.stdin.read().strip()
    if not key:
        die("No API key was provided on stdin.")
    path = key_file_path(provider)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(key + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def mime_type(path: Path) -> str:
    guessed = mimetypes.guess_type(str(path))[0]
    return guessed or "image/png"


def image_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def image_dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source)
        return image.size


def aspect_ratio_value(aspect_ratio: str) -> float:
    width, height = (int(part) for part in aspect_ratio.split(":", maxsplit=1))
    return width / height


def nearest_aspect_ratio(width: int, height: int) -> str:
    if width <= 0 or height <= 0:
        raise ValueError("Image dimensions must be positive.")
    source_ratio = width / height
    return min(
        SUPPORTED_ASPECT_RATIOS,
        key=lambda candidate: abs(math.log(source_ratio / aspect_ratio_value(candidate))),
    )


def parse_pixel_size(value: str | None) -> tuple[int, int] | None:
    if value is None or value.lower() == "auto":
        return None
    parts = value.lower().split("x")
    if len(parts) != 2:
        raise ValueError("--size must use WIDTHxHEIGHT, for example 2528x1696.")
    try:
        width, height = (int(part) for part in parts)
    except ValueError as exc:
        raise ValueError("--size width and height must be integers.") from exc
    if width <= 0 or height <= 0:
        raise ValueError("--size width and height must be positive.")
    return width, height


def validate_gpt_size(width: int, height: int) -> None:
    if width > GPT_MAX_EDGE or height > GPT_MAX_EDGE:
        raise ValueError(f"GPT image edges must not exceed {GPT_MAX_EDGE}px.")
    if width % 16 or height % 16:
        raise ValueError("GPT image width and height must both be multiples of 16px.")
    long_edge, short_edge = max(width, height), min(width, height)
    if long_edge / short_edge > GPT_MAX_ASPECT_RATIO:
        raise ValueError("GPT image long-edge to short-edge ratio must not exceed 3:1.")
    pixels = width * height
    if not GPT_MIN_PIXELS <= pixels <= GPT_MAX_PIXELS:
        raise ValueError(
            f"GPT image total pixels must be between {GPT_MIN_PIXELS:,} and {GPT_MAX_PIXELS:,}."
        )


def resolve_output_geometry(args: argparse.Namespace) -> OutputGeometry:
    source_width, source_height = image_dimensions(args.image[0])
    legacy_size = parse_pixel_size(args.size)

    if args.aspect_ratio != "auto":
        aspect_ratio = args.aspect_ratio
        selection_reason = "explicit --aspect-ratio"
        if legacy_size and nearest_aspect_ratio(*legacy_size) != aspect_ratio:
            raise ValueError("--size and --aspect-ratio describe different output proportions.")
    elif legacy_size:
        aspect_ratio = nearest_aspect_ratio(*legacy_size)
        selection_reason = f"nearest official ratio to explicit --size {legacy_size[0]}x{legacy_size[1]}"
    else:
        aspect_ratio = nearest_aspect_ratio(source_width, source_height)
        selection_reason = (
            f"nearest official ratio to primary image {source_width}x{source_height}"
        )

    if legacy_size:
        gpt_width, gpt_height = legacy_size
    else:
        gpt_width, gpt_height = OFFICIAL_OUTPUT_DIMENSIONS[args.resolution][aspect_ratio]
    validate_gpt_size(gpt_width, gpt_height)

    return OutputGeometry(
        source_width=source_width,
        source_height=source_height,
        aspect_ratio=aspect_ratio,
        resolution=args.resolution,
        gpt_size=f"{gpt_width}x{gpt_height}",
        selection_reason=selection_reason,
    )


def gemini_generation_config(geometry: OutputGeometry) -> dict[str, Any]:
    return gemini_generation_config_for_mode(geometry, "response-format")


def gemini_generation_config_for_mode(
    geometry: OutputGeometry,
    mode: str,
) -> dict[str, Any]:
    image_config = {
        "aspectRatio": geometry.aspect_ratio,
        "imageSize": geometry.resolution,
    }
    config: dict[str, Any] = {"responseModalities": ["IMAGE", "TEXT"]}
    if mode == "response-format":
        config["responseFormat"] = {"image": image_config}
    elif mode == "image-config":
        config["imageConfig"] = image_config
    else:
        raise ValueError(f"Unknown Gemini geometry mode: {mode}")
    return config


def resolve_gemini_geometry_mode(base_url: str, requested_mode: str) -> str:
    if requested_mode != "auto":
        return requested_mode
    hostname = (urlparse(base_url).hostname or "").lower()
    if hostname == "generativelanguage.googleapis.com" or hostname.endswith(".googleapis.com"):
        return "response-format"
    return "image-config"


def validate_generated_aspect_ratio(
    path: Path,
    geometry: OutputGeometry,
    provider: str,
) -> tuple[int, int]:
    width, height = image_dimensions(path)
    actual_ratio = width / height
    expected_ratio = aspect_ratio_value(geometry.aspect_ratio)
    if abs(math.log(actual_ratio / expected_ratio)) > 0.03:
        raise ValueError(
            f"{provider} returned {width}x{height} ({actual_ratio:.4f}) instead of "
            f"the requested {geometry.aspect_ratio} aspect ratio."
        )
    return width, height


def create_preview(path: Path, out_dir: Path, max_edge: int, quality: int) -> Path:
    preview_dir = out_dir / "_previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    preview_path = preview_dir / f"{path.stem}_preview.jpg"

    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source)
        image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)

        if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
            rgba = image.convert("RGBA")
            background = Image.new("RGBA", rgba.size, "white")
            image = Image.alpha_composite(background, rgba).convert("RGB")
        else:
            image = image.convert("RGB")

        image.save(preview_path, "JPEG", quality=quality, optimize=True)

    return preview_path


def strict_prompt(args: argparse.Namespace, geometry: OutputGeometry) -> str:
    image_note = (
        "Use image 1 as the primary edit target. Use the other images only as references for style, material, "
        "environment, facade details, or requested composition. Produce one final image."
        if len(args.image) > 1
        else "Use the input image as the edit target. Produce one final image."
    )
    parts = [
        "Architectural image-to-image render with strict preservation.",
        image_note,
        "",
        "Locked building subject:",
        args.locked_subject.strip(),
        "",
        "Requested style / allowed changes:",
        args.style.strip(),
    ]
    if args.edit_area:
        parts += ["", "Edit area:", args.edit_area.strip()]
    if args.keep_text:
        parts += ["", f'Preserve visible wall text/signage verbatim: "{args.keep_text.strip()}".']
    if args.extra:
        parts += ["", "Additional user requirements:", args.extra.strip()]
    parts += [
        "",
        "Output geometry:",
        f"- Aspect ratio: {geometry.aspect_ratio}.",
        f"- Resolution class: {geometry.resolution}.",
        f"- Preserve or adapt the composition intentionally for this {geometry.aspect_ratio} canvas.",
        "",
        "Hard constraints:",
        "- Do not change the building massing, footprint, floor count, roofline, camera perspective, or facade proportions.",
        "- Do not add, delete, move, or resize doors or windows.",
        "- Do not change stairs, ramps, platforms, railings, columns, canopy, balconies, terraces, entrances, or signage unless explicitly requested.",
        "- Only change material, lighting, environment, landscaping, pavement, sky, or the specified local edit area.",
        "",
        "Avoid:",
        args.avoid
        or "different building, extra floors, extra windows, missing windows, changed entrance, changed sign text, new signboards, cartoon style, distorted perspective",
    ]
    return "\n".join(parts)


def parse_image_from_openai_style(payload: dict[str, Any], session: requests.Session, timeout: int) -> bytes:
    data = payload.get("data") or []
    if not data:
        raise ValueError("no data[] in image response")
    item = data[0]
    b64 = item.get("b64_json") or item.get("image")
    if b64:
        return base64.b64decode(b64)
    url = item.get("url")
    if url:
        r = session.get(url, timeout=timeout)
        r.raise_for_status()
        return r.content
    raise ValueError("no b64_json/image/url in image response")


def image_bytes_from_gpt_payload(
    payload: dict[str, Any],
    session: requests.Session,
    timeout: int,
) -> bytes:
    b64 = payload.get("b64_json") or payload.get("image")
    if isinstance(b64, str):
        return base64.b64decode(b64)
    return parse_image_from_openai_style(payload, session, timeout)


def iter_gpt_stream_events(
    response: requests.Response,
) -> Any:
    """Yield (event type, JSON payload) from SSE or a normal JSON response."""
    event_name = ""
    data_lines: list[str] = []
    raw_lines: list[str] = []
    saw_sse = False
    yielded_event = False

    def flush_event() -> tuple[str, dict[str, Any]] | None:
        nonlocal event_name, data_lines
        if not data_lines:
            event_name = ""
            return None
        current_event_name = event_name
        raw_data = "\n".join(data_lines).strip()
        event_name, data_lines = "", []
        if not raw_data or raw_data == "[DONE]":
            return None
        payload = json.loads(raw_data)
        if not isinstance(payload, dict):
            raise ValueError("GPT stream event data must be a JSON object")
        return str(payload.get("type") or current_event_name or ""), payload

    for raw_line in response.iter_lines(decode_unicode=True):
        line = raw_line.decode("utf-8", errors="replace") if isinstance(raw_line, bytes) else raw_line
        raw_lines.append(line)
        if not line.strip():
            event = flush_event()
            if event:
                yielded_event = True
                yield event
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line.split(":", 1)[1].strip()
            saw_sse = True
            continue
        if line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].lstrip())
            saw_sse = True
            continue
        if data_lines or event_name:
            data_lines.append(line)
            saw_sse = True

    event = flush_event()
    if event:
        yielded_event = True
        yield event

    if not yielded_event and not saw_sse:
        raw_data = "\n".join(raw_lines).strip()
        if raw_data:
            payload = json.loads(raw_data)
            if not isinstance(payload, dict):
                raise ValueError("GPT response must be a JSON object")
            yield str(payload.get("type") or ""), payload


def find_b64_images(obj: Any) -> list[str]:
    found: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            norm = key.replace("_", "").lower()
            if norm in {"inlinedata", "inlineimage"} and isinstance(value, dict):
                data = value.get("data")
                if isinstance(data, str):
                    found.append(data)
            elif norm in {"b64json", "image"} and isinstance(value, str) and len(value) > 100:
                found.append(value)
            else:
                found.extend(find_b64_images(value))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(find_b64_images(item))
    return found


def call_gpt(
    args: argparse.Namespace,
    session: requests.Session,
    key: str,
    prompt: str,
    geometry: OutputGeometry,
) -> tuple[Path, dict[str, Any]]:
    url = f"{args.gpt_base_url.rstrip('/')}/v1/images/edits"
    files: list[tuple[str, Any]] = []
    # OpenAI-compatible image edits expect arrays as image[] in multipart form data.
    image_field = "image[]" if len(args.image) > 1 else "image"
    for image_path in args.image:
        files.append((image_field, (image_path.name, image_path.open("rb"), mime_type(image_path))))
    if args.mask:
        files.append(("mask", (args.mask.name, args.mask.open("rb"), mime_type(args.mask))))
    data = {
        "model": args.gpt_model,
        "prompt": prompt,
        "size": geometry.gpt_size,
        "quality": args.quality,
        "stream": "true",
        "partial_images": str(args.gpt_partial_images),
    }
    stream_info: dict[str, Any] = {
        "requested": True,
        "partial_images_requested": args.gpt_partial_images,
        "events": [],
        "partial_images_received": 0,
        "response_mode": "",
        "partial_previews": [],
    }
    r: requests.Response | None = None
    try:
        r = session.post(
            url,
            headers={
                "Authorization": f"Bearer {key}",
                "Accept": "text/event-stream, application/json",
            },
            files=files,
            data=data,
            stream=True,
            timeout=(30, args.timeout),
        )
        r.raise_for_status()
        content: bytes | None = None
        response_mode = "sse"
        for event_type, payload in iter_gpt_stream_events(r):
            stream_info["events"].append(event_type or "json")
            if event_type == "image_edit.partial_image":
                b64 = payload.get("b64_json") or payload.get("image")
                if isinstance(b64, str):
                    partial_index = payload.get(
                        "partial_image_index",
                        stream_info["partial_images_received"],
                    )
                    partial_path = (
                        args.out_dir
                        / "_previews"
                        / f"{args.prefix}_gpt_partial_{partial_index}_attempt{args.attempt}.png"
                    )
                    partial_path.parent.mkdir(parents=True, exist_ok=True)
                    partial_path.write_bytes(base64.b64decode(b64))
                    stream_info["partial_previews"].append(str(partial_path))
                    stream_info["partial_images_received"] += 1
            elif event_type == "image_edit.completed":
                content = image_bytes_from_gpt_payload(payload, session, args.timeout)
            elif payload.get("data"):
                response_mode = "json"
                content = image_bytes_from_gpt_payload(payload, session, args.timeout)
        stream_info["response_mode"] = response_mode
        if content is None:
            raise ValueError(
                "GPT stream ended without image_edit.completed or a standard image response"
            )
    finally:
        if r is not None:
            r.close()
        for _, file_tuple in files:
            file_tuple[1].close()
    out = args.out_dir / f"{args.prefix}_gpt_{args.gpt_model}_attempt{args.attempt}.png"
    out.write_bytes(content)
    return out, stream_info


def call_gemini(
    args: argparse.Namespace,
    session: requests.Session,
    key: str,
    prompt: str,
    geometry: OutputGeometry,
    geometry_mode: str,
) -> Path:
    url = f"{args.base_url.rstrip('/')}/v1beta/models/{args.gemini_model}:generateContent"
    parts: list[dict[str, Any]] = [
        {
            "text": prompt
            + "\n\nImage 1 is the primary edit target. Images 2+ are reference images only. If a mask image is provided, treat white/bright mask areas as editable and preserve everything else."
        },
    ]
    for index, image_path in enumerate(args.image, start=1):
        parts.append({"text": f"Image {index}: {'primary edit target' if index == 1 else 'reference image'}."})
        parts.append(
            {
                "inlineData": {
                    "mimeType": mime_type(image_path),
                    "data": image_b64(image_path),
                }
            }
        )
    if args.mask:
        parts.append(
            {
                "inlineData": {
                    "mimeType": mime_type(args.mask),
                    "data": image_b64(args.mask),
                }
            }
        )
    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": gemini_generation_config_for_mode(geometry, geometry_mode),
    }
    r = session.post(
        url,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=args.timeout,
    )
    r.raise_for_status()
    payload = r.json()
    images = find_b64_images(payload)
    if not images:
        debug = args.out_dir / f"{args.prefix}_gemini_no_image_attempt{args.attempt}.json"
        debug.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        raise ValueError(f"Gemini response did not contain an image. Saved response: {debug}")
    out = args.out_dir / f"{args.prefix}_gemini_{args.gemini_model}_attempt{args.attempt}.png"
    out.write_bytes(base64.b64decode(images[0]))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate guarded architectural renders with GPT and Gemini.")
    parser.add_argument("--check-key", action="store_true", help="Only check whether API keys are configured.")
    parser.add_argument("--save-key-stdin", action="store_true", help="Legacy alias that saves a GPT API key from stdin.")
    parser.add_argument("--save-gpt-key-stdin", action="store_true", help="Read a GPT API key from stdin and save it under the local Codex directory.")
    parser.add_argument("--save-gemini-key-stdin", action="store_true", help="Read a Gemini API key from stdin and save it under the local Codex directory.")
    parser.add_argument("--key-file", choices=["gpt", "gemini"], nargs="?", const="gpt", help="Print the local key file path for one provider.")
    parser.add_argument("--image", type=Path, nargs="+", help="Input image(s). First image is the primary edit target; additional images are references.")
    parser.add_argument("--preview-only", action="store_true", help="Create lightweight inspection previews for --image paths without calling a model.")
    parser.add_argument("--no-preview", action="store_true", help="Do not create lightweight inspection previews for generated outputs.")
    parser.add_argument("--preview-max-edge", type=int, default=DEFAULT_PREVIEW_MAX_EDGE, help="Maximum width or height of generated inspection previews.")
    parser.add_argument("--preview-quality", type=int, default=DEFAULT_PREVIEW_QUALITY, help="JPEG quality for generated inspection previews.")
    parser.add_argument("--mask", type=Path, help="Optional edit mask image.")
    parser.add_argument("--locked-subject", help="Building body and details that must not change.")
    parser.add_argument("--style", help="Requested render style/material/light/environment.")
    parser.add_argument("--edit-area", default="", help="Specific area to edit.")
    parser.add_argument("--keep-text", default="", help="Exact sign/wall text to preserve.")
    parser.add_argument("--extra", default="", help="Additional user requirements.")
    parser.add_argument("--avoid", default="", help="Negative constraints.")
    parser.add_argument("--out-dir", type=Path, default=Path("outputs/architectural-render-guard"))
    parser.add_argument("--prefix", default="render_guard")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--gpt-base-url", default=DEFAULT_GPT_BASE_URL)
    parser.add_argument("--gpt-model", default=DEFAULT_GPT_MODEL)
    parser.add_argument("--gemini-model", default=DEFAULT_GEMINI_MODEL)
    parser.add_argument(
        "--gemini-geometry-mode",
        choices=("auto", "response-format", "image-config"),
        default="auto",
        help=(
            "Gemini geometry payload mode. Auto uses official REST responseFormat for Google "
            "endpoints and imageConfig compatibility for third-party gateways."
        ),
    )
    parser.add_argument("--models", choices=["both", "gpt", "gemini"], default="both")
    parser.add_argument(
        "--aspect-ratio",
        choices=("auto", *SUPPORTED_ASPECT_RATIOS),
        default="auto",
        help="Output aspect ratio. Auto selects the nearest official ratio to the primary image.",
    )
    parser.add_argument(
        "--resolution",
        choices=tuple(OFFICIAL_OUTPUT_DIMENSIONS),
        default=DEFAULT_RESOLUTION,
        help="Output resolution class for both providers. Defaults to 2K.",
    )
    parser.add_argument(
        "--size",
        default=None,
        help="Legacy GPT pixel-size override. Gemini still uses --aspect-ratio and --resolution.",
    )
    parser.add_argument("--quality", choices=["low", "medium", "high", "auto"], default="low")
    parser.add_argument(
        "--gpt-partial-images",
        type=int,
        choices=range(0, 4),
        default=DEFAULT_GPT_PARTIAL_IMAGES,
        help="Number of GPT streaming partial images to request (0-3).",
    )
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--attempt", type=int, default=1)
    args = parser.parse_args()

    if args.key_file:
        print(key_file_path(args.key_file))
        return 0

    if args.save_key_stdin or args.save_gpt_key_stdin or args.save_gemini_key_stdin:
        provider = "gemini" if args.save_gemini_key_stdin else "gpt"
        path = save_key_from_stdin(provider)
        print(f"{provider.title()} API key saved to local Codex key file: {path}")
        return 0

    if args.check_key:
        missing = [provider for provider in ("gpt", "gemini") if not has_key(provider)]
        if missing:
            die(f"Missing API key(s): {', '.join(missing)}.", code=3)
        print(f"GPT API key found in {key_source('gpt')}.")
        print(f"Gemini API key found in {key_source('gemini')}.")
        return 0

    if not args.image:
        die("Missing --image for generation.")
    for image_path in args.image:
        if not image_path.exists():
            die(f"Input image does not exist: {image_path}")
    if args.preview_max_edge < 128:
        die("--preview-max-edge must be at least 128.")
    if not 20 <= args.preview_quality <= 95:
        die("--preview-quality must be between 20 and 95.")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    try:
        geometry = resolve_output_geometry(args)
    except ValueError as exc:
        die(str(exc))
    gemini_geometry_mode = resolve_gemini_geometry_mode(
        args.base_url,
        args.gemini_geometry_mode,
    )

    if args.preview_only:
        previews = {
            str(path): str(create_preview(path, args.out_dir, args.preview_max_edge, args.preview_quality))
            for path in args.image
        }
        print(
            json.dumps(
                {
                    "previews": previews,
                    "output_geometry": asdict(geometry),
                    "gemini_geometry_mode": gemini_geometry_mode,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if not args.locked_subject:
        die("Missing --locked-subject for generation.")
    if not args.style:
        die("Missing --style for generation.")
    if args.mask and not args.mask.exists():
        die(f"Mask image does not exist: {args.mask}")

    gpt_key = read_key("gpt") if args.models in {"both", "gpt"} else ""
    gemini_key = read_key("gemini") if args.models in {"both", "gemini"} else ""
    prompt = strict_prompt(args, geometry)
    prompt_path = args.out_dir / f"{args.prefix}_attempt{args.attempt}_prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")

    force_ipv4()
    session = requests.Session()
    session.trust_env = False

    outputs: dict[str, str] = {}
    output_dimensions: dict[str, dict[str, int]] = {}
    errors: dict[str, str] = {}
    gpt_stream: dict[str, Any] = {
        "requested": args.models in {"both", "gpt"},
        "partial_images_requested": args.gpt_partial_images,
    }
    started = time.time()

    if args.models in {"both", "gpt"}:
        try:
            output_path, gpt_stream = call_gpt(args, session, gpt_key, prompt, geometry)
            width, height = validate_generated_aspect_ratio(output_path, geometry, "GPT")
            outputs["gpt"] = str(output_path)
            output_dimensions["gpt"] = {"width": width, "height": height}
        except Exception as exc:  # noqa: BLE001
            errors["gpt"] = str(exc)
    if args.models in {"both", "gemini"}:
        try:
            output_path = call_gemini(
                args,
                session,
                gemini_key,
                prompt,
                geometry,
                gemini_geometry_mode,
            )
            width, height = validate_generated_aspect_ratio(output_path, geometry, "Gemini")
            outputs["gemini"] = str(output_path)
            output_dimensions["gemini"] = {"width": width, "height": height}
        except Exception as exc:  # noqa: BLE001
            errors["gemini"] = str(exc)

    previews: dict[str, str] = {}
    if not args.no_preview:
        for provider, output_path in outputs.items():
            try:
                previews[provider] = str(
                    create_preview(
                        Path(output_path),
                        args.out_dir,
                        args.preview_max_edge,
                        args.preview_quality,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                errors[f"{provider}_preview"] = str(exc)

    manifest = {
        "input_images": [str(path) for path in args.image],
        "primary_image": str(args.image[0]),
        "mask": str(args.mask) if args.mask else None,
        "attempt": args.attempt,
        "models": args.models,
        "output_geometry": asdict(geometry),
        "output_dimensions": output_dimensions,
        "gemini_geometry_mode": gemini_geometry_mode,
        "gpt_stream": gpt_stream,
        "prompt_file": str(prompt_path),
        "outputs": outputs,
        "previews": previews,
        "errors": errors,
        "elapsed_seconds": round(time.time() - started, 1),
    }
    manifest_path = args.out_dir / f"{args.prefix}_attempt{args.attempt}_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))

    return 0 if outputs else 2


if __name__ == "__main__":
    raise SystemExit(main())
