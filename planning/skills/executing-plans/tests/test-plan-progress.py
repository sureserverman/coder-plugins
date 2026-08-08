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
import inspect
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


def case_eligibility_filter():
    """Task 2.2 — eligible = started AND not closed out."""
    print("Task 2.2 — started-but-unfinished eligibility:")
    mod = load_module()

    started = "### Task 1.1: a\n- **Status:** [x]\n\n### Task 1.2: b\n- **Status:** [ ]\n"
    check(mod.plan_is_eligible(started), "started and open -> eligible")

    only_partial = "### Task 1.1: a\n- **Status:** [~]\n\n### Task 1.2: b\n- **Status:** [ ]\n"
    check(mod.plan_is_eligible(only_partial),
          "a plan whose ONLY progress is `[~]` counts as started")

    never = "### Task 1.1: a\n- **Status:** [ ]\n\n### Task 1.2: b\n- **Status:** [ ]\n"
    check(not mod.plan_is_eligible(never), "authored but never started -> ineligible")

    check(not mod.plan_is_eligible(started + "\n**Completed:** 2026-08-01 — commits: abc123\n"),
          "carries **Completed:** -> ineligible")
    check(not mod.plan_is_eligible(started + "\n**Abandoned:** 2026-08-01 — superseded\n"),
          "carries **Abandoned:** -> ineligible")

    check(not mod.plan_is_eligible("# Design: a thing\n\nSome prose, no Status fields.\n"),
          "no Status fields at all (legacy / *-design.md) -> ineligible")
    check(not mod.plan_is_eligible(""), "empty document -> ineligible")

    # A Status line outside a task heading is not a task status.
    check(not mod.plan_is_eligible("- **Status:** [x]\n"),
          "a bare Status line with no Task heading above it does not start a plan")

    # The prose hint must NOT suppress: only the structured marker is
    # authoritative (plan-status contract -- a heuristic false positive hides
    # live work, which is BL-001 inverted and silent).
    check(mod.plan_is_eligible("OBSOLETE — DO NOT IMPLEMENT\n\n" + started),
          "banner prose alone does NOT suppress; only the **Abandoned:** marker does")

    # The plan-status contract is owned in exactly one place. Assert that
    # structurally: the renderer must reach through `pu`, not carry its own copy.
    check(hasattr(mod.pu, "COMPLETED_RE"), "portfolio-unify owns COMPLETED_RE")
    check(not hasattr(mod, "COMPLETED_RE"),
          "the renderer does NOT define its own COMPLETED_RE")
    check(not hasattr(mod, "ABANDONED_RE") and not hasattr(mod, "STATUS_RE"),
          "nor its own ABANDONED_RE / STATUS_RE")


