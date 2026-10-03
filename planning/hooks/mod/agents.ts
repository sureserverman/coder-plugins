// This session's Agent dispatches, for the plan pane: a plan's Dispatch: YES
// tasks, its reviewers and its evaluators all go out through the Agent tool, so
// the list is what is running on the plan's behalf right now.

import { atom, update } from 'claude-code'
import type { On } from 'claude-code'

import type { AgentRecord } from '../../types'

const AGENTS = atom({ plugin: 'planning', key: 'agents' } as const, [] as AgentRecord[])

const KEEP = 50

const text = (v: unknown): string => (typeof v === 'string' ? v : '')

export function registerAgents(on: On): void {
  on('tool.call', { tool: 'Agent' }, async ($, e, next) => {
    const record: AgentRecord = {
      id: e.tool_use_id,
      description: text((e as { description?: unknown }).description),
      subagentType: text((e as { subagent_type?: unknown }).subagent_type) || 'general-purpose',
      startedAt: await $.clock.now(),
      isDone: false,
    }
    await update($, AGENTS, list => [...list, record].slice(-KEEP))
    try {
      return await next(e)
    } finally {
      await update($, AGENTS, list => list.map(a => (a.id === record.id ? { ...a, isDone: true } : a)))
    }
  })
}
