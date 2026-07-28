---
name: dispatching-parallel-agents
description: Use when executing-plans has Parallel YES tasks from a planning-projects plan whose dependencies are green. Dispatches one agent per task, running concurrently. Triggers on "dispatch these tasks in parallel", "run these Parallel YES tasks", "fan out these independent fixes".
---

# Dispatching Parallel Agents

Fan out independent tasks from a `planning-projects` plan to concurrent sub-agents, collect their results, propagate the dependency graph, and return control to `executing-plans` (or the caller).

This skill is the operational arm of `planning-projects` Phase 5 ("Parallel Execution") and is usually invoked by `executing-plans` rather than the user directly.

**Announce at start:** "Using the dispatching-parallel-agents skill to fan out <N> independent tasks."

---

## Preconditions

Refuse to dispatch unless all are true:

1. **A plan exists** at a known path, produced by `planning-projects`. The plan's task fields (`Depends on`, `Blocks`, `Parallel`, `Test`, `Red-Green max cycles`) are the source of truth.
2. **Every task in scope has `Parallel: YES`** in the plan.
3. **Every task's `Depends on` list is fully green** (every referenced prior task has passed its test and been committed).
4. **No two tasks in scope modify the same file.** This is checked against the plan's declared file paths; if the plan doesn't list files, scan the task descriptions. When in doubt, force sequential.
5. **The stage gate has not yet run.** Dispatches happen before the gate, not after.

If any precondition fails, stop and report which one — do not relax them on your own.

---

## Checklist

Create a task for each:

1. **Select** — identify the set of tasks that satisfy all preconditions
2. **Guard** — verify file-path disjointness; force any conflicting pair sequential
3. **Brief** — construct an agent prompt per task from the plan (see prompt template)
4. **Dispatch** — launch all selected tasks in a single message (multiple Agent calls)
5. **Collect** — wait for every sub-agent to return
6. **Integrate** — commit green results, escalate failures, re-check the dependency graph
7. **Report** — hand control back to `executing-plans` with the updated task status

---

## Phase 1 — Select

From the current stage, identify tasks where:

- `Parallel: YES`
- Every task in `Depends on` is in the completed set (check TodoWrite or plan status notes)
- The task has not already been dispatched or completed

Call this set **S**. A lone ready task is **still dispatched**: |S| = 1 runs as a single
dispatch rather than a fan-out, and is never a reason to hand the task back to the caller.
Having nothing to run alongside it is a fact about *concurrency*, while `Parallel: YES` is
a *delegation* directive — two different properties (`../planning-projects/SKILL.md` § Stage structure). Only |S| = 0 returns control to the caller with nothing to do.

## Phase 2 — Guard against file conflicts

For every pair `(tᵢ, tⱼ)` in S, compare the file paths each task will modify:

- If paths are disjoint → keep both in S
- If paths overlap → remove one from S (prefer keeping the higher-`Blocks`-count task, since it unblocks more downstream work). The removed task is **dispatched on its own after this batch returns** — removing it from S drops it from *this concurrent batch*, never from dispatch. It carries `Parallel: YES`, so it goes to a subagent whenever it runs; the conflict decided *when*, not *whether*.

Also guard against **shared resources** beyond files: same DB table schema migration, same CI config section, same feature flag — these are "logical" file conflicts even when the literal paths differ.

Log which task (if any) was deferred and why.

## Phase 3 — Brief each agent

For each task remaining in S, construct a self-contained prompt. A sub-agent will not see the conversation — it sees only its prompt.

### Prompt template

```
You are a sub-agent executing Task <N.M> from plan <plan-path>.

## Task
<Task description from plan, verbatim>

## Files
<Files from plan, verbatim — Create / Modify / Test paths>

## Context (only what this task needs)
<Extract from Research Summary the 2-4 bullets that bear on this task.
Do NOT paste the entire research summary.>

## Decisions in force
<From the plan's `## Decisions in force`, ONLY the entries bearing on this task —
same discipline as Context above, not the whole section. One line each:
"DEC-003 (accepted) — <the constraint, in the entry's own words>".
If the task line carries `Honors DEC-NNN`, that entry MUST appear here.
If it carries `Supersedes DEC-NNN`, say so and state what replaces it.
Omit the heading entirely when no decision bears on this task.>

