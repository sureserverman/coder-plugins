#!/usr/bin/env python3
"""review-ledger-check.py — a review a gate report claims was dispatched, was dispatched.

    review-ledger-check.py --plan P --stage N --repo R [--report F]
    review-ledger-check.py --unstopped --repo R

WHY THIS EXISTS. The gate report's review line (stage-gate.md § The gate report's
review line) names the agent that ran each review. Until 0.56.0 that line was a
self-report: a review the executor ran itself, or never ran, read exactly like one a
fresh agent ran (DEC-019's ledger). hooks/dispatch-log.sh now appends every Agent
dispatch, subagent start and stop of a plan run to <R>/.claude/dispatch-log.jsonl;
this script compares the two. The hook gathers, this script decides (DEC-027).

GATE MODE (--plan --stage). Reads Stage N's `review:` and `evaluator:` lines — from
--report F (a draft gate report; `-` is stdin) when given, else from the plan's
`## Stage N` section, where the handoff note carries them verbatim. Each line is one of:

  a dispatch claim   review: <label> <subagent_type> over <range> — <verdict>
                     evaluator: <subagent_type> in the <role> role … — <verdict>
  a substitution     SUBSTITUTED in the line's head — needs no dispatch (DEC-019:
                     a disclosed deviation, valid whatever the log says)
  a scope statement  a line naming no agent that says why no review ran — `not run`,
                     `not mandated`, an `opt-out`, a `trivial` diff
                     ("review: Tier-2 not run — tier none")

The agent and SUBSTITUTED are read from the line's head — the text before the first
` — ` — so nothing written after the verdict can supply either. Prefixes are read in
any case and under list markers or bold. Any other line is refused: "looked at the diff,
clean" claims a review whatever words it uses. Text may follow the range ("over a..b
(round 2): APPROVE"). The task field `Review: required` / `Review: skip` is not a ledger
line. A stage with no ledger line at all is NOT CHECKED (exit 3): a gate report
states every review, run or not.

Each claim needs its own `dispatch` line of that subagent_type whose description names
`Stage N` and the claim's role (the word review or pass, or evaluator) and names no `Task N.M`,
logged at or after the newest `Stage N-1 green` commit (for Stage 1, the log's start).
So the executor writes the dispatch description as `Stage N Tier-2 review` or
`Stage N gate evaluator`. Two claimed passes need two dispatches.

WHAT THIS DOES NOT DO. It cannot tell whether the agent was briefed on the right diff,
or whether the verdict quoted is the one it returned — only that a dispatch of the
claimed type and role happened in the stage's window. The window rests on the newest
commit with the exact subject `Stage N-1 green`: a missing or reworded commit from this
plan lets an older plan's commit open it, and a log left behind by a plan whose
close-out never ran satisfies Stage 1 claims.

UNSTOPPED MODE (--unstopped). Lists every agent with a `start` line and no `stop`
line — an agent still running after the run that started it used its result.

EXIT CODES: 0 every claim matched / no agent left running · 1 a claimed dispatch
has no match, a verdict line names no agent, or an agent is still running (each
named) · 2 usage error (no Stage N section, no `Stage N-1 green` commit, unreadable
input, no git) · 3 NOT RUN — the dispatch log is missing — or NOT CHECKED — no
review: or evaluator: line for the stage; never 0.
"""
import argparse
import datetime
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

LOG = Path(".claude") / "dispatch-log.jsonl"
_STALE = Path(__file__).resolve().parents[2] / "portfolio" / "scripts" / "_staleness.py"
# A line naming no agent is a scope statement only when it says why no review ran: the tier
# did not mandate it, an evidenced opt-out, or a trivial diff (stage-gate.md § The gate
# report's review line). Anything else naming no agent is refused — "looked at it, clean" is
# a claim of a review, whatever words it uses.
SCOPE_REASON = re.compile(r"\bnot run\b|\bnot mandated\b|\bmandates? none\b|\bopt-?out\b|"
                          r"\btrivial\b", re.I)
