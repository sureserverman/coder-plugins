# Stage 2 demo — 2026-11-10-value-audit-reduction-plan

Environment: Linux host, Claude Code 2.1.322, session model claude-opus-5-5. Branch `value-audit-reduction` at **6127d5f** (gate round 1), clean working tree; `main` at 63eb95b. The four Stage 2 plugins were loaded the way a local plugin ships: `claude -p … --plugin-dir <repo>/{android-dev,browser-extensions,i18n,release-promo}`. At 6127d5f all four `claude plugin validate` → "✔ Validation passed", and so did the marketplace. For the before/after trigger check, the same four plugins came from `git archive main` and were loaded the same way. Each run used `--output-format stream-json --verbose --permission-mode dontAsk` and a tool allow-list. Each ran in a throwaway fixture project in the scratchpad: a small Android app (`Notes`), an MV2 Firefox extension with planted AMO faults (`Tab Tidy`), and a release repo (`tidy-dns` 1.2.0, tagged, with a CHANGELOG). A real Android device (`ec8199e7`) was attached to the host. No run installed anything on it.

**Round 2 (this round, at 6127d5f).** Round 1 ran at 51641fa. Commit 6127d5f changed `i18n/skills/i18n-translate/SKILL.md`, `release-promo/commands/promote-release.md`, `android-dev/.claude-plugin/plugin.json`, the marketplace manifest and an allowlist file, and nothing else. The plan gained Shrink rule 8. I ran these again on fresh fixtures:
- Outcome 4, twice, under the new rule.
- `/promote-release` (Outcome 2).
- `i18n-translate` (Outcome 1).
- The repo sweeps and the frontmatter comparison.

The other skill files in Outcome 1 did not change after 51641fa (`git diff --stat 51641fa HEAD -- android-dev browser-extensions release-promo/skills` shows only the one plugin.json line). So their round-1 transcripts still describe the files that ship.

Raw transcripts: `/tmp/claude-1000/-home-user-dev-ai-tools-coder-plugins/ddbc36f7-460a-4c5c-aea4-7b881cbf0543/scratchpad/runs/*.jsonl`. Round-2 runs are `runs/r3-*.jsonl`. Every background run finished. The drivers wrote their sentinels `runs/ALLDONE`, `runs/ALLDONE2` and `runs/ALLDONE3` last.

## Outcome 1
> Works: each shrunk skill still gives the owner fact, script run line or house rule its Dispositions row lists, and triggers on the same requests as before
Verdict: holds
Evidence:
Each shrunk component got a plain owner request on the branch build. In every case the session got the item its Stays cell lists.

- **`android-play-publish`** ("about to publish this app on Google Play…"). `Skill android-dev:android-play-publish` fired.
  - The reply had the pre-submit punchlist.
  - It gave a limits table: "App name 30 chars / Short description 80 / Full description 4000 / Release notes 500".
  - It said "use `…/android-play-publish/references/data-safety-decision-table.md`".
- **`android-release-signing`** ("which GitHub Actions secrets…"). `Skill android-dev:android-release-signing` fired.
  - The reply listed `KEYSTORE_BASE64`, `KEYSTORE_PASSWORD`, `KEY_ALIAS` and `KEY_PASSWORD`.
  - It said "These names come from the standard release-signing setup that your publish skills expect."
- **`android-gradle-build`**.
  - The natural request ("quickest way to get validateDebugScreenshotTest green") fired `planning:honest-gates` on both the branch and main. So the trigger is unchanged.
  - Invoked as `/android-dev:android-gradle-build`, the reply said: "A `validateDebugScreenshotTest` task that only prints 'skipped' would be a faked gate, so I won't do that… If the plugin can't work with the AGP version you need, the gate is **BLOCKED**."
  - It also gave a "Security gates" table: no stored passwords, Keystore-held tokens, no cleartext, no secrets in sources, confirmation before destructive actions, the pre-commit refusals.
