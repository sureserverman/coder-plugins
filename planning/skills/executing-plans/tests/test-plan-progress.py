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

    print("  a change to the ELIGIBILITY RULE invalidates the cache:")
    # The axis the directory signature structurally cannot see, and the one that
    # actually bit: when plan_is_eligible changed to make masters countable
    # (BL-054), every cache on disk kept serving the OLD rule's verdicts against
    # a directory whose signature was still valid -- so the masters stayed
    # invisible and Task 3.2's tree glyphs had nothing to render. Measured on
    # this machine right after that commit: 3 of 4 real caches were serving
    # pre-change verdicts, with the whole suite green.
    mod.PLAN_READS = 0
    mod.discover_plans(plans, cache_file=cache)
    check(mod.PLAN_READS == 0, "precondition: warm cache, nothing on disk changed")
    stale = json.loads(cache.read_text())
    check(stale.get("rule") is not None,
          "the cache records the rule that produced its verdicts")
    check(stale.get("version") == mod.CACHE_VERSION,
          f"and a format version (got {stale.get('version')!r})")
    stale["rule"] = [["plan-progress.py", 1, 1], ["portfolio-unify.py", 1, 1]]
    cache.write_text(json.dumps(stale))
    mod.PLAN_READS = 0
    mod.discover_plans(plans, cache_file=cache)
    check(mod.PLAN_READS > 0,
          f"a cache written by DIFFERENT rule code is discarded (reads={mod.PLAN_READS})")

    # A v1 cache is every cache that exists in the wild today.
    old = json.loads(cache.read_text())
    old["version"] = 1
    old.pop("rule", None)
    cache.write_text(json.dumps(old))
    mod.PLAN_READS = 0
    mod.discover_plans(plans, cache_file=cache)
    check(mod.PLAN_READS > 0,
          f"a pre-existing v1 cache is discarded, not misread (reads={mod.PLAN_READS})")

    # ...and the VERSION check in isolation. Tier-2 reproduced that the case
    # above cannot fail on it: that fixture breaks BOTH `version` and `rule`, so
    # the (separately tested) rule mismatch rejects it whether or not the version
    # line exists — deleting `cached.get("version") == CACHE_VERSION` left the
    # whole case green. The comment in the source claims the field is "checked
    # now, so a future format change invalidates rather than misreads"; this is
    # what makes that claim true. Everything else here is deliberately VALID.
    mod.PLAN_READS = 0
    mod.discover_plans(plans, cache_file=cache)          # rebuild a good cache
    good = json.loads(cache.read_text())
    check(good.get("rule") == mod.rule_signature() and good.get("version") == mod.CACHE_VERSION,
          "precondition: the rebuilt cache is valid in every field")
    good["version"] = mod.CACHE_VERSION + 1              # ONLY the version differs
    cache.write_text(json.dumps(good))
    mod.PLAN_READS = 0
    mod.discover_plans(plans, cache_file=cache)
    check(mod.PLAN_READS > 0,
          f"a cache whose ONLY defect is its version is discarded "
          f"(reads={mod.PLAN_READS})")

    print("  ...and rule_signature() reacts to a REAL edit of the rule's source:")
    # Review finding: everything above substitutes a rule VALUE by hand, which
    # proves the key is compared but not that it tracks anything. Confirmed by
    # the reviewer: replacing rule_signature with `lambda: ["constant"]` — i.e.
    # reintroducing the exact BL-054 staleness this fix exists to close, one
    # layer up — left the whole suite green. So drive the real function against
    # real files it is pointed at.
    srcdir = tmp / "src"
    srcdir.mkdir()
    copies = []
    for real in (Path(mod.__file__), Path(mod._UNIFY)):
        dst = srcdir / real.name
        dst.write_bytes(real.read_bytes())
        copies.append(dst)
    real_file, real_unify = mod.__file__, mod._UNIFY
    try:
        mod.__file__, mod._UNIFY = str(copies[0]), copies[1]
        before = mod.rule_signature()
        check(before is not None and len(before) == 2,
              f"rule_signature() reads the two files it is pointed at ({before})")

        # Timestamp-only change: content is the rule, so this must NOT invalidate.
        os.utime(copies[0], ns=(10 ** 18, 10 ** 18))
        check(mod.rule_signature() == before,
              "an mtime-only touch does NOT change it (the key is content, not stat)")

        # A real edit to the eligibility rule must.
        copies[0].write_bytes(copies[0].read_bytes() + b"\n# a real edit\n")
        after_a = mod.rule_signature()
        check(after_a != before, "editing plan-progress.py changes the rule signature")

        # ...and so must one to the contract file the rule imports from.
        copies[1].write_bytes(copies[1].read_bytes() + b"\n# a real edit\n")
        check(mod.rule_signature() not in (before, after_a),
              "editing portfolio-unify.py changes it too — both files are the rule")

        # A source file that vanishes must decline the cache, not raise.
        copies[0].unlink()
        try:
            gone = mod.rule_signature()
        except Exception as e:
            gone = f"RAISED {type(e).__name__}: {e}"
        check(gone is None, f"an unreadable rule source returns None, never raises ({gone})")
    finally:
        mod.__file__, mod._UNIFY = real_file, real_unify

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
    # This test was SILENTLY DEFEATED by the CACHE_VERSION bump and caught in
    # review. It planted `"version": 1` with no `rule`, so the new key rejected
    # the whole cache before _safe_cache_name() was ever reached; discovery fell
    # through to a real rescan, which of course contains no escaped paths. It
    # passed with the traversal defense deleted outright.
    #
    # So the planted cache must now be VALID in every respect except the name it
    # carries, and the fix is not only to build the key correctly but to assert
    # the cache was actually USED: PLAN_READS == 0 proves the cached branch was
    # taken, which is the thing the old assertion could not distinguish from a
    # wholesale rejection. Without that, any future key field silently disarms
    # this again.
    sig = mod.scan_signature(plans)
    rule = mod.rule_signature()
    cache.parent.mkdir(parents=True, exist_ok=True)
    for label, planted in (("absolute path", "/etc/passwd"),
                           ("parent traversal", "../../../etc/passwd"),
                           ("nested separator", "sub/evil.md")):
        # It happened AGAIN, exactly as predicted, when BL-056 added `masters`:
        # the new key rejected the whole cache, reads went 0 -> 5, and this test
        # went red instead of silently passing. That is the PLAN_READS == 0
        # assertion above doing its job. Every future key belongs here too.
        cache.write_text(json.dumps({"version": mod.CACHE_VERSION, "rule": rule,
                                     "plans_dir": str(plans),
                                     "signature": sig, "eligible": [planted],
                                     "masters": []}),
                         encoding="utf-8")
        mod.PLAN_READS = 0
        got = mod.discover_plans(plans, cache_file=cache)
        check(mod.PLAN_READS == 0,
              f"{label}: the poisoned cache is accepted, so the name filter is "
              f"what must reject it (reads={mod.PLAN_READS})")
        escaped = [p for p in got if p.parent != plans]
        check(not escaped, f"{label}: rejected, not joined ({escaped})")

    # A poisoned name present ONLY in `masters`, absent from `eligible`. Safe by
    # inspection — `cached_masters` is used solely as a membership test against
    # names already drawn from and re-validated out of `eligible` — but this
    # file's history is mostly "the test that would have caught it wasn't
    # written", so the inspection is now an assertion.
    cache.write_text(json.dumps({"version": mod.CACHE_VERSION, "rule": rule,
                                 "plans_dir": str(plans), "signature": sig,
                                 "eligible": [], "masters": ["/etc/passwd"]}),
                     encoding="utf-8")
    mod.PLAN_READS = 0
    got = mod.discover_plans(plans, cache_file=cache)
    check(mod.PLAN_READS == 0, "masters-only poison: the cache is still USED")
    check(all(p.parent == plans for p in got),
          f"a name only in `masters` never reaches a path join ({got})")

    # And a DUPLICATE name cannot spend two cap slots on one plan.
    dupe = sorted(p.name for p in plans.glob("*.md"))[0]
    cache.write_text(json.dumps({"version": mod.CACHE_VERSION, "rule": rule,
                                 "plans_dir": str(plans), "signature": sig,
                                 "eligible": [dupe, dupe, dupe], "masters": []}),
                     encoding="utf-8")
    mod.PLAN_READS = 0
    got = mod.discover_plans(plans, cache_file=cache)
    check(mod.PLAN_READS == 0 and len(got) == 1,
          f"a tampered cache repeating one name yields ONE bar, not three ({got})")

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
    # Byte-identity is asserted above for the ONE-plan case and still holds
    # there. It deliberately stops holding here: Task 3.4 pads the name column
    # so stacked bars share a start column, and the widest of these three names
    # is 2 chars longer than the pinned one. Weakening the check to "starts
    # with" would hide a real regression, so it is re-stated as identity MODULO
    # that padding — every byte but the run of alignment spaces must still match.
    # Stated as an EXACT expectation rather than a fuzzy normalisation: the only
    # licensed difference is the name field widening to the longest of the three
    # names, so build that string and demand byte equality. A `squash the
    # whitespace` comparison would also have accepted padding in the wrong place.
    # The width is derived from the names that actually rendered, not from a
    # hardcoded guess: the pinned plan here lives OUTSIDE the discovered dir and
    # shares a filename with one inside it, so the three lines are not the three
    # files the fixture wrote. Not circular — the names are read with their
    # padding stripped, so a wrong pad width still fails the equality below.
    rendered_names = [ANSI_RE.sub("", ln).split("⚙ ", 1)[1].split(" ▐", 1)[0].rstrip()
                      for ln in lines]
    pad_to = max(len(n) for n in rendered_names)
    expected = GOLDEN_SINGLE_PLAN.replace(
        "2026-08-06-demo", "2026-08-06-demo".ljust(pad_to), 1)
    check(lines[0] == expected,
          f"the pinned plan is still first, and differs from the one-plan golden "
          f"ONLY by the name field widening to {pad_to}")
    if lines[0] != expected:
        print(f"      got:    {lines[0]!r}")
        print(f"      golden: {GOLDEN_SINGLE_PLAN!r}")
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


