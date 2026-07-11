---
name: model
description: "Set an assess-passed project's monetization model, pricing hypothesis, channels, and numeric dated targets in business/BUSINESS.md."

---

# model (Codex front-end)

Thin Codex adapter. Canonical full procedure: `business/skills/model/SKILL.md` — follow it
exactly.

## Determinism boundary

```
python3 scripts/business-scan.py
```

Read verdict/monetization/targets from the scanner JSON; `Read` the actual
`business/BUSINESS.md` for targeted in-place edits (JSON omits `project:` + body). Write
per `references/business-md-format.md`.

## Shared assets (kept in sync by lint-dual.py)

- `scripts/business-scan.py`
- `references/business-md-format.md`

## In brief

Precondition: verdict `monetize` or `free-for-reputation` (else stop → assess). Present
model options one decision at a time → set model, pricing hypothesis, channels, and at
least one numeric dated target. Verify: scanner carries model + targets, zero `errors`.
