"""Brief 015: Zoom connections entered in the app and stored encrypted.

The model (criteria 1-3, 5-7), the connection screens (8, 10-17), credentials read per
operation and the version-keyed token cache (23-26), the webhook's one lookup (27-29), W002's
unreadable state (33), the rotation command (34), and the security sweeps (40-43). The account
pages' side (18-22, 30-32, 35) is in ``test_zoom_accounts_connection.py``.

Every value is the brief's obviously fake "test connection" (``zoommock``): no real credential
appears anywhere, and no test reaches the network.
"""

import logging
import re
import sys
import threading
from io import StringIO
from pathlib import Path
from unittest import mock

import pytest
from cryptography.fernet import Fernet
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.signals import got_request_exception
from django.db import IntegrityError, connection, transaction
from django.db.backends.utils import CursorWrapper
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.views.debug import ExceptionReporter

from apps.zoom import crypto, services, webhooks, zoom_api
from apps.zoom import urls as zoom_urls
from apps.zoom.forms import ZoomConnectionForm
from apps.zoom.models import HostAccount, SecretUnreadable, ZoomConnection, ZoomEvent
from apps.zoom.providers import ZoomProvider

from . import synckit as kit
from . import zoommock as zm
from .conftest import make_account, make_request
from .test_accounts import _user_with
from .test_sidebar_zoom_group import _real_templates

pytestmark = pytest.mark.django_db

ZOOM_APP = Path(__file__).resolve().parents[1]
WEBHOOK_SECRET = "test-webhook-secret-value"
NEW_WEBHOOK_SECRET = "test-webhook-secret-renewed"
TYPED_CLIENT_SECRET = "test-typed-client-secret"
TYPED_WEBHOOK_SECRET = "test-typed-webhook-secret"
LIST_URL = reverse("zoom:connections")
ADD_URL = reverse("zoom:connection_add")


def edit_url(conn):
    return reverse("zoom:connection_edit", args=[conn.pk])


def add_data(**overrides):
    data = {
        "slug": "zoom-01",
        "account_id": zm.ACCOUNT_ID,
        "client_id": zm.CLIENT_ID,
        "client_secret": zm.CLIENT_SECRET,
        "webhook_secret": "",
    }
    data.update(overrides)
    return {key: value for key, value in data.items() if value is not None}


def edit_data(conn, **overrides):
    data = {
        "account_id": conn.account_id,
        "client_id": conn.client_id,
        "client_secret": "",
        "webhook_secret": "",
    }
    data.update(overrides)
    return {key: value for key, value in data.items() if value is not None}


def flashes(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


def ciphertexts():
    found = []
    for conn in ZoomConnection.objects.all():
        found += [t for t in (conn.client_secret_encrypted, conn.webhook_secret_encrypted) if t]
    return found


# --------------------------------------------------------------------------- 1 the model


def test_the_fields_and_nothing_else():
    names = [f.name for f in ZoomConnection._meta.get_fields() if f.concrete]
    assert names == [
        "id",
        "slug",
        "account_id",
        "client_id",
        "client_secret_encrypted",
        "webhook_secret_encrypted",
        "credentials_version",
        "credentials_changed_at",
        "credentials_changed_by",
        "webhook_secret_changed_at",
        "webhook_secret_changed_by",
    ]
    meta = ZoomConnection._meta
    slug = meta.get_field("slug")
    assert (slug.max_length, slug.unique, slug.verbose_name) == (40, True, "Zoom connection name")
    assert (meta.get_field("account_id").max_length, meta.get_field("account_id").unique) == (
        100,
        False,
    )
    assert meta.get_field("client_id").unique is True
    assert meta.get_field("account_id").verbose_name == "Account ID"
    assert meta.get_field("client_id").verbose_name == "Client ID"
    for name in (
        "client_secret_encrypted",
        "webhook_secret_encrypted",
        "credentials_version",
        "credentials_changed_at",
        "credentials_changed_by",
        "webhook_secret_changed_at",
        "webhook_secret_changed_by",
    ):
        assert meta.get_field(name).editable is False
    assert meta.get_field("webhook_secret_encrypted").blank is True
    assert meta.get_field("credentials_version").default == 1
    for name in ("credentials_changed_by", "webhook_secret_changed_by"):
        field = meta.get_field(name)
        assert field.null and field.remote_field.related_name == "+"
    assert meta.ordering == ["slug"] and meta.default_permissions == ()
    assert (str(meta.verbose_name), str(meta.verbose_name_plural)) == (
        "Zoom connection",
        "Zoom connections",
    )
    assert any(
        "^[a-z0-9]+(-[a-z0-9]+)*" in getattr(getattr(v, "regex", None), "pattern", "")
        for v in slug.validators
    )


@pytest.mark.parametrize("column", ["account_id", "client_id", "client_secret_encrypted"])
def test_the_database_refuses_an_empty_required_value(column):
    conn = zm.connection()
    with pytest.raises(IntegrityError), transaction.atomic():
        ZoomConnection.objects.filter(pk=conn.pk).update(**{column: ""})


def test_str_and_repr_show_only_the_name():
    conn = zm.connection(webhook_secret=WEBHOOK_SECRET)
    for text in (str(conn), repr(conn)):
        for value in (
            zm.ACCOUNT_ID,
            zm.CLIENT_ID,
            zm.CLIENT_SECRET,
            WEBHOOK_SECRET,
            *ciphertexts(),
        ):
            assert value not in text
    assert (str(conn), repr(conn)) == ("zoom-test", "<ZoomConnection: zoom-test>")


# --------------------------------------------------------------------------- 2 the methods


def test_the_first_details_are_version_1_with_who_and_when(it_user, frozen_now):
    conn = ZoomConnection(slug="zoom-01")
    assert conn.set_credentials(
        account_id=zm.ACCOUNT_ID, client_id=zm.CLIENT_ID, client_secret=zm.CLIENT_SECRET, by=it_user
    )
    conn.save()
    conn.refresh_from_db()
    assert conn.credentials_version == 1
    assert (conn.credentials_changed_at, conn.credentials_changed_by) == (frozen_now, it_user)
    assert conn.get_client_secret() == zm.CLIENT_SECRET
    assert conn.get_webhook_secret() == ""


@pytest.mark.parametrize(
    "change",
    [
        {"account_id": "test-account-id-2"},
        {"client_id": "test-client-id-2"},
        {"client_secret": zm.NEW_CLIENT_SECRET},
    ],
)
def test_any_changed_part_bumps_the_version_and_records_the_change(it_user, change):
    conn = zm.connection()
    values = {
        "account_id": zm.ACCOUNT_ID,
        "client_id": zm.CLIENT_ID,
        "client_secret": "",
        **change,
    }
    assert conn.set_credentials(**values, by=it_user) is True
    assert conn.credentials_version == 2 and conn.credentials_changed_by == it_user


def test_nothing_changed_records_nothing(it_user):
    conn = zm.connection()
    before = (conn.credentials_version, conn.credentials_changed_at, conn.credentials_changed_by)
    for secret in ("", zm.CLIENT_SECRET, f"  {zm.CLIENT_SECRET} "):
        assert not conn.set_credentials(
            account_id=zm.ACCOUNT_ID, client_id=zm.CLIENT_ID, client_secret=secret, by=it_user
        )
    after = (conn.credentials_version, conn.credentials_changed_at, conn.credentials_changed_by)
    assert after == before and conn.get_client_secret() == zm.CLIENT_SECRET


def test_an_unreadable_secret_counts_any_typed_one_as_a_change(it_user):
    conn = zm.make_unreadable(zm.connection())
    assert conn.set_credentials(
        account_id=zm.ACCOUNT_ID, client_id=zm.CLIENT_ID, client_secret=zm.CLIENT_SECRET, by=it_user
    )
    assert conn.credentials_version == 2 and conn.credentials_state == "saved"


def test_the_webhook_secret_never_touches_the_version(it_user, frozen_now):
    conn = zm.connection()
    assert conn.set_webhook_secret(WEBHOOK_SECRET, by=it_user)
    assert conn.credentials_version == 1
    assert (conn.webhook_secret_changed_at, conn.webhook_secret_changed_by) == (
        frozen_now,
        it_user,
    )
    assert conn.get_webhook_secret() == WEBHOOK_SECRET
    assert not conn.set_webhook_secret(WEBHOOK_SECRET, by=None)  # the same one: no change
    assert conn.webhook_secret_changed_by == it_user


def test_removing_clears_a_stored_secret_readable_or_not(it_user):
    conn = zm.make_unreadable(
        zm.connection(webhook_secret=WEBHOOK_SECRET), client=False, webhook=True
    )
    assert conn.webhook_secret_state == "unreadable"
    assert conn.remove_webhook_secret(by=it_user) is True
    assert conn.webhook_secret_encrypted == "" and conn.webhook_secret_state == "none"
    assert conn.webhook_secret_changed_by == it_user
    assert conn.remove_webhook_secret(by=None) is False  # nothing stored: nothing recorded
    assert conn.webhook_secret_changed_by == it_user


def test_credentials_are_the_token_parts_with_a_safe_repr():
    conn = zm.connection(webhook_secret=WEBHOOK_SECRET)
    found = conn.credentials()
    assert found == zoom_api.ZoomCredentials(
        slug="zoom-test",
        version=1,
        account_id=zm.ACCOUNT_ID,
        client_id=zm.CLIENT_ID,
        client_secret=zm.CLIENT_SECRET,
    )
    assert not hasattr(found, "webhook_secret")
    assert repr(found) == "ZoomCredentials(slug='zoom-test')"


def test_the_states_and_the_secret_getters():
    conn = zm.connection()
    assert (conn.credentials_state, conn.webhook_secret_state, conn.has_webhook_secret) == (
        "saved",
        "none",
        False,
    )
    conn.set_webhook_secret(WEBHOOK_SECRET, by=None)
    assert (conn.webhook_secret_state, conn.has_webhook_secret) == ("saved", True)
    zm.make_unreadable(conn, webhook=True)
    assert (conn.credentials_state, conn.webhook_secret_state, conn.has_webhook_secret) == (
        "unreadable",
        "unreadable",
        False,
    )
    with pytest.raises(SecretUnreadable):
        conn.get_client_secret()
    with pytest.raises(SecretUnreadable):
        conn.get_webhook_secret()
    with pytest.raises(SecretUnreadable):
        conn.credentials()


def test_rotate_secrets_reencrypts_both_and_changes_no_record(settings, it_user):
    conn = zm.connection(webhook_secret=WEBHOOK_SECRET, by=it_user)
    before = (conn.credentials_version, conn.credentials_changed_at, conn.webhook_secret_changed_at)
    new_key = Fernet.generate_key().decode()
    settings.HOST_KEY_ENCRYPTION_KEYS = [new_key, *settings.HOST_KEY_ENCRYPTION_KEYS]
    assert conn.rotate_secrets() == 2
    settings.HOST_KEY_ENCRYPTION_KEYS = [new_key]
    assert (conn.get_client_secret(), conn.get_webhook_secret()) == (
        zm.CLIENT_SECRET,
        WEBHOOK_SECRET,
    )
    after = (conn.credentials_version, conn.credentials_changed_at, conn.webhook_secret_changed_at)
    assert after == before


def test_rotate_secrets_names_what_it_couldnt_read():
    conn = zm.make_unreadable(zm.connection(webhook_secret=WEBHOOK_SECRET))
    with pytest.raises(SecretUnreadable) as caught:
        conn.rotate_secrets()
    assert caught.value.args == ("client secret",) and caught.value.rotated == 1


# --------------------------------------------------------------------------- 3 locks


def test_bookable_and_for_management_load_the_connection(django_assert_num_queries):
    zm.connect(make_account("Zoom 01"))
    with django_assert_num_queries(1):
        [account] = list(HostAccount.objects.bookable())
        assert account.zoom_connection_state == "ready"
    with django_assert_num_queries(1):
        [account] = list(HostAccount.objects.for_management())
        assert account.zoom_connection.slug == "zoom-test"


def test_locking_reads_lock_only_the_account_rows():
    """D8: no booking path ever locks a ``ZoomConnection`` row."""
    zm.connect(make_account("Zoom 01"))
    occurrences = list(make_request().occurrences.all())
    with CaptureQueriesContext(connection) as queries:
        HostAccount.objects.availability_for(occurrences, lock=True)
        list(HostAccount.objects.locked())
    locks = [q["sql"] for q in queries if "FOR UPDATE" in q["sql"]]
    assert locks
    for sql in locks:
        assert "zoom_zoomconnection" not in sql.split("FOR UPDATE")[1]


def test_approve_locks_no_connection_row(it_user):
    account = make_account("Zoom 01")
    zm.connect(account)
    link_request = make_request()
    with CaptureQueriesContext(connection) as queries:
        result = services.approve(link_request.pk, account_id=account.pk, by=it_user)
    assert result.outcome == services.Outcome.APPROVED
    for sql in [q["sql"] for q in queries if "FOR UPDATE" in q["sql"]]:
        assert "zoom_zoomconnection" not in sql.split("FOR UPDATE")[1]


# --------------------------------------------------------------------------- 5-7 at rest


def test_the_secret_name_rule_covers_connections():
    pattern = re.compile(r"password|secret|host_key|hostkey|token|start_url", re.IGNORECASE)
    found = [
        f"ZoomConnection.{field.name}"
        for field in ZoomConnection._meta.get_fields()
        if pattern.search(field.name)
    ]
    assert found == [
        "ZoomConnection.client_secret_encrypted",
        "ZoomConnection.webhook_secret_encrypted",
        "ZoomConnection.webhook_secret_changed_at",
        "ZoomConnection.webhook_secret_changed_by",
    ]


def test_secrets_are_stored_as_ciphertext_only():
    conn = zm.connection(webhook_secret=WEBHOOK_SECRET)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT client_secret_encrypted, webhook_secret_encrypted FROM zoom_zoomconnection "
            "WHERE id = %s",
            [conn.pk],
        )
        client_raw, webhook_raw = cursor.fetchone()
    assert client_raw.startswith("gAAAAA") and webhook_raw.startswith("gAAAAA")
    for raw in (client_raw, webhook_raw):
        assert zm.CLIENT_SECRET not in raw and WEBHOOK_SECRET not in raw


