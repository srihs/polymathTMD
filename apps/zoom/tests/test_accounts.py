"""The Zoom accounts screens and their model rules (brief 008).

Criteria covered here: 1-2 (permissions), 4-8 (the list, as far as the view layer goes),
9-15 (add and change), 16-19 (stopping bookings, and its row lock), 20-23 (no delete, the key
record, email and uniqueness, no admin), 24 (every page renders without key material, against
the real templates) and 25 (the old admin copy is gone). Criteria 1's migration test and
24's logging and error-report tests live in ``test_views.py`` and ``test_review_fixes.py``,
next to the brief-005 tests they replace.

Frozen "now" is brief 005's: Mon 28 Sep 2026, 10:00 Colombo (see ``conftest.py``). Most tests
use the stub page templates from ``conftest.py``; the ones that render real pages say so.
"""

import re
from datetime import date, datetime, time
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.core import mail
from django.db import connection
from django.db.models import ProtectedError
from django.test.utils import CaptureQueriesContext
from django.urls import NoReverseMatch, reverse

from apps.zoom import urls as zoom_urls
from apps.zoom.forms import HostAccountForm
from apps.zoom.models import (
    HostAccount,
    HostSlot,
    LinkRequest,
    Occurrence,
    is_bookable_with,
)

from .conftest import COLOMBO, FROZEN_NOW, book, make_account, make_request
from .test_sidebar_zoom_group import _real_templates

pytestmark = pytest.mark.django_db

HOST_KEY = "8421973"
APPROVED = LinkRequest.Status.APPROVED
ZOOM_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = Path(django_settings.BASE_DIR) / "templates" / "zoom"


# --------------------------------------------------------------------------- helpers


def _messages(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


def _data(account=None, **overrides):
    """A complete POST for the account form: the account's stored values, or a new one."""
    data = {
        "label": account.label if account else "Zoom 05",
        "email": account.email if account else "zoom05@polymath.edu.lk",
        "notes": account.notes if account else "",
        "is_paid": "on",
        "is_active": "on",
        "sort_order": account.sort_order if account else 5,
        "host_key": "",
    }
    data.update(overrides)
    return {key: value for key, value in data.items() if value is not None}


def _edit(account):
    return reverse("zoom:account_edit", args=[account.pk])


def classes_on(account, *, status=APPROVED, **schedule):
    """A request with the given status whose classes are all on ``account``.

    Written directly rather than through ``services.approve()``, so past and in-progress
    classes can be set up (approval refuses those) and waiting or rejected requests can carry
    an account too, which proves the status filter.
    """
    extra = {}
    if status == APPROVED:
        extra = {"host_account": account, "join_url": "https://us02web.zoom.us/j/12345678901"}
    elif status == LinkRequest.Status.REJECTED:
        extra = {"rejection_reason": "Use Grade 10."}
    link_request = make_request(status=status, **schedule, **extra)
    link_request.occurrences.update(host_account=account)
    return link_request


def twelve_classes(account):
    """12 upcoming classes, the first Mon 28 Sep 2026 (in progress), the last Wed 28 Oct."""
    classes_on(
        account,
        first_date=date(2026, 9, 28),
        start=time(9, 0),
        end=time(11, 0),
        weekdays="1,3",
        last_date=date(2026, 10, 28),
    )  # 10 classes, Mondays and Wednesdays
    classes_on(account, first_date=date(2026, 9, 29))
    classes_on(account, first_date=date(2026, 10, 1))
    assert account.upcoming_classes().count() == 12


def _user_with(*codenames, username="viewer"):
    user = get_user_model().objects.create_user(username=username, password="pw")
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="zoom", codename__in=codenames)
    )
    return user


@pytest.fixture
def viewer(db):
    """The key-less viewer: a test-only user holding just ``zoom.view_hostaccount``."""
    return _user_with("view_hostaccount")


@pytest.fixture
def zoom03(db):
    return make_account("Zoom 03", sort_order=3, host_key=HOST_KEY)


# --------------------------------------------------------------------------- 1-2 access


PAGES = ["zoom:accounts", "zoom:account_add", "zoom:account_edit"]


def _url(page, account):
    return _edit(account) if page == "zoom:account_edit" else reverse(page)


@pytest.mark.parametrize("page", PAGES)
def test_anonymous_visitors_are_sent_to_sign_in(client, account, page):
    url = _url(page, account)
    response = client.get(url)
    assert response.status_code == 302
    assert response.url == f"{reverse('accounts:login')}?next={url}"


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("who", ["plain_user", "staff_user"])
def test_plain_users_get_403_with_or_without_is_staff(client, request, account, page, who):
    client.force_login(request.getfixturevalue(who))
    assert client.get(_url(page, account)).status_code == 403
    assert client.post(_url(page, account), _data(account)).status_code == 403


