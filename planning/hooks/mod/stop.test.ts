import type { On } from 'claude-code'
import { expect, mock, test } from 'claude-code/testing'

const ROOT = '/repo'
const STATE_PATH = `${ROOT}/.claude/plan-progress.json`
const PROMISE = 'Stage 2 is green and committed — starting now with Task 2.1.'
const STATE = { plan: 'plans/x-plan.md', phase: 'task', stage: 2, task: '2.1', updated: '2026-10-04T00:00:00Z' }

type Classified = { decision: string; reason?: string; system_message?: string; notice?: string }
type Opts = {
  optIn?: boolean
  realPath?: string
  root?: string | null
  classify?: (input: { count: number; max: number; check_updated?: boolean }) => Classified | 'timeout'
  stateText?: string
}

const ran = (stdout: string) => ({
  value: { exitCode: 0, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false },
})

// The world beneath the mod for a Stop: the environment, the session's cwd, the
// two process runs (`--root`, then the classifier — answered here as the Python
// module would), the state file, and what the chain below the mod receives.
function harness(on: On, o: Opts = {}) {
  const spawned: string[][] = []
  const below: Record<string, unknown>[] = []
  const notices: string[] = []
  const inputs: { count: number; max: number; check_updated?: boolean }[] = []
  const statted: unknown[] = []
  mock.env(on, o.optIn === false ? {} : { PLAN_CONTINUE: '1' })
  on('session.cwd', () => ({ value: `${ROOT}/sub` }))
  on('process.run', (_$, e) => {
    spawned.push([...e.argv])
    if (e.argv.includes('--root')) return ran(JSON.stringify({ root: o.root === undefined ? ROOT : o.root })) as never
    const input = JSON.parse(e.init?.stdin ?? '{}')
    inputs.push(input)
    const out = (o.classify ?? (() => ({ decision: 'block', reason: 'keep going' })))(input)
    if (out === 'timeout') throw new Error('timed out')
    return ran(JSON.stringify(out)) as never
  })
  on('fs.stat', (_$, e) => {
    const path = (e as { path: string }).path
    statted.push(path)
    const realPath = path === STATE_PATH ? (o.realPath ?? STATE_PATH) : path
    return { value: { kind: 'file', size: 100, mtimeMs: 0, isLink: false, realPath } } as never
  })
  on('fs.read', () => ({ value: o.stateText ?? JSON.stringify(STATE) }) as never)
  on('ui.log', (_$, e) => {
    notices.push(String((e as { text?: unknown }).text))
    return { value: undefined } as never
  })
  on('classic.Stop', (_$, e) => {
    below.push(e as Record<string, unknown>)
    return {}
  })
  return { spawned, below, notices, inputs, statted }
}

const stop = ($: { classic: { Stop: (e: never) => Promise<{ block?: string }> } }, text = PROMISE) =>
  $.classic.Stop({ stop_hook_active: false, last_assistant_message: text } as never)

test('opt-in off: the event passes on untouched and nothing is spawned', async ($, on) => {
  const w = harness(on, { optIn: false })
  const r = await stop($ as never)
  expect(r.block).toBe(undefined)
  expect(w.spawned.length).toBe(0)
  expect(w.below.length).toBe(1)
  expect(w.below[0]!.planning_mod_handled).toBe(undefined)
})

test('a promise in phase task blocks with the classifier reason, and the chain below still runs', async ($, on) => {
  const w = harness(on)
  const r = await stop($ as never)
  expect(r.block).toBe('keep going')
  expect(w.below.length).toBe(1)
  expect(w.below[0]!.planning_mod_handled).toBe(true)
  expect(w.inputs[0]!.check_updated).toBe(true)
  expect(w.spawned.some(a => a.some(x => x.endsWith('plan_continue_classify.py')))).toBe(true)
})

test('the same phase|stage|task blocked max times releases the next with a notice', async ($, on) => {
  const w = harness(on, {
    classify: ({ count, max }) =>
      count >= max ? { decision: 'allow', system_message: `released after ${count}` } : { decision: 'block', reason: 'go' },
  })
  for (let i = 0; i < 3; i += 1) expect((await stop($ as never)).block).toBe('go')
  const r = await stop($ as never)
  expect(r.block).toBe(undefined)
  expect(w.inputs.map(x => x.count)).toEqual([0, 1, 2, 3])
  expect(w.inputs[0]!.max).toBe(3)
  expect(w.notices).toEqual(['released after 3'])
})

test('a state file whose realPath leaves the repo -> allow, no classifier run', async ($, on) => {
  const w = harness(on, { realPath: '/etc/elsewhere/plan-progress.json' })
  const r = await stop($ as never)
  expect(r.block).toBe(undefined)
  expect(w.inputs.length).toBe(0)
  expect(w.below[0]!.planning_mod_handled).toBe(true)
})

test('no repo root (none, or a refused world-writable one) -> allow', async ($, on) => {
  const w = harness(on, { root: null })
  const r = await stop($ as never)
  expect(r.block).toBe(undefined)
  expect(w.inputs.length).toBe(0)
  expect(w.statted).toEqual([])
})

test('the classifier timing out -> allow', async ($, on) => {
  harness(on, { classify: () => 'timeout' })
  const r = await stop($ as never)
  expect(r.block).toBe(undefined)
})

test('an unparseable state file -> allow', async ($, on) => {
  const w = harness(on, { stateText: 'not json' })
  const r = await stop($ as never)
  expect(r.block).toBe(undefined)
  expect(w.inputs.length).toBe(0)
})

test('a hostile 100 KB reason is cut to at most 2 KB with no control characters but newlines', async ($, on) => {
  const huge = `${'x'.repeat(50_000)}\u001b[31m\n${'y'.repeat(50_000)}`
  harness(on, { classify: () => ({ decision: 'block', reason: huge }) })
  const r = await stop($ as never)
  expect(typeof r.block).toBe('string')
  expect(new TextEncoder().encode(r.block!).length).toBeLessThanOrEqual(2048)
  expect(/[\x00-\x09\x0b-\x1f\x7f]/.test(r.block!)).toBe(false)
})

test('a stale state is released with the notice and nothing is counted', async ($, on) => {
  const w = harness(on, { classify: () => ({ decision: 'allow', notice: 'plan-continue: 13.0h stale' }) })
  await stop($ as never)
  await stop($ as never)
  expect(w.notices).toEqual(['plan-continue: 13.0h stale', 'plan-continue: 13.0h stale'])
  expect(w.inputs.map(x => x.count)).toEqual([0, 0])
})

test('an empty last message -> allow without spawning the classifier', async ($, on) => {
  const w = harness(on)
  const r = await stop($ as never, '')
  expect(r.block).toBe(undefined)
  expect(w.inputs.length).toBe(0)
})

test('an empty root string is no root: nothing is statted or read', async ($, on) => {
  const w = harness(on, { root: '' })
  const r = await stop($ as never)
  expect(r.block).toBe(undefined)
  expect(w.statted).toEqual([])
  expect(w.inputs.length).toBe(0)
})
