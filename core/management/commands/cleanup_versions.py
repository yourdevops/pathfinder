from django.core.management.base import BaseCommand

from core.tasks import cleanup_old_versions


class Command(BaseCommand):
    help = "Clean up old CI workflow version manifest content and delete unreferenced versions"

    def handle(self, *args, **options):
        result = cleanup_old_versions()
        self.stdout.write(
            self.style.SUCCESS(
                f"Cleanup complete: {result['content_cleared']} manifest(s) cleared, "
                f"{result['versions_deleted']} version(s) deleted."
            )
        )
