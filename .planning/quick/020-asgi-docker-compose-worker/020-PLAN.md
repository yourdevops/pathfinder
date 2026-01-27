---
phase: quick
plan: 020
type: execute
wave: 1
depends_on: []
files_modified:
  - devssp/settings.py
  - requirements.txt
  - Dockerfile
  - entrypoint.sh
  - docker-compose.yml
  - .env.example
autonomous: true

must_haves:
  truths:
    - "Web service runs with uvicorn ASGI server"
    - "Worker service runs db_worker in background"
    - "Both services share data/ volume for SQLite"
    - "Database file lives at data/db.sqlite3"
  artifacts:
    - path: "docker-compose.yml"
      provides: "Multi-service orchestration"
    - path: ".env.example"
      provides: "Environment variable template"
  key_links:
    - from: "docker-compose.yml"
      to: "data/"
      via: "volume mount"
    - from: "entrypoint.sh"
      to: "devssp.asgi:application"
      via: "uvicorn command"
---

<objective>
Switch from Gunicorn WSGI to Uvicorn ASGI, move database to data/ directory, and add docker-compose with web + worker services.

Purpose: Enable ASGI support for future async features and provide proper multi-container deployment with background task worker.
Output: Working docker-compose setup with web (uvicorn) and worker (db_worker) services sharing SQLite database.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/STATE.md
@Dockerfile
@entrypoint.sh
@requirements.txt
@devssp/settings.py
@devssp/asgi.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update settings and requirements for ASGI</name>
  <files>devssp/settings.py, requirements.txt</files>
  <action>
1. In settings.py, update DATABASES to use data/ subdirectory:
   ```python
   # Ensure data directory exists
   DATA_DIR = BASE_DIR / 'data'
   DATA_DIR.mkdir(exist_ok=True)

   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.sqlite3',
           'NAME': DATA_DIR / 'db.sqlite3',
       }
   }
   ```

2. In requirements.txt, add uvicorn with standard extras:
   ```
   uvicorn[standard]>=0.34.0
   ```
   Add after the gunicorn entry if present, or in the deployment section.
  </action>
  <verify>
    - grep "DATA_DIR" devssp/settings.py shows data directory setup
    - grep "uvicorn" requirements.txt shows uvicorn dependency
  </verify>
  <done>Settings point to data/db.sqlite3, uvicorn in requirements</done>
</task>

<task type="auto">
  <name>Task 2: Update Dockerfile and entrypoint for ASGI</name>
  <files>Dockerfile, entrypoint.sh</files>
  <action>
1. In entrypoint.sh, replace gunicorn with uvicorn:
   ```bash
   # Start uvicorn (ASGI server)
   echo "Starting uvicorn server..."
   exec uvicorn devssp.asgi:application --host 0.0.0.0 --port 8000 --workers 2
   ```

2. In Dockerfile, no changes needed to the build process. The entrypoint already points to entrypoint.sh which will use uvicorn. Requirements install will pull uvicorn.

3. Keep gunicorn in requirements.txt for flexibility (can be removed later if desired).
  </action>
  <verify>
    - grep "uvicorn" entrypoint.sh shows uvicorn command
    - grep "asgi:application" entrypoint.sh shows ASGI module
  </verify>
  <done>Entrypoint uses uvicorn with ASGI application</done>
</task>

<task type="auto">
  <name>Task 3: Create docker-compose.yml and .env.example</name>
  <files>docker-compose.yml, .env.example</files>
  <action>
1. Create docker-compose.yml:
   ```yaml
   services:
     web:
       build: .
       ports:
         - "8000:8000"
       volumes:
         - ./data:/app/data
       environment:
         - SSP_ENCRYPTION_KEY=${SSP_ENCRYPTION_KEY}
       depends_on:
         - worker
       restart: unless-stopped

     worker:
       build: .
       command: python manage.py db_worker
       volumes:
         - ./data:/app/data
       environment:
         - SSP_ENCRYPTION_KEY=${SSP_ENCRYPTION_KEY}
       restart: unless-stopped
   ```

2. Create .env.example:
   ```
   # SSP Environment Variables

   # Encryption key for sensitive data (required)
   # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   SSP_ENCRYPTION_KEY=
   ```
  </action>
  <verify>
    - cat docker-compose.yml shows web and worker services
    - cat .env.example shows SSP_ENCRYPTION_KEY placeholder
  </verify>
  <done>docker-compose.yml with web+worker services, .env.example with encryption key template</done>
</task>

</tasks>

<verification>
1. pip install uvicorn (in venv) succeeds
2. python manage.py check --deploy (basic checks)
3. data/ directory is created on settings import
4. docker-compose config validates the compose file
</verification>

<success_criteria>
- settings.py uses data/db.sqlite3 path
- uvicorn in requirements.txt
- entrypoint.sh runs uvicorn instead of gunicorn
- docker-compose.yml defines web and worker services
- .env.example documents required environment variables
</success_criteria>

<output>
After completion, create `.planning/quick/020-asgi-docker-compose-worker/020-SUMMARY.md`
</output>