def test_the_same_secret_twice_gives_different_ciphertexts():
    first = zm.connection("zoom-01")
    second = zm.connection("zoom-02")
    assert first.client_secret_encrypted != second.client_secret_encrypted
    assert first.get_client_secret() == second.get_client_secret() == zm.CLIENT_SECRET


def test_another_key_makes_everything_unreadable():
    account = make_account("Zoom 01")
    zm.connect(account, webhook_secret=WEBHOOK_SECRET)
    with override_settings(HOST_KEY_ENCRYPTION_KEYS=[zm.OTHER_FERNET_KEY]):
        conn = ZoomConnection.objects.get()
        assert (conn.credentials_state, conn.webhook_secret_state) == ("unreadable", "unreadable")
        assert HostAccount.objects.bookable().get().zoom_connection_state == "unreadable"


def test_crypto_names_the_error_for_every_secret_and_is_the_only_cryptography_import():
    assert not hasattr(crypto, "HostKeyUnreadable")
    assert crypto.SecretUnreadable is SecretUnreadable
    assert "the one secret" not in crypto.__doc__
    importers = [
        path.relative_to(ZOOM_APP).as_posix()
        for path in ZOOM_APP.rglob("*.py")
        if "tests" not in path.parts
        and re.search(r"^\s*(from|import)\s+cryptography", path.read_text("utf-8"), re.M)
    ]
    assert importers == ["crypto.py"]


# --------------------------------------------------------------------------- 8 permission


@pytest.mark.parametrize("name", ["list", "add", "edit"])
def test_each_page_needs_the_change_permission(name, plain_user, it_client):
    conn = zm.connection()
    url = {"list": LIST_URL, "add": ADD_URL, "edit": edit_url(conn)}[name]
    client = Client()
    response = client.get(url)
    assert response.status_code == 302 and response.url.startswith(reverse("accounts:login"))
    client.force_login(plain_user)
    assert client.get(url).status_code == 403
    client.force_login(_user_with("view_hostaccount", username="keyless"))
    assert client.get(url).status_code == 403
    response = it_client.get(url)
    assert response.status_code == 200
    assert "no-store" in response["Cache-Control"]


def test_a_connection_has_no_permissions_of_its_own():
    content_type = ContentType.objects.get_for_model(ZoomConnection)
    assert not Permission.objects.filter(content_type=content_type).exists()


# --------------------------------------------------------------------------- 10 the list


def test_the_list_shows_each_connection_with_its_accounts_and_states(it_client):
    first = zm.connection("zoom-01", webhook_secret=WEBHOOK_SECRET)
    zm.make_unreadable(zm.connection("zoom-09"))
    zm.connection("zoom-02")
    for label, order in (("Zoom 05", 1), ("Zoom 02", 1), ("Zoom 03", 0)):
        account = make_account(label, sort_order=order)
        zm.connect(account, slug="zoom-01")
    response = it_client.get(LIST_URL)
    rows = [
        (
            c.pk,
            c.slug,
            [a.label for a in c.accounts_in_use],
            c.credentials_state,
            c.webhook_secret_state,
        )
        for c in response.context["connections"]
    ]
    assert rows[0] == (first.pk, "zoom-01", ["Zoom 03", "Zoom 02", "Zoom 05"], "saved", "saved")
    assert [r[1:] for r in rows[1:]] == [
        ("zoom-02", [], "saved", "none"),
        ("zoom-09", [], "unreadable", "none"),
    ]
    html = response.content.decode()
    for value in (zm.ACCOUNT_ID, zm.CLIENT_ID, zm.CLIENT_SECRET, WEBHOOK_SECRET, *ciphertexts()):
        assert value not in html


