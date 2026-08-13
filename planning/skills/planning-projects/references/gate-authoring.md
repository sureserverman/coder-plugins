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