TYPE = r"(?P<type>[A-Za-z][\w.-]*(?::[\w.-]+)?)"
# Matched against the line's HEAD only — the text before the first ` — ` — so nothing
# written after the verdict ("… carried over to the backlog") can be read as the agent.
REVIEW_CLAIM = re.compile(rf"^review:\s+(?:[^—]*?[\s(])?{TYPE}\s+over\s+\S")
EVALUATOR_CLAIM = re.compile(rf"^evaluator:\s+{TYPE}\s+in\s+the\s")
VERDICT_SEP = re.compile(r"\s+(?:—|--)\s+")
LEDGER_PREFIX = re.compile(r"^(review|evaluator)\s*:", re.I)
# The task field `Review: required` / `Review: skip` (task-fields.md) shares the prefix and is
# never a ledger line.
TASK_FIELD = re.compile(r"^review:\s*(required|skip)\b", re.I)
LIST_MARKER = re.compile(r"^(?:[-*+>]|\d+[.)])\s+")
# A dispatch counts toward a stage's claim only when its description names that stage and
# the claim's role; one naming a task (`Task 2.1`) is per-task work, never the stage's pass.
ROLE = {"review": re.compile(r"\breview|\bpass\b", re.I),
        "evaluator": re.compile(r"evaluat", re.I)}
TASK_REF = re.compile(r"\bTask\s+\d+\.\d+\b", re.I)


def _warn_if_stale():
    try:
        spec = importlib.util.spec_from_file_location("_staleness", _STALE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.warn_if_stale(__file__)
    except Exception:  # noqa: BLE001 — a probe that cannot load must never stop the command
        pass


class Usage(Exception):
    pass


def ts(s):
    t = datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc)


def read_log(repo):
    """The log's rows, or None when there is no log. A row that is not JSON is skipped."""
    path = Path(repo) / LOG
    if not path.is_file():
        return None
    rows = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("event"):
            rows.append(row)
    return rows


def stage_section(plan_text, stage):
    m = re.search(rf"^## Stage {stage}\b.*$", plan_text, re.M)
    if not m:
        raise Usage(f"no `## Stage {stage}` section in the plan")
    nxt = re.search(r"^## ", plan_text[m.end():], re.M)
    return plan_text[m.end(): m.end() + nxt.start()] if nxt else plan_text[m.end():]


def ledger_lines(text):
    """Every review:/evaluator: line, whatever its case, list marker or emphasis, normalised
    to a lowercase prefix with the markup removed."""
    out = []
    for raw in text.splitlines():
        line = LIST_MARKER.sub("", raw.strip()).replace("**", "").strip().strip("`").strip()
        m = LEDGER_PREFIX.match(line)
        if m and not TASK_FIELD.match(line):
            out.append(m.group(1).lower() + ":" + line[m.end():])
    return out


def classify(line):
    """('claim', role, type) | ('substituted', …) | ('scope', …) | ('unnamed', …)."""
    head = VERDICT_SEP.split(line, maxsplit=1)[0]
    role = "evaluator" if line.startswith("evaluator:") else "review"
    if "SUBSTITUTED" in head:
        return "substituted", role, None
    m = REVIEW_CLAIM.match(head) or EVALUATOR_CLAIM.match(head)
    if m:
        return "claim", role, m.group("type")
    return ("scope" if SCOPE_REASON.search(line) else "unnamed"), role, None


def counts_for(row, stage, role):
    d = row.get("description") or ""
    return (re.search(rf"\bStage\s+{stage}\b", d, re.I) is not None
            and ROLE[role].search(d) is not None and not TASK_REF.search(d))


def previous_green(repo, stage):
    """Committer time of the newest `Stage <stage-1> green` commit, or None for Stage 1."""
    if stage <= 1:
        return None
    subject = f"Stage {stage - 1} green"
    try:
        r = subprocess.run(["git", "-C", str(repo), "log", "--format=%cI%x09%s", "HEAD"],
                           capture_output=True, text=True)
    except OSError as e:
        raise Usage(f"cannot run git: {e}")
    if r.returncode != 0:
        raise Usage(f"git log failed in {repo}: {r.stderr.strip()}")
    for row in r.stdout.splitlines():
        when, _, subj = row.partition("\t")
        if subj.strip() == subject:
            return ts(when)
    raise Usage(f"no `{subject}` commit on HEAD in {repo} — the window for Stage {stage}'s "
                "dispatches starts there, so nothing can be matched without it")


