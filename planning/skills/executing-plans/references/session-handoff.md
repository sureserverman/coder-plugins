# Session handoff — a measured stop, never an eyeball call

The executor decides when a plan continues in a fresh session, and it decides by
measurement. Before this rule, every mid-plan stop in five audited executions was the user's
call on context (*"context is pretty full…"*, *"581k out of 1m…"*), and the executor proposed
a handoff zero times. The trunk used to advise a reset on large plans with nothing to
measure against, so the reset was never taken on purpose. Every executing-plans file that
mentions a fresh session cites this one, `session-handoff.md`, as the rule that decides it.

## The measurement

`../scripts/context-usage.py` reads this session's transcript
(`~/.claude/projects/<cwd-slug>/<session>.jsonl`) and reports the exact context in use — the
last main-thread turn's `input + cache_read + cache_creation` tokens, not a guess — against
the model's window, plus the context each `Stage N green` commit in this session cost:

```
python3 <planning>/skills/executing-plans/scripts/context-usage.py \
  --plan <plan path> --next-stage <N+1> [--sub-plan-boundary]
```

**The window.** `--window N` wins. Next comes the live window: on Claude Code 2.1.288+ the
planning mod has `.claude/plan-context.json` written beside the state file at the end of each
main-loop turn, and just before a main-loop Bash call that runs this script, while the
pinned plan is in `preflight`, `task` or `gate` and not stale
(`../../../hooks/mod/context.ts`, through `context-usage.py --write-sidecar`, which never
follows a link the repo planted). Gitignore it with the state file.
The script uses it only when its `session_id` equals `CLAUDE_CODE_SESSION_ID`, its `window`
is a positive integer, and its `updated` is under 15 minutes old. Below the state root the
read refuses links and non-regular files. The `reason:` then says `window from live session`. Otherwise the model
table decides as before, and an unlisted model is `unknown`. The sidecar supplies only the
window: the tokens still come from the transcript, and § The five stop rules are the
script's alone (DEC-026, DEC-027). The band's `context NN%` on the pinned row is a display of the
same engine figure, never a verdict.

**When.** Once per stage gate and once per sub-plan gate (DEC-017 positions), **after** the
gate commit, **in a separate Bash call**. The turn that is running is not in the transcript
until its tool returns, so a `context-usage.py` chained onto the `Stage N green` commit does
not see that commit and reports the previous stage's cost. At a master plan's sub-plan
close-out, add `--sub-plan-boundary`.

**What it reads for per-stage cost.** A stage boundary is the turn whose Bash call runs a
real `git commit` whose *subject* is `Stage N green`. A compaction (`isCompactSummary` row)
resets the baseline, so no cost spans one. `last_stage_cost` is the most recent stage's cost.

## The five stop rules

Evaluated in this order; the script names the rule that fired and its numbers in `reason:`.

