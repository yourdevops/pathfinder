---
phase: 08-implement-service-templates
verified: 2026-02-24T17:01:45Z
status: gaps_found
score: 18/19 must-haves verified
gaps:
  - truth: "Manual sync button on detail page triggers sync_template task"
    status: failed
    reason: "The Sync Now button in detail.html is a disabled placeholder with tooltip 'Sync will be available after sync task is implemented'. The backend (TemplateSyncView at templates:sync URL) exists and is fully implemented, but the button was never wired to POST to it."
    artifacts:
      - path: "core/templates/core/templates/detail.html"
        issue: "Lines 29-34: button is disabled with cursor-not-allowed class and placeholder comment. Needs to be a form POST to templates:sync URL."
    missing:
      - "Replace disabled button with a form POST to {% url 'templates:sync' template_name=template.name %} (same pattern used elsewhere for manual sync triggers)"
      - "Remove the stale comment 'will be wired to sync task in Plan 03'"
---

# Phase 8: Implement Service Templates Verification Report

**Phase Goal:** Operators can register git repos as templates via pathfinder.yaml manifests, sync versions via git tags, and developers select templates when creating services to get pre-populated scaffolding and environment variables
**Verified:** 2026-02-24T17:01:45Z
**Status:** gaps_found
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Template model exists with name, description, git_url, connection FK, runtimes, required_vars, sync_status, last_synced_at fields | VERIFIED | core/models.py line 1066: class Template with all specified fields |
| 2 | TemplateVersion model exists with template FK, tag_name, commit_sha, available boolean, synced_at, sort_key | VERIFIED | core/models.py line 1111: class TemplateVersion with all fields |
| 3 | ProjectTemplateConfig model exists with project OneToOne, default_template FK, allowed_templates M2M | VERIFIED | core/models.py line 1131: class ProjectTemplateConfig with all fields |
| 4 | Service model has template FK (SET_NULL) and template_version text field | VERIFIED | core/models.py lines 506-513: template ForeignKey and template_version CharField |
| 5 | read_pathfinder_manifest function validates kind: ServiceTemplate and DNS-compatible name | VERIFIED | core/git_utils.py line 186: full implementation with YAML parse, kind check, DNS regex |
| 6 | Operator can view a table of registered templates | VERIFIED | core/views/templates.py TemplateListView + list.html (113 lines) with table columns |
| 7 | Operator can register a template via SCM connection dropdown + git URL form | VERIFIED | core/views/templates.py TemplateRegisterView with clone, manifest read, version creation |
| 8 | Operator can view template detail with metadata sections and version list | VERIFIED | core/templates/core/templates/detail.html (191 lines) with metadata, versions, sync sections |
| 9 | Operator can deregister a template (deletion guard blocks if services reference it) | VERIFIED | core/views/templates.py TemplateDeregisterView checks template.services.exists() |
| 10 | Templates appear as top-level expandable section in sidebar navigation | VERIFIED | core/templates/core/components/nav.html: templatesOpen with $persist, link to templates:list |
| 11 | sync_template task re-clones repo, re-reads manifest metadata, refreshes tag list, flags unavailable tags | VERIFIED | core/tasks.py line 117: full implementation with clone, manifest read, tag refresh, unavailable flag |
| 12 | Manual sync button on detail page triggers sync_template task | FAILED | detail.html lines 29-34: button is disabled placeholder, never wired to TemplateSyncView |
| 13 | scaffold_repository task is rewritten for template-aware scaffolding | VERIFIED | core/tasks.py line 257: clones template at tag SHA, passes temp dir to scaffold_new_repository |
| 14 | Wizard repository step shows template dropdown when repo mode is 'new' | VERIFIED | _fields_repository.html: x-show="isNew" with templateSelector Alpine component |
| 15 | Version dropdown appears below template dropdown when a template is selected | VERIFIED | _fields_repository.html: version dropdown with x-show="tplVal !== ''" |
| 16 | Selected template's required_vars are pre-populated as service env vars | VERIFIED | core/views/services.py lines 256-280: template_seeded_vars merged into initial_env_vars_json |
| 17 | Review step shows selected template name and version | VERIFIED | _fields_review.html lines 46-51: template_name and template_version_tag display |
| 18 | Service record stores template FK and template_version text on creation | VERIFIED | core/views/services.py lines 498-501: template and template_version set in Service.objects.create |
| 19 | Template filtering respects ProjectTemplateConfig allowed templates | VERIFIED | core/models.py get_available_templates_for_project filters by allowed_templates if set |

