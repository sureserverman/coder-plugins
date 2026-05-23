# Backlog

Deferred items from plan execution, code review, or ad-hoc capture. Entries are removed when implemented; git history is the audit trail.

---

## BL-001 — Implement bar

- **Opened:** 2026-04-20
- **Source:** docs/sample-plans/2026-04-15-partial-with-deferred-plan.md — Stage 2 / Task 2.1
- **Reason:** Deferred while we figure out the backend; tracked here so it isn't lost.
- **Next step:** Pick up after the schema discussion lands.
- **Tags:** fixture, bar

This fixture entry exists to test the unify dedup rule: a candidate from
the partial plan that shares this exact Source string MUST be dropped.