def gate(args):
    if args.report:
        try:
            text = (sys.stdin.read() if args.report == "-"
                    else Path(args.report).read_text(errors="replace"))
        except OSError as e:
            raise Usage(f"cannot read --report {args.report}: {e}")
    else:
        try:
            text = stage_section(Path(args.plan).read_text(errors="replace"), args.stage)
        except OSError as e:
            raise Usage(f"cannot read plan {args.plan}: {e}")
    lines = ledger_lines(text)
    since = previous_green(args.repo, args.stage)
    try:
        rows = read_log(args.repo)
    except OSError as e:
        raise Usage(f"cannot read the dispatch log: {e}")
    if rows is None:
        print(f"NOT RUN — no dispatch log at {Path(args.repo) / LOG}; no claimed review was "
              "checked. The hook (hooks/dispatch-log.sh) writes it only while "
              ".claude/plan-progress.json exists.")
        return 3
    if not lines:
        print(f"NOT CHECKED — no review: or evaluator: line for Stage {args.stage} "
              f"({'--report' if args.report else 'the plan section'}). A gate states every "
              "review, run or not; pass the draft report with --report.")
        return 3
    pool = []
    for r in rows:
        if r.get("event") != "dispatch":
            continue
        try:
            when = ts(r.get("ts"))
        except (TypeError, ValueError):
            continue
        if since is None or when >= since:
            pool.append(r)
    bad = []
    for line in lines:
        kind, role, stype = classify(line)
        if kind == "claim":
            hit = next((r for r in pool if r.get("subagent_type") == stype
                        and counts_for(r, args.stage, role)), None)
            if hit is not None:
                pool.remove(hit)
                print(f"  matched      {stype} ({hit.get('description')}): {line[:90]}")
            else:
                bad.append(f"no `{stype}` dispatch whose description names Stage {args.stage} "
                           f"and the {role} role, logged since "
                           f"{'the log start' if since is None else since.isoformat()}: {line}")
        elif kind == "unnamed":
            bad.append(f"names no dispatched agent as `<subagent_type> over <range>` before its "
                       f"first ` — `, and gives no reason a review did not run (not run, "
                       f"not mandated, opt-out, trivial): {line}")
        else:
            print(f"  {kind:<12} {line[:100]}")
    for b in bad:
        print(f"  UNMATCHED    {b}")
    return 1 if bad else 0


def unstopped(args):
    try:
        rows = read_log(args.repo)
    except OSError as e:
        raise Usage(f"cannot read the dispatch log: {e}")
    if rows is None:
        print(f"NOT RUN — no dispatch log at {Path(args.repo) / LOG}")
        return 3
    started, stopped = {}, set()
    for r in rows:
        aid = r.get("agent_id")
        if r.get("event") == "start" and aid:
            started.setdefault(aid, r)
        elif r.get("event") == "stop" and aid:
            stopped.add(aid)
    running = [r for aid, r in started.items() if aid not in stopped]
    for r in running:
        print(f"  RUNNING  {r.get('agent_id')} ({r.get('agent_type')}), started {r.get('ts')}")
    print(f"{len(running)} agent(s) started and never stopped")
    return 1 if running else 0


def main(argv=None):
    _warn_if_stale()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--plan")
    ap.add_argument("--stage", type=int)
    ap.add_argument("--report")
    ap.add_argument("--unstopped", action="store_true")
    args = ap.parse_args(argv)
    try:
        if args.unstopped:
            return unstopped(args)
        if not args.plan or args.stage is None:
            raise Usage("--plan and --stage are required (or --unstopped)")
        return gate(args)
    except Usage as e:
        print(f"review-ledger-check: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
