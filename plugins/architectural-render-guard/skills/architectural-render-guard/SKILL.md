---
name: architectural-render-guard
description: Generate or edit architectural renders with Codex built-in image generation and no API key or Gemini. Use for text-to-image, single or multiple reference images, architectural preservation, local RGBA masks, previews, and iterative review.
---

# Architectural Render Guard

Use `<plugin root>/scripts/render_guard.py` for preparation, local previews, masked compositing, and the final manifest. Call Codex's built-in `image_gen` tool between preparation and finalization. Do not invoke an external image API or Gemini.

## Inputs

- With no image, generate a new architectural visualization. Default target composition is 16:9 and requested resolution is 2K.
- With images, image 1 is the edit target. Images 2+ are references for style, materials, and environment only. Preserve the primary image's framing.
- Get the locked building description and desired change. Capture known floor, door, window, entrance, stair, ramp, platform, and sign details. Preserve exact visible text verbatim.
- A mask is an RGBA PNG with the same dimensions as image 1. Transparent pixels are editable; opaque pixels are protected. The finalizer restores protected pixels exactly at the primary image's resolution. Inspect boundaries for seams.

## Workflow

1. Run `python "<plugin root>/scripts/render_guard.py" --init` and `--list-formats` if formats are needed. Confirm that built-in `image_gen` is available in this Codex task. No API key check is required.
2. Inspect each local input with `view_image`. Image 1 is the primary edit target; images 2+ are references only. If the user asks for previews, run `--preview-only --image <paths>`. For editing, obtain the locked building description and requested change.
3. Run `--prepare` with `--prompt` or `--style`, optional `--image`, `--mask`, `--edit-area`, `--keep-text`, `--extra`, `--avoid`, `--aspect-ratio`, `--resolution`, `--size`, `--out-dir`, `--prefix`, and `--attempt`. Read the emitted job JSON and prompt file. The default request is 2K 16:9 for generation; edits choose the nearest supported ratio from image 1. `--size` preserves the original GPT override syntax but is a strict post-generation check, not a native tool setting.
4. Call built-in `image_gen` using the prompt file. For local images, pass the job's `tool_call.referenced_image_paths`; for conversation attachments without paths, use the smallest sufficient `num_last_images_to_include`. Never pass both mechanisms. For generation without images, omit both.
5. Run `--finalize --job <job.json> --output <path to built-in result>`; it copies the selected result, applies an RGBA mask locally if supplied, writes a lightweight preview, and writes a manifest with actual dimensions. Do not overwrite a previous attempt.
6. Check `aspect_ratio_pass` and, when `--size` was explicit, `requested_size_pass` against the raw built-in output; local mask resizing cannot make a native size mismatch pass. A size mismatch is a failed attempt even if the aspect ratio passes. Inspect the preview, then compare the final image with image 1. Reject changes to massing, footprint, floor count, roofline, camera, facade proportions, doors, windows, stairs, ramps, platforms, railings, columns, canopy, balconies, terraces, entrances, or signage unless requested. Check exact visible text, environment, edit area, and mask seams. A passing ratio check does not prove semantic preservation.
7. If rejected, increase `--attempt`, make one targeted correction, generate again, and compare. Accept the first result satisfying the request. Show only the accepted full image unless comparison was requested. Report its actual dimensions and any remaining unverified constraint.

## Limits

No user API key or Gemini is used. The built-in tool is an agent tool, not a Python library; the local CLI alone cannot generate an image. `--list-formats` reports the original GPT reference dimensions, which are not guaranteed native outputs from this tool. Exact native 1K/2K output, streaming partial previews, and semantic geometry preservation cannot be guaranteed through the built-in tool. Local mask compositing guarantees only protected pixels at the primary image's dimensions, not perfect generated alignment inside the editable area. Never present a requested setting as a measured result. If built-in `image_gen` is unavailable, report that this keyless plugin cannot generate in the current Codex task; do not fall back to an API.
