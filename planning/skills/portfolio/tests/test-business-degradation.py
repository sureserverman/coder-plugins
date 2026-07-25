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


def make_env(tmp, business_absent=True, names=("alpha", "beta")):
    """A throwaway HOME + vault with `names` projects, the first carrying a
    business/ assessment. Returns (env, vault)."""
    home = tmp / "home"
    vault = tmp / "vault"
    (home / ".claude").mkdir(parents=True)
    for name in names:
        (vault / "Portfolio" / "ai-tools" / name).mkdir(parents=True)
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
    for name in names:
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


def test_compass_present_attaches_business(tmp):
    """Present-mode: the assessed project gains a 'business' key with its verdict
    and the research/plan ages; the unassessed project does not. alpha gets a
    market-research.md (present → int age) but NO plan.md (absent → null), so both
    the artifact-present and artifact-absent paths of the new age keys are exercised."""
    env, vault = make_env(tmp, business_absent=False)
    if not (ROOT / "business" / "scripts" / "business-scan.py").exists():
        print("  skip  compass present-mode (business plugin not in tree)")
        return
    # alpha: add a schema-2 market-research.md (age becomes a real int); leave plan.md absent
    (vault / "Portfolio" / "ai-tools" / "alpha" / "business" / "market-research.md").write_text(
        "---\nschema: 2\nproject: alpha\nresearched: 2026-07-01\ndepth: brief\n"
        "confidence: medium\n---\n# Market research: alpha\n")
    r = subprocess.run([sys.executable, str(COMPASS_SCAN)], capture_output=True, text=True, env=env)
    check(r.returncode == 0, f"compass-scan (present): exit 0 ({r.stderr.strip()[:120]})")
    doc = json.loads(r.stdout)
    by = {p["name"]: p for p in doc["projects"]}
    ab = by.get("alpha", {}).get("business", {})
    check(ab.get("verdict") == "monetize",
          "compass-scan (present): assessed project carries business.verdict")
    check(isinstance(ab.get("research_age_days"), int) and ab["research_age_days"] >= 0,
          f"compass-scan (present): research_age_days is int (artifact present) — got {ab.get('research_age_days')!r}")
    check(ab.get("plan_age_days") is None,
          f"compass-scan (present): plan_age_days null (no plan.md) — got {ab.get('plan_age_days')!r}")
    check("business" not in by.get("beta", {}),
          "compass-scan (present): unassessed project has no business key")


def test_compass_broken_business_degrades(tmp):
    """Present-but-BROKEN: a business scanner that emits valid-but-wrong-shape JSON
    (or a top-level array, or a project with no name) must degrade to no business
    layer, NEVER crash the whole compass lane."""
    env, _ = make_env(tmp, business_absent=True)
    for label, payload in [
        ("wrong-shape project", '{"projects": [{"assessed": true, "verdict": "monetize"}]}'),
        ("top-level array", '[1, 2, 3]'),
        ("not json", 'this is not json at all'),
    ]:
        fake = tmp / f"fake-{label.replace(' ', '_')}.py"
        fake.write_text(f"print({payload!r})\n")
        env2 = dict(env, BUSINESS_SCAN_PATH=str(fake))
        r = subprocess.run([sys.executable, str(COMPASS_SCAN)], capture_output=True, text=True, env=env2)
        check(r.returncode == 0, f"compass-scan (broken business: {label}): exit 0, not a crash")
        try:
            doc = json.loads(r.stdout)
            ok = "projects" in doc and not any("business" in p for p in doc["projects"])
        except json.JSONDecodeError:
            ok = False
        check(ok, f"compass-scan (broken business: {label}): valid envelope, no business keys")


def _fake_scanner(tmp, label, payload):
    """A stand-in business-scan.py that prints exactly `payload` as JSON."""
    fake = tmp / f"fake-{label}.py"
    fake.write_text(f"print({json.dumps(payload)!r})\n")
    return str(fake)


