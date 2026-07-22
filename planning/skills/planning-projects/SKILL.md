---
name: planning-projects
description: Use when the user wants a plan for a project of any size — triages to a format first (Direct/Light/Standard/Master) and may decline to plan a trivial job. Triggers on "roadmap", "break this down", "create a plan", "plan this", "how should I build".
---

# Project Planner

Create detailed, staged project plans grounded in real technical research. Every task gets a test. Every test gets a Red-Green loop. Nothing moves forward until the current task is green.

This skill produces plans where every task has a concrete test and the execution model prevents half-built states. For the default **Standard** plan, every claim also traces back to researched documentation and every stage carries stage gates and rollback notes; the lighter formats (see Phase -0.5) keep the test-and-gate backbone and scale the rest to the size of the job.

---

## Phase -1 — Clarification

Before researching or planning anything, make sure you understand what the user actually wants. Ambiguous or underspecified prompts produce plans that solve the wrong problem — and a wrong plan executed perfectly is worse than no plan at all.

### When to ask

Ask clarifying questions if any of these are unclear:

- **Scope**: What's included and what's explicitly out of scope?
- **Target environment**: What platform, language, framework, or infrastructure?
- **Constraints**: Performance requirements, compatibility targets, security needs, deadlines?
- **Existing state**: Is this greenfield or does it integrate with an existing system? If existing, where's the code?
- **Success criteria**: How will the user know the project is done? What does "working" look like?
- **Audience**: Who uses the end result — the user, their team, end users, CI/CD?

### How to ask

- One question at a time. Don't dump a wall of questions
- Prefer multiple-choice when the options are finite ("Are you targeting A, B, or C?")
- If you can infer an answer from the codebase or context, state your assumption and ask for confirmation rather than asking open-ended
- Stop asking once you have enough to produce a meaningful plan. You don't need perfect information — you need enough to avoid building the wrong thing

### When NOT to ask

If the prompt is specific enough to plan against (names a technology, describes the goal, implies the scope), skip straight to Phase -0.5. Don't ask questions for the sake of being thorough — ask because the answer would change the plan.

---

## Phase -0.5 — Format triage

Once the request is clear enough to size, pick the **format** before you plan. The
planning apparatus has a size ladder, and matching the format to the job is what keeps a
three-task chore from paying for a twelve-task project's ceremony — and a genuinely large
project from being crammed into too small a container. This is the downward-and-upward
symmetric partner to the decomposition rule in Phase 2.5.

| Format | Trigger | What you produce |
|--------|---------|------------------|
| **Direct** | ≤ ~2 tasks, one session, no staging value | **No plan file.** Recommend direct execution with a test and a commit, then stop — do not run Phases 0–5. |
| **Light** | Single stage, 2–5 tasks, one session, one stack, low risk | A Light plan per `references/light-plan-format.md` (`*-light-plan.md`) |
| **Standard** | Everything between Light and Master | The full staged plan (Phases 0–5 below) |
| **Master** | > ~6 stages / ~25 tasks, or ≥2 independently shippable workstreams | A master plan + sub-plans (Phase 2.5, `references/master-plan-format.md`) |

**How to triage:**

- **Direct is the off-ramp.** If the job is a couple of tested edits in one sitting, say
  so and execute it directly — a plan file would be pure overhead. This is the answer to
  "simple jobs shouldn't have to enter the machinery": the skill is now allowed to decline
  to plan. (Still write a test and commit — those are invariants, not ceremony. And still
  do a quick backlog-title check before you start — silently redoing a tracked item is the
  same planning bug at any size; this is the one Phase 0 step Direct keeps.)
- **Light** is for real-but-small work: one coherent stage of a handful of tested tasks,
  no fan-out, no cross-session handoff. It keeps the invariants (a `Test:` per task,
  `Status:` flips, commit per green task, honest gates) and drops the long-horizon
  artifacts (mandated Research Summary, full Preflight, Risk/Rollback, Blocks/Parallel
  fields). The full spec — and the exact kept-vs-dropped split — is
  `references/light-plan-format.md`.
- **Standard** is the default staged plan authored by Phases 0–5 of this skill.
- **Master** is the existing decomposition path; **Phase 2.5 is the sole authority on the
  Standard→Master decision** — this table only points at it, it does not restate the rule.

**Record the call.** State the chosen format and the trigger that selected it in one line
at the top of the plan you produce (`Format: Light — single stage, 4 tasks, one
session`), so a reader (and `executing-plans`) sees the decision, not just its result. A
Standard or Master plan may omit the line (they are the unmarked default); a Light plan
should carry it.

