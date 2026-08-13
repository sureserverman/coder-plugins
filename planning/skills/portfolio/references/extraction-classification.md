# Extraction classification — `../SKILL.md`

Produced by the token-efficiency plan, Stage 3 Task 3.0, on 2026-08-11.
Trunk measured at **27271 B** across **16 headings** plus 1597 B of scaffolding
(frontmatter, title, the five-point orientation list, and the vault-canonical
paragraph — all of it above the first heading).

**This table is the authority for what Task 3.2 may move.** A section marked
`unconditional` stays in the trunk whole. A section marked `rule+elaboration`
keeps its rule and sheds its justification. Only `conditional` sections leave.

## This trunk is shaped differently from the other two

`executing-plans` and `planning-projects` are single procedures read top to
bottom. **`portfolio` is a dispatcher**: seven subcommands, of which an explicit
invocation runs exactly one. That is the textbook `conditional` shape — per-branch
procedure consulted only when that branch is taken — and it is why this trunk's
estimated reduction (71.7%) is so much larger than `planning-projects`' 41.5%.
The difference is structural, not a sign that this classification was bolder.

**The honest qualification, carried in from Stage 2's Minor m1.** That stage
recorded that calling the extracted material "conditional machinery" was
optimistic, because four of `executing-plans`' references fire on essentially
every run. The same caveat applies here and is stated up front rather than
discovered later: **the default flow (no subcommand) runs `scan` → `unify` →
`maturity` → `rebuild`**, so a default invocation reads **four** of the seven
subcommand references. The true shape after the cut is therefore *a trunk plus
four mandatory reads on a default run, or exactly one read on an explicit
subcommand invocation* — not a flat trunk-sized figure. A named-subcommand
invocation, which is the common case for `migrate`, `integrate` and `plan-status`,
does get the full saving. Measured after the cut: an 11950 B trunk, and the four
default-flow references total 12505 B.

## The `## Reference map` section, created at Task 3.2

The other two trunks index their references from a `## Reference map` table. This
one cited references inline, scattered through the prose — workable at 9 reference
files, unworkable at 17. Task 3.2 added the section.

It was deliberately **not** a row in the table at Task 3.0.
`check-extraction-classification.py` enforces set equality against the trunk's
*real* headings, and a row for a heading that did not exist yet fails immediately.
Task 3.2 added the heading and its row in the same change, so the guard was green
before and after. It is classified `unconditional`: it is the index, and without it
no reference is reachable.

## Derived ceiling — estimated at Task 3.0

```
                            bytes     retained
unconditional   (4 pre-existing sec)  2121    2121
rule+elab       (3 sec)      2508         1200
conditional     (9 sec)     21045         2527
scaffolding                  1597         1597
new Reference map section       0          700
----------------------------------------------
TOTAL                       27271         8145
```

The four `bytes` rows sum to 27271 exactly — the measured file size.

**Estimated ceiling: 8145 B**, a **70.1%** reduction. Recorded in
`scripts/trunk-budget.txt` as a `# derived-ceiling:` **comment**, not an active
ceiling: promoting it while the trunk was still 27271 B would have failed the
ratchet and reddened the suite between two green tasks. Task 3.2 promotes it when
the cut lands.

**If Task 3.2's real retained total exceeds this, record the miss and re-derive.
Never move an obligation to hit the number.**

**`## Remember` is RETAINED, not deleted.** Task 3.0 proposed deleting it: it
restates rules the trunk states in their own sections — the four-op order
(`../SKILL.md` § Default flow), first-run-exits and registry-is-canonical
(`../SKILL.md` § `scan`), dry-run-default and zero-writes
(`../SKILL.md` § Hard rules) — and relocating a duplicate preserves exactly the
drift BL-039 documented. Stage 2 deleted `executing-plans`' `## Remember` on this
reasoning **with the register owner's explicit approval**. That approval was never
obtained for this one, so Task 3.2 kept the section whole and targeted 8145 rather
than the 7728 the deletion would have allowed. **The section is retained pending a
separate decision by the register owner**; deleting it later is a trivial
follow-up, and deleting it now on an approval nobody gave is not reversible in the
same cheap way. `scripts/trunk-budget.txt` still carries `# derived-ceiling: 7728`
as the record of the estimate made under the deletion assumption.

