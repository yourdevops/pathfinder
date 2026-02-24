---
phase: 07-implement-unified-environment-variables-management
verified: 2026-02-24T12:30:00Z
status: human_needed
score: 12/12 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 8/12
  gaps_closed:
    - "Variables sorted in System > Project > Service > Environment order"
    - "Source information shown on tooltip only, not as visible badges"
    - "Wizard save button works for added variables"
    - "All env var edits are client-side with page-level bulk Save button (no per-row HTMX immediate save)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Navigate to project settings env vars. Verify variables appear in order: PTF_PROJECT (system) first, then project-level vars alphabetically below it."
    expected: "System PTF_* variables appear above project-level variables. No colored source badge visible on any row. Hovering over a variable key shows 'From: project' tooltip."
    why_human: "Sort order and badge absence require visual browser confirmation."
  - test: "On any env var context (project/environment/service settings), click 'Add variable', enter KEY and value, click the green checkmark. Then click 'Edit' on the same row, change the value, click the green checkmark. Then delete another row. Verify no server request fires after each action — only after clicking 'Save Changes'."
    expected: "Each action (add, edit, delete, lock toggle) updates the UI immediately with no network activity. An 'Unsaved changes' bar appears. Clicking 'Save Changes' sends one POST to the bulk save endpoint. After save, the bar disappears and a green 'Changes saved successfully' message appears briefly."
    why_human: "Client-side-only state accumulation and bulk save flow requires interactive browser verification."
  - test: "Start the service creation wizard, reach the configuration step. Click 'Add variable', enter KEY=MY_VAR and a value."
    expected: "The new row appears with a brief green ring highlight (ring-1 ring-green-500/50) for approximately 1.5 seconds, then returns to normal styling, confirming the variable was captured."
    why_human: "Visual feedback timing effect requires browser verification."
  - test: "Navigate to environment detail env vars. Edit or add a variable. Click 'Save Changes'. Navigate away and return — verify the saved variable persists."
    expected: "Bulk save endpoint persists changes to the environment's env_vars JSONField. Variable visible after page reload."
    why_human: "End-to-end persistence flow requires browser interaction."
---

# Phase 7: Implement Unified Environment Variables Management — Re-Verification Report

