"""Brief 013, the signed-in pages: ``Check against Zoom`` (criterion 18), the detail and queue
context (15, 27), and the Zoom account page's sync state (29).

The fake provider is steered with ``FakeProvider.meeting_states``, so no HTTP is involved here;
the live provider's path is in ``test_reconcile.py``. Page templates are the conftest stubs
except where a test renders the real ones to search the output (``by None``, the secret).
"""

import logging
from datetime import date, timedelta
from unittest import mock

import pytest
from django.contrib.messages import constants as levels
from django.contrib.messages import get_messages
from django.db import OperationalError, connection
from django.test.utils import CaptureQueriesContext
from django.urls import resolve, reverse

from apps.zoom import services
from apps.zoom.models import LinkRequest, ZoomEvent
from apps.zoom.providers import (
    FakeProvider,
    ZoomAuthFailed,
    ZoomBusy,
    ZoomDailyLimit,
    read_meeting_state,
)

from . import synckit as kit
from . import zoommock as zm
from .conftest import FROZEN_NOW, make_account, make_request
from .test_sidebar_zoom_group import _real_templates

pytestmark = pytest.mark.django_db
at = kit.at
EMAIL = "nimal@example.com"


def _messages(response):
    return [(m.level, str(m)) for m in get_messages(response.wsgi_request)]


def sync_url(link_request):
    return reverse("zoom:sync", args=[link_request.pk])


@pytest.fixture
def zoom02(settings, db):
    account = make_account("Zoom 02", sort_order=2)
    kit.connect(account)
    return account


def _zoom_has(booking, **changes):
    """Steer the fake: Zoom holds ``booking``'s meeting as stored, with ``changes``."""
    FakeProvider.meeting_states[booking.meeting_id] = read_meeting_state(
        kit.booking_series(booking, **changes)
    )


def _press(client, booking):
    response = client.post(sync_url(booking))
    assert response.status_code == 302
    assert response.url == reverse("zoom:detail", args=[booking.pk])
    return _messages(response)


# --------------------------------------------------------------------------- access


def test_check_is_post_only_signed_in_with_the_review_permission(client, plain_user, zoom02):
    booking = kit.zl42(zoom02)
    response = client.post(sync_url(booking))
    assert response.status_code == 302 and response.url.startswith(reverse("accounts:login"))
    client.force_login(plain_user)
    assert client.post(sync_url(booking)).status_code == 403
    assert FakeProvider.state_calls == []


def test_get_is_405(it_client, zoom02):
    assert it_client.get(sync_url(kit.zl42(zoom02))).status_code == 405


def test_the_check_runs_outside_the_request_transaction():
    view = resolve(reverse("zoom:sync", args=[1])).func
    assert "default" in getattr(view, "_non_atomic_requests", set())


def test_a_request_that_was_never_approved_is_404(it_client, zoom02):
    waiting = make_request(first_date=date(2026, 11, 2))
    rejected = make_request(first_date=date(2026, 11, 9))
    rejected.reject(None, "No.")
    unverified = make_request(status=LinkRequest.Status.UNVERIFIED, first_date=date(2026, 11, 16))
    for link_request in (waiting, rejected, unverified):
        assert it_client.post(sync_url(link_request)).status_code == 404
    assert it_client.post(reverse("zoom:sync", args=[999999])).status_code == 404


# --------------------------------------------------------------------------- 18 the messages


def test_matches(it_client, zoom02):
    booking = kit.zl42(zoom02)
    _zoom_has(booking)
    assert _press(it_client, booking) == [
        (levels.SUCCESS, "Checked with Zoom: this booking matches Zoom.")
    ]


@pytest.mark.parametrize(
    ("deleted", "text"),
    [
        ([7], "Checked with Zoom: 1 change copied here. We emailed nimal@example.com."),
        ([7, 12, 14], "Checked with Zoom: 3 changes copied here. We emailed nimal@example.com."),
    ],
)
def test_copied_and_emailed(it_client, zoom02, deleted, text):
    booking = kit.zl42(zoom02)
    _zoom_has(booking, deleted=[at(day, 8, 30) for day in deleted])
    assert _press(it_client, booking) == [(levels.SUCCESS, text)]


