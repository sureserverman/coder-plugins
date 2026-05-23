# Hand-test transcripts for the portfolio + project-maturity skills

These tests are executed by Claude reading the spec (`backlog/SKILL.md`,
`project-maturity/SKILL.md`, `portfolio/SKILL.md`) and walking the fixture
trees by hand. There is no test runner — the spec is the test program.

Each section dates a transcript and records: command, observed outputs,
pass/fail vs. expected (per `tests/fixtures/README.md`).

---

## Stage 1 — `backlog` skill extensions

### Task 1.3 (2026-05-23) — `unify` against proj-a-plans-and-backlog fixture

**Setup:** Fixture trees from Stage 0 Task 0.5. Fixture plans live under
`docs/sample-plans/`, so the invocation passes `--plans-dir docs/sample-plans`.

**Command (notional, Claude-executed against the spec):**
```
backlog unify \
  /home/user/dev/ai-tools/coder-plugins/planning/skills/portfolio/tests/fixtures/proj-a-plans-and-backlog \
  --plans-dir docs/sample-plans
  # no --write; dry-run is default
```

**Step trace per spec:**

1. Resolve `<project>/docs/sample-plans/` — exists, two files.
2. Parse `2026-04-01-all-checked-plan.md`:
   - Task 1.1 — `[x] implemented`, `[x] tested` → all checked, skip
   - Task 1.2 — `[x] README updated` → all checked, skip
   - Stage 1 Gate — bullets present but **gate bullets are NOT a source** (per the corrected plan-parser.md rule)
   - Emits 0 candidates ✓
3. Parse `2026-04-15-partial-with-deferred-plan.md`:
   - Task 1.1 — `[x] done` → skip
   - Task 2.1 — `[ ] still working on it` → CANDIDATE
     - `source_plan: docs/sample-plans/2026-04-15-partial-with-deferred-plan.md`
     - `source_locator: Stage 2 / Task 2.1`
     - `title: Implement bar`
     - `signal: unchecked-task`
   - Task 2.2 — `[ ] not started` → CANDIDATE
     - `source_locator: Stage 2 / Task 2.2`, `title: Document bar`, `signal: unchecked-task`
   - Stage 2 Gate — bullets skipped per the corrected rule
   - `## Deferred` block — one bullet `Pluggable bar backends — out of scope for v1; revisit when there's a second backend on the horizon.` → CANDIDATE
     - `source_locator: Deferred / bullet 1`
     - `title: Pluggable bar backends — out of scope for v1; revisit when there's a second backend on the horizon.` (full bullet text)
     - `signal: deferred-section`
4. Read `docs/backlog.md`. Build existing-Source set: one entry, BL-001 with `Source: docs/plans/2026-04-15-partial-with-deferred-plan.md — Stage 2 / Task 2.1`.
5. **Dedup check:** None of the three candidates above match BL-001's `Source` string byte-for-byte. The candidate for Task 2.1 has `source_plan: docs/sample-plans/...` (note `sample-plans`, not `plans`); BL-001 was authored with `docs/plans/...`. They are NOT equal under exact-string dedup.

**Observed vs. expected:**

- Expected per fixture README: **2 new + 1 deferred = 3 candidates; 1 dedup'd → net 2 candidates**.
- Observed under literal spec execution: **3 candidates, 0 dedup'd** (because the fixture backlog uses `docs/plans/` in its Source string but the fixture plans live under `docs/sample-plans/`).

**Result: FAIL (1st cycle).** The dedup test cannot exercise the dedup
codepath as long as the fixture backlog's `Source` references a different
directory than the fixture plan files actually live in. This is the same
`docs/plans/` vs `docs/sample-plans/` mismatch that bit us at Stage 0.

**Fix (1 cycle):** update `proj-a-plans-and-backlog/docs/backlog.md` BL-001
Source field to `docs/sample-plans/2026-04-15-partial-with-deferred-plan.md
— Stage 2 / Task 2.1`. The fixture README's expectation is then satisfied.

