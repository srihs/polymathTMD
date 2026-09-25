"""The model layer of Staff and access (brief 010): the role migration, the admin-leftovers
migration, ``UserQuerySet`` and the ``User`` rules behind criteria 1, 11, 13, 20 and 23, and,
since review round 1, 31, 34 and 35 ("only roles they hold", D13).

Each guard of criterion 13 has its own unit test here, against the model method, so the rule
is pinned whatever the form or view around it does.
"""

from importlib import import_module

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connection

from apps.accounts.models import (
    LAST_SUPERUSER_ERROR,
    OWN_FULL_ACCESS_ERROR,
    OWN_SIGN_IN_ERROR,
    UserManager,
)

from .conftest import make_user

pytestmark = pytest.mark.django_db

User = get_user_model()


def _perm_labels(group):
    return sorted(f"{p.content_type.app_label}.{p.codename}" for p in group.permissions.all())


# --------------------------------------------------------------------------- criterion 1


def test_staff_managers_role_holds_exactly_view_add_and_change_user():
    group = Group.objects.get(name="Staff managers")
    assert _perm_labels(group) == [
        "accounts.add_user",
        "accounts.change_user",
        "accounts.view_user",
    ]
    assert not group.permissions.filter(codename="delete_user").exists()


def test_it_desk_role_is_unchanged_by_this_brief():
    assert _perm_labels(Group.objects.get(name="IT desk")) == [
        "zoom.add_hostaccount",
        "zoom.change_hostaccount",
        "zoom.review_linkrequest",
        "zoom.view_hostaccount",
    ]
    assert not Group.objects.filter(name="Zoom account managers").exists()


def test_staff_managers_migration_is_idempotent_and_reversible():
    migration = import_module("apps.accounts.migrations.0003_staff_managers_group")
    migration.create_staff_managers_group(apps, None)
    assert Group.objects.filter(name="Staff managers").count() == 1
    assert Group.objects.get(name="Staff managers").permissions.count() == 3
    migration.remove_staff_managers_group(apps, None)
    assert not Group.objects.filter(name="Staff managers").exists()
    assert Permission.objects.filter(codename="change_user").exists(), "permissions stay"
    migration.create_staff_managers_group(apps, None)
    assert Group.objects.get(name="Staff managers").permissions.count() == 3


# --------------------------------------------------------------------------- criterion 20


def test_admin_leftovers_are_gone_after_migrate():
    assert "django_admin_log" not in connection.introspection.table_names()
    assert not ContentType.objects.filter(app_label="admin").exists()
    assert not Permission.objects.filter(content_type__app_label="admin").exists()


def test_admin_leftovers_migration_removes_admin_content_types_and_their_links():
    """A stale ``admin`` content type, with a permission a group holds, is removed cleanly."""
    content_type = ContentType.objects.create(app_label="admin", model="logentry")
    permission = Permission.objects.create(
        content_type=content_type, codename="view_logentry", name="Can view log entry"
    )
    group = Group.objects.create(name="Old admin users")
    group.permissions.add(permission)

    migration = import_module("apps.accounts.migrations.0004_remove_admin_leftovers")
    migration.delete_admin_content_types(apps, None)
    migration.delete_admin_content_types(apps, None)  # running again is harmless

    assert not ContentType.objects.filter(app_label="admin").exists()
    assert not Permission.objects.filter(pk=permission.pk).exists()
    assert group.permissions.count() == 0


def test_admin_leftovers_migration_reverse_is_a_noop_and_drop_is_conditional():
    from django.db import migrations

    migration = import_module("apps.accounts.migrations.0004_remove_admin_leftovers").Migration
    run_python, run_sql = migration.operations
    assert run_python.reverse_code is migrations.RunPython.noop
    assert run_sql.sql == "DROP TABLE IF EXISTS django_admin_log"
    assert run_sql.reverse_sql == migrations.RunSQL.noop


# --------------------------------------------------------------------------- criterion 23


def test_manager_stays_a_django_user_manager():
    from django.contrib.auth.models import UserManager as DjangoUserManager

    assert isinstance(User.objects, UserManager)
    assert isinstance(User.objects, DjangoUserManager)
    user = User.objects.create_user(username="ok", password="pw")
    assert user.check_password("pw")


