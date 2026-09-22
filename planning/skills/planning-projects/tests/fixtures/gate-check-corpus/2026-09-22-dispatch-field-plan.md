# Project Plan: Retry budget for the sync worker
Date: 2026-09-22

Adds a bounded retry budget to the sync worker so a flapping upstream stops producing
unbounded retry storms, and surfaces the budget in the status command.

## Research Summary

- **The worker retries forever today.** `src/sync/worker.py` wraps the upload in a
  `while True` loop with a fixed 2s sleep; there is no counter and no ceiling.
- **The status command already reads worker state** from `state/worker.json`
  (`src/cli/status.py`), so exposing the budget needs one new key, not a new channel.
- **Test layout** — pytest under `tests/`, one module per source module. The full suite
  runs in 11s, so no test-scope tiering is needed; every gate runs it in full.
- **No architecture doc covers this scope.** Structure is decided inline.

## Decisions in force

- None bind this scope. Registers consulted: the project `decisions.md` (DEC-001 … DEC-004);
  none touch the sync worker or the status command.

## Preflight

- [ ] Baseline green: `python3 -m pytest -q` exits 0
- [ ] Working tree clean at branch point; branch `sync-retry-budget` created off `main`

---

## Stage 1: Bounded retries

**Goal:** The worker gives up after a configured number of attempts and records why.
**Depends on:** none
**Blocks:** Stage 2
**Risk:** LOW — the loop is replaced by a counted loop; the happy path is unchanged.
**Rollback:** `git revert` the stage's commits.

### Task 1.1: Add `retry_budget` to the config schema
- **Status:** [ ]
- **Depends on:** none
- **Blocks:** Task 1.3
- **Dispatch:** YES
- **Scope:** `src/sync/config.py` and its schema test
- **Test:** `python3 -m pytest -q tests/test_config.py` passes with a case asserting a missing `retry_budget` defaults to 5 and a negative one is rejected
- **Red-Green max cycles:** 2

### Task 1.2: Backoff helper
- **Status:** [ ]
- **Depends on:** none
- **Blocks:** Task 1.3
- **Dispatch:** YES
- **Scope:** new `src/sync/backoff.py`
- **Test:** `python3 -m pytest -q tests/test_backoff.py` passes, asserting the delay doubles per attempt and caps at 60s
- **Red-Green max cycles:** 2

### Task 1.3: Counted retry loop in the worker
- **Status:** [ ]
- **Depends on:** Task 1.1, Task 1.2
- **Blocks:** none
- **Dispatch:** NO (blocked by 1.1, 1.2 — integrates both)
- **Scope:** the retry loop in `src/sync/worker.py`
- **Test:** `python3 -m pytest -q tests/test_worker.py` passes with a case where the upstream fails every call and the worker stops after exactly `retry_budget` attempts, writing `"gave_up": true`
- **Red-Green max cycles:** 3

### Stage 1 Gate
- [ ] Full suite green: `python3 -m pytest -q`
- [ ] A worker against a dead upstream stops at the budget: `python3 -m sync.worker --simulate-failures | grep -q 'gave up after 5 attempts'`
- [ ] Config default is live: `python3 -m sync.config --print-defaults | grep -q 'retry_budget: 5'`

---

## Stage 2: Surface the budget

**Goal:** `sync status` shows attempts used against the budget, and a worker that gave up
is visible without reading logs.
**Depends on:** Stage 1 gate passing
**Blocks:** none
**Risk:** LOW — additive output only.
**Rollback:** `git revert` the stage's commits.

### Task 2.1: Write attempts to the state file
- **Status:** [ ]
- **Depends on:** none (Stage 1 gate is the only precondition)
- **Blocks:** Task 2.2
- **Dispatch:** NO
- **Scope:** the state writer in `src/sync/worker.py`
- **Test:** `python3 -m pytest -q tests/test_worker.py` passes with a case asserting `state/worker.json` carries `attempts` and `retry_budget` after a failed run
- **Red-Green max cycles:** 2

### Task 2.2: Render the budget in `sync status`
- **Status:** [ ]
- **Depends on:** Task 2.1
- **Blocks:** none
- **Dispatch:** NO (blocked by 2.1)
- **Scope:** `src/cli/status.py`
- **Test:** `python3 -m pytest -q tests/test_status.py` passes with a case asserting the output line `retries: 5/5 (gave up)`
- **Red-Green max cycles:** 2

### Stage 2 Gate
- [ ] Full suite green: `python3 -m pytest -q`
- [ ] Status renders from a real state file: `python3 -m sync status --state tests/fixtures/gave-up.json | grep -q 'gave up'`
