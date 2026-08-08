# Progress state file (live statusline bar)

Mirror execution state to `<repo-root>/.claude/plan-progress.json` so the
shipped statusline renderer (`../scripts/plan-progress.py`) can draw a live
progress bar (`⚙ plan ▐██████░░░░▌ 3/6 (50%) · S2/3 ▶ T2.2 …`). Maintain the
file on every run — it is cheap, and the renderer simply never fires for
users who haven't wired it.

Write the full file (overwrite, don't patch) at each transition:

| When | Write |
|------|-------|
| Preflight starts | `phase: "preflight"` |
| A task starts (incl. re-entering its Red-Green loop) | `phase: "task"`, `stage`, `task` ("2.3"), `task_desc` |
| A stage gate runs | `phase: "gate"`, `stage`, and on a re-run `remediation_round` (+ `remediation_budget` if the plan overrode the default 2) |
| Close-out starts | `phase: "closeout"` |
| A Stop condition halts execution | `phase: "blocked"`, `stage`/`task` if known, `note` (one line, e.g. "cycle budget exhausted") |
| Close-out finishes (last step) | **delete the file** |

Schema (all on one line is fine):

```json
{"plan": "plans/foo-plan.md", "phase": "task", "stage": 2,
 "task": "2.3", "task_desc": "parse config entries",
 "updated": "<ISO-8601 UTC now>"}
```

`plan` is the plan file's path — absolute, or relative to the repo root.
Always refresh `updated` (the renderer marks state older than 12h as stale).

`remediation_round` is optional and only meaningful with `phase: "gate"` — set it
when a gate is being re-run after a failure, so the bar reads
`◆ S2 gate ↻2/2` and a loop that is quietly on its third round is visible rather
than inferred. Omit it on a gate's first run. `remediation_budget` is likewise
optional and only changes the denominator; with neither field the gate renders
exactly as before.
Done/total counts are **not** in the file — the renderer derives them from the
plan's authoritative `Status:` fields, so a forgotten update can never show
wrong progress, only a wrong current-task label. The file is ephemeral session
state: never commit it — during the git bootstrap, ensure
`.claude/plan-progress.json` is gitignored (append it if the repo doesn't
already ignore it). For a master plan, the state file always points at the
**sub-plan** currently executing.

**One-time user setup** (only if asked to wire it): run `/planning:statusline install`.
That command is the invocation — do not hand a user a relative `../scripts/…` path, which
resolves only when the shell's cwd happens to be this file's own directory and fails
everywhere else. The command runs
`python3 "${CLAUDE_PLUGIN_ROOT}/skills/executing-plans/scripts/statusline-install.py"`,
which writes the single `statusLine` entry in `~/.claude/settings.json` pointing at the
shipped `statusline-chain.sh`; that script runs the user's existing statusline first and
appends this renderer's output on the next line when non-empty, both from the same stdin
JSON. `--status` reports what is wired; `--remove` takes it back out.

**What "existing statusline" covers.** The installer preserves a displaced entry as the
chain's base only when it is a plain `bash <script>` invocation, which it records as a
`PLAN_STATUSLINE_BASE=<path>` prefix on the written command. A `node`/`deno`/`bun`
command, a pipeline, or a `bash` call carrying its own arguments cannot be chained
safely: without `--force` the install refuses, and with `--force` the old command is
replaced, echoed to stderr, and left in the timestamped backup. One shape is refused
deliberately even though it parses — a base script that itself runs `plan-progress.py`,
i.e. a hand-written wrapper from before this command existed, because chaining it would
print the bar twice. `--remove` restores a preserved base rather than clearing the key.

**Both subprocesses are time-bounded**, so a base that blocks cannot freeze every redraw.
The bounds differ deliberately: the base defaults to 15s and the renderer to 5s, because a
base legitimately does slow work and bounds *itself* — the widely installed
ClaudeCodeStatusLine makes a `curl --max-time 10` call, so a snug wrapper bound would
truncate a base working exactly as designed. The wrapper exists to catch an *unbounded*
hang, not to second-guess a self-bounded base. Override with
`PLAN_STATUSLINE_BASE_TIMEOUT` / `PLAN_STATUSLINE_BAR_TIMEOUT`. Where neither `timeout`
nor `gtimeout` exists (a stock macOS), both run unbounded rather than not running at all.

**The written pointer resolves the newest installed version at render time**, rather than
freezing today's path. A plugin installs to a version-pinned directory that changes on
every bump, and `statusLine` is not a plugin contribution point — so `/reload-plugins`,
which re-points hooks, MCP and LSP servers, cannot re-point it, and the stale directory is
removed after roughly two weeks. A frozen path would then take the user's *base* statusline
down with it, since the chain script is what invokes the base.

The wiring is **global and one-time** — it applies in every project, not per repo — and it
is the one piece that cannot ship with the plugin: `statusLine` is not a plugin
contribution point (a plugin's `settings.json` supports only `agent` and
`subagentStatusLine`), so exactly one entry must live in the user's global settings. The
installer exists so that entry is generated rather than hand-authored.

Do **not** tell a user to write their own wrapper script. That was the previous
instruction here, and it produced exactly one defect worth remembering: a hand-written
wrapper hard-codes an absolute path to a dev checkout, so it keeps executing that copy
after the plugin is installed somewhere else, and the shipped renderer and the running one
silently diverge. `statusline-chain.sh` resolves the renderer as its own sibling for that
reason, so it carries no hard-coded checkout path. (It does default the *base* statusline
to `$HOME/.claude/statusline.sh` — an absolute path, but an overridable default rather
than a baked-in location.)
