# plan.md format (schema 1)

`plan.md` is a project's **full, human-readable business plan** — the composed output of
`/business:business-plan`, which folds the `BUSINESS.md` verdict, the `revenue-model`
monetization decision, the `market-research.md` evidence, and the live `gtm-plan.md` /
`metrics.md` state into one classic business-plan document. It lives at
`<vault_dir>/Portfolio/<area>/<project>/business/plan.md`.

Unlike `BUSINESS.md`, the plan is a **document first**: the body is the deliverable a
reader takes end-to-end. Only a light frontmatter is machine-readable — enough for the
scanner to report that a plan exists, how old it is, and its status. Everything else is
prose. `business-scan.py` (the sole parser) reads *only* the frontmatter.

## Frontmatter schema

```yaml
---
schema: 1
project: <registry name, e.g. xray-host>
date: 2026-07-12             # YYYY-MM-DD — when this plan revision was composed
status: draft                # one of: draft | active
market_research: 2026-07-12  # the researched date of the market-research.md folded in, or `none`
---
```

### `schema` (required, int)

`schema: 1` is required. Same discipline as every business artifact: an unknown higher
schema is a loud "upgrade the business plugin" error; a non-integer (including `true`) or
a value below 1 is a malformed-file error. Schema bumps update `business-scan.py` in
lockstep.

### `project` (string)

The registry name. Validated only when present: a mismatch with the assessed project is
a per-file error, symmetric with `BUSINESS.md` (which mismatch-checks rather than
hard-requiring `project`).

### `date` (required, date)

`YYYY-MM-DD`, the date this plan revision was composed. The scanner derives `age_days`;
the roll-up and compass flag a stale plan from it.

### `status` (required, enum)

`draft` | `active`. `business-plan` writes `draft` on first composition; the operator
promotes it to `active` once the plan is being executed. The scanner rejects any other
value.

### `market_research` (required)

The `researched:` date of the `market-research.md` that this plan folded in (a
`YYYY-MM-DD` string), or the literal `none` when the plan was composed without research
(offline / WebSearch denied). When `none`, the body's Market analysis section carries a
visible **"Market analysis — UNRESEARCHED"** header so the gap is never silent.

## Body (the plan — not parsed)

All ten sections are present, scaled to solo-dev reality (detailed, no corporate filler).
Two hard rules the format enforces:

1. **No uncited market numbers.** Any figure sourced from the market — size, price,
   competitor count, demand — traces to `market-research.md` (or, if research was
   skipped, is absent and the UNRESEARCHED header says so). The plan does not invent
   market numbers.
2. **Link, don't duplicate.** The plan references `gtm-plan.md` for launch actions and
   `metrics.md` for actuals rather than copying their numbers — those artifacts are the
   live source of truth, and a copied number goes stale the moment they update.

```markdown
# Business plan: <project>

## Executive summary
<the whole plan in one paragraph — verdict, audience, model, the ask/goal>

## Problem & solution
<the problem, who has it, and how this project solves it>

## Market analysis
<TAM/SAM/SOM and demand, sourced from market-research.md — or the UNRESEARCHED header if none>

## Competitive landscape
<named competitors, their models/prices, and this project's positioning — cited from research>

## Product & roadmap
<what ships now, what's next; links to the project's plans rather than restating them>

## Marketing & sales
<channels and the go-to-market motion; links to ./gtm-plan.md for the concrete checklist>

## Operations
<how it's built, maintained, supported — solo-dev realities: hours/week, tooling, costs>

## Financial scenarios
<a monthly table with conservative / expected / optimistic columns: fixed + variable costs,
price × volume revenue, and the resulting net. Assumptions stated; volume numbers traced
to the demand signal in research where one exists.>

## Risks
<the top risks and their mitigations — market, execution, and operability>

## Milestones
<dated goals; these mirror BUSINESS.md targets[] rather than inventing new numbers>
```

### Financial scenarios table (shape)

```markdown
| Month | Fixed cost | Variable cost | Price | Conservative vol · rev | Expected vol · rev | Optimistic vol · rev | Expected net |
|-------|-----------|---------------|-------|------------------------|--------------------|----------------------|--------------|
| M1    | $5        | $0            | $3    | 2 · $6                 | 10 · $30           | 25 · $75             | $25          |
```

Volume figures state their basis (a cited demand signal, or an explicit assumption marked
as such). An unresearched plan may show costs and price but marks the volume columns as
assumptions, not evidence.

## Schema versioning

`schema: 1` is the current version; the scanner degrades loudly on an unknown higher
schema, never a silent misparse.
