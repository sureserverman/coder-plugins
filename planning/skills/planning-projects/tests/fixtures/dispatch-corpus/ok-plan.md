# Project Plan: Dispatch fixture — clean
Date: 2026-09-23

Fixture for `test-validate-dispatch.py`: every field is consistent, so the validator exits 0.
It also carries the two shapes that must NOT be read as a shared scope (two different
`SKILL.md` full paths; backticked prose inside a parenthetical), and exactly one NO task
that could be YES (Task 2.1) next to one that could not (Task 1.3).

## Stage 1: Two independent edits, then a join

**Goal:** exercise the YES/NO rules.
**Depends on:** none
**Blocks:** Stage 2

### Task 1.1: Edit the planning skill
- **Status:** [ ]
- **Depends on:** none
- **Blocks:** Task 1.3
- **Dispatch:** YES
- **Scope:** `planning/skills/planning-projects/SKILL.md` (§ `## Checklist`; `Dispatch:` wording), `planning/skills/planning-projects/references/task-fields.md`
- **Test:** `grep -c 'Dispatch:' planning/skills/planning-projects/SKILL.md` ≥ 1

### Task 1.2: Edit the executing skill
- **Status:** [ ]
- **Depends on:** none
- **Blocks:** Task 1.3
- **Dispatch:** YES
- **Scope:** `planning/skills/executing-plans/SKILL.md` (§ `## Checklist`), `planning/skills/executing-plans/references/stage-gate.md`
- **Test:** `grep -c 'Dispatch:' planning/skills/executing-plans/SKILL.md` ≥ 1

### Task 1.3: Contract test pins both
- **Status:** [ ]
- **Depends on:** Task 1.1, Task 1.2
- **Blocks:** Stage 2
- **Dispatch:** NO (blocked by 1.1, 1.2)
- **Scope:** `planning/skills/executing-plans/tests/test-contract.py`
- **Test:** `python3 planning/skills/executing-plans/tests/test-contract.py` exits 0

### Stage 1 Gate
- [ ] `python3 planning/skills/executing-plans/tests/test-contract.py` exits 0

## Stage 2: Release

**Goal:** bump and document.
**Depends on:** Stage 1 gate passing
**Blocks:** none

### Task 2.1: Write the changelog entry
- **Status:** [ ]
- **Depends on:** Task 1.3
- **Blocks:** none
- **Dispatch:** NO (blocked by 1.3)
- **Scope:** `planning/CHANGELOG.md`, `planning/README.md`
- **Test:** `grep -c '0.51.0' planning/CHANGELOG.md` ≥ 1

### Task 2.2: Bump the version
- **Status:** [ ]
- **Depends on:** none
- **Blocks:** none
- **Dispatch:** YES
- **Scope:** `planning/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`
- **Test:** `python3 scripts/check-version-mirrors.py` exits 0

### Stage 2 Gate
- [ ] `python3 scripts/check-version-mirrors.py` exits 0
