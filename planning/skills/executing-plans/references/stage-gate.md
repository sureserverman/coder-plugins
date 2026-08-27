# Stage gate — reports, hooks, evaluator, Tier 2, and what "passed" means

The trunk (`../SKILL.md` § Step 3.5 — Stage gate) carries the gate's order, its exit
criterion and its remediation budget. This file carries everything that fires on a branch:
the report's exact shapes, the two verify hooks, the evaluator's briefing, the Tier-2 pass,
the decisions sweep, and the reasoning behind each disposition rule.

## The gate report's dispatch line

**The gate report states the stage's dispatched-vs-inline counts, and a reason for every
inlined `Parallel: YES` task.** Read them off the executor trailers rather than from memory —
`git log --format='%h %(trailers:key=Executor,valueonly)' <base>..HEAD`, where `<base>` is the
previous stage's `"Stage N green"` commit (for Stage 1, the commit the branch started from) —
and reconcile against the roster Preflight declared. One line: `dispatch: 3 of 4 YES tasks
dispatched; Task N.M inlined — <reason>`. A stage that dispatched everything it marked says
`dispatch: 4 of 4` rather than saying nothing, so silence never has to be interpreted. A
**Light plan** has no `Parallel` field and never fans out, so its single gate carries no
dispatch line — the requirement is scoped to plans that can have a roster, not waived where
one would be vacuous.

**An empty trailer value is `unknown`, never `inline`.** Git drops a whole trailer block at a
line it cannot parse, so a wrapped or malformed trailer returns blank with exit 0 —
indistinguishable, to the query, from a task nobody dispatched. Counting blanks as inline
invents a deviation; counting them as dispatched hides one. So resolve each blank against the
commit body, count it as `unknown` if it says nothing either, and report the unknowns:
`dispatch: 1 of 1 dispatched; 2 commits predate the trailer convention (resolved from their
bodies)`.

## The gate report's review line

**The gate report names every review that ran, the agent that ran it, and the diff it saw** —
and, for one that did not, which of the **three** reasons applies: the declared tier never
mandated it (state the tier — this is a *scope* statement and needs no excuse), or, where the
tier did mandate it, an evidenced opt-out (`../references/integration.md` § Review opt-out) or
a trivial/non-code diff. Do not report a tier-scoped absence as an opt-out; that is how a
skipped mandate hides inside a legitimate tier. One line per tier, resolving `<base>` the same
way the dispatch line does — the previous stage's `"Stage N green"` commit — and naming the
agent by a type dispatch can actually take. `goal-evaluator` is a **role**, not a registered
agent: no `goal-evaluator` agent file ships in this marketplace, so a report naming it records
a dispatch nobody can reproduce. Write the type that ran, then the role:

```
review: Tier-2 git-github:code-reviewer over <base>..HEAD — APPROVE, 0 Critical
evaluator: general-purpose in the goal-evaluator role, briefed on the stage goal + gate criteria — PASS, 2 Material
```

Naming the **agent** distinguishes a dispatched review from the executor reading its own diff,
which both tiers forbid; naming the **diff** makes its coverage checkable, since a reviewer
briefed on the wrong range returns a clean verdict over code nobody looked at and "reviewed"
reads identically either way. An inlined `Parallel: YES` task is a **deviation being
disclosed**, not one being ratified — a gate report that keeps producing them is evidence the
plan's `Parallel` fields belong back in `planning-projects`.

## ACTION NEEDED — the one place a report asks the user for something

A gate report either needs something from the user or it does not. When it does, the ask goes
in **one** block, **last**, under this exact heading, with the options numbered so the reply
can be a number rather than a reconstruction of the choice:

```
ACTION NEEDED — <one line naming the decision>
  1. <option>
  2. <option>
```

**A report carrying an `ACTION NEEDED:` block does not also say it is proceeding.** "Two
things for you" in one paragraph and "proceeding to Stage 3" in the next is the shape that
produced three separate *"what do you want from me?"* replies across three sessions: the
reader cannot tell whether the run stopped, and the cost of guessing wrong is asymmetric —
answering a question the run already moved past is wasted, and not answering one it is
blocked on stalls the plan silently. Either the decision blocks the next stage, in which case
say so and stop, or it does not, in which case it is not `ACTION NEEDED:` at all and routes
where its kind already routes — a decision the user must make to the `backlog`, a Suggestion
to the `residuals:` line. This adds no third destination; `residuals:` keeps the definition
§ The handoff note's contents gives it.

**One block per report, or none.** Scattering asks through the narrative is the same defect
with better manners: three asks in three paragraphs is three chances to miss one.