def test_copied_but_the_email_failed(it_client, zoom02):
    booking = kit.zl42(zoom02)
    _zoom_has(booking, moved={at(12, 8, 30): (at(13, 9), 180)})
    with mock.patch.object(services, "send_moved_email", return_value=False):
        found = _press(it_client, booking)
    assert found == [
        (
            levels.WARNING,
            f"Checked with Zoom: 1 change copied here, but the email to {EMAIL} didn't send. "
            "Tell them yourself.",
        )
    ]


def test_copied_emailed_and_needs_a_look(it_client, zoom02):
    booking = kit.zl42(zoom02)
    _zoom_has(booking, deleted=[at(7, 8, 30)], extra=[(at(8, 9), 180)])
    assert _press(it_client, booking) == [
        (
            levels.WARNING,
            f"Checked with Zoom: 1 change copied here, and some changes need a look. We emailed "
            f"{EMAIL}.",
        )
    ]


def test_copied_email_failed_and_needs_a_look(it_client, zoom02):
    booking = kit.zl42(zoom02)
    _zoom_has(booking, deleted=[at(7, 8, 30), at(12, 8, 30)], extra=[(at(8, 9), 180)])
    with mock.patch.object(services, "send_cancelled_email", return_value=False):
        found = _press(it_client, booking)
    assert found == [
        (
            levels.WARNING,
            "Checked with Zoom: 2 changes copied here, and some changes need a look. The email "
            f"to {EMAIL} didn't send, so tell them about the copied changes yourself.",
        )
    ]


def test_needs_a_look_only(it_client, zoom02):
    booking = kit.zl42(zoom02)
    _zoom_has(booking, extra=[(at(8, 9), 180)])
    assert _press(it_client, booking) == [
        (levels.WARNING, "Checked with Zoom: some changes need a look.")
    ]


@pytest.mark.parametrize(
    ("error", "text"),
    [
        (
            ZoomBusy(),
            "We couldn't check with Zoom: Zoom is busy right now. Try again in a few minutes.",
        ),
        (
            ZoomAuthFailed(),
            "We couldn't check with Zoom: Zoom didn't accept this account's connection details. "
            "Ask whoever manages the Zoom accounts to press Check connection for Zoom 02, then "
            "try again.",
        ),
        (
            ZoomDailyLimit(),
            "We couldn't check with Zoom: Zoom's daily limit for this account is used up. Try "
            "again after 5:30 am on Tue 29 Sep 2026.",
        ),
    ],
)
def test_zoom_couldn_t_be_asked(it_client, zoom02, error, text):
    booking = kit.zl42(zoom02)
    FakeProvider.meeting_states[booking.meeting_id] = error
    assert _press(it_client, booking) == [(levels.ERROR, text)]
    assert not booking.occurrences.filter(cancelled_at__isnull=False).exists()


def test_a_lock_race_forced_twice_says_someone_else_was_changing_it(it_client, zoom02):
    booking = kit.zl42(zoom02)
    _zoom_has(booking)
    deadlock = [OperationalError(1213, "Deadlock"), OperationalError(1213, "Deadlock")]
    with mock.patch.object(services, "_reconcile_once", side_effect=deadlock) as attempt:
        found = _press(it_client, booking)
    assert attempt.call_count == 2
    assert found == [
        (
            levels.ERROR,
            "Someone else was changing this booking at the same moment. Nothing was changed. "
            "Try again.",
        )
    ]


def test_nothing_to_check_with_a_provider_that_can_t_reach_zoom(it_client, settings, zoom02):
    settings.ZOOM_PROVIDER = "manual"
    booking = kit.zl42(zoom02)
    assert _press(it_client, booking) == [
        (levels.ERROR, "This system can't reach Zoom, so it can't check this booking.")
    ]
    cancelled = kit.zl43(zoom02, first_date=date(2026, 10, 6))
    it_client.cookies.pop("messages", None)
    LinkRequest.objects.filter(pk=cancelled.pk).update(
        status=LinkRequest.Status.CANCELLED, cancelled_at=FROZEN_NOW
    )
    assert _press(it_client, cancelled) == [  # the provider is tested first
        (levels.ERROR, "This system can't reach Zoom, so it can't check this booking.")
    ]


