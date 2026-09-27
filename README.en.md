# SoDam-RenderBoss-Codex — Codex Built-in Image Edition

> Documentation date: 2026-09-27 · Plugin version: `0.2.0+codex.20260926162227` · Project-folder nickname: `SoDam-RenderBoss-Codex`

This plugin helps you create or edit architectural images with **Codex's built-in image generation tool**. It prepares instructions to preserve the building and records checks on the result. **You do not need a user API key or Gemini.** You do need to sign in to Codex and have access to its built-in image tool in the current task. Running the Python command alone does not generate an image.

**Repository:** The distribution target for this keyless edition is private [`sodam-ai/SoDam-RenderBoss-Codex`](https://github.com/sodam-ai/SoDam-RenderBoss-Codex). Only authorized users can download it. The [public upstream](https://github.com/m174460635/architectural-render-guard) is a different edition requiring API keys.

## Contents

1. [Features](#features)
2. [Prerequisites and downloads](#prerequisites)
3. [Installation](#installation)
4. [Quick start](#quick-start)
5. [Usage and commands](#usage)
6. [How it works, workflow, and architecture](#workflow)
7. [Files and documents](#files)
8. [Security and data flow](#security)
9. [Troubleshooting](#troubleshooting)
10. [FAQ](#faq)
11. [Update summary](#updates)
12. [Copyright, license, and commercial use](#legal)

<a id="features"></a>
## 1. Features

- **New images:** Describe the building and desired appearance; Codex calls its built-in tool to generate an image.
- **Edit an image:** The first image is the building to edit. Additional images are references for materials, color, or surroundings.
- **Preservation instructions:** The prompt calls out massing, floors, roofline, camera, door and window count and positions, entrance, stairs, ramp, rails, and signage.
- **Local partial edits:** A same-size RGBA PNG mask makes **transparent pixels editable** and restores opaque pixels from the original at the end. Inspect the seam by eye.
- **Review material:** Input and output previews, actual output dimensions, aspect-ratio checks, and errors are saved. A person must compare building details with the original.

**Limits:** The default `2K` is a request, not an output guarantee. The actual built-in-tool result is measured afterward. A live generation and edit on 2026-09-27 each produced `1672×941`. Exact pixels, perfect preservation of every building element, and streaming partial images are not guaranteed. You may upscale an approved result in another tool.

<a id="prerequisites"></a>
## 2. Prerequisites and downloads

| Item | Purpose | Where to get or check it |
| --- | --- | --- |
| Windows PC and file space | The commands below use Windows PowerShell. | Prepare a folder for images and results. |
| Codex account and sign-in | The built-in image tool runs through Codex, with no user API key. | Start at [OpenAI Codex](https://openai.com/codex/). Tool access depends on account and task environment. |
| Codex CLI | Runs the `codex plugin` installation commands; you can work in the desktop app afterward. | Follow the Windows path in the [official Codex CLI guide](https://learn.chatgpt.com/docs/codex/cli). |
| Python and pip | Run the local preparation and review scripts. | Install from [Python's official downloads](https://www.python.org/downloads/) and check the PATH option. |
| Pillow | Reads images and creates previews, masks, and PNG files. | Install with the `requirements.txt` command below. |
| Git (optional) | Downloads the private repository by command or sends developer changes. | Install [Git for Windows](https://git-scm.com/download/win). Ordinary users receiving an archive do not need it. |
| Input image | Needed only when editing an existing building. | Prepare a PNG/JPEG or other supported image you own or have permission to use. |

**Getting the keyless project:** Use this local folder or, after receiving private-repository access, run `git clone https://github.com/sodam-ai/SoDam-RenderBoss-Codex.git`. With access, you can also use Code → Download ZIP on the GitHub repository. Without access, ask the owner for a package/archive. Do not use public upstream as the keyless download. Check that `.codex-plugin/plugin.json` describes `Keyless` and `Codex built-in`; do not run installers from unknown sources.

PowerShell is Windows' command window. Open **PowerShell** from Start and paste each command below. Keep quotes around paths with spaces. The example `D:\...` is the current PC's folder; replace it with the real path on another PC.

<a id="installation"></a>
## 3. Installation

### 3-1. Check programs and install the Python dependency

```powershell
codex --version
python --version
python -m pip --version
Set-Location 'D:\AI_Dev_Work\2026y\26y_09m_28d_SoDam-RenderBoss-Codex'
python -m pip install -r requirements.txt
```

If `codex` or `python` is not found, finish installing it and open a fresh PowerShell window. This project's Python dependency is `Pillow>=10,<13`. Install it explicitly as shown instead of relying on `--init` to install it automatically. Installing Python and Pillow may need a download.

### 3-2. Build and install the marketplace from the current local source

```powershell
$marketplaceDir = Join-Path (Get-Location) ('outputs\keyless-marketplace-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
python scripts/build_local_marketplace.py --out-dir $marketplaceDir
codex plugin marketplace add $marketplaceDir
codex plugin add architectural-render-guard@architectural-render-guard-keyless-local
codex plugin list
```

The output folder name includes the current time to avoid an existing folder. If two runs in the same second collide, choose a different name and retry. Keep using the `$marketplaceDir` variable in the **same PowerShell window**. The builder prints the actual `marketplace_root` to register and refuses to overwrite an existing folder. Confirm that `architectural-render-guard@architectural-render-guard-keyless-local` appears as `installed, enabled`. Distinguish it from the public upstream entry. Open a **new Codex task** so the plugin skill loads. If you received the built package on another PC, skip the build command and pass the extracted marketplace root to `codex plugin marketplace add`.

### 3-3. Check local readiness

```powershell
python scripts/render_guard.py --init --no-install
python scripts/render_guard.py --list-formats
```

`--init` checks the local skill file and Pillow. It **does not test access to the built-in image tool**. Requesting a real image in a new Codex task checks that part. This plugin alone cannot generate an image without account access and connectivity.

### 3-4. Developer testing and private repository delivery

```powershell
python -m unittest discover -s tests -v
python -m ruff check scripts tests
python -m compileall -q scripts tests
python scripts/build_local_marketplace.py --out-dir outputs/release-check
git status --short
git push origin builtin-imagegen
```

Ruff is a developer lint tool. If missing, install it with `python -m pip install ruff`; ordinary users do not need it. If a test fails, fix it before delivery. Choose a new build folder if the destination exists. The developer pushes only a reviewed, committed working branch. Open a `builtin-imagegen` → `main` PR on GitHub, review changed files and tests, then merge it. **Do not push directly to `main` or run `scripts/publish.ps1` during normal use.** This project needs no user API-key environment variable. Codex handles sign-in.

The `codex plugin marketplace add` and `codex plugin add` syntax was checked against this PC's CLI `0.156.1` help and installation status. Check `codex plugin --help` if your version differs. This documented installation uses the CLI; a separate desktop-only installation path was not verified.

<a id="quick-start"></a>
## 4. Quick start for first-time users

1. Finish installation, sign in to Codex, and open a new task.
2. Attach the original building image to edit it. For a new building image, no attachment is needed.
3. Paste the following request and replace the parts in `[ ]`. For editing, list exactly what must remain: floors, windows, doors, stairs, ramp, and sign text.

> Use Architectural Render Guard to make this building image photorealistic. Keep [two floors, the existing number and positions of windows and doors, central entrance, front stairs, right ramp, and sign text] unchanged. Change only [natural materials and lighting on a clear day]. Use only Codex built-in image generation, with no API key or Gemini. Compare the result with the original and report its actual pixel dimensions and changes.

4. Compare the result side by side with the original. If a window, door, stair, ramp, or sign changed, identify the specific difference and request a new attempt. For a new image, describe the building type, floors, view, and materials.
5. Use only a reviewed result. Check actual file dimensions even if you requested `2K`.

Codex can follow the skill to prepare, generate, and review without you typing commands. The following commands are for manual review and advanced use.

<a id="usage"></a>
## 5. Running, using, and commanding the plugin

Run every example from the project root in PowerShell. `--out-dir` stores results under project `outputs/`, excluded from Git commits. Replace sample image paths with your own.

### Make a new building image

```powershell
python scripts/render_guard.py --prepare --prompt 'Two-floor neighborhood library, front view, clear entrance, stairs and access ramp, photorealistic daylight' --out-dir outputs/my-first-render --prefix library
```

This command **only prepares a job JSON and prompt**. Ask Codex to read the printed `prompt_file` and create one image with its built-in image tool. Find the actual path where that tool saved the image, then finalize it:

```powershell
python scripts/render_guard.py --finalize --job outputs/my-first-render/library_attempt1_job.json --output 'C:\path\to\codex-generated.png'
```

### Edit an existing building

```powershell
python scripts/render_guard.py --prepare --image 'C:\images\building.png' --locked-subject 'Two floors; keep all windows, doors, central entrance, front stairs, right ramp, and signage' --style 'Photorealistic bright daylight, stone and wood' --out-dir outputs/my-edit --prefix facade
```

The first `--image` is the edit target. Add reference files after it: `--image 'C:\images\building.png' 'C:\images\material.jpg'`. Tell Codex that **only the first is the original building** and the others are style references. Codex may directly use conversation attachments without local paths, but `--prepare --image` needs real local paths.

### Partial edits and retries

Add `--mask 'C:\images\mask.png'` if needed. It must be a **same-width, same-height RGBA PNG**: transparent areas may change and opaque areas keep original pixels. Inspect translucent areas and seams yourself. Use `--attempt 2`, then `--attempt 3`, for a new try without overwriting the first. Finalize with that attempt's own `*_job.json`.

### Main options

| Option | Meaning and caution |
| --- | --- |
| `--prepare` / `--finalize` | Prepare a job / finish the image saved by Codex. Select one action. |
| `--image PATH [PATH ...]` | One original plus optional references. Edits require `--locked-subject` and `--style` or `--prompt`. |
| `--prompt`, `--style`, `--locked-subject` | Describe what to create, allowed style changes, and building parts to keep. |
| `--edit-area`, `--keep-text`, `--extra`, `--avoid` | Edit area, exact text, other requirements, and unwanted changes. |
| `--mask PATH` | Same-size RGBA PNG mask for local partial edits. |
| `--aspect-ratio` | Default `auto`; see `--list-formats`. New images default to `16:9`; edits choose the nearest supported ratio to the original. |
| `--resolution` | Request `native`, `1K`, or `2K`. Default `2K`; actual size is not guaranteed. |
| `--size WIDTHxHEIGHT` | **Checks the raw result after generation** against an explicit size. It does not force the tool to produce that size. Mismatch is recorded as failure. |
| `--out-dir`, `--prefix`, `--attempt` | Result folder, filename prefix, attempt number. A prefix starts with a letter/digit and contains only letters/digits/`_`/`-`. |
| `--preview-only --image PATH` | Make input JPEG previews without generating an image. |
| `--preview-max-edge`, `--preview-quality`, `--no-preview` | Adjust or skip previews. |
| `--init --no-install`, `--list-formats` | Local readiness / supported ratios and reference sizes. |

The original GPT reference size in `--list-formats` (`2K 16:9` is `2752×1536`) is **not guaranteed output from the built-in tool**. `--size 2752x1536` reports failure if the actual result differs. Check `raw_output_dimensions`, `aspect_ratio_pass`, `requested_size_pass`, `errors`, and `semantic_review` in the manifest. `requested_size_pass: null` means no explicit `--size` was given.

<a id="workflow"></a>
## 6. How it works, workflow, and architecture

```text
User request + optional original, references, and mask
  → Codex skill: capture requested changes and protected building parts
  → render_guard.py --prepare: validate inputs; save prompt, job JSON, preview
  → Codex built-in image_gen: generate or edit image
  → render_guard.py --finalize: measure size; optional local mask composite; save PNG, preview, manifest
  → Codex/user: compare building form, windows, doors, stairs, ramp, and signage with original
  → Retry with a new attempt if needed
```

`scripts/builtin_guard.py` supports ratio selection, input-size checks, and prompt writing. `scripts/render_guard.py` is the user-facing command. The plugin has no web server, database, sign-in server, or Gemini connector. The Codex environment handles sign-in and image generation. Python does not automatically invoke the built-in tool; Codex must act between preparation and finalization.

There are two kinds of checks. **Automatic checks** cover file existence, mask format and size, output ratio, and explicit size. **Visual review** compares real building elements and lettering with the source. `aspect_ratio_pass: true` does not prove building preservation.

<a id="files"></a>
## 7. Files and documents

| Relative to project root | Purpose |
| --- | --- |
| `README.md` / `README.html` | Equivalent Korean Markdown / web page. |
| `README.en.md` / `README.en.html` | Equivalent English Markdown / web page. |
| `LICENSE` | Official Apache License, Version 2.0 text for new contributions. |
| `LICENSES/MIT-upstream.txt` / `NOTICE` | Preserved original MIT license and copyright / source attribution. |
| `requirements.txt` | Pillow dependency constraint. |
| `.codex-plugin/plugin.json` | Plugin name, version, and description. |
| `.agents/plugins/marketplace.json` | Configuration pointing to the private repository; GitHub access is required. |
| `skills/architectural-render-guard/SKILL.md` | Codex agent workflow instructions. |
| `scripts/render_guard.py` / `scripts/builtin_guard.py` | User CLI / supporting logic. |
| `scripts/build_local_marketplace.py` | Creates the local install package. |
| `scripts/publish.ps1` | Developer publication script; **do not run during normal installation.** Publish through a working branch and reviewed PR. |
| `tests/` | Automated tests. |
| `outputs/<job name>/` | Job JSON, prompt, PNG, manifest JSON, and JPEG files in `_previews/`. `outputs/` is Git-ignored. |

Open the HTML document in a browser to read it. **Opening HTML does not run the plugin or create images.** The local package builder includes the core plugin files, all four README documents, `LICENSE`, the original MIT notice, and `NOTICE`. Moving the project leaves old absolute paths in existing job JSON; create a new job with `--prepare` after a move.

<a id="security"></a>
## 8. Security and data flow

- The job JSON records **local paths** of inputs, references, and mask. Prompt, previews, final PNG, and manifest are saved under the chosen local `outputs/` directory. Personal details in folder names or images can therefore be exposed in those files.
- During generation, the built-in Codex tool receives the request and selected images. Review applicable [OpenAI Terms of Use](https://openai.com/policies/row-terms-of-use/), [Service Terms](https://openai.com/policies/service-terms/), and account settings for access, data handling, and limits. **No API key does not mean offline processing.**
- This repository's Python image path does not read an API key, call an external image API, or invoke Gemini. `python -m pip install -r requirements.txt` downloads a dependency, while developer-only `scripts/publish.ps1` performs separate GitHub publication actions.
- `.gitignore` excludes `.env`, `*.log`, and `outputs/`. **Images outside `outputs/` are not automatically excluded.** Ignore rules alone cannot prevent every secret leak; review files and image content, signs, people, and addresses before sharing or committing. Check upload permission and account data policies before using confidential client material.
- Existing named jobs and results are protected from overwrite. An empty `errors` array in the manifest is still not visual approval.

<a id="troubleshooting"></a>
## 9. Troubleshooting

| Symptom | Check and remedy |
| --- | --- |
| `codex` or `python` not found | Finish the official installation, open a new PowerShell window, then retry `codex --version` and `python --version`. |
| `Pillow is missing` / `No module named PIL` | Run `python -m pip install -r requirements.txt` in the project root. Use the same `python` to install and run. |
| Plugin missing or asks for an API key | Check `codex plugin list` for the selector ending `@architectural-render-guard-keyless-local`. Do not confuse it with the public entry; start a new Codex task. |
| Built-in image tool unavailable | Check Codex sign-in, tool access for this account/task, and connectivity. There is no API-key or Gemini fallback in this edition. |
| `Destination already exists` / `Job already exists` / `Preview already exists` | Use a new output directory, `--prefix`, or `--attempt`. Do not delete or overwrite the earlier result. |
| `Input image does not exist` or failure after moving folders | Verify the image path and run a fresh `--prepare`. Do not reuse a job JSON with old absolute paths. |
| Mask RGBA or dimension error | Save a transparent RGBA PNG at exactly the original width and height. |
| Result is `1672×941` after requesting `2752×1536` | The `2K` reference size is not guaranteed. Check actual pixels; upscale externally after review if needed. An explicit `--size` mismatch is a failed attempt. |
| Ratio/size check fails or `errors` is nonempty | Do not accept the attempt. Inspect output and manifest, then request a new `--attempt`. |
| Windows, doors, stairs, or text changed | Compare with the original, describe the specific error, and regenerate. Inspect mask seams. Automatic checks cannot guarantee semantic identity. |

When reporting an issue, inspect the error message and job JSON field names, but do not publish customer images, personal information, account details, or passwords in an issue or chat.

<a id="faq"></a>
## 10. FAQ

**Q. Does it really work without an API key?** Yes. This local edition uses Codex built-in image generation with no user API key or Gemini, and a live generation was verified. Codex sign-in and image-tool access are still required.

**Q. Is it entirely free and offline?** This is not guaranteed. No API key is a different question from account charges, usage limits, and internet access. Check current conditions for your account in Codex.

**Q. Where can I get this edition?** With access, download private `sodam-ai/SoDam-RenderBoss-Codex`. The public upstream is a different edition. Inspect the manifest description after installing the local marketplace.

**Q. Why does `--prepare` not create an image?** Python prepares the job. Codex's built-in tool generates the image; `--finalize` then makes the review files.

**Q. Does it guarantee 2K and every building detail?** No. 2K is a request and preservation depends on prompting and human comparison. Only opaque mask regions receive local pixel restoration.

**Q. Can I run it directly on a phone?** The installation, Python, and PowerShell steps here target a Windows PC. Standalone mobile installation and screen behavior were not verified. Viewing the completed image on a phone is separate.

**Q. Can I use the image commercially?** The Apache/MIT permission for code differs from **rights in generated images, sources, and reference material**. Review input permission, trademarks, likeness consent, client contracts, and applicable OpenAI terms below.

<a id="updates"></a>
## 11. Update summary

<details>
<summary>Expand: What changed in the current local keyless edition</summary>
<div>
<p>The former external image API/Gemini route was replaced with a prepare → generate → finalize workflow using Codex built-in image generation. No user API key is required.</p>
<ul><li>Supports new-image creation, editing, multiple references, building-preservation instructions, RGBA mask compositing, input/output previews, and attempt-specific records.</li><li>Records actual size and ratio; an explicit pixel-size mismatch fails. Exact 2K pixels and semantic preservation from the built-in tool are not guaranteed.</li><li>Documents private delivery, Apache 2.0 for new contributions, preserved upstream MIT notice, local marketplace builder, and automated tests.</li></ul>
</div>
</details>

<a id="legal"></a>
## 12. Copyright, license, and commercial use

**Project code and documentation:** New contributions use the **Apache License, Version 2.0** with `Copyright 2026 SoDam AI Studio`. The original `architectural-render-guard` copyright, `Copyright (c) 2026 m174460635`, and **MIT License** are preserved in [`LICENSES/MIT-upstream.txt`](LICENSES/MIT-upstream.txt). [`LICENSE`](LICENSE) contains the Apache text; [`NOTICE`](NOTICE) explains provenance. On redistribution, keep the Apache text and original MIT notice, and mark modified files and their source. Both licenses contain warranty and liability limitations.

**In plain terms:** You may use the code and documentation for personal work, teaching, company work, forks, modification, redistribution, paid sale, service operation, and client delivery if you follow both licenses. Keep `LICENSE`, `LICENSES/MIT-upstream.txt`, and `NOTICE` with copies or modifications. Image and external-service rights are separate, as explained below.

**Installed dependency:** The sole Python dependency in `requirements.txt` is `Pillow>=10,<13`. Pillow uses its own [MIT-CMU license](https://github.com/python-pillow/Pillow/blob/main/LICENSE), separate from this project's Apache/MIT licenses. The locally checked version is 12.3.0. If you redistribute Pillow or a packaged executable/installer containing it, review and include the copyright and permission notices for that exact version and any bundled components. Do not use author names for promotion without permission. This document does not clear future versions within the allowed range or their binary components.

**Codex service and costs:** No user API key is needed for this plugin, but that does not promise free or unlimited access to the Codex image tool. Before use, check the current plan, usage limits, service terms, and image-generation policies that apply to your account. This repository does not pay for external API, model, or SDK access or grant a service entitlement.

**Rights to check separately:** The project's Apache/MIT licenses do not grant rights in your input/reference images, third-party architectural designs or drawings, trademarks, signs, people, generated output, Python/Pillow, or the Codex/OpenAI service. Verify that you may supply, edit, publish, and commercially use every input. The [OpenAI Terms of Use](https://openai.com/policies/row-terms-of-use/) discuss rights in output between you and OpenAI to the extent permitted by law, but **do not guarantee third-party clearance or uniqueness**. Check applicable [Service Terms](https://openai.com/policies/service-terms/) and policies for your location, account, and contract. Before client delivery, advertising, or sale, review sign text, trademarks, likeness permissions, architectural design rights, and contract scope.

**Check each material:** The current code package contains no images, icons, fonts, video, audio, or sample accounts. Local `outputs/` is excluded from Git, but may contain generated images, previews, and logs. Before sharing or delivering these, check the source and commercial permissions for originals, references, drawings, templates, prompts, screenshots, and generated content; inspect for personal data, client information, private material, trademarks, and signs. Before final use, check AI-generated code, documents, and images for provenance, copyright, similarity to third-party works, and commercial-use terms. If you add another API, model, SDK, stock asset, font, or icon, check its separate plan, terms, and license.

**Legal/professional review required:** Repository files alone cannot establish the exact rights and notice boundaries between modified upstream MIT files and new Apache 2.0 contributions, contributors’ authority, permission to upload client materials, third-party rights in output, or the governing delivery contract and law. Check the relevant materials and agreements before public distribution, sale, or client delivery.

**Prohibitions and caution:** Rights-infringing input/use, unauthorized use of a person's likeness, and bypassing OpenAI service restrictions may be prohibited. License warranty exclusions do not authorize unlawful use. This is general information, not a guarantee of legal effect. You are responsible for checking the applicable agreements and should consult a lawyer for a specific commercial release or dispute.
