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

## Stage 1 hand-test summary

| Task | Result | Notes                                                            |
|------|--------|------------------------------------------------------------------|
| 1.3  | PASS   | After 1-cycle fix to parser-spec (gate bullets) + fixture BL-001 |
|      |        | Source string. Net 2 candidates as fixture README predicts.      |
| 1.4  | PASS   | Spec walkthrough confirms `complete` writes done-md + removes.   |
| 1.5  | PASS   | Idempotency holds by construction (Source-equality dedup).       |
