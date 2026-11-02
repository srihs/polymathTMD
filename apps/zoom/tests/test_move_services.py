"""Brief 012, the services and provider layer: moving one class and changing a series' time
against the fake provider and a mocked Zoom, every pinned message, the compensating update, the
"classes moved" email and the start link following the move (criteria 3, 7, 9-16, 18, 19 and 23).

No test reaches the network: Zoom's answers are registered on the project-wide ``responses``
mock (``zoommock.py``), and the fake provider is steered for everything else.

ZL-0042 is weekly, Mon and Wed, 5-28 Oct 2026, 8:30-11:30 (8 classes), meeting 81234567890 on
Zoom 02; the frozen now is Mon 28 Sep 2026, 10:00 Colombo (04:30 UTC).
"""

import json
import logging
from contextlib import contextmanager
from datetime import UTC, date, datetime, time
from unittest import mock
from urllib.parse import parse_qs, urlsplit

import pytest
import requests
import responses
from django.contrib.messages import constants as levels
from django.core import mail
from django.db import OperationalError, connection, connections
from django.test import RequestFactory

from apps.zoom import models, services
from apps.zoom.errors import (
    ProviderError,
    ZoomAuthFailed,
    ZoomBusy,
    ZoomDailyLimit,
    ZoomMeetingNotFound,
    ZoomMissingScope,
    ZoomNotConnected,
    ZoomRejected,
    ZoomUnavailable,
    ZoomUserNotFound,
)
from apps.zoom.models import HostSlot, LinkRequest
from apps.zoom.providers import BusyTime, FakeProvider, ManualProvider, update_payload
from apps.zoom.services import MovedClass, MoveResult, Outcome

from . import zoommock as zm
from .conftest import COLOMBO, FROZEN_NOW, booked_on, make_account, make_request
from .test_cancel_services import _fail_the_first_commit

pytestmark = pytest.mark.django_db
MEETING = "81234567890"
LASTING = (
    "Ask whoever manages the Zoom accounts to press Check connection for Zoom 02, then try again."
)


def at(day, hour, minute=0, month=10):
    return datetime(2026, month, day, hour, minute, tzinfo=COLOMBO)


def _utc_text(moment):
    """Zoom's ``2026-10-DDTHH:MM:00Z`` for an aware time (UTC is 5:30 behind Colombo)."""
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _request():
    return RequestFactory().get("/", HTTP_HOST="testserver")


@pytest.fixture
def zoom02(db):
    return make_account("Zoom 02", sort_order=2, host_key="8421973")


@pytest.fixture
def live(settings, http_mock, zoom02):
    """Zoom 02 on the live provider, connected, with a token and an empty meeting list."""
    settings.ZOOM_PROVIDER = "zoom"
    zm.connect(zoom02)
    zm.add_token(http_mock)
    zm.add_listing(http_mock, zoom02.email, [])
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


def wed7(booking):
    return booking.occurrences.get(starts_at=at(7, 8, 30))


def move_wed7(booking, starts_at=None, ends_at=None, **kwargs):
    kwargs.setdefault("by", None)
    return services.move_class(
        booking.pk,
        wed7(booking).pk,
        starts_at=starts_at or at(8, 9),
        ends_at=ends_at or at(8, 12),
        **kwargs,
    )


def _slots(occurrence):
    return sorted(
        HostSlot.objects.filter(occurrence=occurrence).values_list("starts_at", flat=True)
    )


def _unchanged(booking):
    """Nothing about ZL-0042 was changed here: times, slots, request fields, moved marks."""
    booking.refresh_from_db()
    assert (booking.start_time, booking.end_time) == (time(8, 30), time(11, 30))
    for occurrence in booking.occurrences.all():
        local = occurrence.starts_at.astimezone(COLOMBO)
        assert (local.hour, local.minute) == (8, 30)
        assert occurrence.moved_at is None and occurrence.moved_by is None
        assert len(_slots(occurrence)) == 36
        assert _slots(occurrence)[0] == occurrence.starts_at


def _patches(http_mock):
    return zm.calls_of(http_mock, "PATCH")


def _cancel(occurrence, user):
    occurrence.cancelled_at, occurrence.cancelled_by = FROZEN_NOW, user
    occurrence.cancel_reason = "Sports meet."
    occurrence.save()
    HostSlot.objects.filter(occurrence=occurrence).delete()


# --------------------------------------------------------------------------- 3 what a move writes


def test_moving_one_class_writes_it_and_asks_zoom_once(zoom02, it_user):
    booking = zl42(zoom02)
    target = wed7(booking)
    result = move_wed7(booking, by=it_user)
    assert result.outcome == Outcome.MOVED and result.series is False
    [moved] = result.moves
    assert (moved.old_start, moved.old_end) == (at(7, 8, 30), at(7, 11, 30))
    target.refresh_from_db()
    assert (target.starts_at, target.ends_at) == (at(8, 9), at(8, 12))
    assert (target.moved_at, target.moved_by) == (FROZEN_NOW, it_user)
    assert target.host_account == zoom02
    slots = _slots(target)
    assert len(slots) == 36 and slots[0] == at(8, 9) and slots[-1] == at(8, 11, 55)
    # A one-class move leaves the request's fields alone (D4), and the other classes too.
    booking.refresh_from_db()
    assert (booking.start_time, booking.end_time) == (time(8, 30), time(11, 30))
    assert booking.occurrences.filter(moved_at__isnull=False).count() == 1
    assert FakeProvider.patched == [
        {
            "host_account_id": zoom02.pk,
            "meeting_id": MEETING,
            "occurrence_id": target.zoom_occurrence_id,
            "starts_at": at(8, 9),
            "ends_at": at(8, 12),
            "weekdays": None,
            "count": None,
        }
    ]


def test_moving_a_one_off_class_updates_the_meeting_itself(zoom02, it_user):
    booking = zl43(zoom02)
    result = services.move_class(
        booking.pk,
        booking.occurrences.get().pk,
        starts_at=at(6, 9),
        ends_at=at(6, 10),
        by=it_user,
    )
    assert result.outcome == Outcome.MOVED
    [record] = FakeProvider.patched
    assert (record["meeting_id"], record["occurrence_id"]) == ("81234560000", None)


def test_changing_the_series_moves_every_remaining_class_and_the_request(zoom02, it_user):
    booking = zl42(zoom02)
    result = services.move_series(booking.pk, start_time=time(9), end_time=time(12), by=it_user)
    assert result.outcome == Outcome.MOVED and result.series is True
    assert len(result.moves) == 8
    booking.refresh_from_db()
    assert (booking.start_time, booking.end_time) == (time(9), time(12))
    assert booking.schedule_summary.startswith("Every Monday and Wednesday, 9:00 am to 12:00 pm")
    for occurrence in booking.occurrences.all():
        local = occurrence.starts_at.astimezone(COLOMBO)
        assert (local.hour, local.minute) == (9, 0)
        assert occurrence.moved_by == it_user
        # The fake answers as Zoom would: every class's new occurrence ID is stored.
        assert occurrence.zoom_occurrence_id == str(int(occurrence.starts_at.timestamp() * 1000))
    [record] = FakeProvider.patched
    assert (record["starts_at"], record["weekdays"], record["count"]) == (at(5, 9), "1,3", 8)


def test_a_series_change_never_touches_held_or_cancelled_classes(zoom02, it_user, monkeypatch):
    booking = zl42(zoom02)
    mon12 = booking.occurrences.get(starts_at=at(12, 8, 30))
    _cancel(mon12, it_user)
    monkeypatch.setattr("django.utils.timezone.now", lambda: at(6, 12))  # Mon 5 is held
    result = services.move_series(booking.pk, start_time=time(9), end_time=time(12), by=it_user)
    assert result.outcome == Outcome.MOVED
    assert len(result.moves) == 6
    mon5 = booking.occurrences.get(starts_at=at(5, 8, 30))
    mon12.refresh_from_db()
    for untouched in (mon5, mon12):
        assert untouched.moved_at is None
    assert mon12.starts_at == at(12, 8, 30)
    # Zoom's series starts at the first remaining class, for the pattern's 7 dates, and the
    # cancelled Mon 12 is deleted again straight after.
    [record] = FakeProvider.patched
    assert (record["starts_at"], record["count"]) == (at(7, 9), 7)
    assert FakeProvider.deleted == [(zoom02.pk, MEETING, str(int(at(12, 9).timestamp() * 1000)))]


# --------------------------------------------------------------------------- 7 clashes


def test_moving_onto_the_bookings_own_other_class_clashes(zoom02):
    booking = zl42(zoom02)
    result = move_wed7(booking, at(5, 8, 30), at(5, 11, 30))
    assert (result.outcome, result.message) == (
        Outcome.CONFLICT,
        f"Zoom 02 already has {booking.reference} Grade 11 Physics at that time. "
        "Choose another time.",
    )
    assert FakeProvider.patched == [] and FakeProvider.busy_calls == []
    _unchanged(booking)


def test_touching_the_bookings_own_time_isnt_a_clash(zoom02):
    booking = zl42(zoom02)
    assert move_wed7(booking, at(7, 11, 30), at(7, 12, 30)).outcome == Outcome.MOVED


def test_a_meeting_made_in_zoom_at_the_new_time_clashes(zoom02):
    booking = zl42(zoom02)
    FakeProvider.busy[zoom02.pk] = [
        BusyTime(at(8, 9).astimezone(COLOMBO), at(8, 10), "Staff briefing", "85550001111")
    ]
    result = move_wed7(booking)
    assert (result.outcome, result.message) == (
        Outcome.CONFLICT,
        "Zoom 02 has a meeting in Zoom at that time: Staff briefing, Thu 8 Oct 2026 at 9:00 am. "
        "Choose another time.",
    )
    assert FakeProvider.patched == []
    _unchanged(booking)


