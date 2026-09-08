# market-research.md format (schema 3)

`market-research.md` is a project's **persistent, cited market-research artifact** —
the output of the `market-researcher` agent run through the competitive-analysis method
(`competitive-analysis-method.md`), written by the `/business:market-research` skill and
reused by `assess --research` and `/business:business-plan`. It lives at
`<vault_dir>/Portfolio/<area>/<project>/business/market-research.md`, next to the
competitor table it summarizes (`competitor-table.yaml`, spec in
`competitor-table-format.md`) and the quadrant/trajectory SVGs the skill renders.

**All machine-readable state lives in the YAML frontmatter.** The markdown body is
cited human evidence only — `business-scan.py` (the sole parser) reads *only* the
frontmatter here. If a fact needs to reach a downstream tool, it goes in the
frontmatter; the scanner never reads the body, and never opens the table.

## Frontmatter schema

```yaml
---
schema: 3
project: <registry name, e.g. xray-host>
researched: 2026-09-08       # YYYY-MM-DD — the date the research pass ran
depth: standard              # one of brief | standard | deep
confidence: medium           # one of: high | medium | low — overall evidence strength
competitors: 23              # schema 3: ROW count of competitor-table.yaml (groups + standalones)
coverage: exhausted          # schema 3: exhausted | open — did the discovery rate collapse?
---
```

### `schema` (required, int)

`schema: 3` is the current version; **`schema: 1` and `schema: 2` are still accepted** so
earlier artifacts keep parsing. The scanner keeps a per-artifact supported-schema set
(`{1, 2, 3}` for `market-research.md`) and validates the `depth` enum *against the
file's own schema* (see `depth` below); the schema-3 fields are required only at
schema 3 and emitted `null` for older files. An **unknown higher** schema (`4+`) is an
explicit "newer schema — upgrade the business plugin" error, never a silent misparse. A
non-integer (including `true`) or a value below 1 is a malformed-file error. Schema
changes bump this integer and update `business-scan.py` in lockstep.

### `project` (string)

The registry name. Validated only when present: if it doesn't match the project the
scanner is assessing, that's a per-file error (`stale copy-paste?`), symmetric with
`BUSINESS.md` (which also mismatch-checks rather than hard-requiring `project`).

### `researched` (required, date)

`YYYY-MM-DD`, the date the research pass ran. The scanner derives `age_days` from it;
`assess --research` and `business-plan` treat research older than **90 days** (the default
staleness window) as stale and offer to refresh rather than reuse. a one-off
analysis decays, and a trajectory is a forecast that must be confirmed or refuted.

### `depth` (required, enum — schema-dependent)

The valid values depend on the file's `schema`, and the scanner validates against the
matching set:

- **schema 2 and 3:** `brief` | `standard` | `deep` — the operator-selected research
  depth (the `/business:market-research` skill asks for it up front). See "Depth tiers".
- **schema 1 (legacy):** `triage` | `full` — the old binary depth. Still accepted so
  pre-existing artifacts parse; downstream consumers map `full` → effective `deep` and
  `triage` → effective `brief` when comparing against the tiers.

The scanner rejects any value not in the set for that file's schema.

### `competitors` (required at schema 3, int ≥ 0)

The **row** count of `competitor-table.yaml` — groups plus standalone rows, exactly the
`rows` figure `competitor-table.py validate` prints — not the raw count of companies
found (that goes in the body's `## Coverage`). A `brief` pass has no table, so it records
the number of competitor lines in `## Competitors`. The roll-up shows it (`· 23c`) so a
thin list is visible next to a stale one.

### `coverage` (required at schema 3, enum)

`exhausted` | `open`. **`exhausted`** only when the stop criterion of was met:
the time per newly found competitor had grown several-fold across all three list-building
passes. Anything else — a tier that stops early by design, a WebSearch budget that ran
out, fewer than 20 competitors on a global market with the rate still healthy — is
**`open`**, and the roll-up marks the row `OPEN`. "We found no competitors" is never
`exhausted`; it is `open` with the body's Coverage section saying what was searched.

### Depth tiers

The tier scales how far the pass goes and how much of the body is populated — never the
citation discipline (every claim is cited or an evidenced absence, at every tier). The
skill, the agent, and this file share this one definition; section numbers refer to
`competitive-analysis-method.md`:

- **`brief`** — the problem statement and competitor classes, the three-pass list with coverage stated, pricing signal, channels, demand signal. No table, no
  quadrants, no profiles, no personas, no sizing. "Who else solves this and what do they
  charge."
- **`standard`** — everything in `brief` **plus** the competitor table, the quadrant sweep with a chosen pair and the empty zone,
  group-level competitor profiles across the six blocks, a channel-level
  competitor-marketing summary, market sizing with method,
  trends, positioning gaps, the durability test, a five-component positioning,
  and one persona.
- **`deep`** — everything in `standard` **plus** trajectories, per-competitor
  profiles and per-competitor marketing teardowns, partner candidates among the indirect
  competitors, battlecards for the priority competitors, monitoring indicators, and 2–3 personas.

### `confidence` (required, enum)

`high` | `medium` | `low` — the agent's overall confidence in the evidence set (primary
sources → high; mostly secondary → medium; substantially inferred → low). The scanner
rejects any other value.

## Body (cited human evidence — not parsed)

Every claim carries a source or is framed as an **evidenced absence**; uncited prose is
forbidden. Any number — a market size, a download count, a price, a headcount — states
its **method and cited inputs**, and an estimate is marked low-confidence. "Could not
size — no data found (searched …)" is a first-class finding, never a fabricated number.
A finding also says *why it was kept and what follows from it* — one line,
not a paragraph.