**When in doubt, round up.** A job on the Light/Standard or Standard/Master boundary takes
the heavier format — the cost of slightly too much structure is smaller than the cost of a
container that can't hold the work. The user can always override in either direction.

---

## Light plans

If Phase -0.5 selected **Light**, do not run the full Phase 0–5 apparatus below. Author a
single-stage plan per `references/light-plan-format.md` through this compressed path. The
format doc is the authoritative spec; these are the deltas from the Standard flow so you
know what to skip and what you must still do:

- **Research is proportionate, not a mandated section.** Replace the Research Summary with
  a 1–3 sentence **Context** line at the top of the plan (the key facts that ground it).
  Skip the online/vault research sweep unless a specific unknown demands it. **The backlog
  scan still runs** — a Light plan that silently duplicates an open backlog item is the
  same planning bug at any size; fold in matches with `Closes BL-NNN`. Likewise, if
  `docs/workflows/` exists and the change touches a documented flow, still declare
  `Changes/Removes WF-NNN` on the task — behavior contracts don't get a size exemption.
- **Preflight collapses into the gate.** There is no Preflight section. The only
  pre-execution check that matters at this size — "baseline tests pass" — lives as a bullet
  inside the single `### Stage 1 Gate` (alongside the git bootstrap `executing-plans`
  always does).
- **No Risk / Rollback / Blocks / Parallel fields.** One low-risk stage doesn't need a
  rollback rehearsal, and with ≤5 tasks in one session there's no fan-out to coordinate.
  Keep `Depends on` only where a task genuinely consumes a prior task's output.
- **Output location is unchanged.** A Light plan saves to the same
  `<portfolio_home>/plans/` in the vault under the same resolution and sidecar rules as any
  plan (project auto-registered, `PORTFOLIO-STATUS` block present) — it is a first-class
  plan, just a small one. Filename ends in `-light-plan.md` (and its first heading is
  `# Light Plan:` — either one lets `executing-plans` detect the format).
- **Use the Light checklist**, not the full one — see "Checklist — Light plans" below.

If while authoring you find the job needs a second stage or a 6th task, stop treating it as
Light: re-issue it as a Standard plan (the upgrade rule in `references/light-plan-format.md`).
Don't stretch the Light format past its bounds.

---

## Phase 0 — Research

Before writing a single task, gather the technical facts. Plans built on assumptions fall apart mid-build when the API doesn't work the way you imagined or the library dropped that feature two versions ago.

### Online sources

Use WebSearch / WebFetch to pull documentation for every technology in scope:

- API formats, SDK methods, config schemas
- Version-specific behavior — don't assume, check. A method that exists in v3 may not exist in v2
- Known limitations, gotchas, deprecations, breaking changes between versions
- Community patterns — how do other projects solve this?

If the project uses a library or framework, use context7 MCP to fetch current documentation rather than relying on training data that may be months old.

### Local vault

If an Obsidian vault is linked (check `vault-context:status`), search it for:

- Prior decisions on this topic (ADRs, design docs)
- Architecture notes that constrain the approach
- Related past work — what was tried, what worked, what didn't

Check the project's existing plans for prior design decisions: `<portfolio_home>/plans/` in the vault (the canonical location), falling back to `<repo>/docs/plans/` and `docs/` only if no `vault_dir` is configured or the project predates migration.

### Backlog scan

Call the `backlog` skill (`read` or `list`) and check `docs/backlog.md` for open entries that touch the new plan's scope — same component, same tags, or named in `Source`. For each match:

- If the new plan naturally subsumes the item, fold it in and reference the ID on the relevant task (`Closes BL-NNN`) so `executing-plans` can remove it on Close-out.
- If not, leave it deferred and note in the Research Summary why it stays out.

A new plan that silently duplicates an open backlog item is a planning bug — the scan is how you catch it.

### Workflow-spec scan

If `docs/workflows/` exists, read the files whose scope touches the plan. They are the project's behavior contracts and dictate what the plan must preserve, change, or extend:

- A task that intentionally alters a documented behavior must declare it on the task line: `Changes WF-AUTH-003 — passwordless replaces bcrypt branch`.
- A task that removes a documented behavior must declare it: `Removes WF-AUTH-007`.
- A task that adds a new user-visible flow must add a corresponding capture/extend step to the plan so the spec doesn't fall behind code.

