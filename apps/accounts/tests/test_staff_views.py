"""The Staff and access screens and "Change your password" (brief 010).

Covers criteria 2, 5–18 and the backend half of 28: who may open each page, the list's
order, links and query budget, the add and change forms (copy, widget attributes, the
``roles`` context), creating people, validation, the guards as users meet them, switching
people off, both password flows, and that no typed password ever leaks into a page or a log.
"""

import html
import logging
import re

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import password_validators_help_text_html
from django.contrib.messages import get_messages
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import get_resolver, reverse

from apps.accounts.forms import (
    EMAIL_REQUIRED,
    EMAIL_TAKEN,
    OwnPasswordChangeForm,
    StaffChangeForm,
    StaffCreateForm,
    StaffSetPasswordForm,
)
from apps.accounts.models import OWN_FULL_ACCESS_ERROR, OWN_SIGN_IN_ERROR

from .conftest import GOOD_PASSWORD, make_user

pytestmark = pytest.mark.django_db

User = get_user_model()

STAFF = reverse("accounts:staff")
STAFF_ADD = reverse("accounts:staff_add")
PASSWORD_CHANGE = reverse("accounts:password_change")
LOGIN = reverse("accounts:login")
HOME = reverse("core:home")


def _edit(user):
    return reverse("accounts:staff_edit", args=[user.pk])


def _set_password(user):
    return reverse("accounts:staff_password", args=[user.pk])


def _flashes(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


def _input_tag(content, name):
    match = re.search(rf'<input[^>]*\bname="{name}"[^>]*>', content)
    assert match, f"no input named {name!r}"
    return match.group(0)


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
    return {key: value for key, value in data.items() if value is not None}


def _edit_data(user, **overrides):
    data = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "email": user.email,
        "groups": [str(pk) for pk in user.groups.values_list("pk", flat=True)],
    }
    if user.is_active:
        data["is_active"] = "on"
    if user.is_superuser:
        data["is_superuser"] = "on"
    data.update(overrides)
    return {key: value for key, value in data.items() if value is not None}


# --------------------------------------------------------------------------- criterion 2


def _page_url(page, target):
    if page in ("staff_edit", "staff_password"):
        return reverse(f"accounts:{page}", args=[target.pk])
    return reverse(f"accounts:{page}")


PAGES = ["staff", "staff_add", "staff_edit", "staff_password", "password_change"]


@pytest.mark.parametrize("page", PAGES)
def test_anonymous_visitors_are_sent_to_sign_in(client, plain_user, page):
    url = _page_url(page, plain_user)
    response = client.get(url)
    assert response.status_code == 302
    assert response.url == f"{LOGIN}?next={url}"


@pytest.mark.parametrize("who", ["plain_user", "it_user", "staff_flag_user"])
@pytest.mark.parametrize("page", PAGES)
def test_people_without_staff_permissions_get_403_except_own_password(client, request, who, page):
    viewer = request.getfixturevalue(who)
    target = make_user("target")
    client.force_login(viewer)
    expected = 200 if page == "password_change" else 403
    assert client.get(_page_url(page, target)).status_code == expected


@pytest.mark.parametrize("page", PAGES)
def test_staff_manager_opens_every_page_for_someone_they_may_manage(
    manager_client, plain_user, page
):
    assert manager_client.get(_page_url(page, plain_user)).status_code == 200


@pytest.mark.parametrize("page", ["staff_edit", "staff_password"])
def test_staff_manager_gets_403_for_a_superuser_target(manager_client, superuser, page):
    assert manager_client.get(_page_url(page, superuser)).status_code == 403


@pytest.mark.parametrize("page", PAGES)
def test_superuser_opens_every_page_even_for_another_superuser(super_client, page):
    other = make_user("other.head", is_superuser=True)
    assert super_client.get(_page_url(page, other)).status_code == 200


def test_posting_to_a_superuser_as_staff_manager_is_refused_and_changes_nothing(
    manager_client, superuser
):
    response = manager_client.post(
        _set_password(superuser), {"new_password1": GOOD_PASSWORD, "new_password2": GOOD_PASSWORD}
    )
    assert response.status_code == 403
    superuser.refresh_from_db()
    assert superuser.check_password("pw")
    response = manager_client.post(_edit(superuser), _edit_data(superuser, first_name="Hacked"))
    assert response.status_code == 403
    superuser.refresh_from_db()
    assert superuser.first_name == "Ruwan"


