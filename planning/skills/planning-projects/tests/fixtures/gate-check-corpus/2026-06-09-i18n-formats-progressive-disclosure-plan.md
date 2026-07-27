# Project Plan: i18n-formats Progressive Disclosure
Date: 2026-06-09

Split `i18n/skills/i18n-formats/SKILL.md` (355 lines, one section per catalog
format) into per-format `references/<format>.md` files behind a thin dispatch
table, and rewire the four consumers to point at the specific reference file
for the detected framework. Pure content move + pointer rewiring — no code logic
changes.

## Research Summary

### Online sources
- N/A — this is an internal docs/skill refactor; no external API in scope. Progressive-disclosure convention is defined by the repo's own `plugin-dev` validator (below), not an external spec.

### Vault / local docs
- Source paper that motivated it: arXiv:2606.05720 (MicroSkill Architecture) — "atomic, sharply scoped capsules + load only the relevant ones." The i18n-formats skill is catalog-shaped (17 format families), so a single invocation needs ~1 format; loading all 17 is the waste progressive disclosure removes.
- No prior plan touches the i18n plugin (`/mnt/vault/Portfolio/ai-tools/coder-plugins/plans/` reviewed).
- No `docs/backlog.md` entries in scope (i18n/format/disclosure scan returned nothing).
- No `docs/workflows/` in this repo — no behavior contracts to declare against.

### Project context
- `plugin-dev/scripts/validate-skill.sh` encodes the success criterion: `skill-no-references` (info) fires for a SKILL.md >300 lines with no `references/` dir; `skill-too-long` (warn) >500; `skill-ref-too-deep` (warn) if any reference nests >1 level under `references/`.
- **Baseline captured (on `main`):** `bash plugin-dev/scripts/validate-plugin.sh i18n --json` → `{errors:0, warnings:0, info:1}`, the lone info being `skill-no-references` on `skills/i18n-formats/SKILL.md`. `bash i18n/scripts/validate.sh i18n --json` → verdict `pass` (`info:2`, unrelated to formats).
- The i18n domain validators (`validate-placeholders`, `validate-catalog-diff`) parse catalog files, **not** i18n-formats prose — so the split cannot break them.
- Consumers already reference i18n-formats **by section** ("the relevant section for the detected framework"), and via prose, not `#anchor` links — so there are no anchor links to break.
- Section boundaries in current SKILL.md (H2): CLDR plural categories (L10, KEEP); gettext (L31); i18next (L57); react-intl/FormatJS (L80); Vue i18n (L106); Android (L119); iOS .strings/.stringsdict/.xcstrings (L151); Flutter ARB (L233); Rails (L259); Django (L279); Qt (L287); .NET .resx (L309); Java .properties (L324); RTL languages (L338, KEEP); Common cross-format mistakes (L348, KEEP). → **12 per-format reference files**; SKILL.md retains description + CLDR + RTL + cross-format mistakes + a dispatch table.
- Consumers to rewire: `skills/i18n-translate/SKILL.md` (L49, L58, L105), `skills/i18n-audit/SKILL.md` (L23, L80, L101), `agents/translator.md` (L21, L31), `commands/i18n-add-locale.md` (L23, L34), `commands/i18n-audit.md` (L23, L28), `commands/i18n-fill-gaps.md` (L23).

## Preflight

- [ ] **jq present**: `command -v jq` (validators require it) — confirmed ok.
- [ ] **Baseline validators captured**: plugin-dev = `info:1` (skill-no-references on i18n-formats); i18n domain = `pass`. (Done above.)
- [ ] **Branch off main**: `git -C /home/user/dev/ai-tools/coder-plugins checkout -b i18n-formats-progressive-disclosure` (repo currently on `main`; never execute task commits on main).
- [ ] **Original snapshot for integrity diff**: the pre-refactor body is recoverable via `git show main:i18n/skills/i18n-formats/SKILL.md` — used by the Stage 3 content-integrity check.

---

## Stage 1: Carve content into per-format references + dispatch-table SKILL.md

**Goal:** Every format family lives in its own `references/<format>.md`; SKILL.md becomes a thin cross-cutting core + dispatch table, with zero format content lost.
**Depends on:** none
**Blocks:** Stage 2
**Risk:** LOW — mechanical text move; deterministic validator + content-integrity diff give an exact pass/fail.
**Rollback:** `git checkout -- i18n/skills/i18n-formats/` (or delete the branch); the original SKILL.md is intact on `main`.