Plans that touch the codebase without referencing any in-scope WF-ID either (a) genuinely don't change documented behavior, or (b) are missing a declaration. Be explicit about which.

**Redesign-from-handoff plans** (reproducing a Claude Design handoff pack via the
`applying-design-handoff` skill) make behavior changes *the rule, not the exception* —
the design is the source of truth and reshapes functionality to fit. Plan them so the
design wins but every behavior change is gated: each task that alters or drops a flow to
match the design declares it (`Changes WF-NNN` / `Removes WF-NNN`), each new design screen
adds a capture step, and the stage carries a **reconciliation/sign-off task** that
presents the conflict report and gets the user's explicit approval before any destructive
behavior change is applied. A redesign plan with no WF declarations is almost certainly
missing them.

### Architecture doc scan

If the `architecting-projects` skill produced an architecture doc for this topic
(`<portfolio_home>/plans/YYYY-MM-DD-<topic>-architecture.md`, or `docs/plans/` in the
no-vault fallback), it is the authoritative structure the plan builds — read it before
writing any task:

- **Structure-creating tasks MUST cite the ARCH-ID they implement** on the task line
  (`Creates ARCH-01 tree`, `Implements ARCH-03 RemoteStore boundary`). A task that
  invents structure not present in the doc is either missing a citation or
  contradicting an approved decision — resolve which before presenting the plan.
- **Emit the conformance gate:** the plan's final stage gate includes the check
  `- [ ] Built structure conforms to the architecture doc (ARCH-NN tree matches,
  ARCH-NN boundaries respected — list the IDs actually in scope)` so
  `executing-plans` verifies conformance at close-out without any special handling.
