import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { DevDashboard } from '../DevDashboard'
import { phasesTab } from './index'
import { inMemoryPhasesClient } from './memoryClient'

beforeEach(() => {
  window.location.hash = ''
})
afterEach(() => cleanup())

const PHASES = [
  { phase: 'ui', label: 'UI', status: 'in_progress', complexity: 5, color: '#abc' },
  { phase: 'api', label: 'API', status: 'pending', complexity: 3 },
]

describe('inMemoryPhasesClient', () => {
  it('returns provided data and empty defaults', async () => {
    const c = inMemoryPhasesClient({ phases: PHASES })
    expect((await c.listPhases()).map((p) => p.phase)).toEqual(['ui', 'api'])
    expect((await c.projection()).method).toBe('none')
    expect((await c.tokenStats()).cost_usd).toBe(0)
  })
})

describe('PhasesTab', () => {
  it('renders the phase table with labels', async () => {
    render(<DevDashboard tabs={[phasesTab({ client: inMemoryPhasesClient({ phases: PHASES }) })]} />)
    expect(await screen.findByText('UI')).toBeInTheDocument()
    expect(screen.getByText('API')).toBeInTheDocument()
  })

  it('shows the projection finish date when calibrated', async () => {
    const client = inMemoryPhasesClient({
      phases: PHASES,
      projection: {
        method: 'calibrated',
        cumulative_sec: 3600,
        remaining_sec: 3600,
        target_sec: 7200,
        burn_per_day_sec: 3600,
        projected_finish_date: '2026-07-01',
      },
    })
    render(<DevDashboard tabs={[phasesTab({ client })]} />)
    expect(await screen.findByText('2026-07-01')).toBeInTheDocument()
  })

  it("hides the finish date and prompts for complexity when method is 'none'", async () => {
    render(<DevDashboard tabs={[phasesTab({ client: inMemoryPhasesClient({ phases: PHASES }) })]} />)
    expect(await screen.findByText(/add complexity/)).toBeInTheDocument()
  })

  it('renders token cost from stats', async () => {
    const client = inMemoryPhasesClient({
      tokenStats: { messages: 12, input_tokens: 1, output_tokens: 2, cost_usd: 4.2, by_model: {} },
    })
    render(<DevDashboard tabs={[phasesTab({ client })]} />)
    expect(await screen.findByText('$4.20')).toBeInTheDocument()
  })
})
