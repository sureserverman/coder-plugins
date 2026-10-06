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
  a substitution     any line containing SUBSTITUTED — needs no dispatch (DEC-019:
                     a disclosed deviation, valid whatever the log says)
  a scope statement  a line stating no verdict ("review: Tier-2 not run — tier none")

A review line that states a verdict (APPROVE, PASS, FAIL, Critical, …) but fits
neither of the first two shapes is refused: a claim cannot leave the check by
leaving the grammar. Each claim needs its own `dispatch` line of that subagent_type
logged at or after the previous stage's `Stage N-1 green` commit (the newest commit
with that subject; for Stage 1, the log's start). Two claimed passes of one type
need two dispatches.

UNSTOPPED MODE (--unstopped). Lists every agent with a `start` line and no `stop`
line — an agent still running after the run that started it used its result.

EXIT CODES: 0 every claim matched / no agent left running · 1 a claimed dispatch
has no match, a verdict line names no agent, or an agent is still running (each
named) · 2 usage error (no Stage N section, no `Stage N-1 green` commit, unreadable
input) · 3 NOT RUN — the dispatch log is missing, so nothing was checked; never 0.
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
VERDICT = re.compile(r"\b(APPROVE\w*|REQUEST[_ -]CHANGES|PASS(ED)?|FAIL(ED)?|Critical|"
                     r"Important|Blocking|Material|findings?)\b")
REVIEW_CLAIM = re.compile(r"^review:\s+(?:.*\s)?(?P<type>[A-Za-z][\w.-]*(?::[\w.-]+)?)\s+over\s+\S")
EVALUATOR_CLAIM = re.compile(r"^evaluator:\s+(?P<type>[A-Za-z][\w.-]*(?::[\w.-]+)?)\s+in\s+the\s")


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
    out = []
    for raw in text.splitlines():
        line = raw.strip().lstrip("-*> ").strip().strip("`").strip()
        if re.match(r"^(review|evaluator):", line):
            out.append(line)
    return out


def classify(line):
    """('claim', type) | ('substituted', None) | ('scope', None) | ('unnamed', None)."""
    if "SUBSTITUTED" in line:
        return "substituted", None
    m = REVIEW_CLAIM.match(line) or EVALUATOR_CLAIM.match(line)
    if m:
        return "claim", m.group("type")
    return ("unnamed", None) if VERDICT.search(line) else ("scope", None)


def previous_green(repo, stage):
    """Committer time of the newest `Stage <stage-1> green` commit, or None for Stage 1."""
    if stage <= 1:
        return None
    subject = f"Stage {stage - 1} green"
    r = subprocess.run(["git", "-C", str(repo), "log", "--format=%cI%x09%s", "HEAD"],
                       capture_output=True, text=True)
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
            text = sys.stdin.read() if args.report == "-" else Path(args.report).read_text()
        except OSError as e:
            raise Usage(f"cannot read --report {args.report}: {e}")
    else:
        try:
            text = stage_section(Path(args.plan).read_text(errors="replace"), args.stage)
        except OSError as e:
            raise Usage(f"cannot read plan {args.plan}: {e}")
    lines = ledger_lines(text)
    since = previous_green(args.repo, args.stage)
    rows = read_log(args.repo)
    if rows is None:
        print(f"NOT RUN — no dispatch log at {Path(args.repo) / LOG}; no claimed review was "
              "checked. The hook (hooks/dispatch-log.sh) writes it only while "
              ".claude/plan-progress.json exists.")
        return 3
    pool = {}
    for r in rows:
        if r.get("event") != "dispatch":
            continue
        try:
            when = ts(r.get("ts"))
        except (TypeError, ValueError):
            continue
        if since is None or when >= since:
            pool[r.get("subagent_type")] = pool.get(r.get("subagent_type"), 0) + 1
    bad = []
    for line in lines:
        kind, stype = classify(line)
        if kind == "claim":
            if pool.get(stype, 0) > 0:
                pool[stype] -= 1
                print(f"  matched      {stype}: {line[:100]}")
            else:
                bad.append(f"no `{stype}` dispatch logged since "
                           f"{'the log start' if since is None else since.isoformat()}: {line}")
        elif kind == "unnamed":
            bad.append(f"states a verdict but names no dispatched agent "
                       f"(`<label> <subagent_type> over <range>`): {line}")
        else:
            print(f"  {kind:<12} {line[:100]}")
    for b in bad:
        print(f"  UNMATCHED    {b}")
    if not lines:
        print(f"  (no review: or evaluator: lines for Stage {args.stage})")
    return 1 if bad else 0


def unstopped(args):
    rows = read_log(args.repo)
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
