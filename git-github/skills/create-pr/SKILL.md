---
name: create-pr
description: >
  Use when the user explicitly asks to open a GitHub pull request — "open
  a PR", "create a pull request", "draft a PR for this branch", "gh pr
  create", "send this branch up for review". Dispatches a Haiku subagent to
  scope the branch diff, draft a PR title and body in the repo's style, and
  call `gh pr create` after the user confirms. Does NOT push to a base
  branch, does NOT mark PRs ready when the user asked for a draft, does
  NOT trigger on its own — only on an explicit user request.
---

# Create PR (Haiku-powered)

Drafts and opens a GitHub pull request by dispatching a `general-purpose`
subagent pinned to Haiku. The mechanical work — `git status`, `git log
<base>..HEAD`, `git diff <base>...HEAD`, optional `git push`, the
`gh pr create` call — is cheap on Haiku and keeps Opus context clear of
raw diff and log output.

**Announce at start:** "Using the create-pr skill — dispatching a Haiku
agent to scope the branch and open the PR."

## When NOT to use this skill

- The user did not explicitly ask for a PR. The global rule is to never
  push or open PRs without an explicit request; this skill never fires
  proactively.
- The remote isn't on github.com (e.g. GitLab, Gitea, Codeberg). `gh` only
  speaks GitHub. Detect via `git remote get-url origin` — if the host
  isn't `github.com`, stop and tell the user.
- The branch has no commits ahead of base. Tell the user; do not dispatch.
- The user wants to push to the base branch directly, force-push, or
  rewrite history. Those need direct user-facing confirmation, not a
  delegated Haiku run.

## Preflight (run before dispatch)

1. **Verify a request exists.** The user must have asked. If unsure, ask.
2. **Verify `gh` is on PATH.** If not, tell the user how to install it
   (`brew install gh`, `apt install gh`, etc.) and stop.
3. **Detect the base branch.** Try in order: the repo's default via
   `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`, then
   fall back to `origin/HEAD` symbolic-ref, then `main`, then `master`.
4. **Confirm branch state.** Run `git status --short`, `git rev-list
   --left-right --count <base>...HEAD`, and `git remote get-url origin`
   once locally. Surface to the user before dispatching:
   - branch name and base
   - commits ahead / behind
   - whether the working tree is clean
   - whether the branch is already pushed (`git rev-parse --abbrev-ref
     --symbolic-full-name @{u}` succeeds)
5. **Capture the user's intent in one sentence.** The Haiku agent will not
   see this conversation. It needs to know *why* the change exists.
6. **Capture any user-supplied title or hint** verbatim. If the user said
   "open a PR titled 'fix: nil deref in handler'", pass that through
   exactly — do not let Haiku re-draft over a user-specified title.
7. **Decide draft vs ready.** Default to **draft** unless the user said
   otherwise; opening as draft is reversible, opening as ready is
   socially heavier to undo.

## Dispatch template

```
Agent({
  description: "Create PR",
  subagent_type: "general-purpose",
  model: "haiku",
  prompt: """Open a single GitHub pull request for the current branch.

Intent (from the user, not derivable from the diff alone):
<one-sentence intent>

User-supplied title (use verbatim if non-empty, otherwise draft one):
<title or "(none — draft one)">

Base branch: <base>
Draft mode: <true|false>

Constraints — follow strictly:
- Run these in parallel to scope the change:
    git status --short
    git log --oneline <base>..HEAD
    git diff --stat <base>...HEAD
    git diff <base>...HEAD
  and (for tone-matching) read the most recent merged PR via
    gh pr list --state merged --limit 5 --json title,body
- If the local branch is unpushed or behind its remote tracking branch,
  run `git push -u origin HEAD`. Do NOT use --force, --force-with-lease,
  or any rewrite. If push fails because the branch diverged, STOP and
  report — never force.
- Do NOT push to the base branch. Do NOT touch other branches.
- Draft the PR title (≤72 chars) in the repo's existing style — check
  recent merged PRs for prefix conventions (Conventional Commits, ticket
  IDs, etc.). Do NOT impose a style the project doesn't use.
- Draft the body with these sections (only include the ones that have
  real content):
    ## Summary
    1–3 bullets on what changed and why.
    ## Test plan
    bullet checklist of how to verify; mark items already done with [x].
- Append this trailer on its own line at the end of the body:
    Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
- Open the PR with:
    gh pr create --base "<base>" --head "<current-branch>" \\
      <--draft if draft mode> \\
      --title "<title>" \\
      --body "$(cat <<'EOF'
<body>
EOF
)"
- Do NOT pass --fill (it overrides the drafted body).
- Do NOT mark the PR ready (`gh pr ready`) — leave that to the user.
- Do NOT request reviewers, add labels, or assign — that's a follow-up
  action the user hasn't asked for.

After the call, run:
    gh pr view --json number,url,title,isDraft,baseRefName,headRefName
and report: PR number, URL, title, draft status, base, head, and the
files included.

Return a short report. Do not narrate your shell session."""
})
```

## After the agent returns

1. **Surface the PR URL, number, and title verbatim.** Do not paraphrase.
2. **Flag refusals.** If the agent declined to push (diverged branch,
   force required, suspected secret in diff), report that to the user and
   ask how to proceed — do not silently re-dispatch.
3. **Suggest follow-ups but don't run them.** Examples: "want me to mark
   it ready?", "want me to request reviewers?", "want me to run
   `code-review` on the diff before review starts?". Each is a separate
   user-confirmed action.

## Why Haiku

PR title/body drafting is a pattern-matching task over the branch diff
and recent merged PRs. Haiku 4.5 handles it well, costs roughly an order
of magnitude less than Opus, and the work is bounded (a handful of git +
`gh` calls). Keeping the raw diff and PR-body output out of Opus context
also leaves more room for the substantive work the user is doing.

## Reference

- **GitHub CLI manual** — https://cli.github.com/manual/gh_pr_create
  (flags, defaults, `--draft` vs ready behavior).
- **Conventional Commits** — https://www.conventionalcommits.org/ (only
  apply if the repo's recent merged PRs already follow it; don't impose
  a style the project doesn't use).
- **Google Code Review Developer Guide — CL descriptions** —
  https://google.github.io/eng-practices/review/developer/cl-descriptions.html
  (subject + body conventions the agent matches against).
- Global rule in `~/.claude/CLAUDE.md` and the Bash tool's git protocol:
  never push without asking, never `--force`, never amend or rewrite
  shared history, always confirm before opening PRs or other shared
  state.
