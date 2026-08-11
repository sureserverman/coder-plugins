# `migrate` — the one-time repo→vault move

The procedure behind `../SKILL.md` § `migrate` — move a project's operational docs from its
repo into the vault (one-time). The trunk states the safety property (copy → verify → delete,
all-or-nothing); this file is the steps.

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
5. Only after ALL files verify: remove the sources from the repo — `git rm` in a git work tree, plain `rm` in a non-git repo (per the preflight step). The repo source is the **last** thing removed — an interruption before this step always leaves the repo intact (copy→verify→delete invariant).
6. If `<repo>/docs/` is now empty, remove it. If other files remain, leave `docs/` and report what's left. **No tombstone** — the sidecar is the only pointer.
7. Write/refresh the repo sidecar `portfolio_home: <abs vault_home>` (contract: `../references/sidecar-format.md`).
8. Rewrite the migrated `MATURITY.md` detector evidence paths with a `repo:` prefix (they point at repo files, now read from the vault checklist).

Dry-run (`--all` without `--write`) prints, per project, the copy set and resolved target, flags already-populated targets as SKIP, and moves nothing. `--write` executes the procedure. Report: `migrated N, skipped M, failed K` with per-project sha256-verify status.

**Rollback** (per project): copy `vault_home`'s docs back to `<repo>/docs/` and `git checkout` the repo deletion (originals are in the repo's git history). Reversible because the vault keeps the files and the repo git keeps the deletions.
