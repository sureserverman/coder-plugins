# Preflight checks — the machinery behind each one

The trunk (`../SKILL.md` § Phase 2 — Preflight) carries the rule each of these
checks imposes on every run. This file carries the procedure, the worked
reasoning and the incidents that produced them — read the entry for the check
you are actually running.

## Decisions re-check (the plan's snapshot can be stale)

The decisions register **accretes between planning and execution**. A plan written last
month can be executed against a register that has since gained a constraint, or superseded
one the plan still honors — the same staleness problem the plan's own age signals, applied
to a second artifact.

So Preflight does not trust the recorded section: re-run the scan and diff it.

1. Call the `decisions` skill's `relevant` operation for this project and its stacks
   (`../../decisions/references/domain-slugs.md`).
2. Diff the result against the plan's `## Decisions in force`:
   - **New entry in scope** → surface it before Stage 1. It may invalidate a task.
   - **An entry the plan honors is now superseded** → surface it. The plan may be
     implementing a constraint that no longer holds.
   - **Unchanged** → say so in one line and proceed.
3. **A plan with no section** (written before the convention): report the scan result as
   the working set and proceed. Absence is not exemption.

Surfacing at Preflight is cheap; discovering it at the gate costs a stage. This is a report,
not a stop condition — unless the diff invalidates a task outright, in which case it is a
plan defect and returns to `planning-projects` (`../SKILL.md` § When to revisit earlier steps).

## Calibration re-check (the plan's ceremony can be stale)

The **calibration references accrete between planning and execution**, exactly as the
decisions register does — and a plan's Preflight froze its review-scope tier, its test-scope
commands and its roster at authoring time. A plan written under older rules therefore
executes at older ceremony forever, however much the rules have since improved. This is the
same staleness the decisions re-check exists for, applied to the second thing a plan
records about how it will be run.

So Preflight does not trust the recorded declarations either: recompute and diff them.

1. Recompute from the current rules — `../references/review-scope.md` for the tier (including
   **which tasks** a `high` declaration binds), `../../planning-projects/references/test-scope-tiers.md`
   for the scoped commands, and the roster from the plan's own `Parallel:` fields.
2. Diff against what the plan's Preflight declares:
   - **Unchanged** → say so in one line and proceed.
   - **Changed** → **amend** under the protocol in this file, and state both values in the
     Preflight report (`review-scope: high — recalibrated to bind tasks 1.1, 1.3; as
     authored, bound all 12`).
3. **A plan with no declaration** (written before the convention): recompute and record the
   result as the working set. Absence is not exemption — the same rule the decisions
   re-check applies.

**What is never recomputed: the plan's facts.** Tasks, their `Test:` fields, gate checks'
substance, invariants, `Scope:` sets. Recalibration changes only what the run *costs* — how
many reviews and evaluators it buys, how wide its regression sweeps are. A rule that let
Preflight rewrite what a task must prove would not be recalibration, it would be re-planning
without the user in the room.

## Amending authored ceremony

Execution has always edited authored gate checks when they turned out unrunnable — the
practice existed as ad-hoc `*(corrected during execution …)*` annotations, with no rule
about what may be touched or what must be disclosed. That is the mechanism this protocol
formalizes rather than invents.

An amendment is legal only when all three hold:

- **Unexecuted checks only.** A check belonging to a stage whose gate has already passed, or
  a task already `Status: [x]`, is **never** rewritten. Recorded results describe a run that
  happened; editing their checks retroactively edits the evidence.
- **The annotation cites the authorizing rule.** Not "corrected during execution" but
  `*(amended at Preflight per review-scope.md § task-scoped floor — was: `review-scope: high`
  binding all tasks)*`. A reader must be able to check the amendment against the rule that
  permitted it, which is exactly what the bare form made impossible.
- **The was-value survives.** An amendment that deletes what it replaced leaves no way to
  tell a recalibration from an author's original intent.

**honest-gates treats an unannotated ceremony change as it treats an undisclosed scope
change** — the artifacts are identical either way, so the annotation is the only thing
distinguishing "the rules moved" from "the executor wanted a cheaper run". Amending a check
to make a *failing* gate pass is not recalibration under any reading; that is the gate-
failure procedure, and it is not this.

**What never authorizes an amendment.** Cost, wall-clock and disk are real constraints and
arguments for **re-scoping the plan** — never for re-scoping the evidence a written gate
demands. A suite dropped from a gate command "for disk/time" does not make the gate cheaper;
it is recorded `[~]` **BLOCKED on that suite**, not reported as a pass on the remainder
(`../../honest-gates/SKILL.md`, the *Prohibited* section's excluding-the-failing-case bullet,
which owns this rule).
The tiering policy is not an exception to it: narrowing per `test-scope-tiers.md` drops only
trees the stage's commits neither touched nor depend on, is declared as scope, and lands on
the gate report's scope line — a suite a written check names, or a tree the stage touched,
removed for cost, is an amendment whatever the report calls it, and cost is not among the
rules that can authorize one.