Sections in this order. Tier annotations say which tiers populate a section; a tier
that does not populate one **omits** it rather than leaving a stub.

```markdown
# Market research: <project>

## Problem & customer job
<all tiers. The confirmed job statement — "when [situation], I want to [action], so that
[outcome]" — and the alternatives the customer uses today, each
cited or marked operator-stated. The whole analysis rests on this line.>

## Competitors
<all tiers. One line per row: **name** · class (direct/indirect) · group · found by
(category/customer-job/alternatives) · model (free/paid/freemium/donations/subscription)
· price · source URL. Same-job-different-method competitors are called out — they are
the dangerous ones. Non-consumption is NOT a row; its share goes under Demand.>

## Coverage
<all tiers. Raw count found · rows after grouping · passes run · the discovery-rate
observation that justified stopping (or that it was still healthy → `coverage: open`) ·
the source classes searched. Under 20 on a global market says so plainly.>

## Pricing signal
<all tiers. The price cluster and what it implies; unpublished prices traced to where a
customer asked in public; minimum price / average deal / what drives price where
found. Sales model per competitor (self-service / transactional / enterprise) from the
price-to-complexity ratio.>

## Channels
<all tiers. Per candidate channel: the distribution/monetization norm + the policy page
that makes a rule load-bearing.>

## Demand signal
<all tiers. Download counts, stars, thread volume — concrete, cited, hardness-marked —
plus the non-consumption share where any evidence of "no decision" outcomes exists.>

## Competitor table
<standard+. Points at `./competitor-table.yaml`; states the row/column counts and the
four characteristic categories covered; notes the columns collected beyond the
obvious and which were dropped for yielding nothing.>

## Quadrants
<standard+. The axis pair chosen from `competitor-table.py sweep` and why; the empty
zone; where `self` sits and its nearest neighbour; the grouping check outcome (groups
that scattered were dissolved); any unattractive-quadrant test applied. Links the
rendered SVG(s) (`./quadrant-<x>-<y>.svg`).>

## Trajectories
<deep. Per row: direction, vector length (trust), size change; the zone projected
to clear in two years and the reasoning; links `./trajectory-<x>-<y>.svg`. Marked as a
hypothesis to be confirmed by monitoring.>

## Competitor profiles
<standard = one profile per GROUP; deep = per competitor. The six blocks: team (public
professional history only — no personal data), strategy (the four levels and the judged
branch), product (positioning, measured weaknesses, switching cost, barriers, sales
model), marketing (see next section), metrics (with estimation method), investment &
organization (round-reading, investor roster, M&A direction). Every line cited.>

## Competitor marketing
<standard = channel-level summary; deep = per-competitor teardown. Channels (cited to
the observed presence), observed campaigns (cited to an ad-transparency library, a
landing page, or an announcement — "no ad-library entries found (searched Meta + Google,
<date>)" is a first-class evidenced absence), detected tooling (cited, marked
low-confidence), messaging/keywords (quoted and cited).>

## Customer personas
<standard = one; deep = 2–3. Evidence-grounded ideal-customer sketches: who, the job,
where they already look, willingness/ability to pay. A persona resting on an unconfirmed
audience is marked as such.>

## Market sizing
<standard+. TAM / SAM / SOM with the method stated and every input cited; estimates
marked soft; the adjacent-market conversion method when no analyst covers the
segment, with its calibration point if one was obtained. "Could not size" is valid.>

## Trends
<standard+. Demand direction over time — search interest, release cadence, forum
activity — cited. Analyst reports are facts, not the picture.>

## Positioning gaps
<standard+. Unmet needs / underserved segments a new entrant could take, grounded in the
evidence above and the empty zone in the quadrant.>

## Durability of advantage
<standard+. The benefit + barrier test: which of the seven barriers the project can
claim, the copy-rationality test, and the incumbent-reaction estimate (segment sized in
the incumbent's money vs. ~10% of their enterprise value). "Temporary" is an honest
answer.>

## Positioning
<standard+. The five components in order: competitive alternatives → unique
attributes → value with evidence → customers for whom it is critical → market category
(existing vs. a named subcategory). Ends in one sentence business-plan can quote.>

## Partner candidates
<deep. Each indirect competitor with the two shares (revenue from the competing product;
development spend on it) where evidenced, and the white-label case.>

## Battlecards
<deep. One block per priority competitor: how they position, strong points, weak
points, standard objections both ways, when we win, when we lose.>

## Monitoring indicators
<deep. Per priority competitor: the situations that affect us and the observable
indicator for each, with the source to watch. The trajectory each indicator tests.>

## Gaps
<all tiers. What could not be evidenced — sources searched and empty — so downstream
consumers lower confidence rather than assume coverage.>
```

## Schema versioning

`schema: 3` is the current version; **`schema: 1` and `schema: 2` remain supported** (the
scanner accepts all three and validates `depth` against the file's own schema). The
scanner degrades loudly on an unknown higher schema — `4+` is an "upgrade the business
plugin" error, never a silent misparse — the same discipline as `BUSINESS.md`. Schema 3
added the `competitors` and `coverage` frontmatter fields and the method-driven body
sections (Problem & customer job, Coverage, Competitor table, Quadrants, Trajectories,
Competitor profiles, Durability of advantage, Positioning, Partner candidates,
Battlecards, Monitoring indicators); schema 2 had added the tiered `depth` enum and the
Competitor marketing / Customer personas sections; a schema-1 artifact has the binary
`triage|full` depth and neither.
