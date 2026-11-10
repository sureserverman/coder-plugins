---
name: hackernews-show-hn
description: Drafts a Hacker News "Show HN" submission for a project that readers can run, install, or use today. Triggers on "draft a Show HN", "post on Hacker News", "submit to HN", or "hackernews submission" — encodes Show HN eligibility, title rules, and first-comment conventions.
disable-model-invocation: true
---

# hackernews-show-hn

Drafts a Show HN submission and the maintainer's first follow-up comment.

## Eligibility

Per `news.ycombinator.com/showhn.html`:

- The thing must be **finished enough for users to try it now.** A landing page, waitlist, demo video without a live demo, or pre-launch announcement is **not** Show HN.
- It must be the user's own work, or their team's.
- Don't post the same project as Show HN twice in a short period.

If the project doesn't meet these, draft a regular HN submission instead and say so in the output.

## First comment

For a link with comments, the HN FAQ says to submit the link, then add a regular comment (checked 2026-11-10, https://news.ycombinator.com/newsfaq.html). showhn.html does not say whether Show HN takes text, so by convention the text field stays blank and context goes in the first comment.

## Output format

```
TITLE (paste into "title" field):
Show HN: <project> – <one-line>

URL (paste into "url" field):
<link>

(Leave the text field blank by convention; context goes in the first comment.)

FIRST COMMENT (post immediately after submission):
---
<comment body>
---
```

If Show HN isn't the right format:

```
TITLE: <descriptive title without "Show HN" prefix>
URL: <link to article / repo / demo>
```
