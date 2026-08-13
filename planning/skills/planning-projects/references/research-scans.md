# Phase 0 scans — literal forms, and the reasoning behind each

`../SKILL.md` § Phase 0 — Research carries the rules: run the decisions, backlog, workflow-spec
and architecture-doc scans, and record what each one found on the plan. This file carries the
literal output forms and the reasoning those rules compress.

## Decisions scan

### Why the register beats a plan's own summary

Unlike a plan, a register entry carries the *reason* a constraint exists. That includes
security recommendations recorded from `sec-audit` runs whose report files are local-only and
unreadable from a planning session — the register is the only place those constraints are
legible at planning time. Calling the `decisions` skill's `relevant` operation infers the
domain registers from the project's stack (`../../decisions/references/domain-slugs.md`) and
digests both halves in one step, rather than making you hand-read files.

### The literal `## Decisions in force` section

The scan's output goes directly under the Research Summary. Use non-checkbox bullets: a raw
`- [ ]` outside Preflight and Gate blocks becomes a false backlog candidate in
`portfolio unify`. When nothing applies, say so explicitly:

```markdown
## Decisions in force

- none — registers consulted: `Portfolio/decisions/rust.md`, `Portfolio/decisions/ubuntu.md`; no entry binds this scope

**Registers consulted:** rust, ubuntu (project register: absent — new project)
**Domains inferred:** rust, ubuntu, tor (no register exists for `tor` yet)
```

Recording what was consulted is what lets a reader tell **"nothing binds this scope"** from
**"nobody looked"** — the same distinction the architecture-doc rule makes with its
"no architecture doc — structure decided inline" form. Two plans that both say nothing about
decisions are indistinguishable; two plans where one names its registers are not.

### Greenfield projects

On a project with no registry entry, `portfolio_home` does not resolve and there is no
`decisions.md`. The **per-domain** registers are keyed by domain rather than project, so they
bind a greenfield project just the same — and they are the half that matters most to it, since
it has no project history of its own. Registration then happens on the normal path, when the
plan is written (`../SKILL.md` § Output location (vault-canonical), step 3).

## Workflow-spec scan

### Redesign-from-handoff plans

A plan reproducing a Claude Design handoff pack via the `applying-design-handoff` skill makes
behavior changes *the rule, not the exception*: the design is the source of truth and reshapes
functionality to fit. Plan it so the design wins but every behavior change is gated —

- each task that alters or drops a flow to match the design declares it
  (`Changes WF-NNN` / `Removes WF-NNN`);
- each new design screen adds a capture step, so the spec does not fall behind the code;
- the stage carries a **reconciliation/sign-off task** that presents the conflict report and
  gets the user's explicit approval **before** any destructive behavior change is applied.

A redesign plan with no WF declarations is almost certainly missing them, not free of them.

## Architecture doc scan

### Why the conformance gate carries the `(judgment)` marker

The final stage gate's architecture check is a conformance judgment over a *built tree*: no
sweep can prove that a directory layout matches an approved structure, or that a boundary was
respected rather than merely declared. It carries **(judgment)** for the same reason the
decisions-conformance check does, and a template emitting it unmarked would ship the one check
shape `../SKILL.md` § Write a set-valued check as the sweep that proves it forbids. The marker
routes it to the gate's evaluator, and `executing-plans` then verifies conformance at close-out
with no special handling.

### Decomposed projects

Each *sub-plan* that creates structure carries its own ARCH-ID citations and its own
conformance check in its own final stage gate. The master's register `**Gate:**` blocks are
untouched, and the master's no-tasks / no-Preflight parser-safety invariant is unaffected by
the citation convention — citations live on task lines, which masters do not have.

## Citing decisions on tasks

The citation mechanism is deliberately **identical** to `ARCH-NN`, so `executing-plans` needs
no special handling for either. `Honors DEC-003` is what carries a constraint from the register
to the person or agent implementing the task, who may never read the register itself.
`Supersedes GDEC-AND-002 — <why>` is what makes an override *auditable* rather than silent, and
it is the executor's instruction to record the supersede at close-out.

Per DEC-001, a citation restates the constraint in the entry's own words — a decision sourced
from a sec-audit never brings the report body into the plan, because those reports are
local-only by policy.

An uncited change contradicting an accepted decision is a **gate failure** in
`executing-plans`, not an advisory: silently violating a recorded decision is the exact failure
the register exists to prevent.
