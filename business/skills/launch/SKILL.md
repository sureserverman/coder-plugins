---
name: launch
description: >
  Build a go-to-market plan for a portfolio project whose monetization model is decided — a dated checklist of concrete launch actions at business/gtm-plan.md. Use when a project is ready to plan its launch. Triggers on "plan the launch", "go-to-market plan", "how do I ship this to users", "GTM for this project", "launch checklist", "distribution plan". Guarded by the project's ship-readiness (MATURITY.md) — warns before planning a launch for something not near-ready.
---

# launch — go-to-market plan

Turn a decided monetization model into a concrete, dated launch checklist at
`business/gtm-plan.md`. The operator ticks actions off over subsequent sessions; progress
rolls up through the scanner like any plan.

**Announce at start:** "Using the business launch skill to plan <project>'s go-to-market."

## Determinism boundary

Read business state via the scanner:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/business-scan.py
```

Write `business/gtm-plan.md` conforming to
`${CLAUDE_PLUGIN_ROOT}/references/gtm-plan-format.md` (a flat checkbox checklist — the
scanner counts `- [ ]`/`- [x]` bullets). When re-planning an existing gtm-plan.md, `Read`
it first and preserve the operator's already-ticked boxes.

## Precondition — a decided model

From the scanner JSON, this project must have `monetization.model` set (not null) — i.e.
`/business:revenue-model` has run. If not:

- `assessed: false` (never assessed — no `business/` dir, so no `verdict`/`monetization`
  fields at all) → **stop**: run `/business:assess`, then `/business:revenue-model`, first.
- `model: null` but verdict is `monetize`/`free-for-reputation` → **stop**: run
  `/business:revenue-model` first.
- verdict `park`/`internal-only` → **stop**: there is no launch to plan.
- `errors` non-empty → **stop** and report; fix the assessment first.

## Ship-readiness guard (MATURITY.md)

`Read` the project's `MATURITY.md` (in the same vault home). Count the open items
(`- [ ]`) per axis. A go-to-market plan for something far from ship-ready is premature:

- If there are open items on load-bearing axes (Documentation, Security, Packaging), **warn
  with the specific gaps** — e.g. "Security: sec-audit not clean; Packaging: no release
  target" — and ask the operator to confirm before proceeding. Planning a launch is fine;
  *executing* it before these close is the risk you're flagging.
- If MATURITY.md is absent, say so and suggest `/planning:project-maturity init` — proceed
  only on confirmation.
- A near-ship-ready project (few or no open items) proceeds without friction.

Never *block* — the operator may legitimately plan ahead. Warn, get acknowledgement,
continue.

## Build the plan

Write `gtm-plan.md` as dated launch actions grouped under plain `##` phase headers, each
action a `- [ ]` checkbox (see gtm-plan-format.md). Ground the actions in the project's
model and channels from `BUSINESS.md`:

- **Pre-launch** — store/listing assets, announcement copy, docs, whatever the channels
  require (e.g. AMO listing, F-Droid fastlane metadata, a Sponsors page).
- **Launch** — tag/sign/release, submit to each channel, publish the announcement. Put
  target dates inline (`target: 2026-07-20`).
- **Post-launch** — first `/business:track` pass, feedback triage, iterate.

Keep actions concrete and checkable ("Submit to F-Droid", not "do marketing"). Tie the
channel actions to the `channels` list in `BUSINESS.md` — don't plan a Play launch for a
project whose channel is F-Droid.

## Verify

Run `business-scan.py` and confirm the project's `gtm` shows `{done, total, pct}` with the
expected `total` (your action count) — this proves the file parses under the shared
checkbox contract. Zero ticked at creation is correct (`done: 0`).

## Hand off

Suggest `/business:track` for the first metrics pass once launch actions start landing,
and `/business:biz-portfolio` to see this project in the roll-up.
