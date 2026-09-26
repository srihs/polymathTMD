"""Brief 011, the services and provider layer: cancelling against a mocked Zoom, the honest
failure messages, the cancellation email, the start token and ``start_class()``, the provider's
new calls, the host-key reveal, the IT desk phone and check ``zoom.E006`` (criteria 11-15, 17-19,
23, 25, 27, 28, 36, 40-41, 43 and 47).

No test reaches the network: Zoom's answers are registered on the project-wide ``responses``
mock (``zoommock.py``), and the fake provider is steered for everything else.
"""

import logging
from datetime import date, datetime, time, timedelta
from unittest import mock

import pytest
import requests
import responses
from cryptography.fernet import Fernet
from django.core import mail, signing
from django.db import OperationalError, connections
from django.test import RequestFactory
from urllib3.exceptions import ProtocolError

from apps.zoom import services
from apps.zoom.checks import check_it_desk_phone
from apps.zoom.models import HostKeyReveal, HostKeyUnreadable, HostSlot, LinkRequest
from apps.zoom.providers import (
    FakeProvider,
    ManualProvider,
    MeetingProvider,
    ZoomProvider,
    ZoomUnavailable,
)
from apps.zoom.services import Outcome

from . import zoommock as zm
from .conftest import COLOMBO, FROZEN_NOW, book, booked_on, make_account, make_request

pytestmark = pytest.mark.django_db
HOST_KEY = "8421973"
MEETING = "81234567890"
QUIET = {"schedule_for_reminder": "false", "cancel_meeting_reminder": "false"}
SECRET_START = "https://us02web.zoom.us/s/81234567890?zak=SECRETZAK"


def at(day, hour, minute=0):
    return datetime(2026, 10, day, hour, minute, tzinfo=COLOMBO)


def _request():
    return RequestFactory().get("/", HTTP_HOST="testserver")


@pytest.fixture
def zoom02(db):
    return make_account("Zoom 02", sort_order=2, host_key=HOST_KEY)


@pytest.fixture
def live(settings, http_mock, zoom02):
    """Zoom 02 on the live provider, connected, with a token registered."""
    settings.ZOOM_PROVIDER = "zoom"
    zm.connect(settings, zoom02)
    zm.add_token(http_mock)
    return zoom02


def zl42(account, **kwargs):
    return booked_on(
        make_request(
            weekdays="1,3",
            first_date=date(2026, 10, 5),
            last_date=date(2026, 10, 28),
            class_name="Grade 11 Physics",
            requester_name="Nimal Perera",
            email="nimal@example.com",
        ),
        account,
        **kwargs,
    )


def zl43(account):
    return booked_on(
        make_request(first_date=date(2026, 10, 5), class_name="Grade 10 Chemistry"),
        account,
        meeting_id="81234560000",
    )


def _deletes(http_mock):
    return zm.calls_of(http_mock, "DELETE")


def _nothing_cancelled(link_request):
    link_request.refresh_from_db()
    assert link_request.status == LinkRequest.Status.APPROVED
    assert not link_request.occurrences.filter(cancelled_at__isnull=False).exists()
    assert HostSlot.objects.filter(occurrence__link_request=link_request).count() == (
        36 * link_request.occurrences.count()
    )


# --------------------------------------------------------------------------- 11 which call


def test_a_whole_weekly_booking_is_one_delete_of_the_meeting(live, http_mock, it_user):
    booking = zl42(live)
    zm.add_delete(http_mock, MEETING)
    result = services.cancel(booking.pk, by=it_user, reason="Closed.")
    assert result.outcome == Outcome.CANCELLED and result.whole
    [call] = _deletes(http_mock)
    assert call.request.url.split("?")[0] == zm.meeting_url(MEETING)
    assert zm.query(call) == QUIET
    booking.refresh_from_db()
    assert booking.status == "cancelled"
    assert booking.occurrences.filter(cancelled_at__isnull=True).count() == 0


def test_a_one_off_booking_is_one_delete_of_its_meeting(live, http_mock, it_user):
    booking = zl43(live)
    zm.add_delete(http_mock, "81234560000")
    result = services.cancel(booking.pk, by=it_user, reason="Closed.")
    assert result.outcome == Outcome.CANCELLED
    [call] = _deletes(http_mock)
    assert zm.query(call) == QUIET


