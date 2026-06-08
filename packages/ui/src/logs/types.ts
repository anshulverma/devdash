// Frontend mirror of the backend log-viewing contract. The LogsClient
// abstracts transport so the same LogsTab works against the HTTP backend or a
// client-side in-memory store (demo/tests).

export type TextSearchMode = 'fulltext' | 'substring' | 'none'

export interface LogEntry {
  id: string
  ts: string
  level: string
  message: string
  service?: string | null
  container?: string | null
  stream?: string | null
  fields?: Record<string, string>
}

export interface LogFilters {
  services?: string[]
  levels?: string[]
  search?: string
  limit?: number
}

export interface LogPage {
  entries: LogEntry[]
  cursor?: string | null
  total?: number | null
}

export interface LogFacets {
  services: string[]
  levels: string[]
}

export interface LogCapabilities {
  can_search: boolean
  can_tail: boolean
  can_enumerate: boolean
  text_search: TextSearchMode
  time_range: boolean
  cursor_pagination: boolean
}

export interface TailHandlers {
  onPrime?: (entries: LogEntry[]) => void
  onEntry: (entry: LogEntry) => void
  onError?: (message: string) => void
}

/** Transport abstraction behind the Logs tab. */
export interface LogsClient {
  capabilities(): Promise<LogCapabilities>
  facets(): Promise<LogFacets>
  search(filters: LogFilters): Promise<LogPage>
  /** Subscribe to a live tail. Returns an unsubscribe function. */
  subscribe(filters: LogFilters, handlers: TailHandlers): () => void
}
