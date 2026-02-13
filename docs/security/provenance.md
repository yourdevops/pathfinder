# SLSA Provenance and Artifact Signing

Artifact provenance proves where a software artifact came from, how it was built, and that it has not been tampered with. Pathfinder uses SLSA (Supply-chain Levels for Software Artifacts) Level 3 as its provenance target: CI generates signed attestations using Cosign, and Pathfinder verifies them before allowing deployment. This is a second verification layer complementing the existing manifest hash verification in [build-authorization.md](../ci-workflows/build-authorization.md).

## Two-Layer Verification Model

Pathfinder uses two complementary verification layers to ensure deployment integrity:

**Layer 1 -- Manifest Hash Verification (existing).** Proves the CI pipeline definition is authorized. A build is deployable only if its manifest hash matches an authorized `CIWorkflowVersion`. This layer answers: "Was this build produced by an approved pipeline?" See [build-authorization.md](../ci-workflows/build-authorization.md) for the full verification flow.

**Layer 2 -- Artifact Attestation (new).** Proves the artifact itself was produced by a verified build and has not been modified since. A signed SLSA provenance attestation is attached to the artifact at build time and cryptographically verified before deployment. This layer answers: "Is this artifact exactly what the approved pipeline produced?"

Both layers must pass for production deployment. Non-production environments can opt out of Layer 2 via per-environment configuration.

## Responsibilities Split

Pathfinder follows a CI-generates/Pathfinder-verifies model. The responsibilities are clearly separated:

**CI engine is responsible for:**
- Generating the SLSA provenance predicate (build inputs, builder identity, timestamps)
- Signing the artifact with Cosign using the configured KMS backend
- Attaching signed attestations to the OCI registry alongside the image

**Pathfinder is responsible for:**
- Declaring the expected attestation format (`https://pathfinder.dev/ci-workflow/v1` build type)
- Fetching and verifying attestations after build completion
- Storing verification metadata on the Build record
- Re-verifying attestations at deploy time before deployment execution
- Enforcing attestation policy per environment

Pathfinder never signs artifacts -- it is the verification and policy enforcement point.

## Signing Toolchain

