# Project Plan: Decisions Section Parser Safety (Standard)
Date: 2026-07-25

## Research Summary

### Project context
- Fixture: a Standard plan carrying a `## Decisions in force` section.

## Decisions in force

- DEC-001 — DECISIONS-SECTION-MARKER project entry (accepted; security) — constraint in one line
- GDEC-SEC-001 — DECISIONS-SECTION-MARKER domain entry (accepted; security) — constraint in one line
- none — registers consulted: rust, ubuntu; no further entry binds this scope

**Registers consulted:** security, rust (project register: absent — new project)
**Domains inferred:** security, rust, tor (no register exists for `tor` yet)

## Preflight

- [ ] PREFLIGHT-MARKER baseline suite passes

---

## Stage 1: Only real task

**Goal:** one unchecked task, nothing else
**Depends on:** none
**Blocks:** none
**Risk:** LOW — fixture
**Rollback:** none

### Task 1.1: REAL-CANDIDATE-MARKER the one deferred task
- **Status:** [ ]
- **Depends on:** none
- **Blocks:** none
- **Parallel:** YES
- **Test:** `true`
- **Red-Green max cycles:** 3

### Stage 1 Gate
- [ ] GATE-MARKER integration check
- [ ] No change contradicts a decision in force (DEC-001, GDEC-SEC-001); any Supersedes citation recorded
