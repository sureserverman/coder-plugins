#!/usr/bin/env python3
"""Fixture suite for scripts/validate-dispatch.py — run directly (CI convention):
    python3 planning/skills/planning-projects/tests/test-validate-dispatch.py

Asserts the validator's contract: the clean fixture exits 0; each negative fixture in
tests/fixtures/dispatch-corpus/ exits 1 with a `FAIL:` line naming its class; the retired
`Parallel:` spelling is silent before the cutover and a note after it; the could-be-YES
note fires on the one task that earns it; every gate-check-corpus plan exits 0; and a
master plan resolves its register links against its own directory and reads nothing else.

Stdlib only.
"""
import importlib.util
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "scripts", "validate-dispatch.py")
CORPUS = pathlib.Path(HERE) / "fixtures" / "dispatch-corpus"
GATE_CORPUS = pathlib.Path(HERE) / "fixtures" / "gate-check-corpus"

FAILURES = []


def check(cond, msg):
    if cond:
        print(f"  ok: {msg}")
    else:
        print(f"  FAIL: {msg}")
        FAILURES.append(msg)


def run(*args, cwd=None):
    """Run the script as a subprocess; return (rc, stdout, stderr)."""
    r = subprocess.run([sys.executable, SCRIPT, *map(str, args)],
                       capture_output=True, text=True, cwd=cwd)
    return r.returncode, r.stdout, r.stderr


def fail_lines(err, cls):
    return [ln for ln in err.splitlines() if ln.startswith("FAIL:") and f": {cls}:" in ln]


if not os.path.isfile(SCRIPT):
    print(f"FAILED — script missing: {SCRIPT}")
    sys.exit(1)

spec = importlib.util.spec_from_file_location("vd", SCRIPT)
vd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vd)


print("group 1 — the clean plan exits 0 and earns exactly the could-be-YES note")
rc, out, err = run(CORPUS / "ok-plan.md")
check(rc == 0, f"ok-plan.md exits 0 (got {rc}; stderr: {err.strip()[:200]})")
check("FAIL:" not in err, "ok-plan.md prints no FAIL line")
check(any("Task 2.1 could be YES" in ln and ln.startswith("note:")
          for ln in out.splitlines()),
      "a NO task with no same-stage deps and a disjoint Scope earns `could be YES`")
check("Task 1.3 could be YES" not in out,
      "a NO task with a same-stage dependency earns no could-be-YES note")
check("retired spelling" not in out, "a `Dispatch:` plan earns no retired-spelling note")


print("group 2 — each negative fixture fails with its own class")
for name, cls, who in [
    ("yes-same-stage-dep-plan.md", "YES-SAME-STAGE-DEP", "Task 1.2"),
    ("yes-shared-scope-plan.md", "YES-SHARED-SCOPE", "Task 1.1"),
    ("yes-no-scope-plan.md", "YES-NO-SCOPE", "Task 1.2"),
    ("stage-cycle-plan.md", "STAGE-CYCLE", "Stage 1"),
]:
    rc, out, err = run(CORPUS / name)
    lines = fail_lines(err, cls)
    check(rc == 1, f"{name} exits 1 (got {rc})")
    check(bool(lines) and all(name in ln for ln in lines),
          f"{name} prints a `FAIL: {name}: {cls}:` line")
    check(any(who in ln for ln in lines), f"the {cls} line names {who}")
    other = [ln for ln in err.splitlines() if ln.startswith("FAIL:") and f": {cls}:" not in ln]
    check(not other, f"{name} fails for {cls} only (other: {other[:2] or 'none'})")

rc, out, err = run(CORPUS / "master-yes-sibling-dep-master-plan.md")
lines = fail_lines(err, "MASTER-YES-SIBLING-DEP")
check(rc == 1, f"master-yes-sibling-dep-master-plan.md exits 1 (got {rc})")
check(any("Sub-plan 2" in ln for ln in lines),
      "a YES entry whose Gate reads an undeclared sibling fails (Sub-plan 2 — the openclaw shape)")
