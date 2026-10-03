import type { On } from 'claude-code'
import { expect, mock, test } from 'claude-code/testing'

import type { PlanModelState } from '../../types'

const FIXTURE = {
  groups: [
    { name: 'fixture-plan', done: 2, total: 5, role: 'pinned', stage: 1, stage_count: 2, task: '1.3', phase: 'task' },
  ],
  detail: null,
}

const ran = (stdout: string, exitCode = 0) => ({
  value: { exitCode, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false },
})

// The test's own hooks sit beneath the plugin and stand for the engine: a
// process.run answered here is what the mod's $.process.run receives.
function fakeProcess(on: On, answer: () => unknown) {
  const calls: string[][] = []
  on('session.cwd', () => ({ value: '/repo' }))
  on('process.run', (_$, e) => {
    calls.push([...e.argv])
    return answer() as never
  })
  return calls
}

// The test's $ has no state noun; the mod's writes are observed on their way
// down instead, the last one being what a drawing would read.
function captureModel(on: On) {
  const seen: { last: PlanModelState | null } = { last: null }
  on('state.set', (_$, e, next) => {
    if (e.plugin === 'planning' && e.key === 'model') seen.last = e.value as PlanModelState
    return next(e)
  })
  mock.clock(on, { now: 1_000 })
  return seen
}

function fakeTool(on: On) {
  on('tool.call', () => ({ result: 'ok' }) as never)
}

test('a refresh stores the script output as the model', async ($, on) => {
  const model = captureModel(on)
  const calls = fakeProcess(on, () => ran(JSON.stringify(FIXTURE)))
  fakeTool(on)
  await $.tool.call({ tool: 'Write', file_path: '/repo/.claude/plan-progress.json', content: '{}' })
  expect(calls.length).toBe(1)
  expect(calls[0]!.some(a => a.endsWith('plan-progress.py'))).toBe(true)
  expect(calls[0]!).toContain('--json')
  const state = model.last
  expect(state?.model?.groups[0]?.name).toBe('fixture-plan')
  expect(state?.stale).toBe(false)
})

test('a write to the state file triggers exactly one refresh', async ($, on) => {
  const model = captureModel(on)
  const calls = fakeProcess(on, () => ran(JSON.stringify(FIXTURE)))
  fakeTool(on)
  await $.tool.call({ tool: 'Write', file_path: '.claude/plan-progress.json', content: '{}' })
  expect(calls.length).toBe(1)
})

test('an edit to a plan file and a Bash call naming one each refresh', async ($, on) => {
  const model = captureModel(on)
  const calls = fakeProcess(on, () => ran(JSON.stringify(FIXTURE)))
  fakeTool(on)
  await $.tool.call({ tool: 'Edit', file_path: '/vault/plans/2026-10-03-x-plan.md', old_string: 'a', new_string: 'b' })
  await $.tool.call({ tool: 'Bash', command: "printf '{}' > .claude/plan-progress.json" })
  expect(calls.length).toBe(2)
})

test('a write to an unrelated file triggers no refresh', async ($, on) => {
  const model = captureModel(on)
  const calls = fakeProcess(on, () => ran(JSON.stringify(FIXTURE)))
  fakeTool(on)
  await $.tool.call({ tool: 'Write', file_path: '/repo/src/main.rs', content: 'fn main() {}' })
  await $.tool.call({ tool: 'Bash', command: 'ls -la' })
  expect(calls.length).toBe(0)
})

test('a timeout keeps the previous model and marks it stale', async ($, on) => {
  const model = captureModel(on)
  let fail = false
  fakeProcess(on, () => {
    if (fail) throw new Error('timed out')
    return ran(JSON.stringify(FIXTURE))
  })
  fakeTool(on)
  await $.tool.call({ tool: 'Write', file_path: '.claude/plan-progress.json', content: '{}' })
  fail = true
  await $.tool.call({ tool: 'Write', file_path: '.claude/plan-progress.json', content: '{}' })
  const state = model.last
  expect(state?.model?.groups[0]?.name).toBe('fixture-plan')
  expect(state?.stale).toBe(true)
})

test('unparseable output keeps the previous model and marks it stale', async ($, on) => {
  const model = captureModel(on)
  let out = JSON.stringify(FIXTURE)
  fakeProcess(on, () => ran(out))
  fakeTool(on)
  await $.tool.call({ tool: 'Write', file_path: '.claude/plan-progress.json', content: '{}' })
  out = 'Traceback (most recent call last):'
  await $.tool.call({ tool: 'Write', file_path: '.claude/plan-progress.json', content: '{}' })
  const state = model.last
  expect(state?.model?.groups.length).toBe(1)
  expect(state?.stale).toBe(true)
})

test('session.start refreshes once', async ($, on) => {
  const model = captureModel(on)
  const calls = fakeProcess(on, () => ran(JSON.stringify(FIXTURE)))
  on('session.start', (_$, e) => ({ cwd: e.cwd }))
  await $.session.start({ cwd: '/repo', surface: null, isInteractive: false })
  expect(calls.length).toBe(1)
})
