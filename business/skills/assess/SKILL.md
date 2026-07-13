---
name: assess
description: >
  Decide whether ONE portfolio project is worth monetizing, for whom, and on what evidence — and record the verdict in business/BUSINESS.md. Use for commercial triage of a single project. Triggers on "is this worth monetizing", "assess this project's business case", "business viability", "should I commercialize this", "who would pay for this", "triage this project commercially". Produces a verdict of monetize | free-for-reputation | internal-only | park (park and internal-only are complete, valid outcomes). Supports an optional --research market pass.
---

# assess — viability triage

Decide whether ONE project is worth monetizing, for whom, and on what evidence —
then record it in `business/BUSINESS.md`. The verdict is the gate the rest of the
pipeline (`model` → `launch` → `track`) depends on.

**Announce at start:** "Using the business assess skill to triage <project>'s viability."

## Determinism boundary

For **cross-project state and decisions**, run the scanner and consume its JSON — never
hand-parse another project's artifacts:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/business-scan.py
```

You WRITE `BUSINESS.md` conforming to
`${CLAUDE_PLUGIN_ROOT}/references/business-md-format.md` (schema 1). The scanner is the
sole *cross-project* reader; if a field isn't in the frontmatter, no downstream tool sees
it. **But when editing an existing `BUSINESS.md`, `Read` the actual file first and make
targeted edits** — the scanner JSON deliberately omits the `project:` field and the entire
markdown body, so reconstructing the file from JSON alone would silently drop them.

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

When invoked with `--research`, first check the scanner JSON for an existing
`market-research.md` artifact before dispatching anything — the `market-research` skill
may already have produced one, and re-researching wastes a WebSearch pass:

- **Reuse a fresh artifact.** If the project's scanner entry shows `research.exists: true`
  with `research.age_days` ≤ **90** (the staleness window), read
  `business/market-research.md`, fold its cited findings into the evidence section, and set
  `evidence: researched` — do **not** dispatch the agent. Note in the body that the verdict
  reused the dated research artifact.
- **Otherwise dispatch.** If there's no artifact, or it's stale (`age_days` > 90), dispatch
  the **market-researcher** agent (`${CLAUDE_PLUGIN_ROOT}/agents/market-researcher.md`) at
  **`depth: triage`** with the project, the audience hypothesis, the repo path, and
  candidate channels. It returns cited competitors, pricing signal, channel norms, and
  demand evidence — never a verdict. Fold its findings in and set `evidence: researched`.
  (assess does a fast viability pass, so `triage` depth is correct here; the deeper `full`
  pass belongs to `/business:market-research`, which persists the artifact this phase
  reuses.)

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

Branch on whether this is a first assessment or a re-assessment:

- **Fresh assessment** (no prior `BUSINESS.md`): write frontmatter (schema 1) with
  `verdict`, `audience`, `evidence`, `last_reviewed: <today>`, a `monetization` stub
  (`model: null`, `pricing: null`, `channels: []`), and empty `targets: []`. Set
  `project: <name>` to the registry name. Put rationale, audience reasoning, and (if
  researched) the cited findings in the markdown body.
- **Re-assessment** (a `BUSINESS.md` already exists — `Read` it first): update `verdict`,
  `audience`, `evidence`, and `last_reviewed` **in place**, and **preserve the existing
  `monetization` block, `targets`, `project:`, and the body**. `model` and `track` wrote
  those — never reset them to a stub just because you re-ran assess. Only when the new
  verdict moves *away* from `monetize`/`free-for-reputation` (e.g. to `park`) do you clear
  `monetization`/`targets`, and then state that to the user as a deliberate consequence,
  not a silent side effect.

**Verify before finishing:** run `business-scan.py` and confirm the project shows
`assessed: true`, the right `verdict`, and **zero `errors`** (a non-empty `errors` array
means the file doesn't conform — fix it). Note: "zero errors" does *not* prove you
preserved `model`'s monetization/targets on a re-assessment — that's on you, per above.

## Hand off

- `monetize` / `free-for-reputation` → suggest `/business:revenue-model` next.
- `park` / `internal-only` → done; the verdict is the deliverable. No launch, no model.
