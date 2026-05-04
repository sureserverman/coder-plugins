# General programming and launch subs

Per-sub conventions beyond the quick reference table in `SKILL.md`.

## r/programming

Hostile to anything that reads like a launch ad. Two ways to survive:

1. **Deep technical post-mortem** — describe a hard problem the project solved, with code or diagrams. The release/repo is mentioned at the end.
2. **Short factual announcement** — one paragraph, stack, link, no marketing words.

Title rules:

- No "I made", no "Show", no "Released".
- Describe the thing or the technique. `A self-hosted Matrix homeserver in Rust with ~30 dependencies` is fine. `I made a new Matrix homeserver!` is not.

Mod actions are aggressive. Account age and karma matter.

## r/opensource

- Always state license in the body (SPDX identifier preferred).
- State contribution model: solo, open-to-PRs, governance doc.
- State funding model if any (donations, grants, none).
- Re-licensing or relicensing-controversy posts get heavy traffic but heavier moderation — link primary sources.

## r/SideProject

- Honesty about scope works here. "Solo project, used by 12 people" is fine and gets engagement.
- Revenue figures welcome.
- "What I learned" framing is over-used; use it only if you actually have a non-obvious lesson.

## r/coolgithubprojects

- Title format: `<project> — <one line>`
- Body can be very short (the link is the point).
- Make sure the GitHub repo has a screenshot or screencast at the top of the README — that's what readers see.

## r/selfhosted

- **Self-hostable is the bar.** SaaS-only tools get removed.
- Body must include: deploy method (Docker, single binary, k8s helm chart, ansible, manual), resource requirements (RAM, disk), license, port/auth defaults.
- Use the `Release` or `Self Promo` flair if the sub offers it.
- Disclosure required: "I'm the maintainer" in the first line.

## Language subs

### r/rust

- Posting flair: `project` for new projects, `announcement` for releases.
- Body should mention: MSRV, no_std support if any, `unsafe` use (and why), feature flags.
- "Why Rust" pitches in the body get downvoted — readers already chose Rust.

### r/golang

- Minimalism is currency: dependency count, binary size.
- "Why Go" pitches: same as Rust, skip.

### r/python

- Mention supported Pythons (`3.9+`, `3.12 only`, etc.).
- Mention install path (`pip install`, `uv add`, `pipx install`).
- If it's a CLI, screencast > screenshot > nothing.

### r/AndroidDev

- For library/dev-tool releases only. End-user apps go to r/Android.
- Min SDK, target SDK, Compose vs Views, Kotlin version.
- License.

### r/Android

- End-user apps only. Library posts get redirected.
- Play Store link, F-Droid link, direct APK link (in that order if all three exist).
- Screenshots required.
- Permissions disclosure helps trust.

### r/javascript / r/typescript / r/node

- Bundle size matters; mention it for browser-targeting libs.
- Tree-shakeable / ESM / CJS support.
- Node version range.

## Topic subs

### r/privacy

- State the threat model in the first paragraph.
- State what it does NOT protect against.
- Avoid "more secure than" comparisons unless you have evidence.
- "Privacy by design" without specifics is filler.

### r/Tor

- v3 onion addresses only. Mention if the project bundles a Tor client (Arti, official tor) or expects a system Tor.
- Don't post promotional content for clearnet-only tools.

### r/GrapheneOS

- Heavily moderated. Read the rules sidebar.
- No "more secure than stock Android" claims unless you can cite the GrapheneOS hardening features you depend on.
- Solid choice for posts about apps that benefit from per-app network controls, sandboxed Google Play, hardened malloc.

### r/linux

- Distro coverage: which distros have it packaged, AppImage / Flatpak / snap availability.
- Avoid distro-war framing.

### r/commandline

- Asciinema or animated GIF strongly preferred over text-only.
- Mention shell compatibility (bash, zsh, fish).

### r/bash

- Pure-bash project rules: state bash version requirements, list any non-coreutils dependencies.
- Snippets in the body, not just a link.
