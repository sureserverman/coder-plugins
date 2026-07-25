# planning

A fourteen-skill pipeline (v0.25.0) that turns a vague idea into executed work — including redesigning an app to a Claude Design handoff — keeps each project's contracts honest, and gives a cross-project portfolio view across `~/dev/`. Each skill hands off to the next; they were designed as a unit.

## Installation

Add the marketplace:
```bash
/plugin marketplace add sureserverman/coder-plugins
```

Install the plugin:
```bash
/plugin install planning@coder-plugins
```

## The pipeline

```
compass                 ── (optional entry point) what's in flight, what to
    │                      work on next, what's going stale — across every
    │                      project. Report-only; picks the work, never runs it.
    ▼
vague idea
    │
    ▼
brainstorming           ── validate the design via Q&A: purpose, constraints,
    │                      alternatives, risks. One question at a time.
    ▼
architecting-projects   ── (designs with a structural surface) research 2–4
    │                      architecture candidates via parallel researcher
    │                      agents, user approves one, write the ARCH-ID doc.
    ▼
planning-projects       ── triage a format first (Direct / Light / Standard /
    │                      Master), then stage the work: tasks with Depends on /
    │                      Blocks / Parallel fields, Red-Green cycles, gates.
    ▼
executing-plans         ── drive the plan: Red-Green loops, tiered test-scope
    │                      gates, fan independent tasks out for parallel run.
    ▼
dispatching-parallel-agents  ── one agent per task marked Parallel YES whose
                               dependencies are all green; integrate results
                               respecting the dependency graph.

  ┌─ cross-cutting, no fixed position in the flow ────────────────────────┐
  │ honest-gates       ── the integrity contract every gate above obeys.  │
  │ capability-router  ── reach a marketplace skill/agent whose plugin    │
  │                       isn't enabled this session.                     │
  └───────────────────────────────────────────────────────────────────────┘
```

## Skills

### `brainstorming`

Use **before** any non-trivial creative or implementation work — new features, refactors, migrations, behavior changes. Turns a vague idea into a validated design by exploring purpose, constraints, alternatives, and risks one question at a time. Terminal handoff is to `architecting-projects` (designs with a structural surface) or straight to `planning-projects`.

**Triggers:** "I'm thinking about adding X", "what's the best way to", "should I refactor", "design a new", "let's brainstorm".

### `architecting-projects` (since v0.17.0)

Use after a design is validated (or on a direct architecture request) to produce a researched, user-approved architecture document that `planning-projects` consumes. Derives 2–4 stack-concrete candidates, fans out one sonnet-pinned `architecture-researcher` agent per candidate in parallel (uncited claims are discarded), presents a comparison matrix for explicit approval, then writes a parser-safe `*-architecture.md` with stable `ARCH-NN` section IDs beside the plan. Plans cite the ARCH-IDs on structure-creating tasks and carry an architecture-conformance check in their final stage gate. On existing codebases, **re-architecture mode** (v0.18.0) inventories the current module map, requires each candidate's research to address the migration explicitly, and adds an `ARCH-NN Migration map` section whose ordered, build-green steps seed the plan's stage order.

**Triggers:** "design the architecture", "architecture options", "how should the codebase be structured", "compare architecture candidates", "pick an architecture".

### `planning-projects`

Produces a staged plan for a non-trivial project with phase gates before execution. Plans use a strict format with Stages, Tasks, `Depends on` / `Blocks` / `Parallel` fields, Red-Green max cycles, and Stage gates that `executing-plans` can drive mechanically.

**Format ladder (since v0.22.1).** Every request is triaged to a format *first*, so the apparatus scales to the size of the job — and a trivial request may be declined a plan file entirely:

| Format | Shape | Use when |
|---|---|---|
| **Direct** | no plan file — just do it | the job is trivial and self-evident |
| **Light** | one stage, 2–5 tasks, one gate (`*-light-plan.md`) | small but worth a test-and-gate backbone |
| **Standard** | multiple stages, full task fields, per-stage gates | the default for non-trivial work |
| **Master** | 2–7 sub-plans linked by a register (`*-master-plan.md`) | >~6 stages / >~25 tasks, or several independently shippable workstreams |

The Light and Master formats are specified in `skills/planning-projects/references/light-plan-format.md` and `master-plan-format.md`; both are parser-safe by construction (zero `portfolio unify` backlog candidates, locked by the `validate-plan-parser` CI fixture suite).

