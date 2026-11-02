"""Brief 013 on committed data: Zoom is asked with no transaction open (criterion 13), two
deliveries of one event at once (criterion 8), a webhook about a cancel that's still
committing (criterion 17's thread test), and an app change committing between the webhook's
``GET`` and its lock (criterion 30's three thread tests, review round 1, B1).

Like ``test_cancel_race.py``, these commit real rows through the ``committed`` fixture, so
every thread sees the others' commits; ``events`` also removes the ``ZoomEvent`` rows they
leave. Zoom is the live provider with its answers mocked (the project-wide mock covers every
thread); the webhook is called through Django's test ``Client``.
"""

import json
import threading
import time
from datetime import date

import pytest
import responses
from django.contrib.auth.models import Group
from django.core import mail
from django.db import connection
from django.test import Client, RequestFactory
from django.urls import reverse

from apps.zoom import services
from apps.zoom.models import LinkRequest, Occurrence, ZoomEvent

from . import synckit as kit
from . import zoommock as zm
from .conftest import booked_on
from .test_race import (  # noqa: F401  (committed is a fixture)
    _run_together,
    _tracked_account,
    _tracked_request,
    _tracked_user,
    committed,
)

at = kit.at


@pytest.mark.django_db
def test_committed_rows_go_to_the_test_database():
    assert connection.settings_dict["NAME"].startswith("test_")


@pytest.fixture
def events(committed):  # noqa: F811
    yield committed
    ZoomEvent.objects.filter(slug=kit.SLUG).delete()


def _setup(committed, settings, http_mock):  # noqa: F811
    user = _tracked_user(committed, username="race-it", password="pw", email="race@x.example")
    user.groups.add(Group.objects.get(name="IT desk"))
    account = _tracked_account(committed, "Race 02", host_key="8421973")
    kit.live(settings, http_mock, account)
    return user, account


def _weekly(committed, account):  # noqa: F811
    link_request = _tracked_request(
        committed,
        weekdays="1,3",
        first_date=date(2026, 10, 5),
        last_date=date(2026, 10, 28),
        class_name="Race Physics",
        email="nimal@example.com",
    )
    return booked_on(link_request, account, meeting_id=kit.MEETING)


# --------------------------------------------------------------------------- 13 no transaction


def test_zoom_is_asked_with_no_transaction_open_from_the_webhook_and_the_button(
    events, settings, http_mock
):
    user, account = _setup(events, settings, http_mock)
    booking = _weekly(events, account)
    seen = []

    def answer(request):
        seen.append(connection.in_atomic_block)
        return 200, {}, json.dumps(kit.booking_series(booking))

    kit.add_meeting(http_mock, callback=answer)
    assert kit.post(Client(), kit.meeting_event("meeting.updated")).status_code == 200
    client = Client()
    client.force_login(user)
    assert client.post(reverse("zoom:sync", args=[booking.pk])).status_code == 302
    services.reconcile(booking)
    assert seen == [False, False, False]


# --------------------------------------------------------------------------- 8 at the same time


def test_two_deliveries_at_once_reconcile_once_and_email_once(events, settings, http_mock):
    _, account = _setup(events, settings, http_mock)
    booking = _weekly(events, account)
    both_asked = threading.Barrier(2, timeout=10)

    def answer(request):
        both_asked.wait()  # both are past the "seen it already?" check before either writes
        return 200, {}, json.dumps(kit.booking_series(booking, deleted=[at(7, 8, 30)]))

    kit.add_meeting(http_mock, callback=answer)
    event = kit.meeting_event()

    def deliver():
        return kit.post(Client(), event).status_code

    assert _run_together(deliver, deliver) == [200, 200]
    rows = list(ZoomEvent.objects.filter(slug=kit.SLUG))
    assert [row.outcome for row in rows] == ["changed"]
    assert len([m for m in mail.outbox if m.to == ["nimal@example.com"]]) == 1
    assert booking.occurrences.filter(cancelled_at__isnull=False).count() == 1


# --------------------------------------------------------------------------- 17 the echo waits


