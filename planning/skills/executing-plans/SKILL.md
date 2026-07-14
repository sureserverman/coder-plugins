---
name: executing-plans
description: Use when you have a plan file from planning-projects (Stages, Tasks, Depends on / Blocks / Parallel), or a master plan linking sub-plans, and need to execute it — driving Red-Green loops and stage gates. Triggers on "execute this plan", "run the plan", "execute the master plan".
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

**Exception — master plans.** A file whose name ends in `-master-plan.md` or whose first
heading is `# Master Plan:` is a **master plan** (format:
`../planning-projects/references/master-plan-format.md`). It deliberately has no
Preflight, Stages, or Tasks — do NOT reject it; execute it per the **Master plans**
section below.

---

## Master plans

A master plan links 2–7 **sub-plans** — each a standard planning-projects plan in the
same directory — through a `## Sub-plans` register carrying per-entry `Status`, `Plan`
link, `Goal`, `Depends on` / `Blocks`, `Parallel`, and a `**Gate:**` block of cross-plan
integration checks.

**Critique (master-level Phase 1).** Before executing anything: every register `Plan:`
link resolves to an existing file; register `Depends on` / `Blocks` fields are symmetric
and acyclic; every entry ends with a `**Gate:**` block; every sub-plan carries the
`Master:` backlink and is itself a valid planning-projects plan (critique each one on
load, as usual). Surface concerns before starting.

**Execution model:**

1. **Order by the register graph.** A sub-plan is dispatchable when every entry in its
   `Depends on` is `[x]`. Execute it via the normal single-plan flow below — its own
   Preflight, stages, Red-Green loops, gates, and close-out. `Parallel: YES` sub-plans
   with no repo/file overlap may run concurrently (separate sessions or worktrees), but
   the file-conflict rule applies at this level too: overlapping sub-plans run
   sequentially regardless of the graph.
2. **One sub-plan per session, ideally.** Each sub-plan is a natural context-reset
   boundary (see Context resets below, scaled up): finish a sub-plan, then recommend the
   user start the next one in a fresh session pointed at the master path. The master
   file — register `Status` flips plus its handoff notes — is the cross-session handoff
   artifact; a fresh session needs the master, the next sub-plan, and nothing else.
3. **On a sub-plan's close-out** (its `**Completed:**` line just landed): flip the
   master register entry's `- **Status:** [ ]` to `[x]`, run that entry's `**Gate:**`
   checks (they prove integration with previously completed sub-plans — a failure here
   is handled like any stage-gate failure, traced to the culprit sub-plan/task), append
   a short `**Sub-plan N handoff:**` note under the entry, and commit
   `"Sub-plan N green"`.
4. **Version bumps are deferred to the master close-out.** Sub-plan close-outs run all
   their usual steps (full suite, evaluator, backlog reconcile, workflow audit) EXCEPT
   step 4 (version bumps) — one feature landing across five sub-plans is one release
   event, not five. Note the deferral in each sub-plan's close-out.
5. **Master close-out.** When every register entry is `[x]` and every gate passed: run
   the deferred version bumps once across everything the sub-plans touched (all mirrors),
   run the full suite and the independent evaluator pass against the *master's* overall
   goal, then append to the master:
   `**Completed:** YYYY-MM-DD — sub-plans: <list>`.

**Stop conditions are unchanged** and apply inside whichever sub-plan is executing; a
stopped sub-plan blocks its register dependents exactly as a failed task blocks its
`Blocks` list.

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

## Run to completion — don't stop until you have to

Once Preflight passes, **drive the plan straight through to close-out.** Stage
boundaries are checkpoints, not approval gates: when a stage gate passes,
commit it and start the next stage without pausing to ask "should I continue?"
The plan is the approval. Burning a turn to ask permission between green stages
is the failure mode this skill exists to prevent.

Keep going through:

- a task that goes green (→ next task / unblock)
- a stage gate that passes (→ next stage, immediately)
- a Red-Green cycle that fails but still has budget (→ diagnose and retry)
- a recoverable surprise you can resolve from the plan + evidence (→ resolve, note it, continue)

