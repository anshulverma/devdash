import { Suspense, useMemo, type ReactNode } from 'react'
import type { Branding, DevDashContextValue, TabDescriptor, ThemeTokens } from './types'
import {
  CategoryColorProvider,
  DevDashboardProvider,
  useDevDash,
  type CategoryColorResolver,
} from './context'
import { RoutingProvider, useActiveTabId, useNavigateTab } from './routing'
import { TabErrorBoundary } from './ErrorBoundary'
import { resolveTheme, themeToCssVars } from './theme'

export interface DevDashboardProps {
  /** Tabs to render, composed by the host at build time (ADR-D01). Defaults are
   * never auto-injected — this array is the complete set, in display order. */
  tabs: TabDescriptor[]
  branding?: Branding
  theme?: ThemeTokens
  apiBaseUrl?: string
  fetch?: typeof fetch
  /** Host resolver for category/phase colors. */
  categoryColor?: CategoryColorResolver
}

function isProd(): boolean {
  // Read NODE_ENV without depending on @types/node (this is a browser lib).
  // Bundlers replace `process.env.NODE_ENV`; absent any bundler/runtime we
  // default to dev semantics (throw on duplicate ids).
  const env = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process
    ?.env
  return env?.NODE_ENV === 'production'
}

/** De-duplicate by id: throw in dev (programming error), first-wins + warn in
 * prod so the operator dashboard still boots. */
export function dedupeTabs(tabs: TabDescriptor[]): TabDescriptor[] {
  const seen = new Set<string>()
  const out: TabDescriptor[] = []
  for (const tab of tabs) {
    if (seen.has(tab.id)) {
      const msg = `[devdash] duplicate tab id "${tab.id}"`
      if (!isProd()) throw new Error(msg)
      console.error(msg)
      continue
    }
    seen.add(tab.id)
    out.push(tab)
  }
  return out
}

/** Apply explicit `order` (stable) while preserving array order as the default. */
function orderTabs(tabs: TabDescriptor[]): TabDescriptor[] {
  return tabs
    .map((tab, index) => ({ tab, index }))
    .sort((a, b) => {
      const ao = a.tab.order ?? a.index
      const bo = b.tab.order ?? b.index
      return ao - bo || a.index - b.index
    })
    .map((e) => e.tab)
}

export function DevDashboard(props: DevDashboardProps) {
  const { tabs, branding, theme, apiBaseUrl = '', fetch: fetchImpl, categoryColor } = props
  const resolvedTheme = useMemo(() => resolveTheme(theme), [theme])

  return (
    <div
      className="devdash-root"
      style={{
        ...themeToCssVars(resolvedTheme),
        height: '100svh',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        background: 'var(--devdash-color-surface)',
        color: 'var(--devdash-color-on-surface)',
        fontFamily: 'var(--devdash-font-sans)',
      }}
    >
      <DevDashboardProvider
        apiBaseUrl={apiBaseUrl}
        fetch={fetchImpl}
        branding={branding}
        theme={resolvedTheme}
      >
        <CategoryColorProvider resolve={categoryColor}>
          <RoutingProvider>
            <Shell tabs={tabs} />
          </RoutingProvider>
        </CategoryColorProvider>
      </DevDashboardProvider>
    </div>
  )
}

function Shell({ tabs }: { tabs: TabDescriptor[] }) {
  const ctx = useDevDash()
  const activeId = useActiveTabId()
  const navigate = useNavigateTab()

  const visible = useMemo(() => {
    const deduped = dedupeTabs(tabs)
    const enabled = deduped.filter((t) => filterEnabled(t, ctx))
    return orderTabs(enabled)
  }, [tabs, ctx])

  if (visible.length === 0) {
    return (
      <div
        role="status"
        style={{ margin: 'auto', opacity: 0.7, fontFamily: 'var(--devdash-font-sans)' }}
      >
        No tabs registered.
      </div>
    )
  }

  // Active tab: match the hash id, else fall back to the first (default) tab.
  const active = visible.find((t) => t.id === activeId) ?? visible[0]!

  return (
    <>
      <nav
        role="tablist"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.25rem',
          padding: '0.6rem 1.25rem',
          borderBottom: '1px solid var(--devdash-color-outline)',
        }}
      >
        <Wordmark branding={ctx.branding} />
        {visible.map((tab) => {
          const isActive = tab.id === active.id
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => navigate(tab.id)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.35rem 0.85rem',
                borderRadius: 'var(--devdash-radius-lg)',
                border: 'none',
                cursor: 'pointer',
                font: 'inherit',
                background: isActive ? 'var(--devdash-color-on-surface)' : 'transparent',
                color: isActive
                  ? 'var(--devdash-color-surface)'
                  : 'var(--devdash-color-on-surface-variant)',
              }}
            >
              {tab.icon}
              {tab.label}
            </button>
          )
        })}
      </nav>
      <div
        className="devdash-tab-body"
        style={{
          flex: 1,
          minHeight: 0,
          overflow: active.scrollModel === 'chrome' ? 'hidden' : 'auto',
        }}
      >
        <TabErrorBoundary label={active.label}>
          <Suspense fallback={<TabFallback />}>
            <active.component tab={active} />
          </Suspense>
        </TabErrorBoundary>
      </div>
    </>
  )
}

function filterEnabled(tab: TabDescriptor, ctx: DevDashContextValue): boolean {
  try {
    return tab.enabled ? tab.enabled(ctx) : true
  } catch {
    return true
  }
}

function Wordmark({ branding }: { branding: Branding }) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.5rem',
        marginRight: '0.75rem',
        fontSize: '0.85rem',
        letterSpacing: '0.12em',
        textTransform: 'uppercase',
        color: 'var(--devdash-color-on-surface-variant)',
      }}
    >
      {branding.logo}
      {branding.wordmark}
    </span>
  ) as ReactNode
}

function TabFallback() {
  return (
    <div style={{ padding: '1.5rem', opacity: 0.6 }} aria-busy="true">
      Loading…
    </div>
  )
}