def test_a_webhook_during_a_cancel_waits_then_finds_nothing_to_do(events, settings, http_mock):
    user, account = _setup(events, settings, http_mock)
    booking = _weekly(events, account)
    asked = threading.Event()
    outcome = {}

    def zoom_get(request):
        asked.set()
        return 404, {}, '{"code": 3001, "message": "Meeting does not exist"}'

    kit.add_meeting(http_mock, callback=zoom_get)
    kit.add_user(http_mock)  # criterion 31: the host user is there, so 3001 means gone

    def webhook():
        try:
            outcome["status"] = kit.post(Client(), kit.meeting_event()).status_code
        finally:
            connection.close()

    def zoom_delete(request):
        # Called by cancel() with the request row locked: the webhook now asks Zoom (no
        # lock), then waits on that row until cancel() commits.
        thread = threading.Thread(target=webhook)
        outcome["thread"] = thread
        thread.start()
        assert asked.wait(timeout=10)
        time.sleep(0.5)  # long enough for it to reach the row lock
        return 204, {}, ""

    http_mock.add_callback(responses.DELETE, zm.meeting_url(kit.MEETING), callback=zoom_delete)
    result = services.cancel(booking.pk, by=user, reason="Closed.")
    assert result.outcome == services.Outcome.CANCELLED
    services.send_cancelled_email(
        RequestFactory().get("/", HTTP_HOST="testserver"),
        result.link_request,
        result.cancelled,
        result.remaining,
        "Closed.",
    )
    outcome["thread"].join(timeout=30)

    assert outcome["status"] == 200
    assert list(ZoomEvent.objects.filter(slug=kit.SLUG).values_list("outcome", flat=True)) == [
        "no_change"
    ]
    assert len(mail.outbox) == 1
    booking.refresh_from_db()
    assert booking.status == LinkRequest.Status.CANCELLED
    assert booking.cancelled_by_id == user.pk  # the app's cancel, not a copy from Zoom


# --------------------------------------------------------------------------- 30 a stale answer
#
# Review round 1, B1: Zoom is asked before the lock (criterion 13), so a change made here can
# commit between the webhook's GET and its lock. Each test below makes that happen for real:
# Zoom's answer is built first, from the rows as they are, then the app's change runs on its
# own connection in another thread and commits, and only then does the GET return. Without
# criterion 30's fingerprint re-check, the stale answer was copied back over the app's change.


def _in_another_thread(work):
    """Run ``work`` on its own connection, wait for it to commit, and return its result."""
    done = {}

    def run():
        try:
            done["result"] = work()
        finally:
            connection.close()

    thread = threading.Thread(target=run)
    thread.start()
    thread.join(timeout=30)
    assert "result" in done, "the app's change didn't finish"
    return done["result"]


def _zoom_answers(http_mock, booking, changes):
    """``GET /meetings/{id}``: Zoom's answer as the booking stands when asked; then, for the
    first ``len(changes)`` calls, the next change commits before that answer is returned."""
    pending = list(changes)
    calls = []

    def answer(request):
        body = json.dumps(kit.booking_series(booking))  # what Zoom holds, read before…
        calls.append(body)
        if pending:
            _in_another_thread(pending.pop(0))  # …the app changes it here and commits
        return 200, {}, body

    kit.add_meeting(http_mock, callback=answer)
    return calls


def _app_move(user, booking, start, new_start):
    def move():
        target = Occurrence.objects.get(link_request=booking, starts_at=start)
        result = services.move_class(
            booking.pk,
            target.pk,
            starts_at=new_start,
            ends_at=new_start + (target.ends_at - target.starts_at),
            by=user,
        )
        assert result.outcome == services.Outcome.MOVED, result
        return result

    return move


def _zoom_takes_moves(http_mock, account):
    zm.add_listing(http_mock, account.email)
    http_mock.add(responses.PATCH, zm.meeting_url(kit.MEETING), status=204)


def _in_zoom_mail():
    return [m for m in mail.outbox if "directly in Zoom" in m.body]


