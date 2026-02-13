# Security & Compliance

These design documents cover three interconnected capabilities: secrets management (protecting sensitive configuration), artifact provenance (proving software supply chain integrity), and role-based access control (enforcing who can do what, where). Together they address the security findings from the [deployment design review](../deployments/review.md) and prepare Pathfinder for regulated industry adoption.

## What Security & Compliance Docs Do Not Do

- Define a proprietary encryption protocol (uses established standards: Fernet, Cosign, SLSA)
- Replace external vault systems (Pathfinder integrates with them, does not compete)
- Implement a policy-as-code engine (future consideration)
- Cover network security, TLS configuration, or infrastructure hardening
- Design external IAM integration (LDAP, SAML, OIDC -- future phase)
- Address deployment freeze windows or lifecycle hooks (Phase 7 scope)

## Cross-Cutting Concerns

The three security domains interact at multiple points:

- **RBAC gates secret access.** Who can create secrets, view secret names, and update secret values is controlled by the granular permission model. The `secrets-admin` system role enables cross-project secret management.
- **Provenance verification respects RBAC.** Non-production environments can skip attestation verification when configured, controlled by role-based deploy permissions.
- **Secrets flow through approval-gated deployments.** Secrets are referenced in deployments which, for production environments, require explicit approval from a separate user (four-eyes principle).
- **Audit trail spans all three domains.** Every secret mutation, provenance verification, role assignment, and approval decision is logged to the shared audit system.

## Threat Model Summary

These documents address three key threats identified in the [deployment design review](../deployments/review.md):

1. **Centralized credential risk ("god mode" problem)** -- Mitigated by [Secrets Management](secrets.md) with external vault integration. Production secrets never need to exist in Pathfinder's database; the write-only internal store is a stepping stone for teams without vault infrastructure, not the recommended production pattern.
2. **Artifact tampering in promotion chain** -- Mitigated by [Artifact Provenance](provenance.md) with SLSA Level 3 signing via Cosign and in-toto attestations. Cryptographic verification at build ingestion and deploy time prevents TOCTOU attacks.
3. **Insufficient authorization for regulated industries** -- Mitigated by [Access Control](rbac.md) with SOX-compliant RBAC, granular CRUD permissions, and a four-eyes approval workflow for production deployments.

## Documentation

| Document | Description |
|----------|-------------|
| [Secrets Management](secrets.md) | Secret model, encryption, vault plugin interface, deploy-time resolution |
| [Artifact Provenance](provenance.md) | SLSA Level 3, Cosign signing, in-toto attestations, verification flow |
| [Access Control](rbac.md) | Granular permissions, role bundles, two-tier scoping, approval workflow |

---

## Quick Reference

### Secrets Source Types

| Source | Storage | Resolution | Use Case |
|--------|---------|------------|----------|
| **Internal** | Fernet-encrypted in Pathfinder DB | Decrypted at deploy time by Pathfinder | Teams without external vault |
| **External** | External vault (HashiCorp Vault, AWS SM, GCP SM) | Resolved at deploy time by vault plugin | Enterprise / regulated environments |

### Role Tiers

| Tier | Scope | Example Roles | Assigned Via |
|------|-------|---------------|--------------|
| **System** | Platform-wide | platform-admin, platform-operator, security-auditor, secrets-admin | Group system_roles |
| **Project** | Single project | project-admin, release-manager, developer, viewer | ProjectMembership |

Production-specific behavior (approval workflow, attestation verification) is driven by `Environment.is_production` flag, not by per-environment role assignments.

---

**Supersedes:** This document supersedes the top-level `docs/rbac.md` which describes the original permission model. The new model in [docs/security/rbac.md](rbac.md) replaces owner/contributor/viewer with granular CRUD permissions and role bundles.
