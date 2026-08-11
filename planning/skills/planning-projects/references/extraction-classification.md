# Extraction classification — `../SKILL.md`

Produced by the token-efficiency plan, Stage 3 Task 3.0, on 2026-08-11.
Trunk measured at **46102 B** across **37 headings** plus 886 B of scaffolding
(frontmatter, title, and the preamble that precedes the first heading).

**This table is the authority for what Task 3.1 may move.** A section marked
`unconditional` stays in the trunk whole. A section marked `rule+elaboration`
keeps its rule and sheds its justification. Only `conditional` sections leave.

The rule this implements: extraction is safe for material a reader consults when
a branch is taken, and unsafe for a rule that must bind every run — because a
`references/` file is a definition site the author may never open, which is the
defect `2026-07-26-dispatch-fidelity-plan.md` diagnosed when `Parallel:` was
authored as a capability and consumed as an instruction.

## Two corrections carried in from Stage 2

**The retention ratio.** Task 2.0 estimated that a `rule+elaboration` section
compresses to ~30% of its bytes. Measured across `executing-plans`, it is
**40–50%**, and the gap made that stage miss its ceiling by 10600 B. Every
`retained` figure in the tables is estimated at **45%** unless the row's reason
argues otherwise, per the Stage 2 handoff's instruction to *"estimate accordingly
rather than repeat the 30% assumption."*

**The heading count is 37, not 38.** A `^#{2,4} ` scan of this trunk reports 38,
because `## Decisions in force` appears inside a ```markdown fence as a worked
example of what a plan's own section should look like. It is sample content, not
a section of this skill. `scripts/_skill_sections.py` now excludes fenced
headings for both guards; without that fix this table would have had to file a
classification decision about a code sample, and the row would have failed the
day anyone edited the example.

## Derived ceiling — estimated at Task 3.0

```
                          bytes     retained
unconditional  (14 sec)    6477         6650
rule+elab      (22 sec)   37762        19190
conditional     (1 sec)     977          250
scaffolding                 886          886
--------------------------------------------
TOTAL                     46102        26976
```

The four `bytes` rows sum to 46102 exactly — the measured file size.

**Estimated ceiling: 26976 B**, a **41.5%** reduction. It is recorded in
`scripts/trunk-budget.txt` as a `# derived-ceiling:` **comment**, not as an active
ceiling: promoting it while the trunk is still 46102 B would fail the ratchet and
redden the suite between two green tasks. Task 3.1 promotes it when the cut lands.

**If Task 3.1's real retained total exceeds this, record the miss and re-derive.
Never move an obligation to hit the number.** That is what Stage 2 did, and the
miss it recorded was worth more than the number would have been.

## Re-derived at Task 3.1 — the ceiling was MISSED by 8788 B

The cut landed at **35764 B**, a **22.5%** reduction, against an estimated 26976
(41.5%). The ceiling in `scripts/trunk-budget.txt` is set to 35764 — what was
actually retained — rather than the estimate, because the gap is rule text and
moving it would defeat the plan.

```
                          bytes   estimated    actual
unconditional  (14 sec)    6477        6650      6878
rule+elab      (22 sec)   37762       19190     27784
conditional     (1 sec)     977         250       216
scaffolding                 886         886       886
-----------------------------------------------------
TOTAL                     46102       26976     35764
```

**The whole miss is in one row, and it is the same row Stage 2 missed on.**
`unconditional` came in 228 B over (the `Reference map` went 627 → 1028, four new
rows rather than the ~800 B the estimate allowed) and `conditional` 34 B under.
`rule+elaboration` retained **73.6%**, not the 45% Task 3.0 estimated — and 45% was itself the
*correction* Stage 2 handed forward after measuring 40–50% against a 30%
assumption. The correction was applied and was still low by 28 points.

**Why 73.6% here and 40–50% there is not a worse cut but a different trunk.**
`executing-plans` has procedure to relocate: a section like `Step 3.5 — Stage
gate` states a rule and then describes how to run it, and the description leaves.
`planning-projects` states a rule and then says *why*, and the why is usually one
or two sentences attached to a rule that is three or four. Measured on the six
largest sections, the justification available to shed was:

```
section                                    bytes   after   kept   estimated
Checklist — Before Presenting the Plan      4550    2073    46%        1200
Phase -0.5 — Format triage                  4586    3203    70%        2300
A plan that adds an obligation ...          2616    1691    65%        1300
Decisions scan                              2526    1921    76%        1250
Preflight checklist                         2833    2381    84%        1800
Phase 2.5 — Decomposition decision          2413    2039    85%        1350
```

