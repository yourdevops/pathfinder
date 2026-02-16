# CI Workflows -- Gap Analysis and Remediation Plan

**Date**: 2026-02-16
**Status**: Draft
**Scope**: All 9 CI Workflows design documents vs. current implementation

## Purpose

This document catalogs every gap between the CI Workflows design (defined in `docs/ci-workflows/`) and the current implementation (primarily `core/models.py`, `core/tasks.py`, `core/ci_steps.py`, `core/views/ci_workflows.py`, `core/views/webhooks.py`, `core/views/services.py`, and `plugins/github/plugin.py`). Each gap is assigned a severity and mapped to a remediation phase.

**How to use**: Each remediation phase (R1 through R6) maps to a future GSD phase. Phases are ordered so that foundation changes land before features that depend on them. Execute phases sequentially; parallelizable phases are noted.

---

## Gap Inventory

| ID | Name | Design Doc | Severity | Phase |
|----|------|-----------|----------|-------|
| GAP-01 | Step Identity and Slug System | steps-catalog.md | High | R1 |
| GAP-02 | Step Version Identity via Git | steps-catalog.md | High | R1 |
| GAP-03 | Step Tracking and Change Detection | steps-catalog.md | High | R1 |
| GAP-04 | Step Archival Instead of Hard Delete | steps-catalog.md | Critical | R1 |
| GAP-05 | Branch Protection Validation | steps-catalog.md | Medium | R4 |
| GAP-06 | Repository Sync Triggers | steps-catalog.md | Medium | R4 |
| GAP-07 | Sync Operation Logging | logging.md | Medium | R4 |
| GAP-08 | Explicit Engine Field on CIWorkflow | workflow-definition.md | High | R2 |
| GAP-09 | Step Ordering Validation | workflow-definition.md | Medium | R2 |
| GAP-10 | Workflow Archived Status | versioning.md | Low | R2 |
| GAP-11 | Auto-Update on Version Publish | versioning.md | Medium | R5 |
| GAP-12 | Version Cleanup and Retention | versioning.md | Low | R5 |
| GAP-13 | Artifact Discovery via CI Plugin | build-lifecycle.md | Medium | R6 |
| GAP-14 | Build Categorization by manifest_id | build-authorization.md | Medium | R3 |
| GAP-15 | "revoked" Build Verification Status | build-lifecycle.md | High | R3 |
| GAP-16 | Engine-Agnostic Build Model | build-lifecycle.md | Low | R3 |
| GAP-17 | CI Variables in Manifest | steps-catalog.md | Low | R6 |
| GAP-18 | Step Validation API | steps-catalog.md | Low | R6 |
| GAP-19 | manifest_path Cleanup | plugin-interface.md | Low | R6 |

**Severity criteria**:
- **Critical**: Data integrity or security risk (hard deletes losing data, missing verification states)
- **High**: Core workflow feature gap (versioning, change detection, engine identity)
- **Medium**: Operational feature gap (logging, cleanup, sync triggers)
- **Low**: Code quality or naming inconsistency (field rename, dead code)

---

## Detailed Gap Descriptions

### GAP-01: Step Identity and Slug System

**Design Reference**: steps-catalog.md, Section "Step Identity"

**Current Implementation**: The `CIStep` model (`core/models.py:594`) uses `directory_name` (CharField) as its primary identifier, with uniqueness scoped per repository via `unique_together = ["repository", "directory_name"]` (`core/models.py:632`). No `slug` field exists.

**Gap**: Steps should be identified by `(ci_engine, slug)` where the slug is derived from the `x-pathfinder.name` metadata field. Slugs must be unique per CI engine across the entire catalog -- not per repository. Collision detection at import time should emit warnings.

**Impact**: Without global slug uniqueness, different repositories can import conflicting steps for the same engine. No collision detection means silent overwrites when steps from different repos share the same directory name and engine.

**Remediation**:
- Add `slug` CharField to `CIStep` model with `unique_together = ["engine", "slug"]`
- Add slug derivation (from `x-pathfinder.name`, falling back to `directory_name`) in `scan_steps_repository` task (`core/tasks.py:298`)
- Add collision detection: if a slug already exists for the same engine in a different repository, skip with a logged warning
- Migration: backfill existing steps with slug derived from `directory_name`

---

### GAP-02: Step Version Identity via Git

**Design Reference**: steps-catalog.md, Section "Version Identity via Git"

**Current Implementation**: `core/tasks.py:298` sets `commit_sha = repo_obj.head.commit.hexsha` (the repository HEAD SHA) for ALL steps in a single scan pass.

**Gap**: Each step should be versioned by its own file's last-modified commit SHA, computed via `git log -1 --format=%H -- <path>`. This gives each step an independent version that changes only when its definition file changes.

