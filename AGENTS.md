# Repository Instructions

This repository publishes the `architectural-render-guard` Codex plugin.

After changing plugin code, skill instructions, references, tests, or manifest:

1. Run `python -m unittest discover -s tests -v`.
2. Run the Codex skill and plugin validators when available.
3. Review staged paths and secrets, commit on a working branch, push that branch to the private repository, and open a PR to `main`.
4. Never commit API keys, `.env` files, generated images, previews, logs, or
   Python cache files.
5. Keep `.agents/plugins/marketplace.json` pointed at the private
   `sodam-ai/_SoDam-RenderBoss` repository and keep the marketplace/plugin names stable.

The publishing script can change local caches and commit files; it must run
only on a reviewed working branch with the expected private `origin`. Never
push directly to `main` or use its API fallback.
