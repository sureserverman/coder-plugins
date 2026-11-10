# Stage 1 demo — 2026-11-10-value-audit-reduction-plan

Environment: (see below)

Fill in Verdict and Evidence under each Outcome. Do not edit the quoted lines.

## Outcome 1
> Works: a publish, promo or release skill states the current store or venue rule with the date it was checked and its source
Verdict: holds
Evidence:
Round 2, at HEAD ca3c9d9. Route: real `claude -p` sessions (Claude Code 2.1.322), all repo plugins loaded by `--plugin-dir`, cwd an unrelated scratch folder.
- Model-invocable skills were loaded with the Skill tool (session `r2-o1`).
- The five release-promo skills were run the way the owner runs them: `/release-promo:<skill> <ask to quote every venue rule with its date and source>` (sessions `r2-rp-*`).
- Each dated fact was then checked against its live page today (curl, 2026-11-10, all HTTP 200).

What the sessions quoted, and what the live page says:
- **android-play-publish:** "API 36 (Android 16) for new phone and tablet apps and updates since 2026-08-31 (Wear OS and Automotive 35, TV and XR 34) (checked 2026-11-10, https://support.google.com/googleplay/android-developer/answer/11926878)". The punchlist line says "`targetSdk ≥ 36` … checked 2026-11-10" with the same URL. Live page: "Starting August 31, 2026: New apps and app updates must target Android 16 (API level 36) … except for Wear OS, and Android Automotive OS apps, which must target Android 15 (API level 35) … Android TV and Android XR apps … Android 14 (API level 34)". Matches.
- **android-fdroid-publish:**
  - "F-Droid only uses metadata files from the latest release (checked 2026-11-10, https://f-droid.org/docs/All_About_Descriptions_Graphics_and_Screenshots/)". Live: "F-Droid will only use metadata files from the latest release."
  - The `Binaries:` + `AllowedAPKSigningKeys` skip rule is dated 2026-11-10 and cites f-droid.org/docs/Reproducible_Builds/.
- **browser-extensions:** "AMO: Follow Mozilla's add-on policies (checked 2026-11-10, https://extensionworkshop.com/documentation/publish/add-on-policies/)". The live page title is "Add-on Policies | Firefox Extension Workshop".
- **twim-submission:** the room, the bot mention, the 16:00 Paris deadline and the ⭕ media rule are each dated 2026-11-10, citing https://matrix.org/twim-guide/. The room is `#thisweekin:matrix.org`. Live guide: "participate in the #thisweekin:matrix.org Matrix room".
- **fediverse-post:** "Every link counts as 23 characters toward the 500-char limit … (checked 2026-11-10, https://docs.joinmastodon.org/user/posting/)". Live: "counted as 23 characters regardless of length".
- **hackernews-show-hn:** "for a link with comments, the HN FAQ says to submit the link, then add a regular comment" is dated 2026-11-10 and cites newsfaq.html. Live FAQ: "just submit the link, then add a regular comment."
- **lobsters-post:** "Tags come from a predefined list; lobste.rs/about names no per-story tag cap (checked 2026-11-10, https://lobste.rs/about)". The live page's tag sentences give no cap.
- **release-tag:** "Trailer is optional; when used, it follows the session's own commit attribution, not a fixed model name."
- **reddit-promo:** no line has a date or a source. This is the OD-8 owner exception (see Outcome 5).

Residuals: other store facts are still undated (see Findings).

## Outcome 2
> Works: a skill that names a bundled script names a path that resolves from any project directory
Verdict: holds
Evidence:
Session `r2-o2`, cwd `elsewhere2`, an unrelated scratch folder holding `ext/` (a manifest) and `bin/clean.sh`.
- It loaded 13 components, among them:
  - android-mcp-orchestrator, android-ui-design-figma and the android-screenshots command
  - amo-compliance-check, github-workflow-audit, bash-script-audit
  - mac-package, deb-package, android-stage-verify, android-release-signing, android-gradle-build
  - rust-coding, i18n-audit
- It listed every script path the loaded text names and ran `test -e` (and `command -v` for bare names) from that directory.

What it found:
- **Run paths:** all 16 are absolute after loading, for example `/home/user/dev/ai-tools/coder-plugins/browser-extensions/scripts/validate.sh`. All 16 print EXISTS. They cover android-mcp-orchestrator ×4, amo-check.py, browser-extensions, git-github and rust-dev validate.sh, i18n validate.sh, audit-workflows.py, validate-workflows.sh, audit.sh, validate-deb.sh and the three i18n-audit .py files.
- **The round-1 Blocking is gone.** The loaded amo-compliance-check text now reads: "via `/home/user/dev/ai-tools/coder-plugins/browser-extensions/scripts/validate.sh` (which runs `validate-amo.sh`, a thin wrapper over `amo-check.py`). Run `bash /home/user/dev/ai-tools/coder-plugins/browser-extensions/scripts/validate.sh <extension-dir> --json`". `validate-amo.sh` is now named only as what the rooted script runs. It is no longer a command to type.
- **Other bare names** are in the same position: `validate-cargo.sh`, `validate-safety.sh`, `stack-report.sh`, `validate-catalog-diff.sh` and `validate-placeholders.sh`. Each sits in a prose sentence after a rooted command, for example rust-coding's `bash "/home/user/dev/ai-tools/coder-plugins/rust-dev/scripts/validate.sh" <project-root> --json`.
- **Relative paths** (`scripts/postinstall`, `./gradlew`) are project files the skill makes in the user's project, not bundled scripts.

