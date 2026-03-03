module.exports = {
  darkMode: 'class',
  content: [
    '../templates/**/*.html',
    '../../**/templates/**/*.html',
    '../../core/templates/**/*.html',
  ],
  theme: {
    extend: {
      colors: {
        'dark-bg': 'rgb(var(--color-bg) / <alpha-value>)',
        'dark-surface': 'rgb(var(--color-surface) / <alpha-value>)',
        'dark-surface-alt': 'rgb(var(--color-surface-alt) / <alpha-value>)',
        'dark-surface-hover': 'rgb(var(--color-surface-hover) / <alpha-value>)',
        'dark-border': 'rgb(var(--color-border) / <alpha-value>)',
        'dark-text': 'rgb(var(--color-text) / <alpha-value>)',
        'dark-text-secondary': 'rgb(var(--color-text-secondary) / <alpha-value>)',
        'dark-text-tertiary': 'rgb(var(--color-text-tertiary) / <alpha-value>)',
        'dark-muted': 'rgb(var(--color-muted) / <alpha-value>)',
        'dark-icon-muted': 'rgb(var(--color-icon-muted) / <alpha-value>)',
        'dark-accent': 'rgb(var(--color-accent) / <alpha-value>)',
        'dark-accent-hover': 'rgb(var(--color-accent-hover) / <alpha-value>)',
        'dark-btn-neutral': 'rgb(var(--color-btn-neutral) / <alpha-value>)',
        'dark-btn-neutral-hover': 'rgb(var(--color-btn-neutral-hover) / <alpha-value>)',
      }
    }
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}
