# Matrix subreddits

Two subs cover the Matrix ecosystem on Reddit. They overlap but have different audiences and tones.

## r/matrixprotocol

- **Audience:** developers, homeserver admins, MSC authors, bridge maintainers.
- **Expected content:** new servers/clients/bridges/SDKs, MSC discussions, federation issues, performance work, sliding-sync / Matrix 2.0 progress, encryption / device-verification work.
- **Tone:** technical. Assume readers know what a homeserver is, what a bridge does, and what `m.room.message` looks like.
- **Title pattern:** `<project> v<X.Y>: <feature/scope>` or `<project> — <one-line>`.
- **Body must include:**
  - Implementation language and runtime.
  - Spec compliance: which Matrix version, which optional features (E2EE, sliding sync, threads, voice/video).
  - Federation status (federates / doesn't / partial).
  - License.
  - Whether it's been submitted to TWIM (and link the TWIM entry once published).
- **Avoid:**
  - "Matrix is the future of chat" framing — readers already agree, it reads as filler.
  - Claims of being "the first" — almost always wrong; check matrix.org/ecosystem first.
  - Comparisons to Element/Synapse without specifics.

## r/matrixdotorg

- **Audience:** end users, self-hosters, people evaluating Matrix vs Discord/Slack, sysadmins running Element for a community.
- **Expected content:** new clients with a UI to look at, hosted-server announcements, integration guides, "I migrated my community from X to Matrix" stories, user-facing feature releases.
- **Tone:** user-friendly. Screenshots help. Plain-English explanations of what changed.
- **Title pattern:** `<project>: <user-visible benefit>` or `<thing> for Matrix users — <what it does>`.
- **Body must include:**
  - One-paragraph plain-English summary.
  - Screenshots or a short demo video link if it's a client/UI thing.
  - How to try it (hosted demo, install command, F-Droid / Play / direct download).
  - License.
- **Avoid:**
  - Posting MSC-spec discussion here — wrong audience, send it to r/matrixprotocol.
  - Linking only to a GitHub README with no screenshots for a client.

## Cross-posting rule

Do **not** cross-post the same body to both subs. Either:

- Write a developer-flavored post for r/matrixprotocol and a user-flavored post for r/matrixdotorg, **or**
- Pick one sub based on which audience the release primarily serves, and skip the other.

Lazy duplicate posts get noticed by the moderators of both communities (small ecosystem; same people moderate adjacent spaces).

## TWIM coordination

If the project is going into the next This Week in Matrix:

- Submit to TWIM **first** (see the `twim-submission` skill).
- Wait until TWIM publishes (Fridays).
- Then post to the relevant subreddit, and link the TWIM entry from the body. This routes traffic and adds credibility.

If the project is too early or too small for TWIM, posting directly to r/matrixprotocol is fine. Do not pretend it was in TWIM if it wasn't.

## Matrix-specific moderation pitfalls

- **Onion-only links** — fine to include alongside a clearnet repo, but don't make a `.onion` the primary link.
- **"Element fork" posts** — always disclose fork lineage in the body and link to the upstream commit you forked at.
- **Bridge posts** — name the protocol you bridge, the puppeting model (single-puppet / double-puppet), and whether it's e2ee-aware.