`Checklist — Before Presenting the Plan` reached 46% because its items *restate*
rules owned by other trunk sections, so moving them loses nothing — it is the only
section in this trunk that was structurally duplicative. `Preflight checklist` and
`Phase 2.5` barely moved because their bullets **are** the rule: the Preflight
checks and the decomposition thresholds have no justification layer to remove.
Task 3.0 sized them at 1800 and 1350; the bullets alone, verbatim, exceed both.

**One amendment to the classification's own rows.** `Preflight checklist` is
described as "the nine checklist bullets ARE the rule". It now carries **ten**.
The trailing rationale the row calls elaboration contained a live obligation — the
plan declares its stage-scope and plan-scope test commands in Preflight — which
would have been deleted along with the paragraph carrying it. It was promoted to a
bullet rather than dropped or left in prose the cut was about to remove. This is
the Stage 2 lesson applied: the paragraph was elaboration, the sentence inside it
was not.

**What a future estimator should take from this.** The retention ratio is not a
property of the classification class, it is a property of the trunk's *shape*.
Before estimating, ask what fraction of the trunk's rule+elaboration sections are
prose-over-rule (which compress) versus enumerations of rules (which do not). A
trunk that is mostly lists of obligations has no 45% in it at any level of effort,
and an estimate that assumes one will be missed by exactly the amount of rule text
the cut refused to move.

**One row grows rather than shrinks:** `Reference map` (627 → 800 B), because the
extraction creates new reference files and each needs an index row. An index
growing with the extraction is the extraction working.

## The table

`bytes` is the section's size in the 46102 B trunk. `retained` is the estimate
Task 3.1 is measured against.

### unconditional — 14 sections, 6477 B, 6650 B retained

| bytes | retained | section | reason |
|---|---|---|---|
| 1311 | 1311 | Stage structure | the literal task/stage field template every plan is built from |
| 977 | 977 | Write a set-valued check as the sweep that proves it | DEC-005; binds every gate check an author writes |
| 758 | 758 | Task and stage fields | already a pointer at task-fields.md plus two load-bearing rules |
| 627 | 800 | Reference map | the index — without it no reference is reachable |
| 470 | 470 | Plan Document Format | already a pointer at the template fixture |
| 402 | 402 | Phase 3 — The Red-Green Loop | already compressed to a pointer plus its two obligations |
| 277 | 277 | Phase -1 — Clarification | phase header; runs before every plan |
| 271 | 271 | Research summary | every task must trace back to it |
| 267 | 267 | When NOT to ask | the off-ramp rule; small and unconditional |
| 243 | 243 | Phase 4 — Stage Gates | phase header |
| 233 | 233 | Phase 0 — Research | phase header |
| 230 | 230 | Stage sizing | the >7-tasks rule; one sentence, binds every stage |
| 213 | 213 | Phase 2 — Stage Breakdown | phase header |
| 198 | 198 | Phase 1 — Preflight | phase header |

### rule+elaboration — 22 sections, 37762 B, 19190 B retained