**Impact**: All steps show the same version (repo HEAD) regardless of when their specific file was last changed. Version identity is meaningless -- a step that has not changed in months shows the same SHA as one modified today.

**Remediation**:
- In `scan_steps_repository` (`core/tasks.py:298`), after cloning, run `git log -1 --format=%H -- ci-steps/{dir_name}/{engine_file}` for each discovered step
- Use the per-file SHA as `commit_sha` instead of `repo_obj.head.commit.hexsha`
- Requires full clone (not shallow) or shallow clone with sufficient depth; alternatively use `git.repo.Repo.git.log()` from GitPython

---

### GAP-03: Step Tracking and Change Detection

**Design Reference**: steps-catalog.md, Sections "Step Tracking" and "Change Detection"

**Current Implementation**: No `definition_hash` field exists on `CIStep` (`core/models.py:594`). No change detection logic in `scan_steps_repository` (`core/tasks.py:217`). Steps are silently updated via `update_or_create`.

**Gap**: `CIStep` should have a `definition_hash` computed from normalized tracked attributes (name, path, inputs, outputs, runtimes, phase, produces). On sync, the new hash should be compared to the stored hash. Changes should be classified as interface changes (inputs/outputs changed) vs. metadata changes (description, tags). Workflows using steps with interface changes should be flagged with a warning badge.

**Impact**: No way to detect which steps changed during a sync. Workflows using updated steps get no notification. Breaking interface changes (e.g., renamed inputs) go undetected until builds fail.

**Remediation**:
- Add `definition_hash` CharField to `CIStep` model
- Compute hash from `(name, phase, inputs_schema, runtime_constraints, produces)` during scan
- In `scan_steps_repository`, compare old hash vs. new hash before updating
- Add `has_step_updates` BooleanField or similar on `CIWorkflow` for UI badge display
- Track change type (interface vs. metadata) for logging

---

### GAP-04: Step Archival Instead of Hard Delete

**Design Reference**: steps-catalog.md, Section "Step Removal"

**Current Implementation**: `core/tasks.py:324` hard-deletes steps that are no longer found in the repository: `CIStep.objects.filter(repository=repository).exclude(directory_name__in=scanned_dir_names).delete()`.

**Gap**: Steps removed from the repository should be marked "archived" rather than deleted. Workflows referencing archived steps should display a warning. Published versions remain valid (step pinned at last known SHA). Auto-cleanup should occur when no workflow version references an archived step.

**Impact**: Hard deletion breaks `CIWorkflowStep` FK references. The `on_delete=models.PROTECT` on the FK (`core/models.py:696`) prevents deletion of steps currently in use, but unused steps lose all history. There is no graceful deprecation path.

**Remediation**:
- Add `status` CharField to `CIStep` with choices `("active", "Active"), ("archived", "Archived")`, defaulting to `"active"`
- Replace `.delete()` at `core/tasks.py:324` with a status update to `"archived"`
- Filter out archived steps in the workflow composer step picker (unless already used in current workflow)
- Add UI warning on workflow detail when a step is archived
- Add periodic cleanup task that deletes archived steps with zero `CIWorkflowStep` references

---

### GAP-05: Branch Protection Validation

**Design Reference**: steps-catalog.md, Section "Branch Protection Requirements"

**Current Implementation**: No branch protection validation exists in `StepsRepoRegisterView` (`core/views/ci_workflows.py:53`) or `scan_steps_repository` (`core/tasks.py:217`).

**Gap**: Before accepting a Steps Repository, Pathfinder should validate branch protection rules on the default branch: no direct push allowed, no force push, at least 1 required reviewer, no branch deletion. Re-validate on each sync. Offer auto-configuration if the connected SCM plugin supports it.

**Impact**: Unprotected step repos can be tampered with via direct push or force push, undermining the trust chain for build authorization.

**Remediation**:
- Add `check_branch_protection()` method to `CICapableMixin` (`plugins/base.py:85`)
- Implement in `GitHubPlugin` using PyGithub's `get_branch_protection()` API
- Call on registration in `StepsRepoRegisterView` and on each sync in `scan_steps_repository`
- Store validation result on `StepsRepository` model (e.g., `protection_valid` BooleanField)
- Block registration if protection is absent; allow admin override with warning

---

### GAP-06: Repository Sync Triggers

**Design Reference**: steps-catalog.md, Section "Repository Synchronization"

**Current Implementation**: Only manual poll exists via `StepsRepoScanView` (`core/views/ci_workflows.py:139`). No webhook handler for step repo push events. No scheduled periodic task.

**Gap**: Three sync triggers are needed: (1) Webhook on repository push to the default branch, (2) Manual poll (already exists), (3) Scheduled daily sync task.

