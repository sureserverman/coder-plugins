---
name: reddit-promo
description: Drafts a Reddit post for promoting a software release or project, tailored to subreddit rules. Triggers on "draft a Reddit post", "post this to r/<sub>", "announce on Reddit", "submit to r/matrixprotocol", "submit to r/matrixdotorg", "post on r/selfhosted", "share on r/programming", "promote on r/SideProject", "post on r/coolgithubprojects", "Show this on r/rust / r/golang / r/python / r/AndroidDev", "post on r/privacy", "share on r/Tor", "draft a launch post for Reddit", or any request to write a subreddit-aware release/launch/show-off post. Encodes self-promotion rules and flair conventions per sub.
---

# reddit-promo

Drafts a Reddit submission tailored to one specific subreddit. Reddit rejects content that reads like cross-posted marketing — every sub gets its own draft.

## Reference map

| When you're posting to… | Read first |
|---|---|
| r/matrixprotocol or r/matrixdotorg | `references/matrix-subs.md` |
| Any general programming / launch sub | `references/general-subs.md` |

---

## 1. Reddit rules that apply to every sub

- **Reddit's site-wide self-promotion guideline**: more participating than promoting. If the account has only ever posted its own project, it will be flagged as spam regardless of sub rules. If the user has a thin account, recommend they comment elsewhere first.
- **Title is everything.** Reddit titles cannot be edited. Aim for: `<thing>: <one-line value prop>` or `<thing> v<X.Y> — <what changed>`. No clickbait, no all-caps, no leading emoji.
- **Self-post over link-post** for project announcements unless the sub explicitly prefers links. A self-post lets you write context; a link-post is a single click and dies fast.
- **Disclose authorship** in the first line of the body if you are the maintainer. Some subs (r/selfhosted, r/programming) require it; all subs tolerate it well.
- **No "[Show]" / "[Launch]" prefixes** in titles unless the sub uses flair for that — Reddit isn't HN.

## 2. Output structure

Always produce three sections:

1. **Title** — one line, ≤300 chars (Reddit hard cap), but aim for ≤120 to render fully on mobile.
2. **Flair** — name the appropriate flair if the sub has one (e.g. r/rust uses `project`, `announcement`).
3. **Body** — markdown. See per-sub guidance for required headings.

## 3. Body skeleton (works in most subs)

```
Hi r/<sub> — I'm the maintainer of <project>.

**What it is:** <one sentence, plain language>

**Why it exists:** <one sentence, the gap it fills>

**What's new in <version>:** (only for release posts)
- <bullet>
- <bullet>

**Stack:** <relevant tech that the sub cares about>

**Status:** <alpha/beta/stable>, <license>

**Repo:** <link>
**Docs / demo:** <link if any>

Happy to answer questions or take feedback.
```

Drop sections that don't apply. Never pad.

## 4. Per-sub quick reference

| Sub | Self-promo OK | Link or self | Flair | Tone |
|---|---|---|---|---|
| r/matrixprotocol | yes | self | none | technical, MSC-aware (see ref) |
| r/matrixdotorg | yes | self | none | user-friendly (see ref) |
| r/selfhosted | yes if self-hostable | self | yes (`Release`, `Self Promo`) | what does it self-host, license, deploy method |
| r/programming | yes if substantive | self or link | none | no "I made" titles — describe the thing |
| r/opensource | yes | self | yes | license, contribution model |
| r/SideProject | yes | self | none | revenue/audience honesty welcome |
| r/coolgithubprojects | yes | link to GH | language flair | terse, repo-link-driven |
| r/rust | yes | self | `project`, `announcement` | tech depth, no-unsafe boasts welcome |
| r/golang | yes | self | none | minimalism, dependencies count |
| r/python | yes | self | none | venv/install path, supported pythons |
| r/AndroidDev | yes if dev tool | self | none | min SDK, Compose vs Views |
| r/Android | end-user apps only | self | none | Play / F-Droid links, screenshots |
| r/privacy | yes if privacy-relevant | self | yes | threat model, what it protects against |
| r/Tor | yes if Tor-related | self | none | onion address if any, `.onion` v3 only |
| r/GrapheneOS | yes if Graphene-relevant | self | none | factual, no "more secure than X" claims |
| r/commandline | yes | self | none | screencast or asciinema preferred |
| r/linux | yes if Linux-native | self | yes | distro coverage |

For r/matrixprotocol / r/matrixdotorg, **always read** `references/matrix-subs.md` — they have specific MSC and TWIM-coordination conventions.

## 5. Refusals

Refuse to draft:

- **Vote manipulation** — multiple accounts, bot upvotes, "post and DM your friends to upvote".
- **Stealth marketing** — undisclosed maintainer posts, fake "I found this cool tool" framing.
- **Cross-sub identical copies** — propose distinct drafts instead.
- **Posts to subs the user has never participated in** without warning them about karma/age filters.

## 6. After drafting

End with a 3-line review checklist:

```
Before posting:
- [ ] Read the sub's rules sidebar one more time.
- [ ] Check if the sub has a "Showcase Saturday" / "Self-Promo Sunday" thread.
- [ ] Confirm flair selection matches the post type.
```
