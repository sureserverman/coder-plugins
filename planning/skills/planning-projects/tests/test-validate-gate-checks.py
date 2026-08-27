#!/usr/bin/env python3
"""Fixture suite for scripts/validate-gate-checks.py — run directly (CI convention):
    python3 planning/skills/planning-projects/tests/test-validate-gate-checks.py

Asserts the classifier's contract: every classification branch, the `(judgment)`
opt-out, the empty-sweep refusal, a gate-less plan refusing rather than passing,
and crash-resistance across two real corpora (the 18 plan-parser fixtures and
every real plan in the vault, when present).

It also pins the *measured* false-positive shapes. These were measured when the
corpus stood at 357 real gate checks — it is 374 now, since recognising master-plan
`**Gate:**` blocks later surfaced 17 more; the shapes below are unchanged by that
and the live pin below asserts the current figures. The entire false-positive
population was (a) a slash
inside ordinary prose ("pass/fail", "4/4", "skill/agent", "scan/rollup") matching a
path pattern, and (b) a bare script name (`validate-stack-routing.py`) not being
recognised as invoking a program. Both are regression-guarded below, because both
are the kind of thing a later "tightening" of the regex would silently reintroduce.

Stdlib only.
"""
import importlib.util
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "scripts", "validate-gate-checks.py")

spec = importlib.util.spec_from_file_location("vgc", SCRIPT)
vgc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vgc)

FAILURES = []


def check(cond, msg):
    if cond:
        print(f"  ok: {msg}")
    else:
        print(f"  FAIL: {msg}")
        FAILURES.append(msg)


def kind(text):
    return vgc.classify(text)[0]


