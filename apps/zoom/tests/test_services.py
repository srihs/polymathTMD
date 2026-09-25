"""Services, crypto, checks and the rotation command (brief 005, criteria 10-11, 13, 35-41,
46, 48, 50, 59-61, 63-65)."""

import logging
from datetime import date, time
from io import StringIO
from unittest import mock

import pytest
from cryptography.fernet import Fernet
from django.core import checks, mail
from django.core.management import call_command
from django.db import IntegrityError, OperationalError
from django.test import RequestFactory, override_settings

from apps.zoom import crypto, services
from apps.zoom.checks import (
    check_fake_provider_not_deployed,
    check_host_key_encryption_keys,
    check_provider_setting,
)
from apps.zoom.models import HostAccount, HostKeyUnreadable, HostSlot, LinkRequest
from apps.zoom.providers import FakeProvider, ManualProvider, get_provider
from apps.zoom.services import Outcome

from .conftest import book, make_account, make_request

pytestmark = pytest.mark.django_db
HOST_KEY = "8421973"

# --------------------------------------------------------------------------- client IP (11)


@pytest.mark.parametrize(
    ("proxies", "forwarded", "expected"),
    [
        (0, "203.0.113.9", "10.0.0.1"),
        (0, "", "10.0.0.1"),
        (1, "198.51.100.7, 203.0.113.9", "203.0.113.9"),
        (2, "198.51.100.7, 203.0.113.9", "198.51.100.7"),
        (2, "203.0.113.9", "10.0.0.1"),
        (1, "not-an-ip", "10.0.0.1"),
    ],
)
def test_client_ip_trusts_forwarded_for_only_as_far_as_the_proxy_count(
    settings, proxies, forwarded, expected
):
    settings.TRUSTED_PROXY_COUNT = proxies
    request = RequestFactory().get("/", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR=forwarded)
    assert services.client_ip(request) == expected


def test_throttle_counts_email_and_ip_separately():
    for _ in range(4):
        make_request(email="a@example.com", submitted_ip="10.0.0.2")
    assert not services.is_throttled(email="A@example.com", ip="10.0.0.9")
    make_request(email="a@example.com", submitted_ip="10.0.0.2")
    assert services.is_throttled(email="a@example.com", ip="10.0.0.9")
    for number in range(15):
        make_request(email=f"x{number}@example.com", submitted_ip="10.0.0.2")
    assert services.is_throttled(email="new@example.com", ip="10.0.0.2")
    assert not services.is_throttled(email="new@example.com", ip="10.0.0.3")


# --------------------------------------------------------------------------- approve (35-40, 64)


def test_approve_books_every_class_and_slot_and_stores_the_fake_meeting(account, it_user):
    link_request = make_request(weekdays="1,3", last_date=date(2026, 10, 28), wants_recording=True)
    result = services.approve(link_request.pk, account_id=account.pk, by=it_user)

    assert result.outcome == Outcome.APPROVED
    assert result.host_key == HOST_KEY
    assert HOST_KEY not in repr(result)
    link_request.refresh_from_db()
    assert link_request.status == LinkRequest.Status.APPROVED
    assert link_request.host_account == account
    assert link_request.decided_by == it_user
    assert link_request.decided_at is not None
    assert link_request.join_url.startswith("https://zoom.example.invalid/j/")
    assert link_request.meeting_id and link_request.passcode
    assert set(link_request.occurrences.values_list("host_account", flat=True)) == {account.pk}
    assert HostSlot.objects.filter(host_account=account).count() == 8 * 36
    assert FakeProvider.calls == [
        {
            "link_request_id": link_request.pk,
            "host_account_id": account.pk,
            "occurrence_count": 8,
            "wants_recording": True,
        }
    ]