@pytest.mark.parametrize(("page", "status"), [(PAGES[0], 200), (PAGES[1], 403), (PAGES[2], 403)])
def test_the_key_less_viewer_may_only_see_the_list(client, viewer, account, page, status):
    client.force_login(viewer)
    assert client.get(_url(page, account)).status_code == status


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("who", ["it_user", "superuser"])
def test_it_users_and_superusers_open_every_accounts_page(client, request, account, page, who):
    client.force_login(request.getfixturevalue(who))
    assert client.get(_url(page, account)).status_code == 200


def test_the_viewer_list_has_no_add_button_and_no_name_links(client, viewer, account):
    client.force_login(viewer)
    context = client.get(reverse("zoom:accounts")).context
    assert (context["can_add"], context["can_change"], context["can_review"]) == (
        False,
        False,
        False,
    )


def test_it_users_may_add_change_and_review(it_client, account):
    context = it_client.get(reverse("zoom:accounts")).context
    assert (context["can_add"], context["can_change"], context["can_review"]) == (
        True,
        True,
        True,
    )


def test_unknown_account_is_404(it_client):
    assert it_client.get(reverse("zoom:account_edit", args=[999999])).status_code == 404


# --------------------------------------------------------------------------- 4-8 the list


def test_list_puts_accounts_in_use_first_then_order_then_name(it_client):
    make_account("Zoom 09", sort_order=1, is_active=False)
    make_account("Zoom 02", sort_order=2)
    make_account("Zoom 01", sort_order=2)
    make_account("Zoom 07", sort_order=1)
    make_account("Zoom 04", sort_order=0, is_active=False)
    accounts = it_client.get(reverse("zoom:accounts")).context["accounts"]
    assert [a.label for a in accounts] == ["Zoom 07", "Zoom 01", "Zoom 02", "Zoom 04", "Zoom 09"]


def test_list_page_chrome_and_table_markup_on_real_templates(client, settings, it_user, account):
    """Criterion 4: h1, title, breadcrumb, and the table's caption and column headers.

    Rendered with the real ``accounts.html`` (``conftest.py`` otherwise stubs it), because
    the pinned heading, breadcrumb and table structure only exist in that template.
    """
    _real_templates(settings)
    client.force_login(it_user)
    html = client.get(reverse("zoom:accounts")).content.decode()

    assert "<title>Zoom accounts · " in html
    assert '<h1 class="page-heading">Zoom accounts</h1>' in html
    assert '<span aria-current="page">Zoom accounts</span>' in html
    assert '<caption class="visually-hidden">Zoom accounts, those in use first</caption>' in html
    columns = ["Name", "Zoom sign-in email", "Type", "In use", "Host key", "Upcoming classes"]
    headers = re.findall(r'<th scope="col"[^>]*>([^<]+)</th>', html)
    assert headers == columns


def test_empty_list_real_template_shows_pinned_copy_and_add_button(client, settings, it_user):
    """Criterion 7: the exact empty-state wording, and the Add button for add_hostaccount."""
    _real_templates(settings)
    client.force_login(it_user)
    html = client.get(reverse("zoom:accounts")).content.decode()
    assert "No Zoom accounts yet." in html
    assert "Add a Zoom account" in html
    assert "Accounts (0)" in html


def test_upcoming_figures_count_booked_classes_that_have_not_ended(it_client, account):
    """Criterion 5: ended, in-progress, future, waiting and rejected classes on one account."""
    classes_on(account, first_date=date(2026, 9, 27), start=time(9, 0), end=time(11, 0))
    classes_on(account, first_date=date(2026, 9, 28), start=time(9, 0), end=time(11, 0))
    classes_on(account, first_date=date(2026, 10, 5), start=time(8, 30), end=time(11, 30))
    classes_on(account, status=LinkRequest.Status.WAITING, first_date=date(2026, 10, 6))
    classes_on(account, status=LinkRequest.Status.REJECTED, first_date=date(2026, 10, 7))
    idle = make_account("Zoom 02", sort_order=2)

    accounts = list(it_client.get(reverse("zoom:accounts")).context["accounts"])
    row = next(a for a in accounts if a.pk == account.pk)
    assert row.upcoming_count == 2
    assert row.next_class_start == datetime(2026, 9, 28, 9, 0, tzinfo=COLOMBO)
    idle_row = next(a for a in accounts if a.pk == idle.pk)
    assert (idle_row.upcoming_count, idle_row.next_class_start) == (0, None)


