# Project Plan: Close the open backlog (BL-020 … BL-027)
Date: 2026-07-26

Closes the eight open entries in `backlog.md`. Four carried a judgment call the entry
itself deferred; all four were settled with the user before authoring and the chosen
option is recorded on the owning task.

## Research Summary

### Verification pass (all eight re-checked against the tree, 2026-07-26)

Every entry was re-verified before planning. **All eight still hold** — none had been
silently fixed. Two carry text that is now inaccurate and is corrected as part of closing
them:

- **BL-020** — the entry says "every test-invoking command **in this repo**" globs
  python-only. There is no repo-side aggregate glob at all: CI runs suites through 13
  individual workflows, and the bash suite has its own (`validate-mount-validation.yml`).
  The python-only glob is the **Preflight-command convention in the vault plans**
  (`for t in planning/skills/*/tests/test-*.py scripts/tests/test-*.py; do …`), which is
  what "run the suite" actually means here. The gate-oscillation plan's own close-out
  (line 438) already established that no CI glob exists and called it the P7 failure class.
  Same defect, wrong location named — and the location decides where the fix goes.
- **BL-024** — the body is accurate (`resolve_any_component` returns true for a name in
  *any* plugin; no attribution is verified). Its **Note** is stale: it proposes that if
  false behavioral claims recur, "the answer is a different check — assertions about
  behavior need a source citation." That check shipped as part of P7 —
  `honest-gates` § *A behavioral claim is a gate too*, wired into Tier-1 review
  (`executing-plans` line 364) and the stage-gate behavioral-claim sweep (line 457).

Confirmed unchanged, quoted at the line they were verified against:

- **BL-021** — `android-dev/infrastructure/mcp-server/server.mjs:13-14` reads
  `SCREENSHOTS_DIR` / `APK_BASE_DIR`; the host-side override contract is
  `SCREENSHOT_DIR` / `APK_DIR` across `android-dev/README.md`,
  `android-dev/infrastructure/README.md`, and `android-dev/commands/android-screenshots.md`.
  No doc mentions the container-side pair; the only prose naming `APK_BASE_DIR` is
  `server.mjs`'s own tool description (lines 501-525).
- **BL-022** — measured by extracting every component token per flow: flow 1 names 9
  components, **all `planning`**; flow 6 names 6, all `planning`; flow 7 names 2, all
  `planning`. 3 of 10 flows do not span plugins.
- **BL-023** — `scripts/check-usage-tokens.py:88`, `START = r"(?:(?<=^)|(?<=\s)|(?<=`))"`,
  unchanged. Premise re-verified: zero punctuation-adjacent slash tokens exist in
  `docs/USAGE.md` today, so the current pass is sound and this is a latent gap, not a live
  miss.
- **BL-025** — `planning/skills/executing-plans/SKILL.md:502-545`: step 2 says "name the
  set the finding quantifies over", step 3 requires the sweep-over-the-set, budget default
  2 with round counting. Prose discipline with no derivation procedure, exactly as written.
- **BL-026** — no `Scope:` field exists in `planning-projects/SKILL.md`.
- **BL-027** — `grep -c 'no-fafo' planning/skills/executing-plans/SKILL.md` → **0**. The
  skill is referenced from `honest-gates`, `planning/README.md`, `testing/README.md` and
  `docs/USAGE.md` — everywhere except the gate-failure procedure, which is now fully
  specified at lines 502-545 and is exactly where evidence-first diagnosis belongs.

### Project context

- **The suite is cheap.** Full baseline (all python suites + stack routing + the bash
  mount suite) runs green in **3.9s**. No test-scope tiering is needed; every gate runs
  the full suite. This plan declares no stage-scope/plan-scope split.
- **Test layout** — 23 python suites in four homes (`planning/skills/*/tests/`,
  `planning/skills/decisions/scripts/tests/`, `scripts/tests/`, `business/scripts/tests/`)
  plus **one** bash suite (`android-dev/skills/android-mcp-orchestrator/scripts/tests/test-mount-validation.sh`).
  Repo convention is direct `python3 <file>` invocation, **not** pytest.
- **No canonical test command is documented anywhere** — no `CONTRIBUTING.md`, and
  `README.md` never names one. This is the vacuum the per-plan Preflight string filled.
- **`capability-index.json` is viable as BL-024's resolution source**: a dict with a
  `components` list, each entry carrying `name`, `kind`, `plugin`, `path`. It is rebuilt by
  `scripts/build-capability-index.py` (PyYAML 6.0.1 present, exits 0) and pinned in CI by
  `validate-frontmatter-budget.yml`.
- **`scripts/tests/test-check-usage-tokens.py`** builds synthetic plugin *trees* under a
  temp root (`fixture()` at line 48, `load(repo)` at line 32) — BL-024's rewrite requires
  these fixtures to also write a synthetic *index*.
- **No `docs/workflows/`** — this repo has no behavior-contract specs, so no `WF-NNN`
  declarations apply to any task in this plan.
