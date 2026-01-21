# Feature Landscape: Internal Developer Platforms

**Domain:** Internal Developer Platform / Developer Self-Service Portal
**Researched:** 2026-01-21
**Overall Confidence:** HIGH (verified against multiple authoritative sources)

## Executive Summary

Internal Developer Platforms (IDPs) have matured significantly. Backstage holds ~89% market share among organizations that have adopted an IDP, with Gartner predicting 75% of organizations with platform engineering teams will provide internal developer portals by 2026 (up from 45% in 2023).

DevSSP's planned features align well with industry table stakes. The current design covers the essential foundation: service catalog, blueprints/golden paths, RBAC, environment management, and deployment tracking. However, several differentiating opportunities and notable gaps exist.

---

## Table Stakes

Features users expect. Missing these means the product feels incomplete or users will choose alternatives.

| Feature | Why Expected | Complexity | DevSSP Status | Gap Analysis |
|---------|--------------|------------|---------------|--------------|
| **Software Catalog** | Central inventory for all services, APIs, and resources. Users need to know "what exists and who owns it." | Medium | Covered (Services, Projects) | DevSSP models services well; consider extending to non-service entities (APIs, data pipelines, libraries) in future |
| **Service Blueprints / Golden Paths** | Scaffold new services with best practices baked in. 89% of IDPs provide templates. | Medium | Covered (Blueprints with ssp-template.yaml) | Well-designed. Consider multiple archetype support (REST, event-driven, scheduled jobs, ML models) |
| **Self-Service Deployment** | Developers deploy without filing tickets. Core value proposition of any IDP. | High | Covered (wizard + deployment flows) | Strong design with direct/GitOps/pipeline mechanisms |
| **Environment Management** | Dev/staging/prod separation with appropriate connections and variables. | Medium | Covered (Environments model) | Well-designed with connection binding and env vars cascade |
| **Role-Based Access Control** | Granular permissions at system and project level. Enterprise compliance requirement. | High | Covered (SystemRoles + ProjectRoles) | Comprehensive design with admin/operator/auditor/user + owner/contributor/viewer. Group-based model is enterprise-ready |
| **Build & Deployment Tracking** | Visibility into what's deployed where and when. Audit trail requirement. | Medium | Covered (Build/Deployment models + webhooks) | Good webhook-based approach. Consider adding real-time status updates (WebSocket) |
| **Integration Plugins** | Connect to existing tools (SCM, CI, Artifact registries, Deploy targets). | High | Covered (IntegrationPlugin + IntegrationConnection) | Well-architected plugin model. Plan covers GitHub, Jenkins, BitBucket, K8s, Docker, ArgoCD |
| **Service Ownership Tracking** | Know who owns each service for incidents, changes, approvals. | Low | Partial (created_by fields, ProjectMembership) | Gap: No explicit "owner" field on Service. Ownership derived from project membership is indirect |
| **Production Safeguards** | Protect prod from accidental changes. Require elevated permissions, approvals. | Medium | Covered (is_production flag, permission matrix) | Good foundation. Approval workflows marked as planned |
| **Audit Logging** | Track who did what when for compliance (SOX, PCI DSS, HIPAA). | Medium | Planned | Currently only permission-related actions logged. Comprehensive audit trails on roadmap |

### Table Stakes Gap Summary

**Covered Well:**
- Service catalog (Services/Projects)
- Blueprints/golden paths
- Self-service deployment
- Environment management
- RBAC
- Build/deployment tracking
- Integration plugins

**Needs Attention:**
1. **Service Ownership** - Add explicit owner field on Service model (team/group reference, not just created_by)
2. **Real-time Updates** - Add WebSocket for deployment/build status (marked as planned, should be higher priority)
3. **Comprehensive Audit Trails** - Expand beyond permission changes (marked as planned)

---

## Differentiators

Features that set product apart. Not expected but valued highly by users who have them.

