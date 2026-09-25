"""Shared fixtures for the accounts tests (brief 010).

The people in these tests match the brief's terms: a **superuser**, a **staff manager** (only
the ``Staff managers`` role; "SM" in criteria 31–35), a **desk manager** (``Staff managers``
and ``IT desk``; "SM+IT"), an **IT user** (only ``IT desk``), a **plain user** (no roles) and
a user with ``is_staff=True`` but no permissions, which now means nothing (D5).

Since review round 1 a staff manager can only manage people whose rights they hold (D13), so
tests that change an IT user do it as the desk manager, and tests that only need "someone
else" use the plain user.

Unlike ``apps/zoom/tests``, these tests render the real templates: criteria 17 and 28 are
about what the rendered page does and doesn't contain (no typed password, no permission
codename), so a stub would prove nothing.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

# A password that passes every AUTH_PASSWORD_VALIDATORS rule and has no HTML-escaped
# characters, so a plain text search of a response body is reliable (criterion 17).
GOOD_PASSWORD = "Tr0ub4dor-3xyz-Q"


def make_user(username, *, groups=(), password="pw", **fields):
    fields.setdefault("email", f"{username}@polymath.example")
    user = get_user_model().objects.create_user(username=username, password=password, **fields)
    if groups:
        user.groups.add(*Group.objects.filter(name__in=groups))
    return user


@pytest.fixture
def superuser(db):
    return get_user_model().objects.create_superuser(
        username="head",
        password="pw",
        email="head@polymath.example",
        first_name="Ruwan",
        last_name="Silva",
    )


@pytest.fixture
def staff_manager(db):
    return make_user("manager", groups=["Staff managers"], first_name="Nimali", last_name="Perera")


@pytest.fixture
def desk_manager(db):
    """SM+IT in criteria 31–35: a Staff manager who is also in ``IT desk``, so they may give
    ``IT desk`` and manage people who hold it (D13)."""
    return make_user(
        "desk.manager",
        groups=["Staff managers", "IT desk"],
        first_name="Sunil",
        last_name="Ranasinghe",
    )


@pytest.fixture
def it_user(db):
    return make_user("kasun.it", groups=["IT desk"], first_name="Kasun", last_name="Fernando")


@pytest.fixture
def plain_user(db):
    return make_user("teacher", first_name="Dilani", last_name="Jayasuriya")


@pytest.fixture
def staff_flag_user(db):
    """``is_staff`` without any permission: sees no Administration group (criterion 3)."""
    return make_user("staffer", is_staff=True)


@pytest.fixture
def manager_client(client, staff_manager):
    client.force_login(staff_manager)
    return client


@pytest.fixture
def desk_manager_client(client, desk_manager):
    client.force_login(desk_manager)
    return client


@pytest.fixture
def super_client(client, superuser):
    client.force_login(superuser)
    return client