def test_list_query_count_does_not_grow_with_accounts_or_classes(it_client):
    """Criterion 6: 2 accounts, then 15 with 3 upcoming classes each, same query count."""
    url = reverse("zoom:accounts")
    for n in range(1, 3):
        make_account(f"Zoom {n:02d}", sort_order=n)
    it_client.get(url)  # warm up per-process caches (content types)
    with CaptureQueriesContext(connection) as small:
        assert len(it_client.get(url).context["accounts"]) == 2

    for n in range(3, 16):
        make_account(f"Zoom {n:02d}", sort_order=n)
    for account in HostAccount.objects.all():
        classes_on(
            account,
            first_date=date(2026, 10, 5),
            weekdays="1",
            last_date=date(2026, 10, 19),
        )
    with CaptureQueriesContext(connection) as large:
        accounts = it_client.get(url).context["accounts"]
        assert len(accounts) == 15
        assert {a.upcoming_count for a in accounts} == {3}
    assert len(large) == len(small)


def test_empty_list(it_client):
    context = it_client.get(reverse("zoom:accounts")).context
    assert list(context["accounts"]) == []
    assert context["can_add"] is True


# --------------------------------------------------------------------------- 9 the add form


def test_add_form_fields_order_labels_and_widgets(it_client):
    response = it_client.get(reverse("zoom:account_add"))
    context = response.context
    form = context["form"]
    assert (context["is_add"], context["account"], context["host_key_state"]) == (
        True,
        None,
        "none",
    )
    assert list(form.fields) == [
        "label",
        "email",
        "notes",
        "is_paid",
        "is_active",
        "sort_order",
        "host_key",
    ]
    assert "credential_set" not in form.fields
    assert "remove_host_key" not in form.fields
    labels = {name: field.label for name, field in form.fields.items()}
    assert labels == {
        "label": "Name",
        "email": "Zoom sign-in email",
        "notes": "Notes",
        "is_paid": "Paid account",
        "is_active": "In use",
        "sort_order": "Order",
        "host_key": "Host key",
    }
    assert all(field.help_text for field in form.fields.values())
    assert form["is_paid"].value() is True and form["is_active"].value() is True
    assert form["host_key"].value() is None
    assert form.fields["email"].widget.input_type == "email"
    assert form.fields["email"].widget.attrs["autocomplete"] == "off"
    assert form.fields["email"].widget.attrs["spellcheck"] == "false"
    assert form.fields["label"].widget.attrs == {"autocomplete": "off", "maxlength": "60"}
    sort_attrs = form.fields["sort_order"].widget.attrs
    assert (str(sort_attrs["min"]), sort_attrs["step"], sort_attrs["inputmode"]) == (
        "0",
        "1",
        "numeric",
    )
    key_attrs = form.fields["host_key"].widget.attrs
    assert key_attrs == {
        "autocomplete": "off",
        "inputmode": "numeric",
        "spellcheck": "false",
        "maxlength": "10",
    }
    assert form.key_was_typed is False


# --------------------------------------------------------------------------- 10 create


def test_adding_an_account_encrypts_the_key_and_records_who(it_client, it_user):
    response = it_client.post(
        reverse("zoom:account_add"),
        _data(label="Zoom 05", email="  Zoom05@Polymath.EDU.lk ", host_key=HOST_KEY),
    )
    assert response.status_code == 302
    assert response.url == reverse("zoom:accounts")
    assert _messages(response) == ["Added Zoom 05."]
    account = HostAccount.objects.get(label="Zoom 05")
    assert account.email == "zoom05@polymath.edu.lk"
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT host_key_encrypted FROM zoom_hostaccount WHERE id = %s", [account.pk]
        )
        [raw] = cursor.fetchone()
    assert raw.startswith("gAAAAA") and HOST_KEY not in raw
    assert account.get_host_key() == HOST_KEY
    assert (account.host_key_changed_at, account.host_key_changed_by) == (FROZEN_NOW, it_user)


def test_adding_an_account_without_a_key(it_client):
    response = it_client.post(reverse("zoom:account_add"), _data())
    assert response.status_code == 302
    account = HostAccount.objects.get()
    assert account.has_host_key is False
    assert account.host_key_changed_at is None and account.host_key_changed_by is None


# --------------------------------------------------------------------------- 11 validation


LABEL_TAKEN = "Another Zoom account already has this name. Choose a different one."
EMAIL_BAD = "Type the email address this Zoom account signs in with, like zoom01@polymath.edu.lk."
EMAIL_TAKEN = "Another Zoom account already signs in with this email address."
KEY_BAD = "A Zoom host key is 6 to 10 digits."


