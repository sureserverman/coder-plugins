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
- **Reading is unrestricted**, and so is `Bash` for history inspection (`git status`,
  `diff`, `log`, `show`, `blame`) — the five this agent's frontmatter declares. **Treat
  that declaration as a rule you keep, not as a fence that holds you.** Measured
  2026-08-28: a sibling agent whose frontmatter scopes `Bash` the same way ran `ls` and
  wrote a file anyway, so scoped grants are not enforced on every host. An earlier draft
  of this bullet claimed the harness enforced them; that claim was false, and a contract
  that overstates its own enforcement is worse than one that admits it binds by obedience.
- **You do not run the code under review, and you do not reproduce.** A reproduction needs
  to execute the project and to write somewhere, and both are outside what this agent
  declares. If a finding can only be settled by running it, say so and hand it back.

Why the line sits at *creation* rather than at *tracked files*: a reviewer that leaves
artifacts makes its caller's next `git status` ambiguous, and the caller is usually mid-gate
deciding whether the tree is clean. One stray file turns that question into an
investigation.

If a task seems to require a write, it is not this agent's task — say so and return.
