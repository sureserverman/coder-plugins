#!/usr/bin/env python3
"""Fixture suite for compass-scan.py — run directly (CI convention):
    python3 planning/skills/compass/tests/test-compass-scan.py

Builds a throwaway HOME with a portfolio-config + registry pointing at the
fixture vault tree, runs the scanner as a subprocess, and asserts the JSON
contract: envelope keys, unconfigured error, plan-state extraction, signal
collectors, couldnt_assess partition, and the read-only guarantee.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "compass-scan.py"
FIXTURES = HERE / "fixtures"

FAILURES = []


def check(cond, label):
    print(("  ok  " if cond else "  FAIL") + f"  {label}")
    if not cond:
        FAILURES.append(label)


def tree_digest(root):
    h = hashlib.sha256()
    for p in sorted(Path(root).rglob("*")):
        if p.is_file():
            h.update(p.as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def run_scan(home, expect_ok=True):
    env = dict(os.environ, HOME=str(home))
    r = subprocess.run([sys.executable, str(SCRIPT)],
                       capture_output=True, text=True, env=env)
    if expect_ok:
        assert r.returncode == 0, f"scanner failed:\n{r.stderr}"
        return json.loads(r.stdout)
    return r


def make_env(tmp):
    """Fixture HOME + vault: copy the vault tree, patch registry paths."""
    home = tmp / "home"
    vault = tmp / "vault"
    (home / ".claude").mkdir(parents=True)
    shutil.copytree(FIXTURES / "vault", vault)
    (home / ".claude" / "portfolio-config.yaml").write_text(
        f"version: 1\nvault_dir: {vault}\n")

    # repos: alpha is a real git repo with a fixed-date commit; beta is a
    # plain dir (non-git); ghost's path doesn't exist at all
    alpha_repo = tmp / "dev" / "ai-tools" / "alpha"
    alpha_repo.mkdir(parents=True)
    (alpha_repo / "README.md").write_text("alpha\n")
    env = dict(os.environ,
               GIT_AUTHOR_DATE="2026-01-01T12:00:00 +0000",
               GIT_COMMITTER_DATE="2026-01-01T12:00:00 +0000")
    git = ["git", "-c", "user.email=t@t", "-c", "user.name=t",
           "-c", "core.hooksPath=/dev/null"]
    for cmd in (git + ["init", "-q"],
                git + ["add", "-A"],
                git + ["commit", "-qm", "init", "--no-verify"]):
        subprocess.run(cmd, cwd=alpha_repo, env=env, check=True,
                       capture_output=True)
    beta_repo = tmp / "dev" / "ai-tools" / "beta"
    beta_repo.mkdir(parents=True)
    (beta_repo / "notes.txt").write_text("not a git repo\n")

    (home / ".claude" / "projects-registry.yaml").write_text(f"""\
projects:
  - name: alpha
    area: ai-tools
    path: {alpha_repo}
    enabled: true
  - name: beta
    area: ai-tools
    path: {beta_repo}
    enabled: true
  - name: ghost
    area: ai-tools
    path: {tmp}/dev/ai-tools/ghost
    enabled: true
  - name: off
    area: ai-tools
    path: {tmp}/dev/ai-tools/off
    enabled: false
