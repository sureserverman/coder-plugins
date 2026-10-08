# Project Plan: goal-check fixture — a filtered sweep the author scoped
Date: 2026-10-08

## Stage 1: Rule every new row

**Goal:** every `-new` row of the lane table has a ruling; `-fork` rows are ruled by another plan.

### Task 1.1: Write the rulings
- **Status:** [ ]
- **Test:** `python3 docs/verify-rulings.py`

### Stage 1 Gate

- [ ] **(goal)** (scoped) `awk -F'|' '$3 ~ /-new/ {print $2}' docs/spec.md | while read p; do grep -qF "$p" docs/rulings.md || echo "unruled $p"; done | wc -l` prints 0 — the `-new` rows are this plan's whole set; `-fork` rows belong to sub-plan 2
