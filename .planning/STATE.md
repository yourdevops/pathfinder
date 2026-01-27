# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-21)

**Core value:** Developers can deploy production-ready services in minutes through self-service, while platform teams maintain governance and visibility.
**Current focus:** Phase 5 complete - Ready for Phase 6 (Builds)

## Current Position

Phase: 5 of 7 (Services)
Plan: 4 of 4 in current phase - COMPLETED (all plans)
Status: Phase complete
Last activity: 2026-01-26 - Completed 05-04-PLAN.md (Service List and Detail)

Progress: [====================================] 100% (Phase 5)

## Performance Metrics

**Velocity:**
- Total plans completed: 31
- Average duration: 4 min
- Total execution time: 2.25 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation-security | 6 | 25 min | 4 min |
| 02-core-domain | 4 | 20 min | 5 min |
| 03-integrations | 6 | 23 min | 4 min |
| 03.1-unified-sidebar | 3 | 9 min | 3 min |
| 04-blueprints | 3 | 10 min | 3.3 min |
| 04.1-replace-uuid-urls-with-slugs | 4 | 19 min | 4.75 min |
| 05-services | 4 | 18 min | 4.5 min |

**Recent Trend:**
- Last 5 plans: 05-01 (1 min), 05-03 (4 min), 05-02 (8 min), 05-04 (5 min)
- Trend: stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

