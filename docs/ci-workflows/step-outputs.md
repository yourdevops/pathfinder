# Step Outputs

Steps can produce outputs that downstream steps consume as inputs. Pathfinder tracks output declarations for change detection and relies on CI-engine-native mechanisms for runtime data flow.

## Output Declaration

Steps declare outputs in their CI-native metadata file. During repository sync, Pathfinder parses these alongside inputs to populate the Catalog.

```yaml
# GitHub Actions example (action.yml)
outputs:
  image-ref:
    description: Full image reference with tag
    value: ${{ steps.meta.outputs.tags }}
  image-digest:
    description: Image digest (sha256)
    value: ${{ steps.push.outputs.digest }}
```

### Tracked Attributes

| Attribute | Change Impact |
|-----------|---------------|
| Output added | Non-breaking |
| Output removed | Breaking (downstream steps may depend on it) |
| Output renamed | Breaking (treated as remove + add) |

Output changes are classified as **interface changes** and trigger warning badges on affected workflows (see [Change Detection](steps-catalog.md#change-detection)).

## Output Wiring

When composing a workflow, step inputs can reference outputs from earlier steps. A wired input uses a reference instead of a static value:

| Input Type | Example `input_config` Value |
|------------|------------------------------|
| Static value | `"Dockerfile.prod"` |
| Output reference | `{"$ref": "package-docker.image-ref"}` |

The reference format is `<step_slug>.<output_name>`. The workflow composer validates that:

1. The referenced step appears **before** the consuming step in workflow order
2. The output name exists in the referenced step's declared outputs
3. No circular references exist (guaranteed by ordering constraint)

## Engine-Native Mechanisms

Each CI engine has its own runtime mechanism for passing data between steps. The CI Plugin translates output references into the correct engine-native syntax during [Manifest Generation](steps-catalog.md#manifest-generation).

### GitHub Actions

GitHub Actions uses a file-based output mechanism within a single job. Steps write key-value pairs to `$GITHUB_OUTPUT` and downstream steps read them via the `steps` context.

**Setting an output (in the step implementation):**

```bash
echo "image-ref=ghcr.io/org/app:sha-abc123" >> "$GITHUB_OUTPUT"
```

**Consuming an output (in the generated manifest):**

```yaml
steps:
  - name: Package Docker Image
    id: package-docker
    uses: org/ci-steps/package/docker@abc123
    with:
      image-name: ghcr.io/org/app

  - name: Security Scan
    id: security-scan
    uses: org/ci-steps/scan@def456
    with:
      image-ref: ${{ steps.package-docker.outputs.image-ref }}
```

The CI Plugin assigns each step an `id` derived from the step slug and resolves `$ref` entries to `${{ steps.<id>.outputs.<name> }}` expressions.

**Multiline outputs** use a delimiter syntax:

```bash
{
  echo 'report<<EOF'
  cat scan-results.json
  echo EOF
} >> "$GITHUB_OUTPUT"
```

The delimiter string must not appear on its own line within the value.

**Constraints:**

| Limit | Value |
|-------|-------|
| Output size per job | 1 MB |
| Total output size per workflow run | 50 MB |
| Size calculation | UTF-16 encoding |
| Step `id` required | Yes, for output referencing |
| Secrets in outputs | Auto-redacted, not sent to GitHub Actions |

### GitLab CI

GitLab CI passes data between jobs using **dotenv artifact reports**. The producing job writes variables to a `.env` file and declares it as an artifact. Downstream jobs receive the variables as environment variables.

**Setting an output:**

```yaml
build-job:
  stage: build
  script:
    - echo "IMAGE_REF=registry.io/app:1.0" >> build.env
  artifacts:
    reports:
      dotenv: build.env
```

**Consuming an output:**

```yaml
test-job:
  stage: test
  needs: [build-job]
  script:
    - echo "$IMAGE_REF"
```

The CI Plugin translates output references into dotenv variable names, generates the `artifacts:reports:dotenv` block on the producing job, and adds the appropriate `needs` or `dependencies` entry on the consuming job.

**Controlling variable reception:**

| Configuration | Effect |
|---------------|--------|
| `needs: [build-job]` | Receives dotenv variables (default) |
| `needs: [{job: build-job, artifacts: true}]` | Explicitly receives |
| `needs: [{job: build-job, artifacts: false}]` | Does not receive |
| `dependencies: []` | Does not receive from any job |

**Constraints:**

| Limit | Value |
|-------|-------|
| Dotenv file size | 5 KB |
| Variable format | `KEY=VALUE`, one per line |
| Multiline values | Not supported |
| Variable substitution | Not supported |
| Encoding | UTF-8 only |
| Empty lines / comments | Not allowed |
| Duplicate keys | Last definition wins |
| Scope | Available in `script` only, not in `rules` or pipeline config |
| Security | Downloadable from pipeline details page |

### Bitbucket Pipelines

Bitbucket uses **output variables** declared on the step and written to a special file path.

**Setting an output:**

```yaml
pipelines:
  default:
    - step:
        name: Build
        script:
          - echo "IMAGE_REF=registry.io/app:1.0" >> $BITBUCKET_PIPELINES_VARIABLES_PATH
        output-variables:
          - IMAGE_REF
```

**Consuming an output:**

```yaml
    - step:
        name: Test
        script:
          - echo "$IMAGE_REF"
```

The CI Plugin adds output names to the `output-variables` list on the producing step and ensures the step script writes to `$BITBUCKET_PIPELINES_VARIABLES_PATH`.

**Constraints:**

| Limit | Value |
|-------|-------|
| Variables per pipeline | 50 |
| Total size (all shared variables) | 100 KB (key + value) |
| Variable naming | ASCII letters, digits, underscores; no leading digit |
| Security | Values logged in plain text in subsequent steps |
| Re-run behavior | Variables persist on failure re-runs but not on full pipeline re-runs |

### Jenkins Declarative Pipeline

Jenkins passes data between stages using **environment variable assignment** inside `script {}` blocks. All stages on the same agent share a workspace.

**Setting an output:**

```groovy
stage('Build') {
    steps {
        script {
            env.IMAGE_REF = sh(
                returnStdout: true,
                script: 'make build-image'
            ).trim()
        }
    }
}
```

**Consuming an output:**

```groovy
stage('Test') {
    steps {
        sh "trivy image $IMAGE_REF"
    }
}
```

The CI Plugin translates output references into `env.VARIABLE_NAME` assignments within `script {}` blocks in the producing stage and `${env.VARIABLE_NAME}` references in the consuming stage.

For file-based data transfer across different agents, Jenkins provides `stash`/`unstash`:

```groovy
stage('Build') {
    steps {
        sh 'make build'
        stash includes: '**/target/*.jar', name: 'app'
    }
}
stage('Test') {
    steps {
        unstash 'app'
        sh 'make check'
    }
}
```

**Constraints:**

| Limit | Value |
|-------|-------|
| `env.X` scope | Available in all subsequent stages |
| `env.X` override | Imperative assignments can be overridden; `environment {}` directive cannot |
| `stash` size | Soft limit ~5-100 MB (compressed TAR on controller) |
| `stash` scope | Single pipeline run only |
| Cross-agent | `stash`/`unstash` works; shared workspace does not |
| `returnStdout` | Includes trailing newline; always use `.trim()` |

## Engine Comparison

| Concern | GitHub Actions | GitLab CI | Bitbucket | Jenkins |
|---------|---------------|-----------|-----------|---------|
| Scope | Same job (steps context) | Cross-job (dotenv artifacts) | Cross-step (output-variables) | Cross-stage (`env.X`) |
| Set mechanism | `>> $GITHUB_OUTPUT` | `>> file.env` + `artifacts:reports:dotenv` | `>> $BITBUCKET_PIPELINES_VARIABLES_PATH` | `env.X = sh(returnStdout:true, ...).trim()` |
| Read mechanism | `${{ steps.id.outputs.key }}` | `$VARIABLE_NAME` | `$VARIABLE_NAME` | `$VARIABLE_NAME` |
| Reference style | Expression in YAML | Env var (auto-injected) | Env var (auto-injected) | Env var (auto-injected) |
| Size limit | 1 MB/job | 5 KB dotenv file | 50 vars / 100 KB | No hard limit |
| Multiline support | Delimiter syntax | No | No | Via file I/O |
| Manifest strategy | Reference + SHA pin | Inline generation | Inline generation | Inline generation |

The key difference is that GitHub Actions is the only engine where output references appear as **expressions in the generated YAML**. The other three engines use environment variables that are automatically injected into downstream steps/jobs/stages, so the manifest generator only needs to ensure the producing step writes to the correct location and the variable names are consistent.
