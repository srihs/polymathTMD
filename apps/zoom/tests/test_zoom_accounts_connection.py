"""The Zoom connection on the accounts pages, the command and the system checks (brief 006,
criteria 1, 4-6, 34-37, 39, 40 and 41), as amended by brief 015 (criteria 3, 18, 19, 21, 22,
30-32 and 35): the account picks a saved ``ZoomConnection``, and nothing reads settings."""

import re
from io import StringIO
from pathlib import Path
from unittest import mock

import pytest
import responses
from django import forms
from django.contrib.messages import constants as levels
from django.contrib.messages import get_messages
from django.core import checks, mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import ProgrammingError, connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import resolve, reverse

from apps.zoom import checks as zoom_checks
from apps.zoom import urls as zoom_urls
from apps.zoom.forms import HostAccountForm
from apps.zoom.models import HostAccount, Occurrence
from apps.zoom.providers import FakeProvider

from . import zoommock as zm
from .conftest import make_account, make_request
from .test_accounts import _data, _edit, _user_with
from .test_sidebar_zoom_group import _real_templates

pytestmark = pytest.mark.django_db

HOST_KEY = "8421973"


def _check(client, account):
    return client.post(reverse("zoom:account_check", args=[account.pk]))


def _flash(response):
    """The newest message: redirects aren't followed, so earlier ones are still queued."""
    message = list(get_messages(response.wsgi_request))[-1]
    return message.level, str(message)


# --------------------------------------------------------------------------- 34 the field
# Brief 015, criterion 18: the typed connection name became a select of saved connections.


def test_the_connection_field_is_a_select_in_order_with_its_label_help_and_empty_label():
    form = HostAccountForm()
    assert list(form.fields) == [
        "label",
        "email",
        "notes",
        "is_paid",
        "is_active",
        "sort_order",
        "zoom_connection",
        "host_key",
    ]
    field = form.fields["zoom_connection"]
    assert isinstance(field, forms.ModelChoiceField)
    assert isinstance(field.widget, forms.Select)
    assert field.label == "Zoom connection"
    assert field.empty_label == "No Zoom connection yet"
    assert field.help_text == (
        "The Zoom app this account books through. If it isn't in the list, add it on the Zoom "
        "connections page first."
    )
    assert field.required is False
    assert HostAccountForm.Meta.fields[-1] == "zoom_connection"
    # One copy of the help: the form borrows the model's (review round 1, SF3).
    assert field.help_text == HostAccount._meta.get_field("zoom_connection").help_text


def test_the_choices_read_only_the_name_never_a_secret_column():
    zm.connection()
    form = HostAccountForm()
    with CaptureQueriesContext(connection) as queries:
        choices = [str(label) for _, label in form.fields["zoom_connection"].choices]
    assert choices == ["No Zoom connection yet", "zoom-test"]
    [query] = queries
    for column in ("secret", "account_id", "client_id", "credentials"):
        assert column not in query["sql"]


@pytest.mark.parametrize(
    ("is_paid", "is_active", "needs"),
    [(True, True, True), (True, False, False), (False, True, False), (False, False, False)],
)
def test_only_an_account_that_can_be_booked_needs_a_zoom_connection(is_paid, is_active, needs):
    """Review round 1, SF2: the accounts list's warning follows the one bookable rule."""
    account = HostAccount(label="Zoom 09", email="z9@polymath.example")
    account.is_paid, account.is_active = is_paid, is_active
    assert account.needs_zoom_connection is needs
    # The list shows the same answer as the database's bookable filter.
    account.save()
    assert HostAccount.objects.bookable().filter(pk=account.pk).exists() is needs


