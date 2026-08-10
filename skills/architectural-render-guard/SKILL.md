---
name: architectural-render-guard
description: Use this plugin skill for architectural text-to-image generation or image editing through the local Architectural Render Guard script. Trigger when the user wants GPT and Gemini to generate a building image, edit or restyle an uploaded building image, combine reference images into one architectural render, compare GPT and Gemini outputs, or preserve a building subject, massing, floor count, doors, windows, stairs, ramps, platforms, signs, and entrance positions.
---

# Architectural Render Guard

## Contract

Use the local script at:

`<plugin root>/scripts/render_guard.py`

The plugin supports two modes:

- No input image: text-to-image generation.
- One or more input images: image editing. Image 1 is the primary edit target; images 2+ are references unless the user says otherwise.

Run GPT and Gemini through the configured gateway, inspect lightweight previews, and show only one accepted full-resolution result unless the user asks for a comparison.

## First-Use Preflight

Before the first generation or edit in a task, run:

```powershell
python "<plugin root>/scripts/render_guard.py" --init --models both
```

This checks the plugin skill file, Python runtime packages, local config directory, and API key readiness. It automatically installs missing Python runtime packages (`requests`, `pillow`, `urllib3`) with `python -m pip install --user`.

If `--init` reports a missing skill file or missing runtime package after installation, stop and tell the user to reinstall or update the plugin from GitHub. Do not call model APIs until the preflight is clean.

## Key Handling

The default shared API key is stored at:

`$CODEX_HOME/architectural-render-guard/api_key.txt`

Provider-specific override files are also supported:

- `$CODEX_HOME/architectural-render-guard/gpt_api_key.txt`
- `$CODEX_HOME/architectural-render-guard/gemini_api_key.txt`

Environment variables are supported:

- shared: `ARCH_RENDER_GUARD_API_KEY`, `IIIII_TOKEN_API_KEY`
- GPT override: `ARCH_RENDER_GUARD_GPT_API_KEY`
- Gemini override: `ARCH_RENDER_GUARD_GEMINI_API_KEY`

If `CODEX_HOME` is not set, the script uses `D:/CodexHome` when it exists, otherwise `~/.codex`.

This is a hard preflight gate. If a required key is missing:

- Stop immediately.
- Ask the user to provide the iiiiitoken API key.
- Do not call GPT, Gemini, local image editing, local compositing, or fallback rendering.
- When the user provides the key, save it using stdin:

```powershell
$key | python "<plugin root>/scripts/render_guard.py" --save-key-stdin
```

Do not put the key in plugin files, source code, command-line arguments, logs, or final responses.

## Default API Settings

- GPT generation/edit base URL: `https://api.iiiiitoken.com`
- Gemini generation/edit base URL: `https://api.iiiiitoken.com`
- GPT image model: `gpt-image-2-x`
- Gemini image model: `gemini-3.1-flash-image`
- Default generation geometry: 2K landscape, `16:9`
- Default edit geometry: nearest supported official ratio to the uploaded primary image
- Network: direct IPv4 only; the script forces `AF_INET` DNS resolution and disables proxy environment variables.

## Supported Generation Formats

Before text-to-image generation, tell the user that the default is `2K` landscape `16:9`. If the user asks what formats are supported, or if no format was specified, use:

```powershell
python "<plugin root>/scripts/render_guard.py" --list-formats
```

The shared GPT/Gemini-safe generation formats are:

`1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`

Supported shared resolution classes:

`1K`, `2K`

`--list-formats` also prints the official Gemini `gemini-3.1-flash-image`
format table, including `512px`, `4K`, and the extreme `1:4`, `4:1`, `1:8`,
and `8:1` aspect ratios. In dual-provider mode, stay with the shared safe
subset unless the user explicitly chooses Gemini only.

Do not pass `--size` for normal operation. It remains a backward-compatible GPT pixel override.

## Required User Inputs

For text-to-image generation, require a clear `--prompt` or `--style`. If the user does not specify a format, use the default `--resolution 2K --aspect-ratio auto`, which becomes `16:9` landscape when no image is provided.

For image editing, require:

- input image path(s);
- the building subject that must not change;
- desired render style, material, lighting, environment, or edit instruction;
- edit area, if local editing is requested;
- exact wall text/signage that must remain unchanged;
- known constraints such as floor count, door/window counts, ramp/stair logic.

If the user already supplied enough information, proceed without asking. By default, image 1 is the primary edit target and images 2+ are references only.

## Generation Workflow

1. Run `--init --models both`. If a key is missing, ask for it and save it with `--save-key-stdin`, then rerun `--init`.
2. If no image is supplied, run text-to-image generation. Mention the default `2K` `16:9` landscape format and the supported shared aspect ratios.
3. If image(s) are supplied, inspect the input when possible. If a local image is not already visible, create previews with `--preview-only`.
4. For image editing, keep `--aspect-ratio auto` unless the user requests a different composition; the script will select the nearest supported ratio from the primary image.
5. Write a strict prompt with locked subject, allowed changes, reference-image roles, edit area, signage/text constraints, and avoid list.
6. Call `scripts/render_guard.py` with both models unless the user requests one provider.
7. Inspect only the generated files listed under `previews` in the manifest. Do not open full-resolution candidate files with `view_image`.
8. Accept the first output that satisfies the requirements.
9. If neither output satisfies the requirements, revise the prompt with one targeted correction and run another attempt.
10. Show only the accepted full-resolution image and its path. Do not show previews or rejected candidate paths unless the user explicitly asks.

## Script Usage

Text-to-image example:

```powershell
python "<plugin root>/scripts/render_guard.py" `
  --prompt "Photorealistic 2K landscape render of a calm modern community clinic, warm off-white facade, clear glass entrance, accessible ramp, trees and clean pavement" `
  --out-dir "C:/path/outputs"
```

Single-image edit example:

```powershell
python "<plugin root>/scripts/render_guard.py" `
  --image "C:/path/primary-building.png" `
  --locked-subject "two-story rehab building; keep massing, floor count, facade openings, entrance canopy, stairs, accessible ramp, and wall text unchanged" `
  --style "warm off-white modern facade, gray stone steps, clear glass, clean street foreground, realistic daylight" `
  --edit-area "only improve materials, light, and courtyard environment" `
  --out-dir "C:/path/outputs"
```

Multi-image edit example:

```powershell
python "<plugin root>/scripts/render_guard.py" `
  --image "C:/path/primary-building.png" "C:/path/material-reference.jpg" "C:/path/environment-reference.png" `
  --locked-subject "image 1 building body; keep massing, floor count, doors, windows, entrance, stairs, ramp, and signage unchanged" `
  --style "use image 2 for facade material style and image 3 for landscape atmosphere; generate one photorealistic render" `
  --out-dir "C:/path/outputs"
```

Preview-only example:

```powershell
python "<plugin root>/scripts/render_guard.py" `
  --preview-only `
  --image "C:/path/building.png" "C:/path/material-reference.jpg" `
  --out-dir "C:/path/outputs"
```

For local edits, provide `--mask` when available. The GPT endpoint uses the mask directly. Gemini receives the mask as an additional reference image plus text instructions.

## Inspection Rules

Reject an output if:

- the building becomes a different building;
- floor count, massing, roofline, entrance, canopy, stairs, ramp, or platform changes;
- doors/windows are added, deleted, moved, or resized;
- wall text/signage changes or new signs appear;
- the edit area violates building logic, such as a ramp not connected to the landing;
- the result changes season/environment when not requested.

Prefer small crop or mask reruns over full-image reruns for repeated failures near doors, windows, signs, ramps, stairs, or platforms.
