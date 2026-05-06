---
description: Survey the current repo, pick eligible promotion channels (Reddit, TWIM, HN Show HN, Lobsters, Fediverse), and draft one post per channel for review. Does not post anywhere.
argument-hint: "[version-or-hint] (optional)"
allowed-tools: ["Read", "Glob", "Grep", "Agent", "Bash(git:*)", "Bash(ls:*)", "Bash(jq:*)", "Bash(find:*)", "Bash(test:*)"]
model: inherit
---

# /promote-release

Drafts release-announcement posts for every platform this project actually belongs on. **Never posts.** Always emits markdown drafts for the user to copy.

The user invoked this command with: `$ARGUMENTS`

If `$ARGUMENTS` names a version (e.g. `v0.4.0`) or gives a hint ("focus on the federation feature"), incorporate it. Otherwise infer from the latest tag / CHANGELOG / recent commits.

## Phase 1 — Survey the repo

Run these in parallel:

- `git log --oneline -30` — recent commits.
- `git tag --sort=-creatordate | head -10` — recent tags.
- Read `README.md`, `README.*`.
- Read `CHANGELOG.md` / `CHANGES.md` / `HISTORY.md` if present.
- Glob for manifests: `Cargo.toml`, `package.json`, `pyproject.toml`, `go.mod`, `build.gradle*`, `*.gemspec`, `composer.json`, `Pipfile`.
- Glob for Android: `AndroidManifest.xml`, `app/build.gradle*`.
- Glob for Tor / privacy markers: `torrc`, `*.onion`, `tor-*`, `whonix-*`, `graphene*`.
- Glob for Matrix markers: `synapse*`, `matrix*`, `dendrite*`, `conduit*`, `conduwuit*`, `mautrix-*`, `mxc://`, `m.room.*`, `MSC[0-9]+`.

Extract:

- **Project name** (from manifest / README first heading).
- **Latest version** (from tag or CHANGELOG).
- **What changed** in this version (from CHANGELOG entry or commits since previous tag).
- **License** (LICENSE file SPDX or manifest field).
- **Stack** (language + key frameworks).
- **Project type** signals: Matrix-ecosystem, self-hostable service, CLI tool, Android app, library, browser extension, Tor/privacy tooling.

If the repo can't be identified from these signals, ask the user one clarifying question and continue.

## Phase 2 — Pick channels

Apply these rules to build the channel set:

| Signal | Channels added |
|---|---|
| Matrix-ecosystem (server, client, bridge, bot, library, MSC) | `twim-submission`, `reddit-promo` for r/matrixprotocol, `reddit-promo` for r/matrixdotorg |
| Self-hostable service | `reddit-promo` for r/selfhosted |
| CLI tool | `reddit-promo` for r/commandline; r/bash if shell |
| Android app | `reddit-promo` for r/AndroidDev (if dev-tool) or r/Android (if end-user) |
| Privacy/Tor/Graphene tooling | `reddit-promo` for r/privacy, r/Tor, r/GrapheneOS as relevant |
| Language-specific library or app | `reddit-promo` for the language sub (r/rust, r/golang, r/python, r/AndroidDev, etc.) |
| Anything with a runnable demo / installable artifact | `hackernews-show-hn` |
| User confirms Lobsters invite + prior participation | `lobsters-post` |
| Default-on for any release | `fediverse-post` |
| Default-on (general programming) | `reddit-promo` for r/programming **only if** the post can be technical-substantive, else r/SideProject or r/coolgithubprojects |

Show the user the chosen channel list as a single bullet block before drafting. Let them remove channels.

## Phase 3 — Draft one post per channel (parallel fan-out)

Dispatch the **`post-drafter`** subagent (haiku-pinned, read-only) once per chosen channel. **All dispatches in a single message so they run in parallel** — that's the whole point of the haiku worker.

Pass each invocation:

- `channel` — one of `reddit:<sub>`, `twim`, `showhn`, `lobsters`, `fediverse`.
- `facts` — the survey output as a structured block: `name`, `version`, `summary`, `whats_new` (bullet list), `license`, `stack`, `links` (repo, demo, docs, release notes), `project_type`, `audience_hint`.
- `hint` *(optional)* — anything from `$ARGUMENTS` that biases tone or focus.

The subagent reads the matching SKILL.md, applies its emit-block format, and returns one markdown section. It will return `SKIP: <reason>` if the skill's refusal rules apply (e.g. Show HN for vapor, r/Android for a dev-only library).

Channel → invocation mapping:

| Chosen channel | post-drafter input |
|---|---|
| r/matrixprotocol | `channel: reddit:matrixprotocol` |
| r/matrixdotorg | `channel: reddit:matrixdotorg` |
| r/selfhosted, r/programming, r/rust, r/AndroidDev, etc. | `channel: reddit:<sub>` |
| TWIM | `channel: twim` |
| Show HN | `channel: showhn` |
| Lobsters | `channel: lobsters` |
| Fediverse | `channel: fediverse` |

**Do not** invoke the skills directly from the orchestrator and do not draft from the orchestrator's own context. The fan-out is the design.

## Phase 4 — Emit a single bundle

Output one markdown document with one `## <Channel>` section per draft. Add a top "Channels" summary listing what was drafted and what was skipped (with the reason).

Emit a final block:

```
DO NOT AUTOPOST.
Each draft is a starting point — read your sub's rules sidebar / TWIM editor's pinned message before submitting.
```

## Refusals and edge cases

- **Empty repo / no commits** — refuse and tell the user there's nothing to announce yet.
- **Closed-source SaaS** — drop Lobsters and r/opensource; warn the user.
- **No README** — emit a clarifying question for project description before drafting.
- **Pre-release / alpha / vapor** — recommend skipping Show HN (per HN Show HN rules) and emit a regular HN submission template instead.
- **Account-thinness for Reddit/Lobsters** — flag the risk in the bundle; do not refuse to draft.

## Never

- Open a browser.
- Authenticate to any platform.
- Submit anything.
- Generate fake screenshots or fake demo links.
- Cross-post identical text across subs — every channel gets a tailored draft.
