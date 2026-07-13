---
name: biz-portfolio
description: >
  Sweep every registry project's business state and rebuild the global-business.md roll-up — a portfolio-wide view of verdicts, stages, and staleness. Triggers on "business portfolio sweep", "which projects have a business case", "rebuild global-business", "portfolio monetization overview".
---

# biz-portfolio — portfolio business sweep

Give a one-command, portfolio-wide picture of commercial coverage and rebuild the
`global-business.md` roll-up.

**Announce at start:** "Using the business biz-portfolio skill to sweep all projects."

## Determinism boundary

The whole sweep is two deterministic scripts piped together — the scanner (sole parser)
into the renderer (pure formatter). Never parse the vault yourself. **Write atomically** —
a failed sweep must leave the existing `global-business.md` intact, never truncate it to
an empty file (`> file` truncates *before* the pipeline runs):

`resolve-dest.py` resolves the destination via the same `load_env` the scanner uses, so a
missing/malformed portfolio-config yields the scanner's clean "portfolio not configured"
message instead of a raw traceback — don't re-derive the path inline.

```bash
set -o pipefail
DEST="$(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve-dest.py)" || exit 1
TMP="$(mktemp "${DEST}.XXXXXX")"
if python3 ${CLAUDE_PLUGIN_ROOT}/scripts/business-scan.py \
     | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/business-rollup.py > "$TMP"; then
  mv -f "$TMP" "$DEST"
else
  rm -f "$TMP"
  echo "biz-portfolio: sweep failed — left existing $DEST untouched" >&2
  exit 1
fi
```

`global-business.md` conforms to `${CLAUDE_PLUGIN_ROOT}/references/global-business-format.md`
and sits beside `global-backlog.md` / `global-maturity.md`. It is machine-generated —
regenerate it, never hand-edit.

## What to report

Narrate the coverage — judgment only. For raw facts, read the scanner JSON (the same run
that fed the rollup); for the **pipeline stage**, read the **Stage column of the rendered
`global-business.md`** rather than recomputing it — stage is a *derived* value
(tracked > launched > modeled > assessed, per global-business-format.md), not a raw JSON
field, so recomputing it risks disagreeing with the table you just wrote.

- **Coverage:** how many projects are assessed vs. the triage gap (not yet assessed).
- **By verdict:** counts of monetize / free-for-reputation / internal-only / park.
- **Pipeline:** how many rows in each Stage (modeled / launched / tracked), read off the
  rendered table.
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