**Impact**: The step catalog only updates when an admin manually rescans. New steps and updates are delayed indefinitely until someone remembers to click "Rescan."

**Remediation**:
- Add webhook handler for steps repository push events (new view, similar to `build_webhook` in `core/views/webhooks.py`)
- Add scheduled daily scan task using django-tasks
- Register webhook on steps repo registration in `StepsRepoRegisterView`
- Store `webhook_registered` flag on `StepsRepository`

---

### GAP-07: Sync Operation Logging

**Design Reference**: logging.md, Sections "Operation Log: Steps Repository Sync" and "UI"

**Current Implementation**: No `StepsRepoSyncLog` or `StepSyncEntry` models exist. Scan results go only to the Python logger (`core/tasks.py:332`).

**Gap**: Need `StepsRepoSyncLog` (repository FK, commit_sha, previous_sha, status, timing, protection_valid) and `StepSyncEntry` (sync_log FK, step_slug, action, severity, message). A sync history UI should be displayed on the repo detail page.

**Impact**: No audit trail for step changes. Admins cannot troubleshoot sync issues. No visibility into what changed when.

**Remediation**:
- Create `StepsRepoSyncLog` model with fields: `repository` FK, `commit_sha`, `previous_sha`, `status`, `started_at`, `completed_at`, `protection_valid`, `steps_added`, `steps_updated`, `steps_archived`
- Create `StepSyncEntry` model with fields: `sync_log` FK, `step_slug`, `action` (added/updated/archived/skipped), `severity`, `message`
- Update `scan_steps_repository` to create log entries during scan
- Add sync history section to the repo detail template (`core/templates/core/ci_workflows/repo_detail.html`)

---

### GAP-08: Explicit Engine Field on CIWorkflow

**Design Reference**: workflow-definition.md, Section "CI Workflow Fields"

**Current Implementation**: `CIWorkflow` (`core/models.py:639`) has no `engine` field. The engine is derived at runtime from the first step's engine: `first_step.step.engine if first_step else "github_actions"`. This pattern appears in at least 3 locations:
- `core/tasks.py:412` (verify_build)
- `core/tasks.py:627` (push_ci_manifest)
- Other views and tasks that need the workflow's engine

**Gap**: `CIWorkflow` should have an explicit `engine` CharField, set at creation time and immutable after.

**Impact**: Engine derivation is fragile -- it fails if the workflow has no steps. The default fallback to `"github_actions"` masks errors. Repeated derivation is a DRY violation that requires multiple select_related queries.

**Remediation**:
- Add `engine` CharField to `CIWorkflow` model with `max_length=63, default="github_actions"`
- Set engine in `WorkflowComposerView.post()` (`core/views/ci_workflows.py:504`) based on the steps being composed
- Remove all `first_step.step.engine` derivation patterns in tasks and views
- Migration: backfill from first step's engine for existing workflows

---

### GAP-09: Step Ordering Validation

**Design Reference**: workflow-definition.md, Section "Step Ordering Rules"

**Current Implementation**: `WorkflowComposerView.post()` (`core/views/ci_workflows.py:504`) accepts any step order without validation. Steps are saved in the order provided by the user.

**Gap**: A "setup-before-use" rule should be enforced: a step that requires a specific runtime (e.g., Python 3.12) must be preceded by a setup step that provides that runtime. Pathfinder should block saving workflows that violate this constraint.

**Impact**: Users can create invalid workflows that will fail at CI runtime. The failure only becomes visible after a build attempt, wasting developer time.

**Remediation**:
- Add validation in `WorkflowComposerView.post()` that iterates through steps in order
- For each step with `runtime_constraints`, verify a setup step for the same runtime appears earlier
- Return a user-friendly error message listing which step requires which setup step
- Use `CIStep.runtime_constraints` and `CIStep.phase == "setup"` for the check

---

### GAP-10: Workflow Archived Status

**Design Reference**: versioning.md, Section "Deprecation and Deletion"

**Current Implementation**: `CIWorkflow.status` choices (`core/models.py:669`) are only `("published", "Published")` and `("draft", "Draft")`. No "archived" state.

**Gap**: An "archived" status should prevent new service onboarding to the workflow but allow existing builds and service updates to continue.

**Impact**: No way to deprecate a workflow gracefully. Must either delete it (blocked by PROTECT FK if in use) or leave it active and discoverable.

**Remediation**:
- Add `("archived", "Archived")` to `CIWorkflow.status` choices
- Filter out archived workflows in the service wizard step and in `get_available_workflows_for_project()`
- Allow existing services using an archived workflow to continue operating
- Add archive/unarchive action to workflow detail view

---

### GAP-11: Auto-Update on Version Publish

**Design Reference**: versioning.md, Sections "Auto-Update Behavior" and "Publishing"

