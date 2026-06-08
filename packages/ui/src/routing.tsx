import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import type { QueryCodec } from './types'

export interface ParsedHash {
  id: string | null
  params: URLSearchParams
}

/** Parse `#<id>?<query>` into its id segment and query params. */
export function parseHash(hash: string): ParsedHash {
  const raw = hash.replace(/^#/, '')
  const [idPart, queryPart = ''] = raw.split('?')
  return {
    id: idPart ? decodeURIComponent(idPart) : null,
    params: new URLSearchParams(queryPart),
  }
}

/** Build a `#<id>?<query>` hash string. */
export function buildHash(id: string, params?: URLSearchParams): string {
  const q = params?.toString()
  return q ? `#${encodeURIComponent(id)}?${q}` : `#${encodeURIComponent(id)}`
}

interface RoutingValue {
  activeId: string | null
  params: URLSearchParams
  navigate: (id: string) => void
  setParams: (params: URLSearchParams) => void
}

const RoutingContext = createContext<RoutingValue | null>(null)

/** Owns hash routing for the shell. Reads `window.location.hash`, listens for
 * `hashchange`, and exposes navigation + per-tab query updates. */
export function RoutingProvider({ children }: { children: ReactNode }) {
  const [hash, setHash] = useState<string>(() =>
    typeof window === 'undefined' ? '' : window.location.hash,
  )

  useEffect(() => {
    if (typeof window === 'undefined') return
    const onHash = () => setHash(window.location.hash)
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  const { id: activeId, params } = useMemo(() => parseHash(hash), [hash])

  const navigate = useCallback((id: string) => {
    if (typeof window === 'undefined') return
    window.location.hash = buildHash(id)
  }, [])

  const setParams = useCallback(
    (next: URLSearchParams) => {
      if (typeof window === 'undefined') return
      const current = parseHash(window.location.hash)
      const id = current.id
      if (!id) return
      window.location.hash = buildHash(id, next)
    },
    [],
  )

  const value = useMemo<RoutingValue>(
    () => ({ activeId, params, navigate, setParams }),
    [activeId, params, navigate, setParams],
  )

  return <RoutingContext.Provider value={value}>{children}</RoutingContext.Provider>
}

function useRouting(): RoutingValue {
  const ctx = useContext(RoutingContext)
  if (!ctx) throw new Error('routing hooks must be used within <DevDashboard>')
  return ctx
}

/** The active tab id from the hash (null when no/unknown hash). */
export function useActiveTabId(): string | null {
  return useRouting().activeId
}

/** Imperatively navigate to a tab by id. */
export function useNavigateTab(): (id: string) => void {
  return useRouting().navigate
}

/**
 * Typed deep-link filter state for the active tab. Reads from the hash query
 * via the codec; writing updates the hash (preserving the active tab id), so
 * filter state is shareable/bookmarkable (ADR-D03).
 */
export function useTabQuery<T>(codec: QueryCodec<T>): [T, (value: T) => void] {
  const { params, setParams } = useRouting()
  const value = useMemo(() => codec.parse(params), [codec, params])
  const setValue = useCallback(
    (next: T) => setParams(codec.serialize(next)),
    [codec, setParams],
  )
  return [value, setValue]
}