def test_nothing_to_check_when_no_class_is_left(it_client, it_user, zoom02, monkeypatch):
    booking = kit.zl43(zoom02)
    monkeypatch.setattr("django.utils.timezone.now", lambda: at(5, 9))  # in progress
    it_client.force_login(it_user)  # a week on, the first session has expired
    text = "There are no classes left to check in this booking."
    assert _press(it_client, booking) == [(levels.ERROR, text)]
    LinkRequest.objects.filter(pk=booking.pk).update(
        status=LinkRequest.Status.CANCELLED, cancelled_at=FROZEN_NOW
    )
    it_client.cookies.pop("messages", None)
    assert _press(it_client, booking) == [(levels.ERROR, text)]
    assert FakeProvider.state_calls == []


def test_a_class_that_begins_after_the_view_s_check_never_reads_matches_zoom(
    it_client, zoom02, monkeypatch
):
    """Criterion 18, review round 1, N2: ``not_asked`` is never "this booking matches Zoom"."""
    booking = kit.zl43(zoom02)  # one class, Mon 5 Oct, 8:30 am
    _zoom_has(booking)
    real_check = services.sync_blocked_message

    def check_then_the_class_begins(*args, **kwargs):
        found = real_check(*args, **kwargs)
        monkeypatch.setattr("django.utils.timezone.now", lambda: at(5, 8, 31))
        return found

    monkeypatch.setattr(services, "sync_blocked_message", check_then_the_class_begins)
    assert _press(it_client, booking) == [
        (levels.ERROR, "There are no classes left to check in this booking.")
    ]
    assert FakeProvider.state_calls == []


def test_two_changes_in_a_row_say_someone_else_was_changing_it(it_client, zoom02):
    """Criterion 30: the button's mapping of a second fingerprint mismatch."""
    booking = kit.zl42(zoom02)
    _zoom_has(booking)
    changed = services.BookingChangedMeanwhile()
    with mock.patch.object(services, "_reconcile_once", side_effect=changed) as attempt:
        found = _press(it_client, booking)
    assert attempt.call_count == 2 and len(FakeProvider.state_calls) == 2
    assert found == [
        (
            levels.ERROR,
            "Someone else was changing this booking at the same moment. Nothing was changed. "
            "Try again.",
        )
    ]


# --------------------------------------------------------------------------- 15, 18 detail


def _detail(client, booking):
    response = client.get(reverse("zoom:detail", args=[booking.pk]))
    assert response.status_code == 200
    return response.context


def test_the_detail_offers_the_check_only_when_there_is_something_to_check(
    it_client, it_user, settings, zoom02, monkeypatch
):
    booking = kit.zl42(zoom02)
    context = _detail(it_client, booking)
    assert context["can_sync"] is True and context["zoom_attention_lines"] == []
    settings.ZOOM_PROVIDER = "manual"
    assert _detail(it_client, booking)["can_sync"] is False
    settings.ZOOM_PROVIDER = "fake"
    waiting = make_request(first_date=date(2026, 11, 2))
    assert _detail(it_client, waiting)["can_sync"] is False
    monkeypatch.setattr("django.utils.timezone.now", lambda: at(29, 9))
    it_client.force_login(it_user)  # a month on, the first session has expired
    assert _detail(it_client, booking)["can_sync"] is False


def test_the_detail_carries_the_attention_lines(it_client, zoom02):
    booking = kit.zl42(zoom02)
    LinkRequest.objects.filter(pk=booking.pk).update(zoom_attention="First.\nSecond.")
    assert _detail(it_client, booking)["zoom_attention_lines"] == ["First.", "Second."]


def test_the_queue_rows_carry_the_flag_with_no_extra_query(it_client, zoom02):
    booking = kit.zl42(zoom02)
    url = reverse("zoom:queue") + "?status=approved"
    with CaptureQueriesContext(connection) as before:
        it_client.get(url)
    LinkRequest.objects.filter(pk=booking.pk).update(zoom_attention="First.")
    with CaptureQueriesContext(connection) as after:
        response = it_client.get(url)
    [row] = response.context["link_requests"]
    assert row.zoom_attention == "First."
    assert len(after) == len(before)


