# Test-Scope Tiers Reference

Canonical policy for **how much of the test suite runs at each point of plan
execution**. This file is the single source of truth for that policy —
`planning-projects` authors plans that declare their scoped commands, and
`executing-plans` drives gates and review fixes at the tier this file assigns them.

The problem it solves: on a project with an expensive suite (device instrumentation,
e2e, hardware-in-the-loop), a plan that runs "the full suite" at every stage gate and
after every review fix spends hours re-proving code that didn't change. Real
executions have logged 80+ minutes of repeated full device passes in a single
session, plus a `clean` at every gate that throws away all incremental build state
for zero extra verification. Per-task tests were never the problem — targeted,
class-filtered runs cost 1–3 minutes. The waste lives exclusively in **full-suite
re-runs at intermediate checkpoints**.

The fix is not fewer tests — it is the same total coverage, scheduled so the
expensive full pass happens **exactly once per plan**, where it actually protects
the merge.

## The four tiers

| Tier | When it runs | What runs |
|------|--------------|-----------|
| **task-scope** | Every Red-Green cycle | The task's own `Test:` — already targeted (a class filter, a module's unit tests, a single command) — **and nothing else**. The stage-scope command does not run inside a task. |
| **fix-scope** | After a Tier-1/Tier-2 Critical fix, a gate-triage fix, or **any re-verification inside a gate's remediation loop** | Only the test classes/modules the fix touched, plus the originating task's own `Test:` and the gate check that failed. Never the full suite, and never a repeat of the gate's stage-scope command — a review or remediation fix is a targeted change and gets a targeted re-proof. |
| **stage-scope** | Intermediate stage gates | All **cheap host-side checks in full** (unit tests, lint, static/architecture checks, build). **Expensive suites restricted to the modules touched by the stage's commits.** Never `clean`. |
| **plan-scope** | Final stage gate + close-out — once | The full suite from a clean state, including every expensive suite and every quarantined slow test. The one place `clean` belongs. |

`clean` appears in **exactly one command per plan**: the plan-scope pass. An
intermediate gate that wipes incremental state re-buys the whole build for nothing —
regressions an incremental build would miss are exactly what the single clean
plan-scope pass exists to catch.

## A stage-scope pass runs once per gate entry

**The stage-scope command runs once, when the gate is first attempted.** Every
re-verification inside that gate's remediation loop is **fix-scope**, and the gate goes
green on the fix-scope result *plus* the stage-scope result already recorded — which is
still a real pass over real commits, not a remembered one, because the fixes since are
exactly what fix-scope re-proves.

Without this rule the tiers are correct per-run and unbounded in aggregate: a gate that
takes three remediation rounds runs its full stage-scope sweep four times, and nothing in
the table above forbids it. Measured live (remote-agents `bot-live-view` sub-plan 01,
2026-08-10): 75 pytest invocations in one session, of which 10 ran the declared stage-scope
set or the full suite — and **6 of those 10 were labelled per task**, not per gate
(`Full stage-scope suite for Task 2.3`, twice; `for Task 2.4`; `after Task 2.5 fixes`).
Re-measuring that session is what corrected this paragraph: the sweeps were first attributed
to gate re-entries, and most of them were not. A task's own `Test:` was never the problem —
what an executor adds *after* it is, which is what the next section bounds.

**A class sweep is not a fix-scope re-run.** When the repair is a **project-wide class fix**
(DEC-013 — a defect found at a gate is swept across the project and fixed at every member),
fix-scope covers the classes the fix touched, and the fix touched every member of the class:
the sweep *is* the scope, and it runs in full. This rule bounds a gate from re-buying its
whole stage-scope command per round; it does not narrow a repair that legitimately spans the
project. Where the two read as competing, DEC-013 wins and the gate report says which scope
ran, per guard rail 2.

**Accepted cost, stated because it is real.** Running stage-scope once per gate entry means a
remediation fix that breaks a *sibling* module — via a shared dependency or a signature
change — is no longer caught at that gate; it surfaces at the plan-scope pass. That is
latency, not lost coverage: the same trade DEC-010 already accepted at tier `standard`, where
a Critical waits for the stage gate rather than the next task. It is named here so a future
reader meets it as a decision rather than discovering it as a surprise.

**A declared stage-scope command is subject to the same cost threshold as the full
suite.** If the stage-scope command itself crosses ~5 minutes, narrow it: run the cheap
trees the stage's commits *touched or depend on*, not every cheap tree the project owns.
"Cheap host-side checks in full" is an economy when a project has three test trees and a
tax when it has ten — the same sub-plan declared four whole trees as its stage-scope at
every gate, for stages that touched one.

## A stage-scope pass never runs inside a task

**Between a task's Red-Green loop starting and its commit landing, the only tests that run
are the task's own `Test:`** — plus, when a Tier-1 Critical is fixed, that fix's fix-scope.
Nothing else. Not the stage-scope command, not "the suites this task touched", not a
regression sweep across sibling trees. The stage that owns the task runs stage-scope **at its
gate**, once (previous section), and that is where a cross-task regression is meant to
surface.

The previous section bounded a gate to one stage-scope pass per entry and left the per-task
step unbounded, on the belief that per-task runs were already targeted. They were not.
Measured after that rule shipped (sub-plan 02, 2026-08-10, planning 0.41.0 in force):
`Lint and full regression for Task 1.2` ran the stage-scope trees plus `tests/integration`
and `tests/e2e` for **297s** — the whole 290-second suite, for one task, between its green
`-k` test and its commit. A per-gate bound cannot help here, because these runs were never
attributed to a gate.

