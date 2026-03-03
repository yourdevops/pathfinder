---
phase: 43-frontend-code-deduplication
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - theme/static_src/tailwind.config.js
  - theme/static_src/src/styles.css
  - core/templates/core/services/_builds_tab.html
  - core/templates/core/services/_build_row.html
  - core/templates/core/services/_build_row_expanded.html
  - core/templates/core/services/_build_logs_partial.html
  - core/templates/core/services/_stats_row.html
  - core/templates/core/services/_recent_builds.html
  - core/templates/core/services/_details_tab.html
  - core/templates/core/services/_ci_tab.html
  - core/templates/core/services/_ci_manifest_status.html
  - core/templates/core/services/list.html
  - core/templates/core/projects/_services_tab.html
  - core/templates/core/components/nav_service.html
  - core/templates/core/ci_workflows/workflow_detail.html
autonomous: true
requirements: [DEDUP-01, DEDUP-02]

must_haves:
  truths:
    - "All color references in templates use semantic dark-* tokens, not raw gray-*/slate-* colors"
    - "Common UI patterns (status badges, interactive surface hover) use CSS component classes"
    - "Scrollbar CSS uses Tailwind token references, not hardcoded hex values"
    - "Visual appearance is unchanged after refactoring"
  artifacts:
    - path: "theme/static_src/tailwind.config.js"
      provides: "Extended semantic color tokens for surfaces and interactive states"
      contains: "dark-surface-alt"
    - path: "theme/static_src/src/styles.css"
      provides: "CSS component classes for badges, interactive surfaces, scrollbar using tokens"
      contains: "badge-"
  key_links:
    - from: "theme/static_src/tailwind.config.js"
      to: "theme/static_src/src/styles.css"
      via: "@apply directives using new semantic tokens"
      pattern: "dark-surface-alt"
    - from: "core/templates/core/services/_builds_tab.html"
      to: "theme/static_src/src/styles.css"
      via: "CSS component classes replace inline gray-* colors"
      pattern: "badge-|dark-surface-alt"
---

<objective>
Deduplicate frontend color usage by replacing all raw gray-* hardcoded colors with semantic dark-* Tailwind tokens and extracting repeated UI patterns (status badges, hover surfaces) into CSS component classes. This prepares the codebase for a light/dark theme toggle by ensuring all colors flow through a single semantic layer.

Purpose: When a theme toggle is introduced, only the Tailwind config color definitions need to change -- no template hunting for raw color values.
Output: Updated tailwind.config.js with new semantic tokens, styles.css with component classes, and 13 template files with raw colors replaced.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@theme/static_src/tailwind.config.js
@theme/static_src/src/styles.css
@theme/templates/base.html
</context>

<tasks>

<task type="auto">
  <name>Task 1: Extend Tailwind semantic tokens and extract CSS component classes</name>
  <files>
    theme/static_src/tailwind.config.js
    theme/static_src/src/styles.css
  </files>
  <action>
**1. Add missing semantic color tokens to tailwind.config.js:**

The current config has 7 semantic tokens (dark-bg, dark-surface, dark-border, dark-text, dark-muted, dark-accent, dark-accent-hover). Templates use raw gray-800, gray-900, gray-300, gray-500, gray-200, gray-400, gray-700, gray-600 that bypass the semantic layer.

Add these new tokens to the `colors` extend section:

```js
'dark-surface-alt': '#111827',    // gray-900 — deeper surface (build rows, code blocks)
'dark-surface-hover': '#374151',  // gray-700 — hover state for interactive surfaces
'dark-text-secondary': '#d1d5db', // gray-300 — secondary text (log lines, badge text)
'dark-text-tertiary': '#9ca3af',  // gray-400 — tertiary text (timestamps, copy buttons)
'dark-icon-muted': '#6b7280',     // gray-500 — muted icons and copy indicators
'dark-btn-neutral': '#4b5563',    // gray-600 — neutral button bg (archive/secondary actions)
'dark-btn-neutral-hover': '#374151', // gray-700 — neutral button hover
```

**2. Extract repeated status badge patterns into CSS component classes in styles.css:**

Inside `@layer components`, add these badge classes that appear 32+ times across 13 templates:

```css
.badge-success {
  @apply px-2 py-1 text-xs rounded bg-green-500/20 text-green-400;
}
.badge-warning {
  @apply px-2 py-1 text-xs rounded bg-amber-500/20 text-amber-400;
}
.badge-danger {
  @apply px-2 py-1 text-xs rounded bg-red-500/20 text-red-400;
}
.badge-info {
  @apply px-2 py-1 text-xs rounded bg-blue-500/20 text-blue-400;
}
.badge-neutral {
  @apply px-2 py-1 text-xs rounded bg-dark-icon-muted/20 text-dark-text-secondary;
}
.badge-sm-success {
  @apply px-2 py-0.5 text-xs rounded bg-green-500/20 text-green-400;
}
.badge-sm-warning {
  @apply px-2 py-0.5 text-xs rounded bg-amber-500/20 text-amber-400;
}
.badge-sm-danger {
  @apply px-2 py-0.5 text-xs rounded bg-red-500/20 text-red-400;
}
.badge-sm-neutral {
  @apply px-2 py-0.5 text-xs rounded bg-dark-icon-muted/20 text-dark-text-secondary;
}
```

