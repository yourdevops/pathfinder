# Blueprints - DEPRECATED

!!! Deprecated in favor of [ci-workflows](ci-workflows/README.md) and [templates](templates/README.md) !!!

Blueprints are "golden paths" that define how applications (services) are built and deployed. They contain source code scaffolding, CI configuration, and deployment metadata.

## Overview

An Service Template is a git repository containing:
1. **Source scaffolding**: Dockerfile, application code structure, config files
2. **CI configuration**: Jenkinsfile, GitHub Actions workflow, or build scripts
3. **Template manifest**: `ssp-template.yaml` defining metadata and requirements

When a developer creates an service using a template, Pathfinder:
1. Clones/copies the template contents to the target repository
2. Substitutes variables (service name, project name, etc.)
3. Commits and pushes the result
4. Registers the service with metadata from the manifest

---

## Template Manifest

Every template must include an `ssp-template.yaml` file in the repository root.

### Manifest Format

```yaml
# pathfinder-template.yaml

# Required fields
name: python-k8s-service
description: Python service deployed to Kubernetes

# Source configuration
source:
  # Files/directories to copy (relative to template repo root)
  # If omitted, copies entire repo (excluding pathfinder-template.yaml and .git)
  include:
    - src/
    - Dockerfile
    - Jenkinsfile
    - requirements.txt
  # Files to exclude from copying
  exclude:
    - "*.md"
    - tests/
  # How to handle files when applying to existing repository (optional)
  # If on_copy is omitted, all template files overwrite existing files
  on_copy:
    # Files to delete from target repo (e.g., legacy CI configs)
    delete:
      - .travis.yml
      - circle.yml
    # Files to preserve if they exist (don't touch)
    preserve:
      - src/
      - README.md
      - .env.example
      - docs/*
    # All other template files: overwrite (default behavior)

# CI Configuration
ci:
  type: jenkins                    # jenkins, github-actions, gitlab-ci, none
  # Optional: path to CI config file (for display/documentation)
  config_file: Jenkinsfile

# Deployment Configuration
deploy:
  type: container                  # container, serverless, static
  mechanism: direct                # direct, gitops, pipeline
  required_plugins:                # Plugin types needed for deployment
    - kubernetes

# Metadata
tags:
  - python
  - kubernetes
  - container

# Variable Schema (optional)
# Defines additional variables the template expects beyond built-in ones
variables:
  - name: service_port
    description: Port the service listens on
    type: number
    default: 8080
  - name: replicas
    description: Number of pod replicas
    type: number
    default: 1

# Default Service Configuration (optional)
# Pre-filled values for the wizard
defaults:
  port: 8080
  cpu_request: "100m"
  cpu_limit: "500m"
  memory_request: "128Mi"
  memory_limit: "512Mi"
  health_endpoint: "/health"
```

---

## Template Registration

Blueprints are registered in Pathfinder by providing a git URL. Pathfinder fetches the manifest and stores the metadata.

### Registration Flow

```
1. Admin provides template git URL
   └─ https://github.com/yourdevops/blueprints/python-k8s-service

2. Pathfinder clones repository (shallow)

3. Pathfinder reads pathfinder-template.yaml
   └─ Validates required fields
   └─ Parses all metadata

4. Pathfinder creates Blueprint record
   └─ name: from manifest
   └─ description: from manifest
   └─ source: { type: git, url: ..., ref: main }
   └─ ci_type, deploy_type, etc: from manifest
   └─ required_plugin_types: from manifest

5. Template is now available in projects with compatible environments
```

### Syncing Blueprints

Blueprints can be re-synced to pick up manifest changes:
- Manual: Admin clicks "Sync" on template detail page
- Automatic: Webhook from git provider (optional)
- Scheduled: Periodic sync job (configurable)

---

## Template Availability

An Service Template is available in a Project when at least one Environment in that Project has a Connection matching the template's `required_plugins`.

```
Template: python-k8s-service
  required_plugins: [github, kubernetes]

Project: team-a
  Environment: dev
    connections: [dev-k3s (kubernetes), github-yourdevops (github)]
  Environment: prod
    connections: [prod-eks (kubernetes)]

Result: python-k8s-service is available (at least one env has github and kubernetes)
```
---

## Template Directory Structure

### Example: Python Kubernetes Service

```
python-k8s-service/
├── pathfinder-template.yaml         # Template manifest (required)
├── Dockerfile                # Container build
├── Jenkinsfile               # CI pipeline
├── requirements.txt          # Python dependencies
├── src/
│   ├── __init__.py
│   ├── main.py               # {{ app_name }} references
│   └── config.py
├── k8s/
│   ├── deployment.yaml       # {{ service_handler }}, {{ replicas }}
│   └── service.yaml          # {{ service_port }}
└── README.md                 # Template documentation
```

### Example: Python Lambda

```
python-lambda-vpc/
├── pathfinder-template.yaml
├── Jenkinsfile               # CI: build + package
├── Jenkinsfile.deploy        # CD: terraform apply
├── src/
│   ├── handler.py            # Lambda handler
│   └── requirements.txt
├── terraform/
│   ├── main.tf               # {{ app_name }}, {{ project_name }}
│   ├── variables.tf
│   └── outputs.tf
└── README.md
```

---

### Access Control

| SystemRole | View Blueprints | Register/Edit | Delete |
|------------|----------------|---------------|--------|
| `admin` | Yes (all) | Yes | Yes |
| `operator` | Yes (all) | Yes | No |
| `auditor` | Yes (all, with details) | No | No |
| `user` | Yes (cards only) | No | No |

**Notes:**
- All authenticated users can see template cards (name, description, tags) as baseline access
- Only users with `operator` or `admin` SystemRole can register, sync, or edit blueprints
- Template deletion requires `admin` SystemRole

See [rbac.md](rbac.md) for full permission model documentation.

---

## Common Deploy Types

| Type | Description | Artifact | Common Plugins |
|------|-------------|----------|----------------|
| `container` | Containerized application | Docker image | kubernetes, docker |
| `serverless` | Function/lambda | Zip, JAR, or image | jenkins (for terraform), aws-lambda |
| `static` | Static website/assets | HTML/JS/CSS bundle | s3, cloudfront |

## Common Deploy Mechanisms

| Mechanism | Description | How Pathfinder Deploys |
|-----------|-------------|-----------------|
| `direct` | Pathfinder calls integration API | `kubernetes.apply()`, `docker.run()` |
| `gitops` | Pathfinder commits manifests | Push to gitops repo, ArgoCD syncs |
| `pipeline` | Pathfinder triggers CD pipeline | `jenkins.trigger(job, params)` |
