// Tailwind preset mapping `devdash-*` utilities onto `--devdash-*` CSS custom
// properties (ADR theme-neutrality). Neutral default theme; hosts override the
// CSS vars at runtime or extend this preset at build time. Expanded in M1.
export const devdashTailwindPreset = {
  theme: {
    extend: {
      colors: {
        'devdash-surface': 'var(--devdash-color-surface)',
        'devdash-on-surface': 'var(--devdash-color-on-surface)',
        'devdash-primary': 'var(--devdash-color-primary)',
      },
      borderRadius: {
        'devdash-md': 'var(--devdash-radius-md)',
      },
    },
  },
}

export default devdashTailwindPreset