def test_approve_with_manual_provider_stores_what_was_typed(account, it_user):
    link_request = make_request()
    manual = {
        "join_url": "https://us02web.zoom.us/j/12345678901",
        "meeting_id": "12345678901",
        "passcode": "abc",
    }
    result = services.approve(
        link_request.pk, account_id=account.pk, by=it_user, manual=manual, provider=ManualProvider()
    )
    assert result.outcome == Outcome.APPROVED
    link_request.refresh_from_db()
    assert (link_request.join_url, link_request.meeting_id, link_request.passcode) == (
        manual["join_url"],
        "12345678901",
        "abc",
    )


def test_approve_refuses_an_overlapping_booking_on_the_same_account(account, it_user):
    book(make_request(start=time(9, 0), end=time(10, 0), class_name="Grade 10"), account)
    link_request = make_request()
    result = services.approve(link_request.pk, account_id=account.pk, by=it_user)
    assert result.outcome == Outcome.CONFLICT
    assert result.message == (
        "Zoom 01 was booked for an overlapping class a moment ago. Choose another free account."
    )
    link_request.refresh_from_db()
    assert link_request.status == LinkRequest.Status.WAITING
    assert not link_request.occurrences.filter(host_account__isnull=False).exists()
    assert len(FakeProvider.calls) == 1  # only the first booking's


@pytest.mark.parametrize("flags", [{"is_paid": False}, {"is_active": False}])
def test_approve_refuses_unbookable_accounts(it_user, flags):
    unbookable = make_account("Zoom 09", **flags)
    result = services.approve(make_request().pk, account_id=unbookable.pk, by=it_user)
    assert (result.outcome, result.message) == (
        Outcome.CONFLICT,
        "Choose one of the free accounts listed.",
    )


def test_approve_refuses_decided_and_started_requests(account, it_user):
    decided = book(make_request(), account)
    result = services.approve(decided.pk, account_id=account.pk, by=it_user)
    assert result.outcome == Outcome.ALREADY_DECIDED
    started = make_request(first_date=date(2026, 9, 28), start=time(9, 0), end=time(11, 0))
    result = services.approve(started.pk, account_id=account.pk, by=it_user)
    assert result.outcome == Outcome.STARTED
    assert FakeProvider.calls[1:] == []


def test_provider_failure_books_nothing(account, it_user):
    FakeProvider.next_error = "Zoom is not responding"
    link_request = make_request()
    result = services.approve(link_request.pk, account_id=account.pk, by=it_user)
    assert result.outcome == Outcome.PROVIDER_ERROR
    assert result.message == (
        "Zoom didn't create the meeting: Zoom is not responding. Nothing was booked. "
        "Try again in a few minutes."
    )
    link_request.refresh_from_db()
    assert link_request.status == LinkRequest.Status.WAITING
    assert HostSlot.objects.count() == 0
    assert not link_request.occurrences.filter(host_account__isnull=False).exists()


def test_unreadable_host_key_books_nothing_and_logs_only_label(account, it_user, settings, caplog):
    settings.HOST_KEY_ENCRYPTION_KEYS = [Fernet.generate_key().decode()]
    link_request = make_request()
    with caplog.at_level(logging.DEBUG):
        result = services.approve(link_request.pk, account_id=account.pk, by=it_user)
    assert result.outcome == Outcome.HOST_KEY_UNREADABLE
    assert result.message == (
        "The host key saved for Zoom 01 can't be read. Ask someone in the IT desk to type it "
        "again on the Zoom accounts page, then approve."
    )
    assert FakeProvider.calls == []
    assert HostSlot.objects.count() == 0
    [record] = [r for r in caplog.records if r.name == "apps.zoom.services"]
    assert record.getMessage() == "Host key for Zoom 01 can't be read: InvalidToken"


SAME_MOMENT = "Someone else was approving at the same moment. Nothing was booked. Try again."


def test_the_slot_backstop_is_the_booked_a_moment_ago_conflict(account, it_user):
    link_request = make_request()
    error = IntegrityError(1062, "Duplicate entry")
    with mock.patch.object(HostSlot.objects, "bulk_create", side_effect=error):
        result = services.approve(link_request.pk, account_id=account.pk, by=it_user)
    assert result.outcome == Outcome.CONFLICT
    assert result.message == (
        "Zoom 01 was booked for an overlapping class a moment ago. Choose another free account."
    )