| Feature | Value Proposition | Complexity | DevSSP Status | Recommendation |
|---------|-------------------|------------|---------------|----------------|
| **Scorecards / Service Maturity** | Track service health, production readiness, compliance against standards. Cortex/OpsLevel key differentiator. | High | Missing | **HIGH PRIORITY**: Add scorecards for service maturity (has tests, has docs, has SLOs, security scans passing) |
| **API Documentation Integration** | Unified API docs via OpenAPI/Swagger specs attached to services. Reduces context-switching. | Medium | Missing | Consider: Attach OpenAPI specs to services, render in UI |
| **Service Dependencies Graph** | Visualize service relationships and impact of changes. | High | Missing | Defer: Nice to have but complex |
| **Cost Attribution / FinOps** | Track cloud costs per service/team. 89% of CFOs report cloud spending negatively impacted profitability. | High | Missing | Consider for enterprise tier: Integration with FinOps tools |
| **Observability Integration** | Link services to monitoring (Datadog, Prometheus, Grafana). 32.8% of platform engineers cite observability as main focus. | Medium | Missing | **MEDIUM PRIORITY**: Add observability connection type to link services to dashboards/alerts |
| **Secrets Management Integration** | First-class integration with Vault/AWS Secrets Manager. 2026 standard is dynamic, JIT secrets. | Medium | Planned (roadmap) | Good. Implement via External Secrets Operator pattern for K8s |
| **AI-Assisted Features** | Catalog discovery, incident response, IaC generation. Port/Backstage adding AI features in 2026. | High | Missing | Defer: Emerging but not essential yet |
| **Incident Management Integration** | Link services to PagerDuty/OpsGenie incidents. Critical for production services. | Medium | Missing | Consider: Useful for mature organizations |
| **SLO/SLA Tracking** | Define and monitor service level objectives. | Medium | Missing | Consider: Often combined with scorecards |
| **Documentation as Code (TechDocs)** | Store docs next to code, render in portal. Backstage pioneered this. | Medium | Missing | **MEDIUM PRIORITY**: Markdown docs in service repos rendered in UI |
| **Ephemeral Environments** | Spin up temporary environments for PR reviews, demos. | High | Missing | Defer: Complex, not essential for MVP |
| **Multi-Cluster / Multi-Cloud** | Manage deployments across multiple clusters and cloud providers. | High | Partial (via connections) | Current connection model supports this conceptually |
| **GitOps Native** | First-class ArgoCD/Flux integration with sync status visibility. | Medium | Planned (ArgoCD plugin) | Good direction |

### Differentiator Priority Matrix

**Build Now (High Value, Manageable Complexity):**
1. **Scorecards** - Major differentiator, adds governance value
2. **Documentation Integration** - Reduces doc sprawl

**Build Soon (High Value, Higher Complexity):**
3. **Observability Links** - Connect services to monitoring
4. **Secrets Management** - Already on roadmap, prioritize

**Defer (Nice to Have):**
- Service dependencies graph
- AI features
- Ephemeral environments
- Full FinOps integration

---

## Anti-Features

Features to explicitly NOT build. Common mistakes in this domain.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Full PaaS Functionality** | DevSSP should orchestrate existing tools (K8s, Jenkins, ArgoCD), not replace them. Building a full PaaS creates massive scope creep and maintenance burden. | Delegate execution to battle-tested tools. Be the control plane, not the compute plane. |
| **Custom CI System** | Jenkins, GitHub Actions, GitLab CI are mature. Building CI from scratch is years of work. | Integrate via webhooks and API calls. Track builds, don't execute them. |
| **Built-in Secrets Storage** | Security liability. Vault, AWS Secrets Manager are purpose-built and audited. | Integrate with external secrets managers. Never store secrets in DevSSP database. |
| **Custom Container Runtime** | Docker/containerd are standards. Building container orchestration is Kubernetes-level effort. | Use deployment plugins that call K8s/Docker APIs. |
| **Comprehensive Log Aggregation** | Datadog, Grafana Loki, ELK are specialized. Building log management is a separate product. | Link to external observability tools. Show deployment logs via CI/CD integration. |
| **Full GitOps Engine** | ArgoCD/Flux are mature, CNCF-backed. | Integrate with existing GitOps tools. Commit manifests, let them sync. |
| **Custom Identity Provider** | Auth0, Okta, Azure AD are mature and compliant. | Integrate via OIDC/LDAP (already on roadmap). Focus on authorization, not authentication. |
| **Unlimited Custom Workflows** | Port's fully flexible approach requires significant platform engineering effort. Can become maintenance nightmare. | Provide opinionated golden paths. Flexibility within guardrails, not unlimited customization. |
| **Per-Feature Pricing Model** | Cortex at $65/user/month is prohibitive for many. Complex pricing reduces adoption. | Simple pricing: Free tier for small teams, predictable enterprise pricing. |
| **Mandatory Manual Catalog Maintenance** | Cortex's heavy manual effort for catalog is a key criticism. | Auto-discovery from SCM and CI/CD. Minimize manual data entry. |

