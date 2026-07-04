# Master Plan Format Reference

Canonical format for **multi-plan decomposition**: when a project is too big for one
staged plan, `planning-projects` splits it into several independently executable
**sub-plans** plus one **master plan** that links them together. This file is the single
source of truth for that format — `planning-projects` writes it, `executing-plans`
executes it, and the portfolio plan parser (`../../portfolio/references/plan-parser.md`)
reads it deterministically.

## When to decompose

Decompose instead of writing one plan when ANY of these hold:

- The single plan would exceed **~6 stages or ~25 tasks**.
- The work spans **two or more independently shippable workstreams** (different
  deliverables, repos, or subsystems that could land separately).
- Execution will clearly span **multiple sessions or stacks** (e.g. a backend service, an
  Android client, and a packaging pipeline) — each wants its own context window.

Bounds and unit rule:

- **2–7 sub-plans.** One sub-plan means you didn't need a master; more than seven means
  the sub-plans themselves need grouping (or the scope is a portfolio, not a project).
- **A sub-plan is an independently executable unit**: its own Research Summary, Preflight,
  Stages, gates, and close-out. If a "sub-plan" can't run alone — no runnable preflight, no
  gate that proves it end-to-end — it's a stage, not a sub-plan; fold it back in.
- **If you can't name a master gate check between two sub-plans** (an integration check
  that only makes sense once both are done), question the split: they're either one plan
  or two unrelated projects.

## Naming

All files live flat in the same `plans/` directory (vault `<portfolio_home>/plans/`, or
`docs/plans/` in the no-vault fallback):

```
YYYY-MM-DD-<topic>-master-plan.md            # exactly one master
YYYY-MM-DD-<topic>-sub-01-<slug>-plan.md     # sub-plans, numbered in dependency order
YYYY-MM-DD-<topic>-sub-02-<slug>-plan.md
```

Detection rule (used by executing-plans and the plan parser): a file is a master plan
when its name ends in `-master-plan.md` **or** its first heading is `# Master Plan:`.

## Master plan document format

The master plan holds the shared research, the sub-plan register (the cross-plan
dependency graph), and the integration gates. It contains **no tasks and no Preflight** —
sub-plans own those.

```markdown
# Master Plan: [Name]
Date: YYYY-MM-DD

## Research Summary

[Shared findings — everything that grounds more than one sub-plan. Each sub-plan
carries its own summary too, scoped to what that sub-plan needs.]

## Sub-plans

### Sub-plan 1: [Name]
- **Status:** [ ]
- **Plan:** ./YYYY-MM-DD-<topic>-sub-01-<slug>-plan.md
- **Goal:** [one sentence — what shipping this sub-plan proves]
- **Depends on:** none
- **Blocks:** Sub-plan 2
- **Parallel:** YES

**Gate:**
- [ ] [Integration check runnable once this sub-plan completes]
- [ ] [Cross-plan regression check]

### Sub-plan 2: [Name]
- **Status:** [ ]
- **Plan:** ./YYYY-MM-DD-<topic>-sub-02-<slug>-plan.md
- **Goal:** [one sentence]
- **Depends on:** Sub-plan 1
- **Blocks:** none
- **Parallel:** NO (blocked by Sub-plan 1)

**Gate:**
- [ ] [Integration check across Sub-plans 1+2 — the whole is proven here]
```

When every sub-plan is `[x]` and every gate has passed, `executing-plans` appends the
master close-out line:

```markdown
**Completed:** YYYY-MM-DD — sub-plans: sub-01-<slug>, sub-02-<slug>
```

### Register field semantics

| Field | Meaning |
|-------|---------|
| `Status` | `[ ]` planned → flipped to `[x]` by executing-plans when the sub-plan's own `**Completed:**` close-out line lands. Authoritative done-marker at master level. |
| `Plan` | Relative link (`./…`) to the sub-plan file in the same directory. Must resolve. |
| `Goal` | One sentence; the master-level analogue of a stage Goal. |
| `Depends on` / `Blocks` | Cross-sub-plan dependency graph. Symmetric, exactly like task fields: if Sub-plan 2 depends on Sub-plan 1, Sub-plan 1 lists Sub-plan 2 in Blocks. |
| `Parallel` | YES when all dependencies are done/none — the sub-plan may execute in a separate session/worktree. File-conflict rule still applies: two sub-plans touching the same files run sequentially regardless. |
| `**Gate:**` | Bold marker + `- [ ]` checks, **always the last block of the register entry**. Run when the sub-plan completes; proves integration with previously completed sub-plans. |

## Sub-plan skeleton

A sub-plan is a **standard planning-projects plan** — same stages, tasks, Status fields,
gates, and close-out — plus one backlink line directly below `Date:`:

```markdown
# Project Plan: [Sub-plan name]
Date: YYYY-MM-DD
Master: ./YYYY-MM-DD-<topic>-master-plan.md

## Research Summary
[Scoped to this sub-plan...]

## Preflight
[...]

## Stage 1: [Name]
[Standard stage/task format — see the Plan Document Format in SKILL.md]
```

Because sub-plans are ordinary plans, everything downstream works unchanged:
`executing-plans` runs them with the normal single-plan flow, and `portfolio unify`
mines their unchecked tasks as backlog candidates.

## Parser-safety rules (mandatory)

The deterministic parser (`portfolio-unify.py`) treats every raw unchecked `- [ ]` bullet
outside Preflight/Gate blocks as deferred work. A master plan must therefore emit **zero**
candidates by construction:

1. **No raw `- [ ]` bullets anywhere in a master plan except under a `**Gate:**` bold
   marker** (or a heading containing the word "Gate"). Gate blocks are excluded by the
   parser.
2. **Register done-state uses the `- **Status:** [ ]` field form, never a bare checkbox
   bullet.** The field form does not match the parser's unchecked-bullet regex; a bare
   `- [ ] Sub-plan 1` line would become a false backlog candidate.
3. **Each `**Gate:**` block is the last block of its register entry.** The next
   `### Sub-plan N:` heading closes the gate block for the parser; putting fields after
   the gate would leave them inside it.
4. **The tasks live only in sub-plan files.** The master never restates them — restating
   would double-count candidates once in the master and once in the sub-plan.

A master plan following this file yields no candidates; its sub-plans yield exactly their
own unchecked tasks. That invariant is locked by
`../../portfolio/tests/test-portfolio-unify.py`.

## Execution semantics (summary)

Full model in `../../executing-plans/SKILL.md` § Master plans. In short: execute
sub-plans in register dependency order, each via the normal single-plan flow (fresh
session per sub-plan recommended — the master file is the handoff artifact); on a
sub-plan's close-out, flip its register `Status`, run its `**Gate:**` checks, commit
`"Sub-plan N green"`; version bumps are deferred from sub-plan close-outs to the master
close-out.