| Phase | Decision | Rationale |
|-------|----------|-----------|
| 01-01 | Custom User extends AbstractUser with UUID field | Simpler than AbstractBaseUser, UUID as public ID for URLs |
| 01-01 | Custom Group model (not Django built-in) | Need system_roles JSONField for RBAC |
| 01-01 | AuditlogMiddleware after AuthenticationMiddleware | Captures request.user in audit entries |
| 01-02 | darkMode: class with hardcoded dark class | No toggle needed per requirements |
| 01-02 | Context processor for role booleans | Computed once per request, cleaner than template logic |
| 01-02 | Sidebar navigation 64rem fixed width | Main content offset with ml-64 class |
| 01-03 | Setup state = token exists OR (no token AND no admins) | Distinguishes fresh install from completed setup |
| 01-03 | SetupMiddleware before AuthenticationMiddleware | Must enforce setup before auth processing |
| 01-03 | Fallback to hardcoded /users/ path | users:list URL does not exist until Plan 04 |
| 01-04 | AdminRequiredMixin for CBV permission checking | Consistent with Django patterns for class-based views |
| 01-04 | has_system_role helper for system_roles checking | Reusable permission logic via GroupMembership query |
| 01-05 | Card-based group list vs table for users | Visual hierarchy and scanability for groups |
| 01-05 | Template tags for audit log formatting | Consistent human-readable entries like John created user Alice |
| 01-06 | LoginRequiredMixin for placeholder views | Standard Django pattern for auth enforcement |
| 02-01 | JSONField for env_vars with list of dicts | Flexible schema, supports locked values, easy merge |
| 02-01 | project_role on ProjectMembership not Group | Same group can have different roles per project |
| 02-01 | HTMX via CDN (unpkg) | No build step, version pinned in template |
| 02-02 | Settings section groups User Management | Cleaner organization per CONTEXT.md |
| 02-02 | Projects link visible to all users | Permissions handled at view/project level |
| 02-02 | LOGIN_REDIRECT_URL to projects:list | Projects is the primary workflow entry point |
| 02-03 | Role hierarchy viewer < contributor < owner | Clear role escalation with system role override |
| 02-03 | HTMX tab pattern with hx-push-url | No page reload, browser history works |
| 02-03 | Context-replacing sidebar (AWS style) | Clearer project context, dedicated project nav |
| 02-04 | Env var lock prevents override | Locked project vars cannot be overridden at environment level |
| 02-04 | Amber styling for production | bg-amber-500/20 for production environments |
| 02-04 | Inheritance shown via badge | Blue Inherited for project-level, green Environment for local |
| 03-01 | Fernet key from env or auto-generated file | SSP_ENCRYPTION_KEY env for prod, secrets/encryption.key for dev |
| 03-01 | Sensitive field detection by pattern | Matches token, secret, password, private_key, api_key, client_secret |
| 03-01 | Plugin registry singleton pattern | Class methods on PluginRegistry for global access |
| 03-04 | OperatorRequiredMixin for system-level access | Uses existing has_system_role helper |
| 03-04 | Connections grouped by plugin category | SCM, Deploy, Other sections in list view |
| 03-04 | Plugin URL autodiscovery | Dynamic registration at /integrations/<plugin>/ |
| 03.1-01 | Expandable sidebar with $persist() | localStorage state persistence for nav sections |
| 03.1-01 | Settings in main nav not separate sidebar | nav_settings.html deprecated, settings in expandable section |
| 03.1-01 | active_settings_section context variable | Nav highlighting for settings sub-pages |
| quick-017 | Services as default project landing page | Consolidated nav: Services, Environments, Settings |
| quick-017 | Members section in Settings tab | Reduces nav items, keeps related config together |
| 03.1-03 | Back button in DevSSP logo position | Consistent styling with text-xl font-bold |
| 04-01 | GitPython for SCM abstraction (not GitHub API) | Supports any Git server (GitHub, GitLab, Bitbucket, self-hosted) |
| 04-01 | Sort key format for versions | {major:05d}.{minor:05d}.{patch:05d}.{prerelease or 'zzzz'} |
| 04-01 | Manifest file names | Primary: ssp-template.yaml, fallback: devssp-template.yaml |
| 04-02 | SCM connection dropdown for private repos | "None" option for public repos, GitHub connections for private |
| 04-02 | HTMX live preview validates manifest | Registration blocked until valid manifest previewed |
| 04-02 | Redirect to detail after registration | Per CONTEXT.md decision, not to list page |
| 04-03 | Show unavailable toggle default unchecked | Per CONTEXT.md, unavailable blueprints hidden by default |
| 04-03 | HTMX auto-poll every 3s while syncing | Stops polling when sync_status changes from 'syncing' |
| 04-03 | Unavailable blueprints remain clickable | Link to detail page where setup hint banner appears |
| 04.1-01 | RFC 1123 label format allows starting with digit | Relaxed from RFC 952 letter-only requirement |
| 04.1-01 | Custom 'dns' path converter | Built-in 'slug' allows uppercase/underscores, not DNS-compatible |
| 04.1-01 | max_length=63 for name fields | DNS subdomain limit |
| 04.1-02 | Environment lookups include project scope | Environment names are unique within a project |
| 04.1-04 | Connection names used as URL slug | Human-readable URLs like /connections/github-main/ |
| 04.1-03 | User URLs remain UUID-based for privacy | Group remove_member keeps user_uuid for the user being removed |
| 04.1-03 | Blueprint name lookup uses exact match | Already enforced by model validator |
| 05-01 | PROTECT on_delete for blueprint ForeignKeys | Prevents orphan services when blueprints deleted |
| 05-01 | Service status: draft, active, error | draft=not built, active=successful build, error=failed |
| 05-01 | Env var merge: project first, service overrides | Locked project vars cannot be overridden at service level |
| 05-02 | forms.py converted to forms/ package | Better organization as forms modules grow |
| 05-02 | SessionWizardView for service creation | Multi-step state management from django-formtools |
| 05-02 | HTMX for dynamic blueprint versions | Clean UX without page reload |
| 05-02 | JavaScript env var editor with JSON field | Dynamic add/remove with JSON serialization |
| 05-03 | Jinja2 for template substitution | StrictUndefined mode to catch missing variables early |
| 05-03 | Feature branch naming: feature/{service-name} | Consistent convention for scaffolding into existing repos |
| 05-04 | Service URLs under projects namespace | URLs follow /projects/<project_name>/services/<service_name>/ pattern |
| 05-04 | Wizard redirect to project detail | After service creation, redirects to projects:detail (services tab) |
| 05-04 | Service sidebar navigation pattern | Details, Builds, Environments tabs with HTMX switching |

### Roadmap Evolution

- Phase 3.1 inserted after Phase 3: Unified sidebar navigation structure (URGENT) - 2026-01-26
- Phase 4.1 inserted after Phase 4: Replace UUID URLs with Slugs - Use human-readable slugs instead of UUIDs in all URLs (URGENT) - 2026-01-26

### Pending Todos

None yet.

### Blockers/Concerns