| bytes | retained | section | reason |
|---|---|---|---|
| 4586 | 2300 | Phase -0.5 — Format triage | the format table, the size-each-request rule, round-up and record-the-call stay; the per-format prose and the remote-agents worked example are elaboration |
| 4550 | 1200 | Checklist — Before Presenting the Plan | the imperative to run every item stays, with the items that restate no other trunk section (the validator commands, the vault-save item, the master addendum); the rest of the list restates rules stated in their own sections and moves |
| 2833 | 1800 | Preflight checklist | the nine checklist bullets ARE the rule and stay; the three trailing rationale paragraphs are elaboration |
| 2616 | 1300 | A plan that adds an obligation names what it removes | Removes/Replaces/Adds-net, the has-it-caught-a-defect test and DEC-017's naming rule stay; the measured example is elaboration |
| 2526 | 1250 | Decisions scan | call `relevant`, contradiction-is-a-planning-bug, record-what-was-consulted and the new-project rule stay; the sample block and the why are elaboration |
| 2413 | 1350 | Phase 2.5 — Decomposition decision (master plan + sub-plans) | the decompose-when triggers and the 2–7 split rule stay — this is the sole authority on Standard→Master; the how-to-split detail is branch-taken |
| 2236 | 950 | Light plans | already a trunk summary over light-plan-format.md; the five deltas and the upgrade rule stay, the per-delta prose goes |
| 2099 | 1000 | Architecture doc scan | cite-the-ARCH-ID, emit-the-conformance-gate and no-silent-deviation stay; sub-plan mechanics are branch-taken |
| 1935 | 1100 | Output location (vault-canonical) | the four resolution steps stay; the sidecar prose in step 4 is elaboration |
| 1820 | 900 | Every fact has one owner | the one-owner rule, both exceptions and the `(judgment)` restriction stay; the bot-live-view example is elaboration |
| 1574 | 880 | Citing decisions on tasks | Honors/Supersedes citation forms, the required conformance gate and DEC-001 stay; the reasoning is elaboration |
| 1475 | 720 | Workflow-spec scan | the three declaration rules and be-explicit-about-which stay; the redesign paragraph is branch-taken |
| 1327 | 700 | When a stage gate fails | class-sampled-once and the do-not-restate deferral to executing-plans stay; the rest is elaboration |
| 1135 | 800 | What a stage gate checks | the four check kinds stay; the regressions bullet's scope policy is already owned by test-scope-tiers.md |
| 843 | 500 | Status marking (per-task done-state) | the exact `- **Status:** [ ]` form and the close-out line stay; the rationale is elaboration |
| 692 | 350 | Phase 5 — Parallel Execution | the mark-YES-when rule stays once; the section currently states what-the-plan-owes twice and the duplicate goes |
| 615 | 420 | When to ask | the six ambiguity axes are the rule and stay; the framing is elaboration |
| 566 | 400 | Backlog scan | fold-in-with-`Closes BL-NNN` and duplicate-is-a-planning-bug stay |
| 534 | 350 | Online sources | check version-specific behavior and use context7 stay; the category list compresses |
| 513 | 340 | Local vault | search-the-vault and the plans-path fallback stay |
| 451 | 250 | How to ask | one-question-at-a-time and state-your-assumption stay |
| 423 | 330 | Project context | the four read-before-planning axes stay |

### conditional — 1 section, 977 B, 250 B retained

| bytes | retained | section | reason |
|---|---|---|---|
| 977 | 250 | Checklist — Light plans | read only when Phase -0.5 selected Light, and light-plan-format.md is already its authority; the retained 250 B is the existence pointer Task 3.1's `Test:` requires to stay trunk-resident |

**Only one row is `conditional`, and that is the finding.** `planning-projects`
is nearly all standing obligation: it is consulted once per plan, and almost
every section fires on that single pass. The reduction here therefore comes from
compressing justification, not from relocating procedure — which is why the
estimated ceiling is 41.5% rather than Stage 2's 50%.

`conditional` rows carry no retention marker, by the same construction Stage 2
used: they are the rows that were supposed to leave, and their retained pointer is
checked by the DEAD-PATH half of `check-extraction-integrity.py` instead.

## Retention markers

A heading over a pointer satisfies set equality perfectly and loses the rule, so
each binding row names a string that must be **trunk-resident** after the cut.
`scripts/check-trunk-retention.py` sweeps this table in full.

**Every binding section carries at least one marker, and a multi-obligation
section carries several** — the two properties Stage 2's gate had to add after
finding the guard blind on exactly the rows it called most dangerous.

These markers are written against the **post-cut** trunk and are Task 3.1's
contract. Where a marker quotes text that must survive verbatim, it is quoted
from the current trunk.

