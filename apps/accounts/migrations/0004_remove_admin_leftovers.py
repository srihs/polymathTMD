"""Remove what ``django.contrib.admin`` left in the database (brief 010, D6, criterion 20).

Uninstalling an app doesn't drop its tables, so ``django_admin_log`` (with foreign keys to
``accounts_user``) and the ``admin`` content types would otherwise stay behind. This deletes
the ``admin`` content types, which cascades to their permissions and any group or user links
to them, and drops the table if it exists.

Either order works. ``django.contrib.admin`` isn't installed, so the historical models this
migration sees have no ``LogEntry``, and deleting the content types never cascades into
``django_admin_log`` (review round 1, nit 1).

What stays behind, on purpose: the ``admin`` rows in ``django_migrations``. They're
bookkeeping only, with nothing reading them now the app is gone; removing them would mean
editing Django's own migration history for no gain. If the admin were ever reinstalled,
Django would think its tables exist, so it would need ``migrate admin zero --fake`` first.

The admin's edit history is lost; production isn't live yet, so it only held dev edits. The
reverse is a no-op: the admin isn't coming back, and there's nothing to restore it from. On a
fresh database (tests), where the table never existed, both steps simply do nothing.
"""

from django.db import migrations


def delete_admin_content_types(apps, schema_editor):
    apps.get_model("contenttypes", "ContentType").objects.filter(app_label="admin").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_staff_managers_group"),
        ("contenttypes", "0002_remove_content_type_name"),
        # For ordering only: permissions (auth) must exist before their content types go.
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(delete_admin_content_types, migrations.RunPython.noop),
        migrations.RunSQL(
            "DROP TABLE IF EXISTS django_admin_log", reverse_sql=migrations.RunSQL.noop
        ),
    ]