def test_no_detail_page_says_by_none_after_changes_copied_from_zoom(
    it_client, it_user, settings, zoom02
):
    _real_templates(settings)
    booking = kit.zl42(zoom02, by=it_user)  # approved by a person, as approve() records
    _zoom_has(booking, deleted=[at(7, 8, 30)], moved={at(12, 8, 30): (at(13, 9), 180)})
    it_client.post(sync_url(booking))
    html = it_client.get(reverse("zoom:detail", args=[booking.pk])).content.decode()
    assert "by None" not in html
    FakeProvider.meeting_states[booking.meeting_id] = None  # the whole meeting deleted
    it_client.post(sync_url(booking))
    booking.refresh_from_db()
    assert booking.status == LinkRequest.Status.CANCELLED and booking.cancelled_in_zoom
    html = it_client.get(reverse("zoom:detail", args=[booking.pk])).content.decode()
    assert "by None" not in html


# --------------------------------------------------------------------------- 29 account page


def _account_context(client, account):
    response = client.get(reverse("zoom:account_edit", args=[account.pk]))
    assert response.status_code == 200
    return response.context


def test_the_three_states_of_the_account_page(it_client, settings, zoom02, monkeypatch):
    context = _account_context(it_client, zoom02)
    assert (context["webhook_secret_set"], context["last_zoom_event_at"]) == (True, None)

    heard = FROZEN_NOW - timedelta(minutes=3)
    monkeypatch.setattr("django.utils.timezone.now", lambda: heard)
    ZoomEvent.objects.create(slug="zoom-02", event="x", body_sha256="1" * 64, outcome="ignored")
    monkeypatch.setattr("django.utils.timezone.now", lambda: FROZEN_NOW)
    context = _account_context(it_client, zoom02)
    assert (context["webhook_secret_set"], context["last_zoom_event_at"]) == (True, heard)

    kit.connect(zoom02, secret="")
    context = _account_context(it_client, zoom02)
    assert (context["webhook_secret_set"], context["last_zoom_event_at"]) == (False, None)


def test_none_where_there_is_nothing_to_say(it_client, settings, zoom02):
    add = it_client.get(reverse("zoom:account_add")).context
    assert (add["webhook_secret_set"], add["last_zoom_event_at"]) == (None, None)
    settings.ZOOM_PROVIDER = "manual"
    context = _account_context(it_client, zoom02)
    assert (context["webhook_secret_set"], context["last_zoom_event_at"]) == (None, None)
    settings.ZOOM_PROVIDER = "fake"
    # Brief 015: the stored connection can't be read with the server's keys.
    zm.make_unreadable(zoom02.zoom_connection)
    context = _account_context(it_client, zoom02)
    assert context["zoom_connection_state"] == "unreadable"
    assert context["webhook_secret_set"] is None
    unnamed = make_account("Zoom 07", sort_order=7)
    assert _account_context(it_client, unnamed)["webhook_secret_set"] is None


def test_two_accounts_on_one_connection_show_the_same_last_heard(it_client, settings, zoom02):
    zoom03 = make_account("Zoom 03", sort_order=3)
    kit.connect(zoom02, zoom03)
    ZoomEvent.objects.create(slug="zoom-02", event="x", body_sha256="1" * 64, outcome="ignored")
    first = _account_context(it_client, zoom02)["last_zoom_event_at"]
    assert first is not None
    assert _account_context(it_client, zoom03)["last_zoom_event_at"] == first


def test_the_account_page_costs_at_most_one_query_more(it_client, settings, zoom02):
    kit.connect(zoom02, secret="")
    with CaptureQueriesContext(connection) as without:
        _account_context(it_client, zoom02)
    kit.connect(zoom02)
    with CaptureQueriesContext(connection) as with_secret:
        _account_context(it_client, zoom02)
    assert len(with_secret) <= len(without) + 1


def test_no_page_shows_the_webhook_secret(it_client, settings, zoom02, caplog):
    _real_templates(settings)
    caplog.set_level(logging.DEBUG)
    booking = kit.zl42(zoom02)
    for url in (
        reverse("zoom:account_edit", args=[zoom02.pk]),
        reverse("zoom:accounts"),
        reverse("zoom:detail", args=[booking.pk]),
    ):
        response = it_client.get(url)
        assert response.status_code == 200
        assert kit.WEBHOOK_SECRET not in response.content.decode()
    assert kit.WEBHOOK_SECRET not in caplog.text