def test_the_bookings_own_meeting_in_zoom_at_the_old_time_doesnt_clash(zoom02):
    booking = zl42(zoom02)
    FakeProvider.busy[zoom02.pk] = [BusyTime(at(7, 8, 30), at(7, 11, 30), "Physics", MEETING)]
    assert move_wed7(booking, at(7, 9), at(7, 12)).outcome == Outcome.MOVED


def test_an_untitled_zoom_meeting_is_named_through_display_topic(zoom02):
    booking = zl42(zoom02)
    FakeProvider.busy[zoom02.pk] = [BusyTime(at(8, 8), at(8, 10), "", "85550001111")]
    assert "at that time: a meeting with no name, Thu 8 Oct 2026 at 8:00 am." in (
        move_wed7(booking).message
    )


# --------------------------------------------------------------------------- 9 the other rows


def test_an_account_that_isnt_connected_refuses_the_move(zoom02):
    booking = zl42(zoom02)
    FakeProvider.not_connected = {zoom02.pk}
    result = move_wed7(booking)
    assert (result.outcome, result.message) == (
        Outcome.CONFLICT,
        "Zoom 02 isn't connected to Zoom, so this class can't be moved here. Set up its Zoom "
        "connection on the Zoom accounts page.",
    )
    assert FakeProvider.busy_calls == [] and FakeProvider.patched == []


@pytest.mark.parametrize(
    ("error", "ending"),
    [
        (ZoomBusy(), "Zoom is busy right now. Try again in a few minutes."),
        (ZoomUnavailable(), "No answer from Zoom. Try again in a few minutes."),
        (
            ZoomAuthFailed(),
            "Zoom didn't accept this account's connection details. Ask whoever manages the "
            "Zoom accounts to press Check connection for Zoom 02.",
        ),
    ],
)
def test_when_zoom_cant_be_asked_nothing_is_changed(zoom02, error, ending):
    booking = zl42(zoom02)
    FakeProvider.unavailable[zoom02.pk] = error
    result = move_wed7(booking)
    assert (result.outcome, result.message) == (
        Outcome.PROVIDER_ERROR,
        f"We couldn't check Zoom 02's meetings in Zoom, so nothing was changed. {ending}",
    )
    assert FakeProvider.patched == []
    _unchanged(booking)


def test_the_slot_backstop_says_booked_a_moment_ago(zoom02):
    """A slot at the new time that the locked re-check can't see (a stray row) still stops it."""
    booking = zl42(zoom02)
    stray = make_request(first_date=date(2026, 10, 8), start=time(9), end=time(10))
    HostSlot.objects.create(
        host_account=zoom02, starts_at=at(8, 9), occurrence=stray.occurrences.get()
    )
    result = move_wed7(booking)
    assert (result.outcome, result.message) == (
        Outcome.CONFLICT,
        "Zoom 02 was booked at that time a moment ago. Choose another time.",
    )
    assert FakeProvider.patched == []
    _unchanged(booking)


def test_a_class_that_cant_be_moved_is_refused_before_zoom(zoom02, it_user, monkeypatch):
    booking = zl42(zoom02)
    _cancel(wed7(booking), it_user)
    assert move_wed7(booking).message == "That class was cancelled."
    monkeypatch.setattr("django.utils.timezone.now", lambda: at(5, 9))
    mon5 = booking.occurrences.get(starts_at=at(5, 8, 30))
    result = services.move_class(
        booking.pk, mon5.pk, starts_at=at(6, 9), ends_at=at(6, 10), by=None
    )
    assert (result.outcome, result.message) == (
        Outcome.NOTHING_TO_DO,
        "That class has already started, so it can't be moved.",
    )
    assert FakeProvider.busy_calls == [] and FakeProvider.patched == []


def test_a_time_already_booked_is_invalid_not_a_clash(zoom02):
    result = move_wed7(zl42(zoom02), at(7, 8, 30), at(7, 11, 30))
    assert (result.outcome, result.message) == (Outcome.INVALID, models.MOVE_UNCHANGED)


# --------------------------------------------------------------------------- 10 the calls


def test_one_class_of_a_weekly_booking_is_one_patch_of_its_occurrence(live, http_mock):
    booking = zl42(live)
    target = wed7(booking)
    http_mock.add(responses.PATCH, zm.meeting_url(MEETING), status=204)
    assert move_wed7(booking).outcome == Outcome.MOVED
    [call] = _patches(http_mock)
    assert zm.query(call) == {"occurrence_id": target.zoom_occurrence_id}
    assert zm.body(call) == {
        "start_time": "2026-10-08T09:00:00",
        "timezone": "Asia/Colombo",
        "duration": 180,
    }


def test_a_blank_occurrence_id_is_looked_up_first_and_kept(live, http_mock):
    booking = zl42(live, occurrence_ids=False)
    http_mock.add(
        responses.GET,
        zm.meeting_url(MEETING),
        json={
            "id": int(MEETING),
            "occurrences": [
                {"occurrence_id": "1759800600000", "start_time": _utc_text(at(7, 8, 30))}
            ],
        },
    )
    http_mock.add(responses.PATCH, zm.meeting_url(MEETING), status=204)
    assert move_wed7(booking).outcome == Outcome.MOVED
    meeting_calls = [c.request.method for c in http_mock.calls if "/meetings/" in c.request.url]
    assert meeting_calls == ["GET", "PATCH"]
    assert zm.query(_patches(http_mock)[0]) == {"occurrence_id": "1759800600000"}
    assert booking.occurrences.get(starts_at=at(8, 9)).zoom_occurrence_id == "1759800600000"


def test_the_one_off_class_is_a_patch_of_the_meeting(live, http_mock):
    booking = zl43(live)
    http_mock.add(responses.PATCH, zm.meeting_url("81234560000"), status=204)
    result = services.move_class(
        booking.pk, booking.occurrences.get().pk, starts_at=at(6, 9), ends_at=at(6, 10), by=None
    )
    assert result.outcome == Outcome.MOVED
    [call] = _patches(http_mock)
    assert zm.query(call) == {}
    assert set(zm.body(call)) == {"start_time", "timezone", "duration"}


def _series_answer(starts, deleted=()):
    return {
        "id": int(MEETING),
        "join_url": zm.JOIN_URL,
        "start_url": zm.START_URL,
        "occurrences": [
            {
                "occurrence_id": f"70{index}",
                "start_time": _utc_text(start),
                "duration": 180,
                "status": "deleted" if start in deleted else "available",
            }
            for index, start in enumerate(starts)
        ],
    }


NEW_STARTS = [at(day, 9) for day in (5, 7, 12, 14, 19, 21, 26, 28)]


def test_a_series_is_one_patch_then_the_read_back_then_the_cancelled_dates_deletes(
    live, http_mock, it_user
):
    booking = zl42(live)
    _cancel(booking.occurrences.get(starts_at=at(12, 8, 30)), it_user)
    http_mock.add(responses.PATCH, zm.meeting_url(MEETING), status=204)
    http_mock.add(responses.GET, zm.meeting_url(MEETING), json=_series_answer(NEW_STARTS))
    zm.add_delete(http_mock, MEETING)
    result = services.move_series(booking.pk, start_time=time(9), end_time=time(12), by=it_user)
    assert result.outcome == Outcome.MOVED, result.message
    meeting_calls = [c.request.method for c in http_mock.calls if "/meetings/" in c.request.url]
    assert meeting_calls == ["PATCH", "GET", "DELETE"]
    [patch] = _patches(http_mock)
    assert zm.query(patch) == {}
    assert zm.body(patch) == {
        "start_time": "2026-10-05T09:00:00",
        "timezone": "Asia/Colombo",
        "duration": 180,
        "recurrence": {"type": 2, "repeat_interval": 1, "weekly_days": "2,4", "end_times": 8},
    }
    [delete] = zm.calls_of(http_mock, "DELETE")
    assert zm.query(delete) == {
        "occurrence_id": "702",
        "schedule_for_reminder": "false",
        "cancel_meeting_reminder": "false",
    }
    stored = dict(
        booking.occurrences.filter(cancelled_at__isnull=True).values_list(
            "starts_at", "zoom_occurrence_id"
        )
    )
    assert stored == {start: f"70{i}" for i, start in enumerate(NEW_STARTS) if i != 2}


def test_no_update_body_ever_carries_settings_topic_or_agenda():
    one = update_payload(at(8, 9), at(8, 12))
    series = update_payload(at(5, 9), at(5, 12), weekdays="1,3", count=8)
    assert set(one) == {"start_time", "timezone", "duration"}
    assert set(series) == {"start_time", "timezone", "duration", "recurrence"}


# --------------------------------------------------------------------------- 11 and 32 putting back
#
# Criterion 32's booking: ZL-0042 with the Wed 14 Oct class cancelled (011) and the Mon 12 Oct
# class moved by itself to 13:00-16:00. Its seven remaining classes are Mon 5, Wed 7, Mon 12
# (13:00), Mon 19, Wed 21, Mon 26 and Wed 28; the series span is the eight pattern dates.

REMAINING_DAYS = (5, 7, 12, 19, 21, 26, 28)
PATTERN_DAYS = (5, 7, 12, 14, 19, 21, 26, 28)
RESTORED = [(at(day, 13) if day == 12 else at(day, 8, 30)) for day in REMAINING_DAYS]
# Criterion 32's two put-back messages (D21), as D.13 renders them with the fixtures.
NOT_PUT_BACK = (
    "We couldn't save the new time here, or undo it in Zoom. Zoom 02's meeting 81234567890 "
    "may still be at the new time in Zoom. Check that meeting in Zoom against this booking's "
    "Classes list, then tell whoever looks after the system."
)
PARTLY_PUT_BACK = (
    "We couldn't save the new time here. We put Zoom 02's meeting 81234567890 back to the "
    "times saved here, but some classes in Zoom may not match this booking. A cancelled class "
    "may have come back, or a class moved on its own may be at the usual time. Check that "
    "meeting in Zoom against this booking's Classes list, then tell whoever looks after the "
    "system."
)


