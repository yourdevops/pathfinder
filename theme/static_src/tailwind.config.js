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
        'dark-bg': '#0f172a',        // slate-900
        'dark-surface': '#1e293b',   // slate-800
        'dark-border': '#334155',    // slate-700
        'dark-text': '#f1f5f9',      // slate-100
        'dark-muted': '#94a3b8',     // slate-400
        'dark-accent': '#3b82f6',    // blue-500
        'dark-accent-hover': '#2563eb', // blue-600
        'dark-surface-alt': '#111827',    // gray-900 — deeper surface (build rows, code blocks)
        'dark-surface-hover': '#374151',  // gray-700 — hover state for interactive surfaces
        'dark-text-secondary': '#d1d5db', // gray-300 — secondary text (log lines, badge text)
        'dark-text-tertiary': '#9ca3af',  // gray-400 — tertiary text (timestamps, copy buttons)
        'dark-icon-muted': '#6b7280',     // gray-500 — muted icons and copy indicators
        'dark-btn-neutral': '#4b5563',    // gray-600 — neutral button bg (archive/secondary actions)
        'dark-btn-neutral-hover': '#374151', // gray-700 — neutral button hover
      }
    }
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}