def test_the_list_query_count_is_fixed(it_client):
    def count():
        with CaptureQueriesContext(connection) as queries:
            assert it_client.get(LIST_URL).status_code == 200
        return len(queries)

    def add(number):
        zm.connection(f"zoom-{number:02d}")
        for index in (1, 2):
            zm.connect(make_account(f"Zoom {number}-{index}"), slug=f"zoom-{number:02d}")

    add(1)
    one = count()
    for number in range(2, 6):
        add(number)
    assert count() == one


# --------------------------------------------------------------------------- 11 add


def test_a_valid_add_creates_the_connection_through_the_model(it_client, it_user, frozen_now):
    response = it_client.post(ADD_URL, add_data(webhook_secret=WEBHOOK_SECRET))
    assert response.status_code == 302 and response.url == LIST_URL
    conn = ZoomConnection.objects.get()
    assert (conn.slug, conn.account_id, conn.client_id) == ("zoom-01", zm.ACCOUNT_ID, zm.CLIENT_ID)
    assert conn.credentials_version == 1
    assert (conn.credentials_changed_at, conn.credentials_changed_by) == (frozen_now, it_user)
    assert (conn.webhook_secret_changed_at, conn.webhook_secret_changed_by) == (frozen_now, it_user)
    assert (conn.get_client_secret(), conn.get_webhook_secret()) == (
        zm.CLIENT_SECRET,
        WEBHOOK_SECRET,
    )
    assert flashes(response) == [
        "Added the Zoom connection zoom-01. Next, choose it on the Zoom account that uses it, "
        "then press Check connection there."
    ]


def test_values_are_trimmed_and_the_webhook_secret_is_optional(it_client):
    response = it_client.post(ADD_URL, add_data(slug=" zoom-01 ", account_id=f" {zm.ACCOUNT_ID}\t"))
    assert response.status_code == 302
    conn = ZoomConnection.objects.get()
    assert (conn.slug, conn.account_id, conn.webhook_secret_state) == (
        "zoom-01",
        zm.ACCOUNT_ID,
        "none",
    )
    assert conn.webhook_secret_changed_at is None


ADD_COPY = {
    "slug": (
        "Connection name",
        "A short name for this Zoom app, like zoom-01. Use lower-case letters, numbers and "
        "hyphens. It can't be changed later, because it's part of the address Zoom sends changes "
        "to.",
    ),
    "account_id": ("Account ID", "Copy the Account ID from App Credentials and paste it here."),
    "client_id": ("Client ID", "Copy the Client ID from App Credentials and paste it here."),
    "client_secret": (
        "Client secret",
        "Copy the Client Secret from App Credentials and paste it here. For safety, it's never "
        "shown again once saved.",
    ),
    "webhook_secret": (
        "Webhook secret",
        "Optional. The Secret Token from the Event Subscriptions part of the Zoom app. You can "
        "add it later, on this connection's page, which also shows the address Zoom needs.",
    ),
}
CLIENT_HELP = {
    "saved": "Leave it empty to keep the saved one. If the Client Secret was regenerated in "
    "Zoom, paste the new one here.",
    "unreadable": "Paste the Client Secret from App Credentials. The saved one can't be used.",
}
WEBHOOK_HELP = {
    "none": "Paste the Secret Token from the Event Subscriptions part of the Zoom app, and "
    "save. Then press Validate in Zoom.",
    "saved": "Leave it empty to keep the saved one. If the Secret Token was regenerated in "
    "Zoom, paste the new one here.",
    "unreadable": "Paste the Secret Token from the Event Subscriptions part of the Zoom app. "
    "The saved one can't be used.",
}
REMOVE_COPY = (
    "Remove the saved webhook secret",
    "Tick this if the saved secret is wrong and you don't have the new one yet. Changes made "
    "in Zoom then stop being seen here.",
)


def test_the_add_form_labels_and_help():
    form = ZoomConnectionForm()
    assert list(form.fields) == list(ADD_COPY)
    assert {n: (f.label, f.help_text) for n, f in form.fields.items()} == ADD_COPY
    assert [n for n, f in form.fields.items() if f.required] == [
        "slug",
        "account_id",
        "client_id",
        "client_secret",
    ]


@pytest.mark.parametrize(
    ("page", "required"), [("add", True), ("unreadable", True), ("saved", False)]
)
def test_the_client_secret_is_marked_required_only_when_it_is(page, required):
    """Criterion 11 (D21 SF2): add, or change with an unreadable secret; not a readable one."""
    if page == "add":
        form = ZoomConnectionForm()
    else:
        conn = zm.connection()
        if page == "unreadable":
            zm.make_unreadable(conn)
        form = ZoomConnectionForm(instance=conn)
    tag = str(form["client_secret"])
    assert form.fields["client_secret"].required is required
    assert (" required" in tag) is required
    assert form.fields["client_secret"].error_messages["required"] == CLIENT_SECRET_ERROR


def test_the_name_and_id_help_is_the_models_and_is_the_pinned_text():
    """Criterion 11 (D21 SF3): one definition, on the model, borrowed by both pages."""
    for name in ("slug", "account_id", "client_id"):
        assert ZoomConnection._meta.get_field(name).help_text == ADD_COPY[name][1]
    assert ZoomConnectionForm().fields["slug"].help_text == ADD_COPY["slug"][1]
    for form in (ZoomConnectionForm(), ZoomConnectionForm(instance=zm.connection())):
        for name in ("account_id", "client_id"):
            assert form.fields[name].help_text == ZoomConnection._meta.get_field(name).help_text


def test_the_rendered_name_and_id_help_on_both_pages_is_the_models(it_client, settings):
    _real_templates(settings)
    conn = zm.connection()
    for url, names in ((ADD_URL, ("slug", "account_id", "client_id")), (edit_url(conn), ())):
        html = it_client.get(url).content.decode()
        for name in (*names, "account_id", "client_id"):
            help_text = ZoomConnection._meta.get_field(name).help_text
            help_block = re.search(rf'id="{name}-help"[^>]*>(.*?)</', html, re.S)
            assert help_block is not None, name
            assert " ".join(help_block.group(1).split()) == help_text.replace("'", "&#x27;")


@pytest.mark.parametrize("client_state", ["saved", "unreadable"])
@pytest.mark.parametrize("webhook_state", ["none", "saved", "unreadable"])
def test_the_change_form_labels_and_help_follow_the_stored_state(client_state, webhook_state):
    conn = zm.connection(webhook_secret=WEBHOOK_SECRET if webhook_state != "none" else "")
    zm.make_unreadable(
        conn, client=client_state == "unreadable", webhook=webhook_state == "unreadable"
    )
    form = ZoomConnectionForm(instance=conn)
    copy = {n: (f.label, f.help_text) for n, f in form.fields.items()}
    expected = {
        "account_id": ADD_COPY["account_id"],
        "client_id": ADD_COPY["client_id"],
        "client_secret": ("New client secret", CLIENT_HELP[client_state]),
        "webhook_secret": ("New webhook secret", WEBHOOK_HELP[webhook_state]),
    }
    if webhook_state != "none":
        expected["remove_webhook_secret"] = REMOVE_COPY
    assert copy == expected
    assert list(form.fields) == list(expected)


@pytest.mark.parametrize("name", ["account_id", "client_id", "client_secret", "webhook_secret"])
def test_the_pasted_boxes_are_plain_text_with_no_maxlength(name):
    for form in (ZoomConnectionForm(), ZoomConnectionForm(instance=zm.connection())):
        html = str(form[name])
        assert 'type="text"' in html and "maxlength" not in html
        for attribute in (
            'autocomplete="off"',
            'autocapitalize="none"',
            'autocorrect="off"',
            'spellcheck="false"',
        ):
            assert attribute in html
        assert "value=" not in html or name in ("account_id", "client_id")


def test_the_name_keeps_its_maxlength():
    assert 'maxlength="40"' in str(ZoomConnectionForm()["slug"])


# --------------------------------------------------------------------------- 12 change


def test_the_change_form_has_no_name_and_a_posted_name_changes_nothing(it_client):
    conn = zm.connection()
    form = ZoomConnectionForm(instance=conn)
    assert "slug" not in form.fields
    assert form["account_id"].value() == zm.ACCOUNT_ID
    assert form["client_id"].value() == zm.CLIENT_ID
    assert form["client_secret"].value() is None and form["webhook_secret"].value() is None
    response = it_client.post(edit_url(conn), edit_data(conn, slug="zoom-renamed"))
    assert response.status_code == 302
    conn.refresh_from_db()
    assert conn.slug == "zoom-test"


