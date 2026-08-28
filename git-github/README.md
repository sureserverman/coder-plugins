# git-github

Everyday git/GitHub operations for Claude Code: draft commits and PRs that match the repo's style, run a single-tool authoritative code review, dispatch the same diff to sibling CLIs for multi-model second opinions, audit code comments for explanatory value, audit GitHub Actions workflows, review READMEs, audit licenses, and cut release tags. Skills auto-trigger on natural language; nothing autoposts, force-pushes, or rewrites history.

## What it covers

| Skill | When it fires | What it does |
|---|---|---|
| `create-commit` | "commit this", "create a commit" | Dispatches a Haiku subagent to draft a message in the repo's style and run `git commit`. Never amends, never `git add -A`. |
| `create-pr` | "open a PR", "draft a pull request" | Detects the base branch, scopes the diff, drafts title + body matching recent merged PRs, then runs `gh pr create` (defaults to draft) after you confirm. |
| `github-workflow-audit` | "audit my workflows", "check github actions" | Runs the bundled `audit-workflows.py` over `.github/workflows/*` for YAML errors, expression injection, outdated action versions, missing `permissions:`, and more. |
| `license-audit` | "what license should this project use", "audit my licenses", "are my deps GPL-compatible" | Walks every dependency source (Dockerfile, manifests, vendored code), resolves SPDX licenses, applies copyleft-propagation rules per usage type, proposes compatible LICENSE options, and generates `LICENSE` after you pick one. |
| `review-readme` | "my readme is a mess", "clean up the README" | Audits the README against a 30-second-rule checklist and applies user-approved edits. README only shrinks. |
| `release-tag` | "tag a release", "cut v1.4.0" | Drafts an annotated-tag message from the top CHANGELOG entry (or commit log), confirms before tagging, confirms again before pushing, and optionally creates a GitHub release. |
| `code-review` | "review this", "review my implementation", "check this commit against the plan", "security review" | Scopes the diff (uncommitted / staged / commit / PR / plan-stage) and dispatches the `code-reviewer` subagent for a single-tool authoritative review. |
| `request-external-reviews` | "get reviews from other tools", "second opinion on this diff", "multi-model review" | Dispatches the same diff to sibling CLIs (codex, gemini, opencode — plus claude when the caller is Cursor) in non-interactive read-only mode and aggregates findings with consensus marking. |
| `code-comment-audit` | "audit my comments", "are my comments useful", "review the comments in this file" | Disciplined comment pass: surfaces magic numbers, ordering constraints, workarounds, and un-introduced entry points where a concrete *why* exists; removes comments that just restate the code. |
| `gate-audit` | "audit the gates", "did these tests actually run", "this build looks suspiciously green", at a stage boundary, or when reviewing someone else's "all gates green" claim | Audits a repo or diff for **faked verification**: stubbed gates, tests that were never executed, fabricated evidence, and hidden exclusions (quarantined suites, skipped matrices, narrowed scopes that weren't disclosed). Dispatches an independent reviewer for the judgment calls rather than self-grading. The natural counterpart to `planning:honest-gates`, which defines what an honest gate *is* — this checks whether yours are. |
| `repo-health` | "check github health", "any failed workflows across my projects", "repo health sweep" | Runs the bundled `repo-health-scan.py` over every registry project with a GitHub remote: red default-branch workflows, open issues, stale PRs, Dependabot alerts. Report-first; findings the user picks are filed into per-project backlogs via `planning:backlog`, with URL-keyed dedup and zombie-entry detection on re-sweeps. |

All skills auto-trigger on the phrases above, and each is also invocable explicitly as `/git-github:<skill>`. There is no umbrella slash command — each skill stands alone.

### Which skills will never act on their own

Four skills touch shared state, and **none of them ever fires autonomously** — they trigger only on an explicit request from you, and then confirm before acting. Knowing which is which matters more than any other detail on this page:

| Skill | Never does | Confirms before |
|---|---|---|
| `create-commit` | amend, `git add -A`, push | creating the commit |
| `create-pr` | push a branch you didn't ask to push | `gh pr create` (defaults to **draft**) |
| `release-tag` | force-push, delete or move an existing tag | tagging — **and again** before pushing |
| `repo-health` | write anything you didn't pick | filing each finding into a project backlog |

Everything else in the table is read-only or edits only local working files.

### Arguments and scope

Most skills take a scope argument; when omitted they scope sensibly and say what they chose.

```text
/git-github:code-review                 # your working diff (default)
/git-github:code-review HEAD~3          # a commit range
/git-github:code-review 412             # a PR number
/git-github:gate-audit                  # the current branch's gates
/git-github:repo-health                 # sweep every registry project
/git-github:release-tag v1.4.0          # a specific version
```

`code-review` accepts uncommitted / staged / commit / PR / plan-stage scopes; the plan-stage form is what `planning:executing-plans` uses at its gates.

### Artifacts

Most skills write nothing — findings come back in the conversation. The exceptions:

| Skill | Writes |
|---|---|
| `license-audit` | `LICENSE` (only after you pick from the proposed options) |
| `review-readme` | edits `README.md` in place — and **only ever shrinks it** |
| `code-comment-audit` | edits comments in the files you scoped |
| `create-commit` / `create-pr` / `release-tag` | git objects: a commit, a PR, an annotated tag |
| `repo-health` | backlog entries in **other projects'** registers via `planning:backlog`, for findings you pick — URL-keyed dedup, zombie detection on re-sweeps |

**Review reports are never committed.** `code-review`, `gate-audit`, and `request-external-reviews` return findings in-conversation; any report file you save locally stays local, per the portfolio-wide rule that security and review report `.md` files are gitignored and never reach a remote.

## Agent

| Agent | Model | Tools | Purpose |
|---|---|---|---|
| `code-reviewer` | sonnet | Read, Grep, Glob, Bash, WebFetch, TaskCreate, TaskUpdate | **Read-only** white-box reviewer — the term is defined once, in the agent's own `read-only-contract` block; this line names the property rather than restating it. Runs six protocols (context detection, plan-alignment, structural, Fowler code-smell, OWASP security, testability) and returns a **Critical / Important / Suggestion** triage with `file:line` citations and a Final Verdict. Reports findings — never edits, commits, or merges; the caller acts. |

The `code-review` skill dispatches this agent for an authoritative local review, and
the `planning` plugin's `executing-plans` consumes it for its two-tier review
(per-task quick review where a **Critical** blocks within the Red-Green budget, and a
per-stage deep review at the gate). Because it ships here, both consumers resolve it
as `git-github:code-reviewer` with no "if installed" fallback.

The agent body carries the protocols, the triage thresholds and the output contract;
the stable catalogs it cites — the SOLID/structural discriminators, the Fowler smell
vocabulary, the security checklist with its OWASP/CWE ids, the test-smell vocabulary and
the bibliography — live in
[`references/review-catalogs.md`](references/review-catalogs.md) and are read only when a
protocol calls for one. A given review needs at most one or two of them, so keeping them
out of the always-loaded body is what lets the agent stay a router rather than a rulebook.

## Install

```
/plugin marketplace add sureserverman/coder-plugins
/plugin install git-github@coder-plugins
```

`gh` (GitHub CLI) is required for `create-pr`, `repo-health`, and the GitHub-release step of `release-tag`. The other skills work with plain `git`. `repo-health` additionally reads the planning plugin's `~/.claude/projects-registry.yaml` and files triaged findings through `planning:backlog` (report-only when the planning plugin is absent).

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

/git-github:code-review
```

Scopes your working diff and dispatches the read-only `code-reviewer` agent, which returns a
Critical / Important / Suggestion triage with `file:line` citations and a Final Verdict. It reports
— it never edits, commits, or merges; acting on the findings is yours.

```text
/git-github:gate-audit
```

The complementary question: not "is this code good" but "did the verification actually happen".
Checks for stubbed gates, tests that never ran, and undisclosed exclusions.

```text
"commit this"
```

`create-commit` drafts a message in the repo's existing style via a Haiku subagent and shows it
before committing. It will not amend and will not `git add -A`.

```text
"open a PR"
/git-github:release-tag v1.4.0
```

`create-pr` reads recent merged PRs for tone, defaults to **draft**, and confirms first.
`release-tag` drafts an annotated-tag message from the top CHANGELOG entry, confirms before
tagging, and confirms **again** before pushing.

## Related plugins

- **`planning`** — `executing-plans` consumes `code-reviewer` for its two-tier review, with the
  plan's declared **review scope** deciding how much of each runs: per-stage at the gate (a
  Critical fails it) from tier `standard` up, one whole-plan-diff pass at `light`, and the
  per-task tier (a Critical blocks within the Red-Green budget) only at `high` or on a task
  annotated `Review: required`. `honest-gates` defines what a gate may claim; `gate-audit` checks whether yours do.
- **`testing`** — `testing-expert` reviews the *tests*; `code-reviewer` reviews the code. Distinct
  axes, both read-only.
- **`release-promo`** — takes over after `release-tag`; this plugin deliberately does not draft
  announcements.

## Design rules

- **Never autonomous on shared state.** Every commit, push, PR open, tag, and release waits for an explicit "yes". The skills surface what they're about to do; you approve.
- **Never `--force`, never `--amend` on shared history, never `git add -A`.** Matches the global rules in `~/.claude/CLAUDE.md` and the Bash tool's git protocol.
- **Haiku where it pays.** The mechanical drafting (commit messages, PR bodies) runs on Haiku via the host-provided `general-purpose` subagent — bounded work, ~10× cheaper, keeps raw diffs out of Opus context.
- **Hands off promotion.** After cutting a release, this plugin points you at `release-promo` (`/promote-release`) — it does not draft announcement posts itself.

## License

MIT.
