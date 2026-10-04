#!/usr/bin/env bash
# proof-guard.sh — Claude Code PreToolUse hook (matcher Bash): the commit gate stays on.
#
# INERT UNLESS OPTED IN. A plugin's hooks.json hook runs for every user who enables
# the plugin; there is no per-hook opt-in, so this hook decides for itself to do
# nothing. It acts only in a repo whose git `reference-transaction` hook is the
# shim proof-hooks-install.py writes (the project opted in) AND which has a plan
# in flight (.claude/plan-progress.json, read with plan-continue.sh's hardening).
# Everywhere else it prints nothing and exits 0 — no decision at all.
#
# WHAT IT DENIES. The git ref hook (hooks/git-ref-gate.sh) refuses an unproven
# task commit by every route git has; the one way around it is to stop git running
# it. So, in a gated repo the command can reach (the payload's cwd, each `cd <dir>`,
# each `git -C <dir>`), it denies a command whose text:
#   - mentions `hooksPath`, any case — the key must be spelled out to be set;
#   - names the hook file (`reference-transaction`) or the `.git/hooks` directory;
#   - runs proof-hooks-install.py --remove — the user removes the gate, with `!`,
#     which no hook sees.
# It parses no commands beyond those text rules: the Cursor port's parsers each
# had a hole (a quoted `;`), and the ref hook does not need this guard to read a
# commit. It is a rail against an agent switching the gate off, not a sandbox.
#
# IT FAILS OPEN on its own errors: a payload it cannot read, a git it cannot run.
set -uo pipefail
PAYLOAD="$(cat)"
# Every deny rule needs one of these strings in the command; without one, no
# Python starts — this runs on every Bash call of every user.
printf '%s' "$PAYLOAD" | grep -qiE 'hookspath|reference-transaction|\.git/hooks|proof-hooks-install' \
    || exit 0
PROOF_GUARD_PAYLOAD="$PAYLOAD" python3 - <<'PY' || exit 0
import json, os, re, stat, subprocess, sys
from pathlib import Path

MARK = "planning commit gate"  # in the shim proof-hooks-install.py writes
HOOK_NAME = "reference-transaction"


def none(note=None):
    if note:
        sys.stderr.write(f"proof-guard: {note}\n")
    sys.exit(0)


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny",
        "permissionDecisionReason": reason}}))
    sys.exit(0)


try:
    payload = json.loads(os.environ.get("PROOF_GUARD_PAYLOAD") or "")
except Exception:
    none("payload is not JSON")
if not isinstance(payload, dict):
    none()
ti = payload.get("tool_input")
command = ti.get("command") if isinstance(ti, dict) else None
if not isinstance(command, str):
    none()


def git(d, *a):
    return subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True,
                          timeout=10)


# ---- every repo the command can reach (over-inclusive on purpose: a deny here
# is a reason handed to the model, never a trapped session)
cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else None
starts = [m.strip("\"'") for m in re.findall(r"\bgit\s+-C\s+(\"[^\"]+\"|'[^']+'|\S+)", command)]
starts += [m.strip("\"'") for m in re.findall(r"\bcd\s+(\"[^\"]+\"|'[^']+'|[^\s;&|)]+)", command)]
starts += [cwd] if cwd else []
repos = []
for s in starts:
    p = Path(os.path.expanduser(s))
    if not p.is_absolute() and cwd:
        p = Path(cwd) / p
    try:
        top = git(p, "rev-parse", "--show-toplevel")
    except Exception:
        continue
    r = Path(top.stdout.strip()) if top.returncode == 0 else None
    if r and r not in repos:
        repos.append(r)


def opted_in(repo):
    """Our shim is the repo's reference-transaction hook (the marker is enough:
    an altered shim is still a repo that opted in)."""
    try:
        hooks = git(repo, "rev-parse", "--git-path", "hooks").stdout.strip()
        hook = (Path(hooks) if os.path.isabs(hooks) else repo / hooks) / HOOK_NAME
        with open(hook, errors="replace") as fh:
            return MARK in fh.read(4096)
    except Exception:
        return False


def in_flight(repo):
    """True when a plan is in flight (same hardening as plan-continue.sh's read_state)."""
    try:
        fd = os.open(repo / ".claude" / "plan-progress.json",
                     os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        return False
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_size > 256 * 1024:
            return False
        with os.fdopen(fd, "r", errors="replace") as fh:
            fd = None
            state = json.load(fh)
    except Exception:
        return False
    finally:
        if fd is not None:
            os.close(fd)
    plan = state.get("plan") if isinstance(state, dict) else None
    return isinstance(plan, str) and bool(plan)


gated = [r for r in repos if opted_in(r) and in_flight(r)]
if not gated:
    none()
where = ", ".join(str(r) for r in gated)
inst = "proof-hooks-install.py"

if re.search(r"hookspath", command, re.I):
    deny(f"Denied: a plan is in flight in {where}, which opted into the proof-record commit "
         "gate, and this command mentions `hooksPath`. git must keep running the gate from the "
         "repo's own hooks directory; core.hooksPath is the one setting that would point it "
         "elsewhere. If the mention is only in a commit message or a document, reword it.")
if re.search(rf"{HOOK_NAME}|\.git/hooks", command):
    deny(f"Denied: a plan is in flight in {where}, and this command names the git "
         f"{HOOK_NAME} hook or the hooks directory — the proof-record commit gate. Prove the "
         "task with prove-claim.py instead; only the user switches the gate off.")
if inst in command and re.search(r"--remove\b", command):
    deny(f"Denied: a plan is in flight in {where}; removing the proof-record commit gate is "
         "the user's decision, not the agent's. Ask the user. They can remove it themselves "
         f"by typing `! python3 <planning>/skills/executing-plans/scripts/{inst} --remove "
         "--repo <repo>` in the prompt.")
none()
PY
exit 0