@pytest.mark.parametrize(
    ("overrides", "field", "error"),
    [
        ({"label": ""}, "label", "Type a short name for the account, like Zoom 01."),
        ({"label": "   "}, "label", "Type a short name for the account, like Zoom 01."),
        ({"label": "zoom 01"}, "label", LABEL_TAKEN),
        ({"label": "ZOOM 01"}, "label", LABEL_TAKEN),
        ({"email": "not-an-email"}, "email", EMAIL_BAD),
        ({"email": ""}, "email", EMAIL_BAD),
        ({"email": "Zoom01@Polymath.Example"}, "email", EMAIL_TAKEN),
        ({"email": " ZOOM01@POLYMATH.EXAMPLE "}, "email", EMAIL_TAKEN),
        ({"host_key": "12345"}, "host_key", KEY_BAD),
        ({"host_key": "12ab567"}, "host_key", KEY_BAD),
        ({"host_key": "12345678901"}, "host_key", KEY_BAD),
        ({"sort_order": "-1"}, "sort_order", None),
        ({"sort_order": "first"}, "sort_order", None),
    ],
)
def test_invalid_add_saves_nothing_and_says_how_to_fix_it(
    it_client, account, overrides, field, error
):
    """``account`` is "Zoom 01" / "zoom01@polymath.example"; the checks ignore letter case."""
    response = it_client.post(reverse("zoom:account_add"), _data(**overrides))
    assert response.status_code == 200
    assert HostAccount.objects.count() == 1
    errors = response.context["form"].errors
    assert list(errors) == [field]
    if error is not None:
        assert errors[field] == [error]


def test_uniqueness_ignores_letter_case_in_the_model_too(account):
    """Criterion 22: proved through ``validate_unique``, never by catching IntegrityError.

    The MySQL collation (utf8mb4_0900_ai_ci) compares case-insensitively, so Django's own
    unique check already finds ``zoom 01`` when ``Zoom 01`` exists.
    """
    from django.core.exceptions import ValidationError

    twin = HostAccount(label="zoom 01", email="ZOOM01@polymath.example")
    with pytest.raises(ValidationError) as caught:
        twin.full_clean()
    assert set(caught.value.message_dict) == {"label", "email"}


# --------------------------------------------------------------------------- 12 no echo


@pytest.mark.parametrize(
    "overrides",
    [
        {"label": "", "host_key": "5566778"},  # a valid key, another field wrong
        {"host_key": "5566"},  # the key itself wrong
    ],
)
def test_a_typed_key_is_never_sent_back(it_client, overrides):
    typed = overrides["host_key"]
    response = it_client.post(
        reverse("zoom:account_add"), _data(notes="Renews in May", **overrides)
    )
    assert response.status_code == 200
    form = response.context["form"]
    assert form.key_was_typed is True
    assert form["host_key"].value() is None
    assert form["notes"].value() == "Renews in May"  # everything else is kept
    assert typed not in response.content.decode()
    assert 'name="host_key"' in response.content.decode()


def test_no_key_typed_means_no_note(it_client):
    form = it_client.post(reverse("zoom:account_add"), _data(label="")).context["form"]
    assert form.key_was_typed is False


# --------------------------------------------------------------------------- 13 the change form


def test_change_form_context_and_host_key_copy(it_client, it_user, zoom03):
    response = it_client.get(_edit(zoom03))
    context = response.context
    form = context["form"]
    assert context["account"] == zoom03
    assert context["is_add"] is False
    assert context["saved_label"] == "Zoom 03"
    assert context["host_key_state"] == "saved"
    assert (context["upcoming_count"], context["next_class_start"]) == (0, None)
    assert form["label"].value() == "Zoom 03"
    assert form["host_key"].value() is None
    assert form.fields["host_key"].label == "New host key"
    assert form.fields["host_key"].help_text == "Leave it empty to keep the saved key."
    assert form.fields["remove_host_key"].label == "Remove the saved host key"
    assert list(form.fields)[-2:] == ["host_key", "remove_host_key"]
    assert HOST_KEY not in response.content.decode()


def test_change_form_without_a_key_has_no_remove_box(it_client):
    account = make_account("Zoom 04")
    form = it_client.get(_edit(account)).context["form"]
    assert "remove_host_key" not in form.fields
    assert form.fields["host_key"].help_text == (
        "Type the 6 to 10 digits from the account's Zoom profile."
    )


def test_host_key_state_covers_saved_legacy_none_and_unreadable(settings, it_user):
    saved = make_account("Zoom 01", host_key=HOST_KEY)
    assert saved.host_key_state == "saved"
    HostAccount.objects.filter(pk=saved.pk).update(host_key_changed_at=None)
    saved.refresh_from_db()
    assert saved.host_key_state == "saved_legacy"
    assert make_account("Zoom 02").host_key_state == "none"
    settings.HOST_KEY_ENCRYPTION_KEYS = [Fernet.generate_key().decode()]
    assert saved.host_key_state == "unreadable"


def test_change_context_names_the_stored_account_after_an_invalid_post(it_client, zoom03):
    """G3: the heading keeps the saved name even when the typed one is empty or taken."""
    make_account("Zoom 04")
    response = it_client.post(_edit(zoom03), _data(zoom03, label="Zoom 04"))
    assert response.status_code == 200
    assert response.context["form"].errors["label"] == [LABEL_TAKEN]
    assert response.context["saved_label"] == "Zoom 03"


