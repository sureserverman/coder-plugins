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

## Derived ceiling — estimated at Task 2.0, re-derived at Task 2.1

Task 2.0 published an estimated ceiling of **32617 B**. Task 2.1 executed the cut
and **missed it by 10600 B**. Under the rule this file already stated — *"if
Task 2.1's actual retained total exceeds the ceiling, the honest response is to
record the miss and re-derive — never to move an obligation to hit a number"* —
the ceiling is re-derived from what the cut actually retained. Nothing was moved
to close the gap.

```
                          estimated     actual      delta
unconditional retained        13735      14583       +848
rule portion retained         17487      26357      +8870
conditional pointers            700       1613       +913
scaffolding                     695        664        -31
------------------------------------------------------------
CEILING                       32617      43217     +10600
```

Every figure above is bytes, measured with the same accounting
`scripts/check-trunk-budget.py` uses; the four rows sum to the file size exactly.

Measured trunk after the cut: **43217 B**, a **53.5% reduction** from 92987 B.

**Corrected at Task 2.2: the trunk is 44536 B, −52.1%.** The contract suite found that the
cut had dropped nine obligation-bearing phrases while keeping each rule's gist — the
gate-failure branch's routing to the class rule and its `no-fafo-debugging` call, the `Scope:`
derivation source, "write the command down", the sweep's outer bound, Tier-2's binding of an
Important to the exit criterion, the evaluator's tier reference, and the handoff's "carried
here". All nine were restored to the trunk, +1319 B. **The compression, not the
classification, was wrong**: every one is a rule that must bind each run, so none belonged in
a reference file. The per-row `retained` figures below are Task 2.1's measurements and are
left as recorded; the active ceiling in `scripts/trunk-budget.txt` is whatever that file says — it has
risen twice since (the Stage 2 gate's two restored rules, then Stage 5's BL-039 pair).
Read it there rather than here; a byte count copied into prose is a second definition
site for a number the ratchet already owns.

**Where the estimate was wrong, and what that finding is worth.** The `rule+elaboration`
figures were explicitly flagged as estimates while the `unconditional` and `conditional`
figures were measurements — and the estimate assumed a rule compresses to roughly 30% of
its section. In practice it is 40–50%: `Step 3.5 — Stage gate` retains its exit criterion,
gate order, evaluator rule, Tier-2 rule, decisions-conformance rule, remediation budget and
pass/fail branches, and those *are* the section's obligations. Four sections carry most of
the miss — Step 3.3 (+2071), Step 3.5 (+1149), the dispatch roster (+1221) and Step 3.2
(+1160).

Read as a finding rather than a failure, this is the number the plan's extraction-eligibility
rule said was worth knowing: **these three skills now carry roughly 26 KB of standing, unconditional
obligation in one trunk**, and no amount of extraction discipline reduces that without
deleting rules. The 30 KB intuition the plan started from was never reachable at the trunk's
current obligation load — not because the extraction was timid, but because the trunk gained
12,304 B of new standing rules in the six days before execution.

**Two rows exceed their tabled figure, deliberately:**

- **`Amending authored ceremony`** (tabled 150 B, retained 400 B) — the pointer alone would
  leave an executor amending unguided, so the three legality conditions (unexecuted checks
  only, the annotation cites the authorizing rule, the was-value survives) stay in the trunk.
  *A pointer is not a rule.*
- **`Reference map`** (tabled 956 B, retained 1605 B) — six new reference files need six new
  index rows. The index growing with the extraction is the extraction working.

**One row is retired rather than retained:** `Remember` (2097 B) was **deleted, not
relocated**, as approved before the cut — it restated rules the trunk states in their own
sections, and relocating a duplicate preserves the drift BL-039 documented. Its row is gone
from the table below because `scripts/check-extraction-classification.py` enforces set
equality against the trunk's real headings; the decision is recorded here instead, which is
the only place it can now live.

## The table

`bytes` is the section's size in the 92987 B trunk. `retained` is what Task 2.1
actually left in the trunk, measured — not estimated.

### unconditional — 13 sections, 13735 B, 14583 B retained

| bytes | retained | section | reason |
|---|---|---|---|
| 2643 | 2638 | Phase 1 — Load and critique | runs on every plan |
| 2461 | 2488 | The plan is the authorization — dispatch without a confirmation turn | DEC-014 obligation; binds every dispatch decision |
| 2262 | 2298 | Stop conditions | must bind every run, whole — never a pointer |
| 1435 | 1452 | What this skill expects | the format contract; every run validates against it |
| 1078 | 1200 | Phase 2 — Preflight | phase header + the check list itself |
| 970 | 965 | Run to completion — don't stop until you have to | governs every turn of every run |
| 956 | 1605 | Reference map | the index — without it no reference is reachable |
| 526 | 532 | Safety rails | branch/destructive/secrets/shared-infra — every run |
| 520 | 517 | Checklist | the four-step loop every execution follows |
| 331 | 332 | When to revisit earlier steps | small, unconditional |
| 269 | 270 | Step 3.1 — Identify what can run now | every stage start |
| 227 | 228 | Step 3.4 — Propagate unblock | every green task |
| 57 | 58 | Phase 3 — Stage execution | phase header |

