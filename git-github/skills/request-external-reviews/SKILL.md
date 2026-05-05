---
name: request-external-reviews
description: >
  Use when the user asks for a second opinion, cross-tool review, or
  multi-model review of a diff. Triggers: "get reviews from other tools",
  "ask codex/gemini/opencode to review", "second opinion on this diff",
  "cross-check this change", "multi-model review". Dispatches the same diff
  to sibling CLIs (codex, gemini, opencode — plus claude when the caller is
  Cursor) in non-interactive read-only mode and aggregates their findings
  with consensus marking. For a single authoritative local review, use
  code-review instead.
---

# Request External Reviews

Sends the same scoped diff to every OTHER AI CLI installed on this machine,
collects their outputs in parallel, and presents a consolidated, consensus-
ranked finding table. Each CLI runs in read-only / plan mode; none of them
modify files in this repo.

## Why

Independent reviewers catch different defects (Fagan, 1976). Running the
same diff through multiple models surfaces:

- **Consensus findings** — when ≥2 tools flag the same `file:line`, the
  finding is high-confidence.
- **Divergent findings** — what one tool flags and others miss is often
  either a false positive or a blind spot worth investigating.

Never dispatch to yourself — that's not a second opinion. If the caller is
Claude Code, don't call `claude`; if the caller is Codex, don't call `codex`.

## Host detection

Determine the caller's environment:

| Caller | Signal | Dispatch to |
|---|---|---|
| Claude Code | `CLAUDECODE=1` env var | codex, gemini, opencode |
| Cursor | `CURSOR_TRACE_ID` set OR `TERM_PROGRAM=cursor` | codex, gemini, opencode, claude |
| Codex CLI | `CODEX_SANDBOX_*` env present | gemini, opencode, claude |
| Gemini CLI | `GEMINI_CLI=1` or user states so | codex, opencode, claude |
| OpenCode | `OPENCODE=1` or user states so | codex, gemini, claude |

If the signal is ambiguous, ASK the user before dispatching. Do NOT guess
and end up talking to yourself.

## Scope selection

Same scope options as `code-review`:

| Scope | Diff command |
|---|---|
| Uncommitted | `git diff HEAD` |
| Staged | `git diff --cached` |
| Last commit | `git show HEAD` |
| Specific commit | `git show <sha>` |
| Branch vs base | `git diff <base>...HEAD` |

## Workflow

1. **Detect host** (above) and confirm the dispatch list with the user in
   one short sentence: "I'll ask codex, gemini, and opencode for a review —
   OK?"
2. **Scope the diff.** Build it once; all tools review the same bytes.
3. **Secret scan.** Grep the diff for obvious credentials (`AKIA`, `ghp_`,
   `sk-`, PEM blocks, `.env` contents). If found, STOP and ask the user
   whether to redact or abort. Never send secrets to external CLIs.
4. **Size check.** If the diff is >2000 lines, warn the user — each CLI
   will produce a shallow review. Offer to split.
