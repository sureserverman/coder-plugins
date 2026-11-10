# Stage 3 demo — 2026-11-10-value-audit-reduction-plan

Environment: Linux host, `claude` 2.1.322. Repo at 476c1e6 on `value-audit-reduction`. The marketplace was installed from the repo folder into fresh config dirs:
- `cfg`: the nine plugins, no planning.
- `cfg2`: `cfg` plus `planning@staged-planning` 1.4.3, from the local staged-planning marketplace.
- `cfgmain`: `main`'s rust-dev 0.5.2, from `git archive main`, used as the baseline.
- `cfg0`: empty, for the executor runs.

Sessions were `claude -p` runs (session model `claude-sonnet-5-5`) started in throwaway project folders under the scratchpad. The user's token was passed by environment and never written to disk. Every transcript is `<scratchpad>/runs/s3-<name>.jsonl`, where `<scratchpad>` = `/tmp/claude-1000/-home-user-dev-ai-tools-coder-plugins/ddbc36f7-460a-4c5c-aea4-7b881cbf0543/scratchpad`. The fixtures are in `<scratchpad>/work/` and the prompts in `<scratchpad>/prompts/s3-*.txt`. Afterwards, `git status` in the repo showed only this file.

Fill in Verdict and Evidence under each Outcome. Do not edit the quoted lines.

## Outcome 1
> Works: each shrunk component still gives what its Dispositions row lists, and triggers on the same requests as before
Verdict: holds
Evidence:
- **Triggers, live.** Each prompt below is a phrase from the component's own description, run in `cfg` in a fixture repo (`work/app`, `work/rustcrate3`). Each loaded the right skill (first `Skill` call):
  - "tag a release v0.2.0" → `git-github:release-tag`
  - "audit my workflows" → `git-github:github-workflow-audit`
  - "audit this script before it ships inside our .deb: install.sh" → `infra-build:bash-script-audit`
  - "my readme is a mess — what's wrong with it?" → `git-github:review-readme`
  - "audit the code comments in src/app.py…" → `git-github:code-comment-audit`
  - "how should this project make money? pick a revenue model" → `business:revenue-model`
  - "is this idiomatic Rust? check src/main.rs and the crate setup" → `rust-dev:rust-coding`
- **Same requests as before.**
  - The rust prompt also loads `rust-dev:rust-coding` on main's 0.5.2 (`s3-o1-rust2-main`).
  - "Is anything wrong with its Cargo manifest?" loads no skill on either tree. On the branch the session ran `cargo check` (`s3-o4-rust`). On main it read the manifest (`s3-o1-rust-manifest-main`). The miss existed before this stage.
  - The frontmatter `name:`/`description:` of the nine Stage 3 shrunk or edited skills is the same in the installed copy as on main: rust-coding, github-workflow-audit, release-tag, code-comment-audit, review-readme, gate-audit, request-external-reviews, bash-script-audit, revenue-model. Sizes now: 3148, 3085, 2691, 4164, 1757, 1625 and 3011 B. All are within their bounds.
- **Stays, used in the runs:**
  - **release-tag:** showed the tag, SHA and message from the CHANGELOG, then asked "Should I create the tag…? Say "yes"". `git tag -l` afterwards was still only `v0.1.0`.
  - **github-workflow-audit:** ran `…/git-github/scripts/validate-workflows.sh .`. It then added the judgment items, merged everything into the ERROR/WARN/INFO table and offered fixes.
  - **bash-script-audit:** ran `…/bash-script-audit/scripts/audit.sh install.sh` (exit 1). It then reported the judgment items by hand: mkdir `./demoapp` against `cp … "~/demoapp/"`, the AppImage never `chmod +x`'d, and the unquoted `<<CONF` heredoc expanding `$HOME`.
  - **review-readme:** "9 top-level sections, over the limit of 6"; "Installation has 5 steps (the limit is 3)". It proposed a shorter README.
  - **code-comment-audit:** Project Map first, no proposed comments, 5 "Flagged for human attention", one noise removal, the summary table, and "This was a dry run, so I changed nothing".
  - **revenue-model:** ran `business-scan.py`, found no assess verdict, and stopped: "The skill's rule is to stop and run `/business:assess` first".
  - **rust-coding:** ran `bash ".../rust-dev/scripts/validate.sh" <crate> --json` and reported the edition/MSRV error.
