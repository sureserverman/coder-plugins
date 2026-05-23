---
name: portfolio
description: Use to manage backlog and maturity across every project in ~/dev/ via a single command. Triggers on "portfolio scan", "global backlog", "unify plans and backlog", "maturity dashboard", "ship readiness across projects", "what's parked across projects", "what's missing before I can publish anything", "rebuild global backlog", "scan all my projects", "first-time portfolio setup". Default flow: scan registry drift → unify each project's plans into its backlog (dry-run) → audit per-project maturity → rebuild global roll-ups. Four subcommands: `scan`, `unify`, `maturity`, `rebuild`.
---

# Portfolio Orchestrator

Single user-facing skill that ties three things together across every project in `~/dev/`:

1. A canonical **registry** at `~/.claude/projects-registry.yaml` listing every tracked project. Schema in `references/registry-format.md`.
2. **Per-project unification** of `docs/plans/` ↔ `docs/backlog.md` via the `backlog` skill's `unify` subcommand. Parser rules in `references/plan-parser.md`.
3. **Per-project maturity audit** + roll-up via the `project-maturity` skill. Axes in `references/maturity-axes.md`.

Roll-up writes land at `~/.claude/global-backlog.md` and `~/.claude/global-maturity.md`. Format templates in `references/global-formats.md`.

**Announce at start:** "Using the portfolio skill — `<scan|unify|maturity|rebuild|default>`."

---

## Subcommands

### `scan` — load the registry, detect drift, optionally first-run-seed

Inputs: optional `--write` (default off — dry-run shows the proposed registry diff but doesn't persist).

Operation:

1. Read `~/.claude/projects-registry.yaml` (path documented in `references/registry-format.md`).
2. **First-run flow** — if the file does not exist:
   - Walk `~/dev/` for project markers: `find ~/dev -maxdepth 4 -type d -path '*/docs/plans' -o -path '*/docs/backlog.md'` (parent-of-`docs` is the project root; dedup by realpath).
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

### `rebuild` — regenerate the two global roll-up files

Inputs: optional `--globals-dir <path>` (default `~/.claude/`; override for testing).

Operation:

1. Load the registry (enabled-only — `enabled: false` projects are excluded from both globals).
2. Build `<globals-dir>/global-backlog.md` per `references/global-formats.md`:
   - For each project that has a `docs/backlog.md`, read the file. Emit a per-project section with the project's `area/name`, link to the backlog file path, open-entry count, and 3 newest titles.
   - **Preserve the `<! BEGIN PRESERVE !>` ... `<! END PRESERVE !>` block** from the existing file byte-for-byte. If the file doesn't exist (first rebuild), insert an empty preserve block.
   - Sort per-project sections by `area/name` ascending.
   - Render the `**Last rebuilt:**` timestamp ONLY if the regenerated content (excluding that line and the preserve block) differs from the prior file. This keeps reruns byte-identical when nothing changed — the §5 idempotency guarantee.
3. Build `<globals-dir>/global-maturity.md`:
   - For each project that has a `docs/MATURITY.md`, invoke `project-maturity get --format json` and render a table row per the template.
   - Cells use the legend in `references/global-formats.md` (🟢 auto, 🟡 claim, ⚪ N/A, 🔴 unticked, ❓ stale-detector).
   - `ship_ready` column from the `get` output's overall field.
4. Report: `Rebuilt: global-backlog.md (N projects), global-maturity.md (M projects). 0 writes` if both files are byte-identical to prior versions; otherwise list the changes.

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

## Remember

- `scan` → `unify` → `maturity` → `rebuild`. Default flow runs all four; subcommands are for drill-in.
- First-run flow seeds the registry and EXITS — no project files touched.
- Dry-run is the default; nothing writes without user confirm.
- Re-running with no upstream changes produces zero writes.
- The registry is the canonical project list; auto-walk runs every invocation to surface drift.
