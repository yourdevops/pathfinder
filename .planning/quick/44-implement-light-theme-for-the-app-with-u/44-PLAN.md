---
phase: 44-implement-light-theme
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - theme/static_src/tailwind.config.js
  - theme/static_src/src/styles.css
  - theme/templates/base.html
  - core/templates/core/auth/login.html
  - core/templates/core/setup/unlock.html
  - core/templates/core/components/nav.html
  - core/templates/core/components/nav_project.html
autonomous: true
requirements: [THEME-01]

must_haves:
  truths:
    - "User can toggle between light and dark theme via a button in the sidebar"
    - "Theme preference persists across page reloads and browser sessions via localStorage"
    - "No flash of wrong theme on page load (correct theme applied before render)"
    - "All semantic token colors change when theme switches (surfaces, text, borders, accents)"
    - "Login page respects the saved theme preference"
  artifacts:
    - path: "theme/static_src/src/styles.css"
      provides: "CSS custom properties for light and dark palettes under :root and .dark selectors"
      contains: ".dark {"
    - path: "theme/static_src/tailwind.config.js"
      provides: "Semantic color tokens using CSS variable references with alpha support"
      contains: "var(--"
    - path: "theme/templates/base.html"
      provides: "Theme toggle Alpine component and flash-prevention script"
      contains: "themeToggle"
    - path: "core/templates/core/components/nav.html"
      provides: "Theme toggle button in sidebar user section"
      contains: "themeToggle"
  key_links:
    - from: "theme/static_src/src/styles.css"
      to: "theme/static_src/tailwind.config.js"
      via: "CSS variables referenced in Tailwind color config"
      pattern: "var\\(--"
    - from: "theme/templates/base.html"
      to: "core/templates/core/components/nav.html"
      via: "Alpine themeToggle component used by sidebar toggle button"
      pattern: "themeToggle"
    - from: "theme/templates/base.html"
      to: "localStorage"
      via: "Flash-prevention script reads theme before render"
      pattern: "_x_theme"
---

<objective>
Implement a light/dark theme toggle for the Pathfinder app with user-level persistence in the browser's localStorage. The toggle should be accessible from the sidebar, persist across sessions, and switch all semantic colors instantly without page reload.

Purpose: Enable users to choose their preferred visual theme. The previous quick task 43 prepared the codebase by extracting semantic color tokens, making this a clean single-point change.
Output: Working theme toggle with light palette, dark palette (existing), persistence, and no flash of wrong theme.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@theme/static_src/tailwind.config.js
@theme/static_src/src/styles.css
@theme/templates/base.html
@core/templates/core/auth/login.html
@core/templates/core/components/nav.html
@core/templates/core/components/nav_project.html
@.planning/quick/43-frontend-code-deduplication-as-preparati/43-SUMMARY.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Convert Tailwind semantic tokens to CSS custom properties with light/dark palettes</name>
  <files>
    theme/static_src/tailwind.config.js
    theme/static_src/src/styles.css
  </files>
  <action>
**1. Update styles.css: Replace the existing `:root` block and add light/dark CSS custom property palettes.**

The current `:root` has 3 scrollbar variables. Replace and expand it with a full palette system. Define colors as space-separated RGB channels (e.g., `15 23 42`) to support Tailwind's opacity modifier syntax (`bg-dark-bg/50`).

Replace the entire `:root { ... }` block at the top of styles.css with:

```css
/* Light theme (default) */
:root {
  --color-bg: 249 250 251;              /* gray-50 */
  --color-surface: 255 255 255;         /* white */
  --color-surface-alt: 243 244 246;     /* gray-100 */
  --color-surface-hover: 229 231 235;   /* gray-200 */
  --color-border: 209 213 219;          /* gray-300 */
  --color-text: 17 24 39;               /* gray-900 */
  --color-text-secondary: 55 65 81;     /* gray-700 */
  --color-text-tertiary: 107 114 128;   /* gray-500 */
  --color-muted: 107 114 128;           /* gray-500 */
  --color-icon-muted: 156 163 175;      /* gray-400 */
  --color-accent: 59 130 246;           /* blue-500 */
  --color-accent-hover: 37 99 235;      /* blue-600 */
  --color-btn-neutral: 229 231 235;     /* gray-200 */
  --color-btn-neutral-hover: 209 213 219; /* gray-300 */
  --scrollbar-track: #f3f4f6;
  --scrollbar-thumb: #d1d5db;
  --scrollbar-thumb-hover: #9ca3af;
}

/* Dark theme */
.dark {
  --color-bg: 15 23 42;                 /* slate-900 */
  --color-surface: 30 41 59;            /* slate-800 */
  --color-surface-alt: 17 24 39;        /* gray-900 */
  --color-surface-hover: 55 65 81;      /* gray-700 */
  --color-border: 51 65 85;             /* slate-700 */
  --color-text: 241 245 249;            /* slate-100 */
  --color-text-secondary: 209 213 219;  /* gray-300 */
  --color-text-tertiary: 156 163 175;   /* gray-400 */
  --color-muted: 148 163 184;           /* slate-400 */
  --color-icon-muted: 107 114 128;      /* gray-500 */
  --color-accent: 59 130 246;           /* blue-500 */
  --color-accent-hover: 37 99 235;      /* blue-600 */
  --color-btn-neutral: 75 85 99;        /* gray-600 */
  --color-btn-neutral-hover: 55 65 81;  /* gray-700 */
  --scrollbar-track: #1e293b;
  --scrollbar-thumb: #4b5563;
  --scrollbar-thumb-hover: #6b7280;
}
```