def test_one_class_is_a_delete_of_its_occurrence(live, http_mock, it_user):
    booking = zl42(live)
    wed7 = booking.occurrences.get(starts_at=at(7, 8, 30))
    zm.add_delete(http_mock, MEETING)
    result = services.cancel(booking.pk, occurrence_id=wed7.pk, by=it_user, reason="Closed.")
    assert result.outcome == Outcome.CANCELLED and not result.whole
    assert [o.pk for o in result.cancelled] == [wed7.pk]
    assert len(result.remaining) == 7
    [call] = _deletes(http_mock)
    assert zm.query(call) == {**QUIET, "occurrence_id": wed7.zoom_occurrence_id}
    booking.refresh_from_db()
    assert booking.status == "approved"


def _series(starts):
    return {
        "id": int(MEETING),
        "start_url": SECRET_START,
        "join_url": zm.JOIN_URL,
        "occurrences": [
            {"occurrence_id": f"17{index}", "start_time": start, "status": status}
            for index, (start, status) in enumerate(starts)
        ],
    }


def test_a_class_with_no_stored_occurrence_id_is_looked_up_first(live, http_mock, it_user):
    booking = zl42(live, occurrence_ids=False)
    wed7 = booking.occurrences.get(starts_at=at(7, 8, 30))
    http_mock.add(
        responses.GET,
        zm.meeting_url(MEETING),
        json=_series(
            [
                ("2026-10-07T03:00:00Z", "deleted"),  # a deleted one never matches
                ("2026-10-05T03:00:00Z", "available"),
                ("2026-10-07T03:00:00Z", "available"),
            ]
        ),
    )
    zm.add_delete(http_mock, MEETING)
    result = services.cancel(booking.pk, occurrence_id=wed7.pk, by=it_user, reason="Closed.")
    assert result.outcome == Outcome.CANCELLED
    assert [c.request.method for c in http_mock.calls if "/meetings" in c.request.url] == [
        "GET",
        "DELETE",
    ]
    [call] = _deletes(http_mock)
    assert zm.query(call) == {**QUIET, "occurrence_id": "172"}


@pytest.mark.parametrize(
    "answer",
    [
        {"json": _series([("2026-10-05T03:00:00Z", "available")])},
        {"status": 404, "json": zm.zoom_error(3001)},
    ],
)
def test_a_class_zoom_no_longer_has_is_cancelled_with_no_delete(live, http_mock, it_user, answer):
    booking = zl42(live, occurrence_ids=False)
    wed7 = booking.occurrences.get(starts_at=at(7, 8, 30))
    http_mock.add(responses.GET, zm.meeting_url(MEETING), **answer)
    result = services.cancel(booking.pk, occurrence_id=wed7.pk, by=it_user, reason="Closed.")
    assert result.outcome == Outcome.CANCELLED
    assert _deletes(http_mock) == []
    wed7.refresh_from_db()
    assert wed7.cancelled_at is not None


def test_a_delete_answered_no_such_meeting_counts_as_done(live, http_mock, it_user):
    booking = zl42(live)
    zm.add_delete(http_mock, MEETING, status=404)
    http_mock.replace(
        responses.DELETE, zm.meeting_url(MEETING), status=404, json=zm.zoom_error(3001)
    )
    result = services.cancel(booking.pk, by=it_user, reason="Closed.")
    assert result.outcome == Outcome.CANCELLED


# --------------------------------------------------------------------------- 12 and 13


LASTING = (
    "Ask whoever manages the Zoom accounts to press Check connection for Zoom 02, then try again."
)


