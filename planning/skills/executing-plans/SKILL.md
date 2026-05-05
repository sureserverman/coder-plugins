---
name: executing-plans
description: Use when you have a plan file produced by the planning-projects skill (format with Stages, Tasks, Depends on / Blocks / Parallel fields, Red-Green max cycles, and Stage gates) and need to execute it. Drives Red-Green loops, respects the stage-gate model, and dispatches independent tasks through the dispatching-parallel-agents skill. Triggers on "execute this plan", "run the plan", "implement docs/plans/...", "pick up this plan".
---

# Executing Plans

Execute a plan produced by `planning-projects`. Honor the stage-gate model: tasks run through Red-Green loops, a stage's gate must pass before the next stage starts, and independent tasks are dispatched in parallel when the plan's dependency graph allows it.

**Announce at start:** "Using the executing-plans skill to implement `<plan-path>`."

## What this skill expects

The plan file was produced by `planning-projects`. It contains:

- A **Research Summary** (background, not executed)
- A **Preflight** checklist (verified before Stage 1)
- One or more **Stages**, each with:
  - Goal, Depends on, Blocks, Risk, Rollback
  - Ordered **Tasks**, each with `Depends on`, `Blocks`, `Parallel: YES|NO`, `Test:` (a concrete runnable check), `Red-Green max cycles: N`
  - A **Stage gate** checklist

If the plan doesn't have these fields, stop — it wasn't produced by `planning-projects` and must be either rewritten through that skill or executed manually.

---

## Checklist

Create a task for each, work them in order:

1. **Load and critique the plan** — raise concerns before starting
2. **Run Preflight** — verify every check; stop on failure
3. **For each stage, in order:**
   a. Dispatch `Parallel: YES` tasks via `dispatching-parallel-agents`; work `Parallel: NO` tasks in the main session
   b. Drive each task through its Red-Green loop
   c. Run the stage gate; stop if it fails
4. **After all stages green:** hand off for review and merge (see Phase Close-out)

---

## Phase 1 — Load and critique

1. Read the plan file in full
2. Verify the structure: Research Summary, Preflight, Stages with the expected fields
3. Critique: is any task's test vague ("should work")? Is any stage oversized (>7 tasks)? Is any dependency cycle present? Does any task modify a file that a parallel sibling also modifies?
4. **If concerns exist, surface them to the user before starting.** A plan with an unrunnable test or a dependency cycle will waste an entire Red-Green budget before the problem is found

Create a TodoWrite list mirroring the plan: one task per stage, sub-items per task. Mark the current stage as `in_progress` only when Preflight passes.

## Phase 2 — Preflight

Run every check in the Preflight section and report pass/fail:

- Tools installed and at compatible versions
- Dependencies resolvable
- APIs reachable, keys valid
- Access / permissions verified
- Baseline test suite passes

**If Preflight fails, stop.** Report which check failed and how it failed. Do not proceed to Stage 1. A broken baseline makes every downstream Red-Green loop noise.

## Phase 3 — Stage execution

For each stage in order:

### Step 3.1 — Identify what can run now

Scan the stage's tasks. A task is **dispatchable** when every task in its `Depends on` list is green. At stage start, this is every task whose `Depends on` is either empty or lists only tasks from already-green prior stages.

### Step 3.2 — Split by parallelism

- Tasks with `Parallel: YES` and no file conflicts with another ready task → hand to `dispatching-parallel-agents`
- Tasks with `Parallel: NO` or that modify files another parallel task modifies → work sequentially in the main session

**File-conflict check:** before dispatching, verify no two parallel tasks edit the same file. If they do, force one of them sequential even if the graph says independent.

### Step 3.3 — Red-Green loop (per task)

Every task follows this loop. No task is "done" until its test is green.

```
 Attempt → Test → Pass? ──yes──► Next task
            │
            no
            ↓
         Diagnose → Fix → Retest
            (max `Red-Green max cycles` per task)
```

**Loop rules:**

1. **One fix per cycle.** Don't shotgun. Isolate, fix that one thing, retest.
2. **Diagnose before fixing.** Read the actual error. Form a hypothesis. Confirm against the code. Then write the fix.
3. **Respect the cycle budget.** The plan sets a max (default 3). When exceeded, stop and escalate — don't keep looping. Three failed targeted fixes means the approach is wrong, not just the implementation.
4. **Never skip the test.** The task's Test field is the gate. "It looks right" is not green.
5. **Commit after each green task** with a message referencing the stage and task (`"Stage 2 Task 2.3: parse config entries"`).

