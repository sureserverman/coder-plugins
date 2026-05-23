# Project Plan: Three-Unchecked Fixture
Date: 2026-05-01

This plan has 3 unchecked tasks across 1 stage. Project has no existing
backlog.md — unify should auto-create one and add all 3 candidates.

## Preflight
- [x] **Tool installed**: `baz --version` returns

## Stage 1: Build baz

**Goal:** ship baz v1.
**Depends on:** none
**Blocks:** none
**Risk:** MEDIUM
**Rollback:** `git checkout -- .`

### Task 1.1: Scaffold baz module
- **Depends on:** none
- **Blocks:** Task 1.2, Task 1.3
- **Parallel:** YES
- **Test:** `baz --module-check`
- **Red-Green max cycles:** 3
- [ ] not started

### Task 1.2: Implement baz handler
- **Depends on:** Task 1.1
- **Blocks:** none
- **Parallel:** NO
- **Test:** `baz --handler-check`
- **Red-Green max cycles:** 3
- [ ] not started

### Task 1.3: Wire baz CLI
- **Depends on:** Task 1.1
- **Blocks:** none
- **Parallel:** NO
- **Test:** `baz --cli-check`
- **Red-Green max cycles:** 3
- [ ] not started

### Stage 1 Gate
- [ ] `baz --module-check && baz --handler-check && baz --cli-check`