def _error_line(booking, move_error, failure, answered):
    """Criterion 32's neutral ERROR line (D21), exactly. It claims no time for Zoom."""
    return (
        f"Moving {booking.reference}: Zoom meeting {MEETING} doesn't match this database: "
        f"{move_error} (putting it back: {failure}, restoring update answered: {answered})"
    )


DATES_DIFFER = (
    "Zoom scheduled different dates from these classes, so nothing was changed. Tell "
    "whoever looks after the system."
)


def _occurrences(starts, prefix):
    """Zoom's ``occurrences`` for these starts, 180 minutes each, IDs ``{prefix}{index}``."""
    return {
        "id": int(MEETING),
        "join_url": zm.JOIN_URL,
        "start_url": zm.START_URL,
        "duration": 180,
        "occurrences": [
            {
                "occurrence_id": f"{prefix}{index}",
                "start_time": _utc_text(start),
                "duration": 180,
                "status": "available",
            }
            for index, start in enumerate(starts)
        ],
    }


# Zoom's answers along the way.
FORWARD_WRONG = _occurrences([at(day, 9) for day in REMAINING_DAYS[:-1]], "70")  # Wed 28 missing
FORWARD_RIGHT = _occurrences([at(day, 9) for day in PATTERN_DAYS], "70")  # Wed 14 made again
AFTER_RESTORE = _occurrences([at(day, 8, 30) for day in PATTERN_DAYS], "80")  # step 2's GET
FINAL = _occurrences(RESTORED, "90")  # step 4's GET: renumbered, so the IDs must be stored
FINAL_FLATTENED = _occurrences([at(day, 8, 30) for day in REMAINING_DAYS], "90")


class _Zoom:
    """Zoom's meeting endpoint, answering each method from its own script, in order.

    Every call is logged as ``(method, request)``. An answer is ``(status, body)`` or an
    exception to raise; a call with no answer left fails the test, so the calls are exact.
    """

    def __init__(self, http_mock, **scripts):
        self.log = []
        self.scripts = {method: list(scripts.get(method, ())) for method in ("PATCH", "GET")}
        self.scripts["DELETE"] = list(scripts.get("DELETE", [(204, None)] * 4))
        for method in self.scripts:
            http_mock.add_callback(method, zm.meeting_url(MEETING), callback=self._answer(method))

    def _answer(self, method):
        def reply(request):
            self.log.append((method, request))
            assert self.scripts[method], f"unexpected {method} {request.url}"
            answer = self.scripts[method].pop(0)
            if isinstance(answer, Exception):
                return answer
            status, body = answer
            return status, {}, "" if body is None else json.dumps(body)

        return reply

    def methods(self):
        return [method for method, _ in self.log]

    def calls(self, method):
        return [request for logged, request in self.log if logged == method]


def _q(request):
    return {key: values[-1] for key, values in parse_qs(urlsplit(request.url).query).items()}


def _b(request):
    return json.loads(request.body)


def _criterion_32_booking(live, user):
    booking = zl42(live)
    _cancel(booking.occurrences.get(starts_at=at(14, 8, 30)), user)
    mon12 = booking.occurrences.get(starts_at=at(12, 8, 30))
    mon12.starts_at, mon12.ends_at = at(12, 13), at(12, 16)
    mon12.moved_at, mon12.moved_by = FROZEN_NOW, user
    mon12.save()
    HostSlot.objects.filter(occurrence=mon12).delete()
    HostSlot.objects.bulk_create(mon12.new_slots())
    return booking


def _state(booking):
    """Everything about the classes a failed move must leave as it was, IDs aside."""
    booking.refresh_from_db()
    rows = booking.occurrences.order_by("pk").values_list(
        "pk", "starts_at", "ends_at", "moved_at", "moved_by", "cancelled_at"
    )
    slots = sorted(HostSlot.objects.values_list("occurrence_id", "starts_at"))
    return booking.start_time, booking.end_time, list(rows), slots


def _stored_ids(booking):
    return list(
        booking.occurrences.filter(cancelled_at__isnull=True)
        .order_by("starts_at")
        .values_list("zoom_occurrence_id", flat=True)
    )


def _move_to_nine(booking, user):
    return services.move_series(booking.pk, start_time=time(9), end_time=time(12), by=user)


def _assert_the_four_steps(zoom, start=0):
    """Criterion 32's steps from the log's ``start``: PATCH, GET, the Wed 14 DELETE, the
    Mon 12 occurrence PATCH back to 13:00, and the final GET."""
    assert zoom.methods()[start:] == ["PATCH", "GET", "DELETE", "PATCH", "GET"]
    series, _, delete, one, _ = [request for _, request in zoom.log[start:]]
    assert _q(series) == {} and _b(series) == {
        "start_time": "2026-10-05T08:30:00",
        "timezone": "Asia/Colombo",
        "duration": 180,
        "recurrence": {"type": 2, "repeat_interval": 1, "weekly_days": "2,4", "end_times": 8},
    }
    assert _q(delete)["occurrence_id"] == "803"  # Wed 14 Oct, cancelled earlier
    assert _q(one) == {"occurrence_id": "802"}  # Mon 12 Oct, flattened by the series PATCH
    assert _b(one) == {
        "start_time": "2026-10-12T13:00:00",
        "timezone": "Asia/Colombo",
        "duration": 180,
    }


def _one_error(caplog):
    [error] = [record for record in caplog.records if record.levelno >= logging.ERROR]
    text = error.getMessage()
    for secret in ("zoom.us", "pwd", "zak", "RAW-ZOOM-TEXT", *zm.SECRETS):
        assert secret not in text
    return text


def test_a_series_zoom_got_wrong_is_put_back_fully(live, http_mock, it_user):
    """Criterion 32's recorded calls, the DATES_DIFFER message and the stored IDs."""
    booking = _criterion_32_booking(live, it_user)
    before = _state(booking)
    zoom = _Zoom(
        http_mock,
        PATCH=[(204, None)] * 3,
        GET=[(200, FORWARD_WRONG), (200, AFTER_RESTORE), (200, FINAL)],
    )
    result = _move_to_nine(booking, it_user)
    assert (result.outcome, result.message) == (Outcome.PROVIDER_ERROR, DATES_DIFFER)
    assert zoom.methods() == ["PATCH", "GET", "PATCH", "GET", "DELETE", "PATCH", "GET"]
    assert _b(zoom.calls("PATCH")[0])["start_time"] == "2026-10-05T09:00:00"
    _assert_the_four_steps(zoom, start=2)
    assert _state(booking) == before
    assert _stored_ids(booking) == [f"90{index}" for index in range(7)]


STEP_FAILURES = {
    # step 1: the restoring series PATCH is refused
    "1 series patch": (
        {"PATCH": [(204, None), (400, zm.zoom_error(3000))], "GET": [(200, FORWARD_WRONG)]},
        ["PATCH", "GET", "PATCH"],
        "ZoomRejected",
    ),
    # step 2: the read-back fails, or a delete of the cancelled date is refused
    "2 read-back": (
        {"PATCH": [(204, None)] * 2, "GET": [(200, FORWARD_WRONG), (503, None)]},
        ["PATCH", "GET", "PATCH", "GET"],
        "ZoomUnavailable",
    ),
    "2 delete": (
        {
            "PATCH": [(204, None)] * 2,
            "GET": [(200, FORWARD_WRONG), (200, AFTER_RESTORE)],
            "DELETE": [(400, zm.zoom_error(3000))],
        },
        ["PATCH", "GET", "PATCH", "GET", "DELETE"],
        "ZoomRejected",
    ),
    # step 3: the flattened class's own PATCH is refused
    "3 class patch": (
        {
            "PATCH": [(204, None), (204, None), (400, zm.zoom_error(3000))],
            "GET": [(200, FORWARD_WRONG), (200, AFTER_RESTORE)],
        },
        ["PATCH", "GET", "PATCH", "GET", "DELETE", "PATCH"],
        "ZoomRejected",
    ),
    # step 4: the final read-back fails, or doesn't match (Mon 12 still flattened)
    "4 final read-back": (
        {
            "PATCH": [(204, None)] * 3,
            "GET": [(200, FORWARD_WRONG), (200, AFTER_RESTORE), (503, None)],
        },
        ["PATCH", "GET", "PATCH", "GET", "DELETE", "PATCH", "GET"],
        "ZoomUnavailable",
    ),
    "4 mismatch": (
        {
            "PATCH": [(204, None)] * 3,
            "GET": [(200, FORWARD_WRONG), (200, AFTER_RESTORE), (200, FINAL_FLATTENED)],
        },
        ["PATCH", "GET", "PATCH", "GET", "DELETE", "PATCH", "GET"],
        "mismatch",
    ),
}


@pytest.mark.parametrize("step", list(STEP_FAILURES))
def test_a_failure_at_any_step_of_putting_it_back_says_so(live, http_mock, it_user, caplog, step):
    """Criterion 32 (D21): a failed step 1 means no restoring PATCH was answered, so Zoom may
    still be at the new time: MOVE_NOT_PUT_BACK. Any later step failing, or a final check that
    doesn't match, comes after Zoom took the saved times back: MOVE_PARTLY_PUT_BACK. Either
    way, exactly one neutral ERROR line naming the reference, the meeting and the failure."""
    scripts, calls, failure = STEP_FAILURES[step]
    landed = not step.startswith("1 ")
    booking = _criterion_32_booking(live, it_user)
    before = _state(booking)
    zoom = _Zoom(http_mock, **scripts)
    with caplog.at_level(logging.DEBUG, logger="apps.zoom"):
        result = _move_to_nine(booking, it_user)
    message = PARTLY_PUT_BACK if landed else NOT_PUT_BACK
    assert (result.outcome, result.message) == (Outcome.PROVIDER_ERROR, message)
    assert zoom.methods() == calls
    assert _one_error(caplog) == _error_line(
        booking, "_DatesDiffer", failure, "yes" if landed else "no"
    )
    assert _state(booking) == before


