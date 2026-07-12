# business

Per-project business-planning pipeline for the `~/dev` portfolio. Turns a
shippable project into a commercial decision and keeps it tracked, storing
artifacts in the vault portfolio homes alongside `MATURITY.md` so the planning
plugin's `portfolio` and `compass` skills can read business state.

## Skills

| Skill | Does |
|-------|------|
| `/business:assess` | Viability triage → `business/BUSINESS.md` verdict (monetize / free-for-reputation / internal-only / park). Opt-in `--research`. |
| `/business:revenue-model` | Monetization model, pricing, channels, numeric dated targets for an assess-passed project. |
| `/business:launch` | Go-to-market plan → `business/gtm-plan.md`, guarded by `MATURITY.md` state. |
| `/business:track` | Record actuals → `business/metrics.md`, diff vs targets, bump Last reviewed. |
| `/business:biz-portfolio` | Sweep every project, rebuild `global-business.md`. |

## Artifacts (in the vault)

Per project, under `<vault_dir>/Portfolio/<area>/<project>/business/`:

- `BUSINESS.md` — canonical, schema-versioned. Sole machine-readable index.
- `gtm-plan.md` — dated go-to-market checklist (portfolio-unify-parseable).
- `metrics.md` — append-only actuals log.

Roll-up: `<vault_dir>/Portfolio/global-business.md`.

## Determinism boundary

`scripts/business-scan.py` is the **only** parser of the business artifacts. It
emits one JSON document; every skill and every planning-plugin integration
consumes that JSON, never the markdown. The scanner reuses `portfolio-unify`'s
plan-parser regexes for `gtm-plan.md` progress — one contract, one implementation.

## Design & plan

- Design: `<vault>/Portfolio/ai-tools/business-planning/plans/2026-07-11-business-plugin-design.md`
- Plan: `<vault>/Portfolio/ai-tools/business-planning/plans/2026-07-11-business-plugin-plan.md`
