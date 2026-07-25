# Decisions

---

## DEC-004 — Resolver binds inside the Orbot tunnel

- **Decided:** 2026-07-21
- **Status:** accepted
- **Domains:** android, tor
- **Source:** direct
- **Reason:** A resolver outside the tunnel leaks queries on profile switch.
- **Global:** [[decisions/android#GDEC-AND-009]]

---

## DEC-003 — Links a real GDEC but names the wrong domain file

- **Decided:** 2026-07-22
- **Status:** accepted
- **Domains:** android
- **Source:** direct
- **Reason:** GDEC-AND-011 lives in android.md, not rust.md — the mistyped domain
  segment must be reported instead of silently resolving on the ID alone.
- **Global:** [[decisions/rust#GDEC-AND-011]]