**Phase Goal:** Unified env var management with cascade resolution, inline editing component, system-injected PTF_* variables, and deployment gate readiness check across all contexts (project, service, environment, wizard)
**Verified:** 2026-02-24T12:30:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (Plans 07-06 and 07-07)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | resolve_env_vars returns system PTF_* vars for any context | VERIFIED | core/utils.py lines 96-123: PTF_PROJECT always injected, PTF_SERVICE if service, PTF_ENVIRONMENT if environment; all source="system", locked_by="system", lock=True |
| 2 | resolve_env_vars merges project, service, and environment vars in cascade order | VERIFIED | core/utils.py lines 126-183: 4-level merge with skip-if-locked logic at each level |
| 3 | Locked variables cannot be overridden by downstream levels | VERIFIED | Lines 148-149 (service), 171-172 (environment): `if key in merged and merged[key]["lock"]: continue` |
| 4 | Description is inherited from upstream unless downstream provides its own | VERIFIED | Lines 155-156, 174: `desc = var.get("description", "") or upstream_desc` |
| 5 | check_deployment_gate detects empty values and reports which level to fix | VERIFIED | core/utils.py lines 191-198; 13 tests pass |
| 6 | SERVICE_NAME references replaced with PTF_SERVICE throughout codebase | VERIFIED | `grep -r "SERVICE_NAME" core/` returns no results |
| 7 | Variables sorted in System > Project > Service > Environment order | VERIFIED | core/utils.py line 187-188: `source_priority = {"system": 0, "project": 1, "service": 2, "environment": 3}` tuple sort. Test `test_system_vars_always_first` confirms PTF_PROJECT precedes A_VAR/B_VAR regardless of alphabetical key order. |
| 8 | Source information shown on tooltip only, not as visible badges | VERIFIED | _env_var_row.html: 43 lines, no source badge span — only tooltip on line 29: `From: {{ var.source }}`. step_configuration.html: no bg-purple-500/20 badge. Container template: no source badge for Alpine-rendered current-level rows. |
| 9 | Adding a variable in the wizard gives visual feedback confirming capture | VERIFIED | step_configuration.html lines 25-26: `lastAddedIdx = vars.length - 1; setTimeout(() => lastAddedIdx = -1, 1500)`. Line 104: `:class="idx === lastAddedIdx ? 'ring-1 ring-green-500/50' : ''"` |
| 10 | All env var edits are client-side with page-level bulk Save button | VERIFIED | _env_var_container.html: pure Alpine x-for with startEdit/saveEdit/removeVar/toggleLock methods. No hx-post/hx-delete/hx-get anywhere in env_vars templates. "Unsaved changes" / "Save Changes" bar (lines 246-257) appears when `dirty=true`. |
| 11 | Unified component used across all 4 contexts (project, service, environment, wizard) | VERIFIED | _settings_env_vars.html line 8, environment_detail.html line 129, _settings_tab.html line 14: all include _env_var_container.html. Wizard uses envVarWizard Alpine component. |
| 12 | Old modal-based env var code removed | VERIFIED | env_var_modal.html deleted. Old per-row views (EnvVarSaveView, EnvVarDeleteView, EnvVarToggleLockView, EnvVarEditRowView, EnvVarAddRowView, EnvVarDisplayRowView) all absent from core/views/env_vars.py. Old 18 URL patterns absent from core/urls.py. |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `core/utils.py` | resolve_env_vars() with source-priority sort and check_deployment_gate() | VERIFIED | Source-priority tuple sort at line 187-188. Both functions present and substantive. 13 tests pass. |
| `core/tests/test_env_vars.py` | Test suite including sort order verification | VERIFIED | `test_results_sorted_by_source_priority_then_key` (line 185) and `test_system_vars_always_first` (line 197) added. 13 total tests pass. |
| `core/templates/core/env_vars/_env_var_container.html` | Alpine envVarEditor with client-side state, dirty bar | VERIFIED | Full Alpine x-for implementation; edit/add/delete/lock all client-side; "Save Changes" bar with `x-show="dirty"`; success feedback with `x-show="saveSuccess"`. |
| `core/templates/core/env_vars/_env_var_row.html` | Read-only upstream display, no source badge, no HTMX | VERIFIED | 43-line template; tooltip only (line 29); no hx-* attributes; no source badge. |
| `core/templates/core/env_vars/_env_var_row_edit.html` | Deleted (replaced by inline Alpine edit) | VERIFIED | File does not exist. |
| `core/templates/core/env_vars/_env_var_add_row.html` | Deleted (replaced by inline Alpine add) | VERIFIED | File does not exist. |
| `core/views/env_vars.py` | Single EnvVarBulkSaveView replacing 6 old per-row views | VERIFIED | 108-line file; only EnvVarBulkSaveView class plus 3 utility functions. Validates key format, PTF_ prefix, duplicates, upstream lock conflicts. Replaces env_vars entirely on save. |
| `theme/templates/base.html` | envVarEditor Alpine.data() component registered | VERIFIED | Line 164: `Alpine.data('envVarEditor', function() { ... })`. All 9 methods present: initFromData, startEdit, cancelEdit, saveEdit, startAdd, cancelAdd, confirmAdd, removeVar, toggleLock, updateNewKey, updateEditKey, bulkSave. |
| `core/templates/core/projects/_settings_env_vars.html` | Project settings wired to Alpine component | VERIFIED | Line 8: includes _env_var_container.html with current_level_vars_json and env_var_bulk_save_url from context. |
| `core/templates/core/projects/environment_detail.html` | Environment detail wired to Alpine component | VERIFIED | Line 129: includes _env_var_container.html with current_level="environment" and bulk save URL. |
| `core/templates/core/services/_settings_tab.html` | Service settings wired to Alpine component | VERIFIED | Line 14: includes _env_var_container.html with current_level="service" and bulk save URL. |
| `core/templates/core/services/wizard/step_configuration.html` | Wizard with visual feedback on variable add | VERIFIED | lastAddedIdx tracked (line 11); setTimeout 1500ms auto-clear (line 26); ring-green-500/50 class applied (line 104). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `core/utils.py` | `core/models.py` | resolve_env_vars reads env_vars JSONField | VERIFIED | Lines 126, 146, 168: project.env_vars, service.env_vars, environment.env_vars accessed |
| `core/views/env_vars.py` | `core/utils.py` | EnvVarBulkSaveView calls resolve_env_vars for lock conflict check | VERIFIED | Line 13: `from core.utils import resolve_env_vars`; line 96: `resolved = resolve_env_vars(self.project, service, environment)` |
| `core/urls.py` | `core/views/env_vars.py` | 3 bulk save URL patterns | VERIFIED | Lines 284-300: project/environment/service bulk save routes resolve correctly (confirmed via reverse()) |
| `core/views/projects.py` | `core/utils.py` | resolve_env_vars called; context passes current_level_vars_json and env_var_bulk_save_url | VERIFIED | Lines 163-167: ProjectDetailView context; lines 263-268: EnvironmentDetailView context |
| `core/views/services.py` | `core/utils.py` | resolve_env_vars called; context passes current_level_vars_json and env_var_bulk_save_url | VERIFIED | Lines 651-656: ServiceDetailView settings tab context |
| `theme/templates/base.html` | `core/templates/core/env_vars/_env_var_container.html` | envVarEditor Alpine.data() consumed via x-data="envVarEditor" | VERIFIED | base.html line 164 registers component; container line 5 uses `x-data="envVarEditor"` |
| `_env_var_container.html` | `EnvVarBulkSaveView` | Alpine bulkSave() POSTs JSON to saveUrl (env_var_bulk_save_url) | VERIFIED | base.html line 262: `fetch(self.saveUrl, { method: 'POST', ... body: JSON.stringify(self.vars) })` |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DPLY-01 | 07-01, 07-03, 07-04, 07-05 | Contributor can deploy service to non-production environment | NOT SATISFIED | No deployment UI or deploy action exists. Phase 7 delivers env var infrastructure only. DPLY-01 requires a deploy endpoint + UI outside this phase's scope. |
| DPLY-02 | 07-01, 07-03, 07-04, 07-05 | Project owner can deploy service to production environment | NOT SATISFIED | Same as DPLY-01 — no deployment functionality implemented. |
| DPLY-03 | 07-02, 07-04, 07-05 | Deploy modal shows environment selector and build selector | NOT SATISFIED | No deploy modal exists in the codebase. |
| DPLY-04 | 07-01, 07-02, 07-04, 07-05, 07-06, 07-07 | Deploy modal shows merged environment variables | INFRASTRUCTURE READY | The cascade resolution (resolve_env_vars), unified display component (envVarEditor), and bulk save endpoint (EnvVarBulkSaveView) provide the complete infrastructure a future deploy modal would consume. The deploy modal consumer does not yet exist. |