### Task 1.1: Create the 12 per-format reference files
- **Status:** [x]
- **Depends on:** none
- **Blocks:** Task 1.2
- **Parallel:** YES (creates 12 distinct new files; reads the on-`main` source — no shared-file write)
- **Test:** All 12 files exist — `gettext, i18next, react-intl, vue-i18n, android, ios, flutter-arb, rails, django, qt, dotnet-resx, java-properties` — each under `i18n/skills/i18n-formats/references/` (exactly one level deep), each with a one-line `# <Format>` H1, and the verbatim body of its source section(s). Signature-token check passes: each of `msgid_plural`, `react-i18next`, `FormatJS`, `numerusform`, `.stringsdict`, `@key`, `.resx`, `Plural-Forms` appears in exactly one reference file.
- **Red-Green max cycles:** 3

### Task 1.2: Rewrite SKILL.md to cross-cutting core + dispatch table
- **Status:** [x]
- **Depends on:** Task 1.1
- **Blocks:** Task 2.1, Task 2.2, Task 2.3, Task 2.4
- **Parallel:** NO (blocked by 1.1; rewrites the shared SKILL.md)
- **Test:** `wc -l i18n/skills/i18n-formats/SKILL.md` < 150; SKILL.md still contains the CLDR plural categories, RTL, and Common cross-format mistakes sections; contains a dispatch table whose every `references/<file>.md` entry resolves to a file created in 1.1 (12/12); frontmatter `description` unchanged.
- **Red-Green max cycles:** 3

### Stage 1 Gate
- [ ] `bash plugin-dev/scripts/validate-plugin.sh i18n --json | jq '.findings[]|select(.path|test("i18n-formats"))'` returns **empty** (the `skill-no-references` info is gone) and no new `skill-too-long` / `skill-ref-too-deep`.
- [ ] Content integrity: every H2 format-section heading present in `git show main:i18n/skills/i18n-formats/SKILL.md` now resolves to content in exactly one reference file (none dropped, none duplicated).
- [ ] `references/` is exactly one level deep (no subdirs).

**Stage 1 handoff:** 12 reference files created (gettext, i18next, react-intl, vue-i18n, android, ios, flutter-arb, rails, django, qt, dotnet-resx, java-properties) verbatim from the source sections; `django.md` cross-links `gettext.md` (it was "see gettext section" originally). SKILL.md shrank 355→67 lines, keeps description (unchanged), CLDR table, RTL, cross-format mistakes, + a 12-row dispatch table. `validate-plugin.sh i18n` went from `info:1` (skill-no-references) to `{0,0,0}`. No deviations from plan.

---

## Stage 2: Rewire the four consumers to the reference paths

**Goal:** Every consumer that needed "the relevant section of i18n-formats" now names the concrete `references/<format>.md` (or the dispatch table) — no dangling vague pointers, every named path resolves.
**Depends on:** Stage 1 gate passing
**Blocks:** Stage 3
**Risk:** LOW — string/pointer edits across independent files.
**Rollback:** `git checkout -- i18n/skills/i18n-translate i18n/skills/i18n-audit i18n/agents i18n/commands`.

### Task 2.1: Update `i18n-translate` skill
- **Status:** [x]
- **Depends on:** Task 1.2
- **Blocks:** Task 3.1
- **Parallel:** YES (only file: `skills/i18n-translate/SKILL.md`)
- **Test:** No occurrence of "the relevant section of i18n-formats" (or "Read `skills/i18n-formats/SKILL.md` for ... section") remains without a `references/<format>.md` pointer; every `references/*.md` path it now names resolves to a real file.
- **Red-Green max cycles:** 3

### Task 2.2: Update `i18n-audit` skill
- **Status:** [x]
- **Depends on:** Task 1.2
- **Blocks:** Task 3.1
- **Parallel:** YES (only file: `skills/i18n-audit/SKILL.md`)
- **Test:** L23/L80/L101 pointers now name `references/<format>.md` (or the dispatch table in SKILL.md); every named `references/*.md` resolves.
- **Red-Green max cycles:** 3

### Task 2.3: Update `translator` agent
- **Status:** [x]
- **Depends on:** Task 1.2
- **Blocks:** Task 3.1
- **Parallel:** YES (only file: `agents/translator.md`)
- **Test:** the "format reference" instruction (L21) names `references/<format>.md` for source+target; every named path resolves.
- **Red-Green max cycles:** 3

### Task 2.4: Update the three commands
- **Status:** [x]
- **Depends on:** Task 1.2
- **Blocks:** Task 3.1
- **Parallel:** YES (files: `commands/i18n-add-locale.md`, `commands/i18n-audit.md`, `commands/i18n-fill-gaps.md` — disjoint from 2.1–2.3)
- **Test:** each command that passes an i18n-formats section to the translator now names `references/<format>.md`; every named path resolves.
- **Red-Green max cycles:** 3

