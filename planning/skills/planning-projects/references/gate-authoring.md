# Gate authoring — the measurements behind the rules

`../SKILL.md` § Phase 4 — Stage Gates and its subsections carry the rules an author must
follow. This file carries the measured incidents those rules were derived from, and the
accretion argument behind `../SKILL.md` § A plan that adds an obligation names what it removes.

## Why a process only ever grows

Every plan arrives with a reason to *add* a step, and none arrives with a reason to *remove*
one. That growth is invisible per plan and obvious in aggregate: each new rule is individually
defensible, and the sum is a workflow where a small change costs more than it is worth. Nothing
in this skill previously asked the question, which is why it kept happening — the Removes /
Replaces / Adds-net rule exists to make the question unavoidable rather than to make adding
hard.

The point of the `Adds, net:` option is that it must be *argued*, not assumed. A run cannot be
asked to weigh a cost nobody wrote down.

## DEC-017, and the measurement behind it

DEC-010 established that a mandate costing an **agent dispatch** must name the tier that gates
it. DEC-017 extends the same requirement to a mandate costing a **command**, because those
accrete the same way and are easier to wave through precisely because each one is cheap.

A gate sweep is a line of text to write and minutes to run — on every future execution of every
plan. Nobody compares the second number to what the sweep protects unless a rule asks.

**Measured:** one sub-plan's four-tree stage-scope command, re-run at every gate and every
remediation round, produced **13 broad sweeps in a single session**, re-proving code that had
not changed.

So a plan adding a mandate names which of three things governs it — a **review-scope tier**
(anything dispatching an agent), a **test-scope tier** (task / fix / stage / plan, for a test
command), or a **position** (once per gate entry, final gate only, close-out only). "It runs
every time" is a legitimate answer; it is simply the one that must be argued hardest.

## Every fact has one owner — the measured incident

A check that re-runs a task's own assertion buys nothing: the task cannot be green without it.

**Observed live (remote-agents `bot-live-view` sub-plan 01, 2026-08-10):** a single fact —
view-expiry was removed — was verified **four times**:

1. a task test asserting no `expires_at` column,
2. a Stage-1 gate grep,
3. the same grep repeated at close-out,
4. a `(judgment)` line asking an evaluator to confirm no surviving claim that a view can
   expire.

Two of those are legitimate and distinct, and they are exactly the two exceptions the trunk
names: the task test (this migration is right) and one tree-wide sweep (the vocabulary is gone
everywhere). The repeat and the judgment line were cost with no coverage behind it.

The `(judgment)` line is the worst place for this defect because the marker routes to an
evaluator dispatch — the most expensive check in the plan — so spending it on a question a
command has already answered pays the maximum price for zero information.

## Where the class-predicate rule fits

The "strictly wider set" exception is the class-predicate rule doing its job: the gate owns the
*class*, the task owns its *instance*. The widening has to be **nameable** — "the task proved
the column is gone from the migration; the gate sweeps the whole source tree for the
vocabulary" — because an unnameable widening is indistinguishable from a duplicate.

## A gate heuristic ships with a severity axis and a measured trigger rate

This governs the plugin's own checks — a validator finding, an audit pattern, a detector a
gate calls — not the checks a plan author writes into a stage gate.

Any heuristic wired into a gate ships with a severity axis and a trigger rate. The axis has
two values, blocking and advisory. The trigger rate is measured over a real corpus, stated in
its source with the corpus and the date, in the form
`measured <date> over <corpus>: <n> hits, <t> true`. A blocking finding is one whose measured hits were all true defects, over at least one hit.
Anything less is advisory: it is reported and named in the gate report, and it never exits 1
and never fails a gate (`plan-flip-audit.py` exits 4 on advisory findings alone).

