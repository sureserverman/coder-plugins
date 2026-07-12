# Changelog

All notable changes to the `business` plugin are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
