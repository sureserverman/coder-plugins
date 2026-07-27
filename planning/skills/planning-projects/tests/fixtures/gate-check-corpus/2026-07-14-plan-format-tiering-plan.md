# Project Plan: Downward tiering for planning-projects / executing-plans (Light plan format)
Date: 2026-07-14

## Research Summary

### Problem and design decision

The planning pipeline's size dial only turns upward (Phase 2.5 decomposes big plans
into master + sub-plans). There is no downward step: a 3-task job invoked through
`planning-projects` pays the full ceremony (Research Summary, Preflight, Risk/Rollback,
symmetric Blocks, Parallel fields) and `executing-plans` adds per-task reviewer
dispatches, gate evaluators, and the mirror version-bump ritual. The fix is a
**format ladder** with an explicit decision rule, symmetric to Phase 2.5:

| Format | Trigger (heuristic) | Artifact |
|--------|--------------------|----------|
| **Direct** | ≤ ~2 tasks, one session, no staging value | No plan file — decline to plan; execute with a test + commit |
| **Light** | Single stage, ≤ ~5 tasks, one session, one stack | `*-light-plan.md` per new `references/light-plan-format.md` |
| **Standard** | Everything between | Current full format (unchanged) |
| **Master** | Phase 2.5 triggers (> ~6 stages / ~25 tasks / multi-workstream) | Existing master + sub-plans (unchanged) |

**Naming:** deliberately NOT "Tier 0–3" — `executing-plans` already uses "Tier 1/Tier 2"
for its two code-review passes; overloading "tier" for plan sizes would make the skill
text ambiguous. Formats are named Direct / Light / Standard / Master.

**Invariants kept at every format** (these are the drift protection): concrete `Test:`
per task, `Status:` flips on green, commit per green task, Red-Green cycle budget
(default 3), run-to-completion, stop conditions, honest-gates.