# Stage 3 Tier-2 Critical: `Depends on` orders the register, and fan-out after a shared
# prerequisite is the commonest real master shape (four coder-plugins masters). Reading a
# sibling you declared — directly or through your chain — is not a defect.
check(not any("MASTER-YES-SIBLING-DEP: Sub-plan 3 " in ln for ln in lines),
      "a YES entry that depends on Sub-plan 1 and gates on it does not fail (fan-out), "
      "and an HTML-comment amendment naming Sub-plan 2 in its gate is not a check")
check(not any("MASTER-YES-SIBLING-DEP: Sub-plan 4 " in ln for ln in lines),
      "a YES entry reading a sibling reached through its declared chain does not fail (4→3→1)")
check(not any("MASTER-YES-SIBLING-DEP: Sub-plan 1 " in ln for ln in lines),
      "a YES entry whose gate names a downstream consumer (Sub-plan 3, which depends on "
      "it) does not fail — that is a forward reference, not a dependency (Sub-plan 1)")


rc, out, err = run("--cutover", "2026-09-30", CORPUS / "yes-same-stage-dep-plan.md")
check(rc == 0 and "FAIL:" not in err
      and any(ln.startswith("note:") and "YES-SAME-STAGE-DEP" in ln for ln in out.splitlines()),
      f"before --cutover a same-stage YES dependency is a note, not a FAIL (rc {rc}) — "
      f"older plans used YES under looser conventions")

rc, out, err = run("--cutover", "2026-09-30", CORPUS / "yes-no-scope-plan.md")
check(rc == 0 and "YES-NO-SCOPE" not in err,
      f"YES-NO-SCOPE binds only plans dated on/after --cutover (rc {rc})")


print("group 3 — the retired `Parallel:` spelling: silent before cutover, a note after")
rc, out, err = run(CORPUS / "old-field-plan.md")
check(rc == 0 and not out.strip() and not err.strip(),
      f"dated before the default cutover: exit 0, silent (rc {rc}, out {out.strip()[:120]!r})")
rc, out, err = run("--cutover", "2026-09-01", CORPUS / "old-field-plan.md")
check(rc == 0, f"dated after --cutover: still exit 0 (got {rc})")
check(any(ln.startswith("note:") and "Parallel: is the retired spelling" in ln
          for ln in out.splitlines()),
      "dated after --cutover: `note: … Parallel: is the retired spelling`")
check("FAIL:" not in err, "the old spelling is read, never failed")
rc, out, err = run("--cutover", "2026-09-01", CORPUS / "ok-master-plan.md")
check("retired spelling" not in out,
      "a master register's `Parallel:` never earns the retired-spelling note")


print("group 4 — the clean master and its sub-plans")
rc, out, err = run(CORPUS / "ok-master-plan.md")
check(rc == 0, f"ok-master-plan.md exits 0 (got {rc}; stderr: {err.strip()[:200]})")
check("FAIL:" not in err, "ok-master-plan.md prints no FAIL line (handoff prose after "
                          "the gate block is not read as the gate)")

with tempfile.TemporaryDirectory() as d:
    plans = pathlib.Path(d) / "vault" / "plans"
    plans.mkdir(parents=True)
    for f in ("ok-master-plan.md", "ok-master-sub-01-plan.md", "ok-master-sub-02-plan.md"):
        shutil.copy(CORPUS / f, plans / f)
    # A decoy beside the sub-plans that FAILS if anything reads it. The master does not
    # link it, so a validator that globbed its directory would trip here.
    shutil.copy(CORPUS / "yes-no-scope-plan.md", plans / "ok-master-sub-03-plan.md")
    elsewhere = pathlib.Path(d) / "elsewhere"
    elsewhere.mkdir()
    rc, out, err = run(plans / "ok-master-plan.md", cwd=elsewhere)
    check(rc == 0 and "FAIL:" not in err,
          f"links resolve against the master's directory, not the cwd (rc {rc}, "
          f"stderr {err.strip()[:160]!r})")
    check("ok-master-sub-03" not in out + err, "an unlinked sibling file is never read")

    reads = []
    real_read = vd._read

    def spy(p):
        reads.append(pathlib.Path(p).resolve())
        return real_read(p)

    vd._read = spy
    try:
        vd.main([str(plans / "ok-master-plan.md")])
    finally:
        vd._read = real_read
    want = {(plans / f).resolve() for f in
            ("ok-master-plan.md", "ok-master-sub-01-plan.md", "ok-master-sub-02-plan.md")}
    check(set(reads) == want, f"reads exactly the master + its two linked sub-plans "
                              f"(read: {sorted(p.name for p in reads)})")

    # A task-level defect inside a linked sub-plan fails the master run, naming the sub-plan.
    sub2 = plans / "ok-master-sub-02-plan.md"
    sub2.write_text(sub2.read_text().replace(
        "- **Dispatch:** NO (blocked by 1.1)", "- **Dispatch:** YES"), encoding="utf-8")
    rc, out, err = run(plans / "ok-master-plan.md", cwd=elsewhere)
    lines = fail_lines(err, "YES-SAME-STAGE-DEP")
    check(rc == 1 and any("ok-master-sub-02-plan.md" in ln for ln in lines),
          "task-level checks run on each linked sub-plan and name the sub-plan file")

    missing = plans / "ok-master-sub-01-plan.md"
    missing.unlink()
    rc, out, err = run(plans / "ok-master-plan.md", cwd=elsewhere)
    check(rc == 2 and "ok-master-sub-01-plan.md" in err,
          f"a register link that does not resolve exits 2 naming it (rc {rc})")


