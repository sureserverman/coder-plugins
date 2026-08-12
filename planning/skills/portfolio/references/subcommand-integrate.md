# `integrate` — the inter-project rollup

The procedure behind `../SKILL.md` § `integrate` — roll up inter-project edges + integration
backlog.

Inputs: optional `--write` (off by default).

**Run the shipped tool rather than executing these steps by hand:** `python3 ../scripts/portfolio-integrate.py [--write]` implements all four — adjacency, symmetry check, dangling targets, the tagged-backlog rollup, and both writes. The numbered procedure is that script's contract: read it to check what a run produced, not to reproduce the work.

1. Read every `<vault>/Portfolio/<area>/<name>/integration.md` (schema in `../references/integration-format.md`).
2. Build `Portfolio/integration-graph.md`: the `depends_on → upstream` adjacency, plus a `## Asymmetries (review)` section. **Symmetry rule:** if A declares `impacts: [[B]]`, B must declare `depends_on: [[A]]` (and vice-versa). Asymmetries are reported, **never auto-fixed** — the user resolves by editing one side. Targets that aren't registered projects are flagged under `## Unresolved targets` (dangling) but don't block the rollup.
3. Build `Portfolio/integration-backlog.md`: scan every project's `backlog.md` for entries tagged `integration` (or carrying an `Integration:` line); group them by `edge=<slug>` / `plan=<arc>`. Cross-project rollup view; the items themselves stay in their project's backlog.
4. Integration plans live under `Portfolio/integrations/<arc>/` (schema in `../references/integration-plan-format.md`); each spanned project's backlog carries an `Integration: plan=<arc>` pointer, which this rollup surfaces.

Dry-run by default; `--write` persists the two generated files.
