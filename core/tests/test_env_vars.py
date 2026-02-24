"""Tests for environment variable cascade resolution and deployment gate."""

from django.test import TestCase

from core.models import Environment, Project, Service
from core.utils import check_deployment_gate, resolve_env_vars


class TestResolveEnvVars(TestCase):
    """Test resolve_env_vars cascade logic."""

    def setUp(self):
        self.project = Project.objects.create(
            name="acme",
            env_vars=[
                {"key": "DATABASE_URL", "value": "postgres://dev", "lock": False, "description": "DB connection"},
                {"key": "LOG_FORMAT", "value": "json", "lock": True, "description": "Logging format"},
            ],
        )
        self.service = Service.objects.create(
            project=self.project,
            name="order-service",
            env_vars=[
                {"key": "REDIS_URL", "value": "redis://cache:6379", "lock": False, "description": "Redis URL"},
                {"key": "DATABASE_URL", "value": "postgres://service-db", "lock": False, "description": ""},
            ],
        )
        self.environment = Environment.objects.create(
            project=self.project,
            name="staging",
            env_vars=[
                {"key": "DATABASE_URL", "value": "postgres://staging-db", "lock": False, "description": ""},
                {"key": "LOG_LEVEL", "value": "info", "lock": False, "description": "Log verbosity"},
            ],
        )

    def test_project_only_context(self):
        """Resolve with just a project: returns PTF_PROJECT (system, locked) + project vars."""
        result = resolve_env_vars(self.project)

        # Should have PTF_PROJECT + 2 project vars = 3
        keys = {v["key"] for v in result}
        self.assertIn("PTF_PROJECT", keys)
        self.assertIn("DATABASE_URL", keys)
        self.assertIn("LOG_FORMAT", keys)

        # Verify PTF_PROJECT
        ptf_project = next(v for v in result if v["key"] == "PTF_PROJECT")
        self.assertEqual(ptf_project["value"], "acme")
        self.assertEqual(ptf_project["source"], "system")
        self.assertTrue(ptf_project["lock"])
        self.assertEqual(ptf_project["locked_by"], "system")

        # Verify project var source
        db_url = next(v for v in result if v["key"] == "DATABASE_URL")
        self.assertEqual(db_url["source"], "project")

    def test_project_environment_context(self):
        """Resolve with project + environment: PTF_PROJECT + PTF_ENVIRONMENT + merged vars."""
        result = resolve_env_vars(self.project, environment=self.environment)

        keys = {v["key"] for v in result}
        self.assertIn("PTF_PROJECT", keys)
        self.assertIn("PTF_ENVIRONMENT", keys)
        self.assertNotIn("PTF_SERVICE", keys)  # No service provided

        # Environment overrides project value for DATABASE_URL
        db_url = next(v for v in result if v["key"] == "DATABASE_URL")
        self.assertEqual(db_url["value"], "postgres://staging-db")
        self.assertEqual(db_url["source"], "environment")

        # Environment adds LOG_LEVEL
        log_level = next(v for v in result if v["key"] == "LOG_LEVEL")
        self.assertEqual(log_level["value"], "info")
        self.assertEqual(log_level["source"], "environment")

    def test_full_cascade(self):
        """Resolve with project + service + environment: all 3 PTF_* + merged cascade."""
        result = resolve_env_vars(self.project, service=self.service, environment=self.environment)

        keys = {v["key"] for v in result}
        self.assertIn("PTF_PROJECT", keys)
        self.assertIn("PTF_SERVICE", keys)
        self.assertIn("PTF_ENVIRONMENT", keys)
        self.assertIn("DATABASE_URL", keys)
        self.assertIn("LOG_FORMAT", keys)
        self.assertIn("REDIS_URL", keys)
        self.assertIn("LOG_LEVEL", keys)

        # PTF_SERVICE value
        ptf_service = next(v for v in result if v["key"] == "PTF_SERVICE")
        self.assertEqual(ptf_service["value"], "order-service")
        self.assertEqual(ptf_service["source"], "system")

        # PTF_ENVIRONMENT value
        ptf_env = next(v for v in result if v["key"] == "PTF_ENVIRONMENT")
        self.assertEqual(ptf_env["value"], "staging")

        # DATABASE_URL should be environment value (overrides service which overrides project)
        db_url = next(v for v in result if v["key"] == "DATABASE_URL")
        self.assertEqual(db_url["value"], "postgres://staging-db")
        self.assertEqual(db_url["source"], "environment")

        # REDIS_URL from service
        redis = next(v for v in result if v["key"] == "REDIS_URL")
        self.assertEqual(redis["value"], "redis://cache:6379")
        self.assertEqual(redis["source"], "service")

    def test_locked_var_prevents_override(self):
        """Project locks a var, service tries to override: project's locked value wins."""
        # LOG_FORMAT is locked at project level
        self.service.env_vars.append({"key": "LOG_FORMAT", "value": "text", "lock": False, "description": ""})
        self.service.save()

        result = resolve_env_vars(self.project, service=self.service)

        log_format = next(v for v in result if v["key"] == "LOG_FORMAT")
        self.assertEqual(log_format["value"], "json")  # Project's locked value
        self.assertEqual(log_format["source"], "project")
        self.assertTrue(log_format["lock"])

    def test_locked_var_at_service_level(self):
        """Service locks a var, environment tries to override: service's locked value wins."""
        self.service.env_vars = [
            {"key": "REDIS_URL", "value": "redis://locked:6379", "lock": True, "description": "Locked Redis"},
        ]
        self.service.save()

        self.environment.env_vars.append(
            {"key": "REDIS_URL", "value": "redis://env-override:6379", "lock": False, "description": ""}
        )
        self.environment.save()

        result = resolve_env_vars(self.project, service=self.service, environment=self.environment)

        redis = next(v for v in result if v["key"] == "REDIS_URL")
        self.assertEqual(redis["value"], "redis://locked:6379")
        self.assertEqual(redis["source"], "service")
        self.assertTrue(redis["lock"])

    def test_system_vars_always_locked(self):
        """PTF_* vars cannot be overridden by any level."""
        # Try to override PTF_PROJECT at service level
        self.service.env_vars.append({"key": "PTF_PROJECT", "value": "hacked", "lock": False, "description": ""})
        self.service.save()

        result = resolve_env_vars(self.project, service=self.service)

        ptf_project = next(v for v in result if v["key"] == "PTF_PROJECT")
        self.assertEqual(ptf_project["value"], "acme")  # System value, not overridden
        self.assertEqual(ptf_project["source"], "system")

    def test_description_inheritance(self):
        """Description inherited from upstream unless downstream provides its own."""
        # Service overrides DATABASE_URL value but has empty description
        # -> should inherit project's description
        result = resolve_env_vars(self.project, service=self.service)

        db_url = next(v for v in result if v["key"] == "DATABASE_URL")
        self.assertEqual(db_url["value"], "postgres://service-db")
        self.assertEqual(db_url["description"], "DB connection")  # Inherited from project

        # Now set service description
        self.service.env_vars = [
            {"key": "DATABASE_URL", "value": "postgres://service-db", "lock": False, "description": "Service DB"},
        ]
        self.service.save()

        result = resolve_env_vars(self.project, service=self.service)
        db_url = next(v for v in result if v["key"] == "DATABASE_URL")
        self.assertEqual(db_url["description"], "Service DB")  # Service's own description

    def test_empty_value_not_lockable(self):
        """A variable with empty value should have lock=False regardless of stored value."""
        self.project.env_vars = [
            {"key": "EMPTY_VAR", "value": "", "lock": True, "description": "Should not be lockable"},
        ]
        self.project.save()

        result = resolve_env_vars(self.project)

        empty_var = next(v for v in result if v["key"] == "EMPTY_VAR")
        self.assertFalse(empty_var["lock"])  # Empty value cannot be locked

    def test_results_sorted_by_key(self):
        """Output is alphabetically sorted by key."""
        result = resolve_env_vars(self.project, service=self.service, environment=self.environment)

        keys = [v["key"] for v in result]
        self.assertEqual(keys, sorted(keys))


