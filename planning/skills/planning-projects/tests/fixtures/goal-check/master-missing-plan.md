# Master Plan: goal-check fixture — one register entry lacks a (goal) check
Date: 2026-10-08

## Sub-plans

### Sub-plan 1: Spec
- **Status:** [ ]
- **Plan:** ./sub-01-plan.md
- **Goal:** every lane path has a ruling.
- **Depends on:** none

**Gate:**
- [ ] **(goal)** `python3 docs/verify-rulings.py --all` exits 0 — every lane path has a ruling

### Sub-plan 2: Lane
- **Status:** [ ]
- **Plan:** ./sub-02-plan.md
- **Goal:** the lane's copy dir equals upstream.
- **Depends on:** Sub-plan 1

**Gate:**
- [ ] `python3 docs/verify-lane.py` exits 0
