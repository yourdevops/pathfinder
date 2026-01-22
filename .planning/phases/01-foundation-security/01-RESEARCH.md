# Phase 1: Foundation & Security - Research

**Researched:** 2026-01-22
**Domain:** Django authentication, RBAC, audit logging, dark mode UI
**Confidence:** HIGH

## Summary

This research covers the technical foundation for implementing Phase 1: Foundation & Security in DevSSP. The phase requires implementing an unlock flow, custom user/group management with SystemRoles, session-based authentication, audit logging, and a dark mode UI.

The standard approach for Django 6.x projects is to use a custom user model extending `AbstractUser` from the start (before any migrations), implement groups as a separate model (not Django's built-in groups which lack the flexibility needed for SystemRoles), use `django-auditlog` for change tracking, and integrate Tailwind CSS with the `class` strategy for dark mode.

Key decisions are locked: no welcome page after unlock, user management as first destination after setup, modal dialogs for user creation, dedicated group detail pages, and summary-only audit entries without diffs.

**Primary recommendation:** Create a custom User model extending AbstractUser with UUID public ID, implement Group and GroupMembership as custom models, use django-auditlog for audit logging, and integrate django-tailwind with class-based dark mode.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 6.0.1 | Web framework | Already installed, latest stable |
| django-tailwind | 3.8+ | Tailwind CSS integration | Official Django-Tailwind bridge with hot reload |
| django-auditlog | 3.0+ | Audit logging | Best balance of automation and efficiency for Django |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| secrets (stdlib) | Python 3.13 | Secure token generation | Unlock token generation |
| htmx | 2.0+ | Dynamic UI updates | Modal forms, partial page updates (later phases) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| django-auditlog | django-simple-history | simple-history stores full object state (more storage), auditlog stores only changes (more efficient) |
| django-tailwind | Manual Tailwind setup | Manual requires more configuration, django-tailwind provides hot reload and better DX |
| Custom audit model | DIY signals | DIY requires manual implementation, prone to missing cases |

**Installation:**
```bash
pip install django-tailwind[cookiecutter,honcho,reload] django-auditlog
```

## Architecture Patterns

### Recommended Project Structure
```
devssp/
├── devssp/              # Project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                # Core app (users, groups, audit, setup)
│   ├── models.py        # User, Group, GroupMembership, AuditLog
│   ├── views/
│   │   ├── setup.py     # Unlock flow views
│   │   ├── auth.py      # Login/logout views
│   │   ├── users.py     # User management views
│   │   ├── groups.py    # Group management views
│   │   └── audit.py     # Audit log views
│   ├── forms.py
│   ├── admin.py
│   ├── middleware.py    # Setup check middleware
│   └── templates/
│       └── core/
│           ├── setup/   # Unlock and registration templates
│           ├── auth/    # Login/logout templates
│           ├── users/   # User management templates
│           ├── groups/  # Group management templates
│           └── audit/   # Audit log templates
├── theme/               # django-tailwind theme app
│   ├── static_src/
│   │   └── src/
│   │       └── styles.css
│   ├── templates/
│   │   └── base.html
│   └── tailwind.config.js
└── secrets/             # Auto-generated secrets (gitignored)
    ├── initialUnlockToken
    └── encryption.key
```

### Pattern 1: Custom User Model with UUID Public ID
**What:** Extend AbstractUser with a separate UUID field for external references while keeping integer PK for DB efficiency
**When to use:** New Django projects that need URL-safe identifiers without exposing sequential IDs
**Example:**
```python
# Source: Django 6.0 docs + community best practice
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """Custom user model with UUID for external references."""
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=[('active', 'Active'), ('inactive', 'Inactive')],
        default='active'
    )
    source = models.CharField(
        max_length=20,
        choices=[('local', 'Local'), ('oidc', 'OIDC'), ('ldap', 'LDAP')],
        default='local'
    )
    external_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'core_user'
```

### Pattern 2: Custom Group Model (Not Django Groups)
**What:** Implement groups as a custom model to support SystemRoles and future OIDC/LDAP sync
**When to use:** When Django's built-in Group model lacks required features
**Example:**
```python
# Source: Project RBAC requirements
class Group(models.Model):
    """Custom group model with SystemRole support."""
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.CharField(max_length=63, unique=True)  # DNS-compatible
    description = models.TextField(blank=True)
    source = models.CharField(
        max_length=20,
        choices=[('local', 'Local'), ('oidc', 'OIDC'), ('ldap', 'LDAP')],
        default='local'
    )
    external_id = models.CharField(max_length=255, blank=True, null=True)
    system_roles = models.JSONField(default=list)  # ['admin', 'operator', 'auditor']
    status = models.CharField(
        max_length=20,
        choices=[('active', 'Active'), ('inactive', 'Inactive')],
        default='active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_group'

class GroupMembership(models.Model):
    """Many-to-many relationship between User and Group."""
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_memberships'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_group_membership'
        unique_together = ['group', 'user']
```

### Pattern 3: Setup State Management
**What:** Use a simple flag-based approach to track setup completion
**When to use:** Single-instance applications with one-time setup
**Example:**
```python
# Source: Project requirements (FNDN-01 through FNDN-06)
from pathlib import Path
import secrets

def get_unlock_token_path():
    """Return path to unlock token file."""
    return Path(settings.BASE_DIR) / 'secrets' / 'initialUnlockToken'

def is_setup_complete():
    """Check if initial setup has been completed."""
    # Setup is complete when unlock token no longer exists
    return not get_unlock_token_path().exists()

def generate_unlock_token():
    """Generate a secure unlock token on fresh install."""
    token_path = get_unlock_token_path()
    if not token_path.exists():
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token = secrets.token_urlsafe(32)
        token_path.write_text(token)
    return token_path.read_text()

def verify_unlock_token(provided_token):
    """Verify the provided token matches the stored one."""
    token_path = get_unlock_token_path()
    if not token_path.exists():
        return False
    return secrets.compare_digest(token_path.read_text().strip(), provided_token.strip())

def complete_setup():
    """Delete the unlock token after successful setup."""
    token_path = get_unlock_token_path()
    if token_path.exists():
        token_path.unlink()
```

### Pattern 4: Setup Middleware
**What:** Middleware that redirects to unlock page when setup is incomplete
**When to use:** Enforce setup flow before any other access
**Example:**
```python
# Source: Common Django pattern
from django.shortcuts import redirect
from django.urls import reverse

class SetupMiddleware:
    """Redirect to setup if not complete, redirect away if complete."""

    SETUP_URLS = ['/setup/', '/setup/unlock/', '/setup/register/']
    EXEMPT_URLS = ['/static/', '/favicon.ico']

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Allow static files
        if any(path.startswith(url) for url in self.EXEMPT_URLS):
            return self.get_response(request)

        setup_complete = is_setup_complete()
        is_setup_url = any(path.startswith(url) for url in self.SETUP_URLS)

        if not setup_complete and not is_setup_url:
            # Setup not complete, redirect to unlock
            return redirect('setup:unlock')

        if setup_complete and is_setup_url:
            # Setup complete, redirect away from setup pages
            return redirect('auth:login')

        return self.get_response(request)
```

### Pattern 5: Session-based Authentication with Remember Me
**What:** Django's session framework with configurable expiry
**When to use:** Standard web authentication with persistent sessions
**Example:**
```python
# Source: Django 6.0 sessions documentation
# settings.py
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 86400  # 1 day default
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True  # In production
SESSION_SAVE_EVERY_REQUEST = True  # Reset expiry on activity

# In login view
def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password']
            )
            if user:
                login(request, user)
                # Handle "remember me"
                if form.cleaned_data.get('remember_me'):
                    request.session.set_expiry(604800)  # 7 days
                else:
                    request.session.set_expiry(86400)  # 1 day
                return redirect('users:list')
    # ...
```

### Anti-Patterns to Avoid
- **Using Django's built-in Group model:** Too limited for SystemRoles and lacks OIDC/LDAP sync fields
- **Storing setup state in database:** Chicken-and-egg problem on fresh install; use filesystem
- **Hardcoding unlock token:** Must be generated securely per installation
- **Changing AUTH_USER_MODEL after migrations:** Causes complex schema issues; do it first
- **Using random module for tokens:** Use secrets module for cryptographic randomness

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Audit logging | Custom signals/decorators | django-auditlog | Handles edge cases, bulk updates, M2M tracking |
| Tailwind integration | Manual PostCSS setup | django-tailwind | Hot reload, proper Django template integration |
| Password hashing | Custom hashing | Django's auth system | Constantly updated with best practices |
| CSRF protection | Manual tokens | Django's CSRF middleware | Battle-tested, handles edge cases |
| Session management | Custom cookies | Django sessions | Secure, configurable, well-tested |
| Secure token generation | random module | secrets module | Cryptographically secure |

**Key insight:** Django's auth system and established packages handle security concerns that are easy to get wrong. The audit logging in particular has many edge cases (bulk operations, M2M changes, middleware context) that custom solutions typically miss.

## Common Pitfalls

### Pitfall 1: Changing User Model After Migrations
**What goes wrong:** Schema becomes inconsistent, ForeignKeys break
**Why it happens:** Developer starts with default User, realizes custom is needed later
**How to avoid:** Always create custom User model before first `makemigrations`
**Warning signs:** `AUTH_USER_MODEL` change after `0001_initial.py` exists

### Pitfall 2: Referencing User Model Directly
**What goes wrong:** Code breaks when AUTH_USER_MODEL changes
**Why it happens:** Using `from django.contrib.auth.models import User` directly
**How to avoid:** Always use `settings.AUTH_USER_MODEL` in models or `get_user_model()` at runtime
**Warning signs:** Direct `User` imports in models.py

### Pitfall 3: Storing Secrets in Database Before Setup
**What goes wrong:** Can't access database on fresh install
**Why it happens:** Trying to store unlock token in Settings model
**How to avoid:** Use filesystem for bootstrap secrets, database for runtime config
**Warning signs:** Database errors on fresh install

### Pitfall 4: Forgetting Audit Middleware
**What goes wrong:** Audit entries have no actor (user who made change)
**Why it happens:** django-auditlog needs middleware to capture request.user
**How to avoid:** Always add `auditlog.middleware.AuditlogMiddleware` to MIDDLEWARE
**Warning signs:** Empty actor fields in audit log

### Pitfall 5: Insecure Token Comparison
**What goes wrong:** Timing attacks can leak token information
**Why it happens:** Using `==` for token comparison
**How to avoid:** Always use `secrets.compare_digest()` for token comparison
**Warning signs:** Direct string comparison with sensitive values

### Pitfall 6: Dark Mode Flash on Page Load
**What goes wrong:** Page briefly shows light mode before JavaScript runs
**Why it happens:** Theme preference stored in localStorage, loaded after render
**How to avoid:** Add inline script in `<head>` that sets class before render, or use server-side preference
**Warning signs:** White flash on page load in dark mode

## Code Examples

Verified patterns from official sources:

### Unlock Flow View
```python
# Source: Project requirements + Django patterns
from django.shortcuts import render, redirect
from django.views import View
from .forms import UnlockForm, AdminRegistrationForm
from .utils import verify_unlock_token, complete_setup

class UnlockView(View):
    """Handle unlock token entry."""
    template_name = 'core/setup/unlock.html'

    def get(self, request):
        return render(request, self.template_name, {'form': UnlockForm()})

    def post(self, request):
        form = UnlockForm(request.POST)
        if form.is_valid():
            if verify_unlock_token(form.cleaned_data['token']):
                # Store verified state in session for registration step
                request.session['unlock_verified'] = True
                return redirect('setup:register')
            form.add_error('token', 'Invalid unlock token')
        return render(request, self.template_name, {'form': form})


class AdminRegistrationView(View):
    """Handle first admin account creation."""
    template_name = 'core/setup/register.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('unlock_verified'):
            return redirect('setup:unlock')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, self.template_name, {'form': AdminRegistrationForm()})

    def post(self, request):
        form = AdminRegistrationForm(request.POST)
        if form.is_valid():
            # Create user
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )

            # Create admins group with admin SystemRole
            admins_group, _ = Group.objects.get_or_create(
                name='admins',
                defaults={
                    'description': 'System administrators',
                    'system_roles': ['admin']
                }
            )

            # Add user to admins group
            GroupMembership.objects.create(group=admins_group, user=user)

            # Complete setup (delete token)
            complete_setup()

            # Clear session and log in user
            request.session.flush()
            login(request, user)

            # Redirect to user management per requirements
            return redirect('users:list')

        return render(request, self.template_name, {'form': form})
```

### Audit Log Registration
```python
# Source: django-auditlog documentation
# At bottom of models.py
from auditlog.registry import auditlog

auditlog.register(User, exclude_fields=['password', 'last_login'])
auditlog.register(Group)
auditlog.register(GroupMembership)
```

### SystemRole Permission Check
```python
# Source: Project RBAC requirements
def has_system_role(user, role):
    """Check if user has a specific SystemRole through any group."""
    if not user.is_authenticated:
        return False
    return GroupMembership.objects.filter(
        user=user,
        group__status='active',
        group__system_roles__contains=[role]
    ).exists()

def get_user_system_roles(user):
    """Get all SystemRoles for a user."""
    if not user.is_authenticated:
        return ['user']  # Baseline for all authenticated

    roles = set(['user'])  # Implicit user role
    memberships = GroupMembership.objects.filter(
        user=user,
        group__status='active'
    ).select_related('group')

    for membership in memberships:
        roles.update(membership.group.system_roles)

    return list(roles)
```

### Dark Mode Tailwind Configuration
```javascript
// Source: Tailwind CSS documentation
// tailwind.config.js
module.exports = {
  darkMode: 'class',
  content: [
    '../templates/**/*.html',
    '../../**/templates/**/*.html',
  ],
  theme: {
    extend: {
      colors: {
        // Dark mode palette
        'dark-bg': '#0f172a',        // slate-900
        'dark-surface': '#1e293b',   // slate-800
        'dark-border': '#334155',    // slate-700
        'dark-text': '#f1f5f9',      // slate-100
        'dark-muted': '#94a3b8',     // slate-400
      }
    }
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}
```

### Base Template with Dark Mode
```html
<!-- Source: Tailwind CSS + django-tailwind documentation -->
{% load tailwind_tags %}
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}DevSSP{% endblock %}</title>
    {% tailwind_css %}
    <!-- Prevent dark mode flash -->
    <script>
        // Always dark mode per requirements
        document.documentElement.classList.add('dark');
    </script>
</head>
<body class="bg-dark-bg text-dark-text min-h-screen">
    {% block content %}{% endblock %}
</body>
</html>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Django default User | Custom AbstractUser from start | Django 1.5+ (2013) | Flexibility for future changes |
| UUIDv4 primary keys | Integer PK + UUID public field | 2024-2025 | 40-90% better write performance |
| Manual Tailwind | django-tailwind package | 2023+ | Hot reload, better integration |
| Custom audit signals | django-auditlog | Mature | Handles edge cases automatically |
| SESSION_EXPIRE_AT_BROWSER_CLOSE | set_expiry() per login | Long-standing | Per-user control |

**Deprecated/outdated:**
- Using `AbstractBaseUser` for simple customizations: Use `AbstractUser` unless you need to change the username field
- Manual Tailwind CSS compilation: django-tailwind handles this
- Storing setup state in database: Use filesystem for bootstrap

## Open Questions

Things that couldn't be fully resolved:

1. **Audit log human-readable format**
   - What we know: django-auditlog stores JSON changes, not human-readable summaries
   - What's unclear: Best way to generate "John created user Alice" format
   - Recommendation: Create a template tag or model method that formats LogEntry into human-readable text

2. **Modal form pattern for HTMX**
   - What we know: Multiple approaches exist (django-htmx-modal-forms, manual patterns)
   - What's unclear: Which approach best fits the project's needs
   - Recommendation: Start with simple manual approach per spookylukey/django-htmx-patterns; add library if needed

3. **Navigation visibility logic**
   - What we know: Nav items based on permissions (UIUX-01)
   - What's unclear: How to efficiently compute permissions for nav rendering
   - Recommendation: Add context processor that computes user roles once per request

## Sources

### Primary (HIGH confidence)
- [Django 6.0 Custom Authentication](https://docs.djangoproject.com/en/6.0/topics/auth/customizing/) - Custom user model, AUTH_USER_MODEL, authentication backends
- [Django 6.0 Sessions](https://docs.djangoproject.com/en/6.0/topics/http/sessions/) - Session configuration, set_expiry()
- [django-auditlog Documentation](https://django-auditlog.readthedocs.io/en/latest/usage.html) - Model registration, middleware, field tracking
- [Tailwind CSS Dark Mode](https://tailwindcss.com/docs/dark-mode) - Class-based dark mode strategy
- [Python secrets Module](https://docs.python.org/3/library/secrets.html) - Secure token generation

### Secondary (MEDIUM confidence)
- [django-tailwind GitHub](https://github.com/timonweb/django-tailwind) - Installation, configuration, development workflow
- [Django-HTMX Modal Patterns](https://github.com/spookylukey/django-htmx-patterns/blob/master/modals.rst) - Modal dialog implementation

### Tertiary (LOW confidence)
- WebSearch results on UUIDv7 vs UUIDv4 performance - Specific performance numbers may vary by workload
- Community posts on remember-me implementation - Multiple valid approaches exist

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Based on installed Django version, official docs, well-established packages
- Architecture: HIGH - Standard Django patterns, verified with official documentation
- Pitfalls: HIGH - Common issues documented in official Django docs and community resources
- UI patterns: MEDIUM - Tailwind integration well-documented, HTMX modal patterns less standardized

**Research date:** 2026-01-22
**Valid until:** 2026-02-22 (30 days - stable domain, mature frameworks)
