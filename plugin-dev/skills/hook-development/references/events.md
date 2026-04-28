# Hook Events Reference

Maturity labels used throughout:
- **widely-used** — proven across many production plugins; stable API.
- **documented** — covered in official docs; real-world coverage is thinner.
- **experimental** — subject to change; test before shipping.

> **Version compatibility — verify before shipping.** Several field names and env vars below
> evolve between Claude Code releases. Confirm against `code.claude.com/docs/en/hooks` for
> your installed SDK version, in particular:
> - `output.path` field name on `PostToolUse` for file-edit tools (some SDK versions use `file_path` or `tool_input.file_path`).
> - `summary` field on `SessionEnd` input (presence and shape vary).
> - Prompt-rewriting on `UserPromptSubmit` (some versions only support `block`/`reason`, not in-place rewrite).
> - The Stop-loop guard env var name — `STOP_HOOK_ACTIVE` vs `CLAUDE_STOP_HOOK_ACTIVE`. Bash examples use `STOP_HOOK_ACTIVE`; substitute if your SDK uses the prefixed form.
>
> Treat all bash snippets as templates, not drop-in code, until field names are confirmed.

---

## Lifecycle events

### `SessionStart` — widely-used

Fires when a session begins (new or resumed).

**Input fields:**

| Field | Type | Description |
|---|---|---|
| `session_id` | string | Unique session identifier |
| `resumed` | boolean | `true` if this is a resumed session |

**Output fields (optional):**

| Field | Type | Description |
|---|---|---|
| `env` | object | Key-value pairs to write to `$CLAUDE_ENV_FILE` for persistence |

**Use-case:** Load per-project config, set `PROJECT_ROOT`, write auth tokens to the env file
so downstream hooks can read them without re-computing.

**Worked example:**

```bash
#!/usr/bin/env bash
# hooks/session-init.sh
PROJECT=$(jq -r '.session_id' <<<"$1")
jq -n --arg root "$PWD" '{"env": {"PROJECT_ROOT": $root}}'
```

(The `STOP_HOOK_ACTIVE` guard is for `Stop` hooks only — see that section below; it does not apply to `SessionStart`.)

```json
{ "event": "SessionStart", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-init.sh" }
```

---

### `SessionEnd` — widely-used

Fires when the session terminates.

**Input fields:**

| Field | Type | Description |
|---|---|---|
| `session_id` | string | Session identifier |
| `reason` | string | One of `clear`, `resume`, `logout`, `prompt_input_exit`, `other` |
| `summary` | string | Brief model-generated session summary (may be empty) |

**Matcher:** `reason` — filter to specific termination causes.

**Output fields:** None expected; hook runs for side-effects only.

**Use-case:** Archive a session transcript to a vault, trigger a journal entry, flush a
metrics buffer.

**Worked example:**

```bash
#!/usr/bin/env bash
# hooks/session-capture.sh
REASON=$(jq -r '.reason' <<<"$1")
SUMMARY=$(jq -r '.summary // ""' <<<"$1")
DATE=$(date -u +%Y-%m-%d)
echo "[$DATE] session-end reason=$REASON" >> ~/.claude/session-log.txt
[ -n "$SUMMARY" ] && echo "$SUMMARY" >> ~/.claude/session-log.txt
```

```json
{
  "event": "SessionEnd",
  "matcher": { "reason": "logout" },
  "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-capture.sh"
}
```

---

### `UserPromptSubmit` — widely-used

Fires immediately after the user submits a prompt, before the model processes it.

**Input fields:**

| Field | Type | Description |
|---|---|---|
| `prompt` | string | Raw user prompt text |
| `session_id` | string | Current session |

**Output fields (optional):**

| Field | Type | Description |
|---|---|---|
| `prompt` | string | Rewritten prompt (replaces the original) |
| `block` | boolean | If `true`, prevents the prompt from reaching the model |
| `reason` | string | Shown to user when `block` is `true` |

**Use-case:** Scrub secrets/PII from prompts, enforce prompt policies, inject per-turn context.

**Worked example — secret scrub:**

```bash
#!/usr/bin/env bash
# hooks/secret-scrub.sh
PROMPT=$(jq -r '.prompt' <<<"$1")
# Redact anything that looks like AWS keys
CLEAN=$(echo "$PROMPT" | sed 's/AKIA[0-9A-Z]\{16\}/[REDACTED_AWS_KEY]/g')
if [ "$CLEAN" != "$PROMPT" ]; then
  jq -n --arg p "$CLEAN" '{"prompt": $p}'
else
  exit 0   # no change needed
fi
```

---

## Tool execution events

### `PreToolUse` — widely-used

Fires before a tool call executes. The hook can allow, deny, or defer the call.

**Input fields:**

| Field | Type | Description |
|---|---|---|
| `tool` | string | Tool name (e.g., `Bash`, `Edit`, `Write`) |
| `input` | object | Tool-specific input (e.g., `command` for Bash, `path` for Edit) |
| `session_id` | string | Current session |

**Matcher:** `tool` — bind only to specific tools.

**Output fields:**

| Field | Type | Description |
|---|---|---|
| `permissionDecision` | string | `"allow"`, `"deny"`, or `"defer"` |
| `reason` | string | Shown to user/model on deny |

**Use-case:** Block destructive commands, require confirmation for sensitive operations,
enforce branch-protection rules.

**Worked example — block force-push to main:**

```bash
#!/usr/bin/env bash
# hooks/guard-bash.sh
CMD=$(jq -r '.input.command // empty' <<<"$1")
if echo "$CMD" | grep -qE 'git push --force(-with-lease)? origin main'; then
  jq -n '{"permissionDecision": "deny", "reason": "Force-push to main is blocked by policy."}'
  exit 0
fi
jq -n '{"permissionDecision": "allow"}'
```