- **Decomposed projects (Phase 2.5):** each *sub-plan* that creates structure carries
  its own ARCH-ID citations and its own conformance check in its own final stage
  gate; the master's register `**Gate:**` blocks are untouched, and the master's
  no-tasks/no-Preflight parser-safety invariant is unaffected by the citation
  convention (citations live on task lines, which masters don't have).
- The plan must not silently deviate from the doc. A deviation discovered during
  planning goes back to the user (the architecture was explicitly approved); the doc
  is then revised — ARCH-IDs are stable, revisions append rather than renumber.

No architecture doc for a plan with obvious structural surface? State it explicitly in
the Research Summary ("no architecture doc — structure decided inline") rather than
leaving the reader to wonder whether one was consulted.

### Project context

Read the codebase before planning against it:

- Existing patterns, conventions, file structure — the plan should fit, not fight
- Dependencies already in use — don't introduce a second HTTP client when one is already there
- Test patterns already established — match the existing test framework and style
- CI/CD pipeline — understand what runs on push so you can write tests that work in CI

### Research summary

Compile findings into a **Research Summary** at the top of the plan document. Every task below should trace back to something learned here. If a task can't be grounded in research, that's a signal you need to research more before planning it.

---

## Phase 1 — Preflight

Before Stage 1 begins, verify that everything needed to execute the plan is in place. Discovering a missing tool or expired API key mid-build wastes time and breaks flow.

### Preflight checklist

Verify each of these and report the result:

- [ ] **Tools**: All CLI tools required by the plan are installed and at compatible versions
- [ ] **Dependencies**: All libraries/packages are available and version-compatible with each other
- [ ] **APIs**: Required endpoints are reachable, keys are valid, auth works
- [ ] **Access**: Required permissions exist (repo write, service accounts, deploy targets)
- [ ] **Environment**: The dev environment can build the project and run the test suite
- [ ] **Baseline**: Existing tests pass before any changes begin (don't build on a broken foundation)

If any preflight check fails, stop. Fix it or flag it to the user before proceeding. Starting Stage 1 with a broken preflight is how you end up debugging environment issues instead of building features.

For a project whose full test suite is expensive (see references/test-scope-tiers.md), the plan declares its stage-scope and plan-scope test commands here in Preflight, so executors run known-good invocations instead of improvising scope mid-execution.

---

## Phase 2 — Stage Breakdown

Divide the project into sequential stages. Each stage is a coherent unit of work that produces a testable milestone — something you can point to and say "this works end-to-end."

### Stage structure

```
Stage N: [Name]
  Goal:       What this stage achieves (one sentence)
  Depends on: Stage(s) that must be green first
  Blocks:     Stage(s) that cannot start until this stage's gate passes
  Risk:       LOW | MEDIUM | HIGH — why
  Rollback:   What to undo if this stage fails irreparably

  Tasks (dependency-ordered):
    Task N.1: [description]
      Depends on: [prior task(s) or "none"]
      Blocks:     [task(s) that wait on this one, or "none"]
      Parallel:   YES | NO  (can a sub-agent run this concurrently?)
      Test:       [concrete pass/fail criterion]

    Task N.2: [description]
      Depends on: Task N.1
      Blocks:     Task N.3, Task N.4
      Parallel:   NO  (blocked by N.1)
      Test:       [concrete pass/fail criterion]

  Stage gate:
    - [ ] Integration check 1
    - [ ] Integration check 2
    - [ ] No regressions in existing tests
```

### Status marking (per-task done-state)

Every task carries a **Status** checkbox as its first field: `- **Status:** [ ]` when planned, flipped to `- **Status:** [x]` by `executing-plans` the moment the task's test goes green (and committed in the same commit). This is the **single source of truth for task completion** — it removes the ambiguity that arises when done-ness is inferred only from stage gates or git archaeology. A downstream tool (e.g. `portfolio unify`) can read `Status: [x]` vs `[ ]` to know exactly what was executed, with no guessing.

When the whole plan is finished, `executing-plans` appends a close-out line at the end of the plan: `**Completed:** YYYY-MM-DD — commits: <list>`. A plan with that line and all `Status: [x]` is unambiguously done; absent the line, any `Status: [ ]` task is genuinely unexecuted.

### Dependency marking

Every task and stage carries two dependency fields — this makes the graph navigable in both directions:

- **Depends on**: What must be green before this task/stage can start
- **Blocks**: What is waiting on this task/stage to finish

These fields are symmetric: if Task 2.1 depends on Task 1.3, then Task 1.3 must list Task 2.1 in its Blocks field. This redundancy is intentional — when a task finishes, you can immediately see what it unblocks without scanning the entire plan.

Mark each task's **Parallel** field:
- **YES** if the task has no unfinished dependencies (all its `Depends on` items are green or "none") — it can be dispatched to a sub-agent immediately
- **NO** if it's blocked — list which dependency is blocking it

### Ordering rules

1. **Stages are sequential.** Stage 2 does not start until Stage 1's gate passes
2. **Tasks within a stage follow their dependency graph.** If Task B needs output from Task A, Task A comes first — this isn't optional, it's structural
3. **Independent tasks can run in parallel.** If Tasks 2.3 and 2.4 have no dependency on each other, they can be worked simultaneously
4. A task cannot enter its Red-Green loop until every task it depends on is green

### Risk flags

Mark each stage with a risk level. This tells the user (and you) where to expect friction:

- **LOW**: Well-understood tech, clear path, prior art exists in the codebase
- **MEDIUM**: Some unknowns — unfamiliar API, complex integration point, limited docs
- **HIGH**: Novel territory, unreliable external dependencies, tight constraints, or no prior art

High-risk stages deserve extra care: consider a spike or prototype first, prepare the rollback plan in detail, and expect the Red-Green loop to cycle more than once per task.

### Rollback notes

Each stage documents what to undo if it fails beyond recovery. Half-built states with no way back are worse than not starting:

- Which files or changes to revert (`git` refs if applicable)
- Which migrations or schema changes to roll back
- Which services or infrastructure to restore to prior state
- Which side effects (messages sent, data written) cannot be undone — flag these explicitly

### Stage sizing

If a stage has more than 7 tasks, it's too large. Split it. Large stages hide integration problems behind a wall of individual task tests that all pass but don't work together. Aim for 3-5 tasks per stage.

---

## Phase 2.5 — Decomposition decision (master plan + sub-plans)

Stage sizing has a project-level analogue: when the *plan itself* is too large, don't
write one monolith — decompose it into several independently executable **sub-plans**
linked by one **master plan**. The canonical format (naming, master document structure,
register fields, parser-safety rules) is `references/master-plan-format.md`; this section
is only the decision rule.

**Decompose when ANY of these hold:**

- The single plan would exceed **~6 stages or ~25 tasks**
- The work spans **two or more independently shippable workstreams** (separate
  deliverables, repos, or subsystems)
- Execution will clearly span **multiple sessions or stacks**, each wanting its own
  context window

**How to split:**

- **2–7 sub-plans.** One sub-plan means no master was needed; more than seven means the
  scope is a portfolio, not a project.
- **Each sub-plan is a complete, independently executable plan** — its own Research
  Summary (scoped), Preflight, Stages, gates, and close-out. If a candidate sub-plan
  can't run alone, it's a stage of another sub-plan; fold it back in.
- **The master plan holds what's shared:** the cross-cutting Research Summary, the
  sub-plan register (Status / Plan link / Goal / Depends on / Blocks / Parallel per
  entry), and a `**Gate:**` block per entry with integration checks across sub-plans.
  The master carries **no tasks and no Preflight** — and no raw `- [ ]` bullets outside
  `**Gate:**` blocks, so the portfolio parser reads it cleanly (see the parser-safety
  rules in the reference).
- **Sub-plan register dependencies are symmetric**, exactly like task fields — and if you
  can't name a master gate check between two sub-plans, question the split: they're
  either one plan or two unrelated projects.
- **Each sub-plan backlinks to the master** (`Master: ./<master-file>` under `Date:`).

Research once, at master level, then scope each sub-plan's Research Summary down to what
that sub-plan needs. The backlog scan and workflow-spec scan run once for the whole
decomposition; fold-ins (`Closes BL-NNN`) and WF declarations land on tasks inside the
relevant sub-plan.

Hand the master plan to `executing-plans` — it recognizes the format, drives sub-plans in
register dependency order (fresh session per sub-plan recommended), and defers version
bumps to the master close-out.

---

## Output location (vault-canonical)

Plans live in the vault, not the repo. Before writing, resolve the project's portfolio home:

1. Read `vault_dir` from `~/.claude/portfolio-config.yaml`. **If unset**, fall back to `<repo>/docs/plans/` and warn the user that the plan is landing in-repo (no vault configured) — then skip the rest of these steps.
2. Compute `portfolio_home = <vault_dir>/Portfolio/<area>/<name>/`, deriving `<area>`/`<name>` from the project's `~/dev/<area>/<name>` path.
3. **Auto-register if new:** if the project isn't in `~/.claude/projects-registry.yaml`, append an entry (`path`, `name`, `area`, `enabled: true`, `added: <today>`). This is how a brand-new project joins the portfolio — no separate step.
4. **Create/refresh the sidecar:** ensure `<repo>/.claude/vault-context.md` carries the `PORTFOLIO-STATUS` block (per `../portfolio/references/sidecar-format.md`) — run `/planning:portfolio rebuild` (or `scripts/portfolio-rebuild.py`) for the canonical writer rather than hand-editing the block. `mkdir -p` the vault `plans/` dir. The block's **Plans:** line points at `<portfolio_home>/plans/`, so the plan you save in the next step is discoverable from the sidecar the instant it lands — no per-plan write into vault-context is needed (the link is to the directory, and never goes stale). On a project that already has the block, the existing pointer already covers the new plan; you only need to (re)generate the block for a brand-new project that has none yet.

Then save the plan to `<portfolio_home>/plans/YYYY-MM-DD-<topic>-plan.md`. (The design doc from `brainstorming` lands beside it via the same resolution.)

**Decomposed projects** (Phase 2.5) save all files flat in the same `plans/` dir: the
master plan as `YYYY-MM-DD-<topic>-master-plan.md` and each sub-plan as
`YYYY-MM-DD-<topic>-sub-NN-<slug>-plan.md`, numbered in dependency order — per
`references/master-plan-format.md`.

## Plan Document Format

Output the plan as a markdown document following this structure. Save it to `<portfolio_home>/plans/YYYY-MM-DD-<topic>-plan.md` (vault), or `docs/plans/` only in the no-`vault_dir` fallback above.

```markdown
# Project Plan: [Name]
Date: [YYYY-MM-DD]

## Research Summary

### Online sources
- [What was found, with links]

### Vault / local docs
- [Prior decisions, architecture notes]

### Project context
- [Existing patterns, dependencies, test framework]

## Preflight

- [ ] [Check 1]: [how to verify]
- [ ] [Check 2]: [how to verify]

**Test-scope commands** (per references/test-scope-tiers.md — only when the full suite exceeds ~5 min):
- stage-scope: [cheap checks in full + expensive suites for touched modules; no clean]
- plan-scope:  [the single full clean pass, quarantined tests included]

---

## Stage 1: [Name]

**Goal:** [one sentence]
**Depends on:** none
**Blocks:** Stage 2
**Risk:** LOW | MEDIUM | HIGH — [reason]
**Rollback:** [what to undo and how]

### Task 1.1: [description]
- **Status:** [ ]
- **Depends on:** none
- **Blocks:** Task 1.2
- **Parallel:** YES
- **Test:** `[exact command or criterion]`
- **Red-Green max cycles:** 3

### Task 1.2: [description]
- **Status:** [ ]
- **Depends on:** Task 1.1
- **Blocks:** Task 1.3, Task 2.1
- **Parallel:** NO (blocked by 1.1)
- **Test:** `[exact command or criterion]`
- **Red-Green max cycles:** 3

### Stage 1 Gate
- [ ] [Integration check]
- [ ] [No regressions in touched scope (stage-scope — see references/test-scope-tiers.md)]
- [ ] [Stage goal verified end-to-end]

---

## Stage 2: [Name]

**Goal:** ...
**Depends on:** Stage 1 gate passing
**Blocks:** Stage 3
**Risk:** ...
**Rollback:** ...

[Tasks with Depends on / Blocks / Parallel fields...]

### Stage 2 Gate
[Checks...] — if Stage 2 is the plan's final stage, its gate replaces the
regression check above with the plan-scope bullet instead:
- [ ] [Full clean test pass (plan-scope — the plan's single full run)]
```

---

## Phase 3 — The Red-Green Loop

This is the execution model for every task. No task is "done" until its test is green. "It looks right" is not green — run the test.

```
    +----------+
    | Attempt  |  Write the code / make the change
    +----+-----+
         |
         v
    +----------+
    |   Test   |  Run the task's specific test
    +----+-----+
         |
     +---+---+
     | Pass? |
     +---+---+
      |     |
    GREEN   RED
      |     |
      |     v
      |  +----------+
      |  | Diagnose |  Read the error. Understand WHY it failed
      |  +----+-----+
      |       |
      |       v
      |  +----------+
      |  |   Fix    |  One targeted fix based on diagnosis
      |  +----+-----+
      |       |
      |       v
      |    Retest ----> back to Test
      |       |
      |  (max 3 RED cycles, then escalate)
      |
      v
  Next task
```

### Loop rules

1. **One fix per cycle.** Don't shotgun multiple changes hoping one sticks. Isolate the problem, fix that one thing, retest
2. **Diagnose before fixing.** Read the actual error output. Form a hypothesis. Confirm it against the code. Only then write the fix
3. **Max 3 RED cycles per task.** If a task fails its test 3 times in a row, stop the loop and escalate to the user. Three failures usually means the approach is wrong, not just the implementation. Continuing to loop is wasting time
4. **Never skip the test.** Every attempt ends with running the test. No exceptions. The test is the only thing that says you're done

---

## Phase 4 — Stage Gates

After all tasks in a stage pass their individual tests, run a stage-level integration check before proceeding to the next stage. Individual tests prove each piece works. Stage gates prove the pieces work together.

### What a stage gate checks

- **Integration**: The tasks in this stage interact correctly (e.g., the API endpoint serves data from the database schema that was just created)
- **Regressions**: Scoped to the gate's position in the plan. Intermediate gates check at **stage-scope** — cheap host-side checks (unit tests, lint, static/architecture checks, build) run in full, and any expensive suite (device/instrumented/e2e) is restricted to the modules the stage touched, never `clean`. The final gate (and close-out) runs **plan-scope** — one full clean pass, quarantined slow tests included. If the project's full suite is cheap (well under ~5 min), skip the tiering and just run it in full at every gate. Scope policy: references/test-scope-tiers.md.
- **Goal verification**: The stage's stated goal is actually met end-to-end, not just task-by-task
- **Live artifact over static checks**: Where the stage produces something runnable, at least one gate check launches it and drives the user-visible flow (run the app, hit the endpoint, click the screen). Unit tests pass on stubbed features; only live interaction catches them

### When a stage gate fails

If the gate fails, the problem is usually in how tasks interact, not in any single task. Identify which task interaction caused the failure, add a new test for that interaction to the relevant task, and run that task through its Red-Green loop again.

---

## Phase 5 — Parallel Execution

When executing the plan, use sub-agents to run independent tasks concurrently. This is where the dependency graph pays off — you don't have to guess what can run in parallel, the `Blocks` and `Depends on` fields tell you exactly.

### Dispatch rules

1. **At stage start**, identify all tasks with `Parallel: YES` (no unfinished dependencies). Dispatch them all to sub-agents simultaneously
2. **When a task completes green**, check its `Blocks` list. For each blocked task, check if ALL of that task's dependencies are now green. If yes, dispatch it to a new sub-agent
3. **Never dispatch a task whose dependencies aren't all green.** The Parallel field in the plan is the initial state — during execution, a task becomes dispatchable only when its actual dependencies have passed
4. **Each sub-agent runs one task's Red-Green loop independently.** The sub-agent attempts the task, runs the test, and if RED, diagnoses and fixes within the 3-cycle limit. It reports back GREEN or ESCALATE
5. **Stage gate runs only after all tasks in the stage are green.** Don't start the gate while any task is still in its Red-Green loop
6. **Match each sub-agent to the task's stack.** Pick the sub-agent type — and the stack skill it should load first — from the shared routing table at `../dispatching-parallel-agents/references/stack-routing.md` (Rust → `rust-expert`, Android UI → `ui-android`, tests → `testing-expert`, … with a `general-purpose` fallback). The same table governs `executing-plans` and `dispatching-parallel-agents`, so dispatch decisions stay consistent from planning through execution

### Dispatch flow

```
Stage starts
    |
    v
Scan tasks: which have all dependencies green?
    |
    +---> Dispatch each ready task to a sub-agent (in parallel)
    |
    v
Wait for any sub-agent to finish
    |
    v
Task GREEN?
  |       |
  YES     NO (escalated after 3 RED cycles)
  |       |
  |       +--> Pause. Surface to user. Do NOT dispatch dependents
  |
  v
Check Blocks list of completed task
  |
  v
For each blocked task: are ALL its dependencies now green?
  |       |
  YES     NO
  |       |
  v       (wait for other dependencies)
Dispatch to sub-agent
    |
    v
(repeat until all tasks green or escalated)
    |
    v
Run stage gate
```

### What a sub-agent receives

Each sub-agent needs enough context to work independently:

- The task description and its test criterion
- Relevant research findings from Phase 0 (not the entire research summary — just what this task needs)
- File paths and patterns from the project context
- The Red-Green loop rules (attempt, test, diagnose, fix, retest, max 3 cycles)
- The stack skill to invoke first, if the routing table names one for this task's stack — so the agent authors to that stack's conventions instead of generic defaults
- What to do on failure: report back with the error and diagnosis, don't keep looping silently

### Guardrails

- **No cross-task file conflicts.** Before dispatching parallel tasks, verify they don't modify the same files. If two tasks edit the same file, they must run sequentially even if the dependency graph says they're independent
- **Merge check after parallel tasks complete.** If multiple sub-agents wrote code in the same stage, run the test suite before the stage gate to catch integration issues introduced by parallel work
- **Failed task blocks its dependents.** If Task 2.1 fails and escalates, do not dispatch Tasks 2.3 and 2.4 that depend on it. Mark them as BLOCKED and surface the entire chain to the user

---

## Checklist — Before Presenting the Plan

**Light plans use the "Checklist — Light plans" below instead of this one.** This full
checklist applies to Standard plans (and, with the decomposition addendum, Master plans).

Before showing the plan to the user, verify:

- [ ] Every task has a concrete, runnable test — no "it should work" tests
- [ ] Tasks within each stage follow their dependency order
- [ ] No task depends on something from a later stage
- [ ] Every stage has a risk flag with a reason
- [ ] Every stage has a rollback note
- [ ] Every stage has a gate with specific checks
- [ ] No stage has more than 7 tasks
- [ ] Every user-facing stage has at least one gate check that exercises the running artifact, not only static tests
- [ ] The research summary has actual findings, not placeholders
- [ ] Preflight checks cover all tools, deps, and access needed by the plan
- [ ] If the project's full suite is expensive (>~5 min): the plan declares its stage-scope and plan-scope commands, only the final gate runs the full clean pass, and any single test >~2 min is quarantined behind an opt-in filter (references/test-scope-tiers.md)
- [ ] Every task has both `Depends on` and `Blocks` fields — and they're symmetric
- [ ] Every task has a `Parallel` field (YES/NO) consistent with its dependencies
- [ ] No two parallel tasks modify the same files
- [ ] The plan is saved to the project's `<portfolio_home>/plans/` in the vault (project auto-registered + sidecar carries the `PORTFOLIO-STATUS` block whose **Plans:** pointer reaches the new plan); or `docs/plans/` only in the no-`vault_dir` fallback
- [ ] Open backlog items in scope were reviewed; folded-in items carry a `Closes BL-NNN` reference on the task that closes them
- [ ] Workflow specs in scope were read; any altered or removed behavior is declared on the corresponding task (`Changes WF-NNN` / `Removes WF-NNN`); new flows have a capture/extend task
- [ ] If an architecture doc exists for this topic: every structure-creating task cites its ARCH-ID, the final stage gate carries the architecture-conformance check, and no task contradicts an approved ARCH section

**Additionally, for a decomposed project (master plan + sub-plans):**

- [ ] The decomposition trigger actually held (Phase 2.5) — 2–7 sub-plans, each independently executable
- [ ] Register `Depends on` / `Blocks` fields are symmetric across sub-plan entries
- [ ] Every register entry ends with a `**Gate:**` block containing at least one cross-plan integration check
- [ ] Every sub-plan carries the `Master: ./<master-file>` backlink; every register `Plan:` link resolves
- [ ] The master plan is parser-safe: no raw `- [ ]` bullets outside `**Gate:**` blocks, no tasks, no Preflight (see `references/master-plan-format.md`)

---

## Checklist — Light plans

For a **Light** plan (Phase -0.5), verify only these — the full checklist above does not
apply:

- [ ] Every task has a concrete, runnable `Test:` — the same bar as any plan
- [ ] Tasks are in dependency order; any `Depends on` points only backward within the stage
- [ ] Exactly one stage, with 2–5 tasks (a 6th task or a second stage means re-issue as Standard)
- [ ] The single `### Stage 1 Gate` includes "full existing test suite passes" and a goal-level end-to-end check
- [ ] The `Format: Light — …` line is present at the top; the file is saved to `<portfolio_home>/plans/` as `*-light-plan.md`
- [ ] Open backlog items in scope were reviewed (the scan runs at every size); folded-in items carry `Closes BL-NNN`
- [ ] If `docs/workflows/` exists and the change touches a documented flow, the altered/removed behavior is declared on the task (`Changes WF-NNN` / `Removes WF-NNN`) — behavior contracts don't get a size exemption

---

## Common Pitfalls

These pitfalls are written for **Standard** (and Master) plans. Rows about Risk, Rollback,
`Blocks`, `Parallel`, mandated research, or the Preflight section don't apply to a **Light**
plan, which legitimately drops those fields (Phase -0.5) — a Light author should read the
"Tasks without tests", "Wrong task order", and "Vague stage gates" rows as still binding
and treat the rest as Standard-only.

| Pitfall | What goes wrong | Fix |
|---------|----------------|-----|
| Tasks without tests | You don't know if the task actually works until 3 stages later when something breaks | Write the test first. If you can't write a test, the task is too vague — split or clarify it |
| Wrong task order | Task B fails because Task A's output isn't ready yet, wasting Red-Green cycles | Draw the dependency graph before ordering. If B reads from A, A comes first |
| Skipping research | You plan around an API that was deprecated last month, or a config format that changed | 20 minutes of research prevents hours of rework. Check the current docs |
| Monolith stages | A 12-task stage where one failing gate is impossible to diagnose | Split stages at natural boundaries. 3-5 tasks per stage |
| Vague stage gates | "Everything works" as a gate tells you nothing when it fails | Name the specific command or check. "Run `npm test` and all 47 tests pass" |
| Static-only gates | Every gate is unit tests; a stubbed feature sails through all of them and ships broken | Gates on user-facing stages must run the artifact and drive the flow live, not just grep and test |
| No rollback notes | Stage 3 fails, you've modified the database schema and 6 config files, and you don't know how to get back | Document rollback at planning time, not panic time |
| Infinite Red-Green loops | Cycling through fixes without understanding the root cause | 3 cycles max. If 3 targeted fixes don't work, the approach — not just the code — needs rethinking |
| Research-free planning | "I'll figure out the API as I go" | You won't. Research first, plan second, build third |
| Asymmetric dependencies | Task A says it blocks B, but B doesn't list A in Depends on — the graph is broken | Always write both directions. If you add a Depends on, update the other task's Blocks |
| Parallel file conflicts | Two sub-agents edit the same file simultaneously, producing merge conflicts or silent overwrites | Check file paths before dispatching. If tasks touch the same file, force sequential execution |
| Full suite at every gate | On an expensive suite (device/e2e), every intermediate gate re-proves unchanged code — hours of wall-clock lost per plan, plus `clean` wiping incremental state each time | Tier the scope — stage-scope at intermediate gates, one clean plan-scope pass at the final gate (references/test-scope-tiers.md) |
| Planning without clarifying | The prompt says "build a dashboard" so you plan a React app, but the user wanted a CLI tool | If the prompt is ambiguous about scope, target, or constraints, ask before you plan. A 30-second question saves a 30-minute rewrite |
