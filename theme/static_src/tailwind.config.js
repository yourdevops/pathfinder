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
      }
    }
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}
