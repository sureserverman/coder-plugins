---
name: planning-projects
description: Use when the user wants a plan for a project of any size — triages to a format first (Direct/Light/Standard/Master) and may decline to plan a trivial job. Triggers on "roadmap", "break this down", "create a plan", "plan this", "how should I build".
---

# Project Planner

Create detailed, staged project plans grounded in real technical research. Every task gets a test. Every test gets a Red-Green loop. Nothing moves forward until the current task is green.

This skill produces plans where every task has a concrete test and the execution model prevents half-built states. For the default **Standard** plan, every claim also traces back to researched documentation and every stage carries stage gates and rollback notes; the lighter formats (see Phase -0.5) keep the test-and-gate backbone and scale the rest to the size of the job.

---

## Reference map

The trunk carries the authoring decisions. These load when their condition is met:

| Read this | When |
|---|---|
| `references/plan-document-template.md` | writing the plan file — the literal template |
| `references/task-fields.md` | the exact semantics of any task or stage field |
| `references/set-valued-checks.md` | writing a gate check whose goal quantifies over a set |
| `references/light-plan-format.md` | Phase -0.5 selected **Light** |
| `references/master-plan-format.md` | Phase 2.5 selected **Master** |
| `references/test-scope-tiers.md` | declaring the plan's test-scope commands |

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

### Decisions scan

Call the `decisions` skill's `relevant` operation — it infers the domain registers from the project's stack (`../decisions/references/domain-slugs.md`) and digests both halves in one step, rather than making you hand-read files. Unlike a plan, these entries carry the *reason* a constraint exists, including security recommendations recorded from sec-audit runs whose reports are local-only and unreadable from here.

- A task that would contradict an accepted decision is a planning bug. Either the plan supersedes the decision deliberately — say so on the task with a `Supersedes` citation, and the executor records the supersede at close-out — or the task is re-scoped.
- A plan that *creates* a binding constraint should add a task to record it (`decisions add`), so the next plan inherits the reason rather than rediscovering it.
- **Superseded entries in the digest are still informative.** They record an approach already tried and abandoned; re-proposing it is the failure they exist to prevent.

**On a project with no registry entry** (a brand-new project), `portfolio_home` doesn't resolve and there is no `decisions.md` — that is expected, not a reason to skip the scan. The per-domain registers are keyed by domain, not project, so they bind a greenfield project just the same and are the half that matters most to it. Record the state in the plan (`project register: absent — new project`) and carry the global half forward. Registration then happens on the normal path, when you write the plan (§ Output location step 3).

**Write the findings into the plan.** The scan's output goes in a `## Decisions in force` section directly below the Research Summary — the plan file is the cross-session handoff artifact, and a constraint discovered at planning time that isn't recorded there is a constraint the executor will never see. Use non-checkbox bullets (a raw `- [ ]` outside Preflight/Gate blocks becomes a false backlog candidate in `portfolio unify`). Record what was consulted, so a reader can tell **"nothing binds this scope"** from **"nobody looked"** — the same distinction the architecture-doc rule makes. When nothing applies, say so explicitly:

```markdown
## Decisions in force

- none — registers consulted: `Portfolio/decisions/rust.md`, `Portfolio/decisions/ubuntu.md`; no entry binds this scope

**Registers consulted:** rust, ubuntu (project register: absent — new project)
**Domains inferred:** rust, ubuntu, tor (no register exists for `tor` yet)
```

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
  `- [ ] **(judgment)** Built structure conforms to the architecture doc (ARCH-NN tree
  matches, ARCH-NN boundaries respected — list the IDs actually in scope)` so
  `executing-plans` verifies conformance at close-out without any special handling. The
  marker is required for the same reason as the decisions-conformance gate below: this
  is a conformance judgment over a built tree, no sweep can prove it, and a template
  emitting it unmarked would ship the one check shape the class-predicate rule forbids.
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

