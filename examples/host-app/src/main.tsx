import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import {
  DevDashboard,
  RecordTable,
  FilterChips,
  StatusStrip,
  useTabQuery,
  type TabDescriptor,
  type TabProps,
  type QueryCodec,
} from '@devdash/ui'

// --- A placeholder "scroll" tab -------------------------------------------
function Overview() {
  return (
    <div style={{ padding: '1.5rem', lineHeight: 1.6 }}>
      <h1 style={{ marginTop: 0 }}>Overview</h1>
      <p>A long-form (scroll) tab. The shell parent scrolls this content.</p>
    </div>
  )
}

function About() {
  return (
    <div style={{ padding: '1.5rem' }}>
      <h1 style={{ marginTop: 0 }}>About</h1>
      <p>This example exercises the devdash tab-plugin API end to end.</p>
    </div>
  )
}

// --- A custom "chrome" tab built on devdash primitives --------------------
// Demonstrates the "shell for events": a host-authored tab that reuses the
// shared RecordTable + FilterChips + StatusStrip and deep-links its filter
// state via useTabQuery.
interface Row {
  id: string
  level: string
  message: string
}

const SAMPLE: Row[] = [
  { id: '1', level: 'info', message: 'service started' },
  { id: '2', level: 'warn', message: 'cache miss' },
  { id: '3', level: 'error', message: 'connection refused' },
  { id: '4', level: 'info', message: 'request handled' },
]

const filterCodec: QueryCodec<string[]> = {
  parse: (p) => (p.get('levels') ? p.get('levels')!.split(',') : []),
  serialize: (levels) =>
    new URLSearchParams(levels.length ? { levels: levels.join(',') } : {}),
}

function Records(_props: TabProps) {
  const [levels, setLevels] = useTabQuery(filterCodec)
  const rows = levels.length ? SAMPLE.filter((r) => levels.includes(r.level)) : SAMPLE
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '0.75rem 1rem' }}>
        <FilterChips
          options={[{ value: 'info' }, { value: 'warn' }, { value: 'error' }]}
          selected={levels}
          onChange={setLevels}
        />
      </div>
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '0 1rem' }}>
        <RecordTable
          rows={rows}
          rowKey={(r) => r.id}
          columns={[
            { key: 'level', header: 'level', width: 80 },
            { key: 'message', header: 'message' },
          ]}
        />
      </div>
      <StatusStrip live>{rows.length} records (deep-linked via #records?levels=…)</StatusStrip>
    </div>
  )
}

const tabs: TabDescriptor[] = [
  { id: 'overview', label: 'Overview', scrollModel: 'scroll', component: Overview },
  { id: 'records', label: 'Records', scrollModel: 'chrome', component: Records },
  { id: 'about', label: 'About', scrollModel: 'scroll', component: About },
]

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <DevDashboard
      tabs={tabs}
      branding={{ wordmark: 'Example / Dev' }}
      theme={{ 'color-primary': '#3b6ea5', 'color-on-surface': '#1f2225' }}
      categoryColor={(key) => (key === 'error' ? '#c0392b' : undefined)}
    />
  </StrictMode>,
)
