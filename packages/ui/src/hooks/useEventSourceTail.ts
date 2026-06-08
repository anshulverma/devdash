import { useEffect, useRef, useState } from 'react'

export interface TailEvent<T> {
  /** Adapter-supplied stable id (ADR-D04), used for dedup + SSE resume. */
  id: string
  data: T
}

export interface UseEventSourceTailOptions<T> {
  /** SSE endpoint URL. When null/undefined the hook stays idle (no connection). */
  url: string | null | undefined
  /** Parse a raw SSE message payload into a typed record. */
  parse: (raw: string) => TailEvent<T>
  /** Max records retained in the in-memory ring (default 5000). */
  ringSize?: number
  /** EventSource factory (injectable for tests). Defaults to window EventSource. */
  eventSourceFactory?: (url: string) => EventSourceLike
}

/** Minimal structural type for an EventSource, so tests can inject a fake. */
export interface EventSourceLike {
  addEventListener: (type: string, listener: (ev: { data: string }) => void) => void
  close: () => void
}

export interface TailState<T> {
  rows: TailEvent<T>[]
  /** True between open and the first error. */
  connected: boolean
  /** Count of rows dropped from the ring head (drop-oldest backpressure). */
  dropped: number
  error: string | null
}

/**
 * Subscribe to an SSE tail (`prime` / `entry` / `error` events). Maintains a
 * bounded ring (drop-oldest), dedups by stable id, and reconnects implicitly by
 * URL change. The shared tail primitive behind both the Logs viewer and any
 * host record-stream tab ("the shell for events").
 */
export function useEventSourceTail<T>(opts: UseEventSourceTailOptions<T>): TailState<T> {
  const { url, parse, ringSize = 5000, eventSourceFactory } = opts
  const [state, setState] = useState<TailState<T>>({
    rows: [],
    connected: false,
    dropped: 0,
    error: null,
  })
  const seen = useRef<Set<string>>(new Set())

  useEffect(() => {
    if (!url) return
    seen.current = new Set()
    setState({ rows: [], connected: false, dropped: 0, error: null })

    const factory =
      eventSourceFactory ??
      ((u: string) => new EventSource(u) as unknown as EventSourceLike)
    const es = factory(url)

    const append = (events: TailEvent<T>[]) => {
      setState((prev) => {
        const fresh = events.filter((e) => !seen.current.has(e.id))
        for (const e of fresh) seen.current.add(e.id)
        let rows = prev.rows.concat(fresh)
        let dropped = prev.dropped
        if (rows.length > ringSize) {
          const overflow = rows.length - ringSize
          rows = rows.slice(overflow)
          dropped += overflow
        }
        return { ...prev, rows, dropped, connected: true }
      })
    }

    es.addEventListener('prime', (ev) => {
      const lines = ev.data ? ev.data.split('\n').filter(Boolean) : []
      append(lines.map(parse))
    })
    es.addEventListener('entry', (ev) => append([parse(ev.data)]))
    es.addEventListener('error', (ev) => {
      setState((prev) => ({ ...prev, connected: false, error: ev.data || 'stream error' }))
    })

    return () => es.close()
  }, [url, parse, ringSize, eventSourceFactory])

  return state
}
