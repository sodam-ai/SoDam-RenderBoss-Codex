#!/usr/bin/env python3
"""Package the keyless plugin as a local Codex marketplace without secrets or outputs."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

FILES = (
    ".codex-plugin/plugin.json",
    "skills/architectural-render-guard/SKILL.md",
    "scripts/builtin_guard.py",
    "scripts/render_guard.py",
    "requirements.txt",
    "README.md",
    "README.en.md",
    "README.html",
    "README.en.html",
    "LICENSE",
    "LICENSES/MIT-upstream.txt",
    "NOTICE",
)


def build(root: Path, destination: Path) -> dict:
    if destination.exists():
        raise ValueError(f"Destination already exists: {destination}")
    for relative in FILES:
        if not (root / relative).is_file():
            raise ValueError(f"Required file is missing: {root / relative}")
    plugin = destination / "plugins" / "architectural-render-guard"
    for relative in FILES:
        target = plugin / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative, target)
    marketplace = {
        "name": "architectural-render-guard-keyless-local",
        "interface": {"displayName": "Architectural Render Guard (Keyless Local)"},
        "plugins": [{
            "name": "architectural-render-guard",
            "source": {"source": "local", "path": "./plugins/architectural-render-guard"},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": "Productivity",
        }],
    }
    target = destination / ".agents" / "plugins" / "marketplace.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(marketplace, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"marketplace_root": str(destination.resolve()),
            "plugin_root": str(plugin.resolve()),
            "plugin_version": json.loads((plugin / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))["version"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        result = build(root, args.out_dir)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
