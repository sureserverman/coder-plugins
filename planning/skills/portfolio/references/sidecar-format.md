# Sidecar Format: Portfolio Status Block (v2)

The portfolio status block is a sentinel-delimited section that `/planning:portfolio rebuild`
writes into each registered project's `.claude/vault-context.md` sidecar. The
vault-context plugin owns the rest of that file; the portfolio skill owns
**only** the content between the sentinels and must never touch anything outside
them. Re-runs replace only the block's inner content — the operation is
idempotent, and anything the vault-context plugin wrote above or below the
sentinels is preserved byte-for-byte.

## Sentinels

- **Begin:** `<!-- PORTFOLIO-STATUS-BEGIN — managed by /planning:portfolio rebuild; do not hand-edit -->`
- **End:** `<!-- PORTFOLIO-STATUS-END -->`

Insertion logic:

- If both sentinels are present in the file → replace the content between them
  with the freshly generated block body. The sentinel lines themselves are not
  touched.
- If either sentinel is absent → append the entire block (begin sentinel,
  content, end sentinel) at the end of the file, preceded by exactly one blank
  line separator.

The logic is strictly one of those two branches. There is no partial-sentinel
recovery; a file with only one sentinel present is treated as "absent" and
receives a fresh appended block.

## v2 block template

```
<!-- PORTFOLIO-STATUS-BEGIN — managed by /planning:portfolio rebuild; do not hand-edit -->
## Portfolio status

- **Home:** `<portfolio_home absolute path>`   (plans/backlog/maturity live here, not in this repo's docs/)
- **Plans:** see [plans/](<portfolio_home>/plans/)
- **Backlog:** see [backlog.md](<portfolio_home>/backlog.md)
- **Maturity:** see [MATURITY.md](<portfolio_home>/MATURITY.md)
- **Ship-ready:** see [global dashboard](<vault>/Portfolio/global-maturity.md)
- **⬆ Depends on:** [[X]] (why), [[Y]] (why)        ← upstreams this project relies on
- **⬇ Impacts:** [[B]] (why), [[C]] (why)            ← downstreams a change here may break
- **Inbound integration debt:** see [integration-backlog.md](<vault>/Portfolio/integration-backlog.md)
<!-- PORTFOLIO-STATUS-END -->
```

### Pointer-only, not snapshotted

The `Plans`, `Backlog`, `Maturity`, `Ship-ready`, and `Inbound integration
debt` lines are **links, not values**. The sidecar is committed in the repo and
therefore lags the live vault — any count or verdict embedded here (`N open`,
the maturity emoji row, `❌ no`, `K items`) goes stale the moment the vault's
`backlog.md` / `MATURITY.md` change, and a rebuild only re-syncs it on demand. A
reader who needs the current number opens the linked file, which is always
authoritative. Only the structural `Depends on` / `Impacts` wikilinks carry
inline content, because edges change rarely and are themselves the payload.

The `Plans` line points at `<portfolio_home>/plans/` (the directory, not
individual files), so every plan `planning-projects` saves there is discoverable
from the sidecar the instant it lands — no per-plan enumeration to maintain and
nothing to regenerate.

## Field sources

| Field | Source |
|---|---|
| `Home` | Resolver output: registry `area` + `name` fields mapped through `vault_dir` from `~/.claude/portfolio-config.yaml` → `<vault_dir>/Portfolio/<area>/<name>/`. This is the absolute `portfolio_home`. See registry-format.md, "Resolver" section, for the full mapping rule. |
| `Plans` | Static link to `<portfolio_home>/plans/` (the directory). Not enumerated — the link is constant for a project, so any plan saved into that dir (e.g. by `planning-projects`) is reachable without a rebuild. |
| `Backlog` | Static link to `<portfolio_home>/backlog.md`. Pointer only — the open-item count is **not** read or embedded (it would go stale against the live file). |
| `Maturity` | Static link to `<portfolio_home>/MATURITY.md`. Pointer only — the per-axis emoji row is **not** read or embedded. |
| `Ship-ready` | Static link to `<vault>/Portfolio/global-maturity.md`. Pointer only — the ✅/❌ verdict is **not** derived or embedded; the dashboard is authoritative. |
| `Depends on` | Read from this project's `<portfolio_home>/integration.md`, `depends_on:` section. Each entry is an Obsidian wikilink to the upstream project plus a one-phrase reason. Cross-checked for consistency against `<vault>/Portfolio/integration-graph.md`. |
| `Impacts` | Read from this project's `<portfolio_home>/integration.md`, `impacts:` section. Each entry is an Obsidian wikilink to the downstream project plus a one-phrase reason. Cross-checked against `integration-graph.md`. |
| `Inbound integration debt` | Static link to `<vault>/Portfolio/integration-backlog.md`. Pointer only — the item count is **not** embedded. |

## Why impacts/deps in the sidecar

When a developer opens project A, the session loads `.claude/vault-context.md`
immediately. The `⬇ Impacts` line surfaces right there — before any code is
read, before any edit is made — so the session knows that a change to A may
break B or C. Armed with that awareness, the agent (or the developer) can drop
a new integration backlog item directly into B's or C's vault backlog without
leaving the session. This is the impact-awareness the whole sidecar design
exists to deliver: not buried in a separate planning run, not discovered after
the fact, but visible at session-open time in the project where the change will
be made.

## Hard rules

- **No tombstone in the repo.** The sidecar (`.claude/vault-context.md`) is
  the only pointer that remains in the repo after migration. The repo's `docs/`
  directory is emptied as part of the vault migration: plans, backlog, and
  MATURITY all move to `<portfolio_home>/`. The sidecar block is therefore the
  sole surviving navigation aid from within the repo to its vault home. No
  additional pointer file is written into the repo.
- **Idempotent.** Re-running `/planning:portfolio rebuild` with no upstream
  change to the registry, backlog, maturity, or integration data must produce a
  byte-identical block. Field values are derived deterministically from their
  sources; no timestamps or run-IDs are embedded in the block.
- **Registry-gated.** Only projects listed in `~/.claude/projects-registry.yaml`
  with `enabled: true` receive a portfolio status block. If a repo is not in
  the registry, its `.claude/vault-context.md` is left completely untouched —
  the skill does not append, remove, or inspect the sidecar of unregistered
  repos.
