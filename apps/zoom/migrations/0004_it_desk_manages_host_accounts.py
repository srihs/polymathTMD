"""Give the ``IT desk`` group the host-account permissions (brief 008, Q1 and D2).

Everyone in the IT desk manages the Zoom accounts, so the group gets Django's built-in
``view_``, ``add_`` and ``change_hostaccount`` permissions, and never ``delete_`` (accounts
aren't deleted, D4). They come from ``django.contrib.auth``, not the admin, so they outlive the
admin's removal in brief 010.

As in ``0002_it_desk_group``, the content type and permissions are created here with
``get_or_create``, because Django normally makes them only after all migrations have run
(``post_migrate``). ``post_migrate`` later finds them and leaves them alone. The names are
Django's defaults. Running it twice adds nothing twice; reversing removes exactly these three
permissions from the group and leaves the group and ``review_linkrequest`` alone.

The reverse only looks the permissions up (``filter``): undoing a grant must never create a
content type or permission as a side effect (review round 1, nit 2).
"""

from django.db import migrations

GROUP_NAME = "IT desk"
MODEL = "hostaccount"
VERBOSE_NAME = "Zoom host account"
ACTIONS = ("view", "add", "change")


def _get_or_create_permissions(apps):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    content_type, _ = ContentType.objects.get_or_create(app_label="zoom", model=MODEL)
    return [
        Permission.objects.get_or_create(
            content_type=content_type,
            codename=f"{action}_{MODEL}",
            defaults={"name": f"Can {action} {VERBOSE_NAME}"},
        )[0]
        for action in ACTIONS
    ]


def _existing_permissions(apps):
    Permission = apps.get_model("auth", "Permission")
    return Permission.objects.filter(
        content_type__app_label="zoom",
        content_type__model=MODEL,
        codename__in=[f"{action}_{MODEL}" for action in ACTIONS],
    )


def grant_host_account_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    group, _ = Group.objects.get_or_create(name=GROUP_NAME)
    group.permissions.add(*_get_or_create_permissions(apps))


def revoke_host_account_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    group = Group.objects.filter(name=GROUP_NAME).first()
    if group is not None:
        group.permissions.remove(*_existing_permissions(apps))


class Migration(migrations.Migration):
    dependencies = [
        ("zoom", "0003_hostaccount_host_key_changed"),
    ]

    operations = [
        migrations.RunPython(grant_host_account_permissions, revoke_host_account_permissions),
    ]
