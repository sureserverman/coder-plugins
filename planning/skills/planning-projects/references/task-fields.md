# Task and stage field specs

The per-field rules a plan's tasks carry. `planning-projects` Phase 2 sets the
structure; this is the reference for each field's exact semantics.

### `Review: skip` — an authored field, never an executor's

Both review tiers are default-on in `executing-plans`. A task may carry `Review: skip` to
turn them off for that task — but **only when the user has said so**, and the field exists
in this template precisely so the annotation has a provenance: it lands in the plan the
user reads and approves, before execution starts.

Do not add it on your own judgment that a task looks trivial. `executing-plans` already
auto-skips genuinely non-code diffs (docs-only, config-only, pure version bumps) without
any annotation, so the field is not needed for that case — its only job is to record a
*user's* decision. An executor that adds it mid-run is recording its own decision as the
user's, which is why `executing-plans` snapshots these annotations at Preflight and honors
only the ones present at the run's base commit (`../../executing-plans/SKILL.md` § Dispatch
roster and capability probe, and § Review opt-out).

Omit the field entirely on every task the user did not name. An absent field is the
default; `Review: run` is not a thing.

### Scope marking (the set a task changes)

A task that changes a **class** of artifact declares the set it must sweep, on a `Scope:`
field:

```
Scope: every commands/*.md, each skills/*/SKILL.md, both scripts' --help
```

This is the authoring-time half of the class-predicate rule. The gate check proves the set
was swept; `Scope:` is where the set gets **named**, before anyone starts editing — so the
surfaces are enumerated once rather than discovered one gate round at a time.

**Conditional, not universal.** Declare it only when the task changes more than one
artifact. A task editing exactly one file has no set, and writing `Scope: this file`
everywhere is noise that trains readers to skip the field. No `Scope:` on a
single-artifact task is correct, not missing.

**Derive the set with a command; do not type it from memory.** This is the failure mode
worth naming, because it is not carelessness and it survives careful authors:

> A plan authored in this repo enumerated "every doc naming the host-side mount vars" as
> three files, from a `grep` whose output had been truncated by `head -40`. A fourth doc
> existed. The task shipped covering three; the stage gate's set-valued check found the
> fourth. A `Scope:` line is only as trustworthy as the sweep behind it — paste the
> command you ran, not the answer you remember.

So: run the sweep, and prefer a `Scope:` that names the **command** (`Scope: every file
matching grep -rl 'X' src/ — 7 files at authoring time`) over one that names a
hand-copied list. A count is useful precisely because it is falsifiable later.

**There is an automated backstop.** `../scripts/validate-gate-checks.py` reports a stage that
declares a `Scope:` whose gate contains neither an executable sweep nor a `(judgment)`
marker — the set named but not swept. It is advisory (it never changes an exit code), so
treat it as a reminder, not a gate.

**Masters carry no `Scope:`.** A master plan has no tasks (`master-plan-format.md`),
so the field never appears there and its parser-safety invariant is untouched.

### Dependency marking

Every task and stage carries two dependency fields — this makes the graph navigable in both directions:

- **Depends on**: What must be green before this task/stage can start
- **Blocks**: What is waiting on this task/stage to finish

These fields are symmetric: if Task 2.1 depends on Task 1.3, then Task 1.3 must list Task 2.1 in its Blocks field. This redundancy is intentional — when a task finishes, you can immediately see what it unblocks without scanning the entire plan.

Mark each task's **Parallel** field. It is a directive to the executor, not a description
of the task: `executing-plans` dispatches every `Parallel: YES` task to a subagent (its
Step 3.2), it does not merely note that a subagent *could* handle it.
- **YES** if the task has no unfinished dependencies (all its `Depends on` items are green
  or "none") — it is dispatched, whether or not another ready task exists to run alongside
  it. A lone ready task with no concurrent sibling is still dispatched, not inlined for
  lack of one.
**A file conflict is expressed as a dependency, never as a downgraded `Parallel` field.**
Two dependency-free tasks that touch the same file cannot both be `YES` (the checklist
forbids two parallel tasks modifying one file), but neither is `NO` in the field's own
terms, because `NO` means *blocked by a dependency* and there is none. Resolve it where it
belongs: add an explicit `Depends on` edge serialising the two at authoring time, then the
second task is `NO` for the ordinary reason. Downgrading the field instead would reintroduce
exactly the reading this section removes — that `Parallel` describes whether things happen
to run side by side, rather than instructing the executor to dispatch.

- **NO** if it's blocked — list which dependency is blocking it. (Once unblocked, `NO`
  defaults to the main session, but `executing-plans` may still delegate it to a subagent
  on its own context-hygiene criteria — that decision doesn't depend on having a
  concurrent sibling either.)

### Ordering rules

1. **Stages are sequential.** Stage 2 does not start until Stage 1's gate passes
2. **Tasks within a stage follow their dependency graph.** If Task B needs output from Task A, Task A comes first — this isn't optional, it's structural
3. **Independent tasks are dispatched, and run in parallel.** If Tasks 2.3 and 2.4 have no dependency on each other and touch no common file, both are dispatched and run simultaneously — and if only Task 2.3 is ready, it is dispatched by itself. "Can" describes the schedule, not the obligation: whether they overlap in time is a scheduling consequence, whereas dispatching each to a subagent is the instruction their `Parallel: YES` carries
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