def test_the_accounts_list_warns_only_where_a_connection_is_needed():
    """The list's objects carry ``needs_zoom_connection`` for the Zoom connection tag."""
    make_account("Zoom 01")
    make_account("Zoom 02", is_paid=False)
    user = _user_with("view_hostaccount")
    client = Client()
    client.force_login(user)
    response = client.get(reverse("zoom:accounts"))
    assert {a.label: a.needs_zoom_connection for a in response.context["accounts"]} == {
        "Zoom 01": True,
        "Zoom 02": False,
    }


def test_choosing_a_connection_saves_it_and_an_empty_choice_clears_it(it_client):
    chosen = zm.connection()
    account = make_account("Zoom 03", sort_order=3)
    response = it_client.post(_edit(account), _data(account, zoom_connection=chosen.pk))
    assert response.status_code == 302
    account.refresh_from_db()
    assert account.zoom_connection == chosen
    response = it_client.post(_edit(account), _data(account, zoom_connection=""))
    assert response.status_code == 302
    account.refresh_from_db()
    assert account.zoom_connection is None


@pytest.mark.parametrize("value", ["99999", "zoom-test", "not-a-number"])
def test_a_choice_not_in_the_list_gets_one_plain_error(it_client, value):
    zm.connection()
    account = make_account("Zoom 03", sort_order=3)
    response = it_client.post(_edit(account), _data(account, zoom_connection=value))
    assert response.status_code == 200
    assert response.context["form"].errors["zoom_connection"] == [
        "Choose a Zoom connection from the list."
    ]
    account.refresh_from_db()
    assert account.zoom_connection is None


def test_after_an_invalid_post_the_persons_choice_is_still_selected(it_client):
    chosen = zm.connection()
    account = make_account("Zoom 03", sort_order=3)
    response = it_client.post(_edit(account), _data(account, label="", zoom_connection=chosen.pk))
    assert response.status_code == 200
    bound = response.context["form"]["zoom_connection"]
    assert str(bound.value()) == str(chosen.pk)
    assert f'<option value="{chosen.pk}" selected>' in str(bound)


# --------------------------------------------------------------------------- 35 connection state


def test_the_connection_state_reads_the_loaded_row_only():
    """Brief 015, criterion 3: none, ready or unreadable, with no query once loaded."""
    account = make_account("Zoom 03")
    ready = zm.connection()
    broken = zm.make_unreadable(zm.connection("zoom-broken"))
    with CaptureQueriesContext(connection) as queries:
        assert account.zoom_connection_state == "none"
        account.zoom_connection = ready
        assert account.zoom_connection_state == "ready"
        assert account.is_zoom_connected()
        account.zoom_connection = broken
        assert account.zoom_connection_state == "unreadable"
        assert not account.is_zoom_connected()
    assert len(queries) == 0


def test_the_pages_show_the_state_and_make_no_http_call(it_client, http_mock):
    ready = make_account("Zoom 01", sort_order=1)
    unreadable = make_account("Zoom 02", sort_order=2)
    none = make_account("Zoom 03", sort_order=3)
    zm.connect(ready)
    broken = zm.connect(unreadable, slug="zoom-broken")
    zm.make_unreadable(broken)

    response = it_client.get(reverse("zoom:accounts"))
    accounts = response.context["accounts"]
    assert [a.zoom_connection_state for a in accounts] == ["ready", "unreadable", "none"]
    assert response.context["can_manage_connections"] is True

    context = it_client.get(_edit(unreadable)).context
    assert (context["zoom_connection_state"], context["zoom_connection_name"]) == (
        "unreadable",
        "zoom-broken",
    )
    assert context["zoom_connection_url"] == reverse("zoom:connection_edit", args=[broken.pk])
    assert context["can_manage_connections"] is True
    assert context["can_check_connection"] is True and context["account"].pk == unreadable.pk
    context = it_client.get(_edit(none)).context
    assert (context["zoom_connection_state"], context["zoom_connection_name"]) == ("none", "")
    assert context["zoom_connection_url"] == ""

    context = it_client.get(reverse("zoom:account_add")).context
    assert (context["zoom_connection_state"], context["zoom_connection_name"]) == ("none", "")
    assert context["zoom_connection_url"] == "" and context["can_manage_connections"] is True
    assert context["can_check_connection"] is False and context["account"] is None
    assert len(http_mock.calls) == 0


