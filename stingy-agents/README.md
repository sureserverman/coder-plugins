# stingy-agents

Three Claude Code subagents that let a skill or a caller on Opus offload bulk
or mechanical work to a cheaper, faster model. The goal is simple: spend Opus
tokens on the judgment calls, spend Haiku and Sonnet tokens on everything else.

| Agent | Model | Tools | What it does |
|---|---|---|---|
| `readonly-scanner` | `haiku` | `Read, Glob, Grep, Bash, WebFetch` | Bulk file I/O, greps, URL probes, lint passes, log sampling. Never writes. |
| `skill-rewriter` | `sonnet` | `Read, Edit, Glob, Grep` | Rewrites existing skill / README / subagent files to a spec. Never creates or deletes. |
| `code-generator` | `sonnet` | `Read, Write, Edit, Glob, Grep, Bash` | Generates code, config, scaffolding from a concrete spec. Bash is verify-only (no installs, no commits). |

## Why

Claude Code lets a subagent pin its own model via the `model` field in
frontmatter ([official docs](https://code.claude.com/docs/en/sub-agents)).
Values accepted: `haiku`, `sonnet`, `opus`, a full model ID, or `inherit`.
A parent session on Opus that spawns one of these agents via the Agent tool
pays Haiku or Sonnet rates for that subtree of work.

The [Choosing a Model](https://platform.claude.com/docs/en/about-claude/models/choosing-a-model)
guide maps the tiers cleanly:

- **Haiku** — real-time, high-volume, latency-sensitive, straightforward.
- **Sonnet** — balanced intelligence for coding, content transformation, data
  analysis.
- **Opus** — complex reasoning, multi-hour agentic tasks, architecture calls.

Most skills have phases that are cheaper than their caller needs to be. These
three agents are the delegation targets for the common cases. Sibling plugins
in this marketplace (`plugin-dev`, `git-github`) reference them by name from
audit and review skills.

## Install

This plugin is part of the `coder-plugins` marketplace. Install via:

```
/plugin marketplace add sureserverman/coder-plugins
/plugin install stingy-agents@coder-plugins
```

Verify in a Claude Code session — `/agents` should list `readonly-scanner`,
`skill-rewriter`, and `code-generator`.

## How to use

These agents are **callable** — they aren't invoked by user prompts directly.
Something else (your own skill, an orchestrating agent, or Claude in a given
session) calls them via the Agent tool:

```
Agent(
  subagent_type: "readonly-scanner",
  description: "Enumerate vault orphans",
  prompt: "Vault at /home/me/Vault. Return a bulleted list of .md files under
           Gotchas/, Patterns/, Projects/, Technologies/ that have zero inbound
           `[[...]]` references anywhere else in the vault. Exclude raw/ and
           .obsidian/."
)
```

The parent session gets back structured findings and does the judgment work.

### Typical delegation patterns

```
┌────────────────────────────┐
│  Skill running on Opus     │
│  (orchestration, judgment) │
└──────────────┬─────────────┘
               │
     ┌─────────┴─────────┐
     │                   │
     ▼                   ▼
┌─────────────┐   ┌──────────────┐
│ scan phase  │   │ rewrite or   │
│ → Haiku     │   │ generate     │
│ scanner     │   │ → Sonnet     │
└─────────────┘   └──────────────┘
```

- **Audit skills**: `readonly-scanner` gathers evidence → caller judges → optional
  `skill-rewriter` or `code-generator` applies edits.
- **Content skills** (ingest, merge, import): caller decides *what* to write →
  a sibling Sonnet writer produces the file.
- **Scaffolding skills**: caller decides the spec → `code-generator` writes the
  files and verifies they parse.

See each agent file for the specific jobs it accepts and the shape of input it
expects.

## What each agent won't do

All three refuse to expand scope. They are **scope-bounded workers**, not
autonomous assistants:

- `readonly-scanner` never writes, edits, deletes, or runs mutating commands.
  It will return the would-be content instead of writing it.
- `skill-rewriter` never creates or deletes files. It only edits files the
  caller names.
- `code-generator` never installs packages, never commits, never touches
  remote state. Verification is the only Bash work it does.

This discipline is deliberate — the whole value of delegation collapses if a
cheap agent starts making architecture decisions.

## Model override resolution

Claude Code resolves the model a subagent uses in this order
([docs](https://code.claude.com/docs/en/model-config)):

1. `CLAUDE_CODE_SUBAGENT_MODEL` environment variable
2. Per-invocation `model` parameter (when a caller passes one)
3. The subagent file's `model:` frontmatter
4. The main conversation's model (when `model: inherit`)

So these agents always run on their pinned tier unless the env var or
caller-side override says otherwise.

## Layout

```
stingy-agents/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   ├── readonly-scanner.md     # Haiku
│   ├── skill-rewriter.md       # Sonnet
│   └── code-generator.md       # Sonnet
├── LICENSE
└── README.md
```

Each `.md` file is a self-contained subagent definition — YAML frontmatter
(`name`, `description`, `tools`, `model`) plus a system prompt. Read them to
see exactly what each agent will and won't do.

## References

- [Claude Code — Create custom subagents](https://code.claude.com/docs/en/sub-agents)
- [Claude Code — Model configuration](https://code.claude.com/docs/en/model-config)
- [Anthropic — Choosing a model](https://platform.claude.com/docs/en/about-claude/models/choosing-a-model)

## License

MIT. See [LICENSE](LICENSE).
