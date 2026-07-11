---
name: portfolio
description: >
  Use to manage backlog and maturity across every project in ~/dev/ via a single command. Triggers on "portfolio scan", "global backlog", "unify plans and backlog", "maturity dashboard", "ship readiness across projects", "what's parked across projects", "what's missing before I can publish anything", "rebuild global backlog", "scan all my projects", "first-time portfolio setup", "migrate docs to vault", "integration graph", "what does this project impact". Subcommands: `scan`, `unify`, `maturity`, `migrate`, `integrate`, `rebuild`.
---

# Portfolio Orchestrator

Single user-facing skill that ties together every project in `~/dev/`:

1. A canonical **registry** at `~/.claude/projects-registry.yaml` listing every tracked project. Schema in `references/registry-format.md`.
2. **Per-project unification** of plans ↔ backlog via the `backlog` skill's `unify` subcommand. Parser rules in `references/plan-parser.md`.
3. **Per-project maturity audit** + roll-up via the `project-maturity` skill. Axes in `references/maturity-axes.md`.
4. **Inter-project integration** edges, symmetry, and cross-project arcs. Formats in `references/integration-format.md` and `references/integration-plan-format.md`.

**Vault-canonical storage.** Operational docs do NOT live in repos. Each project's plans, backlog, maturity, and integration edges live in the Obsidian vault under `<vault_dir>/Portfolio/<area>/<name>/`. Global roll-ups live at `<vault_dir>/Portfolio/global-{backlog,maturity}.md` plus `integration-graph.md` and `integration-backlog.md`. Format templates in `references/global-formats.md`.

## Resolver (read this before any read/write)

Every read/write to a project's operational docs goes through the resolver defined in `references/registry-format.md`:

```
repo ~/dev/<area>/<project>  →  <vault_dir>/Portfolio/<area>/<name>/
```

- `vault_dir` is read from `~/.claude/portfolio-config.yaml`.
- The repo's `.claude/vault-context.md` caches the resolved `portfolio_home`; the registry+convention is authoritative if they disagree.
- **No silent fallback.** If `vault_dir` is unset, every subcommand that would resolve a vault home **fails loudly** — print `portfolio not configured: set vault_dir in ~/.claude/portfolio-config.yaml` and refuse. NEVER write to `<repo>/docs/` — that would re-fragment the centralized docs.

**Announce at start:** "Using the portfolio skill — `<scan|unify|maturity|migrate|integrate|rebuild|default>`."

---

## Subcommands

### `scan` — load the registry, detect drift, optionally first-run-seed