**3. Replace hardcoded hex colors in scrollbar CSS with semantic tokens:**

Replace the `.scrollbar-visible` styles that currently use hardcoded hex:
- `#4b5563` -> use CSS variable or the `dark-btn-neutral` semantic equivalent
- `#1f2937` -> use `dark-surface` semantic equivalent
- `#6b7280` -> use `dark-icon-muted` semantic equivalent

Since scrollbar CSS cannot use @apply, use CSS custom properties approach. At the top of styles.css (before @tailwind directives), add:

```css
:root {
  --scrollbar-track: #1e293b;
  --scrollbar-thumb: #4b5563;
  --scrollbar-thumb-hover: #6b7280;
}
```

Then update `.scrollbar-visible` to reference these variables instead of hardcoded hex. This makes future theme switching a single-point change.

**4. Add an interactive surface hover utility:**

```css
.surface-interactive {
  @apply bg-dark-surface border border-dark-border rounded hover:bg-dark-surface-hover transition-colors;
}
```

This pattern appears 8+ times for buttons/rows that hover to gray-800.
  </action>
  <verify>
    <automated>cd /Users/fandruhin/work/yourdevops/pathfinder && make build 2>&1 | tail -5</automated>
    <manual>Verify styles.css has badge-success, badge-neutral classes and scrollbar uses CSS variables</manual>
  </verify>
  <done>tailwind.config.js has 7 new semantic tokens. styles.css has 9 badge component classes, CSS custom properties for scrollbar, and surface-interactive utility. `make build` succeeds without errors.</done>
</task>

<task type="auto">
  <name>Task 2: Replace all raw gray-* colors in templates with semantic tokens and badge classes</name>
  <files>
    core/templates/core/services/_builds_tab.html
    core/templates/core/services/_build_row.html
    core/templates/core/services/_build_row_expanded.html
    core/templates/core/services/_build_logs_partial.html
    core/templates/core/services/_stats_row.html
    core/templates/core/services/_recent_builds.html
    core/templates/core/services/_details_tab.html
    core/templates/core/services/_ci_tab.html
    core/templates/core/services/_ci_manifest_status.html
    core/templates/core/services/list.html
    core/templates/core/projects/_services_tab.html
    core/templates/core/components/nav_service.html
    core/templates/core/ci_workflows/workflow_detail.html
  </files>
  <action>
Replace all 27 raw gray-* color references across 13 template files with semantic dark-* tokens or new badge component classes. The mapping is:

**Color replacements (raw gray -> semantic token):**

| Raw Color | Semantic Replacement | Context |
|-----------|---------------------|---------|
| `bg-gray-900` | `bg-dark-surface-alt` | Build rows, expanded panels |
| `bg-gray-800` | `bg-dark-surface-hover` | Table headers, hover targets |
| `hover:bg-gray-800` | `hover:bg-dark-surface-hover` | Interactive row/button hover |
| `hover:bg-gray-800/50` | `hover:bg-dark-surface-hover/50` | Card hover states |
| `text-gray-300` | `text-dark-text-secondary` | Badge text, log text, status labels |
| `text-gray-200` | `text-dark-text` | Hover text states (already near dark-text) |
| `text-gray-400` | `text-dark-text-tertiary` | Muted button icons |
| `text-gray-500` | `text-dark-icon-muted` | Muted icons |
| `hover:text-gray-200` | `hover:text-dark-text` | Hover text brightening |
| `hover:text-gray-300` | `hover:text-dark-text-secondary` | Hover text medium |
| `hover:bg-gray-700` | `hover:bg-dark-surface-hover` | Button hover in log viewer |
| `bg-gray-800/90` | `bg-dark-surface-hover/90` | Log viewer action buttons |
| `bg-gray-500/20` | `bg-dark-icon-muted/20` | Neutral badge backgrounds |
| `bg-gray-600` | `bg-dark-btn-neutral` | Archive/secondary buttons |
| `hover:bg-gray-700` | `hover:bg-dark-btn-neutral-hover` | Secondary button hover |

**Badge class replacements (inline patterns -> component classes):**

Replace these repeated inline patterns with badge component classes:

- `px-2 py-1 text-xs rounded bg-gray-500/20 text-gray-300` -> `badge-neutral` (4 occurrences: _ci_tab.html, _ci_manifest_status.html x2, list.html)
- `px-2 py-0.5 text-xs rounded bg-gray-500/20 text-gray-300` -> `badge-sm-neutral` (1 occurrence: workflow_detail.html)

