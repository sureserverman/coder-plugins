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
| `/business:market-research` | Tiered (`brief`/`standard`/`deep`), cited competitive analysis following a working method — who solves the same problem (three-pass list, coverage rate), pricing, channels, demand; at `standard`+ a competitor table (`business/competitor-table.yaml`) with a quadrant sweep, six-block profiles, sizing, a durability test and a five-component positioning; at `deep` trajectories, battlecards, partner candidates, monitoring indicators → `business/market-research.md`. Confirms the customer-job statement and scope up front. Writes nothing if WebSearch is unavailable. |
| `/business:business-plan` | Compose verdict + model + research + gtm + metrics into a tiered twelve-section `business/plan.md` (adds Customer personas and SWOT & positioning). Asks the depth tier and confirms gaps up front. |
| `/business:launch` | Go-to-market plan → `business/gtm-plan.md`, guarded by `MATURITY.md` state. |
| `/business:track` | Record actuals (incl. optional marketing funnel) → `business/metrics.md`, diff vs targets, bump Last reviewed. |
| `/business:biz-portfolio` | Sweep every project, rebuild `global-business.md` (flags stale research/plans). |

All seven are invocable as `/business:<skill>` and also fire on natural language ("is this worth monetizing", "size the market", "how are we doing vs targets"). They form a pipeline — `assess` gates the rest, since a project that shouldn't be monetized doesn't need a revenue model — but each runs standalone once its predecessor's verdict exists.

## Agent

### `market-researcher`

Gathers **cited** competitive-analysis evidence for one project by the method in `references/competitive-analysis-method.md`: a competitor is anyone who solves the same problem, listed in three passes (category, customer-job, alternatives) and classed direct/indirect, with the discovery rate tracked so "no competitors" reads as a failed search rather than a finding; pricing (unpublished prices traced to where a customer asked in public), channels, demand; at `standard`+ the competitor table as YAML plus six-block profiles (team — public professional history only, strategy, product with *measured* weaknesses, marketing, metrics with their estimation method, investment/organization). Dispatched by `market-research` (and by `assess --research` at `triage`) rather than invoked directly. It never writes files, never renders a verdict, and never makes a product recommendation.

**Model:** `sonnet`. **Tools:** `Read`, `Grep`, `Glob`, `WebFetch`, `WebSearch`.

**Prerequisite that actually bites:** it needs **WebSearch**. Without it there is no evidence to gather, and the skills that depend on it **write nothing rather than emitting an uncited guess** — a market-research file that reads like research but was produced from training data is worse than no file, because the next reader trusts it.

## Artifacts (in the vault)

Per project, under `<vault_dir>/Portfolio/<area>/<project>/business/`:

- `BUSINESS.md` — canonical, schema-versioned. Sole machine-readable index.
- `market-research.md` — tiered, cited competitive analysis (schema 3; `research` block with `depth`, `competitors` row count, `coverage` exhausted|open).
- `competitor-table.yaml` — the competitor table (schema 1): rows × characteristics in four categories, every cell a quantity; parsed only by `scripts/competitor-table.py`, which normalizes it to −5…+5, sweeps axis pairs, and renders `quadrant-<x>-<y>.svg` / `trajectory-<x>-<y>.svg` beside it.
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

Asks for a depth tier (`brief` / `standard` / `deep`) and confirms scope — including the
customer-job statement *"when [situation], I want to [action], so that [outcome]"* the whole
list rests on — before doing anything. Dispatches `market-researcher`, writes
`business/market-research.md` — **cited** — and at `standard`+ the competitor table, then runs
the deterministic lane over it:

```text
python3 scripts/competitor-table.py validate   business/competitor-table.yaml
python3 scripts/competitor-table.py sweep      business/competitor-table.yaml --size headcount
python3 scripts/competitor-table.py quadrant   business/competitor-table.yaml --x price --y depth --size headcount --svg quadrant-price-depth.svg
python3 scripts/competitor-table.py trajectory business/competitor-table.yaml --x price --y depth --size headcount --svg trajectory-price-depth.svg
```

The sweep ranks axis pairs by where the project stands furthest from everyone and how many
quadrants are empty, and flags groups that scatter; the operator picks the map. If WebSearch
is unavailable the skill writes nothing at all rather than producing a research-shaped file
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