1. **Owner request** (`rule requested`): handoff when the owner's rollover request through
   remote-agents names this session. `context-usage.py` reads it at the gate, through
   `handoff-envelope.py`'s reader, and its `reason:` is `rule requested: owner asked for a
   rollover`. It wins over the first-stage exception and over an `unknown` measurement, but
   it is still evaluated only at a gate: a request that arrives mid-stage waits for the
   stage's gate commit.
2. **Sub-plan boundary** (master plans, `--sub-plan-boundary`): handoff, unless the context is
   under 25% of the window. A sub-plan boundary is the natural reset point; below 25% the fresh
   session buys too little to be worth the resume.
3. **Context**: handoff when `now > 50` percent of the window, or when now plus
   `last_stage_cost` would pass 50%. Exactly 50% continues. **The first stage of a session
   always runs** — with no `Stage N green` commit in this session there is no cost history,
   and the verdict is `continue` whatever the percentage.
4. **Dead weight**: handoff when the next stage's `Scope:` / `Test:` paths are `disjoint`
   from every stage finished in this session **and** the context is above 25%. Nothing the
   session holds helps the next stage, so it pays for context it does not use. A stage with
   no `Scope:` field makes `disjoint` `unknown`, and `unknown` is never a stop.
5. **Dated external wait**: a gate check that cannot run before a named future date (a
   release, a store review, a device delivery) is written `- [~]` with the date, and the run
   hands off naming it. This rule's `reason:` is the dated check, quoted; paste the
   `context-usage.py` line beside it.

**Post-compaction re-grounding — not a stop.** When the session has compacted (the script's
`compactions` count rose), re-read the plan's `Status:` flips and handoff notes before the
next tool call. A compaction summary is not a source for task state.

## The bounds

Stated with the rules, not after them: DEC-014 binds every dispatch rule to state its bound
in the same breath, because a rule without one was over-corrected into its inverse. A stop
rule has the same failure shape, so the same discipline applies here.

- **`unknown` never stops.** A missing transcript, an unlisted model, a stage without
  `Scope:` — the script says `unknown`, the gate report says so, and execution continues.
  The one exception is the owner's request (rule 1): a missing measurement does not cancel it.
- **No rule applies before a gate.** A handoff happens at a stage or sub-plan gate, after its
  commit — never mid-stage and never mid-task.
- **A stop without the script's `reason:` line is not a legal stop.** "Context feels large"
  is the eyeball call this rule replaces. The Stop hook (`plan-continue-hook.md`) nudges
  through a `RESUME HERE` block that lacks a `reason:` line.

## On `continue`

Paste the verdict line verbatim into the handoff note as its `context:` line, and issue the
next stage's first tool call in the same turn (`stage-gate.md` § If the gate passes). The
gate report is already committed by then — the script runs after that commit — so the line
goes in the plan, not the report, and rides the next commit that carries the plan (a
vault-resident plan rides none).

## On `handoff`

0. Mint the handoff id once, before the handoff commit, and keep it for steps 1, 3 and 4:

   ```
   python3 <planning>/skills/executing-plans/scripts/handoff-envelope.py new-id --root <repo root>
   ```

   (`../scripts/handoff-envelope.py`; it prints `h-` and 20 hex characters.)
1. Append a `RESUME HERE` block under the stage's handoff note. Write its heading in column
   0: a successor's `handoff-envelope.py verify` reads the plan's last such block and checks
   its `handoff_id:`, `cwd:` and `branch:` against the handoff.

   ```
   **RESUME HERE (<YYYY-MM-DD>):**
   handoff_id: <id>
   reason: <the script's reason: line, verbatim>
   plan: <absolute plan path>   cwd: <repo root>   branch: <branch>
   next: Task <N.M> — <title>
   `dispatch: …`  `review: …`  `residuals: …`   (the gate report's lines, verbatim)
   **Decisions in force:** <IDs>
   ```

2. Commit it as its own `"Stage N handoff"` commit, whose body carries the same `reason:`
   line — the gate commit is already made, since the script runs after it. When the plan
   lives outside the repo, write the block at the plan's absolute path and make the same
   commit empty (`--allow-empty`), so the repo records why the run stopped.
3. Write the progress state file with `phase: "handoff"`, `reason` set to the script's
   reason, and `handoff_id` set to the id from step 0 (`progress-state-file.md`).
4. Tell a supervisor the handoff is ready:

   ```
   python3 <planning>/skills/executing-plans/scripts/handoff-envelope.py ready \
     --root <repo root> --handoff-id <id> --plan <absolute plan path>
   ```

   With no supervisor present (`REMOTE_AGENTS_SESSION_ID` unset) it writes nothing, prints
   `unsupervised` and exits 0, so the manual path is unchanged.
5. End the turn with the reason and one line telling the user to resume in a fresh session
   pointed at the plan path. That line is not an `ACTION NEEDED:` block — nothing is being
   decided.

**From step 3 on, the session owns nothing.** It starts no task or gate, flips no `Status:`,
edits no decision, and does nothing past step 4's envelope but end its turn (step 5). The
plan now belongs to whoever resumes it; a supervisor may start that session as soon as the
`ready` envelope lands, and two sessions writing one plan would race.

**Resuming.** The new session reads the plan in full, finds the last `RESUME HERE` block, and
starts at the task it names; the Research Summary, `Status:` flips and handoff notes carry
everything else. A block too thin to resume from is the bug to fix. Close-out writes no
`RESUME HERE` — there is no next task.
