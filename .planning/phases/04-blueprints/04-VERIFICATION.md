---
phase: 04-blueprints
verified: 2026-01-26T12:45:43Z
status: passed
score: 15/15 must-haves verified
---

# Phase 4: Blueprints Verification Report

**Phase Goal:** Platform engineers can publish service templates; developers can browse available blueprints
**Verified:** 2026-01-26T12:45:43Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Operator can register a Blueprint from a git URL; system syncs metadata from ssp-template.yaml | ✓ VERIFIED | BlueprintRegisterView creates Blueprint, sync_blueprint task clones repo with GitPython and reads manifest |
| 2 | Blueprint displays name, description, tags, ci.plugin, deploy.plugin from manifest | ✓ VERIFIED | Blueprint model has all fields; list.html and detail.html render them; sync task populates from manifest.get() |
| 3 | Blueprint shows available git tags as selectable versions | ✓ VERIFIED | BlueprintVersion model stores parsed tags; detail.html shows version list with prerelease toggle |
| 4 | Operator can manually trigger sync to refresh versions | ✓ VERIFIED | BlueprintSyncView enqueues sync_blueprint task; _sync_status.html has HTMX "Sync Now" button |
| 5 | Blueprint availability is filtered based on project environment connections (matching deploy_plugin) | ✓ VERIFIED | Blueprint.is_available_globally() checks IntegrationConnection; list.html dims unavailable with opacity-50; detail.html shows amber warning banner |
| 6 | Blueprint displays synced metadata (name, description, tags) from repository | ✓ VERIFIED | Same as #2 - sync_blueprint updates name, description, tags from manifest dict |
| 7 | Blueprint versions are sorted correctly by semantic version | ✓ VERIFIED | BlueprintVersion.sort_key computed by compute_version_sort_key; Meta ordering=['-sort_key'] |
| 8 | Operator can see sync status (pending, syncing, synced, error) on blueprint | ✓ VERIFIED | Blueprint.sync_status field; _sync_status.html shows badge with color coding |
| 9 | Pre-release versions are identified and can be filtered separately | ✓ VERIFIED | BlueprintVersion.is_prerelease boolean; detail.html has "Show pre-releases" checkbox that filters via query param |
| 10 | Blueprint sync works with any Git-compatible SCM (not GitHub-specific) | ✓ VERIFIED | git_utils.py uses GitPython clone_repo_shallow (not GitHub API); parse_git_url supports github.com, gitlab.com, etc. |
| 11 | User can view blueprint list with table layout | ✓ VERIFIED | list.html has table with thead/tbody; columns: Name, Tags, Deploy Plugin, Versions, Last Synced, Status |
| 12 | Operator sees live preview of manifest before registering blueprint | ✓ VERIFIED | BlueprintPreviewView clones repo and reads manifest; _preview.html shows fields; register.html has HTMX hx-post to preview endpoint |
| 13 | Operator can select SCM provider (GitHub connections or 'None' for public repos) | ✓ VERIFIED | BlueprintRegisterView GET queries GitHub connections; register.html has dropdown with "None (public repository)" + connections |
| 14 | Registration is blocked until valid manifest is previewed | ✓ VERIFIED | register.html submit button has :disabled="!previewValid"; _preview.html x-init sets previewValid=true/false |
| 15 | Blueprint list can be filtered by tags and deploy plugin | ✓ VERIFIED | list.html x-data has filterTag, filterPlugin; rows have data-tags, data-plugin; x-show filters based on state |