- **Stays, read in the shipped text.** Each Stays item in the Stage 3 Dispositions rows is in the installed files:
  - **rust-coding:** 8 gotchas including NVPTX; the `validate.sh` run line; the owner-rule list with `deny_unknown_fields` and "Channels are bounded".
  - **release-tag:** ask before tagging and again before pushing; `git push origin <tag>`, never `--tags`; never move or delete a tag.
  - **code-comment-audit:** the gate table, "Flagged for human", dry-run default, report shape.
  - **review-readme:** at most 6 sections, at most 3 quick-start steps, "Never grow the README".
  - **bash-script-audit:** the audit.sh line plus the mkdir, heredoc and chmod items.
  - **revenue-model:** determinism boundary, assess precondition, `{metric, target, by}`, write-and-verify, business groups.
- **Not reached:** release-tag's push gate (the fixture has no remote) and revenue-model's write path (the precondition stopped it first).

## Outcome 2
> Works: a review the owner asks for is done by the built-in `/code-review`, and a plan's review pass by `planning:code-reviewer`; `gate-audit` names that agent for its independent read
Verdict: holds
Evidence:
- **Owner's review.** "review my changes before I commit" in `work/appdiff` (an uncommitted diff with three planted bugs) loaded the built-in `code-review` skill (`s3-o2-review`).
  - The session's skill list holds `code-review` and no `git-github:code-review`.
  - It found all three planted defects: the `--port` regression, the `divide()` zero-guard that guards nothing, and the hardcoded `password = "hunter2"`.
- **Plan's review pass.**
  - Standard-flow review: `/planning:executing-plans` on `work/rustplan3` committed the task, then ran `Agent planning:code-reviewer` over the whole diff: "approved it with no Critical or Important findings" (`s3-o7-plan-c`).
  - Asked for the plan's review pass on `work/rustplan`, the executor again dispatched `planning:code-reviewer` (read-only), with verdict APPROVE (`s3-o2-planreview`).
- **gate-audit names the agent.**
  - The installed `gate-audit/SKILL.md` says to dispatch "the `planning:code-reviewer` subagent (Agent tool, `subagent_type: "planning:code-reviewer"`)", and its Integration list names the same agent.
  - In the runs, gate-audit sessions referred to "the independent `planning:code-reviewer` subagent" (`s3-o3-gate-noplan`) and "the `planning:code-reviewer` subagent the skill suggests" (`s3-o3-gate2-noplan`).
  - No gate-audit run actually dispatched it; see finding M1.

## Outcome 3
> A session asks for `git-github:code-reviewer` → the type is unknown to the host; the caller uses `planning:code-reviewer`, or a general agent briefed read-only when planning is not installed
Verdict: holds
Evidence:
- **Without planning** (`cfg`, `s3-o3-cr-noplan`). Prompt: "Dispatch the git-github:code-reviewer subagent to review the last commit (HEAD)…".
  - The host returned `Agent type 'git-github:code-reviewer' not found. Available agents: business:market-researcher, claude, Explore, general-purpose, i18n:translator, Plan, statusline-setup`.
  - The caller stopped and offered "Run the `code-review` skill on HEAD" or "Dispatch a `general-purpose` agent with a review brief".
  - On the user's reply "2" (`s3-o3-cr-noplan-t2`) it dispatched `general-purpose` with a brief that says "Do not modify any files", and returned that agent's findings. The fixture tree was unchanged afterwards.
- **With planning** (`cfg2`, `s3-o3-cr-plan`). Same prompt. The caller dispatched `planning:code-reviewer`: "I ran `planning:code-reviewer`, not the `git-github:code-reviewer` you named, because that agent doesn't exist in this session". It returned a BLOCK verdict with findings.
- **Inventory.** `claude plugin details git-github@coder-plugins` shows `Agents (0)`.
- Residuals: m1, m2.

