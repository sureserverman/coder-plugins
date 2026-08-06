#!/usr/bin/env python3
"""Fixture suite for plan-progress.py — run directly (CI convention):
    python3 planning/skills/executing-plans/tests/test-plan-progress.py

Builds a throwaway repo tree with a .claude/plan-progress.json state file and
a plan fixture, runs the renderer as a subprocess with statusline-style stdin
JSON, and asserts: silence when idle/broken (never a traceback), the Status
counts via the shared portfolio-unify regexes, the bar geometry, the per-phase
glyphs, walk-up discovery from a subdirectory, and staleness marking.
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "plan-progress.py"

FAILURES = []

PLAN = """# Plan: demo feature

## Stage 1 — groundwork

### Task 1.1: scaffold module
- **Status:** [x]

### Task 1.2: wire config
- **Status:** [x]

## Stage 2 — behavior

### Task 2.1: parse entries
- **Status:** [x]

### Task 2.2: render output
- **Status:** [ ]

### Task 2.3: edge cases
- **Status:** [ ]
"""

# BL-001: the `[~]` partial state. One task of each kind, so the bar must read
# 1/3 — the partial task counts toward the denominator (the plan is less
# finished) but never fills the bar. Under the old `!= " "` classification it
# would have read 2/3, reporting in-flight work as done.
PARTIAL_PLAN = """# Plan: partial states

## Stage 1 — mixed

### Task 1.1: finished
- **Status:** [x]

### Task 1.2: in flight
- **Status:** [~]