MASTER_PLAN = """# Master Plan: demo umbrella

## Sub-plans

### Sub-plan 1: foundation
- **Status:** [x]
- **Plan:** ./2026-08-01-demo-sub-01-foundation-plan.md

**Gate:**
- [ ] a gate checkbox, which is NOT a Status line and must not be counted
- [ ] nor this one

### Sub-plan 02 — zero-padded, em-dash separated
- **Status:** [~]
- **Plan:** ./2026-08-02-demo-sub-02-second-plan.md

### Sub-plan 3: not started
- **Status:** [ ]
- **Plan:** ./2026-08-03-demo-sub-03-third-plan.md
"""


def case_master_plans_are_countable():
    """Task 3.2 groundwork (closes BL-054) — a master's bar comes from its
    sub-plan register, not from Task headings it does not have."""
    print("Task 3.2 — master plans count their sub-plan register:")
    mod = load_module()
    tmp = Path(tempfile.mkdtemp(prefix="pp-master-"))

    by_heading = tmp / "2026-08-01-demo-umbrella.md"          # no -master-plan.md suffix
    by_heading.write_text(MASTER_PLAN)
    by_name = tmp / "2026-08-01-demo-master-plan.md"
    by_name.write_text(MASTER_PLAN.replace("# Master Plan: demo umbrella", "# Plan: demo"))

    for label, p in (("first heading `# Master Plan:`", by_heading),
                     ("filename `-master-plan.md`", by_name)):
        check(pu_is_master(mod, p), f"detected as a master by its {label}")

    done, total, stages = mod.parse_plan(MASTER_PLAN, by_heading)
    check((done, total) == (1, 3),
          f"1 of 3 sub-plans done — [~] counts toward total, never done (got {done}/{total})")
    check(stages == 0, f"a master reports 0 stages, not a stage count (got {stages})")
    check(mod.plan_is_eligible(MASTER_PLAN, by_heading),
          "a started, unclosed master IS eligible (it was structurally invisible before)")

    # The zero-padded em-dash entry is the one that used to be missed.
    only_padded = "# Master Plan: p\n\n### Sub-plan 01 — padded\n- **Status:** [x]\n"
    d2, t2, _ = mod.parse_plan(only_padded, tmp / "x.md")
    check((d2, t2) == (1, 1), f"`### Sub-plan 01 — title` is counted (got {d2}/{t2})")

    closed = MASTER_PLAN + "\n**Completed:** 2026-08-05 — all sub-plans green\n"
    check(not mod.plan_is_eligible(closed, by_heading),
          "a master carrying **Completed:** is not eligible")
    # REVERSED DELIBERATELY by BL-056 change 2 (user decision, 2026-08-08). This
    # assertion previously read "an all-[ ] master is 'authored, never started'
    # and earns no bar" — the non-master rule applied to masters. A master with
    # no sub-plan yet begun is work the project has committed to; its bar reads
    # 0/N. Kept as an assertion of the NEW contract rather than deleted, so the
    # boundary stays covered in whichever direction it is defined.
    never = MASTER_PLAN.replace("[x]", "[ ]").replace("[~]", "[ ]")
    check(mod.plan_is_eligible(never, by_heading),
          "an all-[ ] master IS eligible — visible whenever not closed out")
    check(not mod.plan_is_eligible(
              never + "\n**Abandoned:** 2026-08-05 — superseded\n", by_heading),
          "but an abandoned one is not — 'not closed out' means NEITHER marker")

    # An ordinary plan must not be re-read through the master parser.
    check(mod.parse_plan(PLAN, tmp / "2026-08-01-ordinary-plan.md")[1] == 5,
          "a non-master plan still counts its Task headings (5), unaffected")

    shutil.rmtree(tmp, ignore_errors=True)


def pu_is_master(mod, path):
    return mod.pu.is_master_plan(path.read_text(), path)


# --- Task 3.2 (tree glyphs) -------------------------------------------------
# The fixture is built so that FILENAME ORDER CONTRADICTS TREE ORDER: the two
# sub-plans are stamped newer than their master, so plain newest-first ranking
# would print sub-02, sub-01, master. Anything that reproduces master, sub-01,
# sub-02 therefore had to hoist the master and read the register — the ordering
# cannot come out right by accident.
GROUP_MASTER = """# Master Plan: alpha

## Sub-plans

### Sub-plan 1: foundation
- **Status:** [x]
- **Plan:** ./2026-08-02-alpha-sub-01-foundation-plan.md

**Gate:**
- [ ] an integration check

### Sub-plan 2: second
- **Status:** [ ]
- **Plan:** [2026-08-03-alpha-sub-02-second-plan.md](./2026-08-03-alpha-sub-02-second-plan.md)
"""

# Backlinked to its master. Eligible: one [x], no close-out line.
GROUP_SUB_1 = """# Project Plan: foundation
Date: 2026-08-02
Master: ./2026-08-01-alpha-master-plan.md

## Stage 1 — work

### Task 1.1: first
- **Status:** [x]

### Task 1.2: second
- **Status:** [ ]
"""

# Deliberately carries NO `Master:` line: this one is grouped only because the
# master's register names it, which is the fifth clause of Task 3.2's test. Its
# register entry uses the `[text](path)` dialect, so it also proves link_target
# sees the form two of the vault's real masters are written in.
GROUP_SUB_2 = """# Project Plan: second
Date: 2026-08-03

## Stage 1 — work

### Task 1.1: first
- **Status:** [~]

### Task 1.2: second
- **Status:** [ ]
"""


def group_fixture(mod, files):
    """A registered repo whose vault plans/ dir holds `files` {name: text}."""
    tmp = Path(tempfile.mkdtemp(prefix="pp-group-"))
    repo = tmp / "repo"
    (repo / ".claude").mkdir(parents=True)
    vplans = tmp / "vault" / "Portfolio" / "a" / "p" / "plans"
    vplans.mkdir(parents=True)
    for name, text in files.items():
        (vplans / name).write_text(text)
    cfg, reg = tmp / "cfg.yaml", tmp / "reg.yaml"
    write_yaml(cfg, f"version: 1\nvault_dir: {tmp / 'vault'}\n")
    write_yaml(reg, "version: 1\nprojects:\n"
                    f"  - path: {repo}\n    name: p\n    area: a\n    enabled: true\n")
    mod.CONFIG_PATH, mod.REGISTRY_PATH = cfg, reg
    return tmp, repo, vplans


def plain_lines(mod, repo):
    return [ANSI_RE.sub("", ln) for ln in mod.render(str(repo))]


MASTER_NAME = "2026-08-01-alpha-master-plan.md"
SUB1_NAME = "2026-08-02-alpha-sub-01-foundation-plan.md"
SUB2_NAME = "2026-08-03-alpha-sub-02-second-plan.md"
FULL_GROUP = {MASTER_NAME: GROUP_MASTER, SUB1_NAME: GROUP_SUB_1, SUB2_NAME: GROUP_SUB_2}


