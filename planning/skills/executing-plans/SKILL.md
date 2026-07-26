---
name: executing-plans
description: Use when you have a planning-projects plan — Standard (staged), master (sub-plans), or light (single-stage) — and need to execute it, driving Red-Green loops and stage gates. Triggers on "execute this plan", "run the plan", "execute the master plan".
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

**Exception — light plans.** A file whose name ends in `-light-plan.md` or whose first
heading is `# Light Plan:` is a **light plan** (format:
`../planning-projects/references/light-plan-format.md`). It deliberately has **no
Research Summary section, no Preflight section, and no Risk / Rollback / Blocks /
Parallel fields** — a single stage of 2–5 Status-carrying tasks and one gate. Do NOT
reject it for those missing fields; execute it per the **Light plans** section below.

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

**Step 4a applies here too** — run `validate-gate-checks.py` on the master itself, not only
on each sub-plan as it loads. A master's cross-plan checks live under `**Gate:**` markers
rather than `### Stage N Gate` headings, and those are precisely the checks that prove
integration *between* sub-plans, so an instance-shaped one there survives every sub-plan
gate and surfaces only at the master close-out — the most expensive place to find it.

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
   is handled like any stage-gate failure — same severity classification, remediation
   budget and exit criterion — traced to the responsible sub-plan/task or to the defect
   class it belongs to), append
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

## Light plans

A **light plan** (`*-light-plan.md`, format:
`../planning-projects/references/light-plan-format.md`) is a single stage of 2–5
Status-carrying tasks with one gate. Execute it through the normal single-plan flow
below, with these deltas — the machinery **scales to the size of the job** rather than
running at full weight:

1. **Preflight is git-bootstrap + baseline tests only.** A light plan has no Preflight
   section; the "baseline tests pass" check lives in its single gate. Still do the git
   bootstrap (Phase 2 — a repo must exist for commit-per-task) and confirm the baseline
   is green before Stage 1. Nothing else to verify.
2. **No parallel dispatch.** Every task runs **inline in the main session**, in listed
   order, through the normal Red-Green loop. A light plan has no `Parallel` field and no
   fan-out — do not invoke `dispatching-parallel-agents`. (A task may carry an optional
   `Depends on`; honor it as ordering.)