For big projects (roughly >6 stages / >25 tasks, or multiple independently shippable workstreams) it **decomposes** the work into 2–7 independently executable **sub-plans** linked by one **master plan**: the master holds the shared research, a sub-plan register (Status / plan link / Goal / cross-plan `Depends on`+`Blocks` / `Parallel`), and a `**Gate:**` block of integration checks per entry. The canonical format lives in `skills/planning-projects/references/master-plan-format.md` and is parser-safe by construction — a master plan yields zero backlog candidates in `portfolio unify` (locked by the `validate-plan-parser` CI fixture suite); the sub-plans carry the real tasks.

**Triggers:** "plan", "roadmap", "how should I build", "break this down", "what are the steps", "create a plan", "what order should I do this".

### `executing-plans`

Takes a plan file produced by `planning-projects` and executes it. Drives Red-Green loops, respects the stage-gate model, and dispatches independent tasks through `dispatching-parallel-agents`. It executes every rung of the format ladder — a **light plan** runs with proportionate machinery (Preflight-lite, inline no-parallel execution, one whole-diff review instead of per-task Tier-1, opt-in evaluator, a single stated version bump). Also executes **master plans** (`*-master-plan.md`): sub-plans run in register dependency order, each via the normal single-plan flow (ideally one per fresh session — the master file is the cross-session handoff artifact); each sub-plan completion flips its register `Status`, runs that entry's cross-plan `**Gate:**` checks, and commits `"Sub-plan N green"`; version bumps are deferred from sub-plan close-outs to the single master close-out.

