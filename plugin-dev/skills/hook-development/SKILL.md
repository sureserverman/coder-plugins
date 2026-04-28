---
name: hook-development
description: Use when authoring or debugging Claude Code hooks. Triggers on "create a hook", "PreToolUse hook", "PostToolUse hook", "session-end hook", "block dangerous bash", "auto-format on save via hook", "Stop hook infinite loop", "hooks.json", or any request to add or fix a hook in a plugin or settings.json.
---

# hook-development

Rules for writing correct, well-scoped Claude Code hooks. Read `references/events.md` for full
input/output schemas. Read `references/feedback-vs-blocking.md` before choosing to block.

> **Version compatibility — verify before shipping.** A handful of fields and env vars referenced
> in this skill and in `references/events.md` evolve between Claude Code releases. Confirm
> against `code.claude.com/docs/en/hooks` for your installed SDK version, in particular:
> - `output.path` field name on `PostToolUse` for file-edit tools (some SDK versions use `file_path` or `tool_input.file_path`).
> - `summary` field on `SessionEnd` input (presence and shape vary).
> - Prompt-rewriting on `UserPromptSubmit` (some versions only support `block`/`reason`, not in-place rewrite).
> - The Stop-loop guard env var name — `STOP_HOOK_ACTIVE` vs `CLAUDE_STOP_HOOK_ACTIVE`. Bash examples below use `STOP_HOOK_ACTIVE`; substitute if your SDK uses the prefixed form.
>
> Treat all bash snippets as templates, not drop-in code, until field names are confirmed.

## Reference map

| When you're… | Read first |
|---|---|
| Looking up an event's fields or maturity level | `references/events.md` |
| Deciding whether to block or inject feedback | `references/feedback-vs-blocking.md` |

## File and shape

Plugin hooks live in one file at the plugin root:

```
hooks/hooks.json
```

The file is a **JSON array** of hook entries. The schema mirrors the `hooks` block in
`settings.json` — one entry per event binding.

Minimal entry shape:

```json
[
  {
    "event": "PreToolUse",
    "matcher": { "tool": "Bash" },
    "command": "${CLAUDE_PLUGIN_ROOT}/hooks/guard-bash.sh"
  }
]
```

Key fields:

| Field | Required | Notes |
|---|---|---|
| `event` | yes | One of the names in the event catalogue below |
| `command` | yes (or `type:"prompt"`) | Shell command or prompt-hook config |
| `matcher` | depends on event | Filter by `tool`, `file`, `reason`, etc. |

**Always use `${CLAUDE_PLUGIN_ROOT}` for bundled script paths.** Relative paths break when the
plugin is installed outside the authoring directory.

## Event catalogue

Maturity labels: **widely-used** = proven in production across many plugins;
**documented** = in official docs, less battle-tested; **experimental** = subject to change.

### Lifecycle

| Event | Maturity | Notes |
|---|---|---|
| `SessionStart` | widely-used | Fires on new session or resume. Write env vars to `$CLAUDE_ENV_FILE` for cross-turn persistence. |
| `SessionEnd` | widely-used | Fires on termination. Matcher: `reason` — one of `clear`, `resume`, `logout`, `prompt_input_exit`, `other`. |
| `UserPromptSubmit` | widely-used | Fires when user submits a prompt. Can block, augment, or pass through. |

### Tool execution

| Event | Maturity | Notes |
|---|---|---|
| `PreToolUse` | widely-used | Before a tool call. Return `permissionDecision: "deny"` to block, `"allow"` to approve, `"defer"` to escalate. Common: blocking `rm -rf`, guarding force-push. |
| `PostToolUse` | widely-used | After successful tool execution. Return `additionalContext` to inject feedback into the next turn (feedback-injection pattern). Common: lint/typecheck after file edits. |
| `PostToolUseFailure` | documented | After a tool error. Useful for recovery suggestions or alerting. |
| `PostToolBatch` | documented | After a parallel tool batch completes. Receives all results at once. |

### Permissions and failure

| Event | Maturity | Notes |
|---|---|---|
| `PermissionRequest` | documented | User-side permission prompt. Hook can auto-approve or auto-deny. |
| `Stop` | documented | Claude finished its turn. Non-blocking. **See infinite-loop gotcha below.** |
| `StopFailure` | documented | Claude failed (rate limit, auth, billing). Good for alerting or retry logic. |
| `Notification` | documented | Incoming event from a monitor or MCP server. |