- **No architecture doc covers this scope.** The two in `plans/` are
  `2026-07-04-architect-capability-*` and `2026-07-12-business-plan-market-research-*`;
  neither governs the test runner, the USAGE guard, or the planning-skill contract.
  Structure here is decided inline.

### Settled judgment calls (user, 2026-07-26)

- **BL-020 → a `scripts/run-tests.sh` runner.** One script globs python + bash suites and
  becomes the canonical invocation. Rejected: porting the bash suite to python (re-tests
  shell behavior through subprocess, and the port itself needs verifying); widening the
  Preflight glob string (it is copy-pasted per plan and drifts — which is how this gap
  appeared).
- **BL-022 → mixed.** Rewrite flow 1 to span `planning` → `git-github` (shipping a feature
  genuinely involves commit/review/PR); amend the file's purpose statement to admit that
  layer flows (6 portfolio, 7 decisions) legitimately live in one plugin.
- **BL-024 → rewrite resolution against `capability-index.json`.** The entry's own "clean
  fix", including deleting the guard's hand-rolled duplicate of the component-discovery
  rule.
- **BL-026 → implement the `Scope:` field now** rather than parking it.

### Ordering consequence

BL-026 lands **before** BL-025: the `Scope:` field is the authoring-time declaration of the
set, and BL-025's repair procedure derives its class sweep from it. Planned the other way
round, the repair procedure would have nothing to cite.

## Decisions in force

- DEC-005 — A gate check over a set is an executable sweep; an assertion about behavior cites its source (accepted; portfolio-tooling) — every gate check in this plan asserting a property of a set is written as the command that sweeps it, or carries `(judgment)`; every sentence this plan adds asserting what code does cites the file it was checked against.
- DEC-004 — The bundled emulator stack takes its mount paths as overrides, never a hardcoded repo (accepted; android) — binds Task 3.1: the container-side/host-side distinction must be documented as an override contract, and the doc must not reintroduce a project-specific default.
- DEC-003 — A plan carries the decisions that bind it; a contradiction fails a gate (accepted; portfolio-tooling) — satisfied by this section plus the Stage 5 conformance check.
- DEC-001 / GDEC-SEC-001 — sec-audit findings are recorded as decisions; reports stay local (accepted; security) — no security finding is in scope for this plan; noted as consulted, not binding.
- DEC-002 — Business-group manifest (accepted; portfolio-tooling) — does not bind: no business-layer change in scope.

**Registers consulted:** `/mnt/vault/Portfolio/ai-tools/coder-plugins/decisions.md` (DEC-001 … DEC-005); `Portfolio/decisions/security.md` (GDEC-SEC-001)
**Domains inferred:** portfolio-tooling, android, security (only `security` has a domain register today)

## Preflight

- [ ] Baseline green: `for t in planning/skills/*/tests/test-*.py scripts/tests/test-*.py; do python3 "$t" || exit 1; done && python3 planning/skills/decisions/scripts/tests/test-decisions-relevant.py && python3 planning/skills/dispatching-parallel-agents/scripts/validate-stack-routing.py && bash android-dev/skills/android-mcp-orchestrator/scripts/tests/test-mount-validation.sh` — **verified green, 3.9s, 2026-07-26**
- [ ] PyYAML importable (`python3 -c 'import yaml'`) — required by `build-capability-index.py` — **verified, 6.0.1**
- [ ] `capability-index.json` is current: `python3 scripts/build-capability-index.py && git diff --exit-code capability-index.json`
- [ ] Working tree clean at branch point; branch `backlog-bl020-bl027` created off `main`

**Test-scope commands:** not tiered — the full suite is 3.9s, well under the ~5 min
threshold in `references/test-scope-tiers.md`. Every gate runs it in full. From Stage 1
Task 1.3 onward the canonical invocation is `bash scripts/run-tests.sh`.

---

## Stage 1: Canonical test runner

**Goal:** One command runs every suite in the repo regardless of language, and it is
documented where a contributor will find it.
**Depends on:** none
**Blocks:** Stage 2, Stage 3, Stage 4, Stage 5 (every later gate invokes the runner)
**Risk:** LOW — additive; the existing per-suite invocations keep working unchanged.
**Rollback:** `git revert` the stage's commits; delete `scripts/run-tests.sh`. No CI
workflow is modified, so nothing else depends on it.

### Task 1.1: Write `scripts/run-tests.sh` — Closes BL-020 (part 1)
- **Status:** [x]
- **Depends on:** none
- **Blocks:** Task 1.2, Task 1.3
- **Parallel:** YES
- **Scope:** the four python suite homes (`planning/skills/*/tests/`, `planning/skills/decisions/scripts/tests/`, `scripts/tests/`, `business/scripts/tests/`), every `**/scripts/tests/test-*.sh`, and `validate-stack-routing.py`
- **Test:** `bash scripts/run-tests.sh` exits 0, and `bash scripts/run-tests.sh --list` prints ≥24 suite paths including `android-dev/skills/android-mcp-orchestrator/scripts/tests/test-mount-validation.sh`
- **Red-Green max cycles:** 3

