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
