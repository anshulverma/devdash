// @devdash/ui — public entry (semver-governed surface).

/** Wire-contract version negotiated with the backend (ADR-D12). */
export const DEVDASH_CONTRACT_VERSION = 1 as const

// Types
export type {
  ScrollModel,
  QueryCodec,
  TabProps,
  TabDescriptor,
  Branding,
  ThemeTokens,
  DevDashContextValue,
} from './types'

// Shell + tab-plugin API
export { DevDashboard, dedupeTabs, type DevDashboardProps } from './DevDashboard'
export { TabErrorBoundary } from './ErrorBoundary'

// Context + theming
export {
  DevDashboardProvider,
  useDevDash,
  CategoryColorProvider,
  useCategoryColor,
  type DevDashboardProviderProps,
  type CategoryColorResolver,
} from './context'
export { defaultTheme, resolveTheme, themeToCssVars } from './theme'

// Routing
export {
  parseHash,
  buildHash,
  useActiveTabId,
  useNavigateTab,
  useTabQuery,
  type ParsedHash,
} from './routing'

// Viewer primitives ("the shell for events")
export {
  RecordTable,
  FilterChips,
  TimeRangePicker,
  JsonDetailPanel,
  StatusStrip,
  type Column,
  type RecordTableProps,
  type FilterChipsProps,
  type TimeRangePickerProps,
  type StatusStripProps,
} from './primitives'
export {
  useEventSourceTail,
  type TailEvent,
  type TailState,
  type UseEventSourceTailOptions,
  type EventSourceLike,
} from './hooks/useEventSourceTail'