**2. Update the component classes in styles.css that use `@apply` with the OLD token names.**

After the config change (below), the Tailwind class names stay the same (`dark-bg`, `dark-surface`, etc.) but now resolve to CSS variables. The `@apply` directives in component classes will continue to work because they reference Tailwind utility classes.

No changes needed to the `@layer components` block -- the badge classes, surface-interactive, btn-primary, btn-secondary, card, input-field, and table-row classes all use `@apply` with the semantic token names which remain identical.

**However**, the `input-field` class currently hardcodes light-mode colors (`bg-white`, `text-gray-900`, `placeholder-gray-500`). Update it to use semantic tokens:

```css
.input-field {
  @apply bg-dark-surface border border-dark-border rounded-lg px-3 py-2 text-dark-text placeholder-dark-muted focus:outline-none focus:ring-2 focus:ring-dark-accent focus:border-transparent;
}
```

**3. Update tailwind.config.js: Replace all hardcoded hex values with CSS variable references.**

Replace the entire `colors` object in `theme.extend` with:

```js
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
```

The `<alpha-value>` placeholder is Tailwind v3's mechanism for opacity modifier support. This means `bg-dark-bg/50` will correctly generate `rgb(15 23 42 / 0.5)`.

**Important notes:**
- Keep `darkMode: 'class'` in the config (already set).
- Keep `content` paths and `plugins` unchanged.
- The semantic token CLASS NAMES (`dark-bg`, `dark-surface`, etc.) do NOT change -- only their underlying values switch from hardcoded hex to CSS variable references. This means ZERO template changes are needed for the color system to become theme-aware.
  </action>
  <verify>
    <automated>cd /Users/fandruhin/work/yourdevops/pathfinder && make build 2>&1 | tail -5</automated>
    <manual>Verify tailwind.config.js uses var(--color-*) references and styles.css has both :root and .dark blocks with RGB channel values</manual>
  </verify>
  <done>Tailwind config uses CSS variable references for all 14 semantic tokens. styles.css defines light palette in :root and dark palette in .dark selector. `make build` succeeds. input-field class uses semantic tokens. Dark mode appearance is visually unchanged (same hex values as before, now routed through CSS variables).</done>
</task>

<task type="auto">
  <name>Task 2: Add theme toggle component and UI controls with flash prevention</name>
  <files>
    theme/templates/base.html
    core/templates/core/auth/login.html
    core/templates/core/setup/unlock.html
    core/templates/core/components/nav.html
    core/templates/core/components/nav_project.html
  </files>
  <action>
**1. Update base.html: Add flash-prevention script and Alpine themeToggle component.**

**Flash prevention** -- Replace the existing script that hardcodes `dark`:

```html
<script nonce="{{ csp_nonce }}">
    // Ensure dark mode class is set before render to prevent flash
    document.documentElement.classList.add('dark');
</script>
```

With a script that reads from localStorage (Alpine `$persist` stores under `_x_` prefix):

```html
<script nonce="{{ csp_nonce }}">
    // Apply saved theme before render to prevent flash
    // Alpine $persist stores as _x_theme in localStorage
    try {
        var saved = localStorage.getItem('_x_theme');
        if (saved) saved = JSON.parse(saved);
        if (saved === 'dark') {
            document.documentElement.classList.add('dark');
        } else if (saved === 'light') {
            document.documentElement.classList.remove('dark');
        } else {
            // Default to dark if no preference saved
            document.documentElement.classList.add('dark');
        }
    } catch(e) {
        document.documentElement.classList.add('dark');
    }
</script>
```

**Also update the `<html>` tag** -- Remove the hardcoded `class="dark"` from `<html lang="en" class="dark">` and change it to just `<html lang="en">`. The flash-prevention script runs synchronously before paint and will add `dark` when needed.

**Register the themeToggle Alpine component** -- Add inside the existing `alpine:init` event listener block (after the `wsStatus` component):

```js
Alpine.data('themeToggle', function() {
    return {
        theme: this.$persist('dark').as('theme'),
        toggle: function() {
            this.theme = this.theme === 'dark' ? 'light' : 'dark';
            this.applyTheme();
        },
        applyTheme: function() {
            if (this.theme === 'dark') {
                document.documentElement.classList.add('dark');
            } else {
                document.documentElement.classList.remove('dark');
            }
        },
        init: function() {
            this.applyTheme();
        }
    };
});
```

**CRITICAL Alpine CSP note**: `$persist('dark').as('theme')` is a single expression and works with the CSP parser. The `function()` syntax (not arrow functions) is required per project conventions.

