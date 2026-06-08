import type { TabDescriptor } from '../types'
import { PhasesTab } from './PhasesTab'
import type { PhasesClient } from './types'

export interface PhasesTabConfig {
  client: PhasesClient
  id?: string
  label?: string
}

/** Build a devdash Phases tab bound to a PhasesClient (ADR-D01 factory). */
export function phasesTab(config: PhasesTabConfig): TabDescriptor {
  if (!config.client) throw new Error('phasesTab(config): a PhasesClient is required')
  return {
    id: config.id ?? 'phases',
    label: config.label ?? 'Phases',
    scrollModel: 'scroll',
    component: () => <PhasesTab client={config.client} />,
  }
}

export { PhasesTab } from './PhasesTab'
export { httpPhasesClient } from './httpClient'
export { inMemoryPhasesClient } from './memoryClient'
export type {
  Phase,
  Session,
  TokenStats,
  Projection,
  ProjectionMethod,
  PhasesClient,
} from './types'
export type { HttpPhasesClientOptions } from './httpClient'
export type { InMemoryPhasesData } from './memoryClient'
