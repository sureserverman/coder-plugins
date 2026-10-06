#!/usr/bin/env python3
"""Fixture suite for review-ledger-check.py — run directly (repo convention):

    python3 planning/skills/executing-plans/tests/test-review-ledger-check.py

WHAT THIS SUITE IS REALLY GUARDING. A gate report's review line was a self-report:
"review: Tier-2 git-github:code-reviewer over <base>..HEAD — APPROVE" read the same
whether a reviewer ran or not (DEC-019's ledger). review-ledger-check.py compares each
claimed dispatch with the dispatch log hooks/dispatch-log.sh writes. The failures that
matter: a fabricated review passing, an old dispatch (an earlier stage's) satisfying a
new claim, a missing log reading as green, a disclosed SUBSTITUTED line being refused,
and an agent left running going unreported. One case builds its log through the real
hook, so the script and the hook cannot drift apart on the line format.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "review-ledger-check.py"
HOOK = HERE.parents[2] / "hooks" / "dispatch-log.sh"

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ok    {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}")
        if detail:
            print(f"        | {str(detail)[:700]}")


GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t"}


def git(repo, *args, date=None):
    env = dict(GIT_ENV)
    if date:
        env["GIT_COMMITTER_DATE"] = env["GIT_AUTHOR_DATE"] = date
    return subprocess.run(["git", "-C", str(repo), *args], env=env, capture_output=True,
                          text=True, check=True)


def mkrepo(root):
    repo = Path(root) / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "work")
    (repo / ".claude").mkdir()
    (repo / "f").write_text("0\n")
    git(repo, "add", "f")
    git(repo, "commit", "-q", "-m", "base", date="2026-10-06T08:00:00+00:00")
    return repo


def commit(repo, subject, date):
    (repo / "f").write_text(subject + "\n")
    git(repo, "commit", "-q", "-am", subject, date=date)


def write_log(repo, rows):
    with open(repo / ".claude" / "dispatch-log.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def dispatch(ts, stype):
    return {"ts": ts, "event": "dispatch", "session_id": "s", "subagent_type": stype,
            "description": "d"}


def agent(ts, event, aid, atype):
    return {"ts": ts, "event": event, "session_id": "s", "agent_type": atype, "agent_id": aid}


PLAN = """# Project Plan: fixture

## Stage 1: one

### Task 1.1: a
- **Status:** [x]

### Stage 1 Gate

- [x] Stage-scope: `true`

**Handoff (Stage 1):**
{s1}

---

## Stage 2: two

### Task 2.1: b
- **Status:** [x]

### Stage 2 Gate

- [ ] Stage-scope: `true`

