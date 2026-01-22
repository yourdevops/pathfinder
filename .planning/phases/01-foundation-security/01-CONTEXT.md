# Phase 1: Foundation & Security - Context

**Gathered:** 2026-01-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Platform engineers can securely administer users and groups; all authenticated users have baseline platform access. Includes initial unlock flow, user authentication, RBAC via groups with SystemRoles, audit logging, and base navigation UI.

</domain>

<decisions>
## Implementation Decisions

### Unlock & onboarding flow
- Token entry leads immediately to admin registration form (no welcome page)
- Unlock page is minimal and secure — just token field and brief instruction, no branding
- After first admin account creation, redirect to User Management (not dashboard)
- Once setup is complete, unlock route silently redirects to login

### User & group management UI
- User list displayed as simple table (name, email, status, groups, actions)
- New user creation via modal dialog over the list
- Groups have dedicated detail pages (not expandable rows or side panels)
- Group membership manageable from both directions — add users from group page OR assign groups from user edit form

### Audit log presentation
- Summary-only entries for now — human-readable like "John created user Alice"
- No before/after diff in v1 (diffing engine deferred to v2)
- Audit log accessible from Admin section only (not global nav)

### Claude's Discretion
- Audit log filtering approach (basic filters vs search)
- Whether to include CSV export for audit logs
- Table pagination style and page sizes
- Form validation feedback patterns
- Loading states and error handling

</decisions>

<specifics>
## Specific Ideas

- Unlock page should feel like a "system lock" — secure, no-nonsense
- User management is the logical first stop after onboarding — admin needs to add team members

</specifics>

<deferred>
## Deferred Ideas

- Diffing engine for audit trail (complete before/after snapshots) — v2 scope

</deferred>

---

*Phase: 01-foundation-security*
*Context gathered: 2026-01-22*