None - Phase 5 complete with service creation, scaffolding, list and detail pages

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 001 | Fix STATIC_ROOT setting for collectstatic | 2026-01-22 | 1cac75c | [001-fix-static-root-setting-for-collectstati](./quick/001-fix-static-root-setting-for-collectstati/) |
| 002 | Fix input text color and merge unlock/register pages | 2026-01-22 | b24e5cd | [002-fix-input-text-color-and-merge-unlock-re](./quick/002-fix-input-text-color-and-merge-unlock-re/) |
| 003 | Fix unlock token bypass security issue | 2026-01-22 | 92aae42 | [003-fix-unlock-token-bypass-security-issue](./quick/003-fix-unlock-token-bypass-security-issue/) |
| 004 | Add root URL redirect to /projects/ | 2026-01-22 | 9c37520 | [004-add-root-url-redirect-to-projects](./quick/004-add-root-url-redirect-to-projects/) |
| 005 | Fix humanize and JSONField contains errors | 2026-01-22 | 413b55a | [005-fix-humanize-and-jsonfield-contains-errors](./quick/005-fix-humanize-and-jsonfield-contains-errors/) |
| 006 | Consolidate has_system_role SQLite compat | 2026-01-22 | e09d598 | [006-consolidate-has-system-role-sqlite-compat](./quick/006-consolidate-has-system-role-sqlite-compat/) |
| 007 | UI navigation items arrangement - Settings section | 2026-01-23 | 5ea4142 | [007-ui-navigation-items-arrangement](./quick/007-ui-navigation-items-arrangement/) |
| 008 | Fix Settings and Projects UI sidebar replacement | 2026-01-23 | 22deebd | [008-fix-settings-and-projects-ui-sidebar-rep](./quick/008-fix-settings-and-projects-ui-sidebar-rep/) |
| 009 | Fix projects page padding and icon sizing | 2026-01-23 | 6191121 | [009-fix-projects-page-padding-and-huge-icons](./quick/009-fix-projects-page-padding-and-huge-icons/) |
| 010 | Fix integrations page permissions and access control | 2026-01-23 | 342e6c6 | [010-fix-integrations-page-permissions-and-ac](./quick/010-fix-integrations-page-permissions-and-ac/) |
| 011 | Integrations sidebar expansion with Plugins page | 2026-01-23 | 6f82061 | [011-integrations-sidebar-expansion-with-plug](./quick/011-integrations-sidebar-expansion-with-plug/) |
| 012 | Add missing GitHub plugin functionality (PAT auth, list repos) | 2026-01-23 | 30993a6 | [012-add-missing-github-plugin-functionality](./quick/012-add-missing-github-plugin-functionality/) |
| 013 | Remove list repos page and fix auth wizard | 2026-01-23 | 1f50cda | [013-remove-list-repos-page-and-fix-auth-wiza](./quick/013-remove-list-repos-page-and-fix-auth-wiza/) |
| 014 | Create example python-helloworld blueprint | 2026-01-26 | 329ccf0 | [014-create-example-helloworld-blueprint-with](./quick/014-create-example-helloworld-blueprint-with/) |
| 015 | Support multiple deploy plugins in blueprints | 2026-01-26 | 9c0fe11 | [015-support-multiple-deploy-plugins-in-bluep](./quick/015-support-multiple-deploy-plugins-in-bluep/) |
| 016 | Fix sidebar context replacement for project navigation | 2026-01-26 | 9a120cf | [016-fix-sidebar-context-replacement-for-proj](./quick/016-fix-sidebar-context-replacement-for-proj/) |
| 017 | Consolidate project pages and update nav | 2026-01-26 | 69ced86 | [017-consolidate-project-pages-and-update-nav](./quick/017-consolidate-project-pages-and-update-nav/) |
| 018 | Fix blueprint registration name error | 2026-01-27 | b4a723c | [018-fix-blueprint-registration-name-error](./quick/018-fix-blueprint-registration-name-error/) |
| 019 | Show pending blueprints in list view | 2026-01-27 | 679ec3f | [019-show-pending-blueprints-in-list](./quick/019-show-pending-blueprints-in-list/) |
| 020 | ASGI docker-compose with worker | 2026-01-27 | 1552dd8 | [020-asgi-docker-compose-worker](./quick/020-asgi-docker-compose-worker/) |
| 021 | Fix connection detail URL and worker queues | 2026-01-27 | c65a4b3 | [021-fix-connection-detail-url-and-investigat](./quick/021-fix-connection-detail-url-and-investigat/) |
| 022 | Wizard improvements and helper text | 2026-01-27 | 27f64f1 | [022-fix-healthchecks-wizard-improvements](./quick/022-fix-healthchecks-wizard-improvements/) |

## Session Continuity

Last session: 2026-01-27
Stopped at: Completed quick-022 (Wizard improvements and helper text)
Resume file: None