def test_a_deadlock_is_retried_once_and_can_then_succeed(account, it_user):
    link_request = make_request()
    real_bulk_create = HostSlot.objects.bulk_create
    calls = []

    def deadlock_first_time(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise OperationalError(1213, "Deadlock found when trying to get lock")
        return real_bulk_create(*args, **kwargs)

    with mock.patch.object(HostSlot.objects, "bulk_create", side_effect=deadlock_first_time):
        result = services.approve(link_request.pk, account_id=account.pk, by=it_user)
    assert len(calls) == 2
    assert result.outcome == Outcome.APPROVED
    assert HostSlot.objects.count() == 36
    assert len(FakeProvider.calls) == 1


def test_a_second_deadlock_gives_the_same_moment_message(account, it_user):
    link_request = make_request()
    error = OperationalError(1213, "Deadlock found when trying to get lock")
    with mock.patch.object(HostSlot.objects, "bulk_create", side_effect=error) as bulk_create:
        result = services.approve(link_request.pk, account_id=account.pk, by=it_user)
    assert bulk_create.call_count == 2
    assert (result.outcome, result.message) == (Outcome.CONFLICT, SAME_MOMENT)
    link_request.refresh_from_db()
    assert link_request.status == LinkRequest.Status.WAITING
    assert FakeProvider.calls == []


def test_a_lock_wait_timeout_is_not_retried(account, it_user):
    error = OperationalError(1205, "Lock wait timeout exceeded")
    with mock.patch.object(HostSlot.objects, "bulk_create", side_effect=error) as bulk_create:
        result = services.approve(make_request().pk, account_id=account.pk, by=it_user)
    assert bulk_create.call_count == 1
    assert (result.outcome, result.message) == (Outcome.CONFLICT, SAME_MOMENT)


def test_other_database_errors_are_not_hidden(account, it_user):
    with (
        mock.patch.object(
            HostSlot.objects, "bulk_create", side_effect=OperationalError(2006, "gone")
        ),
        pytest.raises(OperationalError),
    ):
        services.approve(make_request().pk, account_id=account.pk, by=it_user)


# ------------------------------------------------------------------ emails (35, 41, 50, 61)


def _request():
    return RequestFactory().get("/", HTTP_HOST="testserver")


def _only_message():
    [message] = mail.outbox
    assert message.cc == [] and message.bcc == []
    assert getattr(message, "alternatives", []) == []
    return message


@override_settings(DEFAULT_FROM_EMAIL="it-desk@polymath.example")
def test_approval_email_carries_link_host_key_classes_and_recording(account, it_user):
    link_request = book(
        make_request(
            class_name="<b>Maths & Science</b>",
            weekdays="1,3",
            last_date=date(2026, 10, 28),
            wants_recording=True,
        ),
        account,
        it_user,
    )
    assert services.send_approved_email(_request(), link_request, HOST_KEY)
    message = _only_message()
    assert message.to == ["nimali@example.com"]
    assert message.from_email == "it-desk@polymath.example"
    assert message.subject == "Your Zoom link for <b>Maths & Science</b>"
    body = message.body
    for expected in (
        link_request.join_url,
        link_request.meeting_id,
        link_request.passcode,
        f"Host key: {HOST_KEY}",
        'To start the class as host, join, choose "Claim host" and type this host key. Keep it '
        "private: anyone who has it can take control of meetings on this Zoom account.",
        "You asked for this class to be recorded to the Zoom cloud.",
        link_request.reference,
        "Mon 5 Oct 2026, 8:30 am to 11:30 am",
        "Wed 28 Oct 2026, 8:30 am to 11:30 am",
        f"When: {link_request.schedule_summary}",
    ):
        assert expected in body
    assert "&amp;" not in body


def test_approval_email_without_a_host_key_says_ask_the_it_desk(it_user):
    link_request = book(make_request(), make_account("Zoom 05"), it_user)
    services.send_approved_email(_request(), link_request, "")
    body = _only_message().body
    assert "Ask the IT desk for the host key to start the class as host." in body
    assert "Host key:" not in body
    assert "recorded to the Zoom cloud" not in body


def test_other_emails_never_carry_the_host_key(account, it_user, superuser, plain_user):
    link_request = make_request(status=LinkRequest.Status.UNVERIFIED)
    services.send_confirm_email(_request(), link_request)
    link_request.mark_verified()
    services.send_it_new_request_email(_request(), link_request)
    link_request.reject(it_user, "Please use the Grade 10 batch link instead.")
    services.send_rejected_email(_request(), link_request)
    assert len(mail.outbox) == 4  # confirm, IT x2 (IT user + superuser), rejected
    for message in mail.outbox:
        assert HOST_KEY not in message.body and HOST_KEY not in message.subject
        assert getattr(message, "alternatives", []) == []


def test_it_email_goes_to_each_active_reviewer_only(it_user, superuser, plain_user):
    link_request = make_request()
    inactive = type(it_user).objects.create_user(
        username="old", email="old@polymath.example", is_active=False
    )
    inactive.groups.set(it_user.groups.all())
    services.send_it_new_request_email(_request(), link_request)
    assert sorted(m.to[0] for m in mail.outbox) == [
        "admin@polymath.example",
        "kasun@polymath.example",
    ]
    message = mail.outbox[0]
    assert (
        message.subject
        == f"New Zoom link request {link_request.reference}: CCC Batch 3 - Mathematics"
    )
    assert f"http://testserver/zoom/requests/{link_request.pk}/" in message.body
    assert "Recording: no" in message.body


def test_rejected_email_has_reason_and_request_link(it_user):
    link_request = make_request()
    link_request.reject(it_user, "Please use the Grade 10 batch link instead.")
    services.send_rejected_email(_request(), link_request)
    message = _only_message()
    assert message.subject == f"Your Zoom link request {link_request.reference} was not approved"
    assert "Please use the Grade 10 batch link instead." in message.body
    assert "http://testserver/zoom/request/" in message.body


def test_send_failure_is_logged_without_secrets(account, it_user, caplog):
    link_request = book(make_request(), account, it_user)
    with (
        mock.patch(
            "django.core.mail.backends.locmem.EmailBackend.send_messages",
            side_effect=ConnectionRefusedError("smtp down"),
        ),
        caplog.at_level(logging.DEBUG),
    ):
        assert not services.send_approved_email(_request(), link_request, HOST_KEY)
    [record] = [r for r in caplog.records if r.levelno == logging.ERROR]
    text = record.getMessage()
    assert link_request.reference in text and "ConnectionRefusedError" in text
    for secret in (HOST_KEY, link_request.join_url, link_request.passcode):
        assert secret not in text


# --------------------------------------------------------------------------- tokens (13)


def test_confirm_token_carries_only_the_pk_and_uses_its_own_salt():
    link_request = make_request(status=LinkRequest.Status.UNVERIFIED)
    token = services.confirm_token(link_request)
    from django.core import signing

    assert signing.loads(token, salt=services.CONFIRM_SALT) == link_request.pk
    with pytest.raises(signing.BadSignature):
        signing.loads(token)
    assert services.confirm_state(token) == ("ready", link_request)
    assert services.confirm_state(token + "x")[0] == "invalid"


# --------------------------------------------------------------------------- providers, checks


def test_get_provider_follows_the_setting(settings):
    assert isinstance(get_provider(), FakeProvider)
    settings.ZOOM_PROVIDER = "manual"
    assert get_provider().needs_manual_details


@pytest.mark.parametrize(("value", "ids"), [("fake", []), ("manual", []), ("zoom", ["zoom.E002"])])
def test_check_e002_rejects_unknown_providers(settings, value, ids):
    settings.ZOOM_PROVIDER = value
    assert [e.id for e in check_provider_setting()] == ids


def test_check_e001_keeps_the_fake_provider_out_of_deploys(settings):
    settings.ZOOM_PROVIDER = "fake"
    [error] = check_fake_provider_not_deployed()
    assert error.id == "zoom.E001"
    assert error.msg == (
        "The fake Zoom provider makes links that don't work. "
        "Set ZOOM_PROVIDER=manual in production."
    )
    deploy_ids = {e.id for e in checks.run_checks(include_deployment_checks=True)}
    assert "zoom.E001" in deploy_ids
    assert "zoom.E001" not in {e.id for e in checks.run_checks()}
    settings.ZOOM_PROVIDER = "manual"
    assert check_fake_provider_not_deployed() == []


@pytest.mark.parametrize("keys", [[], [""], ["not-a-key"], [Fernet.generate_key().decode(), "bad"]])
def test_check_e003_reports_missing_or_invalid_keys_without_echoing_them(settings, keys):
    settings.HOST_KEY_ENCRYPTION_KEYS = keys
    [error] = check_host_key_encryption_keys()
    assert error.id == "zoom.E003"
    assert error.msg == "HOST_KEY_ENCRYPTION_KEYS is missing or not a list of valid Fernet keys."
    assert all(key not in str(error) for key in keys if key)


def test_check_e003_passes_with_the_test_key():
    assert check_host_key_encryption_keys() == []


# --------------------------------------------------------------------------- rotation (63)


def test_rotation_reencrypts_with_the_new_key_so_the_old_one_can_go(settings):
    old_key = settings.HOST_KEY_ENCRYPTION_KEYS[0]
    make_account("Zoom 01", host_key=HOST_KEY)
    make_account("Zoom 02", host_key="1234567")
    make_account("Zoom 03")
    new_key = Fernet.generate_key().decode()

    settings.HOST_KEY_ENCRYPTION_KEYS = [new_key, old_key]
    out = StringIO()
    call_command("rotate_host_keys", stdout=out)
    assert out.getvalue().strip() == "Re-encrypted 2 host keys."

    settings.HOST_KEY_ENCRYPTION_KEYS = [new_key]
    assert HostAccount.objects.get(label="Zoom 01").get_host_key() == HOST_KEY
    assert HostAccount.objects.get(label="Zoom 02").get_host_key() == "1234567"


def test_rotation_changes_neither_who_nor_when_a_key_was_set(settings, it_user):
    """Brief 008, criterion 21: re-encrypting isn't a person changing the key."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    account = make_account("Zoom 01", host_key=HOST_KEY)
    earlier = datetime(2026, 9, 1, 9, 0, tzinfo=ZoneInfo("Asia/Colombo"))
    HostAccount.objects.filter(pk=account.pk).update(
        host_key_changed_at=earlier, host_key_changed_by=it_user
    )
    account.refresh_from_db()
    account.rotate_host_key()
    assert (account.host_key_changed_at, account.host_key_changed_by) == (earlier, it_user)

    settings.HOST_KEY_ENCRYPTION_KEYS = [
        Fernet.generate_key().decode(),
        *settings.HOST_KEY_ENCRYPTION_KEYS,
    ]
    call_command("rotate_host_keys", stdout=StringIO())
    account.refresh_from_db()
    assert (account.host_key_changed_at, account.host_key_changed_by) == (earlier, it_user)
    assert account.get_host_key() == HOST_KEY


def test_removing_a_key_before_rotating_makes_keys_unreadable(settings):
    account = make_account(host_key=HOST_KEY)
    settings.HOST_KEY_ENCRYPTION_KEYS = [Fernet.generate_key().decode()]
    with pytest.raises(HostKeyUnreadable):
        account.get_host_key()
    err = StringIO()
    call_command("rotate_host_keys", stdout=StringIO(), stderr=err)
    assert "Zoom 01" in err.getvalue() and HOST_KEY not in err.getvalue()


def test_crypto_refuses_to_work_without_keys(settings):
    from django.core.exceptions import ImproperlyConfigured

    settings.HOST_KEY_ENCRYPTION_KEYS = []
    with pytest.raises(ImproperlyConfigured):
        crypto.encrypt(HOST_KEY)
