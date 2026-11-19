# Plan demo — 2026-11-17-stack-knowledge-to-vault-sub-03-rollout-and-retire-plan

Environment: Linux, Claude Code 2.1.328, vault-context 0.7.1 (installed). Branch stack-knowledge-to-vault at f859df8, loaded with `--plugin-dir` for android-dev 3.3.0, browser-extensions 0.3.0, infra-build 0.3.0, git-github 0.10.1 and loadout 0.3.0. The installed copies were turned off with `--settings '{"enabledPlugins":{"android-dev@coder-plugins":false,"browser-extensions@coder-plugins":false,"infra-build@coder-plugins":false,"git-github@coder-plugins":false,"loadout@coder-plugins":false}}'` (written below as FLAGS). Scratch git projects and raw logs are in /tmp/claude-1000/-home-user-dev-ai-tools-coder-plugins/691ba292-e15a-4a83-8a67-2a919940b555/scratchpad/demo/. Sessions ran with `claude -p ... --output-format stream-json --verbose --max-turns N`. "Page whole" means the installed page `~/.claude/vault-stacks/vault-stack-<slug>.md`, stripped, appears as one substring of the SessionStart `additionalContext`.

Fill in Verdict and Evidence under each Outcome. Do not edit the quoted lines.

# Stage 1

## Outcome 1
> Works: a session opened (or cleared, or compacted) in a project that tracks a file matching a stack's `paths` starts with that stack page whole.
Verdict: holds (opened and cleared were shown; compacted was not driven)
Evidence:
- Scratch repo `debproj` tracks `deb/DEBIAN/control` and `src/main.sh`. Ran `claude -p "Reply with the single word OK." FLAGS --max-turns 1` there. Exit 0, result "OK". One `hook_response` (SessionStart:startup) carried `additionalContext` of 7,879 chars. It starts `---\npaths: ["**/deb/**", "**/DEBIAN/**"]\n---\n<!-- vault-context:stack-rule source=deb-packaging ... -->\n\n# Debian packaging`. Page whole: True. The context is exactly the 7,879-char page and nothing else.
- One fresh scratch repo per page, same command:
  - `extproj` (`manifest.json`, `_locales/en/messages.json`): browser-extension arrived whole, ctx 4,628 chars.
  - `macproj` (`mac/Makefile`, `mac/scripts/postinstall`): mac-packaging arrived whole, 4,767 chars.
  - `iconproj` (`app/src/main/res/mipmap-hdpi/ic_launcher.png`): android-icons arrived whole, 6,722 chars.
  - `storeproj` (`fastlane/metadata/android/en-US/full_description.txt`): android-store-metadata arrived whole, 8,099 chars.
  - android-build and readme arrived whole in the Outcome 2 run.
  - That makes all seven rollout pages, plus readme, seen arriving on a sample file.
- Cleared: started an interactive `claude FLAGS` in `debproj` under tmux. Accepted the trust prompt, then typed `/clear`. The screen showed `SessionStart:clear says: ...`. The new session's transcript (f6e32b4f-…jsonl) has a `hook_additional_context` attachment of 7,879 chars. Page whole: True.
- Compacted: not driven. `/compact` on an empty session needs a model summary, and that was not worth the spend.

