# Project Plan: All-Checked Fixture
Date: 2026-04-01

This plan is fully executed. The parser should emit ZERO candidates from this file.

## Preflight
- [x] **Tool installed**: `foo --version` returns
- [x] **Baseline clean**: `make test` passes

## Stage 1: Single trivial stage

**Goal:** prove the checked-state path works.
**Depends on:** none
**Blocks:** none
**Risk:** LOW
**Rollback:** `git checkout -- .`

### Task 1.1: Implement foo
- **Depends on:** none
- **Blocks:** Task 1.2
- **Parallel:** YES
- **Test:** `foo --self-check`
- **Red-Green max cycles:** 3
- [x] implemented
- [x] tested

### Task 1.2: Document foo
- **Depends on:** Task 1.1
- **Blocks:** none
- **Parallel:** NO
- **Test:** `grep -q foo README.md`
- **Red-Green max cycles:** 3
- [x] README updated

### Stage 1 Gate
- [x] `foo --self-check` returns 0
- [x] README mentions foo
- [x] No regressions in `make test`
