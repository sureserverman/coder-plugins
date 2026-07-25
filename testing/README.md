# testing

A single strongly-opinionated SDET subagent, `testing-expert`, that runs and triages tests, authors new ones, audits coverage, reviews tests for smells, and explains testing methodology with citations. The shape matters: this is **one agent with six protocols**, not six skills — testing work is usually several of these at once (you run a suite, triage what broke, and end up authoring a missing case), and a single agent keeps that in one context.

## Install

```text
/plugin install testing@coder-plugins
```

No external dependencies. The agent detects your stack from the repo itself and uses the test invocation your CI already declares.

## `testing-expert` (agent)

**What it does.** Acts as a senior SDET. It is opinionated by design — test pyramid, mutation-score-over-line-coverage, OWASP baseline — and defends its positions with named sources (Beck, Fowler, Meszaros, Feathers, Google Testing, OWASP WSTG, Stryker, Hypothesis, ThoughtWorks Radar). It is also pragmatic about restraint: throwaway code needs no tests and it will say so rather than manufacture busywork.

**How it fires.** Three ways:

- **Automatic delegation** when a task matches — "run tests", "test failures", "flaky test", "coverage gap".
- **Direct request** — "have `testing-expert` audit coverage in `src/parsers/`".
- **From plan execution** — `planning`'s `dispatching-parallel-agents` routes any test-authoring/triage/coverage task to it via `references/stack-routing.md`, on any stack. `executing-plans` also reaches for it when a plan task's test is ambiguous or flaky.

**Model:** pinned to `sonnet`. **Tools:** `Bash`, `Read`, `Grep`, `Glob`, `Edit`, `Write`, `WebFetch`, `TaskCreate`, `TaskUpdate` — it can write tests and run them, so scope your request.

### The six protocols

The agent announces which protocol it is in before acting. They compose.

| # | Protocol | Input | Output |
|---|---|---|---|
| 1 | **Stack detection** | an unfamiliar repo | **Stack Report** — languages, frameworks, runners, the canonical CI invocation, coverage and mutation tooling (or a note that it is absent) |
| 2 | **Execute & triage** | the default entry point | **Triage Report** — failures clustered by shared symptom, a root-cause hypothesis per cluster ranked H/M/L, and a minimal repro |
| 3 | **Gap analysis** | an audit or pre-release check | **Coverage Map** — modules × layers (unit / integration / contract / e2e / perf / sec / a11y), top-5 gaps ranked by risk × effort |
| 4 | **Authoring** | a feature spec or an identified gap | new tests at the lowest pyramid layer that gives confidence; a **Test Plan** first when scope exceeds one file |
| 5 | **Review** | a test file or diff | **Test Review** — smells in Meszaros vocabulary, coupling issues, weak assertions, predicted mutation survivors |
| 6 | **Coach** | "why does X work this way?" | a cited explanation, with both sides presented when the question is contested (mocks vs real, for instance) |

Protocol 1 runs first on any repo it doesn't know, and **it will not run your tests before reporting the stack** — that ordering is deliberate, so a wrong invocation doesn't get mistaken for a failing suite.

### Behavior worth knowing before you delegate

- **Flaky suites are quarantined, never silent-skipped.** The path is fixed-seed reproduction → quarantine with an expiry and an owner. A test that is skipped without a record is a test everyone forgets is gone.
- **It will not propose a fix below Medium confidence.** Under that bar it gathers more evidence instead — the same evidence-first discipline as `planning:no-fafo-debugging`.
- **Line coverage is not treated as confidence.** If your repo has no mutation tooling, the gap analysis says so rather than reporting a coverage percentage as if it settled the question.

## Artifacts

**None persisted.** Every protocol returns a report in the conversation; nothing is written to disk except the test files Protocol 4 authors, at paths matching your project's existing test layout. If you want a coverage audit recorded, capture it yourself — or use `planning:project-maturity`, whose Testing & CI axis is the durable home for that verdict.

## Worked example

```text
/plugin install testing@coder-plugins

"the CI suite has been flaky for a week — figure out which tests"
```

The agent enters Protocol 1, reads your manifests and `.github/workflows/`, and reports the canonical invocation. It then enters Protocol 2, runs that invocation, clusters the failures, and reports that three of them share a stack frame in a shared fixture while one is genuinely order-dependent. For the order-dependent one it produces a fixed-seed repro and proposes quarantine with an owner and an expiry date, rather than a skip.

```text
"write the missing tests for the parser gap you found"
```

Protocol 4: since the parser has a domain, it writes property-based tests alongside example-based ones, and gives every happy path an error-path sibling.

## Related plugins

- **`planning`** — `dispatching-parallel-agents` and `executing-plans` both route test work here through the shared `stack-routing.md` table; `project-maturity` owns the durable Testing & CI readiness verdict.
- **`git-github`** — `code-reviewer` reviews the diff; `testing-expert` reviews the *tests*. Distinct axes, both read-only.
- **`android-dev`** — Android instrumented/Compose test work routes here with `kotlin-compose-testing-patterns` loaded first.