def case_ordering_and_cap():
    """Task 2.3 — newest-first by FILENAME date stamp, capped at 3."""
    print("Task 2.3 — ordering by filename date stamp, capped at 3:")
    mod = load_module()
    tmp = Path(tempfile.mkdtemp(prefix="pp-order-"))
    plans = tmp / "plans"
    plans.mkdir()
    started = "### Task 1.1: a\n- **Status:** [x]\n\n### Task 1.2: b\n- **Status:** [ ]\n"

    names = ["2026-01-01-oldest-plan.md", "2026-03-15-third-plan.md",
             "2026-05-20-second-plan.md", "2026-07-04-newest-plan.md",
             "2026-02-10-fourth-plan.md"]
    for n in names:
        (plans / n).write_text(started)

    got = mod.discover_plans(plans)
    check(len(got) == 3, f"exactly 3 of 5 eligible are returned (got {len(got)})")
    check([p.name for p in got] == ["2026-07-04-newest-plan.md",
                                    "2026-05-20-second-plan.md",
                                    "2026-03-15-third-plan.md"],
          f"newest first by date stamp (got {[p.name for p in got]})")

    # mtime must be irrelevant: make the OLDEST file the most recently touched.
    os.utime(plans / "2026-01-01-oldest-plan.md", (2**31 - 1, 2**31 - 1))
    got2 = mod.discover_plans(plans)
    check([p.name for p in got2] == [p.name for p in got],
          "touching the oldest plan does not reorder anything (mtime is not consulted)")

    print("  the state-file plan is always included:")
    pinned = plans / "2026-01-01-oldest-plan.md"   # would rank 5th
    got3 = mod.discover_plans(plans, pinned=pinned)
    check(len(got3) == 3, "still capped at 3 with a pinned plan")
    check(pinned.resolve() in [p.resolve() for p in got3],
          "the pinned plan is present even though its stamp ranks it last")
    check(got3[-1].name == "2026-01-01-oldest-plan.md",
          "and it sorts into its correct rank position, not to the front")

    # A pinned plan that is INELIGIBLE (never started) must still render: the
    # single-plan behavior predates eligibility and must not regress.
    never = plans / "2026-08-01-never-started-plan.md"
    never.write_text("### Task 1.1: a\n- **Status:** [ ]\n")
    check(not mod.plan_is_eligible(never.read_text()), "precondition: it is ineligible")
    got4 = mod.discover_plans(plans, pinned=never)
    check(never.resolve() in [p.resolve() for p in got4],
          "an ineligible pinned plan still renders (0/13 mid-execution case)")
    check(never.resolve() not in [p.resolve() for p in mod.discover_plans(plans)],
          "but it is NOT picked up when it is not the pinned plan")

    print("  unstamped and adversarial filenames:")
    for n in ("no-stamp-plan.md", "2026-13-99-bad-date-plan.md"):
        (plans / n).write_text(started)
    got5 = mod.discover_plans(plans)
    check(len(got5) == 3 and all(date_stamped(p) for p in got5),
          "unstamped names sort last and do not displace real stamps")

    same = tmp / "sameday"
    same.mkdir()
    for n in ("2026-06-01-b-plan.md", "2026-06-01-a-plan.md", "2026-06-01-c-plan.md"):
        (same / n).write_text(started)
    order1 = [p.name for p in mod.discover_plans(same)]
    order2 = [p.name for p in mod.discover_plans(same)]
    check(order1 == order2, "same-day plans have a stable, reproducible order")

    print("  degradation:")
    check(mod.discover_plans(None) == [], "None plans_dir -> []")
    check(mod.discover_plans(tmp / "does-not-exist") == [], "missing plans dir -> []")
    got6 = mod.discover_plans(plans, pinned=plans / "gone.md")
    check(all(p.name != "gone.md" for p in got6), "a vanished pinned plan is simply absent")

    unreadable = tmp / "locked-plans"
    unreadable.mkdir()
    (unreadable / "2026-07-01-x-plan.md").write_text(started)
    os.chmod(unreadable, 0o000)
    try:
        check(mod.discover_plans(unreadable) == [], "unreadable plans dir -> [], no raise")
    finally:
        os.chmod(unreadable, 0o700)

    shutil.rmtree(tmp, ignore_errors=True)


