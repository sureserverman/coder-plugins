# plugin.json — Full Field Reference

Every field the Claude Code plugin runtime reads from `plugin.json`. The file lives at `.claude-plugin/plugin.json` inside the plugin directory.

## Contents

- [Required fields](#required-fields) — `name`, `description`
- [Optional fields](#optional-fields) — `version`, `author`, `homepage`, `repository`, `license`, `keywords`, `skills`
- [Complete example](#complete-example)
- [marketplace.json — Full Schema](#marketplacejson--full-schema)
  - [Plugin entry fields](#plugin-entry-fields)
  - [Valid categories](#valid-categories)
  - [Tag guidance](#tag-guidance)

## Required fields

### `name`

Type: string  
Format: kebab-case  
Constraints: must be unique within any marketplace it is published to; becomes the namespace prefix for all skills (`<name>:<skill-name>`).

```json
"name": "rust-dev"
```

### `description`

Type: string  
One sentence. Shown in `/plugin list`, marketplace listings, and the install confirmation dialog.

```json
"description": "Idiomatic Rust authoring with skills, subagent, and slash commands."
```

## Optional fields

### `version`

Type: string  
Format: semver (`MAJOR.MINOR.PATCH`)  
Default: git commit SHA of the plugin directory at load time.

Set explicitly for any release that users will pin or reproduce. The commit-SHA fallback is adequate for local development but not for published plugins.

```json
"version": "1.4.2"
```

### `author`

Type: object

| Subfield | Type | Notes |
|---|---|---|
| `name` | string | Display name |
| `email` | string | Contact address |

```json
"author": {
  "name": "Jane Developer",
  "email": "jane@example.com"
}
```

### `homepage`

Type: string (URL)  
Linked from marketplace listings and `/plugin info <name>`.

```json
"homepage": "https://example.com/my-plugin"
```

### `repository`

Type: string (URL)  
Should point to the source repository root, not a subdirectory.

```json
"repository": "https://github.com/you/my-plugin"
```

### `license`

Type: string  
Use an SPDX identifier. The runtime does not validate this, but the marketplace indexer surfaces it to users.

```json
"license": "MIT"
```

Common values: `MIT`, `Apache-2.0`, `GPL-3.0-only`, `AGPL-3.0-only`, `MPL-2.0`, `ISC`.

### `keywords`

Type: array of strings  
Used for marketplace search. No enforced limit; keep to the most specific terms.

```json
"keywords": ["rust", "cargo", "linting", "refactor"]
```

### `skills`

Type: array of strings (paths relative to plugin root)  
Overrides or supplements auto-discovery. Rarely needed — use only when you want to control load order or include skills outside the standard `skills/` tree.

```json
"skills": [
  "skills/rust-coding/SKILL.md",
  "skills/rust-expert/SKILL.md"
]
```

When this field is present, its entries are loaded in order before auto-discovery runs for any paths not already listed.

## Complete example

```json
{
  "name": "rust-dev",
  "description": "Idiomatic Rust authoring with skills, subagent, and slash commands.",
  "version": "2.1.0",
  "author": {
    "name": "Jane Developer",
    "email": "jane@example.com"
  },
  "homepage": "https://example.com/rust-dev",
  "repository": "https://github.com/you/rust-dev",
  "license": "MIT",
  "keywords": ["rust", "cargo", "tokio", "clippy"],
  "skills": [
    "skills/rust-coding/SKILL.md",
    "skills/rust-expert/SKILL.md"
  ]
}
```

---

## marketplace.json — Full Schema

Lives at the **marketplace repository root** (not inside any individual plugin). One file lists all plugins the marketplace distributes.

```json
{
  "plugins": [
    {
      "name": "rust-dev",
      "source": "https://github.com/you/rust-dev",
      "description": "Idiomatic Rust authoring with skills, subagent, and slash commands.",
      "version": "2.1.0",
      "category": "languages",
      "tags": ["rust", "cargo", "linting", "refactor", "async", "tokio"]
    }
  ]
}
```

### Plugin entry fields

| Field | Required | Type | Notes |
|---|---|---|---|
| `name` | Yes | string | Must match the plugin's `plugin.json` `name` |
| `source` | Yes | string (URL) | Git-cloneable URL of the plugin repository |
| `description` | Yes | string | One sentence; may differ from plugin.json for marketing copy |
| `version` | Yes | string | Semver; pinned version the marketplace entry references |
| `category` | Yes | string | One of the valid category values below |
| `tags` | Yes | array | 4–8 lowercase strings |

### Valid categories

`development`, `languages`, `security`, `productivity`, `database`, `deployment`, `monitoring`, `design`, `learning`

### Tag guidance

Mix technology identifiers with capability words. Examples:
- `["rust", "cargo", "linting", "refactor", "async", "tokio"]`
- `["python", "typing", "mypy", "dataclasses", "testing"]`
- `["security", "audit", "sast", "secrets", "cve"]`

Avoid vague tags like `"tool"`, `"helper"`, `"utility"` — they do not aid search.