@pytest.mark.parametrize("code", [1213, 1205])
def test_a_lock_race_while_putting_it_back_is_retried_once(live, http_mock, it_user, code):
    """Criterion 32 (SF2): a deadlock or a lock-wait timeout in the put-back's own transaction
    is retried, and the retry runs all four steps again."""
    booking = _criterion_32_booking(live, it_user)
    before = _state(booking)
    zoom = _Zoom(
        http_mock,
        PATCH=[(204, None)] * 5,
        GET=[(200, FORWARD_WRONG)] + [(200, AFTER_RESTORE), (200, FINAL)] * 2,
    )
    with _fail_commits(1, OperationalError(code, "Lock race")):
        result = _move_to_nine(booking, it_user)
    assert (result.outcome, result.message) == (Outcome.PROVIDER_ERROR, DATES_DIFFER)
    _assert_the_four_steps(zoom, start=7)
    assert zoom.methods()[2:7] == ["PATCH", "GET", "DELETE", "PATCH", "GET"]
    assert _state(booking) == before
    assert _stored_ids(booking) == [f"90{index}" for index in range(7)]


def test_a_second_lock_race_while_putting_it_back_says_so(live, http_mock, it_user, caplog):
    """Criterion 32 (D21), after step 1 landed: both tries put Zoom back to the saved times
    and only their commits lost, so it's MOVE_PARTLY_PUT_BACK."""
    booking = _criterion_32_booking(live, it_user)
    zoom = _Zoom(
        http_mock,
        PATCH=[(204, None)] * 5,
        GET=[(200, FORWARD_WRONG)] + [(200, AFTER_RESTORE), (200, FINAL)] * 2,
    )
    with (
        _fail_commits(2, OperationalError(1213, "Deadlock found")),
        caplog.at_level(logging.DEBUG, logger="apps.zoom"),
    ):
        result = _move_to_nine(booking, it_user)
    assert result.message == PARTLY_PUT_BACK
    assert zoom.methods().count("DELETE") == 2  # both tries re-deleted Wed 14
    assert _one_error(caplog) == _error_line(booking, "_DatesDiffer", "OperationalError", "yes")


def test_a_second_lock_race_before_any_restoring_update_says_not_put_back(
    live, http_mock, it_user, caplog
):
    """Criterion 32 (D21), the other half: both tries lost their locks before a restoring
    PATCH was sent, so Zoom still has the forward move's times: MOVE_NOT_PUT_BACK."""
    booking = _criterion_32_booking(live, it_user)
    zoom = _Zoom(http_mock, PATCH=[(204, None)], GET=[(200, FORWARD_WRONG)])
    race = OperationalError(1213, "Deadlock found")
    with (
        mock.patch.object(services, "_put_series_back", side_effect=[race, race]) as put_back,
        caplog.at_level(logging.DEBUG, logger="apps.zoom"),
    ):
        result = _move_to_nine(booking, it_user)
    assert result.message == NOT_PUT_BACK
    assert put_back.call_count == 2  # retried once
    assert zoom.methods() == ["PATCH", "GET"]  # the forward move only
    assert _one_error(caplog) == _error_line(booking, "_DatesDiffer", "OperationalError", "no")


def test_putting_it_back_locks_request_then_account_then_classes(live, http_mock, it_user):
    """Criterion 32: the put-back's own locks, in approve()/cancel()'s order, before its PATCH."""
    booking = _criterion_32_booking(live, it_user)
    log = []
    zoom = _Zoom(
        http_mock,
        PATCH=[(204, None)] * 3,
        GET=[(200, FORWARD_WRONG), (200, AFTER_RESTORE), (200, FINAL)],
    )
    zoom.log = _Tee(zoom.log, log)

    def record_sql(execute, sql, params, many, context):
        log.append(("SQL", sql))
        return execute(sql, params, many, context)

    with connection.execute_wrapper(record_sql):
        assert _move_to_nine(booking, it_user).message == DATES_DIFFER
    http = [i for i, (kind, _) in enumerate(log) if kind != "SQL"]
    forward_get, restore_patch = http[1], http[2]

    def first_lock(table, after):
        return next(
            i
            for i, (kind, sql) in enumerate(log)
            if i > after and kind == "SQL" and f"FROM `{table}`" in sql and "FOR UPDATE" in sql
        )

    request_lock = first_lock("zoom_linkrequest", forward_get)
    account_lock = first_lock("zoom_hostaccount", forward_get)
    classes_lock = first_lock("zoom_occurrence", forward_get)
    assert forward_get < request_lock < account_lock < classes_lock < restore_patch


class _Tee(list):
    """A call log that also writes each entry into a shared, ordered log."""

    def __init__(self, own, shared):
        super().__init__(own)
        self.shared = shared

    def append(self, entry):
        super().append(entry)
        self.shared.append(entry)


@contextmanager
def _fail_commits(count, error):
    """Make the next ``count`` transaction commits fail with ``error`` (or, given a list, the
    first with ``error[0]``, the second with ``error[1]``, and so on).

    Like test_cancel_services' ``_fail_the_first_commit``: inside a test's own transaction a
    service's commit is its savepoint's release. Django also releases a savepoint just after
    rolling back to it, which isn't a commit, so a savepoint that was rolled back is let
    through: a failed move (rolled back) never uses up a failure meant for a later commit.
    """
    wrapper = connections["default"]
    real_commit, real_rollback = wrapper.savepoint_commit, wrapper.savepoint_rollback
    rolled_back, failed = set(), []

    def rollback(sid):
        rolled_back.add(sid)
        return real_rollback(sid)

    def commit(sid):
        if sid not in rolled_back and len(failed) < count:
            failed.append(sid)
            raise error[len(failed) - 1] if isinstance(error, list) else error
        return real_commit(sid)

    with (
        mock.patch.object(wrapper, "savepoint_rollback", side_effect=rollback),
        mock.patch.object(wrapper, "savepoint_commit", side_effect=commit),
    ):
        yield


# Criteria 13 and 15 through the same put-back: whatever stopped the series move, the cancelled
# Wed 14 is deleted again, Mon 12 goes back to 13:00, and the message is true afterwards.
FORWARD_TRIGGERS = {
    "dates differ": (
        {
            "PATCH": [(204, None)] * 3,
            "GET": [(200, FORWARD_WRONG), (200, AFTER_RESTORE), (200, FINAL)],
        },
        DATES_DIFFER,
    ),
    "a failed read-back": (
        {"PATCH": [(204, None)] * 3, "GET": [(503, None), (200, AFTER_RESTORE), (200, FINAL)]},
        "We couldn't move it in Zoom: no answer from Zoom. Nothing was changed. "
        "Try again in a few minutes.",
    ),
    "a failed delete": (
        {
            "PATCH": [(204, None)] * 3,
            "GET": [(200, FORWARD_RIGHT), (200, AFTER_RESTORE), (200, FINAL)],
            "DELETE": [(400, zm.zoom_error(3000)), (204, None)],
        },
        f"We couldn't move it in Zoom: Zoom error 3000. Nothing was changed. {LASTING}",
    ),
    "no answer to the move": (
        {
            "PATCH": [requests.exceptions.ReadTimeout(), (204, None), (204, None)],
            "GET": [(200, AFTER_RESTORE), (200, FINAL)],
        },
        "No answer from Zoom, so we put the class back to its old time there to be safe. "
        "Nothing was changed. Try again in a few minutes.",
    ),
}


@pytest.mark.parametrize("trigger", list(FORWARD_TRIGGERS))
def test_every_failed_series_move_is_put_back_the_same_way(live, http_mock, it_user, trigger):
    scripts, message = FORWARD_TRIGGERS[trigger]
    booking = _criterion_32_booking(live, it_user)
    before = _state(booking)
    zoom = _Zoom(http_mock, **scripts)
    result = _move_to_nine(booking, it_user)
    assert (result.outcome, result.message) == (Outcome.PROVIDER_ERROR, message)
    _assert_the_four_steps(zoom, start=len(zoom.log) - 5)
    assert _state(booking) == before
    assert _stored_ids(booking) == [f"90{index}" for index in range(7)]


def test_a_save_failure_after_the_series_move_is_put_back_the_same_way(live, http_mock, it_user):
    """Criterion 15: the move was right in Zoom, then the commit failed twice (a deadlock, then
    its retry's deadlock). Both tries deleted Wed 14; the put-back deletes it again."""
    booking = _criterion_32_booking(live, it_user)
    before = _state(booking)
    zoom = _Zoom(
        http_mock,
        PATCH=[(204, None)] * 4,
        GET=[(200, FORWARD_RIGHT), (200, FORWARD_RIGHT), (200, AFTER_RESTORE), (200, FINAL)],
    )
    with _fail_commits(2, OperationalError(1213, "Deadlock found")):
        result = _move_to_nine(booking, it_user)
    assert (result.outcome, result.message) == (
        Outcome.CONFLICT,
        "Someone else was changing this booking at the same moment. Nothing was changed. "
        "Try again.",
    )
    assert zoom.methods()[:6] == ["PATCH", "GET", "DELETE", "PATCH", "GET", "DELETE"]
    _assert_the_four_steps(zoom, start=6)
    assert _state(booking) == before


