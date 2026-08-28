---
name: portfolio
description: >
  Use to manage backlog, maturity, and ship-readiness across every project in ~/dev/ via a single command. Triggers on "portfolio scan", "global backlog", "maturity dashboard", "scan all my projects". Subcommands: scan, unify, maturity, migrate, integrate, rebuild, plan-status.
---

# Portfolio Orchestrator

Single user-facing skill that ties together every project in `~/dev/`:

1. A canonical **registry** at `~/.claude/projects-registry.yaml` listing every tracked project. Schema in `references/registry-format.md`.
2. **Per-project unification** of plans ↔ backlog via the `backlog` skill's `unify` subcommand. Parser rules in `references/plan-parser.md`.
3. **Per-project maturity audit** + roll-up via the `project-maturity` skill. Axes in `references/maturity-axes.md`.
4. **Inter-project integration** edges, symmetry, and cross-project arcs. Formats in `references/integration-format.md` and `references/integration-plan-format.md`.
5. **Architectural decisions**, per project and per architecture domain, rolled up to `global-decisions.md`. Format in `references/decisions-format.md`; authored through the `decisions` skill, never by this one.

**Vault-canonical storage.** Operational docs do NOT live in repos. Each project's plans, backlog, maturity, and integration edges live in the Obsidian vault under `<vault_dir>/Portfolio/<area>/<name>/`. Global roll-ups live at `<vault_dir>/Portfolio/global-{backlog,maturity,decisions}.md` plus `integration-graph.md` and `integration-backlog.md`. Format templates in `references/global-formats.md`.

## Resolver (read this before any read/write)

Every read/write to a project's operational docs goes through the resolver defined in `references/registry-format.md` — the LLM lane included, since the three plan-writing skills now call `scripts/resolve-plan-home.py` rather than resolving in prose (BL-101). One definition, not one in code and one in prose free to drift (DEC-011). Bound: a skill's call is still an instruction, so this removes the second *definition*, not the model's ability to skip the step.

```
repo ~/dev/<area>/<project>  →  <vault_dir>/Portfolio/<area>/<name>/
```

- `vault_dir` is read from `~/.claude/portfolio-config.yaml`.
- The repo's `.claude/vault-context.md` caches the resolved `portfolio_home`; the registry+convention is authoritative if they disagree.
- **No silent fallback.** If `vault_dir` is unset, every subcommand that would resolve a vault home **fails loudly** — print `portfolio not configured: set vault_dir in ~/.claude/portfolio-config.yaml` and refuse. NEVER write to `<repo>/docs/` — that would re-fragment the centralized docs.
- **A missing vault is not an empty vault — and an unmounted one is not missing.** A `vault_dir` that is *set* but unreachable is refused identically (`vault unreachable: …`), creating no part of the tree. Unreachable = absent, relative, not a path, unreadable (EACCES/ESTALE refuses, never tracebacks), **or existing with no `Portfolio/`** — what an unmounted mountpoint looks like, a mountpoint being a directory whether or not anything is mounted on it. The `Portfolio/` check is load-bearing: without it `migrate` builds a phantom vault at the mount point and moves a repo's only docs into it. Initialise a new vault by creating `<vault_dir>/Portfolio/` once, by hand. Read-only tools whose corpus IS the vault refuse too — an empty result reads as "nothing is in flight". Divergences: `references/registry-format.md`.

**Announce at start:** "Using the portfolio skill — `<scan|unify|maturity|migrate|integrate|rebuild|plan-status|default>`."

---

## Reference map

The trunk carries what binds every run, whatever was invoked. These load when their condition is met — read the one you need rather than working from memory.

