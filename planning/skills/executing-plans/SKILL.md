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

## Reference map

The trunk carries what fires on every run. These load when their condition is met — read the
one you need rather than working from memory:

| Read this | When |
|---|---|
| `references/master-plans.md` | the plan file is a `*-master-plan.md` |
| `references/light-plans.md` | the plan file is a `*-light-plan.md` |
| `references/review-scope.md` | declaring the tier at Preflight, or resolving how format and tier compose — **the authority on both, and on the opt-out rules** |
| `references/dispatch-fidelity.md` | the roster, probe or `Review: skip` snapshot needs justifying rather than just following |
| `references/gate-failure-procedure.md` | a stage gate has failed |
| `references/progress-state-file.md` | writing `.claude/plan-progress.json`, or wiring the statusline |
| `references/sources.md` | citing why a rule here exists |

Paths are relative to this skill's directory; from a dispatch use
`references/<file>`.

---

## Master plans

A `*-master-plan.md` (or `# Master Plan:` heading) links 2–7 sub-plans through a
`## Sub-plans` register. It deliberately has no Preflight, Stages or Tasks — do not reject
it. Execute sub-plans in register dependency order, one per fresh session where practical;
on each sub-plan's close-out flip its register `Status`, run that entry's `**Gate:**` checks,
append a handoff note, and commit `"Sub-plan N green"`. **Version bumps defer to the master
close-out** — one feature landing across five sub-plans is one release event, not five.

Run `validate-gate-checks.py` on the master itself, not only on each sub-plan: a master's
cross-plan checks are exactly the ones that prove integration *between* sub-plans, so an
instance-shaped one there survives every sub-plan gate.

Full execution model, critique checklist and close-out: `references/master-plans.md`.

---

## Light plans

A `*-light-plan.md` (or `# Light Plan:` heading) is a single stage of 2–5 tasks with one
gate. It deliberately has **no Research Summary, no Preflight section, and no Risk /
Rollback / Blocks / Parallel fields** — do not reject it for those. Execute it through the
normal flow with four deltas: Preflight is git-bootstrap plus a green baseline only; every
task runs **inline** (no fan-out); **one** whole-diff review replaces per-task Tier-1 — **that single pre-gate review IS the
light plan's Tier-2, so do not also run a separate Step 3.5 Tier-2 pass**; and close-out
applies a single stated version bump.

Everything else is unchanged — Status flips, a commit per green task, the cycle budget, the
Stop conditions, honest gates. A light plan is a small plan, not a sloppy one.

Full deltas, including how the review shape composes with the declared tier:
`references/light-plans.md`.

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

Once Preflight passes, **drive the plan straight through to close-out.** Stage boundaries
are checkpoints, not approval gates: commit a passed gate and start the next stage without
asking "should I continue?" The plan is the approval, and burning a turn to ask permission
between green stages is the failure mode this skill exists to prevent. Keep going through a
green task, a passed gate, a failed cycle that still has budget, and any surprise you can
resolve from the plan plus evidence.

**Only the documented Stop conditions below halt execution.** Everything else is work to push
through. When you do stop, it is because continuing would be guessing or unsafe — say which,
with evidence, and what you need to resume. The context-reset guidance is an efficiency
tactic for very large plans, **not** a licence to stop early: prefer a fresh session over a
*degraded* one, never over *finishing the work*.

---

## Phase 1 — Load and critique

1. Read the plan file in full
2. Verify the structure: Research Summary, Preflight, Stages with the expected fields. **For
   a light plan those first two and the Risk / Rollback / Blocks / Parallel fields are
   correctly absent — do not flag it**; verify instead a single stage of 2–5 tasks, each with
   a `Status` and a runnable `Test:`, plus one gate. A light plan with a second stage or a
   6th task should have been Standard — flag that.
3. Critique: is any task's test vague ("should work")? Is any stage oversized (>7 tasks)? Is any dependency cycle present? Does any task modify a file that a parallel sibling also modifies? (The parallel-conflict and stage-oversize checks are moot for a light plan — one stage, inline execution.)
4. **If concerns exist, surface them to the user before starting.** A plan with an unrunnable test or a dependency cycle will waste an entire Red-Green budget before the problem is found

4a. **Classify the plan's gate checks** — run
   `python3 <planning-plugin>/skills/planning-projects/scripts/validate-gate-checks.py <plan>`
   and surface the result with the other concerns. An **INSTANCE-SHAPED** check names one
   artifact where the goal is a property of many, so it cannot fail on the siblings that make
   the defect class — each survivor costs another remediation round, and catching it here is
   the cheapest it will ever be.

   **Advisory on an existing plan, mandatory on a new one** — retro-failing old plans would
   only teach executors to route around the check, so note a flagged existing plan and
   execute it anyway, while `planning-projects` may not present a *newly authored* plan that
   fails. Say which case you are in. The `(judgment)` marker is the sanctioned escape hatch:
   a check that genuinely needs a reader carries it and routes to the evaluator at Step 3.5.
   A plan with no marked checks and no executable sweeps is usually one whose gates were
   never written to be run.

