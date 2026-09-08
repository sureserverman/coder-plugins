---
name: market-research
description: >
  Run a cited competitive analysis for ONE portfolio project — who solves the same problem, coverage, pricing, a competitor table with quadrant sweep, positioning — persisted to business/market-research.md. Triggers on "market research for this project", "competitive analysis", "competitor table".
---

# market-research — the competitive-analysis pass, tiered and persistent

Run the competitive-analysis method (`${CLAUDE_PLUGIN_ROOT}/references/competitive-analysis-method.md`
— read it before starting) for ONE project at an
**operator-selected depth tier** (`brief` | `standard` | `deep`) and persist the result:
`business/market-research.md` (schema 3), and at `standard`+ the competitor table
`business/competitor-table.yaml` plus the quadrant/trajectory SVGs. The artifacts are
reused by `/business:assess --research` (when fresh, ≤ 90 days) and folded into
`/business:business-plan`. This skill gathers **evidence, never a verdict** — the
monetize / free / park decision stays with `assess` and the operator, and the analysis
never answers what to build next (competitive-analysis-method.md § 18 — Limits).

**Announce at start:** "Using the business market-research skill to research <project>'s market."

## Choose the depth tier (ask first, before researching)

Present one multiple-choice question with a one-line cost/benefit each:

- **`brief`** — the job statement, the three-pass competitor list with classes and
  coverage, pricing, channels, demand. Fastest; "who else solves this and what do they
  charge". No table, no quadrants, no profiles, no sizing.
- **`standard`** — everything in brief **plus** the competitor table, the quadrant sweep
  and a chosen map, group-level six-block profiles, a channel-level marketing summary,
  sizing, trends, positioning gaps, the durability test, a five-component positioning, one
  persona. The recommended default for a real go/grow decision.
- **`deep`** — everything in standard **plus** trajectories, per-competitor profiles and
  marketing teardowns, partner candidates, battlecards, monitoring indicators, 2–3
  personas. Slowest; most WebSearch/WebFetch; for a launch or fundraising narrative.

Record the chosen tier — it becomes the agent's dispatch `depth` and the artifact's
`depth:`. If the operator has no preference, default to `standard` and say so.

## Determinism boundary

Read all cross-project state — and resolve the vault home — from the scanner, never by
hand-parsing another project's artifacts or the portfolio config:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/business-scan.py
```

The envelope carries `vault_dir`; each project entry carries `area` and `name`. Resolve
`home = <vault_dir>/Portfolio/<area>/<name>/` and write under `<home>/business/`
(`mkdir -p` it). You WRITE `market-research.md` per
`${CLAUDE_PLUGIN_ROOT}/references/market-research-format.md` and `competitor-table.yaml`
per `${CLAUDE_PLUGIN_ROOT}/references/competitor-table-format.md`; the scanner is the sole
reader of the former's frontmatter, and `competitor-table.py` the sole parser of the
latter. The table's arithmetic — normalization, quadrants, the axis sweep, trajectories —
is the script's, never yours:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/competitor-table.py {validate|normalize|quadrant|sweep|trajectory} …
```

If the project isn't in the scanner output, it isn't registered — auto-register it the way
`assess` does (append to `~/.claude/projects-registry.yaml` from its `~/dev/<area>/<name>`
path) and re-run the scanner before proceeding.

## Preconditions — confirm the scope, don't assume it

Market research is **standalone** — it runs before or after `assess`. Ground and then
**confirm** the scope before dispatching; a pass built on a wrong premise wastes the whole
WebSearch budget. Ask one question at a time, multiple-choice where the answer space is
finite, and skip a question only when the answer is already recorded (in `BUSINESS.md` or
the repo) and unambiguous:

- **What the tool actually is** — `Read` the repo README/manifest at the project's `path`
  so the competitor set matches what the tool does, not what its name suggests. State
  your one-line read and let the operator correct it.
- **The customer job** — propose the statement *"when [situation], I want to
  [action], so that [outcome]"* from the repo and the audience, and **get it confirmed
  or corrected before anything else**. A wrong statement invalidates the list, the
  table, and the positioning built on it. Then ask what the customer does today without
  this product (the alternatives pass seed): a spreadsheet, a hired person, a
  general-purpose tool, nothing.
- **Audience** — state `BUSINESS.md`'s `audience` if one exists, else the audience you
  infer, and ask for confirmation. Any finding resting on an unconfirmed audience is
  marked as such.
- **Geography / market** — global vs a specific country/language, consumer vs
  enterprise. Confirm rather than defaulting to "global" silently.
- **Known competitors / seed list** — a starting point to expand and cite, never a
  closed set.
- **Plot the project itself?** (`standard`+) — whether the project is a row in the table
  (`self`), so the sweep can find the point where it differs from everyone.

Stop asking once the scope is pinned.

## Re-run — refresh, don't clobber

If `market-research.md` exists (scanner shows `research.exists: true`), this is a
**refresh**. `Read` the current file, tell the operator its `researched` date, age, `depth`,
`competitors` and `coverage`, then **confirm before overwriting**. Name the intents:

- **Same tier, fresher evidence** — re-run at the existing depth. A `deep` refresh is also
  the moment the monitoring indicators get checked: say which trajectories the new
  evidence confirmed or refuted.
- **Finish an open search** — `coverage: open` means the list was not exhausted; a
  refresh can concentrate on the passes that were thin.