**Artifacts dropped at Light** (long-horizon guardrails a one-session job can't need):
mandated Research Summary section (findings go inline as a short Context paragraph),
full Preflight (only "baseline tests pass"), Risk/Rollback blocks, `Blocks:` fields
(derivable from `Depends on` in ≤5 tasks), `Parallel:` fields (no fan-out at this size),
Tier-1 per-task review (replaced by ONE whole-diff review before close-out),
goal-evaluator dispatches (opt-in instead of default), and the mirror-grep version-bump
ritual (one stated bump; mirrors named explicitly only when the repo is this
marketplace).

### Parser contract (portfolio-unify / compass)

- `planning/skills/portfolio/scripts/portfolio-unify.py`: `STAGEHDR_RE = ^## Stage (\d+)`,
  `TASK_RE = ^### Task (\d+\.\d+):`, `STATUS_RE = ^- **Status:** [ /x]`. Any file with a
  Status checkbox takes the **authoritative path**: one candidate per `Status: [ ]` task,
  gate bullets ignored, Deferred sections still surface.
- Therefore a Light plan that keeps `## Stage 1:` + `### Task 1.N:` + `- **Status:** [ ]`
  is parser-safe **by construction — zero parser code changes**. Same pattern as master
  plans and architecture docs (`portfolio/references/plan-parser.md` § format guarantees),
  each locked by a fixture in `portfolio/tests/test-portfolio-unify.py` (plain-python
  suite, CI: `.github/workflows/validate-plan-parser.yml`).
- `compass-scan.py` reuses the same regexes (CI: `validate-compass-scan.yml`); a Light
  plan reads as a normal in-flight one-stage plan there. No compass change needed.
- BL-001 (parser `[~]`/OBSOLETE gaps) is adjacent but NOT subsumed — this plan adds no
  new Status states. It stays deferred.

### Repo / release context

- Detection precedent to mirror: master plans are detected by filename suffix
  (`-master-plan.md`) OR first heading (`# Master Plan:`). Light plans will use
  `-light-plan.md` OR `# Light Plan:`.
- Reference-doc precedent: `planning-projects/references/master-plan-format.md` is the
  single-source-of-truth style to copy for `light-plan-format.md`.
- Frontmatter `description:` fields are CI-budgeted ≤300 chars
  (`scripts/check-frontmatter-budget.py`, `validate-frontmatter-budget.yml`); the
  checked-in `capability-index.json` is built from frontmatter by
  `scripts/build-capability-index.py` and must be regenerated when descriptions change.
- Versions now: planning **0.21.0**, marketplace **0.11.0** (root
  `.claude-plugin/marketplace.json` `metadata.version`). This is a minor capability →
  planning 0.22.0; mirrors: marketplace planning entry (version + long description) and
  `metadata.version` per this repo's release convention (see BL-006/BL-007 entries).
- Integration graph: skill interface changes here create re-port debt to
  **engineering-skills** (BL-006/BL-007 pattern) → close-out opens a new BL entry.
- No `docs/workflows/` in this repo → no WF declarations apply. No architecture doc for
  this topic — structure decided inline (two SKILL.md edits + one new reference + one
  fixture; no new module surface).

## Preflight

- [ ] Repo clean and on a feature branch (not `main`): `git -C ~/dev/ai-tools/coder-plugins status --porcelain` empty; create `plan-format-tiering` branch
- [ ] Baseline fixture suite green: `python3 planning/skills/portfolio/tests/test-portfolio-unify.py` exits 0
- [ ] Baseline frontmatter budget green: `python3 scripts/check-frontmatter-budget.py` exits 0
- [ ] Capability index builds clean at baseline: `python3 scripts/build-capability-index.py` produces no diff (`git diff --stat capability-index.json` empty)
- [ ] Compass fixture suite green (shared regexes): its test entry point under `planning/skills/compass/tests/` exits 0

---

## Stage 1: Light-plan format specification + parser lock

**Goal:** The Light plan format exists as a canonical reference doc, and a CI fixture proves it yields correct portfolio-unify candidates with zero parser changes.
**Depends on:** none
**Blocks:** Stage 2
**Risk:** LOW — pure docs + fixture work; parser behavior already proven for Status-field plans
**Rollback:** `git revert` the stage's commits; no state outside the repo

### Task 1.1: Author `planning/skills/planning-projects/references/light-plan-format.md`
- **Status:** [x]
- **Depends on:** none
- **Blocks:** Task 1.2
- **Parallel:** YES
- **Test:** File exists; contains the detection rule (`-light-plan.md` suffix OR first heading `# Light Plan:`), a skeleton with `## Stage 1:`, `### Task 1.1:`, `- **Status:** [ ]`, `- **Test:**`, a `### Stage 1 Gate`, an "Invariants kept / Artifacts dropped" table, and a "Parser-safety rules" section — verified by grep for each marker
- **Red-Green max cycles:** 3

Content requirements: naming (`YYYY-MM-DD-<topic>-light-plan.md`, same `plans/` dir);
document skeleton (`# Light Plan: [Name]`, `Date:`, optional short **Context** paragraph
replacing the Research Summary, one `## Stage 1:` with 2–5 `### Task 1.N:` tasks each
carrying only `Status` / optional `Depends on` / `Test` / optional `Red-Green max cycles`,
and one final `### Stage 1 Gate` whose checks include the full existing test suite);
explicitly forbidden fields at Light (Blocks, Parallel, Risk, Rollback, Preflight section
beyond a baseline-tests check inside the gate); upgrade rule (a Light plan that grows a
second stage or a 6th task is re-issued as a Standard plan — never patched in place);
parser-safety rationale mirroring master-plan-format.md.

### Task 1.2: Add Light-plan fixtures + assertions to the plan-parser suite
- **Status:** [x]
- **Depends on:** Task 1.1
- **Blocks:** Task 1.3
- **Parallel:** NO (blocked by 1.1)
- **Test:** `python3 planning/skills/portfolio/tests/test-portfolio-unify.py` exits 0 and its output includes new `ok` lines for the light-plan checks
- **Red-Green max cycles:** 3

Fixtures in `portfolio/tests/fixtures/plan-parser/`: an in-progress Light plan
(mixed `Status: [x]`/`[ ]`, a gate with unchecked bullets, one Deferred bullet) and a
completed variant (`**Completed:**` line, all `[x]`). Assertions: in-progress yields
exactly one `status-unexecuted` candidate per `[ ]` task plus the Deferred bullet, gate
bullets never surface; completed variant yields zero candidates.

**Review notes (Task 1.2):** Tier-1 APPROVE, no Critical/Important. Suggestions: (1)
test summary print line doesn't mention light plans (cosmetic); (2) `validate-plan-parser.yml`
triggers on `master-plan-format.md` but not `light-plan-format.md`, so a lone edit to the
new reference would skip CI — actionable in Stage 3; (3) fixture filenames deviate from the
`*-light-plan.md` naming rule (no functional effect — routing is off `Status:` regex + first
heading, both satisfied).

### Task 1.3: Document the Light format guarantee in `portfolio/references/plan-parser.md`
- **Status:** [x]
- **Depends on:** Task 1.2
- **Blocks:** Task 2.1
- **Parallel:** NO (blocked by 1.2)
- **Test:** grep finds a `## Light plans` section in plan-parser.md citing the fixture lock; fixture suite still exits 0
- **Red-Green max cycles:** 3

Short section in the style of the master-plan / architecture-doc entries: detection,
"authoritative path by construction, no parser code", fixture-locked guarantee,
cross-reference to `light-plan-format.md`.

### Stage 1 Gate
- [x] `python3 planning/skills/portfolio/tests/test-portfolio-unify.py` exits 0 (all pre-existing + new checks)
- [x] Compass fixture suite still exits 0 (shared regex contract unbroken)
- [x] Hand-parse check: running `portfolio-unify.py`'s `parse_plan` on the in-progress fixture from a Python REPL returns the exact expected candidate list (live artifact, not just the suite's own assertions)
- [x] `light-plan-format.md` and plan-parser.md cross-reference each other by relative path and the paths resolve