```json
{
  "event": "PreToolUse",
  "matcher": { "tool": "Bash" },
  "command": "${CLAUDE_PLUGIN_ROOT}/hooks/guard-bash.sh"
}
```

---

### `PostToolUse` — widely-used

Fires after a tool call completes successfully.

**Input fields:**

| Field | Type | Description |
|---|---|---|
| `tool` | string | Tool name |
| `input` | object | Original tool input |
| `output` | object | Tool result (e.g., `path`, `content` for file edits) |
| `session_id` | string | Current session |

**Matcher:** `tool`, `file` — narrow to specific tools or file patterns.

**Output fields:**

| Field | Type | Description |
|---|---|---|
| `additionalContext` | string | Injected into the next model turn as context |

**Use-case:** Run linters, type-checkers, or tests after edits and surface errors without
blocking the write (feedback-injection pattern). See `feedback-vs-blocking.md`.

**Worked example — mypy feedback injection:**

```bash
#!/usr/bin/env bash
# hooks/mypy-feedback.sh
FILE=$(jq -r '.output.path // empty' <<<"$1")
[[ "$FILE" != *.py ]] && exit 0
RESULT=$(mypy "$FILE" 2>&1 || true)
[ -z "$RESULT" ] && exit 0
jq -n --arg ctx "mypy output:\n$RESULT" '{"additionalContext": $ctx}'
```

```json
{
  "event": "PostToolUse",
  "matcher": { "tool": "Edit", "file": "**/*.py" },
  "command": "${CLAUDE_PLUGIN_ROOT}/hooks/mypy-feedback.sh"
}
```

---

### `PostToolUseFailure` — documented

Fires when a tool call returns an error.

**Input fields:** Same as `PostToolUse`, plus:

| Field | Type | Description |
|---|---|---|
| `error` | string | Error message from the tool |

**Output fields:** Same as `PostToolUse` (`additionalContext`).

**Use-case:** Suggest recovery actions, alert on repeated failures, log tool errors to an
external sink.

---

### `PostToolBatch` — documented

Fires after a batch of parallel tool calls all complete.

**Input fields:**

| Field | Type | Description |
|---|---|---|
| `results` | array | Array of `{tool, input, output, error}` objects |
| `session_id` | string | Current session |

**Output fields:** `additionalContext` (string).

**Use-case:** Aggregate lint results across multiple files edited in parallel, avoiding
per-file noise.

---

## Permissions and failure events

### `PermissionRequest` — documented

Fires when a permission prompt is shown to the user. Hook can resolve it automatically.

**Input fields:**

| Field | Type | Description |
|---|---|---|
| `tool` | string | Tool requesting permission |
| `input` | object | Tool input |
| `permission` | string | The specific permission being requested |

**Output fields:**

| Field | Type | Description |
|---|---|---|
| `decision` | string | `"approve"` or `"deny"` |
| `reason` | string | Optional justification |

**Use-case:** Auto-approve allowlisted tools for CI environments; auto-deny network access
in air-gapped sessions.

---

### `Stop` — documented

Fires when Claude finishes its turn (non-blocking by default).

**Input fields:**

| Field | Type | Description |
|---|---|---|
| `session_id` | string | Current session |
| `turn_id` | string | Completed turn identifier |

**Output fields:** None.

**CRITICAL — infinite loop guard:** Any action a `Stop` hook takes that causes Claude to
run another turn will trigger another `Stop`, recursively. Always check:

```bash
if [ "$STOP_HOOK_ACTIVE" = "true" ]; then exit 0; fi
```

**Use-case:** Post-turn metrics, structured output extraction, triggering downstream pipelines
after Claude's response is complete.

---

### `StopFailure` — documented

Fires when Claude's turn ends with a failure (rate limit, auth error, billing issue).

**Input fields:**

| Field | Type | Description |
|---|---|---|
| `session_id` | string | Current session |
| `error_code` | string | Machine-readable failure category |
| `error_message` | string | Human-readable description |

**Output fields:** None.

**Use-case:** Alert via webhook, write to a dead-letter log, trigger a retry workflow.

---

### `Notification` — documented

Fires when an external event arrives from a monitor or MCP server.

**Input fields:**

| Field | Type | Description |
|---|---|---|
| `source` | string | Monitor or MCP server name |
| `payload` | object | Arbitrary notification payload |

**Output fields:** `additionalContext` (string) to surface the notification in the next turn.

---

## Advanced / niche events

### `UserPromptExpansion` — documented

Fires during slash-command expansion, before the expanded prompt is submitted.

**Input:** `command` (string, the slash command), `args` (string).
**Output:** `prompt` (string, the expanded prompt to use).

---

### `CwdChanged` — documented

Fires when the working directory changes.

**Input:** `old_cwd` (string), `new_cwd` (string).
**Output:** `additionalContext` (string).

**Use-case:** Switch active project context, reload per-directory env vars.

---

### `FileChanged` — documented

Fires when a file is modified outside Claude's own tools (e.g., by another process).

**Input:** `path` (string), `change_type` (string: `created`, `modified`, `deleted`).
**Output:** `additionalContext` (string).

**Use-case:** Notify Claude that a build artifact changed, trigger re-reads.

---

### `SubagentStart` / `SubagentStop` — documented

Fire at the start and end of a subagent's lifecycle.

**Input:** `subagent_id` (string), `subagent_name` (string), `session_id` (string).
**Output:** None.

**Use-case:** Scope resource allocation/cleanup to subagent lifetime, emit tracing spans.
