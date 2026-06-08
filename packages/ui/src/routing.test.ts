import { describe, it, expect } from 'vitest'
import { parseHash, buildHash } from './routing'

describe('hash routing helpers', () => {
  it('parses a bare tab hash', () => {
    const { id, params } = parseHash('#logs')
    expect(id).toBe('logs')
    expect([...params.keys()]).toEqual([])
  })

  it('parses a tab hash with query params', () => {
    const { id, params } = parseHash('#events?severity=error&since=3600')
    expect(id).toBe('events')
    expect(params.get('severity')).toBe('error')
    expect(params.get('since')).toBe('3600')
  })

  it('returns null id for an empty hash', () => {
    expect(parseHash('').id).toBeNull()
    expect(parseHash('#').id).toBeNull()
  })

  it('round-trips id + params through buildHash', () => {
    const p = new URLSearchParams({ a: '1', b: 'two' })
    const built = buildHash('phases', p)
    const back = parseHash(built)
    expect(back.id).toBe('phases')
    expect(back.params.get('a')).toBe('1')
    expect(back.params.get('b')).toBe('two')
  })

  it('omits the query when there are no params', () => {
    expect(buildHash('logs')).toBe('#logs')
    expect(buildHash('logs', new URLSearchParams())).toBe('#logs')
  })
})
