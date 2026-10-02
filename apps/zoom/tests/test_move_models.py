"""Brief 012, the model layer: the ``moved_at`` / ``moved_by`` fields, the move rules and their
pinned copy, "remaining classes" as one definition, the series helpers and the clash query
(criteria 1, 2, 3 and 7's database side). No views, no services.

ZL-0042 is weekly, Mon and Wed, 5-28 Oct 2026, 8:30-11:30 (8 classes), booked on Zoom 02; the
frozen now is Mon 28 Sep 2026, 10:00 Colombo.
"""

from datetime import date, datetime, time

import pytest
from django.core.exceptions import NON_FIELD_ERRORS
from django.db import models

from apps.zoom.models import (
    DATE_PASSED,
    DATE_TOO_FAR,
    END_BEFORE_START,
    END_SAME_DAY,
    MOVE_CLASS_CANCELLED,
    MOVE_STARTED,
    MOVE_UNCHANGED,
    NOTHING_LEFT_TO_MOVE,
    TIME_STEP,
    LinkRequest,
    Occurrence,
)

from .conftest import COLOMBO, booked_on, make_account, make_request

pytestmark = pytest.mark.django_db


def at(month, day, hour, minute=0, year=2026):
    return datetime(year, month, day, hour, minute, tzinfo=COLOMBO)


@pytest.fixture
def zoom02(db):
    return make_account("Zoom 02", sort_order=2)


def zl42(account):
    return booked_on(
        make_request(
            weekdays="1,3",
            first_date=date(2026, 10, 5),
            last_date=date(2026, 10, 28),
            class_name="Grade 11 Physics",
        ),
        account,
    )


def wed7(booking):
    return booking.occurrences.get(starts_at=at(10, 7, 8, 30))


# --------------------------------------------------------------------------- 1 fields


def test_the_moved_fields_are_optional_and_protect_the_user():
    moved_at = Occurrence._meta.get_field("moved_at")
    moved_by = Occurrence._meta.get_field("moved_by")
    assert moved_at.null and moved_at.blank
    assert moved_by.null and moved_by.blank
    assert moved_by.remote_field.on_delete is models.PROTECT
    assert moved_by.remote_field.related_name == "+"
    assert moved_at.help_text and moved_by.help_text


def test_a_new_class_has_not_been_moved(zoom02):
    occurrence = wed7(zl42(zoom02))
    assert occurrence.moved_at is None and occurrence.moved_by is None


# --------------------------------------------------------------------------- remaining classes


def test_remaining_classes_is_the_one_definition(zoom02):
    """The planner's rename: 011's ``cancellable_classes`` is now ``remaining_classes``."""
    assert not hasattr(LinkRequest, "cancellable_classes")
    booking = zl42(zoom02)
    now = at(10, 7, 9)  # Mon 5 held, Wed 7 in progress
    remaining = booking.remaining_classes(now)
    assert [o.starts_at for o in remaining] == [
        o.starts_at for o in booking.occurrences.filter(starts_at__gt=now)
    ]
    assert all(o.can_be_moved(now) and o.can_be_cancelled(now) for o in remaining)


# --------------------------------------------------------------------------- 2 one class


def test_a_valid_move_has_no_errors(zoom02):
    assert wed7(zl42(zoom02)).move_errors(starts_at=at(10, 8, 9), ends_at=at(10, 8, 12)) == {}


@pytest.mark.parametrize(
    ("starts_at", "ends_at", "expected"),
    [
        (at(10, 8, 9, 2), at(10, 8, 12), {"start_time": TIME_STEP}),
        (at(10, 8, 9), at(10, 8, 12, 1), {"end_time": TIME_STEP}),
        (at(10, 8, 12), at(10, 8, 9), {"end_time": END_BEFORE_START}),
        (at(10, 8, 12), at(10, 8, 12), {"end_time": END_BEFORE_START}),
        (at(10, 8, 23), at(10, 9, 0, 30), {"end_time": END_SAME_DAY}),
        (at(9, 28, 9), at(9, 28, 9, 30), {"date": DATE_PASSED}),
        (at(9, 28, 10), at(9, 28, 11), {"date": DATE_PASSED}),
        (at(9, 29, 8, year=2027), at(9, 29, 9, year=2027), {"date": DATE_TOO_FAR}),
        (at(10, 7, 8, 30), at(10, 7, 11, 30), {NON_FIELD_ERRORS: MOVE_UNCHANGED}),
    ],
)
def test_the_rules_for_one_class_and_their_pinned_copy(zoom02, starts_at, ends_at, expected):
    assert wed7(zl42(zoom02)).move_errors(starts_at=starts_at, ends_at=ends_at) == expected