def test_any_other_save_failure_puts_the_series_back_then_raises(live, http_mock, it_user):
    booking = _criterion_32_booking(live, it_user)
    before = _state(booking)
    zoom = _Zoom(
        http_mock,
        PATCH=[(204, None)] * 3,
        GET=[(200, FORWARD_RIGHT), (200, AFTER_RESTORE), (200, FINAL)],
    )
    with (
        _fail_commits(1, OperationalError(2013, "Lost connection")),
        pytest.raises(OperationalError),
    ):
        _move_to_nine(booking, it_user)
    assert zoom.methods()[:3] == ["PATCH", "GET", "DELETE"]
    _assert_the_four_steps(zoom, start=3)
    assert _state(booking) == before


def test_no_answer_and_a_failed_series_undo_keeps_criterion_13s_message(live, http_mock, it_user):
    """Criterion 13: the move went unanswered and so did its undo, so Zoom may never have
    changed: 13's own "couldn't check" message, not MOVE_NOT_PUT_BACK."""
    booking = _criterion_32_booking(live, it_user)
    zoom = _Zoom(http_mock, PATCH=[requests.exceptions.ReadTimeout(), (502, None)])
    result = _move_to_nine(booking, it_user)
    assert result.message == services.MOVE_MAYBE_NOT_RESTORED
    assert zoom.methods() == ["PATCH", "PATCH"]


def test_no_answer_then_an_undo_that_stops_halfway_says_not_put_back(
    live, http_mock, it_user, caplog
):
    """Criterion 13, series only: once the undo's PATCH was answered, Zoom has changed. Step 2
    then failed, so it's MOVE_PARTLY_PUT_BACK (D21; the name is kept, per criterion 32)."""
    booking = _criterion_32_booking(live, it_user)
    zoom = _Zoom(
        http_mock, PATCH=[requests.exceptions.ReadTimeout(), (204, None)], GET=[(503, None)]
    )
    with caplog.at_level(logging.DEBUG, logger="apps.zoom"):
        result = _move_to_nine(booking, it_user)
    assert result.message == PARTLY_PUT_BACK
    assert zoom.methods() == ["PATCH", "PATCH", "GET"]
    assert _one_error(caplog) == _error_line(booking, "ZoomUnavailable", "ZoomUnavailable", "yes")


def test_one_class_is_put_back_with_the_locked_rows_id(live, http_mock, it_user):
    """Criterion 32, one class: a single occurrence PATCH, by the locked row's own ID."""
    booking = zl42(live)
    target = wed7(booking)
    zoom = _Zoom(http_mock, PATCH=[requests.exceptions.ReadTimeout(), (204, None)])
    result = move_wed7(booking)
    assert result.message == services.MOVE_MAYBE_RESTORED
    move, restore = zoom.calls("PATCH")
    assert _q(restore) == {"occurrence_id": target.zoom_occurrence_id}
    assert _b(restore)["start_time"] == "2026-10-07T08:30:00"


def test_a_blank_id_is_put_back_by_the_id_the_move_looked_up(live, http_mock, it_user):
    """The review nit: the locked row's ID first; only a blank one falls back to the ID the
    failed attempt looked up, so the undo never addresses the whole weekly meeting."""
    booking = zl42(live)
    target = wed7(booking)
    booking.occurrences.update(zoom_occurrence_id="")
    zoom = _Zoom(
        http_mock,
        PATCH=[requests.exceptions.ReadTimeout(), (204, None)],
        GET=[(200, _occurrences([at(7, 8, 30)], "55"))],
    )
    result = move_wed7(booking)
    assert result.message == services.MOVE_MAYBE_RESTORED
    move, restore = zoom.calls("PATCH")
    assert _q(move) == _q(restore) == {"occurrence_id": "550"}
    target.refresh_from_db()
    assert target.zoom_occurrence_id == ""  # the move's lookup was rolled back with it


# --------------------------------------------------------------------------- 12 certain refusals


@pytest.mark.parametrize(
    ("reply", "message"),
    [
        (
            {"body": requests.exceptions.ConnectionError("refused")},
            "We couldn't move it in Zoom: no answer from Zoom. Nothing was changed. "
            "Try again in a few minutes.",
        ),
        (
            {"body": requests.exceptions.ConnectTimeout()},
            "We couldn't move it in Zoom: no answer from Zoom. Nothing was changed. "
            "Try again in a few minutes.",
        ),
        (
            {"status": 429},
            "We couldn't move it in Zoom: Zoom is busy right now. Nothing was changed. "
            "Try again in a few minutes.",
        ),
        (
            {"status": 401, "json": {}},
            "We couldn't move it in Zoom: Zoom didn't accept this account's connection details. "
            f"Nothing was changed. {LASTING}",
        ),
        (
            {"status": 400, "json": zm.zoom_error(4711)},
            "The Zoom app for Zoom 02 is missing the permission to change meetings. Nothing was "
            "changed. Ask whoever looks after the server to add the scopes listed in the README.",
        ),
        (
            {"status": 404, "json": zm.zoom_error(1001)},
            "We couldn't move it in Zoom: Zoom has no user with this account's sign-in email. "
            f"Nothing was changed. {LASTING}",
        ),
        (
            {"status": 404, "json": zm.zoom_error(3001)},
            f"We couldn't move it in Zoom: Zoom error 3001. Nothing was changed. {LASTING}",
        ),
        (
            {"status": 400, "json": zm.zoom_error(3000)},
            f"We couldn't move it in Zoom: Zoom error 3000. Nothing was changed. {LASTING}",
        ),
    ],
)
def test_zoom_refused_for_certain_rolls_back_with_one_message_per_kind(
    live, http_mock, reply, message
):
    """Criterion 12. The 401 is Zoom's answer to both tries (the one refresh, brief 006)."""
    booking = zl42(live)
    zm.add_token(http_mock, zm.SECOND_TOKEN)
    http_mock.add(responses.PATCH, zm.meeting_url(MEETING), **reply)
    result = move_wed7(booking)
    assert (result.outcome, result.message) == (Outcome.PROVIDER_ERROR, message)
    # Nothing reached Zoom for certain, so nothing is put back.
    assert len(_patches(http_mock)) == (2 if reply.get("status") == 401 else 1)
    _unchanged(booking)
    assert mail.outbox == []


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (
            ProviderError("the fake failed"),
            "We couldn't move it in Zoom: the fake failed. "
            "Nothing was changed. Try again in a few minutes.",
        ),
        (
            ZoomUnavailable(),
            "We couldn't move it in Zoom: no answer from Zoom. Nothing was "
            "changed. Try again in a few minutes.",
        ),
        (
            ZoomBusy(),
            "We couldn't move it in Zoom: Zoom is busy right now. Nothing was changed. "
            "Try again in a few minutes.",
        ),
        (
            ZoomAuthFailed(),
            "We couldn't move it in Zoom: Zoom didn't accept this account's "
            f"connection details. Nothing was changed. {LASTING}",
        ),
        (
            ZoomMissingScope(),
            "The Zoom app for Zoom 02 is missing the permission to change "
            "meetings. Nothing was changed. Ask whoever looks after the server to add the scopes "
            "listed in the README.",
        ),
        (
            ZoomUserNotFound(),
            "We couldn't move it in Zoom: Zoom has no user with this account's "
            f"sign-in email. Nothing was changed. {LASTING}",
        ),
        (
            ZoomRejected(3000),
            f"We couldn't move it in Zoom: Zoom error 3000. Nothing was changed. {LASTING}",
        ),
        (
            ZoomMeetingNotFound(),
            f"We couldn't move it in Zoom: Zoom error 3001. Nothing was changed. {LASTING}",
        ),
        (
            ZoomNotConnected(),
            "We couldn't move it in Zoom: this account isn't connected to "
            f"Zoom. Nothing was changed. {LASTING}",
        ),
        (
            ZoomDailyLimit(),
            "Zoom's daily limit for changing Zoom 02's meetings is used up. "
            "Nothing was changed. Try again after 5:30 am on Tue 29 Sep 2026.",
        ),
    ],
)
def test_the_message_for_each_error_kind(zoom02, error, message):
    """Criterion 12's table, one row per 006 error kind, through the fake provider."""
    booking = zl42(zoom02)
    FakeProvider.update_errors = [error]
    result = move_wed7(booking)
    assert (result.outcome, result.message) == (Outcome.PROVIDER_ERROR, message)
    assert services.move_failed_message(error, "Zoom 02") == message
    _unchanged(booking)


def test_no_move_message_ever_offers_another_account():
    """Criterion 12 (P6, D11): scan every move message, and every message an error makes."""
    kinds = [
        ProviderError("x"),
        ZoomUnavailable(),
        ZoomUnavailable(maybe_done=True),
        ZoomBusy(),
        ZoomAuthFailed(),
        ZoomMissingScope(),
        ZoomUserNotFound(),
        ZoomRejected(3000),
        ZoomMeetingNotFound(),
        ZoomNotConnected(),
        ZoomDailyLimit(),
    ]
    texts = list(services.MOVE_MESSAGES)
    texts += [
        models.MOVE_STARTED,
        models.MOVE_UNCHANGED,
        models.MOVE_IN_PROGRESS,
        models.NOTHING_LEFT_TO_MOVE,
        models.MOVE_CLASS_CANCELLED,
        models.MOVE_SERIES_OFF_PATTERN,
    ]
    for error in kinds:
        texts.append(services.move_failed_message(error, "Zoom 02"))
        texts.append(services.move_lookup_failed_message(error, "Zoom 02"))
    for text in texts:
        assert "another free account" not in text.lower(), text
        assert "choose another free" not in text.lower(), text


# --------------------------------------------------------------------------- 13 maybe done