print("group 4b — a descendant is exempt only as a hedged forward reference")
# Stage 3 round-1 Important: exempting every descendant hid a gate that REQUIRES a later
# sibling's output — a cycle (1 waits on 3, 3 depends on 1) the pre-fix code caught. A
# hedged mention ("can consume") stays a forward reference; an unhedged one is a wait-on.
with tempfile.TemporaryDirectory() as d:
    dd = pathlib.Path(d)
    sub = ("# Project Plan: sub\nDate: 2026-09-23\n\n## Stage 1: Only\n\n"
           "### Task 1.1: One\n- **Status:** [ ]\n- **Depends on:** none\n"
           "- **Blocks:** none\n- **Dispatch:** NO\n- **Test:** `true` exits 0\n")
    for i in (1, 3):
        (dd / f"s{i}-plan.md").write_text(sub, encoding="utf-8")

    def master(gate_line):
        return ("# Master Plan: descendant cases\nDate: 2026-09-23\n\n## Sub-plans\n\n"
                "### Sub-plan 1: One\n- **Status:** [ ]\n- **Plan:** ./s1-plan.md\n"
                "- **Depends on:** none\n- **Blocks:** Sub-plan 3\n- **Parallel:** YES\n\n"
                f"**Gate:**\n- [ ] {gate_line}\n\n"
                "### Sub-plan 3: Three\n- **Status:** [ ]\n- **Plan:** ./s3-plan.md\n"
                "- **Depends on:** Sub-plan 1\n- **Blocks:** none\n- **Parallel:** YES\n\n"
                "**Gate:**\n- [ ] `true` exits 0\n")
    hard = dd / "hard-master-plan.md"
    hard.write_text(master("Sub-plan 3's test suite has already passed against this "
                           "module's real output"), encoding="utf-8")
    rc, out, err = run(hard)
    check(rc == 1 and any("Sub-plan 1 " in ln for ln in fail_lines(err, "MASTER-YES-SIBLING-DEP")),
          f"a gate requiring a descendant's output fails (a cycle, not a forward reference) (rc {rc})")
    soft = dd / "soft-master-plan.md"
    soft.write_text(master("Sub-plan 3 can consume the module without importing anything "
                           "else"), encoding="utf-8")
    rc, out, err = run(soft)
    check(rc == 0, f"a hedged mention of a descendant ('can consume') passes (rc {rc})")


print("group 5 — the matcher's two named non-matches, and a light plan")
toks = vd.scope_tokens("`planning/skills/planning-projects/SKILL.md` (§ `## Checklist`; "
                       "`KNOWN_PHASES`), `references/task-fields.md` (§ Checklist)")
check(toks == ["planning/skills/planning-projects/SKILL.md", "references/task-fields.md"],
      f"parenthetical prose after a token is not a path (got {toks})")