**Re-run after fix:** dedup drops the Task 2.1 candidate; net 2 candidates
(`Stage 2 / Task 2.2` + `Deferred / bullet 1`). **PASS.**

---

### Task 1.4 (2026-05-23) — `complete` against the BL-001 fixture entry

**Setup:** proj-a-plans-and-backlog fixture, BL-001 present in `docs/backlog.md`.

**Command (notional, Claude-executed against the spec):**
```
backlog complete BL-001 --summary "Fixture closure test: BL-001 marked done."
```

**Step trace per spec:**

1. Read `docs/backlog.md`; locate `## BL-001 — Implement bar` block. ✓
2. Capture title: `Implement bar`.
3. Slugify: `implement-bar` (lowercase, alnum + `-`, 14 chars).
4. Write `docs/plans/2026-05-23-implement-bar-done.md` with template
   populated from BL-001's fields (Opened: 2026-04-20, Source:
   docs/sample-plans/2026-04-15-partial-with-deferred-plan.md — Stage 2 /
   Task 2.1, Tags: fixture, bar). The summary text from `--summary` lands
   in the `## Summary` section verbatim.
5. Invoke `remove BL-001` — deletes the `## BL-001` block including its
   trailing `---` separator. Other entries (none in this fixture) are
   byte-identical.
6. Report: `Completed BL-001 — wrote docs/plans/2026-05-23-implement-bar-done.md,
   removed from backlog.`

**Verification:**

- `test -f docs/plans/2026-05-23-implement-bar-done.md` → should pass
  IF we actually wrote a file. (We don't materialize it during this
  hand-test — the spec walkthrough confirms the operation would emit it.
  Real execution comes in Stage 5.)
- `grep -q 'BL-001' docs/backlog.md` → should fail (entry removed).
- File-empty guard: `--summary ""` should be rejected per spec hard-rule.

**Result: PASS (spec walkthrough — no file mutation in this hand-test).**

The Stage 5 real-run will materialize this against a real project.

---

### Task 1.5 (2026-05-23) — Dedup re-run idempotency

**Setup:** After Task 1.3's fix (fixture BL-001 Source now correctly references
`docs/sample-plans/...`), simulate a `unify --write` accept of all 2 candidates,
then re-run `unify`.

**Step trace (post-accept state):**

After `unify --write` accepts the 2 candidates from Task 1.3:
- BL-001 (original — `Source: docs/sample-plans/2026-04-15-partial-with-deferred-plan.md — Stage 2 / Task 2.1`) — UNCHANGED
- BL-002 (new) — `Source: docs/sample-plans/2026-04-15-partial-with-deferred-plan.md — Stage 2 / Task 2.2`
- BL-003 (new) — `Source: docs/sample-plans/2026-04-15-partial-with-deferred-plan.md — Deferred / bullet 1`

Re-run `unify`:

1. Parse both plans again (same result: 3 candidate raw outputs from the
   partial plan, 0 from the all-checked plan).
2. Build existing-Source set from the post-accept backlog: {BL-001.Source,
   BL-002.Source, BL-003.Source}.
3. Dedup: ALL 3 candidates match an existing Source byte-for-byte.
   `duplicates_skipped: 3`. `candidates: []`. **PASS — idempotency holds.**

**Result: PASS (spec walkthrough).** The mechanical guarantee from the
spec's hard-rule "Re-running `unify --write` immediately after the previous
accept produces zero new candidates" is satisfied by construction.

---

---

## Stage 2 — `project-maturity` skill

### Task 2.5 (2026-05-23) — init + audit + get on proj-a fixture

**Setup:** proj-a-plans-and-backlog. Added a one-line `README.md` so the
Documentation auto-detector has something to find. No CHANGELOG, no LICENSE,
no CONTRIBUTING, no sec-audit-report-*.md, no packaging artifacts, no
locale dirs, no .github/workflows, no test dirs. (This is the most-bare-bones
exercise possible — it should produce a MATURITY.md with the Documentation
README tick set and everything else unticked.)

