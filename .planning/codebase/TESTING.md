# Testing Patterns

**Analysis Date:** 2026-01-21

## Current State

This is an early-stage Django project with no existing tests or test infrastructure. This document describes how testing should be implemented based on Django best practices.

## Test Framework

**Runner:**
- Django's built-in test framework (recommended)
- Command: `python manage.py test`
- No third-party test runner currently configured

**Assertion Library:**
- Django's TestCase provides assertion methods
- Standard: `unittest.TestCase` (via Django)

**Alternative Frameworks (Not Currently Used):**
- pytest: Not installed, not configured
- pytest-django: Not available in venv

**Installation for Testing:**
When testing is added, install:
```bash
pip install pytest pytest-django django-test-plus
```

**Run Commands:**
```bash
python manage.py test                    # Run all tests
python manage.py test app_name           # Run tests for specific app
python manage.py test app_name.tests     # Run specific test module
python manage.py test --keepdb           # Keep test database between runs
```

## Test File Organization

**Location:**
- Django default: `app_name/tests.py` (single file) or `app_name/tests/` (directory)
- Recommendation: Use `tests/` directory for clarity when multiple test modules exist

**Naming:**
- Test functions: `test_*.py` or `*_test.py` pattern
- Test classes: `Test*` prefix (e.g., `TestUserModel`, `TestApiView`)
- Test methods: `test_*` prefix

**Structure:**
```
pathfinder/
└── app_name/
    └── tests/
        ├── __init__.py
        ├── test_models.py
        ├── test_views.py
        ├── test_forms.py
        └── test_api.py
```

## Test Structure

**Suite Organization:**

When tests are implemented, use Django's TestCase classes:

```python
from django.test import TestCase, Client
from django.contrib.auth.models import User

class TestUserModel(TestCase):
    """Tests for User model"""

    def setUp(self):
        """Create test fixtures before each test"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def tearDown(self):
        """Clean up after each test"""
        self.user.delete()

    def test_user_creation(self):
        """Test that user can be created"""
        self.assertEqual(self.user.username, 'testuser')
        self.assertTrue(self.user.check_password('testpass123'))
```

**Patterns:**
- Setup: Use `setUp()` method for test fixtures
- Teardown: Use `tearDown()` method for cleanup (Django TestCase handles database rollback)
- Assertions: Use Django TestCase assertion methods

**Key Assertion Methods:**
```python
self.assertEqual(a, b)              # Test equality
self.assertIn(a, b)                 # Test membership
self.assertTrue/assertFalse(x)      # Test boolean
self.assertRaises(Exception)        # Test exceptions
self.assertQuerySetEqual(qs, list)  # Test QuerySets
```

## View Testing

**TestCase Pattern:**
```python
from django.test import TestCase, Client

class TestAdminView(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )

    def test_admin_accessible(self):
        """Test that admin is accessible when logged in"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)

    def test_admin_login_required(self):
        """Test that admin redirects when not logged in"""
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
```

## Database Testing

**Database Isolation:**
- Django TestCase automatically uses transaction rollback
- Each test runs in isolation
- Test database created fresh (configurable with `--keepdb`)

**Fixtures:**
```python
class TestDeployment(TestCase):
    fixtures = ['deployments.json']  # Load JSON fixture

    def test_deployment_exists(self):
        deployment = Deployment.objects.first()
        self.assertIsNotNone(deployment)
```

## Mocking

**Framework:** `unittest.mock` (Python standard library)

**Patterns:**
```python
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase

class TestExternalIntegration(TestCase):

    @patch('myapp.external_service.api_call')
    def test_deployment_with_mocked_api(self, mock_api):
        """Test deployment when external API is mocked"""
        mock_api.return_value = {'status': 'success'}

        result = deploy_container()

        self.assertEqual(result, 'success')
        mock_api.assert_called_once()
```

**What to Mock:**
- External API calls (Docker API, container registries)
- File system operations (when testing without side effects)
- Network requests
- Time-dependent operations

**What NOT to Mock:**
- Database operations (use TestCase database isolation)
- Django core functionality
- Authentication/authorization (test real behavior)
- Template rendering (test real rendering)

## Fixtures and Factories

**Test Data:**

Factory pattern (using factory_boy if installed):
```python
from factory import django

class UserFactory(django.DjangoModelFactory):
    class Meta:
        model = User

    username = 'testuser'
    email = 'test@example.com'

# Usage
user = UserFactory()
user_list = UserFactory.create_batch(5)
```

**Location:**
- When added: `app_name/tests/factories.py` or `tests/factories.py`
- Currently: No factories exist

## Coverage

**Requirements:** Not enforced
- No coverage targets currently set
- Recommendation: Aim for >80% coverage on critical paths

**View Coverage (when test framework added):**
```bash
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Generate HTML report
```

## CI/CD Test Integration

**Dockerfile:**
The Dockerfile does not currently run tests. When tests are added:

```bash
# Add to Dockerfile before deployment
RUN python manage.py test --noinput

# Or as separate test stage
FROM base as test
RUN python manage.py test --noinput
```

## Test Types

**Unit Tests:**
- Scope: Individual model methods, utility functions
- Approach: Fast, isolated, use setUp/tearDown
- Location: `tests/test_models.py`, `tests/test_forms.py`

**Integration Tests:**
- Scope: API endpoints, database interactions, multi-layer flows
- Approach: Use TestCase (includes database), test full request/response
- Location: `tests/test_views.py`, `tests/test_api.py`

**End-to-End Tests:**
- Framework: Selenium (not currently used)
- Scope: Full wizard workflows, browser testing
- Not yet implemented; consider when UI testing needed

## Test Data Management

**Database State:**
- Use TransactionTestCase for tests needing preserved state
- Use TestCase (default) for automatic rollback per test

**Test Users:**
```python
def setUp(self):
    self.admin = User.objects.create_superuser(
        username='admin',
        password='admin123',
        email='admin@test.com'
    )
    self.user = User.objects.create_user(
        username='user',
        password='user123',
        email='user@test.com'
    )
```

## Future Testing Implementation

**Priority Order:**
1. Model tests (critical business logic)
2. View/API tests (public interfaces)
3. Form validation tests
4. Integration tests (end-to-end flows)
5. Coverage measurement and enforcement

**Recommended Test Setup:**

1. Install testing dependencies:
   ```bash
   pip install pytest pytest-django coverage factory-boy
   ```

2. Create pytest configuration (`pytest.ini`):
   ```ini
   [pytest]
   DJANGO_SETTINGS_MODULE = pathfinder.settings
   python_files = test_*.py
   addopts = --cov --cov-report=html
   ```

3. Create test structure:
   ```
   app_name/
   └── tests/
       ├── __init__.py
       ├── conftest.py          # pytest fixtures
       ├── test_models.py
       ├── test_views.py
       └── factories.py         # test data generation
   ```

4. Create `.coveragerc` for coverage configuration:
   ```ini
   [run]
   source = .
   omit = */tests/*, */migrations/*, */venv/*

   [report]
   exclude_lines =
       pragma: no cover
       def __repr__
       raise AssertionError
       raise NotImplementedError
       if __name__ == .__main__.:
   ```

---

*Testing analysis: 2026-01-21*
