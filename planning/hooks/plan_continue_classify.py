#!/usr/bin/env python3
"""plan_continue_classify.py — the decision half of the `plan-continue` Stop hook.

Two callers share it: plan-continue.sh (the command hook, which keeps the repo-root
boundary, the hardened file reads and the no-progress counter, and imports this file
for the decision), and the planning mod, which runs it as a CLI:

    python3 plan_continue_classify.py  < {"state": {...}, "last_text": "...",
                                          "count": 0, "max": 3,
                                          "context_usage_path": "/.../context-usage.py"}
    -> {"decision": "allow" | "block", "reason"?: "...", "system_message"?: "..."}

`state` is the parsed .claude/plan-progress.json, `last_text` the last main-thread
assistant message, `count` how many continuations this phase|stage|task has already
been forced, `max` the limit (PLAN_CONTINUE_MAX). `system_message` is set only when
the no-progress guard releases a turn the classifier would have blocked; a caller
that keeps the counter advances it when the decision is `block` or that message is
present, and on nothing else.

THE CONTRACT IS FAIL-OPEN. Stdlib only. Malformed, non-object or oversized stdin, a
wrong-typed field, or any internal error prints {"decision":"allow"} and exits 0 —
never a traceback, never a non-zero exit. A Stop hook that fails closed traps the
session in a loop the user cannot leave.

EVERY INPUT STRING IS UNTRUSTED. A repo can commit .claude/plan-progress.json, so a
cloned repo's state file is user-owned and still hostile. Every state field that
reaches `reason` or `system_message` goes through clean() (whitespace flattened,
200 chars), and the whole reason is held to MAX_REASON_BYTES. `last_text` is read to
make a yes/no decision and is never quoted back.

The measurement behind the rules (39 turn ends, 7/7 bad stops caught, 0/30
legitimate waits blocked) is in plan-continue.sh's header and
../skills/executing-plans/references/plan-continue-hook.md.
"""

import json
import os
import re
import sys

ALLOW = {"decision": "allow"}

# An allow-list, so a phase added to the contract later fails open. `closeout`,
# `blocked` and `handoff` are deliberate stops (see plan-continue.sh).
ACTIVE_PHASES = ("preflight", "task", "gate")

DEFAULT_MAX = 3
MAX_FIELD = 200
MAX_REASON_BYTES = 2048
MAX_STDIN_BYTES = 8 * 1024 * 1024
MAX_SHOWN_COUNT = 10 ** 6

# A promise about the next unit of plan work.
PROMISE = re.compile(
    r"\b(next(?: is| up)?[:,]?\s+(?:task|stage)"
    r"|starting (?:now )?with (?:task|stage)"
    r"|i'?ll (?:start|begin|move|run|do)"
    r"|then (?:task|stage)\s*\d"
    r"|moving (?:on )?to (?:task|stage)"
    r"|proceeding to (?:task|stage)"
    r"|follows? next)\b", re.I)

# Asking permission to continue between green units — which SKILL.md § Run to
# completion names as the failure mode the skill exists to prevent.
ASK = re.compile(
    r"\b(want me to (?:carry|continue|proceed|start|go)"
    r"|ready to (?:start|begin|move)"
    r"|shall i (?:carry|continue|proceed|start)"
    r"|say the word"
    r"|whenever you want me to"
    r"|let me know (?:if|when) you"
    r"|or (?:would you rather|do you want)"
    r"|carry straight on)\b", re.I)

# Genuinely parked on work that the harness will report. These turn ends are
# correct on this host and are 30 of the 39 measured.
WAIT = re.compile(
    r"\b(waiting on|wait for"
    r"|once (?:it|they|both|the)"
    r"|when (?:it|they|both|the)\b.{0,30}\b(?:land|report|clear|finish|complete)"
    r"|still running|holding|blocked on|the monitor will|until (?:it|they))\b", re.I)

# A measured handoff (session-handoff.md) is a legal stop only when it carries
# context-usage.py's `reason:` line — a RESUME HERE block without one is the
# eyeball stop the rule replaced.
RESUME = re.compile(r"RESUME HERE", re.I)
REASON_LINE = re.compile(r"^[\s>*`_-]*reason:\s*\S", re.I | re.M)


def clean(value, default="", limit=MAX_FIELD):
    """Bound and flatten one untrusted field: newlines let planted text escape the
    sentence it sits in; length turns a 100 KB field into a 100 KB prompt."""
    text = str(value if value is not None else default)
    # A lone surrogate ("\ud800", legal in JSON) makes every later .encode() raise;
    # scrubbed here so a would-be block is not turned into an allow by an exception.
    text = text.encode("utf-8", "replace").decode("utf-8")
    text = " ".join(text.split())
    if len(text) > limit:
        text = text[:limit] + "...(truncated)"
    return text


def _int(value, default):
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return value


def _where(state, phase, limit):
    where = "phase %s, stage %s, task %s" % (clean(phase, "?", limit),
                                             clean(state.get("stage"), "?", limit),
                                             clean(state.get("task"), "?", limit))
    desc = clean(state.get("task_desc"), "", limit)
    if desc:
        where += " (%s)" % desc
    return where


def guard_message(state, count, limit=MAX_FIELD):
    key = "|".join(clean(str(state.get(k, "")), "", limit) for k in ("phase", "stage", "task"))
    return ("plan-continue: %d continuations with no movement past %s — letting the turn "
            "end so you can look. Raise PLAN_CONTINUE_MAX or unset PLAN_CONTINUE if this "
            "is wrong." % (count, key))


