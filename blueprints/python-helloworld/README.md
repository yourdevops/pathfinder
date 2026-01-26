# Python Helloworld Blueprint

A simple Python Flask application blueprint for DevSSP demonstrating multi-target deployment support.

## Quick Start

### Register in DevSSP

1. Go to **Blueprints** > **Register Blueprint**
2. Enter the git URL for this repository
3. Select an SCM connection (or "None" for public repos)
4. DevSSP will fetch and parse the `ssp-template.yaml` manifest

### Template Variables

When creating a service from this blueprint, you can customize:

| Variable | Description | Default |
|----------|-------------|---------|
| `service_name` | Name of the deployed service | (required) |
| `service_port` | External port for the service | 8080 |
| `replicas` | Kubernetes replicas | 1 |
| `github_org` | GitHub organization for container registry | (required) |

## Local Development

### Build the container

```bash
# Using Podman
podman build -f Containerfile -t helloworld .

# Using Docker
docker build -f Containerfile -t helloworld .
```

### Run locally

```bash
# Using Podman
podman run -p 8080:8080 helloworld

# Using Docker
docker run -p 8080:8080 helloworld
```

### Test endpoints

```bash
# Health check
curl http://localhost:8080/health
# {"status":"healthy"}

# Root endpoint
curl http://localhost:8080/
# {"message":"Hello, World!","service":"{{ service_name }}"}
```

## Deployment Options

### Docker / Podman Compose

```bash
docker-compose -f deploy/docker-compose.yml up -d
```

### Kubernetes

```bash
kubectl apply -f deploy/k8s/deployment.yaml
kubectl apply -f deploy/k8s/service.yaml
```

## Directory Structure

```
python-helloworld/
├── ssp-template.yaml           # DevSSP blueprint manifest
├── Containerfile               # Multi-stage container build
├── .github/
│   └── workflows/
│       └── build.yml           # GitHub Actions CI workflow
├── src/
│   ├── main.py                 # Flask application
│   └── requirements.txt        # Python dependencies
├── deploy/
│   ├── docker-compose.yml      # Docker/Podman compose
│   └── k8s/
│       ├── deployment.yaml     # Kubernetes deployment
│       └── service.yaml        # Kubernetes service
└── README.md                   # This file
```

## License

MIT
