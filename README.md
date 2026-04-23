# coder-plugins

A Claude Code plugin marketplace hosting language-specific authoring plugins.

## Install as a marketplace

```
/plugin marketplace add /home/user/dev/coder-plugins
```

Then install individual plugins:

```
/plugin install rust-dev@coder-plugins
```

Or, if published to a remote git repo:

```
/plugin marketplace add <user>/coder-plugins
/plugin install rust-dev@coder-plugins
```

## Plugins

### rust-dev

Idiomatic Rust authoring. Bundles:

- **`rust-coding` skill** — triggers on `*.rs` / `Cargo.toml` edits; decision rules for unsafe discipline, async correctness, error handling, FFI, performance, edition 2024; progressive disclosure via `references/`.
- **`rust-expert` subagent** — sonnet-pinned, authoring-capable. Protocols: Stack detection, Author, Refactor, Review, Unsafe audit, Edition migration. Cites Rust API Guidelines, Microsoft Pragmatic Rust, *Effective Rust*, Sherlock 2026 Security Guide, tokio docs.
- **`/rust-review`** — dispatches rust-expert on a scoped diff (uncommitted, file, commit, PR).
- **`/rust-idiomize`** — dispatches rust-expert to refactor a path for idioms, behavior-preserving, tests green at each step.

Source: [`rust-dev/`](./rust-dev)

## Layout

```
coder-plugins/
├── .claude-plugin/
│   └── marketplace.json        # marketplace manifest
├── README.md                    # this file
└── rust-dev/                    # first plugin
    ├── .claude-plugin/
    │   └── plugin.json          # plugin manifest
    ├── skills/
    ├── agents/
    └── commands/
```

## Contributing a new plugin

1. Add a top-level directory named `<plugin-name>/`
2. Inside it, create `.claude-plugin/plugin.json` with `name`, `version`, `description`
3. Add `skills/`, `agents/`, `commands/`, and/or `hooks/` subdirectories as needed
4. Register the plugin in `.claude-plugin/marketplace.json` under `plugins`
5. Validate with the `plugin-dev:plugin-validator` skill in Claude Code
