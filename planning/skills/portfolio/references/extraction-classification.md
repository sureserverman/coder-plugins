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
subcommand references. The true shape after the cut is therefore *a ~7.7 KB trunk
plus four mandatory reads on a default run, or exactly one read on an explicit
subcommand invocation* — not a flat 7.7 KB. A named-subcommand invocation, which
is the common case for `migrate`, `integrate` and `plan-status`, does get the full
saving.

## A `## Reference map` section does not exist yet, and Task 3.2 must create one

The other two trunks index their references from a `## Reference map` table. This
one cites references inline, scattered through the prose — workable at 9 reference
files, unworkable at 17. Task 3.2 adds the section.

It is deliberately **not** a row in the table below. `check-extraction-classification.py`
enforces set equality against the trunk's *real* headings, and a row for a heading
that does not exist yet fails immediately. Task 3.2 adds the heading and its row in
the same change, so the guard is green before and after. Its budget is carried in
the derivation block as a named line, not hidden in scaffolding.

## Derived ceiling — estimated at Task 3.0

```
                            bytes     retained
unconditional   (4 sec)      2121         2121
rule+elab       (3 sec)      2508         1200
conditional     (9 sec)     21045         2110
scaffolding                  1597         1597
new Reference map section       0          700
----------------------------------------------
TOTAL                       27271         7728
```

The four `bytes` rows sum to 27271 exactly — the measured file size. The ninth
`conditional` row is `Remember`, retained at 0 because it is proposed for deletion;
see below.

**Estimated ceiling: 7728 B**, a **71.7%** reduction. Recorded in
`scripts/trunk-budget.txt` as a `# derived-ceiling:` **comment**, not an active
ceiling: promoting it while the trunk is still 27271 B would fail the ratchet and
redden the suite between two green tasks. Task 3.2 promotes it when the cut lands.

**If Task 3.2's real retained total exceeds this, record the miss and re-derive.
Never move an obligation to hit the number.**

**`## Remember` is proposed for deletion, not relocation.** It restates rules the
trunk states in their own sections — `scan → unify → maturity → rebuild`
(`../SKILL.md` § Default flow), first-run-exits and registry-is-canonical
(`../SKILL.md` § `scan`), dry-run-default and zero-writes
(`../SKILL.md` § Hard rules). Relocating a duplicate preserves exactly the drift
BL-039 documented. Stage 2 deleted `executing-plans`' `## Remember` on this
reasoning with the register owner's explicit approval; **this one carries the same
reasoning and needs the same approval before Task 3.2 acts on it.**

It is filed as a `conditional` row with `retained 0` rather than under a class of
its own, because `deleted` is not one of the three classes the guards parse — a
`### deleted` heading would leave the rows under it silently inheriting the
preceding class instead of being rejected. **If approval is withheld**, the row's
retained figure becomes ~417 (the section stays whole) and the ceiling rises to
8145; nothing else in this classification changes.

## The table

`bytes` is the section's size in the 27271 B trunk. `retained` is the estimate
Task 3.2 is measured against.

### unconditional — 4 sections, 2121 B, 2121 B retained

| bytes | retained | section | reason |
|---|---|---|---|
| 862 | 862 | Resolver (read this before any read/write) | its own heading says read before any read/write; the no-silent-fallback rule guards every write |
| 744 | 744 | File conflicts and write discipline | the never-mutate-docs/-directly rules bind every subcommand |
| 499 | 499 | Hard rules | dry-run default, the 8-in-flight cap, enabled:false exclusion — every run |
| 16 | 16 | Subcommands | section header |

### rule+elaboration — 3 sections, 2508 B, 1200 B retained

| bytes | retained | section | reason |
|---|---|---|---|
| 1178 | 600 | Default flow (no subcommand, or explicit `portfolio` invocation) | the four-op order and the idempotency guarantee stay; the ASCII sequence block restates them |
| 716 | 300 | Staged rollout | the `--include-maturity` gate is the rule; the rollout rationale is elaboration |
| 614 | 300 | Configuration: `~/.claude/portfolio-config.yaml` | the key list and the missing-file default stay; the sample block moves |

### conditional — 9 sections, 21045 B, 2110 B retained

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
| 417 | 0 | Remember | pure restatement of the trunk's own Default flow, `scan` and Hard rules sections; proposed for DELETION rather than relocation, since relocating a duplicate preserves drift — pending the approval this file records |

## Retention markers

A heading over a pointer satisfies set equality perfectly and loses the rule, so
each binding row names a string that must be **trunk-resident** after the cut.
`scripts/check-trunk-retention.py` sweeps this table in full. `conditional` rows
are exempt by construction — they are the ones that were supposed to leave, and
their retained pointer is checked by the DEAD-PATH half of
`check-extraction-integrity.py` instead.

| section | must appear in the trunk |
|---|---|
| Resolver (read this before any read/write) | No silent fallback |
| Resolver (read this before any read/write) | fails loudly |
| Resolver (read this before any read/write) | NEVER write to |
| Subcommands | Subcommands |
| Default flow (no subcommand, or explicit `portfolio` invocation) | scan |
| Default flow (no subcommand, or explicit `portfolio` invocation) | Idempotency guarantee |
| Default flow (no subcommand, or explicit `portfolio` invocation) | Confirms with the user before any mutation |
| Staged rollout | --include-maturity |
| Configuration: `~/.claude/portfolio-config.yaml` | vault_dir |
| Configuration: `~/.claude/portfolio-config.yaml` | never aborts |
| File conflicts and write discipline | Never mutate a project's |
| File conflicts and write discipline | no two agents touch the same path |
| Hard rules | Dry-run is the default for every write-capable subcommand |
| Hard rules | non-negotiable |
| Hard rules | are excluded from |

## Where the conditional material will go

**Destinations are named, not linked, because Task 3.2 creates them.** A
backticked `../references/<file>.md` here would be a dead pointer until the cut
lands, and `check-extraction-integrity.py` is right to reject one — this plan
exists to stop exactly that. Task 3.2 rewrites this column into real paths in the
same change that creates the files, at which point they resolve.

| moved from | destination (all new) |
|---|---|
| `scan`'s first-run + drift procedures | `subcommand-scan` |
| `unify`'s fan-out procedure | `subcommand-unify` |
| `maturity`'s audit procedure | `subcommand-maturity` |
| `migrate`'s per-project procedure + rollback | `subcommand-migrate` |
| `integrate`'s rollup procedure | `subcommand-integrate` |
| `rebuild`'s eight steps + the business/security layers | `subcommand-rebuild` |
| `plan-status`' classification + evidence grades | `subcommand-plan-status` |
| Integration list | `integration` |
| `Remember` | deleted — restatement, not relocated (pending approval) |

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