@pytest.mark.parametrize(
    ("reply", "message"),
    [
        (
            {"body": requests.exceptions.ConnectionError("refused")},
            "We couldn't cancel it in Zoom: no answer from Zoom. Nothing was cancelled. "
            "Try again in a few minutes.",
        ),
        (
            {"body": requests.exceptions.ConnectTimeout()},
            "We couldn't cancel it in Zoom: no answer from Zoom. Nothing was cancelled. "
            "Try again in a few minutes.",
        ),
        (
            {"status": 429},
            "We couldn't cancel it in Zoom: Zoom is busy right now. Nothing was cancelled. "
            "Try again in a few minutes.",
        ),
        (
            {"status": 401, "json": {}},
            "We couldn't cancel it in Zoom: Zoom didn't accept this account's connection "
            f"details. Nothing was cancelled. {LASTING}",
        ),
        (
            {"status": 400, "json": zm.zoom_error(4700)},
            "We couldn't cancel it in Zoom: the Zoom app for this account is missing a "
            f"permission. Nothing was cancelled. {LASTING}",
        ),
        (
            {"status": 404, "json": zm.zoom_error(1001)},
            "We couldn't cancel it in Zoom: Zoom has no user with this account's sign-in "
            f"email. Nothing was cancelled. {LASTING}",
        ),
        (
            {"status": 400, "json": zm.zoom_error(3000)},
            f"We couldn't cancel it in Zoom: Zoom error 3000. Nothing was cancelled. {LASTING}",
        ),
    ],
)
def test_zoom_said_no_rolls_everything_back_with_one_message_per_kind(
    live, http_mock, it_user, reply, message
):
    """Criterion 12. The 401 is Zoom's answer to both tries (the one refresh, brief 006)."""
    booking = zl42(live)
    zm.add_token(http_mock, zm.SECOND_TOKEN)
    http_mock.add(responses.DELETE, zm.meeting_url(MEETING), **reply)
    result = services.cancel(booking.pk, by=it_user, reason="Closed.")
    assert (result.outcome, result.message) == (Outcome.PROVIDER_ERROR, message)
    _nothing_cancelled(booking)
    assert mail.outbox == []


MAYBE = (
    "We couldn't tell whether Zoom removed it: no answer from Zoom. Nothing was cancelled here. "
    "Try again in a few minutes. Trying again is safe."
)


@pytest.mark.parametrize(
    "reply",
    [
        {"body": requests.exceptions.ReadTimeout()},
        {"body": requests.exceptions.ConnectionError(ProtocolError("Connection aborted."))},
        {"status": 502},
    ],
)
def test_zoom_may_have_done_it_rolls_back_and_says_so(live, http_mock, it_user, reply):
    """Criterion 13, then pressing again: the repeated delete is answered 3001, and succeeds."""
    booking = zl42(live)
    http_mock.add(responses.DELETE, zm.meeting_url(MEETING), **reply)
    result = services.cancel(booking.pk, by=it_user, reason="Closed.")
    assert (result.outcome, result.message) == (Outcome.PROVIDER_ERROR, MAYBE)
    _nothing_cancelled(booking)

    http_mock.replace(
        responses.DELETE, zm.meeting_url(MEETING), status=404, json=zm.zoom_error(3001)
    )
    assert services.cancel(booking.pk, by=it_user, reason="Closed.").outcome == Outcome.CANCELLED


def test_a_failed_occurrence_lookup_is_never_called_maybe_done(live, http_mock, it_user):
    """A GET can't have removed anything, so a 5xx on the lookup is a plain "couldn't"."""
    booking = zl42(live, occurrence_ids=False)
    wed7 = booking.occurrences.get(starts_at=at(7, 8, 30))
    http_mock.add(responses.GET, zm.meeting_url(MEETING), status=503)
    result = services.cancel(booking.pk, occurrence_id=wed7.pk, by=it_user, reason="Closed.")
    assert result.message == (
        "We couldn't cancel it in Zoom: no answer from Zoom. Nothing was cancelled. "
        "Try again in a few minutes."
    )
    assert _deletes(http_mock) == []


# --------------------------------------------------------------------------- 14


def _fail_the_first_commit(error):
    """Make the end of ``cancel()``'s transaction fail once, after the Zoom delete.

    Criterion 10's order puts every write before the Zoom call, so the one step left after
    Zoom has removed the meeting is the commit. Inside a test's own transaction that commit is
    ``cancel()``'s savepoint release, which is what fails here; Django then rolls the
    savepoint back, as a failed commit rolls a transaction back.
    """
    wrapper = connections["default"]
    real = wrapper.savepoint_commit
    calls = []

    def commit(sid):
        calls.append(sid)
        if len(calls) == 1:
            raise error
        return real(sid)

    return mock.patch.object(wrapper, "savepoint_commit", side_effect=commit)


def test_a_deadlock_after_zoom_removed_it_is_retried_and_the_retry_finishes(
    live, http_mock, it_user
):
    booking = zl42(live)
    zm.add_delete(http_mock, MEETING)  # the first delete removes it...
    http_mock.add(responses.DELETE, zm.meeting_url(MEETING), status=404, json=zm.zoom_error(3001))
    with _fail_the_first_commit(OperationalError(1213, "Deadlock found")):
        result = services.cancel(booking.pk, by=it_user, reason="Closed.")
    assert result.outcome == Outcome.CANCELLED
    assert len(_deletes(http_mock)) == 2  # ...and the retry's is answered "no such meeting"
    booking.refresh_from_db()
    assert booking.status == "cancelled"
    assert HostSlot.objects.count() == 0