**Score:** 18/19 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `core/models.py` | Template, TemplateVersion, ProjectTemplateConfig models; Service template FK | VERIFIED | All models exist with correct fields, auditlog registered |
| `core/git_utils.py` | read_pathfinder_manifest function | VERIFIED | Line 186: validates kind, name, DNS regex |
| `core/forms/templates.py` | TemplateRegisterForm | VERIFIED | 48 lines, connection (SCM-filtered) + git_url fields |
| `core/views/templates.py` | TemplateListView, TemplateDetailView, TemplateRegisterView, TemplateDeregisterView, TemplateSyncView, TemplateSyncStatusView | VERIFIED | All 6 views implemented with substantive logic |
| `core/templates/core/templates/list.html` | Template list page with table layout | VERIFIED | 113 lines, table with name/description/runtimes/version_count/sync_status/last_synced |
| `core/templates/core/templates/detail.html` | Template detail page with sections | PARTIAL | 191 lines, metadata/versions/sync sections present, but Sync Now button is disabled stub |
| `core/templates/core/templates/register.html` | Template registration form | VERIFIED | 68 lines, two-field form with error display |
| `core/templates/core/templates/_sync_status.html` | HTMX sync status partial | VERIFIED | 31 lines, HTMX polling for sync status badge |
| `core/templates/core/components/nav.html` | Templates section in sidebar | VERIFIED | Expandable section with $persist and templates:list link |
| `core/tasks.py` | sync_template task and rewritten scaffold_repository | VERIFIED | Both tasks fully implemented |
| `core/forms/services.py` | template_id and template_version_tag fields on RepositoryStepForm | VERIFIED | Hidden fields with clean methods for validation |
| `theme/templates/base.html` | templateSelector Alpine.data component | VERIFIED | Line 347: full component with pickTpl/pickVer methods |
| `core/templates/core/services/wizard/_fields_repository.html` | Template picker section in wizard | VERIFIED | Dropdown + version selector using templateSelector component |
| `core/templates/core/services/wizard/_fields_review.html` | Template name and version display | VERIFIED | Lines 46-51: template_name and template_version_tag |
| `core/migrations/0033_service_templates.py` | Migration for all new models | VERIFIED | Migration exists and is applied |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| core/models.py (Template) | core/models.py (IntegrationConnection) | Template.connection ForeignKey | WIRED | Line 1086: ForeignKey to IntegrationConnection |
| core/models.py (Service) | core/models.py (Template) | Service.template ForeignKey | WIRED | Line 506: ForeignKey to Template |
| core/urls.py | core/views/templates.py | templates_patterns URL routing | WIRED | Lines 236-243: all 6 URL patterns mapped to views |
| pathfinder/urls.py | core/urls.py (templates_patterns) | include with namespace | WIRED | Line 69: include((templates_patterns, "templates")) |
| core/templates/core/components/nav.html | core/urls.py | templates:list URL tag | WIRED | Line 90: href to templates:list |
| core/tasks.py (sync_template) | core/git_utils.py (read_pathfinder_manifest) | import and call | WIRED | Line 136: imported, line 179: called |
| core/tasks.py (scaffold_repository) | core/git_utils.py (apply_template_to_directory) | template file tree copy | WIRED | scaffold_new_repository calls apply_template_to_directory at line 395 of git_utils.py |
| core/views/services.py (ServiceCreateWizard) | core/models.py (Template, TemplateVersion) | template lookup and env var seeding | WIRED | Lines 187, 261: Template queries for context and seeding |
| _fields_repository.html | theme/templates/base.html (templateSelector) | Alpine.data component usage | WIRED | Line 57: x-data="templateSelector(...)" references base.html component |
| core/templates/core/templates/detail.html | core/views/templates.py (TemplateSyncView) | Sync Now button POST | NOT WIRED | Button is disabled; backend exists at templates:sync but button does not call it |
| core/views/templates.py (TemplateSyncView) | core/tasks.py (sync_template) | enqueue task | WIRED | Line 183: sync_template.enqueue(template_id=template.id) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-----------|-------------|--------|----------|
| BPRT-01 | 08-01, 08-02 | Operator can register blueprint from git URL | SATISFIED | TemplateRegisterView clones repo, reads manifest, creates Template + versions |
| BPRT-02 | 08-01, 08-03 | Blueprint syncs metadata from ssp-template.yaml manifest | SATISFIED | read_pathfinder_manifest reads pathfinder.yaml; sync_template re-reads on sync |
| BPRT-03 | 08-02, 08-04 | Blueprint shows available git tags as versions | SATISFIED | TemplateVersion records created from semver tags; detail page shows version list |
| BPRT-04 | 08-02, 08-04 | Blueprint displays name, description, tags, ci.plugin, deploy.plugin | SATISFIED | Detail page displays name, description, runtimes, required_vars; list table shows same |
| BPRT-05 | 08-03 | Operator can manually sync blueprint to refresh versions | BLOCKED | Backend (TemplateSyncView) implemented, but Sync Now button is disabled stub in detail.html |
| BPRT-06 | 08-03 | Blueprint availability filtered by project's environment connections | SATISFIED | get_available_templates_for_project filters by ProjectTemplateConfig.allowed_templates (design evolved from connection-based to allowlist-based filtering) |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| core/templates/core/templates/detail.html | 29 | Comment "will be wired to sync task in Plan 03" | Blocker | Sync Now button never wired despite backend existing |
| core/templates/core/templates/detail.html | 30 | `disabled` attribute on Sync Now button | Blocker | Button is non-functional; cursor-not-allowed CSS class |
| core/templates/core/templates/detail.html | 32 | title="Sync will be available after sync task is implemented" | Warning | Stale placeholder text visible to users on hover |

