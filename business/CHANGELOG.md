# Changelog

All notable changes to the `business` plugin are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
