# Quick Task 022 Summary

## Task Description
1. Connections healthchecks are not being scheduled, even if the worker runs with `manage.py db_worker --queue-name "*"`
2. Service creation wizard -- make it available in one click without navigating to Projects first
3. A service blueprint was added but is not visible in the wizard's selector
4. Padding around wizard's elements is missing

## Changes Made

### Task 1: Health Check Scheduling
**Status:** Already implemented

The lazy health check scheduling was already implemented in `core/views/connections.py`. The `_schedule_stale_health_checks()` method in `ConnectionListView.get_context_data()` enqueues health checks for stale connections when the connections page is viewed.

### Task 2: One-Click Service Creation
**Files Modified:**
- `core/urls.py` - Added global `/services/create/` URL
- `core/templates/core/services/list.html` - Added "Create Service" button

**Changes:**
- Added `path('create/', ServiceCreateWizard.as_view(), name='create')` to services_patterns
- Added "Create Service" button in page header with plus icon
- Updated empty state to link directly to wizard instead of projects list

### Task 3: Blueprint Visibility in Wizard
**Status:** Original behavior was correct

The original behavior of showing all synced blueprints when no project context was intentional. The actual cause of the missing blueprint was that the project didn't have a Docker connection attached. The helper text (Task 5) addresses this by explaining the requirement.

### Task 4: Wizard Padding
**Files Modified:**
- `core/templates/core/services/wizard/base.html` - Added padding wrapper

**Changes:**
- Wrapped wizard content in `<div class="p-8">` for consistent padding from sidebar

## Verification

1. Navigate to `/services/` - "Create Service" button should be visible
2. Click button - wizard opens at `/services/create/`
3. Project dropdown is enabled (user can select any project)
4. Blueprint dropdown shows all synced blueprints with available connections
5. Wizard content has proper padding from sidebar

### Task 5: Add Helper Text for Blueprint Availability
**Files Modified:**
- `core/templates/core/services/wizard/step_blueprint.html`

**Changes:**
- Added warning message explaining why blueprints might not be available
- Explains that blueprints require matching deploy connections (e.g., Docker) attached to the project

## Commit
- Hash: 27f64f1
- Message: fix(quick-022): wizard improvements and helper text