## Outcome 4
> Works: `rust-dev`'s script lane still flags a real manifest fault from a fresh project directory
Verdict: holds
Evidence:
- **Direct run of the installed copy.** `mktemp -d` crate with `edition="2024"`, `rust-version="1.70"`, then `bash <cfg>/plugins/cache/coder-plugins/rust-dev/0.6.0/scripts/validate.sh "$T" --json`. Result: exit 1, `"rule": "cargo-edition-msrv-mismatch"`, `"message": "edition 2024 requires rust-version >= 1.85, found 1.70"`, `"verdict": "fail"`.
- **Through the skill.** In `s3-o1-rust2-branch` (a fresh crate folder) the `rust-coding` skill ran `bash ".../rust-dev/scripts/validate.sh" <crate> --json` (exit 1). The session reported "Error: edition and MSRV don't match". The installed 0.6.0 folder holds `README.md`, `scripts/` and `skills/` only.

## Outcome 5
> Works: every remaining plugin installs from the marketplace; `game-dev` is not offered
Verdict: holds
Evidence:
- `claude plugin validate .` returned "✔ Validation passed".
- `CLAUDE_CONFIG_DIR=<cfg> claude plugin marketplace add <repo>` returned "✔ Successfully added marketplace: coder-plugins".
- `claude plugin install <p>@coder-plugins` printed "✔ Successfully installed plugin" for each of rust-dev, android-dev, release-promo, infra-build, git-github, business, browser-extensions, loadout and i18n.
- `claude plugin list --json` shows the installed versions: rust-dev 0.6.0, android-dev 3.2.0, release-promo 0.4.0, infra-build 0.2.3, git-github 0.10.0, business 0.8.3, browser-extensions 0.2.4, loadout 0.2.3, i18n 0.6.0.
- `claude plugin list --available --json` offers only `planning@coder-plugins` from coder-plugins, besides the installed nine. No `game-dev` id appears among 3664 available entries; the only "game" hits are four unrelated Anthropic-directory plugins.
- From a folder outside the repo, all nine are enabled. Inside the repo, five show "disabled in your settings"; that comes from the repo's own `.claude/settings.local.json` loadout state, not from the plugins.

## Outcome 6
> An install of `game-dev@coder-plugins` is attempted → the CLI refuses it as unknown
Verdict: holds
Evidence:
- Command, on the same fresh config: `CLAUDE_CONFIG_DIR=<cfg> claude plugin install game-dev@coder-plugins`.
- Output: `✘ Failed to install plugin "game-dev@coder-plugins": Plugin "game-dev" not found in marketplace "coder-plugins". Your local copy may be out of date — try \`claude plugin marketplace update coder-plugins\`.`
- Exit 1.
- This settles the open premise: the CLI does refuse a plugin the marketplace does not list.

## Outcome 7
> A plan elsewhere names `rust-dev:rust-expert` → the router falls back to `general-purpose`; the one known open plan is in the backlog
Verdict: holds
Evidence:
- **Backlog.** `/mnt/vault/Portfolio/ai-tools/coder-plugins/backlog.md` has "## BL-150 — open multitor plan names a retired agent". It names `…/multitor/plans/2026-09-19-macos-network-extension-apple-gated-plan.md` line 132, which still reads "Task 2.1 → `rust-dev:rust-expert`".
- **Router, Standard plan.** `work/rustplan4` is a two-task Standard plan on branch `fix-manifest` whose roster says "Task 1.1 → `rust-dev:rust-expert`". `/planning:executing-plans` was run in `cfg2` (`s3-o7-plan-d`).
  - Task 1.1 was dispatched as `Agent general-purpose`. The commit `4c8d850` carries "Executor: dispatched — general-purpose".
  - The session said "Task 1.1 was dispatched via `general-purpose` … because `rust-dev:rust-expert` isn't registered in this session". The plan completed and its gate passed.
- **Direct ask** (`s3-o7-direct`). The host replied `Agent type 'rust-dev:rust-expert' not found`. The caller offered `general-purpose` with a Rust brief.
- **Light plans don't fall back the same way.**
  - On a light-plan fixture, the executor runs the task inline instead (`s3-o7-plan-b`, `s3-o7-plan-c`: "Executor: inline (dispatch failed)").
  - On `main` it stopped once to ask. It offered "(a) Branch, and dispatch Task 1.1 to `general-purpose`" (`s3-o7-plan`). After "(a)", it dispatched `general-purpose` and finished (`s3-o7-plan-t2`).
  - No run crashed or used the retired agent as a registered type. See m3.

