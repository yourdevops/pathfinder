# Domain Pitfalls: Internal Developer Platform (IDP)

**Domain:** Internal Developer Platform / Self-Service Portal
**Project:** DevSSP
**Researched:** 2026-01-21
**Confidence:** MEDIUM-HIGH (based on multiple industry sources + DevSSP design analysis)

---

## Critical Pitfalls

Mistakes that cause rewrites, security breaches, or complete adoption failure.

### Pitfall 1: Static Portal Syndrome

**What goes wrong:** The IDP becomes a "static directory" - developers visit to find links but must leave to perform actual tasks. The portal surfaces information but cannot power workflows, governance, or automation.

**Why it happens:**
- Starting with the UI/frontend before building solid backend APIs and orchestration
- Focusing on "catalog" features rather than self-service actions
- Underestimating the integration depth required for true self-service

**Consequences:**
- Developers bypass the portal for faster manual methods
- Platform team becomes a ticket queue instead of enablers
- ROI impossible to demonstrate - investment with no productivity gains

**Warning signs:**
- High portal page views but low "action completion" rates
- Developers still creating manual tickets for common tasks
- "I just use the CLI directly" feedback

**Prevention:**
- Build orchestration APIs first, UI second
- Every portal page should enable an action, not just display information
- Measure "actions completed via portal" not "portal visits"

**Relevance to DevSSP:**
- DevSSP design correctly emphasizes "orchestrate, don't rebuild"
- Webhook-based CI integration is action-oriented
- Risk: Ensure the wizard UI actually triggers deployments, not just shows status

**Phase to address:** Phase 1 (Core Foundation) - ensure API-first architecture

---

### Pitfall 2: Webhook-Only Integration Fragility

**What goes wrong:** Relying exclusively on webhooks for CI/CD integration creates fragile state synchronization. Missed webhooks leave DevSSP in inconsistent state with no recovery mechanism.

**Why it happens:**
- Webhooks appear simpler than polling
- Assumption that webhooks are reliable "fire and forget"
- DevSSP design explicitly chose "webhook-only CI integration (no polling)"

**Consequences:**
- Builds complete in CI but DevSSP shows "pending" forever
- Deployments succeed but portal shows "failed"
- Loss of trust in the platform - developers check CI directly
- No way to reconcile state without manual database fixes

**Warning signs:**
- Discrepancies between CI system status and DevSSP status
- Support tickets: "my build shows pending but it finished hours ago"
- Increasing "unknown" statuses over time

**Prevention:**
- Implement idempotent webhook handlers with deduplication
- Add a "reconciliation" API endpoint to manually sync state
- Implement webhook delivery verification (check for missed events)
- Consider hybrid approach: webhook for real-time + periodic "health sync" for reconciliation
- Log all webhook payloads for debugging and replay

**Relevance to DevSSP:**
- CRITICAL: DevSSP explicitly chose webhook-only (per milestone context)
- This decision trades operational complexity for simplicity but creates brittleness
- At minimum: implement webhook replay/resync capability
- Consider: optional polling fallback for environments where webhook delivery is unreliable

**Phase to address:** Phase 2 (CI Integration) - build reconciliation from day one

---

### Pitfall 3: Permission Leakage via Object-Level Access

**What goes wrong:** Using django-guardian for object-level permissions without comprehensive query filtering allows data leakage across projects/environments.

**Why it happens:**
- Global permissions checked but object permissions skipped in some queries
- Bulk operations bypass permission checks
- Admin interfaces expose unfiltered querysets
- Complex permission inheritance (Group -> ProjectMembership -> Service) has gaps

**Consequences:**
- User in Project A can view/modify resources in Project B
- Audit logs show access but enforcement is inconsistent
- Compliance violations (SOX, PCI DSS) - DevSSP targets enterprise with compliance needs

**Warning signs:**
- Inconsistent results between API and admin interface
- Users reporting they can see resources they shouldn't
- Permission checks in views but not in queryset filters

