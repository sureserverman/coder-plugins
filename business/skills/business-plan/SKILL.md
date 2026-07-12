---
name: business-plan
description: >
  Compose a full, detailed business plan for ONE portfolio project — executive summary, market analysis, competitive landscape, product & roadmap, marketing & sales, operations, financial scenarios, risks, and milestones — into business/plan.md. Use when you want the whole plan as a document, not a triage verdict. Triggers on "write a business plan", "full business plan for this", "business plan document", "financial projections for this project", "put together the business plan", "compose the plan". Composes existing pipeline state (verdict, monetization, market research, GTM, metrics) plus a short gap interview — it does not re-decide the verdict.
---

# business-plan — compose the full plan

Fold everything the pipeline already knows about a project — the `assess` verdict, the
`revenue-model` monetization decision, the `market-research.md` evidence, and the live
`gtm-plan.md` / `metrics.md` state — plus a short gap interview into one classic business
plan at `business/plan.md`. This skill **composes**; it does not re-decide the verdict or
the model. If a prerequisite is missing, it offers to run the skill that owns it.

**Announce at start:** "Using the business-plan skill to compose <project>'s plan."

## Determinism boundary

Read ALL business state from the scanner — never hand-parse `BUSINESS.md`, `gtm-plan.md`,
`metrics.md`, or `market-research.md` for their cross-project fields:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/business-scan.py
```

The scanner JSON envelope carries `vault_dir`; the project entry carries `area`/`name`,
`verdict`, `monetization`, `targets`, `research`, `gtm`, `metrics`, and `errors`. Resolve
`home = <vault_dir>/Portfolio/<area>/<name>/` and write to `<home>/business/plan.md`,
conforming to `${CLAUDE_PLUGIN_ROOT}/references/plan-format.md` (schema 1). When editing an
existing `plan.md`, `Read` it first (the scanner JSON omits the body) and make targeted
edits. You may `Read` the sibling artifacts' **bodies** for their prose to compose from —
just don't parse their frontmatter for state the scanner already gives you.

## Preflight — check prerequisites from the scanner JSON

Branch on the project's scanner entry. Never fabricate a verdict or a model to fill a gap.

- **No verdict** (`assessed: false`, or `verdict: null`) → **offer to run `/business:assess`
  first** and stop until it's done. A plan with no verdict has no spine.
- **Verdict is `park` / `internal-only`** → there's no plan to compose. Say so and stop
  (these are complete end states; re-assess if that changed).
- **`errors` non-empty** → stop and report; fix the assessment before composing.
- **No monetization model** (`monetization.model: null`) but verdict is
  `monetize`/`free-for-reputation` → **strongly suggest `/business:revenue-model` first**
  (the Financial scenarios and Marketing sections are thin without a model), but do **not**
  block — the operator may want a plan draft now. If they proceed, note the model as TBD.
- **Research** — see the next section.

## Market research — reuse, refresh, or mark unresearched

Read the project's `research` block from the scanner:

- **Fresh** (`research.exists: true`, `research.age_days` ≤ **90**) → `Read`
  `business/market-research.md` and compose the Market analysis and Competitive landscape
  sections from its cited findings. Set `market_research: <its researched date>` in the
  plan frontmatter.
- **Stale or missing** → **offer `/business:market-research`** (a fresh full pass). If the
  operator declines or WebSearch is unavailable, **proceed without inventing market
  numbers**: set `market_research: none`, and give the Market analysis section a visible
  **`## Market analysis — UNRESEARCHED`** header stating no cited sizing exists. The plan is
  still useful; the gap is just honest.

## Gap interview — only what the artifacts can't answer

Ask, one question at a time (multiple-choice where the answer space is finite), only for
what isn't already in the scanner JSON or the artifacts:

- **Cost base** — the monthly fixed + variable costs to run this (hosting, services, fees).
- **Time** — hours/week the operator can put in (sizes what's realistic).
- **Milestones** — target dates for the next 2–3 concrete goals (default to `BUSINESS.md`
  `targets[]` dates where they exist — don't re-ask what's already recorded).
- **Scenario assumptions** — the volume basis for conservative / expected / optimistic (tie
  to the research demand signal where one exists; otherwise mark them as assumptions).

Stop asking once you can populate the financial scenarios. You need enough to compose, not
everything.

## Compose the plan (all ten sections)

Write `<home>/business/plan.md` per `references/plan-format.md` — frontmatter `schema: 1`,
`project: <name>`, `date: <today>`, `status: draft`, `market_research: <date|none>` — and
a body with **all ten sections**: Executive summary · Problem & solution · Market analysis ·
Competitive landscape · Product & roadmap · Marketing & sales · Operations · Financial
scenarios · Risks · Milestones. Two hard rules:

1. **No uncited market numbers.** Every market figure (size, price, competitor count,
   demand) traces to `market-research.md`. If research was skipped, the market numbers are
   absent and the UNRESEARCHED header says so — do not invent them.
2. **Link, don't duplicate.** Reference `./gtm-plan.md` for the launch checklist and
   `./metrics.md` for actuals rather than copying their numbers — those are the live source
   of truth and a copied number goes stale. Milestones mirror `BUSINESS.md` `targets[]`.

**Financial scenarios** is a monthly table with conservative / expected / optimistic
columns (fixed + variable cost, price × volume revenue, resulting net). State every
assumption; tie volume to the research demand signal where one exists, else mark it an
assumption. An unresearched plan may still show costs and price but marks volumes as
assumptions.

## Verify

Run `business-scan.py` and confirm the project shows `plan.exists: true`, `plan.status:
draft`, a computed `plan.age_days` (0 today), and **zero `errors`** for the project.

## Hand off

- No `gtm-plan.md` yet (`gtm: null`) → suggest `/business:launch` to turn the plan's
  Marketing & sales section into a dated go-to-market checklist.
- Suggest `/business:track` once actuals start, and `/business:biz-portfolio` to see the
  plan surfaced in the roll-up.
