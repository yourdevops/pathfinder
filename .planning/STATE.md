# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-21)

**Core value:** Developers can deploy production-ready services in minutes through self-service, while platform teams maintain governance and visibility.
**Current focus:** Phase 4 - Blueprints (Ready to plan)

## Current Position

Phase: 3 of 7 (External Integrations) - COMPLETE
Plan: 6 of 6 in current phase
Status: Complete
Last activity: 2026-01-23 - Completed 03-06-PLAN.md (Connection Attachments)

Progress: [================================] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 16
- Average duration: 4 min
- Total execution time: 1.1 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation-security | 6 | 25 min | 4 min |
| 02-core-domain | 4 | 20 min | 5 min |
| 03-integrations | 6 | 23 min | 4 min |

**Recent Trend:**
- Last 5 plans: 03-02 (4 min), 03-03 (3 min), 03-04 (11 min), 03-05 (4 min), 03-06 (5 min)
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

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 3 complete
- All integration infrastructure in place
- Ready for Phase 4 (Blueprints)

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

## Session Continuity

Last session: 2026-01-23
Stopped at: Completed quick task 012 - GitHub PAT auth and repository listing
Resume file: None