**Only the documented Stop conditions below halt execution** — they are real
blockers (exhausted cycle budget, failed gate that a re-run didn't fix, a
destructive/secret/shared-infra action needing consent, an instruction you
genuinely can't parse). Everything else is work to push through, not a reason to
hand back. When you do stop, it's because continuing would be guessing or unsafe
— say which, with evidence, and what you need to resume.

The context-reset guidance below is an efficiency tactic for very large plans,
**not** a license to stop early: prefer a fresh session over a *degraded* one,
but never over *finishing the work*.

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
- **Version control is live** — see below

### Git bootstrap (hard prerequisite for commit-per-task)

Every task commits its own work (Step 3.3 rule 6), so a working repo must exist
before Stage 1:

```
git rev-parse --is-inside-work-tree  →  is this a repo?
├── NO → `git init`, ensure a sane .gitignore, and make an initial commit of the
│        current tree ("chore: initial commit before plan execution") so the
│        first task has a parent. Then offer to create a GitHub remote
│        (`gh repo create <name> --private --source=. --remote=origin`) — create
│        it only on user confirmation; never push a repo public without consent.
│        Execution proceeds locally whether or not a remote is created.
└── YES ↓
On main / master?  → do NOT execute here. Create a feature branch (or worktree)
                     per the Safety rails before Stage 1.
Working tree dirty with unrelated changes? → surface them; don't sweep them into
                     the first task's commit.
```

A missing remote is **not** a stop condition — local commits are the unit of
record. Only an un-initializable repo (e.g. read-only filesystem) blocks here.

**If Preflight fails, stop.** Report which check failed and how it failed. Do not proceed to Stage 1. A broken baseline makes every downstream Red-Green loop noise.

## Phase 3 — Stage execution

For each stage in order:

### Step 3.1 — Identify what can run now

Scan the stage's tasks. A task is **dispatchable** when every task in its `Depends on` list is green. At stage start, this is every task whose `Depends on` is either empty or lists only tasks from already-green prior stages.

### Step 3.2 — Split by parallelism

- Tasks with `Parallel: YES` and no file conflicts with another ready task → hand to `dispatching-parallel-agents`
- Tasks with `Parallel: NO` or that modify files another parallel task modifies → work sequentially in the main session

**File-conflict check:** before dispatching, verify no two parallel tasks edit the same file. If they do, force one of them sequential even if the graph says independent.

**Delegate sequential tasks for context hygiene.** `Parallel: YES` tasks already go
to subagents. A `Parallel: NO` task still defaults to the main session — but when it
is **independent** (doesn't need the running session's context, and later steps won't
need its working trace), **output-heavy** (builds, broad greps, long test logs, large
reads the orchestrator would otherwise absorb), and **not latency-critical**, hand it
to a single stack-matched subagent instead of running it inline. This keeps the
orchestrator's window on plan state and gates rather than filling it with churn it will
never reference again. It is a context-hygiene move, **not** a token saving — the
subagent's intermediate tokens still burn. Keep a task inline when it is coupled to
accumulated session context, needs iterative back-and-forth, or is a quick targeted
edit. Pick the subagent type (and the stack skill it should load first) from the
routing table at `../dispatching-parallel-agents/references/stack-routing.md` — the
same table the dispatch path uses.

**If the matched capability's plugin isn't enabled**, don't silently fall through to
`general-purpose` with no domain knowledge — resolve it from disk per
`../dispatching-parallel-agents/references/stack-routing.md` § *Resolving a capability
whose plugin isn't enabled*: look the component up in `capability-index.json` (at the
marketplace root; paths resolve against the index file's own directory), then Read-and-follow
its SKILL.md or inject its agent body with the `model` pin. A component flagged
`requires_enablement` (hooks / MCP) can't be lazy-loaded — stop and ask the user to enable
that plugin. When the plugin **is** enabled, use the normal registered `subagent_type` /
skill invocation. (Outside plan execution, the `capability-router` skill wraps this same
lookup-and-resolve flow for ad-hoc needs.)

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
3. **Respect the cycle budget.** The plan sets a max (default 3). When exceeded, stop and escalate — don't keep looping. Three failed targeted fixes means the approach is wrong, not just the implementation. If the user chooses to skip rather than re-plan, defer the task to the `backlog` skill (`add`) before moving on; don't silently drop it.
4. **Never skip the test.** The task's Test field is the gate. "It looks right" is not green.
5. **Flip the task's Status to `[x]` the moment its test is green** — edit the plan's `- **Status:** [ ]` line for that task to `- **Status:** [x]`. This is the authoritative done-marker; downstream tools (e.g. `portfolio unify`) read it instead of guessing from gates or git. Do this in the same change as the work.
6. **Quick review gate (Tier 1).** Once the test is green and Status is flipped, but **before** the commit, run a per-task code review on the task's diff. Dispatch `git-github:code-reviewer` (read-only) as a **fresh dispatch that sees only the task diff** — never the executor self-reviewing — briefed with the task description and its `Test:` criterion. Handle the verdict by severity:
   - **Critical → blocking.** A Critical finding means the task is not actually done. Fix it inline (one fix per cycle, diagnose first — same discipline as the Red-Green loop), then **re-run the test and re-dispatch the review**. Critical-review cycles count against the *same* `Red-Green max cycles` budget as test failures; on exhaustion, escalate like any other budget exhaustion (Stop conditions). The executor applies the fix; the reviewer only ever reports.
   - **Important / Suggestion → advisory.** Do not act on them now. Append them to the plan file as a note under the task (`**Review notes (Task N.M):** …`) so the stage gate's deep review (Step 3.5) can triage the batch. They never block the task.
   - **Skip for trivial/non-code diffs.** Docs-only, config-only, pure version-bump, or comment-only diffs don't need Tier 1 — note the skip and proceed. Honor a `Review: skip` task annotation and the global opt-out (see References) the same way.

   This is a context-hygiene **and** quality move: the review burns its own tokens but keeps bad code from compounding across tasks. It does **not** pause to ask the user — it pauses only to fix autonomously within budget, preserving run-to-completion.
7. **Commit after each green task** with a message referencing the stage and task (`"Stage 2 Task 2.3: parse config entries"`). The commit includes the work, any Tier-1 fixes, and the flipped `Status: [x]`. This is non-negotiable and assumes the Preflight git bootstrap ran — the per-task commit is the unit of record and what makes a mid-plan stop recoverable. A passed stage gate then adds its own `"Stage N green"` commit (Step 3.5): you keep **both** granularities, the per-task commits *and* the per-stage marker — never collapse to only one.

### Step 3.4 — Propagate unblock

When a task finishes green, scan its `Blocks` field. For each blocked task, check whether ALL of its `Depends on` items are now green. If yes, it becomes dispatchable — return to Step 3.1.

### Step 3.5 — Stage gate

When every task in the stage is green, run the stage gate:

- Each gate check has a specific pass criterion (a command output, a test result, a manual verification)
- Run them in order; stop at the first failure
- Run the full existing test suite as part of the gate (regressions check)

**Platform stage-verify hook.** After the stage's own gate checks pass, if the
project's platform ships a stage-verify skill, invoke it as the final gate step
— it proves the stage on the real artifact, not just the test suite. A failure
there is a gate failure (handle it like any other below). Match by project type:

| Project type (detector) | Stage-verify skill |
|-------------------------|--------------------|
| Android — `settings.gradle{,.kts}` / `app/build.gradle{,.kts}` present | `android-stage-verify` (android-dev plugin) — builds the debug APK, and if an adb device is attached, installs + smoke-launches + runs instrumented tests |

If no matching skill is installed, note it and rely on the regular gate checks —
the absence of a platform verifier is not itself a gate failure.

**Design-fidelity verify hook (redesign stages).** A stage whose tasks reproduce a
Claude Design handoff pack (a *design-handoff* / *redesign* task — driven by the
`applying-design-handoff` skill) carries its own gate step: run that skill's
**fidelity verify loop** (capture → grade against its fidelity rubric with a separate
evaluator → iterate, max 3) as the final gate check, exactly as the platform
stage-verify hook proves a platform stage. A below-threshold verdict that doesn't
recover within the loop is a gate failure. This is the design analogue of the
stage-verify hook: a green build is not a reproduced design.

**Independent evaluator for non-command checks.** Command checks are
deterministic — run them yourself. But when a gate contains any check that
requires judgment ("manual verification", "reads coherently", "flow works
end-to-end"), dispatch a fresh evaluator agent for those checks, briefed ONLY
with the stage goal and the gate's pass criteria — never the implementation
transcript or your own summary of the work. The session that wrote the code
grades its own work too generously; external judgment catches what
self-assessment misses. Skip the evaluator only if the user opts out or every
check in the gate is a command.

**Deep code review (Tier 2).** The evaluator above verifies *goals* (black-box,
briefed only on criteria). Add a complementary *white-box* pass: dispatch
`git-github:code-reviewer` (read-only) over the **full stage diff** (`git diff`
across the stage's commits) **plus the collected Tier-1 advisory notes**
(`**Review notes (Task N.M):**` lines accumulated during the stage). This is a
gate criterion, not advisory — a **Critical** finding here is a **gate failure**
(handle it via the "If the gate fails" steps below). Important/Suggestion findings
are surfaced for the user's triage at the gate, not auto-fixed. This is the only
point where findings are reviewed against the *coherent stage*, so cross-task
issues the per-task Tier-1 pass couldn't see (duplication across tasks, an
abstraction that should have been shared) surface here. Skip only on the same
opt-out as Tier 1.

**If the gate fails:**

1. Identify which task interaction caused it (gate failures are usually integration problems, not single-task problems)
2. Add a new test covering that interaction to the relevant task
3. Run that task through its Red-Green loop again
4. Re-run the gate

**If the gate passes:** mark the stage complete, append the stage's handoff note to the plan (see Context resets below), commit with `"Stage N green"`, and start Step 3.1 for the next stage.

---

## Context resets at stage boundaries

Long executions degrade: a context window filled with stage-1 diagnostics is
worse at stage 4 than a fresh one, and automatic compaction loses unpredictable
detail. Structured resets beat degraded context — and the plan file is already
the handoff artifact.

- **Stage gates are the reset points.** After each gate passes, append a short
  note to the plan file under the stage:

  ```
  **Stage N handoff:** <deviations from plan, surprises found, decisions made,
  anything a fresh context needs that the Status flips don't capture>
  ```

  Committed with the `"Stage N green"` commit. Keep it to a few lines — it is
  a briefing, not a log.
- **Resuming fresh:** a new session (or a post-compaction continuation) picks
  up the plan by reading the Research Summary, the `Status:` flips, and the
  handoff notes — never by needing the prior transcript. If you find yourself
  unable to continue without the old transcript, the handoff notes were too
  thin; that's the bug to fix.
- **On large plans, prefer the reset.** When a stage closed with heavy
  diagnostic noise (long Red-Green loops, big tool outputs), suggest the user
  start the next stage in a fresh session pointed at the plan path.

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
3. **Independent evaluator pass (default).** Dispatch a fresh evaluator agent briefed ONLY with the plan's stated goals, the per-stage Goal lines, and the gate criteria — not the implementation transcript. It verifies the plan's overall goal against the artifact itself (run the app / drive the flows where runnable; read the final state where not) and reports per-criterion pass/fail. A FAIL here is a stop condition: surface it to the user before merge. Skip only on explicit user opt-out.
4. **Bump versions for what changed.** A completed plan almost always shifts a
   shippable version somewhere — bump it as part of close-out, don't leave it for
   later. Walk the artifacts the plan touched and apply a SemVer bump to each
   versioned manifest:
   - **breaking / removed behavior** → major; **new feature / capability** →
     minor; **fix / docs / internal only** → patch.
   - Bump the version field wherever the project records it — and **every place
     that mirrors it.** Common pairs: a package/plugin manifest *and* a registry
     or marketplace entry that restates its version; a workspace member *and* the
     lockfile; a `CHANGELOG.md` *and* the manifest. Grep for the old version
     string to catch mirrors. (For this repo: a plugin's
     `.claude-plugin/plugin.json` **and** the root `.claude-plugin/marketplace.json`
     entry; bump the marketplace `metadata.version` when the marketplace set
     itself changed.)
   - If the project keeps a `CHANGELOG.md`, add an entry for the new version.
   - Commit the bumps (`"chore: bump <component> to <version>"`); they ride with
     the close-out, not a follow-up.
   - When the correct bump is genuinely ambiguous (e.g. unclear if a change is
     breaking), state your call and let the user override — don't silently skip.
5. Update the plan document with a closing note: append `**Completed:** YYYY-MM-DD — commits: <list>` at the end. Also confirm every task's `- **Status:**` is `[x]` (any remaining `[ ]` task was not executed — either finish it or note it as deferred). The close-out line + all-`[x]` statuses make the plan's done-state unambiguous for any downstream reader.
6. **Reconcile the backlog.** Scan the plan for `Closes BL-NNN` references and any tasks that implemented an open backlog item. Call the `backlog` skill (`remove`) with that ID list. Reference each removed ID in the close-out commit message.
7. **Audit workflow specs.** If `docs/workflows/` exists, call the `workflow-spec` skill (`audit`) against the plan's cumulative diff. For every WF-ID the plan declared (`Changes WF-NNN`, `Removes WF-NNN`), verify the corresponding block was updated or deleted in this branch. **Any `Removed` finding the audit reports that the plan did not declare is a regression — stop and escalate before merge.** Surface every `Moved`/`Modified` finding for explicit user review.
8. Report to the user with:
   - Stages completed
   - Total commits
   - Version bumps applied (component → old → new)
   - Plan location for future reference
   - Backlog items closed (by ID) and any new ones opened during execution
   - Workflow audit triage: blocks updated, blocks removed, undeclared changes (if any survived escalation)
9. Offer merge / finalize options (worktree cleanup, PR creation, branch merge). Do not merge without explicit confirmation.

---

## Safety rails

- **Never start on `main` / `master` without explicit user consent.** Use a feature branch or worktree.
- **Destructive commands** (schema migrations, data deletes, force pushes, production deploys) — confirm before running, even if the plan says to.
- **Secrets** — if a task would read or write credentials, stop and confirm the mechanism (env var, secrets manager) with the user before proceeding.
- **Shared infrastructure** — staging/prod-adjacent changes get confirmation per stage, not per plan.

## Remember

- Critique the plan before starting
- Preflight is a hard gate — and it includes a live git repo (init one if missing)
- Run to completion: stage gates are checkpoints, not approval gates — don't stop between green stages to ask permission
- Follow the plan's exact tests, exact commands
- Respect the cycle budget — three targeted fixes, then stop
- Stage gates check integration, not just aggregate task success; invoke the platform stage-verify skill there when one matches the project
- Never silently skip a Red-Green cycle — report and move on is fine; skip is not
- Commit each green task; never squash silently during execution
- Append a handoff note at every passed gate — the plan file, not the transcript, is what survives a context reset
- Bump versions at close-out for whatever the plan changed, including every mirror of the version string

---

## Sources and rationale

- **Red-Green loop** — Kent Beck, *Test-Driven Development: By Example* (2002); the "test first, then make it pass" cycle adapted for task-level discipline
- **Stage gates** — Robert Cooper, *Winning at New Products* (1986); phase gates with specific pass/fail criteria
- **Max 3 failure cycles** — heuristic from debugging literature; after three targeted fixes without resolution, the hypothesis (not the implementation) is wrong. See Feynman on "the first principle is that you must not fool yourself"
- **Preflight as hard gate** — aviation checklist tradition; Atul Gawande, *The Checklist Manifesto* (2009)
- **Commit per green task** — frequent, small commits; *The Pragmatic Programmer* Ch. 7; Linus Torvalds on "each commit should be a single logical change"
- **Never skip the test** — Beck (TDD), Fowler ("Continuous Integration"); the test is the only signal that says "done"
- **Independent evaluator, context resets** — Anthropic Engineering, "Harness design for long-running application development" (https://www.anthropic.com/engineering/harness-design-long-running-apps); generators grade their own work too generously, and structured handoffs into fresh context outperform one degrading context

## Integration

- **planning-projects** — produces the plan this skill consumes; for decomposed big projects it produces a master plan plus sub-plans (format: its `references/master-plan-format.md`), which this skill executes per the Master plans section — sub-plans in register order, cross-plan gates on each completion, version bumps deferred to the master close-out
- **dispatching-parallel-agents** — invoked for `Parallel: YES` tasks with no file conflicts; its `references/stack-routing.md` is the shared table Step 3.2 also consults to delegate independent, output-heavy `Parallel: NO` tasks to a stack-matched subagent (e.g. `rust-expert`, `ui-android`, `testing-expert`) instead of running them inline
- **backlog** — invoked to `add` deferred work (skipped task, scope creep at a gate) and to `remove` items the plan closed in Phase Close-out
- **workflow-spec** — invoked in Phase Close-out to `audit` the cumulative diff against `docs/workflows/`; undeclared `Removed` findings block the merge
- **goal-evaluator agent** — the *black-box* gate/close-out evaluator: a fresh agent briefed ONLY with the stage/plan goals and gate criteria, never the implementation transcript. Verifies the *goal* is met against the artifact. Default at any gate with non-command checks and at Phase Close-out; skip only when the user opts out or every check is a command.
- **git-github:code-reviewer agent** — the *white-box* review (read-only): reads the actual diff and returns a Critical / Important / Suggestion triage. Runs in two tiers — **Tier 1** per green task (Step 3.3 rule 6; a Critical blocks the task within its Red-Green cycle budget) and **Tier 2** per stage gate (Step 3.5; a Critical fails the gate, advisories are surfaced for triage). Distinct axis from the goal-evaluator: *code quality* vs *goal attainment*. Shipped by the `git-github` plugin.
- **applying-design-handoff** — drives a *design-handoff* / *redesign* task: detects the
  handoff pack (local bundle or live claude.ai design project), reproduces it precisely,
  reshapes functionality to fit (behavior changes gated through `workflow-spec` with
  sign-off), and dispatches the `planning:design-handoff-reproducer` agent per slice. Its
  fidelity verify loop is the design-fidelity gate hook (Step 3.5).
- **design-handoff-reproducer agent** — the per-slice reproducer the redesign path
  dispatches: reproduces one normalized spec slice (component/screen + tokens + assets)
  faithfully in the target stack, self-checks against the fidelity rubric, and FLAGs
  behavior changes back instead of applying them.
- **testing-expert agent** — invoke when a task's test is ambiguous, flaky, or the plan's coverage is thin
- **platform stage-verify skills** — invoked at each stage gate to prove the stage on the real artifact when the project type matches. Android: `android-stage-verify` (android-dev plugin). Absence of a match is not a gate failure

**Review opt-out.** Both review tiers are default-on. Disable them per task with a `Review: skip` field on the task line (use for non-code or throwaway tasks), or globally for a run when the user opts out (state it once at Preflight, mirroring the goal-evaluator opt-out). Trivial/non-code diffs — docs-only, config-only, pure version bumps, comment-only — are auto-skipped at Tier 1 without needing an annotation. If `git-github:code-reviewer` isn't installed, note it and fall back to the goal-evaluator alone; a missing reviewer is not a gate failure.