def run(plan_text, extra=()):
    """Run the script as a subprocess on a temp plan; return (rc, out+err)."""
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "x-plan.md"
        p.write_text(plan_text, encoding="utf-8")
        r = subprocess.run([sys.executable, SCRIPT, *extra, str(p)],
                           capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr


def plan(*checks):
    body = "\n".join(f"- [ ] {c}" for c in checks)
    return f"# Project Plan: x\n\n## Stage 1: x\n\n### Stage 1 Gate\n{body}\n"


print("group 1 — every classification branch")
check(kind("`! grep -rl 'stale claim' android-dev/`") == "EXECUTABLE",
      "recursive grep over a directory is EXECUTABLE")
check(kind("`python3 scripts/check-doc-coverage.py` exits 0") == "EXECUTABLE",
      "invoking a program is EXECUTABLE")
check(kind("**(judgment)** reads coherently — a sweep cannot prove it") == "JUDGMENT",
      "the (judgment) marker classifies as JUDGMENT")
check(kind("**(scoped)** `! grep -l '^## BL-008 ' vault/infra/proj/backlog.md` — ids are "
           "unique within one register") == "SCOPED",
      "the (scoped) marker classifies as SCOPED")
check(kind("the README no longer claims the stack is not project-agnostic")
      == "INSTANCE-SHAPED",
      "prose naming one artifact is INSTANCE-SHAPED (the canonical BAD form)")
check(kind("`grep -q 'stale claim' android-dev/README.md` exits 1") == "INSTANCE-SHAPED",
      "an inspector scoped to one literal path is INSTANCE-SHAPED (the ALSO-BAD form)")
check(kind("Integration holds end to end") == "PROSE",
      "a claim naming no artifact is PROSE")

print("group 2 — the scope-not-syntax rule the classifier must not bless")
check(kind("`ls android-dev/README.md`") == "INSTANCE-SHAPED",
      "being a shell command does not make a single-path check compliant")
check(kind("`! grep -rl 'x' android-dev/ planning/`") == "EXECUTABLE",
      "a sweep over multiple directories is EXECUTABLE")
check(kind("`grep -c 'x' a.md b.md c.md`") == "EXECUTABLE",
      "an inspector over several paths is a sweep")

print("group 3 — measured false-positive shapes must never regress")
for text, why in [
    ("Fixtures pass/fail as designed.", "slash in prose: pass/fail"),
    ("Full test suite passes (4/4 green — regression)", "slash in a fraction: 4/4"),
    ("`executing-plans` + `planning-projects` reference the new skill/agent; links resolve.",
     "slash in prose: skill/agent"),
    ("Full test suites green (business scan/rollup + portfolio-unify)",
     "slash in prose: scan/rollup"),
    ("`validate-stack-routing.py` exits 0.", "bare script name is an invocation"),
    ("`portfolio-rebuild.py` dry-run against the real vault exits 0",
     "bare script name with prose args"),
]:
    check(kind(text) != "INSTANCE-SHAPED", f"no false positive — {why}")

print("group 4 — backticked names are not commands")
check(kind("Cross-skill coherence: `planning-projects` and `executing-plans` agree")
      == "PROSE",
      "backticked component names alone are not a command")
check(kind("`wait for confirmation` before merging README.md") == "INSTANCE-SHAPED",
      "backticked English prose is not a command ('for'/'awk' as substrings)")

print("group 4b — an invoker must not launder a single-path inspector")
check(kind('`bash -c "grep -q x one.md"` exits 0') == "INSTANCE-SHAPED",
      "bash -c wrapping a single-path grep is still INSTANCE-SHAPED")
check(kind("`python3 -c \"import json; json.load(open('one.md'))\"` succeeds")
      == "INSTANCE-SHAPED",
      "python3 -c wrapping a single-path read is still INSTANCE-SHAPED")
check(kind('`bash -c "grep -rl x plugins/"` finds nothing') == "EXECUTABLE",
      "bash -c wrapping a real sweep is EXECUTABLE")
# The inline-script rule must not VETO a command that is plural for its own reasons.
# First implementation judged the payload as the whole story, which wrongly flagged a
# pipeline that happened to contain `python3 -c` as its last stage.
check(kind("`python3 scripts/dump.py --format json | python3 -c \"import sys; assert sys.stdin.read()\"`")
      == "EXECUTABLE",
      "an inline script inside a pipeline does not veto the pipeline's own scope")
check(kind("`grep -c 'x' a.md b.md c.md`") == "EXECUTABLE",
      "grep's -c count flag is not mistaken for an interpreter's -c")

print("group 4c — a command must not carry an unverified prose claim")
check(kind("`python3 scripts/smoke.py` exits 0 and the README.md changelog entry reads correctly")
      == "INSTANCE-SHAPED",
      "a command plus a claim about a DIFFERENT artifact is INSTANCE-SHAPED")
check(kind("`python3 scripts/smoke.py` exits 0") == "EXECUTABLE",
      "the same command alone stays EXECUTABLE")

print("group 4d — wrapped checks are joined before classifying")
# Reading only the first line changes the verdict in BOTH directions. Both of these
# are real shapes from this repo's plan corpus (28 wrapped bullets across 7 plans).
wrapped_exec = (
    "### Stage 1 Gate\n"
    "- [ ] Capability index fresh: `python3 scripts/build-capability-index.py --write &&\n"
    "      git diff --exit-code capability-index.json`\n")
got = vgc.gate_checks(wrapped_exec)
check(len(got) == 1 and got[0].endswith("capability-index.json`"),
      "a wrapped command is joined into one check")
check(kind(got[0]) == "EXECUTABLE",
      "joined, the wrapped command is EXECUTABLE (truncated, it read INSTANCE-SHAPED)")
wrapped_inst = (
    "### Stage 1 Gate\n"
    "- [ ] Version mirrors consistent: `grep -c 'x'\n"
    "      planning/.claude-plugin/plugin.json` = 1\n")
got2 = vgc.gate_checks(wrapped_inst)
check(len(got2) == 1 and "plugin.json" in got2[0],
      "the path on the continuation line is not lost")
check(kind(got2[0]) == "INSTANCE-SHAPED",
      "joined, the single-path inspector is caught (truncated, it read PROSE and passed)")
check(len(vgc.gate_checks("### Stage 1 Gate\n- [ ] a\n- [ ] b\n")) == 2,
      "consecutive bullets are not accidentally joined")

print("group 4e — the heading contract is not over-matched")
check(vgc.gate_checks("### Task 1.1: Gate `podman build` on image presence\n- [ ] a\n") == [],
      "a task heading merely containing the word Gate is not a gate section")
check(len(vgc.gate_checks("### Stage 2 Gate\n- [ ] a\n")) == 1, "Stage N Gate matches")
check(len(vgc.gate_checks("#### Gate\n- [ ] a\n")) == 1, "a bare Gate heading matches")

print("group 5 — exit codes and the empty-sweep refusal")
rc, out = run(plan("`! grep -rl 'x' plugins/`"))
check(rc == 0 and "instance-shaped 0" in out, "a clean plan exits 0 and reports counts")
rc, out = run(plan("the README no longer claims X"))
check(rc == 1 and "instance-shaped 1" in out, "an instance-shaped check exits 1")
check("names one artifact" in out, "the failure names why, not just that")
rc, out = run("# Project Plan: x\n\n## Stage 1: x\n\nNo gate here at all.\n")
check(rc == 2 and "0 gate checks" in out,
      "a plan with no gate checks exits 2 — an empty sweep must not read as a pass")
rc, out = run(plan("`! grep -rl 'x' p/`"), extra=("--quiet",))
check(rc == 0 and "gate check(s) across" in out, "--quiet still reports the totals")
r = subprocess.run([sys.executable, SCRIPT, "/nonexistent/nope.md"],
                   capture_output=True, text=True)
check(r.returncode == 2 and "not a file" in r.stderr, "a missing file exits 2 clearly")

print("group 6 — crash resistance across real corpora")
repo = pathlib.Path(HERE).parents[3]
fixtures = sorted((repo / "planning/skills/portfolio/tests/fixtures/plan-parser").glob("*.md"))
check(len(fixtures) >= 18, f"plan-parser fixture corpus present ({len(fixtures)} files)")
r = subprocess.run([sys.executable, SCRIPT, "--quiet", *map(str, fixtures)],
                   capture_output=True, text=True)
check(r.returncode in (0, 1) and "gate check(s) across" in r.stdout,
      "the 18 plan-parser fixtures classify without a traceback")
check("Traceback" not in r.stderr, "no traceback on legacy/edge-case plan shapes")

# The frozen calibration corpus, in-repo. Group 9 pins the docstring against THIS, so the
# figures move only when someone deliberately edits the fixture directory — see its
# PROVENANCE.md. The live vault sweep below stays, but purely as an informational rate.
corpus = sorted((repo / "planning/skills/planning-projects/tests/fixtures"
                 / "gate-check-corpus").glob("*-plan.md"))

vault = pathlib.Path("/mnt/vault/Portfolio/ai-tools/coder-plugins/plans")
real = sorted(vault.glob("*.md")) if vault.is_dir() else []
if real:
    r = subprocess.run([sys.executable, SCRIPT, "--quiet", *map(str, real)],
                       capture_output=True, text=True)
    check("Traceback" not in r.stderr,
          f"no traceback across {len(real)} real plans")
    tot = [l for l in r.stdout.splitlines() if "gate check(s) across" in l]
    check(bool(tot), "real-corpus run reports a total")
    if tot:
        # Informational, not asserted: these plans predate the rule, so a nonzero
        # count is legacy non-compliance rather than a classifier defect. Printed so
        # a later precision regression is visible in CI output.
        print(f"       corpus rate (informational): {tot[-1].strip()}")
else:
    print("       skip: vault plan corpus not present on this machine")

print("group 6b — a path-inspecting tool must not launder single-path scope")
# `git`, `sed`, `jq`, `cat`, `head`, `tail` read exactly the paths given, so they are
# INSPECTORS, not opaque program runners. Classing them as runners let them pass the
# very shape the rule calls "ALSO BAD".
for text, exp, why in [
    ("`git grep -q 'x' -- android-dev/README.md` exits 1", "INSTANCE-SHAPED", "git grep on one file"),
    ("`sed -n '1,5p' android-dev/README.md` no longer shows the claim", "INSTANCE-SHAPED", "sed on one file"),
    ("`git grep -rl 'x' -- planning/`", "EXECUTABLE", "git grep over a directory still sweeps"),
    ("`pytest tests/test_one.py` passes", "EXECUTABLE", "a test runner's scope stays opaque"),
]:
    check(kind(text) == exp, f"{why} → {exp}")

print("group 7 — pipe plurality requires a plural SOURCE")
check(kind('`cat CHANGELOG.md | bash -c "grep -q x CHANGELOG.md"`') == "INSTANCE-SHAPED",
      "a single-file pipe source does not launder a single-path inspector")
check(kind('`echo hi | bash -c "grep -q x one.md"`') == "INSTANCE-SHAPED",
      "an opaque-but-scalar pipe source does not either")
check(kind('`python3 scripts/dump.py | python3 -c "import sys; assert sys.stdin.read()"`')
      == "EXECUTABLE",
      "a program on the source side of the pipe still sweeps")

print("group 8 — the join stops at content that is not a wrap")
para = ("### Stage 1 Gate\n"
        "- [ ] Some check here\n"
        "  Note: added because of X, see the discussion above for context.\n"
        "- [ ] Another check\n")
got = vgc.gate_checks(para)
check(len(got) == 2 and got[0] == "Some check here",
      "an indented explanatory Note: is not glued onto the check")
fence = ("### Stage 1 Gate\n"
         "- [ ] Some check here\n"
         "  ```bash\n  grep -q x one.md\n  ```\n")
check(vgc.gate_checks(fence)[0] == "Some check here",
      "an indented fenced code block is not absorbed as continuation")
check(vgc.gate_checks("### Stage 1 Gate\n- [ ] `grep -c 'x'\n      a/b.md` = 1\n")[0]
      .endswith("a/b.md` = 1"),
      "a genuine mid-backtick wrap is still joined")

print("group 8b — a declared Scope: must be swept, not merely named")


def scoped_plan(scope_line, *checks):
    """A one-stage plan whose task optionally declares a Scope:."""
    body = "\n".join(f"- [ ] {c}" for c in checks)
    scope = f"- **Scope:** {scope_line}\n" if scope_line else ""
    return ("# Project Plan: x\n\n## Stage 1: x\n\n### Task 1.1: t\n"
            "- **Status:** [ ]\n" + scope +
            "- **Test:** `python3 t.py`\n\n### Stage 1 Gate\n" + body + "\n")


rc, out = run(scoped_plan("every commands/*.md", "the README no longer claims X"))
check("was named, not swept" in out,
      "a stage declaring Scope: whose gate has no executable sweep is reported")

rc2, out2 = run(scoped_plan("every commands/*.md",
                            "`! grep -rl 'X' commands/`"))
check("was named, not swept" not in out2,
      "a stage declaring Scope: WITH an executable sweep is not reported")

# The sanctioned SECOND shape: a (judgment)-marked check covers a declared Scope: too.
rc_j, out_j = run(scoped_plan("every commands/*.md",
                              "**(judgment)** every command doc reads coherently"))
check("was named, not swept" not in out_j,
      "a Scope: covered by a (judgment) check is NOT flagged — both sanctioned shapes count")

# The asymmetry that must hold: a plan predating the field reports exactly as before.
legacy = plan("the README no longer claims X")
rc3, out3 = run(legacy)
check("was named, not swept" not in out3,
      "a plan with NO Scope: field anywhere is never given the scope note")
check(rc3 == 1 and "instance-shaped" in out3.lower(),
      "and it is still classified exactly as before (no retro-failure, no new failure)")

# The note is advisory: it must not change an exit code in either direction.
rc4, _ = run(scoped_plan("every commands/*.md", "`python3 sweep.py`"))
check(rc4 == 0, "the scope note alone never fails a plan whose checks are clean")
rc5, out5 = run(scoped_plan("every commands/*.md", "the README no longer claims X"))
rc6, _ = run(plan("the README no longer claims X"))
check(rc5 == rc6,
      "exit code is identical with and without the Scope: field — advisory, not a gate")

print("group 2b — (scoped) rescues the narrow-but-correct check without widening the default")
# The marker exists because widening a claim past the set it is over does not make the check
# stricter — it makes it unpassable. The check that motivated it swept a whole portfolio for a
# backlog ID unique to one project's register, matched two dozen unrelated entries, and could
# never go green. What must NOT happen is the marker becoming a general waiver, so both halves
# are pinned: the marked check passes, and the identical check without it still fails.
_scoped = "`! grep -l '^## BL-008 ' vault/infra/proj/backlog.md`"
check(kind(f"**(scoped)** {_scoped} — one register is the whole set") == "SCOPED",
      "a marked single-path check is SCOPED, not INSTANCE-SHAPED")
check(kind(f"{_scoped} — one register is the whole set") == "INSTANCE-SHAPED",
      "the SAME check unmarked still fails — the marker is the assertion, not the path shape")
check(run(plan(f"**(scoped)** {_scoped} — one register is the whole set"))[0] == 0,
      "a plan whose only check is (scoped) exits 0")
check(run(plan(f"{_scoped} — one register is the whole set"))[0] == 1,
      "the same plan unmarked exits 1")

print("group 8c — SELECTOR-UNMATCHED: a gate selector no task builds toward")
# The defect this catches has shipped twice, most recently in remote-agents bot-live-view
# sub-01, whose Stage 1 gate named a real e2e file with a `-k` filter collecting zero tests
# in it. A gate nobody can pass is not caught by any shape rule — the check is a perfectly
# well-formed EXECUTABLE sweep. Hence a separate axis, pinned in BOTH directions here.


def plan_with_task(test_field, *checks):
    """A plan whose single task declares `test_field`, plus the given gate checks."""
    body = "\n".join(f"- [ ] {c}" for c in checks)
    return (f"# Project Plan: x\n\n## Stage 1: x\n\n"
            f"#### Task 1.1 — t\n\n- **Status:** [ ]\n- **Test:** {test_field}\n\n"
            f"### Stage 1 Gate\n{body}\n")


_unmatched = plan_with_task("`pytest tests/foo.py -k parses` — it parses",
                            "`pytest tests/foo.py -k nothing` — the goal, end to end")
_matched = plan_with_task("`pytest tests/foo.py -k parses` — it parses",
                          "`pytest tests/foo.py -k parses` — the goal, end to end")
check(len(vgc.unmatched_selectors(_unmatched)) == 1,
      "a gate -k selector no task declares is SELECTOR-UNMATCHED")
check(vgc.unmatched_selectors(_matched) == [],
      "the same selector passes when a task's Test: declares it")
check(run(_unmatched)[0] == 1, "a plan with an unmatched selector exits 1")
check(run(_matched)[0] == 0, "a plan whose selectors all match a task exits 0")
check("selector-unmatched" in run(_unmatched)[1],
      "the failure is reported under its own name, not folded into the shape classes")
# The wrong-file case and the typo case are distinguishable, and the message says which.
check("different -k filter" in run(_unmatched)[1],
      "a declared file with a different filter is named as the typo case it is")
# A bare whole-file run is legitimate — a regression sweep over an existing suite. Pinning
# this prevents the obvious over-tightening, which would flag every ordinary gate.
check(vgc.unmatched_selectors(
        plan_with_task("`pytest tests/foo.py -k parses`",
                       "`pytest tests/regression.py` — no regressions")) == [],
      "a bare pytest file run with no -k is never a selector")
# Both markers exempt, on the same bargain they make everywhere else in this script.
for marker in ("(judgment)", "(scoped)"):
    check(vgc.unmatched_selectors(
            plan_with_task("`pytest tests/foo.py -k parses`",
                           f"**{marker}** `pytest tests/bar.py -k later` — author asserts")) == [],
          f"a {marker} check is exempt from the selector cross-reference")
# False-positive shapes. These matter more than the true positives: this check is wired into
# the mandatory pre-presentation checklist, so a false positive does not merely miss a defect,
# it blocks a correct plan from being presented — the opposite failure from the one the class
# exists to fix. Both were found by Tier-2 review of the first implementation.
check(vgc.pytest_selectors("`pytest tests/a.py -k foo && pytest tests/b.py -k bar`")
      == [("tests/a.py", "foo"), ("tests/b.py", "bar")],
      "chained invocations keep each path with its OWN -k filter")
check(vgc.unmatched_selectors(
        "# P\n\n## Stage 1: x\n\n"
        "#### Task 1.1 — a\n\n- **Test:** `pytest tests/a.py -k foo`\n\n"
        "#### Task 1.2 — b\n\n- **Test:** `pytest tests/b.py -k bar`\n\n"
        "### Stage 1 Gate\n- [ ] `pytest tests/a.py -k foo && pytest tests/b.py -k bar`\n") == [],
      "a chained gate check whose every invocation is task-declared is not flagged")
check(vgc.pytest_selectors("`pytest tests/x.py -k restart --cov=src/mod.py`")
      == [("tests/x.py", "restart")],
      "a .py value of a --flag= is not a selector path (coverage targets are not test files)")
check(vgc.unmatched_selectors(
        "# P\n\n## Stage 1: x\n\n"
        "#### Task 1.1 — a\n\n- **Test:** `pytest tests/x.py -k restart`\n\n"
        "### Stage 1 Gate\n- [ ] `pytest tests/x.py -k restart --cov=src/mod.py` with coverage\n") == [],
      "a coverage-annotated gate running the declared selector is not flagged")
# A master plan carries no tasks, so every selector in its cross-plan gates would flag —
# 3 of the 5 portfolio-wide flags on the day this check shipped were one master plan.
_master = ("# Master Plan: x\n\n## Sub-plans\n\n### 1. sub-01\n\n"
           "**Gate:** \n- [ ] `pytest tests/e2e/test_x.py -k restart` — the integrated proof\n")
check(vgc.unmatched_selectors(_master) == [],
      "a master plan's selectors are not flagged — its tasks live in its sub-plans")
check(vgc.is_master_plan("# Master Plan: x") and
      vgc.is_master_plan("", path="2026-01-01-topic-master-plan.md"),
      "both master signals are recognised (heading and filename), matching portfolio-unify")
check(vgc.unmatched_selectors(_master.replace("# Master Plan: x", "# Project Plan: x")) != [],
      "the SAME document as a non-master still flags — the skip is the master's, not a waiver")

# The real historical instance, reproduced: the file exists in the plan's world, the filter
# matches nothing in it, and no task builds toward it.
check(len(vgc.unmatched_selectors(plan_with_task(
        "`pytest tests/integration/test_live_service.py -k durable` — a durable token",
        "`pytest tests/e2e/test_telegram_fake_backend.py -k restart` — a button survives "
        "a restart"))) == 1,
      "the remote-agents bot-live-view sub-01 gate would have been caught at authoring")

print("group 10 — TASK-TEST-UNSCOPED: an unbounded task Test: on an expensive-suite plan")
# The measured incident: a task whose `Test:` read `uv run --locked pytest -m 'not
# requires_session'` ran ~3.5 h against a 3132-test collection, inside one Red-Green loop,
# while the same plan's declared stage-scope command took ~7 min. No tier governed it —
# the tiers govern GATES, fix-scope is derived per fix, and a task field had no upstream
# check at all. Task 3.1 retracted the "task fields are scoped by construction" claim;
# this is the check that replaces it.
#
# Scope of the check, pinned in BOTH directions because a false positive here blocks a
# correct plan from being presented (the mandatory pre-presentation checklist runs it):
# it fires ONLY on a plan that declares stage-scope AND plan-scope commands, i.e. one
# whose project is over guard rail 1's ~5 min threshold. Everything else is untouched.


def tiered_plan(test_field, task_extra="", tiers=True):
    """A plan declaring expensive-suite tiering, with one task carrying `test_field`."""
    block = ("**Test-scope commands** (per references/test-scope-tiers.md):\n"
             "- stage-scope: `pytest tests/unit`\n"
             "- plan-scope:  `pytest`\n\n") if tiers else ""
    return (f"# Project Plan: x\n\n## Preflight\n\n{block}"
            f"## Stage 1: x\n\n"
            f"### Task 1.1: t\n\n- **Status:** [ ]\n- **Test:** {test_field}\n"
            f"{task_extra}\n\n"
            f"### Stage 1 Gate\n- [ ] `pytest tests/` passes\n")


def n_unscoped(text, path=None):
    return len(vgc.unscoped_task_tests(text, path))


# --- the true positives -------------------------------------------------------------
check(n_unscoped(tiered_plan("`pytest` passes")) == 1,
      "a bare `pytest` task Test: on a tiered plan is TASK-TEST-UNSCOPED")
check(n_unscoped(tiered_plan("`uv run --locked pytest -m 'not requires_session'`")) == 1,
      "the measured incident's own command is flagged — a DESELECTOR is not a scope")
check(n_unscoped(tiered_plan("`./gradlew test`")) == 1,
      "a bare `./gradlew test` is flagged too — the class is runners, not pytest")

# --- the exemptions -----------------------------------------------------------------
for field, why in [
    ("`pytest tests/unit/test_parse.py`", "a positional path bounds what is collected"),
    ("`pytest -k parses`", "a -k filter bounds it"),
    ("`pytest tests/unit/test_parse.py::test_one`", "a node id bounds it"),
    ("`pytest -m unit`", "a marker SELECTOR bounds it (unlike `-m 'not x'`)"),
    ("`./gradlew :features:test`", "a gradle task path bounds it"),
    ("`./gradlew test --tests '*ParserTest'`", "--tests bounds it"),
]:
    check(n_unscoped(tiered_plan(field)) == 0, f"scoped: {why}")

check(n_unscoped(tiered_plan("`pytest`", "\n- **full-suite: accepted** — cross-cutting")) == 0,
      "an explicit `full-suite: accepted` on the task exempts it — the author priced it")

# --- guard rail 1: a cheap-suite plan is untouched -----------------------------------
check(n_unscoped(tiered_plan("`pytest`", tiers=False)) == 0,
      "a plan that declares NO tiering is not checked at all (guard rail 1: below the "
      "~5 min threshold there is nothing to bound)")
# Found in the frozen corpus before this check was written: a plan can carry the block
# heading and use it to say the opposite. `**Test-scope commands:** not tiered — the full
# suite is 3.9s` must not arm the check, or the guard fires hardest on the author who
# documented the threshold decision most carefully.
check(n_unscoped("# Project Plan: x\n\n**Test-scope commands:** not tiered — the full "
                 "suite is 3.9s, well under the ~5 min threshold.\n\n## Stage 1: x\n\n"
                 "### Task 1.1: t\n\n- **Test:** `pytest`\n\n"
                 "### Stage 1 Gate\n- [ ] `pytest tests/` passes\n") == 0,
      "a 'not tiered' declaration does not arm the check — the block heading is not the "
      "trigger, the stage-scope/plan-scope commands are")

# --- a master plan carries no tasks --------------------------------------------------
check(n_unscoped("# Master Plan: x\n\n**Test-scope commands**\n- stage-scope: `pytest a`\n"
                 "- plan-scope: `pytest`\n\n## Sub-plans\n\n### 1. sub-01\n\n"
                 "**Gate:** \n- [ ] `pytest` — integrated\n") == 0,
      "a master plan is skipped — its tasks live in its sub-plans, same as the selector check")

# --- non-runner commands are not the class -------------------------------------------
for field in ["`grep -q x README.md`", "`python3 scripts/check-versions.py`",
              "`bash scripts/run-tests.sh`"]:
    check(n_unscoped(tiered_plan(field)) == 0,
          f"a non-suite-runner command is not flagged: {field}")

# --- measured false-positive shapes, pinned ------------------------------------------
# Measured over 602 real vault plans. The first implementation flagged 21 fields; 15 were
# false positives — 14 Gradle (any `gradlew` invocation read as unbounded, `--version`
# included) and 1 `cargo test --no-run`, which compiles the tests and runs none. These
# matter more than the true positives: this check is wired into the MANDATORY
# pre-presentation checklist, so a false positive does not merely miss a defect, it blocks
# a correct plan from being presented. After the fix: 6 flags, 6 true positives
# (`cargo test` x3, `pytest -q` x2, `./gradlew check assembleDebug` — so Gradle keeps a
# true positive too; the family is read correctly, not disarmed).
#
# The same figures are stated in the script's GRADLE_AGGREGATE comment. They are cited in
# two files, so they are written once and copied — an earlier draft had 12 here and 15
# there, which is the citation-mismatch class DEC-005 is about.
for field, why in [
    ("`git rev-parse --is-inside-work-tree && ./gradlew --version | rg 'Gradle 9.5'`",
     "`gradlew --version` runs no tests at all"),
    ("`./gradlew verifyArchitecture`", "a specifically named Gradle task IS its own scope"),
    ("`./gradlew verifyArchitecture verifyArchitectureFixtures`", "two named tasks, still scoped"),
    ("`./gradlew securityTest verifyNoSensitiveLogging -PlargeTests=true`",
     "a named test task is not an aggregate lifecycle task"),
    ("`./gradlew benchmarkRelease -PlargeTests=true`", "likewise for a benchmark task"),
    ("`./gradlew projects && ./gradlew :poetry:test :app:assembleDebug`",
     "a chained invocation is judged per link, and both links are bounded"),
    ("`./gradlew :app:connectedDebugAndroidTest "
     "-Pandroid.testInstrumentationRunnerArguments.class=dev.x.Y`",
     "the instrumentation class filter bounds an Android device run"),
    ("`./phone/gradlew -p phone :app:testDebugUnitTest --tests '*SnapshotStoreTest'`",
     "a wrapper reached by path, with -p and --tests, is bounded"),
    ("`make bootstrap-check && cargo test --workspace --no-run && make lint`",
     "`--no-run` compiles the tests and runs none of them"),
    ("`xcodebuild -scheme App build`", "xcodebuild without a `test` action runs no suite"),
]:
    check(n_unscoped(tiered_plan(field)) == 0, f"not flagged: {why}")

# And the aggregates that ARE unbounded, so the fix above did not simply disarm Gradle.
for field in ["`./gradlew check assembleDebug`", "`./gradlew test`",
              "`./gradlew connectedCheck`"]:
    check(n_unscoped(tiered_plan(field)) == 1,
          f"still flagged — an aggregate lifecycle task collects everything: {field}")

# --- gaps review found in the first cut, pinned so they cannot come back ---------------
check(n_unscoped(tiered_plan("`npm run test`")) == 1,
      "`npm run test` is flagged — adjacency made the commoner shape invisible")
check(n_unscoped(tiered_plan("`npm test`")) == 1, "`npm test` still flagged")
check(n_unscoped(tiered_plan("`./gradlew testProductionReleaseUnitTest`")) == 1,
      "a product-flavor unit-test variant is an aggregate — matched by SHAPE, because the "
      "flavor/build-type matrix generates names no literal list can enumerate")
check(n_unscoped(tiered_plan("`./gradlew connectedStagingDebugAndroidTest`")) == 1,
      "the same for a flavored connected-test variant")
check(n_unscoped(tiered_plan("`./gradlew securityTest`")) == 0,
      "a named task that merely CONTAINS 'Test' is still its own scope")

# The exemption must be ATTACHED to a field. Prose that DENIES it must not grant it —
# the same defect the sibling contract suite's RETRACTED exclusion exists to stop.
check(n_unscoped(tiered_plan(
        "`pytest`", "\n- **Note:** we deliberately did not mark this `full-suite: accepted`")) == 1,
      "a sentence denying the exemption does not grant it")
check(n_unscoped(tiered_plan(
        "`pytest`  (full-suite: accepted — cross-cutting)")) == 0,
      "the inline form on the Test: line exempts — it is what test-scope-tiers.md documents")
check(n_unscoped(tiered_plan("`pytest`", "\n- **full-suite: accepted** — cross-cutting")) == 0,
      "the field form exempts too")

# The report names the INVOCATION, not the whole backticked span: a chained command is
# usually mostly fine and unbounded in one link.
_flag = vgc.unscoped_task_tests(tiered_plan("`make lint && pytest -q && make docs`"))
check(len(_flag) == 1 and _flag[0][1] == "pytest -q",
      "the message names the offending invocation, not the line it sits in")

# --- exit codes and reporting --------------------------------------------------------
rc, out = run(tiered_plan("`pytest` passes"))
check(rc == 1, "a plan with an unscoped task Test: exits 1")
check("task-test-unscoped" in out.lower(),
      "the failure is reported under its own name, on its own axis")
check(run(tiered_plan("`pytest tests/unit/test_parse.py`"))[0] == 0,
      "the same plan with a scoped task Test: exits 0")
check(run(tiered_plan("`pytest`", "\n- **full-suite: accepted** — cross-cutting"))[0] == 0,
      "the flagged fixture exits 0")

print("group 9 — the docstring's calibration numbers match the frozen corpus")
# Unconditional: the corpus is in the repo, so this runs everywhere the suite runs —
# including CI, where the old vault-conditioned version skipped silently and pinned
# nothing. A missing corpus is now a failure rather than a skip, because an absent
# fixture directory is a defect in the repo, not a property of the machine.
check(bool(corpus), "frozen calibration corpus present "
                    f"({len(corpus)} plan(s) in tests/fixtures/gate-check-corpus/)")
import collections
frozen = collections.Counter()
for f in corpus:
    for c in vgc.gate_checks(f.read_text()):
        frozen[vgc.classify(c)[0]] += 1
doc = vgc.__doc__
for label in ("EXECUTABLE", "JUDGMENT", "INSTANCE-SHAPED", "PROSE"):
    # Every class must be represented, or the corpus silently stops testing that branch
    # while the count still "matches" at zero.
    check(frozen[label] > 0, f"corpus exercises the {label} branch")
    check(f"{frozen[label]} {label}" in doc,
          f"docstring states the corpus {label} count ({frozen[label]})")
check(f"{sum(frozen.values())} gate checks" in doc,
      f"docstring states the corpus total ({sum(frozen.values())})")

print()
if FAILURES:
    print(f"FAILED — {len(FAILURES)} check(s):")
    for f in FAILURES:
        print(f"  {f}")
    sys.exit(1)
print("OK — validate-gate-checks.py classifies every branch, honors the (judgment) "
      "opt-out, refuses an empty sweep, and holds its measured precision")