## Outcome 2
> The pages that apply to one project total more than 9,500 characters (an Android app with F-Droid metadata and Rust code, as `multitor-android`) → the session starts with the pages that fit, in slug order, and one line naming each page that did not, with its path to read.
Verdict: holds
Evidence:
- `cd /home/user/dev/android/multitor-android`, then ran `claude -p "Reply with the single word OK." FLAGS --max-turns 1`. Exit 0. **No stack context at all.** The project's `.claude/settings.local.json` was written by loadout before 0.3.0 and holds `"vault-context@obsidian-wiki": false`, so the hook never ran. This is the Outcome 6 case; see the Material finding below.
- Re-ran with `"vault-context@obsidian-wiki":true` added to `--settings`. Exit 0. `git status --short` was unchanged before and after (6 lines, the owner's own edits). One context of 7,194 chars, in this order:
  1. android-build page (whole, 5,553 chars)
  2. `[vault-context] The android-icons stack page applies to this project but did not fit in the session-start context; read /home/user/.claude/vault-stacks/vault-stack-android-icons.md`
  3. `[vault-context] The android-store-metadata stack page applies ... read /home/user/.claude/vault-stacks/vault-stack-android-store-metadata.md`
  4. readme page (whole, 1,095 chars)
  5. `[vault-context] The rust stack page applies ... read /home/user/.claude/vault-stacks/vault-stack-rust.md`
- That is slug order, with one line and a path for each page that did not fit.
- The applying pages total about 25,000 chars (5,554 + 6,722 + 8,099 + 1,096 + 3,530). That is more than 9,500.
- The result matches the budget.tsv row for multitor-android: inlined android-build,readme; named android-icons,android-store-metadata,rust; 7194 chars.

## Outcome 3
> A project that tracks no matching file → no page; `budget.tsv` shows it with nothing applying.
Verdict: holds
Evidence:
- Scratch repo `plainproj` tracks `notes.txt` and `src/app.py`. Ran `claude -p "Reply with the single word OK." FLAGS --max-turns 1`. Exit 0, result "OK".
  - No hook returned `additionalContext`.
  - The jsonl contains no "stack-rule" or "stack page" text.
  - The only hook output was the `[vault-context] No vault context for this project yet...` systemMessage.
- `/mnt/vault/Portfolio/ai-tools/coder-plugins/evidence/stack-knowledge/move/budget.tsv` (8,746 bytes) lists 11 projects with empty applies/inlined/named and 0 chars. Among them are `/home/user/dev/servers/action-matrix` and `/home/user/dev/virt`.
- Cross-check: `git ls-files` in those two projects matches none of the eight pages' path patterns (0 hits each).

# Stage 2

## Outcome 4
> Works: the retired skills are no longer offered; a session in a project holding a matching file starts with the stack page (or a line naming it, where the applying pages overflow the budget); `android-fdroid-publish`, `android-ui-design-figma`, `build-readiness-check` and `review-readme` still run and point at the page by name where they used to carry the facts.
Verdict: holds
Evidence:
- **Not offered.** The session init event of the `debproj` run lists plugins `android-dev 3.3.0`, `browser-extensions 0.3.0`, `infra-build 0.3.0`, `git-github 0.10.1` and `loadout 0.3.0`, all `@inline` from the branch paths.
  - Its skills/slash_commands list (406 entries) holds none of android-gradle-build, android-release-signing, browser-extensions:browser-extensions, deb-package or mac-package.
  - It still holds android-dev:android-fdroid-publish, android-dev:android-ui-design-figma, infra-build:build-readiness-check and git-github:review-readme.
- **Stack page at start.** Shown in the Outcome 1 runs (whole page) and the Outcome 2 run (overflow lines), all on this build.
- **The four kept skills.** In scratch repo `overflow`, ran `claude -p "Invoke each of these four skills with the Skill tool ... quote verbatim every line ... that names a stack page" FLAGS --allowedTools Skill --max-turns 8`. Exit 0.
  - All four Skill calls returned `Launching skill: ...` with no error. Each loaded from `/home/user/dev/ai-tools/coder-plugins/<plugin>/skills/<skill>`.
  - Lines in the loaded skill text, checked against the transcript:
    - android-fdroid-publish:
      - "...per-file limits, hard rules and locale conventions in the `android-store-metadata` stack page (`~/.claude/vault-stacks/vault-stack-android-store-metadata.md`)"
      - "...the command that computes `AllowedAPKSigningKeys` are in the `android-store-metadata` stack page"
      - "Release signing is set up per the `android-build` stack page"
      - "See the `android-icons` stack page"
    - android-ui-design-figma:
      - "Build and test per the `android-build` stack page"
      - "follow the spec, scaffold and verification recipe in the `android-icons` stack page (`~/.claude/vault-stacks/vault-stack-android-icons.md`)"
    - build-readiness-check:
      - "defer to the `deb-packaging` stack page (`~/.claude/vault-stacks/vault-stack-deb-packaging.md`) — don't duplicate its content here"
      - "defer to the `mac-packaging` stack page"
    - review-readme: "Review the README against the house limits in the `readme` stack page (`~/.claude/vault-stacks/vault-stack-readme.md`)"

## Outcome 5
> The owner asks for a retired skill by name → Claude Code reports it is not available; the plugin README says where its facts went.
Verdict: holds
Evidence:
- In `debproj`, ran `claude -p "/infra-build:deb-package" FLAGS --max-turns 1`. The reply was "The `/infra-build:deb-package` command isn't installed in this session. I'll do the deb packaging work directly, following your deb-packaging rules..." The run stopped at max turns (exit 1, as bounded).
- In `overflow`, ran `claude -p "Use these skills, one after another, with the Skill tool: android-dev:android-gradle-build, android-dev:android-release-signing, browser-extensions:browser-extensions, infra-build:deb-package, infra-build:mac-package ..." FLAGS --allowedTools Skill --max-turns 8`. Exit 0.
  - Each of the five Skill calls returned `<tool_use_error>Unknown skill: <name></tool_use_error>`.
  - The final reply: "None of the five skills ran. The Skill tool returned "Unknown skill" for each one", plus that the build and signing rules "are still in this session. A session-start hook loaded them as context".
- READMEs, read as the owner would:
  - android-dev/README.md:86: "The former Gradle-build and release-signing skills were retired; their facts now live in the `android-build` page."
  - browser-extensions/README.md:27: "The former `browser-extensions` authoring skill is retired. ... the `browser-extension` stack page (`~/.claude/vault-stacks/vault-stack-browser-extension.md`)."
  - infra-build/README.md:36: "The reference for the canonical `deb/` layout ... and the `mac/` layout ... is no longer a skill here. ... the `deb-packaging` and `mac-packaging` stack pages, synced locally as `~/.claude/vault-stacks/...`."
  - The top-level README.md rows 26, 27 and 30 say the same.

## Outcome 6
> A project whose loadout settings were written before loadout 0.3.0 → after the update and a loadout re-run there, vault-context is on and the pages arrive *(needs: the merge, the plugin update and a loadout re-run, which happen at close-out after the demo)*.
Verdict: holds. The branch loadout 0.3.0 loaded by `--plugin-dir` stood in for the post-merge plugin update. The installed-update route itself is still owed at close-out.
Evidence:
- **Before.** The real `multitor-android` has a pre-0.3.0 `.claude/settings.local.json` with `"vault-context@obsidian-wiki": false`. A session there got no stack context (Outcome 2, first run).
- **Re-run.** Made scratch project `oldloadout`: a copy of `overflow` (tracks `app/build.gradle.kts`, `AndroidManifest.xml`, `fastlane/metadata/android/en-US/title.txt`, `core/Cargo.toml` and `README.md`). Copied in multitor-android's `settings.local.json` and `loadout.json` (`tech: android`). Ran `claude -p "/loadout:loadout set android" FLAGS --allowedTools "Bash,Read,Skill" --max-turns 6`.
  - It ran `python3 /home/user/dev/ai-tools/coder-plugins/loadout/scripts/loadout.py set android`.
  - Printed: "enabled (5): + android-dev@coder-plugins + git-github@coder-plugins + planning@staged-planning + vault-context@obsidian-wiki + vault-portfolio@obsidian-wiki".
  - Afterwards `settings.local.json` no longer mentions vault-context, so the user-scope `true` applies.
- **After.** A new session there (`claude -p "Reply with the single word OK." FLAGS --max-turns 1`) loaded the vault-context plugin. It started with android-build and readme inlined, and overflow lines for android-icons, android-store-metadata and rust (7,194 chars).

# Findings

- **Blocking:** none.
- **Material (close-out scope, not a product defect).** 32 projects under ~/dev have `"vault-context@obsidian-wiki": false` in `.claude/settings.local.json` today. A grep finds them; they include multitor-android, 10 more of the Android apps in budget.tsv (story-mapper and health-alert are not among them), sec-audit, appimage-control and coder-plugins itself. Until loadout is re-run in each one after the update, a real session there gets **no** stack page, even though budget.tsv lists pages for them. The sweep does not model enabledPlugins. Close-out needs a re-run in every such project, not just one.
- **Minor.** The plugin READMEs describe the retired skills ("the former Gradle-build and release-signing skills", "is no longer a skill here") rather than by their exact names (`deb-package`, `mac-package`). An owner who typed `deb-package` has to make the link from the description. This follows from the plan goal's rule that no retired component is named.
- **Minor, existing before this branch.** The android tech profile turns `loadout@coder-plugins` off. After a re-run, the model warned that "`/loadout` won't be available in this project". The old settings had this too, so it is not caused by this branch.

Verdict: PASS with residuals (compaction route not driven; installed-plugin update route for Outcome 6 happens at close-out).