### Task 1.3: not started
- **Status:** [ ]
"""

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def check(cond, label):
    print(("  ok  " if cond else "  FAIL") + f"  {label}")
    if not cond:
        FAILURES.append(label)


def run(cwd_value, extra_stdin=None):
    stdin = extra_stdin if extra_stdin is not None else json.dumps({"cwd": str(cwd_value)})
    r = subprocess.run(
        [sys.executable, str(SCRIPT)], input=stdin, capture_output=True, text=True
    )
    return r, ANSI_RE.sub("", r.stdout)


def write_state(root, **kw):
    state = {"updated": datetime.now(timezone.utc).isoformat()}
    state.update(kw)
    (root / ".claude").mkdir(exist_ok=True)
    (root / ".claude" / "plan-progress.json").write_text(json.dumps(state))


def load_module():
    """Import plan-progress.py directly (hyphenated filename -> importlib)."""
    spec = importlib.util.spec_from_file_location("plan_progress", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_yaml(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def case_portfolio_resolver():
    """Task 2.1 — portfolio_plans_dir() resolves, or degrades to None.

    Every negative case here would, in the portfolio CLI scripts, be a
    sys.exit() with a message. In the renderer it must be None: this runs on
    every statusline redraw in every project, including on machines with no
    vault, no registry, and no `yaml` module at all.
    """
    print("Task 2.1 — portfolio home resolution:")
    mod = load_module()
    tmp = Path(tempfile.mkdtemp(prefix="pp-resolver-"))
    repo = tmp / "dev" / "area1" / "proj1"
    repo.mkdir(parents=True)
    vault = tmp / "vault"
    plans = vault / "Portfolio" / "area1" / "proj1" / "plans"
    plans.mkdir(parents=True)

    cfg, reg = tmp / "portfolio-config.yaml", tmp / "projects-registry.yaml"
    mod.CONFIG_PATH, mod.REGISTRY_PATH = cfg, reg
    write_yaml(cfg, f"version: 1\nvault_dir: {vault}\n")
    write_yaml(reg, "version: 1\nprojects:\n"
                    f"  - path: {repo}\n    name: proj1\n    area: area1\n    enabled: true\n")

    check(mod.portfolio_plans_dir(repo) == plans, "registered project resolves to its vault plans/ dir")

    # a nested cwd must resolve the same as the repo root
    nested = repo / "a" / "b"
    nested.mkdir(parents=True)
    check(mod.portfolio_plans_dir(repo) == plans, "resolution is stable for the repo root")

    print("  degradation cases (each must be None, never a raise):")
    local = repo / "docs" / "plans"
    local.mkdir(parents=True)
    mod.CONFIG_PATH = tmp / "nope-config.yaml"
    check(mod.portfolio_plans_dir(repo) is None,
          "missing portfolio-config.yaml -> None EVEN THOUGH docs/plans exists "
          "(absent config is not the same claim as an in-tree project)")
    mod.CONFIG_PATH = cfg
    write_yaml(cfg, "version: 1\n")
    check(mod.portfolio_plans_dir(repo) == local,
          "intact config with vault_dir unset falls back to <repo>/docs/plans")
    write_yaml(cfg, f"version: 1\nvault_dir: {vault}\n")

    mod.REGISTRY_PATH = tmp / "nope-registry.yaml"
    check(mod.portfolio_plans_dir(repo) is None, "missing registry -> None")
    mod.REGISTRY_PATH = reg

    unregistered = tmp / "dev" / "area1" / "other"
    unregistered.mkdir(parents=True)
    check(mod.portfolio_plans_dir(unregistered) is None,
          "unregistered project -> None (never another project's plans)")

    write_yaml(reg, "version: 1\nprojects:\n"
                    f"  - path: {repo}\n    name: proj1\n    area: area1\n    enabled: false\n")
    check(mod.portfolio_plans_dir(repo) is None, "registered but disabled -> None")
    write_yaml(reg, "version: 1\nprojects:\n"
                    f"  - path: {repo}\n    name: proj1\n    area: area1\n    enabled: true\n")

    write_yaml(cfg, f"version: 1\nvault_dir: {tmp / 'no-such-vault'}\n")
    check(mod.portfolio_plans_dir(repo) is None, "vault_dir pointing nowhere -> None")

    unreadable = tmp / "locked"
    (unreadable / "Portfolio" / "area1" / "proj1" / "plans").mkdir(parents=True)
    os.chmod(unreadable, 0o000)
    try:
        write_yaml(cfg, f"version: 1\nvault_dir: {unreadable}\n")
        check(mod.portfolio_plans_dir(repo) is None, "unreadable vault path -> None, no raise")
    finally:
        os.chmod(unreadable, 0o700)
    write_yaml(cfg, f"version: 1\nvault_dir: {vault}\n")

    write_yaml(cfg, "version: 1\nvault_dir: [this, is, not, a, string]\n")
    check(mod.portfolio_plans_dir(repo) is None, "non-string vault_dir -> None")
    write_yaml(cfg, "vault_dir: {{{ not valid yaml\n")
    check(mod.portfolio_plans_dir(repo) is None, "malformed YAML -> None")
    write_yaml(cfg, f"version: 1\nvault_dir: {vault}\n")
    write_yaml(reg, "version: 1\nprojects: not-a-list\n")
    check(mod.portfolio_plans_dir(repo) is None, "registry `projects` not a list -> None")
    write_yaml(reg, "version: 1\nprojects:\n"
                    f"  - path: {repo}\n    name: proj1\n    area: area1\n    enabled: true\n")

    # `yaml` absent entirely: sys.modules[name] = None makes `import yaml` raise
    # ImportError, which is what a machine without PyYAML actually presents.
    saved = sys.modules.get("yaml", "__absent__")
    sys.modules["yaml"] = None
    try:
        check(mod.portfolio_plans_dir(repo) is None, "yaml not importable -> None, no raise")
    finally:
        if saved == "__absent__":
            sys.modules.pop("yaml", None)
        else:
            sys.modules["yaml"] = saved

    check(mod.portfolio_plans_dir(repo) == plans, "resolution recovers once yaml is back")
    shutil.rmtree(tmp, ignore_errors=True)


def case_resolver_never_breaks_the_bar():
    """The state-file bar must still render when discovery is unavailable.

    Subprocess-level, with HOME pointed at a directory holding neither config
    nor registry -- the shape of a machine that never ran `portfolio scan`.
    """
    print("Task 2.1 — a broken portfolio does not break the existing bar:")
    tmp = Path(tempfile.mkdtemp(prefix="pp-nohome-"))
    repo = tmp / "repo"
    (repo / "plans").mkdir(parents=True)
    plan = repo / "plans" / "demo-plan.md"
    plan.write_text(PLAN)
    write_state(repo, plan=str(plan), phase="task", stage=2, task="2.2",
                task_desc="render output")
    env = dict(os.environ, HOME=str(tmp / "empty-home"))
    (tmp / "empty-home").mkdir()
    r = subprocess.run([sys.executable, str(SCRIPT)],
                       input=json.dumps({"cwd": str(repo)}),
                       capture_output=True, text=True, env=env)
    out = ANSI_RE.sub("", r.stdout)
    check(r.returncode == 0, "rc 0 with no portfolio config on the machine")
    check(r.stderr == "", "stderr stays clean")
    check("3/5" in out, "the state-file bar still renders")
    shutil.rmtree(tmp, ignore_errors=True)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="plan-progress-test-"))
    repo = tmp / "repo"
    (repo / "sub" / "dir").mkdir(parents=True)
    plan = repo / "plans" / "demo-plan.md"
    plan.parent.mkdir()
    plan.write_text(PLAN)

    print("no state file → silence:")
    r, out = run(repo)
    check(r.returncode == 0 and out.strip() == "" and r.stderr == "", "empty output, rc 0")

    print("task phase:")
    write_state(repo, plan=str(plan), phase="task", stage=2, task="2.2",
                task_desc="render output")
    r, out = run(repo)
    check("3/5" in out, "status counts 3/5")
    check("(60%)" in out, "percentage")
    check(out.count("█") == 12 and out.count("░") == 8, "bar fill 12/20")
    check("S2/2" in out, "stage position")
    check("▶ T2.2 render output" in out, "current task marker")
    check("⚙ demo" in out, "plan name stripped of -plan.md")
    check("stale" not in out, "fresh state not marked stale")

    print("walk-up discovery from subdirectory:")
    r, out = run(repo / "sub" / "dir")
    check("3/5" in out, "state found from nested cwd")

    print("BL-001 partial `[~]` state:")
    ppartial = repo / "plans" / "partial-plan.md"
    ppartial.write_text(PARTIAL_PLAN)
    write_state(repo, plan=str(ppartial), phase="task", stage=1, task="1.2",
                task_desc="in flight")
    r, out = run(repo)
    check("1/3" in out, "partial counted in total, not in done (1/3)")
    check("2/3" not in out, "partial NOT counted as done (would be 2/3)")
    check("(33%)" in out, "percentage reflects partial as unfinished")

    print("gate phase:")
    write_state(repo, plan=str(plan), phase="gate", stage=2)
    r, out = run(repo)
    check("◆ S2 gate" in out, "gate glyph")
    check("↻" not in out, "no remediation marker on a gate's first round")

    print("gate remediation round (optional schema field):")
    write_state(repo, plan=str(plan), phase="gate", stage=2, remediation_round=2)
    _, out = run(repo)
    check("↻2/2" in out, "remediation round rendered against the default budget of 2")
    write_state(repo, plan=str(plan), phase="gate", stage=2,
                remediation_round=3, remediation_budget=4)
    _, out = run(repo)
    check("↻3/4" in out, "plan-overridden budget changes the denominator")
    # Garbage must degrade to the plain gate label, never a traceback: the renderer
    # runs inside the user's statusline, where a crash is worse than a missing field.
    for bad in ("two", 0, -1, None, True, {"a": 1}):
        write_state(repo, plan=str(plan), phase="gate", stage=2, remediation_round=bad)
        proc, out = run(repo)
        check(proc.returncode == 0 and "◆ S2 gate" in out and "↻" not in out,
              f"non-positive-int remediation_round ({bad!r}) ignored, no crash")
    # A malformed budget alongside a VALID round must fall back, not crash or vanish.
    for bad_budget in ("four", 0, -1, None, True):
        write_state(repo, plan=str(plan), phase="gate", stage=2,
                    remediation_round=1, remediation_budget=bad_budget)
        proc, out = run(repo)
        check(proc.returncode == 0 and "↻1/2" in out,
              f"malformed remediation_budget ({bad_budget!r}) falls back to default 2")

    print("preflight / closeout / blocked phases:")
    write_state(repo, plan=str(plan), phase="preflight")
    _, out = run(repo)
    check("⚑ preflight" in out, "preflight glyph")
    write_state(repo, plan=str(plan), phase="closeout")
    _, out = run(repo)
    check("✔ close-out" in out, "close-out glyph")
    write_state(repo, plan=str(plan), phase="blocked", stage=2, task="2.2",
                note="cycle budget exhausted")
    _, out = run(repo)
    check("✘ blocked" in out and "cycle budget exhausted" in out, "blocked glyph + note")

    print("staleness:")
    write_state(repo, plan=str(plan), phase="task", stage=2, task="2.2")
    state_file = repo / ".claude" / "plan-progress.json"
    st = json.loads(state_file.read_text())
    st["updated"] = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    state_file.write_text(json.dumps(st))
    _, out = run(repo)
    check("(stale 30h)" in out, "old state marked stale")

    print("relative plan path resolves against repo root:")
    write_state(repo, plan="plans/demo-plan.md", phase="task", stage=1, task="1.1")
    _, out = run(repo)
    check("3/5" in out, "relative plan path")

    print("degrade to silence, never a traceback:")
    write_state(repo, plan=str(repo / "plans" / "gone-plan.md"), phase="task")
    r, out = run(repo)
    check(r.returncode == 0 and out.strip() == "" and r.stderr == "", "missing plan → silence")
    state_file.write_text("{not json")
    r, out = run(repo)
    check(r.returncode == 0 and out.strip() == "" and r.stderr == "", "corrupt state → silence")
    r, out = run(repo, extra_stdin="")
    check(r.returncode == 0 and r.stderr == "", "empty stdin → rc 0, no traceback")

    print()
    case_portfolio_resolver()
    case_resolver_never_breaks_the_bar()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} failure(s):")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