5. **Read the plan's `## Decisions in force`** — the constraints it was written under,
   carried into the file so a session that never reads the register still implements under
   them. Note which tasks carry `Honors DEC-NNN` and which carry `Supersedes …` (a deliberate
   override you record at close-out). **A plan with no such section is not a plan with no
   decisions** — treat its absence as *"not recorded"*, never *"none apply"*, and run the
   Preflight scan below.

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
- **The dispatch roster is declared** — every `Parallel: YES` task, with its routed agent type; see below
- **Dispatch works in this session** — probed, not assumed, and only when the roster is non-empty; see below
- **Pre-existing `Review: skip` annotations are recorded** — the list, at the commit the run starts from; see below
- **Review scope is declared** — which tier the plan's diff warrants, and why; see below

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

### Dispatch roster and capability probe

1. **Enumerate the roster** — sweep **every task in the plan, across all stages**, and list
   each one whose `Parallel:` reads `YES` with the `subagent_type` it routes to per
   `../dispatching-parallel-agents/references/stack-routing.md`:

   ```
   Dispatch roster (Parallel: YES) — <n> of <total> tasks
     Task <N.M> → <subagent_type>
   ```

   A roster covering only the first stage is not a roster. An empty roster is a legitimate
   result — write `0 tasks`, so the absence is recorded as observed rather than as never
   examined.

2. **Probe the capability — only if the roster is non-empty.** Dispatch one throwaway
   `general-purpose` subagent whose whole task is to reply `DISPATCH-OK`, and confirm it came
   back. With an empty roster, record `probe: skipped — empty roster`.

3. **Snapshot the `Review: skip` annotations** against the commit the run starts from:

   ```
   Review: skip annotations at <base-sha> — <n> task(s): <Task N.M>, …
   ```

   The executor writes to the plan file throughout the run, so only an annotation in this
   snapshot is evidence the *user* authored it. Cite the snapshot when you skip, not the
   task line. Write `0 tasks` when there are none.

**A failed probe is a Preflight failure.** When dispatch is unavailable or disallowed in
this session and the roster lists at least one task, **Preflight fails and you stop** — the
user decides whether to enable it, re-plan those tasks as `Parallel: NO`, or accept inline
execution knowingly. Substituting inline execution on your own authority is not a
resolution; it takes a decision that belongs to the user and makes it silently.

Why each of these three exists, and what breaks without them: `references/dispatch-fidelity.md`.

### Review scope — the machinery scales to the change

**Declare a tier at Preflight and restate it in every gate report** (`review-scope: light —
prose edits to 3 skill files`). An undeclared run is `standard`. Pick it once, from the
plan's **cumulative diff**, not per task. This is the honest-gates disclosure rule applied to
review effort: downgrading silently and downgrading openly produce the same diff, so **the
declaration is what makes the choice reviewable**.

