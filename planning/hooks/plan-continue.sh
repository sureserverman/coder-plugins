#!/usr/bin/env bash
# plan-continue.sh — Claude Code `Stop` hook that refuses a turn ending on a
# promise while a plan is in flight.
#
# WHY THIS EXISTS. `../skills/executing-plans/SKILL.md` § Run to completion already
# forbids this ("Never end a turn on an announcement", "stage boundaries are
# checkpoints, not approval gates"). The rule is read once, at session start, and
# the failure it describes happens hundreds of thousands of tokens later. Measured
# across two real remote-agents sessions executing one master plan (159a71ca,
# 2f7953d6, 2026-08-29/30) — 39 turn ends, of which:
#
#   * 30 ended waiting on a dispatched agent or a background suite. Every one was
#     resumed automatically by the harness's task notification within 0.5-51 min.
#     These are CORRECT on this host and must never be blocked.
#   *  7 ended on a future-tense promise or an approval question with nothing
#      pending: "starting now with Task 2.1", "Next is Task 2.2", "Say the word and
#      I'll start Task 2.1". Each needed a human nudge. Idle cost: 8.1 min, 16.6
#      min, and one overnight stop of 8 h 11 min.
#
# THAT ASYMMETRY IS THE WHOLE DESIGN. The Codex and Cursor ports of this hook
# (engineering-skills/ports/*/…/plan-continue.sh) block EVERY turn end while a plan
# runs, because on those hosts an assistant message *is* the turn boundary. Porting
# that policy here would fight the harness: it would force ~30 pointless
# continuations, each spinning against agents that had not reported yet. So this
# hook keeps the ports' in-flight signal and all of their hardening, and replaces
# their policy with a narrow classifier over the last assistant message.
#
# WHAT IT DOES. A Claude Code `Stop` hook may return {"decision":"block","reason":…},
# which keeps the turn going and hands `reason` to the model. This hook returns that
# only when ALL of the following hold:
#
#   1. PLAN_CONTINUE=1              — opt-in; the default is off.
#   2. .claude/plan-progress.json   — phase is preflight/task/gate. `closeout` and
#                                     `blocked` are excluded (see the allow-list),
#                                     and close-out DELETES the file, so the hook
#                                     self-disables when the plan finishes.
#   3. The last assistant message   — matches PROMISE or ASK, and matches neither
#                                     WAIT nor `ACTION NEEDED:`.
#
# Measured against the 39 turn ends above: 7/7 of the bad stops caught, 0 of the 30
# legitimate waits blocked. One further turn is blocked that the harness happened to
# rescue 4 min later ("Re-running the gate next, then Stage 3." — an announcement
# ending that got lucky), which is the intended reading rather than a miss.
#
# TWO DOCUMENTED WAYS TO STOP ON PURPOSE, both already in the skill's contract:
# write `ACTION NEEDED:` (stage-gate.md § the one place a report asks the user for
# something), or write phase:"blocked" to the state file (a documented Stop
# condition). Neither is invented here; the hook reads the contract that exists.
#
# IT FAILS OPEN, ALWAYS. No state file, unreadable transcript, unparseable JSON,
# missing or garbage timestamp, stale state, no progress — every one allows the
# stop. A Stop hook that fails closed traps a session in a loop the user cannot
# exit, which is strictly worse than the problem it solves. `set -e` is deliberately
# NOT used and every exit is 0.
#
# Kill switch: PLAN_CONTINUE=0 (or simply unset).

set -uo pipefail

PAYLOAD="$(cat)"

# Opt-in, checked before anything else can go wrong.
if [[ "${PLAN_CONTINUE:-0}" != "1" ]]; then
    exit 0
fi

# The payload goes through the ENVIRONMENT, not argv: /proc/<pid>/cmdline is
# world-readable, so passing it as an argument would publish session_id and the
# repo root to every local user — which is what made the counter path below
# predictable enough to pre-plant a symlink at, in the port this is derived from.
PLAN_CONTINUE_PAYLOAD="$PAYLOAD" python3 - <<'PY'
import json, os, sys, re, stat, hashlib, tempfile, datetime

STALE_HOURS = 12
try:
    MAX_NO_PROGRESS = int(os.environ.get("PLAN_CONTINUE_MAX", "3"))
except (TypeError, ValueError):
    MAX_NO_PROGRESS = 3


def allow(msg=None):
    """Let the turn end. Optionally surface one line to the user."""
    if msg:
        json.dump({"systemMessage": msg}, sys.stdout)
    sys.exit(0)