**Verify against committed state.** Recompute from the plan file as committed and confirm
the working tree is clean before recording any Preflight result. A calibration re-check run
over uncommitted edits certifies a plan nobody else can see — the same defect as a gate
verified against a dirty working tree, one phase earlier
(`/mnt/vault/Gotchas/Gate Verified Against Uncommitted Working Tree.md`).

## Access probe (hardware and remote targets are proven by I/O, not by environment)

"Access / permissions verified" used to say nothing about what verification is, and twice
an executor read an unset `PI_MODEM_HIL_CM4` and concluded the hardware did not exist —
while the repo's own deploy script named the host, and the same executor had edited that
script. Its own admission: *"The CM4 was never missing. The gate never tried SSH."*

So for every device, board, VM or remote host a task or gate depends on:

1. **Resolve the target from the repo's own deploy, HIL or provisioning scripts** — the
   address, port, user and serial the project already uses — before concluding anything
   from an environment variable. An unset variable is **missing configuration**; only an
   executed probe can report **missing hardware**, and the two have opposite consequences
   for a gate.
2. **Run a probe** (ssh, ping, a serial identity read — whatever the project's scripts do)
   and **record what answered**, verbatim, in the Preflight report.
3. **Nothing answered** → the target is unreachable: Preflight fails on that line, and every
   gate needing it is **BLOCKED**, written `[~]`. **Something answered but was not what was
   expected** (wrong serial, wrong identity, auth refused) → **investigate before excusing**:
   in the incident the day's first probe found the device genuinely down, the second failed
   on the probe's own `BatchMode=yes` against a password-only host, and a third defect sat
   behind that in the serial comparison — two of three failures were the tool's, not the
   device's, and an env-var check would have reported "no hardware" at every one of them.

Position, per DEC-017: once at Preflight, like the gate-selector probe. A command,
never a dispatch, so untiered. This plugin ships no probe script. The Cursor port in the
engineering-skills repo does (a probe-device shell script under its executing-plans port's
scripts, checked 2026-09-02): exit 78 when nothing answered, exit 1 when something
answered but was not what was expected, exit 0 on a match — those exit codes encode
exactly the split in step 3.

## Gate-selector probe (a gate that cannot pass is a plan defect, not a gate failure)

`planning-projects` cross-references every `pytest <file> -k <expr>` in a gate against the
plan's task `Test:` fields at authoring time (its `validate-gate-checks.py` reports
SELECTOR-UNMATCHED). That check is static, because at authoring time the selected tests
usually do not exist yet. **Preflight runs the half that authoring could not**: here, the
tests either exist or are about to be created by a named task.

For every gate check invoking pytest whose target file exists now:

```
pytest --collect-only -q <the check's selector>
```

- **Collects ≥1 test** → fine, proceed.
- **Collects 0, and no task in the plan creates that test** → **plan defect**. Stop and
  return it to `planning-projects` (`../SKILL.md` § When to revisit earlier steps), exactly
  as an invalidated task in the decisions re-check does. The gate cannot pass however well
  the work goes, so discovering it now saves the stage it would otherwise fail at.
- **Collects 0, but a task's `Test:` builds toward it** → expected. Record which task
  satisfies the selector (`gate-selector: Stage 1 gate `-k restart` — created by Task 1.4`)
  so the gate report can say why an empty collection at Preflight was not a defect.
- **Target file does not exist yet** → same as the previous case: name the task that creates
  it, or it is a defect.

This is a **command, not a dispatch**, so it is not tier-gated by review-scope (DEC-010's
cost rule: a mandate costing an agent dispatch is tiered). Its own gate, per **DEC-017**, is
a **position** — once at Preflight, never per stage — which is what that entry requires a
command-costing mandate to name. It exists because the class has now shipped twice — the
check that motivated 0.40.0's `(scoped)` marker, and remote-agents `bot-live-view` sub-01,
whose Stage 1 gate named a real e2e file with a filter matching nothing in it and was
discovered only by failing mid-stage.

## Git bootstrap (hard prerequisite for commit-per-task)

Every task commits its own work (`../SKILL.md` § Step 3.3 — Red-Green loop (per task), rule
7), so a working repo must exist before Stage 1:

```
git rev-parse --is-inside-work-tree  →  is this a repo?
├── NO → `git init`, ensure a sane .gitignore, and make an initial commit of the
│        current tree ("chore: initial commit before plan execution") so the
│        first task has a parent. Then offer to create a GitHub remote
│        (`gh repo create <name> --private --source=. --remote=origin`) — create
│        it only on user confirmation; never push a repo public without consent.
│        Execution proceeds locally whether or not a remote is created.
└── YES ↓
On main / master?  → do NOT execute here. Create a feature branch (or worktree)
                     per the Safety rails before Stage 1.
Working tree dirty with unrelated changes? → surface them; don't sweep them into
                     the first task's commit.
```

A missing remote is **not** a stop condition — local commits are the unit of
record. Only an un-initializable repo (e.g. read-only filesystem) blocks here.
