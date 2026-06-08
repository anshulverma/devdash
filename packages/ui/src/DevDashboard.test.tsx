import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { DevDashboard, dedupeTabs } from './DevDashboard'
import type { TabDescriptor } from './types'

function tab(id: string, label: string, body: string): TabDescriptor {
  return {
    id,
    label,
    scrollModel: 'scroll',
    component: () => <div>{body}</div>,
  }
}

beforeEach(() => {
  window.location.hash = ''
})
afterEach(() => cleanup())

describe('DevDashboard shell', () => {
  it('renders all tab labels and shows the first tab by default', () => {
    render(<DevDashboard tabs={[tab('a', 'Alpha', 'ALPHA BODY'), tab('b', 'Beta', 'BETA BODY')]} />)
    expect(screen.getByRole('tab', { name: 'Alpha' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Beta' })).toBeInTheDocument()
    expect(screen.getByText('ALPHA BODY')).toBeInTheDocument()
    expect(screen.queryByText('BETA BODY')).not.toBeInTheDocument()
  })

  it('navigates to a tab on click (updates the hash) and renders its body', async () => {
    render(<DevDashboard tabs={[tab('a', 'Alpha', 'ALPHA BODY'), tab('b', 'Beta', 'BETA BODY')]} />)
    fireEvent.click(screen.getByRole('tab', { name: 'Beta' }))
    expect(window.location.hash).toBe('#b')
    // jsdom dispatches `hashchange` asynchronously; the shell re-renders on it.
    expect(await screen.findByText('BETA BODY')).toBeInTheDocument()
    expect(screen.queryByText('ALPHA BODY')).not.toBeInTheDocument()
  })

  it('falls back to the default tab on an unknown hash', () => {
    window.location.hash = '#does-not-exist'
    render(<DevDashboard tabs={[tab('a', 'Alpha', 'ALPHA BODY')]} />)
    expect(screen.getByText('ALPHA BODY')).toBeInTheDocument()
  })

  it('renders an explicit empty state when zero tabs are registered', () => {
    render(<DevDashboard tabs={[]} />)
    expect(screen.getByText('No tabs registered.')).toBeInTheDocument()
  })

  it('applies host theme overrides as --devdash-* css vars', () => {
    const { container } = render(
      <DevDashboard tabs={[tab('a', 'Alpha', 'A')]} theme={{ 'color-primary': '#abccde' }} />,
    )
    const root = container.querySelector('.devdash-root') as HTMLElement
    expect(root.style.getPropertyValue('--devdash-color-primary')).toBe('#abccde')
  })

  it('isolates a crashing tab behind a per-tab error boundary', () => {
    const Boom = () => {
      throw new Error('kaboom')
    }
    const tabs: TabDescriptor[] = [
      { id: 'ok', label: 'OK', scrollModel: 'scroll', component: () => <div>OK BODY</div> },
      { id: 'boom', label: 'Boom', scrollModel: 'scroll', component: Boom },
    ]
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    window.location.hash = '#boom'
    render(<DevDashboard tabs={tabs} />)
    // The shell + nav survive; the crashed tab shows a contained alert.
    expect(screen.getByRole('tab', { name: 'OK' })).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('This tab crashed.')
    spy.mockRestore()
  })

  it('uses a host-supplied branding wordmark', () => {
    render(<DevDashboard tabs={[tab('a', 'Alpha', 'A')]} branding={{ wordmark: 'My App / Dev' }} />)
    expect(screen.getByText('My App / Dev')).toBeInTheDocument()
  })
})

describe('dedupeTabs (ADR-D01 build-time composition)', () => {
  it('throws on duplicate ids in dev', () => {
    expect(() => dedupeTabs([tab('x', 'X', '1'), tab('x', 'X2', '2')])).toThrow(/duplicate tab id "x"/)
  })

  it('keeps distinct ids in array order', () => {
    const result = dedupeTabs([tab('a', 'A', '1'), tab('b', 'B', '2')])
    expect(result.map((t) => t.id)).toEqual(['a', 'b'])
  })
})