It is filed as a `conditional` row rather than under a class of its own, because
`deleted` is not one of the three classes the guards parse — a `### deleted`
heading would leave the rows under it silently inheriting the preceding class
instead of being rejected. Its retained figure is its full ~417 B.

## Re-derived at Task 3.2 — the ceiling was MISSED by 3805 B

The cut landed at **11950 B**, a **56.2%** reduction, against an estimated 8145
(70.1%). The ceiling in `scripts/trunk-budget.txt` is set to 11950 — what was
actually retained — rather than the estimate, because every byte of the gap is
either a rule a branch owns or index text the extraction itself created.

```
                            bytes   estimated    actual
unconditional   (4 pre-existing sec)  2121    2121      2234
rule+elab       (3 sec)      2508        1200      1725
conditional     (9 sec)     21045        2527      4747
scaffolding                  1597        1597      1596
Reference map section           0         700      1648
-----------------------------------------------------
TOTAL                       27271        8145     11950
```

Both derivation blocks count `unconditional` as **4** because they account for the
four sections that existed in the 27271 B trunk; the fifth, `Reference map`, is
broken out on its own line since it did not exist to be measured. The class table
below therefore lists 5 rows against a block that says 4, and that is not a
discrepancy.

**The `retained` column in the class tables is Task 3.0's ESTIMATE.** Actuals live
in the re-derived block, and the two are deliberately not reconciled row by row —
the estimate is kept as authored so the miss stays legible.

*(Both actual columns were measured by Task 3.2 at commit `df5ea44`. The Stage 3
gate's remediation round edited the trunk afterwards — a corrected subcommand
count, a repointed citation — so they are that commit's measurements, not HEAD's.
`scripts/trunk-budget.txt` carries the live ceiling; these figures explain a cut,
they do not track the file.)*

**The miss is mostly in `conditional`, and the cause is a per-pointer floor.**
That row retained **22.6%**, not the 10% Task 3.0 estimated. Measured per section:

```
section          bytes   after   kept
rebuild           5686     732   12.9%
plan-status       4522     700   15.5%
migrate           3374     833   24.7%
scan              2187     383   17.5%
unify             1756     447   25.5%
integrate         1232     475   38.6%
maturity          1160     398   34.3%
Integration        711     361   50.8%
Remember           418     418  100.0%
```

**Retention is not proportional to the source; it is roughly constant per
section.** Excluding `Remember` (retained by decision, not by compression), the
eight pointers average **541 B** with a range of 361–833, and the ratio tracks the
*inverse* of the source size — 12.9% for the largest section and 50.8% for the
smallest. A pointer has a fixed cost: name what the subcommand does, state the
inputs gate that decides whether it writes, carry the invariants the branch owns,
and cite the file. That cost does not shrink because the procedure behind it was
short. **A future estimator should size `conditional` as `n_sections × ~500 B`,
not as a percentage of bytes.** Applied here that rule predicts 9 × 500 = 4500
against an actual 4747.

**Why the pointers are that size at all, and why they should be.** This is a
*dispatcher*, and a dispatcher's branches are where the destructive behavior
lives. Each retained pointer had to keep at least one rule that binds even when
its reference is never opened: `migrate`'s copy→verify→delete invariant,
`integrate`'s asymmetries-are-never-auto-fixed, `rebuild`'s PRESERVE block and
its degrade-but-never-truncate rule, `plan-status`' report-first default and its
never-infers-`**Abandoned:**` rule, `scan`'s seed-then-exit. Stage 2's measured
failure was leaving exactly this kind of rule as a noun inside a pointer
sentence; the extra bytes here are that lesson applied.

**`Reference map` at 1648 B against 700.** Seventeen rows, and a row costs ~45 B
before any text is written. Task 3.1 saw the same direction (627 → 1028 for four
new rows). An index that grows with the extraction is the extraction working, but
the estimate should carry `~45 B × n_files + ~200 B` rather than a flat figure.

**One row retained 100%, and it is the same shape Task 3.1 found.**
`Configuration: ~/.claude/portfolio-config.yaml` was sized at 300 of 614 on the
reasoning that "the sample block moves". The sample block **is** the key list and
the missing-file default — the two things the row promised to keep — so there was
no justification layer under it to shed. Task 3.1's finding restated: the
retention ratio is a property of the section's *shape*, not of its class, and an
enumeration has no 45% in it at any level of effort.