check(not vd.paths_overlap("planning/skills/planning-projects/SKILL.md",
                           "planning/skills/executing-plans/SKILL.md"),
      "two different SKILL.md full paths are distinct")
check(vd.paths_overlap("SKILL.md", "planning/skills/executing-plans/SKILL.md"),
      "a bare filename matches a full path ending in it")
check(vd.paths_overlap("scripts/plan-progress.py",
                       "planning/skills/executing-plans/scripts/plan-progress.py"),
      "a shorter path matches a longer one ending in it after a `/`")
check(not vd.paths_overlap("progress.py", "scripts/plan-progress.py"),
      "a suffix that is not a whole path component does not match")
# Stage-dependency prose shapes that invented cycles in real vault plans before the
# parser read only the first clause.
check(vd.stage_refs("Stage 1 gate (policy available for Stage 3; can run early)") == [1],
      "a parenthetical after the dependency is not an edge")
check(vd.stage_refs("Stage 3 gate (sequencing only). **No code dependency on Stages 2–3**")
      == [3], "a later sentence denying a dependency is not an edge")
check(vd.stage_refs("Stages 1–3 gates") == [1, 2, 3], "a stage range expands")
check(vd._fields(["**Depends on:** Stage 1. **Blocks:** Stage 3, 4."])
      == {"depends on": "Stage 1."}, "two bold fields on one line split")
with tempfile.TemporaryDirectory() as d:
    p = pathlib.Path(d) / "2026-10-01-light-plan.md"
    p.write_text("# Project Plan: light\nDate: 2026-10-01\n\n## Stage 1: x\n\n"
                 "### Task 1.1: x\n- **Status:** [ ]\n- **Depends on:** none\n"
                 "- **Test:** `true`\n\n### Stage 1 Gate\n- [ ] `true`\n", encoding="utf-8")
    rc, out, err = run(p)
    check(rc == 0 and "FAIL:" not in err, f"a light plan without the field exits 0 (rc {rc})")
    rc, out, err = run(pathlib.Path(d) / "absent-plan.md")
    check(rc == 2 and "absent-plan.md" in err, f"an unreadable file exits 2 naming it (rc {rc})")


print("group 5b — an amendment note is history, not a gate reading a sibling")
# preflight-checks.md § Amending authored ceremony REQUIRES the `*(amended … was: …)*`
# note to cite its rule and keep the was-value, and that prose names sub-plans as
# narrative ("the live drive at the final gate (Sub-plan 3 below)"). Read as gate text,
# it failed writer-pad's 2026-09-08 master with an undeclared dependency it never had.
with tempfile.TemporaryDirectory() as d:
    for f in CORPUS.glob("ok-master*"):
        shutil.copy(f, d)
    m = pathlib.Path(d) / "ok-master-plan.md"
    m.write_text(m.read_text(encoding="utf-8").replace(
        "- [ ] `pytest alpha/tests/` exits 0 — Sub-plan 1's module imports cleanly",
        "- [ ] `pytest alpha/tests/` exits 0 — Sub-plan 1's module imports cleanly"
        " *(amended 2026-09-12 per `master-plan-format.md` § sub-plan gate, which puts the"
        " live drive at the final gate (Sub-plan 2 below). Was: `pytest alpha/`)*", 1),
        encoding="utf-8")
    rc, out, err = run(m)
    check(rc == 0 and not fail_lines(err, "MASTER-YES-SIBLING-DEP"),
          f"a sibling named only inside an amendment note is not a dependency (rc {rc}; {err.strip()[:200]})")

print("group 6 — every gate-check-corpus plan exits 0")
corpus = sorted(GATE_CORPUS.glob("*-plan.md"))
check(len(corpus) >= 3, f"gate-check corpus present ({len(corpus)} plan(s))")
for f in corpus:
    rc, out, err = run(f)
    check(rc == 0, f"{f.name} exits 0 (got {rc}; stderr: {err.strip()[:200]})")


print()
if FAILURES:
    print(f"FAILED — {len(FAILURES)} check(s):")
    for f in FAILURES:
        print(f"  {f}")
    sys.exit(1)
print("OK — validate-dispatch.py fails each defect class, notes the retired spelling and "
      "the could-be-YES task, and reads only the plans it is pointed at")