def test_remove_shows_only_when_a_secret_is_stored():
    assert "remove_webhook_secret" not in ZoomConnectionForm(instance=zm.connection()).fields
    saved = zm.connection("zoom-02", webhook_secret=WEBHOOK_SECRET)
    assert "remove_webhook_secret" in ZoomConnectionForm(instance=saved).fields


def test_ticking_remove_clears_an_unreadable_secret(it_client, it_user, frozen_now):
    conn = zm.make_unreadable(
        zm.connection(webhook_secret=WEBHOOK_SECRET), client=False, webhook=True
    )
    response = it_client.post(edit_url(conn), edit_data(conn, remove_webhook_secret="on"))
    assert response.status_code == 302
    conn.refresh_from_db()
    assert conn.webhook_secret_state == "none"
    assert (conn.webhook_secret_changed_at, conn.webhook_secret_changed_by) == (
        frozen_now,
        it_user,
    )


def test_the_change_post_locks_its_row_first(it_client):
    conn = zm.connection()
    with CaptureQueriesContext(connection) as queries:
        it_client.post(edit_url(conn), edit_data(conn))
    sql = [q["sql"] for q in queries]
    lock = next(i for i, s in enumerate(sql) if "FOR UPDATE OF `zoom_zoomconnection`" in s)
    update = next(i for i, s in enumerate(sql) if s.startswith("UPDATE `zoom_zoomconnection`"))
    assert lock < update


@pytest.mark.parametrize(
    ("labels", "words"),
    [
        ([], None),
        (["Zoom 01"], "Zoom 01"),
        (["Zoom 01", "Zoom 02"], "Zoom 01 and Zoom 02"),
        (["Zoom 01", "Zoom 02", "Zoom 03"], "Zoom 01, Zoom 02 and Zoom 03"),
    ],
)
def test_the_save_message_names_the_accounts_to_check(it_client, labels, words):
    conn = zm.connection()
    for order, label in enumerate(labels):
        zm.connect(make_account(label, sort_order=order))
    response = it_client.post(edit_url(conn), edit_data(conn, client_secret=zm.NEW_CLIENT_SECRET))
    assert response.status_code == 302 and response.url == LIST_URL
    if words is None:
        expected = (
            "Saved the Zoom connection zoom-test. Next, choose it on the Zoom account that uses "
            "it, then press Check connection there."
        )
    else:
        expected = (
            "Saved the Zoom connection zoom-test. To make sure Zoom accepts it, press Check "
            f"connection on {words}."
        )
    assert flashes(response) == [expected]


def test_a_save_that_changes_nothing_records_nothing(it_client):
    conn = zm.connection()
    before = (conn.credentials_version, conn.credentials_changed_at, conn.credentials_changed_by)
    response = it_client.post(edit_url(conn), edit_data(conn))
    assert response.status_code == 302
    conn.refresh_from_db()
    assert (
        conn.credentials_version,
        conn.credentials_changed_at,
        conn.credentials_changed_by,
    ) == before
    assert flashes(response)[0].startswith("Saved the Zoom connection zoom-test.")


# --------------------------------------------------------------------------- 13 errors

SUMMARY_LEAD = "We couldn't save this Zoom connection yet."
ACCOUNT_ID_ERROR = (
    "Paste the Account ID from the App Credentials page of the Zoom app. It has no spaces."
)
CLIENT_ID_ERROR = (
    "Paste the Client ID from the App Credentials page of the Zoom app. It has no spaces."
)
CLIENT_SECRET_ERROR = (
    "Paste the Client Secret from the App Credentials page of the Zoom app. It has no spaces."
)
WEBHOOK_SECRET_ERROR = (
    "Paste the Secret Token from the Event Subscriptions part of the Zoom app. It has no spaces."
)
NAME_RULE = "Use lower-case letters, numbers and hyphens only, like zoom-01."


@pytest.mark.parametrize(
    ("overrides", "field", "message"),
    [
        ({"slug": ""}, "slug", "Type a name for this connection, like zoom-01."),
        ({"slug": "Zoom_01"}, "slug", NAME_RULE),
        ({"slug": "zoom 01"}, "slug", NAME_RULE),
        ({"slug": "a" * 41}, "slug", NAME_RULE),
        ({"account_id": ""}, "account_id", ACCOUNT_ID_ERROR),
        ({"account_id": "has space"}, "account_id", ACCOUNT_ID_ERROR),
        ({"account_id": "a" * 101}, "account_id", ACCOUNT_ID_ERROR),
        ({"account_id": "café-id"}, "account_id", ACCOUNT_ID_ERROR),
        ({"client_id": ""}, "client_id", CLIENT_ID_ERROR),
        ({"client_id": "a" * 101}, "client_id", CLIENT_ID_ERROR),
        ({"client_secret": ""}, "client_secret", CLIENT_SECRET_ERROR),
        ({"client_secret": "   "}, "client_secret", CLIENT_SECRET_ERROR),
        ({"client_secret": "two words"}, "client_secret", CLIENT_SECRET_ERROR),
        ({"client_secret": "s" * 201}, "client_secret", CLIENT_SECRET_ERROR),
        ({"webhook_secret": "two words"}, "webhook_secret", WEBHOOK_SECRET_ERROR),
        ({"webhook_secret": "w" * 201}, "webhook_secret", WEBHOOK_SECRET_ERROR),
    ],
)
def test_each_add_error_has_its_pinned_text_and_keeps_the_rest(
    it_client, overrides, field, message
):
    response = it_client.post(ADD_URL, add_data(**overrides))
    assert response.status_code == 200
    form = response.context["form"]
    assert form.errors[field] == [message]
    assert ZoomConnection.objects.count() == 0
    for name in ("slug", "account_id", "client_id"):
        if name not in overrides:
            assert form[name].value() == add_data()[name]


def test_the_limits_are_100_and_200_exactly(it_client):
    ok = add_data(account_id="a" * 100, client_id="c" * 100, client_secret="s" * 200)
    assert it_client.post(ADD_URL, {**ok, "webhook_secret": "w" * 200}).status_code == 302


def test_a_name_and_a_client_id_already_used_are_refused(it_client):
    zm.connection("zoom-01")
    response = it_client.post(ADD_URL, add_data(client_id=zm.client_id_for("zoom-01")))
    assert response.context["form"].errors == {
        "slug": ["Another Zoom connection already has this name. Choose a different one."],
        "client_id": [
            "The Zoom connection zoom-01 already uses this Client ID. Each Zoom app needs only "
            "one connection."
        ],
    }


def test_an_empty_client_secret_keeps_the_saved_one_but_not_an_unreadable_one(it_client):
    conn = zm.connection()
    assert it_client.post(edit_url(conn), edit_data(conn)).status_code == 302
    zm.make_unreadable(conn)
    response = it_client.post(edit_url(conn), edit_data(conn, account_id="test-account-id-2"))
    assert response.status_code == 200
    assert response.context["form"].errors["client_secret"] == [CLIENT_SECRET_ERROR]
    conn.refresh_from_db()
    assert (conn.account_id, conn.client_id, conn.credentials_version) == (
        zm.ACCOUNT_ID,
        zm.CLIENT_ID,
        1,
    )


def test_a_new_webhook_secret_and_remove_together_are_refused(it_client):
    conn = zm.connection(webhook_secret=WEBHOOK_SECRET)
    response = it_client.post(
        edit_url(conn),
        edit_data(conn, webhook_secret=NEW_WEBHOOK_SECRET, remove_webhook_secret="on"),
    )
    assert response.status_code == 200
    assert response.context["form"].errors["webhook_secret"] == [
        "Type a new webhook secret or tick Remove, not both."
    ]
    conn.refresh_from_db()
    assert conn.get_webhook_secret() == WEBHOOK_SECRET


def test_the_error_summary_lead_on_the_real_page(it_client, settings):
    _real_templates(settings)
    response = it_client.post(ADD_URL, add_data(slug=""))
    assert SUMMARY_LEAD in response.content.decode()


# --------------------------------------------------------------------------- 14 never sent back


