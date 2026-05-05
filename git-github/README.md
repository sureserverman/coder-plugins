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

All nine skills auto-trigger on the phrases above. There is no umbrella slash command — each skill stands alone.

## Install

```
/plugin marketplace add sureserverman/coder-plugins
/plugin install git-github@coder-plugins
```

`gh` (GitHub CLI) is required for `create-pr` and the GitHub-release step of `release-tag`. The other skills work with plain `git`.

## Design rules

- **Never autonomous on shared state.** Every commit, push, PR open, tag, and release waits for an explicit "yes". The skills surface what they're about to do; you approve.
- **Never `--force`, never `--amend` on shared history, never `git add -A`.** Matches the global rules in `~/.claude/CLAUDE.md` and the Bash tool's git protocol.
- **Haiku where it pays.** The mechanical drafting (commit messages, PR bodies) runs on Haiku via the host-provided `general-purpose` subagent — bounded work, ~10× cheaper, keeps raw diffs out of Opus context.
- **Hands off promotion.** After cutting a release, this plugin points you at `release-promo` (`/promote-release`) — it does not draft announcement posts itself.

## License

MIT.
