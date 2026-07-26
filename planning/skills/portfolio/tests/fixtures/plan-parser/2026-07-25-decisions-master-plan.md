# Master Plan: Decisions Section at Master Level
Date: 2026-07-25

## Research Summary

Fixture: a master plan carrying `## Decisions in force` above its register.

## Decisions in force

- DEC-001 — MASTERDEC-MARKER entry (accepted; security) — constraint in one line
- GDEC-SEC-001 — MASTERDEC-MARKER domain entry (accepted; security) — constraint in one line

**Registers consulted:** security   **Domains inferred:** security

## Sub-plans

### Sub-plan 1: First
- **Status:** [ ]
- **Plan:** ./2026-07-25-decisions-standard-plan.md
- **Goal:** fixture entry
- **Depends on:** none
- **Blocks:** Sub-plan 2
- **Parallel:** YES

**Gate:**
- [ ] MASTERDECGATE-MARKER integration check

### Sub-plan 2: Second
- **Status:** [ ]
- **Plan:** ./2026-07-25-decisions-light-plan.md
- **Goal:** fixture entry
- **Depends on:** Sub-plan 1
- **Blocks:** none
- **Parallel:** NO (blocked by Sub-plan 1)

**Gate:**
- [ ] MASTERDECGATE-MARKER cross-plan check
