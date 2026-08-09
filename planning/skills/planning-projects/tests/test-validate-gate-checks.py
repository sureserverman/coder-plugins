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