def test_no_answer_puts_the_class_back_and_says_so(live, http_mock):
    booking = zl42(live)
    target = wed7(booking)
    http_mock.add(responses.PATCH, zm.meeting_url(MEETING), body=requests.exceptions.ReadTimeout())
    http_mock.add(responses.PATCH, zm.meeting_url(MEETING), status=204)
    result = move_wed7(booking)
    assert (result.outcome, result.message) == (
        Outcome.PROVIDER_ERROR,
        "No answer from Zoom, so we put the class back to its old time there to be safe. "
        "Nothing was changed. Try again in a few minutes.",
    )
    move, restore = _patches(http_mock)
    assert zm.query(restore) == {"occurrence_id": target.zoom_occurrence_id}
    assert zm.body(restore)["start_time"] == "2026-10-07T08:30:00"
    _unchanged(booking)


def test_no_answer_and_a_failed_restore_says_trying_again_finishes_it(live, http_mock):
    booking = zl42(live)
    http_mock.add(responses.PATCH, zm.meeting_url(MEETING), status=502)
    http_mock.add(responses.PATCH, zm.meeting_url(MEETING), status=502)
    result = move_wed7(booking)
    assert (result.outcome, result.message) == (
        Outcome.PROVIDER_ERROR,
        "No answer from Zoom, and we couldn't check what it did. Nothing was changed here. Try "
        "again in a few minutes. If the class shows the new time in Zoom, trying again finishes "
        "the move.",
    )
    assert len(_patches(http_mock)) == 2
    _unchanged(booking)


def test_the_restore_sets_the_time_the_database_holds_now(zoom02):
    """Criterion 17a's second half: a restore puts back the winner's time, not the old one."""
    booking = zl42(zoom02)
    assert move_wed7(booking).outcome == Outcome.MOVED  # the winner: Thu 8, 9:00
    target = booking.occurrences.get(starts_at=at(8, 9))
    FakeProvider.update_errors = [ZoomUnavailable(maybe_done=True)]
    result = services.move_class(
        booking.pk,
        target.pk,
        starts_at=at(9, 9),
        ends_at=at(9, 12),
        by=None,
        shown=_shown([target]),
    )
    assert result.message == services.MOVE_MAYBE_RESTORED
    assert [p["starts_at"] for p in FakeProvider.patched] == [at(8, 9), at(8, 9)]


# --------------------------------------------------------------------------- 14 daily limit


def test_the_daily_reset_is_the_next_utc_midnight_in_colombo_time(monkeypatch):
    reset = services.zoom_daily_reset()
    assert models.class_date(reset) == "Tue 29 Sep 2026"
    assert models.class_time(reset) == "5:30 am"
    early = at(29, 2, month=9)
    assert models.class_date(services.zoom_daily_reset(early)) == "Tue 29 Sep 2026"
    monkeypatch.setattr("django.utils.timezone.now", lambda: early)
    assert services.move_failed_message(ZoomDailyLimit(), "Zoom 02").endswith(
        "Try again after 5:30 am on Tue 29 Sep 2026."
    )


# Zoom's two 429 wordings, verbatim from https://developers.zoom.us/docs/api/rate-limits/
# ("Limit Type / HTTP Status / Error Message" table), and the X-RateLimit-Type values the
# page's earlier version named (QPS, Daily-limit).
ZOOM_DAILY_TEXT = (
    "You have reached the maximum daily rate limit for this API. Refer to the response header "
    "for details on when you can make another request."
)
ZOOM_PER_SECOND_TEXT = (
    "You have reached the maximum per-second rate limit for this API. Try again later."
)
DAILY_MESSAGE = (
    "Zoom's daily limit for changing Zoom 02's meetings is used up. Nothing was changed. "
    "Try again after 5:30 am on Tue 29 Sep 2026."
)
BUSY_MESSAGE = (
    "We couldn't move it in Zoom: Zoom is busy right now. Nothing was changed. "
    "Try again in a few minutes."
)


@pytest.mark.parametrize(
    ("reply", "message"),
    [
        # Criterion 14 (D19, amended 2026-10-02; this replaces the earlier
        # ``test_the_live_api_never_claims_a_daily_limit``, which pinned "every 429 is busy").
        ({"json": {"code": 429, "message": ZOOM_DAILY_TEXT}}, DAILY_MESSAGE),
        ({"json": {"code": 429, "message": "DAILY limit reached"}}, DAILY_MESSAGE),
        ({"headers": {"X-RateLimit-Type": "Daily-limit"}, "body": ""}, DAILY_MESSAGE),
        ({"headers": {"x-ratelimit-type": "daily-limit"}, "json": {}}, DAILY_MESSAGE),
        (
            {
                "headers": {"X-RateLimit-Type": "QPS"},
                "json": {"code": 429, "message": ZOOM_PER_SECOND_TEXT},
            },
            BUSY_MESSAGE,
        ),
        ({"body": "<html>Too Many Requests</html>"}, BUSY_MESSAGE),
        ({"body": ""}, BUSY_MESSAGE),
        ({"json": ["daily"]}, BUSY_MESSAGE),
        ({"json": {"code": 429, "message": 7}}, BUSY_MESSAGE),
    ],
    ids=[
        "documented-daily-text",
        "daily-any-case",
        "daily-header",
        "daily-header-any-case",
        "per-second",
        "not-json",
        "empty",
        "json-not-an-object",
        "message-not-text",
    ],
)
def test_a_429_is_the_daily_limit_only_when_zoom_says_daily(live, http_mock, reply, message):
    booking = zl42(live)
    http_mock.add(responses.PATCH, zm.meeting_url(MEETING), status=429, **reply)
    result = move_wed7(booking)
    assert (result.outcome, result.message) == (Outcome.PROVIDER_ERROR, message)
    assert len(_patches(http_mock)) == 1  # refused for certain: nothing to put back
    _unchanged(booking)


def test_daily_in_any_other_refusal_isnt_the_daily_limit(live, http_mock):
    """The rule is 429-only: a 400 that happens to say "daily" is Zoom's plain refusal."""
    booking = zl42(live)
    http_mock.add(
        responses.PATCH,
        zm.meeting_url(MEETING),
        status=400,
        headers={"X-RateLimit-Type": "Daily-limit"},
        json={"code": 300, "message": "The daily schedule is invalid."},
    )
    result = move_wed7(booking)
    assert result.message == (
        f"We couldn't move it in Zoom: Zoom error 300. Nothing was changed. {LASTING}"
    )


def test_zooms_daily_text_is_never_logged_or_kept(live, http_mock, caplog):
    """Criterion 14: Zoom's wording only picks the error; no log record or message holds it."""
    booking = zl42(live)
    marker = f"{ZOOM_DAILY_TEXT} RAW-ZOOM-TEXT-5521"
    http_mock.add(
        responses.PATCH,
        zm.meeting_url(MEETING),
        status=429,
        headers={"X-RateLimit-Type": "Daily-limit-RAW-HEADER-8812"},
        json={"code": 429, "message": marker},
    )
    with caplog.at_level(logging.DEBUG):
        result = move_wed7(booking)
    assert result.message == DAILY_MESSAGE
    logged = "\n".join(record.getMessage() for record in caplog.records)
    for text in (logged, result.message, str(ZoomDailyLimit())):
        assert "RAW-ZOOM-TEXT" not in text and "RAW-HEADER" not in text
        assert ZOOM_DAILY_TEXT not in text and "maximum daily rate limit" not in text
    assert "ZoomDailyLimit" in logged  # the error class, and only that


# --------------------------------------------------------------------------- 15 saving fails


def test_a_deadlock_after_zoom_changed_it_is_retried_and_finishes(live, http_mock):
    booking = zl42(live)
    http_mock.add(responses.PATCH, zm.meeting_url(MEETING), status=204)
    with _fail_the_first_commit(OperationalError(1213, "Deadlock found")):
        result = move_wed7(booking)
    assert result.outcome == Outcome.MOVED
    assert [zm.body(c)["start_time"] for c in _patches(http_mock)] == [
        "2026-10-08T09:00:00",
        "2026-10-08T09:00:00",
    ]
    assert booking.occurrences.filter(starts_at=at(8, 9)).exists()


def test_any_other_failure_after_zoom_changed_it_puts_zoom_back(live, http_mock):
    booking = zl42(live)
    http_mock.add(responses.PATCH, zm.meeting_url(MEETING), status=204)
    with (
        _fail_the_first_commit(OperationalError(2013, "Lost connection")),
        pytest.raises(OperationalError),
    ):
        move_wed7(booking)
    move, restore = _patches(http_mock)
    assert zm.body(restore)["start_time"] == "2026-10-07T08:30:00"
    _unchanged(booking)


def test_a_failure_after_zoom_changed_it_and_a_failed_restore(live, http_mock, caplog):
    booking = zl42(live)
    http_mock.add(responses.PATCH, zm.meeting_url(MEETING), status=204)
    http_mock.add(responses.PATCH, zm.meeting_url(MEETING), status=503)
    with (
        _fail_the_first_commit(OperationalError(2013, "Lost connection")),
        caplog.at_level(logging.DEBUG, logger="apps.zoom"),
    ):
        result = move_wed7(booking)
    assert result.message == NOT_PUT_BACK  # criterion 32: one class, the undo refused
    assert _one_error(caplog) == _error_line(booking, "OperationalError", "ZoomUnavailable", "no")
    _unchanged(booking)


@pytest.mark.parametrize(
    "error",
    [OperationalError(2013, "Lost connection"), OperationalError(1213, "Deadlock found")],
    ids=["lost connection", "deadlock"],
)
def test_one_class_undone_then_its_own_transaction_failing_counts_as_done(
    live, http_mock, caplog, error
):
    """Criterion 32's one-class edge (D21). The move committed nothing (both tries lost a lock
    race); its undo PATCH was answered, so Zoom has the saved time again; then the put-back's
    own, write-free transaction failed. Zoom matches this database, so that's done: the move's
    normal message, no ERROR line, no second undo PATCH, and a WARNING with the reference and
    the error class."""
    booking = zl42(live)
    http_mock.add(responses.PATCH, zm.meeting_url(MEETING), status=204)
    with (
        _fail_commits(3, [OperationalError(1213, "Deadlock found")] * 2 + [error]),
        caplog.at_level(logging.DEBUG, logger="apps.zoom"),
    ):
        result = move_wed7(booking)
    assert (result.outcome, result.message) == (
        Outcome.CONFLICT,
        services.MOVING_AT_THE_SAME_MOMENT,
    )
    move, retry, restore = _patches(http_mock)
    assert zm.body(restore)["start_time"] == "2026-10-07T08:30:00"
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert (
        f"Put {booking.reference} back in Zoom, but its own transaction then failed: "
        "OperationalError" in warnings
    )
    _unchanged(booking)


