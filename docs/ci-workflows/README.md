# CI Workflows

A CI Workflow is a versioned, composable build definition that produces an artifact. It defines what happens between a code push and a deployable artifact appearing in a registry. Pathfinder tracks the produced artifact for downstream use and ensures only authorized workflows can produce deployable artifacts.

## What CI Workflows Do Not Do

- Abstract away CI syntax into a proprietary DSL
- Promise cross-CI portability (a GitHub Actions workflow will not auto-convert to Jenkins)
- Replace existing CI systems
- Define or execute deployments—that is an Environment and Deploy Plugin concern
- Manage CI secrets
- Manage service secrets

## Documentation

| Document | Description |
|----------|-------------|
| [Workflow Definition](workflow-definition.md) | Fields, runtimes, step ordering rules |
| [Steps Catalog](steps-catalog.md) | Step definitions, metadata, batteries-included repos |
| [Step Outputs](step-outputs.md) | Output wiring between steps, engine-native mechanisms |
| [Versioning](versioning.md) | Semver model, draft/publish lifecycle, revocation |
| [Build Authorization](build-authorization.md) | Manifest identification, verification flow, security model |
| [Build Lifecycle](build-lifecycle.md) | Triggering, artifact discovery, build records |
| [Plugin Interface](plugin-interface.md) | CI engine implementations, manifest generation |
| [Logging](logging.md) | Audited entities, sync operation logs |

---

## Quick Reference

### Entity Prefix Mapping

| Entity | Prefix | Example Filename |
|--------|--------|------------------|
| CIWorkflow | `ci-` | `ci-python-uv.yml` |
| DeploymentMethod | `cd-` | `cd-helm.yml` |

### Build Verification States

| State | Meaning | Non-Production | Production |
|-------|---------|----------------|------------|
| **Verified** | Manifest hash matches authorized version | Deploy | Deploy |
| **Draft** | Manifest hash matches draft version | Deploy | Blocked |
| **Unauthorized** | Hash doesn't match any known version | Blocked | Blocked |

**Note on revoked versions**: Builds recorded as Verified *before* a version is revoked retain their status. The UI displays a warning: "Built with revoked workflow version X.Y.Z." Builds that complete *after* revocation are marked Unauthorized.