def test_the_last_date_a_year_ahead_is_still_allowed(zoom02):
    occurrence = wed7(zl42(zoom02))
    starts_at, ends_at = at(9, 28, 8, year=2027), at(9, 28, 9, year=2027)
    assert occurrence.move_errors(starts_at=starts_at, ends_at=ends_at) == {}


def test_the_pinned_one_class_messages():
    assert MOVE_STARTED == "That class has already started, so it can't be moved."
    assert MOVE_UNCHANGED == "That's the time it's already booked for. Choose a different time."
    assert MOVE_CLASS_CANCELLED == "That class was cancelled."


def test_a_class_that_has_started_cant_be_moved(zoom02):
    occurrence = wed7(zl42(zoom02))
    now = at(10, 7, 8, 30)
    assert occurrence.move_blocked_message(now) == MOVE_STARTED
    errors = occurrence.move_errors(starts_at=at(10, 8, 9), ends_at=at(10, 8, 12), now=now)
    assert errors == {NON_FIELD_ERRORS: MOVE_STARTED}


def test_a_cancelled_class_cant_be_moved(zoom02, it_user):
    occurrence = wed7(zl42(zoom02))
    occurrence.cancelled_at, occurrence.cancelled_by, occurrence.cancel_reason = (
        at(9, 28, 9),
        it_user,
        "Closed.",
    )
    occurrence.save()
    assert occurrence.move_blocked_message() == MOVE_CLASS_CANCELLED
    assert not occurrence.can_be_moved()


# --------------------------------------------------------------------------- 2 the series


def test_a_valid_series_move_has_no_errors_and_keeps_each_date(zoom02):
    booking = zl42(zoom02)
    assert booking.series_move_errors(start_time=time(9), end_time=time(12)) == {}
    moves = booking.series_new_times(time(9), time(12))
    assert len(moves) == 8
    for occurrence, start, end in moves:
        assert start.date() == occurrence.starts_at.astimezone(COLOMBO).date()
        assert (start.time(), end.time()) == (time(9), time(12))


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (time(9, 2), time(12), {"start_time": TIME_STEP}),
        (time(9), time(12, 3), {"end_time": TIME_STEP}),
        (time(12), time(9), {"end_time": END_BEFORE_START}),
        (time(8, 30), time(11, 30), {NON_FIELD_ERRORS: MOVE_UNCHANGED}),
    ],
)
def test_the_series_rules_and_their_pinned_copy(zoom02, start, end, expected):
    assert zl42(zoom02).series_move_errors(start_time=start, end_time=end) == expected


def test_a_series_whose_first_remaining_class_would_start_in_the_past(zoom02):
    """At 7:00 on Wed 7 the remaining classes start with Wed 7; 6:30 has passed."""
    errors = zl42(zoom02).series_move_errors(
        start_time=time(6, 30), end_time=time(9), now=at(10, 7, 7)
    )
    assert errors == {"start_time": DATE_PASSED}


def test_a_class_in_progress_blocks_the_series(zoom02):
    booking = zl42(zoom02)
    now = at(10, 5, 9)
    message = (
        "Mon 5 Oct 2026, 8:30 am to 11:30 am is in progress. Change the time of the remaining "
        "classes after it ends at 11:30 am."
    )
    assert booking.series_move_blocked_message(now) == message
    assert booking.series_move_errors(start_time=time(9), end_time=time(12), now=now) == {
        NON_FIELD_ERRORS: message
    }
    assert booking.can_move_series(now) is False


def test_no_remaining_classes_blocks_the_series(zoom02):
    booking = zl42(zoom02)
    now = at(10, 28, 12)
    assert NOTHING_LEFT_TO_MOVE == "There are no classes left to change in this booking."
    assert booking.series_move_blocked_message(now) == NOTHING_LEFT_TO_MOVE
    assert booking.can_move_series(now) is False


def test_a_one_off_or_waiting_booking_has_no_series(zoom02):
    one_off = booked_on(make_request(first_date=date(2026, 10, 5)), zoom02, meeting_id="1")
    waiting = make_request(weekdays="1", first_date=date(2026, 11, 2), last_date=date(2026, 11, 9))
    assert one_off.series_move_blocked_message() == NOTHING_LEFT_TO_MOVE
    assert waiting.series_move_blocked_message() == NOTHING_LEFT_TO_MOVE