| Tier | When (the plan's cumulative diff) | Tier-1 (per task) | Tier-2 (per gate) | Evaluator |
|---|---|---|---|---|
| **none** | docs/config/version-bump/comment-only across the whole plan | skip | skip | skip |
| **light** | no new executable behavior, **or** under ~200 changed lines across ≤ ~5 files — and no risk-listed area touched | skip | one, over the whole plan diff before close-out | only at a gate carrying `(judgment)` |
| **standard** | multi-file code with new behavior — the default when unsure, and what an undeclared run gets | skip | per stage gate | only at a gate carrying `(judgment)` |
| **high** | **risk-listed:** security-sensitive, auth, data-destructive, public API, schema/migration | per task | per stage gate, plus a second independent pass | **always** |

**What the tier gates** is everything in the row — both review tiers, the gate evaluator, the
close-out evaluator, the second pass. What it does **not** gate is the dispatch roster, the
executor trailer, the dispatched-vs-inline reconciliation, honest-gates disclosure, and the
plan's own tests and gate checks: those run at every tier including `none`. The line is cost —
a mandate costing an agent dispatch is tiered, a mandate costing a line of text is not.

**The format decides the review's SHAPE. The tier decides its DEPTH.** Direct and Light plans
review the **whole plan diff once** before close-out; Standard and Master review **per stage
gate**, and per task only at `high`.

**Resolve a disagreement by the risk floor** — not by taking the lighter option, and not by
taking the heavier; both are instincts standing in for a rule. Touching a risk-listed area
sets `high` whatever the size; **size alone never escalates**, so a large prose or
mechanical-rename diff is a big `light` change rather than a `standard` one. A Light plan
touching an auth path is a small plan doing a dangerous thing: whole-diff shape *and*
`high`'s second pass and mandatory evaluator.

A tier is a floor, not a ceiling: escalate mid-plan when the diff turns out riskier than it
looked and say so in the gate report; never quietly de-escalate.

`references/review-scope.md` is the authority on this — it carries the worked composition table,
the per-sub-plan rule for masters, and the opt-out rules. Where a summary here and that file
appear to disagree, the file wins.
## Phase 3 — Stage execution

For each stage in order:

### Step 3.1 — Identify what can run now

Scan the stage's tasks. A task is **dispatchable** when every task in its `Depends on` list is green. At stage start, this is every task whose `Depends on` is either empty or lists only tasks from already-green prior stages.

### Step 3.2 — Split by parallelism

- Tasks with `Parallel: YES` and no file conflicts with another ready task → hand to `dispatching-parallel-agents`, concurrently
- Tasks with `Parallel: YES` that modify files another ready task modifies → still dispatched, one after another (see the file-conflict check)
- Tasks with `Parallel: NO` → work in the main session, unless the delegation rule below applies

**File-conflict check:** before dispatching, verify no two parallel tasks edit the same file. If they do, **serialize the dispatches — do not inline either one.** A file conflict is a fact about *scheduling*: it says these two cannot run at the same moment, which is a different claim from "this task need not go to a subagent". `Parallel: YES` is a delegation directive (`../planning-projects/SKILL.md` § Stage structure), and nothing about a sibling touching the same file withdraws it. So the conflicting task is dispatched on its own once the first returns, and its commit carries `Executor: dispatched — <type>` like any other.

If you genuinely need a `Parallel: YES` task inline, that is a deviation: run it, say so in
the gate report's dispatch line with a reason, and let the trailer record `Executor: inline`.

**Delegate sequential tasks for context hygiene.** A `Parallel: NO` task defaults to the main
session, but when it is **independent**, **output-heavy** (builds, broad greps, long test
logs) and not latency-critical, hand it to one stack-matched subagent instead. This keeps the
orchestrator's window on plan state rather than churn it will never reference again — it is
context hygiene, **not** a token saving, since the subagent's tokens still burn. Brief it
with the decisions bearing on the task and **require the same executor trailer**
(`Executor: dispatched — <type>`): this path doesn't go through `dispatching-parallel-agents`,
so nothing else asks for it, and the task would otherwise land indistinguishable from one the
orchestrator ran. Keep a task inline when it is coupled to session context, needs
back-and-forth, or is a quick targeted edit. Pick the type and its stack skill from
`../dispatching-parallel-agents/references/stack-routing.md`.

**If the matched capability's plugin isn't enabled**, don't fall through to `general-purpose`
with no domain knowledge — resolve it from disk per that same reference's § *Resolving a
capability whose plugin isn't enabled*. A component flagged `requires_enablement` (hooks /
MCP) can't be lazy-loaded: stop and ask the user to enable that plugin.

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
2. **Diagnose before fixing.** Read the error, form a hypothesis, confirm it against the code, then write the fix. On the **second** RED cycle for a task, stop improvising and invoke `no-fafo-debugging`: one failed targeted fix is bad luck, two says the hypothesis is wrong rather than the patch.
3. **Respect the cycle budget** (plan-set, default 3). On exhaustion stop and escalate — three failed targeted fixes means the approach is wrong, not the implementation. If the user skips rather than re-plans, `backlog add` the task; don't silently drop it.
4. **Never skip the test.** The task's Test field is the gate. "It looks right" is not green.
5. **Flip the task's Status to `[x]` the moment its test is green**, in the same change as the work. It is the authoritative done-marker; downstream tools (`portfolio unify`) read it rather than guessing from gates or git. **The flip records that the task is done, never who did it** — an inlined task and a dispatched one write the identical `[x]`, so rule 7's trailer is the only artifact carrying that.
6. **Quick review gate (Tier 1).** Whether it runs, and at what shape, comes from § Review scope — do not re-derive it. After the test is green and Status is flipped but **before** the commit, dispatch `git-github:code-reviewer` (read-only) as a **fresh dispatch seeing only the task diff** — never the executor self-reviewing — briefed with the task description and its `Test:`. **Brief it to check behavioral claims too**: every sentence in the diff asserting what the code does (a default, an exit code, a count, an "every") is verified against the source or flagged, per `honest-gates`. Handle by severity:
   - **Critical → blocking.** A Critical finding means the task is not actually done. Fix it inline (one fix per cycle, diagnose first — same discipline as the Red-Green loop), then **re-run at fix-scope** — the task's own `Test:` plus the test classes the fix touched, never the full suite (`../planning-projects/references/test-scope-tiers.md`) — **and re-dispatch the review**. Critical-review cycles count against the *same* `Red-Green max cycles` budget as test failures; on exhaustion, escalate like any other budget exhaustion (Stop conditions). The executor applies the fix; the reviewer only ever reports.
   - **Important / Suggestion → advisory.** Do not act on them now. Append them to the plan file as a note under the task (`**Review notes (Task N.M):** …`) so the stage gate's deep review (Step 3.5) can triage the batch. They never block the task.
   - **Skip for trivial/non-code diffs.** Docs-only, config-only, pure version-bump, or comment-only diffs don't need Tier 1 — note the skip and proceed. Honor a `Review: skip` task annotation and the global opt-out (see References) the same way — but an opt-out is **evidenced, not asserted** (§ Review opt-out): note the skip *with* the quote or the cited annotation, never as a bare "skipped".

     **Exception — docs that assert executable behavior are not a trivial diff.** A docs change **asserting a fact about** commands, flags, env vars, exit codes, defaults, paths or invocation examples makes exactly the **behavioral claims** `honest-gates` § *A behavioral claim is a gate too* governs, and prose is where they go unchecked longest: no compiler, no test. Such a diff does **not** auto-skip Tier 1. The test is *asserting*, not *mentioning* — naming a flag in a heading or an unchanged sample claims nothing and still skips. The Tier-1 dispatch is scoped to the task *diff*, which bounds what it reviews, not what it may read, so the reviewer opens the cited source to check the claim.

   Tier 1 does **not** pause to ask the user — only to fix autonomously within budget, preserving run-to-completion.
