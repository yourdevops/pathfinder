# Phase 6: Builds - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Webhook ingestion from GitHub Actions and build tracking. Services transition from draft to active on first successful build. Users can view build history for services.

</domain>

<decisions>
## Implementation Decisions

### Webhook Design
- HMAC signature authentication (shared secret per service, signature verification)
- Single endpoint `/webhooks/build/` with status in payload (not separate start/complete endpoints)
- Always return 200 OK regardless of outcome (prevents enumeration attacks, log errors internally)
- Webhook is notification-only — triggers poll to GitHub API for build details
- Use GitHub run_id as unique identifier for builds

### Real-time Updates
- Poll GitHub API after webhook to fetch full build details (commit, branch, author, duration, etc.)
- Consider WebSocket connection for real-time updates when user is viewing an in-progress build page

### Build History Display
- Table rows layout (dense, scannable)
- Detailed columns: status icon, commit SHA + message preview, branch, author avatar, started timestamp, duration, artifact link, GitHub job link
- Filter by status only (all, success, failed, running)
- Classic pagination with 20 builds per page

### Plugin Architecture
- GitHub-specific functionality lives in GitHub plugin, not core app
- Core defines CI capability interfaces (webhook handling, build polling, real-time updates)
- Plugins implement interface for their CI engine
- Expect future plugins: Bitbucket Pipelines (CI+SCM), Gitea (SCM), Jenkins (CI)

### Claude's Discretion
- Build status state machine (pending → running → success/failed)
- Service activation logic and any UI feedback on first successful build
- Exact GitHub API polling implementation
- WebSocket vs polling trade-offs for real-time updates

</decisions>

<specifics>
## Specific Ideas

- "All we need to know is that a job exists" — webhook is lightweight trigger, GitHub API is source of truth
- Build info display should include commit message preview and author avatar for context

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-builds*
*Context gathered: 2026-02-03*