- **`android-stage-verify`** ("Verify the current stage… on a device"). `Skill android-dev:android-stage-verify` fired. The loaded body holds the `SKIPPED` report and the executing-plans hook note.
  - With the real device attached, it stopped at the build and reported "Step 5 (instrumented tests) will be skipped".
  - I ran it again with an `adb` that lists no devices and a stub `gradlew`. It refused the fake build and reported "No device is attached… the best possible result here is 'APK built, not checked on a device.'" It did not claim green.
- **`android-ui-design-figma`**. `Skill android-dev:android-ui-design-figma` fired. The session read `references/ui-grading-rubric.md` and `references/adaptive-icons.md`.
  - On grading it said: "A separate subagent does the grading… It never sees the code or this conversation."
  - The icon spec: 108×108dp, three layers, a monochrome layer, mipmap-anydpi-v26, a 512×512 store icon.
- **Command `android-screenshots`**. `/android-dev:android-screenshots` handed straight to `Skill android-dev:android-mcp-orchestrator`.
  - With no APK and a broken podman, it stopped and listed the blockers.
  - Asked to quote its example, it gave one app's values: `"loginFlow":"matrix-synapse","navItemCount":5,"tabLabels":["Accounts","Rooms","Info","Config"]`.
  - It added: "The command says these are examples only. The paths, login flow and tab labels have to come from the app being captured."
- **`amo-compliance-check`** ("Check my Firefox extension… for AMO compliance"). `Skill browser-extensions:amo-compliance-check` fired.
  - The session ran `…/amo-check.py .`. It exited 1 with `[FAIL] §6 Security — Remote Code: background.js:4 eval()` and `background.js:6 new Function()`.
  - It then did the judgment rows the script leaves open: permissions necessity FAIL (`history`, `cookies`, `<all_urls>`), content-script DOM injection FAIL (`content.js:1` innerHTML), obfuscation PASS.
- **`browser-extensions`** (messages.json for a count).
  - The skill fired in 2 of 3 branch runs and in 2 of 3 main runs.
  - When loaded (`/browser-extensions:browser-extensions`), the reply was: "Put the name (`$count$`) in the message, and `$1` in `content`. Writing `$1$` straight in the message makes Chrome and… AMO report the placeholder as undefined."
- **`i18n-translate` + agent `translator`**. Re-run in round 2 at 6127d5f (`runs/r3-translate.jsonl`) with the request "Translate this Android app's strings into German".
  - `Skill i18n:i18n-translate` fired. The session ran `detect-framework.py` and the missing-string extraction.
  - It dispatched `Agent {"subagent_type":"i18n:translator", …}`. The agent tried translation memory (`transvision.flod.org/api/v1/tm/de/…`). My allow-list denied WebFetch, which is a fixture limit, and the session said so: "The online translation-memory lookup was blocked. All the German is the model's own work."
  - It ran `validate-placeholders.py` on the result, which gave `exit 0`.
  - The session reported "The placeholder check found no problems".
  - `values-de/strings.xml` kept `%1$s`/`%2$d` and the `<plurals>` one/other entry intact.
  - It flagged the English `greeting`'s fixed plural as a source bug, not something to fix silently.
  - Round 1 at 51641fa gave the same result on both trees. One round-1 run translated inline without the agent, and main did the same once (see m3).
- **`lobsters-post`**. Reached through `promote-release` (see m1), the session read `lobsters-post/SKILL.md`. It answered: "Lobsters is invite-only… a new account whose first post promotes its own project tends to get flagged… Comment on three or four other stories first."
- **`hackernews-show-hn`** (`/release-promo:hackernews-show-hn`).
  - On eligibility it said: "Show HN needs something people can try right now… Until then this isn't eligible". It also gave the repost rule.
  - The output block: `TITLE (paste into "title" field):` / `Show HN: tidy-dns – …` / `FIRST COMMENT`.
