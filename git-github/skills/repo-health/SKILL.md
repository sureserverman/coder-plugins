---
name: repo-health
description: >
  Use to sweep every portfolio project's GitHub repo for failed workflows, open issues, stale PRs, and security alerts, then triage picked findings into per-project backlogs. Triggers on "check github health", "repo health sweep", "portfolio CI status". Report-first — writes only what the user picks.
---

# Repo Health — portfolio GitHub sweep

Answers one question across every registry project with a GitHub remote:
**what is rotting upstream?** Red CI on the default branch, open issues
nobody triaged, PRs idling past two weeks, and open Dependabot alerts —
gathered in one deterministic sweep, then *triaged by choice* into the
per-project backlogs. GitHub stays the source of truth; the backlog only
ever holds items the user explicitly filed.

**Announce at start:** "Using the repo-health skill for a portfolio GitHub sweep."

## Determinism boundary

All evidence comes from ONE run of the deterministic scanner:

```
python3 ${CLAUDE_PLUGIN_ROOT}/skills/repo-health/scripts/repo-health-scan.py [--project NAME]... [--stale-days N]
```

It walks `~/.claude/projects-registry.yaml` (enabled projects), resolves each
GitHub remote, and emits one JSON document: per project, latest workflow-run
conclusion per workflow on the default branch (`ci`), open issues with ages
and labels (`issues`), open PRs idle ≥ `stale_pr_days` (`prs.stale`), open
Dependabot alerts by severity (`security`), plus `backlog_zombies` — BL
entries whose linked GitHub item has since closed. Findings whose URL is
already filed in the project's backlog carry `triaged_as: "BL-NNN"`.
Projects without a GitHub remote land in `no_remote`; unassessable ones in
`couldnt_assess`. This skill's job is **judgment only**: severity ranking,
narration, and the triage conversation. Never re-derive facts the JSON
already carries; never present a fact the JSON doesn't back.

`--project` scopes a re-sweep to the projects being triaged; `--stale-days`
tunes the PR staleness window (default 14).

## Hard rules

- **Report first, write only on explicit pick.** The sweep itself is
  read-only. A backlog entry is created only after the user selects a
  specific finding in the triage step — never auto-file, never bulk-file
  "everything red".
- **All backlog writes go through the backlog skill.** Filing uses
  `planning:backlog` `add` (vault-resolved `<portfolio_home>/backlog.md`,
  BL-NNN ID rules, required fields). If the planning plugin is absent,
  repo-health is report-only: say so and stop after the report.
- **Never mirror GitHub wholesale.** An open issue is not backlog debt until
  the user decides it is. Findings already carrying `triaged_as` are shown
  as triaged, not re-offered.
- **Every line cites its evidence** — workflow name + conclusion + run URL,
  issue number + age, PR idle days, alert severity count. No vibes.
- **Degrade loudly.** Per-lane `error` fields (e.g. Dependabot alerts
  disabled, token scope missing), `no_remote`, and `couldnt_assess` all
  appear in a **"Couldn't assess"** footer on every report. Silence is
  never coverage.

## The report — health board

Order projects by severity: red CI first, then open security alerts, then
oldest untriaged issue, then stale PRs. Per project, one block:

- **CI** — each workflow whose latest default-branch run concluded
  red (`failure`, `timed_out`, `startup_failure`, `action_required`), with
  the run URL. A workflow still `in_progress` is noted, not judged.
- **Issues** — open count; list the untriaged ones (number, title, age).
  Ones with `triaged_as` are summarized as "N already in backlog".
- **Stale PRs** — number, title, idle days, draft flag.
- **Security** — open Dependabot alerts by severity.
- **Zombie BL entries** — from `backlog_zombies`: "BL-014 links
  issue #12, closed upstream — remove it?" (removal also goes through the
  backlog skill, only on user confirmation).

Green-and-quiet projects get one collapsed line ("12 repos healthy: …").
End with the Couldn't-assess footer, always.

## The triage step

After the report, offer triage: the user picks findings (by project +
item), and each pick becomes one `planning:backlog` `add` with:

- **Title:** short imperative restatement (e.g. "Fix red release workflow").
- **Source:** `github — <canonical URL of the run/issue/PR/alert>`.
  The URL is the dedup key: the next sweep's cross-check matches on it,
  so keep exactly one canonical GitHub URL in the entry.
- **Reason:** why it's deferred rather than fixed now (ask if unclear).
- **Next step:** concrete (e.g. "re-run with debug logging", "reproduce
  locally then plan").
- **Tags:** one of `gh-ci`, `gh-issue`, `gh-pr`, `gh-security`, plus any
  project-specific tags.

A red workflow the user wants fixed *now* is not backlog material — point
at `github-workflow-audit` (same plugin) for the fix and skip filing.

## Integration

- **planning:backlog** — owns the file format, ID rules, and the vault
  resolver; every write routes there. Absent → report-only mode.
- **planning:portfolio** — maintains the registry the scanner walks;
  registry problems ("portfolio not configured") route to its first-run
  setup, verbatim, never half-answered.
- **planning:compass** — the periodic what-to-work-on sweep; repo-health is
  the upstream-facing complement. A `compass review` that surfaces stale
  projects pairs well with a repo-health sweep of the same names.
- **github-workflow-audit** — the fix lane for a red workflow surfaced
  here; repo-health finds, workflow-audit repairs.

## Remember

- One scanner run per invocation; judgment on top; writes only via the
  backlog skill, only on explicit user picks.
- GitHub is the source of truth — the backlog holds decisions, not mirrors.
- URL in `Source:` is the contract that keeps re-sweeps idempotent.
- Footer every gap: lane errors, no-remote, couldn't-assess.
