# `rebuild` — the eight steps, and the business/security layers

The procedure behind `../SKILL.md` § `rebuild` — regenerate the global roll-ups (in the vault)
+ enrich sidecars. In the default flow this is step 4: regenerate the global roll-ups; report
writes.

Inputs: optional `--write` (off by default). Reads `vault_dir` from `~/.claude/portfolio-config.yaml`; refuses if unset (no silent fallback).

The global roll-ups are **canonical in the vault** at `<vault_dir>/Portfolio/`. There is no `~/.claude/` or `Projects/` copy (those were retired when storage went vault-canonical).

Operation:

1. Load the registry (enabled-only — `enabled: false` projects are excluded).
2. Build `<vault_dir>/Portfolio/global-backlog.md` per `../references/global-formats.md`:
   - For each project whose vault home has a `backlog.md`, emit a per-project section: `### <area>/[[<name>]] — N open`, the absolute backlog path, and the 3 newest entry titles. Project names are `[[wikilinks]]`.
   - Use the format-tolerant entry counter (h2/h3 `BL-NNN` + legacy freeform; see `../references/global-formats.md`).
   - **Preserve the `<!-- BEGIN PRESERVE -->` ... `<!-- END PRESERVE -->` block** (the hand-curated `## Cross-project items`) byte-for-byte.
   - Sort by `area/name`. Render `**Last rebuilt:**` only when the rest of the content changed (idempotency).
3. Build `<vault_dir>/Portfolio/global-decisions.md` per `../references/decisions-format.md`: a by-domain index of every `Portfolio/decisions/<domain>.md` register, a per-project count table (total / accepted / superseded) from each `<home>/decisions.md`, and three review sections — `Malformed entries`, `Asymmetries`, `Unresolved targets`. Link asymmetries between a project's `Global:` and a domain's `Applies to:` are **reported, never auto-fixed**: repairing one side would assert an edge about a project the run has not read, the same rule `integrate` follows. A project with no register contributes nothing and is not an error.
4. Build `<vault_dir>/Portfolio/global-maturity.md`: a table row per project that has a vault `MATURITY.md`, names as `[[wikilinks]]`, cells per the sparse-model legend, `ship_ready` from the per-axis thresholds.
5. **Sidecar enrichment (v2)** — for every registered project, write the sentinel-delimited block into `<repo>/.claude/vault-context.md` (create the file if absent) per `../references/sidecar-format.md`:
   ```
   <!-- PORTFOLIO-STATUS-BEGIN — managed by /planning:portfolio rebuild; do not hand-edit -->
   ## Portfolio status

   - **Home:** `<portfolio_home>`   (plans/backlog/maturity live here, not in this repo's docs/)
   - **Plans:** see [plans/](<portfolio_home>/plans/)
   - **Backlog:** see [backlog.md](<portfolio_home>/backlog.md)
   - **Maturity:** see [MATURITY.md](<portfolio_home>/MATURITY.md)
   - **Ship-ready:** see [global dashboard](<vault_dir>/Portfolio/global-maturity.md)
   - **Decisions:** see [decisions.md](<portfolio_home>/decisions.md)   (only when the file exists)
   - **⬆ Depends on:** [[X]] (why), …          (from this project's integration.md, if any)
   - **⬇ Impacts:** [[B]] (why), …             (from integration.md, if any)
   - **Inbound integration debt:** see [integration-backlog.md](<vault_dir>/Portfolio/integration-backlog.md)
   <!-- PORTFOLIO-STATUS-END -->
   ```
   Pointer-only: counts/verdicts (backlog, maturity, ship-ready, decisions, debt) are NOT snapshotted into the block — the repo-committed sidecar lags the live vault, so the lines link to the source files instead. The static **Plans:** pointer makes any plan saved under `<portfolio_home>/plans/` discoverable without a rebuild. Full contract in `../references/sidecar-format.md`. Replace between sentinels if present; else append with a blank-line separator. Never touch content outside the block. Idempotent.
6. **Business layer (optional, additive)** — if the sibling **business** plugin is installed (the `portfolio-rebuild.py` probe resolves `business/scripts/business-scan.py` under the marketplace root and finds it), `rebuild` also regenerates `<vault_dir>/Portfolio/global-business.md` by piping `business-scan.py | business-rollup.py` (per the business plugin's `global-business-format.md`). When the business plugin is **absent**, this step is skipped with a single `business layer: unavailable` line and nothing else changes — the global-backlog / global-maturity / sidecar outputs are byte-identical either way (guarded by `../tests/test-business-degradation.py`). `portfolio-rebuild.py` handles this probe; the roll-up is never truncated on a failed business sweep.
7. **Security layer (additive)** — `rebuild` also regenerates `<vault_dir>/Portfolio/global-security.md` by piping `../scripts/security-scan.py | ../scripts/security-rollup.py`, sweeping each project's `security/history.jsonl` (written by sec-audit v1.29+) into one dashboard: open CRITICAL/HIGH, trend, days since the last audit, and which projects have never been audited. Format and full input contract: `../references/global-security-format.md`. Three rules it must not break — an unrecorded count renders `?` and **never `0`** (unmeasured is not clean); a `mode: "feeds"` run is flagged `⚠` because it re-checked dependency advisories without running any code lane; and `total_open` already includes accepted findings, so "open and not suppressed" is `total_open − accepted`. If the scripts are missing, fail, or time out, the step degrades to one `security layer: unavailable` line, leaves any existing `global-security.md` **intact** (never truncated), and every other output is byte-identical (guarded by `../tests/test-security-degradation.py`).
8. Report: `Rebuilt: global-backlog.md (N), global-decisions.md (D), global-maturity.md (M), sidecars enriched: K` plus the business- and security-layer statuses. (0 writes when everything matches prior content.)
