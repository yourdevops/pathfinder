from django.db import models


class SiteConfiguration(models.Model):
    """
    Singleton model for site-wide configuration settings.

    Use SiteConfiguration.get_instance() to access the configuration.
    """

    setup_completed = models.BooleanField(
        default=False,
        help_text="Set once during initial unlock. Prevents re-entering the setup wizard.",
    )
    external_url = models.URLField(
        blank=True,
        help_text="Public URL for webhooks and OAuth callbacks (e.g., https://pathfinder.example.com)",
    )
    version_retention_days = models.IntegerField(
        default=365,
        help_text="Days before manifest content is cleared from old versions",
    )
    last_cleanup_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last version cleanup run",
    )

    class Meta:
        db_table = "core_site_configuration"
        verbose_name = "Site Configuration"

    def __str__(self):
        return "Site Configuration"

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        """Get or create the singleton configuration instance."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