### Stage 2 Gate
- [ ] Repo-wide grep: no consumer says "relevant section of i18n-formats" / "i18n-formats ... section" without an accompanying concrete `references/<format>.md` path (or an explicit pointer to the SKILL.md dispatch table).
- [ ] Every `references/<format>.md` string mentioned anywhere under `i18n/` resolves to an existing file (zero broken paths).
- [ ] README `i18n-formats` description ("Loaded on demand by the other two skills") still accurate.

**Stage 2 handoff:** 13 pointer edits across 6 files (i18n-translate, i18n-audit, translator agent, 3 commands). Vague "relevant section of i18n-formats" replaced with `references/<format>.md` or an explicit dispatch-table pointer. `<format>` left as a placeholder the consumer resolves at runtime (9 occurrences, intentional); concrete paths used where the format is fixed (gettext.md in add-locale). No file conflicts — all 6 disjoint.

---

## Stage 3: Verify & regression

**Goal:** Both validators stay green/pass, the target finding is cleared, and the git diff is provably moves + pointer rewires only.
**Depends on:** Stage 2 gate passing
**Blocks:** none
**Risk:** LOW
**Rollback:** delete the branch — `main` is untouched.

### Task 3.1: plugin-dev structural validation
- **Status:** [x]
- **Depends on:** Task 2.1, Task 2.2, Task 2.3, Task 2.4
- **Blocks:** Task 3.3
- **Parallel:** NO (whole-plugin check; runs after all rewiring)
- **Test:** `bash plugin-dev/scripts/validate-plugin.sh i18n --json | jq '.summary'` → `errors:0, warnings:0`, and `info` count for `i18n-formats` paths is 0 (baseline `skill-no-references` cleared; no new findings).
- **Red-Green max cycles:** 3

### Task 3.2: i18n domain validation
- **Status:** [x]
- **Depends on:** Task 2.1, Task 2.2, Task 2.3, Task 2.4
- **Blocks:** Task 3.3
- **Parallel:** YES (independent of 3.1; read-only checks, no file writes)
- **Test:** `bash i18n/scripts/validate.sh i18n --json | jq '.verdict'` → `"pass"` (no regression vs baseline).
- **Red-Green max cycles:** 3

### Task 3.3: Content-integrity & diff review
- **Status:** [x]
- **Depends on:** Task 3.1, Task 3.2
- **Blocks:** none
- **Parallel:** NO (final gate, after validators green)
- **Test:** Union of new SKILL.md + all `references/*.md` contains every format-gotcha line from `git show main:i18n/skills/i18n-formats/SKILL.md` (no prose deleted, only relocated); `git diff --stat main` shows additions under `references/`, a shrunken SKILL.md, and pointer-only edits in the six consumer files — no unexpected files touched.
- **Red-Green max cycles:** 3

### Stage 3 Gate
- [ ] `validate-plugin.sh i18n` → 0 errors, 0 warnings, `skill-no-references` for i18n-formats gone.
- [ ] `i18n/scripts/validate.sh i18n` → `pass`.
- [ ] Content-integrity diff confirms no format guidance lost; consumer edits are pointer-only.
- [ ] (Optional manual spot-check) Pick one format (e.g. Android): the dispatch table in SKILL.md → `references/android.md` round-trips and the Android quoting/`%1$s`/plurals guidance is intact.

---

**Notes for execution**
- Work on branch `i18n-formats-progressive-disclosure`; do not commit to `main`.
- Tasks 1.1, then 2.1–2.4 in parallel (disjoint files), then 3.x. The only true serialization is 1.1 → 1.2 → (2.x fan-out) → 3.x.
- Bump `i18n/.claude-plugin/plugin.json` version (patch) as part of Stage 3 if the repo convention ships a version with skill changes — check sibling plugins' history first.


**Stage 3 handoff:** plugin-dev validate `{0,0,0}` (skill-no-references cleared); i18n domain validate `pass` (info:2 = baseline `i18n-no-framework`, unrelated). Content-integrity: every format-section content line from `main` present in references/ except the one intentional Django cross-link rewording (`see gettext section` → `see [gettext.md]`); Django specifics intact. Independent evaluator (fresh agent, goals-only brief): OVERALL PASS, 5/5 criteria. Bumped i18n 0.2.0 → 0.2.1 (plugin.json + marketplace.json) per repo convention.

**Completed:** 2026-06-09 — commits: 7e4475f (Stage 1), 8796578 (Stage 2), +Stage 3 close-out
