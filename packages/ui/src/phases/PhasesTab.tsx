import { useEffect, useState } from 'react'
import { RecordTable } from '../primitives'
import { useCategoryColor } from '../context'
import type { Phase, PhasesClient, Projection, TokenStats } from './types'

function hours(sec: number): string {
  return `${(sec / 3600).toFixed(1)}h`
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div
      style={{
        flex: 1,
        minWidth: 180,
        padding: '0.9rem 1.1rem',
        borderRadius: 'var(--devdash-radius-lg)',
        background: 'var(--devdash-color-surface-variant)',
      }}
    >
      <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.1em', opacity: 0.7 }}>
        {title}
      </div>
      <div style={{ marginTop: '0.35rem', fontSize: '1.4rem' }}>{children}</div>
    </div>
  )
}

function ProjectionCard({ p }: { p: Projection }) {
  if (p.method === 'none') {
    return <Card title="Projection">— (add complexity to phases)</Card>
  }
  return (
    <Card title="Projection">
      {p.projected_finish_date ?? '—'}
      <div style={{ fontSize: '0.8rem', opacity: 0.7 }}>
        {hours(p.remaining_sec)} left · {p.method}
      </div>
    </Card>
  )
}

export function PhasesTab({ client }: { client: PhasesClient }) {
  const color = useCategoryColor()
  const [phases, setPhases] = useState<Phase[]>([])
  const [stats, setStats] = useState<TokenStats | null>(null)
  const [projection, setProjection] = useState<Projection | null>(null)

  useEffect(() => {
    let alive = true
    client.listPhases().then((p) => alive && setPhases(p)).catch(() => {})
    client.tokenStats().then((s) => alive && setStats(s)).catch(() => {})
    client.projection().then((p) => alive && setProjection(p)).catch(() => {})
    return () => {
      alive = false
    }
  }, [client])

  return (
    <div style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        {projection && <ProjectionCard p={projection} />}
        {stats && <Card title="AI cost">${stats.cost_usd.toFixed(2)}</Card>}
        {stats && <Card title="Messages">{stats.messages}</Card>}
      </div>

      <RecordTable
        rows={phases}
        rowKey={(r) => r.phase}
        empty="No phases configured."
        columns={[
          {
            key: 'phase',
            header: 'phase',
            render: (r) => (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
                <span
                  aria-hidden
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    background: r.color ?? color(r.phase),
                  }}
                />
                {r.label ?? r.phase}
              </span>
            ),
          },
          { key: 'status', header: 'status', width: 130, render: (r) => r.status ?? '' },
          {
            key: 'complexity',
            header: 'complexity',
            width: 110,
            render: (r) => (r.complexity == null ? '' : String(r.complexity)),
          },
        ]}
      />
    </div>
  )
}
