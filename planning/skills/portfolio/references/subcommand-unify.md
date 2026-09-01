# `unify` — one script over the whole registry

The procedure behind `../SKILL.md` § `unify` — derive backlog candidates for every enabled
project. In the default flow this is step 2: surface candidates per project; on confirm,
accepted candidates land in their per-project `backlog.md`.

**This used to fan out one sub-agent per project and no longer does.** The fan-out asked
eight agents to perform, in prose, a parse that `../scripts/portfolio-unify.py` already
performed in one process with the identical flag set — and the script is what the close-out
transcript records actually running. That left the same mechanical rule with **three
definition sites** (the script, this file, and `../../backlog/SKILL.md`), which is three places to
drift and one place the answer really comes from. Retiring the fan-out here was a deliberate
architecture decision (BL-072, decided 2026-09-01), not a cleanup: the 8-in-flight cap still
binds `maturity`, which genuinely needs per-project judgment, and it still binds any second
wave. `unify` simply has no judgment to distribute — walking plan files and comparing
`Source` strings is decidable, and a decidable rule belongs in a script.

What is left for the model is the part that was never mechanical: presenting the candidates
and taking the user's decision.

Inputs, passed straight through to the script: optional `--project <abs-path>` (limit to one
project; matched against the registry `path`), optional `--include-stale` (default off —
surfaces unresolved items in plans older than 90 days by filename stamp), optional `--write`
(default off).

Operation:

1. Run the sweep. It loads the registry, filters to `enabled: true`, and parses every
   project's plans in one process:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/portfolio/scripts/portfolio-unify.py"
   ```

   Add `--project <abs-path>` to narrow it, `--include-stale` to widen the signal set. Do
   **not** pass `--write` here; step 3 is the confirm, and writing before it would make the
   prompt a formality. Parser rules the script implements: `plan-parser.md`.

2. Read its report. It is already grouped by `area/name`, one line per project, and ends with
   a total:

   ```
   anon-tools/multitor: 20 new, 0 dup, 20 candidates
   android/and-hole: 0 new, 1 dup, 0 candidates
   ...
   DRY-RUN: 215 new entries, 0 duplicates skipped, 215 candidates across 89 projects
   ```

   Present it as-is rather than re-typing it. A re-typed figure is a figure nobody measured.

3. **Present to the user** — accept-all / pick-some-per-project / skip-project. This step is
   the confirm, and it is the whole reason a model runs this subcommand at all.

4. On accept, re-run with `--write` (adding `--project` when the user narrowed the set).
   **Never write during dry-run.** Re-running immediately afterwards yields zero new
   candidates: every accepted candidate's `Source` now lives in the project's `backlog.md`
   and matches by exact string equality.

**Hard rules for `unify`** — both bind from `../SKILL.md` § Hard rules, and are repeated here
only as the reasons they exist:

- Dry-run is the default. `--write` is the only path to file mutations, and even then
  candidates must come from a user-confirmed list (the prompt in step 3 IS the confirm).
- The 8-in-flight cap on parallel sub-agents prevents accidentally fan-out-DOS'ing a slow
  filesystem (e.g. NFS-mounted vault, slow CI runner). It no longer applies to this
  subcommand, which dispatches nothing — it still binds `maturity` and any second wave.