### Human Verification Required

### 1. Template Registration End-to-End

**Test:** Register a template from a git repository containing a valid pathfinder.yaml with kind: ServiceTemplate
**Expected:** Template appears in list with name, description, runtimes, version count from manifest; detail page shows metadata and semver tags
**Why human:** Requires live git repository and SCM connection to test clone flow

### 2. Service Creation with Template

**Test:** Create a new service, select a registered template on the repository step, proceed through wizard
**Expected:** Template dropdown shows available templates; version dropdown appears on selection; env vars pre-populated on configuration step; review shows template info; created service has template FK set
**Why human:** Multi-step wizard flow with Alpine.js interactivity

### 3. Template-Aware Scaffolding

**Test:** Complete service creation with template selected and new repository mode
**Expected:** New repository contains template files (excluding pathfinder.yaml) plus CI manifest if workflow assigned
**Why human:** Requires live SCM connection to verify repository contents

### 4. Template Deregistration Guard

**Test:** Try to deregister a template that has services referencing it
**Expected:** Error message "Cannot delete template -- services reference it"; template not deleted
**Why human:** Requires existing service with template reference

### Gaps Summary

There is one gap blocking full goal achievement:

**The Sync Now button on the template detail page is a disabled placeholder.** Plan 02 created the button as a disabled stub with the comment "will be wired to sync task in Plan 03". Plan 03 implemented the backend (`TemplateSyncView` and the `templates:sync` URL) but did not update the detail.html template to wire the button. The result is that operators cannot manually trigger a template sync from the UI, despite the entire backend being ready.

This directly blocks requirement **BPRT-05** ("Operator can manually sync blueprint to refresh versions").

The fix is straightforward: replace the disabled `<button>` with a `<form method="post" action="{% url 'templates:sync' template_name=template.name %}">` containing a CSRF token and an enabled submit button. The backend already handles the POST, checks for sync-in-progress, enqueues the task, and redirects with a success message.

---

_Verified: 2026-02-24T17:01:45Z_
_Verifier: Claude (gsd-verifier)_