**Current Implementation**: `PublishVersionView` (`core/views/ci_workflows.py:750`) changes the draft status to authorized, assigns the version number, and records timestamps. No auto-push to services occurs.

**Gap**: On publish, Pathfinder should identify services pinned to the same workflow. For patch version bumps, automatically push the updated manifest to those services via PR. Digest PR reuse: if a PR from a previous auto-update is still open, update it rather than creating a new one.

**Impact**: Services do not receive security patches automatically. Manual intervention is required for every patch update across potentially many services.

**Remediation**:
- Add a post-publish task that queries `Service.objects.filter(ci_workflow=workflow)`
- Compare the service's pinned version to the new version using semver
- For patch bumps (same major.minor), call `push_ci_manifest` for each eligible service
- Implement PR digest: check for existing open Pathfinder PRs before creating new ones

---

### GAP-12: Version Cleanup and Retention

**Design Reference**: versioning.md, Section "Cleanup and Retention"

**Current Implementation**: No cleanup logic exists. Versions and manifest content persist indefinitely.

**Gap**: Manifest content should be cleared for old authorized versions after a configurable retention period. Version records should be deleted when no Build references them. Workflow deletion should be blocked while builds reference any of its versions.

**Impact**: Storage grows unbounded. No lifecycle management for old versions.

**Remediation**:
- Add retention settings to `ProjectCIConfig` or a new global CI config model (default: 90 days)
- Add periodic cleanup task: clear `manifest_content` for authorized versions older than retention period
- Add deletion guard: prevent `CIWorkflowVersion` deletion while `Build.workflow_version` references exist
- Add `CIWorkflow` deletion guard while any version has build references

---

### GAP-13: Artifact Discovery via CI Plugin

**Design Reference**: build-lifecycle.md, Section "Build State and Artifact Discovery"; build-authorization.md, Step 6

**Current Implementation**: `extract_artifact_ref()` in `core/views/webhooks.py:75` extracts `artifacts_url` directly from the webhook payload.

**Gap**: Artifact references should be fetched from the CI engine API or container registry -- not from webhook payloads. Webhook payloads are untrusted per the security model. The CI plugin should be responsible for resolving the actual image reference and digest.

**Impact**: The current artifact reference is a GitHub API URL, not an actual container image reference. It is extracted from an untrusted webhook payload rather than verified through the API.

**Remediation**:
- Add `resolve_artifact_ref()` method to `CICapableMixin` (`plugins/base.py`)
- Implement in `GitHubPlugin` to query GitHub Packages API or container registry
- Call in `poll_build_details` (`core/tasks.py:481`) instead of passing webhook `artifact_ref`
- Store resolved image ref (e.g., `ghcr.io/owner/repo:sha-abc123`) on `Build.artifact_ref`

---

### GAP-14: Build Categorization by manifest_id

**Design Reference**: build-authorization.md, Section "Build Categorization"

**Current Implementation**: `ServiceDetailView` (`core/views/services.py:449`) categorizes builds by `workflow_name` string matching: `current_builds_qs = all_builds.filter(workflow_name=current_workflow_name)`.

**Gap**: Categorization should use `manifest_id` matching `ci_plugin.manifest_id(service.ci_workflow)`. This is the canonical identifier for Pathfinder-managed workflows.

**Impact**: Fragile categorization that depends on naming conventions. Could miscategorize builds if workflow names change or if the `ci-` prefix stripping logic in `poll_build_details` produces unexpected results.

**Remediation**:
- In `ServiceDetailView` builds tab, replace `workflow_name` filtering with `manifest_id` filtering
- Compute expected `manifest_id` from `ci_plugin.manifest_id(service.ci_workflow)`
- Filter: `current_builds_qs = all_builds.filter(manifest_id=expected_manifest_id)`
- Fallback to `workflow_name` matching for pre-migration builds without `manifest_id`

---

### GAP-15: "revoked" Build Verification Status

**Design Reference**: build-lifecycle.md, Build Model

**Current Implementation**: `Build.verification_status` choices (`core/models.py:856`) are: `verified`, `draft`, `unauthorized`. The `verify_build` task (`core/tasks.py:451`) maps revoked versions to `"unauthorized"`.

**Gap**: A distinct `"revoked"` verification status is needed to distinguish "unauthorized because hash matches no known version" from "unauthorized because the matched version has been revoked."

**Impact**: Cannot distinguish builds that ran a revoked version from builds that ran a completely unknown workflow. The UI cannot display a specific "Built with revoked workflow version X.Y.Z" warning.