Inputs: optional `--write` (default off — dry-run shows the proposed registry diff but doesn't persist).

Operation:

1. Read `~/.claude/projects-registry.yaml` (path documented in `references/registry-format.md`).
2. **First-run flow** — if the file does not exist:
   - Walk `~/dev/` for project markers. A directory is classified as a project root if any of these three markers exists beneath it:
     1. `docs/plans/` directory (has staged-plan output from `planning-projects`)
     2. `docs/backlog.md` file (has the deferred-work register)
     3. `.claude/vault-context.md` file (has been linked to the Obsidian vault by `vault-context:link` — strong "this is a real project I track" signal even when planning hasn't started)
     Walk command: `find ~/dev -maxdepth 4 \( -type d -path '*/docs/plans' -o -type f -path '*/docs/backlog.md' -o -type f -path '*/.claude/vault-context.md' \)`. Parent-of-`docs` OR parent-of-`.claude` is the project root; dedup by realpath.
   - Build candidate registry entries with auto-derived fields per the schema: `path` (absolute), `name` (final segment, slug), `area` (immediate child of `~/dev/`), `enabled: true`, `added: <today>`.
   - Present the list to the user for pruning; on user confirm, write `~/.claude/projects-registry.yaml` for the very first time. **This is the only write `scan` performs during first-run.** No project files touched, no globals built.
   - Exit; user re-invokes `portfolio` (or one of its other subcommands) for the actual work.
3. **Subsequent runs — drift detection** — registry exists:
   - Re-walk `~/dev/` as in step 2.
   - Compute `found_not_in_registry: [paths]` and `registered_but_missing_on_disk: [paths]`.
   - Print a drift report header even when both lists are empty (so the user knows the check happened).
   - For each drifted entry, prompt: add (new) / remove (missing) / skip.
   - On user confirm AND `--write`, update the registry; otherwise leave it alone.

Drift reporting is the mitigation for the "registry rots" failure mode — every `portfolio` invocation surfaces it before doing anything else.

### `unify` — derive backlog candidates for every enabled project, in parallel

Inputs: optional `--project <abs-path>` (limit to one project), optional `--include-stale` (pass through to backlog skill), optional `--write` (default off).

Operation:

1. Load the registry; filter to entries with `enabled: true`. If `--project` is set, narrow to that one.
2. For each project (up to 8 in flight), dispatch a sub-agent via the **dispatching-parallel-agents** skill. Each sub-agent invokes the `backlog` skill's `unify` subcommand on its project. The default `--plans-dir docs/plans` applies; sub-agent passes `--plans-dir docs/sample-plans` when the project path is under `planning/skills/portfolio/tests/fixtures/` (this is the gitignore-workaround documented in `tests/fixtures/README.md`).
3. Each sub-agent returns its `{candidates, existing, duplicates_skipped}` structure.
4. Aggregate into a tree-shaped report grouped by `area/name`:

   ```
   anon-tools/multitor (8 existing, 0 duplicates skipped, 2 new candidates):
     + Stage 3 / Task 3.2     (unchecked-task)  Wire MT slot frames through evdev
     + Deferred / bullet 1    (deferred-section) Bluetooth HID jitter support
   android/and-hole (3 existing, 1 duplicate skipped, 0 new candidates):
     (no new candidates)
   ...
   ```

5. Present to user — they pick accept-all / pick-some-per-project / skip-project.
6. On accept, dispatch a second wave of sub-agents (same 8-in-flight cap) — each runs `backlog add` for that project's accepted candidates. **Never write during dry-run.**

**Hard rules for `unify`:**

- Dry-run is the default. `--write` is the only path to file mutations, and even then candidates must come from a user-confirmed list (the prompt in step 5 IS the confirm).
- The 8-in-flight cap on parallel sub-agents prevents accidentally fan-out-DOS'ing a slow filesystem (e.g. NFS-mounted vault, slow CI runner).

### `maturity` — audit per-project MATURITY.md and surface staleness

Inputs: optional `--project <abs-path>`, optional `--init-missing` (off by default; when set, projects with no MATURITY.md get `project-maturity init` invoked instead of skipped).

Operation:

1. Load the registry (enabled-only, optionally narrowed by `--project`).
2. For each project, dispatch a sub-agent (same 8-in-flight cap) that invokes the `project-maturity` skill's `audit` subcommand (with `--write`). The sub-agent additionally runs `get --format json` to obtain the parsed state for the roll-up.
3. Aggregate. Report:
   - Per-project audit summary lines.
   - List of stale manual claims (>90 days old) across all projects, with `project: axis: item: claim-date`.
   - List of projects with `[?] stale-detector` markers — these block ship-ready and warrant inspection.
4. Prompt the user to refresh/keep stale claims (per project).

`--init-missing` exists for the staged maturity rollout (see `## Staged rollout`). Default behavior is to skip projects without a MATURITY.md so first-time portfolio runs aren't a hard prerequisite of "scaffold 30 maturity files at once."

### `migrate` — move a project's operational docs from its repo into the vault (one-time)

Inputs: `--project <abs-path>` (one project) or `--all` (every enabled project); `--write` (off by default — dry-run prints the plan and moves nothing).

Moves `<repo>/docs/plans/*`, `<repo>/docs/backlog.md`, and `<repo>/docs/MATURITY.md` into the resolved `<vault_dir>/Portfolio/<area>/<name>/`. The vault is **not git-tracked** (NFS-shared Obsidian), so this is a filesystem move with a verification gate — never `git mv`, never a bare `mv`.

Per-project procedure (all-or-nothing):

1. Resolve `vault_home` via the resolver; `mkdir -p vault_home/plans`.
2. **Preflight the project:**
   - If `vault_home` already holds `plans/` or `backlog.md` or `MATURITY.md`, SKIP with `vault home already populated; resolve manually` (never overwrite/merge).
   - **Dirty-guard (refined):** SKIP only if the migrate set contains a *tracked* file with **uncommitted modifications** (`git status --porcelain` shows ` M`/`MM`/`A ` for it) — those edits have no clean committed fallback and could be lost. *Untracked new files* (status `??`, e.g. a freshly-generated `MATURITY.md`) are fine to migrate: their content moves to the vault and nothing committed is lost. Pure-untracked migrate sets do NOT trigger the skip.
   - **Non-git repos:** if `<project-path>` is not a git work tree, migration still proceeds, but step 5 uses plain `rm` (not `git rm`) and the report flags `no-git-fallback` for that project — the vault copy is then the *only* copy (the copy→verify gate is the sole safety net; there is no repo-git archaeology fallback). Acceptable for stub/scratch repos; surfaced so the user knows.
3. **COPY** each source file → its vault destination (plans into `plans/`, `backlog.md` and `MATURITY.md` at the project root). Migrate set = whatever exists: plans always; `backlog.md` and `MATURITY.md` only if present.
4. **VERIFY** — for every copied file, assert `sha256(source) == sha256(destination)`. This is the load-bearing gate; over NFS a truncated write is the realistic failure. Any mismatch → abort this project, delete the partial vault copies, leave the repo untouched, report.
5. Only after ALL files verify: remove the sources from the repo — `git rm` in a git work tree, plain `rm` in a non-git repo (see preflight). The repo source is the **last** thing removed — an interruption before this step always leaves the repo intact (copy→verify→delete invariant).
6. If `<repo>/docs/` is now empty, remove it. If other files remain, leave `docs/` and report what's left. **No tombstone** — the sidecar is the only pointer.
7. Write/refresh the repo sidecar `portfolio_home: <abs vault_home>`.
8. Rewrite the migrated `MATURITY.md` detector evidence paths with a `repo:` prefix (they point at repo files, now read from the vault checklist).

Dry-run (`--all` without `--write`) prints, per project, the copy set and resolved target, flags already-populated targets as SKIP, and moves nothing. `--write` executes the procedure. Report: `migrated N, skipped M, failed K` with per-project sha256-verify status.

**Rollback** (per project): copy `vault_home`'s docs back to `<repo>/docs/` and `git checkout` the repo deletion (originals are in the repo's git history). Reversible because the vault keeps the files and the repo git keeps the deletions.

### `integrate` — roll up inter-project edges + integration backlog

Inputs: optional `--write` (off by default).

1. Read every `<vault>/Portfolio/<area>/<name>/integration.md` (schema in `references/integration-format.md`).
2. Build `Portfolio/integration-graph.md`: the `depends_on → upstream` adjacency, plus a `## Asymmetries (review)` section. **Symmetry rule:** if A declares `impacts: [[B]]`, B must declare `depends_on: [[A]]` (and vice-versa). Asymmetries are reported, **never auto-fixed** — the user resolves by editing one side. Targets that aren't registered projects are flagged under `## Unresolved targets` (dangling) but don't block the rollup.
3. Build `Portfolio/integration-backlog.md`: scan every project's `backlog.md` for entries tagged `integration` (or carrying an `Integration:` line); group them by `edge=<slug>` / `plan=<arc>`. Cross-project rollup view; the items themselves stay in their project's backlog.
4. Integration plans live under `Portfolio/integrations/<arc>/` (schema in `references/integration-plan-format.md`); each spanned project's backlog carries an `Integration: plan=<arc>` pointer, which this rollup surfaces.

Dry-run by default; `--write` persists the two generated files.

### `rebuild` — regenerate the global roll-ups (in the vault) + enrich sidecars

Inputs: optional `--write` (off by default). Reads `vault_dir` from `~/.claude/portfolio-config.yaml`; refuses if unset (no silent fallback).

The global roll-ups are **canonical in the vault** at `<vault_dir>/Portfolio/`. There is no `~/.claude/` or `Projects/` copy (those were retired when storage went vault-canonical).

Operation:

1. Load the registry (enabled-only — `enabled: false` projects are excluded).
2. Build `<vault_dir>/Portfolio/global-backlog.md` per `references/global-formats.md`:
   - For each project whose vault home has a `backlog.md`, emit a per-project section: `### <area>/[[<name>]] — N open`, the absolute backlog path, and the 3 newest entry titles. Project names are `[[wikilinks]]`.
   - Use the format-tolerant entry counter (h2/h3 `BL-NNN` + legacy freeform; see `references/global-formats.md`).
   - **Preserve the `<!-- BEGIN PRESERVE -->` ... `<!-- END PRESERVE -->` block** (the hand-curated `## Cross-project items`) byte-for-byte.
   - Sort by `area/name`. Render `**Last rebuilt:**` only when the rest of the content changed (idempotency).
3. Build `<vault_dir>/Portfolio/global-maturity.md`: a table row per project that has a vault `MATURITY.md`, names as `[[wikilinks]]`, cells per the sparse-model legend, `ship_ready` from the per-axis thresholds.
4. **Sidecar enrichment (v2)** — for every registered project, write the sentinel-delimited block into `<repo>/.claude/vault-context.md` (create the file if absent) per `references/sidecar-format.md`:
   ```
   <!-- PORTFOLIO-STATUS-BEGIN — managed by /planning:portfolio rebuild; do not hand-edit -->
   ## Portfolio status

   - **Home:** `<portfolio_home>`   (plans/backlog/maturity live here, not in this repo's docs/)
   - **Plans:** see [plans/](<portfolio_home>/plans/)
   - **Backlog:** see [backlog.md](<portfolio_home>/backlog.md)
   - **Maturity:** see [MATURITY.md](<portfolio_home>/MATURITY.md)
   - **Ship-ready:** see [global dashboard](<vault_dir>/Portfolio/global-maturity.md)
   - **⬆ Depends on:** [[X]] (why), …          (from this project's integration.md, if any)
   - **⬇ Impacts:** [[B]] (why), …             (from integration.md, if any)
   - **Inbound integration debt:** see [integration-backlog.md](<vault_dir>/Portfolio/integration-backlog.md)
   <!-- PORTFOLIO-STATUS-END -->
   ```
   Pointer-only: counts/verdicts (backlog, maturity, ship-ready, debt) are NOT snapshotted into the block — the repo-committed sidecar lags the live vault, so the lines link to the source files instead. The static **Plans:** pointer makes any plan saved under `<portfolio_home>/plans/` discoverable without a rebuild. Full contract in `references/sidecar-format.md`. Replace between sentinels if present; else append with a blank-line separator. Never touch content outside the block. Idempotent.
5. **Business layer (optional, additive)** — if the sibling **business** plugin is installed (the `portfolio-rebuild.py` probe resolves `business/scripts/business-scan.py` under the marketplace root and finds it), `rebuild` also regenerates `<vault_dir>/Portfolio/global-business.md` by piping `business-scan.py | business-rollup.py` (per the business plugin's `global-business-format.md`). When the business plugin is **absent**, this step is skipped with a single `business layer: unavailable` line and nothing else changes — the global-backlog / global-maturity / sidecar outputs are byte-identical either way (guarded by `tests/test-business-degradation.py`). `portfolio-rebuild.py` handles this probe; the roll-up is never truncated on a failed business sweep.
6. Report: `Rebuilt: global-backlog.md (N), global-maturity.md (M), sidecars enriched: K` plus the business-layer status. (0 writes when everything matches prior content.)

### Default flow (no subcommand, or explicit `portfolio` invocation)

Composes the four ops in order: `scan` → `unify --dry-run` → `maturity` (with the `--include-maturity` gate, see `## Staged rollout`) → `rebuild`. Confirms with the user before any mutation. Exit when done; user can re-invoke individual subcommands to drill in.

Sequence:

```
1. scan          — surface drift; if --write confirmed, update registry
2. unify         — surface candidates per project; on confirm, accepted
                   candidates land in their per-project backlog.md
3. maturity      — only if --include-maturity is set (default off during
                   the staged rollout window); audit existing MATURITY.md,
                   surface stale claims for refresh
4. rebuild       — regenerate the two global files; report writes
```

**Idempotency guarantee:** if nothing has changed upstream (no new plans, no plan edits, no manual-claim refreshes), a second consecutive `portfolio` run produces ZERO writes — registry, per-project backlogs, MATURITY files, and both globals are byte-identical between runs. This is the §5 hard guarantee from the design doc.

---

## Staged rollout

Per the design's §7 rollout step 4: the `project-maturity` skill is shipped but excluded from the default `portfolio` flow for a staging window (~one week). During the staging window:

- `portfolio maturity` (explicit subcommand invocation) works normally.
- `portfolio` (default flow) skips the maturity step UNLESS `--include-maturity` is passed.

This prevents the default flow from dumping 30 unfilled checklist scaffolds in front of you on day one. After the staging window, the default flow's `## Default flow` description above is updated to drop the gate; `--include-maturity` becomes a no-op.

Disabled by default; opt-in via `--include-maturity` during the staged rollout window.

---

## Configuration: `~/.claude/portfolio-config.yaml`

Optional config sidecar to the registry. Holds settings that aren't per-project:

```yaml
# ~/.claude/portfolio-config.yaml
version: 1
vault_dir: /mnt/vault         # if set, rebuild mirrors globals to <vault_dir>/Projects/
include_maturity: false       # default flow opts out of maturity until staging window ends
```

All keys optional. Missing file → all defaults (no vault mirror, maturity opt-out). If `vault_dir` is set but the directory doesn't exist, the rebuild logs a one-line warning and continues with `~/.claude/` writes only — never aborts.

## File conflicts and write discipline

Two write surfaces this skill controls directly: `~/.claude/projects-registry.yaml` (registry) and `~/.claude/global-{backlog,maturity}.md` (globals). Two write surfaces it controls *indirectly* via sub-skills: per-project `docs/backlog.md` (via `backlog add`) and per-project `docs/MATURITY.md` (via `project-maturity audit --write`).

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

- **planning-projects** — produces the plan files that `unify` parses for backlog candidates.
- **executing-plans** — checks off Task N.N items as work lands; `unify` re-runs against the updated plans.
- **backlog** — invoked per-project via sub-agent for `unify` candidate generation and `add` accepted entries.
- **project-maturity** — invoked per-project via sub-agent for `audit` and `get`.
- **dispatching-parallel-agents** — used for the parallel per-project fan-out in `unify` and `maturity`.
- **compass** — "what should I work on next" / "what's in flight" / periodic-review asks route to the `compass` skill, which reads (never writes) the artifacts this skill maintains.

## Remember

- `scan` → `unify` → `maturity` → `rebuild`. Default flow runs all four; subcommands are for drill-in.
- First-run flow seeds the registry and EXITS — no project files touched.
- Dry-run is the default; nothing writes without user confirm.
- Re-running with no upstream changes produces zero writes.
- The registry is the canonical project list; auto-walk runs every invocation to surface drift.
