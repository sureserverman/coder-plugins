#!/usr/bin/env python3
"""lint-dual — keep the Claude Code and Codex skill front-ends honest.

The business plugin authors each skill once as shared logic (scripts/ +
references/ + agents/) with two thin front-ends: business/skills/<name>/SKILL.md
(Claude Code) and business/codex/skills/<name>/SKILL.md (Codex). Drift between
the two is the dual-authoring failure mode this guard prevents.

It checks two invariants per skill:
  1. Parity — every Claude Code skill has a Codex adapter and vice versa.
  2. Shared-asset agreement — both front-ends reference the SAME set of shared
     assets (scripts/*.py, references/*.md, agents/*.md, by basename). If one
     front-end starts using a new script/reference the other doesn't, that's
     drift.

Exit 0 when both hold; exit 1 with a named diff otherwise. Read-only.

Usage: python3 lint-dual.py [plugin_root]   (default: the business/ plugin root)
"""
import sys
from pathlib import Path


def plugin_root():
    # business/scripts/lint-dual.py → business/
    return Path(__file__).resolve().parents[1]


def asset_universe(root):
    """Basenames of the shared assets both front-ends may reference."""
    assets = set()
    for sub, ext in (("scripts", "*.py"), ("references", "*.md"), ("agents", "*.md")):
        d = root / sub
        if not d.is_dir():
            continue
        for f in d.glob(ext):
            if f.name == "lint-dual.py":
                continue        # the linter isn't a skill asset
            assets.add(f.name)
    return assets


def mentioned(text, universe):
    return {a for a in universe if a in text}


def skill_names(base):
    if not base.is_dir():
        return set()
    return {d.name for d in base.iterdir() if (d / "SKILL.md").is_file()}


def lint(root):
    root = Path(root)
    universe = asset_universe(root)
    cc = skill_names(root / "skills")
    cx = skill_names(root / "codex" / "skills")
    problems = []

    for name in sorted(cc - cx):
        problems.append(f"{name}: Claude Code skill has no Codex adapter (business/codex/skills/{name}/)")
    for name in sorted(cx - cc):
        problems.append(f"{name}: Codex adapter has no Claude Code skill (business/skills/{name}/)")

    for name in sorted(cc & cx):
        cc_text = (root / "skills" / name / "SKILL.md").read_text(errors="ignore")
        cx_text = (root / "codex" / "skills" / name / "SKILL.md").read_text(errors="ignore")
        cc_set = mentioned(cc_text, universe)
        cx_set = mentioned(cx_text, universe)
        if cc_set != cx_set:
            only_cc = sorted(cc_set - cx_set)
            only_cx = sorted(cx_set - cc_set)
            problems.append(
                f"{name}: shared-asset drift — "
                f"Claude-Code-only {only_cc or '[]'}, Codex-only {only_cx or '[]'}")
    return problems


def main(argv):
    root = argv[1] if len(argv) > 1 else plugin_root()
    problems = lint(root)
    if problems:
        print("lint-dual: DRIFT between Claude Code and Codex front-ends")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print("lint-dual: OK — Claude Code and Codex front-ends reference identical shared assets")


if __name__ == "__main__":
    main(sys.argv)