**Tier: untiered.** This mandate costs a line of text, not an agent dispatch, so per
DEC-010 it runs at every review scope including `none` — named here because DEC-017
requires a new mandate to state the rule that gates it rather than leave it inferred.

## Platform stage-verify hook

After the stage's own gate checks pass, if the project's platform ships a stage-verify skill,
invoke it as the final gate step — it proves the stage on the real artifact, not just the test
suite. A failure there is a gate failure (handle it like any other). Brief the stage-verify
skill with the gate's tier: at an intermediate gate it verifies at stage-scope (touched-module
instrumented tests); at the final gate it runs the full device suite (plan-scope) — and that
run IS the plan-scope pass's device portion, not an addition to it (don't run the declared
`plan-scope:` device suite separately and then the hook's again). Match by project type:

| Project type (detector) | Stage-verify skill |
|-------------------------|--------------------|
| Android — `settings.gradle{,.kts}` / `app/build.gradle{,.kts}` present | `android-stage-verify` (android-dev plugin) — builds the debug APK, and if an adb device is attached, installs + smoke-launches + runs instrumented tests |

If no matching skill is installed, note it and rely on the regular gate checks — the absence
of a platform verifier is not itself a gate failure.

## Design-fidelity verify hook (redesign stages)

A stage whose tasks reproduce a Claude Design handoff pack (a *design-handoff* / *redesign*
task — driven by the `applying-design-handoff` skill) carries its own gate step: run that
skill's **fidelity verify loop** (capture → grade against its fidelity rubric with a separate
evaluator → iterate, max 3) as the final gate check, exactly as the platform stage-verify hook
proves a platform stage. A sub-threshold verdict that doesn't recover within the loop is a
gate failure. This is the design analogue of the stage-verify hook: a green build is not a
reproduced design.

Its separate evaluator is a dispatch, so **whether it runs comes from
`../references/review-scope.md`** like any other: never at `none`, at `light`/`standard` when
the stage's fidelity is a `(judgment)` gate check, always at `high`.

**If the hook fires and the tier does not fund its evaluator, the hook does not run — and the
gate report says so.** A fidelity loop with no independent grader is the executor grading its
own reproduction, which is the one thing this hook exists to prevent, so running it ungraded
is worse than not running it. Two ways out, both the plan's to choose ahead of time: mark the
stage's fidelity check `(judgment)`, which funds the evaluator at `light` and `standard` and
is the right answer whenever fidelity actually matters; or accept that the stage is verified
by its ordinary gate checks alone and record `design-fidelity: not run — tier <name>, fidelity
not marked (judgment)`. What you may not do is dispatch the loop and let the executor score it.

## Independent evaluator for non-command checks

**Whether it runs comes from `../references/review-scope.md` — do not re-derive it**: never at
`none`, at `light` and `standard` when the gate carries a `(judgment)` check, always at
`high`. Run command checks yourself. When the tier mandates an evaluator, dispatch a fresh one
for the judgment checks, briefed ONLY with the stage goal and the gate's pass criteria — never
the implementation transcript or your own summary. The session that wrote the code grades its
own work too generously.

**Once the tier mandates it, the list of excuses is closed at two** — an **evidenced** user
opt-out, or, **below `high` only**, a gate whose every check is a command. There is no third
reason: an evaluator that cannot be dispatched is a Stop condition, not a skip. A tier that
does not mandate one is not an excuse at all but the machinery scaling as designed, and it is
reported as scope (`evaluator: not run — tier is light, no (judgment) check at this gate`)
rather than as an opt-out.

**Why the command-only excuse stops at `high`.** Below `high` it is not really an excuse: the
tier already says "only at a gate carrying a `(judgment)` check", and an all-command gate has
none, so the two conditions name the same gates and the excuse is a restatement. At `high`
the tier says **always**, and there the excuse would contradict it — collapsing `high` into
`standard` for the one column where they were meant to differ. The evaluator grades whether
the *goal* was met, which a green command check does not establish; at `high` that question
is exactly the one worth paying an agent for.

**Every finding it returns is a class sample**, so the disposition of one is settled by
`../SKILL.md` § A bug found during execution is a class — sweep it, fix every instance — an
evaluator reading the artifact black-box routinely names one instance of something that is
true of several, and it has no way to know that.

**Brief it to grade by severity, not just pass/fail** — a bare pass/fail gives the loop
nothing to terminate on, because a fresh judgment agent reading a real artifact essentially
always finds *something*, so "no adverse findings" is not a reachable state. Require, for
each finding, exactly one of:

| Severity | Meaning | Consequence |
|----------|---------|-------------|
| **Blocking** | the goal in scope is not met — the stage's at a gate, the plan's at close-out | must be fixed; the gate does not pass |
| **Material** | real defect, goal still met | **fixed**, with its class swept; the `backlog` is not where a defect goes |
| **Minor** | nit, polish, taste | recorded in the gate report and carried into the stage handoff note; never blocks |

Blocking maps to Critical, Material to Important, Minor to Suggestion, so both scales
resolve to the one exit criterion in this file. An evaluator FAIL carrying no Blocking finding
is a **pass with recorded residuals**, not a failure — tell the evaluator so explicitly, or
it will withhold PASS to seem rigorous and hand the loop an unsatisfiable condition.

## Deep code review (Tier 2)

Whether it runs, and at what shape, comes from `../references/review-scope.md`. The evaluator
verifies *goals* black-box; this is the complementary *white-box* pass: dispatch
`git-github:code-reviewer` (read-only) over the **full stage diff** plus the stage's collected
`**Review notes (Task N.M):**` lines. It is a gate criterion, not advisory — a **Critical**
here is a **gate failure**. Important findings are **not free either**: each leaves the gate
**fixed**, per the exit criterion, which governs every gate pass and not only one reached
through the failure branch. Suggestions are recorded. This is the only point where findings
are judged against the *coherent stage*, so cross-task issues Tier-1 could not see
(duplication across tasks, an abstraction that should have been shared) surface here. **Each
finding is repaired as a class** per `../SKILL.md` § A bug found during execution is a class —
sweep it, fix every instance — a reviewer cites the line it read, which is one member of
whatever set that line belongs to. **Brief it to audit the stage's behavioral claims as a
set**, per `honest-gates` and its rule that a behavioral claim is a gate too — the stage view is where a
claim that was true when written and false after a later task shows up.

## Decisions-conformance check (gate criterion, not advisory)

**Run it at the final stage gate and at close-out, over the plan's cumulative diff — not at
every intermediate gate.** A contradiction is a **gate failure wherever it is found**
(DEC-003), and finding one at an intermediate gate still fails that gate; what moved is how
often the sweep is *repeated* over a diff that is still growing. Re-running it at every gate
re-reads mostly the same diff and re-reaches mostly the same verdict, and the one reading that
can be complete is the one over the finished diff. An intermediate stage that knowingly lands
a contradiction does not wait for the final gate to say so — raise it when you see it.

A change that contradicts a decision in force, without a `Supersedes` citation on its
task, is a **gate failure**. Two legal resolutions, and only two:

- **Re-scope the change** so it stops contradicting the decision, or
- **Record a deliberate supersede** (`decisions supersede`) and add the `Supersedes
  DEC-NNN — <why>` citation to the task, making the override auditable.

"The decision seems outdated" is not a third option — that judgment is exactly what
`supersede` exists to record, and skipping it is how a register decays into fiction.

**Disclose the check's limits (honest-gates).** This is a judgment call over a diff, not a
test command: it can miss a subtle contradiction, and green is not proof of conformance. The
gate report states **which IDs were checked against which parts of the diff** rather than
asserting blanket conformance — a check that overstates its coverage is worse than one that
admits its scope, because the next reader trusts it. Skip only when the diff is genuinely
non-code and no decision in force bears on documentation.

## Exit criterion — the dispositions behind it

The trunk states the criterion itself. What it resolves to, finding by finding:

**"Recorded" names a destination.** A Suggestion is not a backlog candidate — `backlog add`
refuses a defect found during execution, and a nit is still a defect — so the gate report and
the handoff note are where it lives. Without a named destination it survives only in a
transcript this skill then tells you to discard at the next stage boundary, which is how a
finding disappears with nobody told. A Suggestion worth fixing is simply fixed; a Suggestion
worth neither fixing nor writing down was not a finding.

The criterion is deliberately *not* "the detector returned silent" — a fresh judgment agent
never reports zero findings, so a gate with that exit condition is not a gate but a loop. What
ends the loop is that the findings were *dealt with*, and for a defect that means fixed.

**A defect is fixed. The backlog is for what is not a defect.**