def test_missing_person_is_404_for_a_staff_manager(manager_client):
    assert manager_client.get(reverse("accounts:staff_edit", args=[999999])).status_code == 404


# --------------------------------------------------------------------------- criterion 5


def test_list_context_orders_people_and_marks_who_the_viewer_may_change(
    manager_client, staff_manager, superuser, it_user
):
    make_user("gone", first_name="Aaron", last_name="Aaron", is_active=False)
    response = manager_client.get(STAFF)
    assert response.status_code == 200
    people = list(response.context["people"])
    assert [p.username for p in people] == ["kasun.it", "manager", "head", "gone"]
    manageable = {p.username: p.can_manage for p in people}
    # IT desk's rights aren't all the Staff manager's own (criterion 34); yourself you may.
    assert manageable == {"kasun.it": False, "manager": True, "head": False, "gone": True}
    assert response.context["can_add"] is True


def test_list_can_add_is_false_without_add_user(client):
    viewer_role = Group.objects.create(name="Staff viewers")
    viewer_role.permissions.add(Permission.objects.get(codename="view_user"))
    viewer = make_user("viewer", groups=["Staff viewers"])
    client.force_login(viewer)
    response = client.get(STAFF)
    assert response.status_code == 200
    assert response.context["can_add"] is False
    assert not any(p.can_manage for p in response.context["people"])


def test_list_pages_at_fifty(super_client):
    for number in range(50):
        make_user(f"person{number:02d}")
    response = super_client.get(STAFF)
    assert response.context["is_paginated"]
    assert len(response.context["people"]) == 50
    assert response.context["paginator"].num_pages == 2
    assert len(super_client.get(STAFF, {"page": 2}).context["people"]) == 1


def test_list_shows_roles_and_full_access_from_prefetched_groups(super_client, it_user):
    content = super_client.get(STAFF).content.decode()
    assert "IT desk" in content
    assert "Full access" in content


# --------------------------------------------------------------------------- criterion 6


def _query_count(client, url):
    with CaptureQueriesContext(connection) as queries:
        response = client.get(url)
    assert response.status_code == 200
    return len(queries)


def test_list_query_count_does_not_grow_with_people(super_client):
    roles = list(Group.objects.filter(name__in=["IT desk", "Staff managers"]))
    for number in range(3):
        make_user(f"few{number}").groups.add(*roles)
    few = _query_count(super_client, STAFF)
    for number in range(37):
        make_user(f"many{number}").groups.add(*roles)
    assert User.objects.count() == 41
    assert _query_count(super_client, STAFF) == few


# --------------------------------------------------------------------------- criterion 7


D6_COPY = {
    "first_name": ("First name", "Like Nimali. You can leave the names empty."),
    "last_name": ("Last name", "Like Perera. Without a name, the desk shows their username."),
    "username": ("Username", "They type this to sign in. Letters, numbers and @ . + - _ only."),
    "email": ("Work email", "Emails about Zoom requests go here."),
    "groups": (
        "Roles",
        "Tick every role they need. With no role, they can sign in but only see Home.",
    ),
    "is_superuser": (
        "Full access to everything",
        "They can do everything here, including changing other people with full access. "
        "Give this to as few people as possible.",
    ),
    "password2": ("Type it again", "Type the same password again, to check for typos."),
}


def test_add_form_for_a_superuser_has_criterion_7_fields_and_copy(super_client):
    response = super_client.get(STAFF_ADD)
    form = response.context["form"]
    assert isinstance(form, StaffCreateForm)
    assert list(form.fields) == [
        "first_name",
        "last_name",
        "username",
        "email",
        "groups",
        "is_superuser",
        "password1",
        "password2",
    ]
    for name, (label, help_text) in D6_COPY.items():
        assert form.fields[name].label == label, name
        assert form.fields[name].help_text == help_text, name
    assert form.fields["password1"].label == "Starting password"
    assert form.fields["password1"].help_text == password_validators_help_text_html()
    assert form.fields["email"].required
    assert response.context["is_add"] is True
    assert response.context["person"] is None