def test_any_other_failure_after_zoom_removed_it_says_press_cancel_again(
    live, http_mock, it_user, caplog
):
    booking = zl42(live)
    zm.add_delete(http_mock, MEETING)
    with (
        _fail_the_first_commit(OperationalError(2013, "Lost connection")),
        caplog.at_level(logging.DEBUG, logger="apps.zoom"),
    ):
        result = services.cancel(booking.pk, by=it_user, reason="Closed.")
    assert (result.outcome, result.message) == (
        Outcome.PROVIDER_ERROR,
        "Zoom removed it, but saving the cancellation here failed. Press Cancel again to finish.",
    )
    _nothing_cancelled(booking)
    [error] = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert error.getMessage() == (
        f"Cancelling {booking.reference}: Zoom meeting {MEETING} was removed, but saving "
        "failed: OperationalError"
    )


def test_a_lock_race_before_zoom_says_nothing_was_cancelled(live, http_mock, it_user):
    booking = zl42(live)
    error = OperationalError(1205, "Lock wait timeout exceeded")
    with mock.patch.object(HostSlot.objects, "filter", side_effect=error):
        result = services.cancel(booking.pk, by=it_user, reason="Closed.")
    assert (result.outcome, result.message) == (
        Outcome.CONFLICT,
        "Someone else was changing this booking at the same moment. Nothing was cancelled. "
        "Try again.",
    )
    assert _deletes(http_mock) == []


def test_a_blank_reason_is_refused_by_the_service_too(zoom02, it_user):
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError):
        services.cancel(zl42(zoom02).pk, by=it_user, reason="   ")


# --------------------------------------------------------------------------- 15 the messages


def _result(link_request, whole, cancelled):
    return services.CancelResult(Outcome.CANCELLED, "", link_request, cancelled, [], whole)


def test_the_success_messages(zoom02):
    booking = zl42(zoom02)
    mon5 = booking.occurrences.first()
    from django.contrib.messages import constants as levels

    assert services.cancelled_message(
        _result(booking, True, [mon5]), emailed=True, checks_zoom=True
    ) == (levels.SUCCESS, "Cancelled the booking. We emailed nimal@example.com.")
    assert services.cancelled_message(
        _result(booking, False, [mon5]), emailed=True, checks_zoom=True
    ) == (levels.SUCCESS, "Cancelled the class on Mon 5 Oct 2026. We emailed nimal@example.com.")
    assert services.cancelled_message(
        _result(booking, False, [mon5]), emailed=False, checks_zoom=True
    ) == (
        levels.WARNING,
        "Cancelled, but the email to nimal@example.com didn't send. Tell them yourself.",
    )
    assert services.cancelled_message(
        _result(booking, True, [mon5]), emailed=True, checks_zoom=False
    ) == (
        levels.SUCCESS,
        "Cancelled the booking. We emailed nimal@example.com. This system can't reach Zoom: "
        "delete it in Zoom too.",
    )


def test_the_fake_provider_records_the_delete(zoom02, it_user):
    booking = zl43(zoom02)
    services.cancel(booking.pk, by=it_user, reason="Closed.")
    assert FakeProvider.deleted == [(zoom02.pk, "81234560000", None)]


def test_the_manual_provider_calls_nothing_and_still_cancels(zoom02, it_user, http_mock):
    booking = zl43(zoom02)
    result = services.cancel(booking.pk, by=it_user, reason="Closed.", provider=ManualProvider())
    assert result.outcome == Outcome.CANCELLED
    assert len(http_mock.calls) == 0 and FakeProvider.deleted == []


# --------------------------------------------------------------------------- 17 the email


def _cancel_and_email(booking, user, occurrence=None, reason="The school is closed."):
    result = services.cancel(
        booking.pk, occurrence_id=occurrence.pk if occurrence else None, by=user, reason=reason
    )
    assert result.outcome == Outcome.CANCELLED
    assert services.send_cancelled_email(
        _request(), result.link_request, result.cancelled, result.remaining, reason
    )
    [message] = mail.outbox
    assert message.to == ["nimal@example.com"] and message.cc == [] and message.bcc == []
    assert getattr(message, "alternatives", []) == []
    return message