def test_the_error_line_is_neutral_and_holds_nothing_from_zoom(live, http_mock, caplog):
    """Criterion 32 (D21): the one ERROR line never says what time Zoom has, and holds no link,
    token, secret or any of Zoom's own text, even when Zoom's refusal carried some."""
    booking = zl42(live)
    http_mock.add(responses.PATCH, zm.meeting_url(MEETING), status=204)
    http_mock.add(responses.PATCH, zm.meeting_url(MEETING), status=400, json=zm.zoom_error(3000))
    with (
        _fail_the_first_commit(OperationalError(2013, "Lost connection")),
        caplog.at_level(logging.DEBUG),
    ):
        result = move_wed7(booking)
    assert result.message == NOT_PUT_BACK
    text = _one_error(caplog)
    assert text == _error_line(booking, "OperationalError", "ZoomRejected", "no")
    assert "new time" not in text and "has the" not in text and "http" not in text
    logged = "\n".join(record.getMessage() for record in caplog.records)
    for leak in ("RAW-ZOOM-TEXT", "zoom.us", *zm.SECRETS):
        assert leak not in logged


UNEXPECTED_TEXT = "RAW-ZOOM-TEXT unexpected detail 7731"


def _fail_after_landing():
    """``_restoring_update`` that lets the restoring PATCH reach Zoom, then raises."""
    real = services._restoring_update

    def update_then_fail(back, update, **kwargs):
        real(back, update, **kwargs)
        raise RuntimeError(UNEXPECTED_TEXT)

    return mock.patch.object(services, "_restoring_update", side_effect=update_then_fail)


def _no_unexpected_text(caplog):
    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert "unexpected detail" not in logged and "7731" not in logged


@pytest.mark.parametrize("landed", [False, True], ids=["before it lands", "after it lands"])
def test_an_unexpected_error_while_putting_a_series_back_still_says_so(
    live, http_mock, it_user, caplog, landed
):
    """Criterion 32 (review round 2, nit): a ``RuntimeError`` inside the put-back, before or
    after a restoring PATCH lands, is caught: exactly one neutral ERROR line with its class
    name only, the message for the current ``landed``, and the move's own error (Zoom's dates
    differed) is still the one named."""
    booking = _criterion_32_booking(live, it_user)
    before = _state(booking)
    zoom = _Zoom(http_mock, PATCH=[(204, None)] * 2, GET=[(200, FORWARD_WRONG)])
    failing = (
        _fail_after_landing()
        if landed
        else mock.patch.object(
            services, "_put_series_back", side_effect=RuntimeError(UNEXPECTED_TEXT)
        )
    )
    with failing, caplog.at_level(logging.DEBUG):
        result = _move_to_nine(booking, it_user)
    message = PARTLY_PUT_BACK if landed else NOT_PUT_BACK
    assert (result.outcome, result.message) == (Outcome.PROVIDER_ERROR, message)
    assert zoom.methods() == (["PATCH", "GET", "PATCH"] if landed else ["PATCH", "GET"])
    assert _one_error(caplog) == _error_line(
        booking, "_DatesDiffer", "RuntimeError", "yes" if landed else "no"
    )
    _no_unexpected_text(caplog)
    assert _state(booking) == before


def test_an_unexpected_error_before_a_one_class_undo_lands_keeps_the_moves_error(
    live, http_mock, caplog
):
    """Criterion 32's catch-all, one class: the move's commit failed after Zoom took the new
    time, then the put-back raised before its PATCH. The move's own error is the one named, and
    the put-back's never replaces it (it used to escape instead)."""
    booking = zl42(live)
    http_mock.add(responses.PATCH, zm.meeting_url(MEETING), status=204)
    with (
        _fail_the_first_commit(OperationalError(2013, "Lost connection")),
        mock.patch.object(
            services, "_put_one_class_back", side_effect=RuntimeError(UNEXPECTED_TEXT)
        ),
        caplog.at_level(logging.DEBUG),
    ):
        result = move_wed7(booking)
    assert result.message == NOT_PUT_BACK
    assert len(_patches(http_mock)) == 1  # the forward move only
    assert _one_error(caplog) == _error_line(booking, "OperationalError", "RuntimeError", "no")
    _no_unexpected_text(caplog)
    _unchanged(booking)


def test_an_unexpected_error_after_a_one_class_undo_lands_counts_as_done(live, http_mock, caplog):
    """Criterion 32's one-class edge, through the catch-all: the undo PATCH was answered, so
    Zoom matches this database whatever failed after it. Done: no ERROR line, a WARNING with
    the class name, and the move's own exception is the one raised, not the RuntimeError."""
    booking = zl42(live)
    http_mock.add(responses.PATCH, zm.meeting_url(MEETING), status=204)
    with (
        _fail_the_first_commit(OperationalError(2013, "Lost connection")),
        _fail_after_landing(),
        caplog.at_level(logging.DEBUG),
        pytest.raises(OperationalError),
    ):
        move_wed7(booking)
    move, restore = _patches(http_mock)
    assert zm.body(restore)["start_time"] == "2026-10-07T08:30:00"
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert (
        f"Put {booking.reference} back in Zoom, but its own transaction then failed: "
        "RuntimeError" in warnings
    )
    _no_unexpected_text(caplog)
    _unchanged(booking)


def test_the_two_put_back_messages_are_pinned():
    """Criterion 32's texts (D21), rendered with the fixtures as D.13 renders them, and both
    in MOVE_MESSAGES, so criterion 12's "no other account" scan covers them."""
    fixtures = {"label": "Zoom 02", "meeting_id": MEETING}
    assert services.MOVE_NOT_PUT_BACK.format(**fixtures) == (
        "We couldn't save the new time here, or undo it in Zoom. Zoom 02's meeting 81234567890 "
        "may still be at the new time in Zoom. Check that meeting in Zoom against this "
        "booking's Classes list, then tell whoever looks after the system."
    )
    assert services.MOVE_PARTLY_PUT_BACK.format(**fixtures) == (
        "We couldn't save the new time here. We put Zoom 02's meeting 81234567890 back to the "
        "times saved here, but some classes in Zoom may not match this booking. A cancelled "
        "class may have come back, or a class moved on its own may be at the usual time. Check "
        "that meeting in Zoom against this booking's Classes list, then tell whoever looks "
        "after the system."
    )
    assert services.MOVE_NOT_PUT_BACK in services.MOVE_MESSAGES
    assert services.MOVE_PARTLY_PUT_BACK in services.MOVE_MESSAGES


def test_a_lock_race_before_zoom_changes_nothing(zoom02):
    booking = zl42(zoom02)
    error = OperationalError(1205, "Lock wait timeout exceeded")
    with mock.patch.object(HostSlot.objects, "filter", side_effect=error):
        result = move_wed7(booking)
    assert (result.outcome, result.message) == (
        Outcome.CONFLICT,
        "Someone else was changing this booking at the same moment. Nothing was changed. "
        "Try again.",
    )
    assert FakeProvider.patched == []


# --------------------------------------------------------------------------- 16 the flashes


def _moved(booking, series, count):
    classes = list(booking.occurrences.all())[:count]
    moves = [MovedClass(o.starts_at, o.ends_at, o) for o in classes]
    return MoveResult(Outcome.MOVED, "", booking, moves, series)


def test_the_series_success_messages(zoom02):
    booking = zl42(zoom02)
    move = services.move_series(booking.pk, start_time=time(9), end_time=time(12), by=None)
    assert services.moved_message(move, emailed=True, checks_zoom=True) == (
        levels.SUCCESS,
        "Changed the time of 8 classes to 9:00 am to 12:00 pm. We emailed nimal@example.com.",
    )
    assert services.moved_message(_moved(booking, True, 1), emailed=True, checks_zoom=True)[
        1
    ].startswith("Changed the time of 1 class to 9:00 am to 12:00 pm.")
    assert services.moved_message(move, emailed=False, checks_zoom=True) == (
        levels.WARNING,
        "Moved, but the email to nimal@example.com didn't send. Tell them the new times yourself.",
    )
    assert services.moved_message(move, emailed=True, checks_zoom=False)[1].endswith(
        "We emailed nimal@example.com. This system can't reach Zoom: change it in Zoom too."
    )


def test_the_one_class_success_message(zoom02):
    booking = zl42(zoom02)
    result = move_wed7(booking, at(6, 9), at(6, 12))
    assert services.moved_message(result, emailed=True, checks_zoom=True) == (
        levels.SUCCESS,
        "Moved the class to Tue 6 Oct 2026, 9:00 am to 12:00 pm. We emailed nimal@example.com.",
    )


def test_the_manual_provider_changes_nothing_in_zoom_and_still_moves(zoom02, http_mock):
    booking = zl42(zoom02)
    result = move_wed7(booking, at(7, 13), at(7, 14), provider=ManualProvider())
    assert result.outcome == Outcome.MOVED
    assert len(http_mock.calls) == 0 and FakeProvider.patched == []
    assert FakeProvider.busy_calls == []
    series = services.move_series(
        booking.pk, start_time=time(9), end_time=time(12), by=None, provider=ManualProvider()
    )
    assert series.outcome == Outcome.MOVED


