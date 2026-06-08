import { describe, it, expect } from 'vitest'
import { DEVDASH_CONTRACT_VERSION } from './index'
import { devdashTailwindPreset } from './tailwind-preset'

describe('@devdash/ui skeleton', () => {
  it('exposes a numeric contract version', () => {
    expect(typeof DEVDASH_CONTRACT_VERSION).toBe('number')
  })
  it('ships a tailwind preset that maps devdash-* to CSS vars', () => {
    expect(devdashTailwindPreset.theme.extend.colors['devdash-surface']).toBe(
      'var(--devdash-color-surface)',
    )
  })
})