### Step 3.4 — Propagate unblock

When a task finishes green, scan its `Blocks` field. For each blocked task, check whether ALL of its `Depends on` items are now green. If yes, it becomes dispatchable — return to Step 3.1.

### Step 3.5 — Stage gate

When every task in the stage is green, run the stage gate:

- Each gate check has a specific pass criterion (a command output, a test result, a manual verification)
- Run them in order; stop at the first failure
- Run the full existing test suite as part of the gate (regressions check)

**If the gate fails:**

1. Identify which task interaction caused it (gate failures are usually integration problems, not single-task problems)
2. Add a new test covering that interaction to the relevant task
3. Run that task through its Red-Green loop again
4. Re-run the gate

**If the gate passes:** mark the stage complete, commit with `"Stage N green"`, and start Step 3.1 for the next stage.

---

## Stop conditions

Stop immediately and escalate to the user when:

- Preflight fails
- A task exhausts its Red-Green cycle budget
- A stage gate fails and re-running the culprit task doesn't fix it after one additional cycle
- The plan contains an instruction you don't understand
- A test cannot be run (missing fixture, unreachable service, unclear invocation)
- Verifying the test requires modifying shared infrastructure (production DB, live service) — see Safety rails below

**Never guess through a stop condition.** Ask.

## When to revisit earlier steps

Return to Phase 1 (critique) when:

- The user updates the plan after feedback — treat the new version as a fresh plan and re-critique
- A stage gate failure reveals a fundamental gap in the plan (e.g., missing task, wrong dependency) — stop execution, return to `planning-projects` to revise

## Phase Close-out — After the last stage

When every stage is green:

1. Run the **full** test suite one more time from a clean state (don't trust the per-stage runs)
2. Run any integration / e2e tests the plan flagged
3. Update the plan document with a closing note: "Completed YYYY-MM-DD. Commits: <list>."
4. Report to the user with:
   - Stages completed
   - Total commits
   - Plan location for future reference
   - Any deferred items the user explicitly deprioritized during execution
5. Offer merge / finalize options (worktree cleanup, PR creation, branch merge). Do not merge without explicit confirmation.

---

## Safety rails

- **Never start on `main` / `master` without explicit user consent.** Use a feature branch or worktree.
- **Destructive commands** (schema migrations, data deletes, force pushes, production deploys) — confirm before running, even if the plan says to.
- **Secrets** — if a task would read or write credentials, stop and confirm the mechanism (env var, secrets manager) with the user before proceeding.
- **Shared infrastructure** — staging/prod-adjacent changes get confirmation per stage, not per plan.

## Remember

- Critique the plan before starting
- Preflight is a hard gate
- Follow the plan's exact tests, exact commands
- Respect the cycle budget — three targeted fixes, then stop
- Stage gates check integration, not just aggregate task success
- Never silently skip a Red-Green cycle — report and move on is fine; skip is not
- Commit each green task; never squash silently during execution

---

## Sources and rationale

- **Red-Green loop** — Kent Beck, *Test-Driven Development: By Example* (2002); the "test first, then make it pass" cycle adapted for task-level discipline
- **Stage gates** — Robert Cooper, *Winning at New Products* (1986); phase gates with specific pass/fail criteria
- **Max 3 failure cycles** — heuristic from debugging literature; after three targeted fixes without resolution, the hypothesis (not the implementation) is wrong. See Feynman on "the first principle is that you must not fool yourself"
- **Preflight as hard gate** — aviation checklist tradition; Atul Gawande, *The Checklist Manifesto* (2009)
- **Commit per green task** — frequent, small commits; *The Pragmatic Programmer* Ch. 7; Linus Torvalds on "each commit should be a single logical change"
- **Never skip the test** — Beck (TDD), Fowler ("Continuous Integration"); the test is the only signal that says "done"

## Integration

- **planning-projects** — produces the plan this skill consumes
- **dispatching-parallel-agents** — invoked for `Parallel: YES` tasks with no file conflicts
- **code-reviewer agent** — optional; invoke between stages for an independent review of stage changes before the gate
- **testing-expert agent** — invoke when a task's test is ambiguous, flaky, or the plan's coverage is thin