def test_a_keyless_viewer_gets_no_connections_link():
    make_account("Zoom 01")
    client = Client()
    client.force_login(_user_with("view_hostaccount"))
    assert client.get(reverse("zoom:accounts")).context["can_manage_connections"] is False


def test_the_accounts_list_query_count_is_fixed_with_connections(it_client):
    """Criterion 21: the same count with 1 and with 5 accounts, each linked to a connection."""

    def count():
        with CaptureQueriesContext(connection) as queries:
            assert it_client.get(reverse("zoom:accounts")).status_code == 200
        return len(queries)

    zm.connect(make_account("Zoom 01", sort_order=1), slug="zoom-01")
    one = count()
    for number in range(2, 6):
        zm.connect(make_account(f"Zoom 0{number}", sort_order=number), slug=f"zoom-0{number}")
    assert count() == one


def test_an_invalid_submit_shows_the_stored_connection_not_the_chosen_one(it_client):
    account = make_account("Zoom 03")
    stored = zm.connect(account, slug="zoom-01")
    other = zm.connection("zoom-02")
    response = it_client.post(_edit(account), _data(account, label="", zoom_connection=other.pk))
    assert response.status_code == 200
    context = response.context
    assert (context["zoom_connection_state"], context["zoom_connection_name"]) == (
        "ready",
        "zoom-01",
    )
    assert context["zoom_connection_url"] == reverse("zoom:connection_edit", args=[stored.pk])
    assert str(context["form"]["zoom_connection"].value()) == str(other.pk)


def test_the_change_view_locks_only_the_account_row(it_client):
    """Brief 015, criterion 3 and D8: ``FOR UPDATE OF`` the account, never the connection."""
    account = make_account("Zoom 03")
    zm.connect(account)
    with CaptureQueriesContext(connection) as queries:
        it_client.post(_edit(account), _data(account, zoom_connection=account.zoom_connection_id))
    locks = [
        q["sql"] for q in queries if "FOR UPDATE" in q["sql"] and "zoom_hostaccount" in q["sql"]
    ]
    assert locks and all(s.endswith("FOR UPDATE OF `zoom_hostaccount`") for s in locks)
    assert not any(
        "FOR UPDATE" in q["sql"] and "zoom_zoomconnection`" in q["sql"].split("FOR UPDATE")[1]
        for q in queries
    )


# --------------------------------------------------------------------------- 36 check connection


def test_check_connection_needs_the_change_permission(plain_user, it_client):
    account = make_account("Zoom 03")
    url = reverse("zoom:account_check", args=[account.pk])
    client = Client()
    response = client.post(url)
    assert response.status_code == 302 and response.url.startswith(reverse("accounts:login"))
    client.force_login(plain_user)
    assert client.post(url).status_code == 403
    client.force_login(_user_with("view_hostaccount", username="keyless"))
    assert client.post(url).status_code == 403
    assert it_client.get(url).status_code == 405
    assert it_client.post(reverse("zoom:account_check", args=[99999])).status_code == 404
    view = resolve(url).func
    assert "default" in getattr(view, "_non_atomic_requests", set())


@pytest.fixture
def ready():
    """Zoom 03, paid and in use, on the test connection."""
    account = make_account("Zoom 03", sort_order=3)
    zm.connect(account)
    return account


def _zoom_answers(http_mock, account, *, user=None, user_reply=None, token_reply=None):
    if token_reply is None:
        zm.add_token(http_mock)
    else:
        http_mock.add(responses.POST, zm.TOKEN_URL, **token_reply)
    user_url = zm.API + f"/users/{account.email}"
    http_mock.add(responses.GET, user_url, **(user_reply or {"json": user or {"type": 2}}))
    zm.add_listing(http_mock, account.email)