### The "Field of Dreams" Trap

**Critical Anti-Pattern:** Building a platform and assuming developers will use it.

**What DevSSP Does Right:**
- Wizard-driven service creation (low friction onboarding)
- Integration with existing tools developers already use (GitHub, Jenkins)
- Solves real pain: "deploy my code without filing tickets"

**Recommendations to Avoid This Trap:**
- Measure adoption metrics (services created, deployments triggered)
- Gather developer feedback early and often
- Start with one high-friction problem (service scaffolding + deployment)
- Add features based on actual user requests, not assumptions

---

## Feature Dependencies

Understanding which features require others to function properly.

```
Foundation (Build First):
  Projects + Environments + RBAC
      |
      v
Integration Plugins (SCM, CI, Artifact, Deploy)
      |
      v
Service Blueprints
      |
      v
Services + Build Tracking + Deployment Tracking
      |
      v
[Differentiators - Build After Foundation]
  ├─> Scorecards (requires: Services, metric integrations)
  ├─> Observability Links (requires: Services, observability plugins)
  ├─> Secrets Management (requires: Environments, K8s/Vault plugins)
  └─> Documentation (requires: Services, SCM integration)
```

### Dependency Notes

1. **Blueprints require SCM integration** - Can't scaffold repos without SCM connection
2. **Deployments require Build artifacts** - Artifact promotion model depends on build tracking
3. **Scorecards require Services + External integrations** - Metrics come from external tools
4. **Secrets require Environment context** - Secrets are scoped to environments

---

## MVP Recommendation

For MVP, prioritize these features in order:

### Phase 1: Foundation (Already Designed)
1. **Projects + Environments + RBAC** - Organizational structure and permissions
2. **Integration Plugins Framework** - Plugin architecture for extensibility
3. **Core Integrations** - GitHub/GitLab SCM, Jenkins CI, K8s/Docker deploy

### Phase 2: Self-Service Core (Already Designed)
4. **Service Blueprints** - Golden path templates with manifest
5. **Service Creation Wizard** - Self-service onboarding flow
6. **Build Tracking** - Webhook-based CI integration
7. **Deployment Management** - Deploy to environments, track status

### Phase 3: Enterprise Ready (Partially Designed)
8. **OIDC/LDAP Integration** - Enterprise auth (on roadmap)
9. **Comprehensive Audit Trails** - Compliance requirement (on roadmap)
10. **Approval Workflows** - Production safeguards (on roadmap)

### Phase 4: Differentiators (New)
11. **Scorecards** - Service maturity tracking (recommended addition)
12. **Secrets Management Integration** - Vault/AWS SM (on roadmap)
13. **Observability Links** - Dashboard/alert linking (recommended addition)
14. **TechDocs** - Documentation as code (recommended addition)

### Defer to Post-MVP
- Service dependencies visualization
- AI-assisted features
- Full FinOps integration
- Ephemeral environments
- Multi-artifact services

---

## Competitive Positioning

### DevSSP vs. Backstage