def test_change_context_has_the_upcoming_figures(it_client, zoom03):
    """G4: the facts behind the booked-classes note."""
    twelve_classes(zoom03)
    context = it_client.get(_edit(zoom03)).context
    assert context["upcoming_count"] == 12
    assert context["next_class_start"] == datetime(2026, 9, 28, 9, 0, tzinfo=COLOMBO)


# --------------------------------------------------------------------------- 14 saving


def test_saving_without_touching_the_key_keeps_it_byte_for_byte(it_client, zoom03, superuser):
    HostAccount.objects.filter(pk=zoom03.pk).update(host_key_changed_by=superuser)
    zoom03.refresh_from_db()
    before = (zoom03.host_key_encrypted, zoom03.host_key_changed_at, zoom03.host_key_changed_by)
    response = it_client.post(_edit(zoom03), _data(zoom03, notes="Renews in May"))
    assert response.status_code == 302 and response.url == reverse("zoom:accounts")
    assert _messages(response) == ["Saved Zoom 03."]
    zoom03.refresh_from_db()
    assert zoom03.notes == "Renews in May"
    assert (
        zoom03.host_key_encrypted,
        zoom03.host_key_changed_at,
        zoom03.host_key_changed_by,
    ) == before


def test_saving_a_new_key_replaces_it_and_records_who(it_client, it_user, zoom03):
    response = it_client.post(_edit(zoom03), _data(zoom03, host_key="7654321"))
    assert response.status_code == 302
    assert _messages(response) == [
        "Saved Zoom 03. The new host key goes out with the next approved link."
    ]
    zoom03.refresh_from_db()
    assert zoom03.get_host_key() == "7654321"
    assert (zoom03.host_key_changed_at, zoom03.host_key_changed_by) == (FROZEN_NOW, it_user)


def test_removing_the_key(it_client, it_user, zoom03):
    HostAccount.objects.filter(pk=zoom03.pk).update(host_key_changed_at=None)
    response = it_client.post(_edit(zoom03), _data(zoom03, remove_host_key="on"))
    assert response.status_code == 302
    assert _messages(response) == ["Saved Zoom 03. Its host key was removed."]
    zoom03.refresh_from_db()
    assert zoom03.has_host_key is False
    assert (zoom03.host_key_changed_at, zoom03.host_key_changed_by) == (FROZEN_NOW, it_user)


def test_a_new_key_and_remove_together_are_refused(it_client, zoom03):
    before = zoom03.host_key_encrypted
    response = it_client.post(
        _edit(zoom03), _data(zoom03, host_key="7654321", remove_host_key="on", notes="x")
    )
    assert response.status_code == 200
    assert response.context["form"].errors["host_key"] == [
        "Type a new host key or tick Remove, not both."
    ]
    assert "7654321" not in response.content.decode()
    zoom03.refresh_from_db()
    assert (zoom03.host_key_encrypted, zoom03.notes) == (before, "")


# --------------------------------------------------------------------------- 15 unreadable


def test_an_unreadable_key_still_opens_and_can_be_replaced(it_client, zoom03, settings):
    settings.HOST_KEY_ENCRYPTION_KEYS = [Fernet.generate_key().decode()]
    response = it_client.get(_edit(zoom03))
    assert response.status_code == 200
    assert response.context["host_key_state"] == "unreadable"
    assert "remove_host_key" in response.context["form"].fields
    response = it_client.post(_edit(zoom03), _data(zoom03, host_key="7654321"))
    assert response.status_code == 302
    zoom03.refresh_from_db()
    assert zoom03.get_host_key() == "7654321"
    assert zoom03.host_key_state == "saved"


# --------------------------------------------------------------------------- 16-17 the block


def test_bookable_is_defined_once_for_the_database_and_for_unsaved_flags():
    assert is_bookable_with(is_active=True, is_paid=True) is True
    assert is_bookable_with(is_active=False, is_paid=True) is False
    assert is_bookable_with(is_active=True, is_paid=False) is False


def test_upcoming_classes_are_booked_not_ended_and_soonest_first(account):
    classes_on(account, first_date=date(2026, 9, 27), start=time(9, 0), end=time(11, 0))
    later = classes_on(account, first_date=date(2026, 10, 5))
    now = classes_on(account, first_date=date(2026, 9, 28), start=time(9, 0), end=time(11, 0))
    classes_on(account, status=LinkRequest.Status.WAITING, first_date=date(2026, 10, 2))
    upcoming = list(account.upcoming_classes())
    assert [o.link_request_id for o in upcoming] == [now.pk, later.pk]
    assert Occurrence.objects.upcoming().count() == 3  # upcoming() alone ignores status
    assert account.stop_booking_errors(is_active=True, is_paid=True) == {}


