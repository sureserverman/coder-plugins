# Project Plan: Every task partial
Date: 2026-07-24

Lockstep guard for the authoritative-path detection regex. Every task here is
`[~]`. While that character was missing from the detection class (but present
in STATUS_RE) this file matched nothing, fell through to the LEGACY heuristic,
and emitted its gate bullet as a candidate instead of its task — a silent
mis-classification of the whole file, not just one line.

## Stage 1: Only partial tasks

### Task 1.1: ALLPARTIAL-A: in flight
- **Status:** [~]
- **Test:** `true`

### Stage 1 Gate
- [ ] ALLPARTIAL-GATE-MARKER: must never surface as a candidate
