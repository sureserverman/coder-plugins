# competitor-table.yaml format (schema 1)

`competitor-table.yaml` is the **main working artifact** of a competitive analysis
(`competitive-analysis-method.md` § 7 — The table): competitors down, characteristics
across, every cell a quantity. It sits next to `market-research.md` at
`<vault_dir>/Portfolio/<area>/<project>/business/competitor-table.yaml` and is written
by the `/business:market-research` skill at `standard`+ from the `market-researcher`
agent's findings.

**Sole parser: `scripts/competitor-table.py`.** `business-scan.py` never opens this
file — the scanner reads `market-research.md`'s frontmatter, where the skill records the
row count (`competitors:`) and `coverage:`. Skills and the business-plan composer consume
the script's JSON, never the YAML directly. The script is read-only except for the SVG it
is explicitly asked to write with `--svg`.

## Top level

```yaml
schema: 1
project: xray-host          # registry name — mismatch with market-research.md is an error
updated: 2026-09-08         # YYYY-MM-DD
year: 2026                  # optional; the Y0 year for trajectories (default: updated's year)
self: xray-host             # optional; the row id that is THIS project, when it is plotted
center: median              # median | mean — the zero point of every axis (default median)
characteristics: [...]      # columns, see below
competitors: [...]          # rows, see below
```

## Characteristics (columns)

```yaml
characteristics:
  - id: revenue             # column key: [a-z0-9_]+, unique
    label: Revenue (USD/yr) # optional display label (default: id)
    category: company       # quantitative-product | qualitative-product | target-market | company
    type: number            # number | percentage | flag | score | categorical
    scale: log              # linear | log | auto (default auto: log when every value > 0
                            #   and max/min ≥ 100 — the "ratio between extremes" rule)
    invert: false           # true when "more" is not the contrast you want on this axis
    source: <free text>     # optional: how the column was collected
```

**Types and the conversion rule** — anything that can be a quantity is one:

| type | accepted cell values | stored as |
|---|---|---|
| `number` | int / float | float |
| `percentage` | `7`, `7.5`, `"7%"` | float, percent points |
| `flag` | `yes`/`no`, `true`/`false`, `1`/`0` | 1.0 / 0.0 |
| `score` | int / float (any range you declare in `label`) | float |
| `categorical` | a string | **expanded** into one `flag` column per observed value, keyed `<id>:<value>` (`color:green`), 1.0 where the row has that value, else 0.0 |

`null` / absent is a missing value: the row is skipped on any quadrant that uses that
column, and the skip is reported. A `log` axis with a non-positive value is an error
(declare `scale: linear` or fix the datum). A `categorical` column cannot be an axis
itself; its expanded `<id>:<value>` columns can.

Geography is entered as a **score** of business difficulty for where the team
actually sits, never a country name.

## Competitors (rows)

```yaml
competitors:
  - id: c1                  # [a-z0-9_-]+, unique
    name: Acme Compare      # display name
    class: direct           # direct | indirect  (non-consumption is not a row)
    group: suites           # optional; rows sharing a group are one homogeneous cluster
    found_by: customer-job  # category | customer-job | alternatives — which pass surfaced it
    source: https://…       # optional: the primary citation for the row
    values:                 # the Y0 state, keyed by characteristic id
      revenue: 200000
      headcount: 112
      geo_difficulty: 4
      self_service: yes
      color: green
    history:                # optional; prior-year states for trajectories (deep)
      2024: {revenue: 80000, headcount: 40}
      2025: {revenue: 150000, headcount: 75}
```

`history` keys are years strictly before `year`; each is a partial `values` map — only
the columns that changed need repeating, missing ones inherit nothing (they are missing
for that year). Two prior years (Y-2, Y-1) are the working norm; one is enough for a
vector, more are used as given.

## Normalization (what `normalize`, `quadrant`, `sweep`, `trajectory` compute)

Per numeric column, over the **Y0** values of every row that has one:

1. transform: identity for `linear`; `log10` for `log`;
2. centre `c` = median (default) or mean of the transformed values;
3. half-range `h` = max(|max − c|, |c − min|); a constant column has `h = 0` and scores 0
   everywhere;
4. score = 5 × (v − c) / h, so every axis spans **−5 … +5** with zero at the centre;
5. `invert: true` negates the score.

History values are projected onto the **same** centre and half-range as Y0, so a
trajectory is drawn on the map the current state defines.

Bubble radius is proportional to the square root of the `--size` column's raw value
(area ∝ value), clamped to a readable pixel range; distance is always measured between
centres.

## Sweep scoring (what `sweep` ranks)

For every ordered pair of distinct numeric axes, using the rows with both values:

- `spread` — mean pairwise distance between centres (contrast on the pair);
- `empty_quadrants` — how many of the four quadrants hold no row;
- `self_isolation` — distance from `self` to its nearest other row (only when `self` is
  set) — the point where you differ from everyone;
- `group_cohesion` — for each group, mean intra-group distance divided by `spread`;
  a group scoring above 1.0 on many pairs scatters more than the population and should be
  dissolved. Reported per group across the whole sweep.

Ranking: `self_isolation` desc when `self` is set, then `empty_quadrants` desc, then
`spread` desc. The ranking is a **starting order for the operator's own look**, not a
verdict: the method says intuition proposes, the sweep configures, and the operator
decides which pair shows the market and the strategy at once.

## Schema versioning

`schema: 1` is the only version. The script rejects a missing or non-integer `schema`, and
a value above 1 with an explicit "newer than supported — upgrade the business plugin"
error, never a silent misparse — the same discipline as every other business artifact.