MANY_ACTIVE = (
    "Zoom 03 still has 12 booked classes, from Mon 28 Sep 2026 to Wed 28 Oct 2026. It can be "
    "taken out of use once the last one has finished."
)
MANY_PAID = (
    "Zoom 03 still has 12 booked classes, from Mon 28 Sep 2026 to Wed 28 Oct 2026. It can be "
    "marked as free once the last one has finished."
)


@pytest.mark.parametrize(
    ("unticked", "expected"),
    [
        ({"is_active": None}, {"is_active": [MANY_ACTIVE]}),
        ({"is_paid": None}, {"is_paid": [MANY_PAID]}),
        (
            {"is_active": None, "is_paid": None},
            {"is_paid": [MANY_PAID], "is_active": [MANY_ACTIVE]},
        ),
    ],
)
def test_stopping_bookings_is_refused_while_classes_are_booked(
    it_client, zoom03, unticked, expected
):
    twelve_classes(zoom03)
    before = HostAccount.objects.values().get(pk=zoom03.pk)
    response = it_client.post(
        _edit(zoom03),
        _data(zoom03, notes="Subscription ends", label="Zoom 03b", host_key="7654321", **unticked),
    )
    assert response.status_code == 200
    form = response.context["form"]
    assert dict(form.errors) == expected
    assert HostAccount.objects.values().get(pk=zoom03.pk) == before  # nothing saved
    assert form["notes"].value() == "Subscription ends"  # typed values kept...
    assert form["label"].value() == "Zoom 03b"
    for name in unticked:
        assert form[name].value() is False
    assert form["host_key"].value() is None  # ...except the key
    assert "7654321" not in response.content.decode()
    assert response.context["saved_label"] == "Zoom 03"


def test_one_upcoming_class_is_worded_in_the_singular(it_client, zoom03):
    classes_on(zoom03, first_date=date(2026, 10, 5))
    response = it_client.post(_edit(zoom03), _data(zoom03, is_active=None, is_paid=None))
    assert response.context["form"].errors == {
        "is_paid": [
            "Zoom 03 still has 1 booked class, on Mon 5 Oct 2026. It can be marked as free "
            "once it has finished."
        ],
        "is_active": [
            "Zoom 03 still has 1 booked class, on Mon 5 Oct 2026. It can be taken out of use "
            "once it has finished."
        ],
    }


def test_the_message_uses_the_stored_name_not_the_typed_one(zoom03):
    classes_on(zoom03, first_date=date(2026, 10, 5))
    form = HostAccountForm(data=_data(zoom03, label="Renamed", is_active=None), instance=zoom03)
    assert not form.is_valid()
    assert form.errors["is_active"][0].startswith("Zoom 03 still has 1 booked class")


def test_an_account_already_out_of_use_can_still_be_edited(it_client, zoom03):
    """Only removing a tick is refused: older data may have classes on an unused account."""
    classes_on(zoom03, first_date=date(2026, 10, 5))
    HostAccount.objects.filter(pk=zoom03.pk).update(is_active=False)
    zoom03.refresh_from_db()
    response = it_client.post(_edit(zoom03), _data(zoom03, is_active=None, notes="Old one"))
    assert response.status_code == 302
    zoom03.refresh_from_db()
    assert zoom03.notes == "Old one"


@pytest.mark.parametrize(
    ("stored", "posted"),
    [
        ({"is_active": False}, {"is_active": None, "is_paid": None}),
        ({"is_paid": False}, {"is_active": None, "is_paid": None}),
    ],
)
def test_an_account_that_was_not_bookable_can_lose_its_other_tick(
    it_client, zoom03, stored, posted
):
    """Review round 1, nit 1: only a change from bookable to not bookable is refused.

    An account already out of use (or already free) with classes from older data can have its
    other tick removed too, and the check doesn't even query its classes.
    """
    classes_on(zoom03, first_date=date(2026, 10, 5))
    HostAccount.objects.filter(pk=zoom03.pk).update(**stored)
    zoom03.refresh_from_db()
    with CaptureQueriesContext(connection) as queries:
        assert zoom03.stop_booking_errors(is_active=False, is_paid=False) == {}
    assert len(queries) == 0
    response = it_client.post(_edit(zoom03), _data(zoom03, **posted))
    assert response.status_code == 302
    zoom03.refresh_from_db()
    assert (zoom03.is_active, zoom03.is_paid) == (False, False)


# --------------------------------------------------------------------------- 18 no block


@pytest.mark.parametrize("unticked", [{"is_active": None}, {"is_paid": None}])
def test_ended_waiting_and_rejected_classes_never_block(it_client, zoom03, unticked):
    classes_on(zoom03, first_date=date(2026, 9, 27), start=time(9, 0), end=time(11, 0))
    classes_on(zoom03, status=LinkRequest.Status.WAITING, first_date=date(2026, 10, 5))
    classes_on(zoom03, status=LinkRequest.Status.REJECTED, first_date=date(2026, 10, 6))
    response = it_client.post(_edit(zoom03), _data(zoom03, **unticked))
    assert response.status_code == 302
    zoom03.refresh_from_db()
    assert not HostAccount.objects.bookable().filter(pk=zoom03.pk).exists()