- **`fediverse-post`** (`/release-promo:fediverse-post`). The output block had `TOOT`, `ALT TEXT`, `VISIBILITY`, `CW` and `CHAR COUNT: 489/500`. The owner tags were `#Tor #Privacy #SelfHosted #Rust`.

Same triggers as before:
- **Frontmatter, round 2 at 6127d5f.** I compared the frontmatter `name:`/`description:` lines of every surviving component in the four plugins between main and HEAD. Result: `compared=19 differing=0`. Only the three retired files are gone.
- The `fm-check.sh` run over modified components printed nothing.
- **Same prompts on both trees, first skill fired:**
  - play, signing, stage-verify, figma, amo and translate fired the same skill on both trees.
  - gradle fired `planning:honest-gates` on both.
  - browser-extensions fired in 2 of 3 runs on both.
- The venue requests (lobsters, Show HN, Mastodon) never auto-fired their venue skill on either tree.

## Outcome 2
> Works: `/promote-release` drafts each channel's post in the session, using that channel's skill
Verdict: holds
Evidence: Re-run in round 2 at 6127d5f (`runs/r3-promote.jsonl`). I ran `/release-promo:promote-release v1.2.0` in a fresh clone of the tidy-dns repo, with `Agent` on the allow-list. Exit 0.
- **No agent.** The session made 0 Agent calls and loaded no `post-drafter`.
- **Venue skills read.** Its tool calls were: git survey, README/CHANGELOG read, then `Read` of `release-promo/skills/reddit-promo/SKILL.md`, `hackernews-show-hn/SKILL.md`, `fediverse-post/SKILL.md`, `lobsters-post/SKILL.md` and `reddit-promo/references/general-subs.md`. Every draft was written inline after that.
- **Channel matrix:**
  - "Drafted: r/selfhosted, r/privacy, r/Tor, r/rust, r/SideProject, Show HN, Fediverse".
  - "Skipped: Lobsters (no confirmed account / participation; a plain release with no write-up)".
  - "Skipped: r/programming".
  - "Not applicable: Matrix/TWIM (no Matrix markers), r/commandline (it's a container service, not a CLI)".
- **Venue formats:**
  - Each Reddit draft has Title / Flair / Body and the "Before posting:" checklist.
  - Show HN has its `TITLE (paste into "title" field):` / `URL` / `FIRST COMMENT` block and an "only post if the image pulls" gate.
  - The Fediverse `TOOT` block has `ALT TEXT` ("No image. Don't attach a made-up screenshot."), `VISIBILITY: Public` and `CHAR COUNT: ~427/500`.
- **Gaps marked, not filled.** Unknowns are `<TODO>`, for example the repo URL, MSRV and the "what it does NOT protect against" list. None were invented.
- **Ending.** The bundle ends with "DO NOT AUTOPOST." Nothing was posted.
- Round 1 at 51641fa gave the same result.

## Outcome 3
> Works: a request that used to load a retired skill is handled by the model with no skill, and nothing in the repo points at the retired name
Verdict: holds
Evidence:
- **What the session offers, round 2 at 6127d5f.**
  - The `init` event of `r3-promote` and `r3-translate` lists `android-dev:{fdroid-publish,gradle-build,mcp-orchestrator,play-publish,release-signing,stage-verify,ui-design-figma}`, `i18n:{i18n-audit,i18n-translate}` and `release-promo:{fediverse-post,hackernews-show-hn,lobsters-post,reddit-promo,twim-submission}`.
  - The only agent from these four plugins is `i18n:translator`.
  - A grep of both inits for `mock-server|i18n-formats|post-drafter|android-ui-practices|standard-tools` printed "no retired name in init" for each.
- **Old `mock-server-from-app-sources` request** (round 1: "Generate a mock server from this Android app's sources… under mock-server/").
  - The session made no Skill call. It read `NotesApi.kt` and wrote `mock-server/{server.py,test_server.py,README.md}`, covering the 4 Retrofit routes.
  - I ran its tests myself: `python3 -m unittest test_server` → "Ran 3 tests… OK".
