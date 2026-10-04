// The live context window, for the two readers that want it: context-usage.py,
// through the sidecar .claude/plan-context.json, and the band, through
// planning.context. context-usage.py otherwise knows the window only from its
// model table, and an unknown model there leaves its handoff verdict `unknown`.
//
// This file only carries the engine's figures across. The verdict stays the
// script's (DEC-026): the sidecar names the window, and the script still counts the
// tokens from the transcript and applies its own rules. The sidecar is written at
// the end of each main-loop turn while the pinned plan is in preflight, task or
// gate, and never otherwise.
//
// The sidecar lives in a repo-controlled directory, so the write refuses a path it
// cannot vouch for: a `.claude` that resolves anywhere but inside the repo, or a
// sidecar that is a link or not a regular file. A swap between that check and the
// write is not closed here; the reader opens the file without following links.

import { atom, read, update } from 'claude-code'
import type { EngineInterface, On } from 'claude-code'

import type { ContextFigures, PlanModelState } from '../../types'

const MODEL = atom({ plugin: 'planning', key: 'model' } as const, null as PlanModelState | null)
const CONTEXT = atom({ plugin: 'planning', key: 'context' } as const, null as ContextFigures | null)

const STATE = '.claude/plan-progress.json'
const SIDECAR = '.claude/plan-context.json'
const ACTIVE_PHASES = ['preflight', 'task', 'gate']
// No repo is this deep; the walk stops here whatever it finds.
const MAX_DEPTH = 64

const count = (v: unknown): number | null =>
  typeof v === 'number' && Number.isSafeInteger(v) && v >= 0 ? v : null

// The engine's figures, held to what the readers accept: a window that is a
// positive whole number, else none at all.
export function figuresOf(usage: unknown): ContextFigures | null {
  const c = (usage as { context?: unknown } | null)?.context as Record<string, unknown> | undefined
  if (c === null || typeof c !== 'object') return null
  const window = count(c.window)
  if (window === null || window === 0) return null
  const percent = count(c.percent)
  return { window, tokens: count(c.tokens), percent: percent === null ? null : Math.min(percent, 100) }
}

// Whether the model shows a plan executing right now: the pinned plan, not stale,
// in a phase the executor writes while it works.
export function inFlight(state: PlanModelState | null): boolean {
  const pinned = state?.model?.groups?.find(g => g?.role === 'pinned')
  if (pinned === undefined || pinned.stale_hours != null) return false
  return ACTIVE_PHASES.includes(String(pinned.phase ?? '').toLowerCase())
}

// `2026-10-04T08:00:00Z`, the state file's own spelling of a time.
export const isoSeconds = (ms: number): string => new Date(ms).toISOString().replace(/\.\d{3}Z$/, 'Z')

const parentOf = (dir: string): string | null => {
  const cut = dir.lastIndexOf('/')
  if (cut < 0 || dir === '/') return null
  return cut === 0 ? '/' : dir.slice(0, cut)
}

const join = (dir: string, rest: string): string => (dir === '/' ? `/${rest}` : `${dir}/${rest}`)

// The repo root plan-progress.py reads the state from: the nearest directory at or
// above the working directory holding .claude/plan-progress.json. Resolved, so the
// checks below compare like with like.
async function stateRoot($: EngineInterface): Promise<string | null> {
  const cwd = (await $.fs.stat(await $.session.cwd(), { resolve: true })).realPath
  let dir: string | null = typeof cwd === 'string' && cwd.startsWith('/') ? cwd : null
  for (let depth = 0; dir !== null && depth < MAX_DEPTH; depth += 1) {
    const found = await $.fs.stat(join(dir, STATE)).catch(() => undefined)
    if (found?.kind === 'file') return dir
    dir = parentOf(dir)
  }
  return null
}

// Where the sidecar may be written, or null: `.claude` is the repo's own
// directory, and the sidecar, when there, is a regular file and no link.
async function sidecarPath($: EngineInterface, root: string): Promise<string | null> {
  const claude = await $.fs.stat(join(root, '.claude'), { resolve: true }).catch(() => undefined)
  if (claude === undefined || claude.isLink || claude.kind !== 'dir') return null
  if (claude.realPath !== join(root, '.claude')) return null
  const path = join(root, SIDECAR)
  const existing = await $.fs.stat(path).catch(() => undefined)
  if (existing !== undefined && (existing.isLink || existing.kind !== 'file')) return null
  return path
}

async function writeSidecar($: EngineInterface, figures: ContextFigures): Promise<void> {
  const root = await stateRoot($)
  if (root === null) return
  const path = await sidecarPath($, root)
  if (path === null) return
  const sidecar = {
    session_id: await $.session.id(),
    window: figures.window,
    tokens: figures.tokens,
    percent: figures.percent,
    updated: isoSeconds(await $.clock.now()),
  }
  await $.fs.write(path, `${JSON.stringify(sidecar)}\n`)
}

export function registerContext(on: On): void {
  // Main loop only: a subagent's turn reports its own loop, not the session's
  // window. Never throws: the turn has already ended.
  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    if (e.agentId !== undefined) return result
    try {
      const figures = figuresOf(await $.session.usage())
      await update($, CONTEXT, () => figures)
      if (figures !== null && inFlight(await read($, MODEL))) await writeSidecar($, figures)
    } catch {
      // no sidecar this turn; context-usage.py falls back to its table
    }
    return result
  })
}
