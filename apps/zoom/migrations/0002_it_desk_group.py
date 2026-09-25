"""Create the ``IT desk`` group holding exactly ``zoom.review_linkrequest`` (brief 005, D2).

A superuser adds IT staff to this group in the admin; that is all it takes to use the queue.
Django normally creates content types and permissions after all migrations run
(``post_migrate``), so this migration creates the one it needs explicitly with
``get_or_create``; ``post_migrate`` later finds it and leaves it alone. Re-running doesn't
duplicate anything; reversing removes the group (the permission belongs to the model and stays).
"""

from django.db import migrations

GROUP_NAME = "IT desk"
CODENAME = "review_linkrequest"
PERMISSION_NAME = "Can approve or reject Zoom link requests"


def create_it_desk_group(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")

    content_type, _ = ContentType.objects.get_or_create(app_label="zoom", model="linkrequest")
    permission, _ = Permission.objects.get_or_create(
        content_type=content_type, codename=CODENAME, defaults={"name": PERMISSION_NAME}
    )
    group, _ = Group.objects.get_or_create(name=GROUP_NAME)
    group.permissions.set([permission])


def remove_it_desk_group(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name=GROUP_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("zoom", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(create_it_desk_group, remove_it_desk_group),
    ]