def case_master_grouping():
    """Task 3.2 — a master's bar sits above its sub-plans, tree-glyphed."""
    print("Task 3.2 — masters group their sub-plans under tree glyphs:")
    mod = load_module()

    check("Master:" not in GROUP_SUB_2,
          "fixture precondition: sub-02 carries NO backlink (register-only grouping)")

    tmp, repo, vplans = group_fixture(mod, FULL_GROUP)
    lines = plain_lines(mod, repo)
    check(len(lines) == 3, f"master + 2 sub-plans = 3 lines (got {len(lines)})")
    if len(lines) == 3:
        check(lines[0].startswith("⚙ ") and "alpha-master" in lines[0],
              f"the master renders FIRST and unindented ({lines[0][:40]!r})")
        check(lines[1].startswith("├─ ") and "sub-01" in lines[1],
              f"sub-plan 1 is indented under it with ├─ ({lines[1][:40]!r})")
        check(lines[2].startswith("└─ ") and "sub-02" in lines[2],
              f"the LAST child gets └─, not ├─ ({lines[2][:40]!r})")
        check("├─" not in lines[2] and "└─" not in lines[1],
              "the two glyphs are not interchangeable — last child only for └─")
    # Tier-1 Suggestion: this used to restate the position check above, which
    # cannot fail independently of it. Assert the fixture's ADVERSARIAL property
    # instead — that plain newest-first ranking really would have produced a
    # different order, so the tree order above is evidence of grouping rather
    # than a coincidence of the filenames.
    by_rank = sorted((vplans / n for n in FULL_GROUP), key=mod._rank, reverse=True)
    check(by_rank[0].name == SUB2_NAME,
          f"rank order alone would lead with sub-02, not the master ({by_rank[0].name})")
    check(lines and MASTER_NAME.startswith(mod.date_stamp(vplans / MASTER_NAME))
          and mod.date_stamp(vplans / MASTER_NAME) < mod.date_stamp(vplans / SUB1_NAME),
          "precondition: the master is stamped OLDER than both its children")

    print("  a sub-plan whose master is not eligible renders ungrouped:")
    # Same three files; the master is merely closed out. This is the sensitivity
    # proof for every assertion above: if grouping were unconditional the glyphs
    # would survive this edit, and if the eligibility filter were ignored the
    # master would still render.
    tmp2, repo2, vplans2 = group_fixture(mod, dict(
        FULL_GROUP, **{MASTER_NAME: GROUP_MASTER + "\n**Completed:** 2026-08-04 — done\n"}))
    lines2 = plain_lines(mod, repo2)
    check(len(lines2) == 2, f"only the two sub-plans render (got {len(lines2)})")
    check(all(ln.startswith("⚙ ") for ln in lines2),
          f"both are top level, no tree glyph anywhere ({lines2})")
    check(not any("├─" in ln or "└─" in ln for ln in lines2),
          "the glyphs are gone — they were not printed unconditionally")

    print("  a master with no eligible sub-plans renders alone:")
    tmp3, repo3, _ = group_fixture(mod, {MASTER_NAME: GROUP_MASTER})
    lines3 = plain_lines(mod, repo3)
    check(len(lines3) == 1 and lines3[0].startswith("⚙ "),
          f"one unindented line, no dangling glyph (got {lines3})")

    print("  a NUL byte in a link does not blank the whole status line:")
    # Tier-1 Critical, reproduced before it was fixed. pathlib raises
    # ValueError -- NOT OSError -- on "embedded null byte", and every guard here
    # named OSError alone. Task 3.2 is what made it reachable: it is the first
    # code to build a Path out of plan PROSE (`Master:` / `- **Plan:**`), and
    # the group_plans() call sits between having the plans and printing them, so
    # one malformed byte cost every bar including the pinned one.
    #
    # render() is called DIRECTLY, unguarded, on purpose: main() ends in
    # `except Exception: sys.exit(0)`, so a subprocess assertion would go green
    # whether this degrades or explodes. Same lane-B reasoning the Stage 2 gate
    # was rewritten around.
    for label, link in (("in a sub-plan's Master: backlink", "Master: ./evil\x00master-plan.md"),
                        ("in a master's register entry", None)):
        files = dict(FULL_GROUP)
        if link is None:
            files[MASTER_NAME] = GROUP_MASTER.replace(
                "./2026-08-02-alpha-sub-01-foundation-plan.md", "./ev\x00il-plan.md")
        else:
            files[SUB1_NAME] = GROUP_SUB_1.replace(
                "Master: ./2026-08-01-alpha-master-plan.md", link)
        tmpn, repon, _ = group_fixture(mod, files)
        try:
            got = mod.render(str(repon))
            ok = isinstance(got, list) and len(got) >= 2
        except Exception as e:
            got, ok = f"RAISED {type(e).__name__}: {e}", False
        check(ok, f"a NUL {label} costs at most its own grouping, not every bar "
                  f"({got if not ok else str(len(got)) + ' lines'})")
        shutil.rmtree(tmpn, ignore_errors=True)

    # And the same byte anywhere else on the render path.
    tmpn, repon, vplansn = group_fixture(mod, FULL_GROUP)
    (repon / ".claude" / "plan-progress.json").write_text(json.dumps({
        "plan": "docs/pl\x00ans/x-plan.md", "phase": "task", "stage": 1, "task": "1.1",
        "updated": datetime.now(timezone.utc).isoformat()}))
    try:
        got = mod.render(str(repon))
        ok = isinstance(got, list)
    except Exception as e:
        got, ok = f"RAISED {type(e).__name__}: {e}", False
    check(ok, f"a NUL in the state file's `plan` field degrades too ({got})")
    # The three render()-level assertions above are satisfied by EITHER the
    # BAD_PATH fix or render()'s group_plans guard, so on their own they cannot
    # say which one is working — reverting the root-cause fix leaves them green.
    # These pin the root cause itself, at the function the Critical lived in.
    try:
        ok = mod._same_file("/a\x00b", "/a\x00b") is False
    except Exception as e:
        ok = False
        got = f"RAISED {type(e).__name__}: {e}"
    check(ok, f"_same_file() returns False for a NUL path rather than raising "
              f"({'ok' if ok else got})")
    # Pin the PLATFORM split the fix depends on, rather than asserting a
    # uniform "everything raises" that is simply untrue. Measured on CPython
    # 3.12: stat/resolve/read_text raise on a NUL, while is_file/is_dir/exists
    # swallow it. `_is_file()` needing no ValueError guard today is a property
    # of pathlib, not of this file — so assert it, and it fails loudly if a
    # future pathlib changes its mind instead of silently reopening the hole.
    raises, swallows = [], []
    for meth in ("stat", "resolve", "read_text", "is_file", "is_dir", "exists"):
        try:
            getattr(Path("/a\x00b"), meth)()
            swallows.append(meth)
        except ValueError:
            raises.append(meth)
        except Exception:
            raises.append(meth + "(non-ValueError)")
    check(set(raises) == {"stat", "resolve", "read_text"},
          f"pathlib raises ValueError on exactly stat/resolve/read_text (got {raises})")
    check(set(swallows) == {"is_file", "is_dir", "exists"},
          f"...and swallows it on is_file/is_dir/exists (got {swallows})")

    # Fault injection for the blast-radius guard, which no reverted fix can
    # exercise: with the root cause fixed, grouping simply never raises. Assert
    # the FALLBACK, not the source text — the Stage 1 handoff called out
    # `assert "os.replace(" in src` as a check that survives a real regression.
    tmpg, repog, _ = group_fixture(mod, FULL_GROUP)
    real = mod.group_plans
    mod.group_plans = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    try:
        got = mod.render(str(repog))
        ok = isinstance(got, list) and len(got) == 3
    except Exception as e:
        got, ok = f"RAISED {type(e).__name__}: {e}", False
    finally:
        mod.group_plans = real
    check(ok, f"if grouping raises, every bar still renders — ungrouped, not lost "
              f"({got if not ok else str(len(got)) + ' lines, no glyphs'})")
    check(ok and not any("├─" in ln or "└─" in ln for ln in got),
          "and the fallback really is ungrouped (the glyphs are what was lost)")

    # The sibling fault injection, for the width step — which had no test, and
    # whose fallback was BROKEN when Tier-2 injected it. width=0 signals "skip
    # alignment", but a tree-prefixed child is passed `width - visible_len(pre)`
    # = -3, which is TRUTHY, so clip(name, -3) returned "" and ljust(-3) did
    # nothing: a complete, correctly-numbered bar with an EMPTY NAME. A wrong
    # bar, not a missing one — the one outcome render() exists to prevent.
    tmpw, repow, _ = group_fixture(mod, FULL_GROUP)
    real_nc = mod.name_column
    mod.name_column = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    try:
        got = mod.render(str(repow))
        plainw = [ANSI_RE.sub("", ln) for ln in got]
        ok = len(plainw) == 3
    except Exception as e:
        plainw, ok = [f"RAISED {type(e).__name__}: {e}"], False
    finally:
        mod.name_column = real_nc
    check(ok, f"if the width step raises, every bar still renders ({plainw})")
    check(ok and all(ln.split("⚙ ", 1)[1].split(" ▐", 1)[0].strip() for ln in plainw),
          f"and NO line renders a blank name beside a full bar ({plainw})")
    # The guard above is belt-and-braces with a max(0, …) clamp at the call
    # site, so the end-to-end case passes on either one alone and pins neither.
    # This pins the inner one directly: a negative width must mean "don't
    # align", never "erase the name".
    for w in (-3, -1, 0):
        line = ANSI_RE.sub("", mod._bar_line("plan-name", 1, 2, mod.DIM, w))
        check(line.startswith("⚙ plan-name"),
              f"_bar_line(width={w}) keeps the name intact ({line!r})")
    shutil.rmtree(tmpw, ignore_errors=True)
    shutil.rmtree(tmpg, ignore_errors=True)

    try:
        ok = mod.find_state("/no/such\x00dir") is None
    except Exception as e:
        ok = False
        got = f"RAISED {type(e).__name__}"
    check(ok, "find_state() survives a NUL in the statusline's stdin cwd")
    try:
        ok = mod.portfolio_plans_dir("/no/such\x00dir") is None
    except Exception:
        ok = False
    check(ok, "portfolio_plans_dir() survives it too, called RAW as the corpus does")
    shutil.rmtree(tmpn, ignore_errors=True)

    print("  detection by first heading, not only by filename:")
    # The register links are unchanged, so the ONLY thing that moved is how the
    # master is recognised — `# Master Plan:` with a filename that says nothing.
    renamed = "2026-08-01-alpha-umbrella.md"
    tmp4, repo4, _ = group_fixture(mod, {
        renamed: GROUP_MASTER,
        SUB1_NAME: GROUP_SUB_1.replace(MASTER_NAME, renamed),
        SUB2_NAME: GROUP_SUB_2})
    lines4 = plain_lines(mod, repo4)
    check(len(lines4) == 3 and lines4[0].startswith("⚙ ")
          and lines4[1].startswith("├─ ") and lines4[2].startswith("└─ "),
          f"a master named `-umbrella.md` still groups its children (got {lines4})")

    print("  ...and by filename, with no `# Master Plan:` heading at all:")
    # Tier-1 Important. master-plan-format.md documents the two signals as
    # INDEPENDENTLY sufficient, and is_master_plan() ORs them — but every other
    # fixture satisfies both at once, so a regression that broke only the
    # filename branch would pass the whole suite. This is the converse
    # isolation: `-master-plan.md` on disk, `# Project Plan:` in the body.
    body_says_nothing = GROUP_MASTER.replace("# Master Plan: alpha", "# Project Plan: alpha")
    check("# Master Plan:" not in body_says_nothing,
          "fixture precondition: the body carries no master heading")
    tmp4b, repo4b, _ = group_fixture(mod, {
        MASTER_NAME: body_says_nothing, SUB1_NAME: GROUP_SUB_1, SUB2_NAME: GROUP_SUB_2})
    lines4b = plain_lines(mod, repo4b)
    check(len(lines4b) == 3 and lines4b[0].startswith("⚙ ")
          and lines4b[1].startswith("├─ ") and lines4b[2].startswith("└─ "),
          f"the filename suffix alone is sufficient (got {lines4b})")

    print("  the backlink alone is enough when the register omits the sub-plan:")
    # Mirror image of sub-02's case: the register names nothing, so only the
    # `Master:` line can associate these. Asserting the union really is a union,
    # rather than one mechanism doing all the work in both directions.
    bare = "# Master Plan: alpha\n\n## Sub-plans\n\n### Sub-plan 1: foundation\n- **Status:** [x]\n"
    tmp5, repo5, _ = group_fixture(mod, {MASTER_NAME: bare, SUB1_NAME: GROUP_SUB_1})
    lines5 = plain_lines(mod, repo5)
    check(len(lines5) == 2 and lines5[0].startswith("⚙ ") and lines5[1].startswith("└─ "),
          f"backlink-only grouping works, and an only child gets └─ (got {lines5})")

    print("  the executing plan's GROUP leads, and the master stays above it:")
    # A newer unrelated plan outranks the whole group. The pinned plan is the
    # CHILD, so hoisting the plan rather than its group would put a sub-plan
    # above its own master and leave the glyphs pointing at nothing.
    #
    # Two members here, so an unrelated plan can be chosen alongside the group
    # and the ordering rule under test is actually exercised.
    #
    # BL-056 HAS SINCE SHIPPED, and this comment used to say the opposite —
    # that a 4th eligible plan "CAN evict a master and leave its children
    # ungrouped... a selection trade-off, not this function's". It no longer
    # can: masters are exempt from the cap. Corrected rather than deleted
    # because a reader who met the old text would take it for a still-open
    # limitation. The affirmative case it described as impossible is now
    # asserted directly, below.
    tmp6, repo6, vplans6 = group_fixture(mod, {
        MASTER_NAME: GROUP_MASTER, SUB1_NAME: GROUP_SUB_1,
        "2026-09-09-unrelated-plan.md": GROUP_SUB_1.replace("Master:", "NotMaster:")})
    (repo6 / ".claude" / "plan-progress.json").write_text(json.dumps({
        "plan": str(vplans6 / SUB1_NAME), "phase": "task", "stage": 1, "task": "1.1",
        "updated": datetime.now(timezone.utc).isoformat()}))
    lines6 = plain_lines(mod, repo6)
    check(len(lines6) == 3, f"still capped at MAX_BARS=3 (got {len(lines6)})")
    check(lines6 and lines6[0].startswith("⚙ ") and "alpha-master" in lines6[0],
          f"the pinned plan's group leads, though a 2026-09-09 plan is newer "
          f"({lines6})")

    # BL-056 end-to-end, through render() rather than discover_plans() alone.
    # This is the exact configuration the old comment above called impossible:
    # a FULL 3-member group plus a newer unrelated plan. Before the fix the cap
    # dropped the master first (within a shared date stamp `-master-plan.md`
    # sorts BELOW `-sub-NN-`), leaving two children flat and glyphless — a tree
    # with no root — and the whole rendering path had no way to notice.
    print("  BL-056: a full group survives a newer unrelated plan, end to end:")
    tmp7, repo7, vplans7 = group_fixture(mod, dict(
        FULL_GROUP, **{"2026-09-09-unrelated-plan.md":
                       GROUP_SUB_1.replace("Master:", "NotMaster:")}))
    (repo7 / ".claude" / "plan-progress.json").write_text(json.dumps({
        "plan": str(vplans7 / SUB1_NAME), "phase": "task", "stage": 1, "task": "1.1",
        "updated": datetime.now(timezone.utc).isoformat()}))
    lines7 = plain_lines(mod, repo7)
    check(any("alpha-master" in ln for ln in lines7),
          f"the master is NOT evicted by the newer unrelated plan ({lines7})")
    kids7 = [ln for ln in lines7 if ln.startswith(("├─", "└─"))]
    check(len(kids7) == 2, f"and BOTH children still render under it ({lines7})")
    check(kids7 and kids7[-1].startswith("└─"),
          f"the last child still closes the tree ({kids7})")
    check(any("unrelated" in ln for ln in lines7),
          f"while the unrelated plan keeps its own bar — masters ride on top, "
          f"they do not displace ({lines7})")
    shutil.rmtree(tmp7, ignore_errors=True)
    check(len(lines6) > 2 and lines6[1].startswith("└─ ") and "sub-01" in lines6[1]
          and "▶ T1.1" in lines6[1],
          f"the pinned child keeps its phase indicator UNDER its master ({lines6})")
    check(len(lines6) > 2 and "unrelated" in lines6[2] and not lines6[2].startswith("└"),
          f"the newer unrelated plan is pushed below the whole group ({lines6})")

    for d in (tmp, tmp2, tmp3, tmp4, tmp5, tmp6):
        shutil.rmtree(d, ignore_errors=True)