**Stage 1 handoff:** Gate passed; Tier-2 review APPROVE (no Critical). Three gate-time
remediations folded into the "Stage 1 green" commit rather than deferred: (1) added
`light-plan-format.md` to `validate-plan-parser.yml`'s push+PR `paths:` triggers — closes
the Important CI-gap the review flagged, so Stage 3 no longer needs to (advisory (b) from
Task 1.2 is now resolved here). (2)+(3) tightened two doc-precision Suggestions in
light-plan-format.md: the detection-rule line no longer claims the parser uses filename
detection (it routes off `Status:` only), and Parser-safety rule 2 no longer implies a
gate-specific exclusion mechanism. Fixture filename convention nit (advisory (c)) left
as-is — verified zero functional effect (parser routes off content regex, never
filename). No parser code was changed the entire stage — the format is parser-safe by
construction, as designed.

---

## Stage 2: planning-projects — format triage + Light lane

**Goal:** planning-projects picks a format explicitly before planning (Direct / Light / Standard / Master), can decline to plan, and can emit a conformant Light plan.
**Depends on:** Stage 1 gate passing
**Blocks:** Stage 3
**Risk:** LOW — single SKILL.md rewrite with a stable reference doc to lean on; main risk is internal contradiction with existing phases, caught by the coherence gate
**Rollback:** `git revert` the stage's commits

### Task 2.1: Add "Phase -0.5 — Format triage" to `planning/skills/planning-projects/SKILL.md`
- **Status:** [x]
- **Depends on:** Task 1.3
- **Blocks:** Task 2.2
- **Parallel:** NO (Stage 1 gate + same file as 2.2)
- **Test:** grep finds the four format names with explicit thresholds, the Direct decline rule ("recommend direct execution with a test and a commit — do not produce a plan file"), and a pointer to `references/light-plan-format.md`; the section sits before Phase -1 (Phase 2.5 remains the Standard→Master rule and is referenced, not duplicated)
- **Red-Green max cycles:** 3

The triage runs on the clarified request: state the chosen format and its trigger in one
line at the top of the eventual plan (`Format: Light — single stage, 4 tasks, one
session`). Borderline cases round UP to the heavier format; the user can override either
way. Direct answers the "simple jobs shouldn't enter the machinery" problem — the skill
now has an off-ramp.

### Task 2.2: Add the Light-plan authoring lane (phase deltas + checklist variant)
- **Status:** [x]
- **Depends on:** Task 2.1
- **Blocks:** Task 2.3
- **Parallel:** NO (same file as 2.1)
- **Test:** grep finds a "Light plans" subsection covering: research proportionate (inline Context paragraph, no mandated Research Summary/backlog-scan write-up — but the backlog scan itself still runs), Preflight reduced to baseline-tests-green inside the gate, no Risk/Rollback/Blocks/Parallel fields, output location unchanged (vault `plans/`, same sidecar rules), and a separate short "Checklist — Light plans" (~6 items) that the full checklist explicitly defers to for Light plans
- **Red-Green max cycles:** 3

The Light checklist keeps: every task has a concrete Test; dependency order holds;
single stage of ≤5 tasks; gate includes full existing test suite; saved to
`<portfolio_home>/plans/`; format line present. The full checklist gains one line at the
top: "Light plans use the Light checklist below instead."

