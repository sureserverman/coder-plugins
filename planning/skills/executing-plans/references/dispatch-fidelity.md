# Dispatch fidelity — why the roster, the probe and the executor trailer exist

An inlined task and a dispatched one produce byte-identical artifacts: the same diff, the
same `Status: [x]`, the same commit subject. So a run that ignores its `Parallel: YES`
directives leaves nothing for a later reader to notice. Everything in this file exists to
make that specific omission visible. `executing-plans` keeps the mechanics — the roster
format, the probe, the snapshot, the trailer shapes; this is the reasoning behind them.

### Dispatch roster and capability probe

A `Parallel: YES` task is a directive to dispatch, not a note about concurrency
(`../planning-projects/SKILL.md` § Stage structure) — and an inlined task and a
dispatched one produce byte-identical artifacts. So a run that ignores the field leaves
no trace in the diff, the commits, or the gate: there is nothing for a later reader to
notice. The omission becomes visible only if the run wrote down what it was going to do
*before* it did anything. Preflight is where that happens, and Preflight is already a
hard stop.

1. **Enumerate the roster.** Sweep **every task in the plan**, across all stages, and
   list in the Preflight report each task whose `Parallel:` field reads `YES`, with the
   `subagent_type` it routes to per
   `../dispatching-parallel-agents/references/stack-routing.md`:

   ```
   Dispatch roster (Parallel: YES) — <n> of <total> tasks
     Task <N.M> → <subagent_type>
     Task <N.M> → <subagent_type>
     …
   ```

   The roster is a **sweep over the task set**, never one worked example: a report
   naming a single task cannot fail on its siblings — the same instance-vs-class gap the
   gate rules above close, arriving one phase earlier. A roster covering only the first
   stage is not a roster. An empty roster is a legitimate result — write `0 tasks`, so
   the absence is on the record as observed rather than as never examined. What the
   roster buys is contradiction: a run whose Preflight declared five dispatches and whose
   execution shows none now disagrees with a written list instead of disappearing.

2. **Probe the capability — only if the roster is non-empty.** Dispatch one throwaway
   subagent — `general-purpose`, whose entire task is to reply with a fixed string
   (`DISPATCH-OK`) — and confirm the string came back. One trivial dispatch proves the
   mechanism works in *this* session, while the finding can still change what happens
   next. Learning at Stage 3 that dispatch is unavailable is the same fact arriving after
   every decision it should have informed.

   **Roster first, probe second**, because the roster decides whether the probe is worth
   running: a plan with `0 tasks` on its roster will never dispatch, so a throwaway
   dispatch there proves a capability nothing in the run will use. Record `probe: skipped
   — empty roster` and move on. This is also why the failure rule below is conditioned on
   a non-empty roster; ordering the steps the other way made that condition read as an
   afterthought.

3. **Snapshot the `Review: skip` annotations.** In the same sweep, list every task
   already carrying `Review: skip`, and record it in the Preflight report against the
   commit the run starts from:

   ```
   Review: skip annotations at <base-sha> — <n> task(s): <Task N.M>, …
   ```

   This is what makes the annotation usable as evidence later. `Review: skip` says *the
   user chose not to review this task* — but the executor writes to the plan file on
   every task (Status flips, review notes), so an annotation read at skip time cannot
   distinguish one the user authored from one the executor added ten minutes earlier.
   The snapshot fixes the reference point: an annotation in this list was there before
   the run touched anything, and one that is not **is not evidence of a user opt-out**,
   whatever it says. Cite the snapshot when you skip, not the task line.

   Same shape as the decisions re-check above, and for the same reason: an artifact the
   run can modify is not evidence about the run unless you pin it first. Write `0 tasks`
   when there are none — an empty list observed beats an absent one.

**A failed probe is a Preflight failure.** When dispatch is unavailable or disallowed in
this session and the roster lists at least one task, Preflight fails and you stop — the
user decides whether to enable it, re-plan those tasks as `Parallel: NO`, or accept
inline execution knowingly. Substituting inline execution on your own authority is not a
resolution; it takes a decision that belongs to the user and makes it silently, which is
the exact failure this check exists to surface.

**If Preflight fails, stop.** Report which check failed and how it failed. Do not proceed to Stage 1. A broken baseline makes every downstream Red-Green loop noise.
