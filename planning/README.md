# planning

A nine-skill pipeline (v0.5.0) that turns a vague idea into executed work, keeps each project's contracts honest, and gives a cross-project portfolio view across `~/dev/`. Each skill hands off to the next; they were designed as a unit.

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

Use **before** any non-trivial creative or implementation work — new features, refactors, migrations, behavior changes. Turns a vague idea into a validated design by exploring purpose, constraints, alternatives, and risks one question at a time. Terminal handoff is to `planning-projects`.

**Triggers:** "I'm thinking about adding X", "what's the best way to", "should I refactor", "design a new", "let's brainstorm".

### `planning-projects`

Produces a staged plan for a non-trivial project with phase gates before execution. Plans use a strict format with Stages, Tasks, `Depends on` / `Blocks` / `Parallel` fields, Red-Green max cycles, and Stage gates that `executing-plans` can drive mechanically.

**Triggers:** "plan", "roadmap", "how should I build", "break this down", "what are the steps", "create a plan", "what order should I do this".

### `executing-plans`

Takes a plan file produced by `planning-projects` and executes it. Drives Red-Green loops, respects the stage-gate model, and dispatches independent tasks through `dispatching-parallel-agents`.

**Triggers:** "execute this plan", "run the plan", "drive this plan to green", "work the plan in plan.md".

### `dispatching-parallel-agents`

Used by `executing-plans` (or directly) when a set of tasks is marked `Parallel YES` and all their dependencies are green. Dispatches one agent per task, runs them concurrently, integrates results respecting the plan's dependency graph.

**Triggers:** "dispatch these tasks in parallel", "run these in parallel", "fan out the parallel-marked tasks".

### `no-fafo-debugging`

The diagnostic counterpart to the pipeline. Blocks "Fix And Forget" — speculative patches that make the symptom go away without explaining root cause. Use when a plan task fails red and the fix is non-obvious, or any time you're tempted to propose a fix without first answering *what*, *why*, and *how*.

**Triggers:** "debug this", "why is X broken", "fix this bug", any diagnostic request where evidence-first root-cause analysis is expected over speculative patches.

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

### `portfolio` (NEW in v0.5.0)

Cross-project orchestrator. Single user-facing entry point that ties registry + per-project unification + per-project maturity into one command. Subcommands:

- `scan` — load `~/.claude/projects-registry.yaml`, walk `~/dev/` for project markers, surface drift; first-run flow auto-seeds the registry.
- `unify` — dispatches a sub-agent per registered project (8 in flight) that invokes `backlog unify`. Aggregates candidate reports; user accepts per-project.
- `maturity` — dispatches a sub-agent per project that invokes `project-maturity audit`; surfaces stale claims.
- `rebuild` — regenerates `~/.claude/global-backlog.md` and `~/.claude/global-maturity.md`. Preserves a `<! BEGIN PRESERVE !>` ... `<! END PRESERVE !>` block in `global-backlog.md` for hand-curated cross-project items.

Default flow composes the four in order: `scan → unify (dry-run) → maturity (opt-in during staged rollout) → rebuild`. Idempotent: re-running with no upstream changes produces zero writes.

**Triggers:** "portfolio scan", "global backlog", "what's parked across projects", "ship readiness across projects", "scan all my projects".

## Why a separate plugin

All nine skills reference each other by name (handoffs from brainstorming → planning-projects → executing-plans → dispatching-parallel-agents; planning-projects/executing-plans ↔ backlog and workflow-spec; portfolio → backlog + project-maturity + dispatching-parallel-agents). Splitting them across plugins would break the handoffs. They have no transitive runtime dependencies and can be installed alongside any other plugin without conflict.

## License

MIT
