"""Tests for the setup/unlock sequence.

The unlock flow is a one-time operation. SiteConfiguration.setup_completed
(DB) is the single source of truth. The token file is just a first-run
ownership proof.
"""

from unittest.mock import patch

import pytest
from django.urls import reverse

from core.models import SiteConfiguration


@pytest.fixture()
def secrets_dir(tmp_path):
    """Provide a temp secrets dir and patch get_secrets_dir to use it."""
    d = tmp_path / "secrets"
    d.mkdir()
    with patch("core.utils.get_secrets_dir", return_value=d):
        yield d


@pytest.fixture()
def token_file(secrets_dir):
    """Create a token file in the temp secrets dir."""
    f = secrets_dir / "initialUnlockToken"
    f.write_text("test-token-abc")
    f.chmod(0o400)
    return f


@pytest.fixture(autouse=True)
def _real_setup_state():
    """Override the conftest autouse bypass so setup tests use real behavior."""
    import core.utils

    core.utils._setup_complete = False
    yield
    core.utils._setup_complete = False


# ── is_setup_complete ────────────────────────────────────────────


class TestIsSetupComplete:
    def test_fresh_db_returns_false(self, db):
        from core.utils import is_setup_complete

        assert is_setup_complete() is False

    def test_returns_true_when_flag_set(self, db):
        from core.utils import is_setup_complete

        config = SiteConfiguration.get_instance()
        config.setup_completed = True
        config.save()
        assert is_setup_complete() is True

    def test_stale_token_file_ignored_when_flag_set(self, db, token_file):
        """DB flag wins even if a stale token file exists."""
        from core.utils import is_setup_complete

        config = SiteConfiguration.get_instance()
        config.setup_completed = True
        config.save()
        assert is_setup_complete() is True

    def test_cached_after_first_true(self, db):
        """Once True, subsequent calls skip DB (one-way latch)."""
        from core.utils import is_setup_complete

        config = SiteConfiguration.get_instance()
        config.setup_completed = True
        config.save()

        assert is_setup_complete() is True

        # Flip DB back — cache still returns True (per-worker latch)
        config.setup_completed = False
        config.save()
        assert is_setup_complete() is True


# ── Middleware ───────────────────────────────────────────────────


class TestSetupMiddleware:
    def test_no_redirect_when_setup_complete(self, client, db):
        config = SiteConfiguration.get_instance()
        config.setup_completed = True
        config.save()

        import core.utils

        core.utils._setup_complete = True

        response = client.get("/")
        assert "/setup/" not in response.url

    def test_redirects_to_setup_when_not_complete(self, client, db, token_file):
        response = client.get("/")
        assert response.status_code == 302
        assert reverse("setup:unlock") in response.url


# ── Registration completes setup ─────────────────────────────────


class TestRegistration:
    def test_registration_sets_setup_completed(self, client, db, token_file):
        """Completing registration stores setup_completed=True in DB."""
        session = client.session
        session["unlock_verified"] = True
        session.save()

        response = client.post(
            reverse("setup:unlock"),
            {
                "username": "admin",
                "email": "admin@test.com",
                "password": "AdminPass123!",
                "password_confirm": "AdminPass123!",
            },
        )
        assert response.status_code == 302

        config = SiteConfiguration.get_instance()
        assert config.setup_completed is True

    def test_setup_page_unreachable_after_completion(self, client, db):
        """Once complete, /setup/unlock/ redirects away."""
        config = SiteConfiguration.get_instance()
        config.setup_completed = True
        config.save()

        import core.utils

        core.utils._setup_complete = True

        response = client.get(reverse("setup:unlock"))
        assert response.status_code == 302
        assert "/setup/" not in response.url
