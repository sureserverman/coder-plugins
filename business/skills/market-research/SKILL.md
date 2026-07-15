---
name: market-research
description: >
  Produce a deep, cited market-research report for ONE portfolio project — competitors, pricing, TAM/SAM/SOM sizing, trends, channel norms — persisted to business/market-research.md. Triggers on "market research for this project", "size the market", "TAM SAM SOM", "is there a payable audience".
---

# market-research — tiered, persistent market evidence

Run a market-research pass for ONE project at an **operator-selected depth tier**
(`brief` | `standard` | `deep`) and persist it to `business/market-research.md`. The
artifact is reused by `/business:assess --research` (when fresh, ≤ 90 days, and deep enough
— see below) and folded into `/business:business-plan`, so one research pass serves the
whole pipeline. This skill gathers **evidence, never a verdict** — the monetize / free /
park decision stays with `assess` and the operator.

**Announce at start:** "Using the business market-research skill to research <project>'s market."

## Choose the depth tier (ask first, before researching)

Before dispatching, ask the operator **how deep** the research should go — this is the first
question, and the tier scales both effort and what the artifact contains. Present it as a
single multiple-choice question with a one-line cost/benefit each:

- **`brief`** — competitors, pricing, channels, demand. Fastest; "who else is here and what
  do they charge". No market sizing, no competitor-marketing teardown, no personas.
- **`standard`** — everything in brief **plus** TAM/SAM/SOM sizing, trends, positioning gaps,
  a channel-level competitor-marketing summary, and one customer persona. The recommended
  default for a real go/grow decision.
- **`deep`** — everything in standard **plus** a per-competitor marketing teardown (campaigns,
  tooling, messaging) and 2–3 personas. Slowest; most WebSearch/WebFetch; for a serious
  launch or fundraising narrative.

Record the chosen tier — it becomes the agent's dispatch `depth` and the artifact's
`depth:` frontmatter. If the operator has no preference, default to `standard` and say so.

## Determinism boundary