5. **Dispatch in parallel** (see invocation matrix below). Each call is
   `timeout`-boxed at 180s. Outputs go to `$REVIEW_DIR/<tool>.md`, never
   stdout (keep the user's terminal clean).
6. **Aggregate.** For each output: strip ANSI, extract triage, normalize
   severity labels to Critical / Important / Suggestion.
7. **Mark consensus.** If ≥2 tools flag the same `file:line`, mark the
   finding as **CONSENSUS**. Single-tool findings are informational.
8. **Present the table** (format below) and hand the user the
   `$REVIEW_DIR` path so they can read any full review.

## Invocation matrix

All calls run non-interactively with read-only / plan permissions. Use the
same prompt and diff for every tool so findings are comparable.

```bash
REVIEW_DIR="$(mktemp -d -t xtool-review.XXXXXX)"
DIFF_FILE="$REVIEW_DIR/diff.patch"
git diff HEAD > "$DIFF_FILE"   # or: --cached / <base>...HEAD / <sha>

PROMPT='Review the attached diff. Flag:
- correctness bugs and null/undefined hazards
- security issues (OWASP Top 10, CWE)
- code smells using Fowler vocabulary by name
- missing or inadequate tests
- plan-alignment gaps (if a plan was provided)

Output format (strict):

## Critical
- file:line — <issue> — <why it matters>

## Important
- file:line — <issue> — <why>

## Suggestion
- file:line — <issue> — <why>

Cite file:line for every finding. Do NOT modify files.'

# codex — built-in review subcommand; scope flag selects what to review
timeout 180 codex review --uncommitted "$PROMPT" \
  > "$REVIEW_DIR/codex.md" 2>&1 &

# gemini — plan mode is read-only; diff on stdin
timeout 180 bash -c "cat '$DIFF_FILE' | gemini --approval-mode plan -p '$PROMPT'" \
  > "$REVIEW_DIR/gemini.md" 2>&1 &

# opencode — non-interactive `run`; embed diff inline
timeout 180 bash -c "opencode run \"\$(cat <<'EOF'
$PROMPT

---
\`\`\`diff
$(cat "$DIFF_FILE")
\`\`\`
EOF
)\"" > "$REVIEW_DIR/opencode.md" 2>&1 &

# claude — ONLY when caller is Cursor (never when caller IS claude)
if [ "$CALLER_IS_CURSOR" = "1" ]; then
  timeout 180 bash -c "cat '$DIFF_FILE' | claude -p '$PROMPT'" \
    > "$REVIEW_DIR/claude.md" 2>&1 &
fi

wait
```

Adjust the `codex review` scope flag to match step 2:
- `--uncommitted` for working-tree/staged changes
- `--commit <sha>` for a specific commit
- `--base <branch>` for branch-vs-base

## Presentation

Consolidate into one table. Promote shared findings to CONSENSUS.

```
## External Reviews — <scope>

Tools: codex, gemini, opencode
Full outputs: /tmp/xtool-review.XXXX/

| File:Line | Severity | Finding | Flagged by |
|---|---|---|---|
| src/foo.ts:42 | **Critical** | Null deref on empty input | codex, gemini (CONSENSUS) |
| src/bar.ts:17 | Important | Missing test for error branch | opencode |
| src/baz.ts:88 | Suggestion | Long Method — extract helper | gemini |

Tools that timed out: <none | list>
Tools that errored: <none | tool: first error line>
```

Then offer next steps: open a file, apply a fix, or run `code-review` (the
local code-reviewer agent) for a deeper authoritative review.

## Guardrails

- **Never send secrets** to external CLIs. Redact or abort if the diff
  contains credentials. External calls go over the network to third-party
  providers and may be logged on their side.
- **All calls read-only.** Use `--approval-mode plan` (gemini), default
  `codex review` (non-destructive), `opencode run` without `apply`, and
  `claude -p` without `--dangerously-skip-permissions`. Never pass write
  flags here.
- **Time-box every call.** `timeout 180` — a stuck CLI should not block the
  whole batch.
- **Don't dispatch to yourself.** Host detection exists for this reason. A
  self-review is not a second opinion.
- **Log divergence, don't paper over it.** If one tool flags a Critical
  that others missed, present it; don't drop it for lack of consensus.

## When NOT to use this skill

- **For a single authoritative review** — use `code-review` (invokes the
  code-reviewer agent) instead. This skill is for *additional* opinions.
- **For architecture decisions** — use `brainstorming`.
- **For test triage** — use the `testing-expert` agent.
- **When offline or without the external CLIs installed** — `command -v
  codex` / `gemini` / `opencode` first; skip any that are missing and warn
  the user rather than failing the whole batch.

## Reference

- **Fagan inspection** — Fagan, "Design and code inspections to reduce
  errors in program development" (IBM Systems Journal, 1976). Multi-
  reviewer inspection as the highest-yield defect-detection technique.
- **Egoless programming** — Weinberg, *The Psychology of Computer
  Programming* (1971). Why a second pair of eyes catches what the author
  glides past.
- **Ensemble / consensus evaluation** — Dietterich, "Ensemble Methods in
  Machine Learning" (2000). Independent models agreeing is a stronger
  signal than any one model alone.
- **code-review skill** — `~/.claude/skills/code-review/SKILL.md` (the
  single-tool authoritative counterpart to this skill).