def test_add_form_for_a_staff_manager_has_no_full_access_field(manager_client):
    response = manager_client.get(STAFF_ADD)
    form = response.context["form"]
    assert "is_superuser" not in form.fields
    assert "is_active" not in form.fields
    assert 'name="is_superuser"' not in response.content.decode()


def test_add_form_widget_attributes(manager_client):
    content = manager_client.get(STAFF_ADD).content.decode()
    username = _input_tag(content, "username")
    assert "autofocus" not in username
    for name in ("first_name", "last_name", "username", "email"):
        assert 'autocomplete="off"' in _input_tag(content, name), name
    for name in ("username", "email"):
        tag = _input_tag(content, name)
        assert 'autocapitalize="none"' in tag, name
        assert 'spellcheck="false"' in tag, name
    assert 'type="email"' in _input_tag(content, "email")
    for name in ("password1", "password2"):
        assert 'autocomplete="new-password"' in _input_tag(content, name), name
    for name in ("first_name", "last_name", "username", "email", "password1", "password2"):
        assert f'<label class="field__label" for="id_{name}">' in content, name
        assert f'aria-describedby="{name}-help"' in _input_tag(content, name), name


def _make_two_permission_role():
    role = Group.objects.create(name="A test role")
    role.permissions.add(
        Permission.objects.get(codename="view_user"),
        Permission.objects.get(codename="add_hostaccount"),
    )
    return role


def test_roles_context_lists_every_group_by_name_with_sorted_permission_names(manager_client):
    role = _make_two_permission_role()
    response = manager_client.get(STAFF_ADD)
    roles = response.context["roles"]
    assert [entry["choice"].choice_label for entry in roles] == list(
        Group.objects.order_by("name").values_list("name", flat=True)
    )
    entry = next(e for e in roles if e["choice"].choice_label == role.name)
    assert entry["permissions"] == ["Can add Zoom host account", "Can view user"]
    assert entry["choice"].data["value"] == role.pk
    staff_managers = next(e for e in roles if e["choice"].choice_label == "Staff managers")
    assert staff_managers["permissions"] == ["Can add user", "Can change user", "Can view user"]


def test_a_role_made_in_the_test_gets_a_checkbox_with_its_permissions_in_order(manager_client):
    """Criteria 7 and 18: a new group needs no code change to appear, with its help."""
    role = _make_two_permission_role()
    response = manager_client.get(STAFF_ADD)
    content = response.content.decode()
    choice = next(
        e["choice"] for e in response.context["roles"] if e["choice"].choice_label == role.name
    )
    checkbox = re.search(rf'<input[^>]*\bid="{choice.id_for_label}"[^>]*>', content)
    assert checkbox, "no checkbox for the new role"
    assert f'value="{role.pk}"' in checkbox.group(0)
    # The label wraps the whole choice, or only its words when the role is disabled for the
    # viewer (criterion 32), so only its text is checked here.
    label = re.search(rf'<label[^>]*for="{choice.id_for_label}"[^>]*>(.*?)</label>', content, re.S)
    assert label, "no label for the new role's checkbox"
    text = label.group(1)
    assert "A test role" in text
    assert text.index("Can add Zoom host account") < text.index("Can view user")


def test_add_page_query_count_does_not_grow_with_roles(manager_client):
    few = _query_count(manager_client, STAFF_ADD)
    permissions = Permission.objects.filter(codename__in=["view_user", "add_hostaccount"])
    for number in range(4):
        Group.objects.create(name=f"Role {number}").permissions.add(*permissions)
    assert Group.objects.count() == 6
    assert _query_count(manager_client, STAFF_ADD) == few


# --------------------------------------------------------------------------- criterion 8