## Stack skill — invoke first (omit if the routing table names none)
<Stack skill name from references/stack-routing.md, e.g. rust-coding — load it before editing.
If that skill's plugin isn't enabled, instead: "Read <repo-relative path from capability-index.json>
and follow it" — the same skill body, loaded from disk (see stack-routing.md § Resolving).>

## Execution model (Red-Green loop)
1. Attempt the implementation described by the task
2. Run the Test:
   <Test command, verbatim from plan>
   Expected: <expected pass criterion>
3. If RED: diagnose the actual error, form a hypothesis, make ONE targeted fix, retest
4. Max <Red-Green max cycles> RED cycles. If exceeded, STOP and report — do not keep looping

## Constraints
- Do NOT modify files outside the Files list above
- Do NOT refactor unrelated code
- Do NOT introduce new dependencies not already in the project
- Commit with message: "Stage <N> Task <N.M>: <description>", ending with the
  executor trailer on its own single physical line:
  `Executor: dispatched — <your subagent_type>`
  (`../executing-plans/SKILL.md` Step 3.3 rule 7 — the trailer is the only
  artifact that distinguishes a dispatched task from an inlined one, so a
  dispatched run that omits it reads downstream as `unknown`, not as dispatched)

## Return
A structured report:
- STATUS: GREEN | ESCALATE
- If GREEN: commit SHA, test output summary, any notes
- If ESCALATE: last error, diagnosis, what was tried, what's needed from the caller
```

**Prompt discipline:** focused scope (one task), self-contained (all needed context inlined), explicit constraints (no refactoring creep), specific return format (so the caller can integrate).

**Why decisions must be in the prompt.** A dispatched agent is otherwise structurally
blind to them: it sees a task, a file list, and a slice of research — never the register,
never the plan's decisions section, never the surrounding session. A constraint that is
not in the prompt is a constraint the agent cannot honor, and the violation surfaces (if
at all) at the stage gate, after the work is built. Per **DEC-001**, carry the entry's own
words — a security-sourced decision never brings its report body into an agent prompt.

## Phase 4 — Dispatch

Launch every selected task in a **single message** with multiple `Agent` tool calls. This is the only way they actually run concurrently — sequential tool calls wait on each other.

```
Agent(description: "Task 2.3: parse config", prompt: <per task 2.3>)
Agent(description: "Task 2.4: validate schema", prompt: <per task 2.4>)
Agent(description: "Task 2.5: write config file", prompt: <per task 2.5>)
```

Match each Agent's `subagent_type` — **and the stack skill it should load first** — using
the routing table in `references/stack-routing.md`. That table is the source of truth (it
covers Rust → `rust-expert`, tests → `testing-expert`, game
design → `game-design-expert`, i18n → `translator`, scaffolding → `code-generator`,
markdown rewrites → `skill-rewriter`, bulk read-only scans → `readonly-scanner`, and a
`general-purpose` fallback). Read it before dispatch; don't reinvent the mapping here.

**When the matched agent's plugin isn't enabled**, its `plugin:agent` type isn't
registered, so you can't set `subagent_type` to it. Don't just drop to
`general-purpose` blind — resolve it from disk per `references/stack-routing.md`
§ *Resolving a capability whose plugin isn't enabled*: dispatch `general-purpose` with
the agent's `.md` body (from its `path` in `capability-index.json`) injected as its
instructions and its frontmatter `model` passed as the subagent model. A component
flagged `requires_enablement` can't be lazy-loaded — surface it to the caller to enable
that plugin instead of dispatching. (For ad-hoc, non-plan needs, the `capability-router`
skill wraps this same lookup-and-resolve flow.)

## Phase 5 — Collect

Wait for every dispatched agent to return. A single outstanding agent blocks propagation — don't start integrating until all are in.

Each agent returns `STATUS: GREEN` or `STATUS: ESCALATE`. Trust-but-verify:

- For `GREEN`: confirm the commit exists, run the task's test in the main session to verify, spot-check the diff
- For `ESCALATE`: read the reported diagnosis; that's evidence, not a fix — don't act on it blindly

## Phase 6 — Integrate

For each GREEN task:

1. Mark the task completed in the plan's status notes and in TodoWrite
2. Run the task's test **in the main session** (not just via the sub-agent's report) — agents occasionally claim green on a test that was skipped or misreported
3. **Verify the executor trailer the agent was asked to write**: `git log -1 --format='%(trailers:key=Executor,valueonly)' <sha>` must be non-empty and read `dispatched`. If it is blank or wrong, amend it now. This is the same trust-but-verify this phase already applies to the test, aimed at the one artifact a sub-agent cannot check for itself — it never sees the main session's conventions, and a blank trailer otherwise surfaces only at the stage gate as an `unknown`, long after the cheap moment to fix it (`../executing-plans/SKILL.md` Step 3.3 rule 7, Step 3.5)
4. Check the task's `Blocks` list: for each blocked task, check whether its `Depends on` is now fully green. If yes, that task becomes dispatchable in the next round.

For each ESCALATE task:

1. Do not dispatch its dependents (the graph is blocked through this node)
2. Surface the escalation to the user with: task ID, last error, agent's diagnosis, your read on it, and what option you're recommending (re-dispatch with tighter scope, revise the plan, execute manually)
3. Wait for user direction

### Merge check

After integrating, run the full test suite once more. Parallel work sometimes interacts at seams the individual tests don't cover — catch it here before the stage gate.

## Phase 7 — Report and hand back

Return to `executing-plans` (or the calling session) with:

- Count dispatched, count green, count escalated
- Commit SHAs for green tasks
- Outstanding escalations
- Newly-unblocked tasks ready for the next dispatch round

`executing-plans` decides whether to call this skill again for the next round or move on to the stage gate.

---

## Common mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Dispatching tasks that share a file | Merge conflicts or silent overwrites in parallel branches | Run the Phase 2 file-disjointness check; force sequential on conflict |
| Inlining the entire research summary into every agent prompt | Blown context, slow dispatch, agents get lost | Give each agent only the 2-4 bullets relevant to its task |
| Trusting the agent's "GREEN" without verifying | Integration-time surprises; green tests that were actually skipped | Re-run the task's test in the main session for every green return |
| Dispatching before all Depends-on are green | Agents block waiting for prerequisites, or produce broken code | Hard-check: every task in scope has every Depends-on in the completed set |
| Dispatching sequentially (one Agent call per message) | No actual parallelism; same runtime as running them one after another | Single message, multiple Agent tool calls |
| Relaxing preconditions "just this once" | The shape of the whole execution model breaks; future tasks depend on assumptions that no longer hold | Stop and ask — or revise the plan through `planning-projects` |
| Ignoring escalations to keep the pipeline moving | Downstream dispatch on a broken graph; wasted agent time | Escalation freezes the subtree; surface it and wait |

## When NOT to use this skill

- Tasks are related (one fix might fix others) — investigate as a group first
- You don't have a plan — brainstorm and plan before dispatching
- |S| = 0 — nothing is dispatchable yet (a `Depends on` is still red). **|S| = 1 is not on this list**: a lone `Parallel: YES` task is dispatched as a single dispatch, per Phase 1
- Tasks touch shared state (same file, same DB schema, same CI job) — force sequential
- The stage gate is ready to run — gates are a synchronization point; don't dispatch past them

---

## Sources and rationale

- **Dependency graph execution** — classic topological sort from graph theory; *Introduction to Algorithms* (CLRS) §22.4
- **Fan-out / fan-in pattern** — Communicating Sequential Processes (Hoare, 1978); Go's `sync.WaitGroup` and Erlang supervision trees
- **Self-contained agent prompts** — Anthropic multi-agent orchestration guidance; sub-agents have no conversation context and must be briefed completely
- **Trust-but-verify** — Reagan / Gorbachev; applied to sub-agent reports in *Google SRE Book* Ch. 9 on incident postmortems
- **Merge check after parallel work** — continuous integration practice; Fowler, "Continuous Integration" (2006)
- **Failure propagation through dependents** — Erlang "let it crash" + supervisor trees; don't build on broken foundations

## Integration

- **planning-projects** — the upstream skill producing the plan with Parallel and dependency fields this skill consumes
- **executing-plans** — the usual caller; decides when to invoke this skill during stage execution
- **stack-routing reference** (`references/stack-routing.md`) — the source of truth for Phase 4's `subagent_type` + stack-skill choice; maps stacks to real marketplace agents (`rust-dev:rust-expert`, `testing:testing-expert`, `game-dev:game-design-expert`, `i18n:translator`, `planning:design-handoff-reproducer`, `stingy-agents:code-generator`/`skill-rewriter`/`readonly-scanner`) with a `general-purpose` fallback. Shared with `executing-plans` Step 3.2
- **code-reviewer agent** — optional between dispatch rounds if integrated diffs need independent review before the stage gate