@pytest.mark.parametrize("real", [False, True])
def test_typed_secrets_are_never_sent_back(it_client, settings, real):
    if real:
        _real_templates(settings)
    data = add_data(
        client_id="bad id", client_secret=TYPED_CLIENT_SECRET, webhook_secret=TYPED_WEBHOOK_SECRET
    )
    response = it_client.post(ADD_URL, data)
    assert response.status_code == 200
    form = response.context["form"]
    assert (form.client_secret_was_typed, form.webhook_secret_was_typed) == (True, True)
    html = response.content.decode()
    assert TYPED_CLIENT_SECRET not in html and TYPED_WEBHOOK_SECRET not in html
    for name in ("client_secret", "webhook_secret"):
        tag = re.search(rf'<input[^>]*name="{name}"[^>]*>', html).group(0)
        assert "value=" not in tag
    if real:
        assert "For your safety, the client secret you typed wasn't kept. Type it again." in html
        assert "For your safety, the webhook secret you typed wasn't kept. Type it again." in html


def test_nothing_typed_means_no_note(it_client):
    form = it_client.post(ADD_URL, add_data(client_id="bad id", client_secret="")).context["form"]
    assert (form.client_secret_was_typed, form.webhook_secret_was_typed) == (False, False)


# --------------------------------------------------------------------------- 15 change page


def test_the_change_page_context(it_client, it_user, monkeypatch, frozen_now):
    conn = zm.connection(webhook_secret=WEBHOOK_SECRET, by=it_user)
    zm.connect(make_account("Zoom 02", sort_order=2))
    zm.connect(make_account("Zoom 01", sort_order=1))
    context = it_client.get(edit_url(conn)).context
    assert context["is_add"] is False and context["connection"] == conn
    assert context["saved_slug"] == "zoom-test"
    assert (context["credentials_state"], context["webhook_secret_state"]) == ("saved", "saved")
    assert context["connection"].credentials_changed_by == it_user
    assert context["last_zoom_event_at"] is None
    assert [a.label for a in context["accounts_in_use"]] == ["Zoom 01", "Zoom 02"]
    assert context["webhook_address"] == "http://testserver/zoom/webhooks/zoom-test/"
    assert context["webhook_address_secure"] is False

    ZoomEvent.objects.create(slug="zoom-test", event="x", body_sha256="1" * 64, outcome="ignored")
    assert it_client.get(edit_url(conn)).context["last_zoom_event_at"] == frozen_now
    secure = it_client.get(edit_url(conn), secure=True).context
    assert secure["webhook_address"] == "https://testserver/zoom/webhooks/zoom-test/"
    assert secure["webhook_address_secure"] is True


def test_the_add_page_context(it_client):
    context = it_client.get(ADD_URL).context
    assert {
        key: context[key]
        for key in (
            "is_add",
            "connection",
            "saved_slug",
            "credentials_state",
            "webhook_secret_state",
            "last_zoom_event_at",
            "webhook_address",
            "webhook_address_secure",
            "accounts_in_use",
        )
    } == {
        "is_add": True,
        "connection": None,
        "saved_slug": "",
        "credentials_state": "none",
        "webhook_secret_state": "none",
        "last_zoom_event_at": None,
        "webhook_address": "",
        "webhook_address_secure": False,
        "accounts_in_use": [],
    }


def test_last_heard_only_when_the_webhook_secret_is_readable(it_client):
    conn = zm.connection()
    ZoomEvent.objects.create(slug="zoom-test", event="x", body_sha256="1" * 64, outcome="ignored")
    assert it_client.get(edit_url(conn)).context["last_zoom_event_at"] is None


# --------------------------------------------------------------------------- 16 no reveal


def test_the_only_reveal_route_is_the_host_keys():
    reveals = [
        p.name
        for p in zoom_urls.urlpatterns
        if re.search(r"reveal|host.key|secret", str(p.pattern))
    ]
    assert reveals == ["account_host_key"]


def test_secrets_are_decrypted_only_by_the_allowed_callers():
    allowed = {"models.py", "webhooks.py"}
    for path in ZOOM_APP.rglob("*.py"):
        if "tests" in path.parts or path.name in allowed:
            continue
        text = path.read_text("utf-8")
        assert "get_client_secret(" not in text and "get_webhook_secret(" not in text, path.name
    webhooks_text = (ZOOM_APP / "webhooks.py").read_text("utf-8")
    assert "get_client_secret(" not in webhooks_text


# --------------------------------------------------------------------------- 17 protection


@pytest.mark.parametrize("page", ["add", "edit"])
def test_an_error_inside_save_masks_both_typed_secrets(it_client, page):
    conn = None if page == "add" else zm.connection()
    url = ADD_URL if conn is None else edit_url(conn)
    data = (add_data if conn is None else lambda **kw: edit_data(conn, **kw))(
        client_secret=TYPED_CLIENT_SECRET, webhook_secret=TYPED_WEBHOOK_SECRET
    )
    reports = []

    def capture(sender, request, **kwargs):
        reports.append(ExceptionReporter(request, *sys.exc_info()))

    got_request_exception.connect(capture)
    it_client.raise_request_exception = False
    try:
        with mock.patch.object(ZoomConnection, "save", side_effect=RuntimeError("boom")):
            response = it_client.post(url, data)
    finally:
        got_request_exception.disconnect(capture)
    assert response.status_code == 500
    [reporter] = reports
    for text in (reporter.get_traceback_html(), reporter.get_traceback_text()):
        assert TYPED_CLIENT_SECRET not in text and TYPED_WEBHOOK_SECRET not in text


@pytest.mark.parametrize("page", ["add", "edit"])
def test_both_pages_need_a_csrf_token(it_user, page):
    conn = zm.connection()
    client = Client(enforce_csrf_checks=True)
    client.force_login(it_user)
    url = ADD_URL if page == "add" else edit_url(conn)
    assert client.post(url, add_data(slug="zoom-02")).status_code == 403


# --------------------------------------------------------------------------- 23-24 fresh reads


def _answers_for(http_mock, account):
    http_mock.add("GET", zm.API + f"/users/{account.email}", json={"type": 2})
    zm.add_listing(http_mock, account.email)


def _token_calls(http_mock):
    return [c for c in http_mock.calls if c.request.url == zm.TOKEN_URL]


def test_a_saved_client_secret_is_used_at_once_with_no_restart(it_client, http_mock):
    account = make_account("Zoom 03")
    conn = zm.connect(account)
    zm.add_token(http_mock, zm.TOKEN, secret=zm.CLIENT_SECRET)
    zm.add_token(http_mock, zm.SECOND_TOKEN, secret=zm.NEW_CLIENT_SECRET)
    _answers_for(http_mock, account)
    check = reverse("zoom:account_check", args=[account.pk])

    it_client.post(check)
    saved = it_client.post(edit_url(conn), edit_data(conn, client_secret=zm.NEW_CLIENT_SECRET))
    assert saved.status_code == 302
    response = it_client.post(check)
    assert flashes(response)[-1] == "The Zoom connection works for Zoom 03."
    tokens = _token_calls(http_mock)
    assert len(tokens) == 2
    assert tokens[0].request.headers["Authorization"] == zm.basic_auth(secret=zm.CLIENT_SECRET)
    assert tokens[1].request.headers["Authorization"] == zm.basic_auth(secret=zm.NEW_CLIENT_SECRET)


def _check_once(account):
    fresh = HostAccount.objects.select_related("zoom_connection").get(pk=account.pk)
    return ZoomProvider().check_connection(fresh)


def test_another_workers_save_makes_the_next_call_fetch_a_new_token(http_mock):
    account = make_account("Zoom 03")
    conn = zm.connect(account)
    zm.add_token(http_mock)
    _answers_for(http_mock, account)
    _check_once(account)
    _check_once(account)
    assert len(_token_calls(http_mock)) == 1  # reused
    ZoomConnection.objects.filter(pk=conn.pk).update(credentials_version=2)
    _check_once(account)
    assert len(_token_calls(http_mock)) == 2
    assert {key[1:] for key in zoom_api._token_cache if key[0] == "zoom-test"} == {
        (2, zm.CLIENT_ID)
    }


def test_changing_only_the_webhook_secret_keeps_the_token(http_mock):
    account = make_account("Zoom 03")
    conn = zm.connect(account)
    zm.add_token(http_mock)
    _answers_for(http_mock, account)
    _check_once(account)
    conn.set_webhook_secret(WEBHOOK_SECRET, by=None)
    conn.save()
    _check_once(account)
    assert len(_token_calls(http_mock)) == 1


def test_the_cache_key_is_the_name_the_version_and_the_client_id():
    client = zoom_api.ZoomClient(zm.credentials(version=3))
    client.close()
    assert client._cache_key == ("zoom-test", 3, zm.CLIENT_ID)


def test_a_new_version_drops_the_old_versions_token():
    other = ("zoom-other", 1, zm.client_id_for("zoom-other"))
    zoom_api._token_cache[("zoom-test", 1, zm.CLIENT_ID)] = ("old-token", 10**12)
    zoom_api._token_cache[("zoom-test", 1, "another-apps-client-id")] = ("old-app", 10**12)
    zoom_api._token_cache[other] = ("kept-token", 10**12)
    zoom_api.ZoomClient(zm.credentials(version=2)).close()
    assert [key for key in zoom_api._token_cache if key[0] == "zoom-test"] == []
    assert other in zoom_api._token_cache


