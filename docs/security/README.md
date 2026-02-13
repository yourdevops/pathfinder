# Security & Compliance

These design documents cover three interconnected capabilities: secrets management (protecting sensitive configuration), artifact provenance (proving software supply chain integrity), and role-based access control (enforcing who can do what, where). Together they prepare Pathfinder for regulated industry adoption.

## Threat Model Summary

These documents address three key threats:

1. **Centralized credential risk ("god mode" problem)** -- Mitigated by [Secrets Management](secrets.md) with external vault integration. Production secrets never need to exist in Pathfinder's database. The internal encrypted store serves teams without vault infrastructure; external vault integration is the recommended pattern for production.
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
| **System** | Platform-wide | platform-admin, platform-operator, security-auditor, secrets-admin | `Group.system_roles` field |
| **Project** | Single project | maintainer, release-manager, developer, viewer | `ProjectMembership.project_role` field |

Production-specific behavior (approval workflow, attestation verification) is driven by `Environment.is_production` flag, not by per-environment role assignments.