# --------------------------------------------------------------------------
# Repo root. THIS IS THE HOOK'S SECURITY BOUNDARY, inherited verbatim in intent
# from the port, where the first version was not: it climbed to `/` for any
# `.git`, then put the state file's `plan`/`task_desc` into a prompt the host
# replays. A `.git` planted in a shared ancestor made the hook submit
# attacker-chosen text. Depth-bounded, `.git` FILES count (worktrees), and a
# world-writable candidate root is refused. Every failure returns None -> allow.
# --------------------------------------------------------------------------
def find_repo_root(start, max_depth=16):
    try:
        probe = os.path.abspath(start)
    except Exception:
        return None
    for _ in range(max_depth + 1):
        marker = os.path.join(probe, ".git")
        if os.path.isdir(marker) or os.path.isfile(marker):
            try:
                st = os.stat(probe)
            except OSError:
                return None
            # WORLD-writable only, deliberately not group-writable: with umask 002
            # an ordinary mkdir yields 775, so refusing group-writable disables the
            # hook in normal users' own repos — hardening into a fail-closed hole.
            if st.st_mode & 0o002:
                return None
            return probe
        parent = os.path.dirname(probe)
        if parent == probe:
            return None
        probe = parent
    return None


MAX_STATE_BYTES = 256 * 1024


def read_own_file(path, max_bytes, tail=False):
    """Open ONCE and check the descriptor; return text, or None for any failure.

    O_NOFOLLOW  a symlinked state file leaked another repo's plan text.
    O_NONBLOCK  os.open on a FIFO BLOCKS until a writer appears, so S_ISREG below
                is never reached and the hook hangs until the host kills it — on
                every single turn end.
    fstat       ownership and regular-file checked on the open fd, not by path,
                so the name cannot be swapped in between.
    """
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            return None
        if st.st_uid != os.getuid():
            return None
        if not tail and st.st_size > max_bytes:
            return None
        if tail and st.st_size > max_bytes:
            os.lseek(fd, st.st_size - max_bytes, os.SEEK_SET)
        with os.fdopen(fd, "r", errors="replace") as fh:
            fd = None
            return fh.read(max_bytes + 1)
    except Exception:
        return None
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


try:
    payload = json.loads(os.environ.get("PLAN_CONTINUE_PAYLOAD", "") or "{}")
except Exception:
    allow()
if not isinstance(payload, dict):
    allow()

# stop_hook_active says a continuation already fired. We do NOT blanket-allow on
# it: a plan legitimately needs several in a row. The no-progress counter below is
# the loop guard instead, and it is a better one because it measures whether the
# run is actually moving rather than merely whether it was pushed.
root = find_repo_root(payload.get("cwd") or os.getcwd())
if root is None:
    allow()

raw_state = read_own_file(os.path.join(root, ".claude", "plan-progress.json"),
                          MAX_STATE_BYTES)
if raw_state is None:
    allow()
try:
    state = json.loads(raw_state)
except Exception:
    allow()
if not isinstance(state, dict):
    allow()

phase = str(state.get("phase", "")).strip().lower()

# AN ALLOW-LIST, NOT A DENY-LIST, so a phase added to the contract later fails
# OPEN. `blocked` means a documented Stop condition already halted the run and
# said so. `closeout` matters just as much: close-out ends by offering merge
# options that must not be auto-answered, and its remaining steps are short and
# end by deleting this file, so continuing through it buys nothing. It is also
# the phase at a master plan's sub-plan boundary, where master-plans.md
# RECOMMENDS stopping for a fresh session.
if phase not in ("preflight", "task", "gate"):
    allow()

# An absent or unparseable `updated` is treated as stale rather than fresh: fails
# open, and makes the defect visible instead of silently blocking forever.
try:
    ts = datetime.datetime.fromisoformat(str(state.get("updated", "")).replace("Z", "+00:00"))
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=datetime.timezone.utc)
except Exception:
    allow("plan-continue: .claude/plan-progress.json has no parseable `updated` "
          "timestamp; letting the turn end.")

age_h = (datetime.datetime.now(datetime.timezone.utc) - ts).total_seconds() / 3600.0
# A FUTURE timestamp is garbage and defeats the only time-based backstop: age_h
# goes negative, so the staleness test can never fire and the state never expires.
if age_h < -1.0:
    allow("plan-continue: `updated` is %.1fh in the FUTURE; letting the turn end." % -age_h)
if age_h > STALE_HOURS:
    allow("plan-continue: .claude/plan-progress.json is %.1fh stale; letting the turn "
          "end rather than resuming a run that may be long dead." % age_h)

# --------------------------------------------------------------------------
# The classifier. Applied to the LAST assistant message only, and its text is
# read to make a yes/no decision — never interpolated into the reason, which is
# built solely from clamped state-file fields.
# --------------------------------------------------------------------------
MAX_TRANSCRIPT_TAIL = 512 * 1024

transcript = payload.get("transcript_path")
if not isinstance(transcript, str) or not transcript:
    allow()
