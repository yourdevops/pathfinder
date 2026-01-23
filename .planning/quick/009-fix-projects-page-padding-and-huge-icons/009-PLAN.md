---
phase: quick-009
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/templates/core/projects/list.html
autonomous: true

must_haves:
  truths:
    - "Projects list page has consistent padding with other pages"
    - "Empty state icons are consistently sized across all pages"
  artifacts:
    - path: "core/templates/core/projects/list.html"
      provides: "Projects list with fixed padding and icon sizing"
      contains: "p-8"
---

<objective>
Fix UI inconsistencies on the projects pages:
1. Projects list page (/projects/) has p-6 padding but should have p-8 like other pages (Users page uses p-8)
2. Empty state icon in projects list uses w-16 h-16 but should be w-12 h-12 for consistency with all other empty states

Purpose: Ensure visual consistency across the application
Output: Fixed templates with consistent padding and icon sizes
</objective>

<context>
@.planning/STATE.md
Reference: core/templates/core/users/list.html (uses p-8 for content wrapper)
Reference: core/templates/core/projects/_services_tab.html (uses w-12 h-12 for empty state icon)
Reference: core/templates/core/settings/general.html (uses w-12 h-12 for placeholder icon)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix padding and icon size in projects list</name>
  <files>core/templates/core/projects/list.html</files>
  <action>
    1. Change the outer div padding from `p-6` to `p-8` on line 6 to match other pages like Users list
    2. Change the empty state icon from `w-16 h-16` to `w-12 h-12` on line 72 to match other empty states

    Current (line 6): `<div class="p-6">`
    Change to: `<div class="p-8">`

    Current (line 72): `<svg class="w-16 h-16 mx-auto text-dark-muted mb-4"`
    Change to: `<svg class="w-12 h-12 mx-auto text-dark-muted mb-4"`
  </action>
  <verify>
    1. `grep -n "p-8" core/templates/core/projects/list.html` shows the outer div has p-8
    2. `grep -n "w-16\|w-12" core/templates/core/projects/list.html` shows only w-12 for icons
    3. Visual check: Projects list has same padding as Users page
  </verify>
  <done>
    - Projects list page outer div uses p-8 padding (matching Users page)
    - Empty state icon uses w-12 h-12 (matching all other empty states in the app)
  </done>
</task>

</tasks>

<verification>
1. Run grep to verify p-8 is used: `grep "p-8" core/templates/core/projects/list.html`
2. Run grep to verify no w-16 icons remain: `grep -c "w-16" core/templates/core/projects/list.html` returns 0
3. Visual verification: Navigate to /projects/ and compare padding with /settings/user-management/
</verification>

<success_criteria>
- Projects list page has p-8 padding (2rem) on outer content wrapper
- No w-16 h-16 icons in projects list template
- Empty state icon is w-12 h-12 (3rem) for consistency
</success_criteria>

<output>
After completion, create `.planning/quick/009-fix-projects-page-padding-and-huge-icons/009-SUMMARY.md`
</output>
