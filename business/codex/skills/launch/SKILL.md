---
name: launch
description: "Write a MATURITY-guarded go-to-market checklist for an assessed+modeled project → business/gtm-plan.md."

---

# launch (Codex front-end)

Thin Codex adapter. Canonical full procedure: `business/skills/launch/SKILL.md` — follow it
exactly.

## Determinism boundary

```
python3 scripts/business-scan.py
```

Write `business/gtm-plan.md` per `references/gtm-plan-format.md` (a flat `- [ ]`/`- [x]`
checkbox checklist — the scanner counts checkbox bullets). Preserve ticked boxes when
re-planning.

## Shared assets (kept in sync by lint-dual.py)

- `scripts/business-scan.py`
- `references/gtm-plan-format.md`

## In brief

Precondition: `monetization.model` set (else stop → model; if `assessed: false`, stop →
assess). `Read` the project's `MATURITY.md` and **warn (never block)** on open
Documentation/Security/Packaging items before planning. Write dated launch actions grouped
by phase, tied to the `channels` in `BUSINESS.md`. Verify: scanner reports `gtm`
`{done,total,pct}`.