def test_a_working_connection_says_so_even_with_the_fake_provider(it_client, ready, http_mock):
    _zoom_answers(http_mock, ready)
    response = _check(it_client, ready)
    assert response.status_code == 302 and response.url == _edit(ready)
    assert _flash(response) == (levels.SUCCESS, "The Zoom connection works for Zoom 03.")
    assert [c.request.url.split("?")[0] for c in http_mock.calls] == [
        zm.TOKEN_URL,
        zm.API + f"/users/{ready.email}",
        zm.meetings_url(ready.email),
    ]
    assert FakeProvider.busy_calls == []  # the fake provider wasn't used


def test_a_basic_user_on_a_paid_account_is_a_warning(it_client, ready, http_mock):
    _zoom_answers(http_mock, ready, user={"type": 1})
    assert _flash(_check(it_client, ready)) == (
        levels.WARNING,
        "The Zoom connection works for Zoom 03, but Zoom says zoom03@polymath.example is a Basic "
        "(free) user. Free users' meetings end after 40 minutes. Untick Paid account, or ask the "
        "Zoom account owner to give this user a licence.",
    )


def test_a_basic_user_on_a_free_account_is_fine(it_client, ready, http_mock):
    HostAccount.objects.filter(pk=ready.pk).update(is_paid=False)
    _zoom_answers(http_mock, ready, user={"type": 1})
    assert _flash(_check(it_client, ready))[0] == levels.SUCCESS


def test_no_connection_and_an_unreadable_one_ask_nothing_of_zoom(it_client, http_mock):
    """Brief 015, criterion 22's first two rows: nothing is sent anywhere."""
    none = make_account("Zoom 03")
    broken = make_account("Zoom 04")
    zm.make_unreadable(zm.connect(broken))
    assert _flash(_check(it_client, none)) == (
        levels.ERROR,
        "Zoom 03 has no Zoom connection yet. Choose one, save, then check again.",
    )
    assert _flash(_check(it_client, broken)) == (
        levels.ERROR,
        "The details of the Zoom connection zoom-test can't be read with the server's current "
        "encryption keys. Type its client secret again on the Zoom connection's page, then check "
        "again.",
    )
    assert len(http_mock.calls) == 0


@pytest.mark.parametrize(
    ("answers", "message"),
    [
        (
            {"token_reply": {"status": 401}},
            "Zoom didn't accept the details of the Zoom connection zoom-test. Check its Account "
            "ID, Client ID and Client Secret on the Zoom connection's page, and that the Zoom app "
            "is activated.",
        ),
        (
            {"user_reply": {"status": 400, "json": zm.zoom_error(4711)}},
            "The Zoom app for zoom-test is missing a permission. Add the scopes listed in the "
            "README, then check again.",
        ),
        (
            {"user_reply": {"status": 404, "json": zm.zoom_error(1001)}},
            "The connection works, but that Zoom account has no user zoom03@polymath.example. "
            "Check the Zoom sign-in email.",
        ),
        (
            {"user_reply": {"status": 503}},
            "Couldn't check Zoom 03 with Zoom: no answer from Zoom. Try again in a few minutes.",
        ),
        (
            {"user_reply": {"status": 429}},
            "Couldn't check Zoom 03 with Zoom: Zoom is busy right now. Try again in a few minutes.",
        ),
        (
            {"user_reply": {"status": 400, "json": zm.zoom_error(300)}},
            "Couldn't check Zoom 03 with Zoom: Zoom error 300. Waiting won't fix this. Tell "
            "whoever looks after the server, and give them the Zoom error number.",
        ),
    ],
)
def test_each_failure_has_its_own_message(it_client, ready, http_mock, answers, message):
    _zoom_answers(http_mock, ready, **answers)
    assert _flash(_check(it_client, ready)) == (levels.ERROR, message)


# --------------------------------------------------------------------------- 37 the command