**Score:** 15/15 truths verified (100%)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `core/models.py` | Blueprint and BlueprintVersion models | ✓ EXISTS + SUBSTANTIVE + WIRED | 496 lines total; Blueprint at line 347 (94 lines), BlueprintVersion at line 442 (39 lines); imported by views and tasks |
| `core/tasks.py` | sync_blueprint task with version parsing | ✓ EXISTS + SUBSTANTIVE + WIRED | sync_blueprint at line 113 (100+ lines); imports git_utils; called by views via .enqueue() |
| `core/git_utils.py` | GitPython helper functions for SCM-agnostic Git operations | ✓ EXISTS + SUBSTANTIVE + WIRED | 318 lines; exports 8 functions (parse_git_url, build_authenticated_git_url, clone_repo_shallow, etc.); imported by tasks and views |
| `requirements.txt` | semver and GitPython dependencies | ✓ EXISTS + SUBSTANTIVE | Contains GitPython>=3.1.0, semver>=3.0.0, PyYAML>=6.0.0 |
| `core/migrations/0006_blueprint_blueprintversion.py` | Database schema for blueprints | ✓ EXISTS | 3219 bytes; creates core_blueprint and core_blueprint_version tables |
| `core/views/blueprints.py` | Blueprint views (list, detail, register, preview) | ✓ EXISTS + SUBSTANTIVE + WIRED | 333 lines; 6 view classes; imports Blueprint, sync_blueprint, git_utils; referenced in urls.py |
| `core/templates/core/blueprints/list.html` | Table-style blueprint list | ✓ EXISTS + SUBSTANTIVE | 204 lines; has table, Alpine.js filtering (x-data, x-show), showUnavailable toggle |
| `core/templates/core/blueprints/register.html` | Registration form with SCM dropdown and preview panel | ✓ EXISTS + SUBSTANTIVE | 133 lines; has git_url input, connection dropdown, HTMX preview panel, disabled submit button |
| `core/templates/core/blueprints/_preview.html` | HTMX partial for manifest preview | ✓ EXISTS + SUBSTANTIVE | 54 lines; shows preview_data fields or error; x-init sets previewValid |
| `core/templates/core/blueprints/detail.html` | Blueprint detail with versions | ✓ EXISTS + SUBSTANTIVE | 173 lines; shows metadata, version list, prerelease toggle, availability banner |
| `core/templates/core/blueprints/_sync_status.html` | HTMX partial for sync status updates | ✓ EXISTS + SUBSTANTIVE | 77 lines; shows status badge, last synced, sync button with hx-post |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| core/tasks.py | core/models.py | Blueprint.objects.get | ✓ WIRED | Line 135: `Blueprint.objects.get(id=blueprint_id)` |
| core/tasks.py | core/git_utils.py | clone_repo_shallow, read_manifest_from_repo, list_tags_from_repo | ✓ WIRED | Line 124: `from core.git_utils import` all functions used |
| core/git_utils.py | core/models.py (IntegrationConnection) | Extract credentials for Git URL auth | ✓ WIRED | build_authenticated_git_url accepts connection param; calls connection.get_config() |
| core/views/blueprints.py | core/models.py | Blueprint.objects | ✓ WIRED | Line 42+: `Blueprint.objects.exclude`, line 150+: `Blueprint.objects.filter`, line 216: `Blueprint.objects.create` |
| core/views/blueprints.py | core/tasks.py | sync_blueprint.enqueue | ✓ WIRED | Line 222: `sync_blueprint.enqueue(blueprint_id=blueprint.id)` after creation; line 304: sync button |
| core/views/blueprints.py (BlueprintPreviewView) | core/git_utils.py | clone_repo_shallow, read_manifest_from_repo, build_authenticated_git_url | ✓ WIRED | Line 4: imports all functions; line 88-98: calls them in sequence |
| core/urls.py | core/views/blueprints.py | URL patterns | ✓ WIRED | blueprints_patterns list has 6 routes to view classes |
| core/templates/core/blueprints/register.html | core/views/blueprints.py | HTMX preview fetch | ✓ WIRED | Line 37+: input has `hx-post="{% url 'blueprints:preview' %}"` |
| core/views/blueprints.py (BlueprintRegisterView POST) | Blueprint.connection | connection_id field | ✓ WIRED | Line 209+: gets connection_id from POST, assigns to Blueprint.connection if provided |

### Requirements Coverage

| Requirement | Status | Supporting Truths | Notes |
|-------------|--------|-------------------|-------|
| BPRT-01: Operator can register blueprint from git URL | ✓ SATISFIED | Truths #1, #12, #13, #14 | Register view + preview + validation all verified |
| BPRT-02: Blueprint syncs metadata from ssp-template.yaml | ✓ SATISFIED | Truths #1, #2, #6 | sync_blueprint task reads manifest and updates fields |
| BPRT-03: Blueprint shows available git tags as versions | ✓ SATISFIED | Truths #3, #7, #9 | BlueprintVersion model + sorting + prerelease filtering |
| BPRT-04: Blueprint displays name, description, tags, ci.plugin, deploy.plugin | ✓ SATISFIED | Truths #2, #6 | All fields rendered in list and detail templates |
| BPRT-05: Operator can manually sync blueprint | ✓ SATISFIED | Truth #4, #8 | Sync button in _sync_status.html with HTMX |
| BPRT-06: Blueprint availability filtered by connections | ✓ SATISFIED | Truth #5, #15 | is_available_globally checks + UI dimming + filters |

**Coverage:** 6/6 requirements satisfied (100%)

### Anti-Patterns Found

No anti-patterns found. Scanned:
- `core/views/blueprints.py`: No TODO/FIXME/placeholder patterns
- `core/git_utils.py`: No stub patterns
- `core/tasks.py`: No stub patterns in sync_blueprint
- Templates: Only legitimate HTML placeholder attributes (input placeholders)

### Human Verification Required

#### 1. End-to-End Registration Flow with Public Repository

