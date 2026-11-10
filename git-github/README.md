# git-github

Everyday git/GitHub operations for Claude Code: dispatch a diff to sibling CLIs for multi-model second opinions, audit gates for faked verification, audit code comments for explanatory value, audit GitHub Actions workflows, sweep portfolio repo health, review READMEs, and cut release tags. Skills auto-trigger on natural language; nothing autoposts, force-pushes, or rewrites history.

## What it covers

| Skill | When it fires | What it does |
|---|---|---|
| `github-workflow-audit` | "audit my workflows", "check github actions" | Runs `scripts/validate-workflows.sh` (a wrapper over `audit-workflows.py`) over `.github/workflows/*` for YAML errors, expression injection, outdated action versions, missing `permissions:`, and more. |
| `review-readme` | "my readme is a mess", "clean up the README" | Audits the README against the house limits (at most 6 sections, at most 3 quick-start steps) and applies user-approved edits. README only shrinks. |
| `release-tag` | "tag a release", "cut v1.4.0" | Drafts an annotated-tag message from the top CHANGELOG entry (or commit log), confirms before tagging, confirms again before pushing, and optionally creates a GitHub release. |
| `request-external-reviews` | "get reviews from other tools", "second opinion on this diff", "multi-model review" | Dispatches the same diff to sibling CLIs (codex, gemini, opencode — plus claude when the caller is Cursor) in non-interactive read-only mode and aggregates findings with consensus marking. |
| `code-comment-audit` | "audit my comments", "are my comments useful", "review the comments in this file" | Disciplined comment pass: surfaces magic numbers, ordering constraints, workarounds, and un-introduced entry points where a concrete *why* exists; removes comments that just restate the code. |
| `gate-audit` | "audit the gates", "did these tests actually run", "this build looks suspiciously green", at a stage boundary, or when reviewing someone else's "all gates green" claim | Audits a repo or diff for **faked verification**: stubbed gates, tests that were never executed, fabricated evidence, and hidden exclusions (quarantined suites, skipped matrices, narrowed scopes that weren't disclosed). Dispatches `planning:code-reviewer` for the judgment calls rather than self-grading. The natural counterpart to `planning:honest-gates`, which defines what an honest gate *is* — this checks whether yours are. |
| `repo-health` | "check github health", "any failed workflows across my projects", "repo health sweep" | Runs the bundled `repo-health-scan.py` over every registry project with a GitHub remote: red default-branch workflows, open issues, stale PRs, Dependabot alerts. Report-first; findings the user picks are filed into per-project backlogs via `planning:backlog`, with URL-keyed dedup and zombie-entry detection on re-sweeps. |

All skills auto-trigger on the phrases above, and each is also invocable explicitly as `/git-github:<skill>`. There is no umbrella slash command — each skill stands alone.

### Which skills will never act on their own

Two skills touch shared state, and **none of them ever fires autonomously** — they trigger only on an explicit request from you, and then confirm before acting. Knowing which is which matters more than any other detail on this page:

| Skill | Never does | Confirms before |
|---|---|---|
| `release-tag` | force-push, delete or move an existing tag | tagging — **and again** before pushing |
| `repo-health` | write anything you didn't pick | filing each finding into a project backlog |

Everything else in the table is read-only or edits only local working files.

### Arguments and scope

Most skills take a scope argument; when omitted they scope sensibly and say what they chose.

```text
/git-github:gate-audit                  # the current branch's gates
/git-github:repo-health                 # sweep every registry project
/git-github:release-tag v1.4.0          # a specific version
```

### Artifacts

Most skills write nothing — findings come back in the conversation. The exceptions:

| Skill | Writes |
|---|---|
| `review-readme` | edits `README.md` in place — and **only ever shrinks it** |
| `code-comment-audit` | edits comments in the files you scoped |
| `release-tag` | an annotated tag |
| `repo-health` | backlog entries in **other projects'** registers via `planning:backlog`, for findings you pick — URL-keyed dedup, zombie detection on re-sweeps |

**Review reports are never committed.** `gate-audit` and `request-external-reviews` return findings in-conversation; any report file you save locally stays local, per the portfolio-wide rule that security and review report `.md` files are gitignored and never reach a remote.

## Code review

This plugin ships no reviewer of its own. For a single authoritative review, use Claude
Code's built-in `/code-review`. `gate-audit` and `planning:executing-plans` dispatch
`planning:code-reviewer` from the planning plugin; without planning installed, no reviewer
agent is available.

## Install

```
/plugin marketplace add sureserverman/coder-plugins
/plugin install git-github@coder-plugins
```

`gh` (GitHub CLI) is required for `repo-health` and the GitHub-release step of `release-tag`. The other skills work with plain `git`. `repo-health` additionally reads the projects registry `~/.claude/projects-registry.yaml` (maintained by vault-portfolio's `portfolio` skill) and files triaged findings through `planning:backlog` (report-only when the planning plugin is absent).

## Determinism boundary

Mechanical checks live in a deterministic bash lane (`scripts/`, vendored from the
plugin-dev determinism kit); judgment stays with the skills, which run the lane and consume
its JSON rather than re-deriving rules in prose. Scripts flag; the model decides.

- `scripts/validate-workflows.sh <repo-root> [--json]` — the GitHub Actions lane. A thin
  wrapper over `skills/github-workflow-audit/scripts/audit-workflows.py`; it re-implements no
  check, so the two can never drift apart.

Run the whole lane: `bash scripts/validate.sh <target-root> [--json]` — it discovers every
`validate-*.sh`, merges their findings, and prints one verdict. Rule ids and severities are
documented in [`scripts/README.md`](scripts/README.md).

## Worked example

```text
/plugin install git-github@coder-plugins

/git-github:gate-audit
```

Not "is this code good" but "did the verification actually happen".
Checks for stubbed gates, tests that never ran, and undisclosed exclusions.

```text
/git-github:release-tag v1.4.0
```

`release-tag` drafts an annotated-tag message from the top CHANGELOG entry, confirms before
tagging, and confirms **again** before pushing.

## Related plugins

- **`planning`** — ships `planning:code-reviewer`, which `executing-plans` uses for its two-tier review, with the
  plan's declared **review scope** deciding how much of each runs: per-stage at the gate (a
  Critical fails it) from tier `standard` up, one whole-plan-diff pass at `light`, and the
  per-task tier (a Critical blocks within the Red-Green budget) only at `high` or on a task
  annotated `Review: required`. `honest-gates` defines what a gate may claim; `gate-audit` checks whether yours do.
- **`release-promo`** — takes over after `release-tag`; this plugin deliberately does not draft
  announcements.

## Design rules

- **Never autonomous on shared state.** Every commit, push, PR open, tag, and release waits for an explicit "yes". The skills surface what they're about to do; you approve.
- **Never `--force`, never `--amend` on shared history, never `git add -A`.** Matches the global rules in `~/.claude/CLAUDE.md` and the Bash tool's git protocol.
- **Hands off promotion.** After cutting a release, this plugin points you at `release-promo` (`/promote-release`) — it does not draft announcement posts itself.

## License

MIT.
