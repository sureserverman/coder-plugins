# Project Plan: goal-check fixture — sweeps restricted by a category filter
Date: 2026-10-08

## Stage 1: Rule every row

**Goal:** every row of the lane table has a ruling.

### Task 1.1: Write the rulings
- **Status:** [ ]
- **Test:** `python3 docs/verify-rulings.py`

### Stage 1 Gate

- [ ] **(goal)** `awk -F'|' '$3 ~ /-new/ {print $2}' docs/spec.md | while read p; do grep -qF "$p" docs/rulings.md || echo "unruled $p"; done | wc -l` prints 0 — every new row is ruled
- [ ] `git ls-files 'docs/*.md' | grep -v '^docs/archive/' | xargs grep -L 'Status:' | wc -l` prints 0 — every doc carries a status
- [ ] `grep -rL 'Status:' docs/ | wc -l` prints 0 — every doc carries a status, unfiltered
- [ ] `python3 docs/verify-rulings.py | grep -q 'OK'` — the verifier reports OK
