from django.db import migrations, models


def populate_step_commit_sha(apps, schema_editor):
    """Set step_commit_sha from current CIStep.commit_sha for all existing records."""
    CIWorkflowStep = apps.get_model("core", "CIWorkflowStep")
    for ws in CIWorkflowStep.objects.select_related("step").all():
        ws.step_commit_sha = ws.step.commit_sha
        ws.save(update_fields=["step_commit_sha"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0033_service_templates"),
    ]

    operations = [
        migrations.AddField(
            model_name="ciworkflowstep",
            name="step_commit_sha",
            field=models.CharField(
                blank=True,
                help_text="CIStep.commit_sha captured when this workflow was last saved.",
                max_length=40,
            ),
        ),
        migrations.RunPython(populate_step_commit_sha, migrations.RunPython.noop),
    ]
