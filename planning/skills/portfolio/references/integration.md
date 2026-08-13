# Integration — what each neighbouring skill is for

The per-skill detail behind `../SKILL.md` § Integration. Read it when routing an ask to one of
these rather than handling it here.

- **planning-projects** — produces the plan files that `unify` parses for backlog candidates.
- **executing-plans** — checks off Task N.N items as work lands; `unify` re-runs against the updated plans.
- **backlog** — invoked per-project via sub-agent for `unify` candidate generation and `add` accepted entries.
- **project-maturity** — invoked per-project via sub-agent for `audit` and `get`.
- **dispatching-parallel-agents** — used for the parallel per-project fan-out in `unify` and `maturity`.
- **compass** — "what should I work on next" / "what's in flight" / periodic-review asks route to the `compass` skill, which reads (never writes) the artifacts this skill maintains.