**Requirements Note:** DPLY-01 through DPLY-04 all describe deployment flow features. Phase 7's plan frontmatter claimed these requirement IDs, but the phase goal is env var management infrastructure — not the deploy modal itself. DPLY-04's infrastructure is now complete. DPLY-01, DPLY-02, and DPLY-03 remain entirely unaddressed and must be addressed in a future phase that builds the actual deployment UI.

### Anti-Patterns Found

No blockers found. Previous blockers all resolved:

| File | Pattern | Previous Status | Current Status |
|------|---------|-----------------|----------------|
| `core/utils.py` | Alphabetical-only sort | Blocker | FIXED — source-priority tuple sort at line 187-188 |
| `core/templates/core/env_vars/_env_var_row.html` | Visible source badge | Blocker | FIXED — file rewritten to read-only upstream display only, no badge |
| `core/templates/core/env_vars/_env_var_row.html` | HTMX per-row immediate save | Blocker | FIXED — file no longer has any hx-* attributes |
| `core/templates/core/env_vars/_env_var_row_edit.html` | hx-post per-row form save | Blocker | FIXED — file deleted |

### Human Verification Required

#### 1. Sort Order and Source Badge Absence

**Test:** Navigate to project settings env vars on a project that has both system PTF_* vars and project-level vars (e.g., add DATABASE_URL at project level).
**Expected:** PTF_PROJECT appears at the top of the list. DATABASE_URL appears below it. No colored source badge appears on any row. Hovering over a variable key shows a tooltip with "From: project" text.
**Why human:** Sort order and badge absence are visual properties requiring browser confirmation.