PHASE_PLAN = """# Project Plan: p
Date: 2026-08-01

## Stage 1 — one

### Task 1.1: a
- **Status:** [x]

### Task 1.2: b
- **Status:** [ ]
"""

PHASE_FILES = {"2026-09-01-newest-plan.md": PHASE_PLAN,
               "2026-08-15-middle-plan.md": PHASE_PLAN,
               "2026-07-01-oldest-plan.md": PHASE_PLAN}
GLYPHS = ("▶", "◆", "⚑", "✔", "✘")


def case_phase_indicator():
    """Task 3.3 — only the actively-executing plan carries a phase indicator,
    and a state file written in the OTHER live dialect degrades to silence
    rather than pasting a paragraph into the status line."""
    print("Task 3.3 — the phase indicator belongs to one plan only:")
    mod = load_module()
    tmp, repo, vplans = group_fixture(mod, PHASE_FILES)
    state = repo / ".claude" / "plan-progress.json"

    def render_with(**kw):
        s = {"plan": str(vplans / "2026-08-15-middle-plan.md"),
             "updated": datetime.now(timezone.utc).isoformat()}
        s.update(kw)
        state.write_text(json.dumps(s))
        return [ANSI_RE.sub("", ln) for ln in mod.render(str(repo))]

    lines = render_with(phase="task", stage=1, task="1.2", task_desc="b")
    check(len(lines) == 3, f"three in-flight plans -> three lines (got {len(lines)})")
    carrying = [ln for ln in lines if any(g in ln for g in GLYPHS)]
    check(len(carrying) == 1,
          f"exactly ONE line carries a phase glyph (got {len(carrying)})")
    check(carrying and "middle" in carrying[0],
          f"and it is the plan the state file names, not the newest ({carrying})")
    others = [ln for ln in lines if "middle" not in ln]
    check(len(others) == 2 and all("1/2" in ln and "(50%)" in ln for ln in others),
          f"the other two still render name + bar + counts ({others})")

    # "...dimmed" is half this task's acceptance criterion, and every assertion
    # above runs the output through ANSI_RE first — which strips exactly the
    # escape codes that would prove it. Caught in review: nothing here could fail
    # if render_other() stopped applying DIM entirely. So assert on the RAW lines.
    raw = mod.render(str(repo))
    raw_others = [ln for ln in raw if "middle" not in ln]
    raw_pinned = [ln for ln in raw if "middle" in ln]
    check(len(raw_others) == 2 and all(ln.startswith(mod.DIM) for ln in raw_others),
          "the two non-executing plans are DIM-prefixed (checked before ANSI stripping)")
    check(len(raw_pinned) == 1 and raw_pinned[0].startswith(mod.CYAN),
          "and the executing one is not dimmed — it opens CYAN")

    print("  the staleness marker is likewise the executing plan's alone:")
    old = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    lines = render_with(phase="task", stage=1, task="1.2", updated=old)
    stale = [ln for ln in lines if "stale" in ln]
    check(len(stale) == 1 and "middle" in stale[0],
          f"only the pinned line is marked stale (got {stale})")

    print("  with NO state file, every line renders and none carries a phase:")
    state.unlink()
    try:
        lines = [ANSI_RE.sub("", ln) for ln in mod.render(str(repo))]
        ok = len(lines) == 3 and not any(g in ln for ln in lines for g in GLYPHS)
    except Exception as e:
        lines, ok = f"RAISED {type(e).__name__}: {e}", False
    check(ok, f"3 phase-free lines, nothing raised ({lines})")

    print("  the OTHER live dialect — prose where the schema promises a scalar:")
    # Every value below is copied from android/writer-pad's real state file,
    # written by its own execution session. Interpolated raw, `phase` fell
    # through every branch and rendered a bare "▶ " with a dangling separator
    # before it; a prose `task` would have pasted a sentence where T3.1 goes.
    prose_phase = "STOPPED — Stage 2 re-gate FAILED; awaiting user direction"
    lines = render_with(phase=prose_phase, stage_index=2, stage_total=2)
    pinned = [ln for ln in lines if "middle" in ln][0]
    check("S2/2" in pinned,
          f"`stage_index`/`stage_total` are read even when `stage` is absent ({pinned!r})")

    # These two carry the fixture shapes that make the assertions DISCRIMINATING,
    # and both were added after a mutation run showed the obvious fixture proves
    # nothing. With no `task` and no `task_desc`, an unrecognised phase falls
    # through to the task branch and is caught by the empty-label guard anyway —
    # so the KNOWN_PHASES check could be deleted and the test stayed green. The
    # phase must be prose WHILE a valid task is present for the guard to be the
    # thing under test.
    lines = render_with(phase=prose_phase, stage_index=2, stage_total=2,
                        task="1.1", task_desc="d")
    pinned = [ln for ln in lines if "middle" in ln][0]
    check(not any(g in pinned for g in GLYPHS) and "T1.1" not in pinned,
          f"an unrecognised `phase` suppresses the task glyph even when a valid "
          f"task IS present ({pinned!r})")

    # Likewise the dangling separator: with stage_index present the tail is
    # non-empty and the separator is legitimately emitted, so the earlier fixture
    # could not tell a conditional separator from an unconditional one. Strip
    # every tail source and the two diverge.
    lines = render_with(phase=prose_phase)
    pinned = [ln for ln in lines if "middle" in ln][0]
    check(not pinned.rstrip().endswith("·"),
          f"nothing to say -> no dangling ` · ` separator ({pinned!r})")
    check(pinned.rstrip() == pinned.rstrip().rstrip("·").rstrip(),
          f"...and the line ends at the counts ({pinned!r})")

    prose_task = "close-out: owed review passes dispatched over Stage 2 and whole-plan diffs"
    lines = render_with(phase="task", stage=1, task=prose_task)
    pinned = [ln for ln in lines if "middle" in ln][0]
    check("close-out:" not in pinned and "▶" not in pinned,
          f"a prose `task` is omitted, not pasted into the bar ({pinned!r})")
    check(len(pinned) < 120, f"so the line stays a line ({len(pinned)} chars)")

    # A malformed `task` costs the LABEL only — `task_desc` is free text by
    # schema and is not implicated by its sibling. Review found the first version
    # returning "" here, silently dropping a valid desc and contradicting the
    # `task` absent case below; the mutation proving it was untested was that the
    # only fixture exercising the branch never set task_desc, so both behaviors
    # produced "". These two cases are what make the rule discriminating.
    lines = render_with(phase="task", stage=1, task="T2.3", task_desc="parse config entries")
    pinned = [ln for ln in lines if "middle" in ln][0]
    check("parse config entries" in pinned and "T2.3" not in pinned,
          f"a malformed `task` drops the label but KEEPS task_desc ({pinned!r})")
    lines = render_with(phase="task", stage=1, task_desc="parse config entries")
    pinned = [ln for ln in lines if "middle" in ln][0]
    check("▶ parse config entries" in pinned,
          f"...matching the `task` absent case exactly ({pinned!r})")

    print("  the ints win over a prose `stage`, and bad types never crash:")
    lines = render_with(phase="gate", stage="all stages green — S1 PASSED, S2 PASSED",
                        stage_index=3, stage_total=4)
    pinned = [ln for ln in lines if "middle" in ln][0]
    check("S3/4" in pinned and "all stages green" not in pinned,
          f"prose `stage` ignored in favour of the ints ({pinned!r})")
    check("◆ S3 gate" in pinned, f"and the gate glyph still renders ({pinned!r})")

    # Stages are 1-indexed everywhere in the format, so 0 and negatives are
    # malformed, not edge cases — both degrade rather than rendering `S0/3` or
    # `S-1/3`. Review flagged the earlier truthy-`or` form for letting `stage`
    # silently beat an explicit `stage_index`; the rule is now "among VALID
    # values", which these pin.
    for bad_stage in (0, -1, -99):
        lines = render_with(phase="task", stage=bad_stage, task="1.1", task_desc="d")
        pinned = [ln for ln in lines if "middle" in ln][0]
        check(f"S{bad_stage}/" not in pinned and "▶ T1.1 d" in pinned,
              f"stage={bad_stage} is not a stage position ({pinned!r})")
    lines = render_with(phase="gate", stage=-1)
    pinned = [ln for ln in lines if "middle" in ln][0]
    check("S-1" not in pinned and "◆ gate" in pinned,
          f"and a negative stage never reaches the gate glyph either ({pinned!r})")

    for bad in (True, 1.5, "2", None, [], {"a": 1}):
        lines = render_with(phase="task", stage=bad, task="1.1", task_desc="d")
        pinned = [ln for ln in lines if "middle" in ln][0]
        check("▶ T1.1 d" in pinned and "S" + str(bad) not in pinned,
              f"stage={bad!r} degrades to no stage position, task intact ({pinned!r})")

    # A gate with no stage at all used to render the literal "SNone gate".
    lines = render_with(phase="gate")
    pinned = [ln for ln in lines if "middle" in ln][0]
    check("None" not in pinned and "◆ gate" in pinned,
          f"a gate with no stage recorded renders `◆ gate`, never `SNone` ({pinned!r})")

    shutil.rmtree(tmp, ignore_errors=True)