## The table

`bytes` is the section's size in the 27271 B trunk. `retained` is the estimate
Task 3.2 is measured against.

### unconditional — 5 sections, 2121 B, 2821 B retained

The fifth section, `Reference map`, contributes 0 bytes because it did not exist in
the 27271 B trunk; Task 3.2 created it, and its 700 B estimate is the derivation
block's named line rather than a share of the measured file.

| bytes | retained | section | reason |
|---|---|---|---|
| 862 | 862 | Resolver (read this before any read/write) | its own heading says read before any read/write; the no-silent-fallback rule guards every write |
| 744 | 744 | File conflicts and write discipline | the never-mutate-docs/-directly rules bind every subcommand |
| 499 | 499 | Hard rules | dry-run default, the 8-in-flight cap, enabled:false exclusion — every run |
| 16 | 16 | Subcommands | section header |
| 0 | 700 | Reference map | created at Task 3.2 — the index over 17 reference files; without it no reference is reachable, so it may never become a pointer itself |

### rule+elaboration — 3 sections, 2508 B, 1200 B retained

| bytes | retained | section | reason |
|---|---|---|---|
| 1178 | 600 | Default flow (no subcommand, or explicit `portfolio` invocation) | the four-op order and the idempotency guarantee stay; the ASCII sequence block restates them |
| 716 | 300 | Staged rollout | the `--include-maturity` gate is the rule; the rollout rationale is elaboration |
| 614 | 300 | Configuration: `~/.claude/portfolio-config.yaml` | the key list and the missing-file default stay — AMENDED at Task 3.2: the row said "the sample block moves", and it did not, because the sample block IS the key list and the missing-file default. Nothing under it was justification, so the section retained 614 of 614 |

### conditional — 9 sections, 21045 B, 2527 B retained

| bytes | retained | section | reason |
|---|---|---|---|
| 5686 | 330 | `rebuild` — regenerate the global roll-ups (in the vault) + enrich sidecars | eight-step procedure read only when rebuild runs |
| 4522 | 320 | `plan-status` — reconcile every vault plan's recorded status against its real progress | classification and evidence-grading detail, read only on this subcommand |
| 3374 | 320 | `migrate` — move a project's operational docs from its repo into the vault (one-time) | a one-time per-project procedure; the retained pointer must name the copy→verify→delete invariant |
| 2187 | 260 | `scan` — load the registry, detect drift, optionally first-run-seed | first-run and drift procedures, read only when scan runs |
| 1756 | 240 | `unify` — derive backlog candidates for every enabled project, in parallel | the six-step fan-out; its two hard rules are already restated in `../SKILL.md` § Hard rules |
| 1232 | 210 | `integrate` — roll up inter-project edges + integration backlog | four-step rollup, read only on this subcommand |
| 1160 | 210 | `maturity` — audit per-project MATURITY.md and surface staleness | four-step audit, read only on this subcommand |
| 711 | 220 | Integration | per-skill descriptions consulted only when routing to one |
| 417 | 417 | Remember | pure restatement of the trunk's own Default flow, `scan` and Hard rules sections; Task 3.0 proposed DELETION rather than relocation, since relocating a duplicate preserves drift — AMENDED at Task 3.2: the approval that proposal was pending was never given, so the section is RETAINED WHOLE pending a separate decision by the register owner |

## Retention markers

A heading over a pointer satisfies set equality perfectly and loses the rule, so
each binding row names a string that must be **trunk-resident** after the cut.
`scripts/check-trunk-retention.py` sweeps this table in full. `conditional` rows
are exempt by construction — they are the ones that were supposed to leave, and
their retained pointer is checked by the DEAD-PATH half of
`check-extraction-integrity.py` instead.

**One marker was RETIRED after the cut, and the reason belongs here rather than in
a commit message.** `Configuration:` originally pinned **`never aborts`**. That
phrase was deleted by the DEC-013 defect fix this file records under the heading
"One inconsistency found while classifying" — it was the tail of a sentence
promising to fall back to
`~/.claude/` writes, a destination retired when storage went vault-canonical. The
marker was pinning a stale claim, so keeping it would have forced the stale claim
to stay.