### rule+elaboration — 14 sections, 59338 B, 26357 B retained

| bytes | retained | section | reason |
|---|---|---|---|
| 21784 | 5949 | Step 3.5 — Stage gate | exit criterion + gate order stay; the two verify hooks (Android, redesign), evaluator briefing, Tier-2 shape, decisions sweep and failure procedure are each branch-taken |
| 12342 | 5671 | Step 3.3 — Red-Green loop (per task) | loop rules 1-7 stay; Tier-1 machinery is tier-gated and the test-first rationale is elaboration |
| 4106 | 1910 | A bug found during execution is a class — sweep it, fix every instance | rule is one paragraph; the worked reasoning is elaboration |
| 3689 | 1556 | Review scope — the machinery scales to the change | tier declaration is unconditional; the table is RESTATED from references/review-scope.md, which the trunk already calls the authority |
| 3331 | 2060 | Step 3.2 — Split by parallelism | the YES-obligates-dispatch rule stays; the retired-nudge history is elaboration |
| 2704 | 1971 | Dispatch roster and capability probe | fires every Preflight; rationale already in references/dispatch-fidelity.md |
| 2372 | 1491 | Context resets at stage boundaries | the handoff-note requirement fires at every gate; the rest is guidance |
| 1987 | 676 | Gate-selector probe (a gate that cannot pass is a plan defect, not a gate failure) | probe fires every Preflight; the false-positive analysis is elaboration |
| 1820 | 905 | Calibration re-check (the plan's ceremony can be stale) | fires every Preflight; the worked example is elaboration |
| 1315 | 767 | Decisions re-check (the plan's snapshot can be stale) | fires every Preflight; the why is elaboration |
| 1188 | 1204 | Light plans | already a trunk summary over references/light-plans.md |
| 1151 | 646 | Git bootstrap (hard prerequisite for commit-per-task) | fires every Preflight; the decision tree is mechanical detail |
| 888 | 889 | Master plans | already a trunk summary over references/master-plans.md |
| 661 | 662 | Progress state file (live statusline bar) | already a pointer at references/progress-state-file.md |

### conditional — 4 sections, 17122 B, 1613 B retained

| bytes | retained | section | reason |
|---|---|---|---|
| 8087 | 546 | Phase Close-out — After the last stage | a phase reached once, at the end; nothing before it needs the text |
| 6654 | 458 | Integration | per-skill descriptions consulted only when routing to one |
| 1925 | 400 | Amending authored ceremony | only when an amendment is actually needed; the three legality conditions stay because a pointer is not a rule |
| 456 | 209 | Sources and rationale | already a pointer at references/sources.md |

## Where the conditional material went

| moved from | now lives in |
|---|---|
| Phase Close-out (steps 1–10) | `../references/close-out.md` |
| Integration list + Review opt-out | `../references/integration.md` |
| Step 3.5's hooks, evaluator, Tier 2, dispositions, failure branch, handoff shape | `../references/stage-gate.md` |
| Step 3.2's rationale + Step 3.3's test-first evidence, Tier-1 machinery, trailer detail | `../references/task-execution.md` |
| Preflight's five check procedures + the amendment protocol | `../references/preflight-checks.md` |
| The class-sweep reasoning and its cost rule | `../references/bug-is-a-class.md` |
| `Remember` | deleted — restatement, not relocated |

## Retention markers

Task 2.1's obligation is not only that a heading survived — a heading over a pointer would
satisfy set equality perfectly and lose the rule. Each row names a string that must be
**trunk-resident**: the rule the row promised to keep, in the trunk's own words.
`scripts/check-trunk-retention.py` sweeps this table in full, so a rule quietly demoted to a
pointer in some later edit fails the suite rather than passing unnoticed.

**Every binding section carries at least one marker, and a section may carry several.** Both
properties were added at the Stage 2 gate, from findings by an independent evaluator and a
Tier-2 review that reached them separately:

- **`unconditional` rows were originally exempt**, on the reasoning that they may never move
  so heading presence is enough. That is exactly backwards: they carry the strongest
  guarantee in the table, and heading presence is the one check that cannot see a section
  gutted to a stub. The guard was blind on the class it calls most dangerous.
- **One marker per section is instance-shaped.** `Step 3.5 — Stage gate` retains eight
  distinct obligations; pinned by a single string, seven could be demoted with the sweep
  still green — the defect class this repo's own gate rules exist to reject, reproduced
  inside the guard meant to enforce them.

**A marker may not span a line wrap.** `check-trunk-retention.py` matches plain
case-sensitive substrings against **the body of the section that claims the marker** — not the
raw file, and not including that section's own heading line. So a marker crossing a newline
plus the next line's indent (or a `> ` blockquote prefix) can never match, and the guard reports MISSING-RULE
for a rule that is present. Pick a marker that sits on one physical line. Found the hard way
adding the three Step 3.5 rows below.

| section | must appear in the trunk |
|---|---|
| What this skill expects | It deliberately has no |
| What this skill expects | it wasn't produced by `planning-projects` |
| Reference map | The trunk carries what fires on every run |
| Master plans | Version bumps defer to the master |
| Light plans | that single pre-gate review IS the light plan's Tier-2 |
| Checklist | Run the stage gate; stop if it fails |
| Run to completion — don't stop until you have to | Only the documented Stop conditions halt execution |
| Run to completion — don't stop until you have to | Stage boundaries |
| The plan is the authorization — dispatch without a confirmation turn | is a direct order, and you execute it without asking |
| The plan is the authorization — dispatch without a confirmation turn | conditional, not absolute |
| The plan is the authorization — dispatch without a confirmation turn | no plan in play |
| A bug found during execution is a class — sweep it, fix every instance | one sample of a class until a command proves |
| A bug found during execution is a class — sweep it, fix every instance | nothing wider |
| A bug found during execution is a class — sweep it, fix every instance | costs a command, never a dispatch |
| Phase 1 — Load and critique | Read the plan file in full |
| Phase 1 — Load and critique | INSTANCE-SHAPED |
| Phase 1 — Load and critique | Decisions in force |
| Phase 2 — Preflight | Baseline test suite passes |
| Phase 2 — Preflight | Review scope is declared |
| Decisions re-check (the plan's snapshot can be stale) | accretes between planning and execution |
| Calibration re-check (the plan's ceremony can be stale) | What is never recomputed: the plan's facts |
| Amending authored ceremony | unexecuted checks only |
| Amending authored ceremony | the was-value survives |
| Gate-selector probe (a gate that cannot pass is a plan defect, not a gate failure) | pytest --collect-only -q |
| Gate-selector probe (a gate that cannot pass is a plan defect, not a gate failure) | plan defect |
| Git bootstrap (hard prerequisite for commit-per-task) | A missing remote is **not** a stop condition |
| Dispatch roster and capability probe | A failed probe is a Preflight failure |
| Dispatch roster and capability probe | across all stages |
| Dispatch roster and capability probe | Snapshot the `Review: skip` annotations |
| Review scope — the machinery scales to the change | Declare a tier at Preflight and restate it in every gate report |
| Review scope — the machinery scales to the change | size alone never escalates |
| Phase 3 — Stage execution | For each stage in order |
| Step 3.1 — Identify what can run now | every task in its `Depends on` list is green |
| Step 3.2 — Split by parallelism | `YES` obligates a dispatch, `NO` means inline |
| Step 3.2 — Split by parallelism | serialize the dispatches |
| Step 3.2 — Split by parallelism | is a deviation |
| Step 3.3 — Red-Green loop (per task) | **One fix per cycle.** |
| Step 3.3 — Red-Green loop (per task) | must go RED for the right |
| Step 3.3 — Red-Green loop (per task) | Respect the cycle budget |
| Step 3.3 — Red-Green loop (per task) | Flip the task's Status to `[x]` |
| Step 3.3 — Red-Green loop (per task) | Executor: dispatched — <subagent_type> |
| Step 3.3 — Red-Green loop (per task) | one physical line |
| Step 3.4 — Propagate unblock | scan its `Blocks` field |
| Step 3.5 — Stage gate | A gate passes when **no Critical finding remains** |
| Step 3.5 — Stage gate | A gate is green only when its real command ran |
| Step 3.5 — Stage gate | is a substitution, not a review |
| Step 3.5 — Stage gate | with no recorded reason the gate |
| Step 3.3 — Red-Green loop (per task) | keeps it in the vault |
| Step 3.3 — Red-Green loop (per task) | from the repo root |
| Run to completion — don't stop until you have to | Never end a turn on an announcement |
| Step 3.5 — Stage gate | gate is BLOCKED, not green |
| Step 3.5 — Stage gate | Never collapse BLOCKED into GREEN |
| Step 3.5 — Stage gate | Regressions check runs at stage-scope |
| Step 3.5 — Stage gate | dispatched-vs-inline counts |
| Step 3.5 — Stage gate | the agent that ran it |
| Step 3.5 — Stage gate | Platform stage-verify hook |
| Step 3.5 — Stage gate | briefed ONLY with the stage goal |
| Step 3.5 — Stage gate | pass with |
| Step 3.5 — Stage gate | a **Critical** here is a |
| Step 3.5 — Stage gate | Decisions-conformance check |
| Step 3.5 — Stage gate | default 2 rounds per gate |
| Step 3.5 — Stage gate | re-dispatched review or evaluator is a round |
| Context resets at stage boundaries | Stage gates are the reset points |
| Context resets at stage boundaries | the review ledger cannot |
| Context resets at stage boundaries | never by needing |
| Progress state file (live statusline bar) | delete it when close-out |
| Stop conditions | Never guess through a stop condition |
| Stop conditions | never ask through a dispatch the plan mandated |
| Stop conditions | cannot be performed |
| When to revisit earlier steps | treat the new version as a fresh plan |
| Phase Close-out — After the last stage | Do not merge without explicit confirmation |
| Safety rails | Never start on `main` / `master` without explicit user consent |
| Safety rails | Destructive commands |
| Sources and rationale | references/sources.md |
| Integration | references/integration.md |