**Handoff (Stage 2):**
{s2}
"""


_plans = 0


def write_plan(root, s1="", s2=""):
    # A file per call: a case holding an earlier plan must not read a later one's text.
    global _plans
    _plans += 1
    p = Path(root) / f"fixture-{_plans}-plan.md"
    p.write_text(PLAN.format(s1=s1, s2=s2))
    return p


def run(*args, stdin=None):
    r = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True,
                       text=True, input=stdin)
    return r.returncode, r.stdout + r.stderr


REVIEW = "review: Tier-2 git-github:code-reviewer over 1a2b3c..HEAD — APPROVE, 0 Critical"

print("review-ledger-check — claimed reviews against the dispatch log, and agents left running")
print()

if not SCRIPT.exists():
    print(f"FAIL: {SCRIPT} does not exist")
    sys.exit(1)

with tempfile.TemporaryDirectory() as t:
    repo = mkrepo(t)
    commit(repo, "Stage 1 green", "2026-10-06T10:00:00+00:00")

    # Catches: a real review being refused.
    plan = write_plan(t, s2=REVIEW)
    write_log(repo, [dispatch("2026-10-06T10:05:00+00:00", "git-github:code-reviewer")])
    rc, out = run("--plan", plan, "--stage", 2, "--repo", repo)
    check("a claimed Tier-2 review with a matching dispatch passes", rc == 0, f"rc={rc} {out}")

    # Catches: a fabricated review passing — no dispatch of the claimed type.
    write_log(repo, [dispatch("2026-10-06T10:05:00+00:00", "general-purpose")])
    rc, out = run("--plan", plan, "--stage", 2, "--repo", repo)
    check("a claimed review with no dispatch of that type exits 1 naming it",
          rc == 1 and "git-github:code-reviewer" in out, f"rc={rc} {out}")

    # Catches: an old dispatch (before the previous stage's green commit) satisfying a new claim.
    write_log(repo, [dispatch("2026-10-06T09:55:00+00:00", "git-github:code-reviewer")])
    rc, out = run("--plan", plan, "--stage", 2, "--repo", repo)
    check("a dispatch before the previous stage's green commit does not count",
          rc == 1 and "git-github:code-reviewer" in out, f"rc={rc} {out}")

    # Catches: two passes claimed on one dispatch (high tier's second pass).
    plan2 = write_plan(t, s2=REVIEW + "\nreview: second pass git-github:code-reviewer over "
                       "1a2b3c..HEAD — APPROVE")
    write_log(repo, [dispatch("2026-10-06T10:05:00+00:00", "git-github:code-reviewer")])
    rc, out = run("--plan", plan2, "--stage", 2, "--repo", repo)
    check("two claimed passes need two dispatches", rc == 1, f"rc={rc} {out}")

    # Catches: an evaluator claim escaping the check.
    plan3 = write_plan(t, s2="evaluator: general-purpose in the goal-evaluator role, briefed "
                       "on the stage goal + gate criteria — PASS")
    write_log(repo, [dispatch("2026-10-06T10:05:00+00:00", "git-github:code-reviewer")])
    rc, out = run("--plan", plan3, "--stage", 2, "--repo", repo)
    check("a claimed evaluator with no general-purpose dispatch exits 1",
          rc == 1 and "general-purpose" in out, f"rc={rc} {out}")

    # Catches: a claim dodging the grammar — a verdict with no named dispatched agent.
    plan4 = write_plan(t, s2="review: Tier-2 deep review done — APPROVE, 0 Critical")
    rc, out = run("--plan", plan4, "--stage", 2, "--repo", repo)
    check("a review line stating a verdict but naming no agent exits 1", rc == 1,
          f"rc={rc} {out}")

    # Catches: a tier-scope statement being refused.
    plan5 = write_plan(t, s2="review: Tier-2 not run — review-scope none mandates none")
    rc, out = run("--plan", plan5, "--stage", 2, "--repo", repo)
    check("a scope statement with no verdict passes", rc == 0, f"rc={rc} {out}")

    # Catches: DEC-019's disclosed path being refused.
    plan6 = write_plan(t, s2='review: Tier-2 SUBSTITUTED — ran inline, user authorised at '
                       'Preflight: "skip dispatch" — over 1a2b3c..HEAD — APPROVE')
    write_log(repo, [])
    rc, out = run("--plan", plan6, "--stage", 2, "--repo", repo)
    check("a SUBSTITUTED line passes with no dispatch", rc == 0, f"rc={rc} {out}")

    # Catches: a draft report (--report) being ignored in favour of the plan.
    draft = Path(t) / "draft.txt"
    draft.write_text(REVIEW + "\n")
    plan7 = write_plan(t, s2="")
    write_log(repo, [])
    rc, out = run("--plan", plan7, "--stage", 2, "--repo", repo, "--report", draft)
    check("--report is read instead of the plan's handoff note", rc == 1, f"rc={rc} {out}")

    # Catches: Stage 1 having no previous green commit to bound it — the log's start is the bound.
    plan8 = write_plan(t, s1=REVIEW)
    write_log(repo, [dispatch("2026-10-06T09:00:00+00:00", "git-github:code-reviewer")])
    rc, out = run("--plan", plan8, "--stage", 1, "--repo", repo)
    check("Stage 1 counts from the log's start", rc == 0, f"rc={rc} {out}")

    # Catches: no evidence reading as green.
    os.remove(repo / ".claude" / "dispatch-log.jsonl")
    rc, out = run("--plan", plan, "--stage", 2, "--repo", repo)
    check("a missing log exits 3 (NOT RUN), never 0", rc == 3 and "NOT RUN" in out,
          f"rc={rc} {out}")

    # Catches: an agent left running going unreported.
    write_log(repo, [agent("2026-10-06T10:01:00+00:00", "start", "a1", "general-purpose"),
                     agent("2026-10-06T10:02:00+00:00", "start", "a2", "git-github:code-reviewer"),
                     agent("2026-10-06T10:03:00+00:00", "stop", "a1", "general-purpose")])
    rc, out = run("--unstopped", "--repo", repo)
    check("--unstopped lists a started-never-stopped agent and exits 1",
          rc == 1 and "a2" in out and "a1" not in out, f"rc={rc} {out}")
    write_log(repo, [agent("2026-10-06T10:01:00+00:00", "start", "a1", "general-purpose"),
                     agent("2026-10-06T10:03:00+00:00", "stop", "a1", "general-purpose")])
    rc, out = run("--unstopped", "--repo", repo)
    check("--unstopped exits 0 when every started agent stopped", rc == 0, f"rc={rc} {out}")
    os.remove(repo / ".claude" / "dispatch-log.jsonl")
    rc, out = run("--unstopped", "--repo", repo)
    check("--unstopped with no log exits 3 (NOT RUN)", rc == 3, f"rc={rc} {out}")

    # Catches: the script and the hook disagreeing on the line format — the log is
    # written by piping hook inputs through the real dispatch-log.sh.
    (repo / ".claude" / "plan-progress.json").write_text('{"plan": "p", "phase": "gate"}\n')
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(repo)}
    for payload in (
        {"session_id": "s", "hook_event_name": "PreToolUse", "tool_name": "Agent",
         "tool_input": {"subagent_type": "git-github:code-reviewer", "description": "Stage 2",
                        "prompt": "p"}},
        {"session_id": "s", "hook_event_name": "SubagentStart", "agent_id": "h1",
         "agent_type": "git-github:code-reviewer"},
    ):
        subprocess.run(["bash", str(HOOK)], input=json.dumps(payload), text=True, env=env,
                       capture_output=True)
    rc, out = run("--plan", plan, "--stage", 2, "--repo", repo)
    check("a log written by the real hook satisfies a matching claim", rc == 0, f"rc={rc} {out}")
    rc, out = run("--unstopped", "--repo", repo)
    check("a start written by the real hook, with no stop, is listed by --unstopped",
          rc == 1 and "h1" in out, f"rc={rc} {out}")

    # Catches: a missing Stage N-1 green commit silently widening the window.
    repo2 = Path(t) / "r2"
    repo2.mkdir()
    git(repo2, "init", "-q", "-b", "work")
    (repo2 / ".claude").mkdir()
    (repo2 / "f").write_text("0\n")
    git(repo2, "add", "f")
    git(repo2, "commit", "-q", "-m", "base")
    write_log(repo2, [dispatch("2026-10-06T10:05:00+00:00", "git-github:code-reviewer")])
    rc, out = run("--plan", plan, "--stage", 2, "--repo", repo2)
    check("no `Stage N-1 green` commit is a usage error (exit 2), not a pass", rc == 2,
          f"rc={rc} {out}")

print()
print(f"{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
