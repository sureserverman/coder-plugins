# business

Per-project business-planning pipeline for the `~/dev` portfolio. Turns a
shippable project into a commercial decision and keeps it tracked, storing
artifacts in the vault portfolio homes alongside `MATURITY.md` so the planning
plugin's `portfolio` and `compass` skills can read business state.

## Install

```text
/plugin install business@coder-plugins
```

**Prerequisites.** A configured vault (`vault_dir` in `~/.claude/portfolio-config.yaml`) — every
artifact is vault-canonical, and the scripts fail loudly rather than writing into your repo. The
research-backed skills additionally need **WebSearch**; without it they write nothing rather than
emit an uncited guess. `assess` expects the project to exist in `~/.claude/projects-registry.yaml`
(the `planning` plugin's `portfolio scan` seeds it).

## Skills

| Skill | Does |
|-------|------|
| `/business:assess` | Viability triage → `business/BUSINESS.md` verdict (monetize / free-for-reputation / internal-only / park). Opt-in `--research` (reuses a fresh `market-research.md`). |
| `/business:revenue-model` | Monetization model, pricing, channels, numeric dated targets for an assess-passed project. |
| `/business:market-research` | Tiered (`brief`/`standard`/`deep`), cited market pass — competitors, pricing, TAM/SAM/SOM, trends, positioning, plus competitor-marketing teardown and customer personas at `standard`/`deep` → `business/market-research.md`. Asks the tier + confirms scope up front. Writes nothing if WebSearch is unavailable. |
| `/business:business-plan` | Compose verdict + model + research + gtm + metrics into a tiered twelve-section `business/plan.md` (adds Customer personas and SWOT & positioning). Asks the depth tier and confirms gaps up front. |
| `/business:launch` | Go-to-market plan → `business/gtm-plan.md`, guarded by `MATURITY.md` state. |
| `/business:track` | Record actuals (incl. optional marketing funnel) → `business/metrics.md`, diff vs targets, bump Last reviewed. |
| `/business:biz-portfolio` | Sweep every project, rebuild `global-business.md` (flags stale research/plans). |

All seven are invocable as `/business:<skill>` and also fire on natural language ("is this worth monetizing", "size the market", "how are we doing vs targets"). They form a pipeline — `assess` gates the rest, since a project that shouldn't be monetized doesn't need a revenue model — but each runs standalone once its predecessor's verdict exists.

## Agent

### `market-researcher`

Gathers **cited** market evidence for one project: competitors and their pricing, market signals, distribution-channel norms. Dispatched by `market-research` (and by `assess --research`) — one agent per research axis, in parallel — rather than invoked directly.

**Model:** `sonnet`. **Tools:** `Read`, `Grep`, `Glob`, `WebFetch`, `WebSearch`.

**Prerequisite that actually bites:** it needs **WebSearch**. Without it there is no evidence to gather, and the skills that depend on it **write nothing rather than emitting an uncited guess** — a market-research file that reads like research but was produced from training data is worse than no file, because the next reader trusts it.

## Artifacts (in the vault)

Per project, under `<vault_dir>/Portfolio/<area>/<project>/business/`:

- `BUSINESS.md` — canonical, schema-versioned. Sole machine-readable index.
- `market-research.md` — tiered, cited market evidence (schema 2; `research` block with `depth`).
- `plan.md` — tiered twelve-section business plan (schema 2; `plan` block with `depth`).
- `gtm-plan.md` — dated go-to-market checklist (portfolio-unify-parseable).
- `metrics.md` — append-only actuals log.

Roll-up: `<vault_dir>/Portfolio/global-business.md`.

### Business groups

Several repos that are really **one product** — a server and its admin client, a CLI and
its GUI — are grouped into a single business case. The manifest and the group's artifacts
live together:

```
<vault_dir>/Portfolio/business-groups/<slug>/group.md      # schema 1: group, members[>=2], created
<vault_dir>/Portfolio/business-groups/<slug>/BUSINESS.md   # project: <slug>
… plus plan.md / market-research.md / gtm-plan.md / metrics.md
```

Membership lives in the vault, **not** in `~/.claude/projects-registry.yaml`: eight
independent consumers parse that registry with a fixed field set, so a grouping key there
would couple all of them to one plugin's feature. `assess` creates a group (never
silently — grouping decides which repos stop having a business case of their own); every
other skill then treats it as one project. `track` runs each collector once per member,
sums into the flat `<source>.<metric>` keys that targets match, and records per-member
`@<area>/<name>` breakdown lines for attribution. `launch` gates on the **weakest
member's** `MATURITY.md` — a suite ships when all of it ships. `global-business.md`
renders the group as one row naming every member.

Full rules: `references/group-format.md`.

## Determinism boundary

`scripts/business-scan.py` is the **only** parser of the business artifacts. It
emits one JSON document; every skill and every planning-plugin integration
consumes that JSON, never the markdown. The scanner reuses `portfolio-unify`'s
plan-parser regexes for `gtm-plan.md` progress — one contract, one implementation.

## Design & plan

- Design: `<vault>/Portfolio/ai-tools/coder-plugins/plans/2026-07-11-business-plugin-design.md`
- Plan: `<vault>/Portfolio/ai-tools/coder-plugins/plans/2026-07-11-business-plugin-plan.md`

## Worked example

```text
/plugin install business@coder-plugins

/business:assess
```

Triages viability and writes a verdict to `business/BUSINESS.md` — one of *monetize*,
*free-for-reputation*, *internal-only*, or *park*. A *park* verdict is a real outcome, not a
failure; the rest of the pipeline is gated on it, so nothing further runs on a project that
shouldn't be commercialized.

```text
/business:market-research
```

Asks for a depth tier (`brief` / `standard` / `deep`) and confirms scope before doing anything.
Fans out `market-researcher` agents and writes `business/market-research.md` — **cited**. If
WebSearch is unavailable it writes nothing at all rather than producing a research-shaped file
from training data.

```text
/business:revenue-model
/business:business-plan
```

The model, pricing and dated targets land in `BUSINESS.md`; the plan composes verdict + model +
research + GTM + metrics into a twelve-section `business/plan.md`.

```text
/business:track
```

Records actuals and diffs them against the targets you set — the step that makes the earlier
numbers accountable rather than aspirational.

## Related plugins

- **`planning`** — the sibling pipeline for the *engineering* side. `project-maturity`'s
  ship-readiness verdict gates `launch`; `compass` and `portfolio` read the business state these
  skills write; `decisions` is where a commercial constraint that binds the architecture belongs.
- **`release-promo`** — drafts the launch announcements the `gtm-plan.md` checklist calls for.
- **`git-github`** — `repo-health` and `license-audit` surface the compliance and maintenance
  facts an honest assessment depends on.