**Retiring a marker is the move this guard's `UNMARKED-SECTION` check exists to
make expensive**, because deleting a marker silences a row just as effectively as
keeping its rule. So it is replaced, not merely removed: `optional except` and
`not settled` pin what the section now actually promises — that `vault_dir` is the
one required key, and that the set-but-missing case is openly undecided rather
than answered by a pointer at retired storage. The section's marker count went
2 → 3.

| section | must appear in the trunk |
|---|---|
| Reference map | These load when their condition is met |
| Resolver (read this before any read/write) | No silent fallback |
| Resolver (read this before any read/write) | fails loudly |
| Resolver (read this before any read/write) | NEVER write to |
| Subcommands | An explicit invocation runs exactly one |
| Subcommands | composes four, one of them gated |
| Subcommands | Each procedure lives in its own reference |
| Default flow (no subcommand, or explicit `portfolio` invocation) | scan |
| Default flow (no subcommand, or explicit `portfolio` invocation) | Idempotency guarantee |
| Default flow (no subcommand, or explicit `portfolio` invocation) | Confirms with the user before any mutation |
| Staged rollout | skips the maturity step UNLESS |
| Staged rollout | works normally |
| Configuration: `~/.claude/portfolio-config.yaml` | never a fallback |
| Configuration: `~/.claude/portfolio-config.yaml` | optional except |
| Configuration: `~/.claude/portfolio-config.yaml` | not settled |
| File conflicts and write discipline | Never mutate a project's |
| File conflicts and write discipline | no two agents touch the same path |
| Hard rules | Dry-run is the default for every write-capable subcommand |
| Hard rules | non-negotiable |
| Hard rules | are excluded from |

## Where the conditional material went

The files exist as of Task 3.2, so the destinations are links rather than names.

| moved from | destination |
|---|---|
| `scan`'s first-run + drift procedures | `../references/subcommand-scan.md` |
| `unify`'s fan-out procedure | `../references/subcommand-unify.md` |
| `maturity`'s audit procedure | `../references/subcommand-maturity.md` |
| `migrate`'s per-project procedure + rollback | `../references/subcommand-migrate.md` |
| `integrate`'s rollup procedure | `../references/subcommand-integrate.md` |
| `rebuild`'s eight steps + the business/security layers | `../references/subcommand-rebuild.md` |
| `plan-status`' classification + evidence grades | `../references/subcommand-plan-status.md` |
| Integration list | `../references/integration.md` |
| `Staged rollout`'s rationale (the staging window, the 30-scaffolds argument) | `../references/subcommand-maturity.md` |
| `Default flow`'s ASCII sequence block | folded into the four subcommand references it enumerates |
| `Remember` | nowhere — RETAINED WHOLE in the trunk (the deletion was never approved) |

**Three rows are Task 3.2 amendments, not Task 3.0's plan.** The `Staged rollout`
and `Default flow` rows record where shed `rule+elaboration` material landed:
Task 3.0's table sized only the seven subcommand procedures and the Integration
list, but two of the three `rule+elaboration` sections also shed prose, and prose
that leaves has to have a destination or it is a deletion nobody recorded. The
staging-window argument went to the maturity reference by subject. The default
flow's ASCII block was per-op detail already owned by the subcommand it described
(`1. scan — surface drift; if --write confirmed, update registry`), so each line
became the opening sentence of the corresponding reference rather than a new file.
The `Remember` row records the retention, so a reader of this table is not left
believing a section was moved that never went anywhere.

## One inconsistency found while classifying, not fixed here

The trunk's Resolver section says an unset `vault_dir` makes every resolving
subcommand **fail loudly and refuse**. Its Configuration section says a missing
config file means **all defaults**, and that a `vault_dir` pointing at a
non-existent directory logs a warning and **continues, never aborts**.

These are not strictly contradictory — unset, missing-file, and set-but-absent are
three different states — but the trunk never says so, and a reader resolving "no
vault configured" has two rules pointing opposite ways. Task 3.2 must not silently
pick one while compressing: **preserve both statements as written.**

Which behavior is correct is a decision about what `portfolio` should do, not a
defect in the extraction, so it is recorded rather than fixed here.