7. **Commit after each green task** (`"Stage 2 Task 2.3: parse config entries"`), including the work, any Tier-1 fixes, and the flipped `Status: [x]`. The per-task commit is the unit of record and what makes a mid-plan stop recoverable. A passed gate adds its own `"Stage N green"` commit: keep **both** granularities, never collapse to one.

   **Every per-task commit ends with an executor trailer** — the last line of the message, taking one of these shapes:

   ```
   Executor: inline
   Executor: dispatched — <subagent_type>
   Executor: dispatched — <subagent_type>, <subagent_type>    (one task, several agents)
   Executor: inline (dispatch failed)                          (the body says why)
   Executor: inline (user authorised)                          (dispatch was available)
   ```

   **Keep the trailer to one physical line.** Git folds a continuation into the preceding
   trailer only when it is **indented**; an unindented wrap ends the block instead, so the
   trailer vanishes from every `%(trailers:…)` query with no error at all. The rule here is
   deliberately stricter than git — one physical line, never a folded continuation — because
   "indent it and it still parses" is a detail nobody checks at commit time and the failure
   is silent. Put the reason in the body; keep the trailer bare.

   Name the actual `subagent_type` that ran the work, not the routing table's suggestion, and
   say so when a dispatch failed and finished inline: a substitution nobody can see is the
   defect this trailer exists to end. **A trailer that misstates who ran the task is worse
   than none** — it converts a visible gap into a false record. Why a trailer at all: every
   other artifact is byte-identical whether a task ran inline or dispatched, so
   `git log --format='%(trailers:key=Executor,valueonly)' <base>..HEAD` is the only check
   that can read "5 marked YES, 0 dispatched" straight off the log.

### Step 3.4 — Propagate unblock

When a task finishes green, scan its `Blocks` field. For each blocked task, check whether ALL of its `Depends on` items are now green. If yes, it becomes dispatchable — return to Step 3.1.

### Step 3.5 — Stage gate

When every task in the stage is green, run the stage gate:

- Each gate check has a specific pass criterion (a command output, a test result, a manual verification)
- Run them in order; stop at the first failure
- **Regressions check runs at stage-scope on intermediate gates:** cheap host-side checks in full, expensive suites (device/instrumented/e2e) restricted to the modules the stage's commits touched — never `clean`. Use the plan's declared `stage-scope:` command when its Preflight carries a "Test-scope commands" block; when the full suite is cheap (<~5 min), just run it in full. Policy: `../planning-projects/references/test-scope-tiers.md`.
- **The final stage's gate runs at plan-scope**, together with close-out — the plan's one full clean pass (see Phase Close-out).
- A scoped gate report states what scope actually ran (honest-gates disclosure) — e.g. "gate green — stage-scope: `:features` instrumented + full `check`." An expensive stage-scope suite may run in the background while the Tier-2 review below is dispatched — the two are independent.
- **The gate report states the stage's dispatched-vs-inline counts, and a reason for every inlined `Parallel: YES` task.** Read them off the executor trailers rather than from memory — `git log --format='%h %(trailers:key=Executor,valueonly)' <base>..HEAD`, where `<base>` is the previous stage's `"Stage N green"` commit (for Stage 1, the commit the branch started from) — and reconcile against the roster Preflight declared. One line: `dispatch: 3 of 4 YES tasks dispatched; Task N.M inlined — <reason>`. A stage that dispatched everything it marked says `dispatch: 4 of 4` rather than saying nothing, so silence never has to be interpreted. A **Light plan** has no `Parallel` field and never fans out (§ Light plans — a Light plan never fans out), so its single gate carries no dispatch line — the requirement is scoped to plans that can have a roster, not waived where one would be vacuous.

  **An empty trailer value is `unknown`, never `inline`.** Git drops a whole trailer block at a line it cannot parse, so a wrapped or malformed trailer returns blank with exit 0 — indistinguishable, to the query, from a task nobody dispatched. Counting blanks as inline invents a deviation; counting them as dispatched hides one. So resolve each blank against the commit body, count it as `unknown` if it says nothing either, and report the unknowns: `dispatch: 1 of 1 dispatched; 2 commits predate the trailer convention (resolved from their bodies)`.

