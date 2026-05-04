---
name: hackernews-show-hn
description: Drafts a Hacker News "Show HN" submission for a project that readers can run, install, or use today. Triggers on "draft a Show HN", "post on Hacker News", "submit to HN", "Show HN for my project", "HN launch post", "hackernews submission", or any request to write an HN announcement. Encodes Show HN guidelines (must be a usable thing, not vapor or a blog post), title rules, first-comment conventions, and what dang's mods will downweight or rename.
---

# hackernews-show-hn

Drafts a Show HN submission and the maintainer's first follow-up comment.

## 1. Show HN eligibility

Per the official HN Show HN guidelines (`news.ycombinator.com/showhn.html`):

- The thing must be **finished enough for users to try it now.** A landing page, waitlist, demo video without a live demo, or pre-launch announcement is **not** Show HN. It will be renamed by mods or buried.
- It must be your own work, or your team's. Don't post other people's stuff as Show HN.
- Don't post the same project as Show HN twice in a short period. Major version bumps are sometimes acceptable, but don't make it a habit.
- Show HN is for things you've **made**, not things you've **read** or **think are cool**. Articles go as a regular submission.

If the project doesn't meet these, draft a regular HN submission (link to repo / blog post) instead — say so explicitly in the output.

## 2. Title rules

HN titles are heavily moderated. Format:

```
Show HN: <project> – <one-line value prop>
```

- **Use the en-dash `–` or hyphen `-`** between project and tagline. The "Show HN: " prefix is automatically rendered specially.
- **No version numbers** in the title. `Show HN: Foo 2.0 – …` gets trimmed to `Show HN: Foo – …`.
- **No marketing words.** dang has personally renamed titles containing "the best", "revolutionary", "amazing", "blazing fast". Don't include them.
- **No emoji, no all-caps.**
- **Max ~80 chars** for full mobile rendering, hard cap 80 by HN.
- **Describe what it is**, not what it isn't. `Show HN: A self-hosted Matrix homeserver in Rust` works. `Show HN: Synapse but not Python` does not.

## 3. URL choice

Show HN posts can link to:

- A **live demo** — best if interactive.
- A **GitHub / source repository** — fine, very common.
- A **product/landing page** — only if it has install instructions and links to source. Pure marketing pages get downvoted.

Order of preference: live demo → repo → product page.

## 4. The maintainer's first comment

By convention the maintainer posts the first comment immediately after submission. This is where context lives because Show HN doesn't have a body field for self-posts (Show HN posts are always link-posts).

First-comment skeleton:

```
Hi HN — I'm <name/handle>, maintainer of <project>.

<2–4 paragraph backstory>:
- What gap it fills / why I built it.
- How it works at a high level (one paragraph of architecture).
- What's there now vs. what's coming.

Stack: <relevant tech>.

License: <SPDX>.

Would love feedback, especially on <specific area>. Happy to answer questions.
```

Total length: 150–400 words. Longer comments get skimmed.

## 5. What HN reacts well to

- **Concrete technical details.** Architecture diagrams, dependency counts, performance numbers with methodology, MSRV, supported platforms.
- **Honest limits.** "Doesn't do X yet" is welcomed; vagueness is punished.
- **A working demo link.** One-click try beats a setup wall.
- **License clarity.** State the license. AGPL/SSPL/source-available distinctions matter to this audience.

## 6. What HN reacts badly to

- **Closed-source-but-"open"** framing.
- **Pricing reveal in the title** ("Show HN: X, free for solo devs"). Move pricing into the comment.
- **AI-generated copy.** This audience can spot it. Write the post yourself.
- **Promising features that aren't shipped.** They will be tested live.
- **Defensive responses to critical comments.** Take feedback or stay quiet; arguing is the worst-rated behavior on HN.

## 7. Timing

- **Best windows (UTC):** Tuesday–Thursday, 13:00–17:00 UTC. Weekend traffic is lower.
- Don't post the same project at multiple times (HN throttles).
- Re-post after weeks/months only if there's substantive new news.

## 8. Output format

```
TITLE (paste into "title" field):
Show HN: <project> – <one-line>

URL (paste into "url" field):
<link>

(HN doesn't take a body for Show HN — leave the text field blank.)

FIRST COMMENT (post immediately after submission):
---
<comment body>
---

POST-SUBMISSION CHECKLIST:
- [ ] Verify the URL is reachable from a fresh browser.
- [ ] Confirm the repo README has install/run instructions visible above the fold.
- [ ] Be available for ~2 hours after posting to answer questions.
- [ ] Don't argue with critics; thank them and move on.
```

## 9. If Show HN isn't the right format

Output a regular submission template instead:

```
TITLE: <descriptive title without "Show HN" prefix>
URL: <link to article / repo / demo>

NO COMMENT REQUIRED — but a first technical comment with context still helps.
```
