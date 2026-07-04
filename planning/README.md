# planning

A ten-skill pipeline (v0.12.0) that turns a vague idea into executed work — including redesigning an app to a Claude Design handoff — keeps each project's contracts honest, and gives a cross-project portfolio view across `~/dev/`. Each skill hands off to the next; they were designed as a unit.

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
planning-projects       ── stage the work: tasks with Depends on / Blocks /
    │                      Parallel fields, Red-Green max cycles, stage gates.
    ▼
executing-plans         ── drive the plan: Red-Green loops, respect stage
    │                      gates, fan independent tasks out for parallel run.
    ▼
dispatching-parallel-agents  ── one agent per task marked Parallel YES whose
                               dependencies are all green; integrate results
                               respecting the dependency graph.
```

## Skills

### `brainstorming`

Use **before** any non-trivial creative or implementation work — new features, refactors, migrations, behavior changes. Turns a vague idea into a validated design by exploring purpose, constraints, alternatives, and risks one question at a time. Terminal handoff is to `architecting-projects` (designs with a structural surface) or straight to `planning-projects`.

**Triggers:** "I'm thinking about adding X", "what's the best way to", "should I refactor", "design a new", "let's brainstorm".

### `architecting-projects` (NEW in v0.17.0)

Use after a design is validated (or on a direct architecture request) to produce a researched, user-approved architecture document that `planning-projects` consumes. Derives 2–4 stack-concrete candidates, fans out one sonnet-pinned `architecture-researcher` agent per candidate in parallel (uncited claims are discarded), presents a comparison matrix for explicit approval, then writes a parser-safe `*-architecture.md` with stable `ARCH-NN` section IDs beside the plan. Plans cite the ARCH-IDs on structure-creating tasks and carry an architecture-conformance check in their final stage gate.

**Triggers:** "design the architecture", "architecture options", "how should the codebase be structured", "compare architecture candidates", "pick an architecture".

### `planning-projects`

Produces a staged plan for a non-trivial project with phase gates before execution. Plans use a strict format with Stages, Tasks, `Depends on` / `Blocks` / `Parallel` fields, Red-Green max cycles, and Stage gates that `executing-plans` can drive mechanically.

For big projects (roughly >6 stages / >25 tasks, or multiple independently shippable workstreams) it **decomposes** the work into 2–7 independently executable **sub-plans** linked by one **master plan**: the master holds the shared research, a sub-plan register (Status / plan link / Goal / cross-plan `Depends on`+`Blocks` / `Parallel`), and a `**Gate:**` block of integration checks per entry. The canonical format lives in `skills/planning-projects/references/master-plan-format.md` and is parser-safe by construction — a master plan yields zero backlog candidates in `portfolio unify` (locked by the `validate-plan-parser` CI fixture suite); the sub-plans carry the real tasks.

**Triggers:** "plan", "roadmap", "how should I build", "break this down", "what are the steps", "create a plan", "what order should I do this".

### `executing-plans`

Takes a plan file produced by `planning-projects` and executes it. Drives Red-Green loops, respects the stage-gate model, and dispatches independent tasks through `dispatching-parallel-agents`. Also executes **master plans** (`*-master-plan.md`): sub-plans run in register dependency order, each via the normal single-plan flow (ideally one per fresh session — the master file is the cross-session handoff artifact); each sub-plan completion flips its register `Status`, runs that entry's cross-plan `**Gate:**` checks, and commits `"Sub-plan N green"`; version bumps are deferred from sub-plan close-outs to the single master close-out.

Preflight includes a **git bootstrap** — if the project isn't a repo it runs `git init` (and offers a GitHub remote) so the per-task commits have somewhere to land. Execution **runs to completion**: stage gates are checkpoints, not approval gates, so it doesn't pause between green stages to ask permission — only the documented stop conditions halt it. At each stage gate it invokes a matching **platform stage-verify skill** (Android → `android-stage-verify`: build the debug APK, and if an adb device is attached, install + smoke-launch + run instrumented tests). At close-out it **bumps versions** for whatever the plan changed, across every mirror of the version string (e.g. a plugin's `plugin.json` and the root `marketplace.json`).

**Triggers:** "execute this plan", "run the plan", "drive this plan to green", "work the plan in plan.md".

### `applying-design-handoff`

Redesigns an app to **precisely reproduce a Claude Design handoff pack** (the spec bundle from claude.ai/design — tokens, components, layout, assets), reshaping functionality to fit the design where they conflict. Auto-detects the input (a local exported bundle or a live claude.ai design-system project via the `DesignSync` tool), inventories the app and its `workflow-spec` contracts, builds a design→app fidelity map, and writes a **reconciliation report** — the design wins, but every behavior change is declared via `workflow-spec` (`Changes`/`Removes WF-*`) and destructive changes require user sign-off. Implementation is cross-platform: it delegates to the matching `ui-*` agent for platform idiom and to the **`design-handoff-reproducer`** subagent for precise per-slice reproduction, then runs a fidelity verify loop (separate evaluator, rubric-graded, max 3 iterations). `executing-plans` drives it for a design-handoff/redesign task and fires the fidelity loop as a stage-gate hook.

**Triggers:** "reproduce this design", "apply the handoff pack", "redesign to match the design", "implement the Claude Design spec".

### `dispatching-parallel-agents`

Used by `executing-plans` (or directly) when a set of tasks is marked `Parallel YES` and all their dependencies are green. Dispatches one agent per task, runs them concurrently, integrates results respecting the plan's dependency graph.

**Triggers:** "dispatch these tasks in parallel", "run these in parallel", "fan out the parallel-marked tasks".

### `no-fafo-debugging`

The diagnostic counterpart to the pipeline. Blocks "Fix And Forget" — speculative patches that make the symptom go away without explaining root cause. Fires at the **start of any debugging or diagnostic work**, not just when a plan task fails red: the moment a symptom, error, failing test, crash, or "it's not working" shows up, before the first hypothesis. Also drives evidence-first **autonomy** — Claude reads logs, runs read-only diagnostics, reproduces failures, and builds interceptors/probes *itself*, escalating to the user only when genuinely blocked (access it lacks, a world-action only the user can take, or a decision only they can make) — and when it must ask, it asks once, batched and specific.

**Triggers:** "debug this", "why is X broken", "fix this bug", "diagnose", "investigate", "it's not working", "tests are failing", a stack trace / error / crash / hang / regression — any diagnostic request where evidence-first root-cause analysis is expected over speculative patches.

### `backlog` (v0.4.0+; v0.5.0 adds `unify` + `complete`)

Owns the per-project deferred-work register at `docs/backlog.md`. Append on defer, remove on implement, list on plan research. v0.5.0 adds:

- `unify <project-path>` — derive backlog candidates from this project's plans via the parser rules in `portfolio/references/plan-parser.md`. Dedups by exact `Source` string equality. Dry-run by default.
- `complete <BL-NNN> --summary "<text>"` — archive a backlog item as a short `docs/plans/YYYY-MM-DD-<slug>-done.md` plan-summary and remove the entry. Commit convention `Closes BL-NNN` remains the audit trail.

**Triggers:** "add to backlog", "defer this", "what's in the backlog", "BL-007 is done", "unify plans and backlog for this project".

### `workflow-spec` (v0.4.0+)

Owns behavior contracts at `docs/workflows/`. Provides `capture`, `extend`, `audit` subcommands so behavior changes can be detected against a versioned spec.

**Triggers:** "capture this workflow", "audit workflows against the diff", "this PR changes documented behavior".

### `project-maturity` (NEW in v0.5.0)

Scaffolds and audits a per-project `docs/MATURITY.md` checklist across six publishing-readiness axes: Documentation, Security, Packaging, UI/UX, i18n, Testing & CI. Three subcommands:

- `init <project-path>` — scaffold MATURITY.md from a template.
- `audit <project-path> [--write]` — run deterministic auto-detectors (file globs, sec-audit-report findings parse, packaging-recipe presence, locale dirs, CI workflow detection). Dry-run by default. Never overwrites manual `[x] claim:` lines.
- `get <project-path>` — return parsed state as JSON for the portfolio orchestrator.

**Triggers:** "scaffold maturity", "is this ready to publish", "ship-readiness", "init MATURITY.md".

**v0.5.1:** the UI/UX icon auto-detector now recognizes the WebExtension layout — an `icons/` dir holding `icon*.{png,svg}` beside a `manifest.json` (e.g. `mozilla/icons/`, `chrome/icons/`, or root `icons/`) — in addition to root-level `icon.*`/`app-icon.*` and Android `res/mipmap-*`.

### `portfolio` (NEW in v0.5.0)

Cross-project orchestrator. Single user-facing entry point that ties registry + per-project unification + per-project maturity into one command. Subcommands:

- `scan` — load `~/.claude/projects-registry.yaml`, walk `~/dev/` for project markers, surface drift; first-run flow auto-seeds the registry.
- `unify` — dispatches a sub-agent per registered project (8 in flight) that invokes `backlog unify`. Aggregates candidate reports; user accepts per-project.
- `maturity` — dispatches a sub-agent per project that invokes `project-maturity audit`; surfaces stale claims.
- `rebuild` — regenerates `~/.claude/global-backlog.md` and `~/.claude/global-maturity.md`. Preserves a `<! BEGIN PRESERVE !>` ... `<! END PRESERVE !>` block in `global-backlog.md` for hand-curated cross-project items.

Default flow composes the four in order: `scan → unify (dry-run) → maturity (opt-in during staged rollout) → rebuild`. Idempotent: re-running with no upstream changes produces zero writes.

**Triggers:** "portfolio scan", "global backlog", "what's parked across projects", "ship readiness across projects", "scan all my projects".

## Why a separate plugin

All twelve skills reference each other by name (handoffs from brainstorming → architecting-projects → planning-projects → executing-plans → dispatching-parallel-agents; executing-plans → applying-design-handoff for redesign tasks; planning-projects/executing-plans ↔ backlog and workflow-spec; portfolio → backlog + project-maturity + dispatching-parallel-agents). Splitting them across plugins would break the handoffs. They have no transitive runtime dependencies and can be installed alongside any other plugin without conflict.

## License

MIT
