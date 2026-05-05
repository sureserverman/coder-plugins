# planning

A four-skill pipeline that turns a vague idea into executed work. Each skill hands off to the next; they were designed as a unit.

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

## Why a separate plugin

The four skills reference each other by name (handoffs from brainstorming → planning-projects → executing-plans → dispatching-parallel-agents). Splitting them across plugins would break the handoff. They have no transitive runtime dependencies and can be installed alongside any other plugin without conflict.

## License

MIT