def test_after_a_stop_the_account_is_not_offered_and_nothing_else_changes(it_client, zoom03):
    classes_on(zoom03, first_date=date(2026, 9, 27), start=time(9, 0), end=time(11, 0))
    waiting = make_request()
    tables = (Occurrence, HostSlot, LinkRequest)
    before = [list(model.objects.order_by("pk").values()) for model in tables]

    response = it_client.post(_edit(zoom03), _data(zoom03, is_active=None))
    assert response.status_code == 302
    assert [list(model.objects.order_by("pk").values()) for model in tables] == before
    assert mail.outbox == []
    assert zoom03 not in HostAccount.objects.bookable()
    availability = HostAccount.objects.availability_for(waiting.occurrences.all())
    assert zoom03.pk not in [account.pk for account, _ in availability]

    # Ticking both back always saves, and the account is offered again.
    response = it_client.post(_edit(zoom03), _data(zoom03, is_active="on", is_paid="on"))
    assert response.status_code == 302
    availability = HostAccount.objects.availability_for(waiting.occurrences.all())
    assert zoom03.pk in [account.pk for account, _ in availability]
    detail = it_client.get(reverse("zoom:detail", args=[waiting.pk]))
    assert zoom03 in [entry["account"] for entry in detail.context["availability"]]


# --------------------------------------------------------------------------- 19 row lock


def test_the_stop_check_and_save_run_under_locks_taken_before_the_update(it_client, zoom03):
    """Criterion 19: FOR UPDATE on the account, then on its classes and requests, then UPDATE."""
    with CaptureQueriesContext(connection) as queries:
        response = it_client.post(_edit(zoom03), _data(zoom03, is_active=None))
    assert response.status_code == 302
    sql = [query["sql"] for query in queries]

    def first(predicate):
        return next(i for i, statement in enumerate(sql) if predicate(statement))

    account_lock = first(
        lambda s: (
            s.startswith("SELECT") and re.search(r"FROM `zoom_hostaccount` WHERE .* FOR UPDATE$", s)
        )
    )
    classes_lock = first(
        lambda s: (
            s.startswith("SELECT")
            and s.endswith("FOR UPDATE OF `zoom_occurrence`, `zoom_linkrequest`")
        )
    )
    update = first(lambda s: s.startswith("UPDATE `zoom_hostaccount`"))
    assert account_lock < classes_lock < update
    # Review round 1, B1: the requests are locked too, so their status is read at its latest
    # committed version, not from a snapshot taken before the account lock was granted.
    # test_race.py proves the interleaving on two connections.
    assert "`zoom_linkrequest`" in sql[classes_lock].split("FOR UPDATE")[1]


def test_approval_refuses_an_account_taken_out_of_use(it_user, zoom03, it_client):
    """The other half of criterion 19: approve() books only bookable accounts, under lock."""
    it_client.post(_edit(zoom03), _data(zoom03, is_active=None))
    from apps.zoom import services

    result = services.approve(make_request().pk, account_id=zoom03.pk, by=it_user)
    assert result.outcome == services.Outcome.CONFLICT


# --------------------------------------------------------------------------- 20 no delete


def test_no_zoom_url_deletes_anything():
    names = [pattern.name for pattern in zoom_urls.urlpatterns]
    assert {"accounts", "account_add", "account_edit"} <= set(names)
    assert not [name for name in names if "delete" in name]


def test_an_account_with_bookings_is_protected(zoom03):
    book(make_request(), zoom03)
    with pytest.raises(ProtectedError):
        zoom03.delete()


# --------------------------------------------------------------------------- 21-22 model


def test_set_host_key_records_when_and_who(it_user):
    account = HostAccount(label="Zoom 01", email="z@polymath.example")
    account.set_host_key("", by=it_user)
    assert (account.host_key_changed_at, account.host_key_changed_by) == (None, None)
    account.set_host_key(HOST_KEY, by=it_user)
    assert (account.host_key_changed_at, account.host_key_changed_by) == (FROZEN_NOW, it_user)
    account.host_key_changed_at = account.host_key_changed_by = None
    account.set_host_key("")
    assert account.host_key_changed_at == FROZEN_NOW and account.host_key_changed_by is None


def test_new_fields_are_not_editable_and_forget_a_deleted_user(it_user):
    fields = {f.name: f for f in HostAccount._meta.get_fields()}
    assert fields["host_key_changed_at"].editable is False
    by = fields["host_key_changed_by"]
    assert by.editable is False and by.null and by.remote_field.related_name == "+"
    account = make_account("Zoom 01")
    account.set_host_key(HOST_KEY, by=it_user)
    account.save()
    it_user.delete()
    account.refresh_from_db()
    assert account.host_key_changed_by is None and account.has_host_key


