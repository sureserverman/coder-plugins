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

**Exception — master plans.** A `*-master-plan.md`, or a first heading of `# Master Plan:`
(format: `../planning-projects/references/master-plan-format.md`). It deliberately has no
Preflight, Stages, or Tasks — do NOT reject it; execute it per **Master plans** below.

**Exception — light plans.** A `*-light-plan.md`, or `# Light Plan:` (format:
`../planning-projects/references/light-plan-format.md`). It deliberately has no Research
Summary, no Preflight, and no Risk / Rollback / Blocks / Parallel fields — a single stage of
2–5 Status-carrying tasks and one gate. Do NOT reject it for those; execute it per **Light
plans** below.

---

## Reference map

The trunk carries what fires on every run — every rule that must bind, whole. These load when
their condition is met: read the one you need rather than working from memory.

| Read this | When |
|---|---|
| `references/master-plans.md` | the plan file is a `*-master-plan.md` |
| `references/light-plans.md` | the plan file is a `*-light-plan.md` |
| `references/review-scope.md` | declaring the tier at Preflight, or resolving how format and tier compose — **the authority on both, and on the opt-out rules** |
| `references/preflight-checks.md` | running Preflight — the procedure for each check, and the amendment protocol |
| `references/dispatch-fidelity.md` | the roster, probe or `Review: skip` snapshot needs justifying rather than just following |
| `references/task-execution.md` | dispatching or inlining a task, writing its test, or running Tier 1 |
| `references/bug-is-a-class.md` | a bug surfaced and the set it belongs to has to be named |
| `references/stage-gate.md` | running a stage gate — report shapes, verify hooks, evaluator, Tier 2, dispositions |
| `references/gate-failure-procedure.md` | a stage gate has failed |
| `references/close-out.md` | every stage is green — the close-out procedure |
| `references/progress-state-file.md` | writing `.claude/plan-progress.json`, or wiring the statusline |
| `references/integration.md` | routing to another skill or agent, or citing the opt-out rules |
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
task runs **inline** (no fan-out); the format sets a **whole-diff** review shape in place of
per-task passes — **that single pre-gate review IS the light plan's Tier-2, so do not also
run a separate stage-gate Tier-2 pass**; and close-out applies a single stated version bump.
**How many passes actually run is the declared tier's call, not the format's**
(`references/review-scope.md`): `none` runs none, `light` and `standard` run that one, `high`
adds a second pass and Tier-1 even here, on the risk-listed tasks its declaration names.

Everything else is unchanged — Status flips, a commit per green task, the cycle budget, the
Stop conditions, honest gates.

Full deltas: `references/light-plans.md`.

---

## Checklist

Create a task for each, work them in order:

1. **Load and critique the plan** — raise concerns before starting
2. **Run Preflight** — verify every check; stop on failure
3. **For each stage, in order:**
   a. Dispatch `Parallel: YES` tasks via `dispatching-parallel-agents`; work `Parallel: NO` tasks in the main session
   b. Drive each task through its Red-Green loop
   c. Run the stage gate; stop if it fails
4. **After all stages green:** hand off for review and merge (Phase Close-out)

---

## Run to completion — don't stop until you have to

Once Preflight passes, **drive the plan straight through to close-out.** Stage boundaries
are checkpoints, not approval gates: commit a passed gate and start the next stage without
asking "should I continue?" The plan is the approval, and burning a turn to ask permission
between green stages is the failure mode this skill exists to prevent. Keep going through a
green task, a passed gate, a failed cycle that still has budget, and any surprise you can
resolve from the plan plus evidence.

**Only the documented Stop conditions halt execution.** Everything else is work to push
through. When you do stop, it is because continuing would be guessing or unsafe — say which,
with evidence, and what you need to resume. The context-reset guidance is an efficiency
tactic for very large plans, **not** a licence to stop early: prefer a fresh session over a
*degraded* one, never over *finishing the work*.

**Never end a turn on an announcement.** *"Starting Stage 3."* as a turn's last words has not
started Stage 3 — it hands the turn back on a promise, and the user has to ask again for work
already authorized. The tool call opening the announced work — a stage, a task, or
anything else this skill has you announce — goes in the **same turn** as the sentence
announcing it, or instead of it where the sentence was yours to choose. An announcement this
skill mandates is still made — in the same turn as the call, never in place of it. This is
run-to-completion at the granularity of a single turn.

---

## The plan is the authorization — dispatch without a confirmation turn

