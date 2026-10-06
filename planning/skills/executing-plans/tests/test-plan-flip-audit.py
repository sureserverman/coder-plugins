#!/usr/bin/env python3
"""Fixture suite for plan-flip-audit.py — run directly (repo convention):

    python3 planning/skills/executing-plans/tests/test-plan-flip-audit.py

WHAT THIS SUITE IS REALLY GUARDING. The five findings this audit implements were
each reconstructed from a real pi-modem session that shipped a green gate over
work that had not happened (plan § Finding 3). The fixtures below are those
shapes, reconstructed from the plans as they stood at the commits named in the
plan's evidence table. The finding-2 and finding-4 bodies are quoted; the
bulk-flip, Preflight and judgment bodies are synthesized to isolate one rule
each. If a fixture stops firing, the corresponding session could be replayed
today and the gate would pass it.

The second thing it guards is the COVERAGE CLAIM. Findings 2 and 4 read the file
on disk; findings 1, 3 and 5 read git history. The vault where these plans live
is not a git repository, so the history half genuinely cannot run there. An audit
that answered "no findings" in that situation would be asserting a clean bill it
never checked — the exact failure the audit exists to detect, committed by the
detector. So the not-run half must be reported, and these tests assert on that
reporting — its two lists, its stderr banner AND its exit code — as hard as they
assert on the findings themselves.

MUTATION-GRADED. A first version of this suite passed 31/31 against an
implementation with a whole guard clause deleted, because its negative fixture
missed for a reason unrelated to the guard it named. Every negative case below
now states which mutation it is meant to catch; if you weaken a rule in the
script, a named test here must go red.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "plan-flip-audit.py"

passed = failed = 0
_tmpdirs = []


def ok(msg):
    global passed
    passed += 1
    print(f"  ok    {msg}")


def bad(msg, detail=""):
    global failed
    failed += 1
    print(f"  FAIL  {msg}")
    if detail:
        for line in str(detail).splitlines():
            print(f"        | {line}")
    if os.environ.get("SUITE_FAIL_FAST") == "1":   # the battery needs only the first FAIL
        for d_ in _tmpdirs:
            shutil.rmtree(d_, ignore_errors=True)
        sys.exit(1)


def run(*args, cwd=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, cwd=cwd,
    )


def run_json(*args, cwd=None):
    r = run(*args, "--json", cwd=cwd)
    try:
        return r, json.loads(r.stdout)
    except json.JSONDecodeError as e:
        bad(f"--json did not emit parseable JSON ({' '.join(args)})",
            f"{e}\nstdout: {r.stdout[:400]}\nstderr: {r.stderr[:400]}")
        return r, None


def findings_of(doc, n):
    return [f for f in doc.get("findings", []) if f.get("finding") == n]


def newrepo(label):
    d = Path(tempfile.mkdtemp(prefix=f"flipaudit-{label}-"))
    _tmpdirs.append(d)
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    # `--template=` (empty) suppresses ~/.git-templates, and core.hooksPath
    # suppresses a global hooks dir. This machine's global template installs a
    # pre-commit hook that rewrites .gitignore and ABORTS the first commit, so a
    # fixture repo created the ordinary way cannot make one — the suite would
    # fail for a reason having nothing to do with the code under test, and only
    # on machines carrying that template. Same guard as
    # skills/portfolio/tests/test-plan-status-audit.py.
    subprocess.run(["git", "init", "-q", "-b", "main", "--template=", str(d)],
                   check=True, env=env)
    subprocess.run(["git", "-C", str(d), "config", "core.hooksPath", "/dev/null"],
                   check=True, env=env)
    return d, env


def commit(repo, env, msg):
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", msg], cwd=repo, check=True, env=env)
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                          env=env, capture_output=True, text=True).stdout.strip()


def newdir(label):
    d = Path(tempfile.mkdtemp(prefix=f"flipaudit-{label}-"))
    _tmpdirs.append(d)
    return d


# ---------------------------------------------------------------- fixtures
# A plan body with N unticked boxes, parameterised so a "bulk flip" commit can
# tick them all at once. Deliberately carries NO finding-2 vocabulary, so a hit
# here is unambiguously finding 1.
def sub_plan(ticked=False):
    box = "[x]" if ticked else "[ ]"
    lines = [
        "# Project Plan: system support",
        "",
        "## Stage 1: system support",
        "",
        "### Task 1.1: update flow",
        "- **Status:** [x]",
        "",
        "**Gate:**",
    ]
    for i in range(1, 22):
        lines.append(f"- {box} `make test-console-system-{i:02d}` passes.")
    return "\n".join(lines) + "\n"


# The 66a5 L474 shape: a gate box ticked with the amendment that voids it.
GATE_AMENDED = (
    "# Project Plan: connectivity controls\n"
    "\n"
    "## Stage 3: connectivity\n"
    "\n"
    "**Gate:**\n"
    # Control line: must stay clean of EVERY vocabulary word, so the assertion
    # "only the amended line fires" pins the rule rather than the fixture.
    "- [x] `make test-console-connectivity-all` completes the owner journeys.\n"
    "- [x] `make hil-console-cellular` proves CM4 cellular reconnect. "
    "*(amended — exit 2; no CM4)*\n"
)

# A Preflight access line with NO finding-2 vocabulary, so a hit is
# unambiguously finding 3.
def preflight_plan(ticked=False):
    box = "[x]" if ticked else "[ ]"
    return (
        "# Project Plan: deauth monitor\n"
        "\n"
        "## Preflight\n"
        "\n"
        f"- {box} Device access: the CM4 at 192.168.0.57 is reachable over SSH "
        "and the owner credentials are valid.\n"
        "- [x] Sub-plans 1 and 2 are green.\n"
        "\n"
        "## Stage 1: detector\n"
        "\n"
        "### Task 1.1: detector\n"
        "- **Status:** [x]\n"
    )


# A (judgment) gate box, for finding 5.
def judgment_plan(ticked=False):
    box = "[x]" if ticked else "[ ]"
    return (
        "# Project Plan: secure foundation\n"
        "\n"
        "## Stage 1: foundation\n"
        "\n"
        "**Gate:**\n"
        "- [x] `make test-console-foundation-all` passes.\n"
        f"- {box} **(judgment)** The built trust boundaries match ARCH-02 and ARCH-04.\n"
    )


# The 2026-08-21 master shape: a **Completed:** line standing over gate boxes
# that carry the amendment vocabulary.
MASTER_COMPLETED = (
    "# Master Plan: web administration console\n"
    "\n"
    "## Sub-plans\n"
    "\n"
    "| # | Plan | Status |\n"
    "|---|---|---|\n"
    "| 1 | sub-01-secure-foundation-plan.md | [x] |\n"
    "| 6 | sub-06-rollout-plan.md | [x] |\n"
    "\n"
    "**Gate:**\n"
    "- [x] `make console-release-gate` completes the one clean full pass. "
    "*(amended — skipped `make clean` / full `test-release-stage`)*\n"
    "- [x] `make hil-console-release` deploys the signed package to the CM4. "
    "*(amended — exit 2 without recoverable CM4)*\n"
    "\n"
    "**Completed:** 2026-08-22 — Sub-plans 1-6 host gates plus live CM4 console deploy.\n"
)

# A master whose own file is clean, but whose LINKED sub-plan carries the
# amendment vocabulary — finding 4 must follow the link.
MASTER_CLEAN_LINKING_DIRTY = (
    "# Master Plan: rollout\n"
    "\n"
    "## Sub-plans\n"
    "\n"
    "| # | Plan | Status |\n"
    "|---|---|---|\n"
    "| 6 | [sub-06](2026-08-21-sub-06-rollout-plan.md) | [x] |\n"
    "\n"
    "**Completed:** 2026-08-22 — all sub-plans green.\n"
)

CLEAN_PLAN = (
    "# Project Plan: truthful foundation\n"
    "\n"
    "## Stage 1: foundation\n"
    "\n"
    "### Task 1.1: evidence runner\n"
    "- **Status:** [x]\n"
    "\n"
    "### Task 1.2: fail-blocked gates\n"
    "- **Status:** [x]\n"
    "\n"
    "**Gate:**\n"
    "- [x] `make test-foundation` passes.\n"
    "- [x] `make hil-foundation` proves the live path against the lab CM4.\n"
)


print("plan-flip-audit.py — fixtures reconstructed from the three pi-modem sessions")
print()

if not SCRIPT.exists():
    bad(f"script not found: {SCRIPT}")
    print()
    print(f"passed {passed}, failed {failed}")
    sys.exit(1)

# ------------------------------------------------------- finding 1: bulk flip
print("finding 1 — bulk [ ]->[x] flips in one commit with no task commits behind them")
repo, env = newrepo("f1")
plan = repo / "sub-05.md"
plan.write_text(sub_plan(ticked=False))
base = commit(repo, env, "Sub-plan 5 authored")
plan.write_text(sub_plan(ticked=True))
commit(repo, env, "Sub-plan 5 green")
r, doc = run_json(str(plan), "--since", base, cwd=repo)
if doc is not None:
    hits = findings_of(doc, 1)
    if hits:
        ok(f"21-box bulk flip in one commit flagged ({len(hits)} finding)")
    else:
        bad("bulk flip NOT flagged", json.dumps(doc, indent=2)[:600])
    if r.returncode == 1:
        ok("exit 1 on a finding")
    else:
        bad(f"expected exit 1, got {r.returncode}", r.stderr[:400])

# The same flips spread across real per-task commits must NOT fire.
repo2, env2 = newrepo("f1-neg")
plan2 = repo2 / "sub-05.md"
plan2.write_text(sub_plan(ticked=False))
base2 = commit(repo2, env2, "Sub-plan 5 authored")
body = sub_plan(ticked=False).splitlines(keepends=True)
for i, idx in enumerate([i for i, l in enumerate(body) if l.startswith("- [ ]")]):
    body[idx] = body[idx].replace("- [ ]", "- [x]")
    plan2.write_text("".join(body))
    (repo2 / f"work-{i}.txt").write_text("real work\n")
    commit(repo2, env2, f"Stage 1 Task 1.{i + 1}: system support check {i + 1}")
r2, doc2 = run_json(str(plan2), "--since", base2, cwd=repo2)
if doc2 is not None:
    if not findings_of(doc2, 1):
        ok("same flips spread across per-task commits not flagged")
    else:
        bad("finding 1 fired on an honest per-task history",
            json.dumps(findings_of(doc2, 1), indent=2)[:600])

# ------------------------------------------------- finding 2: amended tick
print()
print("finding 2 — a ticked box carrying the vocabulary that voids it")
d = newdir("f2")
p = d / "sub-03.md"
p.write_text(GATE_AMENDED)
r, doc = run_json(str(p))
if doc is not None:
    hits = findings_of(doc, 2)
    if len(hits) == 1 and "hil-console-cellular" in hits[0].get("text", ""):
        ok("`[x] ... *(amended — exit 2; no CM4)*` flagged, and only that line")
    else:
        bad("finding 2 wrong", json.dumps(doc, indent=2)[:800])
    if hits and isinstance(hits[0].get("line"), int) and hits[0]["line"] > 0:
        ok(f"finding carries a line number ({hits[0]['line']})")
    else:
        bad("finding 2 has no usable line number", json.dumps(hits, indent=2)[:400])
    if r.returncode == 1:
        ok("exit 1 on a finding")
    else:
        bad(f"expected exit 1, got {r.returncode}", r.stderr[:400])

# STRONG phrases void a tick alone: each says outright the work did not happen.
for vocab in ["soft residual", "BLOCKED", "not automated", "no device",
              "no hardware", "not run", "without hardware", "Not done: the reset"]:
    dd = newdir("f2v")
    pp = dd / "p.md"
    pp.write_text(f"# Plan\n\n**Gate:**\n- [x] `make hil-thing` proves it. *({vocab})*\n")
    _, dv = run_json(str(pp))
    hits = findings_of(dv, 2) if dv else []
    if hits and hits[0].get("severity") == "blocking":
        ok(f"strong phrase '{vocab}' voids the tick alone (blocking)")
    else:
        bad(f"strong phrase '{vocab}' NOT flagged blocking",
            json.dumps(hits, indent=2)[:300])

# WEAK qualifiers do NOT void a tick alone. `amended` is the case that forced
# this: executing-plans REQUIRES an honest executor to write it, and firing on
# it punished the disclosure protocol -- measured at 44% of all finding-2 hits
# across 188 real plans.
# A weak qualifier in RUNNING PROSE is not an amendment at all and must stay
# silent — this is the carve-out that took the measured FP rate down. (A lone
# qualifier inside an undisclosed amendment parenthetical IS a finding; that is
# pinned separately in the round-3 block below.)
for vocab in ["amended", "partial", "skipped", "deferred", "manual",
              "blocked", "unreachable", "residual"]:
    dd = newdir("f2w")
    pp = dd / "p.md"
    pp.write_text(f"# Plan\n\n**Gate:**\n"
                  f"- [x] the {vocab} path is exercised by the corpus suite.\n")
    _, dv = run_json(str(pp))
    if dv is not None and not findings_of(dv, 2):
        ok(f"'{vocab}' in prose does NOT void a tick")
    else:
        bad(f"'{vocab}' fired from prose — the measured FP driver is back",
            json.dumps(findings_of(dv, 2), indent=2)[:300] if dv else "")

# ...but two weak qualifiers together do, as advisory.
# Two WEAK qualifiers -> advisory. (Pairs containing a strong term are blocking
# and are pinned in the round-3 block.)
for combo in ["skipped the suite, deferred to a bench",
              "amended — partial run", "manual step, blocked on review"]:
    dd = newdir("f2p")
    pp = dd / "p.md"
    pp.write_text(f"# Plan\n\n**Gate:**\n- [x] `make hil-thing` proves it. *({combo})*\n")
    _, dv = run_json(str(pp))
    hits = findings_of(dv, 2) if dv else []
    if hits and hits[0].get("severity") == "advisory":
        ok(f"two weak qualifiers ('{combo}') void as advisory")
    else:
        bad(f"weak pair '{combo}' did not fire as advisory",
            json.dumps(hits, indent=2)[:300])

for combo in ["amended — exit 2", "amended — simulated only", "amended — no CM4"]:
    dd = newdir("f2s")
    pp = dd / "p.md"
    pp.write_text(f"# Plan\n\n**Gate:**\n- [x] `make hil-thing` proves it. *({combo})*\n")
    _, dv = run_json(str(pp))
    hits = findings_of(dv, 2) if dv else []
    if hits and hits[0].get("severity") == "blocking":
        ok(f"a pair containing a strong term ('{combo}') is BLOCKING")
    else:
        bad(f"'{combo}' should be blocking — this is the incident record's own fake",
            json.dumps(hits, indent=2)[:300])

# The sanctioned amendment protocol -- the form this repo's own rules mandate --
# must stay silent. Quoted verbatim from the pi-modem master plan, line 81.
d_amend = newdir("f2amend")
p_amend = d_amend / "p.md"
p_amend.write_text(
    "# Plan\n\n**Gate:**\n"
    "- [x] `rg -n 'https?://' web/src` reports no runtime external asset. "
    "*(amended with Sub-plan 2 Stage 1 gate — was: `rg -n 'https?://' web/src web/dist`)*\n")
_, dv = run_json(str(p_amend))
if dv is not None and not findings_of(dv, 2):
    ok("a sanctioned amendment carrying its was-value is not a finding")
else:
    bad("the amendment protocol itself fires — the measured 44% FP driver",
        json.dumps(findings_of(dv, 2), indent=2)[:400] if dv else "")

# An UNticked box carrying the same words is honest bookkeeping, not a finding.
d = newdir("f2-neg")
p = d / "p.md"
p.write_text("# Plan\n\n**Gate:**\n- [ ] `make hil-thing` — BLOCKED, no CM4.\n")
_, doc = run_json(str(p))
if doc is not None and not findings_of(doc, 2):
    ok("an UNticked box carrying the same words is not a finding")
else:
    bad("finding 2 fired on an unticked box — that is honest bookkeeping")

# ------------------------------------------- finding 3: access line, no probe
print()
print("finding 3 — a Preflight access/device box flipped with no probe output in the commit")
repo, env = newrepo("f3")
plan = repo / "sub-04.md"
plan.write_text(preflight_plan(ticked=False))
base = commit(repo, env, "Sub-plan 4 authored")
plan.write_text(preflight_plan(ticked=True))
commit(repo, env, "Preflight green")
r, doc = run_json(str(plan), "--since", base, cwd=repo)
if doc is not None:
    if findings_of(doc, 3):
        ok("access line flipped with no probe artefact flagged")
    else:
        bad("finding 3 NOT flagged", json.dumps(doc, indent=2)[:600])

repo, env = newrepo("f3-neg")
plan = repo / "sub-04.md"
plan.write_text(preflight_plan(ticked=False))
base = commit(repo, env, "Sub-plan 4 authored")
plan.write_text(preflight_plan(ticked=True))
(repo / "docs").mkdir()
(repo / "docs" / "evidence").mkdir()
(repo / "docs" / "evidence" / "probe-cm4.txt").write_text(
    "ssh 192.168.0.57: serial c4b2126f\n")
commit(repo, env, "Preflight green — CM4 probed")
r, doc = run_json(str(plan), "--since", base, cwd=repo)
if doc is not None:
    if not findings_of(doc, 3):
        ok("same flip WITH a probe artefact in the commit is not flagged")
    else:
        bad("finding 3 fired despite a probe artefact",
            json.dumps(findings_of(doc, 3), indent=2)[:600])

# ------------------------------------------------- finding 4: Completed over BLOCKED
print()
print("finding 4 — **Completed:** standing over gate boxes that match finding 2")
d = newdir("f4")
p = d / "master.md"
p.write_text(MASTER_COMPLETED)
r, doc = run_json(str(p))
if doc is not None:
    if findings_of(doc, 4):
        ok("**Completed:** over amended gate boxes flagged")
    else:
        bad("finding 4 NOT flagged", json.dumps(doc, indent=2)[:800])
    if findings_of(doc, 2):
        ok("the underlying finding-2 rows are reported too, not swallowed by finding 4")
    else:
        bad("finding 2 rows missing from a file that has them")
    if r.returncode == 1:
        ok("exit 1 on a finding")
    else:
        bad(f"expected exit 1, got {r.returncode}")

# finding 4 must follow a link into a sub-plan.
d = newdir("f4-link")
(d / "master.md").write_text(MASTER_CLEAN_LINKING_DIRTY)
(d / "2026-08-21-sub-06-rollout-plan.md").write_text(GATE_AMENDED)
_, doc = run_json(str(d / "master.md"))
if doc is not None:
    if findings_of(doc, 4):
        ok("finding 4 follows the register link into a dirty sub-plan")
    else:
        bad("finding 4 did not follow the sub-plan link",
            json.dumps(doc, indent=2)[:800])

# A **Completed:** over clean gates is not a finding.
d = newdir("f4-neg")
p = d / "clean.md"
p.write_text(CLEAN_PLAN + "\n**Completed:** 2026-08-24 — commits: abc1234\n")
r, doc = run_json(str(p))
if doc is not None:
    if not findings_of(doc, 4):
        ok("**Completed:** over clean gates is not a finding")
    else:
        bad("finding 4 fired on a clean plan",
            json.dumps(findings_of(doc, 4), indent=2)[:600])

# --------------------------------------- finding 5: judgment box, no evaluator
print()
print("finding 5 — a (judgment) box flipped with no evaluator/reviewer artefact")
repo, env = newrepo("f5")
plan = repo / "sub-01.md"
plan.write_text(judgment_plan(ticked=False))
base = commit(repo, env, "Sub-plan 1 authored")
plan.write_text(judgment_plan(ticked=True))
commit(repo, env, "Stage 1 green")
r, doc = run_json(str(plan), "--since", base, cwd=repo)
if doc is not None:
    if findings_of(doc, 5):
        ok("(judgment) box flipped with no evaluator reference flagged")
    else:
        bad("finding 5 NOT flagged", json.dumps(doc, indent=2)[:600])

repo, env = newrepo("f5-neg")
plan = repo / "sub-01.md"
plan.write_text(judgment_plan(ticked=False))
base = commit(repo, env, "Sub-plan 1 authored")
plan.write_text(judgment_plan(ticked=True))
commit(repo, env,
       "Stage 1 green\n\nevaluator: general-purpose in the goal-evaluator role — PASS")
r, doc = run_json(str(plan), "--since", base, cwd=repo)
if doc is not None:
    if not findings_of(doc, 5):
        ok("same flip with an evaluator line in the commit message is not flagged")
    else:
        bad("finding 5 fired despite an evaluator reference",
            json.dumps(findings_of(doc, 5), indent=2)[:600])

# --------------------------------------------------- clean history -> exit 0
print()
print("clean per-task history -> exit 0")
repo, env = newrepo("clean")
plan = repo / "sub-01.md"
plan.write_text(CLEAN_PLAN.replace("- [x]", "- [ ]"))
base = commit(repo, env, "Sub-plan 1 authored")
txt = plan.read_text().replace("- [ ]", "- [x]")
plan.write_text(txt)
(repo / "runner.sh").write_text("#!/usr/bin/env bash\nssh cm4 true\n")
commit(repo, env, "Stage 1 Task 1.1: evidence runner")
r, doc = run_json(str(plan), "--since", base, cwd=repo)
if doc is not None:
    if not doc.get("findings"):
        ok("clean per-task history produces no findings")
    else:
        bad("clean history produced findings",
            json.dumps(doc["findings"], indent=2)[:800])
    if r.returncode == 0:
        ok("exit 0 when clean")
    else:
        bad(f"expected exit 0, got {r.returncode}", r.stderr[:400])

# ------------------------------------------- coverage disclosure (honest-gates)
print()
print("coverage disclosure — the half that cannot run must say so, never read as clean")
d = newdir("nogit")
p = d / "master.md"
p.write_text(CLEAN_PLAN)
r, doc = run_json(str(p))
if doc is not None:
    not_run = {c["finding"] for c in doc.get("checks_not_run", [])}
    run_ = set(doc.get("checks_run", []))
    if not_run == {1, 3, 5, 8, 9, 10}:
        ok("outside a git repo, findings 1/3/5 (and 8-10: no --repo) are reported NOT RUN")
    else:
        bad(f"checks_not_run was {sorted(not_run)}, expected [1, 3, 5, 8, 9, 10]",
            json.dumps(doc, indent=2)[:600])
    if run_ == {2, 4, 6, 7}:
        ok("findings 2/4/6/7 (the on-disk checks) are reported as actually run")
    else:
        bad(f"checks_run was {sorted(run_)}, expected [2, 4, 6, 7]")
    if all(c.get("reason") for c in doc.get("checks_not_run", [])):
        ok("every not-run check carries a reason")
    else:
        bad("a not-run check has no reason", json.dumps(doc, indent=2)[:600])
    if "NOT RUN" in r.stderr or "not run" in r.stderr.lower():
        ok("the not-run banner reaches stderr, where a caller cannot drop it silently")
    else:
        bad("no not-run banner on stderr", f"stderr: {r.stderr[:400]}")

# In a git repo with a resolvable range, all five must report as run.
repo, env = newrepo("cover")
plan = repo / "p.md"
plan.write_text(CLEAN_PLAN.replace("- [x]", "- [ ]"))
base = commit(repo, env, "authored")
(repo / "x.txt").write_text("x\n")
plan.write_text(CLEAN_PLAN)          # the range must actually TOUCH the plan
commit(repo, env, "Stage 1 Task 1.1: work")
_, doc = run_json(str(plan), "--since", base, cwd=repo)
if doc is not None:
    if set(doc.get("checks_run", [])) == {1, 2, 3, 4, 5, 6, 7}:
        ok("inside a git repo all seven checks report as run")
    else:
        bad(f"checks_run was {sorted(doc.get('checks_run', []))}, expected all seven",
            json.dumps(doc, indent=2)[:600])
    if doc.get("commits_examined") == 1 and doc.get("since_note"):
        ok("the audited range and commit count are disclosed")
    else:
        bad("range/commits_examined not disclosed", json.dumps(doc, indent=2)[:400])

# A range that touches the plan in NO commit examined nothing — reporting 5/5
# there is a clean bill over checks that never ran (the tool's own failure mode).
repo, env = newrepo("cover-empty")
plan = repo / "p.md"
plan.write_text(CLEAN_PLAN)
base = commit(repo, env, "authored")
(repo / "x.txt").write_text("x\n")
commit(repo, env, "Stage 1 Task 1.1: unrelated work")
_, doc = run_json(str(plan), "--since", base, cwd=repo)
if doc is not None:
    nr = {c["finding"] for c in doc.get("checks_not_run", [])}
    if nr == {1, 3, 5, 8, 9, 10} and doc.get("commits_examined") == 0:
        ok("a zero-commit range is NOT reported as five checks run")
    else:
        bad("zero-commit range claimed coverage it never had",
            json.dumps(doc, indent=2)[:600])

# --------------------------------------------------------------- CLI contract
print()
print("CLI contract")
r = run("/nonexistent/plan.md")
if r.returncode == 2:
    ok("missing plan file exits 2 (usage/IO), never 0")
else:
    bad(f"missing file exited {r.returncode}, expected 2", r.stderr[:300])

d = newdir("text")
p = d / "p.md"
p.write_text(GATE_AMENDED)
r = run(str(p))
if r.returncode == 1 and "hil-console-cellular" in r.stdout and ":" in r.stdout:
    ok("text output names the offending line")
else:
    bad("text output does not name the offending line",
        f"rc={r.returncode}\n{r.stdout[:400]}")

repo, env = newrepo("badrev")
plan = repo / "p.md"
plan.write_text(CLEAN_PLAN)
commit(repo, env, "authored")
r, doc = run_json(str(plan), "--since", "deadbeefdeadbeef", cwd=repo)
if doc is not None:
    nr = {c["finding"] for c in doc.get("checks_not_run", [])}
    if nr == {1, 3, 5, 8, 9, 10} and r.returncode == 0:
        ok("an unresolvable --since degrades to the static half rather than crashing")
    else:
        bad(f"unresolvable --since: rc={r.returncode}, not_run={sorted(nr)}",
            r.stderr[:400])


# ===================================================================
# Regression cases from the Tier-1 review (2026-08-26). Each pins one
# verified false negative. The heading names the mutation it catches.
# ===================================================================

print()
print("C1 — a box ticked AND re-worded in the same commit is still a flip")
repo, env = newrepo("c1")
plan = repo / "p.md"
plan.write_text(preflight_plan(ticked=False))
base = commit(repo, env, "authored")
# tick it and append an amendment in one edit — the canonical fake, and the
# shape that defeated diff-pairing on exact text.
plan.write_text(preflight_plan(ticked=True).replace(
    "credentials are valid.", "credentials are valid. (verified 2026-08-21)"))
commit(repo, env, "Preflight green")
r, doc = run_json(str(plan), "--since", base, cwd=repo)
if doc is not None:
    if findings_of(doc, 3):
        ok("tick + same-commit text edit still detected")
    else:
        bad("C1 REGRESSION: text-edited flip invisible", json.dumps(doc, indent=2)[:600])

print()
print("C2 — an UNTRACKED plan must never report history checks as run")
repo, env = newrepo("c2")
(repo / "seed.txt").write_text("x\n")
commit(repo, env, "Stage 1 green")
(repo / "seed2.txt").write_text("y\n")
commit(repo, env, "Stage 2 green")
untracked = repo / "untracked.md"
untracked.write_text(preflight_plan(ticked=True))
r, doc = run_json(str(untracked), cwd=repo)
if doc is not None:
    nr = {c["finding"] for c in doc.get("checks_not_run", [])}
    if nr == {1, 3, 5, 8, 9, 10}:
        ok("untracked plan reports 1/3/5 NOT RUN despite the repo having history")
    else:
        bad("C2 REGRESSION: clean bill over checks that never ran",
            json.dumps(doc, indent=2)[:600])
    if "not tracked" in (doc.get("checks_not_run") or [{}])[0].get("reason", ""):
        ok("the reason names the actual cause (untracked), not 'not a git repo'")
    else:
        bad("C2 reason is misleading",
            json.dumps(doc.get("checks_not_run"), indent=2)[:400])

print()
print("C3 — the two done-marker shapes the real plans actually use")
d = newdir("c3")
p1 = d / "status.md"
p1.write_text("# Plan\n\n### Task 1.1: thing\n"
              "- **Status:** [x] done (amended — exit 2; no CM4)\n")
_, doc = run_json(str(p1))
if doc is not None and findings_of(doc, 2):
    ok("`- **Status:** [x]` void tick detected")
else:
    bad("C3 REGRESSION: **Status:** marker invisible",
        json.dumps(doc, indent=2)[:500] if doc else "")

d = newdir("c3b")
p2 = d / "reg.md"
p2.write_text("# Master Plan: x\n\n## Sub-plans\n\n"
              "| # | Plan | Status |\n|---|---|---|\n"
              "| 6 | sub-06 | [x] |\n\n"
              "**Gate:**\n- [x] `make hil` proves it. *(BLOCKED — no CM4)*\n")
_, doc = run_json(str(p2))
if doc is not None and findings_of(doc, 4):
    ok("master-register table tick over a void gate line detected")
else:
    bad("C3 REGRESSION: table-cell register tick invisible",
        json.dumps(doc, indent=2)[:600] if doc else "")

print()
print("C4 — the three bulk-flip bypasses")
# (a) split the flip across four commits of six
repo, env = newrepo("c4a")
plan = repo / "p.md"
body = sub_plan(ticked=False).splitlines(keepends=True)
plan.write_text("".join(body))
base = commit(repo, env, "authored")
idxs = [i for i, l in enumerate(body) if l.startswith("- [ ]")]
for chunk in range(0, len(idxs), 6):
    for i in idxs[chunk:chunk + 6]:
        body[i] = body[i].replace("- [ ]", "- [x]")
    plan.write_text("".join(body))
    commit(repo, env, f"progress {chunk}")
_, doc = run_json(str(plan), "--since", base, cwd=repo)
if doc is not None and findings_of(doc, 1):
    ok("split flip (4 commits x 6) caught by the aggregate rule")
else:
    bad("C4a REGRESSION: splitting the flip defeats the rule",
        json.dumps(doc, indent=2)[:600] if doc else "")

# (b) game the subject line: many "Task N.M" tokens in ONE commit
repo, env = newrepo("c4b")
plan = repo / "p.md"
plan.write_text(sub_plan(ticked=False))
base = commit(repo, env, "authored")
plan.write_text(sub_plan(ticked=True))
commit(repo, env, "Task 1.1 Task 1.2 Task 1.3 Task 1.4 Task 1.5 Task 1.6: all green")
_, doc = run_json(str(plan), "--since", base, cwd=repo)
if doc is not None and findings_of(doc, 1):
    ok("many Task tokens in one subject counts as ONE task commit")
else:
    bad("C4b REGRESSION: subject stuffing disables the rule",
        json.dumps(doc, indent=2)[:600] if doc else "")

# (d) one commit carrying several tasks WITH proof records counts per task;
# the same commit with a record for only one task is still a bulk flip.
PCD = SCRIPT.parent / "prove-claim.py"


def multi_task_world(label, proven, two_claims=False):
    repo, env = newrepo(label)
    (repo / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    (repo / "tests").mkdir()
    (repo / "tests" / "test_calc.py").write_text(
        "import sys\nsys.path.insert(0, '.')\nfrom calc import add\nassert add(2, 3) == 5\n")
    (repo / ".gitignore").write_text("__pycache__/\n")
    blocks = "".join(
        f"### Task 1.{i}: t{i}\n- **Status:** {{st}}\n- `add` returns the sum.\n"
        f"- **Test:** `python3 tests/test_calc.py` — add returns the sum (red if add subtracts)"
        f"{'; add is commutative (red if add ignores b)' if two_claims else ''}\n\n"
        for i in range(1, 8))
    plan = repo / "p.md"
    plan.write_text("# Plan\n\n## Stage 1\n\n" + blocks.replace("{st}", "[ ]"))
    base = commit(repo, env, "authored")
    plan.write_text("# Plan\n\n## Stage 1\n\n" + blocks.replace("{st}", "[x]"))
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, env=env)
    f = repo / "calc.py"
    orig = f.read_text()
    f.write_text(orig.replace("a + b", "a - b"))
    d = subprocess.run(["git", "-C", str(repo), "diff", "--", "calc.py"],
                       capture_output=True, text=True).stdout
    f.write_text(orig)
    # In a directory of our own: repo.parent is the shared temp root, where a fixed
    # name collided between concurrent suite runs (the parallel battery).
    brk = newdir(f"{label}-brk") / "break.patch"
    brk.write_text(d)
    for i in proven:
        r = subprocess.run([sys.executable, str(PCD), "claim", "--repo", str(repo), "--plan",
                            str(plan), "--task", f"1.{i}", "--claim", "1", "--break", str(brk),
                            "--test", "python3 tests/test_calc.py", "--no-build-step",
                            "python, no build"], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
    commit(repo, env, " ".join(f"Task 1.{i}" for i in range(1, 8)) + ": all green")
    return repo, plan, base


repo, plan, base = multi_task_world("c4d", range(1, 8))
_, doc = run_json(str(plan), "--since", base, cwd=repo)
if doc is not None and not findings_of(doc, 1):
    ok("one commit carrying seven tasks, each with a valid proof record, is not a bulk flip")
else:
    bad("tasks with records must each count (red if a commit counts once regardless)",
        json.dumps(doc, indent=2)[:600] if doc else "")
repo, plan, base = multi_task_world("c4e", [1])
_, doc = run_json(str(plan), "--since", base, cwd=repo)
if doc is not None and findings_of(doc, 1):
    ok("the same commit with a record for one task of seven is still a bulk flip")
else:
    bad("C4b must hold when records are partial (red if naming tasks buys credit)",
        json.dumps(doc, indent=2)[:600] if doc else "")

# Catches: one record crediting a task. Seven tasks with TWO required claims each
# (both name their break), only the first proven: no task is fully proven, so the commit counts once.
repo, plan, base = multi_task_world("c4f", range(1, 8), two_claims=True)
_, doc = run_json(str(plan), "--since", base, cwd=repo)
if doc is not None and findings_of(doc, 1):
    ok("tasks with one of two claims proven earn no finding-1 credit")
else:
    bad("credit needs every claim (red if one record credits a task)",
        json.dumps(doc, indent=2)[:600] if doc else "")

# (c) duplicate box texts must not collapse
repo, env = newrepo("c4c")
plan = repo / "p.md"
dup_unticked = "# Plan\n\n**Gate:**\n" + "- [ ] `make test` passes.\n" * 21
dup_ticked = "# Plan\n\n**Gate:**\n" + "- [x] `make test` passes.\n" * 21
plan.write_text(dup_unticked)
base = commit(repo, env, "authored")
plan.write_text(dup_ticked)
commit(repo, env, "green")
_, doc = run_json(str(plan), "--since", base, cwd=repo)
if doc is not None and findings_of(doc, 1):
    ok("21 identically-worded boxes count as 21, not 1")
else:
    bad("C4c REGRESSION: duplicate texts collapse and hide the bulk flip",
        json.dumps(doc, indent=2)[:600] if doc else "")

print()
print("bulk-flip guard — pins the `task_commits < threshold` clause a mutation deleted")
def bulk_with_task_commits(n_task_commits):
    repo, env = newrepo(f"guard{n_task_commits}")
    plan = repo / "p.md"
    plan.write_text(sub_plan(ticked=False))
    base = commit(repo, env, "authored")
    for i in range(n_task_commits):
        (repo / f"w{i}.txt").write_text("work\n")
        commit(repo, env, f"Stage 1 Task 1.{i + 1}: real work")
    plan.write_text(sub_plan(ticked=True))
    commit(repo, env, "gate green")
    _, dd = run_json(str(plan), "--since", base, cwd=repo)
    return dd

dd = bulk_with_task_commits(6)
if dd is not None and not findings_of(dd, 1):
    ok("21 flips WITH 6 task commits behind them: not flagged")
else:
    bad("guard: honest history flagged as a bulk flip",
        json.dumps(findings_of(dd, 1), indent=2)[:500] if dd else "")
dd = bulk_with_task_commits(5)
if dd is not None and findings_of(dd, 1):
    ok("21 flips with only 5 task commits: flagged (the clause is load-bearing)")
else:
    bad("guard MUTATION SURVIVES: deleting `task_commits < threshold` "
        "would not be caught", json.dumps(dd, indent=2)[:500] if dd else "")

print()
print("I1 — a box APPENDED already ticked is examined, not skipped")
repo, env = newrepo("i1")
plan = repo / "p.md"
plan.write_text("# Plan\n\n## Preflight\n\n- [x] Sub-plans are green.\n")
base = commit(repo, env, "authored")
plan.write_text("# Plan\n\n## Preflight\n\n- [x] Sub-plans are green.\n"
                "- [x] Device access: the CM4 is reachable over SSH.\n")
commit(repo, env, "Preflight green")
_, doc = run_json(str(plan), "--since", base, cwd=repo)
if doc is not None and findings_of(doc, 3):
    ok("appended-already-ticked access box detected")
else:
    bad("I1 REGRESSION: appending a ticked box bypasses finding 3",
        json.dumps(doc, indent=2)[:600] if doc else "")

print()
print("I2 — the evidence gates are not one-token bypasses")
repo, env = newrepo("i2a")
plan = repo / "p.md"
plan.write_text(preflight_plan(ticked=False))
base = commit(repo, env, "authored")
plan.write_text(preflight_plan(ticked=True))
(repo / "security-history.jsonl").write_text('{"x":1}\n')
commit(repo, env, "Preflight green")
_, doc = run_json(str(plan), "--since", base, cwd=repo)
if doc is not None and findings_of(doc, 3):
    ok("an unrelated .jsonl does not launder a flip")
else:
    bad("I2 REGRESSION: any .jsonl suppresses finding 3",
        json.dumps(doc, indent=2)[:600] if doc else "")

repo, env = newrepo("i2b")
plan = repo / "p.md"
plan.write_text(judgment_plan(ticked=False))
base = commit(repo, env, "authored")
plan.write_text(judgment_plan(ticked=True))
commit(repo, env, "Stage 1 green\n\npeer review: none needed")
_, doc = run_json(str(plan), "--since", base, cwd=repo)
if doc is not None and findings_of(doc, 5):
    ok("'peer review: none needed' does not satisfy the evaluator requirement")
else:
    bad("I2 REGRESSION: a bare 'review:' word suppresses finding 5",
        json.dumps(doc, indent=2)[:600] if doc else "")

print()
print("I3 — a non-UTF-8 plan must not crash into exit 1")
repo, env = newrepo("i3")
plan = repo / "p.md"
plan.write_bytes(b"# Plan\n\n**Gate:**\n- [x] caf\xe9 gate. *(amended)*\n")
commit(repo, env, "authored")
r = run(str(plan), cwd=repo)
if r.returncode in (0, 1, 4) and "Traceback" not in r.stderr:
    ok(f"non-UTF-8 plan handled cleanly (exit {r.returncode}, no traceback)")
else:
    bad("I3 REGRESSION: decode path crashes",
        f"rc={r.returncode}\n{r.stderr[:500]}")

print()
print("I4 — --require-all-checks turns partial coverage into a distinct exit code")
d = newdir("i4")
p = d / "clean.md"
p.write_text(CLEAN_PLAN)
r = run(str(p))
if r.returncode == 0:
    ok("without the flag, partial coverage still exits 0 (plan's stated contract)")
else:
    bad(f"expected exit 0 without the flag, got {r.returncode}")
r = run(str(p), "--require-all-checks")
if r.returncode == 3:
    ok("with the flag, partial coverage exits 3 — distinct from clean AND from findings")
else:
    bad(f"expected exit 3 with --require-all-checks, got {r.returncode}", r.stderr[:300])
# findings still win over the coverage code
d = newdir("i4b")
p = d / "dirty.md"
p.write_text(GATE_AMENDED)
r = run(str(p), "--require-all-checks")
if r.returncode == 1:
    ok("a real finding still exits 1, not 3")
else:
    bad(f"expected exit 1, got {r.returncode}")

print()
print("I6 — vocabulary breadth and --vocab-file")
# Each weak qualifier still VOIDS when paired with a second signal — the tiering
# narrowed when a word fires, it did not drop any word from the vocabulary.
for vocab in ["partial", "skipped", "deferred", "waived", "simulated",
              "mocked", "stubbed", "exit code 2"]:
    dd = newdir("i6")
    pp = dd / "p.md"
    pp.write_text(f"# Plan\n\n**Gate:**\n- [x] `make hil` proves it. *({vocab} — amended)*\n")
    _, dv = run_json(str(pp))
    if dv is not None and findings_of(dv, 2):
        ok(f"'{vocab}' still voids a tick when paired")
    else:
        bad(f"'{vocab}' does not void even when paired — it left the vocabulary",
            json.dumps(dv, indent=2)[:300] if dv else "")

d = newdir("i6f")
vf = d / "vocab.txt"
vf.write_text("# custom\nfrobnicated\n")
pp = d / "p.md"
pp.write_text("# Plan\n\n**Gate:**\n- [x] `make hil` proves it. *(frobnicated)*\n"
              "- [x] `make other` proves it. *(amended)*\n")
# EXTEND is the default: adding one project word must not silently disable the
# other 20. Replacing was the old default and was a fail-open reachable by using
# the feature as documented.
# Extra patterns join the WEAK tier, so a bare project keyword still needs a
# co-signal — otherwise --vocab-file would reintroduce the single-word FP class.
pp.write_text("# Plan\n\n**Gate:**\n"
              "- [x] `make hil` proves it. *(frobnicated)*\n"
              "- [x] `make two` proves it. *(frobnicated — exit 2)*\n"
              "- [x] `make three` proves it. *(no hardware)*\n")
_, dv = run_json(str(pp), "--vocab-file", str(vf))
lines = {f["line"] for f in findings_of(dv, 2)} if dv else set()
sev = {f["line"]: f.get("severity") for f in findings_of(dv, 2)} if dv else {}
if lines == {4, 5, 6} and sev.get(4) == "advisory" and sev.get(6) == "blocking":
    ok("--vocab-file joins the WEAK tier (lone custom term advisory, built-ins intact)")
else:
    bad(f"--vocab-file extension wrong: lines {sorted(lines)} sev {sev}",
        json.dumps(dv, indent=2)[:500] if dv else "")

_, dv = run_json(str(pp), "--vocab-file", str(vf), "--vocab-replace")
lines = {f["line"] for f in findings_of(dv, 2)} if dv else set()
if lines == {4, 5} and 6 not in lines:
    ok("--vocab-replace makes the custom list STRONG and drops the built-ins")
else:
    bad(f"--vocab-replace wrong: fired on lines {sorted(lines)}, expected 4 and 5",
        json.dumps(dv, indent=2)[:500] if dv else "")

print()
print("CLI guards")
d = newdir("thr")
p = d / "p.md"
p.write_text(CLEAN_PLAN)
r = run(str(p), "--flip-threshold", "0")
if r.returncode == 2:
    ok("--flip-threshold 0 is rejected (it would silently disable check 1)")
else:
    bad(f"--flip-threshold 0 exited {r.returncode}, expected 2", r.stderr[:300])

d = newdir("contain")
sub = d / "inner"
sub.mkdir()
(sub / "master.md").write_text(
    "# Master Plan: x\n\n## Sub-plans\n\n| 1 | [out](../outside.md) | [x] |\n"
    "\n**Completed:** 2026-08-22 — done.\n")
(d / "outside.md").write_text("# Plan\n- [x] `make hil`. *(BLOCKED — no CM4)*\n")
_, doc = run_json(str(sub / "master.md"))
if doc is not None and not findings_of(doc, 4):
    ok("a `../outside.md` link is not followed out of the plan's subtree")
else:
    bad("containment: link traversal escaped the plan directory",
        json.dumps(doc, indent=2)[:500] if doc else "")



# ===================================================================
# Second Tier-1 round (2026-08-26). No Criticals; these pin the seven
# Importants, including the two mutations PROVEN load-bearing but
# unpinned — a suite that stays green while a real guard is deleted is
# not evidence, which is the whole lesson of the first round.
# ===================================================================

print()
print("I-2 — a renamed plan file must not fabricate a bulk flip")
repo, env = newrepo("i2rename")
plan = repo / "old-plan.md"
plan.write_text(sub_plan(ticked=True))
base = commit(repo, env, "authored, already green")
subprocess.run(["git", "mv", "old-plan.md", "new-plan.md"], cwd=repo, check=True, env=env)
commit(repo, env, "rename the plan")
_, doc = run_json(str(repo / "new-plan.md"), "--since", base, cwd=repo)
if doc is not None and not findings_of(doc, 1):
    ok("git mv of an already-ticked plan produces no bulk-flip finding")
else:
    bad("I-2 REGRESSION: a rename fabricates a bulk flip",
        json.dumps(findings_of(doc, 1), indent=2)[:500] if doc else "")

print()
print("I-3 — a task commit must contain WORK, not just a subject line")
def bulk_with_empty_task_commits(mode):
    repo, env = newrepo(f"i3{mode}")
    plan = repo / "p.md"
    plan.write_text(sub_plan(ticked=False))
    base = commit(repo, env, "authored")
    for i in range(6):
        if mode == "empty":
            subprocess.run(["git", "commit", "-q", "--allow-empty",
                            "-m", f"Task 1.{i + 1}: work"], cwd=repo, check=True, env=env)
        else:                       # touches ONLY the plan file
            plan.write_text(sub_plan(ticked=False) + f"\n<!-- {i} -->\n")
            commit(repo, env, f"Task 1.{i + 1}: work")
    plan.write_text(sub_plan(ticked=True))
    commit(repo, env, "gate green")
    _, dd = run_json(str(plan), "--since", base, cwd=repo)
    return dd

for mode, label in (("empty", "six --allow-empty commits"),
                    ("planonly", "six commits touching only the plan")):
    dd = bulk_with_empty_task_commits(mode)
    if dd is not None and findings_of(dd, 1):
        ok(f"{label} titled 'Task 1.N' do NOT buy a pass")
    else:
        bad(f"I-3 REGRESSION: {label} defeat the bulk-flip rule",
            json.dumps(dd, indent=2)[:500] if dd else "")

print()
print("I-1 — the two mutations the reviewer proved load-bearing but unpinned")
# (a) Counter-not-set: a parent with ONE pre-ticked duplicate must not mask the
# other 20. With `set`, prev contains the shared key and every flip vanishes.
repo, env = newrepo("i1counter")
plan = repo / "p.md"
dup = "- [ ] `make test` passes.\n"
plan.write_text("# Plan\n\n**Gate:**\n" + "- [x] `make test` passes.\n" + dup * 20)
base = commit(repo, env, "authored with one already ticked")
plan.write_text("# Plan\n\n**Gate:**\n" + "- [x] `make test` passes.\n" * 21)
commit(repo, env, "green")
_, doc = run_json(str(plan), "--since", base, cwd=repo)
if doc is not None and findings_of(doc, 1):
    ok("one pre-ticked duplicate does not mask the other 20 (Counter, not set)")
else:
    bad("I-1 REGRESSION: the Counter guard is unpinned — `set` would pass this",
        json.dumps(doc, indent=2)[:500] if doc else "")

# (b) the git decode path: a non-UTF-8 plan across TWO commits, so file_at() and
# therefore git(errors="replace") is actually exercised. The single-commit
# fixture above never reaches it.
repo, env = newrepo("i1decode")
plan = repo / "p.md"
plan.write_bytes(b"# Plan\n\n**Gate:**\n- [ ] caf\xe9 gate.\n")
base = commit(repo, env, "authored")
plan.write_bytes(b"# Plan\n\n**Gate:**\n- [x] caf\xe9 gate. *(amended)*\n")
commit(repo, env, "green")
r = run(str(plan), "--since", base, cwd=repo)
if r.returncode in (0, 1, 4) and "Traceback" not in r.stderr:
    ok(f"non-UTF-8 plan across two commits: no crash (exit {r.returncode})")
else:
    bad("I-1 REGRESSION: git decode path crashes — errors='replace' is unpinned",
        f"rc={r.returncode}\n{r.stderr[:400]}")

print()
print("I-4 — the vocabulary does not fire on honest evidence prose")
d = newdir("i4fp")
p_ = d / "honest.md"
p_.write_text(
    "# Project Plan: honest\n\n**Gate:**\n"
    "- [x] `pytest -q` — `1452 passed, 27 skipped in 296.72s` against the tree.\n"
    "- [x] Fixture and budget suites both exit 0.\n"
    "- [x] `! rg -n 'soft residual|BLOCKED.*exit 0' Makefile` finds no residue.\n"
    "- [x] All 29 source files exist with non-zero size.\n"
    "- [x] Tier-2 review completed — no Critical, so the gate is not blocked.\n"
    "- [x] **(judgment)** The re-authoring is complete, not partial.\n")
r, doc = run_json(str(p_))
if doc is not None:
    n = len(findings_of(doc, 2))
    if n == 0:
        ok("six honest evidence lines produce zero findings (was 7 before I-4)")
    else:
        bad(f"I-4 REGRESSION: {n} false positive(s) on honest prose",
            json.dumps(findings_of(doc, 2), indent=2)[:800])

# ...while every genuinely void tick still fires, unquoted.
d = newdir("i4tp")
p_ = d / "void.md"
p_.write_text("# Plan\n\n**Gate:**\n"
              "- [x] make hil-console-cellular proves reconnect. *(amended — exit 2; no CM4)*\n"
              "- [x] make soak proves 72h. *(soft residual)*\n")
_, doc = run_json(str(p_))
if doc is not None and len(findings_of(doc, 2)) == 2:
    ok("the true positives still fire — the FP fix did not blunt the rule")
else:
    bad("I-4 went too far: a genuine void tick stopped firing",
        json.dumps(doc, indent=2)[:600] if doc else "")

print()
print("I-7 — ordinary markdown tables are not scanned as checkboxes")
d = newdir("i7")
p_ = d / "risk.md"
p_.write_text("# Plan\n\n## Risks\n\n"
              "| Risk | Mitigated | Residual |\n|---|---|---|\n"
              "| supply chain | [x] | N/A |\n"
              "| flash wear | [x] | partial, tracked in backlog |\n")
_, doc = run_json(str(p_))
if doc is not None and not findings_of(doc, 2):
    ok("a risk table with [x] cells and 'N/A'/'partial' text is not a finding")
else:
    bad("I-7 REGRESSION: ordinary tables scanned as checkboxes",
        json.dumps(findings_of(doc, 2), indent=2)[:500] if doc else "")



# ===================================================================
# Third round (2026-08-26). The tiering introduced a severity field and
# a two-signal rule; a mutation battery found SIX survivors against a
# green 91/91 — the severity of findings 1/3/4/5 was entirely unpinned,
# and the pre-filters had become unreachable from their own fixtures.
# Each case below names the mutation it kills.
# ===================================================================

print()
print("severity — pinned for every finding, not just finding 2 (M7-M11)")

# M9: finding 1's severity flipped to advisory.
repo, env = newrepo("sev1")
plan = repo / "p.md"
plan.write_text(sub_plan(ticked=False))
base = commit(repo, env, "authored")
plan.write_text(sub_plan(ticked=True))
commit(repo, env, "green")
_, doc = run_json(str(plan), "--since", base, cwd=repo)
f1 = findings_of(doc, 1) if doc else []
if f1 and all(f.get("severity") == "blocking" for f in f1):
    ok("finding 1 (bulk flip) is blocking")
else:
    bad("M9 SURVIVES: finding 1 severity unpinned", json.dumps(f1, indent=2)[:300])

# M10: finding 3.
repo, env = newrepo("sev3")
plan = repo / "p.md"
plan.write_text(preflight_plan(ticked=False))
base = commit(repo, env, "authored")
plan.write_text(preflight_plan(ticked=True))
commit(repo, env, "Preflight green")
_, doc = run_json(str(plan), "--since", base, cwd=repo)
f3 = findings_of(doc, 3) if doc else []
if f3 and all(f.get("severity") == "blocking" for f in f3):
    ok("finding 3 (device box, no probe) is blocking")
else:
    bad("M10 SURVIVES: finding 3 severity unpinned", json.dumps(f3, indent=2)[:300])

# M11: finding 5.
repo, env = newrepo("sev5")
plan = repo / "p.md"
plan.write_text(judgment_plan(ticked=False))
base = commit(repo, env, "authored")
plan.write_text(judgment_plan(ticked=True))
commit(repo, env, "Stage 1 green")
_, doc = run_json(str(plan), "--since", base, cwd=repo)
f5 = findings_of(doc, 5) if doc else []
if f5 and all(f.get("severity") == "blocking" for f in f5):
    ok("finding 5 (judgment box, no evaluator) is blocking")
else:
    bad("M11 SURVIVES: finding 5 severity unpinned", json.dumps(f5, indent=2)[:300])

# M7/M8: finding 4 must INHERIT from its evidence, both directions. M7 (always
# advisory) is the 2026-08-21 master-plan fraud downgraded to a note.
d = newdir("sev4b")
(d / "m.md").write_text(
    "# Master Plan: x\n\n**Gate:**\n"
    "- [x] `make hil` proves it. *(no CM4)*\n"
    "\n**Completed:** 2026-08-22 — green.\n")
_, doc = run_json(str(d / "m.md"))
f4 = findings_of(doc, 4) if doc else []
if f4 and f4[0].get("severity") == "blocking":
    ok("finding 4 inherits BLOCKING from a blocking gate line (kills M7)")
else:
    bad("M7 SURVIVES: **Completed:** over a blocking gate line is not blocking",
        json.dumps(f4, indent=2)[:300])

d = newdir("sev4a")
(d / "m.md").write_text(
    "# Master Plan: x\n\n**Gate:**\n"
    "- [x] `make hil` proves it. *(amended — skipped the bench step)*\n"
    "\n**Completed:** 2026-08-22 — green.\n")
_, doc = run_json(str(d / "m.md"))
f4 = findings_of(doc, 4) if doc else []
if f4 and f4[0].get("severity") == "advisory":
    ok("finding 4 inherits ADVISORY when every gate line is advisory (kills M8)")
else:
    bad("M8 SURVIVES: finding 4 ignores its evidence's severity",
        json.dumps(f4, indent=2)[:300])

print()
print("the exit code carries the severity (a caller gates on $?)")
d = newdir("rc4")
(d / "adv.md").write_text("# P\n\n**Gate:**\n"
                          "- [x] `make x` proves it. *(amended — skipped a step)*\n")
r = run(str(d / "adv.md"))
if r.returncode == 4:
    ok("advisory-only exits 4 — distinct from a RED gate")
else:
    bad(f"advisory-only exited {r.returncode}, expected 4", r.stdout[:200])
(d / "blk.md").write_text("# P\n\n**Gate:**\n- [x] `make x` proves it. *(no CM4)*\n")
r = run(str(d / "blk.md"))
if r.returncode == 1:
    ok("a blocking finding still exits 1")
else:
    bad(f"blocking exited {r.returncode}, expected 1")

print()
print("the pre-filters must stay reachable (M14/M15) and the words distinct (M3)")
# Two weak terms where one is NEGATED: without the negation guard this fires.
d = newdir("negf")
(d / "p.md").write_text("# P\n\n**Gate:**\n"
    "- [x] The amended step is complete, not partial.\n")
_, doc = run_json(str(d / "p.md"))
if doc is not None and not findings_of(doc, 2):
    ok("negated second term keeps a two-term line silent (kills M14)")
else:
    bad("M14 SURVIVES: the NEGATED guard is unreachable from its fixture",
        json.dumps(findings_of(doc, 2), indent=2)[:300] if doc else "")

# Two weak terms where one is COUNTED.
d = newdir("cntf")
(d / "p.md").write_text("# P\n\n**Gate:**\n"
    "- [x] `pytest` — 1452 passed, 27 skipped — under the amended runner. *(per §4)*\n")
_, doc = run_json(str(d / "p.md"))
if doc is not None and not findings_of(doc, 2):
    ok("counted second term keeps a two-term line silent (kills M15)")
else:
    bad("M15 SURVIVES: the COUNTED guard is unreachable from its fixture",
        json.dumps(findings_of(doc, 2), indent=2)[:300] if doc else "")

# M3: the same word twice is one signal, not two.
d = newdir("dupw")
(d / "p.md").write_text("# P\n\n**Gate:**\n"
    "- [x] `make x` proves it. *(deferred pending a deferred bench slot — per §4, was: none)*\n")
_, doc = run_json(str(d / "p.md"))
if doc is not None and not findings_of(doc, 2):
    ok("the same qualifier twice is one signal, not two (kills M3)")
else:
    bad("M3 SURVIVES: duplicate words counted as independent signals",
        json.dumps(findings_of(doc, 2), indent=2)[:300] if doc else "")

print()
print("a lone qualifier is never SILENT — the round-3 Critical")
for term in ["amended", "stubbed", "mocked", "waived", "exit 78", "exit 2"]:
    dd = newdir("lone")
    pp = dd / "p.md"
    pp.write_text(f"# P\n\n**Gate:**\n- [x] `make hil` proves the board. *({term})*\n")
    r, dv = run_json(str(pp))
    hits = findings_of(dv, 2) if dv else []
    if hits:
        ok(f"lone '{term}' in an undisclosed amendment is a finding "
           f"({hits[0].get('severity')})")
    else:
        bad(f"ROUND-3 CRITICAL REGRESSION: lone '{term}' is silent")

# ...but a lone qualifier that DISCLOSES stays silent, and so does one in prose.
d = newdir("lonok")
(d / "p.md").write_text("# P\n\n**Gate:**\n"
    "- [x] `rg -n x web/src` reports none. *(amended per §4.1 — was: `rg -n y`)*\n"
    "- [x] zero SELECTOR-UNMATCHED under the amended validator.\n"
    "- [x] Manual torrc line byte-identical before and after all applies.\n")
_, doc = run_json(str(d / "p.md"))
if doc is not None and not findings_of(doc, 2):
    ok("a disclosed amendment, and the word in prose, stay silent")
else:
    bad("the disclosure escape hatch or the prose carve-out broke",
        json.dumps(findings_of(doc, 2), indent=2)[:400] if doc else "")

print()
print("the two-signal rule, isolated from the lone-parenthetical rule")
# Two weak terms in PROSE — no amendment parenthetical, so the lone-qualifier
# rule cannot reach it and only the >=2 threshold can. Without this the two
# rules mask each other: a mutation raising the threshold to 3 stayed green
# because every two-term fixture also sat inside a parenthetical.
d = newdir("two")
(d / "p.md").write_text("# P\n\n**Gate:**\n"
                        "- [x] The skipped step was deferred to a bench slot.\n")
_, doc = run_json(str(d / "p.md"))
hits = findings_of(doc, 2) if doc else []
if hits and hits[0].get("severity") == "advisory":
    ok("two weak terms in prose fire via the >=2 rule alone")
else:
    bad("the >=2 threshold is unpinned — it is masked by the parenthetical rule",
        json.dumps(hits, indent=2)[:300])
# ...and one weak term in prose must still be silent, which is the other half.
(d / "q.md").write_text("# P\n\n**Gate:**\n"
                        "- [x] The skipped step is covered by the corpus suite.\n")
_, doc = run_json(str(d / "q.md"))
if doc is not None and not findings_of(doc, 2):
    ok("one weak term in prose stays silent")
else:
    bad("a single prose term fired — the measured FP driver is back")

print()
print("--vocab-replace alone is rejected rather than silently ignored")
d = newdir("vr")
(d / "p.md").write_text(CLEAN_PLAN)
r = run(str(d / "p.md"), "--vocab-replace")
if r.returncode == 2:
    ok("--vocab-replace without --vocab-file exits 2")
else:
    bad(f"--vocab-replace alone exited {r.returncode}, expected 2", r.stderr[:200])


print()
print("a tool's own name is never a confession (the gate-stub-audit trap)")
# `\bstub\b` matches inside `gate-stub-audit` because a hyphen is a word
# boundary. A gate report is required to cite that audit by
# name, so the detector was flagging compliance with its own mandate. Found
# 2026-08-26 by running this audit over the plan that ships it, against a real
# pasted gate report.
d = newdir("toolname")
(d / "p.md").write_text(
    "# Plan\n\n**Gate:**\n"
    "- [x] gate integrity checked. gate-stub-audit: 0 shell gate scripts; "
    "plan-flip-audit: no findings; probe-device.sh not needed.\n")
_r, _doc = run_json(str(d / "p.md"))
f2 = findings_of(_doc, 2)
if not f2:
    ok("a gate line citing gate-stub-audit / plan-flip-audit / probe-device is silent")
else:
    bad("a gate report citing the audits by name must not be a finding",
        str(f2)[:300])

# The guard must not blind the real word. `stubbed` on its own still fires.
d = newdir("toolname-neg")
(d / "p.md").write_text(
    "# Plan\n\n**Gate:**\n"
    "- [x] hil-console verified *(stubbed \u2014 no hardware)*\n")
_r, _doc = run_json(str(d / "p.md"))
if findings_of(_doc, 2):
    ok("the mask does not blind a genuine 'stubbed' confession")
else:
    bad("masking tool names must not suppress a real stub confession")


# ------------------------------------------------- finding 6: owner attestation
# Reconstructed from metabrush-android 2026-10-02: an executor ticked
# "Owner confirms the DEC-MB-006 acceptance extends to …" with no trace of the
# owner ever being asked. The owner's words are the only evidence such a box can
# have, so a tick without them is the executor's say-so.
print()
print("finding 6 — an owner decision needs the owner's words")
OWNER_BOX = ("- [x] Owner confirms the DEC-MB-006 acceptance extends to on-device "
             "inputs the user chose — Task 1.5 records it")

d = newdir("owner-pos")
(d / "p.md").write_text("# Plan\n\n## Preflight\n\n" + OWNER_BOX + "\n")
r, doc = run_json(str(d / "p.md"), "--repo", str(d))
f6 = findings_of(doc, 6) if doc else []
if f6 and r.returncode == 1:
    ok("a ticked 'Owner confirms …' with no quote is finding 6, exit 1")
else:
    bad("unquoted owner decision must be a blocking finding 6",
        f"exit {r.returncode}\n{json.dumps(doc, indent=2)[:600] if doc else r.stderr}")
# Catches: severity demoted to advisory.
if f6 and all(f.get("severity") == "blocking" for f in f6):
    ok("finding 6 is blocking")
else:
    bad("finding 6 must be blocking", str(f6)[:300])

# Catches: the ATTESTED escape deleted.
d = newdir("owner-quoted")
(d / "p.md").write_text("# Plan\n\n## Preflight\n\n" + OWNER_BOX +
                        ' *(owner, 2026-10-02: "yes, it covers the phone")*\n')
_r, doc = run_json(str(d / "p.md"), "--repo", str(d))
if doc is not None and not findings_of(doc, 6):
    ok("the same box carrying the owner's quoted words is silent")
else:
    bad("a quoted owner attestation must clear finding 6",
        json.dumps(doc, indent=2)[:500] if doc else "")

# Catches: action verbs ("runs", "creates") added to the decision vocabulary.
# Those boxes are proven by their own command; a quote is not their evidence.
d = newdir("owner-action")
(d / "p.md").write_text(
    "# Plan\n\n## Preflight\n\n"
    "- [x] Owner runs `sudo apt install libimage-exiftool-perl`; `exiftool -ver` prints a version\n"
    "- [x] Owner creates the GitHub repo; `git ls-remote` answers\n")
_r, doc = run_json(str(d / "p.md"), "--repo", str(d))
if doc is not None and not findings_of(doc, 6):
    ok("'owner runs …' / 'owner creates …' are actions, not decisions — silent")
else:
    bad("owner ACTIONS must not need a quote", json.dumps(doc, indent=2)[:500] if doc else "")

# Catches: the start-of-box anchor removed. Mid-sentence mentions are prose —
# measured across 775 vault plans, the unanchored form fired on 44 of them.
d = newdir("owner-prose")
(d / "p.md").write_text(
    "# Plan\n\n**Gate:**\n"
    "- [x] Restore never mutates text until the user confirms the dialog\n"
    "- [x] Drafts are versioned, pending owner approval of the copy\n")
_r, doc = run_json(str(d / "p.md"), "--repo", str(d))
if doc is not None and not findings_of(doc, 6):
    ok("an owner/user verb in the middle of a box is prose — silent")
else:
    bad("finding 6 must anchor to the start of the box", json.dumps(doc, indent=2)[:500] if doc else "")

# Catches: the ticked-only guard removed. An unticked box claims nothing.
d = newdir("owner-unticked")
(d / "p.md").write_text("# Plan\n\n## Preflight\n\n" + OWNER_BOX.replace("[x]", "[ ]") + "\n")
_r, doc = run_json(str(d / "p.md"), "--repo", str(d))
if doc is not None and not findings_of(doc, 6):
    ok("an unticked owner box is silent")
else:
    bad("an unticked box must not be finding 6", json.dumps(doc, indent=2)[:400] if doc else "")

# ------------------------------------------------ finding 7: stale was-values
# Same session: the engine pin was amended a23ae13 -> 721dc06 at Preflight, with
# a proper `was:`, but the Research Summary still said a23ae13.
print()
print("finding 7 — an amended value must not survive elsewhere unannotated")
AMEND_LINE = ("- [x] Engine reachable: `git ls-remote … | grep 721dc06` "
              "*(amended at Preflight — was: `a23ae13`; fixed and pushed)*\n")
d = newdir("stale-pos")
(d / "p.md").write_text("# Plan\n\n## Research\n\nThe engine compiles at commit `a23ae13`.\n\n"
                        "## Preflight\n\n" + AMEND_LINE)
r, doc = run_json(str(d / "p.md"), "--repo", str(d))
f7 = findings_of(doc, 7) if doc else []
if len(f7) == 1 and f7[0].get("line") == 5:
    ok("the surviving a23ae13 in the Research section is finding 7, and only it")
else:
    bad("expected exactly one finding 7 on line 5", json.dumps(doc, indent=2)[:700] if doc else "")
# Catches: severity promoted to blocking (exit would become 1).
if f7 and all(f.get("severity") == "advisory" for f in f7) and r.returncode == 4:
    ok("finding 7 is advisory: exit 4, a line owed in the gate report")
else:
    bad(f"finding 7 must be advisory with exit 4, got exit {r.returncode}", str(f7)[:300])

# Catches: the STALE_EXEMPT check deleted. A survivor marked historical is the
# disclosure, not the defect.
d = newdir("stale-historical")
(d / "p.md").write_text("# Plan\n\n## Research\n\nThe engine compiled at commit `a23ae13` "
                        "(historical — the pin is now 721dc06).\n\n## Preflight\n\n" + AMEND_LINE)
_r, doc = run_json(str(d / "p.md"), "--repo", str(d))
if doc is not None and not findings_of(doc, 7):
    ok("a survivor marked historical is silent")
else:
    bad("a historical mention must clear finding 7", json.dumps(doc, indent=2)[:500] if doc else "")

# Catches: the DISTINCTIVE filter deleted. A was-value that is ordinary words
# legitimately recurs; measured, sweeping those fired on 9 of 775 plans.
d = newdir("stale-words")
(d / "p.md").write_text(
    "# Plan\n\nThe tier review-scope: standard-plus applies to docs.\n\n## Preflight\n\n"
    "- [x] Review scope declared *(amended at Preflight per review-scope.md — "
    "was: `review-scope: standard-plus`)*\n")
_r, doc = run_json(str(d / "p.md"), "--repo", str(d))
if doc is not None and not findings_of(doc, 7):
    ok("a was-value that is words, not an identifier, is not swept")
else:
    bad("only identifier-like was-values may be swept", json.dumps(doc, indent=2)[:500] if doc else "")

# ------------------------------------------- baseline: no git history for the plan
# Every real plan lives in a vault that is not a git repository. Before the
# baseline, findings 1/3/5 could never run on one — and that is exactly the
# situation in which an executor ticked a whole Preflight at once, unseen.
print()
print("baseline — a plan outside git is audited against its --snapshot copy")

def baseline_world(label):
    """A vault dir holding the plan, and a separate project repo."""
    vault = newdir(f"{label}-vault")
    proj, env = newrepo(f"{label}-proj")
    plan = vault / "plan.md"
    lines = ["# Plan", "", "## Preflight", ""]
    lines += [f"- [ ] Tool {i} installed: `tool{i} --version`" for i in range(4)]
    lines += ["", "## Stage 1", ""]
    for i in range(1, 5):
        lines += [f"### Task 1.{i}: thing {i}", "- **Status:** [ ]", ""]
    lines += ["### Stage 1 Gate", "", "- [ ] **(judgment)** reads well", ""]
    plan.write_text("\n".join(lines))
    return vault, proj, env, plan

def snap(plan, proj):
    return run(str(plan), "--snapshot", "--repo", str(proj))

vault, proj, env, plan = baseline_world("bl-none")
r, doc = run_json(str(plan), "--repo", str(proj))
reasons = " ".join(c.get("reason", "") for c in (doc or {}).get("checks_not_run", []))
if doc is not None and {c["finding"] for c in doc["checks_not_run"]} == {1, 3, 5, 8, 9, 10} \
        and "--snapshot" in reasons:
    ok("with no baseline, 1/3/5 are NOT RUN and the reason says to --snapshot")
else:
    bad("no baseline must leave 1/3/5 not run, pointing at --snapshot",
        json.dumps(doc, indent=2)[:500] if doc else r.stderr)

# The metabrush-android shape: snapshot, one task commit, then every Preflight
# box and every task box ticked in one edit, plus the (judgment) box.
vault, proj, env, plan = baseline_world("bl-bulk")
(proj / "README").write_text("x\n"); commit(proj, env, "chore: initial commit")
r = snap(plan, proj)
if r.returncode == 0:
    ok("--snapshot exits 0 and writes the baseline")
else:
    bad(f"--snapshot failed: exit {r.returncode}", r.stderr[:300])
# Catches: the refuse-to-overwrite guard deleted.
r2 = snap(plan, proj)
if r2.returncode == 2 and "already exists" in r2.stderr:
    ok("a second --snapshot is refused (exit 2) — it would launder every flip")
else:
    bad(f"second --snapshot must exit 2, got {r2.returncode}", r2.stderr[:300])
(proj / "a.kt").write_text("x\n"); commit(proj, env, "Stage 1 Task 1.1: scaffold")
plan.write_text(plan.read_text().replace("- [ ]", "- [x]").replace("**Status:** [ ]", "**Status:** [x]"))
r, doc = run_json(str(plan), "--repo", str(proj), "--require-all-checks")
got = {f["finding"] for f in (doc or {}).get("findings", [])}
if doc is not None and {1, 3, 5} <= got and r.returncode == 1:
    ok("bulk flip, Preflight ticks with no probe, judgment with no review: 1, 3, 5 all fire")
else:
    bad(f"expected findings 1, 3, 5 and exit 1; got {sorted(got)}, exit {r.returncode}",
        json.dumps(doc, indent=2)[:900] if doc else r.stderr)
if doc is not None and set(doc.get("checks_run", [])) == {1, 2, 3, 4, 5, 6, 7, 8, 9, 10} \
        and doc.get("baseline"):
    ok("baseline mode with --repo reports all ten checks run, and names the baseline")
else:
    bad("baseline mode must report 1-7 run", json.dumps(doc, indent=2)[:500] if doc else "")
f3 = findings_of(doc, 3) if doc else []
if len(f3) == 4:
    ok("each of the 4 Preflight ticks is its own finding 3")
else:
    bad(f"expected 4 finding-3 entries, got {len(f3)}", str(f3)[:400])

# The honest version of the same run: one task commit per task, a committed
# probe artefact, a review ledger line. Nothing fires; coverage is complete.
vault, proj, env, plan = baseline_world("bl-honest")
r = snap(plan, proj)                      # no commits yet: repo_head is null
if r.returncode == 0 and "no commits yet" in r.stdout:
    ok("--snapshot works before the first commit (a fresh `git init`)")
else:
    bad("--snapshot must work in a repo with no commits", r.stdout + r.stderr)
(proj / "evidence").mkdir()
(proj / "evidence" / "preflight-probe.txt").write_text("tool0 1.0\n")
commit(proj, env, "chore: Preflight report")
for i in range(1, 8):
    (proj / f"f{i}.kt").write_text(f"{i}\n")
    commit(proj, env, f"Stage 1 Task 1.{i}: work\n\nmutation: reverting f{i}.kt turns the test red")
(proj / "g.txt").write_text("g\n")
commit(proj, env, "Stage 1 green\n\nevaluator: PASS — reads well")
plan.write_text(plan.read_text().replace("- [ ]", "- [x]").replace("**Status:** [ ]", "**Status:** [x]"))
r, doc = run_json(str(plan), "--repo", str(proj), "--require-all-checks")
# Its tasks are evidenced by `mutation:` lines, which are legacy since proof
# records replaced them: finding 8 reports them advisory, nothing else fires.
others = [f for f in (doc or {}).get("findings", []) if not (
    f["finding"] == 8 and f["severity"] == "advisory" and "legacy" in f["rule"])]
if doc is not None and not others and r.returncode == 4:
    ok("with task commits, a probe artefact and a review ledger: the history checks are clean")
else:
    bad(f"honest run must be clean; exit {r.returncode}",
        json.dumps(doc, indent=2)[:900] if doc else r.stderr)

# Catches: the hash check deleted. An edited baseline is not evidence.
import hashlib as _hl
key = _hl.sha256(str(plan.resolve()).encode()).hexdigest()[:16]
bp = proj / ".claude" / "plan-baseline" / f"{key}.json"
bdoc = json.loads(bp.read_text())
bdoc["text"] = bdoc["text"].replace("- [ ]", "- [x]")
bp.write_text(json.dumps(bdoc))
r = run(str(plan), "--repo", str(proj))
if r.returncode == 2 and "hash" in r.stderr:
    ok("a baseline edited after capture exits 2, never clean")
else:
    bad(f"tampered baseline must exit 2, got {r.returncode}", r.stdout[:300] + r.stderr[:300])

# Catches: the plan-identity check deleted. A baseline of another plan must not
# be borrowed.
bdoc["text"] = "# other\n"; bdoc["sha256"] = _hl.sha256(b"# other\n").hexdigest()
bdoc["plan"] = str(vault / "other.md")
bp.write_text(json.dumps(bdoc))
r = run(str(plan), "--repo", str(proj))
if r.returncode == 2 and "different plan" in r.stderr:
    ok("a baseline recording a different plan exits 2")
else:
    bad(f"foreign baseline must exit 2, got {r.returncode}", r.stdout[:300] + r.stderr[:300])


# Finding 1 counts a stage's gate boxes only while that stage has no `Stage N green`
# commit in the range. Five task commits, five Status ticks and two gate boxes is an
# honest stage — counting the gate boxes made it 7 > 6, a blocking bulk flip, at every
# plan's second gate. The same ticks with no green commit are still a bulk flip.
def gated_plan(label, n_tasks=5):
    vault = newdir(f"{label}-vault")
    lines = ["# Plan", "", "## Stage 1", ""]
    for i in range(1, n_tasks + 1):
        lines += [f"### Task 1.{i}: thing {i}", "- **Status:** [ ]", ""]
    lines += ["### Stage 1 Gate", "", "- [ ] `make test` exits 0", "- [ ] `make lint` exits 0", ""]
    plan = vault / "plan.md"
    plan.write_text("\n".join(lines))
    return plan


def tick_all(plan):
    plan.write_text(plan.read_text().replace("- [ ]", "- [x]").replace("**Status:** [ ]", "**Status:** [x]"))


for label, green, want in (("bl-gate-green", True, False), ("bl-gate-nogreen", False, True)):
    plan = gated_plan(label)
    proj, env = newrepo(f"{label}-proj")
    (proj / "README").write_text("x\n"); commit(proj, env, "chore: initial commit")
    snap(plan, proj)
    for i in range(1, 6):
        (proj / f"f{i}.txt").write_text(f"{i}\n"); commit(proj, env, f"Stage 1 Task 1.{i}: work")
    if green:
        (proj / "gate.txt").write_text("gate report\n"); commit(proj, env, "Stage 1 green")
    tick_all(plan)
    r, doc = run_json(str(plan), "--repo", str(proj))
    f1 = findings_of(doc, 1) if doc else []
    if bool(f1) == want:
        ok("baseline: 5 task ticks + 2 gate boxes " + ("with" if green else "without")
           + " a `Stage 1 green` commit " + ("fires finding 1" if want else "is not a bulk flip"))
    else:
        bad("a stage's gate boxes are backed only by its green commit (red if gate boxes "
            "count, or count as backed with no green commit)", json.dumps(f1)[:400])

for label, green, want in (("hist-gate-green", True, False), ("hist-gate-nogreen", False, True)):
    repo, env = newrepo(label)
    plan = repo / "p.md"
    plan.write_text(gated_plan(f"{label}-src").read_text())
    base = commit(repo, env, "authored")
    for i in range(1, 6):
        (repo / f"f{i}.txt").write_text(f"{i}\n"); commit(repo, env, f"Stage 1 Task 1.{i}: work")
    tick_all(plan)
    commit(repo, env, "Stage 1 green" if green else "progress")
    r, doc = run_json(str(plan), "--since", base, cwd=repo)
    f1 = findings_of(doc, 1) if doc else []
    if bool(f1) == want:
        ok("history: the gate ticked " + ("in its `Stage 1 green` commit is not a bulk flip"
                                          if green else "in an ordinary commit still fires finding 1"))
    else:
        bad("history mode must back gate boxes by the green commit alone", json.dumps(f1)[:400])


# Finding 1 counts a Preflight box only while no probe artefact backs it. Six Preflight
# boxes and three task ticks, after three task commits, is an honest Stage 1 gate once
# the Preflight output is committed — counting those boxes made it 9 > 6, a blocking
# bulk flip at the first gate of every plan with six Preflight checks (sub-01 of the
# workflow-rollover master, 2026-10-05). With no probe it is still a bulk flip.
def preflight_heavy_plan(label):
    vault = newdir(f"{label}-vault")
    lines = ["# Plan", "", "## Preflight", ""]
    lines += [f"- [ ] Check {i}: `tool{i} --version` exits 0" for i in range(6)]
    lines += ["", "## Stage 1", ""]
    for i in range(1, 4):
        lines += [f"### Task 1.{i}: thing {i}", "- **Status:** [ ]", ""]
    plan = vault / "plan.md"
    plan.write_text("\n".join(lines))
    return plan


for label, probed, want in (("bl-pre-probed", True, False), ("bl-pre-unprobed", False, True)):
    plan = preflight_heavy_plan(label)
    proj, env = newrepo(f"{label}-proj")
    (proj / "README").write_text("x\n"); commit(proj, env, "chore: initial commit")
    snap(plan, proj)
    for i in range(1, 4):
        (proj / f"f{i}.txt").write_text(f"{i}\n"); commit(proj, env, f"Stage 1 Task 1.{i}: work")
    if probed:
        (proj / "evidence").mkdir()
        (proj / "evidence" / "preflight-probe.txt").write_text("tool0 1.0\n")
        commit(proj, env, "Preflight probe output")
    tick_all(plan)
    r, doc = run_json(str(plan), "--repo", str(proj))
    f1 = findings_of(doc, 1) if doc else []
    if bool(f1) == want:
        ok("baseline: 6 Preflight + 3 task ticks after 3 task commits "
           + ("with a committed probe is not a bulk flip" if probed
              else "with no probe still fires finding 1"))
    else:
        bad("a probe-backed Preflight box is not a bulk flip (red if Preflight boxes count "
            "despite the probe, or count as backed with none)", json.dumps(f1)[:400])

for label, probed, want in (("hist-pre-probed", True, False), ("hist-pre-unprobed", False, True)):
    repo, env = newrepo(label)
    plan = repo / "p.md"
    plan.write_text(preflight_heavy_plan(f"{label}-src").read_text())
    base = commit(repo, env, "authored")
    for i in range(1, 4):
        (repo / f"f{i}.txt").write_text(f"{i}\n"); commit(repo, env, f"Stage 1 Task 1.{i}: work")
    tick_all(plan)
    if probed:
        (repo / "evidence").mkdir()
        (repo / "evidence" / "preflight-probe.txt").write_text("tool0 1.0\n")
    commit(repo, env, "Preflight green" if probed else "progress")
    r, doc = run_json(str(plan), "--since", base, cwd=repo)
    f1 = findings_of(doc, 1) if doc else []
    if bool(f1) == want:
        ok("history: 6 Preflight + 3 task ticks in one commit "
           + ("carrying a probe artefact is not a bulk flip" if probed
              else "with no probe still fires finding 1"))
    else:
        bad("history mode must back Preflight boxes by a probe in their own commit",
            json.dumps(f1)[:400])

# The exemption's bounds (Stage 2 review, 2026-10-05). A probe file is blind to which
# box it backs, so it clears at most N Preflight boxes; it never touches a non-Preflight
# box, even one repeating a Preflight line's text; and in history mode a probe counts
# from the commit that adds it onward, never backwards.
def bounds_plan(label, n_pre, n_tasks, gate_dupes=0):
    vault = newdir(f"{label}-vault")
    lines = ["# Plan", "", "## Preflight", ""]
    lines += [f"- [ ] Check {i}: `tool{i} --version` exits 0" for i in range(n_pre)]
    lines += ["", "## Stage 1", ""]
    for i in range(1, n_tasks + 1):
        lines += [f"### Task 1.{i}: thing {i}", "- **Status:** [ ]", ""]
    if gate_dupes:
        lines += ["### Stage 1 Gate", ""]
        lines += ["- [ ] Check 0: `tool0 --version` exits 0"] * gate_dupes
    plan = vault / "plan.md"
    plan.write_text("\n".join(lines) + "\n")
    return plan


def bounds_case(label, n_pre, n_tasks, gate_dupes=0):
    plan = bounds_plan(label, n_pre, n_tasks, gate_dupes)
    proj, env = newrepo(f"{label}-proj")
    (proj / "README").write_text("x\n"); commit(proj, env, "chore: initial commit")
    snap(plan, proj)
    (proj / "f1.txt").write_text("1\n"); commit(proj, env, "Stage 1 Task 1.1: work")
    (proj / "evidence").mkdir()
    (proj / "evidence" / "preflight-probe.txt").write_text("tool0 1.0\n")
    commit(proj, env, "Preflight probe output")
    tick_all(plan)
    r, doc = run_json(str(plan), "--repo", str(proj))
    return findings_of(doc, 1) if doc else []


for label, args, why in (
        ("bl-cap", (8, 0), "8 probed Preflight boxes exceed the cap of 6"),
        ("bl-nonpre", (2, 7), "7 task ticks are not cleared by a Preflight probe"),
        ("bl-dupe", (1, 0, 7), "7 gate boxes repeating a Preflight line are not Preflight boxes")):
    f1 = bounds_case(label, *args)
    if f1:
        ok(f"baseline: finding 1 still fires — {why}")
    else:
        bad(f"a probe clears only up to N Preflight boxes, by line (red if {why} is exempted)",
            json.dumps(f1)[:300])

for label, order, want in (("hist-probe-first", "before", False),
                           ("hist-probe-after", "after", True)):
    repo, env = newrepo(label)
    plan = repo / "p.md"
    plan.write_text(preflight_heavy_plan(f"{label}-src").read_text())
    base = commit(repo, env, "authored")
    for i in range(1, 4):
        (repo / f"f{i}.txt").write_text(f"{i}\n"); commit(repo, env, f"Stage 1 Task 1.{i}: work")

    def probe():
        (repo / "evidence").mkdir()
        (repo / "evidence" / "preflight-probe.txt").write_text("tool0 1.0\n")
        commit(repo, env, "Preflight probe output")
    if order == "before":
        probe()
    tick_all(plan)
    commit(repo, env, "progress")
    if order == "after":
        probe()
    r, doc = run_json(str(plan), "--since", base, cwd=repo)
    f1 = findings_of(doc, 1) if doc else []
    if bool(f1) == want:
        ok("history: a probe committed " + order + " the Preflight ticks "
           + ("does not back them" if want else "backs them, as in baseline mode"))
    else:
        bad("history mode backs Preflight boxes by a probe in that commit or earlier, "
            "never a later one", json.dumps(f1)[:400])

# ------------------------------- findings 8 and 9: proof is a record, not a line
# metabrush-android: executors wrote `mutation:` and `req:` lines that were
# false (a substituted break, a cleanup that was never exercised). A line is a
# claim; a prove-claim.py record is the tool having watched it. Findings 8 and 9
# now read records from the committed tree and validate each against the commit
# that added it; lines alone are "legacy, unverified" (advisory).
print()
print("findings 8 and 9 — proof records, bound to their commit")
PC = SCRIPT.parent / "prove-claim.py"
REC_PLAN = (
    "# Plan\n\n## Stage 1\n\n"
    "### Task 1.1: calc\n- **Status:** [x]\n- `add` returns the sum.\n"
    "- **Test:** `python3 tests/test_calc.py` — add returns the sum (red if add subtracts)\n"
)
CALC = "def add(a, b):\n    return a + b\n"
TESTPY = "import sys\nsys.path.insert(0, '.')\nfrom calc import add\nassert add(2, 3) == 5\n"
BUILD = "python3 -c 'import ast; ast.parse(open(\"calc.py\").read())'"


def rec_world(label):
    vault = newdir(f"{label}-vault")
    proj, env = newrepo(f"{label}-proj")
    (proj / "calc.py").write_text(CALC)
    (proj / "tests").mkdir()
    (proj / "tests" / "test_calc.py").write_text(TESTPY)
    (proj / ".gitignore").write_text("__pycache__/\n")
    commit(proj, env, "base")
    plan = vault / "2026-10-04-rec-plan.md"
    plan.write_text(REC_PLAN)
    return plan, proj, env


def prove_task(plan, proj, req_kind="covered"):
    """Prove claim 1 and requirement 1 of Task 1.1 on the current index."""
    f = proj / "calc.py"
    orig = f.read_text()
    f.write_text(orig.replace("return a + b", "return a - b"))
    d = subprocess.run(["git", "-C", str(proj), "diff", "--", "calc.py"],
                       capture_output=True, text=True).stdout
    f.write_text(orig)
    brk = newdir(f"{proj.name}-brk") / "break.patch"
    brk.write_text(d)
    base = ["--repo", str(proj), "--plan", str(plan), "--task", "1.1"]
    r1 = subprocess.run([sys.executable, str(PC), "claim", *base, "--claim", "1", "--break",
                         str(brk), "--test", "python3 tests/test_calc.py", "--build", BUILD],
                        capture_output=True, text=True)
    if req_kind == "covered":
        extra = ["req", *base, "--req", "1", "--covered-by-claim", "1"]
    else:
        extra = ["deviation", *base, "--req", "1", "--why", "add is not separately checkable here"]
    r2 = subprocess.run([sys.executable, str(PC), *extra], capture_output=True, text=True)
    assert r1.returncode == 0 and r2.returncode == 0, (r1.stderr, r2.stderr)
    return brk


def task_findings(doc, n):
    return [f for f in findings_of(doc, n) if f.get("text") == "Task 1.1"]


# A proven task, its records committed with its code: clean.
plan, proj, env = rec_world("rec-ok")
(proj / "calc.py").write_text(CALC + "\n\ndef twice(a):\n    return 2 * a\n")
subprocess.run(["git", "-C", str(proj), "add", "-A"], check=True, env=env)
prove_task(plan, proj)
commit(proj, env, "Stage 1 Task 1.1: twice")
r, doc = run_json(str(plan), "--repo", str(proj))
if doc is not None and not task_findings(doc, 8) and not task_findings(doc, 9) and {8, 9} <= set(doc["checks_run"]):
    ok("a task whose records are committed with its code is clean on 8 and 9")
else:
    bad("valid committed records must satisfy 8 and 9 (red if records are not read)",
        json.dumps(doc, indent=2)[:900] if doc else r.stderr)

# Catches: the commit binding not checked. The code changes after the proof and
# is committed together with the now-stale record.
plan, proj, env = rec_world("rec-stale")
subprocess.run(["git", "-C", str(proj), "add", "-A"], check=True, env=env)
prove_task(plan, proj)
(proj / "calc.py").write_text(CALC + "# changed after the proof\n")
commit(proj, env, "Stage 1 Task 1.1: changed after proving")
r, doc = run_json(str(plan), "--repo", str(proj))
f8 = task_findings(doc, 8) if doc else []
if f8 and f8[0]["severity"] == "blocking" and "different tree" in f8[0]["rule"]:
    ok("a record proven on another tree than its commit's is blocking")
else:
    bad("a stale record must be blocking (red if the binding is not checked)", str(f8)[:500])

# Catches: exit codes not validated. A hand-edited record: red exit 0.
plan, proj, env = rec_world("rec-forged")
subprocess.run(["git", "-C", str(proj), "add", "-A"], check=True, env=env)
prove_task(plan, proj)
rp = proj / "proof" / plan.stem / "1.1" / "claim-1.json"
data = json.loads(rp.read_text())
data["red"]["exit"] = 0
rp.write_text(json.dumps(data))
commit(proj, env, "Stage 1 Task 1.1: forged")
r, doc = run_json(str(plan), "--repo", str(proj))
f8 = task_findings(doc, 8) if doc else []
if f8 and f8[0]["severity"] == "blocking" and "did not fail" in f8[0]["rule"]:
    ok("a record whose test did not fail under the break is blocking")
else:
    bad("a forged record must be blocking (red if exit codes are not checked)", str(f8)[:500])

# Catches: records not bound to the plan's wording. The claim is reworded after
# it was proven: the record proves a sentence the plan no longer says.
plan, proj, env = rec_world("rec-reworded")
subprocess.run(["git", "-C", str(proj), "add", "-A"], check=True, env=env)
prove_task(plan, proj)
commit(proj, env, "Stage 1 Task 1.1: proven")
plan.write_text(REC_PLAN.replace("add returns the sum (red", "add returns the total of both (red"))
r, doc = run_json(str(plan), "--repo", str(proj))
f8 = task_findings(doc, 8) if doc else []
if f8 and f8[0]["severity"] == "blocking" and "different wording" in f8[0]["rule"]:
    ok("a record proven against wording the plan has since changed is blocking")
else:
    bad("a reworded claim must be blocking (red if wording is not compared)", str(f8)[:500])

# Schema 2: a req check must be proven by a break. A schema-1 req check — seen
# to pass, never to fail — is legacy, reported as such. The same shape claiming
# schema 2 is what a hand-written record would look like: the requirement is not
# shown met. A schema-1 record is legacy only when first added before the
# schema-2 cutover (engineering-skills e0a8cdb, 2026-10-04T10:07:25Z); the same
# record committed now is not shown met. Finding 9 is advisory upstream in every
# case (no blocking mandate until measured), so the message is what differs.
BEFORE = {"GIT_COMMITTER_DATE": "2026-10-03T12:00:00+00:00", "GIT_AUTHOR_DATE": "2026-10-03T12:00:00+00:00"}
for label, schema, sev, dated in (("rec-legacy-req", 1, "legacy schema-1", BEFORE),
                                  ("rec-bare-req", 2, "not shown met", {}),
                                  ("rec-late-legacy", 1, "not shown met", {})):
    plan, proj, env = rec_world(label)
    subprocess.run(["git", "-C", str(proj), "add", "-A"], check=True, env=env)
    prove_task(plan, proj)
    rp = proj / "proof" / plan.stem / "1.1" / "req-1.json"
    data = json.loads(rp.read_text())
    data.pop("covered_by_claim", None)
    data.update({"schema": schema, "check": "python3 tests/test_calc.py",
                 "result": {"exit": 0, "tail": ""}})
    rp.write_text(json.dumps(data))
    commit(proj, {**env, **dated}, "Stage 1 Task 1.1: req by a bare check")
    r, doc = run_json(str(plan), "--repo", str(proj))
    f9 = task_findings(doc, 9) if doc else []
    when = " (added before the cutover)" if dated else (" (added after the cutover)" if schema == 1 else "")
    if f9 and f9[0]["severity"] == "advisory" and sev in f9[0]["rule"]:
        ok(f"a schema-{schema} req record with a bare passing check{when} is advisory: {sev}")
    else:
        bad(f"schema-{schema} bare req check{when} must be advisory '{sev}' (red if legacy has "
            "no cutoff)", str(f9)[:400])

# Catches: a covered-by citation not followed. The req cites claim 5 of a task
# that has one claim: the record validates on its own, the citation does not.
plan, proj, env = rec_world("rec-cites")
subprocess.run(["git", "-C", str(proj), "add", "-A"], check=True, env=env)
prove_task(plan, proj)
rp = proj / "proof" / plan.stem / "1.1" / "req-1.json"
data = json.loads(rp.read_text())
data["covered_by_claim"] = 5
rp.write_text(json.dumps(data))
commit(proj, env, "Stage 1 Task 1.1: req cites a claim that does not exist")
r, doc = run_json(str(plan), "--repo", str(proj))
f9 = task_findings(doc, 9) if doc else []
if f9 and f9[0]["severity"] == "advisory" and "cites claim 5" in f9[0]["rule"]:
    ok("a req citing a claim that is missing or unproven is reported (advisory)")
else:
    bad("covered-by must be followed (red if the citation is not checked)", str(f9)[:400])

# Catches: proof/ as a hiding place in the committed tree.
plan, proj, env = rec_world("rec-stray")
subprocess.run(["git", "-C", str(proj), "add", "-A"], check=True, env=env)
prove_task(plan, proj)
(proj / "proof" / "helper.py").write_text("x = 1\n")
commit(proj, env, "Stage 1 Task 1.1: with a stray file under proof/")
r, doc = run_json(str(plan), "--repo", str(proj))
st = [f for f in findings_of(doc, 8) if f.get("text") == "proof/"] if doc else []
if st and st[0]["severity"] == "blocking" and "proof/helper.py" in st[0]["rule"]:
    ok("a committed file under proof/ that is not a record is blocking")
else:
    bad("stray proof/ files must be blocking (red if proof/ can carry anything)",
        json.dumps(doc, indent=2)[:600] if doc else r.stderr)

# Catches: the audit and the ref hook reading subjects differently. One reader,
# subject_tasks(), is shared; it is case-insensitive and expands lists and ranges.
_sp = importlib.util.spec_from_file_location("pfa_subjects", SCRIPT)
_sm = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(_sm)
cases = {"Stage 2 Task 2.8: x": {"2.8"}, "task 2.1: x": {"2.1"}, "Tasks 2.1 and 2.2: x": {"2.1", "2.2"},
         "Stage 1 Task 1.1 + Task 1.2: x": {"1.1", "1.2"}, "Tasks 2.4-2.7: x": {"2.4", "2.5", "2.6", "2.7"},
         "Tasks 2.4–2.7": {"2.4", "2.5", "2.6", "2.7"}, "Task #2.1": {"2.1"}, "Task-2.1": {"2.1"},
         "Stage 1 Task 1.10: x": {"1.10"}, "Stage 2 gate: none": set()}
wrong = {k: _sm.subject_tasks(k) for k, v in cases.items() if _sm.subject_tasks(k) != v}
if not wrong:
    ok("subject_tasks reads case, lists, ranges and 1.10 vs 1.1 as intended")
else:
    bad("subject_tasks must read every subject form", wrong)
plan, proj, env = rec_world("rec-lower")
subprocess.run(["git", "-C", str(proj), "add", "-A"], check=True, env=env)
prove_task(plan, proj)
commit(proj, env, "stage 1 task 1.1: lowercase subject")
r, doc = run_json(str(plan), "--repo", str(proj))
if doc is not None and not task_findings(doc, 8) and not task_findings(doc, 9):
    ok("a lowercase 'task 1.1' subject is that task's commit for the audit, as for the hook")
else:
    bad("lowercase subjects must count (red if the audit reads subjects differently)",
        json.dumps(doc, indent=2)[:600] if doc else r.stderr)

# Catches: lines still counted as proof. Self-reported lines, no records.
plan, proj, env = rec_world("rec-legacy")
(proj / "x.txt").write_text("x\n")
commit(proj, env, "Stage 1 Task 1.1: work\n\nmutation: add subtracts -> red\nreq: add -> test")
r, doc = run_json(str(plan), "--repo", str(proj))
f8, f9 = (task_findings(doc, 8), task_findings(doc, 9)) if doc else ([], [])
if (f8 and f9 and all(f["severity"] == "advisory" and "legacy" in f["rule"] for f in f8 + f9)
        and r.returncode == 4):
    ok("lines alone are advisory 'legacy, unverified' on 8 and 9 — never clean, never blocking")
else:
    bad("lines alone must be legacy advisories (red if lines still count as proof)",
        json.dumps(doc, indent=2)[:900] if doc else r.stderr)

# Nothing at all: a commit with neither lines nor records.
plan, proj, env = rec_world("rec-none")
(proj / "x.txt").write_text("x\n")
commit(proj, env, "Stage 1 Task 1.1: work")
r, doc = run_json(str(plan), "--repo", str(proj))
f8, f9 = (task_findings(doc, 8), task_findings(doc, 9)) if doc else ([], [])
if f8 and f8[0]["severity"] == "blocking" and r.returncode == 1:
    ok("a task commit with no proof at all is blocking on 8")
else:
    bad("no proof must be blocking on 8", json.dumps(doc, indent=2)[:900] if doc else r.stderr)
# Upstream rule: an unaccounted requirement is reported, never blocking — finding
# 9 carries no blocking mandate until it is measured.
if f9 and all(f["severity"] == "advisory" for f in f9) and "not shown met" in f9[0]["rule"]:
    ok("an unaccounted requirement is advisory on 9, never blocking")
else:
    bad("an unaccounted requirement must be advisory (red if finding 9 blocks)", str(f9)[:400])

# A requirement recorded as a deviation: advisory, named.
plan, proj, env = rec_world("rec-dev")
subprocess.run(["git", "-C", str(proj), "add", "-A"], check=True, env=env)
prove_task(plan, proj, req_kind="deviation")
commit(proj, env, "Stage 1 Task 1.1: with a deviation")
r, doc = run_json(str(plan), "--repo", str(proj))
f9 = task_findings(doc, 9) if doc else []
if f9 and f9[0]["severity"] == "advisory" and "deviation" in f9[0]["rule"] and not task_findings(doc, 8):
    ok("a requirement recorded as a deviation is an advisory naming it")
else:
    bad("a deviation must be advisory", str(f9)[:400])

# A ticked task with no commit naming it: finding 8 advisory, finding 9 silent.
plan, proj, env = rec_world("rec-nocommit")
r, doc = run_json(str(plan), "--repo", str(proj))
f8, f9 = (task_findings(doc, 8), task_findings(doc, 9)) if doc else ([], [])
if f8 and "no commit" in f8[0]["rule"] and f8[0]["severity"] == "advisory" and not f9:
    ok("a ticked task with no commit: finding 8 advisory, finding 9 leaves it to 8")
else:
    bad("no-commit must be one advisory, from finding 8", f"f8={f8} f9={f9}")

# The claim set a ticked task must prove (upstream rule): its FIRST claim, and
# every claim that names its break "(red if …)". Any other claim needs no record.
# Catches: named breaks not required. Two claims, both named, only the first proven.
plan, proj, env = rec_world("rec-two")
plan.write_text(REC_PLAN.replace("(red if add subtracts)\n",
                                 "(red if add subtracts); add is commutative (red if add ignores b)\n"))
subprocess.run(["git", "-C", str(proj), "add", "-A"], check=True, env=env)
prove_task(plan, proj)
commit(proj, env, "Stage 1 Task 1.1: two claims, one proven")
r, doc = run_json(str(plan), "--repo", str(proj))
f8 = task_findings(doc, 8) if doc else []
if f8 and f8[0]["severity"] == "blocking" and "1 of 2 required claim" in f8[0]["rule"]:
    ok("a missing record for a claim that names its break is blocking")
else:
    bad("named breaks need a record (red if named breaks are not required)", str(f8)[:400])

# Catches: every claim required. The second claim names no break and has no record.
plan, proj, env = rec_world("rec-unnamed")
plan.write_text(REC_PLAN.replace("(red if add subtracts)\n",
                                 "(red if add subtracts); add is commutative\n"))
subprocess.run(["git", "-C", str(proj), "add", "-A"], check=True, env=env)
prove_task(plan, proj)
commit(proj, env, "Stage 1 Task 1.1: second claim names no break")
r, doc = run_json(str(plan), "--repo", str(proj))
f8 = task_findings(doc, 8) if doc else []
if doc is not None and not f8:
    ok("a claim with no named break and no record is clean")
else:
    bad("only the first claim and named breaks need records (red if every claim is required)",
        str(f8)[:400] if doc else r.stderr)

# Catches: the first claim not required. Claim 1 names no break and has no record;
# claim 2 names its break and is proven.
plan, proj, env = rec_world("rec-first")
plan.write_text(REC_PLAN.replace("add returns the sum (red if add subtracts)\n",
                                 "add is defined; add returns the sum (red if add subtracts)\n"))
subprocess.run(["git", "-C", str(proj), "add", "-A"], check=True, env=env)
brk = prove_task(plan, proj)
# prove_task records claim 1; drop it, and prove claim 2 with the same break.
(proj / "proof" / plan.stem / "1.1" / "claim-1.json").unlink()
r2 = subprocess.run([sys.executable, str(PC), "claim", "--repo", str(proj), "--plan", str(plan),
                     "--task", "1.1", "--claim", "2", "--break", str(brk), "--test",
                     "python3 tests/test_calc.py", "--build", BUILD], capture_output=True, text=True)
assert r2.returncode == 0, r2.stderr
commit(proj, env, "Stage 1 Task 1.1: first claim unrecorded")
r, doc = run_json(str(plan), "--repo", str(proj))
f8 = task_findings(doc, 8) if doc else []
if f8 and f8[0]["severity"] == "blocking" and "claim 1:" in f8[0]["rule"]:
    ok("a ticked task whose first claim has no record is blocking")
else:
    bad("the first claim needs a record (red if the first claim is not required)",
        str(f8)[:400] if doc else r.stderr)

# Catches: a claim deviation counted as proof. claim-1.json holds a claim
# deviation (prove-claim.py deviation --claim): disclosed, so advisory — never clean.
plan, proj, env = rec_world("rec-claimdev")
subprocess.run(["git", "-C", str(proj), "add", "-A"], check=True, env=env)
prove_task(plan, proj)
fp = subprocess.run([sys.executable, str(PC), "fingerprint", "--repo", str(proj)],
                    capture_output=True, text=True).stdout.strip()
rp = proj / "proof" / plan.stem / "1.1" / "claim-1.json"
rp.write_text(json.dumps({"schema": 2, "kind": "claim-deviation", "plan": str(plan),
                          "task": "1.1", "index": 1,
                          "text": "add returns the sum (red if add subtracts)",
                          "why": "the evidence lives outside the repo", "fingerprint": fp,
                          "created": "2026-10-04T00:00:00+00:00"}))
commit(proj, env, "Stage 1 Task 1.1: claim recorded as a deviation")
r, doc = run_json(str(plan), "--repo", str(proj))
f8 = task_findings(doc, 8) if doc else []
if (f8 and all(f["severity"] == "advisory" for f in f8) and "deviation" in f8[0]["rule"]
        and "outside the repo" in f8[0]["rule"]):
    ok("a claim recorded as a deviation is an advisory naming it, not clean")
else:
    bad("a claim deviation must be advisory (red if a claim deviation counts as proof)",
        str(f8)[:400] if doc else r.stderr)
# The same deviation without a reason is no record at all: blocking.
d = json.loads(rp.read_text()); d["why"] = ""
rp.write_text(json.dumps(d))
commit(proj, env, "Stage 1 Task 1.1: deviation with no reason")
r, doc = run_json(str(plan), "--repo", str(proj))
f8 = task_findings(doc, 8) if doc else []
if f8 and f8[0]["severity"] == "blocking":
    ok("a claim deviation without a reason is blocking")
else:
    bad("a reasonless claim deviation must be blocking (red if it is waived silently)", str(f8)[:400])

# A claim deviation is bound like a proof: to its path, the plan's wording and
# its commit's tree. Each of these is blocking, never a disclosed advisory.
def claimdev_world(label, mutate):
    plan, proj, env = rec_world(label)
    subprocess.run(["git", "-C", str(proj), "add", "-A"], check=True, env=env)
    prove_task(plan, proj)
    fp = subprocess.run([sys.executable, str(PC), "fingerprint", "--repo", str(proj)],
                        capture_output=True, text=True).stdout.strip()
    rec = {"schema": 2, "kind": "claim-deviation", "plan": str(plan), "task": "1.1", "index": 1,
           "text": "add returns the sum (red if add subtracts)",
           "why": "the evidence lives outside the repo", "fingerprint": fp,
           "created": "2026-10-04T00:00:00+00:00"}
    mutate(rec, plan, proj)
    (proj / "proof" / plan.stem / "1.1" / "claim-1.json").write_text(json.dumps(rec))
    commit(proj, env, f"Stage 1 Task 1.1: {label}")
    r, doc = run_json(str(plan), "--repo", str(proj))
    return task_findings(doc, 8) if doc else []


f8 = claimdev_world("claimdev-index", lambda rec, plan, proj: rec.update(index=2))
if f8 and f8[0]["severity"] == "blocking" and "not Task 1.1 #1" in f8[0]["rule"]:
    ok("a claim deviation stored at another claim's path is blocking")
else:
    bad("a claim deviation must match its path (red if task/index are not compared)", str(f8)[:400])
f8 = claimdev_world("claimdev-wording", lambda rec, plan, proj: rec.update(text="add returns a total"))
if f8 and f8[0]["severity"] == "blocking" and "different wording" in f8[0]["rule"]:
    ok("a claim deviation recorded against other wording is blocking")
else:
    bad("a claim deviation must match the plan's wording (red if wording is not compared)",
        str(f8)[:400])
f8 = claimdev_world("claimdev-tree", lambda rec, plan, proj: (proj / "calc.py").write_text(
    CALC + "# changed after the deviation was recorded\n"))
if f8 and f8[0]["severity"] == "blocking" and "different tree" in f8[0]["rule"]:
    ok("a claim deviation recorded on another tree than its commit's is blocking")
else:
    bad("a claim deviation must be bound to its commit (red if the fingerprint is not compared)",
        str(f8)[:400])

# Catches: unticked tasks audited. An open task with no commit is not a finding.
plan, proj, env = rec_world("rec-open")
plan.write_text(REC_PLAN.replace("**Status:** [x]", "**Status:** [ ]"))
r, doc = run_json(str(plan), "--repo", str(proj))
if doc is not None and not task_findings(doc, 8) and not task_findings(doc, 9):
    ok("an unticked task is not audited on 8 and 9")
else:
    bad("unticked tasks must be skipped", json.dumps(doc, indent=2)[:600] if doc else r.stderr)

# Catches: the task-id boundary. A commit for Task 1.10 is not one for Task 1.1.
plan, proj, env = rec_world("rec-110")
(proj / "x.txt").write_text("x\n")
commit(proj, env, "Stage 1 Task 1.10: other work\n\nmutation: x -> red")
r, doc = run_json(str(plan), "--repo", str(proj))
f8 = task_findings(doc, 8) if doc else []
if f8 and "no commit" in f8[0]["rule"]:
    ok("a 'Task 1.10' commit does not count as one for Task 1.1")
else:
    bad("task ids must match whole (red if 1.10 counts as 1.1)", str(f8)[:400])

# Catches: legacy `deviation:` lines ignored. Lines alone stay legacy, not blocking.
plan, proj, env = rec_world("rec-legacy-dev")
(proj / "x.txt").write_text("x\n")
commit(proj, env, "Stage 1 Task 1.1: work\n\nmutation: add subtracts -> red\n"
                  "deviation: add is checked by the claim")
r, doc = run_json(str(plan), "--repo", str(proj))
f9 = task_findings(doc, 9) if doc else []
if f9 and f9[0]["severity"] == "advisory" and "legacy" in f9[0]["rule"]:
    ok("legacy `deviation:` lines alone are a legacy advisory on 9")
else:
    bad("deviation lines must count as legacy evidence", str(f9)[:400])

# Without --repo, 8 and 9 are NOT RUN, never clean.
r, doc = run_json(str(plan))
nr = {c["finding"]: c.get("reason", "") for c in (doc or {}).get("checks_not_run", [])}
if doc is not None and 8 in nr and 9 in nr and "--repo" in nr[8]:
    ok("without --repo, findings 8 and 9 are NOT RUN and say to pass --repo")
else:
    bad("no --repo must leave 8 and 9 not run", json.dumps(doc, indent=2)[:400] if doc else "")

# ------------------------------- amendment notes are history, never clauses
# A plan amended under the protocol carries notes like
# `*(amended 2026-10-04 per … — was: …; …)*` inside a task's description or
# Test field. Split as clauses, one note read as two extra requirements.
print()
print("clause splitting ignores amendment / superseded notes")
import importlib.util as _ilu  # noqa: E402
_spec = _ilu.spec_from_file_location("pfa_clauses", SCRIPT)
_pfa = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_pfa)
plain = "Do a; do b. Then do c."
noted = ("Do a; do b *(amended 2026-10-04 per x — was: do b; then d. Also e)*. "
         "Then do c. *(superseded 2026-10-04 by commit abc; see y. Done)*")
if _pfa.requirement_clauses(noted) == _pfa.requirement_clauses(plain) == ["Do a", "do b", "Then do c."]:
    ok("a description's amendment and superseded notes add no requirement clauses")
else:
    bad("notes must not be clauses", f"{_pfa.requirement_clauses(noted)} vs {_pfa.requirement_clauses(plain)}")
t_plain = "`make t` — one works; two works"
t_noted = "`make t` — one works; two works *(superseded 2026-10-04 by commit abc — the x; y)*"
if len(_pfa.claim_clauses(t_noted)) == len(_pfa.claim_clauses(t_plain)) == 2:
    ok("a Test field's superseded note adds no claims")
else:
    bad("notes must not be claims", _pfa.claim_clauses(t_noted))

# Catches: a note used to hide a requirement. A note without history (no date,
# no was:, no by commit) is not history; it counts. And a code span is never a note.
hidden = "Do a. *(amended: do b too; and c)*"
if _pfa.count_requirements(hidden) == 3:
    ok("a note with no history in it is not stripped — its clauses still count")
else:
    bad("a history-free note must still count", _pfa.requirement_clauses(hidden))
spanned = "Do a; run `x *(amended 2026-10-04 was: y)*` exactly"
if _pfa.count_requirements(spanned) == 2 and "amended" in _pfa.requirement_clauses(spanned)[1]:
    ok("a note-shaped string inside a code span is kept")
else:
    bad("code spans must not be stripped as notes", _pfa.requirement_clauses(spanned))


# ------------------------- finding 10: a live-check remediation with no fixture sweep
# BL-140: a remediation round fitted to the one capture a failed live run left
# behind, then re-ran the live check, 15 minutes a turn, several turns. The rule
# (gate-failure-procedure.md § Remediation that re-runs a live check): sweep every
# capture on the host first and record the command as a `fixture-sweep:` trailer.
print()
print("finding 10 — a live-check remediation commit with no fixture-sweep: trailer")
LIVE_PLAN = (
    "# Plan\n\n## Stage 1: parser\n\n"
    "### Task 1.1: parse\n- **Status:** [ ]\n"
    "- **Test:** `python3 t.py` — parses (red if it does not)\n\n"
    "### Stage 1 Gate\n\n"
    "- [ ] Stage-scope: `make test` exits 0\n"
    "- [ ] **Live check, session-driven:** a real bot session answers the prompt\n\n"
    "## Stage 2: docs\n\n"
    "### Task 2.1: docs\n- **Status:** [ ]\n"
    "- **Test:** `python3 d.py` — documents (red if it does not)\n\n"
    "### Stage 2 Gate\n\n"
    "- [ ] Stage-scope: `make test` exits 0\n"
)


def live_world(label, subject, body=""):
    vault = newdir(f"{label}-vault")
    proj, env = newrepo(f"{label}-proj")
    (proj / "README").write_text("x\n")
    commit(proj, env, "base")
    plan = vault / "2026-10-01-live-plan.md"
    plan.write_text(LIVE_PLAN)
    (proj / "parser.py").write_text("x = 1\n")
    commit(proj, env, subject + ("\n\n" + body if body else ""))
    return plan, proj, env


# Catches: the finding silent — a live-check remediation with no sweep reads as clean.
plan, proj, env = live_world("live-nosweep", "Stage 1 gate remediation round 1: fit the parser")
r, doc = run_json(str(plan), "--repo", str(proj))
f10 = findings_of(doc, 10) if doc else []
if len(f10) == 1 and f10[0].get("severity") == "advisory" and 10 in doc.get("checks_run", []):
    ok("a live-check gate's remediation commit with no fixture-sweep: trailer is reported advisory")
else:
    bad("a live-check remediation with no sweep must be finding 10, advisory (red if it is silent)",
        json.dumps(doc, indent=2)[:900] if doc else r.stderr)
# Catches: the severity raised — an advisory heuristic turned into a RED gate.
if f10 and r.returncode == 4 and not any(f.get("severity") == "blocking" for f in f10):
    ok("finding 10 alone exits 4, never 1 — it is never blocking")
else:
    bad(f"finding 10 must never block (red if it changes the exit code); exit {r.returncode}",
        json.dumps(f10, indent=2)[:400])

# Catches: the trailer ignored — the sweep was recorded and the finding fires anyway.
plan, proj, env = live_world("live-sweep", "Stage 1 gate remediation round 1: fit the parser",
                             "fixture-sweep: python3 -m pytest tests/captures  # 3 captures")
r, doc = run_json(str(plan), "--repo", str(proj))
if doc is not None and not findings_of(doc, 10) and 10 in doc.get("checks_run", []) \
        and r.returncode == 0:
    ok("the same remediation with a fixture-sweep: trailer is clean")
else:
    bad("a recorded fixture sweep must satisfy finding 10 (red if the trailer is ignored)",
        json.dumps(doc, indent=2)[:900] if doc else r.stderr)

# Catches: every remediation flagged — Stage 2's gate has no live check.
plan, proj, env = live_world("live-hostonly", "Stage 2 gate remediation round 1: reword the docs")
r, doc = run_json(str(plan), "--repo", str(proj))
if doc is not None and not findings_of(doc, 10) and 10 in doc.get("checks_run", []) \
        and r.returncode == 0:
    ok("a remediation of a gate with no live check is clean")
else:
    bad("only a gate with a **Live check line is in scope (red if every remediation is flagged)",
        json.dumps(doc, indent=2)[:900] if doc else r.stderr)

# Catches: the date bound dropped — a "Stage 1 gate remediation" from a plan the
# repo executed before this one was written is not this plan's remediation.
vault = newdir("live-old-vault")
proj, env = newrepo("live-old-proj")
(proj / "README").write_text("x\n")
old_env = dict(env, GIT_AUTHOR_DATE="2026-09-01T12:00:00+00:00",
               GIT_COMMITTER_DATE="2026-09-01T12:00:00+00:00")
commit(proj, old_env, "Stage 1 gate remediation round 1: another plan's work")
plan = vault / "2026-10-01-live-plan.md"
plan.write_text(LIVE_PLAN)
r, doc = run_json(str(plan), "--repo", str(proj))
if doc is not None and not findings_of(doc, 10) and 10 in doc.get("checks_run", []) \
        and r.returncode == 0:
    ok("a remediation commit older than the plan's date is another plan's, not flagged")
else:
    bad("finding 10 must read only commits from the plan's date on",
        json.dumps(doc, indent=2)[:900] if doc else r.stderr)

# Catches (Stage 3 review I1): the comma form `Stage N gate, remediation round K` — this
# repo's dominant remediation subject until 2026-10-04 — read as no remediation at all.
plan, proj, env = live_world("live-comma", "Stage 1 gate, remediation round 1: fit the parser")
r, doc = run_json(str(plan), "--repo", str(proj))
if doc is not None and len(findings_of(doc, 10)) == 1:
    ok("the comma form `Stage N gate, remediation` is a remediation commit too")
else:
    bad("finding 10 must read `Stage N gate, remediation` (red if the comma form is missed)",
        json.dumps(doc, indent=2)[:900] if doc else r.stderr)

# Catches (Stage 3 review S3): the "on or after" boundary — a commit dated ON the plan's
# date is this plan's.
vault = newdir("live-same-vault")
proj, env = newrepo("live-same-proj")
(proj / "README").write_text("x\n")
same_env = dict(env, GIT_AUTHOR_DATE="2026-10-01T09:00:00+00:00",
                GIT_COMMITTER_DATE="2026-10-01T09:00:00+00:00")
commit(proj, same_env, "Stage 1 gate remediation round 1: same day")
plan = vault / "2026-10-01-live-plan.md"
plan.write_text(LIVE_PLAN)
r, doc = run_json(str(plan), "--repo", str(proj))
if doc is not None and len(findings_of(doc, 10)) == 1:
    ok("a remediation commit dated on the plan's own date is in scope")
else:
    bad("the date bound is `on or after` the plan's date (red if the same day is dropped)",
        json.dumps(doc, indent=2)[:900] if doc else r.stderr)


for d_ in _tmpdirs:
    shutil.rmtree(d_, ignore_errors=True)

print()
print(f"passed {passed}, failed {failed}")
sys.exit(1 if failed else 0)
