---
name: skill-development
description: Covers authoring, reviewing, and auditing Claude Code skill files (SKILL.md). Triggers on "write a skill", "create a SKILL.md", "improve this SKILL.md", "skill description triggering", "skill not loading", "skill fires but runs wrong logic", "description leak", "skill description leak", "progressive disclosure", "skill too long", "injection in skill", "skill security", "skill frontmatter", "skill anatomy", or any request to create, restructure, or security-audit a skill. Also triggers on skill description rewrites and "is this description safe".
---

# skill-development

Canonical rules for authoring, reviewing, and security-auditing Claude Code `SKILL.md` files.
Consult the `references/` files when a topic goes deep.

## Reference map

| When you're… | Read first |
|---|---|
| Rewriting or auditing a description | `references/description-style.md` |
| Checking a skill for injection or leak risk | `references/leak-and-injection.md` |

---

## 1. Skill anatomy

A skill is a directory `skills/<name>/` containing `SKILL.md` and optional subdirs:

```
skills/
  my-skill/
    SKILL.md          ← required
    references/       ← deep content, one level only
    scripts/          ← executable utilities
    assets/           ← non-code resources (also: templates/)
```

**`SKILL.md` frontmatter** (between `---` fences):

| Field | Required | Rules |
|---|---|---|
| `name` | yes | Must match the directory name exactly. |
| `description` | yes | Trigger-spec only — see §2. Hard cap 1024 chars. |
| `allowed-tools` | no | Restricts tools when this skill is active. Use rarely. |

No `version` field in frontmatter.

**Body structure:**

1. One-sentence purpose (do not restate the description).
2. Reference map table — one row per `references/` file, if any exist.
3. Skill content.

---

## 2. Description rules (security-critical)

See `references/description-style.md` for worked examples and before/after rewrites.

### 2.1 Third-person only

Wrong: "I help you write skills..." or "You should trigger this when..."
Right: "Covers authoring and reviewing Claude Code skill files..."

Mixed or first-person POV degrades trigger matching (Anthropic-confirmed).

### 2.2 Trigger-spec, not summary

The description must answer only: *when should this skill fire?*

Pattern:
```
[What it does in one phrase]. Triggers on "exact phrase 1", "exact phrase 2",
..., or [other concrete signal].
```

Front-load the most discriminating trigger phrases — the harness allocates
roughly 1536 chars per skill entry when many skills are loaded, and clips from
the tail.

### 2.3 Hard cap: 1024 characters

Effective cap is tighter under load. Count characters before committing. If
over cap, cut worked examples and summaries first — never cut trigger phrases.

### 2.4 Description-leak hazard (silent failure)

If the description contains a procedure ("First X, then Y..."), Claude may
execute the description and skip the body entirely. The skill appears loaded
but runs a truncated version of its own trigger spec.

**Symptom:** skill produces output that looks like a paraphrase of its
description, not the detailed logic in the body.

**Fix:** description = trigger spec only. All procedure lives in the body or
in `references/`.

Full audit checklist: `references/leak-and-injection.md §Leak`.

### 2.5 No user-controlled content in descriptions

Never embed user-controlled URLs, file paths, secret names, or env-var
contents in the description. Adversaries can plant prompt-injection there.
Details: `references/leak-and-injection.md §Injection`.

---

## 3. Progressive disclosure

### 3.1 Line limits

| Scope | Limit |
|---|---|
| `SKILL.md` | ≤500 lines (community hard cap); ≤200 for coder-plugins |
| Any single `references/` file | ≤300 lines recommended |

When a SKILL.md approaches the limit, split content into `references/`.

### 3.2 Reference file rules

- **One level deep only.** No `references/foo/bar.md`. Claude tends to `head -100`
  on deeply nested paths and misses the body.
- **Domain-split over generic.** `references/finance.md` + `references/sales.md`
  beats `references/details.md`.
- **TOC required** when a reference file exceeds 100 lines.
- **Mark intent in the reference map:** "Run `scripts/check.sh`" vs "See
  `references/patterns.md`" — the model behaves differently for each.

### 3.3 Subdirectory purposes

| Subdir | Contains |
|---|---|
| `references/` | Markdown deep-dives, looked up not executed |
| `scripts/` | Executable utilities (bash, python, etc.) |
| `assets/` or `templates/` | Non-code resources |

---

## 4. Injection safety

The SKILL.md body is injected into the system prompt. Treat any embedded
content as potentially adversarial.

**Hard rules:**

1. Never embed user-controlled URLs, file paths, or env-var contents in the
   skill body. Adversaries can plant instructions there.
2. Never embed content fetched at runtime (API responses, file contents from
   user repos) directly into skill text.
3. Skill body is static. Dynamic content belongs in tool output, not the body.

Pre-flight scanner: Repello SkillCheck (https://repello.ai/blog/claude-code-skill-security).

Required reading: Snyk ToxicSkills 2025 audit — found injection in 36% of
audited community skills (https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub).

Full checklist and injection vectors: `references/leak-and-injection.md §Injection`.

---

## 5. Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| First-person POV in description ("I help you...") | Degrades trigger matching |
| Description summarizes skill instead of triggering it | Triggers are missed; model reads summary instead of body |
| Description contains procedure ("First X, then Y") | Leak — model skips body and executes description |
| SKILL.md >500 lines without splitting references | Body is partially read or skipped |
| Nested references (`references/foo/bar.md`) | Partial reads; model misses content |
| Restating the description in the body's first paragraph | Token waste, no added value |
| Embedding user input or fetched content in skill body | Injection vector |

---


## 6. Common mistakes — worked examples


### Mistake 1: Weak Trigger Description

❌ **Bad:**
```yaml
description: Provides guidance for working with hooks.
```

**Why bad:** Vague, no specific trigger phrases, not third person

✅ **Good:**
```yaml
description: This skill should be used when the user asks to "create a hook", "add a PreToolUse hook", "validate tool use", or mentions hook events. Provides comprehensive hooks API guidance.
```

**Why good:** Third person, specific phrases, concrete scenarios

### Mistake 2: Too Much in SKILL.md

❌ **Bad:**
```
skill-name/
└── SKILL.md  (8,000 words - everything in one file)
```

**Why bad:** Bloats context when skill loads, detailed content always loaded

✅ **Good:**
```
skill-name/
├── SKILL.md  (1,800 words - core essentials)
└── references/
    ├── patterns.md (2,500 words)
    └── advanced.md (3,700 words)
```

**Why good:** Progressive disclosure, detailed content loaded only when needed

### Mistake 3: Second Person Writing

❌ **Bad:**
```markdown
You should start by reading the configuration file.
You need to validate the input.
You can use the grep tool to search.
```

**Why bad:** Second person, not imperative form

✅ **Good:**
```markdown
Start by reading the configuration file.
Validate the input before processing.
Use the grep tool to search for patterns.
```

**Why good:** Imperative form, direct instructions

### Mistake 4: Missing Resource References

❌ **Bad:**
```markdown
# SKILL.md

[Core content]

[No mention of references/ or examples/]
```

**Why bad:** Claude doesn't know references exist

✅ **Good:**
```markdown
# SKILL.md

[Core content]

## Sources

- https://code.claude.com/docs/en/skills
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- https://repello.ai/blog/claude-code-skill-security
- https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub
- https://github.com/obra/superpowers (community skill-writing patterns)
- Vault: [[Claude Code Skill Description Leak]], [[Claude Code Plugins]]
