# Changelog

All notable changes to the `business` plugin are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] - 2026-08-28

### Changed
- `market-researcher` carries the canonical **reference-resolution contract** — it must
  confirm each resolved reference *exists* rather than only that
  `${CLAUDE_PLUGIN_ROOT}` is set (a superseded cache resolves to a directory that exists
  with the file missing), fall back versioned-cache-then-dev-checkout saying which arm it
  used, and open with `DEGRADED RESEARCH — <references>` as its **first line** whenever a
  named reference went unread. A closing caveat is not enough: a degraded run and a
  complete one are otherwise identical in shape. Honors DEC-009; enforced by
  `scripts/check-agent-references.py`.
- `business-scan.py` has defined behavior when `vault_dir` is set but missing, rather
  than treating it as unset (Stage 4).

### Removed
- `market-researcher`'s `Bash` grant. The agent's own prose said "you have no Write/Edit
  tool by design" while an unrestricted `Bash` could write files, and the agent documented
  no `Bash` use anywhere. The grant is gone rather than the claim softened. Note that
  scoped `Bash(cmd:*)` grants were measured **not enforced** on at least one host, so a
  removed grant is a stronger guarantee than a narrowed one.

## [0.6.3] - 2026-08-12

### Changed
- `market-researcher` carries a deliberate `effort: medium` pin alongside its existing
  `model: sonnet`, and its reference path is `${CLAUDE_PLUGIN_ROOT}`-rooted rather than
  relative (a dispatched agent's cwd is the repo under review, so the relative form
  resolved nowhere). It also now discloses in its report when a reference or a cited
  source could not be read — a sweep that silently skipped its format spec and one that
  followed it return the same shape, so the disclosure is the only thing that tells them
  apart. Honors DEC-009.

## [0.6.2] - 2026-07-28

### Changed
- Version bump only, as part of the marketplace-wide `ui-*` retirement and
  context-engineering release (`a34724c`). No change to this plugin's own behavior.

## [0.6.1] - 2026-07-25

### Changed
- Version bump only, as part of the decisions-aware execution + full-usage docs release
  (`a8a0303`). No change to this plugin's own behavior.

## [0.6.0] - 2026-07-25

### Added
- **Business project groups.** Several registry projects can now form one business
  project via a vault manifest at `Portfolio/business-groups/<slug>/group.md`
  (`references/group-format.md`), with the group's business artifacts beside it. The
  scanner emits one entry per group (`group: true`, `members`) and suppresses grouped
  members' own rows; `global-business.md` renders a group as a single row naming every
  member; `compass-scan.py` attaches the group's state to each member tagged with
  `group: <slug>`. `assess` creates groups, `track` collects per member and sums into
  aggregate keys, `launch` gates on the weakest member's `MATURITY.md`.
  Membership deliberately does **not** live in `~/.claude/projects-registry.yaml` —
  eight independent consumers parse it with a fixed field set.
- **Per-member metric breakdown.** A `metrics.md` key containing `@` (e.g.
  `github.stars@big-projects/xray-host`) parses into a new `breakdown` block, never into
  `values`, so it is never target-matched and never counted as an actual. Without this the
  suffix-after-last-`.` target rule would make every member's key claim the same target and
  silently discard all but one.

### Fixed
- **BL-012: `metrics.md` allowed only one `- note:` per block.** A block may now carry a
  note per degraded metric and all are retained in a new `notes` list. One `track` cycle
  can degrade several metrics at once — a private npm package nulls all three `npm.*` keys
  while a missing push token separately kills `github.clones_14d` — and the single-string
  note kept only the last reason, exactly in the runs where per-metric provenance matters
  most. `values["note"]` still carries the last note for consumers written against the old
  contract.
- The roll-up's sort key used `x.get("area", "")`, but a group entry carries `area`
  present-and-`None` and a dict default only applies to a *missing* key — sorting a group
  beside a project raised `TypeError`. Would have crashed the first real group sweep.

## [0.5.0] - 2026-07-25

### Added
- **Per-channel metric collectors (BL-002).** `scripts/collect-npm.py` (`npm.downloads_last_week`,
  `npm.downloads_last_month`, `npm.versions` — accepts a package name or a repo path with a
  `package.json`) and `scripts/collect-amo.py` (`amo.daily_users`, `amo.downloads_last_week`,
  `amo.rating_count`, `amo.rating_average` — accepts a slug, numeric id, or GUID). Both public
  and unauthenticated. `track` runs them alongside `collect-github.py` and folds their values
  into `metrics.md` under their own `<channel>.*` keys. Play and donation platforms are
  deliberately deferred: both need per-project credentials rather than a public read.
- **`references/collector-contract.md`** — the contract every collector must meet, extracted
  from `collect-github.py`: one JSON document on stdout, `values` always carrying every known
  metric key (null when uncollected), degrade-to-null-plus-reason, **exit 0 even when nothing
  collected**, non-zero only on a usage error, secret redaction, and the `<channel>.<metric>`
  namespace. Includes the test checklist a new collector must satisfy.
- **`scripts/_collector.py`** — shared best-effort HTTP, reason accumulation, redaction, and
  document emission, so a new channel is mechanical. `collect-github.py` is deliberately not
  retrofitted onto it (it has a passing suite and no behavior to gain).

### Changed
- **`track` Phase 2 no longer prompts for metrics a collector now reaches**, and a
  hand-supplied figure covering a degraded collector is recorded under `manual.<suffix>` —
  never the collector's own `<channel>.*` key — so the prefix stays an honest provenance record.

