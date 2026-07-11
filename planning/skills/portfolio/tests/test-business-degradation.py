#!/usr/bin/env python3
"""Degradation guard for the business-plugin integration — run directly:
    python3 planning/skills/portfolio/tests/test-business-degradation.py

Written BEFORE the portfolio-rebuild / compass-scan patches land (Stage 5). It
pins the invariant that when the business plugin is ABSENT, compass-scan.py and
portfolio-rebuild.py behave exactly as they do today — no business keys in the
compass JSON, no global-business.md written — with only a single loud
"business layer unavailable" signal added. The business probe is forced off via
the BUSINESS_SCAN_PATH env var pointing at a nonexistent path.

The PRESENT-mode assertions (business data appears when the plugin IS installed)
are added by the patches themselves; this file's absent-mode assertions must
stay green across the whole stage.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]                       # marketplace root (coder-plugins/)
COMPASS_SCAN = ROOT / "planning" / "skills" / "compass" / "scripts" / "compass-scan.py"
PORTFOLIO_REBUILD = ROOT / "planning" / "skills" / "portfolio" / "scripts" / "portfolio-rebuild.py"

FAILURES = []


def check(cond, label):
    print(("  ok  " if cond else "  FAIL") + f"  {label}")
    if not cond:
        FAILURES.append(label)


def make_env(tmp, business_absent=True):
    """A throwaway HOME + vault with two projects, one carrying a business/
    assessment. Returns (env, vault)."""
    home = tmp / "home"
    vault = tmp / "vault"
    (home / ".claude").mkdir(parents=True)
    for area, name in (("ai-tools", "alpha"), ("ai-tools", "beta")):
        (vault / "Portfolio" / area / name).mkdir(parents=True)
    # alpha carries a business assessment; beta does not
    (vault / "Portfolio" / "ai-tools" / "alpha" / "business").mkdir()
    (vault / "Portfolio" / "ai-tools" / "alpha" / "business" / "BUSINESS.md").write_text(
        "---\nschema: 1\nproject: alpha\nverdict: monetize\naudience: x\n"
        "evidence: local-only\nlast_reviewed: 2026-07-01\n"
        "monetization:\n  model: paid\n  pricing: null\n  channels: []\ntargets: []\n---\n# x\n")
    (home / ".claude" / "portfolio-config.yaml").write_text(f"version: 1\nvault_dir: {vault}\n")
    repos = tmp / "dev" / "ai-tools"
    repos.mkdir(parents=True)
    reg = "projects:\n"
    for name in ("alpha", "beta"):
        (repos / name).mkdir()
        reg += f"  - name: {name}\n    area: ai-tools\n    path: {repos/name}\n    enabled: true\n"
    (home / ".claude" / "projects-registry.yaml").write_text(reg)

    env = dict(os.environ, HOME=str(home))
    # Force the business probe OFF (absent) by pointing it at a nonexistent path.
    env["BUSINESS_SCAN_PATH"] = str(tmp / "nonexistent" / "business-scan.py") if business_absent else str(
        ROOT / "business" / "scripts" / "business-scan.py")
    return env, vault


def test_compass_absent_is_unchanged(tmp):
    env, _ = make_env(tmp, business_absent=True)
    r = subprocess.run([sys.executable, str(COMPASS_SCAN)], capture_output=True, text=True, env=env)
    check(r.returncode == 0, f"compass-scan (business absent): exit 0 ({r.stderr.strip()[:120]})")
    doc = json.loads(r.stdout)
    # Degradation invariant: NOT ONE project entry carries a business key.
    has_biz = any("business" in p for p in doc.get("projects", []))
    check(not has_biz, "compass-scan (absent): no per-project 'business' key — output shape unchanged")
    # Today's envelope keys are all still present and no others leaked in.
    check({"generated", "vault_dir", "projects", "couldnt_assess"} <= set(doc),
          "compass-scan (absent): today's envelope keys intact")


def test_portfolio_rebuild_absent_writes_no_global_business(tmp):
    env, vault = make_env(tmp, business_absent=True)
    r = subprocess.run([sys.executable, str(PORTFOLIO_REBUILD), "--write"],
                       capture_output=True, text=True, env=env)
    check(r.returncode == 0, f"portfolio-rebuild (business absent): exit 0 ({r.stderr.strip()[:120]})")
    gb = vault / "Portfolio" / "global-backlog.md"
    gm = vault / "Portfolio" / "global-maturity.md"
    gbiz = vault / "Portfolio" / "global-business.md"
    check(gb.exists() and gm.exists(), "portfolio-rebuild (absent): global-backlog + global-maturity still written")
    check(not gbiz.exists(), "portfolio-rebuild (absent): global-business.md NOT written when plugin absent")


def test_portfolio_rebuild_present_writes_global_business(tmp):
    """Present-mode (business plugin installed): global-business.md IS rebuilt,
    while global-backlog/maturity are unaffected."""
    env, vault = make_env(tmp, business_absent=False)
    if not (ROOT / "business" / "scripts" / "business-scan.py").exists():
        print("  skip  portfolio-rebuild present-mode (business plugin not in tree)")
        return
    r = subprocess.run([sys.executable, str(PORTFOLIO_REBUILD), "--write"],
                       capture_output=True, text=True, env=env)
    check(r.returncode == 0, f"portfolio-rebuild (present): exit 0 ({r.stderr.strip()[:120]})")
    gbiz = vault / "Portfolio" / "global-business.md"
    check(gbiz.exists(), "portfolio-rebuild (present): global-business.md written")
    check(gbiz.exists() and "ai-tools/[[alpha]]" in gbiz.read_text(),
          "portfolio-rebuild (present): assessed project appears in the roll-up")
    check("global-business written" in r.stdout, "portfolio-rebuild (present): status line reports it")


def main():
    for fn in (test_compass_absent_is_unchanged,
               test_portfolio_rebuild_absent_writes_no_global_business,
               test_portfolio_rebuild_present_writes_global_business):
        with tempfile.TemporaryDirectory() as td:
            fn(Path(td))
    if FAILURES:
        print(f"\nFAILED — {len(FAILURES)} check(s):")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("\nOK — business-integration degradation invariants hold")


if __name__ == "__main__":
    main()