def test_add_creates_a_person_who_can_sign_in_with_a_hashed_password(desk_manager_client):
    it_desk = Group.objects.get(name="IT desk")
    response = desk_manager_client.post(STAFF_ADD, _add_data(groups=[str(it_desk.pk)]))
    assert response.status_code == 302
    assert response.url == STAFF
    person = User.objects.get(username="chamari.b")
    assert person.is_active and not person.is_staff and not person.is_superuser
    assert person.check_password(GOOD_PASSWORD)
    assert GOOD_PASSWORD not in person.password
    assert list(person.groups.all()) == [it_desk]
    assert person.email == "chamari@polymath.example"
    assert _flashes(response) == [
        "Added Chamari Bandara. Give them their username and starting password yourself, "
        "not by email."
    ]
    assert Client().login(username="chamari.b", password=GOOD_PASSWORD)


def test_superuser_can_give_full_access_when_adding(super_client):
    super_client.post(STAFF_ADD, _add_data(is_superuser="on"))
    assert User.objects.get(username="chamari.b").is_superuser


def test_add_stores_the_email_in_lower_case(manager_client):
    manager_client.post(STAFF_ADD, _add_data(email="Chamari@Polymath.Example"))
    assert User.objects.get(username="chamari.b").email == "chamari@polymath.example"


# --------------------------------------------------------------------------- criteria 9–10


@pytest.mark.parametrize(
    ("overrides", "field", "expected"),
    [
        ({"username": ""}, "username", "This field is required."),
        (
            {"username": "bad name!"},
            "username",
            "Enter a valid username. This value may contain only letters, numbers, "
            "and @/./+/-/_ characters.",
        ),
        ({"username": "Kasun.IT"}, "username", "A user with that username already exists."),
        ({"email": ""}, "email", EMAIL_REQUIRED),
        ({"email": "KASUN.IT@polymath.example"}, "email", EMAIL_TAKEN),
        ({"password2": "Different-9pass"}, "password2", "The two password fields didn’t match."),
        (
            {"password1": "12345678", "password2": "12345678"},
            "password2",
            "This password is too common.",
        ),
        (
            {"password1": "12345678", "password2": "12345678"},
            "password2",
            "This password is entirely numeric.",
        ),
    ],
)
def test_add_validation_errors_save_nothing_and_keep_typed_values(
    manager_client, it_user, overrides, field, expected
):
    before = User.objects.count()
    data = _add_data(**overrides)
    response = manager_client.post(STAFF_ADD, data)
    assert response.status_code == 200
    assert User.objects.count() == before
    assert expected in response.context["form"].errors[field]
    content = response.content.decode()
    assert "We couldn't save this person yet." in html.unescape(content)
    for name in ("first_name", "last_name", "username", "email"):
        if data.get(name):
            assert f'value="{data[name]}"' in _input_tag(content, name), name
    for name in ("password1", "password2"):
        assert "value=" not in _input_tag(content, name)


def test_staff_manager_cannot_grant_full_access_with_a_crafted_post(manager_client):
    response = manager_client.post(STAFF_ADD, _add_data(is_superuser="on"))
    assert response.status_code == 302
    assert not User.objects.get(username="chamari.b").is_superuser


# --------------------------------------------------------------------------- criteria 11–12


def test_change_form_has_criterion_12_fields_copy_and_context(
    manager_client, staff_manager, plain_user
):
    response = manager_client.get(_edit(plain_user))
    form = response.context["form"]
    assert isinstance(form, StaffChangeForm)
    assert list(form.fields) == [
        "first_name",
        "last_name",
        "username",
        "email",
        "groups",
        "is_active",
    ]
    assert form.fields["is_active"].label == "Can sign in"
    assert form.fields["is_active"].help_text == (
        "Untick this to switch them off. They can't sign in until someone ticks it again. "
        "Their past work stays."
    )
    assert response.context["person"] == plain_user
    assert response.context["user"] == staff_manager, "the viewer, not the person being changed"
    assert response.context["is_add"] is False
    assert response.context["roles_read_only"] is False
    assert [e["choice"].data["selected"] for e in response.context["roles"]] == [False, False]
    content = response.content.decode()
    assert _set_password(plain_user) in content
    assert "autofocus" not in _input_tag(content, "username")
    assert 'autocomplete="off"' in _input_tag(content, "email")


def test_change_form_for_a_superuser_includes_full_access(super_client, it_user):
    form = super_client.get(_edit(it_user)).context["form"]
    assert "is_superuser" in form.fields
    assert form.fields["is_superuser"].label == "Full access to everything"


