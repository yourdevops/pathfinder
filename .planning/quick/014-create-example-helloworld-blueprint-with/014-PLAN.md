---
phase: quick
plan: 014
type: execute
wave: 1
depends_on: []
files_modified:
  - blueprints/python-helloworld/ssp-template.yaml
  - blueprints/python-helloworld/Containerfile
  - blueprints/python-helloworld/.github/workflows/build.yml
  - blueprints/python-helloworld/src/main.py
  - blueprints/python-helloworld/src/requirements.txt
  - blueprints/python-helloworld/deploy/docker-compose.yml
  - blueprints/python-helloworld/deploy/k8s/deployment.yaml
  - blueprints/python-helloworld/deploy/k8s/service.yaml
  - blueprints/python-helloworld/README.md
autonomous: true

must_haves:
  truths:
    - "Blueprint can be registered in DevSSP via git URL"
    - "Manifest is valid and parseable by sync_blueprint task"
    - "Container builds successfully with Containerfile"
    - "App responds to health check at /health"
  artifacts:
    - path: "blueprints/python-helloworld/ssp-template.yaml"
      provides: "Blueprint manifest"
      contains: "name: python-helloworld"
    - path: "blueprints/python-helloworld/Containerfile"
      provides: "Multi-stage container build"
      contains: "FROM python"
    - path: "blueprints/python-helloworld/src/main.py"
      provides: "Flask HTTP server with health endpoint"
      contains: "/health"
  key_links:
    - from: "ssp-template.yaml"
      to: "deploy/docker-compose.yml"
      via: "required_plugins reference"
      pattern: "docker"
---

<objective>
Create an example "python-helloworld" blueprint in the `blueprints/` directory at the project root.

Purpose: Provide a working example blueprint that demonstrates DevSSP's blueprint format and can be used for testing service creation. This blueprint showcases multi-target deployment (docker, podman, kubernetes) using a simple Python Flask app.

Output: Complete blueprint directory ready to be pushed to a separate repo and registered as a blueprint in DevSSP.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@docs/blueprints.md

Blueprint Model Limitation:
The Blueprint model stores a single `deploy_plugin` field (line 371 of core/models.py).
For multi-target support, we set deploy_plugin to "docker" (most common) but include
deployment manifests for kubernetes as well. The manifest's deploy.required_plugins
array can list multiple plugins for documentation purposes.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create blueprint manifest and application code</name>
  <files>
    blueprints/python-helloworld/ssp-template.yaml
    blueprints/python-helloworld/Containerfile
    blueprints/python-helloworld/src/main.py
    blueprints/python-helloworld/src/requirements.txt
  </files>
  <action>
Create the core blueprint files:

1. **ssp-template.yaml** - Blueprint manifest following docs/blueprints.md format:
   - name: python-helloworld
   - description: Simple Python Flask app with multi-target deployment
   - source.include: src/, Containerfile, deploy/, .github/
   - source.exclude: README.md, *.md
   - ci.type: github-actions
   - ci.config_file: .github/workflows/build.yml
   - deploy.type: container
   - deploy.mechanism: direct
   - deploy.required_plugins: [docker] (docker as primary, note in description that k8s manifests included)
   - tags: [python, flask, container, docker, kubernetes]
   - variables: service_port (number, default 8080), replicas (number, default 1)
   - defaults: port=8080, health_endpoint=/health

2. **Containerfile** - Multi-stage build:
   - Stage 1: python:3.12-slim as builder, install requirements
   - Stage 2: python:3.12-slim runtime, copy from builder
   - Create non-root user (appuser, uid 1000)
   - EXPOSE 8080
   - HEALTHCHECK using curl or wget to /health
   - CMD ["python", "main.py"]

3. **src/main.py** - Flask app:
   - Import Flask
   - Get PORT from env (default 8080)
   - Root endpoint "/" returns {"message": "Hello, World!", "service": "{{ service_name }}"}
   - Health endpoint "/health" returns {"status": "healthy"}
   - Run with host="0.0.0.0"

4. **src/requirements.txt**:
   - flask==3.0.0
   - gunicorn==21.2.0

Note: Use {{ variable }} syntax for template variables (service_name, service_port).
  </action>
  <verify>
    - All files exist in blueprints/python-helloworld/
    - ssp-template.yaml is valid YAML with required fields
    - Containerfile uses multi-stage build pattern
    - main.py has /health endpoint
  </verify>
  <done>Blueprint manifest and core application files created with proper structure</done>
</task>