| Read this | When |
|---|---|
| `references/subcommand-scan.md` | running `scan` — first-run seeding, drift detection |
| `references/subcommand-unify.md` | running `unify` — the fan-out and its report |
| `references/subcommand-maturity.md` | running `maturity`, or why the default flow gates it |
| `references/subcommand-migrate.md` | running `migrate` — steps, preflight skips, rollback |
| `references/subcommand-integrate.md` | running `integrate` |
| `references/subcommand-rebuild.md` | running `rebuild` — the eight steps and both layers |
| `references/subcommand-plan-status.md` | running `plan-status` — classes, evidence grades |
| `references/registry-format.md` | the registry schema, or resolving a repo's vault home |
| `references/plan-parser.md` | a plan is parsed for backlog candidates |
| `references/maturity-axes.md` | reading or writing a MATURITY.md axis |
| `references/global-formats.md` | writing `global-backlog.md` / `global-maturity.md` |
| `references/decisions-format.md` | writing `global-decisions.md` |
| `references/global-security-format.md` | writing `global-security.md` |
| `references/sidecar-format.md` | writing a repo's `vault-context.md` block |
| `references/integration-format.md` | reading or writing a project's `integration.md` |
| `references/integration-plan-format.md` | an integration arc under `Portfolio/integrations/` |
| `references/integration.md` | routing an ask to a neighbouring skill |

---

## Subcommands

An explicit invocation runs exactly one; the default flow composes four, one of them gated (§ Staged rollout). Each procedure lives in its own reference.

### `scan` — load the registry, detect drift, optionally first-run-seed

Loads `~/.claude/projects-registry.yaml`, seeds it on first run and then **exits** (the user re-invokes for the actual work), and on every later run re-walks `~/dev/` and reports drift for add/remove/skip. The registry changes only on user confirm AND `--write`. Procedure: `references/subcommand-scan.md`.

### `unify` — derive backlog candidates for every enabled project, in parallel

Dispatches one sub-agent per enabled project (up to 8 in flight) via `dispatching-parallel-agents`, each invoking the `backlog` skill's `unify`; the aggregated per-project report is presented for accept-all / pick-some / skip-project, and only then does a second wave run `backlog add`. **Never write during dry-run.** Procedure: `references/subcommand-unify.md`.

### `maturity` — audit per-project MATURITY.md and surface staleness

Fans out `project-maturity audit --write` per project (same 8-in-flight cap), then reports stale manual claims (>90 days) and `[?] stale-detector` markers, which block ship-ready. **A project with no MATURITY.md is skipped, not scaffolded**, unless `--init-missing` is passed. Procedure: `references/subcommand-maturity.md`.

### `migrate` — move a project's operational docs from its repo into the vault (one-time)

Moves `<repo>/docs/plans/*`, `docs/backlog.md` and `docs/MATURITY.md` into the resolved vault home. **All-or-nothing, and the invariant is copy → verify → delete:** COPY every file, VERIFY `sha256(source) == sha256(destination)` for each, and only then remove the repo sources — so an interruption always leaves the repo intact, and any mismatch aborts that project, deletes the partial vault copies and leaves the repo untouched. Never `git mv`, never a bare `mv`; dry-run unless `--write`. A vault home that already holds `plans/`, `backlog.md` or `MATURITY.md` is SKIPPED for manual resolution — **never overwritten or merged**. Per-project procedure, the other preflight skips and rollback: `references/subcommand-migrate.md`.

### `integrate` — roll up inter-project edges + integration backlog

Rolls every project's `integration.md` up into `Portfolio/integration-graph.md` and `Portfolio/integration-backlog.md`. **Symmetry rule:** if A declares `impacts: [[B]]`, B must declare `depends_on: [[A]]` (and vice-versa) — asymmetries are **reported, never auto-fixed**; the user resolves by editing one side. Dry-run by default; `--write` persists. Procedure: `references/subcommand-integrate.md`.

### `rebuild` — regenerate the global roll-ups (in the vault) + enrich sidecars

Regenerates the vault-canonical roll-ups — `global-backlog.md`, `global-decisions.md`, `global-maturity.md`, plus the business and security dashboards — and refreshes every repo's `PORTFOLIO-STATUS` sidecar block. Refuses if `vault_dir` is unset. Three rules bind it whatever else changes: the hand-curated `<!-- BEGIN PRESERVE -->` block survives **byte-for-byte**; an absent or failed business/security layer degrades to one `<layer>: unavailable` line and **never truncates an existing roll-up**; an unrecorded security count renders `?` and **never `0`** (unmeasured is not clean). Eight-step procedure: `references/subcommand-rebuild.md`.

### `plan-status` — reconcile every vault plan's recorded status against its real progress

