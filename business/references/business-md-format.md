# BUSINESS.md format (schema 1)

`BUSINESS.md` is the **canonical, machine-readable index** of a project's business
case. It lives at `<vault_dir>/Portfolio/<area>/<project>/business/BUSINESS.md`.

**All machine-readable state lives in the YAML frontmatter.** The markdown body is
human rationale only — the scanner (`business-scan.py`, the sole parser) reads *only*
the frontmatter here (plus `metrics.md` and `gtm-plan.md` separately). Never encode a
fact the scanner needs in prose; if it isn't in the frontmatter, the scanner can't see it.

## Frontmatter schema

```yaml
---
schema: 1
project: <registry name, e.g. multitor-android>
verdict: monetize            # one of: monetize | free-for-reputation | internal-only | park
audience: <one line — who the end result is for>
evidence: local-only         # one of: local-only | researched
last_reviewed: 2026-07-11    # YYYY-MM-DD — the "Last reviewed" stamp, bumped by track/assess/revenue-model
monetization:
  model: null                # null until the model skill runs; then e.g.
                             # paid | freemium | donations | dual-license | oss-services | sponsorship
  pricing: null              # free-text hypothesis, e.g. "$3 one-time" or "$5/mo pro tier"
  channels: []               # e.g. [f-droid, play, amo, github-releases]
targets: []                  # numeric, dated goals — see below
---
```

### `verdict` (required, enum)

Exactly one of: `monetize` | `free-for-reputation` | `internal-only` | `park`.

- `monetize` — pursue revenue. Unlocks the `model` skill.
- `free-for-reputation` — ship free deliberately (reputation, portfolio, funnel). Unlocks `model` (channels/targets still matter).
- `internal-only` — for the operator's own use; no external launch. **Complete, valid end state.**
- `park` — not worth pursuing now. **Complete, valid end state.** The point of triage is permission to not pursue most projects.

The scanner rejects any other value for `verdict` as a malformed-file error.

### `evidence` (required, enum)

`researched` when a `--research` market pass grounded the verdict with citations;
`local-only` when the verdict rests only on repo/vault/operator input (lowers confidence — stated explicitly by `assess`).

### `last_reviewed` (required, date)

`YYYY-MM-DD`. The **Last reviewed** stamp. `assess`, `model`, and `track` bump it to
today whenever they touch the file. The scanner derives `last_reviewed_age_days`; the
compass integration flags staleness from it.

### `targets` (list)

Each target is numeric and dated so `track` can diff actuals against it:

```yaml
targets:
  - metric: installs        # free-text metric name
    target: 1000            # number
    by: 2026-12-31          # YYYY-MM-DD
  - metric: mrr_usd
    target: 200
    by: 2026-12-31
```

`business-scan.py` validates each target's shape: `metric` must be a non-empty string,
`target` must be numeric (a non-finite float is accepted here and nulled downstream), and
`by` must be a `YYYY-MM-DD` date. A malformed target produces a per-target scanner error
(`targets[i].<field> ...`) — never fatal; the project is still assessed and the error is
surfaced in the roll-up's Errors section.

## Body (human rationale — not parsed)

```markdown
# Business case: <project>

## Verdict — <verdict>
<why, in prose>

## Audience
<who, and why they'd care>

## Monetization
<the reasoning behind the model / pricing / channels>

## Evidence
<local-only note, or the cited market-researcher findings if --research ran>
```

## Schema versioning

`schema: 1` is required. The scanner treats an **unknown** (higher) schema version as an
explicit "newer schema — upgrade the business plugin" error, never a silent misparse.
Schema changes bump this integer and update `business-scan.py` in lockstep.