## Outcome 8
> A task finds a Stays item missing from its file → it stops and reports
Verdict: holds
Evidence:
- **Route.** This is the executor's route, as in Stage 2. A fresh `claude -p` executor (`cfg0`, no plugins) got a brief built verbatim from the plan (`prompts/s3-o8.txt`). It holds Task 3.1 with Status reset to `[ ]`, Shrink rules 1–8 and the four `rust-dev` Dispositions rows.
- **Fixtures.** Both are `git archive main rust-dev scripts`, committed as `base`.
  - `work/o8a`: gotcha 6 (NVPTX) is deleted from `rust-coding/SKILL.md`. NVPTX exists nowhere else, so it could only come back from memory.
  - `work/o8b`: every `deny_unknown_fields` / `rust-serde-missing-deny-unknown` mention is deleted from the SKILL.md. It still lives in `references/api-design.md`, `agents/rust-expert.md` and the scripts.
- **Run A** (`s3-o8a`, 3 turns, exit 0): "I stopped without changing anything or committing… a Stays item is missing… item 6 is gone… rule 8 says not to restore a Stays item from memory or from another file." It asked for the original gotcha or a corrected Test.
- **Run B** (`s3-o8b`, 3 turns, exit 0): "I stopped without changing anything… `deny_unknown_fields` is missing from `rust-dev/skills/rust-coding/SKILL.md`, and rule 8 says to stop… Rule 8 forbids writing it back from `api-design.md` or from memory." It ended with a call for the plan's executor.
- **Trees afterwards, checked by me.** Each still has only its `base` commit (`f29b617` / `a7b6da3`), and `git status --short` is empty in both.
  - o8a: NVPTX count 0, SKILL.md still 5047 B.
  - o8b: `deny_unknown_fields` count 0, SKILL.md still 5205 B.
  - Nothing was written back, and `agents/` and `references/` were left in place.

## Findings

No Blocking findings.

- **M1 (Material) — gate-audit never dispatched its independent reviewer.**
  - Across four runs it did not dispatch the independent reviewer, with or without planning installed: `s3-o2-gate-plan`, `s3-o3-gate-noplan`, `s3-o2-gate2-plan`, `s3-o3-gate2-noplan`.
  - That includes `gates2`, whose findings were judgment calls ("The soak log looks fabricated", "Treat it as unverifiable or hand-edited"). Each run graded itself: "the findings above don't depend on judgment calls".
  - In `cfg` it noted the agent "isn't in this session's agent list" and went on with no fallback. The skill text gives none, and the README says "without planning installed, no reviewer agent is available" (DEC-041's accepted cost).
  - This stage changed only the agent's name in gate-audit (3839 → 3844 B), so the skip is likely older. I did not run main's gate-audit to confirm.
- **m1 (Minor) — the caller asks before falling back.** Without planning, the caller stops and asks before using a general agent. The read-only brief appears only after the user picks it. Nothing in the shipped text tells the caller to fall back.
- **m2 (Minor) — the no-planning answer misnames the review skill.** It told the user "The `git-github` plugin does provide skills, such as `code-review`". That skill is the built-in one; git-github no longer ships it. This is the model's wording, not a shipped string.
- **m3 (Minor) — an old cached copy of the retired agent is still read.**
  - The Standard-plan router briefed `general-purpose` "using the on-disk `rust-expert` definition". It read `/home/user/.claude/plugins/cache/coder-plugins/rust-dev/0.5.2/agents/rust-expert.md` from the host's real cache, outside the fresh config.
  - This host still has the pre-change installs: rust-dev 0.5.2, git-github 0.9.1 (with `git-github:code-reviewer`), game-dev 0.3.1. OD-4 cleans only game-dev.
  - BL-150 names this ("the router may load it"). Close-out should update every installed coder-plugins plugin, not only remove game-dev, or the retired agents stay reachable on this host.
- **m4 (Minor) — light plans with a missing roster agent behave in two ways.** They run the task inline, or ask once. BL-150 says "falls back to `general-purpose`… so the plan still runs", which is true for a Standard plan only.