### Advanced / niche

| Event | Maturity | Notes |
|---|---|---|
| `UserPromptExpansion` | documented | Slash-command expansion. |
| `CwdChanged` | documented | Working directory changed. |
| `FileChanged` | documented | File modified outside Claude's tools. |
| `SubagentStart` / `SubagentStop` | documented | Subagent lifecycle. |

### Prompt-based hooks (experimental)

Instead of `command:` (bash), use `type: "prompt"` to have Claude evaluate a prompt as the
hook decision. Slower and more expensive than bash hooks, but capable of nuanced judgment.

```json
{
  "event": "UserPromptSubmit",
  "type": "prompt",
  "prompt": "Check whether this prompt contains credentials or PII. If yes, return {\"block\": true, \"reason\": \"credential detected\"}."
}
```

Use only when bash decision logic is not expressive enough.

## Patterns

### PostToolUse feedback injection (linter)

Run a linter after edits and return errors as context rather than blocking the write.
See `references/feedback-vs-blocking.md` for why this beats blocking.

```json
{
  "event": "PostToolUse",
  "matcher": { "tool": "Edit", "file": "**/*.ts" },
  "command": "${CLAUDE_PLUGIN_ROOT}/hooks/eslint-feedback.sh"
}
```

`eslint-feedback.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
# Hook receives tool output on stdin as JSON
FILE=$(jq -r '.output.path // empty' <<<"$1")
[ -z "$FILE" ] && exit 0
RESULT=$(eslint --format=compact "$FILE" 2>&1 || true)
[ -z "$RESULT" ] && exit 0
jq -n --arg ctx "$RESULT" '{"additionalContext": $ctx}'
```

### PreToolUse guard for dangerous bash

```json
{
  "event": "PreToolUse",
  "matcher": { "tool": "Bash" },
  "command": "${CLAUDE_PLUGIN_ROOT}/hooks/guard-bash.sh"
}
```

`guard-bash.sh`:

```bash
#!/usr/bin/env bash
CMD=$(jq -r '.input.command // empty' <<<"$1")
if echo "$CMD" | grep -qE '(rm\s+-rf\s+/|git push --force(-with-lease)? origin main)'; then
  jq -n '{"permissionDecision": "deny", "reason": "Blacklisted pattern matched"}'
  exit 0
fi
jq -n '{"permissionDecision": "allow"}'
```

### SessionEnd auto-capture

Archive the session to a vault or journal:

```json
{
  "event": "SessionEnd",
  "matcher": { "reason": "logout" },
  "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-capture.sh"
}
```

### UserPromptSubmit security scrub

Strip secrets from user input before the model sees them:

```json
{
  "event": "UserPromptSubmit",
  "command": "${CLAUDE_PLUGIN_ROOT}/hooks/secret-scrub.sh"
}
```

The hook receives the prompt text and returns a (possibly rewritten) prompt or a block decision.

## Anti-patterns

1. **`Stop` hook without `stop_hook_active` guard — infinite loop.** The #1 newbie bug. A `Stop`
   hook that itself triggers Claude's turn causes another `Stop`, forever.
   Always open every `Stop` hook script with:

   ```bash
   if [ "$STOP_HOOK_ACTIVE" = "true" ]; then exit 0; fi
   ```

2. **Blocking on error in PostToolUse hooks.** Returning a hard block from a linter silently
   cancels writes the user expected to succeed. Prefer feedback injection — return the error
   as `additionalContext` and let the model self-correct.

3. **Relative script paths in `command:`.** They break the moment the plugin is installed
   anywhere other than the authoring directory. Always use `${CLAUDE_PLUGIN_ROOT}/…`.

4. **Long-running hooks on hot events.** A 500 ms lint run on every `PostToolUse` for every
   Edit compounds across the session. Gate by `tool` name and `file` pattern to limit scope.

5. **Shell profile / rc-file output to stderr.** Hooks parse stdout as JSON. Anything that
   sources a profile (`~/.bashrc`, `/etc/profile`) or produces banner output to stderr can
   corrupt hook parsing. Run hook scripts with `env -i` or a minimal shebang that avoids
   profile sourcing.

## Sources

- code.claude.com/docs/en/hooks (canonical event reference)
- code.claude.com/docs/en/hooks-guide
- Community examples: github.com/wshobson/agents, github.com/obra/superpowers
