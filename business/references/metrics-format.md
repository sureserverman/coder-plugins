# metrics.md format

`metrics.md` is an **append-only** log of a project's actual business metrics. It lives
at `<vault_dir>/Portfolio/<area>/<project>/business/metrics.md`. The `track` skill appends
one dated block per review; nothing is ever edited or deleted (git history is the audit trail).

## Structure

```markdown
# Metrics: <project>

<!-- append-only — newest block at the bottom, one per `track` run. Never edit past blocks. -->

## 2026-07-11
- github.stars: 42
- github.release_downloads: 130
- github.clones_14d: 8
- manual.revenue_usd: 0
- manual.installs: 500
- note: first tracking pass; installs from F-Droid page

## 2026-08-11
- github.stars: 61
- github.release_downloads: 240
- manual.revenue_usd: 15
- manual.installs: 900
```

## Parse contract (what `business-scan.py` reads)

- Each dated block opens with a `## YYYY-MM-DD` heading.
- Following it, each `- <key>: <value>` bullet is one metric.
  - **key** is `<source>.<metric>` where source is `github` (auto-collected) or `manual` (operator-entered). Any other source label is allowed and carried through verbatim.
  - **value** is a number (int/float) or empty (unknown this cycle → the scanner records `null`).
    Non-finite floats (`inf`/`nan`) are rejected to `null` too, so the emitted JSON stays
    RFC-8259 valid for every consumer.
  - `- note: <free text>` is carried as a string, never diffed.
- The scanner takes the **last** dated block as "latest actuals" and exposes it in JSON;
  earlier blocks are history. A `## ` heading that isn't a `YYYY-MM-DD` date is treated as
  prose and ignored, so a stray section can't become the reported "latest" block. A
  malformed value (non-numeric, non-empty) on a non-`note` key is recorded as `null` and
  the block still parses.

## Target linkage

`BUSINESS.md` `targets[]` use **bare** metric names (`metric: installs`, `metric: stars`);
`metrics.md` keys are **source-prefixed** (`manual.installs`, `github.stars`). A target
matches a metrics key by the **suffix after the last `.`**: target `installs` matches
`manual.installs`; target `stars` matches `github.stars`.

When **more than one** source-prefixed key shares the same suffix (e.g. `manual.stars` and
`github.stars`, or a future `store.installs` alongside `manual.installs` for an `installs`
target), resolve to a single value by this **source precedence**, highest trust first:

1. `github.*` — auto-collected, highest trust.
2. `manual.*` — operator-entered.
3. any **other source** prefix, in ascending **alphabetical** order of the prefix
   (e.g. `apple.*` before `store.*`).

The winner is deterministic and the ambiguity is noted by `track` when it diffs.
`business-scan.py` does not link the two arrays — it returns `targets` and `metrics.values`
independently; the `track` skill applies this suffix-plus-precedence rule when diffing.

## Source tagging

Every metric is source-tagged via its key prefix so provenance is never ambiguous:
`github.*` came from `collect-github.py`; `manual.*` was entered by the operator during
the `track` run. A metric with no auto-collector is always `manual.*`.

## Conventional metric names — marketing funnel

The parse contract already accepts **any** `<source>.<metric>` key (see above), so these
need **no scanner change** — they are naming *conventions* so a project's funnel metrics
land under stable, diffable keys instead of ad-hoc ones. The `track` skill offers them as an
optional block; a project that isn't marketing-driven simply omits them.

| Key | Meaning |
|-----|---------|
| `manual.visits` | Unique visitors to the landing/store page this cycle |
| `manual.signups` | New signups / accounts / waitlist joins this cycle |
| `manual.conversion_pct` | Visit→signup (or signup→paid) conversion rate, as a percentage |
| `manual.cac_usd` | Customer acquisition cost this cycle, in USD |

These are `manual.*` (no auto-collector reaches an analytics dashboard). A `BUSINESS.md`
target can reference any of them by its bare suffix (`metric: signups` matches
`manual.signups`) exactly like `installs`/`stars`, so a funnel target diffs through the same
suffix-plus-precedence rule as any other. Leave a funnel metric blank (→ `null`) in a cycle
the operator didn't measure it — a null never counts toward actuals and never inflates a
diff. Other conventional prefixes (e.g. a future `plausible.*`/`store.*` analytics collector)
remain free to add later without a schema change.