Runs `scripts/plan-status-audit.py` over every plan in the vault. **Report-first: the default invocation writes nothing.** `--fix` presents one candidate at a time with its graded evidence and requires a per-plan `y`, taking a timestamped backup under `plans/.audit-backups/<run-id>/` first — `--restore <run-id>` is the only undo the vault has. A plan carrying a bracketed `Status:` marker outside `[ xX~]` is **never offered as a completion candidate, under any flag**, and the audit **never infers `**Abandoned:**`**. Classification order and evidence grades: `references/subcommand-plan-status.md`.

### Default flow (no subcommand, or explicit `portfolio` invocation)

Composes the four ops in order: `scan` → `unify --dry-run` → `maturity` (with the `--include-maturity` gate, see `## Staged rollout`) → `rebuild`. Confirms with the user before any mutation. Exit when done; user can re-invoke individual subcommands to drill in.

**Idempotency guarantee:** if nothing has changed upstream (no new plans, no plan edits, no manual-claim refreshes), a second consecutive `portfolio` run produces ZERO writes — registry, per-project backlogs, MATURITY files, and both globals are byte-identical between runs. This is the design doc's section 5 hard guarantee.

---

## Staged rollout

The `project-maturity` skill is shipped but excluded from the default `portfolio` flow for a staging window (~one week). During the staging window:

- `portfolio maturity` (explicit subcommand invocation) works normally.
- `portfolio` (default flow) skips the maturity step UNLESS `--include-maturity` is passed.

Why the gate exists and what changes when the window closes: `references/subcommand-maturity.md`.

---

## Configuration: `~/.claude/portfolio-config.yaml`

Optional config sidecar to the registry. Holds settings that aren't per-project:

```yaml
# ~/.claude/portfolio-config.yaml
version: 1
vault_dir: /mnt/vault         # required; roll-ups land in <vault_dir>/Portfolio/
include_maturity: false       # default flow opts out of maturity until staging window ends
```

Every key is optional except `vault_dir`. A missing file means the maturity opt-out plus an **unset** `vault_dir` — a hard refusal under the Resolver rules at the top of this file, never a fallback. The `~/.claude/` mirror this section used to describe was retired when storage went vault-canonical, so there is no longer a degraded mode to fall back to.

A `vault_dir` that is *set* but unreachable is settled: **the same refusal** (Resolver, above). It is not the lesser failure — unset has no destination to get wrong, while a stale or unmounted path is one `mkdir -p` from a plausible second vault.

## File conflicts and write discipline

Two write surfaces this skill controls directly: `~/.claude/projects-registry.yaml` (registry) and `<vault>/Portfolio/global-{backlog,maturity}.md` (globals). Two write surfaces it controls *indirectly* via sub-skills: per-project `docs/backlog.md` (via `backlog add`) and per-project `docs/MATURITY.md` (via `project-maturity audit --write`).

Hard rules:

- Never mutate a project's `docs/` directly. Always delegate to `backlog` or `project-maturity`.
- The registry is read-mostly; only `scan --write` modifies it, and only on user confirm.
- Parallel sub-agents write to DIFFERENT projects' files; no two agents touch the same path. Verified by the registry being a flat list (no project nesting).

## Hard rules

- Dry-run is the default for every write-capable subcommand.
- The first-run flow never touches project files. It only writes the registry, and only after user confirm.
- Drift is reported on every run, even when there is none — the report header is the proof the check happened.
- The 8-in-flight cap on parallel sub-agents is non-negotiable; not configurable from CLI.
- `enabled: false` projects appear in `scan` output but are excluded from `unify`, `maturity`, and `rebuild`.

## Integration

Routes to `planning-projects` and `executing-plans` (which produce and tick the plans `unify` parses), `backlog` and `project-maturity` (invoked per-project via sub-agent), `dispatching-parallel-agents` (the fan-out), and `compass` (which reads, never writes, the artifacts this skill maintains). What each is for: `references/integration.md`.

## Remember

- `scan` → `unify` → `maturity` → `rebuild`. Default flow runs all four; subcommands are for drill-in.
- First-run flow seeds the registry and EXITS — no project files touched.
- Dry-run is the default; nothing writes without user confirm.
- Re-running with no upstream changes produces zero writes.
- The registry is the canonical project list; auto-walk runs every invocation to surface drift.