### Citing decisions on tasks

Decisions use the **same citation mechanism as `ARCH-NN`** — deliberately, so
`executing-plans` needs no special handling for either:

- **A task constrained by a decision cites it:** `Honors DEC-003` on the task line. This
  is what carries the constraint from the register to the person (or agent) implementing
  the task, who may never read the register itself.
- **A task that deliberately overrides one cites it with a reason:**
  `Supersedes GDEC-AND-002 — Orbot dropped per-app mode in 17.4`. The citation is what
  makes the override *auditable* rather than silent, and it is the executor's instruction
  to record the supersede at close-out.
- **Emit the conformance gate:** the plan's final stage gate carries
  `- [ ] **(judgment)** No change contradicts a decision in force (DEC-NNN / GDEC-… — list
  the IDs actually in scope); any Supersedes citation has been recorded via decisions
  supersede`. The marker is **required**, not optional: this is the canonical
  "conformance judgment over a diff" the set-valued-check rule below names as needing a
  reader, so a template emitting it unmarked would ship the one check shape the rule
  forbids.
- **Per DEC-001**, a citation restates the constraint in the entry's own words. A decision
  sourced from a sec-audit never brings the report body into the plan.

An uncited change that contradicts an accepted decision is a **gate failure** in
`executing-plans`, not an advisory — silently violating a recorded decision is the exact
failure the register exists to prevent.

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
- [ ] **Review scope**: the tier this plan's cumulative diff warrants — `none` / `light` / `standard` / `high` — stated with its reason. Undeclared means `standard`; touching a risk-listed area sets `high` regardless of size. **A `high` declaration names the risk-listed tasks it binds** (`review-scope: high — tasks 1.1, 1.3 (schema migration)`), because Tier-1 attaches to the **risk-listed task**, not the plan — an unnamed `high` conservatively binds every task (`../executing-plans/references/review-scope.md`)
- [ ] **Dispatch probe**: A throwaway subagent returns a fixed string — dispatch works in this session (skipped on an empty roster, or below tier `standard`)
- [ ] **Dispatch roster**: Every `Parallel: YES` task in the plan is listed with the subagent type it routes to (`../dispatching-parallel-agents/references/stack-routing.md`), or `0 tasks` when there are none

If any preflight check fails, stop. Fix it or flag it to the user before proceeding. Starting Stage 1 with a broken preflight is how you end up debugging environment issues instead of building features.

The review-scope line is what lets the executor's machinery scale to the job: it gates both review tiers, both evaluators and the dispatch probe, so an undeclared plan silently pays `standard` for work that may warrant `light`. Declare it from the plan's **cumulative** diff, once, not per task.