<task type="auto">
  <name>Task 2: Create deployment manifests and CI workflow</name>
  <files>
    blueprints/python-helloworld/.github/workflows/build.yml
    blueprints/python-helloworld/deploy/docker-compose.yml
    blueprints/python-helloworld/deploy/k8s/deployment.yaml
    blueprints/python-helloworld/deploy/k8s/service.yaml
  </files>
  <action>
Create deployment configurations for multiple targets:

1. **.github/workflows/build.yml** - GitHub Actions workflow:
   - name: Build and Push Container
   - on: push (tags: v*, branches: main)
   - jobs.build:
     - runs-on: ubuntu-latest
     - steps: checkout, login to ghcr.io, build with buildx, push
     - Use GITHUB_TOKEN for ghcr.io auth
     - Tag with git sha and latest (or version tag)
   - Use template vars: {{ service_name }} for image name

2. **deploy/docker-compose.yml** - Docker/Podman compose:
   - version: "3.8"
   - services.{{ service_name }}:
     - image: ghcr.io/{{ github_org }}/{{ service_name }}:latest
     - ports: ["{{ service_port }}:8080"]
     - environment: PORT=8080
     - healthcheck: test curl /health
     - restart: unless-stopped

3. **deploy/k8s/deployment.yaml** - Kubernetes deployment:
   - apiVersion: apps/v1
   - kind: Deployment
   - metadata.name: {{ service_name }}
   - spec.replicas: {{ replicas }}
   - spec.template.spec.containers[0]:
     - name: {{ service_name }}
     - image: ghcr.io/{{ github_org }}/{{ service_name }}:latest
     - ports.containerPort: 8080
     - env: PORT=8080
     - livenessProbe: httpGet /health
     - readinessProbe: httpGet /health
     - resources: requests 100m/128Mi, limits 500m/512Mi
     - securityContext: runAsNonRoot, runAsUser 1000

4. **deploy/k8s/service.yaml** - Kubernetes service:
   - apiVersion: v1
   - kind: Service
   - metadata.name: {{ service_name }}
   - spec.type: ClusterIP
   - spec.ports: port={{ service_port }}, targetPort=8080
   - spec.selector: app={{ service_name }}
  </action>
  <verify>
    - All deployment files exist
    - YAML files are valid syntax
    - Template variables use {{ var }} format consistently
  </verify>
  <done>CI workflow and deployment manifests for docker, podman, and kubernetes created</done>
</task>

<task type="auto">
  <name>Task 3: Create README documentation</name>
  <files>
    blueprints/python-helloworld/README.md
  </files>
  <action>
Create documentation for the blueprint:

**README.md** structure:
1. Title: Python Helloworld Blueprint
2. Description: What this blueprint provides
3. Quick Start:
   - How to register in DevSSP (git URL)
   - Template variables available
4. Local Development:
   - Build: `podman build -f Containerfile -t helloworld .`
   - Run: `podman run -p 8080:8080 helloworld`
   - Test: `curl localhost:8080/health`
5. Deployment Options:
   - Docker/Podman: reference docker-compose.yml
   - Kubernetes: reference k8s/ directory
6. Template Variables table:
   - service_name: Name of the service
   - service_port: External port (default 8080)
   - replicas: K8s replicas (default 1)
   - github_org: GitHub organization for image registry
7. Directory Structure explanation
8. License: MIT

Keep it concise and practical.
  </action>
  <verify>
    - README.md exists and is valid markdown
    - Contains build/run instructions
    - Documents template variables
  </verify>
  <done>Blueprint documentation complete</done>
</task>

</tasks>

<verification>
1. Directory structure matches expected layout:
   ```
   blueprints/python-helloworld/
   ├── ssp-template.yaml
   ├── Containerfile
   ├── .github/workflows/build.yml
   ├── src/
   │   ├── main.py
   │   └── requirements.txt
   ├── deploy/
   │   ├── docker-compose.yml
   │   └── k8s/
   │       ├── deployment.yaml
   │       └── service.yaml
   └── README.md
   ```
2. `cat blueprints/python-helloworld/ssp-template.yaml` shows valid manifest
3. Containerfile follows best practices (multi-stage, non-root user)
</verification>

<success_criteria>
- All 9 files created in blueprints/python-helloworld/
- Manifest parseable by YAML parser
- Blueprint can be registered in DevSSP (structure matches docs/blueprints.md)
- Deploy manifests support docker-compose and kubernetes
</success_criteria>

<output>
After completion, create `.planning/quick/014-create-example-helloworld-blueprint-with/014-SUMMARY.md`
</output>