def test_a_move_made_here_between_the_get_and_the_lock_is_kept(events, settings, http_mock):
    user, account = _setup(events, settings, http_mock)
    booking = _weekly(events, account)
    _zoom_takes_moves(http_mock, account)

    def move_and_email():
        result = _app_move(user, booking, at(7, 8, 30), at(8, 9))()
        services.send_moved_email(None, result.link_request, result.moves)
        return result

    asked = _zoom_answers(http_mock, booking, [move_and_email])

    assert kit.post(Client(), kit.meeting_event("meeting.updated")).status_code == 200

    assert _in_zoom_mail() == []  # no false "changed directly in Zoom" email
    moved = Occurrence.objects.get(link_request=booking, starts_at=at(8, 9))
    assert moved.moved_by_id == user.pk and not moved.moved_in_zoom  # the app's move is kept
    assert not Occurrence.objects.filter(link_request=booking, starts_at=at(7, 8, 30)).exists()
    assert [m.to for m in mail.outbox] == [["nimal@example.com"]]  # the move's own email only
    booking.refresh_from_db()
    assert booking.zoom_attention == ""
    assert list(ZoomEvent.objects.filter(slug=kit.SLUG).values_list("outcome", flat=True)) == [
        "no_change"
    ]
    assert len(asked) == 2  # the stale answer, then a fresh one


def test_a_cancel_made_here_between_the_get_and_the_lock_is_kept(events, settings, http_mock):
    user, account = _setup(events, settings, http_mock)
    booking = _weekly(events, account)
    http_mock.add(responses.DELETE, zm.meeting_url(kit.MEETING), status=204)

    def cancel_and_email():
        wed7 = Occurrence.objects.get(link_request=booking, starts_at=at(7, 8, 30))
        result = services.cancel(booking.pk, occurrence_id=wed7.pk, by=user, reason="Closed.")
        assert result.outcome == services.Outcome.CANCELLED, result
        services.send_cancelled_email(
            None, result.link_request, result.cancelled, result.remaining, "Closed."
        )
        return result

    asked = _zoom_answers(http_mock, booking, [cancel_and_email])

    assert kit.post(Client(), kit.meeting_event("meeting.updated")).status_code == 200

    booking.refresh_from_db()
    assert booking.zoom_attention == ""  # no false "isn't booked here" flag
    assert [m.to for m in mail.outbox] == [["nimal@example.com"]]  # the cancel's own; no IT email
    assert _in_zoom_mail() == []
    wed7 = Occurrence.objects.get(link_request=booking, starts_at=at(7, 8, 30))
    assert wed7.cancelled_by_id == user.pk and not wed7.cancelled_in_zoom
    assert list(ZoomEvent.objects.filter(slug=kit.SLUG).values_list("outcome", flat=True)) == [
        "no_change"
    ]
    assert len(asked) == 2  # the stale answer, then a fresh one


def test_two_changes_in_a_row_are_a_lock_race_that_changes_nothing(events, settings, http_mock):
    user, account = _setup(events, settings, http_mock)
    booking = _weekly(events, account)
    _zoom_takes_moves(http_mock, account)
    asked = _zoom_answers(
        http_mock,
        booking,
        [
            _app_move(user, booking, at(7, 8, 30), at(8, 9)),
            _app_move(user, booking, at(12, 8, 30), at(13, 9)),
        ],
    )

    assert kit.post(Client(), kit.meeting_event("meeting.updated")).status_code == 500

    assert len(asked) == 2  # asked once more, then gave up
    assert ZoomEvent.objects.filter(slug=kit.SLUG).count() == 0  # so Zoom retries
    for new_start in (at(8, 9), at(13, 9)):
        moved = Occurrence.objects.get(link_request=booking, starts_at=new_start)
        assert moved.moved_by_id == user.pk
    assert (
        not Occurrence.objects.filter(link_request=booking, moved_by__isnull=True)
        .exclude(moved_at__isnull=True)
        .exists()
    )
    booking.refresh_from_db()
    assert booking.zoom_attention == "" and mail.outbox == []
