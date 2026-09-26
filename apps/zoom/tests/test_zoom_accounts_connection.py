"""The Zoom connection on the accounts pages, the command and the system checks (brief 006,
criteria 1, 4-6, 34-37, 39, 40 and 41)."""

import re
from io import StringIO
from unittest import mock

import pytest
import responses
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
NAME_RULE = "Use lower-case letters, numbers and hyphens only, like zoom-01."


def _check(client, account):
    return client.post(reverse("zoom:account_check", args=[account.pk]))


def _flash(response):
    """The newest message: redirects aren't followed, so earlier ones are still queued."""
    message = list(get_messages(response.wsgi_request))[-1]
    return message.level, str(message)


# --------------------------------------------------------------------------- 34 the field


def test_the_connection_name_field_follows_order_and_has_its_label_help_and_attributes():
    form = HostAccountForm()
    assert list(form.fields) == [
        "label",
        "email",
        "notes",
        "is_paid",
        "is_active",
        "sort_order",
        "credential_set",
        "host_key",
    ]
    field = form.fields["credential_set"]
    assert field.label == "Zoom connection name"
    assert field.help_text == (
        "The name of this account's Zoom connection on the server, like zoom-01. Whoever looks "
        "after the server tells you the name."
    )
    assert field.required is False
    html = str(form["credential_set"])
    for attribute in (
        'autocomplete="off"',
        'autocapitalize="none"',
        'spellcheck="false"',
        'maxlength="40"',
    ):
        assert attribute in html
    assert HostAccountForm.Meta.fields[-1] == "credential_set"
    # One copy of the help: the form borrows the model's (review round 1, SF3).
    assert field.help_text == HostAccount._meta.get_field("credential_set").help_text


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


@pytest.mark.parametrize(
    "value", ["Zoom-01", "zoom_01", "zoom 01", "-zoom", "zoom-", "zoom--01", "a" * 41, "zoom.01"]
)
def test_a_bad_connection_name_gets_one_plain_error(it_client, value):
    account = make_account("Zoom 03", sort_order=3)
    response = it_client.post(_edit(account), _data(account, credential_set=value))
    assert response.status_code == 200
    assert response.context["form"].errors["credential_set"] == [NAME_RULE]
    account.refresh_from_db()
    assert account.credential_set == ""


@pytest.mark.parametrize("value", ["zoom-01", "zoom01", "a", "a" * 40, ""])
def test_a_good_connection_name_saves_even_if_the_server_doesnt_have_it(it_client, value):
    account = make_account("Zoom 03", sort_order=3)
    response = it_client.post(_edit(account), _data(account, credential_set=value))
    assert response.status_code == 302
    account.refresh_from_db()
    assert account.credential_set == value


def test_the_model_refuses_a_bad_name_too():
    account = make_account("Zoom 03")
    account.credential_set = "Zoom_01"
    with pytest.raises(Exception) as caught:
        account.full_clean()
    assert NAME_RULE in str(caught.value)


# --------------------------------------------------------------------------- 35 connection state


def test_the_connection_state_reads_settings_only(settings):
    settings.ZOOM_S2S_SECRETS = {"zoom-01": zm.credentials("zoom-01")}
    account = make_account("Zoom 03")
    with CaptureQueriesContext(connection) as queries:
        assert account.zoom_connection_state == "none"
        account.credential_set = "zoom-02"
        assert account.zoom_connection_state == "missing"
        assert not account.is_zoom_connected()
        account.credential_set = "zoom-01"
        assert account.zoom_connection_state == "ready"
        assert account.is_zoom_connected()
    assert len(queries) == 0