blob = read_own_file(transcript, MAX_TRANSCRIPT_TAIL, tail=True)
if not blob:
    allow()

last_text = None
lines = blob.splitlines()
# The tail may begin mid-line; that first fragment is dropped by json.loads failing.
for line in reversed(lines):
    try:
        row = json.loads(line)
    except Exception:
        continue
    if not isinstance(row, dict) or row.get("type") != "assistant":
        continue
    if row.get("isSidechain"):        # a subagent's own transcript, not ours
        continue
    msg = row.get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = "\n".join(b.get("text", "") for b in content
                         if isinstance(b, dict) and b.get("type") == "text")
    else:
        continue
    if text.strip():
        last_text = text
        break

if not last_text:
    allow()

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

tail = last_text[-400:]
if not (PROMISE.search(tail) or ASK.search(tail)):
    allow()
if WAIT.search(tail):
    allow()
# The skill's own sanctioned ask. Checked over the WHOLE message: the block is
# specified to come last, but a report that carries one is stopping on purpose
# wherever it sits.
if "ACTION NEEDED" in last_text:
    allow()

# --------------------------------------------------------------------------
# No-progress guard. Keyed per session so it needs no file in the user's repo.
# --------------------------------------------------------------------------
key = "|".join(str(state.get(k, "")) for k in ("phase", "stage", "task"))
# Hashed, never interpolated raw: session_id is host-supplied and this is a
# filename. Folding the root in stops two repos in one session sharing a counter.
sid = hashlib.sha1(("%s|%s" % (payload.get("session_id") or "", root)).encode()).hexdigest()[:16]
counter_path = os.path.join(tempfile.gettempdir(), "claude-plan-continue-%s.json" % sid)

count = 0
try:
    rfd = os.open(counter_path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(rfd, "r") as fh:
        prev = json.load(fh)
    if prev.get("key") == key:
        count = int(prev.get("count", 0))
except Exception:
    pass

count += 1
try:
    # O_NOFOLLOW: the tmpdir is world-writable, and a symlink pre-planted here made
    # open(path,"w") overwrite whatever it pointed at — an arbitrary file write as
    # the user. 0600 keeps the counter unreadable by whoever planted it.
    wfd = os.open(counter_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(wfd, "w") as fh:
        json.dump({"key": key, "count": count}, fh)
except Exception:
    pass    # a counter we cannot persist must not block the run

if count > MAX_NO_PROGRESS:
    allow("plan-continue: %d continuations with no movement past %s — letting the turn "
          "end so you can look. Raise PLAN_CONTINUE_MAX or unset PLAN_CONTINUE if this "
          "is wrong." % (count - 1, key))

# EVERY INTERPOLATED FIELD IS BOUNDED AND FLATTENED. A repo can commit
# .claude/plan-progress.json — the gitignore convention is advice, not enforcement
# — so a cloned repo's state file is user-owned and still hostile. Newlines let
# planted text escape the sentence it sits in; length turns a 100 KB field into a
# 100 KB prompt. Neither is answered by validating who wrote the file.
MAX_FIELD = 200


def clean(value, default=""):
    text = str(value if value is not None else default)
    text = " ".join(text.split())
    if len(text) > MAX_FIELD:
        text = text[:MAX_FIELD] + "...(truncated)"
    return text


where = "phase %s, stage %s, task %s" % (clean(phase, "?"), clean(state.get("stage"), "?"),
                                         clean(state.get("task"), "?"))
desc = clean(state.get("task_desc"))
if desc:
    where += " (%s)" % desc

reason = (
    "You ended that turn on an announcement or a question while plan execution is "
    "still in flight: %s — %s.\n\n"
    "executing-plans § Run to completion: stage boundaries are checkpoints, not "
    "approval gates, and the tool call opening announced work goes in the SAME turn "
    "as the sentence announcing it. Start the announced work now — do not re-plan, "
    "do not re-verify finished work, and do not summarise what you have done.\n\n"
    "If you genuinely need to stop, do it the two documented ways rather than by "
    "trailing off: write an `ACTION NEEDED:` block naming the decision that blocks "
    "the next stage, or write phase:\"blocked\" to .claude/plan-progress.json when a "
    "documented Stop condition has fired. Waiting on a dispatched agent is not a "
    "stop — say what you are waiting on and this hook will let the turn end."
) % (clean(state.get("plan"), "the plan"), where)

json.dump({"decision": "block", "reason": reason}, sys.stdout)
sys.exit(0)
PY

# The invariant this file claims is "every exit is 0", and it must be the script's
# own rather than borrowed from the host's fail-open treatment of odd exit codes:
# python3 absent from PATH (127), an OOM kill, or a bad env override would otherwise
# leak that code to a host that may one day read it as fail-closed.
exit 0
