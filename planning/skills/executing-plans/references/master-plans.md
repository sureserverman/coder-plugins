# Master plans

How `executing-plans` runs a `*-master-plan.md`. Format: `../../planning-projects/references/master-plan-format.md`.

A master plan links 2–7 **sub-plans** — each a standard planning-projects plan in the
same directory — through a `## Sub-plans` register carrying per-entry `Status`, `Plan`
link, `Goal`, `Depends on` / `Blocks`, `Parallel`, and a `**Gate:**` block of cross-plan
integration checks.

**Critique (master-level Phase 1).** Before executing anything: every register `Plan:`
link resolves to an existing file; register `Depends on` / `Blocks` fields are symmetric
and acyclic; every entry ends with a `**Gate:**` block; every sub-plan carries the
`Master:` backlink and is itself a valid planning-projects plan (critique each one on
load, as usual). Surface concerns before starting.

**Step 4a applies here too** — run `validate-gate-checks.py` on the master itself, not only
on each sub-plan as it loads. A master's cross-plan checks live under `**Gate:**` markers
rather than `### Stage N Gate` headings, and those are precisely the checks that prove
integration *between* sub-plans, so an instance-shaped one there survives every sub-plan
gate and surfaces only at the master close-out — the most expensive place to find it.

**Execution model:**

1. **Order by the register graph.** A sub-plan is dispatchable when every entry in its
   `Depends on` is `[x]`. Execute it via the normal single-plan flow — its own
   Preflight, stages, Red-Green loops, gates, and close-out. `Parallel: YES` sub-plans
   with no repo/file overlap may run concurrently (separate sessions or worktrees), but
   the file-conflict rule applies at this level too: overlapping sub-plans run
   sequentially regardless of the graph.
2. **One sub-plan per session, ideally.** Each sub-plan is a natural context-reset
   boundary (the trunk's Context resets at stage boundaries, scaled up): finish a sub-plan, then recommend the
   user start the next one in a fresh session pointed at the master path. The master
   file — register `Status` flips plus its handoff notes — is the cross-session handoff
   artifact; a fresh session needs the master, the next sub-plan, and nothing else.
3. **On a sub-plan's close-out** (its `**Completed:**` line just landed): flip the
   master register entry's `- **Status:** [ ]` to `[x]`, run that entry's `**Gate:**`
   checks (they prove integration with previously completed sub-plans — a failure here
   is handled like any stage-gate failure — same severity classification, remediation
   budget, and the same **exit criterion** — findings are not the only way a gate fails; of
   the findings, no Critical remains and each Important leaves the
   gate **fixed**, traced to the responsible sub-plan/task or to the defect class it belongs
   to; a defect this session cannot fix escalates with its blocker named rather than being
   filed, exactly as at a stage gate), append
   a short `**Sub-plan N handoff:**` note under the entry, and commit
   `"Sub-plan N green"`.

   **What flips the entry is a terminal marker in the sub-plan file, and the set has exactly
   two members:** `**Completed:**` alone, or `**Completed:**` **together with**
   `**Blocked-accepted:** <date> — <why>` when one of that sub-plan's gate checks is `[~]`.
   Both are written into the sub-plan **before** the entry flips. **An intention to close out
   later is not a member of that set.**

   **Why this needed saying.** With a blocked gate, three rules collide and cannot all hold:
   this step wants the sub-plan's `**Completed:**` line first; `close-out.md` § *Closing a plan
   whose gate could not be run* forbids a clean `**Completed:**` over a `[~]`; and a dependent
   sub-plan cannot start until this entry reads `[x]`. Something gives, and what gave in
   practice was the record — a register flipped to unblock the next sub-plan, a close-out never
   written, and a master that then declared the decomposition done without coming back. That is
   not hypothetical; it is `2026-08-13-backlog-closure-sub-04`'s own account of itself.
   `**Blocked-accepted:**` is what dissolves the collision, and this step predates it: the
   marker landed 2026-08-27, months after the rule above was written, so until now there was no
   legal way through and the executor had to break one of the three.
4. **Version bumps are deferred to the master close-out.** Sub-plan close-outs run all
   their usual steps (full suite, the evaluator **its own declared tier calls for**,
   backlog reconcile, workflow audit) EXCEPT step 4 (version bumps) — one feature landing
   across five sub-plans is one release event, not five. Note the deferral in each
   sub-plan's close-out.
5. **Master close-out.** When every register entry is `[x]` and every gate passed: run
   the deferred version bumps once across everything the sub-plans touched (all mirrors),
   run the full suite, run the independent evaluator pass **that the master's tier calls
   for** (below), then append to the master:
   `**Completed:** YYYY-MM-DD — sub-plans: <list>`.

   **Which tier the master close-out runs at.** Tiers are declared *per sub-plan*
   (`../references/review-scope.md`), so none of them governs the master itself. The master takes the
   **highest tier any sub-plan declared** — its close-out is the only pass that sees the
   integrated result, and a `high` sub-plan's risk does not stop being the master's
   because a cheap sibling landed after it. Declare that tier in the master close-out
   report the same way a stage gate restates its own.

**Stop conditions are unchanged** and apply inside whichever sub-plan is executing; a
stopped sub-plan blocks its register dependents exactly as a failed task blocks its
`Blocks` list.