**Remediation**:
- Add `("revoked", "Revoked")` to `Build.verification_status` choices
- Update `verify_build` (`core/tasks.py:447-452`) to set `"revoked"` when `version_match.status == CIWorkflowVersion.Status.REVOKED`
- Update the builds UI templates to show a distinct badge/warning for revoked builds
- Update README.md Build Verification States table to include the new state

---

### GAP-16: Engine-Agnostic Build Model

**Design Reference**: build-lifecycle.md, Build Model

**Current Implementation**: `Build` model (`core/models.py:840`) has `github_run_id = models.BigIntegerField(unique=True)`. `map_github_status` is a static method on `Build` (`core/models.py:904`).

**Gap**: The field should be engine-agnostic (`ci_run_id`). Status mapping should live in the plugin, not the model.

**Impact**: The Build model is coupled to GitHub. Adding Jenkins or GitLab CI would require model changes rather than just a new plugin.

**Remediation**:
- Rename `github_run_id` to `ci_run_id` (database column rename via migration)
- Move `map_github_status` from `Build` to `GitHubPlugin` as `map_run_status`
- Update all references: `core/tasks.py:558` (`Build.objects.update_or_create(github_run_id=run_id)`), `core/models.py:902` (`__str__`), and any template references
- Add `map_run_status(status, conclusion)` to `CICapableMixin` interface

---

### GAP-17: CI Variables in Manifest

**Design Reference**: steps-catalog.md, Section "CI Integration -- Variables"

**Current Implementation**: `generate_manifest()` in `plugins/github/plugin.py:61` has no knowledge of the service context. No `PTF_*` environment variables are injected into the generated workflow.

**Gap**: When pushing a manifest to a service repo, Pathfinder should inject `PTF_PROJECT`, `PTF_SERVICE`, and `PTF_ENVIRONMENT` as environment variables in the GitHub Actions workflow.

**Impact**: CI steps cannot use Pathfinder context variables. Integration between Pathfinder and the CI pipeline is incomplete -- steps that need to know which service or project they belong to have no way to find out.

**Remediation**:
- Modify `generate_manifest()` to accept an optional `service_context` dict
- When provided, inject an `env` block into the workflow YAML with `PTF_PROJECT`, `PTF_SERVICE`, `PTF_ENVIRONMENT`
- Update `push_ci_manifest` (`core/tasks.py:594`) to pass service context when generating or re-generating manifests
- For stored version content, consider injecting variables at push time rather than at generation time

---

### GAP-18: Step Validation API

**Design Reference**: steps-catalog.md, Section "Step Validation API"

**Current Implementation**: Not implemented. No API endpoint exists.

**Gap**: A `POST /api/ci-workflows/steps/validate` endpoint should accept a step definition file and return parsed metadata, computed slug, conflict detection results, warnings, and definition_hash. This allows step authors to validate definitions before merging to the steps repo.

**Impact**: Step authors cannot validate definitions before merging. Errors are only discovered after the sync task runs, which may be hours later.

**Remediation**:
- Create a new API view with token authentication
- Reuse parsing logic from `discover_steps` (`core/ci_steps.py:16`) and `parse_step_file` (`plugins/github/plugin.py:47`)
- Return structured validation result: `{slug, name, phase, inputs, conflicts: [], warnings: [], definition_hash}`
- Add URL route at `api/ci-workflows/steps/validate`

---

### GAP-19: manifest_path Cleanup

**Design Reference**: plugin-interface.md

**Current Implementation**: `GitHubPlugin` has both `manifest_id(workflow)` (`plugins/github/plugin.py:139`) returning `.github/workflows/ci-{workflow.name}.yml` AND `manifest_path(service)` (`plugins/github/plugin.py:135`) returning `.github/workflows/{service.handler}.yml`.

**Gap**: `manifest_path` is inconsistent with the design -- it uses `service.handler` instead of the workflow name. The `push_ci_manifest` task correctly uses `manifest_id`, but `manifest_path` still exists as dead code that could confuse future developers.

**Impact**: Code confusion. A developer might use the wrong method and generate manifests at incorrect file paths.

**Remediation**:
- Remove `manifest_path` from `CICapableMixin` (`plugins/base.py`) if it exists as an abstract method
- Remove `manifest_path` from `GitHubPlugin` (`plugins/github/plugin.py:135`)
- Verify no code references `manifest_path` via grep
- Update any documentation referencing the method

---

## Remediation Phases

### Phase R1: Step Identity and Change Tracking

**Goal**: Steps have proper identity (globally unique slug per engine), per-file versioning, change detection via definition hash, and soft-delete via archival instead of hard delete.

**Gaps Addressed**: GAP-01, GAP-02, GAP-03, GAP-04

**Estimated Complexity**: Large (3-4 plans)
- Plan 1: Add `slug`, `definition_hash`, `status` fields to `CIStep`; migration with backfill
- Plan 2: Rewrite `scan_steps_repository` for per-file SHA, collision detection, change detection, archival
- Plan 3: Update workflow composer and detail views for archived step warnings; add cleanup task