| Aspect | Backstage | DevSSP |
|--------|-----------|--------|
| **Model** | Framework (build your own) | Opinionated product |
| **Setup Time** | Weeks to months | Hours to days |
| **Customization** | Unlimited (plugin architecture) | Guided (within guardrails) |
| **Maintenance** | High (upgrades, plugin compatibility) | Low (managed by DevSSP) |
| **Target** | Large enterprises with platform teams | SMB to mid-market, lean platform teams |

**DevSSP Advantage:** Faster time-to-value for teams without dedicated platform engineers.

### DevSSP vs. Port.io

| Aspect | Port.io | DevSSP |
|--------|---------|--------|
| **Model** | Flexible data model (any entity) | Opinionated (Services focus) |
| **Complexity** | High (powerful but complex blueprints) | Medium (guided wizard) |
| **Use Case** | Any software catalog | Service deployment self-service |

**DevSSP Advantage:** Focused on deployment self-service, not general-purpose catalog.

### DevSSP vs. Humanitec

| Aspect | Humanitec | DevSSP |
|--------|-----------|--------|
| **Focus** | Platform Orchestration (Score spec) | Service Deployment |
| **IaC Approach** | Dynamic configuration generation | Template-based (existing IaC) |
| **Pricing** | Enterprise only | Accessible (to be defined) |

**DevSSP Advantage:** Works with existing tooling rather than requiring Score adoption.

### DevSSP vs. Cortex/OpsLevel

| Aspect | Cortex/OpsLevel | DevSSP |
|--------|-----------------|--------|
| **Focus** | Service maturity, scorecards | Service deployment |
| **Primary Value** | Governance and standards | Self-service deployment |
| **Pricing** | $40-65/user/month | TBD |

**DevSSP Opportunity:** Add scorecards to compete, while maintaining deployment focus.

---

## Sources

### Primary Sources (HIGH Confidence)
- [Backstage Official Documentation](https://backstage.io/)
- [Port.io Documentation](https://docs.port.io/)
- [Humanitec Platform Orchestrator](https://humanitec.com/products/platform-orchestrator)
- [CNCF Platform Engineering Guide](https://www.cncf.io/blog/2022/08/04/what-is-a-platform-orchestrator/)

### Market Research (MEDIUM Confidence)
- [Gartner Peer Insights - Internal Developer Portals](https://www.gartner.com/reviews/market/internal-developer-portals) - 75% adoption by 2026
- [Roadie: Platform Engineering in 2026](https://roadie.io/blog/platform-engineering-in-2026-why-diy-is-dead/) - Backstage 89% market share
- [Platform Engineering Tools 2026](https://platformengineering.org/blog/platform-engineering-tools-2026)
- [Internal Developer Platforms 2026 Top 11](https://www.cycloid.io/cycloid_page/internal-developer-platforms-idps-2026s-top-11/)

### Feature Analysis (MEDIUM Confidence)
- [Cortex - Internal Developer Portal](https://www.cortex.io/post/what-is-an-internal-developer-portal)
- [OpsLevel vs Cortex Comparison](https://www.opslevel.com/resources/opslevel-vs-cortex-whats-the-best-internal-developer-portal)
- [InfoWorld: Platform Engineering Anti-Patterns](https://www.infoworld.com/article/4064273/8-platform-engineering-anti-patterns.html)
- [Jellyfish: Anti-Patterns That Kill Adoption](https://jellyfish.co/library/platform-engineering/anti-patterns/)

### Technology Trends (MEDIUM Confidence)
- [FinOps Tools for Platform Engineers 2026](https://platformengineering.org/blog/10-finops-tools-platform-engineers-should-evaluate-for-2026)
- [Observability Tools for Platform Engineers 2026](https://platformengineering.org/blog/10-observability-tools-platform-engineers-should-evaluate-in-2026)
- [Secrets Management in 2026](https://www.javacodegeeks.com/2025/12/secrets-management-in-2026-vault-aws-secrets-manager-and-beyond-a-developers-guide.html)
- [Golden Paths Guide - Platform Engineering](https://platformengineering.org/blog/what-are-golden-paths-a-guide-to-streamlining-developer-workflows)
