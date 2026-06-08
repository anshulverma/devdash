import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { DevDashboard } from '../DevDashboard'
import { logsTab } from './index'
import { inMemoryLogsClient } from './memoryClient'
import type { LogEntry } from './types'

const SAMPLE: LogEntry[] = [
  { id: '1', ts: '2026-06-08T00:00:01Z', level: 'info', message: 'service started', service: 'api' },
  { id: '2', ts: '2026-06-08T00:00:02Z', level: 'error', message: 'connection refused', service: 'worker' },
]

beforeEach(() => {
  window.location.hash = ''
})
afterEach(() => cleanup())

describe('inMemoryLogsClient', () => {
  it('filters search by level + substring', async () => {
    const c = inMemoryLogsClient(SAMPLE)
    expect((await c.search({ levels: ['error'] })).entries.map((e) => e.id)).toEqual(['2'])
    expect((await c.search({ search: 'started' })).entries.map((e) => e.id)).toEqual(['1'])
  })

  it('delivers pushed entries to subscribers', async () => {
    const c = inMemoryLogsClient([])
    const got: string[] = []
    c.subscribe({ levels: ['error'] }, { onEntry: (e) => got.push(e.id) })
    c.push({ id: '9', ts: 't', level: 'info', message: 'ignored' })
    c.push({ id: '7', ts: 't', level: 'error', message: 'boom' })
    expect(got).toEqual(['7'])
  })

  it('reports facets', async () => {
    const f = await inMemoryLogsClient(SAMPLE).facets()
    expect(f.services).toEqual(['api', 'worker'])
    expect(f.levels).toEqual(['error', 'info'])
  })
})

describe('LogsTab (capability-driven)', () => {
  it('renders searched rows from the in-memory client', async () => {
    render(<DevDashboard tabs={[logsTab({ client: inMemoryLogsClient(SAMPLE) })]} />)
    expect(await screen.findByText('service started')).toBeInTheDocument()
    expect(screen.getByText('connection refused')).toBeInTheDocument()
  })

  it('hides the search box when the adapter cannot search', async () => {
    const client = inMemoryLogsClient(SAMPLE, { capabilities: { can_search: false } })
    render(<DevDashboard tabs={[logsTab({ client })]} />)
    // facets still load (levels chips appear) but no search input
    expect(await screen.findByRole('group')).toBeInTheDocument()
    expect(screen.queryByLabelText('search logs')).not.toBeInTheDocument()
  })

  it('shows the declared search mode in the status strip', async () => {
    render(<DevDashboard tabs={[logsTab({ client: inMemoryLogsClient(SAMPLE) })]} />)
    expect(await screen.findByText(/search: substring/)).toBeInTheDocument()
  })
})
