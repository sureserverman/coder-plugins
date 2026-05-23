# Project Plan: Partial-With-Deferred Fixture
Date: 2026-04-15

This plan has 2 unchecked tasks and 1 Deferred-section entry.
Expected candidates from this file:
  - Stage 2 / Task 2.1 (unchecked-task)
  - Stage 2 / Task 2.2 (unchecked-task)
  - Deferred / bullet 1 (deferred-section)

NOTE: one of the unchecked-task candidates' Source string matches
an existing BL entry in this fixture project's backlog.md, so the
unify dedup should drop it. Net: 2 new candidates.

## Preflight
- [x] **Tool installed**: `bar --version` returns
- [x] **Baseline clean**: `make test` passes

## Stage 1: Setup (done)

### Task 1.1: Setup bar
- **Depends on:** none
- **Blocks:** Task 2.1
- **Parallel:** YES
- **Test:** `bar --setup-check`
- **Red-Green max cycles:** 3
- [x] done

### Stage 1 Gate
- [x] `bar --setup-check` returns 0

## Stage 2: Feature work (in progress)

### Task 2.1: Implement bar
- **Depends on:** Task 1.1
- **Blocks:** Task 2.2
- **Parallel:** NO
- **Test:** `bar --feature-check`
- **Red-Green max cycles:** 3
- [ ] still working on it

### Task 2.2: Document bar
- **Depends on:** Task 2.1
- **Blocks:** none
- **Parallel:** NO
- **Test:** `grep -q bar README.md`
- **Red-Green max cycles:** 3
- [ ] not started

### Stage 2 Gate
- [ ] `bar --feature-check` returns 0
- [ ] README mentions bar

## Deferred

- Pluggable bar backends — out of scope for v1; revisit when there's a
  second backend on the horizon.
