---
name: assess
description: >
  Use to run a viability triage for one portfolio project — decide whether it is worth monetizing, for whom, and on what evidence — and write the verdict to business/BUSINESS.md. Triggers on "is this worth monetizing", "assess this project's business case", "business viability", "should I commercialize this", "who would pay for this", "triage this project commercially". Reads the repo, the project's vault page, and MATURITY.md, runs a structured one-question-at-a-time interview, and with --research dispatches a cited market-researcher pass. Writes a schema-versioned verdict: monetize | free-for-reputation | internal-only | park (park and internal-only are complete, valid outcomes).
---

# assess — viability triage

Decide whether ONE project is worth monetizing, for whom, and on what evidence —
then record it in `business/BUSINESS.md`. The verdict is the gate the rest of the
pipeline (`model` → `launch` → `track`) depends on.

**Announce at start:** "Using the business assess skill to triage <project>'s viability."

## Determinism boundary

You never hand-parse the business artifacts. To read existing business state, run the
scanner and consume its JSON:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/business-scan.py
```

You only ever WRITE `BUSINESS.md`, conforming to
`${CLAUDE_PLUGIN_ROOT}/references/business-md-format.md` (schema 1). The scanner is the
sole reader; if a field isn't in the frontmatter, no downstream tool can see it.

## Resolve the project

Business artifacts are vault-canonical. Resolve the home the same way the planning
plugin does: read `vault_dir` from `~/.claude/portfolio-config.yaml`, then
`home = <vault_dir>/Portfolio/<area>/<name>/` from the project's `~/dev/<area>/<name>`
path (auto-register the project in `~/.claude/projects-registry.yaml` if it's new). Write
to `<home>/business/BUSINESS.md`; `mkdir -p` the `business/` dir.

If a `BUSINESS.md` already exists (scanner shows `assessed: true`), this is a
re-assessment — read its current verdict from the scanner JSON, and confirm before
overwriting a non-`park` verdict.

## Phase 1 — Ground in evidence (before asking anything)

Gather what the repo and vault already tell you, so you don't ask what you can infer:

- **Repo:** README, manifest, what the tool actually does (not what its name implies).
- **Vault page:** `<vault>/Projects/<name>.md` or the project's vault-context — prior
  notes on audience or intent.
- **MATURITY.md** (via scanner or the file): how close to ship-ready — a project far from
  shippable can still be assessed, but note the distance.
- **Existing plans/backlog** in the vault home — commercial intent already recorded.

## Phase 2 — Structured interview (one question at a time)

Ask only what you can't infer. One question per message, multiple-choice where the answer
space is finite. Cover:

- **Problem & audience** — who is this for, what do they do today without it? (If you
  inferred an audience in Phase 1, state it and ask for confirmation.)
- **Payable?** — would that audience pay, or is the value reputational / funnel /
  internal? This maps directly to the verdict.
- **Substitutes** — what do they use instead, and is it free? (Informs whether money is
  even on the table.)
- **Operator intent** — does the user *want* to monetize this, or ship it free, or is it
  a personal tool? Respect this: a great market with no intent to sell is
  `free-for-reputation` or `internal-only`, not `monetize`.

Stop asking once you can justify a verdict. You need enough to decide, not everything.

## Phase 3 — Optional research (`--research`)

When invoked with `--research`, dispatch the **market-researcher** agent
(`${CLAUDE_PLUGIN_ROOT}/agents/market-researcher.md`) with the project, the audience
hypothesis, the repo path, and candidate channels. It returns cited competitors, pricing
signal, channel norms, and demand evidence — never a verdict. Fold its findings into the
evidence section and set `evidence: researched`.

If research is unavailable (offline, WebSearch denied) or `--research` was not passed,
proceed on local evidence, set `evidence: local-only`, and say so explicitly — the
verdict's confidence is lower and the file records that.

## Phase 4 — Verdict

Choose exactly one, and make the "no" verdicts first-class outcomes, not failures:

- **`monetize`** — a payable audience, a substitute gap or willingness to pay, and
  operator intent to earn. Unlocks `model`.
- **`free-for-reputation`** — ship free on purpose (portfolio, reputation, a funnel to
  paid work). Unlocks `model` (channels and targets still matter).
- **`internal-only`** — for the operator's own use; no external launch. **Done.**
- **`park`** — not worth pursuing now. **Done.** Most projects land here, and that's the
  point of triage — permission to focus. Record *why* so a future re-assessment has the
  reasoning.

## Phase 5 — Write BUSINESS.md

Write the frontmatter (schema 1) with `verdict`, `audience`, `evidence`,
`last_reviewed: <today>`, a `monetization` stub (`model: null` until `model` runs), and an
empty `targets: []`. Set `project: <name>` to match the registry. Put the rationale,
audience reasoning, and (if researched) the cited findings in the markdown body.

**Verify before finishing:** run `business-scan.py` and confirm the project now shows
`assessed: true`, the right `verdict`, and **zero `errors`** — a non-empty `errors` array
means the file you wrote doesn't conform to the schema (fix it, don't leave it).

## Hand off

- `monetize` / `free-for-reputation` → suggest `/business:model` next.
- `park` / `internal-only` → done; the verdict is the deliverable. No launch, no model.
