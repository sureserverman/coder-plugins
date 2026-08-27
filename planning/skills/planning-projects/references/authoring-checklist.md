# Pre-presentation checklist — the full item list

`../SKILL.md` § Checklist — Before Presenting the Plan carries the imperative (run every item)
and restates four of them — **the four a command decides rather than a reading**. This file
is the list itself.

*(An earlier version of this paragraph said those restated items were "the items no other section of
that trunk states". That was false and a Tier-2 review caught it: the INSTANCE-SHAPED bar is
stated at `../SKILL.md` § Write a set-valued check, and the save-location item at § Output
location — which this file's own line 46 cites. Being command-decidable is the real reason
they are restated, and it is the one the trunk gives.)*

Most items name the section that owns the rule they enforce, so a failed item is fixed at its
source rather than argued with here; a few name the reference file that owns it instead, and
four name nothing because their rule lives in `../SKILL.md` § Task and stage fields. The
checklist is a **sweep**, not a second definition site: nothing here introduces an obligation
the trunk does not already carry.

## Checklist — Standard plans

Run every item before showing the plan to the user.

**Structure**

- [ ] Every task has a concrete, runnable test — no "it should work" tests (`../SKILL.md` § Phase 3 — The Red-Green Loop)
- [ ] Tasks within each stage follow their dependency order
- [ ] No task depends on something from a later stage
- [ ] Every stage has a risk flag with a reason (`task-fields.md`)
- [ ] Every stage has a rollback note (`task-fields.md`)
- [ ] Every stage has a gate with specific checks (`../SKILL.md` § Phase 4 — Stage Gates)
- [ ] No stage has more than 7 tasks (`../SKILL.md` § Stage sizing)

**Gate checks**

- [ ] Every user-facing stage has at least one gate check that exercises the running artifact, not only static tests (`../SKILL.md` § What a stage gate checks)
- [ ] Every gate check asserting a property of a **set** is an executable sweep over that set, or carries the `(judgment)` marker naming why a reader must verify it, or — where one artifact genuinely *is* the whole set — the `(scoped)` marker saying why. No check names one artifact where the goal is a property of many, and none is widened past the set its claim is over, which produces a check that cannot pass at all (`../scripts/validate-gate-checks.py` reports zero INSTANCE-SHAPED; `set-valued-checks.md`)
- [ ] **One owner per fact**: no gate check re-proves what a task's `Test:` already decides, unless it sweeps a strictly wider, nameable set; and no `(judgment)` line restates a fact an executable check in this plan already answers (`../SKILL.md` § Every fact has one owner)
- [ ] **Every gate check can pass as authored**: `validate-gate-checks.py` reports zero SELECTOR-UNMATCHED — every `pytest <file> -k <expr>` selector in a gate is one some task's `Test:` builds toward, so no gate names a filter that collects nothing (the defect that shipped twice; `executing-plans` re-checks it at Preflight with `--collect-only`, where the tests actually exist)

**Research and Preflight**

- [ ] The research summary has actual findings, not placeholders (`../SKILL.md` § Research summary)
- [ ] Preflight checks cover all tools, deps, and access needed by the plan (`../SKILL.md` § Preflight checklist)
- [ ] If the project's full suite is expensive (>~5 min): the plan declares its stage-scope and plan-scope commands, only the final gate runs the full clean pass, and any single test >~2 min is quarantined behind an opt-in filter (`test-scope-tiers.md`)

**Task fields**

- [ ] Every task that changes more than one artifact carries a `Scope:` naming that set, derived from a command that was actually run rather than recalled; single-artifact tasks correctly omit it (`../SKILL.md` § Task and stage fields)
- [ ] Every task has both `Depends on` and `Blocks` fields — and they're symmetric
- [ ] Every task has a `Parallel` field (YES/NO) consistent with its dependencies
- [ ] No two parallel tasks modify the same files (`../SKILL.md` § Phase 5 — Parallel Execution)
- [ ] On an expensive-suite project (>~5 min), every task's `Test:` is path- or suite-scoped, or the task carries `full-suite: accepted` with a reason — an **authoring-time** check, run once per authored plan and never per execution turn (`test-scope-tiers.md` § A task-level `Test:` is task-scope only when the author scoped it; `../scripts/validate-gate-checks.py` reports zero TASK-TEST-UNSCOPED)

