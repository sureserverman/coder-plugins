# Master Plan: Dispatch fixture — YES entries that lean on a sibling
Date: 2026-09-23

Negative fixture for MASTER-YES-SIBLING-DEP, both shapes. Sub-plan 2 is the openclaw
shape: `Depends on: none` with a prose excuse, `Parallel: YES`, but its gate reads a
sibling's output. Sub-plan 3 names a sibling in `Depends on` outright.

## Sub-plans

### Sub-plan 1: One
- **Status:** [ ]
- **Plan:** ./master-yes-sibling-dep-sub-01-plan.md
- **Goal:** ship one.
- **Depends on:** none
- **Blocks:** Sub-plan 3
- **Parallel:** YES

**Gate:**
- [ ] `pytest one/tests/` exits 0

### Sub-plan 2: Two
- **Status:** [ ]
- **Plan:** ./master-yes-sibling-dep-sub-02-plan.md
- **Goal:** ship two.
- **Depends on:** none (scheduled second by owner decision)
- **Blocks:** none
- **Parallel:** YES

**Gate:**
- [ ] Both consumers read the value from `two/cli.py` — Sub-plan 1's
      module and this one agree on it.

### Sub-plan 3: Three
- **Status:** [ ]
- **Plan:** ./master-yes-sibling-dep-sub-03-plan.md
- **Goal:** ship three.
- **Depends on:** Sub-plan 1
- **Blocks:** none
- **Parallel:** YES

**Gate:**
- [ ] `pytest three/tests/` exits 0