# The full three-line master/sub composition, ANSI included — captured from the
# implementation and then read by eye before being pinned. The names are padded
# to a shared 36-column field: the master carries no tree prefix and the two
# children carry a 3-column one, so their NAMES are padded 3 shorter and every
# ▐ still lands on the same column. That relationship is the whole point of the
# golden; a diff here that keeps the bars aligned is a rendering change, one
# that moves them apart is a regression.
COMPOSED_GOLDEN = [
    '\x1b[2m⚙ 2026-08-01-alpha-master              \x1b[0m \x1b[2m▐\x1b[0m'
    '\x1b[38;2;0;160;0m██████████\x1b[0m\x1b[2m░░░░░░░░░░▌\x1b[0m 1/2 \x1b[2m(50%)\x1b[0m',
    '\x1b[2m├─ \x1b[0m\x1b[2m⚙ 2026-08-02-alpha-sub-01-foundation\x1b[0m \x1b[2m▐\x1b[0m'
    '\x1b[38;2;0;160;0m██████████\x1b[0m\x1b[2m░░░░░░░░░░▌\x1b[0m 1/2 \x1b[2m(50%)\x1b[0m',
    '\x1b[2m└─ \x1b[0m\x1b[2m⚙ 2026-08-03-alpha-sub-02-second    \x1b[0m \x1b[2m▐\x1b[0m'
    '\x1b[38;2;0;160;0m\x1b[0m\x1b[2m░░░░░░░░░░░░░░░░░░░░▌\x1b[0m 0/2 \x1b[2m(0%)\x1b[0m',
]