#### 2. Client-Side Bulk Save Flow

**Test:** Navigate to project settings, env vars section. Click "Add variable", enter KEY=TEST_VAR and value=hello, click the green checkmark. Then click "Edit" on an existing variable, change its value, click checkmark. Then click the trash icon on another variable. Observe network traffic (browser DevTools).
**Expected:** No POST requests fire after each individual action. The "Unsaved changes" bar is visible. Clicking "Save Changes" sends exactly one POST to `/projects/{name}/env-vars/bulk-save/`. After save: bar disappears, green "Changes saved successfully" message appears for ~2 seconds.
**Why human:** Client-side-only state accumulation and the bulk save timing require interactive browser + DevTools verification.

#### 3. Wizard Add Variable Visual Feedback

**Test:** Start the service creation wizard, reach the Configuration step. Click "Add variable".
**Expected:** A new row appears with a green ring highlight (subtle green border glow) visible for approximately 1.5 seconds, then the ring fades away. The key/value inputs are editable. Entering key and value updates them correctly.
**Why human:** Visual highlight timing effect requires browser verification.

#### 4. End-to-End Persistence

**Test:** Navigate to environment detail for any environment. Add a new variable (KEY=MY_ENV_VAR, value=test123). Click "Save Changes". Navigate away (e.g., to another tab). Return to the same environment's detail page.
**Expected:** MY_ENV_VAR=test123 appears in the list after page reload, confirming the bulk save endpoint correctly persisted to the database.
**Why human:** End-to-end persistence through page navigation requires browser interaction.

### Re-verification Summary

All 4 gaps from the initial verification have been closed:

**Gap 1 — Sort order (CLOSED):** `resolve_env_vars()` now sorts by `(source_priority, key)` tuple where `system=0, project=1, service=2, environment=3`. Two new tests verify this: `test_results_sorted_by_source_priority_then_key` and `test_system_vars_always_first`.

**Gap 2 — Visible source badges (CLOSED):** `_env_var_row.html` rewritten to a clean 43-line read-only template with no source badge. Only tooltip contains source information (line 29: `From: {{ var.source }}`). `step_configuration.html` System badge also removed.

**Gap 3 — Wizard save feedback (CLOSED):** `envVarWizard` in `step_configuration.html` now tracks `lastAddedIdx` and applies a 1.5-second `ring-1 ring-green-500/50` highlight class to confirm variable capture.

**Gap 4 — Bulk save architecture (CLOSED):** Complete architectural replacement of HTMX per-row save with Alpine.js client-side state management:
- `envVarEditor` Alpine component registered in `base.html` with 12 methods for all editing operations
- All editing operations (add, edit, delete, lock toggle) are client-side — no server round-trips
- "Unsaved changes" bar appears when dirty, "Save Changes" button triggers a single bulk POST
- `EnvVarBulkSaveView` replaces 6 old per-row views; accepts JSON array, validates, persists
- 3 bulk save URL patterns replace 18 old per-row URL patterns
- Old `_env_var_row_edit.html` and `_env_var_add_row.html` deleted
- View contexts updated in `projects.py` and `services.py` to pass `current_level_vars_json`, `env_var_bulk_save_url`, `upstream_var_count`

All 13 tests pass. Django system check is clean. No anti-patterns remain.

---

_Verified: 2026-02-24T12:30:00Z_
_Verifier: Claude (gsd-verifier)_