def test_a_stale_read_doesnt_drop_a_newer_versions_token(http_mock):
    account = make_account("Zoom 03")
    conn = zm.connect(account)
    ZoomConnection.objects.filter(pk=conn.pk).update(credentials_version=2)
    zm.add_token(http_mock)
    _answers_for(http_mock, account)
    _check_once(account)
    assert len(_token_calls(http_mock)) == 1
    # Another worker read the row before the save that made version 2.
    zoom_api.ZoomClient(zm.credentials(version=1)).close()
    assert ("zoom-test", 2, zm.CLIENT_ID) in zoom_api._token_cache
    _check_once(account)
    assert len(_token_calls(http_mock)) == 1  # version 2's token was reused


def test_a_connection_re_added_under_the_same_name_gets_its_own_token(http_mock):
    account = make_account("Zoom 03")
    old = zm.connect(account)
    zm.add_token(http_mock, zm.TOKEN, client_id=zm.CLIENT_ID)
    zm.add_token(http_mock, zm.SECOND_TOKEN, client_id="other-client-id")
    _answers_for(http_mock, account)
    _check_once(account)
    assert ("zoom-test", 1, zm.CLIENT_ID) in zoom_api._token_cache

    account.zoom_connection = None
    account.save(update_fields=["zoom_connection"])
    old.delete()
    readded = ZoomConnection(slug="zoom-test")
    readded.set_credentials(
        account_id=zm.ACCOUNT_ID,
        client_id="other-client-id",
        client_secret=zm.CLIENT_SECRET,
        by=None,
    )
    readded.save()
    assert readded.credentials_version == 1
    zm.connect(account)
    calls_before = len(http_mock.calls)
    _check_once(account)

    tokens = _token_calls(http_mock)
    assert len(tokens) == 2
    assert tokens[1].request.headers["Authorization"] == zm.basic_auth(client_id="other-client-id")
    later = [c for c in http_mock.calls[calls_before:] if c.request.url != zm.TOKEN_URL]
    assert later
    for call in later:
        assert call.request.headers["Authorization"] == f"Bearer {zm.SECOND_TOKEN}"


# --------------------------------------------------------------------------- 25 the preview


def test_the_preview_key_follows_the_connection_and_its_version():
    account = make_account("Zoom 01")
    window = tuple(o.starts_at for o in make_request().occurrences.all()[:1]) * 2
    zm.connect(account)
    first = services._preview_key(account, window)
    ZoomConnection.objects.filter(pk=account.zoom_connection_id).update(credentials_version=2)
    account = HostAccount.objects.select_related("zoom_connection").get(pk=account.pk)
    second = services._preview_key(account, window)
    zm.connect(account, slug="zoom-other")
    third = services._preview_key(account, window)
    assert len({first, second, third}) == 3


def test_the_previews_threads_run_no_query(it_client, settings, http_mock, monkeypatch):
    settings.ZOOM_PROVIDER = "zoom"
    for number in (1, 2):
        account = make_account(f"Zoom 0{number}", sort_order=number)
        zm.connect(account)
        zm.add_listing(http_mock, account.email)
    zm.add_token(http_mock)
    threads = []
    real = CursorWrapper._execute_with_wrappers

    def spy(self, *args, **kwargs):
        threads.append(threading.current_thread().name)
        return real(self, *args, **kwargs)

    monkeypatch.setattr(CursorWrapper, "_execute_with_wrappers", spy)
    response = it_client.get(reverse("zoom:detail", args=[make_request().pk]))
    assert response.status_code == 200
    assert all(entry["zoom_state"] == "checked" for entry in response.context["availability"])
    assert threads and not [name for name in threads if name.startswith("zoom-preview")]


# --------------------------------------------------------------------------- 26 source scan


def test_no_module_reads_credentials_from_settings():
    """Criterion 26 for ``apps/zoom`` (the platform scan of ``config/`` is devops's, c. 36)."""
    needles = ["ZOOM_" + "S2S", "ZOOM_" + "CREDENTIAL"]
    for path in ZOOM_APP.rglob("*.py"):
        text = path.read_text("utf-8")
        for needle in needles:
            assert needle not in text, path.name
        assert "config" + ".settings" not in text, path.name


# --------------------------------------------------------------------------- 27-29 the webhook


@pytest.fixture
def zoom02(db):
    account = make_account("Zoom 02", sort_order=2)
    kit.connect(account)
    return account


def test_a_call_makes_exactly_one_lookup_of_four_columns(client, zoom02):
    with CaptureQueriesContext(connection) as queries:
        assert kit.post(client, kit.validation_event()).status_code == 200
    [query] = queries
    sql = query["sql"]
    assert "zoom_zoomconnection" in sql and "client_secret" not in sql
    for column in ("`id`", "`slug`", "`account_id`", "`webhook_secret_encrypted`"):
        assert column in sql


def test_an_unreadable_webhook_secret_is_404_with_one_warning(client, zoom02, caplog):
    zm.make_unreadable(zoom02.zoom_connection, client=False, webhook=True)
    caplog.set_level(logging.DEBUG)
    assert kit.post(client, kit.validation_event()).status_code == 404
    warnings = [
        r for r in caplog.records if r.name.startswith("apps.zoom") and r.levelno >= logging.WARNING
    ]
    assert [r.getMessage() for r in warnings] == [
        "Zoom webhook call to zoom-02 refused: unreadable secret"
    ]


def test_bookings_are_matched_by_connection(client, settings, zoom02, http_mock, caplog):
    """Criterion 28: the same meeting ID on another connection's account is ``not_ours``."""
    settings.ZOOM_PROVIDER = "zoom"
    other = make_account("Zoom 03", sort_order=3)
    kit.connect(other, slug="zoom-03", secret="x")
    kit.zl42(other)
    caplog.set_level(logging.DEBUG)
    assert kit.post(client, kit.meeting_event()).status_code == 200
    assert ZoomEvent.objects.get().outcome == "not_ours"
    assert len(http_mock.calls) == 0


def test_a_handled_event_costs_at_most_one_lookup_more(client, settings, zoom02, http_mock):
    """Criterion 28: ``meeting.deleted`` that reconciles, against the same call minus verify."""
    settings.ZOOM_PROVIDER = "zoom"
    zm.add_token(http_mock)
    booking = kit.zl42(zoom02)
    kit.add_meeting(http_mock, status=404)
    event = kit.meeting_event()
    with CaptureQueriesContext(connection) as handled:
        assert kit.post(client, event).status_code == 200
    booking.refresh_from_db()
    assert booking.status == "cancelled"
    lookups = [q for q in handled if "FROM `zoom_zoomconnection`" in q["sql"]]
    assert len(lookups) == 1  # verify's; reconcile reads the connection with the account


def test_a_saved_webhook_secret_works_on_the_next_call(client, it_client, zoom02):
    """Criterion 29, steps 1-5, with no restart or cache reset between them."""
    conn = kit.connect(zoom02, secret="")
    assert kit.post(client, kit.validation_event()).status_code == 404
    assert (
        it_client.post(edit_url(conn), edit_data(conn, webhook_secret=WEBHOOK_SECRET)).status_code
        == 302
    )
    response = kit.post(client, kit.validation_event("abc123"), secret=WEBHOOK_SECRET)
    assert response.status_code == 200 and response.json()["plainToken"] == "abc123"
    it_client.post(edit_url(conn), edit_data(conn, webhook_secret=NEW_WEBHOOK_SECRET))
    assert kit.post(client, kit.validation_event(), secret=WEBHOOK_SECRET).status_code == 401
    assert kit.post(client, kit.validation_event(), secret=NEW_WEBHOOK_SECRET).status_code == 200
    it_client.post(edit_url(conn), edit_data(conn, remove_webhook_secret="on"))
    assert kit.post(client, kit.validation_event(), secret=NEW_WEBHOOK_SECRET).status_code == 404


def test_the_verified_connections_repr_names_the_connection_only(zoom02):
    verified = kit.verified()
    assert repr(verified) == f"VerifiedConnection(pk={verified.pk}, slug='zoom-02')"
    assert isinstance(verified, webhooks.VerifiedConnection)


# --------------------------------------------------------------------------- 33 W002 unreadable


def test_w002_reports_an_unreadable_webhook_secret(settings):
    from apps.zoom import checks as zoom_checks

    settings.ZOOM_PROVIDER = "zoom"
    account = make_account("Zoom 02")
    conn = kit.connect(account)
    zm.make_unreadable(conn, client=False, webhook=True)
    [warning] = zoom_checks.check_webhook_secrets(databases=["default"])
    assert (warning.id, warning.msg) == (
        "zoom.W002",
        "Zoom 02's Zoom connection has a webhook secret that can't be read with the current "
        "encryption keys, so changes made directly in Zoom to its meetings aren't seen here.",
    )
    assert warning.hint == (
        "Add the webhook secret on the Zoom connection's page. The README says where Zoom shows it."
    )