The dispatch checks exist because `Parallel: YES` is a directive (see § Stage structure) whose breach is otherwise invisible. They are the *executor's* rules; the author's job is to carry them into the plan's Preflight so a run cannot skip them by never being asked. Note the roster must cover **every stage, not the first** — a partial roster is the instance-shaped check this skill rejects everywhere else. The rest of the reasoning lives at `../executing-plans/SKILL.md` § Dispatch roster and capability probe and is deliberately not repeated here.

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
      Parallel:   YES | NO  (an instruction to the executor — YES obligates dispatch to a
                  subagent; it is not a note about whether a sibling task runs alongside it)
      Scope:      [the SET this task changes — omit when it changes exactly one thing]
      Test:       [concrete pass/fail criterion]
      Review:     skip   (OPTIONAL, and only on the user's say-so — see below)

    Task N.2: [description]
      Depends on: Task N.1
      Blocks:     Task N.3, Task N.4
      Parallel:   NO  (blocked by N.1)
      Test:       [concrete pass/fail criterion]

  Stage gate:
    - [ ] Integration check 1
    - [ ] Class predicate: the command that sweeps the set the claim is over
    - [ ] No regressions in existing tests
    - [ ] (judgment) [what needs a reader, and why a sweep cannot prove it]
```

### Status marking (per-task done-state)

Every task carries a **Status** checkbox as its first field: `- **Status:** [ ]` when planned, flipped to `- **Status:** [x]` by `executing-plans` the moment the task's test goes green (and committed in the same commit). This is the **single source of truth for task completion** — it removes the ambiguity that arises when done-ness is inferred only from stage gates or git archaeology. A downstream tool (e.g. `portfolio unify`) can read `Status: [x]` vs `[ ]` to know exactly what was executed, with no guessing.

When the whole plan is finished, `executing-plans` appends a close-out line at the end of the plan: `**Completed:** YYYY-MM-DD — commits: <list>`. A plan with that line and all `Status: [x]` is unambiguously done; absent the line, any `Status: [ ]` task is genuinely unexecuted.

### Task and stage fields

Each task carries `Status`, `Depends on`, `Blocks`, `Parallel`, `Test:` and
`Red-Green max cycles:`; a task sweeping a set also carries `Scope:`, and each stage carries
`Risk:` and `Rollback:`. Two rules are load-bearing enough to state here rather than defer:

- **`Parallel: YES` is a directive to dispatch**, not a description of what happened.
- **`Scope:` is only as good as the sweep behind it** — a truncated authoring command is a
  documented way for one to arrive short, and a gate failure then repairs an instance while
  its siblings survive.

Exact semantics for every field — including `Review: skip`, dependency symmetry, ordering
rules, risk flags, rollback notes and stage sizing: `references/task-fields.md`.
### Stage sizing

If a stage has more than 7 tasks, it's too large. Split it. Large stages hide integration problems behind a wall of individual task tests that all pass but don't work together. Aim for 3-5 tasks per stage.

---

### A plan that adds an obligation names what it removes

This applies to plans that change a **process** — a skill, a gate, a checklist, a
convention every future run must honor. It does not apply to ordinary feature work.

Every such plan arrives with a reason to add a step, and none arrives with a reason to
remove one, so the process only ever grows. That growth is invisible per plan and obvious
in aggregate: each new rule is individually defensible, and the sum is a workflow where a
small change costs more than it is worth. Nothing in this skill previously asked the
question, which is why it kept happening.

So a plan that adds a mandatory step states, in its Research Summary, one of:

- **Removes:** the obligation it retires, or the one it subsumes; or
- **Replaces:** the step it supersedes rather than sits beside; or
- **Adds, net:** the new obligation with its **cost** (what it makes every future run do)
  and **what it catches that nothing else does** — a step that duplicates an existing
  check's coverage is not new protection, it is new cost.

The third option is legitimate and expected; the point is that it must be *argued*, not
assumed. A run cannot be asked to weigh a cost nobody wrote down.

**The honest test for an existing obligation: has it ever caught a real defect?** Not
"could it in principle" — has it, in this repo's history. An obligation that has produced
only false alarms, or only findings about itself, is a candidate for the `Removes:` line of
the next plan that touches its area.

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

Save to `<portfolio_home>/plans/YYYY-MM-DD-<topic>-plan.md`. The literal template — Research
Summary, Decisions in force, Preflight, per-stage tasks with their fields, and the gate
shape — is `references/plan-document-template.md`. Copy it there rather than reconstructing it from
memory; the parser-safety rules (a non-checkbox bullet in Decisions in force, the exact
`- **Status:** [ ]` form) are why it is a fixture rather than a sketch.
## Phase 3 — The Red-Green Loop

Every task carries a `Test:` and a `Red-Green max cycles:` because execution drives them
through a diagnose → fix → retest loop with a bounded budget. The loop itself is
`executing-plans` Step 3.3 and is not restated here. What the plan owes it: a test that is a
**runnable command or a checkable criterion**, never "should work", and a cycle budget
(default 3).
## Phase 4 — Stage Gates

After all tasks in a stage pass their individual tests, run a stage-level integration check before proceeding to the next stage. Individual tests prove each piece works. Stage gates prove the pieces work together.

### What a stage gate checks

- **Integration**: The tasks in this stage interact correctly (e.g., the API endpoint serves data from the database schema that was just created)
- **Regressions**: Scoped to the gate's position in the plan. Intermediate gates check at **stage-scope** — cheap host-side checks (unit tests, lint, static/architecture checks, build) run in full, and any expensive suite (device/instrumented/e2e) is restricted to the modules the stage touched, never `clean`. The final gate (and close-out) runs **plan-scope** — one full clean pass, quarantined slow tests included. If the project's full suite is cheap (well under ~5 min), skip the tiering and just run it in full at every gate. Scope policy: references/test-scope-tiers.md.
- **Goal verification**: The stage's stated goal is actually met end-to-end, not just task-by-task
- **Live artifact over static checks**: Where the stage produces something runnable, at least one gate check launches it and drives the user-visible flow (run the app, hit the endpoint, click the screen). Unit tests pass on stubbed features; only live interaction catches them

### Every fact has one owner

**A fact a task's `Test:` proves is not re-proved at the gate.** Write each gate check to
verify something no task test already decides — integration between the stage's tasks, the
stage's goal end-to-end, regressions. A check that re-runs the task's own assertion buys
nothing: the task cannot be green without it.

Two exceptions, and they are the useful cases:

- **A strictly wider set.** A gate check may cover ground a task test could not, provided
  the widening is *nameable*: "the task proved the column is gone from the migration; the
  gate sweeps the whole source tree for the vocabulary". That is the class-predicate rule
  below doing its job — the gate owns the *class*, the task owns its *instance*.
- **A different mechanism proving a different claim.** A test asserting the code behaves
  and a sweep asserting no stale prose survives are two facts, not one fact twice.

**A `(judgment)` line may never restate a fact an executable check in the same plan already
decides.** The marker routes to an evaluator dispatch — the most expensive check in the
plan — so spending it on a question a command has already answered is the worst version of
this defect. Reserve it for what genuinely needs a reader.

Observed live (remote-agents `bot-live-view` sub-plan 01, 2026-08-10): a single fact —
view-expiry was removed — was verified four times, by a task test asserting no `expires_at`
column, a Stage-1 gate grep, the same grep repeated at close-out, and a `(judgment)` line
asking an evaluator to confirm no surviving claim that a view can expire. Two of those are
legitimate and distinct: the task test (this migration is right) and one tree-wide sweep
(the vocabulary is gone everywhere). The repeat and the judgment line were cost with no
coverage behind it.

### Write a set-valued check as the sweep that proves it

**A gate check over a set is an executable sweep, not a spot check** (DEC-005). A check that
names one artifact where the goal is a property of many cannot fail on the siblings that make
the defect class — they survive the gate, and each survivor costs another remediation round.
So a check whose goal quantifies over a set is written as the command that sweeps it:
`! grep -rl '<the stale claim>' <scope>` rather than "file X no longer says Y".

A check that genuinely needs a reader carries the **(judgment)** marker and routes to the
gate's evaluator — the sanctioned escape hatch, not a loophole.

Verify before presenting: `python3 scripts/validate-gate-checks.py <plan>` (in this skill's
directory). **A newly authored plan may not be presented while it reports INSTANCE-SHAPED.**

Worked examples, the predicate-vs-instance test, and the validator's classification rules:
`references/set-valued-checks.md`.

### When a stage gate fails

If the gate fails, the problem is usually in how tasks interact, not in any single task. But
it is also rarely a *single instance*: treat the failure as a defect class sampled once, name
the set the finding quantifies over, and make the repair test the **sweep over that set** —
otherwise the siblings survive and each costs another round.

That rule is not gate-only in `executing-plans` — it fires wherever a defect surfaces
(a RED test, a review finding, something noticed while editing), and a gate is simply its
sharpest caller. What matters at *authoring* time is unchanged either way.

`executing-plans` owns the operative procedure and is the single source of truth for it —
severity classification (Critical / Important / Suggestion), a bounded remediation budget
defaulting to 2 rounds, an exit criterion that passes when no Critical remains and every
Important is fixed (the `backlog` takes a significant improvement or a decision the user must
make, never a defect found while running the plan), and escalation with a residual list on
exhaustion. Do not restate those rules here; a second copy is how the two drift apart. What
matters at *authoring* time is that the plan's gate checks are shaped so a class can fail
them at all — which is the class-predicate rule above.

---

## Phase 5 — Parallel Execution

Mark a task `Parallel: YES` when its `Depends on` are satisfiable independently and it
shares no file with a sibling. What the plan owes the dispatch path is accurate `Depends on` / `Blocks` / `Parallel` fields
and a file-conflict-free set — the fields' meaning is § Stage structure's to state.

The dispatch procedure itself — how tasks are selected, briefed, routed to a stack-matched
subagent, and integrated — belongs to `../dispatching-parallel-agents/SKILL.md` and
`executing-plans` Step 3.2, and is deliberately not restated here. What the *plan* owes them
is accurate `Depends on` / `Blocks` / `Parallel` fields and a file-conflict-free set.
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
- [ ] Every gate check asserting a property of a **set** is an executable sweep over that set, or carries the `(judgment)` marker naming why a reader must verify it, or — where one artifact genuinely *is* the whole set — the `(scoped)` marker saying why. No check names one artifact where the goal is a property of many, and none is widened past the set its claim is over, which produces a check that cannot pass at all (`scripts/validate-gate-checks.py` reports zero INSTANCE-SHAPED; see `references/set-valued-checks.md`)
- [ ] **One owner per fact**: no gate check re-proves what a task's `Test:` already decides, unless it sweeps a strictly wider, nameable set; and no `(judgment)` line restates a fact an executable check in this plan already answers (§ Every fact has one owner)
- [ ] The research summary has actual findings, not placeholders
- [ ] Preflight checks cover all tools, deps, and access needed by the plan
- [ ] If the project's full suite is expensive (>~5 min): the plan declares its stage-scope and plan-scope commands, only the final gate runs the full clean pass, and any single test >~2 min is quarantined behind an opt-in filter (references/test-scope-tiers.md)
- [ ] Every task that changes more than one artifact carries a `Scope:` naming that set, derived from a command that was actually run rather than recalled; single-artifact tasks correctly omit it
- [ ] Every task has both `Depends on` and `Blocks` fields — and they're symmetric
- [ ] Every task has a `Parallel` field (YES/NO) consistent with its dependencies
- [ ] No two parallel tasks modify the same files
- [ ] The plan is saved to the project's `<portfolio_home>/plans/` in the vault (project auto-registered + sidecar carries the `PORTFOLIO-STATUS` block whose **Plans:** pointer reaches the new plan); or `docs/plans/` only in the no-`vault_dir` fallback
- [ ] Open backlog items in scope were reviewed; folded-in items carry a `Closes BL-NNN` reference on the task that closes them
- [ ] Workflow specs in scope were read; any altered or removed behavior is declared on the corresponding task (`Changes WF-NNN` / `Removes WF-NNN`); new flows have a capture/extend task
- [ ] If an architecture doc exists for this topic: every structure-creating task cites its ARCH-ID, the final stage gate carries the architecture-conformance check, and no task contradicts an approved ARCH section
- [ ] The decisions scan ran and its result is written into `## Decisions in force` (including the explicit `none — registers consulted: …` form, and `project register: absent` on a new project); tasks constrained by an entry cite it (`Honors DEC-NNN`), any deliberate override cites it (`Supersedes …— <why>`), and the final stage gate carries the decisions-conformance check

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
