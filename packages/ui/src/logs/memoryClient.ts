import type {
  LogCapabilities,
  LogEntry,
  LogFacets,
  LogFilters,
  LogPage,
  LogsClient,
  TailHandlers,
} from './types'

function matches(e: LogEntry, f: LogFilters): boolean {
  if (f.services?.length && !f.services.includes(e.service ?? '')) return false
  if (f.levels?.length && !f.levels.includes(e.level)) return false
  if (f.search && !e.message.toLowerCase().includes(f.search.toLowerCase())) return false
  return true
}

export interface InMemoryLogsClientOptions {
  /** Capabilities to advertise (defaults to full substring-search support). */
  capabilities?: Partial<LogCapabilities>
}

/**
 * Client-side in-memory LogsClient — fully working without a backend, for demos
 * and tests. `push()` simulates live ingest (drives the tail). Mirrors the
 * backend InMemoryLogSource conceptually.
 */
export interface InMemoryLogsClient extends LogsClient {
  push: (entry: LogEntry) => void
}

export function inMemoryLogsClient(
  initial: LogEntry[] = [],
  opts: InMemoryLogsClientOptions = {},
): InMemoryLogsClient {
  const entries = [...initial]
  const subscribers = new Set<{ f: LogFilters; h: TailHandlers }>()
  const caps: LogCapabilities = {
    can_search: true,
    can_tail: true,
    can_enumerate: true,
    text_search: 'substring',
    time_range: true,
    cursor_pagination: false,
    ...opts.capabilities,
  }
  return {
    capabilities: () => Promise.resolve(caps),
    facets: () =>
      Promise.resolve<LogFacets>({
        services: [...new Set(entries.map((e) => e.service).filter(Boolean) as string[])].sort(),
        levels: [...new Set(entries.map((e) => e.level))].sort(),
      }),
    search: (f) => {
      const matched = entries.filter((e) => matches(e, f))
      return Promise.resolve<LogPage>({
        entries: matched.slice(-(f.limit ?? 200)),
        total: matched.length,
      })
    },
    subscribe(f, h) {
      const sub = { f, h }
      subscribers.add(sub)
      h.onPrime?.(entries.filter((e) => matches(e, f)).slice(-(f.limit ?? 100)))
      return () => subscribers.delete(sub)
    },
    push(entry) {
      entries.push(entry)
      for (const { f, h } of subscribers) if (matches(entry, f)) h.onEntry(entry)
    },
  }
}