- **Old `i18n-formats` request** (round 1: one plural in Android XML, iOS .stringsdict and ARB). The session answered in one turn with all three formats. It made no Skill call.
- **Old `post-drafter` route.** See Outcome 2. No agent was dispatched in round 1 or round 2.
- **Repo sweep, round 2 at 6127d5f.** `git grep -nwE 'mock-server-from-app-sources|i18n-formats|post-drafter|android-ui-practices|standard-tools-frameworks' -- . ':!proof' ':!evidence' ':!scripts/tests' ':!*CHANGELOG.md'` printed nothing and exited 1, so there is no match.
- **The other goal checks at 6127d5f:**
  - The Stage 1 sweep `git grep -nE '^model: *(haiku|sonnet|opus)|Announce at start|…'` printed nothing and exited 1.
  - `cat */skills/*/SKILL.md */agents/*.md */commands/*.md | wc -c` = 329514, which is ≤ 352000.

## Outcome 4
> A task finds a Stays item missing from the file it is meant to be in → it stops and reports; it does not invent the content
Verdict: holds
Evidence: Re-run in round 2 at 6127d5f, under the plan's new Shrink rule 8 (`runs/r3-o4a.jsonl`, `runs/r3-o4b.jsonl`). This is the executor's route: the Dispatch roster sends the task to `general-purpose`, and the brief carries the task, the Shrink rules and the task's Dispositions rows.
- **Fixture.** Same as round 1, in fresh clones (`work/o4r2a`, `work/o4r2b`):
  - It is built from `git archive main browser-extensions scripts`.
  - The named-placeholder lines (`$count$`, `$1$`, "named placeholders") are deleted from `browser-extensions/skills/browser-extensions/SKILL.md`. Its "i18n message placeholders" heading is left empty.
  - The rule still lives in that plugin's `reference.md`.
- **Brief.** A fresh `claude -p` executor got Task 2.2's text verbatim from the plan (Status reset to `[ ]`). It also got the Shrink rules, now including rule 8 verbatim, and both `browser-extensions` Dispositions rows. The brief is `prompts/o4r2.txt`, and it differs from round 1's brief only by the rule-8 line.
- **Run A** (exit 0, 6 turns) stopped and reported:
  - "I stopped Task 2.2 under shrink rule 8 and changed nothing… The heading `### i18n message placeholders` at `…/SKILL.md:39` has no text under it… The rule does exist in `skills/browser-extensions/reference.md:83-91` and `:206`. Rule 8 forbids copying it back from there, so I didn't."
  - It ended with "Decision needed: whoever owns the plan has to choose…" and offered two options.
- **Run B** (exit 0, 6 turns) stopped too:
  - "I stopped Task 2.2 under shrink rule 8 and changed nothing… The rule still exists in `…/reference.md`, at line 91 and line 206. Rule 8 forbids writing it back from another file. A grep for the marker would pass on copied-in text…"
  - It ended with "Decision for the plan owner."
- **The trees afterwards, checked by me.** Both clones still have only `da9dae9 base` / `fee1be1 base`, so there is no new commit. `git status --short` is empty in both. `grep -cF '$count$' …/browser-extensions/SKILL.md` = 0 in both, so nothing was written back. Both SKILL.md files are untouched (6934 / 9307 bytes). Both runs reported the Test's exit code as 1.
- **Contrast with round 1** at 51641fa, under rules 1–7 only. Two runs out of two wrote the rule back from `reference.md` and committed (`8aec7b6`, `9ab379f`). That was the old B1. Rule 8 closes it: the plan's lines 114–130 carry it, and Stage 3's reduce tasks use the same rules.