def case_alignment_and_composition():
    """Task 3.4 — stacked bars share a start column, long names are cut rather
    than pushing the bar off-screen, and the composed master/sub output is
    pinned including its ANSI codes."""
    print("Task 3.4 — alignment, truncation, and the composed golden:")
    mod = load_module()

    print("  bars start at the same column, coloured and uncoloured alike:")
    tmp, repo, vplans = group_fixture(mod, FULL_GROUP)
    (repo / ".claude" / "plan-progress.json").write_text(json.dumps({
        "plan": str(vplans / SUB1_NAME), "phase": "task", "stage": 1, "task": "1.1",
        "updated": datetime.now(timezone.utc).isoformat()}))
    raw = mod.render(str(repo))
    # The pinned line opens CYAN and the others DIM — different escape LENGTHS.
    # Measuring with len() instead of visible width lines up the escape bytes
    # rather than the glyphs, so this pair is exactly what catches it.
    cols = [ANSI_RE.sub("", ln).index("▐") for ln in raw]
    check(len(set(cols)) == 1,
          f"every bar starts at one column, across CYAN and DIM lines (got {cols})")
    # NOTE: a FIXTURE-VALIDITY check, not a regression guard — it asserts the
    # CYAN and DIM constants differ in length, so no mutation of the alignment
    # code can fail it. Kept because it is what makes the assertion above
    # meaningful (aligning on len() would visibly diverge here), but it must not
    # be counted as coverage. Flagged as such in review.
    check(len(set(len(ln) for ln in raw)) > 1,
          "[fixture check] the raw byte lengths differ, so len() would NOT have aligned them")

    print("  a long name is truncated, never allowed to push the bar out:")
    long_name = ("2026-08-04-writer-pad-external-import-audio-transcription"
                 "-sub-02-text-import-entry-points-plan.md")
    tmp2, repo2, vplans2 = group_fixture(mod, {long_name: GROUP_SUB_1,
                                               "2026-08-03-short-plan.md": GROUP_SUB_2})
    plain = [ANSI_RE.sub("", ln) for ln in mod.render(str(repo2))]
    check(all(mod.ELLIPSIS in ln for ln in plain if "audio" in ln),
          f"the 90-char name is elided ({plain})")
    check(all(ln.index("▐") <= mod.NAME_WIDTH + 3 for ln in plain),
          f"and every bar still starts within the name column ({[ln.index('▐') for ln in plain]})")
    check(len(set(ln.index("▐") for ln in plain)) == 1,
          "a truncated name and a short one still align")

    print("  free text is bounded — the `blocked` note that ran to 200 chars:")
    # Real value from multitor-gui's live state file. Before Task 3.4 it was
    # interpolated whole; the plan assigned bounding here rather than to 3.3.
    note = ("Sub-plans 1+2 green; Sub-plan 3 (native chains, BL-002) awaits a "
            "fresh session, then master close-out")
    (repo2 / ".claude" / "plan-progress.json").write_text(json.dumps({
        "plan": str(vplans2 / "2026-08-03-short-plan.md"), "phase": "blocked",
        "note": note, "updated": datetime.now(timezone.utc).isoformat()}))
    plain = [ANSI_RE.sub("", ln) for ln in mod.render(str(repo2))]
    blocked = [ln for ln in plain if "✘" in ln][0]
    check(mod.ELLIPSIS in blocked and len(blocked) < 140,
          f"the note is clipped and the line stays a line ({len(blocked)} chars)")
    check(note[:20] in blocked,
          f"...but keeps its informative head ({blocked!r})")

    print("  task_desc is bounded too — note's sibling, same clip, no coverage:")
    # Review found this by mutation: reverting the task_desc clip left the whole
    # suite GREEN, because every task_desc anywhere in this file ("z", "b", "d",
    # "parse config entries"…) is comfortably under NOTE_WIDTH. The motivating
    # case was a long `note`, and its sibling field went along for the ride
    # untested — the bounding was verified for one of the two fields that need it.
    long_desc = ("version catalog, convention plugins, module graph, and the "
                 "instrumented device suite wiring")
    (repo2 / ".claude" / "plan-progress.json").write_text(json.dumps({
        "plan": str(vplans2 / "2026-08-03-short-plan.md"), "phase": "task",
        "stage": 1, "task": "1.2", "task_desc": long_desc,
        "updated": datetime.now(timezone.utc).isoformat()}))
    plain2 = [ANSI_RE.sub("", ln) for ln in mod.render(str(repo2))]
    pinned2 = [ln for ln in plain2 if "▶" in ln][0]
    check(mod.ELLIPSIS in pinned2 and long_desc not in pinned2,
          f"a long task_desc is clipped like a note ({pinned2!r})")
    check(long_desc[:20] in pinned2, "...keeping its head")

    print("  clip() at its boundaries — the widths nothing else drives it to:")
    # Q1 of the review brief was whether `s[:width-1] + ELLIPSIS if width > 1
    # else ELLIPSIS` binds as intended. It does. But no fixture drives a computed
    # width down to 0/1/2, so nothing pinned it and a later "simplification"
    # could reintroduce the ambiguity. Direct unit assertions instead.
    s = "abcdef"
    for width, want in ((0, ""), (1, mod.ELLIPSIS), (2, "a" + mod.ELLIPSIS),
                        (3, "ab" + mod.ELLIPSIS), (6, s), (7, s), (-1, "")):
        got = mod.clip(s, width)
        check(got == want, f"clip({s!r}, {width}) == {want!r} (got {got!r})")
        check(len(got) <= max(width, 0),
              f"...and never exceeds its width (len {len(got)} vs {width})")

    print("  control characters are stripped before anything is measured or cut:")
    # CWE-150, reproduced in review: clip("\x1b[35mHELLO", 3) -> "\x1b[…", an
    # UNTERMINATED escape that eats the bytes after it, including this file's own
    # RESET, and recolours the user's terminal past the end of the status line.
    check(mod.plain("\x1b[35mred") == "[35mred",
          f"plain() removes the ESC ({mod.plain(chr(27) + '[35mred')!r})")
    check("\x1b" not in mod.clip(mod.plain("\x1b[35mHELLO there"), 3),
          "so clip() can no longer bisect an escape sequence")
    # The escape is positioned to STRADDLE the NOTE_WIDTH cut, which is the only
    # place bisection can happen. A first version put it at offset 0, where the
    # clip lands far past it and the sequence survives whole — the assertion
    # below then passed with plain() disabled, i.e. proved nothing.
    straddle = "x" * (mod.NOTE_WIDTH - 2) + "\x1b[35m" + "y" * 40
    (repo2 / ".claude" / "plan-progress.json").write_text(json.dumps({
        "plan": str(vplans2 / "2026-08-03-short-plan.md"), "phase": "blocked",
        "note": straddle,
        "updated": datetime.now(timezone.utc).isoformat()}))
    rendered = mod.render(str(repo2))
    blocked2 = [ln for ln in rendered if "✘" in ANSI_RE.sub("", ln)][0]
    check(blocked2.count("\x1b") == blocked2.count("\x1b[") ==
          len(ANSI_RE.findall(blocked2)),
          "every ESC in a rendered line is part of a COMPLETE, matched sequence")
    check(blocked2.endswith(mod.RESET),
          f"and the line still closes with RESET, so nothing leaks past it")

    print("  sibling children stay DISTINGUISHABLE, not just indented:")
    # Stage 3 gate evaluator, Material. Names clip from the tail, but a
    # sub-plan's distinguishing part -- `sub-NN-<slug>` -- IS the tail, while the
    # shared date and topic eat the column ahead of it. Measured on the live
    # vault, all three of anki-kit's children rendered the byte-identical string
    # `2026-07-16-anki-compatible-flashcard-ecosy…`. The relationship read; the
    # identity did not. A child now shows its name RELATIVE to its master.
    #
    # NOTE this is not covered by COMPOSED_GOLDEN: that fixture's master and
    # children carry DIFFERENT date stamps (deliberately, to make the ordering
    # adversarial), so they share too few tokens to strip and correctly keep
    # their full names. Relative naming needs a same-date master, like the vault's.
    shared = "2026-08-05-payments-platform-migration"
    files = {f"{shared}-master-plan.md":
             ("# Master Plan: payments\n\n## Sub-plans\n\n"
              f"### Sub-plan 1: a\n- **Status:** [x]\n- **Plan:** ./{shared}-sub-01-card-rails-plan.md\n\n"
              f"### Sub-plan 2: b\n- **Status:** [ ]\n- **Plan:** ./{shared}-sub-02-ledger-backfill-plan.md\n"),
             f"{shared}-sub-01-card-rails-plan.md": GROUP_SUB_1.replace(
                 "Master: ./2026-08-01-alpha-master-plan.md", f"Master: ./{shared}-master-plan.md"),
             f"{shared}-sub-02-ledger-backfill-plan.md": GROUP_SUB_2}
    tmpr, repor, _ = group_fixture(mod, files)
    plainr = [ANSI_RE.sub("", ln) for ln in mod.render(str(repor))]
    kids = [ln for ln in plainr if ln.startswith(("├─", "└─"))]
    check(len(kids) == 2, f"master + 2 children render (got {len(plainr)} lines)")
    names = [ln.split("⚙ ", 1)[1].split(" ▐", 1)[0].rstrip() for ln in kids]
    check(len(set(names)) == 2,
          f"the two children are DISTINGUISHABLE, not two identical strings ({names})")
    check(all(n.startswith("sub-0") for n in names),
          f"each shows what distinguishes it, the master's name having been dropped ({names})")
    check(not any(mod.ELLIPSIS in n for n in names),
          f"and neither needed truncating at all any more ({names})")
    # The rule must not fire on a partial DATE — the bug that produced
    # `02-alpha-sub-01-foundation`, a date fragment promoted to the front.
    check(mod.relative_name(Path("2026-08-02-alpha-sub-01-foundation-plan.md"),
                            Path("2026-08-01-alpha-master-plan.md"))
          == "2026-08-02-alpha-sub-01-foundation",
          "a master and child with DIFFERENT dates share too few tokens to strip")
    check(len(set(ln.index("▐") for ln in plainr)) == 1,
          "and the relabelled children still align with their master")
    shutil.rmtree(tmpr, ignore_errors=True)

    print("  the composed three-line master/sub output is pinned, ANSI included:")
    tmp3, repo3, _ = group_fixture(mod, FULL_GROUP)
    composed = mod.render(str(repo3))
    check(composed == COMPOSED_GOLDEN,
          "the full master + 2 sub composition is byte-for-byte as recorded")
    if composed != COMPOSED_GOLDEN:
        for ln in composed:
            print(f"      got:    {ln!r}")
    # A golden nobody has watched fail is not evidence. Perturb one Status and
    # the composition must move.
    tmp4, repo4, vplans4 = group_fixture(mod, dict(
        FULL_GROUP, **{SUB1_NAME: GROUP_SUB_1.replace("- **Status:** [x]",
                                                      "- **Status:** [~]")}))
    check(mod.render(str(repo4)) != COMPOSED_GOLDEN,
          "the composed golden is sensitive — one Status flip moves it")

    for d in (tmp, tmp2, tmp3, tmp4):
        shutil.rmtree(d, ignore_errors=True)


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