# One group entry (alpha + gamma) plus one ungrouped assessed project (beta),
# shaped as business-scan.py emits them. Deliberately distinct values per entry
# so a mis-keyed lookup shows up as the wrong verdict rather than passing.
GROUP_ENTRY = {
    "name": "suite", "area": None, "group": True,
    "members": ["ai-tools/alpha", "ai-tools/gamma"],
    "assessed": True, "verdict": "monetize",
    "monetization": {"model": "paid"}, "gtm": {"pct": 50}, "metrics": [],
    "last_reviewed_age_days": 1,
    "research": {"exists": True, "age_days": 7},
    "plan": {"exists": False, "age_days": None},
}
UNGROUPED_ENTRY = {
    "name": "beta", "area": "ai-tools", "assessed": True, "verdict": "later",
    "monetization": None, "gtm": None, "metrics": [],
    "last_reviewed_age_days": 3,
    "research": {"exists": False, "age_days": None},
    "plan": {"exists": False, "age_days": None},
}
EXPECT_GROUPED = {"verdict": "monetize", "model": "paid", "gtm_pct": 50,
                  "last_reviewed_age_days": 1, "research_age_days": 7,
                  "plan_age_days": None, "stage": "launched", "group": "suite"}
EXPECT_UNGROUPED = {"verdict": "later", "model": None, "gtm_pct": None,
                    "last_reviewed_age_days": 3, "research_age_days": None,
                    "plan_age_days": None, "stage": "assessed"}


def test_compass_group_aware(tmp):
    """A business group is not a registry project: it must not add a project row,
    but each member must carry the GROUP's business state tagged `group: <slug>`.
    Ungrouped projects keep exactly today's block."""
    env, _ = make_env(tmp, business_absent=True, names=("alpha", "beta", "gamma"))
    env = dict(env, BUSINESS_SCAN_PATH=_fake_scanner(
        tmp, "groups", {"groups": ["suite"], "projects": [GROUP_ENTRY, UNGROUPED_ENTRY]}))
    r = subprocess.run([sys.executable, str(COMPASS_SCAN)], capture_output=True, text=True, env=env)
    check(r.returncode == 0, f"compass-scan (groups): exit 0 ({r.stderr.strip()[:120]})")
    doc = json.loads(r.stdout)
    by = {p["name"]: p for p in doc["projects"]}
    check("suite" not in by, "compass-scan (groups): group slug is NOT a top-level project row")
    check(set(by) == {"alpha", "beta", "gamma"},
          f"compass-scan (groups): only registry projects have rows — got {sorted(by)}")
    for member in ("alpha", "gamma"):
        check(by.get(member, {}).get("business") == EXPECT_GROUPED,
              f"compass-scan (groups): member {member} carries the group's block + group:suite "
              f"— got {by.get(member, {}).get('business')!r}")
    check(by.get("beta", {}).get("business") == EXPECT_UNGROUPED,
          f"compass-scan (groups): ungrouped project's block unchanged (no 'group' key) "
          f"— got {by.get('beta', {}).get('business')!r}")


def test_compass_no_group_keys_is_backward_compatible(tmp):
    """Older business plugin: scanner JSON with no `groups`/`group`/`members` keys
    at all must produce exactly today's per-project blocks."""
    env, _ = make_env(tmp, business_absent=True)
    legacy_alpha = dict(UNGROUPED_ENTRY, name="alpha", verdict="monetize",
                        monetization={"model": "paid"})
    env = dict(env, BUSINESS_SCAN_PATH=_fake_scanner(
        tmp, "legacy", {"projects": [legacy_alpha, UNGROUPED_ENTRY]}))
    r = subprocess.run([sys.executable, str(COMPASS_SCAN)], capture_output=True, text=True, env=env)
    check(r.returncode == 0, f"compass-scan (no group keys): exit 0 ({r.stderr.strip()[:120]})")
    by = {p["name"]: p for p in json.loads(r.stdout)["projects"]}
    check(by.get("beta", {}).get("business") == EXPECT_UNGROUPED,
          f"compass-scan (no group keys): block unchanged — got {by.get('beta', {}).get('business')!r}")
    check(by.get("alpha", {}).get("business") ==
          dict(EXPECT_UNGROUPED, verdict="monetize", model="paid", stage="modeled"),
          f"compass-scan (no group keys): assessed block unchanged "
          f"— got {by.get('alpha', {}).get('business')!r}")


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
               test_compass_present_attaches_business,
               test_compass_broken_business_degrades,
               test_compass_group_aware,
               test_compass_no_group_keys_is_backward_compatible,
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