**A dispatch this plan mandates is a direct order, and you execute it without asking.** That
covers a `Parallel: YES` task, and — **each on the conditions `references/review-scope.md`
already sets for it, never beyond them** — a review the declared tier calls for, an evaluator
the tier funds at a `(judgment)` gate, and the Preflight probe on a non-empty roster at
`standard` or `high`. The rule removes the *asking*, never the *conditions*. Do not spend a
turn on *"shall I fan these out?"* or *"should I dispatch the reviewer?"* — the answer was
given when the plan was handed to you.

**Why this needs saying at all.** A session usually carries a standing caution of roughly the
form *"do not call the Agent tool unless the user requested it"*. That caution is
**conditional, not absolute**, and a plan whose execution model names dispatch points is the
condition being met: **approving the plan WAS the request.**

**The bound, which carries equal weight.** With **no plan in play and no mandate**, the
caution stands and you ask. This rule deletes a confirmation turn where a plan already
authorized the work; it does not authorize dispatch in general, and it never makes a dispatch
the *tier* did not fund (`references/review-scope.md`) suddenly due. A rule stated without its
bound gets over-corrected into its own inverse, which is not hypothetical: the recorded
response to this failure was *"standing rule, no exceptions: I won't dispatch unless you
explicitly ask"* — inverting the rule rather than scoping it, and stripping the same reviews
for the opposite reason.

