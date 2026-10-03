// The planning mod's state contract: every `$.state` value the hooks module under
// ../hooks/mod/ reads or writes is declared here, and `claude plugin validate`
// holds the module's keys to it.

// One bar of the render model `plan-progress.py --json` prints; the script owns
// the shape, and a field it leaves out is absent rather than guessed here.
export type PlanGroup = {
  name: string
  plan?: string
  done: number
  total: number
  role: 'pinned' | 'other' | 'master' | 'child'
  depth?: number
  gate_blocked?: boolean
  stage?: number | null
  stage_count?: number | null
  task?: string | null
  phase?: string | null
  stale_hours?: number | null
  remediation_round?: number | null
  remediation_budget?: number | null
  blocked_note?: string | null
  status_lag?: number | null
  task_not_in_plan?: boolean | null
  stage_order?: boolean | null
  [field: string]: unknown
}

// `status` is the plan parser's own word for the marker: done, partial ([~]) or open.
export type PlanTask = { id: string; title: string; status: 'done' | 'partial' | 'open' | null }

// A light plan has no `## Stage` heading: its one stage carries number and name null.
export type PlanStage = {
  number: number | null
  name: string | null
  gate_checked: number
  gate_total: number
  tasks: PlanTask[]
}

export type PlanDetail = { plan: string; name?: string; stages: PlanStage[]; [field: string]: unknown }

export type PlanModel = { groups: PlanGroup[]; detail: PlanDetail | null }

// The last model a refresh produced. `stale` is set when the latest refresh failed
// (timeout, non-zero exit, unparseable output) and the previous model was kept.
export type PlanModelState = { model: PlanModel | null; fetchedAt: number; stale: boolean }

declare module 'claude-code' {
  interface PluginState {
    planning: {
      model: PlanModelState | null
    }
  }
}
