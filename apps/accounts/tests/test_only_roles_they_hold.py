"""Only roles they hold: brief 010, review round 1, SF1 (D13, criteria 32–35).

A Staff manager's power is capped at their own rights: they give or remove only roles whose
rights they have, can't change their own roles, and can't open another Staff manager or
anyone with rights they lack. These tests go through the real forms and views; the rules
themselves are unit-tested in ``test_staff_models.py``.

"SM" is ``staff_manager`` (not in ``IT desk``); "SM+IT" is ``desk_manager``.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.accounts.forms import ROLE_NOT_YOURS, StaffChangeForm

from .conftest import GOOD_PASSWORD, make_user

pytestmark = pytest.mark.django_db

User = get_user_model()

STAFF = reverse("accounts:staff")
STAFF_ADD = reverse("accounts:staff_add")
PASSWORD_CHANGE = reverse("accounts:password_change")


def _edit(user):
    return reverse("accounts:staff_edit", args=[user.pk])


def _set_password(user):
    return reverse("accounts:staff_password", args=[user.pk])


def _pk(name):
    return Group.objects.get(name=name).pk


def _roles_by_name(response):
    return {entry["choice"].choice_label: entry for entry in response.context["roles"]}


def _role_names(user):
    return sorted(user.groups.values_list("name", flat=True))


def _add_data(**overrides):
    data = {
        "first_name": "Chamari",
        "last_name": "Bandara",
        "username": "chamari.b",
        "email": "chamari@polymath.example",
        "password1": GOOD_PASSWORD,
        "password2": GOOD_PASSWORD,
    }
    data.update(overrides)
    return data


def _edit_data(user, **overrides):
    data = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "email": user.email,
        "groups": [str(pk) for pk in user.groups.values_list("pk", flat=True)],
        "is_active": "on",
    }
    data.update(overrides)
    return data


# --------------------------------------------------------------------------- criterion 32


def test_a_role_the_staff_manager_cant_give_is_a_disabled_unticked_box(manager_client):
    response = manager_client.get(STAFF_ADD)
    roles = _roles_by_name(response)
    it_desk, staff_managers = roles["IT desk"], roles["Staff managers"]
    assert it_desk["can_give"] is False
    assert it_desk["choice"].data["attrs"].get("disabled") is True
    assert it_desk["choice"].data["selected"] is False
    assert " disabled" in str(it_desk["choice"].tag())
    assert staff_managers["can_give"] is True
    assert "disabled" not in staff_managers["choice"].data["attrs"]
    assert response.context["roles_read_only"] is False


def test_a_superuser_can_give_every_role(super_client):
    roles = _roles_by_name(super_client.get(STAFF_ADD))
    assert all(entry["can_give"] for entry in roles.values())
    assert not any("disabled" in entry["choice"].data["attrs"] for entry in roles.values())


def test_a_crafted_post_giving_a_role_you_cant_give_is_refused(manager_client):
    before = User.objects.count()
    response = manager_client.post(STAFF_ADD, _add_data(groups=[str(_pk("IT desk"))]))
    assert response.status_code == 200
    assert response.context["form"].errors["groups"] == [ROLE_NOT_YOURS]
    assert User.objects.count() == before


def test_a_crafted_post_on_a_change_giving_a_role_you_cant_give_is_refused(
    manager_client, plain_user
):
    response = manager_client.post(
        _edit(plain_user), _edit_data(plain_user, first_name="Changed", groups=[_pk("IT desk")])
    )
    assert response.status_code == 200
    assert response.context["form"].errors["groups"] == [ROLE_NOT_YOURS]
    plain_user.refresh_from_db()
    assert plain_user.first_name == "Dilani"
    assert _role_names(plain_user) == []


def test_desk_manager_gives_it_desk(desk_manager_client, plain_user):
    response = desk_manager_client.post(
        _edit(plain_user), _edit_data(plain_user, groups=[_pk("IT desk")])
    )
    assert response.status_code == 302
    assert _role_names(plain_user) == ["IT desk"]


def test_desk_manager_saving_an_unrelated_change_leaves_every_role_unchanged(
    desk_manager_client, it_user
):
    response = desk_manager_client.post(_edit(it_user), _edit_data(it_user, first_name="Kasun R"))
    assert response.status_code == 302
    it_user.refresh_from_db()
    assert it_user.first_name == "Kasun R"
    assert _role_names(it_user) == ["IT desk"]


def test_clean_groups_keeps_a_role_the_actor_cant_give_when_the_post_leaves_it_out(
    staff_manager,
):
    """The defensive rule: the person gained ``IT desk`` after the page was loaded."""
    person = make_user("teacher")
    person.groups.add(Group.objects.get(name="IT desk"))
    form = StaffChangeForm(
        data=_edit_data(person, groups=[_pk("Staff managers")]),
        instance=person,
        actor=staff_manager,
    )
    assert form.is_valid(), form.errors
    assert sorted(group.name for group in form.cleaned_data["groups"]) == [
        "IT desk",
        "Staff managers",
    ]
    form.save()
    assert _role_names(person) == ["IT desk", "Staff managers"]

    form = StaffChangeForm(data=_edit_data(person, groups=[]), instance=person, actor=staff_manager)
    assert form.is_valid(), form.errors
    form.save()
    assert _role_names(person) == ["IT desk"], "Staff managers removed, IT desk kept"


# --------------------------------------------------------------------------- criterion 33


def test_a_staff_managers_own_roles_are_read_only(manager_client, staff_manager):
    response = manager_client.get(_edit(staff_manager))
    assert response.context["roles_read_only"] is True
    form = response.context["form"]
    assert form.fields["groups"].disabled
    roles = _roles_by_name(response)
    assert all(entry["choice"].data["attrs"].get("disabled") for entry in roles.values())
    assert roles["Staff managers"]["choice"].data["selected"] is True


@pytest.mark.parametrize(
    "groups",
    [[], ["Staff managers", "IT desk"]],
    ids=["unticks Staff managers", "ticks IT desk"],
)
def test_a_crafted_post_to_your_own_roles_saves_the_rest_and_keeps_the_roles(
    manager_client, staff_manager, groups
):
    data = _edit_data(staff_manager, first_name="Nimali K", groups=[_pk(name) for name in groups])
    response = manager_client.post(_edit(staff_manager), data)
    assert response.status_code == 302
    staff_manager.refresh_from_db()
    assert staff_manager.first_name == "Nimali K"
    assert _role_names(staff_manager) == ["Staff managers"]
    assert manager_client.get(STAFF).status_code == 200, "no self-lockout"


def test_a_superuser_may_still_change_their_own_roles(super_client, superuser):
    response = super_client.get(_edit(superuser))
    assert response.context["roles_read_only"] is False
    data = _edit_data(superuser, groups=[_pk("IT desk")], is_superuser="on")
    assert super_client.post(_edit(superuser), data).status_code == 302
    assert _role_names(superuser) == ["IT desk"]


# --------------------------------------------------------------------------- criterion 34


@pytest.mark.parametrize("page", [_edit, _set_password])
@pytest.mark.parametrize(
    "target", ["other_manager", "it_user", "superuser", "switched_off_manager"]
)
def test_staff_manager_gets_403_for_people_they_may_not_manage(
    manager_client, request, page, target
):
    people = {
        "other_manager": lambda: make_user("other.manager", groups=["Staff managers"]),
        "switched_off_manager": lambda: make_user(
            "was.manager", groups=["Staff managers"], is_active=False
        ),
        "it_user": lambda: request.getfixturevalue("it_user"),
        "superuser": lambda: request.getfixturevalue("superuser"),
    }
    person = people[target]()
    assert manager_client.get(page(person)).status_code == 403


def test_a_peer_cant_switch_a_switched_off_staff_manager_back_on(manager_client):
    switched_off = make_user("was.manager", groups=["Staff managers"], is_active=False)
    response = manager_client.post(_edit(switched_off), _edit_data(switched_off))
    assert response.status_code == 403
    switched_off.refresh_from_db()
    assert not switched_off.is_active


@pytest.mark.parametrize("page", [_edit, _set_password])
def test_desk_manager_opens_it_desk_people_but_not_other_staff_managers(
    desk_manager_client, it_user, staff_manager, page
):
    assert desk_manager_client.get(page(it_user)).status_code == 200
    assert desk_manager_client.get(page(staff_manager)).status_code == 403


def test_list_links_only_the_people_the_staff_manager_may_change(
    manager_client, staff_manager, it_user, plain_user, superuser
):
    response = manager_client.get(STAFF)
    manageable = {person.username: person.can_manage for person in response.context["people"]}
    assert manageable == {"manager": True, "teacher": True, "kasun.it": False, "head": False}
    content = response.content.decode()
    assert _edit(plain_user) in content
    assert _edit(it_user) not in content
    assert _edit(superuser) not in content


@pytest.mark.parametrize("who", ["manager_client", "super_client"])
@pytest.mark.parametrize("method", ["get", "post"])
def test_your_own_set_password_page_sends_you_to_change_your_password(request, who, method):
    client = request.getfixturevalue(who)
    me = User.objects.get(pk=int(client.session["_auth_user_id"]))
    data = {"new_password1": GOOD_PASSWORD, "new_password2": GOOD_PASSWORD}
    response = getattr(client, method)(_set_password(me), data if method == "post" else None)
    assert response.status_code == 302
    assert response.url == PASSWORD_CHANGE
    me.refresh_from_db()
    assert me.check_password("pw"), "nothing changed"


@pytest.mark.parametrize("who", ["plain_user", "it_user"])
def test_your_own_set_password_page_is_still_403_without_staff_rights(client, request, who):
    me = request.getfixturevalue(who)
    client.force_login(me)
    assert client.get(_set_password(me)).status_code == 403


# --------------------------------------------------------------------------- criterion 35


def _query_count(client, url):
    with CaptureQueriesContext(connection) as queries:
        response = client.get(url)
    assert response.status_code == 200
    return len(queries)


def _mixed_people(prefix, count):
    """Staff managers, IT desk people and plain users in turn, the last with its own right."""
    roles = [["Staff managers"], ["IT desk"], []]
    direct = Permission.objects.get(codename="view_user")
    for number in range(count):
        person = make_user(f"{prefix}{number}", groups=roles[number % 3])
        if number % 3 == 2:
            person.user_permissions.add(direct)


def test_list_query_count_as_a_staff_manager_does_not_grow_with_people(manager_client):
    _mixed_people("few", 3)
    few = _query_count(manager_client, STAFF)
    _mixed_people("many", 37)
    assert User.objects.count() == 41
    assert _query_count(manager_client, STAFF) == few


@pytest.mark.parametrize("page", ["add", "change"])
def test_role_list_query_count_does_not_grow_with_roles(manager_client, plain_user, page):
    url = STAFF_ADD if page == "add" else _edit(plain_user)
    few = _query_count(manager_client, url)
    permissions = Permission.objects.filter(codename__in=["view_user", "add_hostaccount"])
    for number in range(4):
        Group.objects.create(name=f"Role {number}").permissions.add(*permissions)
    with CaptureQueriesContext(connection) as queries:
        response = manager_client.get(url)
    assert len(queries) == few
    roles = _roles_by_name(response)
    assert len(roles) == 6
    assert [roles[f"Role {n}"]["can_give"] for n in range(4)] == [False] * 4