| section | must appear in the trunk |
|---|---|
| Reference map | The trunk carries the authoring decisions |
| Phase -1 — Clarification | make sure you understand what the user actually wants |
| When to ask | Success criteria |
| When to ask | Target environment |
| How to ask | One question at a time |
| When NOT to ask | ask because the answer would change the plan |
| Phase -0.5 — Format triage | Size each request, not the batch |
| Phase -0.5 — Format triage | Direct is the off-ramp |
| Phase -0.5 — Format triage | Record the call |
| Phase -0.5 — Format triage | round up — per item, never per batch |
| Light plans | fold in matches with `Closes BL-NNN` |
| Light plans | re-issue it as a Standard plan |
| Phase 0 — Research | Before writing a single task |
| Online sources | don't assume, check |
| Local vault | prior design decisions |
| Decisions scan | contradict an accepted decision is a planning bug |
| Decisions scan | nothing binds this scope |
| Decisions scan | project register: absent |
| Backlog scan | Closes BL-NNN |
| Backlog scan | silently duplicates an open backlog item is a planning bug |
| Workflow-spec scan | Changes WF-AUTH-003 |
| Workflow-spec scan | Removes WF-AUTH-007 |
| Architecture doc scan | MUST cite the ARCH-ID |
| Architecture doc scan | Emit the conformance gate |
| Architecture doc scan | no architecture doc — structure decided inline |
| Citing decisions on tasks | Honors DEC-003 |
| Citing decisions on tasks | The marker is **required**, not optional |
| Citing decisions on tasks | uncited change that contradicts an accepted decision is a **gate failure** |
| Project context | the plan should fit, not fight |
| Research summary | Every task below should trace back |
| Phase 1 — Preflight | Before Stage 1 begins |
| Preflight checklist | Baseline |
| Preflight checklist | Review scope |
| Preflight checklist | Dispatch probe |
| Preflight checklist | Dispatch roster |
| Preflight checklist | If any preflight check fails, stop |
| Phase 2 — Stage Breakdown | Divide the project into sequential stages |
| Stage structure | an instruction to the executor — YES obligates dispatch |
| Stage structure | the SET this task changes |
| Stage structure | Class predicate: the command that sweeps the set |
| Status marking (per-task done-state) | - **Status:** [ ] |
| Status marking (per-task done-state) | single source of truth |
| Task and stage fields | is a directive to dispatch |
| Task and stage fields | only as good as the sweep behind it |
| Stage sizing | more than 7 tasks |
| A plan that adds an obligation names what it removes | Adds, net: |
| A plan that adds an obligation names what it removes | has it ever caught a real defect |
| A plan that adds an obligation names what it removes | names the tier or scope rule that gates it |
| Phase 2.5 — Decomposition decision (master plan + sub-plans) | ~6 stages or ~25 tasks |
| Phase 2.5 — Decomposition decision (master plan + sub-plans) | 2–7 sub-plans |
| Phase 2.5 — Decomposition decision (master plan + sub-plans) | no tasks and no Preflight |
| Output location (vault-canonical) | Plans live in the vault, not the repo |
| Output location (vault-canonical) | Auto-register if new |
| Plan Document Format | references/plan-document-template.md |
| Phase 3 — The Red-Green Loop | runnable command or a checkable criterion |
| Phase 4 — Stage Gates | Stage gates prove the pieces work together |
| What a stage gate checks | Live artifact over static checks |
| What a stage gate checks | Intermediate gates check at **stage-scope** |
| Every fact has one owner | is not re-proved at the gate |
| Every fact has one owner | may never restate a fact an executable check |
| Write a set-valued check as the sweep that proves it | is an executable sweep, not a spot check |
| Write a set-valued check as the sweep that proves it | may not be presented while it reports INSTANCE-SHAPED |
| Write a set-valued check as the sweep that proves it | **(judgment)** |
| When a stage gate fails | defect class sampled once |
| When a stage gate fails | Do not restate those rules here |
| Phase 5 — Parallel Execution | shares no file with a sibling |
| Checklist — Before Presenting the Plan | Before showing the plan to the user, verify |
| Checklist — Before Presenting the Plan | zero SELECTOR-UNMATCHED |

## Where the conditional material will go

The files exist as of Task 3.1, so the destinations are links rather than names.

| moved from | destination |
|---|---|
| The full pre-presentation item list | `authoring-checklist.md` |
| Both checklists' Light half | `authoring-checklist.md` |
| Phase -0.5's per-format prose + the batch-triage example | `format-triage.md` |
| Phase 0's scan rationale (decisions, backlog, workflow, architecture) | `research-scans.md` |
| Citing decisions on tasks' reasoning | `research-scans.md` |
| Phase 4's gate-authoring rationale + the one-owner example | `gate-authoring.md` |
| A plan that adds an obligation's accretion argument + the DEC-017 measurement | `gate-authoring.md` |
| When a stage gate fails' deferral detail | `gate-authoring.md` |
| Light plans' per-delta prose | `light-plan-format.md` (already existed) |

**Three rows are Task 3.1 amendments, not Task 3.0's plan.** The `Citing
decisions on tasks`, `A plan that adds an obligation` and `When a stage gate
fails` rows were not in Task 3.0's table: it named the six destinations it had
sized, but 23 sections shed justification, not six. The shed material had to land
somewhere, and inventing a fifth file for three paragraphs would have cost more
index rows than it saved bytes. Each landed in the nearest existing destination by
subject, and the table now says so rather than leaving three moves unrecorded.