**Measured, and the reason this is a rule.** `plan-flip-audit.py`'s void detector began as
one flat vocabulary where any hit was a RED gate. Over 188 real plans it lit **31.4%** of
them, with a 39.8% hard false-positive rate; the dominant cause was `amended` (44% of hits),
a word the amendment protocol requires an honest executor to write (`plan-flip-audit.py`'s
VOID_STRONG comment). Split into a blocking tier (phrases that say the work did not happen)
and an advisory tier (qualifiers that void only in company), the same corpus lit **12.8%**,
measured at the engineering-skills port that filed BL-090, and the check stayed on. At 31.4% it would have been waived, and
the waiver written as a note beside a green gate: the artifact the check exists to abolish.

A check too noisy to leave on is a defect in the check. It is fixed there — narrowed, split,
or moved to advisory — and the plans it flags carry it as a finding against the check, not as
a residual of their own. A heuristic with no measured rate has no ground for either tier: it
ships advisory until one is measured.

Position (DEC-017): once, when the check is built or its trigger changes. The measurement
over the vault corpus runs in the building task's test, never in a repo validator
(DEC-022).

## The plan's goal is a check from the first gate

Every Standard plan, Light plan and master register entry carries at least one gate check
marked `(goal)`. It is the plan's goal written as a sweep over the **whole** artifact the goal
is about. The rest of a gate proves what a stage built; the `(goal)` check proves the stage
has not left the plan's goal short.

- **The goal check sweeps the whole artifact.** It is never a subset by category: a sweep
  restricted by a filter (`awk '$3 ~ /-new/'`, `git ls-files | grep -v …`) checks the members
  the filter keeps and none of the rest. Where the subset really is the whole set, say so with
  `(scoped)` (`set-valued-checks.md` § The sixth error).
- **It sits in every gate from the first one whose artifact exists.** That is its position
  under DEC-017, and it makes a gap fail at the stage that made it rather than at close-out.
- **It must be cheap.** A sweep, not a suite: it runs at every gate of every execution.
- **`(judgment)` is allowed on it only where no command can decide the goal.** Write
  `**(goal)** **(judgment)** …` and name what the reader decides.
- `(goal)` is orthogonal to shape. The check is still classified, so an instance-shaped goal
  check is still INSTANCE-SHAPED.

`../scripts/validate-gate-checks.py` reports a plan or master entry with no `(goal)` check as
GOAL-CHECK-MISSING, and a filtered sweep as FILTERED-SUBSET. Both are advisory notes (DEC-032).
A **new** plan is presented with zero GOAL-CHECK-MISSING, as it is with zero INSTANCE-SHAPED.
It checks presence, not placement: a plan whose one `(goal)` check sits in its final gate
reports zero. Placement from the first gate is the author's call, and the Tier-2 reviewer's
to question.

**Measured incident (engineering-skills `2026-10-07-upstream-delta-sub-01`, 2026-10-08).** The
sub-plan's register Goal ends "the three lane sub-plans can then execute from the spec
alone". Its Stage 2 gate swept `awk -F'|' '$3 ~ /-new/'`, the `-new` rows only, while six
`-fork` rows needed rulings too. No check swept the goal over the whole lane table. The
Stage 3 gate spent 4 remediation rounds against a budget of 2 (its handoff note records
both). The close-out evaluator, the first reader given the plan goal, then found two `-fork`
rows with no ruling — reported in coder-plugins `2026-10-08-end-goal-checks` research, and
not yet in the engineering-skills record. Raising the budget buys repair attempts, not
earlier detection; a `(goal)` check at the Stage 2 gate would have failed there.

## When a stage gate fails

`executing-plans` owns the operative procedure and is the single source of truth for it:
severity classification (Critical / Important / Suggestion), a bounded remediation budget
defaulting to 2 rounds, an exit criterion that passes when no Critical remains and every
Important is fixed (the `backlog` takes a significant improvement or a decision the user must
make, never a defect found while running the plan), and escalation with a residual list on
exhaustion.

Those rules are deliberately **not** restated in `../SKILL.md`; a second copy is how the two
drift apart. What matters at *authoring* time is unchanged either way: the plan's gate checks
must be shaped so a class can fail them at all.
