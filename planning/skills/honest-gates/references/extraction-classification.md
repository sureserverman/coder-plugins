# Extraction classification — `../SKILL.md`

Produced by `2026-09-01-honest-gates-rule-gaps-plan.md`, Stage 1 Task 1.1, closing BL-102.
Trunk measured at **15802 B** across **8 headings** plus 674 B of scaffolding (frontmatter,
title, preamble), at commit `b0fc9fe`, by:

```
python3 scripts/trunk-sections.py planning/skills/honest-gates/SKILL.md
```

Every figure in the table is that command's output at that sha, and the rows sum to the file
size exactly. Task 1.2 re-emits the `retained` column from the same command after the cut;
until then `retained` equals `bytes` because nothing has moved.

**This table is the authority for what may leave the trunk.** A section marked
`unconditional` stays whole. A section marked `rule+elaboration` keeps its rule and sheds
its justification — the incident narratives and worked examples — into
`references/incidents.md`. Only `conditional` sections leave.

**Why honest-gates is classified at all, given that it was never extracted before.** BL-102
measured on 2026-08-28 that deleting an entire rule section from this trunk left the full
suite green, because the trunk was in neither guard's PAIRS list. The entry's own constraint
forbade the obvious fix — a classification table with invented byte counts to satisfy the
pairing — so the pairing is earned here by a real extraction with real numbers. The rule this
implements is the one `scripts/trunk-budget.txt` records for every honest-gates ceiling
raise: these are **write-time disciplines**, so a rule sentence never leaves the trunk, and
only the story behind it may.

## The table

### unconditional — 3 sections, 2515 B, 2515 B retained

| bytes | retained | section | reason |
|---|---|---|---|
| 824 | 824 | The one rule | the definition of green and BLOCKED; every gate report is written under it |
| 1410 | 1410 | When a gate is BLOCKED | the five-step procedure and the `[~]` rule; binds the moment a check cannot run |
| 281 | 281 | Reporting | the three states and the collapse prohibition; every status report is written under it |

### rule+elaboration — 4 sections, 12215 B, 12215 B retained

| bytes | retained | section | reason |
|---|---|---|---|
| 2635 | 2635 | Prohibited (these are gate-faking) | eight prohibitions stay whole; the amendment bullet's second half is elaboration of the pointer it already carries |
| 3122 | 3122 | A behavioral claim is a gate too | the cite-your-source rule, the absence/aggregate shapes and the two teeth stay; the `178f988`/`edaeba2` correction story is the incident |
| 4301 | 4301 | A test does not exist until its mutant dies | the mechanism question, the two ways out, the three numbered rules and the discriminating-cause rule stay; the checker-that-cost-five-Criticals paragraph, the `Portfolio/` fixture story and the "why this is not covered" paragraph are the incidents |
| 2157 | 2157 | Changing a contract reclassifies everything already written | the do-not-ship rule, the inventory-is-a-command rule and the tier line stay; the `4bb486e` worked example and its 19-plan count are the incident |

### conditional — 1 section, 398 B, 398 B retained

| bytes | retained | section | reason |
|---|---|---|---|
| 398 | 398 | Integration | pointers to the skills that consume these rules; consulted only when routing to one |

## Where the conditional material went

Nothing has moved at Task 1.1. Task 1.2 fills this in with the destination of each
extracted paragraph.

| section | destination |
|---|---|
| Integration | stays — 398 B of pointers is cheaper than a pointer to the pointers |

## Retention markers

Each row names a string that must be **trunk-resident**, in the body of the section that
claims it (not its heading line), on one physical line. `scripts/check-trunk-retention.py`
sweeps this table in full; a marker pins **presence, never assertion** (BL-075), so a rule
inverted in place around its marker text still passes — the contract suite in `../tests/`
is what reads the sentences.

**One marker per obligation, not per section.** § Prohibited retains eight distinct
prohibitions; pinned by one string, seven could be demoted with this sweep green.

| section | marker |
|---|---|
| The one rule | A gate is green only when its real command ran in the current environment and |
| The one rule | If you cannot make the real check run here, the gate is **BLOCKED**, not green. |
| Prohibited (these are gate-faking) | No-op tasks that impersonate a gate. |
| Prohibited (these are gate-faking) | Fabricated evidence. |
| Prohibited (these are gate-faking) | Silently excluding the failing case. |
| Prohibited (these are gate-faking) | Heuristic self-grading. |
| Prohibited (these are gate-faking) | Proxy data that doesn't measure what the gate measures. |
| Prohibited (these are gate-faking) | Unannotated amendment of a gate's own checks. |
| Prohibited (these are gate-faking) | Verifying against a dirty working tree. |
| When a gate is BLOCKED | Stop on that gate. |
| When a gate is BLOCKED | Name the exact blocker |
| When a gate is BLOCKED | Try to unblock it for real |
| When a gate is BLOCKED | escalate to the user |
| When a gate is BLOCKED | Write the checklist item as `- [~]`, never `- [x]` with a note explaining |
| When a gate is BLOCKED | Preflight blockers (repo/SDK/device marked FAILED) are BLOCKED gates by |
| A behavioral claim is a gate too | what a script covers — **cite the |
| A behavioral claim is a gate too | An absence claim |
| A behavioral claim is a gate too | An emergent or aggregate claim |
| A behavioral claim is a gate too | A correction is a new claim. |
| A behavioral claim is a gate too | Unrequested specificity is where errors hide. |
| A behavioral claim is a gate too | This one cannot be a script. |
| A test does not exist until its mutant dies | can this mechanism decide this property? |
| A test does not exist until its mutant dies | Make the property structural |
| A test does not exist until its mutant dies | Write the set down before the fix. |
| A test does not exist until its mutant dies | Revert the fix; the suite must go red. |
| A test does not exist until its mutant dies | Build fixtures from the requirement, never from observed behavior. |
| A test does not exist until its mutant dies | Assert the discriminating cause, not the outcome. |
| Changing a contract reclassifies everything already written | A change to a parsing contract, marker vocabulary or classification rule does not ship |
| Changing a contract reclassifies everything already written | The inventory is a command and its output, never an estimate. |
| Changing a contract reclassifies everything already written | Tier: untiered. |
| Reporting | every gate is one of: **GREEN** |
| Reporting | Never collapse BLOCKED into GREEN. |