**What still halts a dispatch**, unchanged: the probe fails or dispatch is unavailable (a
Preflight failure and a documented Stop condition — the user chooses, and inline substitution
is not the executor's call to make), or a `requires_enablement` component cannot be
lazy-loaded. *"I wasn't sure whether to fan out"* has never been on that list.

Why the incident that produced this rule was invisible while it happened:
`references/dispatch-fidelity.md`.

---

## A bug found during execution is a class — sweep it, fix every instance

**Any defect you find during a run is one sample of a class until a command proves
otherwise.** This fires wherever a bug surfaces: a RED test inside a Red-Green loop, a
finding from either review tier, an evaluator finding, a failed gate check, or something you
simply notice while editing a file. It is **not** scoped to gates — the gate-failure branch
is one caller of this rule, not its home.

When you find one:

1. **Diagnose evidence-first.** Invoke `no-fafo-debugging` before generalizing. A set derived
   from a wrong root cause is a *wrong set*, swept confidently, reporting green.
2. **Name the set, and enumerate it with a command** — grep the defect's distinguishing
   string, list every sibling of the failing artifact's kind, list every caller of the changed
   symbol. The task's `Scope:` field is a starting point, not an authority. **When no `Scope:`
   exists, you still enumerate**; an undeclared set is still a set.
3. **Fix every member the sweep returns, in the same change** — not the instance that
   happened to surface.
4. **Write the command down** — in the commit body, or in the gate report when a gate is what
   surfaced the bug.

**The whole project is the search space, not the plan's blast radius.** A sibling instance
living in a file this plan never touches is the same defect; "out of scope" describes a plan's
*subject matter*, never a defect's *reach*. **Where the sweep stops:** it covers the defect's
own predicate — whatever makes an instance an instance — and nothing wider; it is not a licence
to refactor whatever lives nearby. **A class you cannot express as a command is a class you
have not named yet: disclose the limit**, fix the members you can identify, and say what you
were unable to sweep. **It costs a command, never a dispatch** (DEC-010), so it belongs with
the untiered mandates and runs at **every** review tier, including `none`.

Where the sweep stops, and the one dispatch-shaped consequence when it widens the diff into a
risk-listed area: `references/bug-is-a-class.md`.

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

   **Advisory on an existing plan, mandatory on a new one** — note a flagged existing plan
   and execute it anyway; `planning-projects` may not present a *newly authored* plan that
   fails. Say which case you are in. The `(judgment)` marker is the sanctioned escape hatch:
   a check that genuinely needs a reader carries it and routes to the evaluator at the gate.

5. **Read the plan's `## Decisions in force`** — the constraints it was written under,
   carried into the file so a session that never reads the register still implements under
   them. Note which tasks carry `Honors DEC-NNN` and which carry `Supersedes …` (a deliberate
   override you record at close-out). **A plan with no such section is not a plan with no
   decisions** — treat its absence as *"not recorded"*, never *"none apply"*, and run the
   Preflight scan.

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
- **Every gate selector collects something** — probed with `--collect-only`, not assumed; see below
- **Calibration re-check** — review-scope, test-scope commands and roster recomputed from today's rules rather than trusted from the plan file; see below
- **The dispatch roster is declared** — every `Parallel: YES` task, with its routed agent type; see below
- **Pre-existing `Review: skip` annotations are recorded** — the list, at the commit the run starts from; see below
- **Review scope is declared** — which tier the plan's diff warrants, and why; see below
- **Dispatch works in this session** — probed, not assumed; only when the roster is non-empty **and** the declared tier is `standard` or `high`; see below

**If any check fails, stop and report which check failed and how it failed.** Do not
proceed to Stage 1.

The procedure for each — the steps, the worked examples, the incidents behind them:
`references/preflight-checks.md`.

### Decisions re-check (the plan's snapshot can be stale)

The register **accretes between planning and execution**, so Preflight does not trust the
plan's recorded section: re-run the `decisions` skill's `relevant` operation for this project
and its stacks, and diff it against the plan's `## Decisions in force`. A **new entry in
scope** or **an entry the plan honors that is now superseded** is surfaced before Stage 1 — it
may invalidate a task. **Unchanged** → say so in one line. A plan with no section gets the
scan result as its working set: absence is not exemption.

A report, not a stop condition — unless the diff invalidates a task outright, in which case it
is a plan defect and returns to `planning-projects` (§ When to revisit earlier steps).

### Calibration re-check (the plan's ceremony can be stale)

A plan's Preflight froze its review-scope tier, its test-scope commands and its roster at
authoring time, and **the calibration references accrete too**. Recompute all three from
today's rules (`references/review-scope.md`,
`../planning-projects/references/test-scope-tiers.md`, and the plan's own `Parallel:` fields)
and diff. **Unchanged** → one line. **Changed** → amend under the protocol, stating both
values (`review-scope: high — recalibrated to bind tasks 1.1, 1.3; as authored, bound all
12`). No declaration at all → recompute and record.

**What is never recomputed: the plan's facts.** Tasks, their `Test:` fields, gate checks'
substance, invariants, `Scope:` sets. Recalibration changes only what the run *costs*; a rule
that let Preflight rewrite what a task must prove would be re-planning without the user in the
room.

### Amending authored ceremony

An amendment is legal only when all three hold: **unexecuted checks only** (never a passed
gate's or an `[x]` task's — that edits the evidence), **the annotation cites the authorizing
rule**, and **the was-value survives**. Amending a check to make a *failing* gate pass is the
gate-failure procedure, not recalibration. Protocol:
`references/preflight-checks.md`.

### Gate-selector probe (a gate that cannot pass is a plan defect, not a gate failure)

For every gate check invoking pytest whose target file exists now, run
`pytest --collect-only -q <the check's selector>`. **Collects ≥1** → proceed. **Collects 0 and
no task creates that test** (or the target file does not exist and no task creates it) →
**plan defect**: stop and return it to `planning-projects` (§ When to revisit earlier steps).
**Collects 0 but a task's `Test:` builds toward it** → expected; record which task satisfies
it. A **command, not a dispatch**, so it is not tier-gated (DEC-010); its position, per
DEC-017, is once at Preflight, never per stage.

### Git bootstrap (hard prerequisite for commit-per-task)

Every task commits its own work (the Red-Green loop's rule 7), so a working
repo must exist before Stage 1. Not a repo → `git init`, a sane `.gitignore`, an initial
commit so the first task has a parent, then *offer* a remote — never push a repo public
without consent. On `main`/`master` → do NOT execute here; branch or worktree first (Safety
rails). Dirty with unrelated changes → surface them; don't sweep them into the first task's
commit. A missing remote is **not** a stop condition; only an un-initializable repo blocks.
Decision tree: `references/preflight-checks.md`.

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

2. **Probe the capability — only if the roster is non-empty and the tier is `standard` or
   `high`** (`references/review-scope.md` gates this like any other dispatch). Dispatch one
   throwaway `general-purpose` subagent whose whole task is to reply `DISPATCH-OK`, and
   confirm it came back. Record the skip with its reason — `probe: skipped — empty roster`,
   or `probe: skipped — tier light`.

3. **Snapshot the `Review: skip` annotations** against the commit the run starts from
   (`Review: skip annotations at <base-sha> — <n> task(s): <Task N.M>, …`; `0 tasks` when
   there are none). The executor writes to the plan file throughout the run, so only an
   annotation in this snapshot is evidence the *user* authored it. Cite the snapshot when you
   skip, not the task line.

**A failed probe is a Preflight failure.** When dispatch is unavailable or disallowed in
this session and the roster lists at least one task, **Preflight fails and you stop** — the
user decides whether to enable it, re-plan those tasks as `Parallel: NO`, or accept inline
execution knowingly. Substituting inline execution on your own authority is not a
resolution; it takes a decision that belongs to the user and makes it silently.

Why each of these three exists, and why the probe's condition is a conjunction rather than a
replacement: `references/dispatch-fidelity.md`.

### Review scope — the machinery scales to the change

**Declare a tier at Preflight and restate it in every gate report** (`review-scope: light —
prose edits to 3 skill files`). An undeclared run is `standard`. Pick it once, from the
plan's **cumulative diff**, not per task. **The declaration is what makes the choice
reviewable** — downgrading silently and openly produce the same diff.

**What the tier gates** is both review tiers, the gate evaluator, the close-out evaluator and
`high`'s second pass. What it does **not** gate is the dispatch roster, the executor trailer,
the dispatched-vs-inline reconciliation, honest-gates disclosure, the class sweep every
surfaced bug requires, and the plan's own tests and gate checks: those run at every tier
including `none`. The line is cost — a mandate costing an
agent dispatch is tiered, a mandate costing a line of text is not.

**The format decides the review's SHAPE. The tier decides its DEPTH.** **Resolve a
disagreement by the risk floor**, not by taking the lighter or the heavier option: touching a
risk-listed area sets `high` whatever the size, and **size alone never escalates**. A tier is
a floor, not a ceiling — escalate mid-plan when the diff turns out riskier than it looked and
say so in the gate report; never quietly de-escalate.

`references/review-scope.md` is the authority — the tier table, which tasks a `high`
declaration binds, the per-sub-plan rule for masters, and the opt-out rules.

## Phase 3 — Stage execution

For each stage in order:

### Step 3.1 — Identify what can run now

Scan the stage's tasks. A task is **dispatchable** when every task in its `Depends on` list is green. At stage start, this is every task whose `Depends on` is either empty or lists only tasks from already-green prior stages.

### Step 3.2 — Split by parallelism

- Tasks with `Parallel: YES` and no file conflicts with another ready task → hand to `dispatching-parallel-agents`, concurrently
- Tasks with `Parallel: YES` that modify files another ready task modifies → still dispatched, one after another
- Tasks with `Parallel: NO` → work in the main session, always

**File-conflict check:** before dispatching, verify no two parallel tasks edit the same file.
If they do, **serialize the dispatches — do not inline either one.** A file conflict says
these two cannot run at the same moment, which is a different claim from "this task need not
go to a subagent"; the conflicting task is dispatched on its own once the first returns.

**A `Parallel: NO` task runs in the main session.** The plan's `Parallel` field is the whole
decision: `YES` obligates a dispatch, `NO` means inline. There is no executor discretion to
hand a sequential task to a subagent anyway — and none, in the other direction, to check
first: a `YES` is dispatched **without asking**
(§ The plan is the authorization — dispatch without a confirmation turn).

**If a `Parallel: YES` task ends up inline, that is a deviation the user authorised.** An
unavailable dispatch *raises* the Stop condition, it does not resolve it — the choice that
follows is the user's. *"It seemed easier inline"* and *"I judged it unnecessary"* are not on
that list. Run it, say so in the gate report's dispatch line with the reason, and let
the trailer record `Executor: inline (dispatch failed)` or `Executor: inline (user
authorised)` — a bare `Executor: inline` on a task the plan marked `YES` is the shape that
hides a silent downgrade.

**If the matched capability's plugin isn't enabled**, don't fall through to `general-purpose`
with no domain knowledge — resolve it from disk per that same routing reference. A component
flagged `requires_enablement` (hooks / MCP) can't be lazy-loaded: stop and ask the user to
enable that plugin.

Why there is no third execution mode: `references/task-execution.md`.

### Step 3.3 — Red-Green loop (per task)

Every task follows this loop. **The test is written first and must go RED for the right
reason before any implementation is attempted.** No task is "done" until its test is green.

```
 Write the test → Run it → RED for the named reason?
                              │              │
                              no            yes
                              ↓              ↓
              the TEST is wrong,        Implement → Test → Pass? ──yes──► Next task
              not the code —                        │
              repair and re-run                     no
              (not an implementation                ↓
               cycle)                            Diagnose → Fix → Retest
                                                    (max `Red-Green max cycles` per task)
```

A test written after the implementation cannot distinguish "the behavior is missing" from "my
test is wrong" — both print RED. **Repairing a wrong RED is not an implementation cycle** and
does not consume the budget, which bounds failed *fix hypotheses about the product*; repairs
are still bounded by honesty — never weaken an assertion to reach green (`honest-gates`).
**When the plan names a `pytest <file> -k <expr>` selector, name the tests to match it as you
write them.** The measured incident behind all three: `references/task-execution.md`.

**Loop rules:**

1. **One fix per cycle.** Don't shotgun. Isolate, fix that one thing, retest.
2. **Diagnose before fixing, then fix the class.** Read the error, form a hypothesis, confirm it against the code, then write the fix. On the **second** RED cycle for a task, stop improvising and invoke `no-fafo-debugging`: one failed targeted fix is bad luck, two says the hypothesis is wrong rather than the patch. Once the diagnosis holds, the repair is class-scoped — **A bug found during execution is a class** applies here exactly as it does at a gate, and a RED test is the earliest, cheapest place it fires.
3. **Respect the cycle budget** (plan-set, default 3). On exhaustion stop and escalate — three failed targeted fixes means the approach is wrong, not the implementation. If the user skips rather than re-plans, `backlog add` the task; don't silently drop it.
4. **Never skip the test — and never widen it into a regression sweep.** The task's Test field is the gate; "it looks right" is not green. It is also the **whole** of the task's testing: **do not run the plan's `stage-scope:` command inside a task**. The stage gate runs it once, at the gate. Widening within the task's own subject — the whole test file instead of one filter, or the class a fix touched — is task-scope and needs no permission; a genuine class sweep is likewise untouched.
5. **Flip the task's Status to `[x]` the moment its test is green**, in the same change as the work — except for a plan the repo does not contain, where rule 7 says what happens instead. It is the authoritative done-marker; downstream tools (`portfolio unify`) read it rather than guessing from gates or git. **The flip records that the task is done, never who did it** — an inlined task and a dispatched one write the identical `[x]`, so rule 7's trailer is the only artifact carrying that.
6. **Quick review gate (Tier 1) — `high` tier's risk-listed tasks and `Review: required` tasks only.** Whether it runs comes from `references/review-scope.md`; do not re-derive it. **At `none`, `light` and `standard` there is no per-task review**: a green task goes straight to its commit, and the stage's Tier-2 pass is where its diff is read. When it does run: after the test is green and Status is flipped but **before** the commit, dispatch `git-github:code-reviewer` (read-only) as a **fresh dispatch seeing only the task diff** — never the executor self-reviewing. A **Critical is blocking** (fix inline, sweep its class, re-run at fix-scope, re-dispatch — all against the same cycle budget); **Important / Suggestion are advisory**, appended to the plan as `**Review notes (Task N.M):** …` for the gate's deep review to triage. Trivial/non-code diffs skip it — but a docs change *asserting* a command, flag, exit code, default or path is not trivial. Full machinery: `references/task-execution.md`.
7. **Commit after each green task** (`"Stage 2 Task 2.3: parse config entries"`), including the work, any Tier-1 fixes, and — where this repo contains the plan — the flipped `Status: [x]`. The per-task commit is the unit of record and what makes a mid-plan stop recoverable. A passed gate adds its own `"Stage N green"` commit: keep **both** granularities, never collapse to one.

   **The plan file may not live in the repo you are committing to.** A plan can sit outside
   the repo it plans — the portfolio convention keeps it in the vault — so **edit the plan at
   its absolute path and run every git command from the repo root**. Never `cd` to the plan's
   directory first: the vault is not a git repository, so a directory change chained ahead of
   `git add`/`git commit` dies on `fatal: not a git repository`, the plan edit already
   landed. A vault-resident plan's `Status: [x]` flip therefore rides no commit
   (`references/task-execution.md`).

   **Every per-task commit ends with an executor trailer** — the last line of the message, taking one of these shapes:

   ```
   Executor: inline
   Executor: dispatched — <subagent_type>
   Executor: dispatched — <subagent_type>, <subagent_type>    (one task, several agents)
   Executor: inline (dispatch failed)                          (the body says why)
   Executor: inline (user authorised)                          (dispatch was available)
   ```

   **Keep the trailer to one physical line** — an unindented wrap ends the trailer block, so
   the trailer vanishes from every `%(trailers:…)` query with no error at all. Put the reason
   in the body; keep the trailer bare. **Name the actual `subagent_type` that ran the work**,
   not the routing table's suggestion, and say so when a dispatch failed and finished inline.
   **A trailer that misstates who ran the task is worse than none** — it converts a visible
   gap into a false record. A routed agent that cannot commit does not become an inline task:
   the trailer records who did the work, not who typed `git commit`
   (`references/task-execution.md`, DEC-015).

### Step 3.4 — Propagate unblock

When a task finishes green, scan its `Blocks` field. For each blocked task, check whether ALL of its `Depends on` items are now green. If yes, it becomes dispatchable — return to Step 3.1.

### Step 3.5 — Stage gate

**These four bind every gate**, restated rather than cited — BL-083 measured the pointer
unread:

> **A gate is green only when its real command ran in the current environment and actually
> passed. Nothing else counts as green.** **If you cannot make the real check run here, the
> gate is BLOCKED, not green** — one that ran and failed is RED, and takes the gate-failure
> procedure below. **Violating the letter of a gate is violating its spirit.** **And a
> sentence asserting behavior is itself a claim that something was verified** — cite the
> `file:line`. **Never collapse BLOCKED into GREEN.** **A gate whose commands ran over
> uncommitted edits proved nothing about what is recorded** — commit first, then run it.
> A BLOCKED gate takes neither branch: stop on it, name the blocker and the exact
> command that cannot run, try to unblock it, and escalate. Prohibitions: `honest-gates`.

When every task in the stage is green, run the stage gate:

- Each gate check has a specific pass criterion (a command output, a test result, a manual verification)
- Run them in order; stop at the first failure
- **Regressions check runs at stage-scope on intermediate gates:** cheap host-side checks in full, expensive suites (device/instrumented/e2e) restricted to the modules the stage's commits touched — never `clean`. Use the plan's declared `stage-scope:` command when its Preflight carries a "Test-scope commands" block; when the full suite is cheap (<~5 min), just run it in full. Policy: `../planning-projects/references/test-scope-tiers.md`.
- **The final stage's gate runs at plan-scope**, together with close-out — the plan's one full clean pass.
- A scoped gate report states what scope actually ran (honest-gates disclosure) — e.g. "gate green — stage-scope: `:features` instrumented + full `check`."
- **The gate report states the stage's dispatched-vs-inline counts, and a reason for every inlined `Parallel: YES` task** — read off the executor trailers rather than from memory, and reconciled against the roster Preflight declared. A stage that dispatched everything it marked says `dispatch: 4 of 4` rather than saying nothing, so silence never has to be interpreted. **An empty trailer value is `unknown`, never `inline`.**
- **The gate report names every review that ran, the agent that ran it, and the diff it saw** — and, for one that did not, which of the **three** reasons applies: the declared tier never mandated it (a *scope* statement, needing no excuse), or, where the tier did mandate it, an evidenced opt-out or a trivial/non-code diff. Do not report a tier-scoped absence as an opt-out; that is how a skipped mandate hides inside a legitimate tier. Name the agent by a type dispatch can actually take — `goal-evaluator` is a **role**, not a registered agent.
  **A mandated review the executor ran itself is a substitution, not a review**, legal only
  where the **user** authorised it — an undispatchable reviewer is a Stop condition, not a
  licence. The review line records it, quoting them; **with no recorded reason the gate
  fails.** Bound (DEC-014): only reviews the declared tier mandates, never a dispatch beyond
  it — and within it, the mandate IS the authorization to **dispatch** it.

- **One `ACTION NEEDED:` block, or none** — a report that carries one does not also say it is proceeding. Either the decision blocks the next stage, so say so and stop, or it is not an ask at all (`references/stage-gate.md`).

**Platform stage-verify hook.** After the stage's own gate checks pass, **if the project's
platform ships a stage-verify skill, invoke it as the final gate step** — it proves the stage
on the real artifact, not just the test suite, and a failure there is a gate failure. Android
(a `settings.gradle{,.kts}` / `app/build.gradle{,.kts}` present) → `android-stage-verify`.
Brief it with the gate's tier: stage-scope at an intermediate gate, the full device suite at
the final one — and that run **is** the plan-scope pass's device portion, not an addition to
it. If no matching skill is installed, note it and rely on the regular gate checks; the
absence of a platform verifier is not itself a gate failure.

**A redesign stage carries the design-fidelity hook** in the same position — the
`applying-design-handoff` fidelity verify loop, graded by a separate evaluator. If the tier
does not fund that evaluator, **the hook does not run and the gate report says so**: a
fidelity loop the executor scores itself is worse than none.

Exact report shapes, both hooks' full procedure, the evaluator's briefing, and the Tier-2
pass: `references/stage-gate.md`.

**Independent evaluator for non-command checks.** **Whether it runs comes from
`references/review-scope.md` — do not re-derive it**: never at `none`, at `light` and
`standard` when the gate carries a `(judgment)` check, always at `high`. Run command checks
yourself; dispatch a fresh evaluator for the judgment checks, briefed ONLY with the stage goal
and the gate's pass criteria — never the implementation transcript or your own summary. The
session that wrote the code grades its own work too generously. A declared tier that does not
mandate one is **scope**, reported as such and never as an opt-out; an evaluator that cannot
be dispatched is a Stop condition, not a skip.

**Brief it to grade by severity, not just pass/fail** — **Blocking** (the goal in scope is
not met; the gate does not pass), **Material** (real defect, goal still met — fixed, its
class swept), **Minor** (nit; recorded in the gate report and the handoff note, never
blocking). **Tell it explicitly that a FAIL carrying no Blocking finding is a pass with
recorded residuals**, or it will withhold PASS to seem rigorous and hand the loop an
unsatisfiable condition: a fresh judgment agent reading a real artifact essentially always
finds *something*, so "no adverse findings" is not a reachable state to wait for.

**Deep code review (Tier 2).** Whether it runs, and at what shape, comes from
`references/review-scope.md`. It is a gate criterion, not advisory — a **Critical** here is a
**gate failure**, and every **Important** leaves the gate **fixed** per the exit criterion,
its class swept. **Brief it to audit the stage's behavioral claims as a set**: the stage
view is where a claim that was true when written and false after a later task shows up.

**Decisions-conformance check (gate criterion, not advisory).** Run it at the **final** stage
gate and at close-out, over the plan's cumulative diff — not at every intermediate gate. A
contradiction is a **gate failure wherever it is found** (DEC-003); what is scoped to the
final gate is the *sweep*, not the rule, so an intermediate stage that knowingly lands one
raises it when it sees it. Two legal resolutions, and only two: **re-scope the change**, or
**record a deliberate supersede** (`decisions supersede`) and cite `Supersedes DEC-NNN — <why>`
on the task. "The decision seems outdated" is not a third option. State **which IDs were
checked against which parts of the diff** rather than asserting blanket conformance.

**Exit criterion — what "the gate passed" means.** This governs **every** gate pass, not only
one reached by repairing a failure:

> A gate passes when **no Critical finding remains** and **every Important finding is
> fixed**, its class swept under the class-sweep rule. Suggestions are **recorded in the gate report and carried into the stage handoff
> note**, never blocking.

**Findings are not the only way a gate fails.** The platform stage-verify hook, the
decisions-conformance sweep and an unrecorded review substitution each fail it on their own,
whatever the finding list says.

**A defect is fixed. The backlog is for what is not a defect** — a significant improvement, or
a decision the user must make. A defect you genuinely cannot fix here **escalates with its
blocker named**, and that valve is evidenced, not asserted. It is deliberately *not* "the
detector returned silent": a fresh judgment agent never reports zero findings, so a gate with
that exit condition is not a gate but a loop. Dispositions, the measured backlog-drift
incident, and what a scope guardrail actually bounds: `references/stage-gate.md`.

**If the gate fails:** a gate is one caller of **A bug found during execution is a class**,
and the sharpest one — detection at a gate is goal-scoped while repair defaults to
instance-scoped, so a class with N instances costs about N rounds, each looking like fresh
news.

1. **Classify every finding** as **Critical**, **Important** or **Suggestion** — the same
   scale the review tiers use, so a gate finding and a review finding are graded once.
2. **Run the shared rule: diagnose evidence-first, then name the set.** Invoke
   `no-fafo-debugging` before generalizing; derive the set from the failing task's `Scope:`
   field where it declares one, enumerate it with a command, and **write the command down**
   in the gate report. A set derived from a wrong root cause is a wrong set, swept
   confidently, reporting green.
3. **Add a test covering the set**, not the one file that failed, and fix **every member the
   sweep returns in this round**.
4. **Re-run the task's Red-Green loop**, then re-verify narrowly plus the sweep.

**Remediation budget — default 2 rounds per gate.** A plan may override it. Count the rounds
and report the count. **A re-dispatched review or evaluator is a round** — otherwise the gate
has two counters and only one limit, and fix → re-review → new findings → fix runs
indefinitely because each pass is "just confirming the fix". On exhaustion, escalate with the
residual list — a documented Stop condition, not a licence to keep looping. Full procedure:
`references/gate-failure-procedure.md`.

**If the gate passes** — no Critical remains, every Important is fixed, and no
finding-independent condition is outstanding — mark the
stage complete, append the stage's handoff note to the plan,
commit with `"Stage N green"`, and start Step 3.1 for the next stage. The gate report states
the remediation rounds spent, every Suggestion recorded, and any finding escalated rather than
fixed, so "green" never reads as "nothing was found".

---

## Context resets at stage boundaries

Long executions degrade: a context window filled with stage-1 diagnostics is worse at stage 4
than a fresh one, and automatic compaction loses unpredictable detail. Structured resets beat
degraded context — and the plan file is already the handoff artifact.

- **Stage gates are the reset points.** After each gate passes, append a handoff note to the
  plan file under the stage: the deviations, surprises and decisions a fresh context needs
  that the Status flips don't capture, plus — copied verbatim from the gate report, not
  re-derived — its `dispatch:`, `review:` and `residuals:` lines and the **Decisions in
  force** still binding. **The dispatch and review lines are carried here for the same
  reason**, and they earn the space: the dispatch counts can be rebuilt from the trailers, but
  **the review ledger cannot** — which agent saw which diff exists only in the gate report.
  Committed with the `"Stage N green"` commit, and kept to a few lines — a briefing, not a
  log. Exact shape: `references/stage-gate.md`.
- **Resuming fresh:** a new session (or a post-compaction continuation) picks up the plan by
  reading the Research Summary, the `Status:` flips, and the handoff notes — never by needing
  the prior transcript. If you find yourself unable to continue without the old transcript,
  the handoff notes were too thin; that's the bug to fix.

---

## Progress state file (live statusline bar)

Mirror execution state to `<repo-root>/.claude/plan-progress.json` at **every** transition —
Preflight, each task start, each gate run, close-out — and **delete it when close-out
finishes**. Write the whole file each time; never patch it. It is ephemeral session state:
never commit it, and ensure `.claude/plan-progress.json` is gitignored during the git
bootstrap.

Schema, the per-phase field table, and `remediation_round`:
`references/progress-state-file.md`. Wiring the bar is one command —
`/planning:statusline install` — and is the user's to run, never something to hand-author a
wrapper for.

---

## Stop conditions

Stop immediately and escalate to the user when:

- Preflight fails
- A task exhausts its Red-Green cycle budget
- A stage gate's remediation budget is exhausted — the responsible task(s), or the defect class they belong to, were re-run and Critical findings remain (escalate with the residual list)
- The plan contains an instruction you don't understand
- A test cannot be run (missing fixture, unreachable service, unclear invocation)
- **A mandated verification or dispatch cannot be performed** — dispatch is unavailable or disallowed and Preflight's dispatch roster is non-empty (§ Dispatch roster and capability probe), or a review the gate requires cannot be run. Substituting inline execution, or proceeding unreviewed, is not a documented resolution; asking is
- Verifying the test requires modifying shared infrastructure (production DB, live service) — see Safety rails

**Never guess through a stop condition.** Ask.

**Equally: never ask through a dispatch the plan mandated.** These conditions fire when a
mandated dispatch *cannot be performed*, never when you are merely unsure whether to perform
one — that question is answered by the plan
(§ The plan is the authorization — dispatch without a confirmation turn).

Why an unperformable dispatch needs a rule rather than judgment, and why the choice is the
user's: `references/dispatch-fidelity.md`.

## When to revisit earlier steps

Return to Phase 1 (critique) when:

- The user updates the plan after feedback — treat the new version as a fresh plan and re-critique
- A stage gate failure reveals a fundamental gap in the plan (e.g., missing task, wrong dependency) — stop execution, return to `planning-projects` to revise

## Phase Close-out — After the last stage

When every stage is green: run the plan's **sole plan-scope pass** (the only `clean` in the
whole execution), the tier's remaining review and evaluator passes, the version bumps and
their mirrors, the plan's closing note, the backlog and decisions reconciliation, the
decisions-conformance sweep, and the workflow-spec audit — then report and offer merge
options. **Do not merge without explicit confirmation.**

Ordered procedure, and what the report must contain: `references/close-out.md`.

---

## Safety rails

- **Never start on `main` / `master` without explicit user consent.** Use a feature branch or worktree.
- **Destructive commands** (schema migrations, data deletes, force pushes, production deploys) — confirm before running, even if the plan says to.
- **Secrets** — if a task would read or write credentials, stop and confirm the mechanism (env var, secrets manager) with the user before proceeding.
- **Shared infrastructure** — staging/prod-adjacent changes get confirmation per stage, not per plan.

---

## Sources and rationale

Beck, Cooper, Gawande, Torvalds, *The Pragmatic Programmer*, Anthropic's harness-design work,
Deming and Toyota's jidoka. What each one is load-bearing for: `references/sources.md`.

## Integration

This skill routes to `planning-projects` (which produced the plan),
`dispatching-parallel-agents` (every `Parallel: YES` task), `backlog` and `decisions` (at
close-out), `workflow-spec` (the close-out audit), the `git-github:code-reviewer` agent (both
review tiers) and a fresh agent in the goal-evaluator role (gate and close-out). What each is
for, on what condition it fires, and the **Review opt-out** rules: `references/integration.md`.
