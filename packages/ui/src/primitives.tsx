import type { ReactNode } from 'react'

// Viewer primitives a host's custom tab reuses to match the built-ins — "the
// shell for events". M1 ships working-but-minimal versions; the Logs/Phases
// tabs (M3/M4) drive their richer features.

export interface Column<Row> {
  key: string
  header: ReactNode
  render?: (row: Row) => ReactNode
  width?: string | number
}

export interface RecordTableProps<Row> {
  columns: Column<Row>[]
  rows: Row[]
  rowKey: (row: Row) => string
  empty?: ReactNode
}

/** Time-ordered, columnar record table. */
export function RecordTable<Row>({ columns, rows, rowKey, empty }: RecordTableProps<Row>) {
  if (rows.length === 0) {
    return <div style={{ padding: '1rem', opacity: 0.6 }}>{empty ?? 'No records.'}</div>
  }
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--devdash-font-mono)' }}>
      <thead>
        <tr>
          {columns.map((c) => (
            <th
              key={c.key}
              style={{
                textAlign: 'left',
                padding: '0.35rem 0.6rem',
                borderBottom: '1px solid var(--devdash-color-outline)',
                width: c.width,
              }}
            >
              {c.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={rowKey(row)}>
            {columns.map((c) => (
              <td key={c.key} style={{ padding: '0.3rem 0.6rem', verticalAlign: 'top' }}>
                {c.render ? c.render(row) : String((row as Record<string, unknown>)[c.key] ?? '')}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export interface FilterChipsProps {
  options: { value: string; label?: ReactNode }[]
  selected: string[]
  onChange: (selected: string[]) => void
}

/** Multi-select chip filter. */
export function FilterChips({ options, selected, onChange }: FilterChipsProps) {
  const toggle = (value: string) =>
    onChange(selected.includes(value) ? selected.filter((v) => v !== value) : [...selected, value])
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }} role="group">
      {options.map((o) => {
        const on = selected.includes(o.value)
        return (
          <button
            key={o.value}
            type="button"
            aria-pressed={on}
            onClick={() => toggle(o.value)}
            style={{
              padding: '0.2rem 0.6rem',
              borderRadius: 'var(--devdash-radius-lg)',
              border: '1px solid var(--devdash-color-outline)',
              cursor: 'pointer',
              font: 'inherit',
              background: on ? 'var(--devdash-color-primary)' : 'transparent',
              color: on ? 'var(--devdash-color-on-primary)' : 'var(--devdash-color-on-surface)',
            }}
          >
            {o.label ?? o.value}
          </button>
        )
      })}
    </div>
  )
}

export interface TimeRangePickerProps {
  value: string
  options?: { value: string; label: string }[]
  onChange: (value: string) => void
}

const DEFAULT_RANGES = [
  { value: '15m', label: '15m' },
  { value: '1h', label: '1h' },
  { value: '6h', label: '6h' },
  { value: '24h', label: '24h' },
  { value: '7d', label: '7d' },
]

/** Relative time-range selector. */
export function TimeRangePicker({ value, options = DEFAULT_RANGES, onChange }: TimeRangePickerProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      aria-label="time range"
      style={{ font: 'inherit', padding: '0.2rem 0.4rem', borderRadius: 'var(--devdash-radius-sm)' }}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  )
}

/** Pretty-printed JSON detail panel. */
export function JsonDetailPanel({ value }: { value: unknown }) {
  return (
    <pre
      style={{
        margin: 0,
        padding: '0.75rem',
        overflow: 'auto',
        fontFamily: 'var(--devdash-font-mono)',
        fontSize: '0.85em',
        background: 'var(--devdash-color-surface-variant)',
        borderRadius: 'var(--devdash-radius-md)',
      }}
    >
      {JSON.stringify(value, null, 2)}
    </pre>
  )
}

export interface StatusStripProps {
  live?: boolean
  children?: ReactNode
}

/** Pinned status strip for chrome-managed tabs. */
export function StatusStrip({ live, children }: StatusStripProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        padding: '0.35rem 0.75rem',
        borderTop: '1px solid var(--devdash-color-outline)',
        fontSize: '0.8em',
        color: 'var(--devdash-color-on-surface-variant)',
      }}
    >
      <span
        aria-hidden
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: live ? 'var(--devdash-color-ok)' : 'var(--devdash-color-outline)',
        }}
      />
      {children}
    </div>
  )
}