def test_staff_list_orders_active_first_then_last_first_and_username():
    make_user("zed", first_name="Amal", last_name="Bandara")
    make_user("off", first_name="Aaron", last_name="Aaron", is_active=False)
    make_user("bbb", first_name="Chamari", last_name="Bandara")
    make_user("aaa", first_name="Chamari", last_name="Bandara")
    make_user("x", first_name="", last_name="Alwis")
    names = list(User.objects.staff_list().values_list("username", flat=True))
    assert names == ["x", "zed", "aaa", "bbb", "off"]


def test_staff_list_prefetches_groups():
    assert "groups" in User.objects.staff_list()._prefetch_related_lookups


def test_people_with_only_view_user_manage_nobody_not_even_themselves():
    viewer_role = Group.objects.create(name="Staff viewers")
    viewer_role.permissions.add(Permission.objects.get(codename="view_user"))
    viewer = make_user("viewer", groups=["Staff viewers"])
    assert not viewer.can_be_managed_by(viewer)
    assert not make_user("teacher").can_be_managed_by(viewer)


def test_active_superusers_excludes_switched_off_and_plain_users(superuser):
    make_user("gone", is_superuser=True, is_active=False)
    make_user("teacher")
    assert list(User.objects.active_superusers()) == [superuser]


def test_clean_trims_and_lower_cases_email():
    user = User(username="nimali", email="  Nimali@Polymath.Example ")
    user.clean()
    assert user.email == "nimali@polymath.example"


# --------------------------------------------------------------------------- criterion 11


def test_only_an_active_superuser_can_grant_full_access(superuser, staff_manager):
    assert User.can_grant_full_access(superuser)
    assert staff_manager.can_grant_full_access(superuser)
    assert not User.can_grant_full_access(staff_manager)
    assert not User.can_grant_full_access(None)
    superuser.is_active = False
    assert not User.can_grant_full_access(superuser)


def test_superuser_can_manage_everyone(superuser, staff_manager, plain_user):
    other_super = make_user("other", is_superuser=True)
    for target in (superuser, other_super, staff_manager, plain_user):
        assert target.can_be_managed_by(superuser)


def test_staff_manager_manages_only_people_whose_rights_they_hold(
    superuser, staff_manager, it_user, plain_user
):
    """Criteria 11 (amended) and 34, as SM: not in ``IT desk``."""
    assert plain_user.can_be_managed_by(staff_manager)
    assert staff_manager.can_be_managed_by(staff_manager), "their own record"
    assert not it_user.can_be_managed_by(staff_manager), "IT desk's rights aren't all theirs"
    assert not superuser.can_be_managed_by(staff_manager)
    other_manager = make_user("other.manager", groups=["Staff managers"])
    assert not other_manager.can_be_managed_by(staff_manager), "peers are off limits"


def test_a_switched_off_staff_manager_is_still_off_limits_to_a_peer(staff_manager):
    """The inactive-user trap (criterion 34, D13): Django reports no rights for a switched-off
    user, but their roles still grant them, so a peer mustn't reach them and switch them on."""
    switched_off = make_user("was.manager", groups=["Staff managers"], is_active=False)
    assert switched_off.get_all_permissions() == set()
    assert "accounts.change_user" in switched_off.granted_permissions()
    assert not switched_off.can_be_managed_by(staff_manager)


def test_desk_manager_manages_it_desk_people_but_not_other_staff_managers(
    desk_manager, staff_manager, it_user, plain_user
):
    """Criterion 34, as SM+IT."""
    assert it_user.can_be_managed_by(desk_manager)
    assert plain_user.can_be_managed_by(desk_manager)
    assert not staff_manager.can_be_managed_by(desk_manager)
    assert desk_manager.can_be_managed_by(desk_manager)


def test_a_permission_given_directly_counts_as_a_right_the_actor_must_hold(staff_manager):
    target = make_user("direct")
    target.user_permissions.add(Permission.objects.get(codename="review_linkrequest"))
    assert target.granted_permissions() == {"zoom.review_linkrequest"}
    assert not target.can_be_managed_by(staff_manager)


