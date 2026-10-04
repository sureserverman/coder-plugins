// The stage-boundary note: when a refresh of planning.model shows the pinned plan
// at a (plan, stage) this session has not been reminded about, while it is in
// preflight, task or gate, one short user-role row goes to the end of the
// conversation with the run-to-completion rules. It is appended, never put in a
// system-prompt section: changing the system prompt rewrites the whole cached
// prefix, the most expensive request of a long execution session.
//
// This file builds the note and decides whether a model calls for one; it holds
// no `$`. The append itself runs at the end of model.ts's refresh, because the
// engine never follows `$` across an import, and a write made from the refresh's
// timer never reaches a state.set hook of the plugin's own.
//
// Every field comes from .claude/plan-progress.json or the plan file, both
// repo-controlled and possibly hostile, and this text is model-bound: each field
// passes through clean() (the classifier's own rule: whitespace flattened, cut)
// before it is placed, and the whole note through clean() again at NOTE_MAX.

import type { PlanDetail, PlanGroup, PlanModel } from '../../types'

export const NOTE_MAX = 600
export const NOTED_KEEP = 50
const FIELD_MAX = 80
const ACTIVE_PHASES = ['preflight', 'task', 'gate']
// Every control character, C1 included, and the invisible ones that reorder or hide
// text (bidi overrides and isolates, zero-width marks); whitespace among them
// becomes a space first. A lone surrogate becomes U+FFFD, as Python's
// encode("utf-8", "replace") does in clean().
const CONTROL = /[\x00-\x1f\x7f-\x9f\u200b-\u200f\u202a-\u202e\u2066-\u2069]/g
const SPACE = /[\s\x85]+/g
const LONE_SURROGATE = /[\ud800-\udbff](?![\udc00-\udfff])|(?<![\ud800-\udbff])[\udc00-\udfff]/g
const KEY_MAX = 200

// plan_continue_classify.py's clean(), for text this side builds: whitespace runs
// flattened to one space (a newline lets planted text leave its sentence), other
// controls dropped, and the result cut to `limit` UTF-16 units on a code point.
export function clean(value: unknown, limit: number): string {
  const raw = typeof value === 'string' ? value : value == null ? '' : String(value)
  const text = raw.replace(LONE_SURROGATE, '\ufffd').replace(SPACE, ' ').replace(CONTROL, '').trim()
  if (text.length <= limit) return text
  let out = ''
  for (const ch of text) {
    if (out.length + ch.length > limit - 1) break
    out += ch
  }
  return `${out}…`
}

export function stageNote(pinned: PlanGroup, detail: PlanDetail | null): string {
  const plan = clean(pinned.name, FIELD_MAX)
  const number = typeof pinned.stage === 'number' ? pinned.stage : null
  const entry = number === null ? undefined : detail?.stages.find(s => s.number === number)
  const stageName = clean(entry?.name, FIELD_MAX)
  const where =
    number === null ? `plan "${plan}"` : `plan "${plan}", Stage ${number}${stageName === '' ? '' : ` ("${stageName}")`}`
  return clean(
    `[planning] Now executing ${where}. Run to completion: finish this stage and go straight on to the next; ` +
      'never end a turn on an announcement, the tool call that starts announced work goes in the same turn; ' +
      'stop only with an `ACTION NEEDED:` block, a documented Stop condition, or a `handoff` verdict from ' +
      'context-usage.py run after a gate.',
    NOTE_MAX,
  )
}

// The note a freshly refreshed model calls for, keyed by (plan, stage); null when
// there is no pinned plan or it is not in preflight, task or gate.
export function noteFor(model: PlanModel): { key: string; note: string } | null {
  if (!Array.isArray(model.groups)) return null
  const pinned = model.groups.find(g => g?.role === 'pinned')
  if (pinned === undefined) return null
  if (!ACTIVE_PHASES.includes(String(pinned.phase ?? '').toLowerCase())) return null
  const stage = typeof pinned.stage === 'number' ? pinned.stage : null
  // Held to KEY_MAX: the plan path is repo-controlled, and the key is stored.
  const plan = clean(typeof pinned.plan === 'string' ? pinned.plan : pinned.name, KEY_MAX)
  return {
    key: JSON.stringify([plan, stage]),
    note: stageNote(pinned, model.detail ?? null),
  }
}
