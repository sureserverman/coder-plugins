#!/usr/bin/env bash
# dispatch-log.sh — Claude Code hook (PreToolUse matcher Agent, SubagentStart,
# SubagentStop): log every agent dispatch, start and stop of a plan run.
#
# WHY. A gate report's review line says which reviews were dispatched, and until
# this hook that line was the only record of it — a self-report (DEC-019's ledger).
# This hook gathers; review-ledger-check.py decides (DEC-027): at each gate it
# compares the claimed reviews with the `dispatch` lines here, and at close-out and
# a handoff it lists agents with a `start` and no `stop`.
#
# INERT UNLESS A PLAN IS IN FLIGHT. It runs on every Agent call of every user who
# enables the plugin, so it does nothing — no Python, no write — unless
# $CLAUDE_PROJECT_DIR/.claude/plan-progress.json exists. A `.claude` or log that is
# a symlink is never written through.
#
# ONE LINE PER EVENT, appended to $CLAUDE_PROJECT_DIR/.claude/dispatch-log.jsonl:
#   {"ts", "event": "dispatch", "session_id", "subagent_type", "description"}
#   {"ts", "event": "start"|"stop", "session_id", "agent_type", "agent_id"}
# PreToolUse does not carry the agent id of the launch it precedes (Claude Code
# 2.1.291), so a dispatch and its start are matched by type, not by id.
#
# IT NEVER BLOCKS. Every error exits 0 with empty stdout: a hook's stdout can be
# read as a decision, and a dispatch must never fail because logging did.
D="${CLAUDE_PROJECT_DIR:-}"
[ -n "$D" ] && [ -d "$D/.claude" ] && [ ! -L "$D/.claude" ] \
    && [ -f "$D/.claude/plan-progress.json" ] && [ ! -L "$D/.claude/dispatch-log.jsonl" ] \
    || { cat >/dev/null 2>&1; exit 0; }  # drain stdin: the caller's write must not hit EPIPE
DISPATCH_LOG="$D/.claude/dispatch-log.jsonl" python3 -c '
import datetime, json, os, sys
try:
    p = json.loads(sys.stdin.read())
except Exception:
    sys.exit(0)
if not isinstance(p, dict):
    sys.exit(0)
ev = p.get("hook_event_name")
line = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "session_id": p.get("session_id")}
if ev == "PreToolUse" and p.get("tool_name") in ("Agent", "Task"):
    ti = p.get("tool_input")
    if not isinstance(ti, dict):
        sys.exit(0)
    line.update(event="dispatch", subagent_type=ti.get("subagent_type") or "general-purpose",
                description=ti.get("description"))
elif ev in ("SubagentStart", "SubagentStop") and p.get("agent_id"):
    line.update(event="start" if ev == "SubagentStart" else "stop",
                agent_type=p.get("agent_type"), agent_id=p.get("agent_id"))
else:
    sys.exit(0)
fd = os.open(os.environ["DISPATCH_LOG"], os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
with os.fdopen(fd, "a") as fh:
    fh.write(json.dumps(line) + "\n")
' >/dev/null 2>&1
exit 0
