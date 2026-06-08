import type { TabDescriptor } from '../types'
import { LogsTab } from './LogsTab'
import type { LogsClient } from './types'

export interface LogsTabConfig {
  client: LogsClient
  id?: string
  label?: string
}

/** Build a devdash Logs tab bound to a LogsClient (ADR-D01 factory). */
export function logsTab(config: LogsTabConfig): TabDescriptor {
  if (!config.client) throw new Error('logsTab(config): a LogsClient is required')
  return {
    id: config.id ?? 'logs',
    label: config.label ?? 'Logs',
    scrollModel: 'chrome',
    component: () => <LogsTab client={config.client} />,
  }
}

export { LogsTab } from './LogsTab'
export { httpLogsClient } from './httpClient'
export { inMemoryLogsClient } from './memoryClient'
export type {
  LogEntry,
  LogFilters,
  LogPage,
  LogFacets,
  LogCapabilities,
  LogsClient,
  TailHandlers,
  TextSearchMode,
} from './types'
export type { HttpLogsClientOptions } from './httpClient'
export type { InMemoryLogsClient, InMemoryLogsClientOptions } from './memoryClient'