def test_the_cancellation_email_for_one_class(zoom02, it_user):
    booking = zl42(zoom02)
    wed7 = booking.occurrences.get(starts_at=at(7, 8, 30))
    message = _cancel_and_email(booking, it_user, wed7)
    assert message.subject == f"Cancelled: {booking.reference} Grade 11 Physics"
    body = message.body
    for expected in (
        "- Wed 7 Oct 2026, 8:30 am to 11:30 am",
        "Reason: The school is closed.",
        "Your other classes are still on, with the same link and start link.",
        "Zoom doesn't tell the people you shared the link with. Please let your students know.",
        "To book again, send a new request: http://testserver/zoom/request/",
    ):
        assert expected in body
    _assert_no_secrets(body, booking)


def test_the_cancellation_email_for_a_whole_booking_has_no_still_on_line(zoom02, it_user):
    booking = zl42(zoom02)
    body = _cancel_and_email(booking, it_user).body
    assert body.count("\n- ") == 8
    assert "still on" not in body
    assert "Please let your students know." in body
    _assert_no_secrets(body, booking)


def test_the_cancellation_email_with_the_manual_provider_mentions_no_start_link(
    zoom02, it_user, settings
):
    booking = zl42(zoom02)
    settings.ZOOM_PROVIDER = "manual"
    wed7 = booking.occurrences.get(starts_at=at(7, 8, 30))
    body = _cancel_and_email(booking, it_user, wed7).body
    assert "Your other classes are still on, with the same link." in body
    assert "start link" not in body.lower()


def _assert_no_secrets(text, booking):
    for secret in (booking.join_url, booking.passcode, "/zoom/start/", HOST_KEY):
        assert secret not in text


def test_no_email_of_the_whole_flow_carries_a_host_key(zoom02, it_user, superuser):
    """Criterion 28 (amends 005 criterion 61): confirm, IT, approval, rejection, cancellation."""
    link_request = make_request(status=LinkRequest.Status.UNVERIFIED)
    services.send_confirm_email(_request(), link_request)
    link_request.mark_verified()
    services.send_it_new_request_email(_request(), link_request)
    book(link_request, zoom02, it_user)
    services.send_approved_email(_request(), link_request)
    other = make_request(first_date=date(2026, 11, 2))
    other.reject(it_user, "Use the Grade 10 link.")
    services.send_rejected_email(_request(), other)
    result = services.cancel(link_request.pk, by=it_user, reason="Closed.")
    services.send_cancelled_email(
        _request(), result.link_request, result.cancelled, result.remaining, "Closed."
    )
    assert len(mail.outbox) == 6  # confirm, IT x2, approval, rejection, cancellation
    for message in mail.outbox:
        assert HOST_KEY not in message.body and HOST_KEY not in message.subject


# --------------------------------------------------------------------------- 18 provider


def test_which_providers_can_start():
    assert MeetingProvider.can_start is False
    assert ManualProvider.can_start is False
    assert FakeProvider.can_start is True and ZoomProvider.can_start is True
    assert FakeProvider().start_url(host_account=mock.Mock(pk=1), meeting_id="123") == (
        "https://zoom.example.invalid/s/123"
    )
    assert FakeProvider.start_calls == [(1, "123")]


def test_the_zoom_provider_returns_zooms_start_url(live, http_mock):
    http_mock.add(responses.GET, zm.meeting_url(MEETING), json=_series([]))
    assert ZoomProvider().start_url(host_account=live, meeting_id=MEETING) == SECRET_START


@pytest.mark.parametrize(
    "url",
    [
        None,
        "",
        "http://us02web.zoom.us/s/1",
        "https://evil.example/zoom.us/s/1",
        "https://zoom.us.evil.example/s/1",
        "https://evil.example\\.zoom.us/s/1",
        "https://notzoom.us/s/1",
        "javascript:alert(1)",
    ],
)
def test_a_start_url_that_isnt_https_on_zoom_us_is_refused(live, http_mock, url):
    http_mock.add(responses.GET, zm.meeting_url(MEETING), json={"id": 1, "start_url": url})
    with pytest.raises(ZoomUnavailable):
        ZoomProvider().start_url(host_account=live, meeting_id=MEETING)


