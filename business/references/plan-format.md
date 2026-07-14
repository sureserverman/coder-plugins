# plan.md format (schema 2)

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
schema: 2
project: <registry name, e.g. xray-host>
date: 2026-07-12             # YYYY-MM-DD — when this plan revision was composed
status: draft                # one of: draft | active
depth: standard              # schema 2: one of brief | standard | deep
market_research: 2026-07-12  # the researched date of the market-research.md folded in, or `none`
---
```

### `schema` (required, int)

`schema: 2` is the current version; **`schema: 1` is still accepted** so plans composed
before the depth-tier change keep parsing (a schema-1 plan simply has no `depth` field —
the scanner reports `depth: null` for it, never an error). Same discipline as every
business artifact: an unknown higher schema (`3+`) is a loud "upgrade the business plugin"
error; a non-integer (including `true`) or a value below 1 is a malformed-file error.
Schema bumps update `business-scan.py` in lockstep.

### `depth` (schema 2 — required on new plans, absent on legacy)

`brief` | `standard` | `deep` — the operator-selected plan depth (the `/business:business-plan`
skill asks for it up front and scales the body accordingly, per "Body" below). Required in a
schema-2 plan; the scanner rejects any other value. A **schema-1** plan has no `depth` field
and the scanner reports it as `null` — legacy plans are not retro-tiered.

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

All twelve sections are present, scaled to solo-dev reality (detailed, no corporate
filler). The `depth` frontmatter tier governs how much elaboration each section carries —
the sections themselves are always present at `standard`+; `brief` may condense or omit the
tier-gated ones as noted:

- **`brief`** — the core plan: Executive summary, Problem & solution, Market analysis,
  Competitive landscape, Product & roadmap, Marketing & sales, Operations, Risks,
  Milestones. Customer personas and SWOT & positioning may be condensed to a few lines or
  omitted; Financial scenarios may be a single expected column rather than the full
  three-scenario table.
- **`standard`** — all twelve sections in full: the core above plus **one** Customer
  persona, a full **SWOT & positioning** section, a channel-playbook **Marketing & sales**,
  and the three-column Financial scenarios table.
- **`deep`** — everything in `standard` with fuller elaboration: **2–3** Customer personas,
  a per-competitor marketing read woven into Marketing & sales, and **sensitivity notes**
  on the Financial scenarios (what moves the net most).

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

## Customer personas
<schema 2, `standard`+ (standard = one persona; deep = 2–3). Ideal-customer sketches folded
from market-research.md's `## Customer personas` (or the assess audience if research was
skipped): who they are, their job-to-be-done, where they look today, willingness to pay.
Mark any persona resting on an unconfirmed audience. `brief` may condense or omit.>

## Market analysis
<TAM/SAM/SOM and demand, sourced from market-research.md — or the UNRESEARCHED header if none>

## Competitive landscape
<named competitors, their models/prices, and this project's positioning — cited from research>

## SWOT & positioning
<schema 2, `standard`+. A SWOT grid (Strengths / Weaknesses / Opportunities / Threats)
grounded in the competitive and market evidence above — not generic prose — and a
**one-sentence positioning statement** ("For <persona>, <project> is the <category> that
<key differentiator>, unlike <competitor>"). Strengths/Weaknesses come from the operator
interview; Opportunities/Threats trace to the research's positioning gaps and trends.
`brief` may condense to a few lines or omit.>

## Product & roadmap
<what ships now, what's next; links to the project's plans rather than restating them>

## Marketing & sales
<the channel playbook and go-to-market motion, informed by market-research.md's
`## Competitor marketing` findings: which channels to use and why (where the audience and
competitors actually are), the messaging angle drawn from the positioning statement, and —
at `deep` — a per-competitor read of what to imitate vs. counter. Links to ./gtm-plan.md
for the concrete dated checklist rather than restating it.>

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

`schema: 2` is the current version; **`schema: 1` remains supported** (a schema-1 plan has
no `depth` field — the scanner reports `depth: null`, not an error). The scanner degrades
loudly on an unknown higher schema (`3+` → upgrade prompt), never a silent misparse. Schema
2 added the required `depth` enum (`brief|standard|deep`) and the `## Customer personas` and
`## SWOT & positioning` body sections, and expanded Marketing & sales into a channel
playbook informed by the research's competitor-marketing findings.