**Dependencies**: None (foundation work)

**Key Changes**:
- **Models**: `CIStep` -- add `slug`, `definition_hash`, `status` fields; new unique constraint on `["engine", "slug"]`
- **Tasks**: `scan_steps_repository` -- per-file git log, hash computation, change classification, archive instead of delete
- **Views**: Workflow composer step picker filters out archived steps; workflow detail shows step update warnings
- **Templates**: Badge/warning for archived or updated steps

**Risk Notes**:
- Migration must backfill `slug` from `directory_name` for existing steps
- Changing from shallow clone to full clone (or deeper shallow) in `scan_steps_repository` increases clone time
- The `unique_together` on `["engine", "slug"]` may conflict with existing data if two repos have steps with the same directory name

**Done when**: Steps have unique slugs per engine, `commit_sha` reflects per-file history, changes are detected and logged, removed steps are archived (not deleted).

---

### Phase R2: Workflow Model Hardening

**Goal**: CIWorkflow has an explicit engine field set at creation, step ordering is validated before save, and an "archived" status allows graceful deprecation.

**Gaps Addressed**: GAP-08, GAP-09, GAP-10

**Estimated Complexity**: Small (1-2 plans)
- Plan 1: Add `engine` field to `CIWorkflow`; add ordering validation in composer; add `archived` status choice

**Dependencies**: None (can run in parallel with R1)

**Key Changes**:
- **Models**: `CIWorkflow` -- add `engine` CharField, add `"archived"` to status choices
- **Views**: `WorkflowComposerView.post()` -- set engine from steps, add setup-before-use validation
- **Tasks**: `verify_build`, `push_ci_manifest` -- use `workflow.engine` instead of step-derived engine
- **Templates**: Service wizard and workflow list filter out archived workflows

**Risk Notes**:
- Migration must backfill `engine` from first step for existing workflows
- Ordering validation must not break existing valid workflows (validate only on save, not retroactively)

**Done when**: `CIWorkflow.engine` is set at creation and used everywhere; invalid step orders are rejected with a clear message; archived workflows are hidden from new onboarding but remain functional for existing services.

---

### Phase R3: Build Model Corrections

**Goal**: Build model is engine-agnostic with a generic `ci_run_id`, has a distinct "revoked" verification status, and categorizes builds by `manifest_id` instead of workflow name.

**Gaps Addressed**: GAP-14, GAP-15, GAP-16

**Estimated Complexity**: Small (1-2 plans)
- Plan 1: Rename `github_run_id` to `ci_run_id`; add `"revoked"` verification status; update build categorization to use `manifest_id`

**Dependencies**: R2 (GAP-14 needs `manifest_id` which uses workflow engine from R2; however the field already exists on Build so this dependency is soft)

**Key Changes**:
- **Models**: `Build` -- rename `github_run_id` to `ci_run_id`, add `("revoked", "Revoked")` to `verification_status`
- **Tasks**: `verify_build` -- set `"revoked"` when version is revoked; `poll_build_details` -- use `ci_run_id`
- **Views**: `ServiceDetailView` builds tab -- categorize by `manifest_id` instead of `workflow_name`
- **Plugins**: Move `map_github_status` from `Build` to `GitHubPlugin`; add `map_run_status` to `CICapableMixin`

**Risk Notes**:
- Database column rename for `github_run_id` requires a migration that preserves existing data
- Any external tools querying the `core_build` table directly will break (no external API currently)

**Done when**: `github_run_id` is renamed to `ci_run_id`; revoked versions produce `"revoked"` verification status with distinct UI badge; builds tab categorizes by `manifest_id`.

---

### Phase R4: Sync Operations and Logging

**Goal**: Step repository syncs are triggered by webhooks and scheduled tasks (in addition to manual poll), all sync operations are logged with per-step detail, and branch protection is validated on registration and each sync.

**Gaps Addressed**: GAP-05, GAP-06, GAP-07

**Estimated Complexity**: Medium (2-3 plans)
- Plan 1: Create `StepsRepoSyncLog` and `StepSyncEntry` models; update `scan_steps_repository` to create log entries
- Plan 2: Add webhook handler for steps repo push; add scheduled daily scan task; add branch protection validation
- Plan 3: Add sync history UI on repo detail page

**Dependencies**: R1 (sync logging references step slugs and archive actions from R1)

**Key Changes**:
- **Models**: New `StepsRepoSyncLog` and `StepSyncEntry` models
- **Views**: New webhook handler for steps repo push events; sync history section on repo detail
- **Tasks**: `scan_steps_repository` -- create log entries; new daily scheduled scan task
- **Plugins**: Add `check_branch_protection()` to `CICapableMixin` and `GitHubPlugin`
- **Templates**: Sync history table on repo detail page

