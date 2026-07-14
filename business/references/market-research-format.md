# market-research.md format (schema 2)

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
schema: 2
project: <registry name, e.g. xray-host>
researched: 2026-07-12       # YYYY-MM-DD — the date the research pass ran
depth: deep                  # schema 2: one of brief | standard | deep
confidence: medium           # one of: high | medium | low — overall evidence strength
---
```

### `schema` (required, int)

`schema: 2` is the current version; **`schema: 1` is still accepted** so artifacts
written before the depth-tier change keep parsing. The scanner keeps a per-artifact
supported-schema set (`{1, 2}` for `market-research.md`) and validates the `depth` enum
*against the file's own schema* (see `depth` below). An **unknown higher** schema (`3+`)
is an explicit "newer schema — upgrade the business plugin" error, never a silent
misparse. A non-integer (including `true`) or a value below 1 is a malformed-file error.
Schema changes bump this integer and update `business-scan.py` in lockstep.

### `project` (string)

The registry name. Validated only when present: if it doesn't match the project the
scanner is assessing, that's a per-file error (`stale copy-paste?`), symmetric with
`BUSINESS.md` (which also mismatch-checks rather than hard-requiring `project`).

### `researched` (required, date)

`YYYY-MM-DD`, the date the research pass ran. The scanner derives `age_days` from it;
`assess --research` and `business-plan` treat research older than **90 days** (the default
staleness window) as stale and offer to refresh rather than reuse.

### `depth` (required, enum — schema-dependent)

The valid values depend on the file's `schema`, and the scanner validates against the
matching set:

- **schema 2:** `brief` | `standard` | `deep` — the operator-selected research depth (the
  `/business:market-research` skill asks for it up front). See "Depth tiers" below.
- **schema 1 (legacy):** `triage` | `full` — the old binary depth. Still accepted so
  pre-existing artifacts parse; downstream consumers map `full` → effective `deep` and
  `triage` → effective `brief` when comparing against the schema-2 tiers.

The scanner rejects any value not in the set for that file's schema (a schema-2 file with
`depth: full`, or a schema-1 file with `depth: deep`, is a malformed-file error).

### Depth tiers (schema 2)

The tier scales how far the research pass goes and how much of the body is populated —
never the citation discipline (every claim is cited or an evidenced absence, at every
tier). This is the single definition both the `market-research` skill and the
`market-researcher` agent reference:

- **`brief`** — competitors, pricing signal, channels, demand signal. No market sizing, no
  competitor-marketing teardown, no personas. The fast "who else is here and what do they
  charge" pass.
- **`standard`** — everything in `brief` plus TAM/SAM/SOM sizing, trends, positioning gaps,
  a **channel-level competitor-marketing summary** (which channels competitors use, at a
  glance), and **one** customer persona.
- **`deep`** — everything in `standard` plus a **per-competitor marketing teardown**
  (campaigns observed, detected tooling, messaging/keywords — see "Competitor marketing"
  below) and **2–3** customer personas.

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

## Competitor marketing
<schema 2, `standard`+ (deep = per-competitor teardown; standard = channel-level summary).
How competitors actually reach their audience, every claim cited or framed as an
evidenced absence:
- **Channels** — where each competitor markets (their own blog/newsletter, an app-store
  listing, a subreddit, YouTube, paid search/social), cited to the observed presence.
- **Observed campaigns** — concrete, dated promotions or ad activity, cited to an
  ad-transparency library (Meta Ad Library, Google Ads Transparency Center, TikTok/LinkedIn
  ad libraries), a landing page, or a changelog/announcement. "No ad-library entries found
  (searched Meta + Google, <date>)" is a first-class evidenced absence, never "they don't
  advertise".
- **Detected tooling** — analytics/marketing stack inferred from concrete signals
  (BuiltWith/Wappalyzer readout, page source, tracker domains), each cited; mark inferences
  low-confidence.
- **Messaging / keywords** — the positioning language and search terms a competitor leans
  on (headline copy, meta keywords, store keywords), quoted and cited to the page.
`brief` passes omit this section entirely.>

## Customer personas
<schema 2, `standard`+ (standard = one persona; deep = 2–3). Evidence-grounded ideal-customer
sketches — for each: who they are, the job-to-be-done, where they already look for a
solution, and willingness/ability to pay — each grounded in the demand/channel evidence
above or an operator-confirmed audience, not invented. Mark any persona resting on an
assumed (unconfirmed) audience. `brief` passes omit this section.>

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

`schema: 2` is the current version; **`schema: 1` remains supported** (the scanner accepts
both and validates `depth` against the file's own schema, per the `depth` section). The
scanner degrades loudly on an unknown higher schema — `3+` is an "upgrade the business
plugin" error, never a silent misparse — the same discipline as `BUSINESS.md`. Schema 2
added the tiered `depth` enum (`brief|standard|deep`) and the `## Competitor marketing` and
`## Customer personas` body sections; a schema-1 artifact has neither and its `depth` is the
old `triage|full` binary.
