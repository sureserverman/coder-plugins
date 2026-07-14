---
name: track
description: >
  Record a portfolio project's actual business metrics — GitHub stars, downloads, revenue, installs — and diff them against targets in business/metrics.md. Triggers on "track this project's metrics", "how are we doing vs targets", "update business actuals", "business check-in".
---

# track — record actuals, diff vs targets

Record what a project is *actually* doing and compare it against the targets `model` set.
Appends to `business/metrics.md`; never rewrites history.

**Announce at start:** "Using the business track skill to record <project>'s actuals."

## Determinism boundary

Read targets and current state via the scanner:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/business-scan.py
```

Collect free GitHub metrics via the collector (best-effort, never fails the run):

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/collect-github.py <repo_path>
```

Append to `metrics.md`, and bump `last_reviewed` in `BUSINESS.md` by `Read`-ing the
actual file and making a targeted edit (preserve `project:`, the rest of the frontmatter,
and the body — the scanner JSON omits `project` and the body). Conform to
`${CLAUDE_PLUGIN_ROOT}/references/metrics-format.md` and `business-md-format.md`.

## Precondition

The project must be `assessed: true` with a verdict that has targets — normally `monetize`
or `free-for-reputation` after `model` ran. If there are no `targets`, you can still
record actuals, but say there's nothing to diff against and suggest `/business:revenue-model`.

## Phase 1 — Auto-collect

Run `collect-github.py <repo_path>` for the project's repo. It returns `values`
(`github.stars`, `github.release_downloads`, `github.clones_14d`) and `reasons`. Two reason
shapes:

- **`reasons["_"]`** — a single whole-collection failure (no git remote, `gh` not
  authenticated, non-GitHub remote). When all three values are null, check `"_"` *first* —
  this is the most common case for a fresh project and explains everything at once.
- **`reasons["github.<metric>"]`** — a per-metric failure while others succeeded (e.g.
  `github.clones_14d` needs push access).

Record what came back; surface the reason(s) to the operator plainly — a null metric is
"couldn't collect" (with its reason), not zero.

## Phase 2 — Manual figures

Prompt for the metrics no collector can reach — revenue, installs from a store page,
donation totals, anything the project's targets reference that GitHub doesn't provide. Ask
only for metrics that matter to a target or that the operator wants tracked. Leave a
metric blank (→ null) rather than guessing.

### Marketing funnel (optional — offer once, skippable in one answer)

If the project markets to an audience (it has a `gtm-plan.md`, a landing page, or funnel
targets), offer to record this cycle's **marketing funnel** in one prompt — and let the
operator skip the whole block with a single "skip". Record only what they give; append
nothing for a metric they don't have. Use the conventional keys (metrics-format.md §
Conventional metric names) so the funnel diffs like any other target:

- `manual.visits` — unique visitors to the landing/store page this cycle
- `manual.signups` — new signups / accounts / waitlist joins this cycle
- `manual.conversion_pct` — visit→signup (or signup→paid) conversion rate, as a percentage
- `manual.cac_usd` — customer acquisition cost this cycle, in USD

These are conventions, not a schema change — any `<source>.<metric>` already parses. A
metric the operator can't measure this cycle is left blank (→ null), not guessed. Skip the
block entirely for a project with no marketing motion (an internal tool, a pure library).

## Phase 3 — Append the entry

Append one dated block to `metrics.md` (see metrics-format.md): a `## YYYY-MM-DD` heading
followed by `- <source>.<metric>: <value>` bullets, source-tagged `github.*`
(auto-collected) or `manual.*` (operator-entered), plus an optional `- note:`. **Never
edit or delete prior blocks** — the log is append-only; history is the audit trail.

## Phase 4 — Diff vs targets

For each target in `BUSINESS.md`, find its actual in the latest metrics block. **Match a
target's bare `metric` name to a metrics key by the suffix after the last `.`**: target
`installs` matches `manual.installs`; target `stars` matches `github.stars` (see
metrics-format.md § Target linkage). Then report the delta and whether it's on track for
the `by` date — e.g. "installs 900 / 1000 by 2026-12-31 — 90%, on track" or "mrr_usd 15 /
200 — 8%, behind". Be honest about metrics you couldn't collect ("clones unknown this
cycle — needs push access") and about targets with no matching metric yet ("no actual
recorded for `paid_setups`").

## Phase 5 — Bump the stamp and verify

Bump `last_reviewed: <today>` in `BUSINESS.md`. Run `business-scan.py` and confirm the
project's `metrics` shows the new dated block as latest, `last_reviewed_age_days` is 0, and
**zero `errors`**.

## Cadence

`track` is meant to run periodically (monthly is typical). The `compass` integration flags
a project whose `last_reviewed` is stale, so recording actuals keeps it off the review
agenda and keeps the target diffs meaningful.