- **The gate report names every review that ran, the agent that ran it, and the diff it saw** — and, for a tier that did not run, the evidenced opt-out (§ Review opt-out) or the trivial/non-code diff that excused it. One line per tier, resolving `<base>` the same way the dispatch line above does — the previous stage's `"Stage N green"` commit — and naming the agent by a type dispatch can actually take. `goal-evaluator` is a **role**, not a registered agent: no `agents/goal-evaluator.md` ships in this marketplace, so a report naming it records a dispatch nobody can reproduce. Write the type that ran, then the role:

  ```
  review: Tier-2 git-github:code-reviewer over <base>..HEAD — APPROVE, 0 Critical
  evaluator: general-purpose in the goal-evaluator role, briefed on the stage goal + gate criteria — PASS, 2 Material
  ```

  Naming the **agent** distinguishes a dispatched review from the executor reading its own diff, which both tiers forbid; naming the **diff** makes its coverage checkable, since a reviewer briefed on the wrong range returns a clean verdict over code nobody looked at and "reviewed" reads identically either way. An inlined `Parallel: YES` task is a **deviation being disclosed**, not one being ratified — a gate report that keeps producing them is evidence the plan's `Parallel` fields belong back in `planning-projects`.

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

**Independent evaluator for non-command checks.** **Whether it runs comes from § Review scope
— do not re-derive it**: never at `none`, at `light` and `standard` when the gate carries a
`(judgment)` check, always at `high`. Run command checks yourself. When the tier mandates an
evaluator, dispatch a fresh one for the judgment checks, briefed ONLY with the stage goal
and the gate's pass criteria — never the implementation transcript or your own summary. The
session that wrote the code grades its own work too generously.

**Once the tier mandates it, the list of excuses is closed at two** — an **evidenced** user
opt-out (§ Review scope) or a gate whose every check is a command. There is no third reason:
an evaluator that cannot be dispatched is a Stop condition, not a skip. A tier that does not
mandate one is not an excuse at all but the machinery scaling as designed, and it is reported
as scope (`evaluator: not run — tier is light, no (judgment) check at this gate`) rather than
as an opt-out.

**Brief it to grade by severity, not just pass/fail** — a bare pass/fail gives the loop
nothing to terminate on, because a fresh judgment agent reading a real artifact essentially
always finds *something*, so "no adverse findings" is not a reachable state. Require, for
each finding, exactly one of:

| Severity | Meaning | Consequence |
|----------|---------|-------------|
| **Blocking** | the goal in scope is not met — the stage's at a gate, the plan's at close-out | must be fixed; the gate does not pass |
| **Material** | real defect, goal still met | fixed, or recorded to the `backlog` with the user told |
| **Minor** | nit, polish, taste | recorded; never blocks |

Blocking maps to Critical, Material to Important, Minor to Suggestion, so both scales
resolve to the one **exit criterion** below. An evaluator FAIL carrying no Blocking finding
is a **pass with recorded residuals**, not a failure — tell the evaluator so explicitly, or
it will withhold PASS to seem rigorous and hand the loop an unsatisfiable condition.

**Deep code review (Tier 2).** Whether it runs, and at what shape, comes from § Review
scope. The evaluator above verifies *goals* black-box; this is the complementary *white-box*
pass: dispatch `git-github:code-reviewer` (read-only) over the **full stage diff** plus the
stage's collected `**Review notes (Task N.M):**` lines. It is a gate criterion, not advisory
— a **Critical** here is a **gate failure**. Important findings are not auto-fixed but are
**not free either**: each leaves the gate either fixed or recorded to the `backlog`, per the
**exit criterion** below, which governs every gate pass and not only one reached through the
failure branch. Suggestions are recorded. This is the only point where findings are judged against the *coherent
stage*, so cross-task issues Tier-1 could not see (duplication across tasks, an abstraction
that should have been shared) surface here. **Brief it to audit the stage's behavioral claims
as a set**, per `honest-gates` § *A behavioral claim is a gate too* — the stage view is where
a claim that was true when written and false after a later task shows up.

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

**Disclose the check's limits (honest-gates).** This is a judgment call over a diff, not a
test command: it can miss a subtle contradiction, and green is not proof of conformance. The
gate report states **which IDs were checked against which parts of the diff** rather than
asserting blanket conformance — a check that overstates its coverage is worse than one that
admits its scope, because the next reader trusts it. Skip only when the diff is genuinely
non-code and no decision in force bears on documentation.

**Exit criterion — what "the gate passed" means.** This governs **every** gate pass,
not only one reached by repairing a failure, and it is the single definition the
checks above and the procedure below both resolve to:

> A gate passes when **no Critical finding remains**, and **every Important finding
> is either fixed or recorded to the `backlog` with the user told**. Suggestions are
> recorded, never blocking.

It is deliberately *not* "the detector returned silent" — a fresh judgment agent never
reports zero findings, so a gate with that exit condition is not a gate but a loop. Recording
is not dropping: an unfixed Important leaves the gate as a backlog ID, never as silence. An
Important-only result is a **pass with an obligation** — if nothing was recorded and the user
was not told, the gate has not passed yet.

**"Fixed or recorded" is not a free choice — the finding's kind decides which.**

| Kind of finding | Disposition |
|---|---|
| **A defect in code this plan touched** | **Fix it.** The context is already loaded; this is the cheapest it will ever be. |
| **A decision** — new capability, a change needing sign-off, a trade-off with no obviously right answer | **Record it.** It is the user's call, not the executor's. |
| **A defect outside the plan's blast radius** | Record it, and say why it was out of reach. |