def test_the_pages_show_the_state_and_make_no_http_call(it_client, settings, http_mock):
    settings.ZOOM_S2S_SECRETS = {"zoom-01": zm.credentials("zoom-01")}
    ready = make_account("Zoom 01", sort_order=1)
    missing = make_account("Zoom 02", sort_order=2)
    none = make_account("Zoom 03", sort_order=3)
    HostAccount.objects.filter(pk=ready.pk).update(credential_set="zoom-01")
    HostAccount.objects.filter(pk=missing.pk).update(credential_set="zoom-9")

    accounts = it_client.get(reverse("zoom:accounts")).context["accounts"]
    assert [a.zoom_connection_state for a in accounts] == ["ready", "missing", "none"]

    context = it_client.get(_edit(missing)).context
    assert (context["zoom_connection_state"], context["zoom_connection_name"]) == (
        "missing",
        "zoom-9",
    )
    assert context["can_check_connection"] is True and context["account"].pk == missing.pk
    context = it_client.get(_edit(none)).context
    assert (context["zoom_connection_state"], context["zoom_connection_name"]) == ("none", "")

    context = it_client.get(reverse("zoom:account_add")).context
    assert (context["zoom_connection_state"], context["zoom_connection_name"]) == ("none", "")
    assert context["can_check_connection"] is False and context["account"] is None
    assert len(http_mock.calls) == 0


def test_an_invalid_submit_shows_the_stored_connection_not_the_typed_one(it_client, settings):
    settings.ZOOM_S2S_SECRETS = {"zoom-01": zm.credentials("zoom-01")}
    account = make_account("Zoom 03")
    HostAccount.objects.filter(pk=account.pk).update(credential_set="zoom-01")
    response = it_client.post(_edit(account), _data(account, credential_set="Bad Name"))
    assert response.status_code == 200
    context = response.context
    assert (context["zoom_connection_state"], context["zoom_connection_name"]) == (
        "ready",
        "zoom-01",
    )
    assert context["form"]["credential_set"].value() == "Bad Name"


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
def ready(settings):
    """Zoom 03, paid and in use, whose connection name the server has."""
    account = make_account("Zoom 03", sort_order=3)
    zm.connect(settings, account)
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


def test_no_name_and_a_missing_name_ask_nothing_of_zoom(it_client, settings, http_mock):
    none = make_account("Zoom 03")
    missing = make_account("Zoom 04")
    HostAccount.objects.filter(pk=missing.pk).update(credential_set="zoom-test")
    settings.ZOOM_S2S_SECRETS = {}
    assert _flash(_check(it_client, none)) == (
        levels.ERROR,
        "Zoom 03 has no Zoom connection name yet. Type it in, save, then check again.",
    )
    assert _flash(_check(it_client, missing)) == (
        levels.ERROR,
        "The server has no Zoom connection called zoom-test. Ask whoever looks after the server "
        "to add it, then check again.",
    )
    assert len(http_mock.calls) == 0


