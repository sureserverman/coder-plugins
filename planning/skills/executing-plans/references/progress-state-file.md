# Progress state file (live statusline bar)

Mirror execution state to `<repo-root>/.claude/plan-progress.json` so the
shipped statusline renderer (`scripts/plan-progress.py`) can draw a live
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

**One-time user setup** (only if asked to wire it): point `statusLine` in
`~/.claude/settings.json` at a wrapper that feeds the same stdin JSON to the
user's existing statusline command first, then to
`<planning-plugin>/skills/executing-plans/scripts/plan-progress.py`, appending
its output as an extra line when non-empty. The renderer prints nothing when
no plan is executing, so it never disturbs the normal statusline.