**Risk Notes**:
- Webhook handler for steps repo uses the same webhook URL format as build webhooks; must distinguish by event type or use separate endpoints
- Branch protection check requires API permissions that the GitHub connection might not have
- Daily scheduled task requires django-tasks periodic task infrastructure

**Done when**: Steps repo push triggers automatic rescan; daily scan runs without manual intervention; every sync creates a detailed log; branch protection is validated with clear status display.

---

### Phase R5: Version Lifecycle Automation

**Goal**: Patch version publishes auto-push updated manifests to services; old versions are cleaned up per retention policy.

**Gaps Addressed**: GAP-11, GAP-12

**Estimated Complexity**: Medium (2-3 plans)
- Plan 1: Add auto-update task triggered after version publish; implement PR digest reuse
- Plan 2: Add retention settings; add periodic cleanup task; add deletion guards

**Dependencies**: R2 (needs workflow `archived` status for filtering), R3 (cleanup references builds for deletion guards)

**Key Changes**:
- **Tasks**: New post-publish auto-update task; new periodic cleanup task
- **Models**: Retention settings on `ProjectCIConfig` or global config; deletion guards on `CIWorkflowVersion`
- **Views**: `PublishVersionView` -- enqueue auto-update task after publish

**Risk Notes**:
- Auto-update creates PRs in service repos; must handle rate limiting and PR conflicts
- Cleanup task must not delete manifest content that is still needed for build verification
- PR digest reuse requires checking for existing open PRs, adding complexity

**Done when**: Publishing a patch version triggers automatic manifest PRs for eligible services; old version content is cleaned up after retention period; version and workflow deletion is guarded by build references.

---

### Phase R6: Manifest and Plugin Interface

**Goal**: Artifact discovery uses CI plugin API (not webhook payloads), CI variables are injected into manifests, a step validation API exists, and dead `manifest_path` code is removed.

**Gaps Addressed**: GAP-13, GAP-17, GAP-18, GAP-19

**Estimated Complexity**: Medium (2-3 plans)
- Plan 1: Add `resolve_artifact_ref()` to plugin interface; implement in GitHubPlugin; inject PTF_* variables in manifest
- Plan 2: Create step validation API endpoint; remove `manifest_path` dead code

**Dependencies**: R2 (manifest generation uses engine field), R3 (artifact ref resolution relates to build model)

**Key Changes**:
- **Plugins**: Add `resolve_artifact_ref()` and `map_run_status()` to `CICapableMixin`; implement in `GitHubPlugin`; remove `manifest_path`
- **Tasks**: `poll_build_details` -- call `resolve_artifact_ref()` instead of using webhook artifact_ref
- **Views**: New API view for step validation at `api/ci-workflows/steps/validate`
- **Plugin base**: `generate_manifest()` accepts optional service context for PTF_* variables

**Risk Notes**:
- `resolve_artifact_ref()` requires access to container registry or GitHub Packages API; authentication may differ from standard GitHub App permissions
- Step validation API needs authentication; token-based auth must be added if not already available
- Removing `manifest_path` is safe only if confirmed no code references it

**Done when**: Artifact refs are resolved via CI plugin API; manifests include PTF_* variables when pushed for a service; step validation API returns parsed metadata; `manifest_path` is removed.

---

## Migration and Risk Assessment

### Database Migrations (ordered)

| Phase | Model | Change | Migration Type |
|-------|-------|--------|----------------|
| R1 | CIStep | Add `slug` CharField | AddField + data migration (backfill from directory_name) |
| R1 | CIStep | Add `definition_hash` CharField | AddField |
| R1 | CIStep | Add `status` CharField (default="active") | AddField |
| R1 | CIStep | New unique constraint `["engine", "slug"]` | AddConstraint (after backfill) |
| R2 | CIWorkflow | Add `engine` CharField (default="github_actions") | AddField + data migration (backfill from first step) |
| R2 | CIWorkflow | Add "archived" to status choices | AlterField (no data change) |
| R3 | Build | Rename `github_run_id` to `ci_run_id` | RenameField |
| R3 | Build | Add "revoked" to verification_status choices | AlterField (no data change) |
| R4 | New | Create `StepsRepoSyncLog` model | CreateModel |
| R4 | New | Create `StepSyncEntry` model | CreateModel |
| R4 | StepsRepository | Add `protection_valid` BooleanField | AddField |
| R4 | StepsRepository | Add `webhook_registered` BooleanField | AddField |
| R5 | ProjectCIConfig | Add retention settings fields | AddField |

### Data Migration Notes