def case_scan_cache():
    """Task 2.4 — the scan is cached, and invalidated by what actually changes.

    Every "was the cache used?" assertion counts real plan-file READS rather
    than measuring elapsed time. A timing assertion passes on a fast machine
    whether or not the cache works, which is the test-that-cannot-fail shape
    this plan keeps producing.
    """
    print("Task 2.4 — scan cache:")
    mod = load_module()
    tmp = Path(tempfile.mkdtemp(prefix="pp-cache-"))
    plans = tmp / "plans"
    plans.mkdir()
    cache = tmp / ".claude" / "plan-progress-cache.json"
    started = "### Task 1.1: a\n- **Status:** [x]\n\n### Task 1.2: b\n- **Status:** [ ]\n"
    for i in range(5):
        (plans / f"2026-0{i+1}-01-p{i}-plan.md").write_text(started)

    mod.PLAN_READS = 0
    first = [p.name for p in mod.discover_plans(plans, cache_file=cache)]
    reads_cold = mod.PLAN_READS
    check(reads_cold == 5, f"cold scan reads every plan file (got {reads_cold})")
    check(cache.is_file(), "the cache file is written")

    mod.PLAN_READS = 0
    second = [p.name for p in mod.discover_plans(plans, cache_file=cache)]
    check(mod.PLAN_READS == 0,
          f"a second scan with nothing changed reads ZERO plan files (got {mod.PLAN_READS})")
    check(second == first, "and returns the same result")

    print("  invalidation:")
    # The case directory mtime CANNOT catch: same size, same entry count.
    # `- **Status:** [ ]` -> `- **Status:** [x]` is a byte-for-byte-length edit.
    target = plans / "2026-01-01-p0-plan.md"
    before_size = target.stat().st_size
    target.write_text(started.replace("- **Status:** [x]", "- **Status:** [~]"))
    check(target.stat().st_size == before_size,
          "precondition: the edit changed no byte count (size cannot detect it)")
    mod.PLAN_READS = 0
    mod.discover_plans(plans, cache_file=cache)
    check(mod.PLAN_READS > 0,
          f"a same-size content edit invalidates the cache (reads={mod.PLAN_READS})")

    mod.PLAN_READS = 0
    mod.discover_plans(plans, cache_file=cache)
    check(mod.PLAN_READS == 0, "and the rebuilt cache is used on the next call")

    (plans / "2026-09-09-added-plan.md").write_text(started)
    mod.PLAN_READS = 0
    mod.discover_plans(plans, cache_file=cache)
    check(mod.PLAN_READS > 0, "adding a plan invalidates the cache")

    mod.PLAN_READS = 0
    mod.discover_plans(plans, cache_file=cache)
    (plans / "2026-09-09-added-plan.md").unlink()
    mod.PLAN_READS = 0
    mod.discover_plans(plans, cache_file=cache)
    check(mod.PLAN_READS > 0, "removing a plan invalidates the cache")

    print("  a broken cache is discarded, never raised on:")
    for label, blob in [("truncated JSON", '{"version": 1, "signa'),
                        ("not JSON at all", "\x00\x01 binary junk"),
                        ("valid JSON, wrong type", "[1, 2, 3]"),
                        ("valid dict, junk fields", '{"signature": "nope", "eligible": 7}')]:
        cache.write_text(blob, encoding="utf-8", errors="ignore")
        mod.PLAN_READS = 0
        got = mod.discover_plans(plans, cache_file=cache)
        check(len(got) > 0 and mod.PLAN_READS > 0,
              f"{label}: discarded and rebuilt from a real scan")

    # A cache belonging to a DIFFERENT plans directory must not be honoured.
    #
    # `other` is built as a byte-for-byte SIGNATURE TWIN of `plans`: same
    # filenames, same sizes, same mtimes. That is the whole point. An earlier
    # version used one differently-named file, so the signatures could never
    # match and the rebuild was forced by the signature check alone — the
    # assertion passed identically with the plans_dir comparison deleted, and
    # so proved nothing about the key it names. With a twin, only the
    # plans_dir field can tell the two directories apart.
    other = tmp / "other-plans"
    other.mkdir()
    for src in sorted(plans.glob("*.md")):
        twin = other / src.name
        twin.write_bytes(src.read_bytes())
        st = src.stat()
        os.utime(twin, ns=(st.st_mtime_ns, st.st_mtime_ns))
    check(mod.scan_signature(other) == mod.scan_signature(plans),
          "the twin directory really does produce an identical signature")

    mod.discover_plans(plans, cache_file=cache)      # cache now describes `plans`
    mod.PLAN_READS = 0
    got = mod.discover_plans(other, cache_file=cache)
    check(mod.PLAN_READS > 0,
          "a cache written for another directory is not reused (plans_dir key, "
          "not the signature, is what rejects it)")
    check(all(p.parent == other for p in got),
          "and the rebuilt result names files in the directory actually asked for")

    print("  an unwritable cache degrades to no caching, not to a failure:")
    ro = tmp / "ro"
    ro.mkdir()
    os.chmod(ro, 0o500)
    try:
        got = mod.discover_plans(plans, cache_file=ro / "sub" / "c.json")
        check(len(got) == 3, "discovery still returns results with an unwritable cache path")
    finally:
        os.chmod(ro, 0o700)

    # `is not None` was the old assertion here and could not fail: every path
    # through discover_plans returns a list. Assert the caching is actually OFF.
    mod.PLAN_READS = 0
    got = mod.discover_plans(plans, cache_file=None)
    check(len(got) == 3 and mod.PLAN_READS > 0,
          f"cache_file=None disables caching — every call rescans "
          f"(reads={mod.PLAN_READS}, got {len(got)})")

    print("  a poisoned cache cannot name a file outside the plans directory:")
    # The cache is trusted to skip reads, so nothing downstream re-validates
    # what it names, and `plans_dir / "/etc/passwd"` discards plans_dir entirely.
    sig = mod.scan_signature(plans)
    cache.parent.mkdir(parents=True, exist_ok=True)
    for label, planted in (("absolute path", "/etc/passwd"),
                           ("parent traversal", "../../../etc/passwd"),
                           ("nested separator", "sub/evil.md")):
        cache.write_text(json.dumps({"version": 1, "plans_dir": str(plans),
                                     "signature": sig, "eligible": [planted]}),
                         encoding="utf-8")
        got = mod.discover_plans(plans, cache_file=cache)
        escaped = [p for p in got if p.parent != plans]
        check(not escaped, f"{label}: rejected, not joined ({escaped})")

    shutil.rmtree(tmp, ignore_errors=True)


