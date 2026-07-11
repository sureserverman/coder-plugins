#!/usr/bin/env python3
"""Fixture suite for lint-dual.py — run directly (CI convention):
    python3 business/scripts/tests/test-lint-dual.py

Builds throwaway plugin trees and runs lint-dual.py against them as a subprocess,
asserting it passes a matched CC/Codex front-end pair and fails on each drift
mode: a shared-asset mismatch and a missing counterpart (parity).
"""
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "lint-dual.py"

FAILURES = []


def check(cond, label):
    print(("  ok  " if cond else "  FAIL") + f"  {label}")
    if not cond:
        FAILURES.append(label)


def build_root(tmp):
    """A minimal plugin tree with the shared-asset dirs populated."""
    root = tmp
    for sub in ("scripts", "references", "agents"):
        (root / sub).mkdir(parents=True)
    (root / "scripts" / "business-scan.py").write_text("# scanner\n")
    (root / "scripts" / "collect-github.py").write_text("# collector\n")
    (root / "references" / "a-format.md").write_text("# a\n")
    (root / "references" / "b-format.md").write_text("# b\n")
    (root / "agents" / "researcher.md").write_text("# agent\n")
    return root


def write_skill(root, side, name, body):
    base = root / ("skills" if side == "cc" else "codex/skills") / name
    base.mkdir(parents=True)
    (base / "SKILL.md").write_text(body)


def run(root):
    return subprocess.run([sys.executable, str(SCRIPT), str(root)],
                          capture_output=True, text=True)


def test_matched():
    with tempfile.TemporaryDirectory() as td:
        root = build_root(Path(td))
        body = "uses scripts/business-scan.py and references/a-format.md"
        write_skill(root, "cc", "foo", body)
        write_skill(root, "codex", "foo", "codex: scripts/business-scan.py + references/a-format.md")
        r = run(root)
        check(r.returncode == 0, "matched pair: exit 0")
        check("OK" in r.stdout, "matched pair: reports OK")


def test_asset_drift():
    with tempfile.TemporaryDirectory() as td:
        root = build_root(Path(td))
        write_skill(root, "cc", "foo", "scripts/business-scan.py references/a-format.md")
        # Codex adapter references b-format.md instead of a-format.md → drift
        write_skill(root, "codex", "foo", "scripts/business-scan.py references/b-format.md")
        r = run(root)
        check(r.returncode == 1, "asset drift: exit 1")
        check("shared-asset drift" in r.stdout, "asset drift: names the drift")
        check("a-format.md" in r.stdout and "b-format.md" in r.stdout,
              "asset drift: reports both sides of the diff")


def test_missing_codex_adapter():
    with tempfile.TemporaryDirectory() as td:
        root = build_root(Path(td))
        write_skill(root, "cc", "orphan", "scripts/business-scan.py")
        # no Codex adapter for 'orphan'
        r = run(root)
        check(r.returncode == 1, "missing codex adapter: exit 1")
        check("no Codex adapter" in r.stdout, "missing codex adapter: named")


def test_missing_cc_skill():
    with tempfile.TemporaryDirectory() as td:
        root = build_root(Path(td))
        write_skill(root, "codex", "ghost", "scripts/business-scan.py")
        # Codex adapter with no Claude Code skill (symmetric parity branch)
        r = run(root)
        check(r.returncode == 1, "missing cc skill: exit 1")
        check("no Claude Code skill" in r.stdout, "missing cc skill: named")


def main():
    test_matched()
    test_asset_drift()
    test_missing_codex_adapter()
    test_missing_cc_skill()
    if FAILURES:
        print(f"\nFAILED — {len(FAILURES)} check(s):")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("\nOK — all lint-dual fixture checks passed")


if __name__ == "__main__":
    main()
