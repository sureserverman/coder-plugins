---
name: fediverse-post
description: Drafts a Mastodon or Fediverse toot announcing a software release. Triggers on "draft a Mastodon post", "post on Fediverse", "toot this release", "share on Mastodon", or "Fediverse announcement" — hashtags, content warnings, alt text, and the 500-char limit for instances like fosstodon.org.
disable-model-invocation: true
---

# fediverse-post

Drafts one Mastodon-compatible toot.

## Length and links

Assume a 500-character cap. Every link counts as 23 characters toward the 500-char limit, however long it is (checked 2026-11-10, https://docs.joinmastodon.org/user/posting/). Don't use link shorteners. Put the link before the hashtags.

## Hashtags

Use 3–5 CamelCase tags, specific over generic. Pick from these sets:

- Matrix ecosystem: `#Matrix`, `#TWIM`, `#Synapse`, `#Conduwuit`, `#Element`, `#Federation`.
- Self-hosting: `#SelfHosted`, `#SelfHosting`, `#FOSS`, `#OpenSource`, `#FreeSoftware`.
- Languages: `#Rust`, `#Golang`, `#Python`, `#Kotlin`, `#TypeScript`.
- Privacy/Tor: `#Privacy`, `#Tor`, `#OnionService`, `#GrapheneOS`.
- Linux: `#Linux`, `#Debian`, `#Ubuntu`, `#Arch`, `#Fedora`, `#NixOS`.
- Releases: `#NewRelease`, `#FOSSdev`.

## Output format

```
TOOT (paste into compose):
---
<text>
---

ALT TEXT (per image):
- Image 1: <description, ≤1500 chars>

VISIBILITY: <Public | Unlisted | Followers-only>

CW (spoiler_text): <empty | label>

CHAR COUNT: <n>/500
```
