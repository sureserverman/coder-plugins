// The run-to-completion Stop check on Claude Code 2.1.288+: the mod's answer to
// classic.Stop, opt-in exactly like the command hook (PLAN_CONTINUE=1). The decision
// is plan_continue_classify.py's — the same module the command hook imports — and
// so is the repo-root boundary (`--root`). This file only gathers the inputs: the
// last assistant message (on the event, no transcript to tail), the state file
// (read only when its realPath lies under that root) and the no-progress count,
// kept in $.state so a hot reload does not reset it.
//
// It always passes the event on, marked planning_mod_handled: the user's own Stop
// hooks still run (answering without next would skip them all), and the command
// hook, seeing the mark, steps aside instead of deciding twice. Every failure
// allows: a Stop hook that fails closed traps the session.

import { atom, read, update } from 'claude-code'
import type { EngineInterface, On } from 'claude-code'

import type { StopCounter } from '../../types'

const COUNTER = atom({ plugin: 'planning', key: 'stopCounter' } as const, null as StopCounter | null)

const CLASSIFIER = 'hooks/plan_continue_classify.py'
const CONTEXT_USAGE = 'skills/executing-plans/scripts/context-usage.py'
const TIMEOUT_MS = 5000
const MAX_STATE_BYTES = 256 * 1024
const MAX_TEXT_BYTES = 2048
const DEFAULT_MAX = 3
// Newlines stay (the reason's paragraphs); every other control character goes.
const CONTROL = /[\x00-\x09\x0b-\x1f\x7f-\x9f]/g

type Decision = { decision: string; reason?: unknown; system_message?: unknown; notice?: unknown }

const ALLOW: Decision = { decision: 'allow' }

// Model-bound or user-visible text from the classifier, held again on this side:
// control characters out, at most MAX_TEXT_BYTES of UTF-8, cut on a character.
export function bounded(text: unknown): string {
  const flat = (typeof text === 'string' ? text : '').replace(CONTROL, '')
  const encoder = new TextEncoder()
  if (encoder.encode(flat).length <= MAX_TEXT_BYTES) return flat
  let out = ''
  let used = 0
  for (const ch of flat) {
    const size = encoder.encode(ch).length
    if (used + size > MAX_TEXT_BYTES - 3) break
    out += ch
    used += size
  }
  return `${out}…`
}

function parse(stdout: string): unknown {
  try {
    return JSON.parse(stdout)
  } catch {
    return null
  }
}

async function runPython($: EngineInterface, args: string[], input: unknown): Promise<unknown> {
  const ran = await $.process.run(['python3', '-I', `${$.plugin.root}/${CLASSIFIER}`, ...args], {
    stdin: JSON.stringify(input),
    timeoutMs: TIMEOUT_MS,
  })
  return ran.exitCode === 0 ? parse(ran.stdout) : null
}

function under(path: string, root: string): boolean {
  return path.startsWith(root.endsWith('/') ? root : `${root}/`)
}

async function decide($: EngineInterface, lastText: unknown): Promise<Decision> {
  if (typeof lastText !== 'string' || lastText.trim() === '') return ALLOW

  const cwd = await $.session.cwd()
  const found = (await runPython($, ['--root'], { cwd })) as { root?: unknown } | null
  if (typeof found?.root !== 'string' || found.root === '') return ALLOW
  const root = (await $.fs.stat(found.root, { resolve: true })).realPath
  if (root === undefined) return ALLOW

  const file = await $.fs.stat(`${root}/.claude/plan-progress.json`, { resolve: true })
  if (file.kind !== 'file' || file.size > MAX_STATE_BYTES) return ALLOW
  if (file.realPath === undefined || !under(file.realPath, root)) return ALLOW
  const state = parse(await $.fs.read(file.realPath))
  if (state === null || typeof state !== 'object' || Array.isArray(state)) return ALLOW

  const s = state as Record<string, unknown>
  const key = ['phase', 'stage', 'task'].map(k => String(s[k] ?? '')).join('|')
  const counter = await read($, COUNTER)
  const count = counter !== null && counter.key === key ? counter.count : 0
  const max = Number.parseInt((await $.env.get('PLAN_CONTINUE_MAX')) ?? '', 10)

  const result = (await runPython($, [], {
    state,
    last_text: lastText,
    count,
    max: Number.isFinite(max) ? max : DEFAULT_MAX,
    context_usage_path: `${$.plugin.root}/${CONTEXT_USAGE}`,
    check_updated: true,
  })) as Decision | null
  if (result === null || typeof result !== 'object') return ALLOW

  // Counted exactly when the command hook counts: a block, or a guard release.
  if (result.decision === 'block' || typeof result.system_message === 'string') {
    await update($, COUNTER, () => ({ key, count: count + 1 }))
  }
  return result
}

export function registerStop(on: On): void {
  on('classic.Stop', async ($, e, next) => {
    let optedIn = false
    try {
      optedIn = (await $.env.get('PLAN_CONTINUE')) === '1'
    } catch {
      optedIn = false
    }
    if (!optedIn) return next(e)

    let decision: Decision = ALLOW
    try {
      decision = await decide($, e.last_assistant_message)
    } catch {
      decision = ALLOW
    }

    const below = await next({ ...e, planning_mod_handled: true } as typeof e)

    // The command hook's systemMessage: one dim transcript line, never sent to the model.
    const note = typeof decision.system_message === 'string' ? decision.system_message : decision.notice
    if (typeof note === 'string' && note !== '') {
      try {
        $.ui.log(bounded(note))
      } catch {
        // a notice that cannot be shown changes no decision
      }
    }

    if (decision.decision !== 'block' || typeof decision.reason !== 'string' || decision.reason === '') return below
    if (typeof below.block === 'string' && below.block !== '') return below
    return { ...below, block: bounded(decision.reason) }
  })
}
