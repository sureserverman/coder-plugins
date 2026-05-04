---
name: fediverse-post
description: Drafts a Mastodon or Fediverse toot announcing a software release, with hashtag selection, content warning guidance, alt text reminders, and link strategy. Triggers on "draft a Mastodon post", "post on Fediverse", "toot this release", "share on Mastodon", "draft a fedi post", "Fediverse announcement", or any request for a short ActivityPub post promoting a project. Targets the 500-char default limit and the conventions of tech-leaning instances like fosstodon.org, hachyderm.io, mas.to, and chaos.social.
---

# fediverse-post

Drafts one Mastodon-compatible toot. Output is plain text plus alt-text and metadata.

## 1. Length

- **Default cap: 500 characters.** Some instances raise it (Pleroma, Akkoma, glitch-soc) but assume 500 for portability.
- Aim for **under 400 chars** so reposts with comment still fit.
- Hashtags count toward the limit.

## 2. Structure

```
<one-line headline — what & why>

<one short paragraph of detail>

<link>

<3–5 hashtags>
```

Example:

```
Released v0.4 of conduwuit-mate, a small CLI for managing user accounts on a Conduwuit homeserver.

This release adds device-list pruning and a `--dry-run` flag.

https://example.org/conduwuit-mate

#Matrix #Conduwuit #SelfHosted #Rust
```

## 3. Hashtag rules

- Mastodon hashtags **must use CamelCase** for accessibility (`#SelfHosted` not `#selfhosted`). Screen readers parse the case as word boundaries.
- 3–5 tags is the sweet spot. More is spammy; fewer reduces discoverability.
- Pick **specific over generic.** `#Matrix` `#Synapse` `#Conduwuit` `#TWIM` outperform `#Open` `#Tech` `#Software`.
- Common relevant tags:
  - Matrix ecosystem: `#Matrix`, `#TWIM`, `#Synapse`, `#Conduwuit`, `#Element`, `#Federation`.
  - Self-hosting: `#SelfHosted`, `#SelfHosting`, `#FOSS`, `#OpenSource`, `#FreeSoftware`.
  - Languages: `#Rust`, `#Golang`, `#Python`, `#Kotlin`, `#TypeScript`.
  - Privacy/Tor: `#Privacy`, `#Tor`, `#OnionService`, `#GrapheneOS`.
  - Linux: `#Linux`, `#Debian`, `#Ubuntu`, `#Arch`, `#Fedora`, `#NixOS`.
  - Releases: `#NewRelease`, `#FOSSdev`.

## 4. Content warnings (CW)

Use a CW (`spoiler_text` field) for:

- Long posts that go beyond the basic announcement (instances vary on what "long" means; >300 chars is a reasonable trigger).
- Posts that mention politics, drama, or contentious software (forks born of conflict, license changes, license-controversy projects).
- Posts that reference vulnerabilities or exploits, even fixed ones.

Don't add a CW for normal release announcements. CW-overuse is a known irritation in tech instances.

CW format: a short label like `release announcement`, `long post`, `fediverse drama`, `CVE`.

## 5. Visibility

Default to **Public** for release announcements.

Use `Unlisted` for:

- Reposts of an earlier announcement that you want available on your profile but not flooding the federated/local timelines.
- Test posts.

Use `Followers-only` only if the user explicitly wants it scoped.

Never use `Direct` for an announcement — it's a DM.

## 6. Image / media

If the user has a screenshot:

- Always provide **alt text**. The toot is incomplete without it on the Fediverse.
- One image is plenty. Two if before/after.
- Animated GIFs / short MP4 work; keep under 40 MB and 60s.

The output must include a separate ALT-TEXT block per image.

## 7. Link strategy

- Mastodon shortens displayed URL but the full URL counts toward the 500-char limit.
- Put the link **above** the hashtags so the link card renders properly.
- One primary link only. Additional links go in a follow-up reply, not the main toot.

## 8. Reply chains

If the announcement needs more than 500 chars:

- Main toot = headline + link + hashtags.
- First reply (self-reply, public) = additional context, "what's new" bullets.
- Second reply = call for feedback, contributor links.

Mark the chain by ending the main toot with `🧵` or `(1/3)` only if you'll actually post the thread.

## 9. Instance-specific notes

- **fosstodon.org / hachyderm.io / chaos.social** — tech audiences, hashtag conventions strict, CW for off-topic content.
- **mastodon.social** — general, larger audience, more tolerance for casual posts.
- **mas.to** — tech-leaning, similar to fosstodon.
- **infosec.exchange** — security-specific; tag posts well; CW for vuln content is expected.

If the user is on a domain-specific instance, adjust hashtag and CW choices accordingly.

## 10. Output format

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

CHECKLIST:
- [ ] Hashtags use CamelCase.
- [ ] Alt text written for every image.
- [ ] Link renders before hashtags so the card previews.
- [ ] Reply-thread plan if total content > 500 chars.
```