def test_the_occurrence_lookup_matches_by_start_and_skips_deleted_classes(live, http_mock):
    http_mock.add(
        responses.GET,
        zm.meeting_url(MEETING),
        json=_series([("2026-10-05T03:00:00Z", "deleted"), ("2026-10-07T03:00:00Z", "ok")]),
    )
    provider = ZoomProvider()
    assert (
        provider.occurrence_id_for(host_account=live, meeting_id=MEETING, starts_at=at(7, 8, 30))
        == "171"
    )
    assert (
        provider.occurrence_id_for(host_account=live, meeting_id=MEETING, starts_at=at(5, 8, 30))
        is None
    )
    assert (
        FakeProvider().occurrence_id_for(
            host_account=live, meeting_id=MEETING, starts_at=at(5, 8, 30)
        )
        is None
    )


# --------------------------------------------------------------------------- 19 the token


def test_a_start_token_names_its_booking(zoom02):
    booking = zl42(zoom02)
    token = services.start_token(booking)
    assert signing.loads(token, salt="apps.zoom.start-class") == {"r": booking.pk, "m": MEETING}
    assert services.link_request_from_start_token(token) == booking
    assert services.start_link(_request(), booking) == f"http://testserver/zoom/start/{token}/"


def test_a_cancelled_bookings_token_still_opens_its_page(zoom02, it_user):
    booking = zl42(zoom02)
    services.cancel(booking.pk, by=it_user, reason="Closed.")
    assert services.link_request_from_start_token(services.start_token(booking)) == booking


def test_invalid_start_tokens(zoom02):
    booking = zl42(zoom02)
    token = services.start_token(booking)
    waiting = make_request(first_date=date(2026, 11, 2))
    dumps = lambda payload: signing.dumps(payload, salt="apps.zoom.start-class")  # noqa: E731
    for bad in (
        token[:-2] + "xx",  # bad signature
        signing.dumps({"r": booking.pk, "m": MEETING}, salt="another-salt"),
        dumps({"r": 999999, "m": MEETING}),  # no such request
        dumps({"r": waiting.pk, "m": ""}),  # never approved
        dumps({"r": waiting.pk, "m": MEETING}),
        dumps({"r": booking.pk, "m": "81234569999"}),  # a different meeting
        dumps({"r": str(booking.pk), "m": MEETING}),
        dumps([booking.pk, MEETING]),
    ):
        assert services.link_request_from_start_token(bad) is None


# --------------------------------------------------------------------------- 23 and 25


def test_starting_a_ready_class_asks_zoom_once_and_logs_the_use(live, http_mock, caplog):
    booking = zl42(live)
    http_mock.add(responses.GET, zm.meeting_url(MEETING), json=_series([]))
    with (
        mock.patch("django.utils.timezone.now", return_value=at(5, 8, 10)),
        caplog.at_level(logging.DEBUG),
    ):
        result = services.start_class(booking, ip="203.0.113.9")
    assert (result.state, result.url) == ("ready", SECRET_START)
    assert "SECRETZAK" not in repr(result)
    assert len(zm.calls_of(http_mock, "GET", f"/meetings/{MEETING}")) == 1
    [record] = [r for r in caplog.records if r.name == "apps.zoom.services"]
    assert record.levelno == logging.INFO
    assert record.getMessage() == (
        f"Start link used for {booking.reference}, class Mon 5 Oct 2026 8:30 am, from 203.0.113.9"
    )


@pytest.mark.parametrize(
    ("reply", "error", "still"),
    [
        ({"status": 429}, "We couldn't reach Zoom just now. Try again in a minute.", True),
        ({"status": 500}, "We couldn't reach Zoom just now. Try again in a minute.", True),
        (
            {"body": requests.exceptions.ConnectTimeout()},
            "We couldn't reach Zoom just now. Try again in a minute.",
            True,
        ),
        (
            {"status": 400, "json": zm.zoom_error(4711)},
            "We couldn't reach Zoom just now. Try again in a minute.",
            True,
        ),
        (
            {"status": 404, "json": zm.zoom_error(3001)},
            "This class's meeting isn't in Zoom any more.",
            False,
        ),
    ],
)
def test_a_failed_start_says_what_to_do_and_logs_a_warning(
    live, http_mock, caplog, reply, error, still
):
    booking = zl42(live)
    http_mock.add(responses.GET, zm.meeting_url(MEETING), **reply)
    with (
        mock.patch("django.utils.timezone.now", return_value=at(5, 8, 10)),
        caplog.at_level(logging.DEBUG, logger="apps.zoom"),
    ):
        result = services.start_class(booking, ip="203.0.113.9")
    assert (result.state, result.url, result.error, result.error_still) == (
        "ready",
        None,
        error,
        still,
    )
    [record] = [r for r in caplog.records if r.name == "apps.zoom.services"]
    assert record.levelno == logging.WARNING
    assert booking.reference in record.getMessage()
    assert "/zoom/start/" not in record.getMessage() and "http" not in record.getMessage()


