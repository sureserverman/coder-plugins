# global-business.md format

The portfolio-wide business roll-up, rendered by `business-rollup.py` from
`business-scan.py`'s JSON and written to `<vault_dir>/Portfolio/global-business.md`
(beside `global-backlog.md` / `global-maturity.md`). Machine-generated — never hand-edit;
`/business:biz-portfolio` (and `portfolio rebuild`) regenerate it.

## Structure

```markdown
# Global Business Roll-up
Generated: 2026-07-11

## Assessed (N)

| Project | Verdict | Model | Stage | Reviewed | Actuals | Plan | Research |
|---------|---------|-------|-------|----------|---------|------|----------|
| big-projects/[[xray-host]] | monetize | paid | launched | 0d | 2026-07-11 (5) | active | 4d |
| servers/[[bootstrapscripts]] | monetize | oss-services | tracked | 0d | 2026-07-11 (4) | draft | 30d |
| web/[[text-vault]] | internal-only | — | assessed | 0d | — | — | — |

## Not yet assessed (M) — triage gap

- foo-area/[[foo]], bar-area/[[bar]], baz-area/[[baz]]

## Couldn't assess (K)

- <name>: <reason>

## Errors (K)

- area/[[project]]: <error string>
- area/[[project]] (unassessed): <error string>
```

## Rules

- **Project** is an **area-qualified** wikilink `<area>/[[<name>]]` (matching
  `portfolio-rebuild.py`) — two projects in different areas may share a name slug, so the
  area prefix disambiguates. Free-text cells (name, model) have `|`/newlines escaped so a
  hostile value can't break the table.
- **Stage** is the pipeline stage, derived from what the scanner reports (highest reached):
  `tracked` (metrics present) > `launched` (gtm-plan present) > `modeled`
  (`monetization.model` set) > `assessed`. `park`/`internal-only` projects normally stop at
  `assessed`.
- **Reviewed** is `last_reviewed_age_days` as `<n>d`, or `—` if unknown.
- **Actuals** is the latest metrics block's date + the count of non-`note`, non-null metric
  values (a metric left blank or that failed numeric parse is `null` and does not count),
  or `—` if none.
- **Plan** reflects `plan.md`: the plan's `status` (`draft`/`active`) when one exists,
  `yes` when it exists but its `status` didn't parse, or `—` when there's no plan.
- **Research** reflects `market-research.md`: its age as `<n>d` when one exists (so a stale
  research pass is visible at a glance), `yes` when it exists but its date didn't parse, or
  `—` when there's none. Both columns are additive — a project scanned before this support,
  or without those artifacts, renders `—` and never breaks the table.
- **Not yet assessed** lists projects the scanner returned with `assessed: false` — a
  triage gap, not an error; the whole point is to see what still needs a verdict.
- **Couldn't assess** and **Errors** sections appear only when non-empty (degrade loudly:
  a project that couldn't be assessed, or whose `BUSINESS.md` had parse/validation errors,
  is always surfaced, never silently dropped). A project carrying `errors` is listed under
  **Errors** whether or not it is `assessed`; an unassessed-but-errored project is tagged
  `(unassessed)`.
- Counts in the section headers (`Assessed (N)`) let a reader see coverage at a glance.