def test_a_class_moved_to_another_day_blocks_the_series(zoom02):
    """Zoom's series can only hold the pattern's days, so the classes can't move together."""
    booking = zl42(zoom02)
    occurrence = wed7(booking)
    occurrence.starts_at, occurrence.ends_at = at(10, 8, 8, 30), at(10, 8, 11, 30)
    occurrence.save()
    # Criterion 29, message 2, exactly as D.12 renders it.
    assert booking.series_move_blocked_message() == (
        "The class now on Thu 8 Oct 2026, 8:30 am to 11:30 am was moved to a different day, so "
        "the remaining classes can't be changed together. Move each class on its own instead, "
        "with Move this class."
    )
    # Criterion 31: the detail's note is the same sentence, and the series box has no button.
    assert booking.series_move_blocked_note() == booking.series_move_blocked_message()
    assert booking.can_move_series() is False


def test_the_pinned_messages_2_and_4():
    """Criterion 29: messages 2 (replaced, D.12) and 4 (approved as written)."""
    from apps.zoom.models import MOVE_SERIES_OFF_PATTERN

    assert MOVE_SERIES_OFF_PATTERN == (
        "The class now on {occurrence} was moved to a different day, so the remaining classes "
        "can't be changed together. Move each class on its own instead, with Move this class."
    )
    assert END_SAME_DAY == "The class must end on the same day it starts. Check the end time."


def test_the_blocked_note_is_only_for_a_moved_day(zoom02):
    """Criterion 31: ``None`` when nothing blocks, or when it's in progress or nothing's left."""
    booking = zl42(zoom02)
    assert booking.series_move_blocked_note() is None
    occurrence = wed7(booking)
    occurrence.starts_at, occurrence.ends_at = at(10, 8, 8, 30), at(10, 8, 11, 30)
    occurrence.save()
    assert booking.series_move_blocked_note(at(10, 5, 9)) is None  # Mon 5 in progress
    assert booking.series_move_blocked_note(at(10, 28, 12)) is None  # nothing left
    one_off = booked_on(make_request(first_date=date(2026, 11, 2)), zoom02, meeting_id="1")
    assert one_off.series_move_blocked_note() is None


def test_the_move_fingerprint_signs_the_classes_as_shown(zoom02):
    """Criterion 30: ``[[pk, start, end], ...]`` in epoch seconds, signed with its own salt."""
    from django.core import signing

    booking = zl42(zoom02)
    classes = booking.remaining_classes()[:2]
    token = LinkRequest.move_fingerprint(classes)
    assert signing.loads(token, salt="apps.zoom.move-shown") == [
        [o.pk, int(o.starts_at.timestamp()), int(o.ends_at.timestamp())] for o in classes
    ]
    with pytest.raises(signing.BadSignature):
        signing.loads(token, salt="apps.zoom.start")


def test_a_class_moved_to_another_time_on_its_day_doesnt_block_the_series(zoom02):
    booking = zl42(zoom02)
    occurrence = wed7(booking)
    occurrence.starts_at, occurrence.ends_at = at(10, 7, 13), at(10, 7, 14)
    occurrence.save()
    assert booking.can_move_series()
    # Not "unchanged": one class isn't at 8:30 yet.
    assert booking.series_move_errors(start_time=time(8, 30), end_time=time(11, 30)) == {}


def test_the_series_span_runs_from_the_first_to_the_last_remaining_class(zoom02):
    booking = zl42(zoom02)
    remaining = booking.remaining_classes(at(10, 6, 12))  # Mon 5 is over
    assert booking.series_span_dates(remaining) == [
        date(2026, 10, day) for day in (7, 12, 14, 19, 21, 26, 28)
    ]


# --------------------------------------------------------------------------- 7 clash query


def test_clashing_finds_overlaps_on_the_account_but_not_touching_or_excluded(zoom02):
    booking = zl42(zoom02)
    mon5, target = booking.occurrences.get(starts_at=at(10, 5, 8, 30)), wed7(booking)
    other = booked_on(
        make_request(first_date=date(2026, 10, 8), start=time(9), end=time(10)),
        zoom02,
        meeting_id="2",
    )
    clashing = Occurrence.objects.clashing
    assert clashing(zoom02, [(at(10, 5, 8, 30), at(10, 5, 9))], exclude_ids=[target.pk]) == [mon5]
    assert clashing(zoom02, [(at(10, 7, 11, 30), at(10, 7, 12, 30))], exclude_ids=[target.pk]) == []
    assert clashing(zoom02, [(at(10, 7, 9), at(10, 7, 10))], exclude_ids=[target.pk]) == []
    assert clashing(zoom02, [(at(10, 8, 9, 30), at(10, 8, 11))]) == [other.occurrences.get()]
    assert clashing(make_account("Zoom 03"), [(at(10, 5, 8, 30), at(10, 5, 9))]) == []
    assert clashing(zoom02, []) == []