def case_masters_are_off_the_cap():
    """BL-056 — MAX_BARS bounds non-masters; eligible masters ride on top.

    The reproduction is the backlog entry's own, and it is built so the OLD code
    fails it in the worst direction: within a shared date stamp
    `-master-plan.md` sorts BELOW `-sub-NN-`, and the unrelated plan is newest,
    so the one plan the shared cap evicted was the PARENT — leaving its children
    rendered flat and glyphless, a tree with no root.
    """
    print("BL-056 — masters do not compete for the MAX_BARS slots:")
    mod = load_module()
    tmp = Path(tempfile.mkdtemp(prefix="pp-bl056-"))
    plans = tmp / "plans"
    plans.mkdir()
    started = "### Task 1.1: a\n- **Status:** [x]\n\n### Task 1.2: b\n- **Status:** [ ]\n"
    master = ("# Master Plan: alpha\n\n## Sub-plans\n\n"
              "### Sub-plan 1: foundation\n- **Status:** [x]\n"
              "- **Plan:** ./2026-08-02-alpha-sub-01-foundation-plan.md\n")

    (plans / "2026-08-01-alpha-master-plan.md").write_text(master)
    (plans / "2026-08-02-alpha-sub-01-foundation-plan.md").write_text(started)
    (plans / "2026-08-03-alpha-sub-02-second-plan.md").write_text(started)
    (plans / "2026-09-09-unrelated-plan.md").write_text(started)

    got = mod.discover_plans(plans)
    names = [p.name for p in got]
    check("2026-08-01-alpha-master-plan.md" in names,
          f"the master survives a full cap — it used to be the first evicted ({names})")
    check(len(got) == 4, f"3 capped non-masters + 1 exempt master = 4 bars (got {len(got)})")
    non_master = [n for n in names if not n.endswith("-master-plan.md")]
    check(len(non_master) == 3,
          f"non-masters are STILL capped at MAX_BARS=3, not uncapped ({non_master})")

    print("  a second master rides on top too, and the cap does not move:")
    (plans / "2026-08-04-beta-master-plan.md").write_text(master)
    names2 = [p.name for p in mod.discover_plans(plans)]
    check(sum(1 for n in names2 if n.endswith("-master-plan.md")) == 2,
          f"both masters render ({names2})")
    check(sum(1 for n in names2 if not n.endswith("-master-plan.md")) == 3,
          f"and exactly 3 non-masters still (got {names2})")

    print("  the exemption is 'not closed out', not 'unconditional':")
    for marker in ("**Completed:** 2026-08-05 — done", "**Abandoned:** 2026-08-05 — dropped"):
        (plans / "2026-08-04-beta-master-plan.md").write_text(master + "\n" + marker + "\n")
        out = [p.name for p in mod.discover_plans(plans)]
        check("2026-08-04-beta-master-plan.md" not in out,
              f"a master carrying {marker.split(':')[0]} earns no bar ({out})")
    (plans / "2026-08-04-beta-master-plan.md").unlink()

    print("  masterhood survives a CACHE HIT with zero plan reads:")
    # Load-bearing: only the FILENAME half of masterhood is recoverable from a
    # cached name, so this master is detected by its `# Master Plan:` heading
    # while carrying an ordinary filename. A cache that stored names alone would
    # have to re-read every plan to classify it — the cost the cache exists to
    # avoid — so anything that passes here without reads read the stored flag.
    hidden = plans / "2026-08-05-heading-only-plan.md"
    hidden.write_text(master)
    cache = tmp / "cache.json"
    first = [p.name for p in mod.discover_plans(plans, cache_file=cache)]
    check(hidden.name in first, f"cold scan: the heading-only master renders ({first})")
    mod.PLAN_READS = 0
    warm = [p.name for p in mod.discover_plans(plans, cache_file=cache)]
    check(mod.PLAN_READS == 0, f"warm run performed no plan reads (reads={mod.PLAN_READS})")
    check(warm == first, f"and returned the same set ({warm} vs {first})")
    check(sum(1 for n in warm if not n.endswith("-master-plan.md")
              and n != hidden.name) == 3,
          f"the heading-only master was NOT counted against the cap ({warm})")

    print("  a pinned master does not spend a capped slot:")
    pinned = plans / "2026-08-01-alpha-master-plan.md"
    got3 = mod.discover_plans(plans, pinned=pinned)
    n3 = [p.name for p in got3]
    check(pinned.resolve() in [p.resolve() for p in got3], f"the pinned master renders ({n3})")
    check(sum(1 for n in n3 if not n.endswith("-master-plan.md")
              and n != hidden.name) == 3,
          f"and 3 non-masters still fit beside it ({n3})")

    shutil.rmtree(tmp, ignore_errors=True)


def date_stamped(p):
    return re.match(r"^\d{4}-\d{2}-\d{2}", p.name) is not None


BLOCKED_GATE_PLAN = """# Plan: a gate that could not be run

## Stage 1 — the work

### Task 1.1: done
- **Status:** [x]

### Stage 1 Gate

- [x] the host suite is green
- [~] the device suite ran on hardware
"""


def case_blocked_gate_renders():
    """Task 2.1 / BL-077 — a `[~]` gate check is BLOCKED, and the bar says so.

    The measured failure: a fully-blocked master rendered as Completed while
    every gate box carried an amendment. Whatever else the bar shows, a plan
    whose gate could not be run must not read as one whose gate passed.
    """
    print("Task 2.1 — a `[~]` gate check renders BLOCKED:")
    mod = load_module()
    tmp = Path(tempfile.mkdtemp(prefix="plan-progress-blocked-"))
    repo = tmp / "repo"
    (repo / "plans").mkdir(parents=True)
    plan = repo / "plans" / "blocked-plan.md"
    plan.write_text(BLOCKED_GATE_PLAN)
    write_state(repo, plan=str(plan), phase="gate", stage=1)

    out = "".join(ANSI_RE.sub("", ln) for ln in mod.render(str(repo)))
    check("GATE BLOCKED" in out,
          f"the rendered line names the gate BLOCKED (got {out!r})")
    check("1/1" in out,
          f"the task count is untouched — BLOCKED is about the GATE, not the "
          f"tasks (got {out!r})")

    print("  and a DISCOVERED (non-executing) plan carries it too:")
    # render_other() has its own append, and only render_pinned()'s was reachable
    # from the fixture above — the discovered path goes through the portfolio
    # vault resolver, not the repo's plans/ dir. Exercised directly rather than
    # plumbed a vault for, because the gap being closed is one line in one
    # function: reverting it broke no test.
    other = repo / "plans" / "second-plan.md"
    other.write_text(BLOCKED_GATE_PLAN)
    line = ANSI_RE.sub("", mod.render_other(other))
    check("GATE BLOCKED" in line,
          f"a discovered, non-executing plan is marked too (got {line!r})")
    other.write_text(BLOCKED_GATE_PLAN.replace(
        "- [~] the device suite ran on hardware", "- [x] the device suite ran on hardware"))
    line2 = ANSI_RE.sub("", mod.render_other(other))
    check("GATE BLOCKED" not in line2,
          f"and a discovered plan with a passed gate is not (got {line2!r})")
    other.unlink()

    print("  and an all-`[x]` gate does NOT render BLOCKED:")
    plan.write_text(BLOCKED_GATE_PLAN.replace(
        "- [~] the device suite ran on hardware", "- [x] the device suite ran on hardware"))
    out2 = "".join(ANSI_RE.sub("", ln) for ln in mod.render(str(repo)))
    check("GATE BLOCKED" not in out2,
          f"a passed gate carries no BLOCKED marker (got {out2!r})")


