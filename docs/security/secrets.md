# Secrets Management

Secrets are sensitive configuration values (API keys, database passwords, private keys) that require stronger protection than standard environment variables. Pathfinder treats secrets as a separate namespace from env vars -- managed independently, merged at deploy time. Secret values are write-only: once set, they can never be read back through any interface.

## Secret Model

A Secret belongs to a project and is optionally scoped to a specific environment:

```
Secret:
  - id: UUID
  - project: FK Project
  - environment: FK Environment (nullable -- project-wide if null)
  - name: string (DNS-compatible, unique within project+environment scope)
  - encrypted_value: binary (Fernet-encrypted, nullable for external secrets)
  - source: enum (internal, external)
  - external_ref: string (nullable -- vault path, ARN, or secret ID for external secrets)
  - description: text
  - created_by, updated_by: user reference
  - created_at, updated_at: datetime
```

**Scope inheritance:** Project-wide secrets (`environment=null`) are available in all environments. Environment-specific secrets override project-wide secrets of the same name. This parallels the env var cascade defined in [Environment Binding](../deployments/environment-binding.md).

**Naming:** Secret names follow DNS label format (lowercase alphanumeric and hyphens, max 63 characters). Names are unique within a project+environment scope. The same name can exist at project-wide and environment-specific levels -- the environment-specific value takes precedence at deploy time.

## Encryption Architecture

Internal secrets use Fernet symmetric encryption via the existing `core/encryption.py` infrastructure:

- Same system-wide key sourced from `PTF_ENCRYPTION_KEY` env var or `secrets/encryption.key` file
- `encrypt_config` / `decrypt_config` functions already handle Fernet operations; the Secret model extends this pattern for individual secret values
- Fernet provides authenticated encryption (AES-128-CBC with HMAC-SHA256), ensuring both confidentiality and integrity. AES-128 is the Fernet specification's choice, not a Pathfinder decision -- the `cryptography` library's Fernet implementation defines this.
- Key rotation is a documented future concern -- not designed in detail now (per locked decision)

External secrets store no encrypted value in Pathfinder. The `external_ref` field holds the vault path or cloud secret ARN, and resolution happens at deploy time via the vault plugin.

## Write-Only Semantics

Secret values are never visible once set -- not to admins, not via API, not in any UI:

- **UI shows:** secret name, source, description, last updated timestamp, and a masked placeholder
- **Available actions:** create, overwrite (replace value), delete
- **No "reveal" or "copy" functionality** exists by design
- Internal resolution happens only inside deploy plugins at deploy time -- never exposed through views or API
- `__repr__` and `__str__` on the Secret model must never include the value
- Audit log records secret mutations (created, updated, deleted) but never logs the value itself

## Deploy-Time Resolution

Secrets flow into deployments through a parallel snapshot mechanism alongside env vars:

1. **Snapshot creation.** When a deployment is created, the deploy snapshot stores `secret_refs_snapshot`: a list of `{name, source, ref}` dicts. This is parallel to `env_vars_snapshot` but never stores actual values.

2. **Resolution at deploy time.** The deploy plugin resolves references immediately before execution:
   - **Internal secrets:** Pathfinder decrypts via `core/encryption.py` and passes resolved values to the plugin
   - **External secrets:** The plugin's `SecretsCapableMixin.resolve_secrets()` fetches values from the external vault

3. **Target-specific injection.**
   - For Kubernetes targets: the plugin creates an ExternalSecret CR or injects secrets via an init container. Plaintext is never stored in Pathfinder for external secrets.
   - For Docker direct targets: the plugin resolves values and passes them as environment variables to the container.

4. **Merge order.** The final container environment is: env vars (visible, from `env_vars_snapshot`) + secrets (resolved). Secrets override env vars of the same name.

## Plugin Interface -- SecretsCapableMixin

External vault integration follows the established plugin mixin pattern (see `CICapableMixin` and `DeployCapableMixin` in `plugins/base.py`):

```
SecretsCapableMixin:
  resolve_secrets(config, secret_refs) -> dict[name, value]
    # Resolve external secret references to actual values at deploy time.
    # Called by deploy pipeline, not exposed to UI/API.
    # config: plugin connection configuration (vault URL, auth method, namespace)
    # secret_refs: list of {name, external_ref} dicts from the snapshot

  validate_secret_ref(config, external_ref) -> bool
    # Validate that an external secret reference is accessible.
    # Called when a user creates or updates an external secret.
    # Returns True if the reference resolves, False otherwise.

  list_available_secrets(config, path) -> list[str]
    # List available secrets at a path in the external vault.
    # Used by the UI for autocomplete/browsing when configuring external secrets.
    # Returns a list of secret names or paths available at the given path.
```

Target implementations: HashiCorp Vault plugin, AWS Secrets Manager plugin, GCP Secret Manager plugin. The interface is generic enough to support all three without provider-specific methods.

## External Vault Integration Pattern

An external vault plugin follows the same architecture as existing plugins:

- Plugin subclasses `BasePlugin` + `SecretsCapableMixin` (same pattern as `CICapableMixin`)
- Connection config stores vault URL, auth method, namespace/region
- `resolve_secrets()` is called at deploy time by the deploy pipeline -- values are never cached in Pathfinder
- For Kubernetes targets: the plugin can generate ExternalSecret resources instead of resolving values directly, delegating secret injection to the External Secrets Operator running in the cluster
- For Docker direct targets: the plugin resolves values and passes them as environment variables to the container

## Access Control

Secret operations are governed by the granular permission model defined in [Access Control](rbac.md):

- Secret CRUD permissions are part of the standard resource permission set (`create`, `read`, `update`, `delete` on the `secret` resource type)
- `secrets-admin` system role enables cross-project secret management
- Project roles determine secret access within a project scope:
  - `maintainer`: read secret names and metadata (no secret write -- maintainers administer members and settings, not resources)
  - `release-manager`: read secret names and metadata
  - `developer`: create and update secrets within their project
  - `viewer`: see secret names and metadata only (never values -- write-only semantics apply to all roles)
- The `read` permission on secrets grants visibility of names, metadata, and source -- never the encrypted value

## Addressing the "God Mode" Problem

This design directly mitigates the centralized credential risk in the platform-as-executor pattern:

- **External vault integration** means production secrets never need to exist in Pathfinder's database. The external vault remains the source of truth, and Pathfinder only holds references.
- **Internal store is a stepping stone**, not the recommended production pattern. It serves teams without external vault infrastructure. The recommended path for production workloads is external vault integration.
- **Credential scoping:** External vault connections are per-environment, limiting blast radius. A compromised staging vault connection cannot access production secrets.
- **Write-only semantics** mean even a compromised Pathfinder UI cannot reveal secret values. The UI never requests decryption; only the deploy plugin does at execution time.
- **Last-moment resolution:** The deploy plugin resolves secrets immediately before container execution, minimizing the window during which plaintext values exist in memory.
