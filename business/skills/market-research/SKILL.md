---
name: market-research
description: >
  Produce a deep, cited market-research report for ONE portfolio project — competitors and pricing, market sizing (TAM/SAM/SOM), trends, positioning gaps, channel norms, and demand — and persist it to business/market-research.md for assess and business-plan to reuse. Use when you want standalone market evidence, not a verdict. Triggers on "research the market for this", "market research for this project", "size the market", "who are the competitors and what do they charge", "TAM SAM SOM", "is there a payable audience", "refresh the market research". Writes nothing if WebSearch is unavailable — a half-cited report is worse than none.
---

# market-research — deep, persistent market evidence

Run a **full-depth** market-research pass for ONE project and persist it to
`business/market-research.md`. The artifact is reused by `/business:assess --research`
(when fresh, ≤ 90 days) and folded into `/business:business-plan`, so one research pass
serves the whole pipeline. This skill gathers **evidence, never a verdict** — the
monetize / free / park decision stays with `assess` and the operator.

**Announce at start:** "Using the business market-research skill to research <project>'s market."

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
conforming to `${CLAUDE_PLUGIN_ROOT}/references/market-research-format.md` (schema 1); the
scanner is the sole *reader* of its frontmatter.

If the project isn't in the scanner output, it isn't registered — auto-register it the way
`assess` does (append to `~/.claude/projects-registry.yaml` from its `~/dev/<area>/<name>`
path) and re-run the scanner before proceeding.

## Preconditions

Market research is **standalone** — it does not require a verdict, so it runs before or
after `assess`. You need two things to research well:

- **What the tool actually is** — `Read` the repo README/manifest at the project's `path`
  (from the scanner entry), so the competitor set matches what the tool does, not what its
  name suggests.
- **An audience hypothesis** — if a `BUSINESS.md` exists, reuse its `audience`; otherwise
  infer one from the repo and state it, or ask the operator in one line if it's genuinely
  ambiguous. Mark findings that rest on an assumed audience.

## Re-run — refresh, don't clobber

If `market-research.md` already exists (scanner shows `research.exists: true`), this is a
**refresh**. `Read` the current file first, tell the operator its `researched` date and
age, and **confirm before overwriting** — then write the new dated pass. Don't silently
replace a recent artifact.

## Dispatch the researcher (depth: full)

Dispatch the **market-researcher** agent
(`${CLAUDE_PLUGIN_ROOT}/agents/market-researcher.md`) at **`depth: full`**, briefed with:
the project (one or two lines of what it does), the audience hypothesis, the repo path, and
the candidate channels (from `BUSINESS.md` `channels` if present, else inferred from the
platform). It returns cited **Competitors, Pricing signal, Market sizing (TAM/SAM/SOM),
Trends, Positioning gaps, Channels, Demand signal, and Gaps** — never a verdict, never a
written file. Every claim is cited or framed as an evidenced absence; discard any uncited
figure.

## If research is unavailable — write nothing

If WebSearch is denied or the environment is offline, the agent cannot gather cited
evidence. **Do not write a half-cited or uncited `market-research.md`** — an
authoritative-looking file with no sources is worse than none. Say so plainly ("market
research needs WebSearch, which is unavailable here — no artifact written"), leave any
existing artifact untouched, and stop. `assess`/`business-plan` will proceed on
`local-only` evidence and record that.

## Write the artifact

Write `<home>/business/market-research.md` per `references/market-research-format.md`:
frontmatter `schema: 1`, `project: <name>`, `researched: <today>`, `depth: full`,
`confidence: <high|medium|low>` (your honest overall read of the evidence — primary
sources → high, mostly secondary → medium, substantially inferred → low). The body carries
the agent's cited findings under the format's section headings. No uncited numbers; "could
not size — searched …" is a first-class finding.

## Verify

Run `business-scan.py` and confirm the project shows `research.exists: true`, the right
`research.depth` (`full`), a computed `research.age_days` (0 today), and **zero `errors`**
for the project (a non-empty `errors` array means the file doesn't conform — fix it).

## Hand off

- If the project has no verdict yet → suggest `/business:assess --research` (it will reuse
  this fresh artifact instead of re-researching).
- If it's assess-passed → suggest `/business:business-plan` to fold this research into a
  full business plan, and `/business:biz-portfolio` to see the research age in the roll-up.