def test_change_saves_and_says_so(manager_client, plain_user):
    staff_managers = Group.objects.get(name="Staff managers")
    data = _edit_data(plain_user, first_name="Dilani R", groups=[str(staff_managers.pk)])
    response = manager_client.post(_edit(plain_user), data)
    assert response.status_code == 302
    assert response.url == STAFF
    plain_user.refresh_from_db()
    assert plain_user.first_name == "Dilani R"
    assert list(plain_user.groups.all()) == [staff_managers]
    assert _flashes(response) == ["Saved Dilani R Jayasuriya."]


def test_change_rejects_an_email_someone_else_uses_but_keeps_your_own(manager_client, plain_user):
    response = manager_client.post(
        _edit(plain_user), _edit_data(plain_user, email="MANAGER@polymath.example")
    )
    assert response.status_code == 200
    assert response.context["form"].errors["email"] == [EMAIL_TAKEN]
    response = manager_client.post(
        _edit(plain_user), _edit_data(plain_user, email="TEACHER@polymath.example")
    )
    assert response.status_code == 302


def test_change_rejects_a_username_taken_in_another_letter_case(manager_client, plain_user):
    response = manager_client.post(_edit(plain_user), _edit_data(plain_user, username="MANAGER"))
    assert response.status_code == 200
    assert response.context["form"].errors["username"] == [
        "A user with that username already exists."
    ]


def test_change_page_heading_names_the_person_as_saved_after_an_error(manager_client, plain_user):
    response = manager_client.post(
        _edit(plain_user), _edit_data(plain_user, first_name="Typed", email="")
    )
    assert response.status_code == 200
    assert str(response.context["person"]) == "Dilani Jayasuriya"


# --------------------------------------------------------------------------- criterion 13


def _assert_refused(response, person, field, message):
    assert response.status_code == 200
    assert response.context["form"].errors[field] == [message]
    fresh = User.objects.get(pk=person.pk)
    assert fresh.first_name == person.first_name, "nothing is saved"
    assert (fresh.is_active, fresh.is_superuser) == (person.is_active, person.is_superuser)


def test_you_cannot_switch_off_your_own_sign_in(manager_client, staff_manager):
    data = _edit_data(staff_manager, first_name="Changed", is_active=None)
    response = manager_client.post(_edit(staff_manager), data)
    _assert_refused(response, staff_manager, "is_active", OWN_SIGN_IN_ERROR)


def test_a_superuser_cannot_remove_their_own_full_access(super_client, superuser):
    make_user("other.head", is_superuser=True)
    data = _edit_data(superuser, first_name="Changed", is_superuser=None)
    response = super_client.post(_edit(superuser), data)
    _assert_refused(response, superuser, "is_superuser", OWN_FULL_ACCESS_ERROR)


def test_the_only_superuser_cannot_switch_themselves_off(super_client, superuser):
    data = _edit_data(superuser, is_active=None)
    response = super_client.post(_edit(superuser), data)
    _assert_refused(response, superuser, "is_active", OWN_SIGN_IN_ERROR)


def test_a_superuser_can_switch_off_or_demote_another_superuser(super_client):
    other = make_user("other.head", is_superuser=True)
    response = super_client.post(_edit(other), _edit_data(other, is_active=None, is_superuser=None))
    assert response.status_code == 302
    other.refresh_from_db()
    assert not other.is_active and not other.is_superuser


def test_a_staff_managers_is_superuser_post_is_ignored_without_error(manager_client, plain_user):
    response = manager_client.post(_edit(plain_user), _edit_data(plain_user, is_superuser="on"))
    assert response.status_code == 302
    plain_user.refresh_from_db()
    assert not plain_user.is_superuser


def test_a_staff_manager_editing_themselves_keeps_their_roles_and_access(
    manager_client, staff_manager
):
    response = manager_client.post(_edit(staff_manager), _edit_data(staff_manager))
    assert response.status_code == 302


# --------------------------------------------------------------------------- criterion 14


