---
name: business-plan
description: >
  Compose a full, detailed business plan for ONE portfolio project — executive summary, market analysis, competitive landscape, financials, risks, milestones — into business/plan.md. Triggers on "write a business plan", "full business plan for this", "business plan document".
---

# business-plan — compose the full plan

Fold everything the pipeline already knows about a project — the `assess` verdict, the
`revenue-model` monetization decision, the `market-research.md` evidence, and the live
`gtm-plan.md` / `metrics.md` state — plus a short gap interview into one classic business
plan at `business/plan.md`. This skill **composes**; it does not re-decide the verdict or
the model. If a prerequisite is missing, it offers to run the skill that owns it.

**Announce at start:** "Using the business-plan skill to compose <project>'s plan."

## Choose the plan depth tier (ask first)

Before composing, ask the operator **how detailed** the plan should be — the first question,
and it scales how much elaboration each section carries (per `plan-format.md`'s tier rules).
Present it as one multiple-choice question with a one-line trade-off each:

- **`brief`** — the core plan (summary, problem, market, competition, roadmap, marketing,
  operations, risks, milestones). Personas and SWOT condensed or omitted; a single expected
  financial column. For a quick internal go/no-go.
- **`standard`** — all twelve sections in full: one customer persona, a full SWOT &
  positioning section, a channel-playbook Marketing & sales, and the three-column financial
  scenarios table. The recommended default for a plan you'll act on.
- **`deep`** — everything in standard with fuller elaboration: 2–3 personas, a per-competitor
  marketing read in Marketing & sales, and sensitivity notes on the financials. For a launch
  or a plan you'll show an outside party.

Record the chosen tier — it becomes the plan's `depth:` frontmatter and governs the body.
If the operator has no preference, default to `standard` and say so. (A `deep` plan composes
best from a `standard`/`deep` market-research artifact — see Market research below.)

## Determinism boundary

Read ALL business state from the scanner — never hand-parse `BUSINESS.md`, `gtm-plan.md`,
`metrics.md`, or `market-research.md` for their cross-project fields:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/business-scan.py
```

The scanner JSON envelope carries `vault_dir`; the project entry carries `area`/`name`,
`verdict`, `monetization`, `targets`, `research`, `gtm`, `metrics`, and `errors`. Resolve
`home = <vault_dir>/Portfolio/<area>/<name>/` and write to `<home>/business/plan.md`,
conforming to `${CLAUDE_PLUGIN_ROOT}/references/plan-format.md` (schema 2). When editing an
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

Read the project's `research` block from the scanner. Two things matter: **freshness**
(`research.age_days` ≤ **90**) and **effective depth**. Map the artifact's `research.depth`
to an effective tier: schema-2 `brief`/`standard`/`deep` are themselves; legacy schema-1
`full` ≈ `deep` and `triage` ≈ `brief`. A plan's Competitive landscape, SWOT, and Marketing
& sales sections draw on the competitor-marketing and positioning evidence that only a
**`standard`+** research pass produces.

- **Fresh AND effective depth ≥ `standard`** → `Read` `business/market-research.md` and
  compose the Market analysis, Competitive landscape, SWOT & positioning, and Marketing &
  sales sections from its cited findings (personas fold into the Customer personas section).
  Set `market_research: <its researched date>` in the plan frontmatter.
- **Fresh but only `brief`/`triage`** → the sizing and competitor-marketing evidence a full
  plan wants isn't there. **Offer `/business:market-research` at `standard`/`deep`** to
  deepen it. If the operator proceeds anyway, compose Market analysis and Competitive
  landscape from what the brief pass *does* have, and mark SWOT/personas/Marketing as resting
  on thin evidence — don't invent the missing sizing or campaigns.
- **Stale or missing** → **offer `/business:market-research`** (a fresh pass at the tier that
  matches the plan depth). If the operator declines or WebSearch is unavailable, **proceed
  without inventing market numbers**: set `market_research: none`, and give the Market
  analysis section a visible **`## Market analysis — UNRESEARCHED`** header stating no cited
  sizing exists. The plan is still useful; the gap is just honest.

## Gap interview — only what the artifacts can't answer

Ask, one question at a time (multiple-choice where the answer space is finite), only for
what isn't already in the scanner JSON or the artifacts. **Confirm inferred inputs rather
than assuming them** — a plan silently built on a guessed cost base or volume is worse than
one that asked. Cover:

- **Cost base** — the monthly fixed + variable costs to run this (hosting, services, fees).
- **Time** — hours/week the operator can put in (sizes what's realistic).
- **Persona inputs** (for the Customer personas section) — beyond what research supplies,
  confirm the primary persona(s): who the plan is really for and what would make them pay.
  Reuse the research personas where they exist; ask only to confirm or add.
- **SWOT raw material** — the operator's own read of the project's **strengths and
  weaknesses** (the internal axes; Opportunities/Threats come from the research's positioning
  gaps and trends, so don't re-ask those). One or two each is enough.
- **Marketing budget & channel priorities** — the monthly marketing spend (often $0 for a
  solo dev — confirm, don't assume) and which of the research-surfaced channels the operator
  will actually work. This grounds the Marketing & sales playbook in reality.
- **Milestones** — target dates for the next 2–3 concrete goals (default to `BUSINESS.md`
  `targets[]` dates where they exist — don't re-ask what's already recorded).
- **Scenario assumptions** — the volume basis for conservative / expected / optimistic.
  **Confirm each with the operator** (tie to the research demand signal where one exists);
  never silently default a volume — state the basis you propose and get agreement, then mark
  any still-unevidenced number as an explicit assumption.

Stop asking once you can populate every section the chosen tier requires. You need enough to
compose, not everything — and a `brief` plan asks less (personas/SWOT are condensed there).

## Compose the plan (all twelve sections)

Write `<home>/business/plan.md` per `references/plan-format.md` — frontmatter `schema: 2`,
`project: <name>`, `date: <today>`, `status: draft`, `depth: <the chosen tier>`,
`market_research: <date|none>` — and a body with **all twelve sections**: Executive summary ·
Problem & solution · Customer personas · Market analysis · Competitive landscape · SWOT &
positioning · Product & roadmap · Marketing & sales · Operations · Financial scenarios ·
Risks · Milestones. The tier scales elaboration (per `plan-format.md`): `standard` gives all
twelve in full; `deep` adds 2–3 personas, a per-competitor read in Marketing & sales, and
financial sensitivity notes; `brief` may condense or omit Customer personas and SWOT &
positioning and show a single expected financial column. Compose the three research-derived
sections deliberately:

- **Customer personas** — from `market-research.md`'s `## Customer personas` (or the
  confirmed audience if research was skipped/brief), marking any assumption-based persona.
- **SWOT & positioning** — Strengths/Weaknesses from the operator interview,
  Opportunities/Threats from the research's positioning gaps and trends, plus a one-sentence
  positioning statement ("For <persona>, <project> is the <category> that <differentiator>,
  unlike <competitor>").
- **Marketing & sales** — a channel playbook informed by `market-research.md`'s
  `## Competitor marketing`: which channels to work and why, the messaging angle from the
  positioning statement, and (at `deep`) what to imitate vs. counter per competitor. Links to
  `./gtm-plan.md` for the dated checklist rather than restating it.

Two hard rules:

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
draft`, `plan.depth: <the tier you chose>`, a computed `plan.age_days` (0 today), and **zero
`errors`** for the project (a non-empty `errors` array means the file doesn't conform — a
schema-2 plan must carry a valid `depth`; fix it).

## Hand off

- No `gtm-plan.md` yet (`gtm: null`) → suggest `/business:launch` to turn the plan's
  Marketing & sales section into a dated go-to-market checklist.
- Suggest `/business:track` once actuals start, and `/business:biz-portfolio` to see the
  plan surfaced in the roll-up.