def test_granted_permissions_come_from_roles_and_own_permissions(it_user):
    it_user.user_permissions.add(Permission.objects.get(codename="view_user"))
    assert it_user.granted_permissions() == {
        "accounts.view_user",
        "zoom.add_hostaccount",
        "zoom.change_hostaccount",
        "zoom.review_linkrequest",
        "zoom.view_hostaccount",
    }
    assert make_user("nobody").granted_permissions() == set()


def test_granted_permissions_cost_no_queries_on_staff_list_rows(
    django_assert_num_queries, staff_manager, it_user, desk_manager
):
    """Criterion 35: ``staff_list()`` prefetches everything ``granted_permissions`` reads."""
    it_user.user_permissions.add(Permission.objects.get(codename="view_user"))
    people = list(User.objects.staff_list())
    with django_assert_num_queries(0):
        granted = {person.username: person.granted_permissions() for person in people}
    assert "zoom.review_linkrequest" in granted["kasun.it"]
    assert "accounts.change_user" in granted["desk.manager"]


def test_staff_list_prefetches_roles_permissions_and_own_permissions():
    lookups = User.objects.staff_list()._prefetch_related_lookups
    assert "groups__permissions__content_type" in lookups
    assert "user_permissions__content_type" in lookups


# --------------------------------------------------------------------------- criterion 31


def _role(name):
    return Group.objects.prefetch_related("permissions__content_type").get(name=name)


@pytest.mark.parametrize(
    ("actor", "expected"),
    [
        ("staff_manager", {"IT desk": False, "Staff managers": True, "Nothing yet": True}),
        ("desk_manager", {"IT desk": True, "Staff managers": True, "Nothing yet": True}),
        ("superuser", {"IT desk": True, "Staff managers": True, "Nothing yet": True}),
    ],
)
def test_can_give_role_only_when_the_actor_holds_all_its_rights(request, actor, expected):
    Group.objects.create(name="Nothing yet")
    who = request.getfixturevalue(actor)
    assert {name: User.can_give_role(who, _role(name)) for name in expected} == expected


def test_nobody_gives_a_role_with_rights_without_an_actor():
    assert not User.can_give_role(None, _role("IT desk"))


def test_people_without_change_user_manage_nobody(it_user, plain_user):
    assert not plain_user.can_be_managed_by(it_user)
    assert not it_user.can_be_managed_by(plain_user)
    assert not plain_user.can_be_managed_by(None)


# --------------------------------------------------------------------------- criterion 13


def test_guard_nobody_switches_off_their_own_sign_in(staff_manager):
    errors = staff_manager.access_change_error(
        actor=staff_manager, is_active=False, is_superuser=False
    )
    assert errors == {"is_active": OWN_SIGN_IN_ERROR}


def test_guard_nobody_removes_their_own_full_access(superuser):
    make_user("second", is_superuser=True)
    errors = superuser.access_change_error(actor=superuser, is_active=True, is_superuser=False)
    assert errors == {"is_superuser": OWN_FULL_ACCESS_ERROR}


def test_guard_the_only_active_superuser_keeps_sign_in_and_full_access(superuser):
    """Reached only by a caller that isn't the superuser, since the self rule answers first."""
    make_user("gone", is_superuser=True, is_active=False)
    expected = LAST_SUPERUSER_ERROR.format(name=superuser)
    assert expected == (
        "Ruwan Silva is the only person with full access. Give someone else full access first."
    )
    assert superuser.access_change_error(actor=None, is_active=False, is_superuser=True) == {
        "is_active": expected
    }
    assert superuser.access_change_error(actor=None, is_active=True, is_superuser=False) == {
        "is_superuser": expected
    }


def test_guard_allows_changing_a_superuser_when_another_remains(superuser):
    other = make_user("other", is_superuser=True)
    assert other.access_change_error(actor=superuser, is_active=False, is_superuser=False) == {}


def test_guard_allows_switching_off_someone_else(superuser, it_user):
    assert it_user.access_change_error(actor=superuser, is_active=False, is_superuser=False) == {}


def test_guard_is_silent_when_nothing_is_taken_away(superuser):
    assert superuser.access_change_error(actor=superuser, is_active=True, is_superuser=True) == {}


def test_guard_never_blocks_granting(staff_manager):
    """Only losing sign-in or full access is guarded; granting never is."""
    staff_manager.is_active = False
    assert (
        staff_manager.access_change_error(actor=staff_manager, is_active=True, is_superuser=True)
        == {}
    )
