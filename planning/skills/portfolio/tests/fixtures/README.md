# Portfolio test fixtures

Three fake project trees used by `unify` / `maturity` / `portfolio` hand-tests.

**Layout note:** real projects keep plans under `docs/plans/`. Fixture plans
live under `docs/sample-plans/` because the repo-wide pre-commit hook (sourced
from `~/.git-templates/gitignore`) unconditionally un-tracks anything under
a literal `plans/` directory. Hand-tests of `unify` therefore must pass
`--plans-dir docs/sample-plans` (or set `PORTFOLIO_PLANS_DIR=docs/sample-plans`)
when invoked against these fixtures. Production runs on `~/dev/` use the
default `docs/plans`.

- `proj-a-plans-and-backlog/` — two plans (one fully-checked, one with 2
  unchecked tasks + a Deferred entry) and an existing `docs/backlog.md`
  whose `BL-001` Source matches the partial plan's `Task 2.1`. Tests:
  multi-plan parsing, Deferred-section parsing, dedup-by-Source.

- `proj-b-plans-only/` — one plan with 3 unchecked tasks, no backlog yet.
  Tests: backlog auto-creation, multi-task candidate emission.

- `proj-c-bare/` — `docs/` exists but no `plans/` and no `backlog.md`.
  Tests: negative control — scanner must NOT classify this as a project.

Expected from a unify pass over `proj-a-plans-and-backlog`:

- 0 candidates from `2026-04-01-all-checked-plan.md` (all checked)
- 2 candidates from `2026-04-15-partial-with-deferred-plan.md`:
  - `Stage 2 / Task 2.2` (unchecked) — NEW
  - `Deferred / bullet 1` (deferred-section) — NEW
  - `Stage 2 / Task 2.1` (unchecked) — DROPPED by dedup (matches BL-001 Source)

Expected from a unify pass over `proj-b-plans-only`:

- 3 candidates from `2026-05-01-three-unchecked-plan.md`, all `unchecked-task` signal.
- `docs/backlog.md` auto-created with the existing-backlog template.

Expected from a scan over the fixtures dir:

- `proj-a-...` and `proj-b-...` classified as projects.
- `proj-c-bare/` NOT classified (no `docs/sample-plans/` and no `docs/backlog.md`).
