---
name: track
description: "Record a project's actual metrics → business/metrics.md (GitHub auto + manual), diff vs targets, bump Last reviewed."

---

# track (Codex front-end)

Thin Codex adapter. Canonical full procedure: `business/skills/track/SKILL.md` — follow it
exactly.

## Determinism boundary

```
python3 scripts/business-scan.py
python3 scripts/collect-github.py <repo_path>
```

Append to `business/metrics.md` per `references/metrics-format.md`; bump `last_reviewed` in
`business/BUSINESS.md` via a targeted `Read`+edit (preserve `project:` + body, per
`references/business-md-format.md`).

## Shared assets (kept in sync by lint-dual.py)

- `scripts/business-scan.py`
- `scripts/collect-github.py`
- `references/metrics-format.md`
- `references/business-md-format.md`

## In brief

Auto-collect GitHub metrics (check `reasons["_"]` first when all null, then per-metric
reasons) → prompt for manual figures → append a dated source-tagged block (never edit
prior blocks) → diff vs targets (match target `metric` to a metrics key by suffix after
the last `.`) → bump `last_reviewed`.