class TestCheckDeploymentGate(TestCase):
    """Test check_deployment_gate logic."""

    def test_all_values_present_passes(self):
        """Returns (True, []) when all vars have values."""
        resolved = [
            {
                "key": "PTF_PROJECT",
                "value": "acme",
                "lock": True,
                "description": "",
                "source": "system",
                "locked_by": "system",
            },
            {
                "key": "DATABASE_URL",
                "value": "postgres://db",
                "lock": False,
                "description": "",
                "source": "project",
                "locked_by": None,
            },
        ]
        is_ready, empty_vars = check_deployment_gate(resolved)
        self.assertTrue(is_ready)
        self.assertEqual(empty_vars, [])

    def test_empty_value_blocks(self):
        """Returns (False, list of empty vars) with correct source info."""
        resolved = [
            {
                "key": "PTF_PROJECT",
                "value": "acme",
                "lock": True,
                "description": "",
                "source": "system",
                "locked_by": "system",
            },
            {
                "key": "DATABASE_URL",
                "value": "",
                "lock": False,
                "description": "",
                "source": "project",
                "locked_by": None,
            },
            {
                "key": "SECRET_KEY",
                "value": "",
                "lock": False,
                "description": "",
                "source": "service",
                "locked_by": None,
            },
        ]
        is_ready, empty_vars = check_deployment_gate(resolved)
        self.assertFalse(is_ready)
        self.assertEqual(len(empty_vars), 2)

        empty_keys = {v["key"] for v in empty_vars}
        self.assertIn("DATABASE_URL", empty_keys)
        self.assertIn("SECRET_KEY", empty_keys)

    def test_system_vars_excluded_from_gate(self):
        """System PTF_* vars are never flagged as empty."""
        resolved = [
            {
                "key": "PTF_PROJECT",
                "value": "acme",
                "lock": True,
                "description": "",
                "source": "system",
                "locked_by": "system",
            },
            {
                "key": "PTF_SERVICE",
                "value": "svc",
                "lock": True,
                "description": "",
                "source": "system",
                "locked_by": "system",
            },
            {
                "key": "DATABASE_URL",
                "value": "postgres://db",
                "lock": False,
                "description": "",
                "source": "project",
                "locked_by": None,
            },
        ]
        is_ready, empty_vars = check_deployment_gate(resolved)
        self.assertTrue(is_ready)
        self.assertEqual(empty_vars, [])
