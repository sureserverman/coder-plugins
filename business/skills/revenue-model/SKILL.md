---
name: revenue-model
description: >
  Decide how an assess-passed portfolio project earns or gains — monetization model, pricing hypothesis, channels, and dated targets — recorded in business/BUSINESS.md. Triggers on "how should this make money", "pick a monetization model", "pricing for this project", "what's the revenue model".
---

# revenue-model — monetization decision

Turn an assessed verdict into a concrete money/reach model: how it earns or gains, at
what price, through which channels, against what numeric dated targets. Updates the
`monetization` and `targets` sections of `business/BUSINESS.md` in place.

**Announce at start:** "Using the business revenue-model skill to set <project>'s monetization model."

## Determinism boundary

Read business state (verdict, current monetization, targets) via the scanner:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/business-scan.py
```

To update `BUSINESS.md`, `Read` the actual file and make **targeted in-place edits**
conforming to `${CLAUDE_PLUGIN_ROOT}/references/business-md-format.md` — preserve the
`project:` field and the markdown body (the scanner JSON omits both, so never rewrite the
file from JSON alone).

## Precondition — an assess verdict

From the scanner JSON, read this project's `verdict`:

- `monetize` or `free-for-reputation` → proceed.
- `park` or `internal-only` → **stop**: there is no model to set for a parked or
  internal-only project. Point the user at `/business:assess` to re-assess if their
  intent changed.
- `assessed: false` (no `business/` dir at all) → **stop**: run `/business:assess` first.

If the project's `errors` array is non-empty, stop and report — the file is malformed;
fix the assessment before layering a model on it.

## Phase 1 — Present model options (one decision at a time)

Ground the options in the verdict and any researched evidence already in `BUSINESS.md`.
Present 2–4 concrete models with tradeoffs, one decision per message. Typical space:

- **paid** — one-time or subscription. Fits a clear payable audience and a channel that
  allows charging (AMO, Play, direct). Tradeoff: friction, support load.
- **freemium** — free tier + paid upgrade. Fits when adoption matters and a subset will
  pay for depth. Tradeoff: you must build and maintain a paywall boundary.
- **donations / sponsorship** — GitHub Sponsors, Ko-fi, OpenCollective. Fits
  `free-for-reputation` and channels that forbid paid apps (e.g. F-Droid). Tradeoff:
  unreliable, reputation-dependent.
- **dual-license / open-core** — free OSS core, paid license or premium features. Fits
  developer tools with a commercial-use angle. Tradeoff: licensing complexity.
- **oss-services** — free tool, paid services/support/hosting. Fits infrastructure.

For `free-for-reputation`, "model" is about reach and funnel, not price — pick channels
and a reputational target (stars, mentions, downstream leads), pricing may stay null.

## Phase 2 — Pricing hypothesis

For a paid/freemium model, set a concrete pricing *hypothesis* (it's a hypothesis to be
tested by `track`, not a commitment). Ground it in the researched pricing signal if
present ("comparable tools cluster at $2–5 one-time"). One line, e.g. `"$3 one-time"` or
`"$5/mo pro tier"`.

## Phase 3 — Channels

Pick the distribution channel(s) as a list, consistent with the model and the project's
platform (e.g. `[f-droid, github-releases]`, `[amo]`, `[play]`, `[pypi]`). Honor channel
rules surfaced during assess research (F-Droid forbids paid apps → donations, not paid).

## Phase 4 — Numeric dated targets

Set at least one **numeric, dated** target so `track` can diff actuals against it. Each
target is `{metric, target, by}` — e.g. `installs 1000 by 2026-12-31`, `mrr_usd 200 by
2026-12-31`, `stars 500 by 2026-12-31`. Prefer targets whose metric `track` can actually
measure (GitHub stars/downloads are auto-collected; revenue/installs are manual).

## Phase 5 — Write and verify

Update the `monetization` block (`model`, `pricing`, `channels`) and `targets` in
`BUSINESS.md`, bump `last_reviewed: <today>`, and add the reasoning to the body. Then run
`business-scan.py` and confirm the JSON carries the new `monetization.model` and
`targets`, with **zero `errors`**.

## Hand off

Suggest `/business:launch` when the project is near ship-ready (it checks MATURITY.md),
or `/business:track` to start recording actuals against the targets you just set.
