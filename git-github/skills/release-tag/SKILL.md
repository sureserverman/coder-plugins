---
name: release-tag
description: >
  Use when the user explicitly asks to cut a release tag — "tag a
  release", "cut v1.4.0", "create a release tag", "tag and release",
  "draft release notes from the changelog". Drafts an annotated tag
  message from the top CHANGELOG entry (or commits since the last tag),
  asks before tagging, asks again before pushing, and optionally creates
  a GitHub release via `gh release create`. Does NOT trigger on its own,
  does NOT force-push, does NOT delete or move existing tags.
---

# Release Tag

Cuts an annotated git tag for a release and (optionally) opens a matching
GitHub release. Two confirmation gates: one before `git tag`, one before
`git push --follow-tags`. Does the mechanical work locally rather than
dispatching a subagent — the steps are tightly sequenced and the user
needs to see and approve each one.

**Announce at start:** "Using the release-tag skill — let me scope the
release first."

## When NOT to use this skill

- The user did not explicitly ask to tag or release. This skill never
  fires proactively.
- The user wants to **delete** or **move** an existing tag. Re-tagging
  a published version is a destructive history rewrite and needs direct
  user-facing confirmation, not a skill.
- The current branch is not the repo's default / release branch. Tagging
  off a feature branch is almost always a mistake — refuse and tell the
  user.
- The working tree is dirty (uncommitted changes). Refuse — release tags
  must be reproducible from the committed tree.
- The remote isn't on github.com **and** the user asked for a GitHub
  release. The tag part still works; the `gh release create` step does
  not. Tell the user and offer to skip the release step.

## Scope (gather before drafting)

Run in parallel:

| Command | Used for |
|---|---|
| `git rev-parse --abbrev-ref HEAD` | Confirm we're on the default branch |
| `git status --short` | Confirm clean tree |
| `git describe --tags --abbrev=0 2>/dev/null` | Last release tag |
| `git tag --sort=-creatordate \| head -10` | Recent tags for style |
| `git log --oneline <last-tag>..HEAD` (or `git log --oneline -50` if no prior tag) | What's new |
| `git remote get-url origin` | GitHub vs other host |
| Read `CHANGELOG.md` / `CHANGES.md` / `HISTORY.md` if present | Curated notes |
| `gh repo view --json defaultBranchRef -q .defaultBranchRef.name` | Default branch |

If the user gave a version (`v1.4.0`, `1.4.0`, `2026.5.4`), use it
verbatim — do not normalize. If they did not, infer from the CHANGELOG
heading or propose the next semver bump and ask.

## Tag message draft

Annotated tags carry a message — that message is what tools (release-promo,
git log, GitHub releases) read later. Source it in this order:

1. **Top CHANGELOG entry** for this version, if one exists. Use it
   verbatim.
2. **Commits since last tag**, grouped by Conventional Commits prefix
   (feat / fix / docs / chore / refactor / perf / test / build / ci) if
   the repo's log already uses that pattern. Otherwise a flat bullet
   list.
3. If the user supplied a hint ("focus on the federation feature"),
   weave it into a one-line summary at the top.

Tag message shape:

```
<one-line summary>

<grouped or flat bullets>

<empty line>
Co-authored-by: Claude Haiku 4.5 <noreply@anthropic.com>
```

(Trailer is optional. Match the project's existing tag-message style if
prior tags have one — `git for-each-ref --format='%(contents)'
refs/tags/<last-tag>` shows it.)

## Procedure

1. **Show the user the draft.** Print:
   - the tag name,
   - the commit SHA it will point at (HEAD of default branch),
   - the full annotated message,
   - whether a GitHub release will be created (default: yes if `gh` is
     available and remote is github.com; ask if unsure).

   Wait for explicit "yes" / "go ahead". Do not infer consent from
   silence.

2. **Create the annotated tag.**
   ```bash
   git tag -a "<tag>" -m "$(cat <<'EOF'
   <message>
   EOF
   )"
   ```
   Do NOT use `-s` (signed) unless the user has signing configured AND
   asked for it. Do NOT use `-f` / `--force` ever in this skill.

3. **Show what was created.** Run `git show <tag> --stat --no-patch` and
   surface the SHA, message, and tagger to the user.

4. **Ask before pushing.** Push is the moment the tag becomes shared
   state. Do not push without a second explicit confirmation.

   ```bash
   git push origin "<tag>"
   ```

   Use `git push origin <tag>` (pushes only the tag), not
   `git push --tags` (pushes every local tag, which can leak in-progress
   tag drafts).

5. **Optional GitHub release.** If `gh` is available, remote is
   github.com, and the user said yes to a release, run:

   ```bash
   gh release create "<tag>" \
     --title "<title>" \
     --notes "$(cat <<'EOF'
   <release notes — same body as the tag message, or richer if a CHANGELOG section exists>
   EOF
   )" \
     <--draft if the user said draft> \
     <--prerelease if version contains -rc / -beta / -alpha>
   ```

   - Default to **non-draft, non-prerelease** unless flags fire.
   - Do NOT pass `--target` (the tag already pins the SHA).
   - Do NOT upload assets unless the user asked. If they did, list each
     `--attach <path>` separately and confirm each path exists.

6. **Report.** Surface:
   - tag name + SHA,
   - whether the tag is pushed,
   - GitHub release URL (if created),
   - any next-step suggestions (see below).

## After the tag is cut

Suggest, do not run, these follow-ups:

- **Promote the release.** If the `release-promo` plugin is installed,
  point at `/promote-release <tag>` for cross-platform announcement
  drafts.
- **Bump the working version.** If the project pins a version in
  `Cargo.toml` / `package.json` / `pyproject.toml` / `build.gradle*`,
  ask whether to bump it on the default branch for the next dev cycle.

Each is a separate user-confirmed action.

## Refusals and edge cases

- **Tag already exists locally or on origin.** Stop. Do not move it,
  delete it, or `--force`. Tell the user and ask whether they meant a
  different version.
- **Working tree dirty.** Stop. Release tags must point at a clean,
  committed state.
- **Wrong branch.** If `HEAD` isn't on the default / release branch,
  stop. Ask whether they meant to switch first.
- **No CHANGELOG and only one or two commits since last tag.** Don't
  invent release notes — use the commit list verbatim and tell the user
  the notes are thin.
- **`gh` missing or remote not GitHub.** Skip step 5; do not fail the
  whole flow. The annotated tag is still useful on its own.

## Reference

- **Pro Git, ch. 2.6 "Tagging"** —
  https://git-scm.com/book/en/v2/Git-Basics-Tagging (annotated vs
  lightweight, signed tags, pushing tags).
- **Semantic Versioning 2.0.0** — https://semver.org/ (when to bump
  major / minor / patch; how `-rc.N`, `-beta.N`, `-alpha.N` parse).
- **Keep a Changelog 1.1.0** — https://keepachangelog.com/ (the
  CHANGELOG format this skill reads from when present).
- **GitHub CLI manual** — https://cli.github.com/manual/gh_release_create
  (flags, draft / prerelease semantics, asset attachment).
- Global rule in `~/.claude/CLAUDE.md` and the Bash tool's git protocol:
  never `--force`, never push without asking, never rewrite shared
  history, always confirm before changing shared state.
