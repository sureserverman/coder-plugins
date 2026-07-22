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
| **task-scope** | Every Red-Green cycle | The task's own `Test:` — already targeted (a class filter, a module's unit tests, a single command). Unchanged from the base model. |
| **fix-scope** | After a Tier-1/Tier-2 Critical fix or a gate-triage fix | Only the test classes/modules the fix touched, plus the originating task's own `Test:`. Never the full suite — a review fix is a targeted change and gets a targeted re-proof. |
| **stage-scope** | Intermediate stage gates | All **cheap host-side checks in full** (unit tests, lint, static/architecture checks, build). **Expensive suites restricted to the modules touched by the stage's commits.** Never `clean`. |
| **plan-scope** | Final stage gate + close-out — once | The full suite from a clean state, including every expensive suite and every quarantined slow test. The one place `clean` belongs. |

`clean` appears in **exactly one command per plan**: the plan-scope pass. An
intermediate gate that wipes incremental state re-buys the whole build for nothing —
regressions an incremental build would miss are exactly what the single clean
plan-scope pass exists to catch.

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

If the project is under the threshold, declare that instead ("full suite ~90s —
tiering not applicable") so the executor knows the omission is deliberate.
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