### Task 2.3: Update planning-projects frontmatter description for triage/Light
- **Status:** [x]
- **Depends on:** Task 2.2
- **Blocks:** Task 3.1
- **Parallel:** NO (blocked by 2.2)
- **Test:** `python3 scripts/check-frontmatter-budget.py` exits 0; the new description names the format triage (Direct/Light/Standard/Master) so routing still fires for "create a plan" but the skill's own text explains it may decline
- **Red-Green max cycles:** 3

Description stays ≤300 chars. Do NOT rebuild capability-index.json here — one rebuild in
Task 3.3 covers both description changes.

### Stage 2 Gate
- [x] Full read-through of planning-projects/SKILL.md: no phase, checklist item, or pitfall contradicts the triage (e.g. nothing still says "every stage has a rollback note" unconditionally where Light is exempt)
- [x] Dry-run (live artifact): following only the updated SKILL.md text, author a toy Light plan for a 3-task job; verify it conforms to light-plan-format.md and that `parse_plan` yields one candidate per `Status: [ ]` task
- [x] Fixture + budget suites both exit 0
- [x] No regressions: `git diff` for the stage touches only planning-projects/SKILL.md and its frontmatter (gate remediation additionally touched `light-plan-format.md` — see handoff)

**Stage 2 handoff:** Gate initially FAILED — the coherence evaluator and Tier-2 review both
found real contradictions between the new triage and pre-existing unconditional wording.
Fixed six coherence gaps before passing (re-evaluated: PASS on all points, no Critical):
(1) intro prose scoped its "mandated research + rollback notes" claim to Standard; (2)
Common Pitfalls got a scope fence (Risk/Rollback/Blocks/Parallel rows are Standard/Master-
only); (3) Light checklist gained the WF-NNN behavior-contract bullet (was only backlog);
(4) Direct off-ramp now keeps a quick backlog-title check (the one Phase 0 step it retains);
(5)+(6) `light-plan-format.md`'s template + field table now carry the mandated
`Format: Light — …` header line, harmonizing it with SKILL.md's "Record the call" rule.
Deviation from plan: Task 2.1's placement said "before Phase -1" but -0.5 is numerically
between -1 and 0 and the triage runs on the *clarified* request, so it sits after Phase -1,
before Phase 0 — the correct slot. Deviation from gate check 4: remediation touched the
Stage 1 file `light-plan-format.md` (cross-doc coherence), not only SKILL.md — intended
scope for a coherence fix, no unrelated sprawl. Version bumps + capability-index rebuild
remain deferred to Task 3.3 as planned.

---

## Stage 3: executing-plans support + release

**Goal:** executing-plans recognizes Light plans, scales its review/evaluator/close-out machinery by format, and the release lands with versions, mirrors, and capability index consistent.
**Depends on:** Stage 2 gate passing
**Blocks:** none
**Risk:** MEDIUM — executing-plans has many interlocking rules (two review tiers, evaluator defaults, close-out steps); a missed cross-reference leaves the skill self-contradictory. Mitigated by the coherence gate check and the dry-run
**Rollback:** `git revert` the stage's commits; versions/mirrors revert with them

### Task 3.1: Teach `planning/skills/executing-plans/SKILL.md` the Light format
- **Status:** [x]
- **Depends on:** Task 2.3
- **Blocks:** Task 3.2
- **Parallel:** NO (blocked by 2.3)
- **Test:** grep finds (a) a Light detection rule mirroring the master exception (`-light-plan.md` / `# Light Plan:` — do NOT reject for missing Preflight/Blocks/Parallel), (b) a "Light plans" section stating the execution deltas, (c) the critique step (Phase 1) exempting Light plans from the missing-field checks it would otherwise flag
- **Red-Green max cycles:** 3

Execution deltas to encode: Preflight = git bootstrap + baseline tests only; no
`dispatching-parallel-agents` (tasks run inline, sequentially, Red-Green as ever);
**skip Tier-1 per-task review** — instead ONE whole-diff `git-github:code-reviewer`
dispatch after the last task goes green and before the gate (Critical blocks exactly as
a Tier-2 Critical fails a gate; Important/Suggestion surfaced for triage); goal-evaluator
NOT dispatched by default (opt-in, or when the gate contains a judgment check the user
flags); close-out = full suite + single stated SemVer bump ("state your call" rule kept;
in this marketplace repo, name the plugin.json + marketplace.json pair explicitly instead
of the grep ritual) + backlog reconcile + `**Completed:**` line. Unchanged at Light:
Status flips, commit per green task, cycle budgets, stop conditions, run-to-completion,
handoff note (one, at the single gate), honest-gates.

