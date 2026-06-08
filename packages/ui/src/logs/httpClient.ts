import type {
  LogCapabilities,
  LogEntry,
  LogFacets,
  LogFilters,
  LogPage,
  LogsClient,
  TailHandlers,
} from './types'

export interface HttpLogsClientOptions {
  /** Base URL of the mounted dashboard, e.g. "/dev". */
  baseUrl: string
  fetch?: typeof fetch
  eventSourceFactory?: (url: string) => EventSourceLike
}

export interface EventSourceLike {
  addEventListener: (type: string, listener: (ev: { data: string }) => void) => void
  close: () => void
}

function qs(filters: LogFilters): string {
  const p = new URLSearchParams()
  for (const s of filters.services ?? []) p.append('services', s)
  for (const l of filters.levels ?? []) p.append('levels', l)
  if (filters.search) p.set('search', filters.search)
  if (filters.limit != null) p.set('limit', String(filters.limit))
  return p.toString()
}

/** LogsClient talking to a devdash backend over REST + SSE. */
export function httpLogsClient(opts: HttpLogsClientOptions): LogsClient {
  const base = opts.baseUrl.replace(/\/$/, '')
  const doFetch = opts.fetch ?? globalThis.fetch.bind(globalThis)

  async function getJson<T>(path: string): Promise<T> {
    const res = await doFetch(`${base}${path}`)
    if (!res.ok) throw new Error(`${path} -> ${res.status}`)
    return (await res.json()) as T
  }

  return {
    capabilities: () => getJson<LogCapabilities>('/logs/capabilities'),
    facets: () => getJson<LogFacets>('/logs/facets'),
    search: (filters) => getJson<LogPage>(`/logs/search?${qs(filters)}`),
    subscribe(filters, handlers: TailHandlers) {
      const url = `${base}/logs/tail?${qs(filters)}`
      const factory =
        opts.eventSourceFactory ??
        ((u: string) => new EventSource(u) as unknown as EventSourceLike)
      const es = factory(url)
      es.addEventListener('prime', (ev) => {
        const entries = (ev.data ? ev.data.split('\n').filter(Boolean) : []).map(
          (l) => JSON.parse(l) as LogEntry,
        )
        handlers.onPrime?.(entries)
      })
      es.addEventListener('entry', (ev) => handlers.onEntry(JSON.parse(ev.data) as LogEntry))
      es.addEventListener('error', (ev) => handlers.onError?.(ev.data || 'stream error'))
      return () => es.close()
    },
  }
}
