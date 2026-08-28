# Plan document format

The literal template `planning-projects` emits. Consulted once, at write time.

## Plan Document Format

Output the plan as a markdown document following this structure. Save it to `<portfolio_home>/plans/YYYY-MM-DD-<topic>-plan.md` (vault), or `docs/plans/` only in the no-`vault_dir` fallback.

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

## Decisions in force

[One NON-CHECKBOX bullet per binding entry — a raw `- [ ]` here would be read as
deferred work by the portfolio parser and become a false backlog candidate.]

- DEC-001 — [title] (accepted; [domains]) — [the constraint in one line]
- GDEC-SEC-001 — [title] (accepted; security) — [the constraint in one line]

**Registers consulted:** [`<portfolio_home>/decisions.md`; `Portfolio/decisions/<slug>.md` …]
**Domains inferred:** [slugs, and any that had no register yet]

## Preflight

- [ ] [Check 1]: [how to verify]
- [ ] [Check 2]: [how to verify]
- [ ] Review scope declared — `review-scope: <none|light|standard|high> — [why, in one clause]`. Emit it in exactly that form: it is the string the executor restates in every gate report, so a plan and its gates read the same. Undeclared means `standard`; a risk-listed area (security/auth, data-destructive, public API, schema/migration) sets `high` whatever the size (`planning/skills/executing-plans/references/review-scope.md`)
- [ ] Dispatch probe: a throwaway subagent returns a fixed string — dispatch works in this session; skipped when the roster is `0 tasks` or the tier is below `standard`
- [ ] Dispatch roster — `<n> of <total> tasks`: every `Parallel: YES` task below, with the subagent type it routes to (`planning/skills/dispatching-parallel-agents/references/stack-routing.md`) — `[Task N.M → <subagent_type>, …]`, or `0 tasks` if the plan has none. The count is what the stage gate reconciles its dispatched-vs-inline ledger against, so a roster without one cannot be checked

**Test-scope commands** (per test-scope-tiers.md — only when the full suite exceeds ~5 min):
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
- **Scope:** [the set this task sweeps — omit for a single-artifact task]
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

<!-- Gate checkbox states: `[ ]` not yet run · `[x]` ran and passed · `[~]` BLOCKED,
     the check could not be run here. `[~]` is not a softer `[x]`: a plan carrying one
     cannot classify as completed, however its close-out line reads. A gate that ran
     and FAILED is not written down at all — it is repaired (honest-gates).
     To close a plan whose gate genuinely cannot be run here, add a terminal
     `**Blocked-accepted:** <date> — <why>` line beside the close-out line. That is
     the author's answer, and it is the ONLY thing that retires such a plan; do not
     edit the `[~]` to `[x]`, which falsifies the record the marker exists to keep. -->
- [ ] [Integration check]
- [ ] [Class predicate — the sweep that proves a set-wide property, e.g. `! grep -rl '<the stale claim>' <scope>`]
- [ ] [No regressions in touched scope (stage-scope — see references/test-scope-tiers.md)]
- [ ] [Stage goal verified end-to-end]
- [ ] **(judgment)** [what needs a reader, and why a sweep cannot prove it — the evaluator verifies this one]

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
- [ ] **(judgment)** [No change contradicts a decision in force (list the DEC/GDEC IDs in
      scope); any Supersedes citation has been recorded via `decisions supersede`] — a
      conformance judgment over a diff; no sweep can prove it
```

---