# --------------------------------------------------------------------------- 34 rotation


def test_rotation_reencrypts_every_secret_in_one_command(settings):
    old_key = settings.HOST_KEY_ENCRYPTION_KEYS[0]
    make_account("Zoom 01", host_key="8421973")
    zm.connection("zoom-01", webhook_secret=WEBHOOK_SECRET)
    zm.connection("zoom-02")
    before = list(
        ZoomConnection.objects.values_list(
            "credentials_version", "credentials_changed_at", "webhook_secret_changed_at"
        )
    )
    new_key = Fernet.generate_key().decode()
    settings.HOST_KEY_ENCRYPTION_KEYS = [new_key, old_key]
    out, err = StringIO(), StringIO()
    call_command("rotate_encryption_keys", stdout=out, stderr=err)
    assert out.getvalue() == "Re-encrypted 1 host key and 3 Zoom connection secrets.\n"
    assert err.getvalue() == ""
    settings.HOST_KEY_ENCRYPTION_KEYS = [new_key]
    assert HostAccount.objects.get().get_host_key() == "8421973"
    for conn in ZoomConnection.objects.all():
        assert conn.get_client_secret() == zm.CLIENT_SECRET
    assert ZoomConnection.objects.get(slug="zoom-01").get_webhook_secret() == WEBHOOK_SECRET
    assert (
        list(
            ZoomConnection.objects.values_list(
                "credentials_version", "credentials_changed_at", "webhook_secret_changed_at"
            )
        )
        == before
    )


def test_rotation_names_every_unreadable_value_and_exits_1(settings):
    make_account("Zoom 01", host_key="8421973")
    zm.make_unreadable(zm.connection("zoom-01", webhook_secret=WEBHOOK_SECRET), webhook=True)
    zm.connection("zoom-02")
    HostAccount.objects.update(host_key_encrypted=zm.foreign_token())
    out, err = StringIO(), StringIO()
    with pytest.raises(CommandError) as caught:
        call_command("rotate_encryption_keys", stdout=out, stderr=err)
    assert caught.value.returncode == 1
    assert out.getvalue() == "Re-encrypted 0 host keys and 1 Zoom connection secret.\n"
    assert err.getvalue() == (
        "Couldn't read: the host key of Zoom 01; the client secret of zoom-01; the webhook "
        "secret of zoom-01. Type those again on the Zoom accounts and Zoom connections pages.\n"
    )
    for text in (out.getvalue(), err.getvalue(), str(caught.value)):
        for value in ("8421973", zm.CLIENT_SECRET, WEBHOOK_SECRET):
            assert value not in text


def test_the_old_command_is_gone():
    assert not (ZOOM_APP / "management" / "commands" / "rotate_host_keys.py").exists()


# --------------------------------------------------------------------------- 40-43 sweeps


def test_nothing_secret_is_logged_anywhere(client, it_client, settings, http_mock, caplog):
    """Criterion 40: records at DEBUG for apps.zoom, django, requests and urllib3."""
    for name in ("apps.zoom", "django", "requests", "urllib3"):
        caplog.set_level(logging.DEBUG, logger=name)
    seen_ciphertexts = []

    it_client.post(ADD_URL, add_data(slug="zoom-02", webhook_secret=WEBHOOK_SECRET))
    conn = ZoomConnection.objects.get(slug="zoom-02")
    seen_ciphertexts += ciphertexts()
    it_client.post(
        edit_url(conn),
        edit_data(conn, client_secret=zm.NEW_CLIENT_SECRET, webhook_secret=NEW_WEBHOOK_SECRET),
    )
    seen_ciphertexts += ciphertexts()
    it_client.post(
        ADD_URL,
        add_data(
            slug="Bad", client_secret=TYPED_CLIENT_SECRET, webhook_secret=TYPED_WEBHOOK_SECRET
        ),
    )
    account = make_account("Zoom 02", sort_order=2)
    zm.connect(account, slug="zoom-02")
    zm.add_token(http_mock)
    _answers_for(http_mock, account)
    it_client.post(reverse("zoom:account_check", args=[account.pk]))
    signed = {"secret": NEW_WEBHOOK_SECRET}
    assert kit.post(client, kit.validation_event(), **signed).status_code == 200
    settings.ZOOM_PROVIDER = "zoom"
    kit.zl42(account)
    kit.add_meeting(http_mock, status=404)
    assert kit.post(client, kit.meeting_event(), **signed).status_code == 200
    settings.HOST_KEY_ENCRYPTION_KEYS = [
        Fernet.generate_key().decode(),
        *settings.HOST_KEY_ENCRYPTION_KEYS,
    ]
    call_command("rotate_encryption_keys", stdout=StringIO(), stderr=StringIO())
    seen_ciphertexts += ciphertexts()

    forbidden = (
        zm.CLIENT_SECRET,
        zm.NEW_CLIENT_SECRET,
        WEBHOOK_SECRET,
        NEW_WEBHOOK_SECRET,
        TYPED_CLIENT_SECRET,
        TYPED_WEBHOOK_SECRET,
        zm.ACCOUNT_ID,
        zm.client_id_for("zoom-02"),
        "Basic ",
        "Bearer ",
        zm.TOKEN,
        *seen_ciphertexts,
    )
    texts = [record.getMessage() for record in caplog.records]
    texts += [str(record.args) for record in caplog.records if record.args]
    assert texts
    for text in texts:
        for value in forbidden:
            assert value not in text


def test_values_appear_only_where_allowed(it_client, settings, http_mock):
    """Criteria 14 and 41: secrets and ciphertexts nowhere; the IDs only on the change page."""
    _real_templates(settings)
    account = make_account("Zoom 01", host_key="8421973")
    conn = zm.connect(account, webhook_secret=WEBHOOK_SECRET)
    secrets = (zm.CLIENT_SECRET, WEBHOOK_SECRET, *ciphertexts())
    ids = (zm.ACCOUNT_ID, zm.CLIENT_ID)
    pages = {
        "list": it_client.get(LIST_URL),
        "add": it_client.get(ADD_URL),
        "accounts": it_client.get(reverse("zoom:accounts")),
        "account add": it_client.get(reverse("zoom:account_add")),
        "account edit": it_client.get(reverse("zoom:account_edit", args=[account.pk])),
        "change": it_client.get(edit_url(conn)),
    }
    saved = it_client.post(edit_url(conn), edit_data(conn))
    for name, page in pages.items():
        assert page.status_code == 200, name
        html = page.content.decode()
        for value in secrets:
            assert value not in html, name
        for value in ids:
            assert (value in html) is (name == "change"), (name, value)
    change = pages["change"].content.decode()
    for value in ids:
        assert re.search(rf'<input[^>]*value="{re.escape(value)}"', change)
    for text in flashes(saved):
        for value in (*secrets, *ids):
            assert value not in text
    assert mail.outbox == []


def test_reprs_show_only_the_name_or_label():
    account = make_account("Zoom 01")
    conn = zm.connect(account, webhook_secret=WEBHOOK_SECRET)
    credentials = conn.credentials()
    client = zoom_api.ZoomClient(credentials)
    texts = [repr(conn), str(conn), repr(credentials), str(credentials), repr(client)]
    texts += [repr(account), repr(HostAccount.objects.select_related("zoom_connection").get())]
    client.close()
    for text in texts:
        for value in (
            zm.ACCOUNT_ID,
            zm.CLIENT_ID,
            zm.CLIENT_SECRET,
            WEBHOOK_SECRET,
            *ciphertexts(),
        ):
            assert value not in text


def test_tokens_are_in_no_table_and_not_in_djangos_cache(http_mock):
    """Criterion 43 (006 criterion 9): the table dump includes ``zoom_zoomconnection``."""
    from django.core.cache import cache

    account = make_account("Zoom 01")
    zm.connect(account)
    zm.add_token(http_mock)
    _answers_for(http_mock, account)
    _check_once(account)
    tables = [t for t in connection.introspection.table_names() if t.startswith("zoom_")]
    assert "zoom_zoomconnection" in tables
    with connection.cursor() as cursor:
        for table in tables:
            cursor.execute(f"SELECT * FROM `{table}`")  # noqa: S608 (a fixed table list)
            dump = repr(cursor.fetchall())
            assert zm.TOKEN not in dump, table
    assert not any(zm.TOKEN in repr(value) for value in cache._cache.values())


# --------------------------------------------------------------------------- 51 saving at once

