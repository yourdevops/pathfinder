# DevSSP - Developer Self-Service Portal

DevSSP is a lightweight internal developer platform that turns your existing templates and CI/CD into governed, self-service workflows. It gives developers fast golden paths while giving platform teams consistent policy enforcement and audit visibility.

## Quick Start

### Running Locally (without containers)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py migrate

# Start development server
python manage.py runserver
```

The portal will be available at **http://localhost:8000**
