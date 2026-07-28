# Stage-gate failure: triage, class repair, remediation budget

Invoked from `executing-plans` Step 3.5 when a gate check fails. The exit criterion that
decides when repairing stops lives in the trunk, beside the gate itself — this file is the
procedure for getting there.

**If the gate fails:**

Treat the failure as a **defect class sampled once**, not a point defect. Detection
at a gate is goal-scoped (the evaluator re-reads the whole artifact every round)
while repair defaults to instance-scoped — so a class with N instances costs ≈N
rounds, each one looking like fresh news. Triage before repairing, and bound the
loop.

1. **Classify every finding by severity** — the same **Critical / Important /
   Suggestion** taxonomy the review tiers already use (Step 3.3 rule 6), so a gate
   finding and a review finding are graded on one scale rather than two.
2. **Diagnose evidence-first, then name the set it belongs to.** Invoke
   `no-fafo-debugging` here — this is the most fix-prone moment in the whole
   workflow (a failed gate, under a bounded round budget), which is exactly where
   "Fix And Forget" produces a plausible-looking repair for a misdiagnosed cause.
   The order matters and is not decorative: a set derived from a wrong root cause is
   a *wrong set*, so the class sweep in step 3 would then sweep confidently over the
   wrong population and report green. Evidence first, then generalize.

   Then name the set the finding quantifies over — the other files, callers,
   examples or docs that could carry the same defect. **Derive it, in this order:**

   a. **The failing task's `Scope:` field**, if it declares one — that is what the
      field is for (`../planning-projects/SKILL.md` § Scope marking). It is a
      starting point, not an authority: a `Scope:` is only as good as the sweep
      behind it, and a truncated authoring command is a documented way for one to
      arrive short.
   b. **When no `Scope:` exists, or the finding escapes it, enumerate one now** —
      run the sweep the check should have been: grep the defect's distinguishing
      string across the repo, list every sibling of the failing artifact's kind
      (`ls <plugin>/commands/*.md`), or list every caller of the changed symbol.
      **Write the command down in the gate report**, so the next round argues with
      a command rather than a recollection.
   c. **Reconcile the two.** If (b) found members (a) did not, the task's `Scope:`
      was wrong — fix the plan's `Scope:` line as part of the repair, or the same
      gap recurs on the next task that trusts it.

   A gate failure is usually an integration problem rather than one task's bug.
   Repairing the instance and leaving its siblings is what converts one class into
   N rounds.
3. **Add a test covering that interaction** to the relevant task. Where the finding
   is set-valued, that test is the **sweep over the set derived in step 2** (the
   class-predicate rule in `../planning-projects/SKILL.md`), not a check on the
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
repair → re-verify. It is a default, and a plan may override it by stating a
different number of remediation rounds on the stage; **count the rounds and report
the count** in the gate report ("gate green — remediation round 2 of 2"). An
uncounted loop is how a gate reaches its fourth round with nobody noticing the
third.

**Stop repairing when the exit criterion above is met** — no Critical remaining,
every Important fixed or recorded. Do not spend a round chasing Suggestions, and do
not spend one trying to make a judgment agent go quiet.

**On budget exhaustion, escalate with the residual list.** Report the findings
that remain, their severities, and how the rounds were spent. This is a documented
**Stop condition** (below) — not a failure to hide, and not a licence to keep
looping. The user decides between another round, returning to
`planning-projects`, and shipping with the residual recorded.
