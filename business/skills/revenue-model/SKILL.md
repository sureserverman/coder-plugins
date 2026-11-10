---
name: revenue-model
description: >
  Decide how an assess-passed portfolio project earns or gains — monetization model, pricing hypothesis, channels, and dated targets — recorded in business/BUSINESS.md. Triggers on "how should this make money", "pick a monetization model", "pricing for this project", "what's the revenue model".
---

# revenue-model — monetization decision

Sets the `monetization` and `targets` sections of `business/BUSINESS.md` in place.
Present model options one decision per message.

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
- `park` or `internal-only` → **stop**: point the user at `/business:assess` to
  re-assess if their intent changed.
- `assessed: false` (no `business/` dir at all) → **stop**: run `/business:assess` first.

If the project's `errors` array is non-empty, stop and report — the file is malformed.

For `free-for-reputation`, pick channels and a reputational target; `pricing` may stay null.

## Fields

- `monetization.model`, `monetization.pricing` (a one-line hypothesis, e.g. `"$3 one-time"`),
  `monetization.channels` (a **list**, e.g. `[f-droid, github-releases]`). Honor channel
  rules found during assess (F-Droid forbids paid apps).
- `targets`: at least one numeric, dated target. Each target is `{metric, target, by}` —
  `metric` a non-empty string, `target` numeric, `by` `YYYY-MM-DD` — e.g. `stars 500 by
  2026-12-31`. Prefer metrics `track` can measure (GitHub stars/downloads are
  auto-collected; revenue/installs are manual).

## Write and verify

Update `monetization` and `targets`, bump `last_reviewed: <today>`, and add the
reasoning to the body. Then run `business-scan.py` and confirm the JSON carries the new
`monetization.model` and `targets`, with **zero `errors`**.

Hand off to `/business:launch` (near ship-ready) or `/business:track`.

## Business groups

This skill operates on a **business group** as readily as on a single project. When the
target is a group slug (or the named project is a member of one — the scanner's `groups`
list and each entry's `members` name them), resolve the working directory to
`<vault_dir>/Portfolio/business-groups/<slug>/` instead of `<home>/business/`, and write
`project: <group-slug>` in any artifact frontmatter. Format and membership rules:
`../../references/group-format.md`.

A group is **one business case**: one audience, one price, one set of targets. Never
produce a per-member verdict, model, or plan.