Must fail loudly on an empty glob — mirroring `validate-plan-progress.yml`'s "No suites
found — the glob is wrong, not the tree", which exists because a silent empty sweep reads
as a pass. `--list` prints discovered paths without running them; it is what Task 1.2
asserts against.

### Task 1.2: Fixture test pinning runner discovery — Closes BL-020 (part 2)
- **Status:** [x]
- **Depends on:** Task 1.1
- **Blocks:** Task 1.3
- **Parallel:** NO (blocked by 1.1)
- **Scope:** every `test-*.py` and `test-*.sh` file on disk
- **Test:** `python3 scripts/tests/test-run-tests-discovery.py` passes — it enumerates every `test-*.py`/`test-*.sh` on disk and asserts each appears in `run-tests.sh --list` output; it must FAIL when a planted suite file is absent from the listing
- **Red-Green max cycles:** 3

This is the class predicate for the whole item: it fails when the *next* suite in a new
language, or a new home, is added without the runner learning about it. A runner that
merely works today would re-open BL-020 on the next addition.

### Task 1.3: Document the canonical command
- **Status:** [x]
- **Depends on:** Task 1.1, Task 1.2
- **Blocks:** none
- **Parallel:** NO (blocked by 1.1, 1.2)
- **Scope:** `README.md`; every repo doc that names a test invocation
- **Test:** `grep -q 'scripts/run-tests.sh' README.md` and `bash scripts/run-tests.sh` re-run green from the documented text verbatim
- **Red-Green max cycles:** 2

A short "Running the tests" section in `README.md` — the repo has no `CONTRIBUTING.md` and
names no test command anywhere today, which is the vacuum the per-plan Preflight string
filled. **CI is deliberately not restructured:** the bash suite already runs in CI via
`validate-mount-validation.yml`, so BL-020's actual defect is the *local/authoring* path,
not coverage.

### Stage 1 Gate
- [ ] `bash scripts/run-tests.sh` exits 0 and its suite count matches disk: `test "$(bash scripts/run-tests.sh --list | wc -l)" = "$(find . -path ./node_modules -prune -o \( -name 'test-*.py' -o -name 'test-*.sh' \) -print | wc -l)"`
- [ ] Every suite on disk is discovered — `python3 scripts/tests/test-run-tests-discovery.py`
- [ ] No regressions: the pre-existing Preflight command still passes unchanged (the runner is additive, not a replacement of the per-suite path)
- [ ] **(judgment)** The runner's failure modes read correctly to someone who has never seen it — empty glob, one failing suite, and a missing interpreter each produce a message naming the cause. No sweep can prove a diagnostic message is *useful*; an evaluator reads them.

**Stage 1 handoff:** Gate green — remediation round 1 of 2. Three deviations worth
carrying forward.

1. **The plan's Preflight baseline was measured before the plan file existed**, so it
   was stale by the time Stage 1 ran. `test-validate-gate-checks.py` group 9 pins the
   validator's docstring calibration against a live sweep of the *vault plan corpus*;
   authoring this plan added 25 checks (13 exec / 7 judgment / 5 prose / 0
   instance-shaped) and turned the suite red. Fixed by recalibrating 374/41 → 399/42
   (commit `df269b8`). **Consequence for every future plan: authoring one turns this
   suite red until the docstring is updated.** Recorded as a new backlog item at
   close-out — it is a treadmill, not a one-off.
2. **The `(judgment)` gate check found a real defect that no executable check did.**
   Exercising the runner's three failure modes showed `run_one()`'s "no known
   interpreter" branch was unreachable: `discover()` only emits `.py`/`.sh`, so a suite
   in any other language was **silently skipped** — BL-020's exact class, one language
   over. Fixed by an explicit `unsupported()` sweep that fails loudly and names the
   supported extensions, scoped to `*/tests/*` so it cannot fire on
   `test-scope-tiers.md` or `test-fixtures/`, with `__pycache__` pruned. Pinned by
   groups 4–5 of the discovery suite.
3. **CI was deliberately not restructured.** The bash suite already runs via
   `validate-mount-validation.yml`; BL-020's defect is the local/authoring path. The
   runner is documented as the local path and CI's per-workflow path filtering is
   stated in the README rather than silently contradicted.

**Residual (Minor, recorded not fixed):** the empty-tree message reads "the discovery
glob is wrong, not the tree", which is misleading when the tree genuinely is empty.

**Decisions in force:** DEC-005, DEC-004, DEC-003 still binding; GDEC-SEC-001 consulted,
not binding. No `Supersedes` citation raised in this stage.

---

## Stage 2: `check-usage-tokens.py` hardening

**Goal:** The USAGE guard tokenizes correctly regardless of surrounding punctuation, and
verifies which plugin ships each component — not merely that the name exists somewhere.
**Depends on:** Stage 1 gate passing
**Blocks:** Stage 3 (Stage 3 rewrites USAGE.md content and must be checked by the hardened guard)
**Risk:** MEDIUM — the resolution core is rewritten and the fixture harness must build
synthetic index files it has never built. The known trap is re-introducing the
path-fragment false positives the current `START` regex exists to prevent.
**Rollback:** `git revert` the stage's commits; `scripts/check-usage-tokens.py` and its
fixture test return to the current regex+tree resolution. Nothing else imports either.