**Why an executor reaches for it, and why the answer is no.** A task's `Test:` proves the
task; it does not prove the task broke nothing else. That instinct is correct and its
scheduling is wrong — "did this break a sibling?" is precisely the question the stage gate
asks, and asking it n times per stage buys the same answer at n times the price. The
accepted cost is the one the previous section already named and takes one paragraph
further: a task that breaks a sibling module is caught at the stage gate rather than at the
task. That is latency measured in tasks, against a full suite per task.

**What is still allowed.** Widening *within* the task's own subject — running a whole test
file rather than one `-k` filter, or the class the fix touched — is task-scope and needs no
permission. **§ A bug found during execution is a class** is likewise untouched: when a
class sweep genuinely reaches other trees, the sweep is the scope and it runs. The rule
bars the *unprompted* regression sweep, not a repair that legitimately spans the project.

**Disclosure.** A task reporting green on a run wider than its `Test:` says so, under the
same guard rail 2 that governs a scoped gate report. "Ran the stage-scope suite for Task
2.3" is honest and now also a rule violation; running it and reporting only the task's
`Test:` as green is the disclosure failure on top.

## Guard rails

1. **Cost activation threshold.** Tiering applies only when the project's full suite
   is expensive — rule of thumb: **> ~5 minutes** wall-clock. Below that, just run
   the full suite at every gate; scoping ceremony on a 90-second suite is overhead
   with no payoff. A plan states which side of the threshold its project is on
   (see the declaration below), and cheap-suite projects execute exactly as before.

2. **Honest-gates disclosure.** A gate reported green on a scoped run must say what
   scope actually ran — e.g. "gate green — stage-scope: `:features` instrumented +
   full `check`". Reporting a stage-scope run as "full suite green" is gate-faking
   under the `honest-gates` contract. The tier vocabulary exists so the report can
   be honest *and* short.

3. **Expensive-test quarantine.** Any single test or fixture costing **> ~2 minutes**
   goes behind an opt-in filter (an `@LargeTest`-style annotation, a Gradle
   property, a pytest marker) and runs only at plan-scope. A slow test inside the
   default suite taxes every scoped run that touches its module; quarantined, it
   costs exactly one run per plan.

4. **Overlap with reviews.** An expensive stage-scope suite and the Tier-2 stage
   review are independent — start the suite in the background, then dispatch the
   review while it runs. Serializing them leaves the test device or CI executor
   idle for the whole review.

5. **Declared commands, never improvised scope.** A plan for an expensive-suite
   project declares its scoped commands once, so executors run known-good
   invocations instead of inventing filters mid-execution (see next section).

## Plan-authoring declaration

A Standard plan whose project crosses the cost threshold carries a **Test-scope
commands** block — in Preflight or as a conventions line near it:

```markdown
**Test-scope commands** (per references/test-scope-tiers.md):
- stage-scope: <command(s) — cheap checks in full + expensive suites for touched modules>
- plan-scope:  <command — the single full clean pass, quarantined tests included>
```

If the project is under the threshold, the block is simply omitted (the plan
template includes it only for expensive suites); optionally note "full suite
~90s — tiering not applicable" so the executor knows the omission is deliberate.
`fix-scope` needs no declaration: it is derived per-fix (the touched classes plus
the task's own `Test:`). Task-level `Test:` fields are already task-scope by
construction.

## Worked example (Android, instrumented suite)

A project whose full pass is `./gradlew clean check verifyArchitecture assembleDebug`
host-side plus `connectedCheck` on a device (~15 min total), with one known 6-minute
model-download test:

```markdown
**Test-scope commands** (per references/test-scope-tiers.md):
- stage-scope: ./gradlew check verifyArchitecture assembleDebug
               && ./gradlew :<touched-module>:connectedDebugAndroidTest   # no clean
- plan-scope:  ./gradlew clean check verifyArchitecture assembleDebug
               && ./gradlew connectedCheck -PlargeTests=true              # the one clean, quarantine included
```

- Task 2.3's Red-Green loop runs its own filtered class
  (`-Pandroid.testInstrumentationRunnerArguments.class=…`) — task-scope, ~2 min.
- A Tier-1 Critical fix to that task re-runs that class plus the classes the fix
  touched — fix-scope, ~2 min. Not the module suite, not `connectedCheck`.
- The Stage 2 gate (stages 2 of 4) runs the stage-scope pair with
  `:features` as the touched module — ~5 min, device suite in the background while
  the Tier-2 review runs.
- The final gate + close-out runs the plan-scope pass once — ~20 min, including the
  quarantined 6-minute test — and that is the only `clean` and the only
  `connectedCheck` in the whole execution.

Total: one expensive pass per plan instead of one per gate per re-run.

## Relationship to the other formats

- **Light plans** need no changes: a Light plan's single gate *is* its final gate,
  so its "full existing test suite" check is already plan-scope. When a Light
  plan's close-out re-run would immediately follow the gate's full pass with no
  commits in between, the gate's pass counts as the close-out run — one pass, not
  two.
- **Master plans**: each sub-plan is an independently executed plan and keeps its
  own single plan-scope pass at its own close-out. Tiering applies *inside* each
  sub-plan (its intermediate gates are stage-scope); the master's register gates
  are integration checks, not suite re-runs.
- **honest-gates** is unchanged and binding: a scoped gate is still a real gate —
  its commands really ran, here, and passed — plus the disclosure duty in guard
  rail 2.