def case_degrades_without_raising():
    """Round-1 gate remediation — failures the corpus sweep's new discovery lane
    exposed, each of which used to escape as a traceback.

    These are regressions for real bugs, not hypotheticals: every one was
    reproduced before it was fixed.
    """
    print("gate remediation — the surface degrades internally, not via a catch-all:")
    mod = load_module()
    tmp = Path(tempfile.mkdtemp(prefix="pp-degrade-"))
    plans = tmp / "plans"
    plans.mkdir()
    started = "### Task 1.1: a\n- **Status:** [x]\n\n### Task 1.2: b\n- **Status:** [ ]\n"
    pinned = plans / "2026-01-01-x-plan.md"
    pinned.write_text(started)

    # pathlib's is_file() swallows ENOENT/ENOTDIR/ELOOP but NOT EACCES, so the
    # pinned plan inside an unreadable directory raised PermissionError out of
    # discover_plans on every redraw.
    os.chmod(plans, 0o000)
    try:
        got = mod.discover_plans(plans, pinned=pinned)
        check(got == [], "an unreadable plans dir with a pinned plan returns [], never raises")
    except Exception as e:                                  # noqa: BLE001
        check(False, f"unreadable plans dir raised {type(e).__name__}: {e}")
    finally:
        os.chmod(plans, 0o755)

    # Path.home() raises RuntimeError with HOME unset and no passwd entry, and
    # it runs at MODULE SCOPE — before main()'s try/except exists.
    src = SCRIPT.read_text(encoding="utf-8")
    check("Path.home() /" not in src and "_home()" in src,
          "module-scope config paths go through the guarded _home() helper")
    probe = (
        "import pwd, os, importlib.util\n"
        "pwd.getpwuid = lambda uid: (_ for _ in ()).throw(KeyError('no passwd entry'))\n"
        "spec = importlib.util.spec_from_file_location('pp', %r)\n"
        "m = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(m)\n"
        "print('IMPORTED')\n" % str(SCRIPT))
    env = {k: v for k, v in os.environ.items() if k != "HOME"}
    r = subprocess.run([sys.executable, "-c", probe],
                       capture_output=True, text=True, env=env)
    check(r.returncode == 0 and "IMPORTED" in r.stdout,
          f"importing with no HOME and no passwd entry does not raise "
          f"(exit {r.returncode}, stderr: {r.stderr.strip()[-120:]})")

    shutil.rmtree(tmp, ignore_errors=True)


