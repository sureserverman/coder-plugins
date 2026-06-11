# rust-dev — deterministic lane

This `scripts/` directory is rust-dev's **deterministic lane**, vendored from
the plugin-dev determinism kit. It encodes one rule:

> **Mechanical, decidable checks belong in scripts. Semantic judgment belongs to
> the LLM.** Scripts flag; the model decides and writes.

The lane runs against a **target Rust project** (the code being authored,
reviewed, or refactored), not against this plugin's own structure — structure
validation is plugin-dev's job (`validate-plugin.sh`, run from outside).

## Layout

```
scripts/
├── lib/findings.sh       # shared finding accumulator + JSON contract (from plugin-dev; do not fork)
├── validate.sh           # orchestrator — discovers and runs every validate-*.sh, merges, prints a verdict
├── validate-cargo.sh     # Cargo.toml / rust-toolchain.toml / Cargo.lock invariants
├── validate-safety.sh    # regex candidates for the house rules over .rs sources
└── stack-report.sh       # deterministic Stack Report (facts, not findings — outside the verdict)
```

Run the whole lane:

```bash
bash scripts/validate.sh <rust-project-root> [--json]
```

`--json` emits the contract (consumed by rust-expert and the slash commands);
without it, a human report. All scripts no-op cleanly (info finding) when the
root contains no Cargo.toml / `.rs` sources.

## Rule ids

`validate-cargo.sh` — hard invariants are `error`, shoulds are `warn`:

| Rule | Severity | Decides |
|---|---|---|
| `cargo-manifest-parse-error` | error | Cargo.toml / rust-toolchain.toml fails TOML parse |
| `cargo-invalid-edition` | error | edition not in 2015\|2018\|2021\|2024 |
| `cargo-edition-msrv-mismatch` | error | edition requires newer MSRV than rust-version |
| `cargo-workspace-member-missing` | error | declared member path has no Cargo.toml |
| `cargo-missing-edition` | warn | no edition (silently defaults to 2015) |
| `cargo-missing-rust-version` | warn | MSRV unspecified |
| `cargo-wildcard-dependency` | warn | dependency version `"*"` |
| `cargo-workspace-glob-empty` | warn | member glob matches nothing |
| `cargo-lockfile-missing` | warn | binary crate without Cargo.lock |
| `cargo-toolchain-invalid-channel` | warn | toolchain channel not a known form |
| `cargo-edition-2015` | info | migration nudge |
| `cargo-no-manifest` | info | nothing to validate |

`validate-safety.sh` — all source-pattern rules are **candidates** (`warn`,
never `error`): the regex points, rust-expert confirms and fixes.

| Rule | House rule | Flags |
|---|---|---|
| `rust-unsafe-missing-safety-comment` | 1 | `unsafe {` / `unsafe impl` with no `// SAFETY:` within 3 lines |
| `rust-sync-lock-in-async-candidate` | 2 | `std::sync::Mutex/RwLock` in a file containing `.await` |
| `rust-unbounded-channel` | 3 | `unbounded_channel()` / `::unbounded(` |
| `rust-box-dyn-error-in-pub-api` | 4 | `pub fn` returning `Box<dyn …Error…>` |
| `rust-unwrap-outside-tests` | 5 | `.unwrap()` / `.expect(` outside main.rs/build.rs/tests/benches/examples/`#[cfg(test)]` |
| `rust-serde-missing-deny-unknown` | 12 | `derive(Deserialize)` without `deny_unknown_fields` nearby |
| `rust-no-sources` | — | info: nothing to scan |

`stack-report.sh` is not a validator: it emits the project's Stack Report
(edition, MSRV, toolchain, workspace shape, runtimes, frameworks, test layout,
risk-surface counts, lockfile, CI cargo invocations) as JSON or text. It is
deliberately not named `validate-*.sh` so the orchestrator excludes it.

## The JSON contract

Every `validate-*.sh`, with `--json`, prints:

```json
{"validator","target","summary":{"errors","warnings","info"},
 "findings":[{"severity":"error|warn|info","rule","category","path","line","message"}],
 "verdict":"pass|pass-with-warnings|fail"}
```

Exit code: `1` if any error, else `0` (`2` usage, `3` jq/python3 missing).

## The boundary

Only decidable checks live here — parse, field presence, enum, count, regex,
cross-file consistency. Whether a flagged `.unwrap()` has a documented-panic
contract, whether a lock is actually held across an await, what the error enum
should look like — that is judgment and lives in `rust-coding` / `rust-expert`,
which run this lane and consume its JSON instead of re-deriving the rules.

Keep rule ids stable and kebab-case; the agents key off them. Refresh
`lib/findings.sh` / `validate.sh` with plugin-dev's `install-kit.sh --force`,
never by hand-editing.