### Task 3.2: Update executing-plans frontmatter description
- **Status:** [x]
- **Depends on:** Task 3.1
- **Blocks:** Task 3.3
- **Parallel:** NO (same file as 3.1)
- **Test:** `python3 scripts/check-frontmatter-budget.py` exits 0; description now says it executes standard, master, AND light plans
- **Red-Green max cycles:** 3

### Task 3.3: Version bumps, mirrors, capability index
- **Status:** [x]
- **Depends on:** Task 3.2
- **Blocks:** none
- **Parallel:** NO (blocked by 3.2)
- **Test:** `grep -c '"version": "0.22.0"'` confirms planning at 0.22.0 in BOTH `planning/.claude-plugin/plugin.json` and the marketplace entry; `metadata.version` bumped to 0.12.0; both JSON files parse (`python3 -m json.tool`); `python3 scripts/build-capability-index.py` then `git diff --stat capability-index.json` shows only the expected description-driven changes and a re-run produces no further diff
- **Red-Green max cycles:** 3

Also append the Light-format capability to the planning plugin's long description in
plugin.json and its marketplace.json mirror (they restate each other verbatim — update
both).

### Stage 3 Gate
- [x] All local CI suites exit 0: `test-portfolio-unify.py`, compass tests, `check-frontmatter-budget.py`, capability-index rebuild idempotent (ran all 11 repo test suites + budget + `--write` freshness — all green)
- [x] Dry-run (live artifact): execute the toy Light plan from the Stage 2 gate end-to-end following only the updated executing-plans text — verify it runs Preflight-lite, flips Statuses, commits per task, dispatches exactly ONE reviewer, skips the evaluator, and close-out applies exactly one stated bump
- [x] Cross-skill coherence: planning-projects, executing-plans, light-plan-format.md, and plan-parser.md agree on detection rule, field set, and review/evaluator behavior (read all four; any disagreement is a gate failure)
- [x] Full existing test suite: no regressions anywhere in the repo's `tests/` trees
- [x] Close-out prep: new backlog entry drafted for the engineering-skills re-port (BL-006/BL-007 pattern — two SKILL.md interface changes + one new reference doc); plus a second discovered entry for `planning/README.md` staleness

**Stage 3 handoff:** Gate passed after remediation. Tier-2 review APPROVE (no Critical);
cross-skill coherence confirmed across all four docs. The first dry-run (docs-only toy
plan) surfaced two items: (a) behavior-5 real gap — the Light deltas made the *gate*
evaluator opt-in but left the *Phase Close-out* default evaluator unaddressed; fixed by
flipping both evaluator passes to opt-in explicitly in delta 4. (b) behavior-4 was a
test-case artifact — a docs-only plan correctly skips the one review (trivial-diff rule),
so I re-ran the dry-run with a *code-bearing* toy plan (slugify refactor): all six
behaviors PASS unambiguously. Also applied three clarity fixes from the reviews: the one
review is labelled a pre-gate check that *replaces* Step 3.5's Tier-2 (not additional);
planning-projects' Light detection mention gained the `# Light Plan:` heading alternative.
Discovered out-of-scope: `planning/README.md` is stale ("ten-skill (v0.12.0)", no format
triage) — pre-existing, backlogged rather than rewritten in-scope. Versions landed:
planning 0.22.0 (plugin.json + marketplace mirror), marketplace metadata 0.12.0,
capability-index regenerated.

---

## Deferred

- Compass-specific handling of Light plans (e.g. a "light" badge in the in-flight board) — they already parse correctly as one-stage plans; cosmetic only
- A `Review: skip`-style per-plan opt-out annotation for the single Light-plan review — wait for real-world friction before adding a knob

---

**Completed:** 2026-07-14 — commits: d61eb50, 30a067d, 14808e1, 74b91e1 (Stage 1); 830c4be, 3f984b5, ccb79dd, c5e1902 (Stage 2); 59a1b93, 21d824d, a8d68de, 1dc6890 (Stage 3). Opened BL-008 (engineering-skills re-port), BL-009 (README modernization). Versions: planning 0.22.0, marketplace 0.12.0.