### Task 2.1: Replace the `START` lookbehind with a real tokenizer — Closes BL-023
- **Status:** [x]
- **Depends on:** none (Stage 1 gate is the only precondition)
- **Blocks:** Task 2.2
- **Parallel:** YES
- **Scope:** every slash-token extraction site in `check-usage-tokens.py` (lines 88, 91, 102)
- **Test:** `python3 scripts/tests/test-check-usage-tokens.py` passes with new cases asserting `(/planning:compass)` and `[/loadout set rust]` ARE extracted, and that `~/dev/`, `<repo>/docs/`, `./foo.md`, `<plugin>/skills/` are still NOT — the negatives are the regression risk, not the positives
- **Red-Green max cycles:** 3

### Task 2.2: Resolve names and attribution via `capability-index.json` — Closes BL-024
- **Status:** [x]
- **Depends on:** Task 2.1
- **Blocks:** Task 2.3
- **Parallel:** NO (blocked by 2.1 — same file)
- **Scope:** `resolve_qualified`, `resolve_bare`, `resolve_any_component`, `plugin_dirs`, and the fixture harness that feeds them
- **Test:** `python3 scripts/tests/test-check-usage-tokens.py` passes with a case where a component exists but is attributed to the WRONG plugin and the guard FAILS on it — plus the existing cases, re-pointed at synthetic index fixtures
- **Red-Green max cycles:** 3

Resolves against the index's per-component `plugin` field, deleting the hand-rolled
duplicate of the discovery rule already in `scripts/_frontmatter_common.PATTERNS`. Covers
both attribution shapes named in BL-024: the routing table's "Shipped by" column and
parenthetical forms like "(an `android-dev` agent)". The guard must degrade honestly if the
index is missing or stale — a guard that silently passes when it cannot resolve is the
failure DEC-005 names.

### Task 2.3: Run the hardened guard against the real `docs/USAGE.md`
- **Status:** [x]
- **Depends on:** Task 2.2
- **Blocks:** none
- **Parallel:** NO (blocked by 2.2)
- **Scope:** every component token and every attribution claim in `docs/USAGE.md`
- **Test:** `python3 scripts/check-usage-tokens.py` exits 0 against the live file and reports a checked-token count ≥ 89
- **Red-Green max cycles:** 3

Any attribution error this surfaces in the current file is fixed here — BL-024 records that
every attribution was verified *by hand* at the last gate, so a failure means the hand pass
missed one, which is the whole argument for mechanizing it.

### Stage 2 Gate
- [ ] `python3 scripts/check-usage-tokens.py` exits 0 on the live file with a non-zero checked count
- [ ] The guard fails on a wrong-plugin attribution — `python3 scripts/tests/test-check-usage-tokens.py` (the negative case is the point; a guard that only passes proves nothing)
- [ ] No path fragment is extracted as a token — the tokenizer negatives all hold in the fixture suite
- [ ] No regressions across the repo: `bash scripts/run-tests.sh`
- [ ] **(judgment)** The rewritten resolution reads as one mechanism rather than two glued together, and the index-missing path degrades honestly rather than silently passing. A conformance judgment over a diff; no sweep can prove it.

**Stage 2 handoff:** Gate green — no remediation rounds. Fixture assertions 30 → 76.

1. **Task 2.1 regressed the live token count 89 → 58 on its first cycle** and every
   fixture still passed. Cause: the new boundary allow-list enumerated space and tab
   but not newline, so every token beginning a line stopped being checked — while
   fixture tokens sit at offset 0, where the `i == 0` branch carries them. A
   positive-only test at offset 0 is structurally blind to this. Fixed with
   `str.isspace()`; group 3b2 pins the class. **Lesson worth carrying: the fixture
   harness's own uniformity was the blind spot, not the code.**
2. **Attribution is now checked for three shapes, not the two BL-024 named.** The
   qualified `/plugin:component` form gets it for free from the index lookup —
   `resolve_qualified` now means "that plugin ships it", where before it meant "that
   path exists". Live count 89 → 99.
3. **BL-024's hand-verification held.** The live file passes the new attribution
   sweep with zero findings, so the manual pass recorded at the previous gate had not
   in fact missed one. The value shipped here is ongoing enforcement, exactly as the
   entry framed it.
4. **One documented exception to index-based resolution:** `/loadout set|add <profile>`
   still resolves against `loadout/profiles/*/`, because profiles are not components
   and do not appear in the index.

**Decisions in force:** DEC-005, DEC-004, DEC-003 binding; GDEC-SEC-001 consulted. No
`Supersedes` raised.

---

## Stage 3: USAGE and android-dev documentation

**Goal:** The container-side/host-side variable distinction is documented, and `USAGE.md`'s
purpose statement matches what its flows actually do.
**Depends on:** Stage 2 gate passing
**Blocks:** none
**Risk:** LOW — prose only, and every executable claim it makes is now checked by the Stage 2 guard.
**Rollback:** `git revert` the stage's commits; the docs return to their current text.