### Fixed
- **Null metrics can no longer be masked by source precedence** (`references/metrics-format.md`):
  a key whose value is null this cycle is skipped *before* precedence ranking. Previously a
  degraded `github.clones_14d` (rank 1) outranked a populated `manual.clones_14d`, so the diff
  reported "unknown" for the very figure the operator supplied to cover the failure.

## [0.4.0] - 2026-07-15

### Added
- **Operator-selected depth tiers (`brief` | `standard` | `deep`)** for
  `/business:market-research` and `/business:business-plan`. Each skill asks the tier up
  front and scales effort and output to it; the tier is recorded in the artifact frontmatter
  (**schema 2**). `market-research.md` and `plan.md` moved to schema 2 — schema 1 artifacts
  still parse (legacy `market-research` depth `triage`≈`brief`, `full`≈`deep`; legacy plans
  have no depth). `business-scan.py` now enforces **per-artifact schema ceilings** and
  validates `depth` against each file's own schema, and exposes `plan.depth`.
- **Competitor-marketing research.** The `market-researcher` agent and `market-research.md`
  gained (at `standard`/`deep`) a **Competitor marketing** section — channels, campaigns
  cited to ad-transparency libraries, detected tooling, messaging/keywords — and a
  **Customer personas** section (1 at standard, 2–3 at deep), same cite-or-evidenced-absence
  discipline.
- **Elaborated business plan (twelve sections).** `plan.md` adds **Customer personas** and
  **SWOT & positioning** (a SWOT grid + one-sentence positioning statement) and an expanded,
  competitor-marketing-informed **Marketing & sales** playbook. `business-plan` reuses
  research only when its effective depth is `standard`+.
- **Questions-first.** `assess`, `market-research`, and `business-plan` now confirm inferred
  facts (audience, geography, substitutes, willingness-to-pay, competitor seeds, scenario
  assumptions) one question at a time instead of silently assuming them.
- **Marketing funnel metrics.** `track` offers an optional, one-answer-skippable funnel block;
  `manual.visits`/`signups`/`conversion_pct`/`cac_usd` are documented conventions (the
  `<source>.<metric>` parse contract already accepts them — no scanner change).
- **Staleness flags.** `global-business.md` marks the Plan/Research cells `STALE` when the
  artifact is strictly `> 90` days old; `biz-portfolio` reports the three staleness axes, and
  the planning `compass` skill nags on stale research/plans (its business object gained
  `research_age_days`/`plan_age_days`).

### Fixed
- De-duplicated the light-frontmatter parse/scan stanzas in `business-scan.py` (shared
  `_project_mismatch` / `_date_or_null` / `_scan_light_artifact` helpers; closes BL-005).

## [0.3.0] - 2026-07-12

### Added
- **`market-research` skill** (`/business:market-research`) — a standalone deep,
  cited market pass. Dispatches the `market-researcher` agent at `depth: full`
  (competitors, pricing, TAM/SAM/SOM sizing, trends, positioning gaps, channel
  norms, demand) and persists the result to `business/market-research.md`.
  Refreshes rather than clobbers on re-run, and writes **nothing** when WebSearch
  is unavailable (a half-cited report is worse than none).
- **`business-plan` skill** (`/business:business-plan`) — composes the `assess`
  verdict, the `revenue-model` monetization decision, the `market-research.md`
  evidence, and the live `gtm-plan.md`/`metrics.md` state, plus a short gap
  interview, into a full ten-section `business/plan.md` (executive summary through
  financial scenarios, risks, milestones). Offers missing prerequisites instead of
  fabricating them; links to `gtm-plan.md`/`metrics.md` rather than duplicating
  their numbers; marks the market analysis UNRESEARCHED when no research exists.
- **`market-researcher` agent** gained a `depth` parameter — `triage` (the `assess`
  default, unchanged) and `full` (adds market sizing, trends, positioning gaps).
- **`market-research.md` and `plan.md` formats** (schema 1) — `references/`
  specs, parsed by `business-scan.py`, which now emits per-project
  `research: {exists, date, age_days, depth, confidence}` and
  `plan: {exists, date, age_days, status}` blocks. The roll-up
  (`global-business.md`) gains **Plan** and **Research** columns. All additive:
  a project without the new artifacts scans/renders cleanly with zero new errors.

### Changed
- `assess --research` now reuses a fresh `market-research.md` (age ≤ 90 days) from
  the scanner JSON instead of always re-dispatching; stale or missing dispatches
  the agent at `depth: triage`. The interview phases are unchanged.
- Synced the marketplace catalog's `business` entry to the current version and
  skill set (it had drifted to 0.1.0 with the pre-rename `model` name).

## [0.2.0] - 2026-07-12

### Changed
- Renamed the `model` skill to `revenue-model` (`/business:model` →
  `/business:revenue-model`). The old name collided with Claude Code's built-in
  `/model` command in fuzzy command autocomplete, surfacing the skill whenever a
  user started typing `/model` to switch Claude's default model. Cross-references
  in `assess`, `launch`, and `track`, plus the README and format docs, were
  updated to the new command name. The `monetization.model` JSON field and
  BUSINESS.md's `model` section are unchanged.

## [0.1.0]

### Added
- Initial release: `assess`, `model`, `launch`, `track`, and `biz-portfolio`
  skills over a deterministic `business-scan.py` evidence lane.
