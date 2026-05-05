# OpenCode custom agent format

Source of truth: `https://opencode.ai/docs/agents/` and `https://opencode.ai/docs/permissions/`. Verify with WebFetch or context7 (`/anomalyco/opencode`) before writing if unsure.

## File location

| Scope   | Path                                       |
| :------ | :----------------------------------------- |
| User    | `~/.config/opencode/agents/<name>.md`        |
| Project | `.opencode/agents/<name>.md`                 |

Filename stem becomes the agent identifier. (Some older docs show `agent/` singular — the current directory is `agents/` plural; if install fails, check the user's version.)

## Agent modes

| Mode       | Purpose                                                                                     |
| :--------- | :------------------------------------------------------------------------------------------ |
| `primary`  | Main assistant. Accessed via Tab key / `switch_agent`. Direct conversation.                  |
| `subagent` | Specialized assistant. Invoked automatically by primary agents or explicitly with `@<name>`. |
| `all`      | Available in either mode. Use sparingly — most agents want one role.                          |

For a subagent bundle, use `mode: subagent`.

## Frontmatter schema

```markdown
---
description: Required. One paragraph. Routing blurb + trigger phrases + stance.
mode: subagent
model: anthropic/claude-sonnet-4-20250514
temperature: 0.1
permission:
  edit: deny
  bash:
    "*": ask
    "git diff": allow
    "git log*": allow
    "grep *": allow
  webfetch: deny
# Optional:
# top_p: 0.9
# steps: 20
# hidden: false
---

<system prompt in markdown>
```

### Fields

| Field         | Required | Notes                                                                                     |
| :------------ | :------- | :---------------------------------------------------------------------------------------- |
| `description` | yes      | Routing mechanism. Same rules as other hosts — phrases, domain, stance.                    |
| `mode`        | no       | `primary` / `subagent` / `all`. Default depends on context.                               |
| `model`       | no       | Provider/model-id format: `anthropic/claude-sonnet-4-20250514`, `openai/gpt-4o`, etc.     |
| `temperature` | no       | `0.0–1.0`. Low (`0.1`) for analysis; higher for generative work.                          |
| `top_p`       | no       | Alternative randomness control.                                                           |
| `steps`       | no       | Max agentic iterations before returning.                                                  |
| `tools`       | no       | **Deprecated.** Old key/bool map (`write: false`). Use `permission` instead on new agents. |
| `permission`  | no       | Fine-grained access control. See below.                                                   |
| `hidden`      | no       | Boolean. `true` = not visible to `@mention` but still programmatically usable.            |

## Permission block

The modern access-control mechanism. Scoped globally or per agent.

```yaml
permission:
  edit: deny       # or "allow" / "ask"
  bash:            # glob-style per command
    "*": ask
    "git diff": allow
    "grep *": allow
    "rm *": deny
  webfetch: deny
```

Values per key: `"allow"`, `"ask"`, `"deny"`.

Prefer the new `permission:` block over the old `tools:` map — the old form is deprecated.

## Invocation

- Automatic: a `primary` agent routes to a `subagent` when task matches description.
- Manual: `@<agent-name>` in the chat.
- Navigation: `session_child_first` enters the subagent session; arrow keys cycle.

## JSON alternative

Agents can also be defined in `opencode.json` under `agent.<name>`. For the multi-host bundle, prefer the markdown + frontmatter form — it's portable and git-friendly.

## Host-affordance hints for the wrapper

- OpenCode is TUI-first with client/server architecture — agents run server-side, the TUI renders.
- Sub-sessions create a navigable thread you can switch between.
- Permission block is granular for `bash` — exploit that instead of a blanket `bash: deny`.
- Temperature matters: set to `0.1–0.2` for triage/review; bump for authoring.

## Common mistakes

- Using the deprecated `tools:` map instead of `permission:`. Works today, will likely break.
- Full model IDs without the provider prefix — `claude-sonnet-4` alone won't resolve; use `anthropic/claude-sonnet-4-20250514`.
- Setting `mode: primary` for an agent meant to be delegated to. Primary agents consume a Tab slot; subagents don't.