### Task 3.1: Document the container-side vs host-side directory variables — Closes BL-021, Honors DEC-004
- **Status:** [x]
- **Depends on:** none (Stage 2 gate is the only precondition)
- **Blocks:** none
- **Parallel:** YES (touches only `android-dev/` docs — no file overlap with 3.2/3.3)
- **Scope:** `android-dev/README.md`, `android-dev/infrastructure/README.md`, `android-dev/commands/android-screenshots.md`
- **Test:** `grep -rl 'SCREENSHOTS_DIR' android-dev/ --include='*.md'` is non-empty, and every doc naming `SCREENSHOT_DIR` also distinguishes it from the container-side `SCREENSHOTS_DIR`: `test "$(grep -rl 'SCREENSHOT_DIR' android-dev/ --include='*.md' | wc -l)" = "$(grep -rl 'SCREENSHOTS_DIR' android-dev/ --include='*.md' | wc -l)"`
- **Red-Green max cycles:** 2

Per DEC-004 the host-side pair is an **override contract**; this task documents that the
container-side pair (`SCREENSHOTS_DIR`, `APK_BASE_DIR` — `server.mjs:13-14`) are the
in-container defaults the mounts land on, and must not introduce a project-specific
default. Documenting the distinction is the chosen resolution; **neither variable is
renamed**, because renaming is a behavior change to the in-container server that wants its
own verification (BL-021's own reasoning).

### Task 3.2: Rewrite USAGE flow 1 to span `planning` → `git-github` — Closes BL-022 (part 1)
- **Status:** [x]
- **Depends on:** none
- **Blocks:** Task 3.3
- **Parallel:** NO (same file as 3.3 — sequential by the file-conflict rule)
- **Scope:** `docs/USAGE.md` § "1. Idea → shipped feature"
- **Test:** flow 1 names components from ≥2 plugins — extract its tokens and assert the plugin set has size ≥2 — and `python3 scripts/check-usage-tokens.py` still exits 0
- **Red-Green max cycles:** 2

Flow 1 currently names 9 components, all `planning`, despite ending at "shipped". The
shipping half (`create-commit`, `code-review`, `create-pr`) lives in `git-github`.

### Task 3.3: Amend the purpose statement to admit single-plugin layer flows — Closes BL-022 (part 2)
- **Status:** [x]
- **Depends on:** Task 3.2
- **Blocks:** none
- **Parallel:** NO (blocked by 3.2 — same file)
- **Scope:** `docs/USAGE.md` purpose/intro statement
- **Test:** the file's stated purpose no longer claims every flow spans plugins, and every flow still satisfies it — verified by the Stage 3 gate's per-flow sweep
- **Red-Green max cycles:** 2

Flows 6 (portfolio) and 7 (decisions) are legitimately single-plugin: those layers really do
live in `planning`. The fix is the purpose statement, not the flows.

### Stage 3 Gate
- [ ] Every USAGE flow satisfies the amended purpose statement — a sweep over all 10 flow sections asserting each either spans ≥2 plugins or is an explicitly-admitted layer flow
- [ ] Every `android-dev` doc naming `SCREENSHOT_DIR` also distinguishes `SCREENSHOTS_DIR` (the Task 3.1 sweep, re-run)
- [ ] `python3 scripts/check-usage-tokens.py` exits 0 — every component named by the rewritten flow 1 resolves AND is correctly attributed
- [ ] No regressions: `bash scripts/run-tests.sh`
- [ ] **(judgment)** The rewritten flow 1 describes a path a real user would take, not a component list assembled to satisfy the ≥2-plugin check. Reads-coherently judgment; a token-set sweep cannot distinguish the two.

**Stage 3 handoff:** Gate green — remediation round 1 of 2.

1. **The gate caught a scope error the task inherited from the plan.** Task 3.1's
   `Scope:` named three docs; a fourth,
   `android-dev/skills/android-mcp-orchestrator/SKILL.md`, also names the host-side
   vars. The plan's research had enumerated the set from a `head -40`-**truncated**
   grep. The set-valued gate check found the missing member; an instance-shaped check
   naming three files could not have. **This is the BL-025/BL-026 argument arriving as
   evidence in the same plan that implements them** — a hand-typed `Scope:` inherits
   whatever the author's command truncated, so Stage 4's field is only as good as the
   sweep behind it. Worth saying in the `Scope:` guidance.
2. **The USAGE guard caught a fabrication I wrote.** Task 3.2's first draft cited
   `security-review` as a `git-github` skill; it is a Claude Code built-in and no
   plugin here ships it. Stage 2's hardened guard failed the build on it. Replaced with
   `gate-audit`, which git-github does ship. Had Stage 3 run before Stage 2, this would
   have shipped.
3. **Scope deliberately held:** four non-doc files (`compose.yaml`, `up.sh`, `run.sh`,
   the mount test) name `SCREENSHOT_DIR` without the distinction. They are executable
   config where only the host-side variable is meaningful; BL-021's class is
   documentation.

**Decisions in force:** DEC-005, DEC-004 (Task 3.1 conforms — override contract
documented, no project-specific default reintroduced), DEC-003 binding. No `Supersedes`.

---

## Stage 4: The `Scope:` task field

**Goal:** A plan task that changes a class of artifact declares the set it must sweep, at
authoring time.
**Depends on:** Stage 1 gate passing
**Blocks:** Stage 5 (BL-025's repair procedure derives its class sweep from this field)
**Risk:** MEDIUM — a plan-format change touches three format references plus the validator,
and every existing plan predates the field. Backward compatibility is the risk: the field
must be optional-but-checked, never retro-failing old plans.
**Rollback:** `git revert` the stage's commits; the field disappears from the format docs
and the validator stops reporting it. Existing plans are unaffected either way, which is
the property to preserve.

### Task 4.1: Add `Scope:` to the plan task format — Closes BL-026 (part 1)
- **Status:** [x]
- **Depends on:** none (Stage 1 gate is the only precondition)
- **Blocks:** Task 4.2, Task 4.3
- **Parallel:** YES
- **Scope:** `planning-projects/SKILL.md` (task template, Phase 2 structure block, authoring checklist), `references/light-plan-format.md`, `references/master-plan-format.md`
- **Test:** every plan-format reference that documents the task field list mentions `Scope:` — `test "$(grep -rl 'Scope:' planning/skills/planning-projects/SKILL.md planning/skills/planning-projects/references/light-plan-format.md planning/skills/planning-projects/references/master-plan-format.md | wc -l)" = 3`
- **Red-Green max cycles:** 3

The field is **conditional, not universal**: required only where a task changes a class of
artifact. A task editing exactly one file has no set to declare, and mandating the field
everywhere would train authors to write `Scope: this file` — noise that defeats the
purpose. The master-plan reference must state that masters carry no tasks and therefore no
`Scope:` (its parser-safety invariant is unaffected).

### Task 4.2: Teach `validate-gate-checks.py` to use `Scope:` — Closes BL-026 (part 2)
- **Status:** [x]
- **Depends on:** Task 4.1
- **Blocks:** Task 4.3
- **Parallel:** NO (blocked by 4.1 — the field must exist before it can be validated)
- **Scope:** `planning/skills/planning-projects/scripts/validate-gate-checks.py`
- **Test:** `python3 planning/skills/planning-projects/tests/test-validate-gate-checks.py` passes with new cases — a task declaring `Scope:` over a set whose gate check is INSTANCE-SHAPED is reported, and a plan with **no** `Scope:` fields anywhere is reported identically to today (no retro-failure)
- **Red-Green max cycles:** 3

The no-retro-failure case is the one that matters: `executing-plans` reports legacy plans
rather than failing them, deliberately, because a check executors learn to route around
protects nothing. This task must not break that asymmetry.

### Task 4.3: Validate this plan against the shipped field
- **Status:** [x]
- **Depends on:** Task 4.1, Task 4.2
- **Blocks:** none
- **Parallel:** NO (blocked by 4.1, 4.2)
- **Scope:** this plan file
- **Test:** `python3 planning/skills/planning-projects/scripts/validate-gate-checks.py <this plan>` reports zero INSTANCE-SHAPED, and every task in this plan that changes a class of artifact carries a `Scope:` line
- **Red-Green max cycles:** 2

Dogfooding: this plan already carries `Scope:` on its class-valued tasks. If the shipped
validator disagrees with the plan that shipped it, one of the two is wrong and this is the
cheapest place to find out.

### Stage 4 Gate
- [ ] Every plan-format reference documents `Scope:` — the Task 4.1 sweep, re-run
- [ ] `python3 planning/skills/planning-projects/tests/test-validate-gate-checks.py` passes, including the legacy-plan no-retro-failure case
- [ ] Every existing plan in the vault still validates as it did before: `for p in /mnt/vault/Portfolio/ai-tools/coder-plugins/plans/*.md; do python3 planning/skills/planning-projects/scripts/validate-gate-checks.py "$p" >/dev/null || echo "REGRESSED: $p"; done` prints nothing
- [ ] No regressions: `bash scripts/run-tests.sh`
- [ ] **(judgment)** The `Scope:` guidance makes clear when the field is required and when it is noise, so an author does not write `Scope: this file` on single-file tasks. A judgment about whether prose will be read correctly; no sweep can prove it.

**Stage 4 handoff:** Gate green — no remediation rounds.

1. **`Scope:` shipped as conditional, not universal**, and the guidance leads with the
   *derivation* rule rather than the syntax — because Stage 3 produced live evidence
   that a hand-typed set inherits whatever the author's command truncated. The rule is
   "paste the command you ran, not the answer you remember", with the Stage 3 incident
   quoted in the SKILL as the worked example.
2. **The validator's `Scope:` awareness is advisory and asymmetric by construction.**
   It reports a stage that declares a `Scope:` whose gate contains no executable sweep
   — the set named but not swept. It never changes an exit code, and a plan with no
   `Scope:` anywhere is classified exactly as before. Group 8b pins both directions,
   including the identical-exit-code assertion.
3. **Corpus verified differentially, not absolutely.** The first cut of gate check 3
   flagged 10 "regressions" that were pre-existing exit-2 files (design docs with no
   gate headings — the script has always exited 2 on a 0-check file). Re-measured as a
   before/after diff across all 42 plans: **no verdict changed**. Distribution both
   sides: 20×exit-0, 12×exit-1, 10×exit-2. A differential claim needs a differential
   check.

**Decisions in force:** DEC-005 (this stage extends its authoring half), DEC-003 binding;
DEC-004 not in scope for this stage. No `Supersedes`.

---

## Stage 5: The gate-failure procedure

**Goal:** A failed gate derives the defect class from a declared set and diagnoses it
evidence-first, rather than relying on prose discipline alone.
**Depends on:** Stage 4 gate passing
**Blocks:** none
**Risk:** MEDIUM — edits the procedure this very plan is executed under, so a mistake here
degrades the machinery mid-flight. The contract suite is the guard.
**Rollback:** `git revert` the stage's commits; `executing-plans/SKILL.md` lines 502-545
return to their current text and the contract suite to its current assertions.

### Task 5.1: Generalize-before-repair derivation procedure — Closes BL-025
- **Status:** [x]
- **Depends on:** none (Stage 4 gate is the only precondition)
- **Blocks:** Task 5.2
- **Parallel:** YES
- **Scope:** `executing-plans/SKILL.md` § "If the gate fails" (steps 2, 3, 5)
- **Test:** `python3 planning/skills/executing-plans/tests/test-gate-remediation-contract.py` passes with a new assertion pinning that step 2 names a derivation source (the failing task's `Scope:` field, falling back to an enumeration procedure when absent) and step 3 requires the sweep over it
- **Red-Green max cycles:** 3

Step 2 currently says "name the set the finding quantifies over" with no procedure for
deriving it. With Stage 4 shipped, the set has a home: the task's `Scope:` field. Where a
task declares none, the procedure must say how to enumerate one — that fallback is the
substance of P1, not the citation.

### Task 5.2: Route `no-fafo-debugging` at gate failure — Closes BL-027
- **Status:** [x]
- **Depends on:** Task 5.1
- **Blocks:** Task 5.3
- **Parallel:** NO (blocked by 5.1 — same file, adjacent lines)
- **Scope:** `executing-plans/SKILL.md` § "If the gate fails" step 2, and the Red-Green diagnose step
- **Test:** `grep -c 'no-fafo' planning/skills/executing-plans/SKILL.md` ≥ 1, and the contract suite asserts the reference sits at the diagnosis step specifically — not merely somewhere in the file
- **Red-Green max cycles:** 2

A bare mention anywhere in the file would satisfy a naive grep while changing nothing; the
contract assertion is what makes this real. Step 2 ("identify what caused it") is the slot —
evidence-first diagnosis is what makes generalize-before-repair produce the *right* set
rather than a plausible-looking one.

### Task 5.3: Extend the contract suite to pin both
- **Status:** [x]
- **Depends on:** Task 5.1, Task 5.2
- **Blocks:** none
- **Parallel:** NO (blocked by 5.1, 5.2)
- **Scope:** `planning/skills/executing-plans/tests/test-gate-remediation-contract.py`
- **Test:** `python3 planning/skills/executing-plans/tests/test-gate-remediation-contract.py` passes, and each new assertion demonstrably fails when its clause is deleted from the SKILL (verified by temporary deletion, reverted)
- **Red-Green max cycles:** 3

The delete-and-see-it-fail step is the honest-gates requirement: an assertion never observed
failing is not known to be testing anything.

### Task 5.4: Version bumps and backlog close-out
- **Status:** [x]
- **Depends on:** Task 5.3
- **Blocks:** none
- **Parallel:** NO (blocked by 5.3)
- **Scope:** `planning/.claude-plugin/plugin.json`, `android-dev/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and every version mirror site
- **Test:** `python3 scripts/check-plugin-description-sync.py` exits 0 and the marketplace version matches the bumped plugin versions
- **Red-Green max cycles:** 2

`planning` 0.30.0 → 0.31.0 (Scope: field, gate-failure procedure), `android-dev` 2.0.0 →
2.0.1 (doc-only), marketplace 0.22.0 → 0.23.0. All eight BL entries are removed from
`backlog.md` at close-out via the `backlog` skill, and the commit carries
`Closes BL-020 … BL-027`.

### Stage 5 Gate
- [ ] `python3 planning/skills/executing-plans/tests/test-gate-remediation-contract.py` passes
- [ ] **(judgment)** The `no-fafo-debugging` reference sits at the diagnosis step and changes what an executor does there, rather than being a mention that satisfies a grep. Presence is already pinned mechanically by the contract suite above; *placement and relevance* are what a grep cannot distinguish, so an evaluator reads the step.
- [ ] Full clean test pass (plan-scope — the plan's single full run): `bash scripts/run-tests.sh && python3 scripts/check-doc-coverage.py && python3 scripts/check-frontmatter-budget.py --max 300 && python3 scripts/check-plugin-description-sync.py && python3 scripts/check-usage-tokens.py && python3 scripts/build-capability-index.py && git diff --exit-code capability-index.json`
- [ ] No backlog entry closed by this plan survives in `backlog.md` — `! grep -qE '^## BL-02[0-7] ' /mnt/vault/Portfolio/ai-tools/coder-plugins/backlog.md`
- [ ] **(judgment)** No change contradicts a decision in force (DEC-005, DEC-004, DEC-003; GDEC-SEC-001 consulted, not binding) — in particular Task 3.1 documents the android mount variables without reintroducing a project-specific default. No `Supersedes` citation was made by this plan, so none needs recording. A conformance judgment over a diff; no sweep can prove it.
- [ ] **(judgment)** The behavioral claims this plan's diffs assert — what the runner discovers, what the guard resolves, what the gate procedure requires — each cite the file they were checked against, per DEC-005. An evaluator reads the diff prose against the source; no sweep can verify a citation is *accurate*.

---

**Stage 5 handoff:** Gate green — no remediation rounds. Seven new contract assertions,
each verified to fail when its clause is deleted from the SKILL and the SKILL restored
byte-for-byte afterwards.

**Completed:** 2026-07-26 — commits: df269b8, abdbe43, 4c52ea6, 76a9fad, f2a2dd2, dce029a, eb11fe7, 20baf30, 42150c9, 302c7f7, 45cdb33, d640117

**Closed:** BL-020, BL-021, BL-022, BL-023, BL-024, BL-025, BL-026, BL-027 (all eight).
**Opened during execution:** BL-028 (calibration treadmill), BL-029 (USAGE purpose claim
has no guard), BL-030 (empty-discovery message wording).
**Decisions recorded:** DEC-006 (canonical runner; unrunnable language fails loudly),
DEC-007 (doc guards resolve through capability-index.json). No `Supersedes` was raised.
**Versions:** planning 0.30.0 → 0.31.0, android-dev 2.0.0 → 2.0.1, marketplace
0.22.0 → 0.23.0.

**Post-merge review round (honest-gates).** The first execution ran with **no independent
review** — the Tier-1/Tier-2 dispatches and both goal-evaluator passes were performed inline
by the executing session, which is the bias those dispatches exist to remove. That was an
execution error, not a constraint: a plan mandating dispatched review IS the user's request
for it. On user instruction the reviews were then run properly — four Tier-2 stage reviewers
over the five stage diffs plus one close-out goal-evaluator, each briefed only on goals and
criteria.

**Result: the evaluator returned PASS on all eight backlog items**, and the four code reviews
returned REQUEST CHANGES with **nine Important + two Material findings, zero Critical**. All
eleven were fixed or recorded; none of them was found by the inline pass. The most significant:

1. **`run-tests.sh` hardcoded a one-entry `VALIDATORS` list** while four other tree-wide
   guards existed — including `check-usage-tokens.py`, the guard this very branch added.
   BL-020's defect (an enumerated list silently omitting members) reproduced inside BL-020's
   own fix, in the half nobody thought to generalize. The README's "every validator" was
   therefore false. Validators are now discovered by the `scripts/check-*.py` convention: 1 → 5.
2. **`mapfile -t X < <(find …)` swallowed find's exit status**, so an unreadable subtree
   dropped suites while the runner still exited 0 — the empty-glob guard cannot fire on a
   *short* array. Same defect class, third route. Now captured and failed loudly; verified
   against a real chmod-000 subtree.
3. **The unsupported-language sweep was scoped to `*/tests/*` while discovery walked the
   whole tree**, so a suite that was both in a new home *and* a new language fell through the
   gap between the two scopes. The scopes now match.
4. **`PROSE_ATTRIB` had no plugin-membership check**, so ordinary English — "`thing-expert`
   (an internal agent)" — yielded a claim against a plugin named "internal" and would have
   failed CI on correct prose.
5. **Three new contract assertions were satisfiable by negated restatements** of the exact
   requirement they pinned ("Do not invoke `no-fafo-debugging` here" passed both no-fafo
   checks). Now screened, and verified by *negation* mutation, not only deletion.
6. **`unswept_scopes` accepted only `EXECUTABLE`**, contradicting the class-predicate rule's
   own sanctioned `(judgment)` shape — an advisory wrong on its own criteria.
7. **A false behavioral claim shipped in `docs/USAGE.md`**: "on your confirmation" for
   `create-commit`/`create-pr`, which have no such gate (only `release-tag` does). My earlier
   verification grepped a *different* claim and passed itself.
8. **Two test assertions were vacuous** — one an algebraic identity, one checking a sentinel
   nothing ever wrote. Both rewritten to re-invoke the runner and observe real behavior.

**Completed (post-review):** 2026-07-26 — residual Suggestions recorded as BL-031, BL-032,
BL-033.
