"""Tests for IntegrationConnection.set_config / get_config encrypt/decrypt roundtrip."""

import pytest

from core.models import IntegrationConnection


@pytest.fixture()
def connection(db):
    return IntegrationConnection.objects.create(
        name="test-conn",
        plugin_name="github",
        status="active",
    )


class TestSetGetConfig:
    def test_roundtrip_mixed_fields(self, connection):
        """Sensitive fields are encrypted, non-sensitive stay in plain config, get_config merges both."""
        connection.set_config(
            {
                "base_url": "https://scm.yourdevops.me",
                "access_token": "ghp_abc123",
                "org_name": "myorg",
            }
        )
        connection.save()
        connection.refresh_from_db()

        result = connection.get_config()
        assert result["base_url"] == "https://scm.yourdevops.me"
        assert result["access_token"] == "ghp_abc123"
        assert result["org_name"] == "myorg"

    def test_sensitive_fields_not_in_plain_config(self, connection):
        """Token/password fields must not appear in the unencrypted config JSON."""
        connection.set_config(
            {
                "base_url": "https://scm.yourdevops.me",
                "access_token": "ghp_abc123",
                "private_key": "-----BEGIN RSA-----",
            }
        )

        assert "access_token" not in connection.config
        assert "private_key" not in connection.config
        assert "base_url" in connection.config

    def test_no_sensitive_fields_skips_encryption(self, connection):
        """When all fields are non-sensitive, config_encrypted stays None."""
        connection.set_config({"base_url": "https://scm.yourdevops.me", "org_name": "myorg"})

        assert connection.config_encrypted is None
        assert connection.get_config() == {"base_url": "https://scm.yourdevops.me", "org_name": "myorg"}

    def test_all_sensitive_fields(self, connection):
        """When all fields are sensitive, plain config is empty."""
        connection.set_config({"access_token": "tok", "client_secret": "sec"})

        assert connection.config == {}
        assert connection.config_encrypted is not None

        result = connection.get_config()
        assert result == {"access_token": "tok", "client_secret": "sec"}

    def test_empty_config(self, connection):
        """Empty dict produces empty config and no encryption."""
        connection.set_config({})

        assert connection.config == {}
        assert connection.config_encrypted is None
        assert connection.get_config() == {}

    def test_empty_sensitive_value_stays_plain(self, connection):
        """Empty string values for sensitive field names are not encrypted."""
        connection.set_config({"access_token": "", "base_url": "https://scm.yourdevops.me"})

        # Empty token value stays in plain config (the `if value` guard in set_config)
        assert "access_token" in connection.config
        assert connection.config_encrypted is None

    def test_overwrite_preserves_roundtrip(self, connection):
        """Calling set_config twice replaces previous values cleanly."""
        connection.set_config({"access_token": "old_token"})
        connection.save()

        connection.set_config({"access_token": "new_token", "base_url": "https://scm.yourdevops.me"})
        connection.save()
        connection.refresh_from_db()

        result = connection.get_config()
        assert result["access_token"] == "new_token"
        assert result["base_url"] == "https://scm.yourdevops.me"

    def test_unknown_plugin_treats_all_as_nonsensitive(self, connection):
        """If plugin is not registered, no fields are encrypted."""
        connection.plugin_name = "nonexistent-plugin"
        connection.set_config({"access_token": "tok", "url": "https://ci.yourdevops.me"})

        assert connection.config == {"access_token": "tok", "url": "https://ci.yourdevops.me"}
        assert connection.config_encrypted is None
