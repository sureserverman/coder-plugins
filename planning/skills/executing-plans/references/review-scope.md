# Review scope and the opt-out rules

How much review machinery a run pays for, what shape it takes, and the two — only two —
reasons a review may be skipped. `executing-plans` declares the tier at Preflight and
restates it in every gate report.

### Review scope — the machinery scales to the change

Declare this at Preflight, next to the test-scope commands, and state it in every gate
report. Test scope is already tiered (`../planning-projects/references/test-scope-tiers.md`)
so a gate does not run the full suite to prove a one-line fix. **Review scope is the same
idea applied to the review machinery**, which until now ran at one weight regardless of what
it was reviewing.

| Tier | When | Tier-1 (per task) | Tier-2 (per gate) | Evaluator |
|---|---|---|---|---|
| **none** | Docs-only, config-only, version-bump-only, comment-only across the whole plan | skip | skip | skip |
| **light** | Prose/config edits, or one file, or no new executable behavior | skip | **one** review over the whole plan diff, before close-out | only if a gate check needs judgment |
| **standard** | Multi-file code with new behavior — the default when unsure | per task | per stage gate | at any gate with a non-command check |
| **high** | Security-sensitive, data-destructive, public API, schema/migration, auth | per task | per stage gate + a second independent pass | every gate, and close-out |

Pick the tier from the **plan's cumulative diff**, not per task, and pick it once. A plan
that edits three markdown files is `light` even if it has four stages; a plan touching an
auth path is `high` even if it is small.

**The tier is declared, not assumed.** Write it in the Preflight report
(`review-scope: light — prose edits to 3 skill files`) and repeat it in each gate report.
An undeclared run is `standard`. This is the honest-gates disclosure rule applied to review
effort: downgrading silently and downgrading openly produce the same diff, so the
declaration is what makes the choice reviewable.

**Why this exists.** A review pass is not free and does not have a fixed value: dispatching
four agents over a 160-line prose change costs more than the change and returns findings
about the reviewing apparatus rather than the product. Running the same four over an auth
rewrite is cheap insurance. The failure this table prevents is the one that is invisible
without it — machinery whose cost nobody compares to what it is protecting, because no rule
ever asked.

**A tier is a floor, not a ceiling.** Escalate mid-plan when the diff turns out riskier than
it looked (say so in the gate report); do not quietly de-escalate — that is what the
declaration exists to catch.

### Composing with the plan format

The format ladder (Direct / Light / Standard / Master) and the tier above answer **different
questions**, and a plan carries both at once. Resolve them this way, always:

> **The format decides the review's SHAPE. The tier decides its DEPTH.**

| From the **format** — shape | |
|---|---|
| Direct, Light | reviews run over the **whole plan diff**, once, before close-out — never per task |
| Standard, Master | Tier-1 **per task**, Tier-2 **per stage gate** |

| From the **tier** — depth | Review passes | Evaluator |
|---|---|---|
| `none` | none | no |
| `light` | one | only if a gate check carries `(judgment)` |
| `standard` | one, at the shape the format sets | **yes, at any gate with a `(judgment)` check** |
| `high` | that, plus a second independent pass | **yes, always** — every gate and close-out |

**Do not resolve a disagreement by "taking the lighter option".** That heuristic is
seductive and wrong at the top of the table: a Light plan touching an auth path is a *small
plan doing a dangerous thing*, and the format's smallness says nothing about the danger.
Under this rule it gets whole-diff shape (from Light) *and* the second independent pass and
mandatory evaluator (from `high`) — which is the correct answer and the one "lighter wins"
would have thrown away.

Master plans declare a tier **per sub-plan**, from that sub-plan's own diff — sub-plans are
independently executable, so a `high` sub-plan must not be diluted by a cheap sibling.

**Why this is written down at all.** Before it existed, the two axes were each internally
consistent and silent about the other, so an executor meeting a Light plan that declared
`standard` could run one review or four and be equally compliant either way. That is not a
tie the executor should be breaking on instinct — it is a rule that was missing. Observed
live: the run that introduced this section resolved the same collision twice by instinct,
took the lighter option both times, and skipped an evaluator this table requires.

---

**Review opt-out.** Both review tiers are default-on. Disable them per task with a `Review: skip` field on the task line (use for non-code or throwaway tasks), or globally for a run when the user opts out (state it once at Preflight, mirroring the goal-evaluator opt-out). Trivial/non-code diffs — docs-only, config-only, pure version bumps, comment-only — are auto-skipped at Tier 1 without needing an annotation. **Two reasons excuse a review, and the list is closed at two: an evidenced user opt-out, and a trivial/non-code diff.** A `git-github:code-reviewer` that cannot be dispatched is not a third one: it is the Stop condition for a mandated review that cannot be run (§ Stop conditions), on the same ground as an unrunnable test. An unrun review is not a passed review, and it leaves an artifact indistinguishable from a reviewed one — which is why the resolution is the user's to choose and not the executor's to assume.

**An opt-out is evidenced, not asserted.** The two reasons differ in who authors them, so
they carry their evidence differently. A **trivial/non-code diff** carries its own evidence:
it is a property of the diff, and any later reader can check it against the diff itself. A
**user opt-out** is a claim about something that happened outside the artifact, and the only
person who can author it is the user — so recording it means **quoting the user's own
words**, with where they were said. For example:

```
Review skipped — user opt-out, Preflight: "don't bother with the reviewer on this one"
```

**A `Review: skip` annotation counts as an opt-out when Preflight's snapshot lists it**
(§ Dispatch roster and capability probe, step 3), and the snapshot is what makes it
evidence. The executor writes to the plan file throughout the run, so an annotation read
at skip time proves nothing about who put it there; one recorded against the run's base
commit was demonstrably there before the run began. An annotation missing from that
snapshot is an executor-authored note, worth exactly what the executor's own judgment is
worth here — nothing. Cite the snapshot line rather than the task line.

**Executor judgment is not an opt-out.** *"I judged the review unnecessary"*, *"the diff
looked small to me"*, *"there was nothing a reviewer would have caught"* are the executor
deciding on the user's behalf and then recording the decision as though the user had made
it. That is the same substitution the executor trailer exists to expose (Step 3.3 rule 7),
one axis over. A skip reported without a quote or a cited annotation is an **unevidenced
skip**: it reads downstream as a review that did not happen, because that is what it is.
The point is not to make opting out hard — it is to keep the legitimate path open and
auditable, so that "the user asked me to skip this" and "I decided to skip this" stop
producing the same record.
