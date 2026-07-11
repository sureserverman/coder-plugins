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

| Project | Verdict | Model | Stage | Reviewed | Actuals |
|---------|---------|-------|-------|----------|---------|
| [[xray-host]] | monetize | paid | launched | 0d | 2026-07-11 (5) |
| [[bootstrapscripts]] | monetize | oss-services | tracked | 0d | 2026-07-11 (4) |
| [[text-vault]] | internal-only | — | assessed | 0d | — |

## Not yet assessed (M) — triage gap

- [[foo]], [[bar]], [[baz]]

## Couldn't assess (K)

- <name>: <reason>

## Errors

- [[project]]: <error string>
```

## Rules

- **Project** is a `[[wikilink]]` to the project name (vault convention).
- **Stage** is the pipeline stage, derived from what the scanner reports (highest reached):
  `tracked` (metrics present) > `launched` (gtm-plan present) > `modeled`
  (`monetization.model` set) > `assessed`. `park`/`internal-only` projects normally stop at
  `assessed`.
- **Reviewed** is `last_reviewed_age_days` as `<n>d`, or `—` if unknown.
- **Actuals** is the latest metrics block's date + the count of non-`note` metric values,
  or `—` if none.
- **Not yet assessed** lists projects the scanner returned with `assessed: false` — a
  triage gap, not an error; the whole point is to see what still needs a verdict.
- **Couldn't assess** and **Errors** sections appear only when non-empty (degrade loudly:
  a project that couldn't be assessed, or whose `BUSINESS.md` had parse/validation errors,
  is always surfaced, never silently dropped).
- Counts in the section headers (`Assessed (N)`) let a reader see coverage at a glance.