The asymmetry this closes: recording is frictionless and always available, while fixing risks
the gate you are trying to pass. So an executor under gate pressure drifts toward the backlog
for *everything*, and each deferral reads as scope discipline rather than as the avoidance it
is. A backlog that grows by half a dozen entries per plan is the symptom, not a sign of
thoroughness.

**A plan's scope guardrails bound that plan's subject matter. They are not a licence to defer
unrelated defects.** A guardrail like *"change only the values, never which fields are
written"* governs exactly that axis. An overflow, a crash, a parser that rejects valid input,
a false claim in a doc comment — none of those are the axis the guardrail names, so it does
not authorise deferring them. Read a guardrail for what it actually constrains, and be
suspicious when your reading of one turns out to be the reading that avoids work: **a defect
found in a file you are already editing is in scope by default.** A plan that genuinely means
"report defects, do not fix them" has to say that about *defects*, not about coverage.

One question settles most cases: *would fixing this change what the gate measures?* If not,
fixing it is not scope creep, and the guardrail is not about it.

**If the gate fails:** treat it as a **defect class sampled once**, not a point defect.
Detection at a gate is goal-scoped while repair defaults to instance-scoped, so a class with
N instances costs about N rounds, each looking like fresh news.

1. **Classify every finding** as **Critical**, **Important**, or **Suggestion** — the same
   scale the review tiers use, so a gate finding and a review finding are graded once.