3. **One review, not per-task.** **Skip the Tier-1 per-task review.** Instead, after the
   last task goes green and **before** the gate (this is a pre-gate check, not the gate
   itself — a light plan still has exactly one gate, its Stage 1 Gate), run **one**
   `git-github:code-reviewer` (read-only) pass over the **whole plan diff** (`git diff`
   across all the light plan's commits). Handle its verdict exactly like the Tier-2 stage
   review: a **Critical** blocks close-out just as a Tier-2 Critical fails a gate (fix
   within the same discipline, re-run test + review), and Important findings are surfaced
   for the user's triage rather than auto-fixed — but they are still bound by the **exit
   criterion** (Step 3.5), so each one leaves the gate either fixed or recorded to the
   `backlog` with the user told. A light plan is a small plan, not one where findings
   evaporate. Skip only on the usual opt-out /
   trivial-diff rules — so an entirely docs-only light plan skips it too (zero reviews is
   correct there, exactly as a docs-only task auto-skips Tier-1 in a Standard plan); the
   one review is guaranteed only when the plan's diff carries reviewable code. **This
   single pre-gate review IS the light plan's Tier-2 — do not also run a separate Step 3.5
   Tier-2 pass.** It keeps one real review in the loop without paying per-task review
   overhead on a handful of tasks.
4. **Both evaluator passes are opt-in, not default.** A light plan does **not** dispatch
   the independent goal-evaluator by default — neither at the gate (Step 3.5) **nor at
   close-out (Phase Close-out step 3)**, which for a Standard plan is default-on. Dispatch
   it only if a check requires genuine judgment ("reads coherently", "flow works
   end-to-end") or the user asks — same rule as any gate, just that a light plan's single
   command-ish gate rarely has such a check. (This is the one place "everything else is
   unchanged from Standard" below does **not** apply — the close-out evaluator's default
   flips from on to off at Light.)
5. **Close-out is one stated bump.** Run the full suite one final time — unless the
   single gate's full-suite run was the last thing to execute with no commits landed
   after it, in which case that run counts as the close-out run (one full pass, not
   two) — reconcile the backlog (`Closes BL-NNN`), and append the `**Completed:**`
   line. For version bumps,
   apply a **single stated SemVer bump** to what changed and its mirror — in this repo,
   name the plugin's `.claude-plugin/plugin.json` **and** the root marketplace entry
   explicitly (that pair) rather than running the full mirror-grep ritual. State your call
   so the user can override.

**Everything else is unchanged from a Standard plan:** Status flips the moment a test is
green, a commit per green task, the Red-Green cycle budget and all Stop conditions,
run-to-completion (don't pause at the gate to ask permission), one handoff note at the
single gate, and the honest-gates integrity contract. A light plan is a small plan, not a
sloppy one.

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
2. Verify the structure: Research Summary, Preflight, Stages with the expected fields.
   **For a light plan (`*-light-plan.md` / `# Light Plan:`), the absence of a Research
   Summary section, a Preflight section, and Risk / Rollback / Blocks / Parallel fields
   is correct, not a defect — do not flag it.** Verify instead that it is a single stage
   of 2–5 tasks, each with a `Status` field and a runnable `Test:`, plus one gate. (A
   light plan with a second stage or a 6th task should have been a Standard plan — flag
   that, per the format's upgrade rule.)
3. Critique: is any task's test vague ("should work")? Is any stage oversized (>7 tasks)? Is any dependency cycle present? Does any task modify a file that a parallel sibling also modifies? (The parallel-conflict and stage-oversize checks are moot for a light plan — one stage, inline execution.)
4. **If concerns exist, surface them to the user before starting.** A plan with an unrunnable test or a dependency cycle will waste an entire Red-Green budget before the problem is found

4a. **Classify the plan's gate checks** — run
   `python3 <planning-plugin>/skills/planning-projects/scripts/validate-gate-checks.py <plan>`
   and surface the result with the other critique concerns. An **INSTANCE-SHAPED** check
   names one artifact where the goal is a property of many, so it *cannot fail on the
   siblings that make the defect class* — they survive the gate, and each survivor costs
   another remediation round. Catching that here is the cheapest it will ever be.

   **Advisory on an existing plan, mandatory on a new one.** Every plan written before
   this rule predates it, and retro-failing them would only teach executors to route
   around the check — so a flagged *existing* plan is a reported concern you note and
   execute anyway, while `planning-projects` may not present a *newly authored* plan that
   fails it. Say which case you are in when you report the result.

   The `(judgment)` marker is the sanctioned escape hatch, not a loophole: a check that
   genuinely needs a reader carries it and routes to the evaluator at Step 3.5. A plan
   with **no** marked checks and **no** executable sweeps is usually a plan whose gates
   were never written to be run.

5. **Read the plan's `## Decisions in force`.** These are the constraints the plan was
   written under — the architectural decisions the register holds, carried into the plan
   file precisely so a session that never reads the register still implements under them.
   Note which tasks carry `Honors DEC-NNN` (a constraint to respect) and which carry
   `Supersedes …` (a deliberate override you will record at close-out).

   **A plan with no such section is not a plan with no decisions.** Every plan written
   before this convention lacks one. Treat its absence as *"not recorded"*, never as
   *"none apply"* — run the scan yourself at Preflight (below) and proceed on that result.

Create a TodoWrite list mirroring the plan: one task per stage, sub-items per task. Mark the current stage as `in_progress` only when Preflight passes.

## Phase 2 — Preflight

Run every check in the Preflight section and report pass/fail:

- Tools installed and at compatible versions
- Dependencies resolvable
- APIs reachable, keys valid
- Access / permissions verified
- Baseline test suite passes
- **Version control is live** — see below
- **Decisions in force are current** — see below

### Decisions re-check (the plan's snapshot can be stale)

The decisions register **accretes between planning and execution**. A plan written last
month can be executed against a register that has since gained a constraint, or superseded
one the plan still honors — the same staleness problem the plan's own age signals, applied
to a second artifact.

So Preflight does not trust the recorded section: re-run the scan and diff it.

1. Call the `decisions` skill's `relevant` operation for this project and its stacks
   (`../decisions/references/domain-slugs.md`).
2. Diff the result against the plan's `## Decisions in force`:
   - **New entry in scope** → surface it before Stage 1. It may invalidate a task.
   - **An entry the plan honors is now superseded** → surface it. The plan may be
     implementing a constraint that no longer holds.
   - **Unchanged** → say so in one line and proceed.
3. **A plan with no section** (written before the convention): report the scan result as
   the working set and proceed. Absence is not exemption.

Surfacing here is cheap; discovering it at the gate costs a stage. This is a report, not a
stop condition — unless the diff invalidates a task outright, in which case it is a
plan defect and returns to `planning-projects` (§ When to revisit earlier steps).

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
never reference again. **Brief it with the decisions in force that bear on the task**,
exactly as the parallel path does (`../dispatching-parallel-agents/SKILL.md` § Prompt
template) — both dispatch paths, one convention. A delegated task is no less bound by the
register than an inline one; it is just less able to discover that on its own. It is a context-hygiene move, **not** a token saving — the
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
   - **Critical → blocking.** A Critical finding means the task is not actually done. Fix it inline (one fix per cycle, diagnose first — same discipline as the Red-Green loop), then **re-run at fix-scope** — the task's own `Test:` plus the test classes the fix touched, never the full suite (`../planning-projects/references/test-scope-tiers.md`) — **and re-dispatch the review**. Critical-review cycles count against the *same* `Red-Green max cycles` budget as test failures; on exhaustion, escalate like any other budget exhaustion (Stop conditions). The executor applies the fix; the reviewer only ever reports.
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
- **Regressions check runs at stage-scope on intermediate gates:** cheap host-side checks in full, expensive suites (device/instrumented/e2e) restricted to the modules the stage's commits touched — never `clean`. Use the plan's declared `stage-scope:` command when its Preflight carries a "Test-scope commands" block; when the full suite is cheap (<~5 min), just run it in full. Policy: `../planning-projects/references/test-scope-tiers.md`.
- **The final stage's gate runs at plan-scope**, together with close-out — the plan's one full clean pass (see Phase Close-out).
- A scoped gate report states what scope actually ran (honest-gates disclosure) — e.g. "gate green — stage-scope: `:features` instrumented + full `check`." An expensive stage-scope suite may run in the background while the Tier-2 review below is dispatched — the two are independent.

**Platform stage-verify hook.** After the stage's own gate checks pass, if the
project's platform ships a stage-verify skill, invoke it as the final gate step
— it proves the stage on the real artifact, not just the test suite. A failure
there is a gate failure (handle it like any other below). Brief the stage-verify
skill with the gate's tier: at an intermediate gate it verifies at stage-scope
(touched-module instrumented tests); at the final gate it runs the full device
suite (plan-scope) — and that run IS the plan-scope pass's device portion, not
an addition to it (don't run the declared `plan-scope:` device suite separately
and then the hook's again). Match by project type:

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
(handle it via the "If the gate fails" steps below). Important findings are not
auto-fixed, but they are **not free either**: they are surfaced for the user's
triage and each one leaves the gate either fixed or recorded to the `backlog`,
per the **exit criterion** below, which applies to *every* gate pass and not only
to one reached through the failure branch. Suggestions are recorded. This is the only
point where findings are reviewed against the *coherent stage*, so cross-task
issues the per-task Tier-1 pass couldn't see (duplication across tasks, an
abstraction that should have been shared) surface here. Skip only on the same
opt-out as Tier 1.

**Decisions-conformance check (gate criterion, not advisory).** Check the stage's
cumulative diff against the decisions in force.
A change that contradicts a decision in force, without a `Supersedes` citation on its
task, is a **gate failure** — handle it via the "If the gate fails" steps below.
Two legal resolutions, and only two:

- **Re-scope the change** so it stops contradicting the decision, or
- **Record a deliberate supersede** (`decisions supersede`) and add the `Supersedes
  DEC-NNN — <why>` citation to the task, making the override auditable.

"The decision seems outdated" is not a third option — that judgment is exactly what
`supersede` exists to record, and skipping it is how a register decays into fiction.

**Disclose the check's limits (honest-gates).** Unlike a test command, this is a judgment
call over a diff: it can miss a subtle contradiction, and a green result is not proof of
conformance. So the gate report states **what was actually examined** — which IDs were
checked against which parts of the diff — rather than asserting blanket conformance. A
check that overstates its coverage is worse than one that admits its scope, because the
next reader trusts it.

Skip only when the stage's diff is genuinely non-code (docs-only, version-bump-only) and
no decision in force bears on documentation.

**Exit criterion — what "the gate passed" means.** This governs **every** gate pass,
not only one reached by repairing a failure, and it is the single definition the
checks above and the procedure below both resolve to:

> A gate passes when **no Critical finding remains**, and **every Important finding
> is either fixed or recorded to the `backlog` with the user told**. Suggestions are
> recorded, never blocking.

The criterion is deliberately *not* "the detector returned silent". A fresh judgment
agent essentially never reports zero adverse findings, so "no findings" is not a
reachable state, and a gate whose exit condition cannot be satisfied is not a gate —
it is a loop. Recording is not dropping: an Important that is not fixed leaves the
gate as a backlog ID, never as silence. An Important-only result is therefore a
**pass with an obligation**, not a clean pass — if nothing was recorded and the user
was not told, the gate has not passed yet.

**If the gate fails:**

Treat the failure as a **defect class sampled once**, not a point defect. Detection
at a gate is goal-scoped (the evaluator re-reads the whole artifact every round)
while repair defaults to instance-scoped — so a class with N instances costs ≈N
rounds, each one looking like fresh news. Triage before repairing, and bound the
loop.

1. **Classify every finding by severity** — the same **Critical / Important /
   Suggestion** taxonomy the review tiers already use (Step 3.3 rule 6), so a gate
   finding and a review finding are graded on one scale rather than two.
2. **Identify what caused it, and name the set it belongs to.** A gate failure is
   usually an integration problem rather than one task's bug. Beyond the task
   interaction, name the set the finding quantifies over — the other files,
   callers, examples or docs that could carry the same defect. Repairing the
   instance and leaving its siblings is what converts one class into N rounds.
3. **Add a test covering that interaction** to the relevant task. Where the finding
   is set-valued, that test is the **sweep over the set** (the class-predicate rule
   in `../planning-projects/SKILL.md`), not a check on the single file that failed —
   an instance-shaped check cannot fail on the siblings that make the class.
4. **Run that task through its Red-Green loop again.**
5. **Re-verify narrowly, plus the sweep.** Re-run the failed check(s), any check
   whose inputs the fix touched, and the step-3 class sweep — not every gate check
   from scratch.

**Remediation budget — default 2 rounds per gate.** One round is classify →
repair → re-verify. It is a default, and a plan may override it by stating a
different number of remediation rounds on the stage; **count the rounds and report
the count** in the gate report ("gate green — remediation round 2 of 2"). An
uncounted loop is how a gate reaches its fourth round with nobody noticing the
third.

**Stop repairing when the exit criterion above is met** — no Critical remaining,
every Important fixed or recorded. Do not spend a round chasing Suggestions, and do
not spend one trying to make a judgment agent go quiet.

**On budget exhaustion, escalate with the residual list.** Report the findings
that remain, their severities, and how the rounds were spent. This is a documented
**Stop condition** (below) — not a failure to hide, and not a licence to keep
looping. The user decides between another round, returning to
`planning-projects`, and shipping with the residual recorded.

**If the gate passes** (per the exit criterion above — including its obligation to have
recorded every unfixed Important and told the user): mark the stage complete, append the
stage's handoff note to the plan (see Context resets below), commit with `"Stage N green"`,
and start Step 3.1 for the next stage. The gate report states the remediation rounds spent
and any residual findings recorded, so "green" never reads as "nothing was found".

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
  **Decisions in force:** <the DEC/GDEC IDs still binding, plus any Supersedes
  citation raised in this stage and not yet recorded>
  ```

  The decisions line is not redundant with the plan's `## Decisions in force`
  section: a fresh session reads the handoff notes to learn *the current state*,
  and a constraint that surfaced mid-stage (a supersede raised at Stage 2, a new
  entry the Preflight re-check caught) exists nowhere else. A constraint absent
  from the handoff is one the next session will not know about.

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

## Progress state file (live statusline bar)

Mirror execution state to `<repo-root>/.claude/plan-progress.json` so the
shipped statusline renderer (`scripts/plan-progress.py`) can draw a live
progress bar (`⚙ plan ▐██████░░░░▌ 3/6 (50%) · S2/3 ▶ T2.2 …`). Maintain the
file on every run — it is cheap, and the renderer simply never fires for
users who haven't wired it.

Write the full file (overwrite, don't patch) at each transition:

| When | Write |
|------|-------|
| Preflight starts | `phase: "preflight"` |
| A task starts (incl. re-entering its Red-Green loop) | `phase: "task"`, `stage`, `task` ("2.3"), `task_desc` |
| A stage gate runs | `phase: "gate"`, `stage` |
| Close-out starts | `phase: "closeout"` |
| A Stop condition halts execution | `phase: "blocked"`, `stage`/`task` if known, `note` (one line, e.g. "cycle budget exhausted") |
| Close-out finishes (last step) | **delete the file** |

Schema (all on one line is fine):

```json
{"plan": "plans/foo-plan.md", "phase": "task", "stage": 2,
 "task": "2.3", "task_desc": "parse config entries",
 "updated": "<ISO-8601 UTC now>"}
```

`plan` is the plan file's path — absolute, or relative to the repo root.
Always refresh `updated` (the renderer marks state older than 12h as stale).
Done/total counts are **not** in the file — the renderer derives them from the
plan's authoritative `Status:` fields, so a forgotten update can never show
wrong progress, only a wrong current-task label. The file is ephemeral session
state: never commit it — during the git bootstrap, ensure
`.claude/plan-progress.json` is gitignored (append it if the repo doesn't
already ignore it). For a master plan, the state file always points at the
**sub-plan** currently executing.

**One-time user setup** (only if asked to wire it): point `statusLine` in
`~/.claude/settings.json` at a wrapper that feeds the same stdin JSON to the
user's existing statusline command first, then to
`<planning-plugin>/skills/executing-plans/scripts/plan-progress.py`, appending
its output as an extra line when non-empty. The renderer prints nothing when
no plan is executing, so it never disturbs the normal statusline.

---

## Stop conditions

Stop immediately and escalate to the user when:

- Preflight fails
- A task exhausts its Red-Green cycle budget
- A stage gate's remediation budget is exhausted — the responsible task(s), or the defect class they belong to, were re-run and Critical findings remain (escalate with the residual list)
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

1. Run the plan's **sole plan-scope pass** — the only `clean` and the only full expensive-suite run in the whole execution (intermediate gates ran stage-scope), including any quarantined slow tests. Use the plan's declared `plan-scope:` command when present. If the final stage gate already ran this exact plan-scope pass and no commits landed after it, that pass counts — don't run it twice.
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
7. **Reconcile the decisions register.** Two directions, both easy to forget and both
   corrosive when skipped:
   - **Supersedes citations → record them.** Scan the plan for `Supersedes DEC-NNN` /
     `Supersedes GDEC-…` on any task. For each, call the `decisions` skill (`supersede`)
     with the replacement entry. Until this runs, the register still asserts a constraint
     the code no longer honors — and the *next* plan will be written against it.
     `planning-projects` promises this step on the planner's behalf ("the executor records
     the supersede at close-out"); this is where that promise is kept.
   - **New constraints created → record them.** Execution discovers things planning
     couldn't: an approach that turned out to be blocked, a platform limit hit at Stage 3,
     a cost knowingly accepted to get a stage green. Each is a decision whether or not
     anyone called it one. Call `decisions add` with the reason — the constraint, the
     evidence, the alternative rejected, the cost accepted. If you cannot name a rejected
     alternative or a cost, it probably wasn't a decision; don't pad the register.
   - Reference the recorded IDs in the close-out report and commit message.

8. **Audit workflow specs.** If `docs/workflows/` exists, call the `workflow-spec` skill (`audit`) against the plan's cumulative diff. For every WF-ID the plan declared (`Changes WF-NNN`, `Removes WF-NNN`), verify the corresponding block was updated or deleted in this branch. **Any `Removed` finding the audit reports that the plan did not declare is a regression — stop and escalate before merge.** Surface every `Moved`/`Modified` finding for explicit user review.
9. Report to the user with:
   - Stages completed
   - Total commits
   - Version bumps applied (component → old → new)
   - Plan location for future reference
   - Backlog items closed (by ID) and any new ones opened during execution
   - Decisions recorded or superseded during close-out (by ID)
   - Workflow audit triage: blocks updated, blocks removed, undeclared changes (if any survived escalation)
10. Offer merge / finalize options (worktree cleanup, PR creation, branch merge). Do not merge without explicit confirmation.

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
- Respect the gate's **remediation budget** too — 2 rounds by default, counted and reported; a gate passes when no Critical remains and every Important is fixed or recorded, never when the detector finally goes quiet
- Repair the defect **class**, not the instance the gate happened to sample — name the set, sweep it
- Stage gates check integration, not just aggregate task success; invoke the platform stage-verify skill there when one matches the project
- Never silently skip a Red-Green cycle — report and move on is fine; skip is not
- Commit each green task; never squash silently during execution
- Append a handoff note at every passed gate — the plan file, not the transcript, is what survives a context reset
- Bump versions at close-out for whatever the plan changed, including every mirror of the version string
- Keep `.claude/plan-progress.json` current at every transition and delete it when close-out finishes
- Scope gates by tier: stage-scope at intermediate gates, fix-scope after review fixes, exactly one clean plan-scope pass at close-out (../planning-projects/references/test-scope-tiers.md)

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
- **decisions** — the architectural-decision register, consumed on three paths: `relevant` at Preflight (re-scan and diff against the plan's recorded `## Decisions in force`, since the register accretes between planning and execution), the conformance check at every stage gate (a contradiction without a `Supersedes` citation is a gate failure), and `supersede` / `add` at close-out (recording overrides the plan declared, and constraints execution itself discovered)
- **workflow-spec** — invoked in Phase Close-out to `audit` the cumulative diff against `docs/workflows/`; undeclared `Removed` findings block the merge
- **goal-evaluator agent** — the *black-box* gate/close-out evaluator: a fresh agent briefed ONLY with the stage/plan goals and gate criteria, never the implementation transcript. Verifies the *goal* is met against the artifact. Default at any gate with non-command checks and at Phase Close-out; skip only when the user opts out or every check is a command.
- **git-github:code-reviewer agent** — the *white-box* review (read-only): reads the actual diff and returns a Critical / Important / Suggestion triage. Runs in two tiers — **Tier 1** per green task (Step 3.3 rule 6; a Critical blocks the task within its Red-Green cycle budget) and **Tier 2** per stage gate (Step 3.5; a Critical fails the gate, and an Important leaves the gate fixed or recorded to the `backlog` per the exit criterion — never merely mentioned). Distinct axis from the goal-evaluator: *code quality* vs *goal attainment*. Shipped by the `git-github` plugin.
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
- **test-scope-tiers reference** (`../planning-projects/references/test-scope-tiers.md`) — the shared scope policy Step 3.3 (fix-scope), Step 3.5 (stage-scope), and Close-out (plan-scope) follow

**Review opt-out.** Both review tiers are default-on. Disable them per task with a `Review: skip` field on the task line (use for non-code or throwaway tasks), or globally for a run when the user opts out (state it once at Preflight, mirroring the goal-evaluator opt-out). Trivial/non-code diffs — docs-only, config-only, pure version bumps, comment-only — are auto-skipped at Tier 1 without needing an annotation. If `git-github:code-reviewer` isn't installed, note it and fall back to the goal-evaluator alone; a missing reviewer is not a gate failure.
