---
name: twim-submission
description: Drafts a This Week in Matrix (TWIM) submission entry for a Matrix-ecosystem project — a homeserver, client, bridge, bot, library, MSC, or hosting service. Triggers on "submit to TWIM", "draft a TWIM entry", "This Week in Matrix submission", "TWIM post", "submit my Matrix project", "matrix.org weekly", or any request to announce a Matrix-related release through the TWIM weekly digest. Encodes the matrix.org TWIM submission room workflow, expected structure, image and link conventions, and what gets edited or rejected.
---

# twim-submission

Drafts a TWIM entry. TWIM is the weekly Matrix newsletter published every Friday on matrix.org. Entries are submitted by posting in the TWIM submission room and tagging the editor.

## 1. How TWIM submission actually works

- **Submission room:** `#twim-submissions:matrix.org` (room alias). Join the room, paste the entry as a single message, optionally with images uploaded as attachments.
- **Editor mention:** the current TWIM editor (rotating; check the room topic) — mention them so they see it. Most weeks the room topic names the editor and the publish day.
- **Deadline:** Friday morning UTC for that week's edition. Earlier in the week is better.
- **Cadence:** one entry per project per release / milestone. Don't submit the same project two weeks in a row unless there's genuinely new news.
- **Editorial discretion:** the editor lightly edits for grammar, length, and consistency. Major rewrites get sent back. Submissions in plain English with concrete details usually go in untouched.

## 2. Categories used by TWIM

The editor places entries into sections. Match yours to one of:

- **Spec / Dept of Spec** — MSC progress, FCP, merges, new SCT activity.
- **Servers** — Synapse / Dendrite / Conduit / Conduwuit / etc. releases or feature work.
- **Clients** — Element X, Cinny, Fractal, gomuks, NeoChat, Fluffy, etc.
- **SDKs and Frameworks** — matrix-rust-sdk, matrix-js-sdk, mautrix-go, trixnity, etc.
- **Bridges** — mautrix-*, matrix-appservice-*, etc.
- **Bots** — moderation bots, integration bots, fun bots.
- **Encryption** — vodozemac, libolm successor work, key-backup, cross-signing.
- **Services** — hosted homeservers, integration providers, identity servers.
- **Dept of \*** — meta sections the editor names ad-hoc (Dept of Federation, Dept of Verification, etc).

If the project doesn't fit, name it in the submission and let the editor pick.

## 3. Required entry shape

Output a single block:

```
### <project name>

<one to four short paragraphs>

<links>
```

### Heading

- Use the project name only — no "v1.4 of …" or "Announcing …".
- The editor adds the section heading; you provide the project heading.

### Body

- **First paragraph: what changed this week.** One or two sentences. Concrete. "Added sliding sync support" beats "Improved performance".
- **Second paragraph (optional): why it matters.** Skip if the change speaks for itself.
- **Third paragraph (optional): what's next.** Roadmap teaser, what to expect next month.
- Total length: 60–250 words. Longer entries get trimmed.

### Tone

- Third-person works. First-person ("we shipped …", "I added …") also works and is common.
- Avoid superlatives ("blazing fast", "revolutionary"). The TWIM audience is technical and reacts negatively to marketing prose.
- Mention specific Matrix terms (sliding sync, MSC numbers, e2ee, cross-signing, threads, knocking, voice/video, MAS) where relevant.

### Links

- **Repo link** required.
- **Release notes / changelog** preferred over a bare repo link if it's a release.
- **Demo / hosted instance** if applicable.
- **Issue tracker or roadmap** if calling for contributions.
- Format as plain markdown links, one per line, at the bottom of the entry.

## 4. Images

- Upload images **as Matrix attachments to the submission room**, not inline URLs. The editor copies the `mxc://` URI into the post.
- One screenshot is plenty. Two if showing before/after. Three is excessive.
- Animated GIFs / short MP4s work for demos but keep them under ~5 MB.
- Always include alt text in the message body when describing the image.

## 5. MSC submissions

For Matrix Spec Change updates the format is slightly different:

```
### MSCxxxx: <title>

<status: open / FCP / merged / withdrawn>

<one paragraph on what changed since last week>

[MSCxxxx](https://github.com/matrix-org/matrix-spec-proposals/pull/xxxx)
```

Mention `@spec-bot` activity (`fcp` flags, `concerns`) where relevant.

## 6. Common edits / rejections

- Marketing language ("the best", "next-generation") gets cut.
- "We're excited to announce" gets cut to "We released".
- Dead links → submission held until fixed.
- Duplicate submissions in consecutive weeks without new news → editor asks you to skip a week.
- Off-topic posts (a non-Matrix project that happens to support Matrix as one of many backends) → may be declined.

## 7. After submission

The editor will react with 👍 or reply once the entry is queued. If you don't see acknowledgement by Thursday evening UTC, ping the editor in the room.

After the issue publishes:

- Post the TWIM permalink in your project's release notes / pinned chat / announcement channel.
- If you also post to r/matrixprotocol or r/matrixdotorg, link the TWIM entry from the body of that post.

## 8. Output format

Always emit:

```
SUGGESTED CATEGORY: <Servers / Clients / Bridges / Bots / SDKs and Frameworks / Encryption / Services / Spec / other>

ENTRY (paste this into #twim-submissions:matrix.org):
---
### <project>

<body paragraphs>

<links>
---

IMAGES TO ATTACH:
- <description of screenshot 1>
- <description of screenshot 2 (if any)>

EDITOR PING: mention the editor named in the room topic.
SUBMIT BY: Friday <UTC date>, earlier in the week if possible.
```