- **Slug backfill (R1)**: Derive from `directory_name` using Django's `slugify()`. Run as a data migration before adding the unique constraint.
- **Engine backfill (R2)**: Query `workflow.workflow_steps.first().step.engine` for each workflow. Default to `"github_actions"` for workflows with no steps.
- **commit_sha recalculation (R1)**: Per-file SHAs will be computed on the next sync run. No data migration needed -- values update organically.

### Breaking Changes

- **`github_run_id` rename (R3)**: Any raw SQL queries or management commands referencing this column name will break. Search codebase for all references before migrating.
- **Hard delete to soft delete (R1)**: Code that assumes deleted steps are gone from the database needs updating. Filter queries with `status="active"` where appropriate.
- **`manifest_path` removal (R6)**: Verify zero references before removing.

### Rollback Strategy

Each phase produces independent migrations. To roll back:
1. Revert the code changes for the phase
2. Run `python manage.py migrate core <previous_migration_number>` to reverse migrations
3. Each phase is designed to be independently deployable -- reverting R3 does not require reverting R2

---

## Implementation Priority Matrix

```
                    HIGH IMPACT
                        |
    GAP-04 (Critical)   |   GAP-01 (High)
    GAP-15 (High)       |   GAP-02 (High)
    GAP-08 (High)       |   GAP-03 (High)
                        |
   --- LOW EFFORT ------+------ HIGH EFFORT ---
                        |
    GAP-19 (Low)        |   GAP-06 (Medium)
    GAP-10 (Low)        |   GAP-07 (Medium)
    GAP-16 (Low)        |   GAP-11 (Medium)
    GAP-14 (Medium)     |   GAP-05 (Medium)
    GAP-17 (Low)        |   GAP-13 (Medium)
                        |   GAP-18 (Low)
                        |   GAP-12 (Low)
                        |
                    LOW IMPACT
```

**Quadrant strategy**:

| Quadrant | Gaps | Strategy |
|----------|------|----------|
| High Impact / Low Effort | GAP-04, GAP-08, GAP-15 | Do first -- quick wins with high value |
| High Impact / High Effort | GAP-01, GAP-02, GAP-03 | Plan carefully -- R1 is the largest phase |
| Low Impact / Low Effort | GAP-10, GAP-14, GAP-16, GAP-17, GAP-19 | Bundle with related work in same phase |
| Low Impact / High Effort | GAP-05, GAP-06, GAP-07, GAP-11, GAP-12, GAP-13, GAP-18 | Defer to later phases or simplify scope |

**Recommended execution order**:
1. **R1** (Step Identity) and **R2** (Workflow Hardening) -- in parallel, foundation work
2. **R3** (Build Corrections) -- quick follow-up
3. **R4** (Sync and Logging) -- depends on R1
4. **R5** (Version Lifecycle) -- depends on R2 and R3
5. **R6** (Manifest and Plugin) -- depends on R2 and R3

---

## What Is Already Implemented

The following design items are fully implemented and do not require remediation. The remediation phases build on this foundation.

- **CIWorkflowVersion model** with draft/authorized/revoked states and state machine transitions
- **Versioning state machine**: draft to authorized, authorized to revoked
- **Publish version** with semver validation and changelog
- **Revoke version** with content clearing
- **Draft discard** action
- **Fork workflow** with `fork_from` query param in composer
- **Suggested version calculation** (next patch/minor/major)
- **Manifest hash computation** and storage (`compute_manifest_hash` in `core/models.py`)
- **Build verification flow** (7-step, per `build-authorization.md`)
- **Sync detection**: `pending_pr` to `synced` transition on build verification match
- **CICapableMixin interface** with all required abstract methods (`plugins/base.py`)
- **Manifest header** with deterministic generation (workflow name, version)
- **Service CI tab** with workflow and version selectors (Alpine `ciSelector` component)
- **Push manifest via PR** with feature branch and PR creation
- **Webhook handler** for build events (`core/views/webhooks.py`)
- **Manual poll** for build details (`poll_build_details` task)
- **Version history tab** in workflow detail view
- **Allow Drafts** project-level toggle (`ProjectCIConfig.allow_draft_workflows`)
- **Build categorization** (basic, by `workflow_name`)

---

## Dependency Graph

```
R1 (Step Identity)  ----+
                        |
R2 (Workflow Model) -+  +--> R4 (Sync & Logging)
                     |
                     +--> R3 (Build Corrections) --+--> R5 (Version Lifecycle)
                     |                             |
                     +-----------------------------+--> R6 (Manifest & Plugin)
```

R1 and R2 have no dependencies and can execute in parallel.
R3 has a soft dependency on R2.
R4 depends on R1 (step slugs, archive status).
R5 depends on R2 and R3.
R6 depends on R2 and R3.