| Kind of finding | Disposition |
|---|---|
| **A defect — anywhere in the project, whether or not this plan touched the file** | **Fix it**, and sweep its class. The diagnosis is already loaded; this is the cheapest it will ever be, and it will not get cheaper by being written down. |
| **A significant improvement** — a refactor, a new capability, performance work with no bug behind it | **Record it.** Nothing is broken; this is work someone should choose to schedule. |
| **A decision** — a change needing sign-off, a trade-off with no obviously right answer, an editorial call | **Record it.** It is the user's call, not the executor's. |
| **A defect you genuinely cannot fix here** — the fix needs a device, a credential, an upstream release, or an environment this session lacks | **Escalate**, naming the blocker. Recording it is then the user's decision, not your default. |

**Why the "outside the blast radius" row is gone.** It used to say *record it, and say why it
was out of reach* — and it was the row that did the damage, because every deferral could be
narrated as scope discipline. A sibling instance in a file this plan never touched is the same
defect, and `../SKILL.md` § A bug found during execution is a class — sweep it, fix every
instance already sends you there. Out of scope describes a plan's *subject matter*; it has
never described a defect's *reach*.

The asymmetry this closes: recording is frictionless and always available, while fixing risks
the gate you are trying to pass. So an executor under gate pressure drifted toward the backlog
for *everything*, and each deferral read as discipline rather than as the avoidance it was. A
backlog that grows by half a dozen entries per plan is the symptom. **Measured 2026-08-09 in
this repo: 28 open entries, among them "residual guard gaps found by review, judged not worth
closing yet" and "residual hardening … judged not worth closing now"** — findings, deferred,
by the executor that found them. One of them (BL-041) left the repo's own test suite standing
red for eight days, teaching every later reader to skim past the runner's verdict.

**The escalation valve is narrow on purpose.** *"I could not fix it"* means the fix needs
something this session does not have, and you say which. It does not mean the fix looked
large, or risky, or like it belonged to someone else — those are the readings that reopen the
door this rule closes. If you find yourself reaching for the valve twice in one gate, the
honest report is that the gate is blocked, not that the backlog grew.

**And the valve is evidenced, not asserted — the same bar the review opt-out sets.**
Escalating names the *missing thing* (`escalated: cannot reproduce without a physical
device`), which is checkable against the session. If the user then decides to file it, that
decision is recorded by **quoting their words**, exactly as a review opt-out is:

```
BL-0NN opened — escalated at Stage 2 gate: "no device here"; user: "yeah, file it for now"
```

Without that bar the valve is strictly weaker than the opt-out mechanism it sits beside, and
in the same way: *"escalated, user chose to file"* written by the executor is the executor
deciding on the user's behalf and recording it as though the user had. That is the exact
failure `../references/integration.md` § Review opt-out names, so it gets the exact same
answer — **an unevidenced escalation is not an escalation**, and the finding is still owed a
fix.

**A plan's scope guardrails bound that plan's subject matter. They are not a licence to defer
unrelated defects.** A guardrail like *"change only the values, never which fields are
written"* governs exactly that axis. An overflow, a crash, a parser that rejects valid input,
a false claim in a doc comment — none of those are the axis the guardrail names, so it does
not authorise deferring them. Read a guardrail for what it actually constrains, and be
suspicious when your reading of one turns out to be the reading that avoids work: **a defect
found in a file you are already editing is in scope by default.** A plan that genuinely means
"report defects, do not fix them" has to say that about *defects*, not about coverage.

One question settles most cases: *would fixing this change what the gate measures?* If not,
fixing it is not scope creep, and the guardrail is not about it.

## If the gate fails

A gate is one caller of `../SKILL.md` § A bug found during execution is a class — sweep it,
fix every instance, and the sharpest one — detection at a gate is goal-scoped while repair
defaults to instance-scoped, so a class with N instances costs about N rounds, each looking
like fresh news.

1. **Classify every finding** as **Critical**, **Important**, or **Suggestion** — the same
   scale the review tiers use, so a gate finding and a review finding are graded once.
2. **Run the shared rule: diagnose evidence-first, then name the set.** Invoke
   `no-fafo-debugging` before generalizing, enumerate the set with a command, and **write
   that command down in the gate report**. A failed gate under a bounded round budget is the
   most fix-prone moment in the workflow, which is why the rule's evidence-first ordering is
   load-bearing here rather than advisory: a set derived from a wrong root cause is a wrong
   set, swept confidently, reporting green.
3. **Add a test covering the set**, not the one file that failed, and fix **every member the
   sweep returns in this round**.
4. **Re-run the task's Red-Green loop**, then re-verify narrowly plus the sweep.

