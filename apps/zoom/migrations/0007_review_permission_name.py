"""Rename ``zoom.review_linkrequest`` for cancelling and rescheduling (brief 011, D8, criterion 32).

Django's ``migrate`` creates missing permissions but never renames one that exists, so without
this the database would keep the old name, and brief 010's Staff and access screen, which lists
permission names, would still say "approve or reject". The codename, and so every check in the
code and the IT desk group's membership, is unchanged. The name already mentions rescheduling,
so brief 012 needs no second rename. Reversing sets the old name back.
"""

from django.db import migrations

CODENAME = "review_linkrequest"
OLD_NAME = "Can approve or reject Zoom link requests"
NEW_NAME = "Can approve, reject, reschedule or cancel Zoom link requests"


def _rename(apps, name):
    Permission = apps.get_model("auth", "Permission")
    Permission.objects.filter(
        content_type__app_label="zoom", content_type__model="linkrequest", codename=CODENAME
    ).update(name=name)


def use_new_name(apps, schema_editor):
    _rename(apps, NEW_NAME)


def use_old_name(apps, schema_editor):
    _rename(apps, OLD_NAME)


class Migration(migrations.Migration):
    dependencies = [
        ("zoom", "0006_cancel_and_start"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(use_new_name, use_old_name),
    ]