def test_the_manual_provider_still_checks_the_database(zoom02):
    booking = zl42(zoom02)
    result = move_wed7(booking, at(5, 8, 30), at(5, 9), provider=ManualProvider())
    assert result.outcome == Outcome.CONFLICT


# --------------------------------------------------------------------------- 17a and 30 stale pages


def _shown(classes):
    """What a move page's ``shown`` reads back as, for ``classes`` as they are now."""
    return services.read_move_shown(LinkRequest.move_fingerprint(classes))


# Criterion 29, 1a and 1b, rendered with the fixtures exactly as D.12 gives them.
MOVED_1A = (
    "Someone else moved this class a moment ago. It's now Thu 8 Oct 2026, 9:00 am to 12:00 pm. "
    "We didn't make your change. If it still needs to move, check the time in the form and press "
    "the button again."
)
CHANGED_1B = (
    "Someone else changed the time of the remaining classes a moment ago. They're now 9:00 am to "
    "12:00 pm. We didn't make your change. If they still need a different time, check the times "
    "in the form and press the button again."
)


def test_a_class_moved_since_the_page_was_shown_isnt_moved_again(zoom02):
    booking = zl42(zoom02)
    target = wed7(booking)
    shown = _shown([target])  # the page, before the other move
    assert move_wed7(booking).outcome == Outcome.MOVED
    result = services.move_class(
        booking.pk, target.pk, starts_at=at(9, 9), ends_at=at(9, 12), by=None, shown=shown
    )
    assert (result.outcome, result.message) == (Outcome.CONFLICT, MOVED_1A)
    assert len(FakeProvider.patched) == 1
    # Refused before the Zoom lookup too: only the first move asked Zoom.
    assert len(FakeProvider.busy_calls) == 1


def test_a_one_class_page_for_another_class_is_refused(zoom02):
    booking = zl42(zoom02)
    other = booking.occurrences.get(starts_at=at(12, 8, 30))
    result = services.move_class(
        booking.pk,
        wed7(booking).pk,
        starts_at=at(8, 9),
        ends_at=at(8, 12),
        by=None,
        shown=_shown([other]),
    )
    assert result.outcome == Outcome.CONFLICT
    assert FakeProvider.patched == [] and FakeProvider.busy_calls == []


def test_a_series_changed_since_the_page_was_shown_isnt_changed_again(zoom02):
    booking = zl42(zoom02)
    shown = _shown(booking.remaining_classes())
    services.move_series(booking.pk, start_time=time(9), end_time=time(12), by=None)
    result = services.move_series(
        booking.pk, start_time=time(13), end_time=time(14), by=None, shown=shown
    )
    assert (result.outcome, result.message) == (Outcome.CONFLICT, CHANGED_1B)
    assert len(FakeProvider.patched) == 1 and len(FakeProvider.busy_calls) == 1


def test_a_series_is_refused_when_one_listed_class_moved(zoom02):
    booking = zl42(zoom02)
    shown = _shown(booking.remaining_classes())
    wed14 = booking.occurrences.get(starts_at=at(14, 8, 30))
    services.move_class(booking.pk, wed14.pk, starts_at=at(14, 13), ends_at=at(14, 14), by=None)
    result = services.move_series(
        booking.pk, start_time=time(9), end_time=time(12), by=None, shown=shown
    )
    assert result.outcome == Outcome.CONFLICT
    assert result.message.startswith("Someone else changed the time of the remaining classes")
    assert len(FakeProvider.patched) == 1


def test_a_series_leaves_out_a_class_cancelled_since_the_page_was_shown(zoom02, it_user):
    booking = zl42(zoom02)
    shown = _shown(booking.remaining_classes())
    wed14 = booking.occurrences.get(starts_at=at(14, 8, 30))
    services.cancel(booking.pk, occurrence_id=wed14.pk, by=it_user, reason="Closed.")
    result = services.move_series(
        booking.pk, start_time=time(9), end_time=time(12), by=None, shown=shown
    )
    assert result.outcome == Outcome.MOVED, result.message
    assert wed14.pk not in [move.occurrence.pk for move in result.moves]
    assert len(result.moves) == 7


def test_the_shown_value_reads_back_only_when_signed_for_a_move(zoom02):
    from django.core import signing

    target = wed7(zl42(zoom02))
    token = LinkRequest.move_fingerprint([target])
    assert services.read_move_shown(token) == {
        target.pk: (int(at(7, 8, 30).timestamp()), int(at(7, 11, 30).timestamp()))
    }
    for bad in (
        None,
        "",
        token[:-1] + ("A" if token[-1] != "A" else "B"),
        signing.dumps([[target.pk, 1, 2]], salt="apps.zoom.start"),
        signing.dumps("text", salt="apps.zoom.move-shown"),
        signing.dumps([[1, 2]], salt="apps.zoom.move-shown"),
    ):
        with pytest.raises(signing.BadSignature):
            services.read_move_shown(bad)


def test_the_pinned_race_messages(zoom02):
    """Criterion 29's texts 1a, 1b and 3, exactly (D.12)."""
    assert services.MOVED_A_MOMENT_AGO == (
        "Someone else moved this class a moment ago. It's now {when}. We didn't make your "
        "change. If it still needs to move, check the time in the form and press the button "
        "again."
    )
    assert services.TIMES_CHANGED_A_MOMENT_AGO == (
        "Someone else changed the time of the remaining classes a moment ago. They're now "
        "{times}. We didn't make your change. If they still need a different time, check the "
        "times in the form and press the button again."
    )
    assert services.MOVING_AT_THE_SAME_MOMENT == (
        "Someone else was changing this booking at the same moment. Nothing was changed. Try again."
    )
    assert services.MOVE_PAGE_OUT_OF_DATE == (
        "This page is out of date. Reload it, check the times, then try again."
    )
    moved = wed7(zl42(zoom02))
    moved.starts_at, moved.ends_at = at(8, 9), at(8, 12)
    assert services.MOVED_A_MOMENT_AGO.format(when=moved) == MOVED_1A
    assert services.TIMES_CHANGED_A_MOMENT_AGO.format(times="9:00 am to 12:00 pm") == CHANGED_1B


# --------------------------------------------------------------------------- 18 the email


def _email(booking, result, settings=None):
    assert result.outcome == Outcome.MOVED
    assert services.send_moved_email(_request(), result.link_request, result.moves)
    [message] = mail.outbox
    assert message.to == ["nimal@example.com"] and message.cc == [] and message.bcc == []
    assert getattr(message, "alternatives", []) == []
    return message


def _assert_no_secrets(text, booking):
    for secret in (booking.join_url, booking.passcode, "/zoom/start/", "8421973", "http"):
        assert secret not in text


def test_the_moved_email_for_one_class(zoom02):
    booking = zl42(zoom02)
    message = _email(booking, move_wed7(booking))
    assert message.subject == f"Class times changed: {booking.reference} Grade 11 Physics"
    assert (
        "Was: Wed 7 Oct 2026, 8:30 am to 11:30 am\nNow: Thu 8 Oct 2026, 9:00 am to 12:00 pm\n"
        in message.body
    )
    assert (
        "Your Zoom link and start link stay the same. The start link follows the new times."
        in message.body
    )
    _assert_no_secrets(message.body, booking)


def test_the_moved_email_for_a_series_has_a_pair_per_class(zoom02):
    booking = zl42(zoom02)
    result = services.move_series(booking.pk, start_time=time(9), end_time=time(12), by=None)
    body = _email(booking, result).body
    assert body.count("Was: ") == 8 and body.count("Now: ") == 8
    assert (
        "Now: Mon 5 Oct 2026, 9:00 am to 12:00 pm\n\n"
        "Was: Wed 7 Oct 2026, 8:30 am to 11:30 am\n"
        "Now: Wed 7 Oct 2026, 9:00 am to 12:00 pm\n"
    ) in body
    _assert_no_secrets(body, booking)


def test_the_moved_email_with_the_manual_provider_mentions_no_start_link(zoom02, settings):
    booking = zl42(zoom02)
    result = move_wed7(booking, provider=ManualProvider())
    settings.ZOOM_PROVIDER = "manual"
    body = _email(booking, result).body
    assert "Your Zoom link stays the same." in body
    assert "start link" not in body.lower()


# --------------------------------------------------------------------------- 19 start link


def test_the_start_link_follows_the_moved_class(zoom02):
    booking = zl42(zoom02)
    move_wed7(booking)
    booking = LinkRequest.objects.get(pk=booking.pk)
    state, occurrence = booking.start_state(at(8, 8, 30))
    assert state == "ready" and occurrence.starts_at == at(8, 9)
    state, occurrence = booking.start_state(at(7, 8))
    assert state != "ready"


def test_the_fake_provider_reads_a_series_back_as_zoom_would(zoom02):
    provider = FakeProvider()
    provider.update_series(
        host_account=zoom02,
        meeting_id="1",
        starts_at=at(7, 9),
        ends_at=at(7, 12),
        weekdays="1,3",
        count=3,
    )
    found = provider.meeting_snapshot(host_account=zoom02, meeting_id="1")
    assert [(item.starts_at, item.ends_at) for item in found] == [
        (at(7, 9), at(7, 12)),
        (at(12, 9), at(12, 12)),
        (at(14, 9), at(14, 12)),
    ]
    # An occurrence update moves that class there, keeping its ID; a delete removes it.
    provider.update_occurrence(
        host_account=zoom02,
        meeting_id="1",
        occurrence_id=found[1].occurrence_id,
        starts_at=at(12, 13),
        ends_at=at(12, 16),
    )
    provider.delete_meeting(
        host_account=zoom02, meeting_id="1", occurrence_id=found[2].occurrence_id
    )
    assert provider.meeting_snapshot(host_account=zoom02, meeting_id="1") == (
        found[0],
        (at(12, 13), at(12, 16), found[1].occurrence_id),
    )
