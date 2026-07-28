# Light plans

How `executing-plans` runs a `*-light-plan.md`. Format: `../../planning-projects/references/light-plan-format.md`.

A **light plan** (`*-light-plan.md`, format:
`../planning-projects/references/light-plan-format.md`) is a single stage of 2–5
Status-carrying tasks with one gate. Execute it through the normal single-plan flow
below, with these deltas — the machinery **scales to the size of the job** rather than
running at full weight:

1. **Preflight is git-bootstrap + baseline tests only.** A light plan has no Preflight
   section; the "baseline tests pass" check lives in its single gate. Still do the git
   bootstrap (Phase 2 — a repo must exist for commit-per-task) and confirm the baseline
   is green before Stage 1. Nothing else to verify.
2. **No parallel dispatch.** Every task runs **inline in the main session**, in listed
   order, through the normal Red-Green loop. A light plan has no `Parallel` field and no
   fan-out — do not invoke `dispatching-parallel-agents`. (A task may carry an optional
   `Depends on`; honor it as ordering.)
3. **One review, not per-task.** **Skip the Tier-1 per-task review.** Instead, after the
   last task goes green and **before** the gate (this is a pre-gate check, not the gate
   itself — a light plan still has exactly one gate, its Stage 1 Gate), run **one**
   `git-github:code-reviewer` (read-only) pass over the **whole plan diff** (`git diff`
   across all the light plan's commits). Handle its verdict exactly like the Tier-2 stage
   review: a **Critical** blocks close-out just as a Tier-2 Critical fails a gate (fix
   within the same discipline, re-run test + review), and Important findings are surfaced
   for the user's triage rather than auto-fixed — but they are still bound by the **exit
   criterion** (Step 3.5), so each one leaves the gate either fixed or recorded to the
   `backlog` with the user told. A light plan is a small plan, not one where findings
   evaporate. Skip only on the usual opt-out /
   trivial-diff rules — so an entirely docs-only light plan skips it too (zero reviews is
   correct there, exactly as a docs-only task auto-skips Tier-1 in a Standard plan); the
   one review is guaranteed only when the plan's diff carries reviewable code. **This
   single pre-gate review IS the light plan's Tier-2 — do not also run a separate Step 3.5
   Tier-2 pass.** It keeps one real review in the loop without paying per-task review
   overhead on a handful of tasks.

   **This rule sets the review's *shape* only.** How many passes run, and whether an
   evaluator runs beside them, comes from the declared review-scope tier — see
   § Review scope → *Composing with the plan format*. A light plan whose diff is `high`
   still gets the second independent pass; it just gets it over the whole diff.
4. **The evaluator follows the tier, not the format.** Whether the independent
   goal-evaluator runs — at the gate (Step 3.5) and at close-out (Phase Close-out step 3) —
   is decided by the review-scope table, not by this plan being Light: off at `none` and
   `light`, on at `standard` wherever a gate check carries `(judgment)`, always on at
   `high`. A Light plan's gate is usually all commands, which is why it *usually* runs no
   evaluator — but that is a consequence of what its gate contains, not an exemption the
   format grants. A `(judgment)` check is a check that needs a reader; being in a small
   plan does not make it need one less.
5. **Close-out is one stated bump.** Run the full suite one final time — unless the
   single gate's full-suite run was the last thing to execute with no commits landed
   after it, in which case that run counts as the close-out run (one full pass, not
   two) — reconcile the backlog (`Closes BL-NNN`), and append the `**Completed:**`
   line. For version bumps,
   apply a **single stated SemVer bump** to what changed and its mirror — in this repo,
   name the plugin's `.claude-plugin/plugin.json` **and** the root marketplace entry
   explicitly (that pair) rather than running the full mirror-grep ritual. State your call
   so the user can override.

**Everything else is unchanged from a Standard plan:** Status flips the moment a test is
green, a commit per green task, the Red-Green cycle budget and all Stop conditions,
run-to-completion (don't pause at the gate to ask permission), one handoff note at the
single gate, and the honest-gates integrity contract. A light plan is a small plan, not a
sloppy one.
