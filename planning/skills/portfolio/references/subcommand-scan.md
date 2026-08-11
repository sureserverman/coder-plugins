# `scan` — first-run seeding and drift detection

The procedure behind `../SKILL.md` § `scan` — load the registry, detect drift, optionally
first-run-seed. In the default flow this is step 1: surface drift; if `--write` is confirmed,
update the registry.

Inputs: optional `--write` (default off — dry-run shows the proposed registry diff but doesn't persist).

Operation:

1. Read `~/.claude/projects-registry.yaml` (path documented in `../references/registry-format.md`).
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