def test_switching_someone_off_ends_their_sign_in_and_session_but_not_their_history(
    desk_manager_client, it_user
):
    from apps.zoom.models import LinkRequest
    from apps.zoom.tests.conftest import make_request

    decided = make_request(
        status=LinkRequest.Status.REJECTED, decided_by=it_user, rejection_reason="Full."
    )
    their_client = Client()
    their_client.force_login(it_user)
    assert their_client.get(reverse("zoom:queue")).status_code == 200

    response = desk_manager_client.post(_edit(it_user), _edit_data(it_user, is_active=None))
    assert response.status_code == 302
    it_user.refresh_from_db()
    assert not it_user.is_active

    queue = reverse("zoom:queue")
    refused = their_client.get(queue)
    assert refused.status_code == 302
    assert refused.url == f"{LOGIN}?next={queue}"
    assert not Client().login(username="kasun.it", password="pw")
    sign_in = Client().post(LOGIN, {"username": "kasun.it", "password": "pw"})
    assert sign_in.status_code == 200
    assert "We couldn&rsquo;t sign you in" in sign_in.content.decode()
    decided.refresh_from_db()
    assert decided.decided_by_id == it_user.pk

    desk_manager_client.post(_edit(it_user), _edit_data(it_user, is_active="on"))
    it_user.refresh_from_db()
    assert it_user.is_active
    assert Client().login(username="kasun.it", password="pw")


def _all_url_names(patterns=None, namespace=""):
    names = []
    for pattern in patterns if patterns is not None else get_resolver().url_patterns:
        if hasattr(pattern, "url_patterns"):
            inner = f"{namespace}{pattern.namespace}:" if pattern.namespace else namespace
            names += _all_url_names(pattern.url_patterns, inner)
        elif pattern.name:
            names.append(f"{namespace}{pattern.name}")
    return names


def test_there_is_no_delete_url_and_no_role_editor():
    """Criteria 14 and 18: people are switched off, not deleted; roles are migrations."""
    names = _all_url_names()
    assert "accounts:staff" in names
    accounts = [name for name in names if name.startswith("accounts:")]
    assert not [name for name in accounts if "delete" in name]
    assert not [name for name in names if "group" in name or "role" in name]


def test_no_staff_page_has_a_delete_button(super_client, it_user):
    for url in (STAFF, _edit(it_user), _set_password(it_user)):
        content = super_client.get(url).content.decode()
        assert not re.search(r"<(button|a)\b[^>]*>[^<]*(?i:delete)", content), url


# --------------------------------------------------------------------------- criterion 15


def test_setting_a_new_password_signs_them_out_and_returns_to_their_page(
    desk_manager_client, it_user
):
    their_client = Client()
    their_client.force_login(it_user)
    assert their_client.get(HOME).status_code == 200

    response = desk_manager_client.get(_set_password(it_user))
    form = response.context["form"]
    assert isinstance(form, StaffSetPasswordForm)
    assert list(form.fields) == ["new_password1", "new_password2"]
    assert form.fields["new_password2"].label == "Type it again"
    assert form.fields["new_password2"].help_text == (
        "Type the new password again, to check for typos."
    )
    assert response.context["person"] == it_user
    content = response.content.decode()
    for name in ("new_password1", "new_password2"):
        assert 'autocomplete="new-password"' in _input_tag(content, name)

    response = desk_manager_client.post(
        _set_password(it_user), {"new_password1": GOOD_PASSWORD, "new_password2": GOOD_PASSWORD}
    )
    assert response.status_code == 302
    assert response.url == _edit(it_user)
    assert _flashes(response) == [
        "Saved a new password for Kasun Fernando. Give it to them yourself, not by email."
    ]
    it_user.refresh_from_db()
    assert it_user.check_password(GOOD_PASSWORD)
    refused = their_client.get(HOME)
    assert refused.status_code == 302
    assert refused.url.startswith(LOGIN)


def test_set_password_errors_are_djangos(desk_manager_client, it_user):
    response = desk_manager_client.post(
        _set_password(it_user), {"new_password1": GOOD_PASSWORD, "new_password2": "nope"}
    )
    assert response.status_code == 200
    assert response.context["form"].errors["new_password2"] == [
        "The two password fields didn’t match."
    ]
    it_user.refresh_from_db()
    assert it_user.check_password("pw")


# --------------------------------------------------------------------------- criterion 16


