import { expect, test } from 'claude-code/testing'

import type { AgentRecord } from '../../types'
import { world } from './testing'

const agents = (w: ReturnType<typeof world>) => (w.seen.keys.agents ?? []) as AgentRecord[]

const dispatch = (description: string, subagent_type = 'general-purpose') =>
  ({ tool: 'Agent', description, prompt: `do ${description}`, subagent_type }) as never

test('two Agent calls record two entries, both done once they resolve', async ($, on) => {
  const w = world(on)
  await $.tool.call(dispatch('Task 1.1: json mode'))
  await $.tool.call(dispatch('Stage 1 review', 'git-github:code-reviewer'))
  const list = agents(w)
  expect(list.length).toBe(2)
  expect(list.map(a => a.description)).toEqual(['Task 1.1: json mode', 'Stage 1 review'])
  expect(list[1]!.subagentType).toBe('git-github:code-reviewer')
  expect(list.every(a => a.isDone)).toBe(true)
  expect(list.every(a => typeof a.startedAt === 'number')).toBe(true)
  expect(new Set(list.map(a => a.id)).size).toBe(2)
})

test('an Agent call is recorded as running before it resolves', async ($, on) => {
  const w = world(on)
  let during: AgentRecord[] = []
  w.hooks.onTool = () => {
    during = agents(w).map(a => ({ ...a }))
  }
  await $.tool.call(dispatch('slow one'))
  expect(during.length).toBe(1)
  expect(during[0]!.isDone).toBe(false)
  expect(agents(w)[0]!.isDone).toBe(true)
})

test('a Bash call records nothing', async ($, on) => {
  const w = world(on)
  await $.tool.call({ tool: 'Bash', command: 'ls' })
  expect(w.seen.keys.agents).toBe(undefined)
})

test('the 51st call evicts the oldest', async ($, on) => {
  const w = world(on)
  for (let i = 1; i <= 51; i += 1) await $.tool.call(dispatch(`agent ${i}`))
  const list = agents(w)
  expect(list.length).toBe(50)
  expect(list[0]!.description).toBe('agent 2')
  expect(list[49]!.description).toBe('agent 51')
})
