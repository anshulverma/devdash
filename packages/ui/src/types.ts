import type { ComponentType, LazyExoticComponent, ReactNode } from 'react'

/**
 * Whether the shell parent scrolls (long-form tabs) or the tab owns its own
 * internal scroller with a pinned status strip (chrome-managed tabs like logs).
 * MANDATORY and non-defaulted — a wrong default silently clips live-arriving
 * rows (ADR-D02).
 */
export type ScrollModel = 'scroll' | 'chrome'

/**
 * Typed (de)serialization of a tab's deep-link filter state to/from the URL
 * hash query string. The shell owns hash routing; a tab supplies a codec and
 * gets shareable deep links for free (ADR-D03).
 */
export interface QueryCodec<T> {
  parse: (params: URLSearchParams) => T
  serialize: (value: T) => URLSearchParams
}

/**
 * Props passed to every registered tab component. Services are pulled from
 * context via hooks (`useDevDash`, `useTabQuery`, `useEventSourceTail`) rather
 * than threaded as props, so lazy/custom tabs need no prop wiring.
 */
export interface TabProps {
  /** The descriptor that registered this tab. */
  tab: TabDescriptor
}

/**
 * The public data shape a host registers to add a dashboard tab. Part of the
 * library's semver surface. Build-time composition only — no runtime plugin
 * loader (ADR-D01).
 */
export interface TabDescriptor {
  /** Freeform id; becomes the hash route segment. Must be unique. */
  id: string
  label: string
  component: ComponentType<TabProps> | LazyExoticComponent<ComponentType<TabProps>>
  scrollModel: ScrollModel
  icon?: ReactNode
  /**
   * Hash this tab is selected by. Defaults to `#<id>`; the first tab in the
   * array is the default when no hash matches.
   */
  defaultHash?: string
  /** Explicit ordering; array order wins by default. */
  order?: number
  /** Optional predicate to hide the tab (e.g. feature flags). */
  enabled?: (ctx: DevDashContextValue) => boolean
  /** Optional typed deep-link query codec for this tab. */
  query?: QueryCodec<unknown>
}

export interface Branding {
  wordmark: ReactNode
  logo?: ReactNode
  subtitle?: ReactNode
}

/**
 * Theme override: a map of `--devdash-*` custom-property names (WITHOUT the
 * leading `--`) to CSS values. Merged over the bundled neutral default.
 * e.g. `{ 'color-primary': '#4A6670' }` sets `--devdash-color-primary`.
 */
export type ThemeTokens = Record<string, string>

/** Ambient services exposed to every tab via `useDevDash()`. */
export interface DevDashContextValue {
  /** Base URL the tabs' backend routers are mounted under. */
  apiBaseUrl: string
  /** Pre-configured fetch (base URL + any auth header). */
  fetch: typeof fetch
  branding: Branding
  /** The resolved theme tokens in effect. */
  theme: ThemeTokens
}