@pytest.mark.parametrize(
    ("answers", "message"),
    [
        (
            {"token_reply": {"status": 401}},
            "Zoom didn't accept the connection details called zoom-test. Check the account ID, "
            "client ID and client secret on the server, and that the Zoom app is activated.",
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


def test_the_command_checks_every_active_paid_account_in_order(settings, http_mock):
    works = make_account("Zoom 02", sort_order=2)
    broken = make_account("Zoom 01", sort_order=1)
    make_account("Zoom 09", sort_order=0, is_paid=False)
    make_account("Zoom 08", sort_order=0, is_active=False)
    zm.connect(settings, works)
    HostAccount.objects.filter(pk=broken.pk).update(credential_set="zoom-gone")
    _zoom_answers(http_mock, works)

    out = StringIO()
    with pytest.raises(CommandError) as caught:
        call_command("check_zoom_connections", stdout=out)
    assert caught.value.returncode == 1
    assert out.getvalue().splitlines() == [
        "Zoom 01: The server has no Zoom connection called zoom-gone. Ask whoever looks after "
        "the server to add it, then check again.",
        "Zoom 02: works",
    ]
    for secret in zm.SECRETS:
        assert secret not in out.getvalue() and secret not in str(caught.value)


def test_the_command_exits_cleanly_when_every_account_works(settings, http_mock):
    account = make_account("Zoom 02")
    zm.connect(settings, account)
    _zoom_answers(http_mock, account)
    out = StringIO()
    call_command("check_zoom_connections", stdout=out)
    assert out.getvalue() == "Zoom 02: works\n"


# --------------------------------------------------------------------------- 4-6 checks


def test_e005_is_silent_unless_the_zoom_provider_is_chosen(settings):
    settings.ZOOM_CREDENTIAL_SETS = []
    for provider in ("fake", "manual"):
        settings.ZOOM_PROVIDER = provider
        assert zoom_checks.check_credential_sets() == []


def test_e005_names_what_is_wrong_and_never_a_value(settings):
    settings.ZOOM_PROVIDER = "zoom"
    settings.ZOOM_CREDENTIAL_SETS = []
    [error] = zoom_checks.check_credential_sets()
    assert (error.id, error.msg) == (
        "zoom.E005",
        "ZOOM_PROVIDER is zoom, but ZOOM_CREDENTIAL_SETS is empty.",
    )

    settings.ZOOM_CREDENTIAL_SETS = ["zoom-01", "Zoom_02", "zoom-03", "zoom-03"]
    settings.ZOOM_S2S_SECRETS = {"zoom-03": zm.credentials("zoom-03")}
    settings.ZOOM_CREDENTIAL_MISSING = {
        "zoom-01": ["ZOOM_S2S_ZOOM_01_CLIENT_ID", "ZOOM_S2S_ZOOM_01_CLIENT_SECRET"]
    }
    messages = [e.msg for e in zoom_checks.check_credential_sets()]
    assert messages == [
        "The Zoom connection zoom-01 is missing ZOOM_S2S_ZOOM_01_CLIENT_ID, "
        "ZOOM_S2S_ZOOM_01_CLIENT_SECRET.",
        "The Zoom connection name 'Zoom_02' in ZOOM_CREDENTIAL_SETS isn't valid.",
        "The Zoom connections zoom-03, zoom-03 all use the variables ZOOM_S2S_ZOOM_03_*.",
    ]
    for secret in zm.SECRETS:
        assert all(secret not in message for message in messages)
    # The bad-name hint is the form's own error, from one definition (review round 1, SF3).
    [bad_name] = [e for e in zoom_checks.check_credential_sets() if "Zoom_02" in e.msg]
    assert bad_name.hint == NAME_RULE


def test_e005_and_the_deploy_checks_pass_with_zoom_and_valid_sets(settings):
    settings.ZOOM_PROVIDER = "zoom"
    settings.ZOOM_CREDENTIAL_SETS = ["zoom-test"]
    settings.ZOOM_S2S_SECRETS = {"zoom-test": zm.credentials()}
    settings.ZOOM_CREDENTIAL_MISSING = {}
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


def test_e004_names_each_paid_account_without_a_working_connection(settings):
    settings.ZOOM_PROVIDER = "zoom"
    settings.ZOOM_S2S_SECRETS = {"zoom-01": zm.credentials("zoom-01")}
    make_account("Zoom 01", sort_order=1)
    HostAccount.objects.filter(label="Zoom 01").update(credential_set="zoom-01")
    make_account("Zoom 02", sort_order=2)
    make_account("Zoom 03", sort_order=3)
    HostAccount.objects.filter(label="Zoom 03").update(credential_set="zoom-03")
    make_account("Zoom 04", is_paid=False)
    make_account("Zoom 05", is_active=False)

    errors = checks.run_checks(databases=["default"])
    mine = [e for e in errors if e.id == "zoom.E004"]
    assert [e.msg for e in mine] == [
        "Zoom 02 has no working Zoom connection: no Zoom connection name is set.",
        "Zoom 03 has no working Zoom connection: the server has no connection details called "
        "zoom-03.",
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


def test_there_is_no_webhook_url():
    for pattern in zoom_urls.urlpatterns:
        assert "webhook" not in (pattern.name or "") and "webhook" not in str(pattern.pattern)


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
    zm.connect(settings, account)
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
