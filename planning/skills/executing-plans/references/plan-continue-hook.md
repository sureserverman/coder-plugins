# `plan-continue` — the optional Stop-hook backstop

**Off by default. It is enabled by one environment variable and does nothing without it.**

`../../../hooks/plan-continue.sh` runs on Claude Code's `Stop` event and refuses a turn that
ends on a promise or an approval question while a plan is in flight, returning
`{"decision":"block","reason":…}` so the run continues instead of waiting for the user.

## Why a hook, when the rule is already written

`../SKILL.md` § Run to completion says it plainly — *"stage boundaries are checkpoints, not
approval gates"*, *"never end a turn on an announcement"* — and `stage-gate.md` § If the gate
passes and `task-execution.md` now restate it at both boundaries where it applies. That is
the fix. This hook is the net under it, for the case those three restatements do not cover:
the rule is read once at session start and the failure happens hundreds of thousands of
tokens later, in a session with no compaction and no error to notice.

Measured across two sessions executing one master plan (2026-08-29/30), 39 turn ends:

| Shape | Count | What it cost |
|---|---|---|
| Ended waiting on a dispatched agent or background suite | 30 | Nothing — the host re-invoked within 0.5–51 min |
| Ended on a promise or an approval question, nothing pending | 7 | 8.1 min, 16.6 min, and one overnight stop of **8 h 11 min** |

The executor knew the rule in every case, and quoted it back when asked.

## Why it is not the port used on Codex and Cursor

The Codex and Cursor ports of this hook, which live in the engineering-skills repo, block
**every** turn end while a plan runs, because on those hosts an assistant message *is* the turn boundary. That policy
would be actively harmful here: 30 of the 39 measured turn ends were correct, and forcing a
continuation through each would spin against agents that had not reported. This port keeps
the in-flight signal and every one of the ports' hardening decisions, and replaces the policy
with a classifier over the last assistant message.

## When it blocks

All four must hold:

1. `PLAN_CONTINUE=1` in the environment.
2. `<repo-root>/.claude/plan-progress.json` exists, is owned by you, and its `phase` is
   `preflight`, `task` or `gate` — an allow-list, so a phase added to the contract later
   fails open. `closeout` and `blocked` are excluded, and close-out deletes the file.
3. `updated` is parseable, not in the future, and under 12 h old.
4. The last main-thread assistant message matches a **promise** (*"Next: Task 2.4"*,
   *"starting now with Task 2.1"*, *"I'll start…"*) or an **approval question** (*"say the
   word"*, *"ready to start Stage 2"*, *"want me to carry on"*), and matches **neither** a
   wait marker (*"waiting on"*, *"once it reports"*, *"still running"*, *"blocked on"*) nor
   an `ACTION NEEDED` block.

Against the 39 measured turn ends: 7/7 bad stops caught, 0 of the 30 legitimate waits
blocked. One further turn is blocked that the host happened to rescue four minutes later
(*"Re-running the gate next, then Stage 3."*) — an announcement ending that got lucky, and
blocking it is the intended reading rather than a miss.

## Two ways to stop on purpose

Both already exist in this skill's contract; the hook reads them rather than inventing a
third:

- Write an **`ACTION NEEDED:`** block naming the decision that blocks the next stage
  (`stage-gate.md` § ACTION NEEDED — the one place a report asks the user for something).
- Write **`phase: "blocked"`** to the progress state file when a documented Stop condition
  fires (`progress-state-file.md`).

Saying what you are waiting on also ends the turn cleanly — that is what the wait marker is.

## Enabling it

The hook ships with the plugin and is wired to `Stop` by `../../../hooks/hooks.json`, so
there is nothing to install; it exits immediately unless opted in. Enable it per project in
`.claude/settings.json`:

```json
{ "env": { "PLAN_CONTINUE": "1" } }
```

`PLAN_CONTINUE_MAX` (default 3) bounds how many times it may force a continuation while
`phase|stage|task` does not move; past that it lets the turn end so you can look. Unset
`PLAN_CONTINUE` or set it to `0` to switch it off.

## It fails open, always

No state file, unreadable or unparseable transcript, garbage timestamp, stale state, a
symlinked or FIFO state file, a world-writable repo root, no progress — every one of these
allows the stop. A Stop hook that fails closed traps a session in a loop the user cannot
exit, which is strictly worse than the problem it solves. Every exit is 0, enforced by the
script rather than borrowed from the host's treatment of odd exit codes.

The reason text is built only from clamped state-file fields (newlines flattened, 200 chars
each). Transcript text is read to make a yes/no decision and never quoted back — a repo can
commit `.claude/plan-progress.json`, so a cloned repo's state file is user-owned and still
untrusted.

Tests: `../tests/test-plan-continue.sh` (30 cases, decision-asserting).
