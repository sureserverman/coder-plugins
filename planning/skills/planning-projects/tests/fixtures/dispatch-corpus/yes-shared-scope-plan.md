# Project Plan: Dispatch fixture — two YES tasks share a file
Date: 2026-09-23

Negative fixture: Tasks 1.1 and 1.2 are both `Dispatch: YES` in one stage and both
touch `plan-progress.py` — one names it by full path, the other by bare filename.

## Stage 1: One stage

**Goal:** trip YES-SHARED-SCOPE.
**Depends on:** none
**Blocks:** none

### Task 1.1: Add the dispatch regex
- **Status:** [ ]
- **Depends on:** none
- **Blocks:** none
- **Dispatch:** YES
- **Scope:** `planning/skills/executing-plans/scripts/plan-progress.py`, `planning/skills/executing-plans/tests/test-plan-progress.py`
- **Test:** `python3 planning/skills/executing-plans/tests/test-plan-progress.py` exits 0

### Task 1.2: Add the stage-order marker
- **Status:** [ ]
- **Depends on:** none
- **Blocks:** none
- **Dispatch:** YES
- **Scope:** `plan-progress.py` (`--stage-order-check`), `planning/skills/executing-plans/references/progress-state-file.md`
- **Test:** `python3 planning/skills/executing-plans/scripts/plan-progress.py --stage-order-check x` exits 0

### Stage 1 Gate
- [ ] `python3 planning/skills/executing-plans/tests/test-plan-progress.py` exits 0
