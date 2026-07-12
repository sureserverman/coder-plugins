# market-research.md format (schema 1)

`market-research.md` is a project's **persistent, cited market-research artifact** —
the deep-depth output of the `market-researcher` agent, written by the
`/business:market-research` skill and reused by `assess --research` and
`/business:business-plan`. It lives at
`<vault_dir>/Portfolio/<area>/<project>/business/market-research.md`.

**All machine-readable state lives in the YAML frontmatter.** The markdown body is
cited human evidence only — `business-scan.py` (the sole parser) reads *only* the
frontmatter here. If a fact needs to reach a downstream tool, it goes in the
frontmatter; the scanner never reads the body.

## Frontmatter schema

```yaml
---
schema: 1
project: <registry name, e.g. xray-host>
researched: 2026-07-12       # YYYY-MM-DD — the date the research pass ran
depth: full                  # one of: triage | full
confidence: medium           # one of: high | medium | low — overall evidence strength
---
```

### `schema` (required, int)

`schema: 1` is required. The scanner treats an **unknown** (higher) schema version as an
explicit "newer schema — upgrade the business plugin" error, never a silent misparse.
A non-integer (including `true`) or a value below 1 is a malformed-file error. Schema
changes bump this integer and update `business-scan.py` in lockstep.

### `project` (required, string)

The registry name. If it doesn't match the project the scanner is assessing, that's a
per-file error (`stale copy-paste?`), symmetric with `BUSINESS.md`.

### `researched` (required, date)

`YYYY-MM-DD`, the date the research pass ran. The scanner derives `age_days` from it;
`assess --research` and `business-plan` treat research older than **90 days** (the default
staleness window) as stale and offer to refresh rather than reuse.

### `depth` (required, enum)

`triage` | `full`. The `market-research` skill always writes `full`; `triage` is recorded
only when a lighter pass produced the artifact. The scanner rejects any other value.

### `confidence` (required, enum)

`high` | `medium` | `low` — the agent's overall confidence in the evidence set (primary
sources → high; mostly secondary → medium; substantially inferred → low). The scanner
rejects any other value.

## Body (cited human evidence — not parsed)

Every claim carries a source or is framed as an **evidenced absence**; uncited prose is
forbidden (it's exactly what the agent exists to prevent). Any number — a market size, a
download count, a price — states its **method and cited inputs**, and an estimate is
marked low-confidence. "Could not size — no data found (searched …)" is a first-class
finding, never a fabricated number.

```markdown
# Market research: <project>

## Competitors
<name · model (free/paid/freemium/donations/subscription) · price · source URL>, one per line.

## Pricing signal
<the price cluster and what it implies, each figure cited>

## Market sizing
<TAM / SAM / SOM with the method stated and every input cited; estimates marked soft.
"Could not size" is a valid, first-class outcome.>

## Trends
<demand direction over time — search interest, release cadence, forum activity — cited>

## Positioning gaps
<unmet needs / underserved segments a new entrant could take, grounded in the evidence above>

## Channels
<per candidate channel: the distribution/monetization norm + the policy page that makes a rule load-bearing>

## Demand signal
<download counts, stars, thread volume — concrete and cited, hardness-marked>

## Gaps
<what could not be evidenced, so downstream consumers lower confidence rather than assume coverage>
```

## Schema versioning

`schema: 1` is the current version. The scanner degrades loudly on an unknown higher
schema (upgrade prompt), never a silent misparse — the same discipline as `BUSINESS.md`.
