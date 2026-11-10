---
name: lobsters-post
description: Drafts a Lobsters submission for a software release, library, or substantive technical write-up. Triggers on "post on Lobsters", "submit to lobste.rs", "draft a Lobsters submission", or "share on Lobsters" — covers tag selection, the show/ask convention, and the invite-only culture.
disable-model-invocation: true
---

# lobsters-post

Drafts a Lobsters submission.

## Account and participation

Lobsters is invite-only (lobste.rs). Before drafting, confirm the user has an account and has commented or posted there before, or will participate after submitting. If neither is true, write nothing and explain: Lobsters punishes drive-by self-promo accounts. The user should comment on three or four other stories first, or skip Lobsters and use HN / Reddit instead.

A plain release with no write-up does not go to Lobsters; submit a blog post about it as a story instead.

## Tags

lobste.rs/about names no per-story tag cap (checked 2026-11-10, https://lobste.rs/about). Pick the fewest that fit from lobste.rs/tags; never invent one. The `show` / `ask` tag comes with the type.

## Output format

```
SUBMISSION TYPE: <story | show | ask>

URL: <link>

TITLE: <plain descriptive title>

TAGS: <tag1>, <tag2>   # fewest that fit; the show/ask tag is automatic

STORY TEXT (paste into the story_text field, may be blank):
---
<2–4 sentences for show; usually blank for plain story>
---

PRE-SUBMISSION CHECKLIST:
- [ ] Account has prior comments / participation.
- [ ] Tags exist on lobste.rs/tags (don't invent).
- [ ] No duplicate of a recent story (search lobste.rs first).
```