Run from that directory exactly as written, each worked:
- `bash …/browser-extensions/scripts/validate.sh ./ext --json`: exit 0, `"warnings":1`, rule `amo-manifest-conditional`.
- `amo-check.py ./ext`: exit 0, "[WARN] §2 Manifest Conditional: browser_specific_settings.gecko.id is recommended".
- `audit.sh ./bin/clean.sh`: exit 0.
- `audit-workflows.py ./`: exit 0, "actions/checkout@v2: outdated (latest major v7)".

The build-readiness-check sessions also ran `bash "/home/user/dev/ai-tools/coder-plugins/infra-build/scripts/validate.sh" "$PWD" --json` from scratch projects (Outcome 3). It worked.

## Outcome 3
> Works: `build-readiness-check` passes a project whose `mac/Makefile` has `pkg`, and warns, naming `pkg`, on one that lacks it
Verdict: holds
Evidence:
Fixtures:
- `proj-pkg/mac/Makefile` has `payload:` and `pkg: payload`.
- `proj-nopkg/mac/Makefile` has `payload:` and `build:`.
- Both have `mac/payload/usr/local/bin/tool`.

Both were run as `/infra-build:build-readiness-check`, typed into a `claude -p` session in that project's directory.
- **proj-nopkg (`r2-o3-nopkg`):** the session ran `bash "/home/user/dev/ai-tools/coder-plugins/infra-build/scripts/validate.sh" "$PWD" --json`.
  - Validator: `"warnings": 1`, `"rule": "mac-makefile-target"`, `"message": "mac/Makefile has no 'pkg:' target (the workflow runs make pkg)"`, `"verdict": "pass-with-warnings"`.
  - Report: "missing: top-level `pkg:` target in mac/Makefile (it only has `payload:` and `build:`; the workflow runs `make -C proj-nopkg/mac pkg`)". Next step: "mac-package to add the `pkg:` target".
- **proj-pkg (`r2-o3-pkg`):**
  - Validator: `"warnings": 0`, `"verdict": "pass"`. No mac-makefile-target finding.
  - Report: "OK: `mac/Makefile` has a top-level `pkg:` target."

## Outcome 4
> Works: a dispatched agent runs on the session's model, and a skill starts without an announce line
Verdict: holds
Evidence:
**Agents.** Sessions `r2-o4-haiku` (`--model haiku`) and `r2-o4-sonnet` (`--model sonnet`) each dispatched all six shipped agents with no `model` field in the Agent call: business:market-researcher, game-dev:game-design-expert, git-github:code-reviewer, i18n:translator, release-promo:post-drafter and rust-dev:rust-expert.
- **haiku:** every subagent message in stream-json has `model: claude-haiku-5-5` (10 messages). modelUsage lists only `claude-haiku-5-5`. Five agents replied "READY — claude-haiku-5-5".
  - git-github:code-reviewer gave no report. Its own messages were "READY claude-haiku-5-5", on claude-haiku-5-5. It then refused to call the hand-back tool, citing my prompt's "Do not use any tools".
  - This failure comes from my test prompt, not the product. Its model is still the session's.
- **sonnet:** every subagent message has `model: claude-sonnet-5-5` (6 messages). modelUsage lists only `claude-sonnet-5-5`. All six replied READY with `claude-sonnet-5-5`.

**Announce lines.** Three skills were invoked the way the owner invokes them.
- `/git-github:release-tag cut v1.2.0` in a tag repo: the first output is a Bash tool call (`git rev-parse …`). The first text is "Draft for your approval: …". No tag was created (`git tag -l` is empty).
- `/android-dev:android-stage-verify`: the first text is "I'll start with Step 1, the debug build. First I'll check that this is an Android project."
- `/business:assess`: the first text is "I'll start by running the scanner and looking at the current directory to find the project."
- No main-session text matches "I'm using … skill" or "Announc".

**Goal sweep.** At ca3c9d9, `! git grep -nE '^model: *(haiku|sonnet|opus)|Announce at start|Claude (Haiku|Sonnet|Opus) [0-9]|twim-submissions|targetSdk ≥ 35' -- '*/agents/*' '*/skills/*' '*/commands/*'` exited 0.

