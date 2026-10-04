import { expect, test } from 'claude-code/testing'
import type { On } from 'claude-code'

import type { PlanGroup } from '../../types'
import { figuresOf, isoSeconds } from './context'
import { group, ran, seed, world } from './testing'

const SESSION = 'session-abc'
const SIDECAR = '/repo/.claude/plan-context.json'
const USAGE = { window: 1_000_000, tokens: 250_000, percent: 25 }

type Entry = { kind: 'file' | 'dir' | 'other'; isLink?: boolean; realPath?: string }

// The file system beneath the mod, as stat sees it: a repo at /repo holding the
// state file, the session at /repo (testing.ts's world). `over` replaces or
// removes entries; `writeFails` refuses every write.
function disk(on: On, over: Record<string, Entry | null> = {}, writeFails = false) {
  const entries: Record<string, Entry | null> = {
    '/repo': { kind: 'dir' },
    '/repo/sub': { kind: 'dir' },
    '/repo/.claude': { kind: 'dir' },
    '/repo/.claude/plan-progress.json': { kind: 'file' },
    ...over,
  }
  const writes: { path: string; text: string }[] = []
  on('fs.stat', (_$, e) => {
    const entry = entries[e.path]
    if (entry == null) throw new Error(`ENOENT: ${e.path}`)
    return {
      value: {
        kind: entry.kind,
        size: 1,
        mtimeMs: 1,
        isLink: entry.isLink ?? false,
        ...(e.resolve ? { realPath: entry.realPath ?? e.path } : {}),
      },
    } as never
  })
  on('fs.write', (_$, e) => {
    if (writeFails) return { deny: 'EACCES' } as never
    writes.push({ path: e.path, text: e.text })
    return { value: undefined } as never
  })
  return writes
}

function engine(on: On, context: unknown = USAGE) {
  on('session.id', () => ({ value: SESSION }))
  on('session.usage', () => ({ value: { startedAt: 0, context, rateLimits: [] } }) as never)
  on('turn.complete', () => ({ text: '' }))
}

const turn = (over: Record<string, unknown> = {}) =>
  ({ answer: 'done', durationMs: 5, isAborted: false, turnId: 't1', reason: 'answer', ...over }) as never

function planned(groups: PlanGroup[]) {
  return () => ran(JSON.stringify({ groups, detail: null }))
}

async function setup($: unknown, on: On, groups: PlanGroup[], over: Record<string, Entry | null> = {}, context?: unknown) {
  const w = world(on, planned(groups))
  const writes = disk(on, over)
  engine(on, context)
  await seed($ as never, w.clock)
  return { w, writes }
}

test('a pinned plan in task: the sidecar carries the engine figures and this session', async ($, on) => {
  const { w, writes } = await setup($, on, [group({ phase: 'task' })])
  await $.turn.complete(turn())
  expect(writes.length).toBe(1)
  expect(writes[0]!.path).toBe(SIDECAR)
  const body = JSON.parse(writes[0]!.text)
  expect(body.session_id).toBe(SESSION)
  expect(body.window).toBe(1_000_000)
  expect(body.tokens).toBe(250_000)
  expect(body.percent).toBe(25)
  expect(body.updated).toBe(isoSeconds(await w.clock.now()))
  expect(body.updated).toMatch(/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$/)
  expect(w.seen.keys.context).toEqual(USAGE)
})

test('no plan in flight: nothing is written', async ($, on) => {
  const { writes } = await setup($, on, [])
  await $.turn.complete(turn())
  expect(writes.length).toBe(0)
})

test('a pinned plan outside preflight, task and gate: nothing is written', async ($, on) => {
  const { writes } = await setup($, on, [group({ phase: 'closeout' }), group({ name: 'other', role: 'other' })])
  await $.turn.complete(turn())
  expect(writes.length).toBe(0)
})

test('a stale pinned plan: nothing is written', async ($, on) => {
  const { writes } = await setup($, on, [group({ phase: 'gate', stale_hours: 30 })])
  await $.turn.complete(turn())
  expect(writes.length).toBe(0)
})

test('a subagent turn: nothing is written', async ($, on) => {
  const { writes } = await setup($, on, [group({ phase: 'task' })])
  await $.turn.complete(turn({ agentId: 'agent-1' }))
  expect(writes.length).toBe(0)
})

// A link, and a directory that is not one yet resolves elsewhere (a junction,
// a bind mount): each check stands on its own.
for (const [what, entry] of [
  ['a link out of the repo', { kind: 'dir', isLink: true, realPath: '/home/someone/.config' }],
  ['no link, resolving out of the repo', { kind: 'dir', isLink: false, realPath: '/home/someone/.config' }],
  ['a link back into itself', { kind: 'dir', isLink: true, realPath: '/repo/.claude' }],
] as [string, Entry][]) {
  test(`a .claude that is ${what}: nothing is written`, async ($, on) => {
    const { writes } = await setup($, on, [group({ phase: 'task' })], { '/repo/.claude': entry })
    await $.turn.complete(turn())
    expect(writes.length).toBe(0)
  })
}

for (const [what, entry] of [
  ['a link', { kind: 'file', isLink: true, realPath: '/home/someone/.bashrc' }],
  ['a directory', { kind: 'dir' }],
] as [string, Entry][]) {
  test(`a sidecar that is ${what}: nothing is written`, async ($, on) => {
    const { writes } = await setup($, on, [group({ phase: 'task' })], { [SIDECAR]: entry })
    await $.turn.complete(turn())
    expect(writes.length).toBe(0)
  })
}

test('an existing regular sidecar is rewritten', async ($, on) => {
  const { writes } = await setup($, on, [group({ phase: 'preflight' })], { [SIDECAR]: { kind: 'file' } })
  await $.turn.complete(turn())
  expect(writes.length).toBe(1)
})

for (const context of [{ window: 0 }, {}, { window: 1.5 }, { window: '1000000' }]) {
  test(`no window from the engine (${JSON.stringify(context)}): nothing is written, no figures`, async ($, on) => {
    const { w, writes } = await setup($, on, [group({ phase: 'task' })], {}, context)
    await $.turn.complete(turn())
    expect(writes.length).toBe(0)
    expect(w.seen.keys.context).toBe(null)
  })
}

test('a write that fails leaves the turn to end normally', async ($, on) => {
  const w = world(on, planned([group({ phase: 'task' })]))
  disk(on, {}, true)
  engine(on)
  await seed($ as never, w.clock)
  const done = await $.turn.complete(turn())
  expect(typeof done.text).toBe('string')
  expect(w.seen.keys.context).toEqual(USAGE)
})

test('figuresOf keeps only whole, non-negative figures and caps percent at 100', () => {
  expect(figuresOf({ context: { window: 200_000, tokens: -1, percent: 140 } })).toEqual({
    window: 200_000,
    tokens: null,
    percent: 100,
  })
  expect(figuresOf({ context: { window: 200_000 } })).toEqual({ window: 200_000, tokens: null, percent: null })
  expect(figuresOf(null)).toBe(null)
  expect(figuresOf({ context: null })).toBe(null)
})
