---
name: code-review
description: >
  Use when the user asks to review code, audit a diff, check a commit, or
  review a PR/branch before merge. Triggers: "review this", "code review
  please", "review my implementation", "check this commit against the plan",
  "security review". Scopes the diff (uncommitted / staged / commit / PR /
  plan-stage), dispatches the code-reviewer subagent, and surfaces the
  triage. For multi-model second opinions, use request-external-reviews.
---

# Code Review (local agent)

Runs the `code-reviewer` subagent against a scoped diff in the current repo
and surfaces its Critical / Important / Suggestion triage to the user.

For a second opinion from sibling CLIs (codex, gemini, opencode, claude), use
`request-external-reviews` instead — this skill is the authoritative local
review.

## Scope selection

Ask, or infer from the request, which slice the agent should review:

| Scope | Diff command | Context hint for the agent |
|---|---|---|
| Uncommitted | `git diff HEAD` | "working tree changes" |
| Staged | `git diff --cached` | "pre-commit review" |
| Last commit | `git show HEAD` | "just-committed work" |
| Specific commit | `git show <sha>` | "commit <sha>" |
| Branch vs base | `git diff <base>...HEAD` | "PR / branch review" |
| Plan stage N | stage's touched files + plan path | "plan-alignment review" |

If scope is ambiguous, ask. Don't guess between "staged" and "uncommitted"
— the user usually means one specifically.

## Workflow

1. **Collect scope.** Build the diff, the list of changed files, and — if a
   plan file is involved (`plans/*.md`, `docs/plans/*`, `.claude/plans/*`) —
   load the relevant stage so the agent can perform plan-alignment review.
2. **Check diff size.** If the diff is >2000 lines, warn the user: large
   reviews produce shallow findings. Offer to split by stage, by file
   cluster, or by commit.
3. **Redact secrets.** Scan the diff for obvious credentials (`.env`
   contents, `AKIA`/`ghp_`/`sk-` prefixes, PEM blocks). If present, redact
   BEFORE passing to the agent and tell the user what was redacted.
4. **Assemble the brief.** The subagent sees none of this conversation —
   the brief must be self-contained. Include: change intent in 1–3
   sentences, known constraints (tests must pass, API stability, perf
   budget), the diff, the plan excerpt if applicable.
5. **Dispatch the `code-reviewer` agent.** Do NOT run the review inline —
   the subagent has its own protocols (plan-alignment, structural,
   code-smell, security, testability) and a dedicated context window.
6. **Surface the triage verbatim.** Present the Critical / Important /
   Suggestion table as-is with file:line citations. Do not re-rank or
   paraphrase severity.
7. **Offer next steps.** For each Critical or Important, offer to open the
   file, apply a fix, or defer to the user. Do NOT auto-fix without
   confirmation — a code review is informational by default.

## Dispatch template

```
Agent({
  description: "Code review of <scope>",
  subagent_type: "code-reviewer",
  prompt: """Review the following <scope> in this repo.

Intent: <1-3 sentence summary of what this change is meant to do>

Known constraints: <tests must pass / API stability / perf budget / etc.>

Diff:
```diff
<git diff output>
```

<if plan-alignment:>
Plan context:
<plan stage excerpt — tasks, tests, stage gate>

Return your full protocol output: Critical / Important / Suggestion triage
with file:line citations. Do NOT modify files. Cite sources (Google CR guide,
Fowler smells, OWASP/CWE) where relevant."""
})
```

## Chaining with other skills

- **Before commit**: run on `git diff --cached`, fix Criticals, then commit.
- **Between plan stages**: `executing-plans` names this skill as the optional
  stage-gate review.
- **Second opinion**: after this review, optionally run
  `request-external-reviews` on the same scope for cross-model agreement.
- **Ambiguous or missing tests**: route the "needs more tests" findings to
  the `testing-expert` agent instead of trying to write them yourself.

## When NOT to use this skill

- For architecture decisions — use `brainstorming`.
- For multi-model second opinions — use `request-external-reviews`.
- For running tests or fixing flakes — use the `testing-expert` agent.
- For security-only deep audits where the whole goal is threat modeling —
  use the built-in `/security-review` command (it's scoped differently).

## Reference

- **Google Code Review Developer Guide** — https://google.github.io/eng-practices/review/
  (what reviewers look for; how to write review comments; CL size)
- **Fagan inspection** — Michael Fagan, "Design and code inspections to
  reduce errors in program development" (IBM Systems Journal, 1976); the
  canonical multi-reviewer defect-detection study.
- **Fowler, *Refactoring*** (2018) — the code-smell vocabulary (Long
  Method, Feature Envy, Shotgun Surgery, etc.) the agent uses by name.
- **OWASP Top 10 / ASVS / CWE** — the security baseline applied in the
  agent's security-review protocol.
- **code-reviewer agent protocols** — `~/dev/agents/agents/code-reviewer/_core.md`
  (the 6 protocols, 12 house rules, and output schemas this skill consumes)
