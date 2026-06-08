import type { PhasesClient, Phase, Session, TokenStats, Projection } from './types'

export interface HttpPhasesClientOptions {
  baseUrl: string
  fetch?: typeof fetch
}

/** PhasesClient talking to a devdash backend over the /phases REST routes. */
export function httpPhasesClient(opts: HttpPhasesClientOptions): PhasesClient {
  const base = opts.baseUrl.replace(/\/$/, '')
  const doFetch = opts.fetch ?? globalThis.fetch.bind(globalThis)
  async function get<T>(path: string): Promise<T> {
    const res = await doFetch(`${base}${path}`)
    if (!res.ok) throw new Error(`${path} -> ${res.status}`)
    return (await res.json()) as T
  }
  return {
    listPhases: () => get<Phase[]>('/phases/phases'),
    listSessions: () => get<Session[]>('/phases/sessions'),
    tokenStats: () => get<TokenStats>('/phases/tokens/stats'),
    projection: () => get<Projection>('/phases/projection'),
  }
}