def handoff_reason(state, phase, context_usage_path, limit=MAX_FIELD):
    return (
        "You ended that turn with a RESUME HERE block that has no `reason:` line, while "
        "plan execution is in flight: %s — %s.\n\n"
        "executing-plans § Context resets / session-handoff.md: a handoff is a legal stop "
        "only on context-usage.py's verdict. Run it now, in its own Bash call:\n"
        "  python3 %s --plan <plan> --next-stage <N>\n"
        "On `handoff`, paste its reason: line into the RESUME HERE block verbatim and "
        "stop. On `continue` or `unknown`, delete the block and start the next stage now."
    ) % (clean(state.get("plan"), "the plan", limit), _where(state, phase, limit),
         clean(context_usage_path, "context-usage.py", limit))


def promise_reason(state, phase, limit=MAX_FIELD):
    return (
        "You ended that turn on an announcement or a question while plan execution is "
        "still in flight: %s — %s.\n\n"
        "executing-plans § Run to completion: stage boundaries are checkpoints, not "
        "approval gates, and the tool call opening announced work goes in the SAME turn "
        "as the sentence announcing it. Start the announced work now — do not re-plan, "
        "do not re-verify finished work, and do not summarise what you have done.\n\n"
        "If you genuinely need to stop, do it the documented ways rather than by "
        "trailing off: write an `ACTION NEEDED:` block naming the decision that blocks "
        "the next stage, write phase:\"blocked\" to .claude/plan-progress.json when a "
        "documented Stop condition has fired, or hand off at a gate on context-usage.py's "
        "`handoff` verdict with its reason: line. Waiting on a dispatched agent is not a "
        "stop — say what you are waiting on and this hook will let the turn end."
    ) % (clean(state.get("plan"), "the plan", limit), _where(state, phase, limit))


def _bounded(build):
    """Hold a reason (or the guard's system_message) to MAX_REASON_BYTES. Normal fields never reach the cap; when
    hostile ones do, tighten the per-field bound first so the instructions survive
    whole, and only then cut."""
    for limit in (MAX_FIELD, 60, 20):
        reason = build(limit)
        if len(reason.encode("utf-8", "replace")) <= MAX_REASON_BYTES:
            return reason
    cut = reason.encode("utf-8", "replace")[:MAX_REASON_BYTES - len(b"...(truncated)")]
    return cut.decode("utf-8", "ignore") + "...(truncated)"


def classify(inp):
    """The decision for one turn end. Never raises; anything unexpected allows."""
    try:
        return _classify(inp)
    except Exception:
        return dict(ALLOW)


def _classify(inp):
    if not isinstance(inp, dict):
        return dict(ALLOW)
    state = inp.get("state")
    last_text = inp.get("last_text")
    if not isinstance(state, dict) or not isinstance(last_text, str) or not last_text.strip():
        return dict(ALLOW)

    phase = str(state.get("phase", "")).strip().lower()
    if phase not in ACTIVE_PHASES:
        return dict(ALLOW)

    # The skill's own sanctioned ask. Checked over the WHOLE message: the block is
    # specified to come last, but a report that carries one is stopping on purpose
    # wherever it sits.
    if "ACTION NEEDED" in last_text:
        return dict(ALLOW)

    # Decided before the promise classifier, whose `next: Task N` pattern would
    # otherwise refuse a legitimate block's `next:` line.
    context_usage_path = inp.get("context_usage_path")
    bare_handoff = False
    m = RESUME.search(last_text)
    if m:
        if REASON_LINE.search(last_text[m.start():]):
            return dict(ALLOW)
        # The nudge sends the executor to run this script; with no script beside
        # the hook it cannot give that instruction, so it fails open.
        if (not isinstance(context_usage_path, str) or not context_usage_path
                or not os.path.isfile(context_usage_path)):
            return dict(ALLOW)
        bare_handoff = True
    else:
        tail = last_text[-400:]
        if not (PROMISE.search(tail) or ASK.search(tail)):
            return dict(ALLOW)
        if WAIT.search(tail):
            return dict(ALLOW)

    # No-progress guard: `count` continuations already forced at this key.
    count = _int(inp.get("count"), 0)
    limit = _int(inp.get("max"), DEFAULT_MAX)
    if count >= limit:
        # Clamped for display only: a 4000-digit JSON integer is a legal `count`.
        shown = max(-MAX_SHOWN_COUNT, min(count, MAX_SHOWN_COUNT))
        msg = _bounded(lambda n: guard_message(state, shown, n))
        return {"decision": "allow", "system_message": msg}

    if bare_handoff:
        reason = _bounded(lambda n: handoff_reason(state, phase, context_usage_path, n))
    else:
        reason = _bounded(lambda n: promise_reason(state, phase, n))
    return {"decision": "block", "reason": reason}


def main():
    result = dict(ALLOW)
    try:
        raw = sys.stdin.buffer.read(MAX_STDIN_BYTES + 1)
        if len(raw) <= MAX_STDIN_BYTES:
            result = classify(json.loads(raw.decode("utf-8", "replace")))
    except Exception:
        result = dict(ALLOW)
    try:
        sys.stdout.write(json.dumps(result) + "\n")
        sys.stdout.flush()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        pass
    os._exit(0)
