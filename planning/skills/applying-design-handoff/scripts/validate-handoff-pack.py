#!/usr/bin/env python3
"""Tolerant structural linter for a *local* Claude Design handoff pack.

Locates the pack root under a given path, confirms at least one recognizable
section (tokens / components / layout / assets), and prints a normalized manifest
as JSON. The pack format is proprietary and moving, so this checks *shape*, not a
frozen schema: it fails only when nothing recognizable can be found at all.

Usage:
    validate-handoff-pack.py <path>

Exit 0 = a usable pack was found (manifest printed to stdout).
Exit 1 = no recognizable pack under <path> (reason printed to stderr).
Exit 2 = bad invocation.

No third-party deps; stdlib only. The *live* (DesignSync) input path is not linted
here — that goes through the DesignSync tool's own read methods.
See ../references/handoff-pack-format.md for the contract.
"""

import json
import os
import sys

MANIFEST_NAMES = ("handoff.json", "manifest.json", "design.json", "_ds_manifest.json")
TOKEN_NAMES = ("tokens.json", "tokens.js", "tokens.css", "tokens.yaml", "tokens.yml")
COMPONENT_DIRS = ("components", "component")
LAYOUT_DIRS = ("screens", "layouts", "layout", "frames")
ASSET_DIRS = ("assets", "asset", "media")
MAX_SEARCH_DEPTH = 4  # how deep below <path> we'll hunt for a pack root


def _has_section(d):
    """Return a sections dict for directory d (counts/flags), or None if barren."""
    try:
        entries = os.listdir(d)
    except OSError:
        return None
    lower = {e.lower(): e for e in entries}

    sections = {"tokens": False, "components": 0, "layout": 0, "assets": 0}

    # tokens: a tokens.* file, or a manifest carrying a "tokens" key
    if any(t in lower for t in TOKEN_NAMES):
        sections["tokens"] = True

    for name in MANIFEST_NAMES:
        if name in lower:
            try:
                with open(os.path.join(d, lower[name]), encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, dict):
                    if "tokens" in data:
                        sections["tokens"] = True
                    comp = data.get("components")
                    if isinstance(comp, (list, dict)):
                        sections["components"] = max(sections["components"], len(comp))
                    lay = data.get("screens") or data.get("layout") or data.get("layouts")
                    if isinstance(lay, (list, dict)):
                        sections["layout"] = max(sections["layout"], len(lay))
            except (OSError, ValueError):
                pass  # tolerant: a malformed manifest doesn't sink an otherwise-good pack

    def _count_dir(names):
        for n in names:
            if n in lower and os.path.isdir(os.path.join(d, lower[n])):
                try:
                    return len([
                        f for f in os.listdir(os.path.join(d, lower[n]))
                        if not f.startswith(".")
                    ])
                except OSError:
                    return 0
        return 0

    sections["components"] = max(sections["components"], _count_dir(COMPONENT_DIRS))
    sections["layout"] = max(sections["layout"], _count_dir(LAYOUT_DIRS))
    sections["assets"] = _count_dir(ASSET_DIRS)

    gradeable = sections["tokens"] or sections["components"] or sections["layout"]
    return sections if gradeable else None


def find_pack_root(start):
    """Walk start (and descendants, bounded) for the first dir that looks like a pack."""
    start = os.path.abspath(start)
    if not os.path.isdir(start):
        return None, None
    start_depth = start.rstrip(os.sep).count(os.sep)
    for dirpath, dirs, _files in os.walk(start):
        depth = dirpath.rstrip(os.sep).count(os.sep) - start_depth
        if depth > MAX_SEARCH_DEPTH:
            dirs[:] = []
            continue
        if os.path.basename(dirpath) == ".git":
            dirs[:] = []
            continue
        sections = _has_section(dirpath)
        if sections is not None:
            return dirpath, sections
    return None, None


def main(argv):
    if len(argv) != 2:
        print("usage: validate-handoff-pack.py <path>", file=sys.stderr)
        return 2
    target = argv[1]
    root, sections = find_pack_root(target)
    if root is None:
        print(
            f"no recognizable handoff pack under {os.path.abspath(target)} "
            "(need at least one of: tokens, components, or layout/screens)",
            file=sys.stderr,
        )
        return 1
    manifest = {
        "source": "local",
        "root": root,
        "sections": sections,
        "gradeable": [
            k for k, v in (
                ("tokens", sections["tokens"]),
                ("components", sections["components"]),
                ("layout", sections["layout"]),
            ) if v
        ],
    }
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