2. **Diagnose evidence-first, then name the set.** Invoke `no-fafo-debugging` **first** — this
   is the most fix-prone moment in the workflow, and the order is not decorative: a set
   derived from a wrong root cause is a *wrong set*, so the sweep would then run confidently
   over the wrong population and report green. Only then name the set the finding quantifies
   over. **Derive it** from the failing task's `Scope:` field where it declares one — a
   starting point, not an authority. **When no `Scope:` exists,
   or the finding escapes it, enumerate the set now**: run the sweep the check should have
   been (grep the defect's distinguishing string, list every sibling of the failing
   artifact's kind, list every caller of the changed symbol) and **write the command down in
   the gate report**, so the next round argues with a command rather than a recollection. If
   that sweep finds members the `Scope:` did not, the plan's `Scope:` line is wrong — fix it
   as part of the repair.
3. **Add a test covering the set**, not the one file that failed, and fix **every member the
   sweep returns in this round**.
4. **Re-run the task's Red-Green loop**, then re-verify narrowly plus the sweep.

**Remediation budget — default 2 rounds per gate.** A plan may override it. Count the rounds
and report the count; an uncounted loop is how a gate reaches its fourth round with nobody
noticing the third. On exhaustion, escalate with the residual list — a documented Stop
condition, not a licence to keep looping.

The full procedure — how to derive the set, when the task's `Scope:` field is the authority
and when it is wrong, and what each severity obliges: `references/gate-failure-procedure.md`.

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
  `dispatch: <the gate report's dispatched-vs-inline line, verbatim>`
  `review: <the gate report's per-tier reviewer/diff line, verbatim>`
  **Decisions in force:** <the DEC/GDEC IDs still binding, plus any Supersedes
  citation raised in this stage and not yet recorded>
  ```

  The decisions line is not redundant with the plan's `## Decisions in force`: a constraint
  that surfaced mid-stage exists nowhere else, and one absent from the handoff is one the
  next session will not know about. **The dispatch and review lines are carried here for the same reason**, and they earn the
  space: this section tells the executor to discard the context that holds them. The dispatch
  counts can be rebuilt from the trailers, but **the review ledger cannot** — which agent saw which diff exists only in the gate
  report, so a reset without it turns "the stage was reviewed" into a claim with no artifact
  behind it. Copy the two lines the gate already produced; do not re-derive them. Committed
  with the `"Stage N green"` commit, and kept to a few lines — a briefing, not a log.
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

Mirror execution state to `<repo-root>/.claude/plan-progress.json` at **every** transition —
Preflight, each task start, each gate run, close-out — and **delete it when close-out
finishes**. Write the whole file each time; never patch it. It is ephemeral session state:
never commit it, and ensure `.claude/plan-progress.json` is gitignored during the git
bootstrap.

Schema, the per-phase field table, `remediation_round`, and the one-time statusline wiring:
`references/progress-state-file.md`.

---

## Stop conditions

Stop immediately and escalate to the user when:

- Preflight fails
- A task exhausts its Red-Green cycle budget
- A stage gate's remediation budget is exhausted — the responsible task(s), or the defect class they belong to, were re-run and Critical findings remain (escalate with the residual list)
- The plan contains an instruction you don't understand
- A test cannot be run (missing fixture, unreachable service, unclear invocation)
- **A mandated verification or dispatch cannot be performed** — dispatch is unavailable or disallowed and Preflight's dispatch roster is non-empty (§ Dispatch roster and capability probe), or a review the gate requires cannot be run. Substituting inline execution, or proceeding unreviewed, is not a documented resolution; asking is
- Verifying the test requires modifying shared infrastructure (production DB, live service) — see Safety rails below

**Never guess through a stop condition.** Ask.

The dispatch entry restores a symmetry the list already had and had lost. "A test cannot be run" blocks, because an unrunnable check is not a passed check — and a mandated dispatch or review that cannot be run is the same fact about a different mechanism. What made the asymmetry survive is that the substitute looks like the work: an inlined task produces the same diff, and an unreviewed gate reads exactly like a reviewed one. That is the reason it needs a rule rather than judgment — the failure is invisible in the artifact, so nothing downstream will raise it. **The choice belongs to the user**: they can enable dispatch, re-mark the tasks `Parallel: NO` through `planning-projects`, or accept inline execution knowingly. What the executor may not do is make that call silently on their behalf, which is exactly what happened in the incident this rule comes from.

## When to revisit earlier steps

Return to Phase 1 (critique) when:

- The user updates the plan after feedback — treat the new version as a fresh plan and re-critique
- A stage gate failure reveals a fundamental gap in the plan (e.g., missing task, wrong dependency) — stop execution, return to `planning-projects` to revise

## Phase Close-out — After the last stage

When every stage is green:

1. Run the plan's **sole plan-scope pass** — the only `clean` and the only full expensive-suite run in the whole execution (intermediate gates ran stage-scope), including any quarantined slow tests. Use the plan's declared `plan-scope:` command when present. If the final stage gate already ran this exact plan-scope pass and no commits landed after it, that pass counts — don't run it twice.
2. Run any integration / e2e tests the plan flagged
3. **Independent evaluator pass.** **Whether it runs comes from § Review scope** — never at `none`; at `light` and `standard` when the final gate carries a `(judgment)` check; always at `high`. When it runs, dispatch a fresh evaluator briefed ONLY with the plan's stated goals, the per-stage Goal lines and the gate criteria — never the implementation transcript. It verifies the goal against the artifact itself and grades every finding Blocking / Material / Minor, as at Step 3.5. **A Blocking finding is the stop condition** — surface it before merge. A FAIL carrying only **Material** findings is *not* a merge blocker: record each Material finding to the `backlog`, then report the residual list and those IDs to the user and let them decide. The distinction matters because "the evaluator returned no adverse findings" is not a reachable state for a fresh reader of a real artifact; treating any FAIL as blocking is what makes the final gate oscillate. Where the tier mandates it, skip only on an **evidenced** user opt-out (§ Review scope); where the tier does not, report it as scope rather than as an opt-out.
4. **Bump versions for what changed**, as part of close-out rather than a follow-up.
   Breaking/removed → major; new capability → minor; fix/docs/internal → patch. Bump it
   wherever the project records it **and every place that mirrors it** — grep the old version
   string to find them. In this repo that is a plugin's `.claude-plugin/plugin.json` **and**
   its root `.claude-plugin/marketplace.json` entry, plus `metadata.version` when the
   marketplace set itself changed. Add a `CHANGELOG.md` entry if the project keeps one, and
   commit the bumps (`"chore: bump <component> to <version>"`). When the right bump is
   genuinely ambiguous, state your call and let the user override — don't silently skip.
5. Update the plan document with a closing note: append `**Completed:** YYYY-MM-DD — commits: <list>` at the end. Also confirm every task's `- **Status:**` is `[x]` (any remaining `[ ]` task was not executed — either finish it or note it as deferred). The close-out line + all-`[x]` statuses make the plan's done-state unambiguous for any downstream reader.
6. **Reconcile the backlog.** Scan the plan for `Closes BL-NNN` references and any tasks that implemented an open backlog item. Call the `backlog` skill (`remove`) with that ID list. Reference each removed ID in the close-out commit message.
7. **Reconcile the decisions register**, in both directions:
   - **Supersedes citations → record them.** For each `Supersedes DEC-NNN` on a task, call
     `decisions supersede`. Until this runs the register still asserts a constraint the code
     no longer honors, and the *next* plan will be written against it.
   - **New constraints created → record them.** Execution discovers what planning couldn't:
     an approach that turned out blocked, a platform limit, a cost knowingly accepted to get
     a stage green. Call `decisions add` with the reason — constraint, evidence, rejected
     alternative, accepted cost. If you cannot name a rejected alternative or a cost, it
     probably wasn't a decision; don't pad the register.
   - Reference the recorded IDs in the close-out report and commit message.

8. **Audit workflow specs.** If `docs/workflows/` exists, call the `workflow-spec` skill (`audit`) against the plan's cumulative diff. For every WF-ID the plan declared (`Changes WF-NNN`, `Removes WF-NNN`), verify the corresponding block was updated or deleted in this branch. **Any `Removed` finding the audit reports that the plan did not declare is a regression — stop and escalate before merge.** Surface every `Moved`/`Modified` finding for explicit user review.
9. Report to the user with:
   - Stages completed
   - Total commits
   - Version bumps applied (component → old → new)
   - Plan location for future reference
   - Reviews that ran: each tier, the agent that ran it, and the diff range it saw — or, for a tier that did not run, the evidenced opt-out that excused it. Same requirement as the stage gate's, at plan scope: a close-out that says the work was reviewed without saying by what, over what, is the claim this list exists to stop being unfalsifiable.
   - **Dispatch reconciled against Preflight's roster, plan-wide.** Read the trailers across the whole plan (`git log --format='%h %(trailers:key=Executor,valueonly)' <plan-base>..HEAD`) and state `dispatch: <n> of <total> rostered tasks dispatched`, naming every inlined `Parallel: YES` task with its reason. Per-stage gates each reconcile their own slice, so aggregate coverage holds **only if every stage gate ran and reported**. The roster is declared once for the whole plan; this is where it is answered.
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
- Respect the gate's **remediation budget** too — counted and reported, with the default stated once at Step 3.5 rather than restated here; a gate passes when no Critical remains and every Important is fixed or recorded, never when the detector finally goes quiet
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

Beck (TDD's red-green cycle), Cooper (phase gates), Gawande (preflight as a hard gate),
Torvalds and *The Pragmatic Programmer* (commit per logical change), and Anthropic's
harness-design work (independent evaluators, structured context handoffs). Full list with
what each one is load-bearing for: `references/sources.md`.
## Integration

- **planning-projects** — produces the plan this skill consumes; for decomposed big projects it produces a master plan plus sub-plans (format: its `references/master-plan-format.md`), which this skill executes per the Master plans section — sub-plans in register order, cross-plan gates on each completion, version bumps deferred to the master close-out
- **dispatching-parallel-agents** — invoked for every `Parallel: YES` task; a file conflict serializes the dispatches rather than cancelling one (Step 3.2). Its `references/stack-routing.md` is the shared table Step 3.2 also consults to delegate independent, output-heavy `Parallel: NO` tasks to a stack-matched subagent (e.g. `rust-expert`, `testing-expert`) instead of running them inline
- **backlog** — invoked to `add` deferred work (skipped task, scope creep at a gate) and to `remove` items the plan closed in Phase Close-out
- **decisions** — the architectural-decision register, consumed on three paths: `relevant` at Preflight (re-scan and diff against the plan's recorded `## Decisions in force`, since the register accretes between planning and execution), the conformance check at every stage gate (a contradiction without a `Supersedes` citation is a gate failure), and `supersede` / `add` at close-out (recording overrides the plan declared, and constraints execution itself discovered)
- **workflow-spec** — invoked in Phase Close-out to `audit` the cumulative diff against `docs/workflows/`; undeclared `Removed` findings block the merge
- **goal-evaluator agent** — the *black-box* gate/close-out evaluator: a fresh agent briefed ONLY with the stage/plan goals and gate criteria, never the implementation transcript. Verifies the *goal* is met against the artifact. **When it runs is the declared review scope's call** (§ Review scope): never at `none`, at `light`/`standard` wherever a gate carries a `(judgment)` check, always at `high` and at that tier's Phase Close-out. Where the tier mandates it, skip only on an evidenced user opt-out (quoted, per § Review opt-out) or when every check is a command.
- **git-github:code-reviewer agent** — the *white-box* review (read-only): reads the actual diff and returns a Critical / Important / Suggestion triage. Runs in two tiers, **each gated by the declared review scope** (§ Review scope, which is the authority on when either fires) — **Tier 1** per green task, at `high` only or on a task's `Review: required` (Step 3.3 rule 6; a Critical blocks the task within its Red-Green cycle budget), and **Tier 2** at `light` once over the whole plan diff, at `standard`/`high` per stage gate (Step 3.5; a Critical fails the gate, and an Important leaves the gate fixed or recorded to the `backlog` per the exit criterion — never merely mentioned). Distinct axis from the goal-evaluator: *code quality* vs *goal attainment*. Shipped by the `git-github` plugin.
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

**Review opt-out.** A review **the declared tier mandates** is default-on; a tier that does
not mandate one is the machinery scaling as designed, reported as scope and never as an
opt-out (§ Review scope). **Two reasons excuse a mandated review, and the list
is closed at two: an evidenced user opt-out, and a trivial/non-code diff.** A reviewer that
cannot be dispatched is not a third: that is the **Stop condition for a mandated review**
that cannot be run, on the same ground as an unrunnable test. An unrun review is not a
passed review, and it leaves an artifact indistinguishable from a reviewed one — which is
why the resolution is the user's to choose, not the executor's to assume.

**An opt-out is evidenced, not asserted.** A trivial/non-code diff carries its own evidence,
checkable against the diff. A user opt-out is a claim about something outside the artifact,
so recording it means **quoting the user's own words**, with where they were said:

```
Review skipped — user opt-out, Preflight: "don't bother with the reviewer on this one"
```

A `Review: skip` annotation **counts as an opt-out when Preflight's snapshot lists it** — the
snapshot is what makes it evidence, because the executor writes to the plan file throughout the run, so an annotation
read at skip time proves nothing about who put it there. An annotation missing from that
snapshot is an executor-authored note. Cite the snapshot line, not the task line.

**Executor judgment is not an opt-out.** *"I judged the review unnecessary"*, *"the diff
looked small"* are the executor deciding on the user's behalf and recording it as though the
user had. A skip reported without a quote or a cited snapshot is an **unevidenced skip**: it
reads downstream as a review that did not happen, because that is what it is.

Why the snapshot rather than the task line is the evidence, and the full tier table:
`references/review-scope.md`.
