# Review scope and the opt-out rules

How much verification machinery a run pays for, what shape it takes, and the two — only two —
reasons a review the tier mandates may be skipped. `executing-plans` declares the tier at
Preflight and restates it in every gate report.

### Review scope — the machinery scales to the change

Declare this at Preflight, next to the test-scope commands, and state it in every gate
report. Test scope is already tiered (`../../planning-projects/references/test-scope-tiers.md`)
so a gate does not run the full suite to prove a one-line fix. **Review scope is the same
idea applied to the verification machinery**, which until 0.33.0 ran at one weight regardless
of what it was reviewing — and which, until 0.37.0, this table only half-corrected, because
it gated the two review passes and left the probe, the evaluator and the conformance check
running unconditionally underneath.

| Tier | When (judged on the plan's **cumulative diff**) | Tier-1 (per task) | Tier-2 (the deep review) | Gate evaluator | Close-out evaluator |
|---|---|---|---|---|---|
| **none** | Docs-only, config-only, version-bump-only, comment-only across the whole plan | skip | skip | skip | skip |
| **light** | No new executable behavior, **or** a diff under roughly 200 changed lines across ≤ ~5 files — and no risk-listed area touched | skip | **one**, over the whole plan diff, before close-out | only at a gate carrying a `(judgment)` check | only if the final gate carries `(judgment)` |
| **standard** | Multi-file code with new behavior — the default when unsure, and what an undeclared run gets | skip | at the shape the format sets | only at a gate carrying a `(judgment)` check | only if the final gate carries `(judgment)` |
| **high** | **Risk-listed:** security-sensitive, auth, data-destructive, public API, schema/migration | per task | that, **plus** a second independent pass | **every gate, always** | **always** |

**Read the table top-down: the first row whose criteria the diff satisfies wins.** `none` and
`light` deliberately overlap (a docs-only plan also has "no new executable behavior"), and
without a precedence rule the "default when unsure" line would push the cheapest plan in the
ladder to the middle of it. Top-down is also why `high`'s risk list is checked first in
practice — see the risk floor below, which overrides the row order in the one direction that
matters.

Pick the tier from the **plan's cumulative diff**, not per task, and pick it once. A plan
that edits three markdown files is `light` even if it has four stages; a plan touching an
auth path is `high` even if it is small.

**What the tier gates.** Everything in the row: the two review tiers, the gate evaluator, the
close-out evaluator, and the second independent pass. Two more agent-dispatching mandates are
gated by it, and are named here because leaving them off this list is what made the 0.33.0
version of this table a half-measure:

- **The Preflight dispatch probe** runs only when the roster is non-empty **and** the tier is
  `standard` or `high`. Below that, a run that dispatches nothing gains nothing from proving
  it could. Record `probe: skipped — tier <name>` alongside the roster line.
- **The decisions-conformance check** runs at the **final** stage gate and at close-out, at
  every tier where the diff is code — not at every intermediate gate. A contradiction is
  still a **gate failure** wherever it is found (DEC-003); what the tier changes is how often
  the sweep is repeated over a diff that is still growing, not whether it binds.

What the tier does **not** gate — because each costs a line of text and its absence is
invisible — is the dispatch roster, the executor trailer, the dispatched-vs-inline
reconciliation, honest-gates disclosure, and the plan's own tests and gate checks. Those run
at every tier including `none`. The distinction is cost: **a mandate that costs an agent
dispatch is tiered; a mandate that costs a line of text is not.**

**The tier is declared, not assumed.** Write it in the Preflight report
(`review-scope: light — prose edits to 3 skill files`) and repeat it in each gate report.
An undeclared run is `standard`. This is the honest-gates disclosure rule applied to review
effort: downgrading silently and downgrading openly produce the same diff, so the
declaration is what makes the choice reviewable.

**Why this exists.** A review pass is not free and does not have a fixed value: dispatching
four agents over a 160-line prose change costs more than the change and returns findings
about the reviewing apparatus rather than the product — measured at ~800k tokens for a
160-line prose plan. Running the same four over an auth rewrite is cheap insurance. The
failure this table prevents is the one that is invisible without it — machinery whose cost
nobody compares to what it is protecting, because no rule ever asked.

**Why the criteria are diff-shaped rather than prose-shaped.** The first version of this
table defined `light` as *"prose or config edits, or one file, or no new executable
behavior"*. Almost no real plan qualified: a plan is multi-file by construction, so every
plan fell through to `standard` and the damping term never engaged. A criterion that cannot
be met is not a conservative default, it is a dead branch — so the bar is now a size the
diff can actually be measured against, and the escalation is carried by the risk list rather
than by making the lower tiers unreachable.

### Escalation: risk raises a tier, size never does

**A tier is a floor, not a ceiling.** Escalate mid-plan when the diff turns out riskier than
it looked — say so in the gate report; do not quietly de-escalate, which is what the
declaration exists to catch.

Two rules govern which direction an ambiguity resolves:

- **Touching a risk-listed area sets `high`**, whatever the size. Small and dangerous is
  still dangerous; the `high` row's list is the authority on what counts.
- **Size alone never escalates.** A large diff of prose, or of mechanical renames, is a big
  `light` change, not a `standard` one. Volume is not risk, and treating it as risk is how
  the old "when in doubt, go heavier" instinct reintroduced the cost this table removes.

### Composing with the plan format

The format ladder (Direct / Light / Standard / Master) and the tier above answer **different
questions**, and a plan carries both at once. Resolve them this way, always:

> **The format decides the review's SHAPE. The tier decides its DEPTH.**

| From the **format** — shape | |
|---|---|
| Direct, Light | Tier-2 runs over the **whole plan diff**, once, before close-out |
| Standard, Master | Tier-2 runs **per stage gate** |

| From the **tier** — depth | Tier-2 passes | Tier-1 (per task) | Evaluator |
|---|---|---|---|
| `none` | none | no | no |
| `light` | **one**, whatever shape the format sets | no | only at a gate carrying `(judgment)` |
| `standard` | one **per** unit the format's shape names | no | only at a gate carrying `(judgment)` |
| `high` | that, plus a second independent pass | **yes** | **yes, always** — every gate and close-out |

**How to read the two together without them fighting.** The format's row names the *unit* a
Tier-2 pass covers (whole plan diff, or one stage). The tier's row names *how many passes and
how deep*. So `light` means **one pass total** over whatever unit the format named — for a
Standard-format plan that is one pass over the whole plan diff before close-out, not one per
stage. The earlier version of this table stated a shape in the `light` row ("over the whole
plan diff") and a shape in the format row ("per stage gate"), which left a Standard plan at
`light` reading as either 1 review or N — and resolving it the format's way would have made
`light` and `standard` identical for every multi-stage plan, retiring the damping term for
the exact case it was built for.

**Tier-1 is the tier's alone.** The format never sets it: `high` runs it per task in any
format, including Light, and no other tier runs it at all without a task's `Review:
required`. The Direct/Light row used to say "never per task", which contradicted `high`'s
"plus per-task Tier-1" for precisely the Light-plan-touching-auth case the risk floor exists
to settle.

**Resolve a disagreement by the risk floor, not by "take the lighter option" and not by
"take the heavier".** Both of those are instincts standing in for a rule. The rule is: apply
the format's shape and the tier's depth, and let a risk-listed area override the tier upward.
A Light plan touching an auth path is a *small plan doing a dangerous thing* — it gets
whole-diff shape (from Light) and `high`'s depth (from the risk floor). A Light plan editing
four prose files is a small plan doing a small thing, and gets exactly one review; the
earlier "never take the lighter option" rule made that case pay `standard`'s price for no
protection, which is the asymmetry the risk floor replaces.

Master plans declare a tier **per sub-plan**, from that sub-plan's own diff — sub-plans are
independently executable, so a `high` sub-plan must not be diluted by a cheap sibling, and a
cheap sibling must not inherit the `high` one's cost.

**Why this is written down at all.** Before it existed, the two axes were each internally
consistent and silent about the other, so an executor meeting a Light plan that declared
`standard` could run one review or four and be equally compliant either way. That is not a
tie the executor should be breaking on instinct — it is a rule that was missing. Observed
live: the run that introduced this section resolved the same collision twice by instinct,
took the lighter option both times, and skipped an evaluator this table requires.

---

**Review opt-out.** A review the declared tier mandates is default-on. Disable it per task with a `Review: skip` field on the task line (use for non-code or throwaway tasks), or globally for a run when the user opts out (state it once at Preflight, mirroring the goal-evaluator opt-out). A task may also opt *in* below `high` with `Review: required`, which is how a plan buys per-task review for the one task that warrants it without raising the whole plan's tier. Trivial/non-code diffs — docs-only, config-only, pure version bumps, comment-only — are auto-skipped without needing an annotation. **Two reasons excuse a mandated review, and the list is closed at two: an evidenced user opt-out, and a trivial/non-code diff.** A `git-github:code-reviewer` that cannot be dispatched is not a third one: it is the Stop condition for a mandated review that cannot be run (§ Stop conditions), on the same ground as an unrunnable test. An unrun review is not a passed review, and it leaves an artifact indistinguishable from a reviewed one — which is why the resolution is the user's to choose and not the executor's to assume.

**A tier that does not mandate a review is not an opt-out at all.** It is the machinery
scaling as designed, and it is recorded by the declared tier rather than by a quote — the
tier *is* the evidence, checkable against the diff it was picked from. Keep the two apart in
the gate report: "Tier-1 not run — tier is `light`" is a *scope* statement; "review skipped —
user opt-out, Preflight: '…'" is an *opt-out* statement. Conflating them is how a skipped
mandate hides inside a legitimate tier.

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