**A re-dispatched review or evaluator is a round.** Fixing a finding and asking the same
reviewer again is the loop the budget exists to bound, so it is counted like any other round
rather than treated as verification of a round already spent. Without this the gate has two
counters and only one limit: repairs are bounded at 2, while fix → re-review → new findings →
fix can run indefinitely because each pass is "just confirming the fix". The failure mode is
not hypothetical — a fresh judgment agent reading a real artifact essentially always returns
*something*, so a loop that re-dispatches until the reviewer goes quiet has no reachable exit.
The exit is the exit criterion (no Critical remains, every Important fixed), evaluated after
each round; the budget is what stops the loop when that criterion is not converging.

The full procedure — how to derive the set, when the task's `Scope:` field is the authority
and when it is wrong, and what each severity obliges: `../references/gate-failure-procedure.md`.

## The handoff note's contents

The trunk requires one at every passed gate. What it must carry:

```
**Stage N handoff:** <deviations from plan, surprises found, decisions made,
anything a fresh context needs that the Status flips don't capture>
`dispatch: <the gate report's dispatched-vs-inline line, verbatim>`
`review: <the gate report's per-tier reviewer/diff line, verbatim>`
`residuals: <every Suggestion recorded at this gate, and anything escalated rather than
fixed — one line each; "none" when there were none>`
**Decisions in force:** <the DEC/GDEC IDs still binding, plus any Supersedes
citation raised in this stage and not yet recorded>
```

The decisions line is not redundant with the plan's `## Decisions in force`: a constraint
that surfaced mid-stage exists nowhere else, and one absent from the handoff is one the
next session will not know about. **The dispatch and review lines are carried for the same
reason**, and they earn the space: the reset discards the context that holds them. The
dispatch counts can be rebuilt from the trailers, but **the review ledger cannot** — which
agent saw which diff exists only in the gate report, so a reset without it turns "the stage
was reviewed" into a claim with no artifact behind it. Copy the lines the gate already
produced; do not re-derive them. Committed with the `"Stage N green"` commit, and kept to a
few lines — a briefing, not a log.

**On large plans, prefer the reset.** A stage that closed with heavy diagnostic noise — long
Red-Green loops, big tool outputs — is one to suggest restarting in a fresh session pointed at
the plan path. The handoff note is what makes that safe; if you could not continue from it
without the old transcript, the note was too thin, and that is the bug to fix.

## The dispatched-vs-inline review ledger

A review the executor ran itself is byte-identical, in every artifact, to one a fresh agent
ran — which is why all five audited dogfooding sessions recorded `Executor: inline` for every
mandated review, dispatched nothing, and produced no artifact that said so. The ledger exists
because nothing else can tell the two apart.

**A mandated review the executor ran itself is a substitution, not a review.** It is recorded
on the gate report's review line, naming the dispatch failure that forced it:

```
review: Tier-2 SUBSTITUTED — ran inline, user authorised at Preflight:
        "don't bother dispatching the reviewer on this one" — over <base>..HEAD
```

**With no recorded reason the gate fails.** Not "is discouraged" — fails. A substitution is a
disclosed deviation; an undisclosed one is a review that did not happen wearing the report of
one, and the exit criterion has no way to see it.

**The bound, which carries equal weight (DEC-014), has two halves.** The ceiling: this
governs only the reviews the declared tier mandates, adds no dispatch beyond the tier, and is
not a licence to run reviews the tier did not fund. The floor, which is the half the incident
actually turned on: **within the tier, the mandate IS the authorization** — approving a plan
whose execution model mandates a review is the request the standing "don't dispatch unless
asked" caution is waiting for, so at this point that caution does not apply and there is no
confirmation turn to spend — a rule stated without its bound gets over-corrected into its
own inverse, and the recorded response to the original incident was exactly that: *"standing
rule, no exceptions: I won't dispatch unless you explicitly ask"*, which strips the same
reviews for the opposite reason.

**A substitution is not an excuse the executor may grant itself, and a dispatch failure is
not one either.** `integration.md` § Review opt-out closes the excuses for a mandated review
at two — an evidenced user opt-out, and a trivial/non-code diff — and says in as many words
that a reviewer which cannot be dispatched **is not a third**: that is the Stop condition for
a mandated review that cannot be run, "the resolution is the user's to choose, not the
executor's to assume."

So the order is: dispatch fails → **stop** → the user chooses (enable dispatch, re-mark the
tasks through `planning-projects`, or authorise the inline run in their own words) → and only
then is there a substitution to record, quoting them. An executor that goes straight from a
failed probe to an inline review and a ledger line has recorded the deviation and skipped the
decision, which is the half that was never the executor's. *"I judged it unnecessary"* and
*"the diff looked small"* are the same move with less paperwork.