# Captured by RUNNING the renderer at acbf3ae — the last commit before Task 3.1
# touched it — against the fixture built in case_render_returns_lines below.
# Provenance is the whole point: a golden captured from the code it is meant to
# pin proves only that the code equals itself. This one was taken from the
# earlier implementation, so it can fail.
GOLDEN_SINGLE_PLAN = (
    "\x1b[38;2;46;149;153m⚙ 2026-08-06-demo\x1b[0m "
    "\x1b[2m▐\x1b[0m\x1b[38;2;0;160;0m██████████\x1b[0m"
    "\x1b[2m░░░░░░░░░░▌\x1b[0m 2/4 \x1b[2m(50%)\x1b[0m \x1b[2m·\x1b[0m S2/2 "
    "\x1b[38;2;0;160;0m▶ T2.1 \x1b[0mz"
)

GOLDEN_PLAN_BODY = """# Plan: demo

## Stage 1 — a
### Task 1.1: x
- **Status:** [x]
### Task 1.2: y
- **Status:** [x]

## Stage 2 — b
### Task 2.1: z
- **Status:** [~]
### Task 2.2: w
- **Status:** [ ]
"""


def case_render_returns_lines():
    """Task 3.1 — render() returns a LIST, main() prints one element per line,
    and the single-plan case is byte-identical to the pre-change output."""
    print("Task 3.1 — render() returns a list of lines:")
    mod = load_module()
    tmp = Path(tempfile.mkdtemp(prefix="pp-lines-"))
    repo = tmp / "repo"
    (repo / ".claude").mkdir(parents=True)
    plans = tmp / "plans"
    plans.mkdir()
    plan = plans / "2026-08-06-demo-plan.md"
    plan.write_text(GOLDEN_PLAN_BODY)
    (repo / ".claude" / "plan-progress.json").write_text(json.dumps({
        "plan": str(plan), "phase": "task", "stage": 2, "task": "2.1",
        "task_desc": "z", "remediation_round": 0,
        "updated": datetime.now(timezone.utc).isoformat()}))

    lines = mod.render(str(repo))
    check(isinstance(lines, list), f"render() returns a list (got {type(lines).__name__})")
    check(len(lines) == 1, f"one in-flight plan -> one line (got {len(lines)})")
    check(lines and lines[0] == GOLDEN_SINGLE_PLAN,
          "the single-plan line is BYTE-IDENTICAL to the pre-Task-3.1 renderer")
    if lines and lines[0] != GOLDEN_SINGLE_PLAN:
        print(f"      got:    {lines[0]!r}")
        print(f"      golden: {GOLDEN_SINGLE_PLAN!r}")

    # And the golden can actually fail: perturbing the plan must move it.
    plan.write_text(GOLDEN_PLAN_BODY.replace("- **Status:** [~]", "- **Status:** [x]"))
    check(mod.render(str(repo))[0] != GOLDEN_SINGLE_PLAN,
          "the golden is sensitive — a Status flip changes it (it is not a tautology)")
    plan.write_text(GOLDEN_PLAN_BODY)

    r, plain = run(repo)
    check(r.returncode == 0 and plain.count("\n") == 1,
          f"main() prints one line per element (got {plain.count(chr(10))} newlines)")

    print("  multiple discovered plans stack, one line each:")
    for n in ("2026-07-01-older-plan.md", "2026-06-01-oldest-plan.md"):
        (plans / n).write_text(GOLDEN_PLAN_BODY)
    # point the resolver at this fixture's plans dir
    cfg, reg = tmp / "cfg.yaml", tmp / "reg.yaml"
    mod.CONFIG_PATH, mod.REGISTRY_PATH = cfg, reg
    write_yaml(cfg, f"version: 1\nvault_dir: {tmp / 'vault'}\n")
    vplans = tmp / "vault" / "Portfolio" / "a" / "p" / "plans"
    vplans.mkdir(parents=True)
    for src in plans.glob("*.md"):
        (vplans / src.name).write_text(src.read_text())
    write_yaml(reg, "version: 1\nprojects:\n"
                    f"  - path: {repo}\n    name: p\n    area: a\n    enabled: true\n")
    lines = mod.render(str(repo))
    check(len(lines) == 3, f"pinned + 2 discovered = 3 lines (got {len(lines)})")
    check(lines[0] == GOLDEN_SINGLE_PLAN,
          "the pinned plan is still first and still byte-identical")
    check(all("\n" not in ln for ln in lines), "no element contains an embedded newline")

    print("  a RELATIVE pinned path is still recognised as itself:")
    # The Tier-1 Critical. A relative `plan` is documented and supported, and
    # `docs/plans` is where one naturally points -- the same directory discovery
    # then scans. Both the relative path and discovery were tested, but never
    # together, and apart they each pass. The pinned plan failed to match itself
    # and rendered twice: once with its phase part, once as a stranger.
    rel = Path(tempfile.mkdtemp(prefix="pp-rel-"))
    relrepo = rel / "repo"
    (relrepo / ".claude").mkdir(parents=True)
    (relrepo / "docs" / "plans").mkdir(parents=True)
    (relrepo / "docs" / "plans" / "2026-08-06-demo-plan.md").write_text(GOLDEN_PLAN_BODY)
    (relrepo / "docs" / "plans" / "2026-01-01-other-plan.md").write_text(GOLDEN_PLAN_BODY)
    (relrepo / ".claude" / "plan-progress.json").write_text(json.dumps({
        "plan": "docs/plans/2026-08-06-demo-plan.md",      # relative, on purpose
        "phase": "task", "stage": 1, "task": "1.1",
        "updated": datetime.now(timezone.utc).isoformat()}))
    relcfg = rel / "cfg.yaml"
    write_yaml(relcfg, "version: 1\n")     # intact, no vault_dir -> docs/plans fallback
    mod.CONFIG_PATH = relcfg
    rlines = mod.render(str(relrepo))
    stems = [ANSI_RE.sub("", ln).split()[1] for ln in rlines]
    check(len(stems) == len(set(stems)),
          f"the pinned plan appears exactly once, not once per resolution form ({stems})")
    check(len(rlines) == 2, f"pinned + 1 other = 2 lines, no duplicate slot burned "
                            f"(got {len(rlines)})")
    shutil.rmtree(rel, ignore_errors=True)

    shutil.rmtree(tmp, ignore_errors=True)


