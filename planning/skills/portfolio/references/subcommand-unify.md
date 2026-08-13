# `unify` — the per-project fan-out

The procedure behind `../SKILL.md` § `unify` — derive backlog candidates for every enabled
project, in parallel. In the default flow this is step 2: surface candidates per project; on
confirm, accepted candidates land in their per-project `backlog.md`.

Inputs: optional `--project <abs-path>` (limit to one project; matched against the registry `path`), optional `--include-stale` (default off — surfaces unresolved items in plans older than 90 days by filename stamp), optional `--write` (default off).

Operation:

1. Load the registry; filter to entries with `enabled: true`. If `--project` is set, narrow to that one.
2. For each project (up to 8 in flight), dispatch a sub-agent via the **dispatching-parallel-agents** skill. Each sub-agent invokes the `backlog` skill's `unify` subcommand on its project. Parser rules for the plan files it reads: `../references/plan-parser.md`.
3. Each sub-agent returns its `{candidates, existing, duplicates_skipped}` structure.
4. Aggregate into a tree-shaped report grouped by `area/name`:

   ```
   anon-tools/multitor (8 existing, 0 duplicates skipped, 2 new candidates):
     + Stage 3 / Task 3.2     (status-unexecuted) Wire MT slot frames through evdev
     + Deferred / bullet 1    (deferred-section) Bluetooth HID jitter support
   android/and-hole (3 existing, 1 duplicate skipped, 0 new candidates):
     (no new candidates)
   ...
   ```

5. Present to user — they pick accept-all / pick-some-per-project / skip-project.
6. On accept, dispatch a second wave of sub-agents (same 8-in-flight cap) — each runs `backlog add` for that project's accepted candidates. **Never write during dry-run.**

**Hard rules for `unify`** — both bind from `../SKILL.md` § Hard rules, and are repeated here
only as the reasons they exist:

- Dry-run is the default. `--write` is the only path to file mutations, and even then candidates must come from a user-confirmed list (the prompt in step 5 IS the confirm).
- The 8-in-flight cap on parallel sub-agents prevents accidentally fan-out-DOS'ing a slow filesystem (e.g. NFS-mounted vault, slow CI runner).
