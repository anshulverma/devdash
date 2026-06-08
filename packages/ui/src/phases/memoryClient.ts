import type { PhasesClient, Phase, Session, TokenStats, Projection } from './types'

export interface InMemoryPhasesData {
  phases?: Phase[]
  sessions?: Session[]
  tokenStats?: TokenStats
  projection?: Projection
}

const EMPTY_STATS: TokenStats = {
  messages: 0,
  input_tokens: 0,
  output_tokens: 0,
  cost_usd: 0,
  by_model: {},
}

const EMPTY_PROJECTION: Projection = {
  method: 'none',
  cumulative_sec: 0,
  remaining_sec: 0,
  target_sec: 0,
  burn_per_day_sec: null,
  projected_finish_date: null,
}

/** Client-side PhasesClient for demos/tests — no backend required. */
export function inMemoryPhasesClient(data: InMemoryPhasesData = {}): PhasesClient {
  return {
    listPhases: () => Promise.resolve(data.phases ?? []),
    listSessions: () => Promise.resolve(data.sessions ?? []),
    tokenStats: () => Promise.resolve(data.tokenStats ?? EMPTY_STATS),
    projection: () => Promise.resolve(data.projection ?? EMPTY_PROJECTION),
  }
}