**Prevention:**
- Always filter querysets by permission, not just check permissions in views
- Use `get_objects_for_user()` for all list views
- Implement comprehensive permission integration tests
- Audit admin customizations to ensure proper filtering
- Add "effective permissions" debug endpoint for troubleshooting

**Relevance to DevSSP:**
- DevSSP uses django-guardian (per milestone context)
- Complex hierarchy: User -> Group -> SystemRole + ProjectMembership -> Resources
- Services, Deployments, Builds all need project-scoped filtering
- IntegrationConnections shared across projects add complexity

**Phase to address:** Phase 1 (RBAC Implementation) - permission filtering in every queryset

---

### Pitfall 4: Secrets in Environment Variables

**What goes wrong:** Environment variable cascade (Project -> Environment -> Service -> Deployment) stores secrets alongside configuration, creating exposure risk.

**Why it happens:**
- Environment variables are convenient and familiar
- "Just put the API key in the env vars" path of least resistance
- Lack of clear boundary between config and secrets

**Consequences:**
- Secrets stored in database (even if encrypted) rather than proper secrets manager
- Secrets visible in deployment logs, error messages, debug output
- No rotation capability - changing a secret requires redeployment
- Audit nightmare - who accessed which secrets when?

**Warning signs:**
- env_vars containing fields like `api_key`, `password`, `token`
- Deployment logs showing environment variable values
- No integration with HashiCorp Vault, AWS Secrets Manager, or K8s Secrets

**Prevention:**
- Explicitly document: "env_vars are for CONFIGURATION ONLY, not secrets"
- Add validation to reject common secret patterns in env_vars
- Integrate with external secrets managers for actual secrets
- Secrets injected at deploy time by the deploy plugin, not stored in DevSSP
- Add "secret reference" type that points to external secret store

**Relevance to DevSSP:**
- DevSSP docs already note: "Secrets must come from external sources (Vault, K8s Secrets)"
- But no enforcement mechanism exists in the design
- Risk: Users WILL put secrets in env_vars if there's no alternative workflow
- Need clear UX showing "Configuration" vs "Secrets" with different handling

**Phase to address:** Phase 3 (Deployment Features) - secrets integration before env vars

---

### Pitfall 5: Template Versioning Drift

**What goes wrong:** Git tag-based template versioning (per milestone context) creates divergence between templates and deployed services over time.

**Why it happens:**
- Templates evolve but existing services don't automatically update
- No link between deployed service and template version used at creation
- Template breaking changes affect new services but not existing ones
- "Sync" feature updates template metadata but not existing service configurations

**Consequences:**
- Fleet of services with inconsistent CI/CD configurations
- Security patches in templates don't propagate to existing services
- Platform team cannot enforce standards across existing services
- Technical debt accumulates invisibly

**Warning signs:**
- Different services from same template behaving differently
- "Works in new projects, fails in old ones" debugging sessions
- Template updates that never reach production services

**Prevention:**
- Track `template_version_used` on each Service record
- Implement "template drift detection" showing which services are behind
- Provide "upgrade template" workflow with diff preview
- Consider: template as "source" vs "one-time scaffolding" modes
- Separate "CI pipeline template" (can upgrade) from "source scaffolding" (one-time)

**Relevance to DevSSP:**
- DevSSP uses "template versioning via git tags" (per milestone context)
- Current design treats templates as one-time scaffolding (clone, substitute, push)
- No mechanism to update existing services when templates change
- This is acceptable for MVP but creates long-term fleet management issues

**Phase to address:** Post-MVP (Phase 4+) - template drift detection and upgrade workflows

---

## Moderate Pitfalls

Mistakes that cause delays, technical debt, or user frustration.

### Pitfall 6: Plugin Architecture Rigidity

