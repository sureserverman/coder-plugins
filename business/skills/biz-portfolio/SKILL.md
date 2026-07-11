---
name: biz-portfolio
description: >
  Sweep every registry project's business state and rebuild the global-business.md roll-up. Use for a portfolio-wide view of commercial coverage — verdicts, stages, staleness, and which projects still need a viability verdict. Triggers on "business portfolio sweep", "which projects have a business case", "business coverage across projects", "rebuild global-business", "who still needs a viability verdict", "portfolio monetization overview".
---

# biz-portfolio — portfolio business sweep

Give a one-command, portfolio-wide picture of commercial coverage and rebuild the
`global-business.md` roll-up.

**Announce at start:** "Using the business biz-portfolio skill to sweep all projects."

## Determinism boundary

The whole sweep is two deterministic scripts piped together — the scanner (sole parser)
into the renderer (pure formatter). Never parse the vault yourself:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/business-scan.py \
  | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/business-rollup.py \
  > "$(python3 - <<'PY'
import yaml, pathlib
cfg = yaml.safe_load(open(pathlib.Path.home()/'.claude'/'portfolio-config.yaml'))
print(pathlib.Path(cfg['vault_dir'])/'Portfolio'/'global-business.md')
PY
)"
```

`global-business.md` conforms to `${CLAUDE_PLUGIN_ROOT}/references/global-business-format.md`
and sits beside `global-backlog.md` / `global-maturity.md`. It is machine-generated —
regenerate it, never hand-edit.

## What to report

Read the scanner JSON once (the same run that fed the rollup) and narrate the coverage —
judgment only, never re-deriving a fact the JSON doesn't carry:

- **Coverage:** how many projects are assessed vs. the triage gap (not yet assessed).
- **By verdict:** counts of monetize / free-for-reputation / internal-only / park.
- **Pipeline:** how many have reached modeled / launched / tracked.
- **Staleness:** projects whose `last_reviewed_age_days` is large — candidates for a fresh
  `/business:track` or re-assessment.
- **Loudly:** every `couldnt_assess` entry and every project with `errors` — surfaced, not
  smoothed over. If any exist, say so plainly.

## Hard rules

- **Report + rebuild only.** Write `global-business.md`; never start the work it surfaces
  (don't launch, don't assess). Recommending "these 3 projects have a validated business
  case but no GTM plan — consider `/business:launch`" is good; doing it is not.
- **Every claim cites the JSON** — a count, a verdict, a staleness age. No vibes.
- **Degrade loudly.** A project the scanner couldn't assess is named in the report and the
  rollup's "Couldn't assess" section, never dropped.