def test_changing_your_own_password_keeps_you_signed_in(client, plain_user):
    client.force_login(plain_user)
    response = client.get(PASSWORD_CHANGE)
    form = response.context["form"]
    assert isinstance(form, OwnPasswordChangeForm)
    assert form.fields["old_password"].label == "Your current password"
    assert form.fields["old_password"].help_text == "The one you use to sign in now."
    assert form.fields["new_password2"].label == "Type it again"
    content = response.content.decode()
    assert 'autocomplete="current-password"' in _input_tag(content, "old_password")

    response = client.post(
        PASSWORD_CHANGE,
        {"old_password": "pw", "new_password1": GOOD_PASSWORD, "new_password2": GOOD_PASSWORD},
    )
    assert response.status_code == 302
    assert response.url == HOME
    assert _flashes(response) == ["Your password was changed."]
    plain_user.refresh_from_db()
    assert plain_user.check_password(GOOD_PASSWORD)
    assert client.get(HOME).status_code == 200, "still signed in"


def test_a_wrong_current_password_shows_djangos_error(client, plain_user):
    client.force_login(plain_user)
    response = client.post(
        PASSWORD_CHANGE,
        {"old_password": "wrong", "new_password1": GOOD_PASSWORD, "new_password2": GOOD_PASSWORD},
    )
    assert response.status_code == 200
    assert response.context["form"].errors["old_password"] == [
        "Your old password was entered incorrectly. Please enter it again."
    ]


# --------------------------------------------------------------------------- criterion 17


def _password_inputs(content):
    return re.findall(r'<input[^>]*type="password"[^>]*>', content)


def _error_rerenders(manager_client, it_user, client, plain_user):
    """The three password forms, each posted with GOOD_PASSWORD and re-rendered with errors."""
    yield manager_client.post(STAFF_ADD, _add_data(password2="Mismatch-0000"))
    yield manager_client.post(
        _set_password(it_user), {"new_password1": GOOD_PASSWORD, "new_password2": "Mismatch-0000"}
    )
    client.force_login(plain_user)
    yield client.post(
        PASSWORD_CHANGE,
        {
            "old_password": GOOD_PASSWORD,
            "new_password1": GOOD_PASSWORD,
            "new_password2": GOOD_PASSWORD,
        },
    )


def test_no_password_comes_back_in_an_error_page(desk_manager_client, it_user, plain_user):
    other = Client()
    for response in _error_rerenders(desk_manager_client, it_user, other, plain_user):
        assert response.status_code == 200
        content = response.content.decode()
        assert GOOD_PASSWORD not in content
        inputs = _password_inputs(content)
        assert len(inputs) >= 2
        assert not [tag for tag in inputs if "value=" in tag]


def test_no_log_record_carries_a_typed_password(caplog, desk_manager_client, it_user, plain_user):
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger="django")
    other = Client()
    list(_error_rerenders(desk_manager_client, it_user, other, plain_user))
    desk_manager_client.post(STAFF_ADD, _add_data())
    desk_manager_client.post(
        _set_password(it_user), {"new_password1": GOOD_PASSWORD, "new_password2": GOOD_PASSWORD}
    )
    other.post(
        PASSWORD_CHANGE,
        {"old_password": "pw", "new_password1": GOOD_PASSWORD, "new_password2": GOOD_PASSWORD},
    )
    assert User.objects.get(username="chamari.b").check_password(GOOD_PASSWORD)
    for record in caplog.records:
        assert GOOD_PASSWORD not in record.getMessage()
        assert GOOD_PASSWORD not in repr(record.args)


@pytest.mark.parametrize("url_name", ["staff_add", "staff_password", "password_change"])
def test_password_views_mark_every_post_parameter_sensitive(desk_manager_client, it_user, url_name):
    url = (
        _set_password(it_user) if url_name == "staff_password" else reverse(f"accounts:{url_name}")
    )
    response = desk_manager_client.post(url, {"x": "y"})
    assert response.wsgi_request.sensitive_post_parameters == "__ALL__"


def test_field_partial_never_writes_a_password_value():
    from django.conf import settings

    source = (settings.BASE_DIR / "templates" / "partials" / "field.html").read_text("utf-8")
    assert 'field.widget_type != "password"' in source
