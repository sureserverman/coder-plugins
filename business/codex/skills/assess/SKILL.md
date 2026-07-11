---
name: assess
description: "Viability triage for one project → business/BUSINESS.md verdict (monetize | free-for-reputation | internal-only | park). Optional --research."

---

# assess (Codex front-end)

Thin Codex adapter over the shared business-plugin logic. The **canonical, full
procedure** (Phases 1–5, interview guidance, verdict rules) is
`business/skills/assess/SKILL.md` — follow it exactly; this file only adapts it to Codex.

## Determinism boundary

Read cross-project state via the sole parser; `Read` the actual file for in-place edits
(the JSON omits `project:` and the body):

```
python3 scripts/business-scan.py
```

Write `business/BUSINESS.md` per `references/business-md-format.md` (schema 1). With
`--research`, dispatch the `agents/market-researcher.md` agent for cited market evidence.

## Shared assets (do not duplicate — kept in sync by lint-dual.py)

- `scripts/business-scan.py`
- `references/business-md-format.md`
- `agents/market-researcher.md`

## In brief

Ground in repo + vault + MATURITY.md → structured interview → verdict. `park` and
`internal-only` are complete outcomes. On re-assessment, preserve `model`'s
monetization/targets unless the verdict changed. Verify: scanner shows `assessed: true`,
correct verdict, zero `errors`.