def test_the_command_checks_every_active_paid_account_in_order(http_mock):
    works = make_account("Zoom 02", sort_order=2)
    broken = make_account("Zoom 01", sort_order=1)
    make_account("Zoom 09", sort_order=0, is_paid=False)
    make_account("Zoom 08", sort_order=0, is_active=False)
    zm.connect(works)
    zm.make_unreadable(zm.connect(broken, slug="zoom-gone"))
    _zoom_answers(http_mock, works)

    out = StringIO()
    with pytest.raises(CommandError) as caught:
        call_command("check_zoom_connections", stdout=out)
    assert caught.value.returncode == 1
    assert out.getvalue().splitlines() == [
        "Zoom 01: The details of the Zoom connection zoom-gone can't be read with the server's "
        "current encryption keys. Type its client secret again on the Zoom connection's page, "
        "then check again.",
        "Zoom 02: works",
    ]
    for secret in zm.SECRETS:
        assert secret not in out.getvalue() and secret not in str(caught.value)


def test_the_command_exits_cleanly_when_every_account_works(http_mock):
    account = make_account("Zoom 02")
    zm.connect(account)
    _zoom_answers(http_mock, account)
    out = StringIO()
    call_command("check_zoom_connections", stdout=out)
    assert out.getvalue() == "Zoom 02: works\n"


# --------------------------------------------------------------------------- 4-6 checks


def test_e005_is_retired_and_its_id_never_produced(settings):
    """Brief 015, criterion 30: no ``check_credential_sets``, and no check says ``zoom.E005``."""
    from django.core.checks import registry

    assert not hasattr(zoom_checks, "check_credential_sets")
    names = {check.__name__ for check in registry.registry.get_checks(True)}
    assert "check_credential_sets" not in names
    for provider in ("fake", "manual", "zoom"):
        settings.ZOOM_PROVIDER = provider
        ids = {
            e.id for e in checks.run_checks(include_deployment_checks=True, databases=["default"])
        }
        assert "zoom.E005" not in ids
    source = (Path(zoom_checks.__file__)).read_text(encoding="utf-8")
    assert "config" + ".settings" not in source


def test_the_deploy_checks_pass_with_zoom_and_no_credential_setting(settings):
    """Brief 015: ``check --deploy`` needs no credential variable at all."""
    settings.ZOOM_PROVIDER = "zoom"
    ids = {e.id for e in checks.run_checks(include_deployment_checks=True)}
    assert not {i for i in ids if i.startswith("zoom.")}


def test_w001_warns_about_manual_under_deploy_only(settings):
    settings.ZOOM_PROVIDER = "manual"
    [warning] = zoom_checks.check_manual_provider_not_deployed()
    assert (warning.id, warning.msg) == (
        "zoom.W001",
        "ZOOM_PROVIDER=manual can't see meetings made directly in Zoom, so it can double-book "
        "them. Set ZOOM_PROVIDER=zoom before taking real requests.",
    )
    assert "zoom.W001" in {e.id for e in checks.run_checks(include_deployment_checks=True)}
    assert "zoom.W001" not in {e.id for e in checks.run_checks()}
    settings.ZOOM_PROVIDER = "zoom"
    assert zoom_checks.check_manual_provider_not_deployed() == []


E004_HINT = (
    "Choose the connection on the Zoom accounts page, or type its client secret again on the "
    "Zoom connections page."
)