## Outcome 5
> A live source cannot be reached → the task stops and names the fact; nothing is rewritten from memory
Verdict: holds
Evidence:
- **The source is unreachable today.** `curl -A 'Mozilla/5.0'` returned 403 on https://www.reddit.com/r/rust/ and on https://old.reddit.com/r/rust/.
- **The stop and the named fact are in the plan.** They are a recorded stop, not one seen live.
  - OD-8 (owner, 2026-11-10: "3"): "Reddit could not be reached, so `reddit-promo`'s flair facts stay as written, undated".
  - Task 1.1's amendment note: "www.reddit.com and old.reddit.com unreachable from this host".
- **Nothing was rewritten.**
  - `git diff --quiet main HEAD -- release-promo/skills/reddit-promo` exited 0.
  - Run as `/release-promo:reddit-promo …` (session `r2-rp-reddit-promo`), the skill still shows the old flair table, for example r/rust "yes | self | `project`, `announcement`" and r/selfhosted "yes (`Release`, `Self Promo`)".
  - The session reported: "None of these rules carries a "checked" date or a source URL, in `SKILL.md` or in either reference file."
  - No fact from memory was given a checked date.

## Outcome 6
> A live source contradicts the audit → the source wins and the text follows it, with the date
Verdict: holds
Evidence:
Each case was re-fetched today. The skill text a session loads now follows the live page, dated 2026-11-10.
- **Play target API (audit said 35):** the skill says "API 36 (Android 16) … since 2026-08-31 (Wear OS and Automotive 35, TV and XR 34)". Live: API 36, with Wear/Automotive at 35 and TV/XR at 34. The skill also took up the live page's per-form-factor split.
- **TWIM room:** `#twim-submissions:matrix.org` is gone. The skill says `#thisweekin:matrix.org` and that "`#twim:matrix.org` is the general TWIM discussion room, not the submission room". Live guide: "#thisweekin:matrix.org".
- **Mastodon link length (suspected):** the skill gives 23 characters, dated, citing docs.joinmastodon.org. Live: "counted as 23 characters regardless of length".
- **Show HN text (suspected):** the skill now dates only what the FAQ says ("submit the link, then add a regular comment", newsfaq.html). It says showhn.html "does not say whether Show HN takes text", so a blank text field is a convention. Live FAQ: "just submit the link, then add a regular comment."
- **Lobsters tag cap (suspected):** the skill says "lobste.rs/about names no per-story tag cap", dated. The live page's tag section gives no cap.
- The goal sweep finds no `twim-submissions` and no `targetSdk ≥ 35` in any component.

## Findings

**Blocking**
- None. The round-1 Blocking (amo-compliance-check's bare `validate-amo.sh <extension-dir> --json` command) is fixed. The only run command is now the rooted `validate.sh <extension-dir> --json`. Run on `./ext` from a scratch directory, it reported the gecko.id warning.

**Material**
- None.

**Minor**
1. Many store and venue facts in the in-scope skills are still undated and unsourced:
   - Play: the $25 fee, the 14-day / 12-tester rule (linked but undated), and the 30/80/4000/500 character limits.
   - HN: the 80-char title cap.
   - Mastodon: the 500-char default and the 40 MB / 60 s media limits.
   - Lobsters: the ~100-char title.
   - TWIM: the 60–250 word length.

   These were outside the audit's line list, so this is not a Stage 1 defect. It does leave room for drift.
2. hackernews-show-hn's §1 eligibility rules cite `news.ycombinator.com/showhn.html` with no scheme and no date.
3. lobsters-post does not mention a live rule from lobste.rs/about: "New users (first 70 days) are not allowed to submit self-promo". The skill's account check speaks of commenting first, not the 70-day bar. This predates Stage 1.
4. rust-coding says "`stack-report.sh` produces the project Stack Report. See `scripts/README.md`." The README pointer is relative. It is a doc pointer, not a command, but it does not resolve from a project directory.
5. Out of Stage 1 scope (Task 3.3 reduces this skill): bash-script-audit's `audit.sh` still reports "ERRORS: 0 WARNINGS: 0" on a script whose body is `rm -rf $1/*`.

Environment: Linux, Claude Code 2.1.322 in `claude -p --output-format stream-json`, sessions on claude-sonnet-5-5 and claude-haiku-5-5, branch value-audit-reduction at ca3c9d9. Plugins were loaded with `--plugin-dir` from the repo, and the installed git-github was disabled for these sessions.
- Fixtures, live-page copies and transcripts are in /tmp/claude-1000/-home-user-dev-ai-tools-coder-plugins/ddbc36f7-460a-4c5c-aea4-7b881cbf0543/scratchpad/ (runs/r2-*.jsonl, proj-pkg, proj-nopkg, elsewhere, elsewhere2, tagrepo, web2/).
- All 14 sessions finished, each confirmed by its own `.done` sentinel, and the whole batch by `runs/r2-ALL.done`. No background job is left running.
