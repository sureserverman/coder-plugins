#!/usr/bin/env python3
"""Enforce a max-length budget on plugin component `description` frontmatter.

For every enabled plugin, Claude Code injects the `description` frontmatter of
each skill, agent, and slash command into model context at session start. This
script measures those descriptions against a character budget so the always-on
context footprint can't silently regress.

Scans `*/skills/*/SKILL.md`, `*/agents/*.md`, `*/commands/*.md` from the repo
root. Paths under `tests/` or `fixtures/` are excluded (they are test data, not
shipped components). A path listed in `scripts/frontmatter-budget-allow.txt`
(one repo-relative path per line, `#` comments allowed) is reported as allowed
and never counts as a violation.

Read-only: never writes to the repo. Exit 0 when clean, 1 when any violation.
"""
import argparse
import glob
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWLIST_PATH = os.path.join(REPO_ROOT, "scripts", "frontmatter-budget-allow.txt")
PATTERNS = (
    ("skill", "*/skills/*/SKILL.md"),
    ("agent", "*/agents/*.md"),
    ("command", "*/commands/*.md"),
)
EXCLUDE_SEGMENTS = ("/tests/", "/fixtures/")

try:
    import yaml as _yaml
except ImportError:  # pragma: no cover - CI installs pyyaml
    _yaml = None


def load_allowlist(path=ALLOWLIST_PATH):
    allowed = set()
    if not os.path.exists(path):
        return allowed
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            entry = line.split("#", 1)[0].strip()
            if entry:
                allowed.add(entry)
    return allowed


def extract_description(text):
    """Return the frontmatter `description` value as a single collapsed line.

    Handles YAML folded/literal blocks (`description: >` / `|`) and plain
    single-line values. Returns None when there is no frontmatter description.
    """
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return None
    fm = m.group(1)
    m2 = re.search(
        r"^description:\s*(.*?)(?=\n[A-Za-z_][\w-]*:|\Z)", fm, re.S | re.M
    )
    if not m2:
        return None
    value = m2.group(1)
    # Strip a leading YAML block-scalar indicator (`>`, `|`, with optional
    # chomping/indent modifiers like `>-`, `|2`) so it isn't measured as text.
    value = re.sub(r"^[>|][+\-0-9]*\s*\n", "", value)
    return re.sub(r"\s+", " ", value.strip())


def yaml_error(text):
    """Return a short reason string if the frontmatter is not valid YAML with a
    usable string `description`, else None.

    Catches the common breakage of an unquoted plain scalar that contains a
    `: ` sequence (e.g. `description: ... Triggers: "x"`), which a real YAML
    loader rejects even though a naive regex parse would not. Falls back to a
    lightweight heuristic when PyYAML is unavailable.
    """
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return None
    fm = m.group(1)
    if _yaml is not None:
        try:
            data = _yaml.safe_load(fm)
        except Exception as exc:  # yaml.YAMLError and friends
            return str(exc).splitlines()[0][:120]
        if not isinstance(data, dict) or not isinstance(data.get("description"), str):
            return "description missing or not a string after YAML parse"
        return None
    # Fallback (no PyYAML): flag an unquoted single-line description containing `: `.
    m2 = re.search(r"^description:[ \t]*(?![>|'\"])(.*)$", fm, re.M)
    if m2 and ": " in m2.group(1):
        return "unquoted description contains ': ' (invalid plain scalar) [heuristic]"
    return None


def scan(root, max_chars, allowlist):
    violations = []
    allowed = []
    invalid = []
    for kind, pattern in PATTERNS:
        for path in glob.glob(os.path.join(root, pattern)):
            rel = os.path.relpath(path, root)
            norm = "/" + rel.replace(os.sep, "/")
            if any(seg in norm for seg in EXCLUDE_SEGMENTS):
                continue
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            plugin = rel.replace(os.sep, "/").split("/", 1)[0]
            err = yaml_error(text)
            if err is not None and rel not in allowlist:
                invalid.append({"path": rel, "kind": kind, "plugin": plugin, "error": err})
            desc = extract_description(text)
            if desc is None:
                continue
            n = len(desc)
            if n <= max_chars:
                continue
            record = {"path": rel, "kind": kind, "plugin": plugin, "chars": n}
            if rel in allowlist:
                allowed.append(record)
            else:
                violations.append(record)
    violations.sort(key=lambda r: -r["chars"])
    allowed.sort(key=lambda r: -r["chars"])
    invalid.sort(key=lambda r: r["path"])
    return violations, allowed, invalid


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max", type=int, default=300, help="max description chars (default 300)")
    ap.add_argument("--root", default=REPO_ROOT, help="repo root to scan")
    ap.add_argument("--allowlist", default=ALLOWLIST_PATH, help="path to allowlist file")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args(argv)

    allowlist = load_allowlist(args.allowlist)
    violations, allowed, invalid = scan(args.root, args.max, allowlist)

    if args.json:
        print(json.dumps(
            {"max": args.max, "violations": violations, "allowed": allowed, "invalid": invalid},
            indent=2,
        ))
    else:
        if invalid:
            print(f"{len(invalid)} description(s) with invalid YAML frontmatter:")
            for r in invalid:
                print(f"  {r['kind']:8s}  {r['path']}  — {r['error']}")
            print()
        if violations:
            print(f"{len(violations)} description(s) over {args.max} chars:")
            for r in violations:
                print(f"  {r['chars']:5d}  {r['kind']:8s}  {r['path']}")
        else:
            print(f"All descriptions within {args.max} chars.")
        if allowed:
            print(f"\n{len(allowed)} allowlisted (not counted):")
            for r in allowed:
                print(f"  {r['chars']:5d}  {r['kind']:8s}  {r['path']}")

    return 1 if (violations or invalid) else 0


if __name__ == "__main__":
    sys.exit(main())