**2. Add theme toggle button to nav.html (main sidebar).**

In the User Section at the bottom of `nav.html`, add a theme toggle button between the user info and the logout button. The current structure is:

```html
<div class="flex items-center justify-between">
    <div class="flex items-center">...</div>
    <form method="post" action="{% url 'auth:logout' %}">...</form>
</div>
```

Replace with a structure that includes the theme toggle:

```html
<div class="flex items-center justify-between">
    <div class="flex items-center">
        <div class="w-8 h-8 rounded-full bg-dark-accent flex items-center justify-center text-white font-medium">
            {{ user.username|slice:":1"|upper }}
        </div>
        <div class="ml-3">
            <p class="text-sm font-medium text-dark-text">{{ user.username }}</p>
            <p class="text-xs text-dark-muted">{{ user.email }}</p>
        </div>
    </div>
    <div class="flex items-center gap-1">
        <!-- Theme toggle -->
        <div x-data="themeToggle">
            <button @click="toggle()" class="text-dark-muted hover:text-dark-text transition-colors p-1" title="Toggle theme">
                <!-- Sun icon (shown in dark mode) -->
                <svg x-show="theme === 'dark'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
                <!-- Moon icon (shown in light mode) -->
                <svg x-show="theme === 'light'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                </svg>
            </button>
        </div>
        <!-- Logout -->
        <form method="post" action="{% url 'auth:logout' %}">
            {% csrf_token %}
            <button type="submit" class="text-dark-muted hover:text-dark-text transition-colors p-1" title="Logout">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
            </button>
        </form>
    </div>
</div>
```

**3. Add the identical theme toggle button to nav_project.html (project sidebar).**

Apply the exact same change to the User Section in `nav_project.html`. The structure is identical -- add the theme toggle button between user info and logout.

**4. Update login.html to use the flash-prevention pattern.**

Replace `<html lang="en" class="dark">` with `<html lang="en">`.

Replace the existing script:
```html
<script nonce="{{ csp_nonce }}">document.documentElement.classList.add('dark');</script>
```
With:
```html
<script nonce="{{ csp_nonce }}">
    try {
        var saved = localStorage.getItem('_x_theme');
        if (saved) saved = JSON.parse(saved);
        if (saved === 'light') {
            /* light: no dark class */
        } else {
            document.documentElement.classList.add('dark');
        }
    } catch(e) {
        document.documentElement.classList.add('dark');
    }
</script>
```

**5. Update unlock.html with the same flash-prevention pattern.**

Read `core/templates/core/setup/unlock.html` first. Apply the same changes as login.html:
- Remove hardcoded `class="dark"` from `<html>` tag
- Replace any hardcoded dark class script with the localStorage-aware version

**Important notes:**
- The `$persist` plugin stores values as `_x_{name}` in localStorage by default. The `.as('theme')` call makes it `_x_theme`.
- Default theme is dark (matching current behavior) -- users who never toggle see no change.
- `x-show` on the SVG icons works with Alpine CSP build since it is a single expression.
- The logout button gets `p-1` added for consistent spacing with the new toggle button.
  </action>
  <verify>
    <automated>cd /Users/fandruhin/work/yourdevops/pathfinder && make build 2>&1 | tail -5 && uv run python manage.py check 2>&1</automated>
    <manual>
1. Visit http://localhost:8000/login/ -- should appear in dark theme (default)
2. Log in, find sun icon next to logout in sidebar bottom
3. Click sun icon -- entire UI should switch to light theme instantly
4. Icon changes to moon
5. Refresh page -- light theme persists (no flash of dark)
6. Click moon -- switches back to dark
7. Navigate to a project -- project sidebar also has the toggle
8. Log out -- login page reflects chosen theme
    </manual>
  </verify>
  <done>Theme toggle button visible in both sidebar variants (main nav and project nav). Clicking toggles between light/dark instantly. Theme persists in localStorage across page reloads. No flash of wrong theme on load. Login and unlock pages respect saved preference. Default theme is dark (no change for existing users).</done>
</task>

</tasks>

<verification>
1. `make build` completes without errors (Tailwind compiles with CSS variable color references)
2. `uv run python manage.py check` passes
3. Dark theme appearance is visually identical to before (same color values routed through CSS variables)
4. Light theme shows white/gray surfaces, dark text, properly contrasted UI elements
5. Theme persists across page reload via localStorage `_x_theme` key
6. No flash of incorrect theme during page load
7. Toggle button shows sun icon in dark mode, moon icon in light mode
</verification>

<success_criteria>
- CSS custom properties define both light and dark color palettes
- Tailwind semantic tokens reference CSS variables with alpha support
- Alpine themeToggle component with $persist manages theme state
- Toggle button in both sidebar variants (nav.html, nav_project.html)
- Flash-prevention script in base.html, login.html, unlock.html
- Default theme is dark (backwards compatible)
- `make build` and `uv run python manage.py check` pass
</success_criteria>

<output>
After completion, create `.planning/quick/44-implement-light-theme-for-the-app-with-u/44-SUMMARY.md`
</output>
