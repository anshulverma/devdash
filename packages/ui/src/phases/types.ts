// Frontend mirror of the phase-tracker REST contract. PhasesClient abstracts
// transport (HTTP backend or a client-side in-memory store for demos/tests).

export interface Phase {
  phase: string
  label?: string | null
  status?: string | null
  complexity?: number | null
  display_order?: number | null
  parent?: string | null
  color?: string | null
}

export interface Session {
  id: number
  dev_name: string
  started_at: string
  ended_at: string
  duration_sec: number
  phase?: string | null
  source: string
  notes?: string | null
}

export interface TokenStats {
  messages: number
  input_tokens: number
  output_tokens: number
  cost_usd: number
  by_model: Record<string, number>
}

export type ProjectionMethod = 'none' | 'naive' | 'calibrated'

export interface Projection {
  method: ProjectionMethod
  cumulative_sec: number
  remaining_sec: number
  target_sec: number
  burn_per_day_sec: number | null
  projected_finish_date: string | null
}

export interface PhasesClient {
  listPhases(): Promise<Phase[]>
  listSessions(): Promise<Session[]>
  tokenStats(): Promise<TokenStats>
  projection(): Promise<Projection>
}
