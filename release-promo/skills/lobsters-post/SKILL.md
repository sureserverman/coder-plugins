---
name: lobsters-post
description: Drafts a Lobsters submission for a software release, library, or substantive technical write-up. Triggers on "post on Lobsters", "submit to lobste.rs", "draft a Lobsters submission", "share on Lobsters", or any request to announce a project on Lobsters. Encodes Lobsters tag selection, the show/ask convention, the invite-only culture, what gets flagged or merged, and the user's responsibility to be a participating community member rather than a drive-by submitter.
---

# lobsters-post

Drafts a Lobsters submission. Lobsters is invite-only (lobste.rs); the user must already have an account. If they don't, output an explicit note saying so and stop.

## 1. Account and invite check

Before drafting, the assistant should confirm:

- The user has a Lobsters account.
- The user has commented or posted on Lobsters before, or is willing to participate after submitting.

If neither is true, write nothing and explain: Lobsters punishes drive-by self-promo accounts. The user should comment on three or four other stories before posting their own, or pass on Lobsters and use HN / Reddit instead.

## 2. Submission type

| Type | Used for | Title prefix |
|---|---|---|
| Story | A linkable resource — repo, blog post, paper, release notes | none |
| `show` | Something the user made and wants feedback on | `show:` flair, set in the form |
| `ask` | A question to the community | `ask:` flair, set in the form |

For a release announcement, **prefer `show`** if there's something to try. Plain releases without a substantive write-up should not go to Lobsters at all — write a blog post first, then submit the blog post as a regular story.

## 3. Tag selection

Lobsters tags are limited to two per submission. Pick from the **actual current tag list at lobste.rs/tags** (the user should verify). Common relevant tags:

- Languages: `rust`, `go`, `python`, `c`, `cpp`, `java`, `ruby`, `js`, `dotnet`, `haskell`, `lisp`, `ml`.
- Topics: `release`, `practices`, `programming`, `compsci`, `formalmethods`, `distributed`, `networking`, `crypto`, `privacy`, `security`, `databases`, `vcs`, `web`, `mobile`, `linux`, `unix`, `bsd`, `osdev`, `hardware`, `audio`, `graphics`, `compilers`, `plt`, `ai`, `ml`.
- Special: `show` (for `show` type), `ask` (for `ask` type).

Rules:

- Two tags max. The system rejects three.
- The `show` / `ask` tag is automatic with the type — do not also pick it manually.
- Don't combine generic + generic (`programming` + `practices`). Pair specific + topical (`rust` + `release`).
- Don't use language tags as filler if the language isn't the point.

## 4. Title rules

- **Plain descriptive titles.** Lobsters strips marketing words harder than HN. "Announcing X 2.0" gets renamed to "X 2.0".
- **No "I made"** — use a noun-phrase title.
- Match the linked page's title where reasonable; the moderators sometimes rewrite to match.
- **Max ~100 chars.**

Good examples:

- `A Matrix homeserver in Rust`
- `vodozemac 0.7: Olm and Megolm reference implementation`
- `Lessons from running a public Synapse for five years`

Bad:

- `Show HN: …` (HN convention, not Lobsters)
- `Excited to announce …`
- `The Future of Decentralized Chat`

## 5. The "story text" field

Lobsters lets you add story text below the link. Use it sparingly:

- For a `show` submission: 2–4 sentences on what the project is, what state it's in, and what feedback you want.
- For a regular story: usually leave blank, or one sentence of context if the link doesn't make the relevance obvious.
- **Do not paste the entire blog post.** Lobsters punishes that.

## 6. Comment etiquette after submitting

- Reply to first technical questions within a few hours.
- If a moderator merges your story into an earlier one or asks for a tag change, do it without arguing.
- Do not ask for upvotes. Do not link your post anywhere with an "upvote on Lobsters" CTA. The community downweights this aggressively.

## 7. Cadence

- One submission per project per major version. No reposting the same v1.0 a week later.
- If a previous user already posted your project, comment on that thread instead of submitting again.

## 8. Output format

```
SUBMISSION TYPE: <story | show | ask>

URL: <link>

TITLE: <plain descriptive title>

TAGS: <tag1>, <tag2>   # two max; the show/ask tag is automatic

STORY TEXT (paste into the story_text field, may be blank):
---
<2–4 sentences for show; usually blank for plain story>
---

COMMENT-ENGAGEMENT PLAN:
- Be available for ~2 hours post-submission.
- Reply factually, not defensively.
- If a mod merges or retags, accept it.

PRE-SUBMISSION CHECKLIST:
- [ ] Account has prior comments / participation.
- [ ] Tags exist on lobste.rs/tags (don't invent).
- [ ] Title has no marketing words.
- [ ] No duplicate of a recent story (search lobste.rs first).
```

## 9. When to skip Lobsters

Skip and tell the user:

- The project is not technically substantive (e.g. yet-another-todo-list, no novel angle).
- The user has no Lobsters account or no prior participation.
- The release was already covered on Lobsters within the last six months.
- The project is closed-source without a written-up technical angle (Lobsters is mostly OSS-leaning; closed-source is fine if the post itself is technical writing about it).
