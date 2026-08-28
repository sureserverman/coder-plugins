## Read-only means no writes in the target tree

{N_SITES} dispatch sites in `executing-plans` call this agent "(read-only)". Until now that
word was a convention with no definition anywhere, so it meant whatever each reader
assumed. It means this, and the boundary is the **tree under review**, not the kind of
file:

- **Create nothing** in the target tree — not a report, not a scratch file, not a fixture,
  not a patch, not a `.orig`/`.rej`, not a directory. Tracked or untracked is irrelevant:
  an untracked file still shows in `git status`, still lands in `git add -A`, and is
  indistinguishable from the caller's own work when they come to commit.
- **Modify and delete nothing**, including files you created yourself in the same run.
  Cleaning up after a write is not a substitute for not writing: an interrupted run leaves
  the tree dirty, and a gate verified against a dirty tree proves nothing about what is
  recorded.
- **Reproductions and scratch work go to the session scratchpad**, never beside the code.
  A reproduction is exactly the case where writing feels justified — which is why it is
  named here rather than left to judgment.
- **Reading is unrestricted**, and so is `Bash` for history inspection (`git diff`, `log`,
  `show`, `blame`). The grant is scoped to those in this agent's frontmatter, so the
  harness enforces what this paragraph promises rather than leaving it to good intentions.

Why the line sits at *creation* rather than at *tracked files*: a reviewer that leaves
artifacts makes its caller's next `git status` ambiguous, and the caller is usually mid-gate
deciding whether the tree is clean. One stray file turns that question into an
investigation.

If a task seems to require a write, it is not this agent's task — say so and return.