NAME_TAKEN = "Another Zoom connection already has this name. Choose a different one."
RACE_LOGGERS = ("apps.zoom", "django", "django.db.backends", "requests", "urllib3")


def _client_id_taken(slug):
    return (
        f"The Zoom connection {slug} already uses this Client ID. Each Zoom app needs only one "
        "connection."
    )


def _stored(conn):
    """Everything a half-save could change, read fresh from the database."""
    return ZoomConnection.objects.filter(pk=conn.pk).values_list(
        "slug",
        "account_id",
        "client_id",
        "client_secret_encrypted",
        "webhook_secret_encrypted",
        "credentials_version",
        "credentials_changed_at",
        "webhook_secret_changed_at",
    )[0]


def _form_check_misses(monkeypatch):
    """The other person's row commits just after this form's Client ID check.

    The form's ``client_id_taken_by`` call finds nothing; every later call (the re-check after
    the ``IntegrityError``) asks the database for real.
    """
    real = ZoomConnection.client_id_taken_by
    calls = []

    def first_call_misses(self, client_id):
        calls.append(client_id)
        return None if len(calls) == 1 else real(self, client_id)

    monkeypatch.setattr(ZoomConnection, "client_id_taken_by", first_call_misses)
    return calls


def _capture_everything(caplog):
    for name in RACE_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=name)


def _assert_nothing_leaked(caplog, secrets, ids, *, real):
    """Criterion 51's log sweep, read as each handler wrote it (``exc_text`` is set at emit).

    With the real templates and ``django`` forced to DEBUG, ``django.template`` logs each
    missing optional variable with a traceback whose text includes the field's widget context,
    and so a typed Account ID or Client ID. ``config/settings/base.py`` pins ``django`` at INFO,
    so those records are never made outside a test; criterion 40's sweep uses the stub
    templates for the same reason. The IDs are therefore checked on the stub-template run,
    and secrets, ciphertexts and the database's error text on both.
    """
    texts = [record.getMessage() for record in caplog.records]
    texts += [str(record.args) for record in caplog.records if record.args]
    texts += [record.exc_text for record in caplog.records if record.exc_text]
    forbidden = ("Duplicate entry", "IntegrityError", *secrets, *(() if real else ids))
    for text in texts:
        for value in forbidden:
            assert value not in text
    assert not [
        r for r in caplog.records if r.name == "django.request" and r.levelno >= logging.ERROR
    ]


def _assert_shown_again_safely(response, data, kept, *, real):
    assert response.status_code == 200
    form = response.context["form"]
    for name in kept:
        assert form[name].value() == data[name]
    assert (form.client_secret_was_typed, form.webhook_secret_was_typed) == (True, True)
    html = response.content.decode()
    assert TYPED_CLIENT_SECRET not in html and TYPED_WEBHOOK_SECRET not in html
    for name in ("client_secret", "webhook_secret"):
        tag = re.search(rf'<input[^>]*name="{name}"[^>]*>', html).group(0)
        assert "value=" not in tag
    if real:
        assert SUMMARY_LEAD in html
        assert "For your safety, the client secret you typed wasn't kept. Type it again." in html
        assert "For your safety, the webhook secret you typed wasn't kept. Type it again." in html
    return form


@pytest.mark.parametrize("real", [False, True])
def test_a_client_id_added_at_the_same_moment_gets_the_taken_error(
    it_client, settings, monkeypatch, caplog, real
):
    if real:
        _real_templates(settings)
    winner = zm.connection("zoom-01")
    winner_before = _stored(winner)
    stored_ciphertexts = ciphertexts()
    calls = _form_check_misses(monkeypatch)
    _capture_everything(caplog)
    data = add_data(
        slug="zoom-02",
        client_id=winner.client_id,
        client_secret=TYPED_CLIENT_SECRET,
        webhook_secret=TYPED_WEBHOOK_SECRET,
    )

    response = it_client.post(ADD_URL, data)

    form = _assert_shown_again_safely(
        response, data, ("slug", "account_id", "client_id"), real=real
    )
    assert len(calls) == 2  # the form's check missed; the re-check after the error found it
    assert form.errors == {"client_id": [_client_id_taken("zoom-01")]}
    assert list(ZoomConnection.objects.values_list("slug", flat=True)) == ["zoom-01"]
    assert _stored(winner) == winner_before
    _assert_nothing_leaked(
        caplog,
        (zm.CLIENT_SECRET, TYPED_CLIENT_SECRET, TYPED_WEBHOOK_SECRET, *stored_ciphertexts),
        (winner.client_id, zm.ACCOUNT_ID),
        real=real,
    )


@pytest.mark.parametrize("real", [False, True])
def test_a_client_id_changed_at_the_same_moment_gets_the_taken_error(
    it_client, settings, monkeypatch, caplog, real
):
    if real:
        _real_templates(settings)
    winner = zm.connection("zoom-01")
    edited = zm.connection("zoom-02")
    winner_before, edited_before = _stored(winner), _stored(edited)
    stored_ciphertexts = ciphertexts()
    calls = _form_check_misses(monkeypatch)
    _capture_everything(caplog)
    data = edit_data(
        edited,
        account_id="test-account-id-new",
        client_id=winner.client_id,
        client_secret=TYPED_CLIENT_SECRET,
        webhook_secret=TYPED_WEBHOOK_SECRET,
    )

    response = it_client.post(edit_url(edited), data)

    form = _assert_shown_again_safely(response, data, ("account_id", "client_id"), real=real)
    assert len(calls) == 2
    assert form.errors == {"client_id": [_client_id_taken("zoom-01")]}
    # The page describes the stored row, not the failed save's in-memory changes.
    context = response.context
    assert context["connection"].client_id == edited.client_id
    assert context["connection"].credentials_version == 1
    assert context["credentials_state"] == "saved" and context["saved_slug"] == "zoom-02"
    assert ZoomConnection.objects.count() == 2
    assert (_stored(winner), _stored(edited)) == (winner_before, edited_before)
    _assert_nothing_leaked(
        caplog,
        (zm.CLIENT_SECRET, TYPED_CLIENT_SECRET, TYPED_WEBHOOK_SECRET, *stored_ciphertexts),
        (winner.client_id, edited.client_id, zm.ACCOUNT_ID, "test-account-id-new"),
        real=real,
    )


@pytest.mark.parametrize("real", [False, True])
def test_a_name_added_at_the_same_moment_gets_the_taken_error(
    it_client, settings, monkeypatch, caplog, real
):
    if real:
        _real_templates(settings)
    winner = zm.connection("zoom-01")
    winner_before = _stored(winner)
    stored_ciphertexts = ciphertexts()
    # The other person's row commits just after this form's own name check.
    monkeypatch.setattr(ZoomConnectionForm, "validate_unique", lambda self: None)
    _capture_everything(caplog)
    data = add_data(
        slug="zoom-01",
        client_id="test-client-id-free",
        client_secret=TYPED_CLIENT_SECRET,
        webhook_secret=TYPED_WEBHOOK_SECRET,
    )

    response = it_client.post(ADD_URL, data)

    form = _assert_shown_again_safely(
        response, data, ("slug", "account_id", "client_id"), real=real
    )
    assert form.errors == {"slug": [NAME_TAKEN]}
    assert ZoomConnection.objects.count() == 1
    assert _stored(winner) == winner_before
    _assert_nothing_leaked(
        caplog,
        (zm.CLIENT_SECRET, TYPED_CLIENT_SECRET, TYPED_WEBHOOK_SECRET, *stored_ciphertexts),
        ("test-client-id-free", zm.ACCOUNT_ID),
        real=real,
    )


def test_a_name_and_a_client_id_both_lost_show_both_errors(it_client, monkeypatch):
    winner = zm.connection("zoom-01")
    _form_check_misses(monkeypatch)
    monkeypatch.setattr(ZoomConnectionForm, "validate_unique", lambda self: None)
    data = add_data(
        slug="zoom-01",
        client_id=winner.client_id,
        client_secret=TYPED_CLIENT_SECRET,
        webhook_secret=TYPED_WEBHOOK_SECRET,
    )
    response = it_client.post(ADD_URL, data)
    assert response.status_code == 200
    assert response.context["form"].errors == {
        "slug": [NAME_TAKEN],
        "client_id": [_client_id_taken("zoom-01")],
    }
    assert ZoomConnection.objects.count() == 1


def test_any_other_integrity_error_is_not_swallowed(it_client, monkeypatch):
    def fails(self, commit=True):
        raise IntegrityError("some other constraint")

    monkeypatch.setattr(ZoomConnectionForm, "save", fails)
    with pytest.raises(IntegrityError):
        it_client.post(ADD_URL, add_data(slug="zoom-02", client_id="test-client-id-free"))
    assert ZoomConnection.objects.count() == 0
