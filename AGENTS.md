# Repository Instructions

This repository publishes the `architectural-render-guard` Codex plugin.

After changing plugin code, skill instructions, references, tests, or manifest:

1. Run `python -m unittest discover -s tests -v`.
2. Run the Codex skill and plugin validators when available.
3. Run `scripts/publish.ps1 -Message "<concise update summary>"`.
4. Never commit API keys, `.env` files, generated images, previews, logs, or
   Python cache files.
5. Keep `.agents/plugins/marketplace.json` pointed at the public repository
   root and keep the marketplace/plugin names stable.

The publishing script refreshes the Codex cachebuster, synchronizes local
versioned caches, commits, and pushes `main`.
