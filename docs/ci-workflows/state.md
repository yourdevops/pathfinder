# Current state

Current build categorization parses workflow `name` field with "CI - " prefix stripping. This is fragile, GitHub-specific, and can't distinguish Pathfinder-managed manifests from developer-added ones. There is no mechanism to verify that a build was produced by an authorized workflow, leaving the deployment path open to artifacts from tampered or unauthorized pipelines.

# Goals

1. Reliably identify Pathfinder-managed manifests across CI engines.
2. Ensure only artifacts produced by authorized workflows are deployable.
3. Maintain an auditable version history of every workflow manifest.
