import type { CSSProperties } from 'react'
import type { ThemeTokens } from './types'

/**
 * Bundled neutral default theme so devdash looks finished out-of-box. Hosts
 * override any subset at runtime via the `theme` prop (CSS custom properties)
 * or at build time via the Tailwind preset. No host theme names are baked in.
 */
export const defaultTheme: ThemeTokens = {
  'color-surface': '#ffffff',
  'color-surface-variant': '#f4f4f5',
  'color-on-surface': '#1f2225',
  'color-on-surface-variant': '#6b7075',
  'color-primary': '#3b6ea5',
  'color-on-primary': '#ffffff',
  'color-outline': '#d4d6d9',
  'color-danger': '#c0392b',
  'color-warn': '#b8860b',
  'color-ok': '#2e7d4f',
  'radius-sm': '4px',
  'radius-md': '8px',
  'radius-lg': '14px',
  'font-sans':
    "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
  'font-mono': "ui-monospace, 'SF Mono', Menlo, Consolas, monospace",
}

/** Merge host overrides over the default theme. */
export function resolveTheme(overrides?: ThemeTokens): ThemeTokens {
  return { ...defaultTheme, ...(overrides ?? {}) }
}

/** Turn resolved tokens into an inline style object of `--devdash-*` vars. */
export function themeToCssVars(theme: ThemeTokens): CSSProperties {
  const style: Record<string, string> = {}
  for (const [name, value] of Object.entries(theme)) {
    style[`--devdash-${name}`] = value
  }
  return style as CSSProperties
}