""")
    return home, vault


def test_envelope_and_unconfigured(tmp):
    print("[envelope]")
    home, vault = make_env(tmp)
    before = tree_digest(vault)
    out = run_scan(home)
    for key in ("generated", "vault_dir", "projects", "couldnt_assess"):
        check(key in out, f"envelope has '{key}'")
    names = {p["name"] for p in out["projects"]}
    check("alpha" in names, "alpha assessed")
    check("off" not in names, "disabled project excluded")
    ca = {c["name"]: c for c in out["couldnt_assess"]}
    check("ghost" in ca and "not exist" in ca["ghost"]["reason"],
          "missing path lands in couldnt_assess with reason")
    check(len(out["projects"]) + len(out["couldnt_assess"]) == 3,
          "projects + couldnt_assess partition the enabled registry")
    check(tree_digest(vault) == before, "vault tree unmodified (read-only)")

    print("[unconfigured]")
    empty = tmp / "empty-home"
    (empty / ".claude").mkdir(parents=True)
    r = run_scan(empty, expect_ok=False)
    check(r.returncode != 0, "unconfigured exits non-zero")
    check("portfolio not configured" in (r.stderr + r.stdout),
          "unconfigured names the fix")


def test_plan_state(tmp):
    print("[plan_state]")
    home, vault = make_env(tmp)
    out = run_scan(home)
    projects = {p["name"]: p for p in out["projects"]}
    plans_a = {p["file"]: p for p in projects["alpha"]["plans"]}

    widget = plans_a["2026-06-01-widget-plan.md"]
    check(widget["active"] is True, "open plan is active")
    check(widget["stage"] == 2, "open plan reports current stage 2")
    check(widget["next_task"] == "Task 2.2: Install windows",
          "next unchecked task surfaced")
    check((widget["done"], widget["total"]) == (3, 4), "task counts 3/4")

    shed = plans_a["2026-05-01-shed-plan.md"]
    check(shed["active"] is False, "closed plan inactive")
    check(shed["completed"] == "2026-05-02", "close-out date parsed")

    plans_b = {p["file"]: p for p in projects["beta"]["plans"]}
    check("2026-06-20-fleet-master-plan.md" not in plans_b,
          "master plan emits nothing")
    mystery = plans_b["2026-06-15-mystery-plan.md"]
    check(mystery["active"] is True and mystery["stage"] is None,
          "malformed plan degrades to active/stage-unknown")
    check("stage unknown" in (mystery["note"] or ""),
          "malformed plan carries the degradation note, not dropped")


def test_signals(tmp):
    print("[signals]")
    home, vault = make_env(tmp)
    out = run_scan(home)
    projects = {p["name"]: p for p in out["projects"]}
    alpha, beta = projects["alpha"], projects["beta"]

    expected_age = (datetime.now(tz=timezone.utc).date() - date(2026, 1, 1)).days
    check(alpha["git"]["last_commit"] == "2026-01-01"
          and alpha["git"]["age_days"] == expected_age,
          "git recency: fixed-date commit yields exact age_days")
    check(beta["git"] is None
          and any(e.startswith("git:") for e in beta["errors"]),
          "non-git repo degrades to git:null + errors entry, project kept")

    bl = alpha["backlog"]
    check(bl["open"] == 3, "backlog open count")
    check(bl["parked"] == 1
          and bl["parked_items"][0]["title"] == "Paint the trim"
          and "dry season" in bl["parked_items"][0]["note"],
          "parked: annotation parsed with reason")

    mat = alpha["maturity"]
    check(mat["axes"]["Documentation"] == {"done": 1, "open": 1, "na": 0},
          "maturity axis Documentation 1 done / 1 open")
    check(mat["axes"]["Testing & CI"] == {"done": 1, "open": 0, "na": 1},
          "maturity axis Testing & CI counts [N/A]")
    check(beta["maturity"] is None, "missing MATURITY.md yields null, no error")

    check(alpha["dependents"] == [{"project": "beta",
                                   "why": "beta consumes alpha's widget API"}],
          "integration out-edge: beta depends on alpha")
    check(alpha["depends_on"][0]["project"] == "gamma",
          "integration in-edge: alpha depends on gamma")


def main():
    with tempfile.TemporaryDirectory() as td:
        test_envelope_and_unconfigured(Path(td))
    with tempfile.TemporaryDirectory() as td:
        test_plan_state(Path(td))
    with tempfile.TemporaryDirectory() as td:
        test_signals(Path(td))
    if FAILURES:
        print(f"\nFAILED — {len(FAILURES)} check(s):")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("\nOK — all compass-scan fixture checks passed")


if __name__ == "__main__":
    main()