Also replace existing inline status badge patterns with badge classes where the pattern matches exactly:
- `px-2 py-1 text-xs rounded bg-green-500/20 text-green-400` -> `badge-success`
- `px-2 py-1 text-xs rounded bg-amber-500/20 text-amber-400` -> `badge-warning`
- `px-2 py-1 text-xs rounded bg-red-500/20 text-red-400` -> `badge-danger`
- `px-2 py-1 text-xs rounded bg-blue-500/20 text-blue-400` -> `badge-info`

**Specific file changes:**

1. **_builds_tab.html** (7 gray refs): Replace `hover:bg-gray-800` -> `hover:bg-dark-surface-hover`, `bg-gray-800` -> `bg-dark-surface-hover`, `hover:text-gray-200` -> `hover:text-dark-text`
2. **_build_row.html** (2 gray refs): `bg-gray-900 hover:bg-gray-800` -> `bg-dark-surface-alt hover:bg-dark-surface-hover`, `text-gray-500 hover:text-gray-300` -> `text-dark-icon-muted hover:text-dark-text-secondary`
3. **_build_row_expanded.html** (3 gray refs): `bg-gray-900` -> `bg-dark-surface-alt`, `hover:bg-gray-800` -> `hover:bg-dark-surface-hover`, `text-gray-500 hover:text-gray-300` -> `text-dark-icon-muted hover:text-dark-text-secondary`
4. **_build_logs_partial.html** (3 gray refs): `bg-gray-800/90 ... hover:bg-gray-700 text-gray-400 hover:text-gray-200` -> `bg-dark-surface-hover/90 ... hover:bg-dark-surface-hover text-dark-text-tertiary hover:text-dark-text`, `text-gray-300` -> `text-dark-text-secondary`
5. **_stats_row.html** (2 gray refs): `hover:bg-gray-800/50` -> `hover:bg-dark-surface-hover/50`
6. **_recent_builds.html** (1 gray ref): `hover:bg-gray-800/50` -> `hover:bg-dark-surface-hover/50`
7. **_details_tab.html** (1 gray ref): `bg-gray-500/20 text-gray-300` -> `badge-neutral` (in draft status)
8. **_ci_tab.html** (1 gray ref): `bg-gray-500/20 text-gray-300` -> `badge-neutral` (Pending badge)
9. **_ci_manifest_status.html** (2 gray refs): Replace both `bg-gray-500/20 text-gray-300` -> `badge-neutral`
10. **list.html** (services) (1 gray ref): `bg-gray-500/20 text-gray-300` -> `badge-neutral`
11. **_services_tab.html** (1 gray ref): `bg-gray-500/20 text-gray-300` -> `badge-neutral` (draft status)
12. **nav_service.html** (1 gray ref): `bg-gray-500/20 text-gray-300` -> use semantic `bg-dark-icon-muted/20 text-dark-text-secondary`
13. **workflow_detail.html** (2 gray refs): `bg-gray-600 hover:bg-gray-700` -> `bg-dark-btn-neutral hover:bg-dark-btn-neutral-hover`, `bg-gray-500/20 text-gray-300` -> `badge-sm-neutral`

**Important:** Only replace gray-* that is being used for surface/text theming. Do NOT replace semantic status colors (green-400 for success, red-400 for error, amber-400 for warning, blue-400 for info) -- those are semantic already and stay.

After all replacements, run `grep -rn 'bg-gray-\|text-gray-\|hover:bg-gray-\|hover:text-gray-' core/templates/` to verify zero remaining raw gray references in templates.
  </action>
  <verify>
    <automated>cd /Users/fandruhin/work/yourdevops/pathfinder && grep -rn 'bg-gray-\|text-gray-\|hover:bg-gray-\|hover:text-gray-' core/templates/ plugins/; echo "Exit: $?"</automated>
    <manual>The grep should return empty (exit 1). If any matches remain, they need replacement.</manual>
  </verify>
  <done>Zero raw gray-* color references remain in any template file. All 27 occurrences across 13 files replaced with semantic dark-* tokens or badge-* component classes. `make build` succeeds. Visual appearance unchanged (same hex values mapped through semantic layer).</done>
</task>

</tasks>

<verification>
1. `make build` completes without errors (Tailwind compiles with new tokens)
2. `grep -rn 'bg-gray-\|text-gray-\|hover:bg-gray-\|hover:text-gray-' core/templates/ plugins/` returns no matches
3. `grep -rn '#[0-9a-fA-F]\{6\}' theme/static_src/src/styles.css` only shows CSS custom property definitions in :root, not inline usage
4. `uv run python manage.py check` passes
</verification>

<success_criteria>
- All 27 raw gray-* color references replaced with semantic tokens across 13 template files
- 7 new semantic color tokens added to tailwind.config.js
- 9 badge component classes + surface-interactive utility in styles.css
- Scrollbar CSS uses CSS custom properties instead of hardcoded hex
- Build succeeds, Django check passes, visual appearance unchanged
</success_criteria>

<output>
After completion, create `.planning/quick/43-frontend-code-deduplication-as-preparati/43-SUMMARY.md`
</output>