**Test:**
1. Navigate to /blueprints/register/
2. Select "None (public repository)" from SCM dropdown
3. Enter a public Git URL with ssp-template.yaml (e.g., a test GitHub repo)
4. Wait for preview to load
5. Verify preview shows parsed manifest fields
6. Click "Register Blueprint"
7. Verify redirect to detail page
8. Wait for sync to complete
9. Verify versions appear

**Expected:**
- Preview fetches manifest via GitPython without authentication
- Blueprint created with connection=null
- Sync completes successfully
- Versions listed on detail page

**Why human:** Requires actual Git repository access and Django server running; can't verify network operations programmatically

#### 2. End-to-End Registration Flow with Private Repository

**Test:**
1. Create a GitHub connection (or use existing)
2. Navigate to /blueprints/register/
3. Select the GitHub connection from dropdown
4. Enter a private repository URL
5. Wait for preview to load
6. Verify preview succeeds with authentication
7. Register blueprint
8. Verify sync uses authenticated connection

**Expected:**
- Preview uses build_authenticated_git_url with connection credentials
- GitPython clones private repo successfully
- Blueprint.connection field set correctly

**Why human:** Requires authenticated GitHub connection setup; network operations; credential handling

#### 3. Blueprint Availability Filtering

**Test:**
1. Register a blueprint with deploy.plugin = "docker"
2. Ensure NO active docker connections exist
3. Navigate to /blueprints/
4. Verify blueprint appears dimmed (opacity-50)
5. Verify tooltip shows "Requires docker connection"
6. Uncheck "Show unavailable" toggle
7. Verify dimmed blueprint disappears
8. Check toggle again, verify it reappears
9. Create an active docker connection
10. Refresh blueprint list
11. Verify blueprint is no longer dimmed

**Expected:**
- is_available_globally returns false when no matching connection
- UI dims unavailable blueprints
- Toggle shows/hides unavailable blueprints
- Availability updates when connections added

**Why human:** Requires dynamic connection state changes; UI behavior verification

#### 4. Version Sorting and Prerelease Filtering

**Test:**
1. Register a blueprint with git tags: v1.0.0, v1.1.0-beta.1, v1.2.0, v0.9.0
2. Navigate to blueprint detail page
3. Verify versions sorted: v1.2.0 (latest badge), v1.0.0, v0.9.0
4. Verify v1.1.0-beta.1 is hidden by default
5. Check "Show pre-releases" toggle
6. Verify v1.1.0-beta.1 appears with "pre-release" badge
7. Verify v1.2.0 still shows "latest" badge (not the prerelease)

**Expected:**
- Semantic version sorting works correctly
- Prereleases hidden by default
- latest_version property ignores prereleases
- UI accurately reflects version state

**Why human:** Requires repository with specific tags; UI state verification

#### 5. Manual Sync with Version Updates

**Test:**
1. Register a blueprint from a repository
2. Wait for initial sync to complete
3. Add new git tags to the repository (externally)
4. On blueprint detail page, click "Sync Now"
5. Verify HTMX updates sync status to "Syncing..."
6. Wait for sync to complete
7. Verify new versions appear in version list
8. Verify version count updates

**Expected:**
- Sync button triggers HTMX request
- Status updates without page reload
- New versions detected and added
- Old versions removed if tags deleted

**Why human:** Requires external repository manipulation; async background task completion; HTMX behavior

#### 6. SCM-Agnostic Operations

**Test:**
1. Try registering blueprints from different Git hosts:
   - GitHub: https://github.com/org/repo
   - GitLab: https://gitlab.com/org/repo
   - Bitbucket: https://bitbucket.org/org/repo (if accessible)
2. Verify parse_git_url handles all formats
3. Verify preview works for all hosts
4. Verify sync works for all hosts

**Expected:**
- GitPython operations work with any Git-compatible server
- No hardcoded GitHub API calls in critical path
- Authentication embeds in Git URL for any host

**Why human:** Requires multiple SCM providers; network operations; GitPython behavior with different hosts

---

## Summary

**All automated verification passed.** Phase 4 goal achieved:

✓ Platform engineers can register blueprints from any Git repository
✓ System syncs metadata from ssp-template.yaml manifests
✓ Blueprints display all required metadata fields
✓ Git tags parsed into semantic versions with sorting
✓ Manual sync refreshes versions via HTMX
✓ Blueprint availability filtered by deploy plugin connections
✓ SCM-agnostic implementation using GitPython (not GitHub API)

**Structural verification complete.** All models, tasks, views, templates, and wiring verified at all three levels (exists, substantive, wired).

**6 human verification tests recommended** to validate end-to-end flows, UI behavior, and external integrations before Phase 5.

---

_Verified: 2026-01-26T12:45:43Z_
_Verifier: Claude (gsd-verifier)_
