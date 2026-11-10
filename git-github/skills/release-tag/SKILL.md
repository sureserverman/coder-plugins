---
name: release-tag
description: >
  Use when the user explicitly asks to cut a release tag — "tag a
  release", "cut v1.4.0", "create a release tag", "draft release notes
  from the changelog". Asks before tagging and again before pushing. Does
  NOT trigger on its own, does NOT force-push, does NOT delete or move
  existing tags.
---

# Release Tag

Cut an annotated tag for a release and, optionally, a matching GitHub release.
Fires only on an explicit request.

## Owner rules

- **Ask before tagging.** Show the tag name, the SHA it will point at, the full
  message, and whether a GitHub release follows. Wait for an explicit "yes";
  silence is not consent.
- **Ask again before pushing.** The push is when the tag becomes shared state.
- **Push only the tag:** `git push origin <tag>`, never `git push --tags`
  (that pushes every local tag, including in-progress drafts).
- **Never move or delete a tag**, and never `-f`/`--force`. If the tag already
  exists locally or on origin, stop and ask whether they meant another version.
- Refuse on a dirty tree or off the default / release branch.
- Use a version the user gives verbatim; do not normalize it. Otherwise
  propose one from the CHANGELOG heading or the next semver bump, and ask.
- No `-s` unless the user has signing set up and asked for it.

## Tag message

Source it from the top CHANGELOG entry for this version, verbatim. Without
one, use the commits since the last tag (grouped by Conventional Commits prefix
if the log uses them). With only a commit or two, say the notes are thin; do not
invent any.

```
<one-line summary>

<grouped or flat bullets>

<attribution trailer>
```

The trailer is optional; when used, it follows the session's own commit
attribution, not a fixed model name. Match the style of prior tag messages
(`git for-each-ref --format='%(contents)' refs/tags/<last-tag>`).

## Procedure

1. Confirm (gate 1), then `git tag -a "<tag>" -m "<message>"`.
2. Show `git show <tag> --stat --no-patch`.
3. Confirm (gate 2), then `git push origin "<tag>"`.
4. If `gh` is available, the remote is github.com, and the user wants a
   release: `gh release create "<tag>"` with the same notes. Add `--draft`
   only if asked, `--prerelease` for `-rc`/`-beta`/`-alpha`; no `--target`;
   attach assets only if asked. If `gh` is missing or the remote is not GitHub,
   skip this step; the tag stands alone.
5. Report the tag, SHA, push state and release URL.

## After the tag

Suggest, do not run: `/promote-release <tag>` if the `release-promo` plugin is
installed (this skill drafts no announcements), and a working-version bump in
`Cargo.toml` / `package.json` / `pyproject.toml` / `build.gradle*`.
