#!/usr/bin/env python3
"""Fixture suite for resolve-dest.py — run directly (CI convention):
    python3 business/scripts/tests/test-resolve-dest.py

Proves resolve-dest prints the global-business.md path for a good portfolio
config, and degrades to business-scan's clean "portfolio not configured"
message (no raw traceback) when vault_dir is unset — the BL-005 guarantee.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "resolve-dest.py"

FAILURES = []


def check(cond, label):
    print(("  ok  " if cond else "  FAIL") + f"  {label}")
    if not cond:
        FAILURES.append(label)


def run(home):
    env = dict(os.environ, HOME=str(home))
    return subprocess.run([sys.executable, str(SCRIPT)],
                          capture_output=True, text=True, env=env)


def test_good():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        home = tmp / "home"
        vault = tmp / "vault"
        (home / ".claude").mkdir(parents=True)
        vault.mkdir()
        (home / ".claude" / "portfolio-config.yaml").write_text(
            f"version: 1\nvault_dir: {vault}\n")
        (home / ".claude" / "projects-registry.yaml").write_text(
            "projects:\n  - name: x\n    area: ai-tools\n    enabled: true\n")
        r = run(home)
        check(r.returncode == 0, f"good: exit 0 (stderr {r.stderr.strip()[:120]})")
        expected = str(vault / "Portfolio" / "global-business.md")
        check(r.stdout.strip() == expected,
              f"good: prints dest (got {r.stdout.strip()!r}, want {expected!r})")


def test_missing_vault_dir():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        home = tmp / "home"
        (home / ".claude").mkdir(parents=True)
        (home / ".claude" / "portfolio-config.yaml").write_text("version: 1\n")
        (home / ".claude" / "projects-registry.yaml").write_text("projects: []\n")
        r = run(home)
        check(r.returncode != 0, "missing vault_dir: non-zero exit")
        check("portfolio not configured" in r.stderr,
              f"missing vault_dir: clean message (got {r.stderr.strip()[:160]!r})")
        check("Traceback" not in r.stderr,
              "missing vault_dir: no raw traceback")


def main():
    test_good()
    test_missing_vault_dir()
    if FAILURES:
        print(f"\nFAILED — {len(FAILURES)} check(s):")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("\nOK — all resolve-dest checks passed")


if __name__ == "__main__":
    main()