def test_e004_names_each_paid_account_without_a_working_connection(settings):
    """Brief 015, criterion 32: from the database, one query whatever the number of accounts."""
    settings.ZOOM_PROVIDER = "zoom"
    zm.connect(make_account("Zoom 01", sort_order=1), slug="zoom-01")
    make_account("Zoom 02", sort_order=2)
    zm.make_unreadable(zm.connect(make_account("Zoom 03", sort_order=3), slug="zoom-03"))
    make_account("Zoom 04", is_paid=False)
    make_account("Zoom 05", is_active=False)

    with CaptureQueriesContext(connection) as queries:
        mine = zoom_checks.check_accounts_connected(databases=["default"])
    assert len(queries) == 1
    assert [(e.id, e.msg, e.hint) for e in mine] == [
        (
            "zoom.E004",
            "Zoom 02 has no working Zoom connection: no Zoom connection is chosen.",
            E004_HINT,
        ),
        (
            "zoom.E004",
            "Zoom 03 has no working Zoom connection: the details of zoom-03 can't be read with "
            "the current encryption keys.",
            E004_HINT,
        ),
    ]
    assert [e.msg for e in checks.run_checks(databases=["default"]) if e.id == "zoom.E004"] == [
        e.msg for e in mine
    ]
    # Only with --database: a plain check never touches the database for it.
    assert "zoom.E004" not in {e.id for e in checks.run_checks()}
    for provider in ("fake", "manual"):
        settings.ZOOM_PROVIDER = provider
        assert zoom_checks.check_accounts_connected(databases=["default"]) == []


def test_e004_is_quiet_before_the_table_exists(settings):
    settings.ZOOM_PROVIDER = "zoom"
    with mock.patch.object(
        HostAccount.objects, "bookable", side_effect=ProgrammingError(1146, "doesn't exist")
    ):
        assert zoom_checks.check_accounts_connected(databases=["default"]) == []


# --------------------------------------------------------------------------- 39, 41


def test_the_only_webhook_url_is_brief_013s():
    # Criterion 39 said "no webhook URL"; brief 013 (D7) amends it deliberately: there is now
    # exactly one, ``zoom:webhook``, one address per Zoom connection.
    found = [
        (pattern.name, str(pattern.pattern))
        for pattern in zoom_urls.urlpatterns
        if "webhook" in (pattern.name or "") or "webhook" in str(pattern.pattern)
    ]
    assert found == [("webhook", "webhooks/<slug:slug>/")]


def test_the_occurrence_id_field_is_labelled_and_optional():
    field = Occurrence._meta.get_field("zoom_occurrence_id")
    assert (field.verbose_name, field.max_length, field.blank) == ("Zoom occurrence ID", 20, True)
    assert not re.search(
        r"password|secret|host_key|hostkey|token|start_url", field.name, re.IGNORECASE
    )
    assert HostAccount._meta.get_field("label").help_text == (
        "IT's short name for the account, like Zoom 01."
    )


# ---------------------------------------------------------------- 40 nothing in the browser


def test_no_credential_or_token_reaches_a_page_a_message_or_the_email(
    it_client, settings, http_mock
):
    """Rendered with the real templates, so anything the markup prints is searched too."""
    _real_templates(settings)
    account = make_account("Zoom 01", host_key=HOST_KEY)
    settings.ZOOM_PROVIDER = "zoom"
    zm.connect(account)
    _zoom_answers(http_mock, account)
    zm.add_create(http_mock, account.email)
    link_request = make_request()

    pages = [
        it_client.get(reverse("zoom:detail", args=[link_request.pk])),
        it_client.get(reverse("zoom:accounts")),
        it_client.get(reverse("zoom:account_add")),
        it_client.get(_edit(account)),
    ]
    checked = _check(it_client, account)
    approved = it_client.post(
        reverse("zoom:approve", args=[link_request.pk]), {"host_account": account.pk}
    )
    assert approved.status_code == 302
    pages.append(it_client.get(reverse("zoom:detail", args=[link_request.pk])))

    texts = [page.content.decode() for page in pages]
    texts += [str(m) for m in get_messages(checked.wsgi_request)]
    texts += [m.body + m.subject for m in mail.outbox]
    assert all(page.status_code == 200 for page in pages)
    assert len(mail.outbox) == 1
    for text in texts:
        for secret in zm.SECRETS:
            assert secret not in text
        assert zm.START_URL not in text
