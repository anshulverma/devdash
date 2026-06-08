import { createContext, useContext, useMemo, type ReactNode } from 'react'
import type { Branding, DevDashContextValue, ThemeTokens } from './types'
import { resolveTheme } from './theme'

const DevDashContext = createContext<DevDashContextValue | null>(null)

export interface DevDashboardProviderProps {
  apiBaseUrl?: string
  fetch?: typeof fetch
  branding?: Branding
  theme?: ThemeTokens
  children: ReactNode
}

const DEFAULT_BRANDING: Branding = { wordmark: 'devdash' }

/**
 * Provides ambient services (api base url, configured fetch, branding, resolved
 * theme) to every tab via `useDevDash()`. Rendered by `<DevDashboard>`, but
 * exported so hosts can wrap custom trees in tests.
 */
export function DevDashboardProvider({
  apiBaseUrl = '',
  fetch: fetchImpl,
  branding = DEFAULT_BRANDING,
  theme,
  children,
}: DevDashboardProviderProps) {
  const value = useMemo<DevDashContextValue>(
    () => ({
      apiBaseUrl,
      fetch: fetchImpl ?? globalThis.fetch.bind(globalThis),
      branding,
      theme: resolveTheme(theme),
    }),
    [apiBaseUrl, fetchImpl, branding, theme],
  )
  return <DevDashContext.Provider value={value}>{children}</DevDashContext.Provider>
}

/** Access the ambient dashboard services from inside a tab. */
export function useDevDash(): DevDashContextValue {
  const ctx = useContext(DevDashContext)
  if (!ctx) {
    throw new Error('useDevDash must be used within <DevDashboard> / <DevDashboardProvider>')
  }
  return ctx
}

// ---------------------------------------------------------------------------
// Category colors — the generic replacement for a host's hardcoded color map.
// A host supplies a `phaseKey -> color` resolver; the lib ships a deterministic
// fallback palette so an unconfigured host still renders.
// ---------------------------------------------------------------------------

export type CategoryColorResolver = (key: string) => string | undefined

const FALLBACK_PALETTE = [
  '#3b6ea5',
  '#2e7d4f',
  '#b8860b',
  '#8e5572',
  '#4f7d8e',
  '#a05a2c',
  '#6a6f8e',
  '#577d5a',
]

function fallbackColor(key: string): string {
  let hash = 0
  for (let i = 0; i < key.length; i++) hash = (hash * 31 + key.charCodeAt(i)) | 0
  const idx = Math.abs(hash) % FALLBACK_PALETTE.length
  return FALLBACK_PALETTE[idx] as string
}

const CategoryColorContext = createContext<CategoryColorResolver | null>(null)

export function CategoryColorProvider({
  resolve,
  children,
}: {
  resolve?: CategoryColorResolver
  children: ReactNode
}) {
  return <CategoryColorContext.Provider value={resolve ?? null}>{children}</CategoryColorContext.Provider>
}

/** Resolve a stable color for a category/phase key, falling back to a
 * deterministic palette when the host supplies none. */
export function useCategoryColor(): (key: string) => string {
  const resolve = useContext(CategoryColorContext)
  return useMemo(
    () => (key: string) => resolve?.(key) ?? fallbackColor(key),
    [resolve],
  )
}
