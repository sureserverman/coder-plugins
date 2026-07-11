# gtm-plan.md format

`gtm-plan.md` is a project's **go-to-market plan** — a dated checklist of concrete launch
actions. It lives at `<vault_dir>/Portfolio/<area>/<project>/business/gtm-plan.md`. The
`launch` skill writes it; the operator ticks items off over subsequent sessions.

## Parseability — the shared checkbox contract

Progress rolls up through `business-scan.py`, which **imports** portfolio-unify's
`CHECKED` / `UNCHECKED` regexes (one contract, one implementation) and counts checkbox
bullets:

- `CHECKED  = ^\s*-\s*\[x\]\s+`  (done)
- `UNCHECKED = ^\s*-\s*\[ \]\s+(.+)$` (open)

So **every launch action is a `- [ ]` / `- [x]` checkbox bullet.** The scanner reports
`gtm: {done, total, pct}` per project from these counts.

> gtm-plan.md deliberately lives under `business/`, **not** under the vault's `plans/`
> dir, so portfolio-unify never scans it for backlog candidates — only `business-scan.py`
> reads it. This is why a flat checkbox checklist (not the staged `### Task N.M` +
> `**Status:**` execution-plan format) is correct here: it's a marketing checklist, not a
> Red-Green build plan.

## Structure

```markdown
# Go-to-market plan: <project>
Date: 2026-07-11
Verdict: monetize · Model: paid · See ./BUSINESS.md

## Pre-launch
- [ ] Finalize store listing copy + screenshots
- [ ] Write the announcement post
- [ ] Set up the F-Droid metadata (fastlane structure)

## Launch
- [ ] Tag and sign the release
- [ ] Submit to F-Droid
- [ ] Publish the announcement (target: 2026-07-20)

## Post-launch
- [ ] First `/business:track` pass one week after launch
- [ ] Collect and triage user feedback
```

## Rules

- **Only launch actions are checkboxes.** Section headings (`## Pre-launch`) are plain
  `##` headers — they carry no checkbox and are not counted.
- Keep dates inline in the action text (`target: 2026-07-20`) — the scanner counts
  progress, it does not schedule.
- No `### Stage N Gate` / Preflight sections here — those are execution-plan constructs.
  A GTM plan is one flat list of grouped actions.
