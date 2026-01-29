# Pathfinder - Developer Self-Service Portal

Pathfinder is a lightweight internal developer platform that turns your existing templates and CI/CD into governed, self-service workflows. It gives developers fast golden paths while giving platform teams consistent policy enforcement and audit visibility.

## Quick Start

### Running Locally (without containers)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Rebuild UI
python manage.py tailwind build

# Collect static files
python manage.py collectstatic

# Run database migrations
python manage.py migrate

# Start development server
python manage.py runserver
```

The portal will be available at **http://localhost:8000**

/gsd:quick UI Navigation items arrangement:
Settings item on navbar should lead to a separate page - General settings. The items on the sidebar nav should be replaced with:
1. General (current tab) -- placeholder for general settings page with settings like "Pathfinder Internal/Public URLs"
2. User Management (A separate page with Users, Groups, LDAP/SSO tabs/pages)
3. Audit & Logs
4. API & Tokens
5. Notifications

The previous quick fix created a messy UI in Settings. The Sidebar nav elements of each consecutive layer should replace the previous sidenav items. Not attach another sidebar to an existing sidebar! Also, this new addition and the Projects UI looks ugly -- the padding around items on the page and subsequent pages like "Services/Environments/Members/Settings" is missing, text starts right when the sidebar ends. Use "Users" page as working reference. Additionally:
  - The navigation elements should be present only on sidebar. Remove them from header. In a header, I need only the title and short description.
  - Some icons are GIANT. What the hell?