**What goes wrong:** Plugin architecture becomes either too abstract (developers can't customize) or too concrete (every integration needs code changes).

**Why it happens:**
- Trying to make plugins handle every possible integration scenario
- Coupling plugin interface too tightly to first implementation (GitHub, Docker)
- Not designing for multi-instance plugins (same plugin type, different configs)

**Consequences:**
- Adding new integration type requires significant code changes
- Existing plugins can't be extended without forking
- Configuration becomes increasingly complex to handle edge cases

**Warning signs:**
- Plugin configuration schema keeps expanding with special-case fields
- "We need a custom plugin" requests for minor variations
- Plugins have many disabled capabilities because they don't apply

**Prevention:**
- Design for configuration over code (JSON schema for plugin config)
- Support plugin inheritance/composition for variations
- Multi-instance from day one (multiple GitHub orgs, multiple K8s clusters)
- Clear capability interface that plugins implement selectively

**Relevance to DevSSP:**
- DevSSP has solid plugin architecture design (IntegrationPlugin -> IntegrationConnection)
- Multi-instance already supported (one GitHub plugin, many GitHub connections)
- Risk: GitHub Actions as CI has different needs than Jenkins
- Risk: Kubernetes direct deploy vs ArgoCD GitOps vs Jenkins pipeline

**Phase to address:** Phase 2 (Integration Plugins) - test with diverse real integrations

---

### Pitfall 7: Audit Logging Gaps

**What goes wrong:** Audit logging is incomplete or performs poorly at scale, failing compliance requirements.

**Why it happens:**
- Audit logging added as afterthought rather than core design
- Bulk operations skip audit logging (django-auditlog limitation)
- Missing actor information when middleware not configured
- M2M relationship changes not tracked

**Consequences:**
- "Who made this change?" unanswerable for compliance audits
- Gaps in audit trail create compliance violations
- Performance degradation with high-volume operations

**Warning signs:**
- Audit entries with null `actor` field
- Missing entries for bulk operations
- Auditors asking for data that doesn't exist
- Slow admin pages when audit tables grow

**Prevention:**
- Use django-auditlog with middleware for actor tracking
- Wrap bulk operations to log explicitly
- Index audit tables properly (timestamp, actor, object_type)
- Register all models including M2M fields explicitly
- Implement async audit logging for high-volume operations

**Relevance to DevSSP:**
- DevSSP targets enterprise compliance (SOX, PCI DSS per RBAC design)
- RBAC doc specifies comprehensive audit logging requirements
- All permission-related actions should be logged
- Need to verify: Build/Deployment updates logged? Connection config changes?

**Phase to address:** Phase 1 (Foundation) - audit logging as core infrastructure

---

### Pitfall 8: Adoption Without Intrinsic Value

**What goes wrong:** Platform adoption driven by management mandate rather than developer value. Developers bypass the platform or use it resentfully.

**Why it happens:**
- Building for operators/compliance first, developers second
- Not measuring developer experience metrics
- Focusing on features leadership wants vs features developers need
- Treating developers as users to manage rather than customers to serve

**Consequences:**
- Shadow IT: developers build workarounds
- Low adoption despite mandates
- Platform team becomes enforcement team, not enablement team
- 36.6% of platforms rely on mandates - these fail as alternatives emerge

**Warning signs:**
- Usage drops when mandates relax
- Developers use CLI/API to bypass UI workflows
- Negative developer satisfaction scores
- "How do I skip this step?" questions

**Prevention:**
- Measure developer satisfaction (NPS) alongside operational metrics
- Track "time to first deployment" for new developers
- Every feature should reduce developer cognitive load
- Build for the "happy path" first, compliance second
- Make the platform the path of least resistance

**Relevance to DevSSP:**
- DevSSP positions as enterprise-focused (compliance, audit)
- Risk: building for admins/auditors first, developers second
- Wizard-based UI is developer-friendly approach
- Self-service is the goal - don't undermine it with approval bottlenecks

**Phase to address:** Every phase - developer experience as continuous priority

---

### Pitfall 9: Abstraction Level Mismatch

**What goes wrong:** Platform either over-abstracts (black boxes developers can't understand) or under-abstracts (exposes too much infrastructure complexity).

**Why it happens:**
- Building for "sophisticated users" who want full control
- Or building for "beginners" who want magic
- Not recognizing different personas need different abstraction levels

**Consequences:**
- Over-abstracted: developers can't debug issues, feel disempowered
- Under-abstracted: cognitive overload, steep learning curve
- One-size-fits-all templates don't fit anyone well

**Warning signs:**
- Over: "I need to change X but the platform won't let me"
- Under: "There are too many options, I don't know what to choose"
- Frequent requests for "escape hatches" to underlying systems

**Prevention:**
- Design progressive disclosure: simple defaults, advanced options available
- Provide "explain mode" showing what platform will do
- Allow power users to override/customize at appropriate points
- Different templates for different experience levels

**Relevance to DevSSP:**
- Blueprints (templates) provide abstractions over infrastructure
- Env var cascade provides layered configuration control
- Risk: template `variables` schema may be too simple or too complex
- Need "view generated manifests" before deploy for transparency

**Phase to address:** Phase 3 (Blueprints) - progressive disclosure in template UX

---

### Pitfall 10: Database-Backed SQLite in Production

**What goes wrong:** SQLite works for development but creates operational issues in production deployments.

**Why it happens:**
- DevSSP stack specifies SQLite (per CLAUDE.md)
- Works fine for single-instance testing
- Migration to PostgreSQL deferred "for later"

**Consequences:**
- Write locks under concurrent webhook load
- No replication for HA deployment
- Backup/restore complexity
- Cannot use database-specific features (JSONB, row-level locking)

**Warning signs:**
- "database is locked" errors under load
- Webhook processing delays during busy periods
- Inability to scale horizontally

**Prevention:**
- Use PostgreSQL from day one (django-tenants, JSON fields work better)
- SQLite only for local development
- Document production database requirements early
- Design for async webhook processing with proper queue

**Relevance to DevSSP:**
- CLAUDE.md specifies SQLite as stack
- Acceptable for early development/demo
- Enterprise deployment will require PostgreSQL
- Consider: SQLite default with PostgreSQL support, not SQLite only

**Phase to address:** Phase 1 (Infrastructure) - PostgreSQL support from start

---

## Minor Pitfalls

Mistakes that cause annoyance but are recoverable.

### Pitfall 11: DNS-Compatible Naming Constraints Too Strict

**What goes wrong:** Strict naming rules (lowercase, hyphens only, 63 chars) frustrate users who want human-readable names.

**Why it happens:**
- DevSSP enforces DNS-compatible naming for all entities
- Users expect to use "My App" not "my-app"
- Error messages don't explain why restrictions exist

**Prevention:**
- Clear UX explaining naming rules and showing preview
- Auto-suggest valid name from user input
- Description field clearly positioned for human-readable text

**Relevance to DevSSP:**
- Already has description field for human context
- Consider: auto-slugify from free-text input?

---

### Pitfall 12: Health Check False Positives

**What goes wrong:** IntegrationConnection health checks pass but actual operations fail.

**Why it happens:**
- Health check only verifies authentication
- Doesn't verify all required permissions
- Network path for health check differs from operation path

**Prevention:**
- Health checks should verify actual capabilities
- "Test connection" should try representative operations
- Track health_status vs operation_success separately

**Relevance to DevSSP:**
- IntegrationConnection has health_status, last_health_check
- Need to ensure health checks are meaningful, not just "can connect"

---

### Pitfall 13: Stale Template Cache

**What goes wrong:** Template sync doesn't pick up latest changes, or caches stale manifest data.

**Why it happens:**
- Aggressive caching of template metadata
- Git clone without proper fetch/pull
- Webhook for auto-sync unreliable

**Prevention:**
- Always fresh-fetch on sync request
- Show "last synced" timestamp prominently
- Validate manifest version matches git tag

---

## Phase-Specific Warnings

| Phase | Likely Pitfall | Mitigation |
|-------|----------------|------------|
| Phase 1: Foundation | Permission filtering gaps (Pitfall 3) | Every queryset filtered by permission |
| Phase 1: Foundation | SQLite in production (Pitfall 10) | PostgreSQL support from start |
| Phase 2: CI Integration | Webhook state inconsistency (Pitfall 2) | Build reconciliation endpoint |
| Phase 2: Integration Plugins | Plugin rigidity (Pitfall 6) | Test with diverse integrations |
| Phase 3: Deployments | Secrets in env vars (Pitfall 4) | External secrets integration first |
| Phase 3: Blueprints | Template versioning drift (Pitfall 5) | Track version used per service |
| All Phases | Adoption failure (Pitfall 8) | Developer experience metrics |

---

## DevSSP Design Decisions: Risk Assessment

| Design Decision | Risk Level | Notes |
|-----------------|------------|-------|
| Django auth + django-guardian | MEDIUM | Solid choice, but watch for query filtering gaps |
| Plugin-based integrations | LOW | Good architecture, test with diverse integrations |
| Simplified capability routing | LOW | Clear model, scales well |
| Environment-scoped infra resources | LOW | Standard pattern, works |
| Webhook-only CI integration | HIGH | Needs reconciliation mechanism |
| Template versioning via git tags | MEDIUM | OK for MVP, plan for drift detection |
| SQLite database | HIGH | Replace with PostgreSQL for production |
| Group-only project membership | LOW | Enterprise-friendly, AD-compatible |

---

## Sources

### IDP Implementation Pitfalls
- [7 Common IDP Implementation Pitfalls](https://www.fairwinds.com/blog/how-to-avoid-7-idp-implementation-pitfalls)
- [7 Most Common Pitfalls When Choosing IDP](https://www.qovery.com/blog/7-most-common-pitfalls-when-choosing-the-right-internal-developer-platform)
- [8 Platform Engineering Anti-Patterns](https://www.infoworld.com/article/4064273/8-platform-engineering-anti-patterns.html)
- [9 Platform Engineering Anti-Patterns That Kill Adoption](https://jellyfish.co/library/platform-engineering/anti-patterns/)

### Webhooks vs Polling
- [Polling vs Webhooks: When to Use One Over the Other](https://www.merge.dev/blog/webhooks-vs-polling)
- [Webhooks vs. Polling](https://medium.com/@nile.bits/webhooks-vs-polling-431294f5af8a)

### Django Security
- [Django-Guardian Object Level Permissions](https://django-guardian.readthedocs.io/)
- [Overcoming Django's Object-Based Permissions Challenge](https://medium.com/@hamzaashes/overcoming-djangos-object-based-permissions-challenge-8eaa0ba8bd53)

### Audit Logging
- [Django Audit Logging Libraries](https://medium.com/@mariliabontempo/django-audit-logging-the-best-libraries-for-tracking-model-changes-with-postgresql-2c7396564e97)
- [Django Auditlog Practical Guide](https://medium.com/@mahdikheireddine7/tracking-changes-in-django-with-django-auditlog-a-practical-guide-5bd2404b68b9)

### Secrets Management
- [Pitfalls of Using Environment Variables for Secrets](https://cloudtruth.com/blog/the-pitfalls-of-using-environment-variables-for-config-and-secrets/)
- [Kubernetes Secrets Management 2025](https://infisical.com/blog/kubernetes-secrets-management-2025)
- [Are Environment Variables Still Safe for Secrets in 2026](https://securityboulevard.com/2025/12/are-environment-variables-still-safe-for-secrets-in-2026/)

### Platform Adoption Metrics
- [Platform Engineering Maturity 2026](https://platformengineering.org/blog/platform-engineering-maturity-in-2026)
- [How to Track Platform Engineering Metrics](https://spacelift.io/blog/platform-engineering-metrics)
