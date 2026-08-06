---
description: Wire, check, or remove the plan-execution progress bar in the Claude Code status line. Triggers on "install the progress bar", "wire the plan statusline", "is the progress bar set up", "remove the statusline bar".
argument-hint: "[install|status|remove] [--force]"
allowed-tools: ["Bash(python3:*)"]
model: inherit
---

# /planning:statusline

Manages the one line of wiring the plan-execution progress bar needs in
`~/.claude/settings.json`.

The bar itself ships with this plugin — `skills/executing-plans/scripts/plan-progress.py`
renders it, and `statusline-chain.sh` chains it after whatever status line you already
have. What cannot ship with the plugin is the pointer: `statusLine` is not a plugin
contribution point (a plugin's `settings.json` supports only `agent` and
`subagentStatusLine`), so exactly one entry must live in your global settings. This
command is what writes it, so you never hand-edit that file.

Wiring is **global and one-time** — it applies in every project, not per repo. The bar
prints nothing when no plan is executing.

## Run

The user invoked this with: `$ARGUMENTS`

Map the argument to a subcommand and run it, from the plugin root:

| Argument | Command |
|---|---|
| `install` (or empty) | `python3 ${CLAUDE_PLUGIN_ROOT}/skills/executing-plans/scripts/statusline-install.py --install` |
| `status` | `python3 ${CLAUDE_PLUGIN_ROOT}/skills/executing-plans/scripts/statusline-install.py --status` |
| `remove` | `python3 ${CLAUDE_PLUGIN_ROOT}/skills/executing-plans/scripts/statusline-install.py --remove` |

Append `--force` when the user passed it.

Report the script's own output. Three cases need a word of explanation rather than
a bare paste:

- **A non-zero exit naming an existing `statusLine`** means something else is already
  wired there. Show what it points at and ask before re-running with `--force` — do not
  pass `--force` on your own initiative.
- **A refusal on malformed JSON** means the settings file could not be parsed. Do not
  offer to repair it by rewriting; say which file failed and let the user look.
- **After a successful install**, tell the user the bar appears on the next status line
  redraw and only while a plan is executing — an empty status line is the expected
  result when nothing is running, not a failed install.
