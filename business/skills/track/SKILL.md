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

Collect free metrics via the per-channel collectors (best-effort, never fail the run —
all three honor `references/collector-contract.md`):

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/collect-github.py <repo_path>
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/collect-npm.py <package-name-or-repo-path>
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/collect-amo.py <addon-slug-id-or-guid>
```

`collect-github.py` **always runs** — every project has a source repo, and stars/clones are
meaningful regardless of how it distributes. `collect-npm.py` and `collect-amo.py` are
conditional: run one only when the project actually ships on that channel, since running it
otherwise wastes a call and produces nulls that mean nothing.

Append to `metrics.md`, and bump `last_reviewed` in `BUSINESS.md` by `Read`-ing the
actual file and making a targeted edit (preserve `project:`, the rest of the frontmatter,
and the body — the scanner JSON omits `project` and the body). Conform to
`${CLAUDE_PLUGIN_ROOT}/references/metrics-format.md` and `business-md-format.md`.

## Precondition

The project must be `assessed: true` with a verdict that has targets — normally `monetize`
or `free-for-reputation` after `model` ran. If there are no `targets`, you can still
record actuals, but say there's nothing to diff against and suggest `/business:revenue-model`.

## Phase 1 — Auto-collect

Always run `collect-github.py`. For the other two, decide from evidence, not familiarity —
**check `monetization.channels` in the scan JSON you already fetched** (`business-scan.py`
exposes it; `business-md-format.md` documents it, e.g. `[f-droid, play, amo,
github-releases]`). An `amo` entry means run `collect-amo.py`; an `npm` entry means run
`collect-npm.py`. When the field is empty or unset, fall back to a concrete check — a
`package.json` in the repo (which `collect-npm.py` will read itself) or a known AMO listing
— and if neither is evident, skip the collector rather than guessing at an id.

Every collector emits the same document shape — `values` plus `reasons` — so they are read
identically:

| Channel | Collector | Target | Metrics |
|---|---|---|---|
| GitHub | `collect-github.py` | repo path | `github.stars`, `github.release_downloads`, `github.clones_14d` |
| npm | `collect-npm.py` | package name, or a repo path with a `package.json` (a private package, or a manifest with no `name`, degrades with a reason) | `npm.downloads_last_week`, `npm.downloads_last_month`, `npm.versions` |
| AMO | `collect-amo.py` | addon slug, numeric id, or GUID | `amo.daily_users`, `amo.downloads_last_week`, `amo.rating_count`, `amo.rating_average` |

Two reason shapes, in every collector:

- **`reasons["_"]`** — a single whole-collection failure, raised **before any request goes
  out**: no git remote or `gh` not authenticated (github); a target that isn't a resolvable
  package — empty, malformed name, missing/unreadable/private `package.json` (npm); an id
  that isn't a legal AMO id, or the addon lookup failing outright (amo).
- **`reasons["<channel>.<metric>"]`** — a per-metric failure (e.g. `github.clones_14d` needs
  push access; `amo.rating_count` is absent on an addon nobody has rated yet).

When all of a channel's values are null, check `"_"` first — but **do not assume it is
there.** A collector that issues one request per metric reports a shared failure once per
metric rather than under `"_"`: an unknown npm package or an unreachable registry nulls all
three `npm.*` metrics with three per-metric reasons and no `"_"` at all. If `"_"` is absent,
read the per-metric reasons — they will say the same thing three times, and that repetition
is the whole-collection signal.

Record what came back; surface the reason(s) to the operator plainly — **a null metric is
"couldn't collect" (with its reason), never zero.** A collector exiting 0 does not mean it
collected anything: check `values`, not the exit code. Never substitute 0 for a null, and
never re-run a collector hoping for a number — if it degraded, report why.

## Phase 2 — Manual figures

Prompt for the metrics **no collector can reach** — revenue, donation totals, Play Store
installs, F-Droid figures, anything the project's targets reference that no collector
above provides. Ask only for metrics that matter to a target or that the operator wants
tracked. Leave a metric blank (→ null) rather than guessing.

**Do not prompt for a metric a collector already covers.** npm downloads and AMO
users/downloads/ratings are collected in Phase 1 — asking for them wastes the operator's
time and invites a hand-typed number that silently disagrees with the API. The one
exception: a collector that *degraded* leaves a genuine gap, so if its reason shows the
metric is unreachable for this project (not merely a transient network failure, which
should be retried instead), you may ask for it. **Record that answer under
`manual.<metric-suffix>`, never under the collector's own `<channel>.*` key** — e.g. a
hand-supplied weekly npm figure is `manual.downloads_last_week`, not
`npm.downloads_last_week`. The key prefix is the provenance record: filing an operator's
estimate under an auto-collector's namespace makes a typed number indistinguishable from an
API-verified one, which is precisely the confusion the collectors exist to remove. The
suffix-plus-precedence rule still diffs it against the same target.

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
followed by `- <source>.<metric>: <value>` bullets, source-tagged `github.*`, `npm.*` or
`amo.*` (auto-collected — write each collector's `values` under its own `<channel>.*` keys,
verbatim) or `manual.*` (operator-entered), plus an optional `- note:`. A metric a collector
could not reach is written with an **empty value** (→ null), never `0`, with its reason in
the `- note:`. **Never edit or delete prior blocks** — the log is append-only; history is
the audit trail.

## Phase 4 — Diff vs targets

For each target in `BUSINESS.md`, find its actual in the latest metrics block. **Match a
target's bare `metric` name to a metrics key by the suffix after the last `.`**: target
`installs` matches `manual.installs`; target `stars` matches `github.stars` (see
metrics-format.md § Target linkage). When several prefixes share a suffix, apply that
section's precedence — and **skip null keys before ranking**: a degraded `github.clones_14d`
must not outrank a `manual.clones_14d` the operator supplied precisely because the collector
failed. Then report the delta and whether it's on track for
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
