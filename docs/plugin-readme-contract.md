# Plugin README contract

Every plugin in this marketplace ships a `README.md` that documents **how to use
every component it ships**. This file is the spec, and
`scripts/check-doc-coverage.py` enforces the mechanical half of it in CI.

## Who a plugin README is for

Two readers, with different needs, and the second is the one currently underserved:

1. **Deciding whether to install.** Wants the one-paragraph pitch and the component
   list. Served by a good lead and a table.
2. **Has installed, needs to use a specific component.** Wants to know how a
   component fires, what arguments it takes, what it writes to disk, and what it
   needs to exist first. This reader is why the contract exists.

A README that only serves reader 1 looks complete — it names everything — while
leaving reader 2 to open `SKILL.md` and reverse-engineer the interface.

## The anti-goal: do not restate frontmatter descriptions

A component's `description:` is a **≤300-character triggering hint written for the
model**, budget-capped because every enabled plugin's descriptions are injected
into context at session start (see the root README's "Description budget"). It is
not usage documentation, and copying it into the README produces the exact
failure this contract targets: a README that names every component and explains
none.

Write for a human who has already decided to use the thing.

## Required sections

### 1. Lead — one paragraph

What the plugin gets you, in prose. Name the shape (pipeline, knowledge-router +
expert agent, a set of independent skills) because that shape tells the reader how
the pieces relate.

### 2. Install

```text
/plugin install <name>@coder-plugins
```

Plus any prerequisite that is not a plugin: an external CLI, an API key, a sibling
repo, a configured vault. If the plugin is useless without it, it belongs here, not
in a footnote.

### 3. Every component, under its own heading

**Every** shipped skill, command, and agent — and every non-frontmatter component
too: a `hooks/` registration, a `.mcp.json`, and a plugin-root `scripts/validate.sh`
determinism lane. Those three are the easiest to forget precisely because they carry
no frontmatter and never show up in a component listing; four plugins shipped an
undocumented lane, and the one plugin that ships a hook runs it on **every session
start** without being asked. The coverage guard checks that each component's name
appears; the contract asks for more than an appearance:

| Must state | Why |
|---|---|
| **What it does** | One or two sentences, concrete. |
| **How it fires** | Automatic on context match (give the real trigger phrases), explicit as `/<plugin>:<skill>`, a slash command, or agent delegation. These are genuinely different and users guess wrong. |
| **Arguments / subcommands** | The actual surface: `portfolio scan\|unify\|maturity\|migrate\|integrate\|rebuild`, `compass now\|next\|review`. A subcommand that exists only in `SKILL.md` is undiscoverable. |
| **Artifacts written, and where** | The single most-asked question about any skill that persists state. Absolute or clearly-rooted paths — say when something lands in the vault rather than the repo. |
| **Prerequisites** | Config files, other plugins, external tools, an attached device. |

Note **dispatch-only** components (`disable-model-invocation: true`) explicitly:
they are reachable only through their orchestrator, never by direct invocation, and
a reader who tries and fails will assume the plugin is broken.

### 4. A worked example

One realistic end-to-end sequence with real commands and a sentence on what
happens between them. Not a diagram — a transcript-shaped walkthrough.

### 5. Cross-links

Which sibling plugins this one hands off to or expects. Components in this
marketplace compose; a README that presents its plugin as an island misrepresents it.

## What the guard checks, and what it cannot

`scripts/check-doc-coverage.py` verifies:

- every plugin in `marketplace.json` has a `README.md`;
- every component on disk has its name present in that README —
  skills/agents/commands per `_frontmatter_common.PATTERNS`, plus hooks,
  `.mcp.json`, and the `scripts/validate.sh` lane, excluding `/tests/` and
  `/fixtures/`;
- the README is not a stub, relative to its component count.

It **cannot** tell a real usage section from a name in a bullet list. Coverage is
a floor, not a quality bar — a green guard means nothing is missing, not that
anything is well explained. Do not read it as more than that, and do not let an
allowlist entry stand in for writing the section.

Exceptions live in `scripts/doc-coverage-allow.txt`, one per line with a written
reason, exactly like `scripts/frontmatter-budget-allow.txt`.