Preflight includes a **git bootstrap** — if the project isn't a repo it runs `git init` (and offers a GitHub remote) so the per-task commits have somewhere to land. Execution **runs to completion**: stage gates are checkpoints, not approval gates, so it doesn't pause between green stages to ask permission — only the documented stop conditions halt it. At each stage gate it invokes a matching **platform stage-verify skill** (Android → `android-stage-verify`: build the debug APK, and if an adb device is attached, install + smoke-launch + run instrumented tests). At close-out it **bumps versions** for whatever the plan changed, across every mirror of the version string (e.g. a plugin's `plugin.json` and the root `marketplace.json`).

**Tiered test-scope gates (v0.24.0).** Gates run the tests their tier warrants rather than the whole suite every time — cheap host-side checks always run in full, expensive suites (device / instrumented / e2e) are scoped:

- **fix-scope** — after a review fix inside a Red-Green cycle: the task's own `Test:` plus the test classes the fix touched.
- **stage-scope** — at an intermediate stage gate: restricted to the modules the stage's commits touched, never `clean`.
- **plan-scope** — exactly one clean full pass, at close-out (the final stage's gate runs at this tier).

A scoped gate report always discloses what actually ran. Policy lives in `skills/planning-projects/references/test-scope-tiers.md`, shared with `planning-projects`.

**Two-tier code review.** Execution wires in `git-github`'s read-only `code-reviewer` agent on a distinct axis from the goal-evaluator (*code quality* vs *goal attainment*): **Tier 1** on each green task's diff, where a Critical finding blocks the task and is fixed within the same Red-Green cycle budget; **Tier 2** on the full stage diff at the gate, where a Critical is a gate failure and advisories are surfaced for triage. Trivial/non-code diffs are auto-skipped.

**Live progress.** Execution state is mirrored to `.claude/plan-progress.json` at every transition, and `scripts/plan-progress.py` renders it as a statusline progress bar (`⚙ plan ▐██████░░░░▌ 3/6 (50%) · S2/3 ▶ T2.2 …`). It chains after any existing statusline and prints nothing when no plan is executing; done/total are derived from the plan's authoritative `Status:` fields, so a missed update can never show wrong progress.

**Triggers:** "execute this plan", "run the plan", "drive this plan to green", "work the plan in plan.md".

### `applying-design-handoff`

Redesigns an app to **precisely reproduce a Claude Design handoff pack** (the spec bundle from claude.ai/design — tokens, components, layout, assets), reshaping functionality to fit the design where they conflict. Auto-detects the input (a local exported bundle or a live claude.ai design-system project via the `DesignSync` tool), inventories the app and its `workflow-spec` contracts, builds a design→app fidelity map, and writes a **reconciliation report** — the design wins, but every behavior change is declared via `workflow-spec` (`Changes`/`Removes WF-*`) and destructive changes require user sign-off. Implementation is cross-platform: it delegates to the matching `ui-*` agent for platform idiom and to the **`design-handoff-reproducer`** subagent for precise per-slice reproduction, then runs a fidelity verify loop (separate evaluator, rubric-graded, max 3 iterations). `executing-plans` drives it for a design-handoff/redesign task and fires the fidelity loop as a stage-gate hook.

**Triggers:** "reproduce this design", "apply the handoff pack", "redesign to match the design", "implement the Claude Design spec".

### `dispatching-parallel-agents`

Used by `executing-plans` (or directly) when a set of tasks is marked `Parallel YES` and all their dependencies are green. Dispatches one agent per task, runs them concurrently, integrates results respecting the plan's dependency graph.

**Triggers:** "dispatch these tasks in parallel", "run these in parallel", "fan out the parallel-marked tasks".

Routing is table-driven: `references/stack-routing.md` maps each task's stack to a matched subagent (`rust-expert`, `ui-android`, `testing-expert`, …). `executing-plans` consults the same table to hand independent, output-heavy *sequential* tasks to a subagent for context hygiene. A CI-enforced `validate-stack-routing.py` check fails the build when the table names an agent or skill the marketplace no longer ships.

### `honest-gates`

The integrity contract behind every gate in this plugin — and any acceptance check, test command, or "done" claim elsewhere. A gate is **GREEN** only when its real command ran *here* and passed; otherwise it is **RED** or **BLOCKED**. Never a stubbed task, fabricated evidence, a hidden exclusion, or a self-graded miss. Includes escalation rules for a genuinely blocked gate, so "I couldn't run it" stays distinguishable from "it passed". Applies eagerly — it does not wait to be asked.

**Triggers:** any point where something must pass, build, run, or be measured — before reporting a gate green, registering a build/test task, or recording test/benchmark evidence.

### `capability-router`

Reaches a marketplace capability — a skill or a subagent — **even when its plugin isn't enabled in this session**. Enablement only controls what Claude Code injects at session start; every component's files are on disk regardless. Looks the capability up in `capability-index.json` and loads it from disk (reading a SKILL.md, or injecting an agent body with its `model` pin). This is the ad-hoc entry point to the same disk-resolution flow `executing-plans` and `dispatching-parallel-agents` use mid-plan. Components that need runtime registration (hooks, MCP) can't be lazy-loaded — those stop and ask you to enable the plugin.

**Triggers:** "load the Rust expert", "which plugin covers X", "write idiomatic Rust", "review my game design".

### `no-fafo-debugging`

The diagnostic counterpart to the pipeline. Blocks "Fix And Forget" — speculative patches that make the symptom go away without explaining root cause. Fires at the **start of any debugging or diagnostic work**, not just when a plan task fails red: the moment a symptom, error, failing test, crash, or "it's not working" shows up, before the first hypothesis. Also drives evidence-first **autonomy** — Claude reads logs, runs read-only diagnostics, reproduces failures, and builds interceptors/probes *itself*, escalating to the user only when genuinely blocked (access it lacks, a world-action only the user can take, or a decision only they can make) — and when it must ask, it asks once, batched and specific.

**Triggers:** "debug this", "why is X broken", "fix this bug", "diagnose", "investigate", "it's not working", "tests are failing", a stack trace / error / crash / hang / regression — any diagnostic request where evidence-first root-cause analysis is expected over speculative patches.

### `backlog` (v0.4.0+; v0.5.0 adds `unify` + `complete`)

Owns the per-project deferred-work register at `docs/backlog.md`. Append on defer, remove on implement, list on plan research. v0.5.0 adds:

- `unify <project-path>` — derive backlog candidates from this project's plans via the parser rules in `portfolio/references/plan-parser.md`. Dedups by exact `Source` string equality. Dry-run by default.
- `complete <BL-NNN> --summary "<text>"` — archive a backlog item as a short `docs/plans/YYYY-MM-DD-<slug>-done.md` plan-summary and remove the entry. Commit convention `Closes BL-NNN` remains the audit trail.

**Triggers:** "add to backlog", "defer this", "what's in the backlog", "BL-007 is done", "unify plans and backlog for this project".

### `decisions` (since v0.27.0)

Owns the architectural-decision register in two linked halves: per-project
`<portfolio_home>/decisions.md` (`DEC-NNN`) and per-architecture-domain
`Portfolio/decisions/<domain>.md` (`GDEC-<DOM>-NNN` — `android`, `ios`, `rust`,
`ubuntu`, …). Every entry carries the **reason** behind the choice: the constraint,
the evidence, the rejected alternative, the accepted cost.

- `add` / `list` / `read` — record and consult decisions for one project.
- `promote <DEC-NNN> --domain <slug>` — lift a project decision into its domain
  register, writing **both** link directions in one step. That symmetry is what
  makes the two halves one register instead of two.
- `supersede` — replace a decision that no longer holds. The old entry stays, marked
  `superseded by DEC-NNN`; its reason is the record of what was believed and why.

`portfolio rebuild` reads both halves, renders `Portfolio/global-decisions.md`
(by-domain index, per-project counts, malformed entries, link asymmetries,
unresolved targets), and adds a `Decisions:` pointer to the repo sidecar. Symmetry
gaps are **reported, never auto-fixed** — repairing one side would assert an edge
about a project the run has not read. `compass-scan.py` surfaces a per-project
`{count, malformed, domains, last_decided}` summary.

**sec-audit recommendations** are recorded here under a hard rule: cite the report by
filename and date, restate its substance in the entry's own words, and
never embed the report body — those reports are local-only and gitignored
across the portfolio.

Format: `portfolio/references/decisions-format.md`.

**Triggers:** "record this decision", "why did we choose X", "log this sec-audit recommendation", "promote this to the android decisions", "what binds all Rust projects".

### `workflow-spec` (v0.4.0+)

Owns behavior contracts at `docs/workflows/`. Provides `capture`, `extend`, `audit` subcommands so behavior changes can be detected against a versioned spec.

**Triggers:** "capture this workflow", "audit workflows against the diff", "this PR changes documented behavior".

### `project-maturity` (since v0.5.0)

Scaffolds and audits a per-project `docs/MATURITY.md` checklist across six publishing-readiness axes: Documentation, Security, Packaging, UI/UX, i18n, Testing & CI. Three subcommands:

- `init <project-path>` — scaffold MATURITY.md from a template.
- `audit <project-path> [--write]` — run deterministic auto-detectors (file globs, sec-audit-report findings parse, packaging-recipe presence, locale dirs, CI workflow detection). Dry-run by default. Never overwrites manual `[x] claim:` lines.
- `get <project-path>` — return parsed state as JSON for the portfolio orchestrator.

**Triggers:** "scaffold maturity", "is this ready to publish", "ship-readiness", "init MATURITY.md".

**v0.5.1:** the UI/UX icon auto-detector now recognizes the WebExtension layout — an `icons/` dir holding `icon*.{png,svg}` beside a `manifest.json` (e.g. `mozilla/icons/`, `chrome/icons/`, or root `icons/`) — in addition to root-level `icon.*`/`app-icon.*` and Android `res/mipmap-*`.

### `compass`

The portfolio **work orchestrator** — decides *what to work on*, where `portfolio` maintains the artifacts. Answers three questions across every registry project, grounded in evidence reconstructed fresh each run (no maintained state, nothing to drift):

- `compass now` — what is in flight? (in-progress plan stages, current task)
- `compass next` — what should I pick up? Ranked by momentum > almost-shippable > unblocking > staleness, with cited evidence on every recommendation.
- `compass review` — a periodic sweep: what's going stale, what's parked, where the gaps are.

The deterministic `compass-scan.py` (CI-guarded, reusing `portfolio-unify`'s plan-parser regexes) rebuilds the cross-project picture from plan stages, backlog open/parked counts, maturity gaps, integration edges, and git recency; the judgment layer only ranks. Respects `Parked:` annotations in backlogs. **Report-only** — it recommends, and never launches work or writes portfolio artifacts.

**Triggers:** "what should I work on next", "what's in flight", "portfolio review", "what's going stale".

### `portfolio` (since v0.5.0)

Cross-project orchestrator. Single user-facing entry point that ties registry + per-project unification + per-project maturity into one command. Subcommands:

- `scan` — load `~/.claude/projects-registry.yaml`, walk `~/dev/` for project markers, surface drift; first-run flow auto-seeds the registry.
- `unify` — dispatches a sub-agent per registered project (8 in flight) that invokes `backlog unify`. Aggregates candidate reports; user accepts per-project.
- `maturity` — dispatches a sub-agent per project that invokes `project-maturity audit`; surfaces stale claims.
- `rebuild` — regenerates `~/.claude/global-backlog.md` and `~/.claude/global-maturity.md`. Preserves a `<! BEGIN PRESERVE !>` ... `<! END PRESERVE !>` block in `global-backlog.md` for hand-curated cross-project items.

Default flow composes the four in order: `scan → unify (dry-run) → maturity (opt-in during staged rollout) → rebuild`. Idempotent: re-running with no upstream changes produces zero writes.

**Triggers:** "portfolio scan", "global backlog", "what's parked across projects", "ship readiness across projects", "scan all my projects".

## Why a separate plugin

All fourteen skills reference each other by name (handoffs from brainstorming → architecting-projects → planning-projects → executing-plans → dispatching-parallel-agents; executing-plans → applying-design-handoff for redesign tasks; planning-projects/executing-plans ↔ backlog and workflow-spec; compass → the plans, backlogs and maturity files portfolio maintains; portfolio → backlog + project-maturity + dispatching-parallel-agents; executing-plans/dispatching-parallel-agents → capability-router's disk-resolution flow; and honest-gates binding every gate the pipeline reports). Splitting them across plugins would break the handoffs. They have no transitive runtime dependencies and can be installed alongside any other plugin without conflict.

## License

MIT