- **Upgrade the tier** — say plainly what the deeper pass adds.

Don't silently replace a recent artifact, and don't silently *downgrade* one — if the
operator picks a shallower tier, confirm they accept losing the deeper sections. An
existing `competitor-table.yaml` is a **starting table**: pass it to the agent so prior
years' states become `history` rather than being lost.

## Dispatch the researcher (at the chosen tier)

Dispatch the **market-researcher** agent
(`${CLAUDE_PLUGIN_ROOT}/agents/market-researcher.md`) at **`depth: <the chosen tier>`**,
briefed with: the project (one or two lines), the **confirmed job statement**, the
**confirmed audience**, the **confirmed market/geography**, the repo path, the seed list
and alternatives, the candidate channels (from `BUSINESS.md` `channels` if present, else
inferred from the platform), whether to plot `self`, and any existing table. It returns
cited findings for every section the tier lists, a Coverage block (raw count, row count,
exhausted/open), and — at `standard`+ — a fenced `competitor-table.yaml`. Never a
verdict, never a written file. Every claim is cited or framed as an evidenced absence;
discard any uncited figure.

## If research is unavailable — write nothing

If WebSearch is denied or the environment is offline, the agent cannot gather cited
evidence. **Do not write a half-cited or uncited artifact** — an authoritative-looking
file with no sources is worse than none. Say so plainly ("market research needs
WebSearch, which is unavailable here — no artifact written"), leave any existing artifacts
untouched, and stop. `assess`/`business-plan` proceed on `local-only` evidence.

## Build the table and read it (`standard`+)

1. Write the agent's YAML block to `<home>/business/competitor-table.yaml` and run
   `competitor-table.py validate` on it. Fix any reported errors — a wrong type, an
   unknown column, a log axis with a zero — and re-validate until `ok: true`. Its `rows`
   figure is the artifact's `competitors:`.
2. Run `competitor-table.py sweep --size <revenue-or-headcount column>` (with `self` set,
   the ranking leads with the pairs where the project stands furthest from everyone).
   **Show the operator the top pairs and the per-group cohesion report** and let them
   choose the map — the sweep proposes, the operator decides. A group that
   `scatters` is dissolved: split its rows, re-validate, re-sweep.
3. Render the chosen pair with `competitor-table.py quadrant --x … --y … --size … --svg
   <home>/business/quadrant-<x>-<y>.svg`. Report the empty quadrants, the most crowded
   one, and `self`'s nearest neighbour. If the empty zone looks unattractive, run the
   unattractive-quadrant test (competitive-analysis-method.md § 8 — Quadrants) with the operator (is there a segment for which that pole is positive or
   neutral?) and, if so, set `invert: true` on that column and re-render.
4. At `deep`, run `competitor-table.py trajectory --x … --y … --size … --svg
   <home>/business/trajectory-<x>-<y>.svg` on the same pair. Report each vector's length
   with the size caveat (competitive-analysis-method.md § 9 — Trajectories) and the `clearing_quadrants` — the zone projected to be
   empty in two years is the strategy target, and it is a hypothesis.

## Write the artifact

Write `<home>/business/market-research.md` per the format: frontmatter `schema: 3`,
`project: <name>`, `researched: <today>`, `depth: <tier>`, `confidence: <high|medium|low>`
(primary sources → high, mostly secondary → medium, substantially inferred → low),
`competitors: <rows>` (the table's row count; at `brief`, the number of competitor
lines), `coverage: exhausted|open` (**`exhausted` only when the agent reported the
discovery rate had collapsed across all three passes** — anything else is `open`). The
body carries the agent's cited findings under the format's section headings in its
order, populated to the tier and **omitting** sections the tier doesn't populate. The
Quadrants and Trajectories sections carry the script's numbers (empty zone, nearest
neighbour, vectors) and link the SVGs. The Positioning section ends in the one sentence
`business-plan` will quote. No uncited numbers; "could not size — searched …" is a
first-class finding.

## Verify

Run `business-scan.py` and confirm the project shows `research.exists: true`, the right
`research.depth`, `research.competitors` equal to the table's row count, the intended
`research.coverage`, a computed `research.age_days` (0 today), and **zero `errors`** for
the project. At `standard`+, `competitor-table.py validate` on the written table is
`ok: true` and the SVGs the body links exist.

## Hand off

- No verdict yet → suggest `/business:assess --research` (reuses this fresh artifact).
- Assess-passed → suggest `/business:business-plan` (its Competitive landscape, SWOT &
  positioning, and Marketing & sales sections draw on the quadrant, the durability test,
  and the positioning here), and `/business:biz-portfolio` for the roll-up, where an
  `OPEN` coverage marker or a thin row count stays visible next to the research age.
- `coverage: open` → say what a follow-up pass should search, so the list gets finished.

## Business groups

This skill operates on a **business group** as readily as on a single project. When the
target is a group slug (or the named project is a member of one — the scanner's `groups`
list and each entry's `members` name them), resolve the working directory to
`<vault_dir>/Portfolio/business-groups/<slug>/` instead of `<home>/business/`, and write
`project: <group-slug>` in any artifact frontmatter. Format and membership rules:
`../../references/group-format.md`.

A group is **one business case**: one audience, one price, one set of targets. Never
produce a per-member verdict, model, or plan — that is the split the group exists to
prevent.
