"""Remove Blueprint models and blueprint FKs from Service.

SQLite requires careful ordering: remove Service FKs first,
then delete BlueprintVersion, then delete Blueprint.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_add_service_model'),
    ]

    operations = [
        # 1. Remove blueprint FK from Service
        migrations.RemoveField(
            model_name='service',
            name='blueprint',
        ),
        # 2. Remove blueprint_version FK from Service
        migrations.RemoveField(
            model_name='service',
            name='blueprint_version',
        ),
        # 3. Delete BlueprintVersion (has FK to Blueprint)
        migrations.DeleteModel(
            name='BlueprintVersion',
        ),
        # 4. Delete Blueprint
        migrations.DeleteModel(
            name='Blueprint',
        ),
    ]