LAGGING_PLAN = """# Plan: markers that stopped moving

## Stage 1: The work

### Task 1.1: first
- **Status:** [x]

### Task 1.2: second
- **Status:** [ ]

### Task 1.3: third
- **Status:** [ ]

### Task 1.4: fourth
- **Status:** [ ]
"""


def case_status_lag_warns():
    """Task 2.2 / BL-096 — the file lagging the live state is visible WHILE it
    happens, not on a sweep weeks later.

    `Status` flips stopped mid-plan in all three audited sessions: tasks kept
    completing and the markers stopped moving. The rule already existed (Step 3.3
    rule 5, flip it in the same change as the work); what was missing was any
    signal at the time. Both artifacts are already maintained — the only new
    thing is noticing they disagree.
    """
    # The fixture is NOT named *lag*: an earlier draft was, and every assertion
    # below matched the plan's own name in the bar. The positive check passed
    # for the wrong reason and only the negative cases exposed it.
    print("Task 2.2 — the plan file lagging the live state warns on the bar:")
    mod = load_module()
    tmp = Path(tempfile.mkdtemp(prefix="plan-progress-lag-"))
    repo = tmp / "repo"
    (repo / "plans").mkdir(parents=True)
    plan = repo / "plans" / "slow-plan.md"
    plan.write_text(LAGGING_PLAN)

    def bar_at(task):
        write_state(repo, plan=str(plan), phase="task", stage=1, task=task)
        return ANSI_RE.sub("", "".join(mod.render(str(repo))))

    print("  markers at 1.1, executor at 1.3 — two tasks of lag:")
    out = bar_at("1.3")
    check("lag" in out.lower(),
          f"the bar warns that the file trails the run (got {out!r})")

    print("  markers at 1.1, executor at 1.2 — one task, the ordinary case:")
    out1 = bar_at("1.2")
    check("lag" not in out1.lower(),
          f"one task of lag is a task in flight, not a stall (got {out1!r})")

    print("  and it clears the moment the markers catch up:")
    plan.write_text(LAGGING_PLAN.replace(
        "### Task 1.2: second\n- **Status:** [ ]",
        "### Task 1.2: second\n- **Status:** [x]"))
    out2 = bar_at("1.3")
    check("lag" not in out2.lower(),
          f"flipping the missing marker silences it (got {out2!r})")

    print("  a `[~]` marker is the marker MOVING, not a stall:")
    # BL-096 is about markers that stop moving. `[~]` is a marker that moved.
    # Measuring lag from the last `[x]` alone warns on a task that is correctly
    # marked in-flight, which is a false positive against the very state the
    # contract added for this purpose.
    inflight = repo / "plans" / "inflight-plan.md"
    inflight.write_text(LAGGING_PLAN.replace(
        "### Task 1.2: second\n- **Status:** [ ]",
        "### Task 1.2: second\n- **Status:** [~]"))
    write_state(repo, plan=str(inflight), phase="task", stage=1, task="1.3")
    iout = ANSI_RE.sub("", "".join(mod.render(str(repo))))
    check("status lag" not in iout,
          f"a `[~]` between last-done and current is not lag (got {iout!r})")
    inflight.unlink()

    print("  concurrency the plan format SANCTIONS is not a stall:")
    # A stage may mark tasks `Parallel: YES`; those are dispatched together and
    # do not finish in document order. The state file names one of them while
    # its siblings are legitimately still `[ ]`, so raw ordinal distance fires
    # on the format's own first-class feature. A warning that cries wolf on
    # sanctioned behaviour is worse than the silence it replaces — it teaches
    # the reader to ignore it, which is the trust BL-096 is trying to buy.
    par = repo / "plans" / "fanout-plan.md"
    par.write_text("""# Plan

## Stage 1: fan out

### Task 1.1: first
- **Status:** [x]
- **Parallel:** NO

### Task 1.2: concurrent sibling
- **Status:** [ ]
- **Parallel:** YES

### Task 1.3: concurrent sibling
- **Status:** [ ]
- **Parallel:** YES
""")
    write_state(repo, plan=str(par), phase="task", stage=1, task="1.3")
    pout = ANSI_RE.sub("", "".join(mod.render(str(repo))))
    check("status lag" not in pout,
          f"an unmarked `Parallel: YES` sibling is concurrency, not lag (got {pout!r})")

    print("  but a SEQUENTIAL gap between them still warns:")
    par.write_text(par.read_text().replace(
        "### Task 1.2: concurrent sibling\n- **Status:** [ ]\n- **Parallel:** YES",
        "### Task 1.2: sequential\n- **Status:** [ ]\n- **Parallel:** NO"))
    pout2 = ANSI_RE.sub("", "".join(mod.render(str(repo))))
    check("status lag" in pout2,
          f"a `Parallel: NO` task left unmarked is still a stall (got {pout2!r})")
    par.unlink()

    print("  a state file naming a task the plan no longer has says so:")
    # Silently returning "" folded this into the ordinary cases. It is a WORSE
    # divergence than a two-task lag — the plan was edited under a run whose
    # markers had already stopped — and it was indistinguishable from nothing
    # to report.
    write_state(repo, plan=str(plan), phase="task", stage=9, task="9.9")
    gout = ANSI_RE.sub("", "".join(mod.render(str(repo))))
    check("not in plan" in gout,
          f"the bar names the divergence rather than going quiet (got {gout!r})")

    print("  a plan nobody is executing is never warned about:")
    # render_other has no state to compare against; the warning is a statement
    # about THIS session's run, not about a file sitting in the vault.
    line = ANSI_RE.sub("", mod.render_other(plan))
    check("lag" not in line.lower(),
          f"a discovered plan carries no lag marker (got {line!r})")


def case_budget_check():
    """Task 2.3 — the remediation budget stops being prose the executor tracks.

    A 4th review round was dispatched after a declared budget of 3, ~160K
    subagent tokens in that round alone and ~604K across four rounds for one
    Critical, ending in "stop it and fix plans". `plan-progress.json` already
    carried `remediation_round`; nothing read it as a stop.
    """
    print("Task 2.3 — --budget-check exits non-zero at the declared ceiling:")
    tmp = Path(tempfile.mkdtemp(prefix="plan-progress-budget-"))
    repo = tmp / "repo"
    (repo / ".claude").mkdir(parents=True)
    (repo / "plans").mkdir()
    plan = repo / "plans" / "b-plan.md"
    plan.write_text(PLAN)

    def budget_check(**kw):
        st = {"plan": str(plan), "phase": "gate", "stage": 1,
              "updated": datetime.now(timezone.utc).isoformat()}
        st.update(kw)
        (repo / ".claude" / "plan-progress.json").write_text(json.dumps(st))
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--budget-check"], cwd=repo,
            capture_output=True, text=True)

    r = budget_check(remediation_round=1)
    check(r.returncode == 0, f"round 1 of the default 2 exits 0 (got {r.returncode})")
    r = budget_check(remediation_round=2)
    check(r.returncode != 0,
          f"round 2 of 2 — the budget is SPENT — exits non-zero (got {r.returncode})")
    check("escalat" in (r.stderr + r.stdout).lower(),
          f"and it names escalation, not another round ({(r.stderr + r.stdout)!r})")
    r = budget_check(remediation_round=3)
    check(r.returncode != 0, "past the ceiling still exits non-zero")

    print("  a plan-declared budget overrides the default:")
    r = budget_check(remediation_round=2, remediation_budget=3)
    check(r.returncode == 0,
          f"round 2 of a declared 3 exits 0 (got {r.returncode})")
    r = budget_check(remediation_round=3, remediation_budget=3)
    check(r.returncode != 0, "round 3 of a declared 3 exits non-zero")

    print("  the phase lagging the round does not reopen the budget:")
    # Step 4 of the gate-failure procedure re-enters the task's Red-Green loop,
    # and the state file legitimately flips back to phase "task" while the gate
    # is still mid-remediation. Requiring phase == "gate" meant a spent budget
    # at exactly that moment exited 0 and permitted another round — the failure
    # this task exists to close, hiding one layer down. A recorded round is
    # meaningful whatever the phase says.
    r = budget_check(phase="task", task="1.2", remediation_round=2)
    check(r.returncode != 0,
          f"a spent budget still stops while the phase reads 'task' (got {r.returncode})")

    print("  and it is silent-zero where there is no gate to bound:")
    r = budget_check(phase="task", task="1.2")
    check(r.returncode == 0,
          "a task phase with NO recorded round carries no budget and exits 0")
    (repo / ".claude" / "plan-progress.json").unlink()
    r = subprocess.run([sys.executable, str(SCRIPT), "--budget-check"], cwd=repo,
                       capture_output=True, text=True)
    check(r.returncode == 0, "no state file at all exits 0, never a traceback")
    check("Traceback" not in r.stderr, f"no traceback ({r.stderr!r})")


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
    case_masters_are_off_the_cap()
    case_scan_cache()
    case_render_budget()
    case_degrades_without_raising()
    case_ordering_ignores_mtime()
    case_render_returns_lines()
    case_master_plans_are_countable()
    case_master_grouping()
    case_phase_indicator()
    case_alignment_and_composition()
    case_blocked_gate_renders()
    case_status_lag_warns()
    case_budget_check()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} failure(s):")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