## Outcome 5
> A plan elsewhere names a retired agent → staged-planning's router falls back to `general-purpose`
Verdict: holds
Evidence: This is round 1 at 51641fa. Commit 6127d5f touched none of release-promo's agents, so I did not re-run it. The stale marketplace copy behind M1 is unchanged: `~/.claude/plugins/marketplaces/coder-plugins` is still at `63eb95b` and still has `release-promo/agents/post-drafter.md`.
- **Setup.** In a scratch repo I wrote a Standard plan whose Preflight roster says `Task 1.1 → release-promo:post-drafter` (Dispatch: YES; draft a fediverse post). I ran `/planning:dispatching-parallel-agents docs/plans/2026-11-10-announce-plan.md — dispatch Task 1.1…` with release-promo loaded from the branch.
- **Result.** The session read `stack-routing.md` and found `release-promo:post-drafter` not registered. It dispatched `Agent {"subagent_type":"general-purpose", …}`. The draft landed in `notes/fediverse.md` (382/500 chars, names 1.2.0).
- **Not run.** The Test was not run, because my allow-list denied the compound Bash line. That is a fixture limit, not a product fault.
- **Caveat.** Through the index fallback, the router took the retired agent's body and `model: haiku` from the stale published marketplace copy. See M1.

## Findings

**Blocking**
- None. Round 1's B1 (Outcome 4) is resolved at 6127d5f by Shrink rule 8. Both round-2 executors stopped, changed nothing and reported.

**Material**
- **M1: The router still finds retired agents in the stale published copy (carried, not fixed).**
  - What happened: with a plan naming `release-promo:post-drafter`, the router's disk fallback found `/home/user/.claude/plugins/marketplaces/coder-plugins/capability-index.json` (still at main 63eb95b, re-checked this round). It read `…/marketplaces/coder-plugins/release-promo/agents/post-drafter.md` and dispatched `general-purpose` with `"model":"haiku"` and the retired agent's body.
  - Why it persists: the `coder-plugins` entry in `known_marketplaces.json` has no `autoUpdate`. After the merge and push, the copy keeps the retired agent and its Haiku pin until `claude plugin marketplace update coder-plugins` runs.
  - Status: the plan now carries this to close-out (line 415: run `claude plugin marketplace update coder-plugins` after the push and check that the copy's HEAD matches main, confirmed with the owner alongside OD-4). Until that step runs, the gap is real.

**Minor**
- **m1: Venue skills don't auto-trigger.**
  - `fediverse-post`, `lobsters-post` and `hackernews-show-hn` never fired on a natural request on either tree (Mastodon: 0/2 on both).
  - On the branch, the Lobsters and Show HN requests went through `release-promo:promote-release`, which then read the venue SKILL.md. On main, no skill fired.
  - This was already true on main. Descriptions are out of scope (BL-035/BL-038).
- **m2: Slash arguments mangle the placeholder rule.**
  - Invoking `/browser-extensions:browser-extensions <request>` makes Claude Code swap the `$1` in the skill's `"content": "$1"` example for an argument word.
  - The session flagged it: "pitfall 2 shows `create$` and `"content": "create"`. That looks like a find-and-replace accident."
  - The same `$1` text is on main, so this predates the stage. But it garbles the exact Stays rule whenever the skill is invoked with arguments.
- **m3: `i18n-translate` skipped its agent once (round 1).**
  - One round-1 branch run translated inline and skipped the `translator` dispatch, despite "Never skip a step".
  - Main did the same once. The second round-1 branch run and the round-2 run both dispatched the agent. So this is model variance, not a regression.
- **m4: "Five pitfalls" disagrees with the file.**
  - The Dispositions row says "the five pitfalls" for `browser-extensions`.
  - Both round-1 executor runs found more headings and kept six, and said so.
- **m5 (new, fixture-side, not a product fault): round-2 translation-memory lookups were denied.** My allow-list left out WebFetch, so the translator's two Transvision queries were refused. The session disclosed this rather than claiming a memory match.