def case_ordering_ignores_mtime():
    """Stage 2 gate check 4 — the mechanism the amended check actually names.

    The check was amended to promise a dynamic assertion "over date_stamp and
    _rank via inspect.getsource". It was never implemented, while the check sat
    marked [x]. This is that assertion. It is scoped to the two ordering
    functions on purpose: the earlier whole-file grep would have banned mtime
    for cache invalidation, a different and necessary use.
    """
    print("Stage 2 gate check 4 — the ordering path consults no stat field:")
    mod = load_module()
    for fn in (mod.date_stamp, mod._rank):
        body = inspect.getsource(fn)
        for field in ("st_mtime", "st_ctime", "st_atime", "getmtime", ".stat("):
            check(field not in body,
                  f"{fn.__name__}() does not reference {field}")


def case_render_budget():
    """Task 2.4 — a 40-plan directory renders inside the 150ms budget.

    End-to-end subprocess, because that is what a statusline redraw actually
    pays: python startup plus the portfolio-unify import dominate, and both are
    invisible to an in-process measurement.

    Asserts the MEDIAN of 20 runs, not the max. A single outlier on a loaded CI
    box says nothing about the code, and a max-based assertion would make this
    the flakiest check in the suite. Measured headroom on the development
    machine is ~4.5x, so the median has room to be meaningful rather than
    merely permissive.
    """
    print("Task 2.4 — render budget (40 plans, 20 runs, median):")
    tmp = Path(tempfile.mkdtemp(prefix="pp-budget-"))
    repo = tmp / "repo"
    plans = repo / "docs" / "plans"
    plans.mkdir(parents=True)
    body = ("\n".join(f"### Task {i//3+1}.{i%3+1}: item {i}\n"
                      f"- **Status:** [{'x' if i % 2 else ' '}]\n" for i in range(40))
            + "\nfiller prose line\n" * 400)
    for i in range(40):
        (plans / f"2026-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}-fixture-{i}-plan.md").write_text(body)

    pinned = plans / "2026-01-01-fixture-0-plan.md"
    write_state(repo, plan=str(pinned), phase="task", stage=1, task="1.1", task_desc="x")

    # An intact config naming no vault_dir routes the resolver to <repo>/docs/plans.
    home = tmp / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / "portfolio-config.yaml").write_text("version: 1\n")
    env = dict(os.environ, HOME=str(home))

    # Written when main() did NOT yet reach discover_plans: timing the plain
    # subprocess would have measured the single-plan path while claiming to
    # measure discovery, so this driver runs the full resolve -> discover (with
    # cache) -> render path explicitly. Task 3.1 has since wired that path into
    # main(), and the explicit driver still earns its place: it asserts
    # DISCOVERED=3, so the measurement provably exercised the code it budgets
    # rather than whatever main() happened to do that day.
    driver = tmp / "driver.py"
    driver.write_text(f'''
import importlib.util, json, pathlib, sys
spec = importlib.util.spec_from_file_location("pp", {str(SCRIPT)!r})
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
state_file = m.find_state({str(repo)!r})
root = m.repo_root_of(state_file)
d = m.portfolio_plans_dir(root)
state = json.loads(state_file.read_text())
found = m.discover_plans(d, pinned=pathlib.Path(state["plan"]),
                         cache_file=root / ".claude" / m.CACHE_NAME)
sys.stdout.write("\\n".join(m.render(str(root))) + "\\n")
sys.stderr.write("DISCOVERED=%d\\n" % len(found))
''')

    import time
    samples = []
    for _ in range(20):
        t0 = time.perf_counter()
        r = subprocess.run([sys.executable, str(driver)],
                           capture_output=True, text=True, env=env)
        samples.append((time.perf_counter() - t0) * 1000)
    samples.sort()
    median = samples[len(samples) // 2]
    check(r.returncode == 0, f"the full discover+render path exits 0 (stderr={r.stderr[:200]!r})")
    check("DISCOVERED=3" in r.stderr,
          f"discovery actually ran and capped at 3 (stderr={r.stderr.strip()!r})")
    check(median < 150,
          f"median discover+render {median:.0f}ms < 150ms budget "
          f"(min {samples[0]:.0f}ms, max {samples[-1]:.0f}ms)")
    shutil.rmtree(tmp, ignore_errors=True)


def date_stamped(p):
    return re.match(r"^\d{4}-\d{2}-\d{2}", p.name) is not None


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
    case_eligibility_filter()
    case_ordering_and_cap()
    case_scan_cache()
    case_render_budget()
    case_degrades_without_raising()
    case_ordering_ignores_mtime()
    case_render_returns_lines()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} failure(s):")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
