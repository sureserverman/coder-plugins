---
name: biz-portfolio
description: "Sweep every registry project's business state and rebuild the global-business.md roll-up."

---

# biz-portfolio (Codex front-end)

Thin Codex adapter. Canonical full procedure: `business/skills/biz-portfolio/SKILL.md` —
follow it exactly, including the **atomic write** (temp + `set -o pipefail` + `mv`) so a
failed sweep never truncates the roll-up.

## Determinism boundary

```
python3 scripts/business-scan.py | python3 scripts/business-rollup.py > <tmp> && mv <tmp> <dest>
```

`<dest>` is `scripts/resolve-dest.py`'s output — `<vault_dir>/Portfolio/global-business.md`,
conforming to `references/global-business-format.md`. Resolving it via the script (not an
inline heredoc) reuses the scanner's config resolver and its clean "portfolio not
configured" error.

## Shared assets (kept in sync by lint-dual.py)

- `scripts/business-scan.py`
- `scripts/business-rollup.py`
- `scripts/resolve-dest.py`
- `references/global-business-format.md`

## In brief

Rebuild `global-business.md`; report coverage, verdict counts, pipeline stage (read the
rendered Stage column), staleness, and every `couldnt_assess`/`errors` entry loudly.
Report + rebuild only — never start the work it surfaces.