| Component | Specification | Notes |
|-----------|---------------|-------|
| **Signing tool** | Cosign 3.x (current stable) | `--type slsaprovenance1` for v1.0 format. Cosign 3 defaults to new bundle format, trusted-root configuration, and OCI 1.1 referrers for attestation storage. |
| **KMS backends** | `hashivault://` (Vault Transit), `awskms://` (AWS KMS), `gcpkms://` (GCP KMS), or keyless via Sigstore | Customer-managed keys for enterprise compliance; keyless for internal/development use. |
| **Timestamping** | DigiCert TSA via `--timestamp-server-url=http://timestamp.digicert.com` | RFC 3161 timestamps for long-term verifiability. |
| **Transparency log** | Rekor with `--tlog-upload=false` by default | Opt-in per environment. Many regulated enterprises cannot publish artifact signatures to a public transparency log. |
| **Minimum versions** | Cosign >= 3.x, timestamp-authority >= 1.2.8 | The timestamp-authority version is required for DigiCert TSA certificate chain compatibility (see [sigstore/cosign#3632](https://github.com/sigstore/cosign/issues/3632)). |

**Important:** Use `--type slsaprovenance1` (with the `1` suffix) to generate SLSA v1.0 format. The deprecated `--type slsaprovenance` (without the suffix) generates SLSA v0.2 format.

## Attestation Format

Attestations use the in-toto v1 statement format with the SLSA v1.0 provenance predicate, wrapped in a DSSE (Dead Simple Signing Envelope):

```
DSSE Envelope:
  payloadType: "application/vnd.in-toto+json"
  payload: (base64-encoded Statement)
  signatures: [...]

Statement:
  _type: "https://in-toto.io/Statement/v1"
  subject:
    - name: <image-ref>
      digest: {sha256: <digest>}
  predicateType: "https://slsa.dev/provenance/v1"
  predicate:
    buildDefinition:
      buildType: "https://pathfinder.dev/ci-workflow/v1"
      externalParameters:
        workflow: <workflow-name>
        version: <workflow-version>
        source:
          uri: "git+<repo-url>"
          digest: {sha1: <commit-sha>}
      resolvedDependencies: [...]
    runDetails:
      builder:
        id: <ci-engine-url>
      metadata:
        invocationId: <ci-run-id>
        startedOn: <timestamp>
        finishedOn: <timestamp>
```

The `buildType` is Pathfinder-specific (`https://pathfinder.dev/ci-workflow/v1`) so Pathfinder can identify its own attestations among any others attached to the image. The `externalParameters` captures exactly the inputs that determine the build. The `source.digest.sha1` must match the Build record's `commit_sha`.

## CI Step -- Sign and Attest

A batteries-included CI step is provided in the steps library for the `package` phase. It runs after build and before notification.

- **Step name:** "Sign and Attest"
- **Location:** `security/sign-attest/action.yml` in the steps repository
- **Phase:** `package`
- **x-pathfinder metadata:** `runtimes: {"*": "*"}` (runtime-agnostic -- works with any build)
- **Inputs:**
  - `image_ref` (required) -- full image reference with digest
  - `kms_key` (optional) -- KMS URI for signing key; keyless if omitted
  - `rekor_upload` (optional, default: `false`) -- upload to Rekor transparency log
- **Actions:** Install Cosign, generate SLSA provenance predicate JSON, sign image, attach provenance attestation to OCI registry
- **Requirements:** `COSIGN_KEY` environment variable or OIDC token for keyless signing

See [steps-catalog.md](../ci-workflows/steps-catalog.md) for step metadata conventions and the batteries-included repository structure.

## SBOM Attestation

SBOM (Software Bill of Materials) is a companion attestation attached alongside provenance. It provides a machine-readable inventory of components in the artifact.

- **Format:** CycloneDX JSON (recommended). CycloneDX is better suited for security-focused use cases -- it natively supports VEX (Vulnerability Exploitability eXchange), component hashing, and dependency trees. Cosign natively supports `--type cyclonedx` for attestation.
- **Generation:** Syft or Trivy in a separate CI step, or combined with the sign-and-attest step.
- **Attachment:** Attached to the same OCI image as a separate attestation: `cosign attest --type cyclonedx --predicate sbom.json <image-ref>`
- **Pathfinder indexing:** Pathfinder can index SBOM metadata (component count, vulnerability summary) from the attestation. Full SBOM analysis and vulnerability management is out of scope.
- **SPDX compatibility:** SPDX is not excluded. Teams needing SPDX for licensing compliance can add a second generation step -- both formats can coexist as separate attestations on the same image.

## Pathfinder Verification Flow

Pathfinder verifies attestations at two points to prevent TOCTOU (time-of-check-to-time-of-use) attacks.

### Point 1: Build Ingestion (after build webhook)

1. Build record created from CI webhook (existing flow per [build-lifecycle.md](../ci-workflows/build-lifecycle.md))
2. Pathfinder fetches attestation from OCI registry: `cosign verify-attestation --type slsaprovenance1 --key <public-key> <image-ref>`
3. Parse the in-toto statement and extract the SLSA provenance predicate
4. Verify `buildType` matches `https://pathfinder.dev/ci-workflow/v1`
5. Verify `source.digest.sha1` matches `Build.commit_sha`
6. Store verification metadata on the Build record (see Build Model Extensions below)
7. If attestation is missing or invalid: `attestation_verified = false`. This does not block build recording -- it only blocks production deployment.

### Point 2: Deploy Time (before deployment execution)

1. Check if the target environment has attestation verification enabled (opt-in per environment, enabled by default for production)
2. Re-verify the attestation on the specific image being deployed -- not a cached result from build ingestion
3. If verification fails: deployment is blocked with a clear error message identifying the failure reason
4. This prevents TOCTOU attacks: an attestation could have been revoked or the image replaced between build and deploy

No separate verification occurs at promotion boundaries. The deploy-time verification at the target environment is sufficient -- promotion between environments does not require its own verification step.

## Environment Configuration

Attestation verification is configurable per environment:

- **`require_attestation_verification`**: boolean, default `true`
- **When enabled:** Deployments must have `attestation_verified = true` on the Build record AND pass re-verification at deploy time
- **When disabled:** Deployments proceed without attestation check (useful for development environments)
- **Recommended configuration:**
  - Production: enabled (mandatory)
  - Staging: enabled (catch issues before production)
  - Development: disabled (reduce friction during iteration)

This setting is independent of the existing `verification_status` checks from build authorization. A production deployment requires both: `verification_status = verified` (Layer 1) AND `attestation_verified = true` (Layer 2).

## Build Model Extensions

The following fields are added to the Build model to track provenance verification. These complement the existing `verification_status` (Verified/Draft/Unauthorized) from build authorization.

```
Build (extensions):
  - attestation_verified: bool (default false)
  - attestation_digest: string (nullable -- SHA-256 of the attestation payload)
  - signer_identity: string (nullable -- key ID or OIDC subject)
  - provenance_bundle_ref: string (nullable -- OCI reference to attestation)
  - timestamp_verified: bool (default false)
  - sbom_attached: bool (default false)
```

The `attestation_verified` field is set during build ingestion (Point 1) and re-checked at deploy time (Point 2). The `signer_identity` records which key or OIDC identity signed the attestation, providing audit trail visibility. The `provenance_bundle_ref` stores the OCI reference to the attestation for direct retrieval during re-verification.

## Supply Chain Trust Model

The end-to-end trust chain for artifact integrity in Pathfinder:

```
Branch Protection -> Authorized Workflow Version -> Manifest Hash -> Artifact Attestation
```

Each layer verifies the output of the previous layer:

1. **Branch protection** on the steps repository prevents unauthorized changes to CI step definitions (enforced at registration per [steps-catalog.md](../ci-workflows/steps-catalog.md))
2. **Authorized workflow version** ensures only reviewed, published workflow versions are used (per [build-authorization.md](../ci-workflows/build-authorization.md))
3. **Manifest hash** verification proves the CI pipeline that ran matches an authorized version
4. **Artifact attestation** proves the artifact was produced by that verified pipeline and has not been tampered with

Individual CI steps are NOT signed. Branch protection on the steps repository (required reviews, no force push, no direct push) provides equivalent trust. Adding step signatures would require a complex key management system for step authors with minimal added security over the existing chain.

## Addressing "Artifact Signing Absent" Finding

The deployment review ([review.md](../deployments/review.md)) identified a critical gap: "no cryptographic guarantee that the artifact deployed to production is the same one that passed tests in staging."

This design directly addresses that finding:

- Every artifact gets a signed SLSA provenance attestation at build time via the Sign and Attest CI step
- Attestations are cryptographically verified at both build ingestion and deploy time
- The promotion chain now has cryptographic integrity: **build -> sign with Cosign -> attach SLSA provenance -> verify at each deployment**
- Re-verification at deploy time prevents TOCTOU attacks where an image could be replaced after initial verification

Combined with the existing manifest hash verification (Layer 1), Pathfinder provides two independent cryptographic guarantees: the pipeline was authorized, and the artifact it produced is authentic.
