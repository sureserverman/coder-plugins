# Registry Format: `~/.claude/projects-registry.yaml`

This file is the canonical source of truth for all projects tracked by the
`portfolio` skill. The orchestrator reads it on every run to know which
projects to scan, unify, and audit for maturity. It is auto-seeded on first
invocation by walking `~/dev/` and proposing entries, but every subsequent
write is gated behind explicit user confirmation. Nothing in the portfolio
flow modifies this file without the user's say-so.

## Schema

### Top-level fields

| Field | Type | Meaning |
|---|---|---|
| `version` | integer | Schema version. Currently `1`. Parsers must reject any other value. |
| `projects` | list | Ordered list of project entries. Order is informational; uniqueness is by `path`. |

### Per-entry fields

| Field | Type | Meaning |
|---|---|---|
| `path` | string | Absolute filesystem path to the project root. Must not contain `~` — expand at write time. E.g. `/home/user/dev/android/my-app`. |
| `name` | slug (string) | Kebab-case identifier derived from the final path component. Informational only; may collide across areas. Uniqueness is enforced by `path`, not `name`. |
| `area` | string | The top-level category directory under `~/dev/` that contains this project. One of: `anon-tools`, `android`, `browsers`, `containers`, `infra`, `routers`, `servers`, `web`, `whonix`, `xray-host`, `ai-tools`, `big-projects`, `tor-vanity`, `virt`, `watch`, `telebots`. |
| `enabled` | boolean | When `true` (default), the project is included in unify and maturity runs. When `false`, the project remains listed in the registry but is skipped during all portfolio operations. Use this for archived or on-hold projects. |
| `added` | string | ISO date (`YYYY-MM-DD`) recording when this entry was first written into the registry. Set once at creation; never updated. |

## Example

```yaml
version: 1

projects:
  - path: /home/user/dev/android/fennec-privacy-browser
    name: fennec-privacy-browser
    area: android
    enabled: true
    added: 2026-05-22

  - path: /home/user/dev/infra/vps-bootstrap
    name: vps-bootstrap
    area: infra
    enabled: true
    added: 2026-04-10

  - path: /home/user/dev/anon-tools/tor-resolver
    name: tor-resolver
    area: anon-tools
    enabled: false
    added: 2026-01-15
```

## Hard rules

- The file is YAML, parsed with Python's `yaml.safe_load`. No anchors and no
  aliases are permitted. The parser will reject them on sight.
- Never re-write the file in bulk during a portfolio run. Only append new
  entries, remove specific entries, or toggle the `enabled` field on an
  existing entry. Full rewrites destroy the diff legibility that makes the
  registry auditable in git.
- `name` is informational. Two projects in different areas may share the same
  `name` slug (e.g. `servers/proxy` and `containers/proxy` would both produce
  `name: proxy`). Uniqueness is enforced by `path` alone.
- On corrupt YAML — a parse error, an unrecognised `version`, a missing
  required field — abort the run immediately with a one-line error that names
  the offending line number. Never attempt to auto-repair or rewrite the
  registry to fix a parse failure. The suggested recovery path is:
  `mv ~/.claude/projects-registry.yaml{,.bad}` and re-invoking to trigger the
  first-run seed flow.

## Resolver: repo → vault portfolio home

This section documents the convention that maps a registered project repo to
its operational-docs home in the Obsidian vault. It is the lynchpin of the
migration that moves per-project plans, backlogs, and maturity docs OUT of
repos and INTO the vault.

### The mapping

A repo registered at `~/dev/<area>/<project>` resolves to its vault home at:

```
<vault_dir>/Portfolio/<area>/<name>/
```

where:

- `vault_dir` is read from `~/.claude/portfolio-config.yaml` (the `vault_dir:`
  key). This is the only authoritative source for the vault root.
- `<area>` and `<name>` come from the registry entry for that project — the
  `area` field and the `name` field respectively.

Example: `~/dev/anon-tools/multitor` → `/mnt/vault/Portfolio/anon-tools/multitor/`.

### What lives under a project's vault home

| Path (relative to vault home) | Contents |
|---|---|
| `plans/` | The project's staged plans, moved from `<repo>/docs/plans/`. |
| `backlog.md` | Moved from `<repo>/docs/backlog.md`, or born here on the first `unify` run. |
| `MATURITY.md` | Moved from `<repo>/docs/MATURITY.md`. |
| `integration.md` | Declared inter-project edges — dependencies and consumers. |

### Sidecar cache: `.claude/vault-context.md`

Each repo's `.claude/vault-context.md` records:

```
portfolio_home: <absolute resolved path>
```

This allows a session opened inside the repo to know its vault home immediately,
without querying the registry on every invocation.

The sidecar value is a **cache**. The registry + the mapping convention above is
**authoritative**. If the two disagree, the tool must recompute from the registry,
update the sidecar, and emit a warning to the user noting the discrepancy.

### HARD RULE: fails loudly — no silent fallback

If `vault_dir` is unset (the key is absent or empty) in
`~/.claude/portfolio-config.yaml`, every tool that would resolve a vault home
**must refuse to write** and print a clear error such as:

```
portfolio not configured: set vault_dir in ~/.claude/portfolio-config.yaml
```

The tool must **never** fall back to writing into `<repo>/docs/` as a
substitute. Doing so would re-fragment the docs that were just centralized into
the vault — exactly the outcome this migration exists to prevent. The tool
**fails loudly** and stops. There is **no silent fallback**.

### Auto-create on first write

A registered project whose vault home directory does not yet exist gets
`Portfolio/<area>/<name>/` created automatically on the first write
(`mkdir -p`), analogous to the backlog skill's auto-create-on-first-write
behavior. This means onboarding a new project requires no manual vault setup —
the directory materializes the moment any portfolio tool first writes to it.

## Auto-registration on first plan

A brand-new project does not need a manual registry step. When `brainstorming`
or `planning-projects` runs in `~/dev/<area>/<name>` and that path is not yet in
the registry, the planner:

1. Appends a registry entry derived from the path (`path`, `name` = final
   segment, `area` = first segment under `~/dev/`, `enabled: true`,
   `added: <today>`).
2. Creates/refreshes the repo sidecar `.claude/vault-context.md` with the
   resolved `portfolio_home`.
3. Writes the design + plan into `<portfolio_home>/plans/`.

This is the on-ramp: a project joins the portfolio the first time it is planned,
so its plans/backlog/maturity are vault-canonical from day one (never a stray
`<repo>/docs/plans/`). The only exception is the no-`vault_dir` fallback, where
the planner warns and writes to `<repo>/docs/plans/` instead.
