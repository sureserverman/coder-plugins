# release-promo

Drafts release-announcement posts for the platforms a project actually belongs on. No autoposting — every draft is reviewed by you before it leaves your terminal.

## What it covers

| Skill | Channel | Use when |
|---|---|---|
| `reddit-promo` | Reddit (subreddit-aware) | You want a post tailored to subreddit rules. Includes Matrix subs (r/matrixprotocol, r/matrixdotorg), r/selfhosted, r/programming, r/opensource, r/SideProject, r/coolgithubprojects, language subs, topic subs (r/privacy, r/Tor, r/linux, r/commandline). |
| `twim-submission` | This Week in Matrix | The project is a Matrix client/server/bridge/bot/library/MSC. |
| `hackernews-show-hn` | Hacker News (Show HN) | The thing is something readers can run/use today, not vapor. |
| `lobsters-post` | Lobsters | You have an invite and a focused, technically substantive announcement. |
| `fediverse-post` | Mastodon / Fediverse | You want a 500-char toot with hashtags and CW where appropriate. |

### All five channel skills are dispatch-only

Every skill in that table carries `disable-model-invocation: true`. Two consequences:

- **They never fire on their own**, and their descriptions are not injected into session context — they cost nothing when you are not releasing.
- **They are reached through `/promote-release`**, which dispatches one `post-drafter` invocation per eligible channel. You *can* still invoke one directly as `/release-promo:reddit-promo`, but nothing will route to it automatically, so if you are waiting for a channel skill to trigger from conversation, it will not.

## Agent

### `post-drafter`

Drafts one channel's post from the survey the orchestrator ran. **Pinned to `haiku`** — this is bounded, format-following work over facts already gathered, so it runs ~10× cheaper and keeps repo survey output out of the orchestrator's context. Fanned out one invocation per channel, in parallel.

## Artifacts

**Nothing is written to disk and nothing is posted.** The bundle of drafts is returned in the conversation for you to copy, edit, and submit yourself. This plugin never opens a browser, never authenticates, and never submits — a design rule, not a limitation to work around.

## Slash command

```
/promote-release
```

Surveys the current repo (README, latest CHANGELOG entry, recent commits, language/framework signals, Matrix detection), picks eligible channels, then **fans out drafting in parallel to the haiku-pinned `post-drafter` subagent — one invocation per channel**. Each draft reads the matching SKILL.md and returns one markdown block. The orchestrator concatenates them into a single bundle for review. Does not post.

You can also pass a hint:

```
/promote-release v1.4.0 — focus on the new federation feature
```

## Channel-selection heuristics

The command reads the repo and applies these rules:

- **Matrix project** (homeserver / client / bridge / bot / library / MSC) → adds **TWIM** + **r/matrixprotocol** + **r/matrixdotorg**. Detected via README/manifest mentioning *matrix*, *synapse*, *dendrite*, *conduit*, *MSC####*, *homeserver*, or `m.*` event types.
- **Self-hostable service** → adds **r/selfhosted**.
- **CLI tool** → adds **r/commandline** and (if shell) **r/bash**.
- **Privacy/anonymity tooling** (Tor, onion, GrapheneOS, Whonix mentions) → adds **r/privacy**, **r/Tor**, **r/GrapheneOS** as appropriate.
- **Language-specific** (Cargo.toml / go.mod / pyproject / package.json / build.gradle) → adds the corresponding language subreddit.
- **Android app** → adds **r/androiddev** and (for end-user apps) **r/Android**.
- **Show HN** is added when the project has a runnable demo or installable artifact.
- **Lobsters** is added only if the user confirms they have an invite (no drive-by submissions).
- **Fediverse** is always eligible.

## Design rules baked in

- **No marketing fluff.** Posts state what the thing is, what changed, and a link. No "revolutionary", no "game-changing".
- **Sub-specific rules.** Each subreddit's self-promotion threshold and flair conventions are encoded in the reddit-promo references.
- **One post per channel.** No copy-paste cross-posting — same facts, different format and tone per platform.
- **You ship the post.** This plugin never opens a browser, never authenticates, never submits. It writes drafts to stdout/markdown.

## Install

```
/plugin marketplace add sureserverman/coder-plugins
/plugin install release-promo@coder-plugins
```

## License

MIT.
