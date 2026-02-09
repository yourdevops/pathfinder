# Plugin Interface

## CICapableMixin

```python
class CICapableMixin:
    def manifest_id(self, workflow: CIWorkflow) -> str:
        """Return manifest identifier (e.g., .github/workflows/ci-python-uv.yml)"""

    def extract_manifest_id(self, run_data: dict) -> str | None:
        """Extract identifier from CI run data. Returns None if not Pathfinder-managed."""

    def get_manifest_id_pattern(self) -> re.Pattern:
        """Regex pattern for validation."""

    def fetch_manifest_content(
        self, config: dict, repo_name: str, manifest_id: str, commit_sha: str
    ) -> str | None:
        """Fetch manifest file content from repo at a specific commit.
        Returns None if file not found at that commit."""
```

## GitHub Actions Implementation

```python
MANIFEST_ID_PATTERN = re.compile(r'^\.github/workflows/ci-[a-z0-9][a-z0-9-]*\.yml$')

def manifest_id(self, workflow: CIWorkflow) -> str:
    return f".github/workflows/ci-{workflow.name}.yml"
```

## Jenkins Implementation

```python
MANIFEST_ID_PATTERN = re.compile(r'^ci-[a-z0-9][a-z0-9-]*\.jenkinsfile$')

def manifest_id(self, workflow: CIWorkflow) -> str:
    return f"ci-{workflow.name}.jenkinsfile"
```

## Future: CD Support

DeploymentMethod (when CI-engine-based) follows the same pattern:

```
ci-{workflow.name}.yml      -> CIWorkflow (Build records)
cd-{method.name}.yml        -> DeploymentMethod (Deployment records)
```

Same `manifest_id` field, plugin methods, and authorization model. Different entity types.
