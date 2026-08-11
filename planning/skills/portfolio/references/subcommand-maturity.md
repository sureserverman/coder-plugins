# `maturity` — the per-project audit, and the rollout window that gated it

The procedure behind `../SKILL.md` § `maturity` — audit per-project MATURITY.md and surface
staleness. In the default flow this is step 3, and it runs only when `--include-maturity` is
set. Axis semantics: `../references/maturity-axes.md`.

Inputs: optional `--project <abs-path>`, optional `--init-missing` (off by default; when set, projects with no MATURITY.md get `project-maturity init` invoked instead of skipped).

Operation:

1. Load the registry (enabled-only, optionally narrowed by `--project`).
2. For each project, dispatch a sub-agent (same 8-in-flight cap) that invokes the `project-maturity` skill's `audit` subcommand (with `--write`). The sub-agent additionally runs `get --format json` to obtain the parsed state for the roll-up.
3. Aggregate. Report:
   - Per-project audit summary lines.
   - List of stale manual claims (>90 days old) across all projects, with `project: axis: item: claim-date`.
   - List of projects with `[?] stale-detector` markers — these block ship-ready and warrant inspection.
4. Prompt the user to refresh/keep stale claims (per project).

`--init-missing` exists for the staged maturity rollout. Default behavior is to skip projects without a MATURITY.md so first-time portfolio runs aren't a hard prerequisite of "scaffold 30 maturity files at once."

## Why the default flow gates this step

Per the design doc's rollout step 4 (section 7): the `project-maturity` skill is shipped but excluded from the default `portfolio` flow for a staging window (~one week). During the staging window:

- `portfolio maturity` (explicit subcommand invocation) works normally.
- `portfolio` (default flow) skips the maturity step UNLESS `--include-maturity` is passed.

This prevents the default flow from dumping 30 unfilled checklist scaffolds in front of you on
day one. After the staging window, the description in `../SKILL.md` § Default flow (no
subcommand, or explicit `portfolio` invocation) is updated to drop the gate; `--include-maturity`
becomes a no-op.