**Where it lands, and what it reconciles**

- [ ] The plan is saved to the project's `<portfolio_home>/plans/` in the vault (project auto-registered + sidecar carries the `PORTFOLIO-STATUS` block whose **Plans:** pointer reaches the new plan); or `docs/plans/` only in the no-`vault_dir` fallback (`../SKILL.md` § Output location (vault-canonical))
- [ ] Open backlog items in scope were reviewed; folded-in items carry a `Closes BL-NNN` reference on the task that closes them (`../SKILL.md` § Backlog scan)
- [ ] Workflow specs in scope were read; any altered or removed behavior is declared on the corresponding task (`Changes WF-NNN` / `Removes WF-NNN`); new flows have a capture/extend task (`../SKILL.md` § Workflow-spec scan)
- [ ] If an architecture doc exists for this topic: every structure-creating task cites its ARCH-ID, the final stage gate carries the architecture-conformance check, and no task contradicts an approved ARCH section (`../SKILL.md` § Architecture doc scan)
- [ ] The decisions scan ran and its result is written into `## Decisions in force` (including the explicit `none — registers consulted: …` form, and `project register: absent` on a new project); tasks constrained by an entry cite it (`Honors DEC-NNN`), any deliberate override cites it (`Supersedes …— <why>`), and the final stage gate carries the decisions-conformance check (`../SKILL.md` § Decisions scan)

## Additionally, for a decomposed project (master plan + sub-plans)

- [ ] The decomposition trigger actually held (`../SKILL.md` § Phase 2.5 — Decomposition decision (master plan + sub-plans)) — 2–7 sub-plans, each independently executable
- [ ] Register `Depends on` / `Blocks` fields are symmetric across sub-plan entries
- [ ] Every register entry ends with a `**Gate:**` block containing at least one cross-plan integration check
- [ ] Every sub-plan carries the `Master: ./<master-file>` backlink; every register `Plan:` link resolves
- [ ] The master plan is parser-safe: no raw `- [ ]` bullets outside `**Gate:**` blocks, no tasks, no Preflight (`master-plan-format.md`)

## Checklist — Light plans

For a **Light** plan (`../SKILL.md` § Phase -0.5 — Format triage selected it), verify only
these eight — the Standard checklist does not apply:

- [ ] Every task has a concrete, runnable `Test:` — the same bar as any plan
- [ ] Tasks are in dependency order; any `Depends on` points only backward within the stage
- [ ] Exactly one stage, with 2–5 tasks (a 6th task or a second stage means re-issue as Standard)
- [ ] The single `### Stage 1 Gate` includes "full existing test suite passes" and a goal-level end-to-end check
- [ ] The `Format: Light — …` line is present at the top; the file is saved to `<portfolio_home>/plans/` as `*-light-plan.md`
- [ ] Open backlog items in scope were reviewed (the scan runs at every size); folded-in items carry `Closes BL-NNN`
- [ ] If `docs/workflows/` exists and the change touches a documented flow, the altered/removed behavior is declared on the task (`Changes WF-NNN` / `Removes WF-NNN`) — behavior contracts don't get a size exemption
- [ ] On an expensive-suite project, every task's `Test:` is path- or suite-scoped or carries `full-suite: accepted` — the same bar as any plan, and an **authoring-time** check (`test-scope-tiers.md`). A Light plan has task `Test:` fields, so this is not one of the items the format drops

**Why the Light list is shorter rather than softer.** Every item it drops is a field the Light
format does not have (Risk, Rollback, Blocks, Parallel, a Preflight section) or a long-horizon
artifact it does not produce. The items it keeps are the invariants — a runnable test, one
gate, the two scans — and those are identical to a Standard plan's, because a small plan can
violate a binding constraint just as thoroughly as a large one.