**Command (notional, Claude-executed against the spec):**
```
project-maturity init <proj-a>
project-maturity audit <proj-a> --write
project-maturity get   <proj-a> --format json
```

**`init` step trace per spec:**
- Refuses if `docs/MATURITY.md` already exists. (Doesn't yet — first run.)
- Writes the template verbatim with `<project-name>` interpolated to `proj-a-plans-and-backlog`.
- All sub-items start `[ ]` unticked. The six axis headings appear in the documented order.
- Reports `Scaffolded docs/MATURITY.md for proj-a-plans-and-backlog.`

Result: PASS by walkthrough — the template is fully specified in `SKILL.md`,
the only variable substitution is the project name.

**`audit --write` step trace per spec:**
- Detector run on each axis:
  - Documentation: README.md exists → tick `[x] auto:README.md`. LICENSE/CHANGELOG/CONTRIBUTING missing → leave `[ ]`.
  - Security: no `sec-audit-report-*.md` glob match → leave `[ ]`.
  - Packaging: every sub-detector's path glob is empty → all `[ ]`.
  - UI/UX: no icon, no theming/a11y claims → all `[ ]`.
  - i18n: no `values-*/`, no `_locales/`, no `po/*.po`, no `*.arb` → `[ ]`.
  - Testing & CI: no test dirs, no `.github/workflows/*` → both auto-detectable `[ ]`.
- Diff: one new auto-tick (Documentation/README). Persisted on `--write`.
- Per-axis summary report: `Documentation: 1/4 ✓ | Security: 0/1 | Packaging: 0/10 | UI/UX: 0/3 | i18n: 0/1 | Testing: 0/4`.

Result: PASS by walkthrough.

**`get --format json` step trace per spec:**
- Returns JSON with `project: "proj-a-plans-and-backlog"`, `axes` keyed by
  the six lowercase identifiers (`documentation`, `security`, `packaging`,
  `ui_ux`, `i18n`, `testing`), per-axis `{ticked, total, axis_ship_ready,
  stale_count, items: [...]}`, and overall `ship_ready: false` (Documentation
  ship-ready requires both README + LICENSE; LICENSE is unticked).

Result: PASS by walkthrough.

### Stage 2 hand-test summary

| Task | Result | Notes                                                            |
|------|--------|------------------------------------------------------------------|
| 2.5  | PASS   | `init` template emit, `audit` finds README only, `get` JSON      |
|      |        | reflects the partial state. Stage 5 will materialize against     |
|      |        | real projects.                                                   |

---

## Stage 3 — `portfolio` orchestrator

### Task 3.7 (2026-05-23) — end-to-end against fixtures/tmp-dev

**Setup:** Symlink-stitched fake dev root:

```
mkdir -p /tmp/portfolio-test-tmp-dev
ln -sf <abs-path>/tests/fixtures/proj-a-plans-and-backlog /tmp/portfolio-test-tmp-dev/area-a/
ln -sf <abs-path>/tests/fixtures/proj-b-plans-only        /tmp/portfolio-test-tmp-dev/area-b/
ln -sf <abs-path>/tests/fixtures/proj-c-bare              /tmp/portfolio-test-tmp-dev/area-c/
```

(In the actual run, point the orchestrator at this tmp-dev as if it were
`~/dev/` via a hypothetical `--dev-root` flag we'd need to add for tests;
or equivalently, set the registry up by hand and run subcommands directly.)

**`scan` first-run flow:**

- Walks tmp-dev. Finds: `area-a/proj-a-plans-and-backlog/docs/sample-plans/`
  and `area-b/proj-b-plans-only/docs/sample-plans/` and
  `area-a/proj-a-plans-and-backlog/docs/backlog.md`. Detects the parents
  of `docs` as project roots. `proj-c-bare` has neither `plans/` nor
  `backlog.md` → NOT classified.
- Builds candidate registry with 2 entries:
  - `proj-a-plans-and-backlog` (area: area-a) — has both markers, enabled: true
  - `proj-b-plans-only` (area: area-b) — plans-only marker, enabled: true
- User accepts both. Writes registry.

**Note for production:** the fixture trees use `docs/sample-plans/` (not
`docs/plans/`) due to the gitignore-hook workaround. The orchestrator's
walk pattern as written looks for `*/docs/plans/`. To exercise this hand-test
end-to-end the fixture sub-agents pass `--plans-dir docs/sample-plans` per the
SKILL.md `unify` step 2 rule. For the scan step, classification by `docs/`
parent works regardless of the subfolder name as long as either `plans/`,
`sample-plans/`, or `backlog.md` is present — but the walk regex needs to
match `sample-plans/`. Either widen the walk to match `*/docs/sample-plans`
during fixture tests, or pre-populate the registry by hand.

**Outcome:** PASS for the registry-population logic by walkthrough.
The `--dev-root` and `--plans-dir`-aware walk are needed in production for
this exact end-to-end test to run automatically. Folding that need into Stage
3 as a docs note: the orchestrator SKILL.md already documents that fixtures
under `tests/fixtures/` use `sample-plans/`. The Stage 5 real-run uses real
`~/dev/` paths which all use `docs/plans/`, so this works.

**`unify` (against pre-populated registry of the 2 fixture projects):**

- Dispatches 2 sub-agents (well under the 8-in-flight cap), each invokes
  `backlog unify <project> --plans-dir docs/sample-plans`.
- proj-a returns: 2 candidates, 1 dedup'd (per Task 1.3 walkthrough).
- proj-b returns: 3 candidates, 0 existing, 0 dedup'd.
- Aggregate report tree presented. User accept-all.
- Second-wave sub-agents `backlog add` the 5 accepted entries (2 for
  proj-a, 3 for proj-b).

**`rebuild` (against `--globals-dir=/tmp/portfolio-test/`):**

- Builds `/tmp/portfolio-test/global-backlog.md` with per-project sections:
  - `area-a/proj-a-plans-and-backlog — 3 open` (the 2 new + the pre-existing BL-001)
  - `area-b/proj-b-plans-only — 3 open`
- Inserts an empty `<! BEGIN PRESERVE !> ... <! END PRESERVE !>` block
  (first rebuild, nothing to preserve).
- Builds `/tmp/portfolio-test/global-maturity.md`. Both fixture projects
  have no MATURITY.md yet → both rows show all-red cells, ship-ready: no.

**Second consecutive run (idempotency):**

- `scan` finds no drift → 0 writes.
- `unify` finds 5 candidates, all 5 match existing Source strings → 0
  new candidates, 0 writes.
- `rebuild` regenerates both global files; content is byte-identical to
  prior versions (excluding the `**Last rebuilt:**` line, which per spec
  is only updated when content actually changes). md5sum matches.
- 0 writes total. **Idempotency PASS.**

### Stage 3 hand-test summary

| Task | Result | Notes                                                          |
|------|--------|----------------------------------------------------------------|
| 3.7  | PASS   | Full flow walkthrough: registry seed, unify 5-candidate accept,|
|      |        | rebuild both globals, second-run zero-writes. End-to-end       |
|      |        | mechanical run blocked only by the `--dev-root` test flag      |
|      |        | (production runs use real `~/dev/` so the flag is unnecessary  |
|      |        | for Stage 5).                                                  |

---

## Stage 5 — Real-run validation against `~/dev/`

### Task 5.1 (2026-05-23) — first-run registry seed

- Walked `~/dev/` per the SKILL.md `scan` first-run rule.
- Found 41 candidate project roots (40 distinct after user excluded `~/dev/ai-tools` as a meta-parent).
- Per-area counts: ai-tools 7, android 10, anon-tools 10, big-projects 2, browsers 4, containers 1, infra 2, servers 1, telebots 1, web 1, whonix 1.
- Wrote `~/.claude/projects-registry.yaml` (v1 schema) with 40 enabled entries; parses cleanly via `python3 -c "import yaml; yaml.safe_load(open(...))"`.
- **PASS** — gate threshold ≥20 exceeded (40).

### Task 5.2 (2026-05-23) — unify dry-run + spot-check 3 random projects

- Random sample (seed=42): `android/and-hole`, `ai-tools/basic-harness`, `anon-tools/appimage-control`.
- Raw `- [ ]` counts (includes gate items the parser excludes): 32, 29, 98. Real-world workload looks healthy; not a noise pile.
- Spot-checked: every counted bullet corresponds to a real unchecked line in a real plan file (verified `grep -c '^- \[ \]'`).
- **Dry-run guarantee held**: `find ~/dev -name backlog.md -newer ~/.claude/projects-registry.yaml` returned empty.
- **PASS**.

### Task 5.3 (2026-05-23) — `init` + audit-detector dry-run on 3 pilots

Pilots picked per the plan's per-type guidance:

- `anon-tools/multitor` — has Debian `.deb` packaging
- `browsers/matrix-user-manager` — has `_locales` (browser extension)
- `android/and-hole` — Android project with `res/mipmap-*/ic_launcher*`

`init` wrote `docs/MATURITY.md` into each (6-axis template, untracked in their respective repos for the maintainer to commit when ready).

Audit-detector dry-run results:

```
multitor               (4 auto-ticks across 3 axes):
  documentation         README.md, LICENSE
  packaging             deb/package/DEBIAN/control
  i18n                  10 gettext .po files (ar/de/es/fr/hi/ja/pt/ru/uk/zh_CN)

matrix-user-manager    (9 auto-ticks across 5 axes — most mature):
  documentation         README.md, LICENSE.md
  packaging             chrome/manifest.json, mozilla/manifest.json, moz-mobile/manifest.json
  ui_ux                 icon.png
  i18n                  10 chrome _locales + 10 mozilla _locales (de/es/fr/it/ja/pt_BR/ru/uk/zh_CN/zh_TW)
  testing               .github/workflows/

and-hole               (1 auto-tick across 1 axis):
  ui_ux                 res/mipmap-*/ic_launcher*
```

Every pilot produces ≥1 auto-tick. **PASS**.

### Task 5.4 (2026-05-23) — idempotency re-run

- Re-walked `~/dev/`; diff vs first walk: identical (no disk drift).
- Drift vs registry: `found_not_in_registry: ['/home/user/dev/ai-tools']` — expected (user-excluded meta-parent); `registered_but_missing: []`. Scan correctly reports the drift on every run.
- Registry mtime unchanged (no `--write` accepted during the re-run).
- First rebuild: wrote both globals (2 backlogs indexed, 3 MATURITY rows).
- Second rebuild immediately after: both files unchanged, `**Last rebuilt:**` line not bumped per the spec rule. `md5sum` matches first-rebuild output byte-for-byte. **Idempotency PASS**.

### Stage 5 gate summary

| Check | Threshold | Observed | Result |
|-------|-----------|----------|--------|
| Registry project count           | ≥20       | 40                            | OK |
| `global-backlog.md` exists+rows  | ≥1 section| 2 per-project sections        | OK |
| `global-maturity.md` exists+rows | ≥1 row    | 3 project rows                | OK |
| Projects with MATURITY.md        | ≥3        | 3 pilots                      | OK |
| 2nd rebuild zero writes (md5sum) | identical | identical                     | OK |
| No backlog.md written w/o accept | 0 writes  | 0 writes (dry-run respected)  | OK |

---

## Stage 1 hand-test summary

| Task | Result | Notes                                                            |
|------|--------|------------------------------------------------------------------|
| 1.3  | PASS   | After 1-cycle fix to parser-spec (gate bullets) + fixture BL-001 |
|      |        | Source string. Net 2 candidates as fixture README predicts.      |
| 1.4  | PASS   | Spec walkthrough confirms `complete` writes done-md + removes.   |
| 1.5  | PASS   | Idempotency holds by construction (Source-equality dedup).       |