def test_no_call_is_made_when_the_class_isnt_ready(live, http_mock):
    booking = zl42(live)
    result = services.start_class(booking, ip="203.0.113.9")  # the frozen now: too early
    assert result.state == "too_early" and result.url is None
    assert result.opens_at == at(5, 8, 0) and result.opens_after_other_class is False
    assert len(http_mock.calls) == 0


def test_the_manual_provider_is_not_set_up_and_calls_nothing(zoom02, http_mock):
    booking = zl42(zoom02)
    with mock.patch("django.utils.timezone.now", return_value=at(5, 8, 10)):
        result = services.start_class(booking, ip=None, provider=ManualProvider())
    assert (result.state, result.occurrence.starts_at) == ("not_set_up", at(5, 8, 30))
    assert len(http_mock.calls) == 0


# --------------------------------------------------------------------------- 40, 41, 43


def test_revealing_a_key_records_it_and_logs_who_without_the_key(zoom02, it_user, caplog):
    with caplog.at_level(logging.DEBUG, logger="apps.zoom"):
        assert services.reveal_host_key(zoom02, by=it_user) == HOST_KEY
    [reveal] = HostKeyReveal.objects.all()
    assert (reveal.host_account, reveal.shown_by, reveal.shown_at) == (zoom02, it_user, FROZEN_NOW)
    [record] = caplog.records
    assert record.levelno == logging.INFO
    assert record.getMessage() == "Host key for Zoom 02 shown to kasun.it"


def test_revealing_no_key_or_an_unreadable_one_records_nothing(zoom02, it_user, settings, caplog):
    empty = make_account("Zoom 05")
    with pytest.raises(services.NoHostKeySaved):
        services.reveal_host_key(empty, by=it_user)
    settings.HOST_KEY_ENCRYPTION_KEYS = [Fernet.generate_key().decode()]
    with caplog.at_level(logging.DEBUG, logger="apps.zoom"), pytest.raises(HostKeyUnreadable):
        services.reveal_host_key(zoom02, by=it_user)
    assert HostKeyReveal.objects.count() == 0
    [record] = caplog.records
    assert record.levelno == logging.WARNING
    assert record.getMessage() == "Host key for Zoom 02 can't be read: InvalidToken"


# --------------------------------------------------------------------------- 47


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("", None),
        ("   ", None),
        ("011 234 5678", {"display": "+94 11 234 5678", "tel": "+94112345678"}),
        ("+94 11 234 5678", {"display": "+94 11 234 5678", "tel": "+94112345678"}),
        ("abc", None),
    ],
)
def test_the_it_desk_phone(settings, value, expected):
    settings.IT_DESK_PHONE = value
    assert services.it_desk_phone() == expected


def test_check_e006_refuses_a_phone_number_it_cant_read(settings):
    settings.IT_DESK_PHONE = "abc"
    [error] = check_it_desk_phone()
    assert error.id == "zoom.E006"
    assert error.msg == (
        "IT_DESK_PHONE isn't a phone number the app can read. Use a form like 011 234 5678 or "
        "+94 11 234 5678."
    )
    for fine in ("", "011 234 5678"):
        settings.IT_DESK_PHONE = fine
        assert check_it_desk_phone() == []


def test_check_e006_runs_with_manage_py_check(settings):
    from django.core import checks

    settings.IT_DESK_PHONE = "abc"
    ids = [message.id for message in checks.run_checks()]
    assert "zoom.E006" in ids


def test_the_window_opens_after_the_class_before_on_the_same_account(zoom02):
    """Criterion 22's second too-early sentence is driven by this flag (StartResult)."""
    earlier = make_request(first_date=date(2026, 10, 5), start=time(6, 30), end=time(8, 15))
    booked_on(earlier, zoom02, meeting_id="81234569999")
    booking = zl43(zoom02)
    result = services.start_state(booking)
    assert result.state == "too_early"
    assert result.opens_at == at(5, 8, 15) and result.opens_after_other_class is True
    assert result.opens_at - result.occurrence.starts_at == timedelta(minutes=-15)
