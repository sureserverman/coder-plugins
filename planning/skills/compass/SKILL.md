---
name: compass
description: >
  Use to decide and organize work across every project in the portfolio — what's in flight, what to work on next, and a periodic review sweep. Triggers on "what should I work on", "what should I work on next", "what's in flight", "what am I in the middle of", "portfolio review", "weekly review", "what's next across my projects", "which project needs attention", "what's going stale". Subcommands: `now` (in-flight board), `next` (ranked recommendations), `review` (cadence sweep). Report-only — recommends work, never launches it and never writes portfolio artifacts.
---

# Compass — portfolio work orchestrator

Answers three questions across every registry project, grounded in evidence
reconstructed fresh each run — no maintained state, nothing to drift:

- **`compass now`** — what is in flight?
- **`compass next`** — what should I work on next?
- **`compass review`** — what needs attention before it rots?

**Announce at start:** "Using the compass skill for a portfolio work sweep."

## Determinism boundary

All evidence comes from ONE run of the deterministic scanner:

```
python3 ${CLAUDE_PLUGIN_ROOT}/skills/compass/scripts/compass-scan.py
```

It emits one JSON document: per project, in-flight plan state (stage, next
unchecked task — parsed with the same authoritative regexes portfolio-unify
uses), backlog open/parked counts, maturity axis summaries, integration-graph
edges (`dependents` / `depends_on`), and git recency (`age_days`, UTC).
This skill's job is **judgment only**: ranking, narration, and the agenda.
Never re-derive facts the JSON already carries; never present a fact the JSON
doesn't back.

## Hard rules

- **Report + recommend only.** Never start the recommended work, never invoke
  another skill to execute it, never write under the vault, `~/.claude/`, or
  any repo. The scanner is read-only; so is the skill. If a roll-up looks
  stale, *suggest* `/planning:portfolio rebuild` — do not run it.
- **Every recommendation cites its evidence** — the plan file, stage, task,
  age, maturity gap, or edge it rests on, e.g. "stage 2 gate open, last
  commit 12 days ago" or "2 maturity boxes from ship-ready". No vibes.
- **Respect parking.** A backlog entry with a `- **Parked:** <date or
  reason>` line (see the backlog skill's file format) is excluded from `next`
  recommendations; mention parked items only in `review` (with their reason),
  or when their parked-until date has passed.
- **Degrade loudly.** Plans with `"note": "stage unknown …"` are still active
  work — list them as such. Every scan `errors` entry and every
  `couldnt_assess` project appears in a **"Couldn't assess"** footer on every
  report. Silence is never coverage.

## Error handling

- Scanner exits with "portfolio not configured" → report that verbatim and
  point to `/planning:portfolio` first-run setup. Do not half-answer from
  memory.
- Individual project errors (non-git repo, unreadable plan) are already in the
  JSON — footer them, never drop them.

## `now` — the in-flight board

List projects that have at least one plan with `"active": true`, ordered by
git recency (freshest first). Per project: the plan file, current stage,
next task (verbatim from `next_task`), done/total counts, and `age_days`.
Plans with a degradation `note` go in the same board with the note shown.
End with the Couldn't-assess footer.

## `next` — ranked recommendations

Rank candidate work items with these signals, in this order:

1. **In-flight momentum** — an open stage on an active plan outranks any new
   start. Freshest active plans first: finish what's started.
2. **Almost-shippable** — projects whose maturity summary shows a small open
   gap (≤2 open boxes) get boosted: finishing beats starting.
3. **Unblocking power** — projects with `dependents` edges get boosted; name
   who gets unblocked and why (the edge's `why` text).
4. **Staleness** — a tie-break booster, not a top-rank driver: among
   otherwise-equal candidates, surface the one rotting longest.

Output the top 5–7 as a ranked list; each entry = one sentence of
recommendation + one line of cited evidence. Parked items are excluded
(Hard rules). Close with one sentence on what was deliberately NOT
recommended and why (e.g. "12 stale legacy plans with unknown stages —
see review").

## `review` — the cadence sweep

Surface drift, one section each (explicit-negative when a section is empty):

- **Abandoned mid-stage** — active plans whose project's last commit is older
  than 30 days.
- **Stale backlogs** — projects with open backlog items and no commit in 60+
  days.
- **Ship-ready but unshipped** — maturity open-count of 0 (or only claims
  missing) with no release evidence in recent plans.
- **Parked items due** — `Parked:` dates in the past, with reasons.
- **Stale roll-ups** — if `global-backlog.md` / `global-maturity.md`
  "Last rebuilt" dates predate the newest plan activity, suggest
  `/planning:portfolio rebuild` (never run it).
- **Couldn't assess** — the footer, always.

End with a **focused agenda**: 3 items max, drawn from the sections above,
each with its evidence line.

## Integration

- **portfolio** — maintains the artifacts compass reads (registry, roll-ups,
  integration graph); compass never writes them. Rebuild suggestions route
  there.
- **backlog** — owns the `Parked:` annotation compass respects.
- **executing-plans / planning-projects** — where the user goes AFTER picking
  a recommendation; compass itself never invokes them.
- **project-maturity** — produces the MATURITY.md files behind the
  almost-shippable signal.

## Remember

- One scanner run per invocation; judgment on top; no writes anywhere.
- Cite evidence on every recommendation; footer every gap in coverage.
- Momentum > almost-shippable > unblocking > staleness.
- Parked means parked until the date says otherwise.
