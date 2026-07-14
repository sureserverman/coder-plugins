# Light Plan Format Reference

Canonical format for a **Light plan**: the smallest plan the pipeline produces, for a
job that is real work but too small to earn the full staged apparatus. This file is the
single source of truth for that format — `planning-projects` writes it, `executing-plans`
executes it, and the portfolio plan parser (`../../portfolio/references/plan-parser.md`)
reads it deterministically.

A Light plan is one stage of a handful of tested tasks. It keeps the invariants that
protect against drift and drops the artifacts that only pay off across long horizons. It
sits one rung below the standard staged plan on the format ladder:

| Format | Trigger | Artifact |
|--------|---------|----------|
| **Direct** | ≤ ~2 tasks, one session, no staging value | No plan file — execute directly with a test + commit |
| **Light** | Single stage, ≤ ~5 tasks, one session, one stack | This format (`*-light-plan.md`) |
| **Standard** | Everything between | The full staged plan (SKILL.md § Plan Document Format) |
| **Master** | > ~6 stages / ~25 tasks, or multiple workstreams | Master + sub-plans (`master-plan-format.md`) |

The triage that picks a format lives in `planning-projects` SKILL.md § "Phase -0.5 —
Format triage". This file only defines the Light artifact.

## When to write a Light plan

Write a Light plan (rather than a Standard one) when ALL of these hold:

- The whole job fits in **one stage of 2–5 tasks**. Fewer than 2 tested tasks is a Direct
  job (no plan); a 6th task or a second natural stage means it's a Standard plan.
- It runs in **one session on one stack** — no fan-out to parallel agents, no
  cross-session handoff.
- The risk is low and the path is understood — no spike, no rollback choreography, no
  external dependency whose failure needs a documented recovery.

When any of those is false, write a Standard plan. Borderline cases round **up** to the
heavier format; the user can always override down.

## Invariants kept vs artifacts dropped

The Light format is defined by exactly this split. The kept column is the drift
protection — it is not negotiable at any format. The dropped column is long-horizon
guardrail that a one-session job cannot need.

| Kept at Light (invariants) | Dropped at Light (long-horizon artifacts) |
|----------------------------|-------------------------------------------|
| Concrete runnable `Test:` per task | Mandated **Research Summary** section (findings go inline as a short **Context** line) |
| `- **Status:** [ ]` per task, flipped on green | Full **Preflight** checklist (only "baseline tests pass", folded into the gate) |
| Commit per green task | **Risk** / **Rollback** stage fields |
| Red-Green cycle budget (default 3) | `Blocks:` field (derivable from `Depends on` at ≤5 tasks) |
| Run-to-completion + stop conditions | `Parallel:` field (no fan-out at this size) |
| A single **Stage 1 Gate** incl. the full existing test suite | Tier-1 per-task review (one whole-diff review before close-out instead) |
| honest-gates integrity contract | Default goal-evaluator dispatch (opt-in at Light) |
| | Mirror-grep version-bump ritual (one stated bump) |

## Naming

A Light plan lives in the same `plans/` directory as any other plan (vault
`<portfolio_home>/plans/`, or `docs/plans/` in the no-vault fallback):

```
YYYY-MM-DD-<topic>-light-plan.md
```

Detection rule (used by `executing-plans` and the plan parser): a file is a Light plan
when its name ends in `-light-plan.md` **or** its first heading is `# Light Plan:`. This
mirrors the master-plan detection rule exactly.

## Light plan document format

A Light plan is one `## Stage 1:` holding 2–5 `### Task 1.N:` tasks and one
`### Stage 1 Gate`. It carries no Preflight section, no Risk/Rollback, and no
Blocks/Parallel fields.

```markdown
# Light Plan: [Name]
Date: YYYY-MM-DD

**Context:** [1–3 sentences: what this changes and the one or two facts that ground it —
the proportionate replacement for a Research Summary. Link a source if one matters.]

## Stage 1: [Name]

### Task 1.1: [description]
- **Status:** [ ]
- **Test:** `[exact command or concrete pass/fail criterion]`

### Task 1.2: [description]
- **Status:** [ ]
- **Depends on:** Task 1.1
- **Test:** `[exact command or concrete pass/fail criterion]`
- **Red-Green max cycles:** 3

### Stage 1 Gate
- [ ] [Integration check — the plan's goal proven end-to-end]
- [ ] Full existing test suite passes (regressions check)
```

### Field semantics

| Field | Meaning |
|-------|---------|
| `Status` | `[ ]` planned → flipped to `[x]` by executing-plans the moment the task's test goes green. Authoritative done-marker, identical to Standard plans. |
| `Depends on` | Optional. Present only when a task genuinely needs a prior task's output; omit for independent tasks (they simply run in listed order). No `Blocks` counterpart at Light. |
| `Test` | Mandatory. A concrete runnable check — the same bar as a Standard task. "It should work" is not a test. |
| `Red-Green max cycles` | Optional; defaults to 3 when omitted. |

The close-out line is identical to a Standard plan's:

```markdown
**Completed:** YYYY-MM-DD — commits: <list>
```

## Upgrade rule (do not patch a Light plan past its bounds)

A Light plan that grows during execution — a task splits into a second stage, or a 6th
task appears — is **re-issued as a Standard plan**, not patched in place. The Light
format has no Risk/Rollback/Blocks/Parallel fields to absorb the growth, and stretching
it produces a malformed hybrid. Re-run `planning-projects` on the expanded scope; the
Light plan file is superseded. This keeps the format boundary crisp: a `-light-plan.md`
file always means "single stage, ≤5 tasks."

## Parser-safety rules (mandatory)

The deterministic parser (`portfolio-unify.py`) is already correct for Light plans **by
construction** — a Light plan keeps the three line shapes the authoritative path keys on
(`## Stage N`, `### Task N.N:`, `- **Status:** [ ]`), so it needs no parser code. The
rules that keep it safe are the same ones every Status-field plan follows:

1. **Task done-state uses the `- **Status:** [ ]` field form, never a bare `- [ ]`
   bullet.** The field form is the authoritative signal; a bare checkbox in a task body
   would be suppressed anyway, but keep task bodies field-shaped.
2. **The only raw `- [ ]` bullets are under the `### Stage 1 Gate` heading.** Gate
   bullets are integration checks the parser excludes by design; they are never backlog
   candidates.
3. **No Preflight section.** A Light plan has none — the single baseline-tests check lives
   inside the gate. (The parser excludes Preflight bullets too, so this is about format
   cleanliness, not parser safety.)

A Light plan following this file yields exactly one backlog candidate per `Status: [ ]`
task while in progress, and **zero** candidates once its close-out line lands and every
task is `[x]` — identical to a Standard plan. That invariant is locked by
`../../portfolio/tests/test-portfolio-unify.py`.

## Execution semantics (summary)

Full model in `../../executing-plans/SKILL.md` § "Light plans". In short: Preflight is
git-bootstrap + baseline tests only; tasks run inline through the normal Red-Green loop
(no parallel dispatch at this size); the Tier-1 per-task review is replaced by **one**
whole-diff `git-github:code-reviewer` pass after the last task goes green and before the
gate; the goal-evaluator is opt-in rather than default; and close-out applies a **single
stated** SemVer bump (naming the manifest/marketplace mirror pair explicitly in this repo
rather than grepping for every mirror). Everything in the "Kept at Light" column above —
Status flips, commit per green task, cycle budgets, stop conditions, honest-gates, and
one handoff note at the single gate — is unchanged from a Standard plan.