Read all cross-project state — and resolve the vault home — from the scanner, never by
hand-parsing another project's artifacts or the portfolio config:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/business-scan.py
```

The scanner JSON envelope carries `vault_dir`; each project entry carries `area` and
`name`. Resolve `home = <vault_dir>/Portfolio/<area>/<name>/` and write to
`<home>/business/market-research.md`; `mkdir -p` the `business/` dir. (This is the shared
resolver — do not re-read `portfolio-config.yaml` inline.) You WRITE the artifact
conforming to `${CLAUDE_PLUGIN_ROOT}/references/market-research-format.md` (schema 2); the
scanner is the sole *reader* of its frontmatter.

If the project isn't in the scanner output, it isn't registered — auto-register it the way
`assess` does (append to `~/.claude/projects-registry.yaml` from its `~/dev/<area>/<name>`
path) and re-run the scanner before proceeding.

## Preconditions — confirm the scope, don't assume it

Market research is **standalone** — it does not require a verdict, so it runs before or
after `assess`. Ground and then **confirm** the scope before dispatching; a research pass
built on a wrong assumption wastes the whole WebSearch budget. Ask one question at a time,
multiple-choice where the answer space is finite, and skip a question only when the answer
is already recorded (in `BUSINESS.md` or the repo) and unambiguous:

- **What the tool actually is** — `Read` the repo README/manifest at the project's `path`
  (from the scanner entry), so the competitor set matches what the tool does, not what its
  name suggests. State your one-line read of what it is and let the operator correct it.
- **Audience** — if a `BUSINESS.md` exists, state its `audience` and ask the operator to
  confirm or refine it; otherwise state the audience you infer from the repo and **ask for
  confirmation before dispatching** — do not silently research against an assumed audience.
  Any finding that ends up resting on an unconfirmed audience is marked as such.
- **Geography / market** — the competitor set and pricing norms differ by market (global vs
  a specific country/language, consumer vs enterprise). Confirm the intended market rather
  than defaulting to "global" silently.
- **Known competitors / seed list** — ask whether the operator already has competitors or
  comparable tools in mind. A seed list sharpens the search and surfaces competitors a
  name-based search would miss; treat it as a starting point to expand and cite, not a
  closed set.

Stop asking once the scope is pinned — you need enough to research well, not an interview.

## Re-run — refresh, don't clobber

If `market-research.md` already exists (scanner shows `research.exists: true`), this is a
**refresh**. `Read` the current file first, tell the operator its `researched` date, age,
**and its current `depth`** (from the scanner's `research.depth`), then **confirm before
overwriting**. Two common refresh intents, so name them:

- **Same tier, fresher evidence** — re-run at the existing depth to update stale findings.
- **Upgrade the tier** — if the existing artifact is `brief` (or legacy `triage`) and the
  operator now wants sizing, competitor-marketing, or personas, offer to re-run at
  `standard`/`deep`. Say plainly what the deeper pass adds.

Don't silently replace a recent artifact, and don't silently *downgrade* one — if the
operator picks a shallower tier than what exists, confirm they accept losing the deeper
sections.

## Dispatch the researcher (at the chosen tier)

Dispatch the **market-researcher** agent
(`${CLAUDE_PLUGIN_ROOT}/agents/market-researcher.md`) at **`depth: <the chosen tier>`**
(`brief` | `standard` | `deep`), briefed with: the project (one or two lines of what it
does), the **confirmed** audience, the **confirmed market/geography**, the repo path, any
**operator-provided competitor seed list**, and the candidate channels (from `BUSINESS.md`
`channels` if present, else inferred from the platform). At `standard`/`deep`, the brief
explicitly asks for the **Competitor marketing** and **Customer personas** groups (the agent
gates these to those tiers). It returns cited findings for every group the tier lists —
never a verdict, never a written file. Every claim is cited or framed as an evidenced
absence; discard any uncited figure.

The agent's tier scopes what comes back: `brief` → Competitors, Pricing signal, Channels,
Demand signal; `standard` adds Market sizing, Trends, Positioning gaps, a channel-level
Competitor marketing summary, and one persona; `deep` adds the per-competitor marketing
teardown and 2–3 personas. (See the agent's Depth section — this skill and the agent share
one tier definition.)

## If research is unavailable — write nothing

If WebSearch is denied or the environment is offline, the agent cannot gather cited
evidence. **Do not write a half-cited or uncited `market-research.md`** — an
authoritative-looking file with no sources is worse than none. Say so plainly ("market
research needs WebSearch, which is unavailable here — no artifact written"), leave any
existing artifact untouched, and stop. `assess`/`business-plan` will proceed on
`local-only` evidence and record that.

## Write the artifact

Write `<home>/business/market-research.md` per `references/market-research-format.md`:
frontmatter `schema: 2`, `project: <name>`, `researched: <today>`, `depth: <the chosen
tier>` (`brief` | `standard` | `deep`), `confidence: <high|medium|low>` (your honest overall
read of the evidence — primary sources → high, mostly secondary → medium, substantially
inferred → low). The body carries the agent's cited findings under the format's section
headings, populated to the chosen tier: a `brief` artifact omits the Market sizing,
Competitor marketing, and Customer personas sections; `standard` includes them at summary
depth; `deep` includes the full per-competitor teardown and 2–3 personas. No uncited
numbers; "could not size — searched …" is a first-class finding.

## Verify

Run `business-scan.py` and confirm the project shows `research.exists: true`, the right
`research.depth` (the tier you chose — `brief`/`standard`/`deep`), a computed
`research.age_days` (0 today), and **zero `errors`** for the project (a non-empty `errors`
array means the file doesn't conform — e.g. a schema-2 file must not carry a legacy
`depth: full`; fix it).

## Hand off

- If the project has no verdict yet → suggest `/business:assess --research` (it will reuse
  this fresh artifact instead of re-researching).
- If it's assess-passed → suggest `/business:business-plan` to fold this research into a
  full business plan, and `/business:biz-portfolio` to see the research age in the roll-up.
