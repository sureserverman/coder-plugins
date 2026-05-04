---
name: create-commit
description: >
  Use when the user explicitly asks to create a git commit — "commit this",
  "commit these changes", "make a commit", "commit with message X", "stage
  and commit", "create a commit for the staged changes". Dispatches a Haiku
  subagent to inspect the working tree, draft a commit message that matches
  the repo's style, and create the commit. Does NOT push, amend, or skip
  hooks. Does NOT trigger on its own — only on an explicit user request.
---

# Create Commit (Haiku-powered)

Drafts and creates a git commit by dispatching a `general-purpose` subagent
pinned to Haiku. The mechanical work — `git status`, `git diff`, `git log`,
message drafting, the commit call — is cheap to do on Haiku and keeps Opus
context clear of raw diff and log output.

**Announce at start:** "Using the create-commit skill — dispatching a Haiku
agent to inspect the tree and create the commit."

## When NOT to use this skill

- The user did not explicitly ask for a commit. The global rule is to never
  commit without an explicit request; this skill never fires proactively.
- The user wants to amend, force-push, rebase, or rewrite history — those
  are destructive and need direct user-facing confirmation, not a delegated
  Haiku run.
- There are no changes (`git status` clean). Tell the user; do not dispatch.
- The user wants to push. This skill creates the commit only. Pushing is a
  separate, user-confirmed step.

## Preflight (run before dispatch)

1. **Verify a request exists.** The user must have asked. If unsure, ask.
2. **Confirm the repo state.** Run `git status` once locally to check there
   is something to commit and to spot obvious red flags (`.env`,
   `credentials.json`, large binaries, lockfiles the user did not edit).
   If anything looks risky, surface it to the user BEFORE dispatching.
3. **Capture the user's intent in one sentence.** The Haiku agent will not
   see this conversation. It needs to know *why* the change exists.
4. **Capture any user-supplied message or scope hint** verbatim. If the user
   said "commit with message 'fix: nil deref in handler'", pass that through
   exactly — do not let Haiku re-draft over a user-specified message.

## Dispatch template

```
Agent({
  description: "Create commit",
  subagent_type: "general-purpose",
  model: "haiku",
  prompt: """Create a single git commit in the current repo.

Intent (from the user, not derivable from the diff alone):
<one-sentence intent>

User-supplied message (use verbatim if non-empty, otherwise draft one):
<message or "(none — draft one)">

Constraints — follow strictly:
- Run `git status` (no -uall flag), `git diff` (staged + unstaged), and
  `git log -n 10 --oneline` in parallel to see state and match style.
- Stage files by name. Do NOT use `git add -A` or `git add .`.
- Do NOT stage files that look like secrets (.env, *.pem, credentials.*,
  id_rsa, *.key) or large binaries that were not already tracked. If you
  see one, stop and report it instead of committing.
- Write the message in the repo's existing style (check `git log`). Keep
  the subject under ~72 chars. Focus the body on *why*, not *what*.
- Append this trailer on its own line at the end of the message:
    Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
- Pass the message via a HEREDOC to `git commit -m "$(cat <<'EOF' ... EOF)"`.
- Do NOT use --amend, --no-verify, --no-gpg-sign, -i, or any flag that
  skips hooks or rewrites history.
- Do NOT push. Do NOT create branches. Do NOT touch git config.
- If a pre-commit hook fails, fix the underlying issue, re-stage, and make
  a NEW commit. Never --amend after a hook failure.
- After the commit, run `git status` and `git log -n 1` and report:
  the new commit SHA, the subject line, the files committed, and any
  hook output worth surfacing.

Return a short report: SHA, subject, file list, and anything the user
should know (hook warnings, files you refused to stage, etc.). Do not
narrate your shell session."""
})
```

## After the agent returns

1. **Surface the SHA, subject, and file list verbatim.** Do not paraphrase.
2. **Flag refusals.** If the agent declined to stage a file (suspected
   secret, unexpected binary), report that to the user and ask how to
   proceed — do not silently re-dispatch.
3. **Do not push.** If the user wants to push, that is a separate, explicit
   request.

## Why Haiku

Commit-message drafting is a pattern-matching task over the diff and recent
log. Haiku 4.5 handles it well, costs roughly an order of magnitude less
than Opus, and the work is bounded (a handful of git calls + one commit).
Keeping the raw diff and `git log` output out of the Opus context window
also leaves more room for the substantive work the user is actually doing.

## Reference

- **Conventional Commits** — https://www.conventionalcommits.org/ (only
  apply if the repo's existing log already follows it; don't impose a style
  the project doesn't use).
- **Pro Git, ch. 5.2 "Commit Guidelines"** —
  https://git-scm.com/book/en/v2/Distributed-Git-Contributing-to-a-Project
  (subject/body conventions the agent matches against).
- Global rule in `~/.claude/CLAUDE.md` and the Bash tool's git protocol:
  never commit without an explicit user request, never skip hooks, prefer
  new commits over `--amend`, never `git add -A`/`.`, never push without
  asking.