def test_clean_trims_and_lower_cases_the_email():
    account = HostAccount(label="Zoom 01", email="  Zoom01@Polymath.EDU.lk ")
    account.clean()
    assert account.email == "zoom01@polymath.edu.lk"


# --------------------------------------------------------------------------- 23 no admin


# Matches ``import django.contrib.admin``, ``from django.contrib.admin… import`` and
# ``from django.contrib import admin`` at the start of a line, so this file's own source (where
# the words sit inside a string) doesn't count.
ADMIN_IMPORT = re.compile(
    r"^\s*(?:import\s+django\.contrib\.admin\b|from\s+django\.contrib\.admin\b"
    r"|from\s+django\.contrib\s+import\s+(?:.*\b)?admin\b)",
    re.MULTILINE,
)


def test_the_zoom_models_are_not_in_the_django_admin():
    assert not (ZOOM_DIR / "admin.py").exists()
    offenders = [
        str(path.relative_to(ZOOM_DIR))
        for path in ZOOM_DIR.rglob("*.py")
        if ADMIN_IMPORT.search(path.read_text("utf-8"))
    ]
    assert offenders == []
    for name in ("admin:zoom_hostaccount_changelist", "admin:zoom_linkrequest_changelist"):
        with pytest.raises(NoReverseMatch):
            reverse(name)


# --------------------------------------------------------------------------- 25 copy


# Spelled with \s+ so this file doesn't match its own pattern.
OLD_ADMIN_COPY = re.compile(r"\bin\s+the\s+admin\b|admin\s+change\s+form", re.IGNORECASE)


def test_no_zoom_code_or_template_sends_people_to_the_admin():
    sources = [
        path
        for path in ZOOM_DIR.rglob("*.py")
        if "migrations" not in path.relative_to(ZOOM_DIR).parts
    ]
    sources += [path for path in TEMPLATES_DIR.rglob("*") if path.is_file()]
    offenders = [str(path) for path in sources if OLD_ADMIN_COPY.search(path.read_text("utf-8"))]
    assert offenders == []


@pytest.mark.parametrize(("who", "can_add"), [("it_user", True), ("viewer", False)])
def test_detail_page_knows_whether_the_user_may_add_an_account(client, request, who, can_add):
    user = request.getfixturevalue(who)
    user.user_permissions.add(Permission.objects.get(codename="review_linkrequest"))
    client.force_login(user)
    response = client.get(reverse("zoom:detail", args=[make_request().pk]))
    assert response.context["can_add_account"] is can_add


# --------------------------------------------------------------------------- 8, 13, 24 real pages


def _assert_no_key_material(response, *secrets):
    assert response.status_code in (200, 302)
    content = response.content.decode()
    assert "gAAAAA" not in content
    for secret in secrets:
        assert secret not in content


def test_no_accounts_page_shows_key_material(client, settings, superuser):
    """Criteria 8, 13 and 24, rendered with the real templates for a superuser."""
    _real_templates(settings)
    client.force_login(superuser)
    zoom03 = make_account("Zoom 03", host_key=HOST_KEY)
    make_account("Zoom 04")
    twelve_classes(zoom03)
    typed = "5566778"

    pages = [
        client.get(reverse("zoom:accounts")),
        client.get(reverse("zoom:account_add")),
        client.get(_edit(zoom03)),
        client.post(reverse("zoom:account_add"), _data(label="", host_key=typed)),
        client.post(reverse("zoom:account_add"), _data(host_key="556677889900")),
        client.post(_edit(zoom03), _data(zoom03, email="bad", host_key=typed)),
        client.post(_edit(zoom03), _data(zoom03, host_key=typed, remove_host_key="on")),
        client.post(_edit(zoom03), _data(zoom03, is_active=None, is_paid=None, host_key=typed)),
    ]
    for response in pages:
        _assert_no_key_material(response, HOST_KEY, typed, "556677889900")
    assert "Zoom 03 still has 12 booked classes" in pages[-1].content.decode()


def test_real_pages_render_for_the_unreadable_and_legacy_key_states(client, settings, superuser):
    _real_templates(settings)
    client.force_login(superuser)
    legacy = make_account("Zoom 05", host_key=HOST_KEY)
    HostAccount.objects.filter(pk=legacy.pk).update(host_key_changed_at=None)
    _assert_no_key_material(client.get(_edit(legacy)), HOST_KEY)
    settings.HOST_KEY_ENCRYPTION_KEYS = [Fernet.generate_key().decode()]
    response = client.get(_edit(legacy))
    _assert_no_key_material(response, HOST_KEY)
    assert response.context["host_key_state"] == "unreadable"
