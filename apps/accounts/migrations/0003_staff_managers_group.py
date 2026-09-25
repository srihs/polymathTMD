"""Create the ``Staff managers`` role: view, add and change users, never delete (brief 010, D8).

It lets the head of IT add people and give them roles without full access. ``delete_user``
is left out on purpose: people are switched off, never deleted (D4).

As in ``zoom/0002_it_desk_group``, the content type and permissions are created here with
``get_or_create``, because Django normally makes them only after all migrations have run
(``post_migrate``); ``post_migrate`` later finds them and leaves them alone. The names are
Django's defaults. Running it twice adds nothing twice. Reversing removes the group; the
permissions belong to the model and stay.
"""

from django.db import migrations

GROUP_NAME = "Staff managers"
MODEL = "user"
ACTIONS = ("view", "add", "change")


def create_staff_managers_group(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")

    content_type, _ = ContentType.objects.get_or_create(app_label="accounts", model=MODEL)
    permissions = [
        Permission.objects.get_or_create(
            content_type=content_type,
            codename=f"{action}_{MODEL}",
            defaults={"name": f"Can {action} {MODEL}"},
        )[0]
        for action in ACTIONS
    ]
    group, _ = Group.objects.get_or_create(name=GROUP_NAME)
    group.permissions.set(permissions)


def remove_staff_managers_group(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name=GROUP_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_alter_user_managers"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(create_staff_managers_group, remove_staff_managers_group),
    ]
