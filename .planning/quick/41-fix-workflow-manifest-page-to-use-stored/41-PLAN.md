---
phase: quick-41
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/views/ci_workflows.py
  - core/templates/core/ci_workflows/workflow_detail.html
autonomous: true
requirements: [quick-41]
must_haves:
  truths:
    - "Manifest tab shows draft version content when a draft exists"
    - "Manifest tab shows latest authorized version content when no draft but authorized versions exist"
    - "Manifest tab shows freshly generated manifest only when no versions exist at all"
    - "Heading says Manifest not Generated Manifest"
  artifacts:
    - path: "core/views/ci_workflows.py"
      provides: "Version-prioritized manifest resolution in WorkflowDetailView"
      contains: "draft_version.manifest_content"
    - path: "core/templates/core/ci_workflows/workflow_detail.html"
      provides: "Correct manifest heading"
      contains: "Manifest"
  key_links:
    - from: "core/views/ci_workflows.py"
      to: "CIWorkflowVersion.manifest_content"
      via: "draft > authorized > generate fallback"
      pattern: "draft_version\\.manifest_content|latest_version\\.manifest_content"
---

<objective>
Fix WorkflowDetailView.get() to use stored version content for the manifest tab instead of always generating on-the-fly.

Purpose: The manifest tab currently always calls ci_plugin.generate_manifest(), ignoring stored draft/authorized version content. This means the manifest tab shows a freshly generated manifest that may differ from what was actually published. The correct pattern already exists in WorkflowManifestView (lines 983-1006) and needs to be replicated in WorkflowDetailView.

Output: Manifest tab shows stored version content (draft priority, then authorized, then fresh generate as fallback).
</objective>

<execution_context>
@/Users/fandruhin/.claude/get-shit-done/workflows/execute-plan.md
@/Users/fandruhin/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@core/views/ci_workflows.py (lines 910-1006 — WorkflowDetailView and WorkflowManifestView)
@core/templates/core/ci_workflows/workflow_detail.html (line 237 — heading)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Use stored version content for manifest in WorkflowDetailView</name>
  <files>core/views/ci_workflows.py, core/templates/core/ci_workflows/workflow_detail.html</files>
  <action>
In `core/views/ci_workflows.py`, `WorkflowDetailView.get()` method (around lines 924-932):

1. Move the `draft_version` and `latest_version` queries (currently lines 929-932) BEFORE the manifest generation (currently line 926).

2. Replace line 926 (`manifest_yaml = ci_plugin.generate_manifest(workflow) if ci_plugin else ...`) with version-prioritized logic matching WorkflowManifestView (lines 991-998):
   ```python
   if draft_version and draft_version.manifest_content:
       manifest_yaml = draft_version.manifest_content
   elif latest_version and latest_version.manifest_content:
       manifest_yaml = latest_version.manifest_content
   else:
       manifest_yaml = ci_plugin.generate_manifest(workflow) if ci_plugin else "# No CI plugin available"
   ```
   Note: Check `manifest_content` is non-empty (truthy) to handle edge cases where a version record exists but content is blank.

3. In `core/templates/core/ci_workflows/workflow_detail.html`, line 237: Change `Generated Manifest` to `Manifest` in the h2 heading text.
  </action>
  <verify>
    Run `uv run python manage.py check` to confirm no Django errors.
    Grep the view to confirm `draft_version.manifest_content` appears before the generate_manifest fallback.
    Grep the template to confirm heading no longer says "Generated".
  </verify>
  <done>
    WorkflowDetailView serves stored version content (draft > authorized > fresh generate) for the manifest tab, matching WorkflowManifestView behavior. Template heading reads "Manifest" instead of "Generated Manifest".
  </done>
</task>

</tasks>

<verification>
- `uv run python manage.py check` passes
- In ci_workflows.py, WorkflowDetailView.get() resolves manifest_yaml from draft_version.manifest_content first, then latest_version.manifest_content, then ci_plugin.generate_manifest() as fallback
- Template heading on manifest tab says "Manifest" not "Generated Manifest"
</verification>

<success_criteria>
Manifest tab on workflow detail page displays stored version content when versions exist, falling back to on-the-fly generation only when no versions are available.
</success_criteria>

<output>
After completion, create `.planning/quick/41-fix-workflow-manifest-page-to-use-stored/41-SUMMARY.md`
</output>
