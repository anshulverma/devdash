import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { FilterChips } from '../primitives'
import { RecordTable, StatusStrip, JsonDetailPanel } from '../primitives'
import { useTabQuery } from '../routing'
import type { QueryCodec } from '../types'
import type { LogCapabilities, LogEntry, LogFacets, LogFilters, LogsClient } from './types'

const RING = 5000

interface LogQuery {
  services: string[]
  levels: string[]
  search: string
}

const queryCodec: QueryCodec<LogQuery> = {
  parse: (p) => ({
    services: p.get('services') ? p.get('services')!.split(',') : [],
    levels: p.get('levels') ? p.get('levels')!.split(',') : [],
    search: p.get('q') ?? '',
  }),
  serialize: (q) => {
    const p = new URLSearchParams()
    if (q.services.length) p.set('services', q.services.join(','))
    if (q.levels.length) p.set('levels', q.levels.join(','))
    if (q.search) p.set('q', q.search)
    return p
  },
}

export function LogsTab({ client }: { client: LogsClient }) {
  const [query, setQuery] = useTabQuery(queryCodec)
  const [caps, setCaps] = useState<LogCapabilities | null>(null)
  const [facets, setFacets] = useState<LogFacets>({ services: [], levels: [] })
  const [rows, setRows] = useState<LogEntry[]>([])
  const [live, setLive] = useState(false)
  const [dropped, setDropped] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<LogEntry | null>(null)
  const seen = useRef<Set<string>>(new Set())

  const filters: LogFilters = useMemo(
    () => ({ services: query.services, levels: query.levels, search: query.search, limit: 500 }),
    [query],
  )

  useEffect(() => {
    let alive = true
    client.capabilities().then((c) => alive && setCaps(c)).catch(() => {})
    client.facets().then((f) => alive && setFacets(f)).catch(() => {})
    return () => {
      alive = false
    }
  }, [client])

  const reset = useCallback((entries: LogEntry[]) => {
    seen.current = new Set(entries.map((e) => e.id))
    setRows(entries.slice(-RING))
    setDropped(0)
  }, [])

  const append = useCallback((entry: LogEntry) => {
    if (seen.current.has(entry.id)) return
    seen.current.add(entry.id)
    setRows((prev) => {
      const next = [...prev, entry]
      if (next.length > RING) {
        setDropped((d) => d + (next.length - RING))
        return next.slice(next.length - RING)
      }
      return next
    })
  }, [])

  // History search (when not live and the adapter can search).
  useEffect(() => {
    if (live || !caps?.can_search) return
    let alive = true
    setError(null)
    client
      .search(filters)
      .then((page) => alive && reset(page.entries))
      .catch((e) => alive && setError(String(e)))
    return () => {
      alive = false
    }
  }, [client, filters, live, caps, reset])

  // Live tail (when live and the adapter can tail).
  useEffect(() => {
    if (!live || !caps?.can_tail) return
    setError(null)
    const unsub = client.subscribe(filters, {
      onPrime: reset,
      onEntry: append,
      onError: setError,
    })
    return unsub
  }, [client, filters, live, caps, reset, append])

  const canSearch = caps?.can_search ?? false
  const canTail = caps?.can_tail ?? false

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', padding: '0.6rem 1rem', flexWrap: 'wrap' }}>
        {canSearch && (
          <input
            aria-label="search logs"
            placeholder="search message…"
            value={query.search}
            onChange={(e) => setQuery({ ...query, search: e.target.value })}
            style={{ font: 'inherit', padding: '0.3rem 0.5rem', borderRadius: 'var(--devdash-radius-sm)', minWidth: 200 }}
          />
        )}
        {facets.levels.length > 0 && (
          <FilterChips
            options={facets.levels.map((l) => ({ value: l }))}
            selected={query.levels}
            onChange={(levels) => setQuery({ ...query, levels })}
          />
        )}
        {canTail && (
          <label style={{ marginLeft: 'auto', display: 'inline-flex', gap: '0.35rem', alignItems: 'center' }}>
            <input type="checkbox" checked={live} onChange={(e) => setLive(e.target.checked)} />
            live
          </label>
        )}
      </div>

      <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '0 1rem' }}>
        {error ? (
          <div role="alert" style={{ color: 'var(--devdash-color-danger)', padding: '1rem' }}>{error}</div>
        ) : (
          <RecordTable
            rows={rows}
            rowKey={(r) => r.id}
            empty="No log entries."
            columns={[
              { key: 'ts', header: 'time', width: 200, render: (r) => r.ts },
              { key: 'level', header: 'level', width: 70, render: (r) => r.level },
              { key: 'service', header: 'service', width: 120, render: (r) => r.service ?? '' },
              {
                key: 'message',
                header: 'message',
                render: (r) => (
                  <button
                    type="button"
                    onClick={() => setSelected(r)}
                    style={{ all: 'unset', cursor: 'pointer', font: 'inherit' }}
                  >
                    {r.message}
                  </button>
                ),
              },
            ]}
          />
        )}
        {selected && (
          <div style={{ marginTop: '0.5rem' }}>
            <JsonDetailPanel value={selected} />
          </div>
        )}
      </div>

      <StatusStrip live={live}>
        {rows.length} rows
        {caps ? ` · search: ${caps.text_search}` : ''}
        {dropped > 0 ? ` · ${dropped} dropped` : ''}
      </StatusStrip>
    </div>
  )
}
