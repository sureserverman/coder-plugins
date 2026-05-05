---
description: <One-paragraph routing blurb with trigger phrases and stance sentence.>
mode: subagent
model: anthropic/claude-sonnet-4-20250514
temperature: 0.1
permission:
  edit: deny
  bash:
    "*": ask
    "grep *": allow
    "git diff": allow
    "git log*": allow
  webfetch: deny
---

# <AGENT_NAME> (OpenCode build)

## Host affordances

- TUI-first with client/server architecture; sub-sessions are navigable via arrow keys.
- Use the `permission:` block for fine-grained control instead of blanket denies.
- Temperature kept low for analysis; bump for generative work.

<!-- CORE -->
