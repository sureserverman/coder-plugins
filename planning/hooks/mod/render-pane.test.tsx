import type { On } from 'claude-code'
import { expect, test } from 'claude-code/testing'

import type { PlanDetail, PlanGroup } from '../../types'
import { PLAN_PANE } from './pane-id'
import { group, ran, seed, world } from './testing'

const SURFACES = ['terminal', 'desktop'] as const

const DETAIL: PlanDetail = {
  plan: '/vault/plans/2026-10-03-fixture-plan.md',
  name: 'fixture-plan',
  stages: [
    {
      number: 1,
      name: 'Data contract',
      gate_checked: 3,
      gate_total: 3,
      tasks: [
        { id: '1.1', title: 'json mode', status: 'done' },
        { id: '1.2', title: 'scaffold', status: 'done' },
      ],
    },
    {
      number: 2,
      name: 'Band and pane',
      gate_checked: 0,
      gate_total: 2,
      tasks: [
        { id: '2.1', title: 'band', status: 'done' },
        { id: '2.2', title: 'agents', status: 'partial' },
        { id: '2.3', title: 'pane', status: 'open' },
      ],
    },
  ],
}

const GROUPS: PlanGroup[] = [
  group({ name: 'fixture-master', role: 'master', depth: 0, tail: '' }),
  group({ name: 'fixture-plan', role: 'pinned', depth: 1, done: 3, total: 5, stage: 2, task: '2.3', remediation_round: 1, remediation_budget: 2 }),
]

const pane = (bodyColumns = 100) => ({
  plugin: 'planning',
  component: 'Pane' as const,
  requestId: PLAN_PANE,
  props: {
    title: 'Plan',
    isFocused: false,
    bodyColumns,
    placement: 'dock' as const,
    scroll: { offset: 0, bodyRows: 40 },
    view: {},
  },
})

const band = {
  plugin: 'planning',
  component: 'AbovePrompt' as const,
  props: { hasSurvey: false, isWorking: false, maxRows: 10, bodyColumns: 100, scroll: { offset: 0, bodyRows: 10 }, view: {} },
}

function opens(on: On): string[] {
  const opened: string[] = []
  on('ui.open', (_$, e) => {
    opened.push(e.id)
    return { value: { isPlaced: true } } as never
  })
  return opened
}

const withPlan = () => ran(JSON.stringify({ groups: GROUPS, detail: DETAIL }))

async function shown(ui: { findAll: (q: { type: string }) => Promise<{ text: string }[]> }): Promise<string> {
  return (await ui.findAll({ type: 'Text' })).map(t => t.text).join('\n')
}

test('running plan-view opens the plan pane, on every surface', async ($, on) => {
  const opened = opens(on)
  world(on, withPlan)
  for (const surface of SURFACES) {
    const answer = await $.command.run({
      command: 'plan-view',
      args: '',
      origin: { kind: 'composer' },
      presentation: { isFullscreen: surface === 'terminal', columns: 160 },
    } as never)
    expect(opened.at(-1)).toBe(PLAN_PANE)
    expect(typeof (answer as { text?: unknown }).text).toBe('string')
  }
})

test('the pane draws the master, the plan, both stage headers with gates, and every task id', async ($, on) => {
  const w = world(on, withPlan)
  await seed($ as never, w.clock)
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ ...pane(), surface })
    const text = await shown(ui)
    expect(text).toContain('fixture-master')
    expect(text).toContain('fixture-plan')
    expect(text).toContain('Stage 1')
    expect(text).toContain('Data contract')
    expect(text).toContain('3/3')
    expect(text).toContain('Stage 2')
    expect(text).toContain('0/2')
    for (const id of ['1.1', '1.2', '2.1', '2.2', '2.3']) expect(text).toContain(id)
    expect(text).toMatch(/▶[^\n]*2\.3/)
    expect(text).toContain('↻1/2')
    await ui.unmount()
  }
})

test("a running agent's description appears in the pane, listed before finished ones", async ($, on) => {
  const w = world(on, withPlan)
  await seed($ as never, w.clock)
  await $.tool.call({ tool: 'Agent', description: 'finished reviewer', prompt: 'p', subagent_type: 'git-github:code-reviewer' } as never)
  for (const surface of SURFACES) {
    let during = ''
    w.hooks.onTool = async e => {
      if (e.tool !== 'Agent') return
      const ui = await $.ui.mount({ ...pane(), surface })
      during = await shown(ui)
      await ui.unmount()
    }
    await $.tool.call({ tool: 'Agent', description: `Task 2.3 dispatch on ${surface}`, prompt: 'p', subagent_type: 'general-purpose' } as never)
    w.hooks.onTool = undefined
    expect(during).toContain(`Task 2.3 dispatch on ${surface}`)
    expect(during.indexOf(`Task 2.3 dispatch on ${surface}`)).toBeLessThan(during.indexOf('finished reviewer'))
  }
})

test("pressing the band's Plan button opens the same pane id", async ($, on) => {
  const opened = opens(on)
  const w = world(on, withPlan)
  await seed($ as never, w.clock)
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ ...band, surface })
    await ui.press({ key: 'open-plan' })
    expect(opened.at(-1)).toBe(PLAN_PANE)
    await ui.unmount()
  }
})

test('with no model the pane says no plan is executing', async ($, on) => {
  world(on)
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ ...pane(), surface })
    expect(await shown(ui)).toMatch(/no plan is executing/i)
    await ui.unmount()
  }
})

test('no pane line is wider than the pane', async ($, on) => {
  const w = world(on, withPlan)
  await seed($ as never, w.clock)
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ ...pane(30), surface })
    for (const t of await ui.findAll({ type: 'Text' })) expect([...t.text].length).toBeLessThanOrEqual(30)
    await ui.unmount()
  }
})

test('an interactive start registers /plan-view; a -p start does not', async ($, on) => {
  world(on)
  const registered: string[] = []
  on('command.register', (_$, e) => {
    registered.push((e as { name: string }).name)
    return { value: undefined } as never
  })
  on('session.start', (_$, e) => ({ cwd: e.cwd }))
  await $.session.start({ cwd: '/repo', surface: null, isInteractive: false })
  expect(registered).toEqual([])
  await $.session.start({ cwd: '/repo', surface: 'terminal', isInteractive: true })
  expect(registered).toEqual(['plan-view'])
})
