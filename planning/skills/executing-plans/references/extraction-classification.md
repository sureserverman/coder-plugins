# Extraction classification — `../SKILL.md`

Produced by the token-efficiency plan, Stage 2 Task 2.0, on 2026-08-11.
Trunk measured at **92987 B** across **32 headings** plus 695 B of
scaffolding (title, preamble, and rules sitting outside any heading).

**This table is the authority for what Task 2.1 may move.** A section marked
`unconditional` stays in the trunk whole. A section marked `rule+elaboration`
keeps its rule and sheds its justification. Only `conditional` sections leave.

The rule this implements: extraction is safe for material a reader consults when
a branch is taken, and unsafe for a rule that must bind every run — because a
`references/` file is a definition site the executor may never open, which is the
defect `2026-07-26-dispatch-fidelity-plan.md` diagnosed when `Parallel:` was
authored as a capability and consumed as an instruction.

## Derived ceiling

    unconditional retained     13735 B
    rule portion retained      17487 B   (estimate — exact at Task 2.1)
    conditional pointers         700 B
    scaffolding                  695 B
    -----------------------------------
    DERIVED CEILING            32617 B      (65% reduction from 92987 B)

The plan's original fixed target of 30,000 B was withdrawn because it was set
against a 69,527 B baseline that had since moved to 92,987 B. The derived figure
lands close to it, which says the original intuition was sound and could not be
*justified*; this one shows its work.

**The `rule+elaboration` retention figures are estimates.** The `unconditional`
and `conditional` figures are measurements. If Task 2.1's actual retained total
exceeds the ceiling, the honest response is to record the miss and re-derive —
never to move an obligation to hit a number.

## The table


### unconditional — 13 sections, 13735 B, 13735 B retained

| bytes | retained | section | reason |
|---|---|---|---|
| 2643 | 2643 | Phase 1 — Load and critique | runs on every plan |
| 2461 | 2461 | The plan is the authorization — dispatch without a confirmation turn | DEC-014 obligation; binds every dispatch decision |
| 2262 | 2262 | Stop conditions | must bind every run, whole — never a pointer |
| 1435 | 1435 | What this skill expects | the format contract; every run validates against it |
| 1078 | 1078 | Phase 2 — Preflight | phase header + the check list itself |
| 970 | 970 | Run to completion — don't stop until you have to | governs every turn of every run |
| 956 | 956 | Reference map | the index — without it no reference is reachable |
| 526 | 526 | Safety rails | branch/destructive/secrets/shared-infra — every run |
| 520 | 520 | Checklist | the four-step loop every execution follows |
| 331 | 331 | When to revisit earlier steps | small, unconditional |
| 269 | 269 | Step 3.1 — Identify what can run now | every stage start |
| 227 | 227 | Step 3.4 — Propagate unblock | every green task |
| 57 | 57 | Phase 3 — Stage execution | phase header |

### rule+elaboration — 14 sections, 59338 B, 17487 B retained

| bytes | retained | section | reason |
|---|---|---|---|
| 21784 | 4800 | Step 3.5 — Stage gate | exit criterion + gate order stay; the two verify hooks (Android, redesign), evaluator briefing, Tier-2 shape, decisions sweep and failure procedure are each branch-taken |
| 12342 | 3600 | Step 3.3 — Red-Green loop (per task) | loop rules 1-7 stay; Tier-1 machinery is tier-gated and the test-first rationale is elaboration |
| 4106 | 1200 | A bug found during execution is a class — sweep it, fix every instance | rule is one paragraph; the worked reasoning is elaboration |
| 3689 | 900 | Review scope — the machinery scales to the change | tier declaration is unconditional; the table is RESTATED from references/review-scope.md, which the trunk already calls the authority |
| 3331 | 900 | Step 3.2 — Split by parallelism | the YES-obligates-dispatch rule stays; the retired-nudge history is elaboration |
| 2704 | 750 | Dispatch roster and capability probe | fires every Preflight; rationale already in references/dispatch-fidelity.md |
| 2372 | 700 | Context resets at stage boundaries | the handoff-note requirement fires at every gate; the rest is guidance |
| 1987 | 550 | Gate-selector probe (a gate that cannot pass is a plan defect, not a gate failure) | probe fires every Preflight; the false-positive analysis is elaboration |
| 1820 | 500 | Calibration re-check (the plan's ceremony can be stale) | fires every Preflight; the worked example is elaboration |
| 1315 | 450 | Decisions re-check (the plan's snapshot can be stale) | fires every Preflight; the why is elaboration |
| 1188 | 1188 | Light plans | already a trunk summary over references/light-plans.md |
| 1151 | 400 | Git bootstrap (hard prerequisite for commit-per-task) | fires every Preflight; the decision tree is mechanical detail |
| 888 | 888 | Master plans | already a trunk summary over references/master-plans.md |
| 661 | 661 | Progress state file (live statusline bar) | already a pointer at references/progress-state-file.md |

### conditional — 5 sections, 19219 B, 700 B retained

| bytes | retained | section | reason |
|---|---|---|---|
| 8087 | 250 | Phase Close-out — After the last stage | a phase reached once, at the end; nothing before it needs the text |
| 6654 | 200 | Integration | per-skill descriptions consulted only when routing to one |
| 2097 | 0 | Remember | pure restatement of rules the trunk states in their own sections — BL-039's 'residual restatement' class; delete, do not relocate |
| 1925 | 150 | Amending authored ceremony | only when an amendment is actually needed |
| 456 | 100 | Sources and rationale | already a pointer at references/sources.md |
