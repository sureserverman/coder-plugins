# Stage-gate failure: triage, class repair, remediation budget

Invoked from `executing-plans` Step 3.5 when a gate check fails. The exit criterion that
decides when repairing stops lives in the trunk, beside the gate itself; so does the
class-repair rule this procedure applies — **§ A bug found during execution is a class**.
This file is the *gate's* application of that rule: the triage, the ordering, and the bound
on the loop.

**If the gate fails:**

A gate is one caller of the class rule, and the sharpest one. Detection at a gate is
goal-scoped (the evaluator re-reads the whole artifact every round) while repair defaults to
instance-scoped — so a class with N instances costs ≈N rounds, each one looking like fresh
news. Triage before repairing, and bound the loop.

1. **Classify every finding by severity** — the same **Critical / Important /
   Suggestion** taxonomy the review tiers already use (Step 3.3 rule 6), so a gate
   finding and a review finding are graded on one scale rather than two.
2. **Run the class rule: diagnose evidence-first, then name the set it belongs to.**
   Invoke `no-fafo-debugging` here — this is the most fix-prone moment in the whole
   workflow (a failed gate, under a bounded round budget), which is exactly where
   "Fix And Forget" produces a plausible-looking repair for a misdiagnosed cause.
   The order matters and is not decorative: a set derived from a wrong root cause is
   a *wrong set*, so the class sweep in step 3 would then sweep confidently over the
   wrong population and report green. Evidence first, then generalize.

   The trunk rule states how to derive and enumerate the set, and that a sweep finding
   members the `Scope:` did not means the plan's `Scope:` line is wrong and is fixed as part
   of the repair. **Two things the gate adds to it:**

   a. **The failing task's `Scope:` field is where the gate starts**, if it declares one —
      that is what the field is for
      (`../../planning-projects/references/task-fields.md` § Scope marking). It remains a
      starting point, not an authority: a `Scope:` is only as good as the sweep behind it,
      and a truncated authoring command is a documented way for one to arrive short.
   b. **Write the enumeration command into the gate report**, not merely into a commit
      body — the gate is what the next remediation round reads, so the command has to be
      where that round will look.

   A gate failure is usually an integration problem rather than one task's bug.
   Repairing the instance and leaving its siblings is what converts one class into
   N rounds.
3. **Add a test covering that interaction** to the relevant task. Where the finding
   is set-valued, that test is the **sweep over the set derived in step 2** (the
   class-predicate rule in `../../planning-projects/SKILL.md`), not a check on the
   single file that failed — an instance-shaped check cannot fail on the siblings
   that make the class. Fix **every member the sweep returns in this round**, not
   just the one the gate happened to report: a class repaired one instance per round
   is the oscillation the budget exists to bound, and bounding it is not the same as
   converging.
4. **Run that task through its Red-Green loop again.**
5. **Re-verify narrowly, plus the sweep.** Re-run the failed check(s), any check
   whose inputs the fix touched, and the step-3 class sweep — not every gate check
   from scratch.

**Remediation budget — default 2 rounds per gate.** One round is classify →
repair → re-verify — and **a re-dispatched review or evaluator is itself a round**
(trunk, § Remediation budget), never a free confirmation of a round already spent.
Without that, a gate has two counters and one limit: repairs bounded at 2, while
fix → re-review → new findings → fix runs until the reviewer goes quiet, which for a
fresh judgment agent is not a reachable state. It is a default, and a plan may override it by stating a
different number of remediation rounds on the stage; **count the rounds and report
the count** in the gate report ("gate green — remediation round 2 of 2"). An
uncounted loop is how a gate reaches its fourth round with nobody noticing the
third.

**Stop repairing when the exit criterion above is met** — no Critical remaining,
every Important fixed — the `backlog` is not a disposition for a defect (trunk, § Exit
criterion). A defect this session genuinely cannot fix — it needs a device, a credential,
an upstream release — escalates with its blocker named; that is the only exit that is not
a repair, and it is the user's call from there. Do not spend a round chasing Suggestions, and do not spend one trying to make a
judgment agent go quiet.

**On budget exhaustion, escalate with the residual list.** Report the findings
that remain, their severities, and how the rounds were spent. This is a documented
**Stop condition** (below) — not a failure to hide, and not a licence to keep
looping. The user decides between another round, returning to
`planning-projects`, and shipping with the residual recorded.
