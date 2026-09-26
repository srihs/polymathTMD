"""Brief 011, the model layer: the cancelled status and fields, the constraints, "booked" without
cancelled classes, the cancel rules, the start window and the start page's state, the
host-key reveal record and the permission's new name (criteria 1-4, 9, 20, 21, 32, 40, 44).

The example booking is the brief's ZL-0042 shape: weekly on Mon and Wed, 5-28 Oct 2026,
8:30-11:30 (8 classes) on Zoom 02, stored through ``booked_on`` so no provider is involved.
"""

import re
from datetime import UTC, date, datetime, time, timedelta
from importlib import import_module

import pytest
from django.apps import apps as django_apps
from django.contrib.auth.models import Permission
from django.db import IntegrityError, connection, models, transaction

from apps.zoom import services
from apps.zoom.models import (
    QUEUE_TABS,
    HostAccount,
    HostKeyReveal,
    HostSlot,
    LinkRequest,
    Occurrence,
)

from .conftest import COLOMBO, FROZEN_NOW, book, booked_on, make_account, make_request

pytestmark = pytest.mark.django_db


def at(day, hour, minute=0):
    """An aware Colombo time in October 2026 (or the given date)."""
    if isinstance(day, int):
        day = date(2026, 10, day)
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=COLOMBO)


@pytest.fixture
def zoom02(db):
    return make_account("Zoom 02", sort_order=2, host_key="8421973")


def zl42(account, **kwargs):
    return booked_on(
        make_request(
            weekdays="1,3",
            first_date=date(2026, 10, 5),
            last_date=date(2026, 10, 28),
            class_name="Grade 11 Physics",
        ),
        account,
        **kwargs,
    )


def cancel_class(link_request, starts_at, user, reason="The school is closed."):
    occurrence = link_request.occurrences.get(starts_at=starts_at)
    result = services.cancel(link_request.pk, occurrence_id=occurrence.pk, by=user, reason=reason)
    assert result.outcome == services.Outcome.CANCELLED, result.message
    occurrence.refresh_from_db()
    return occurrence


# --------------------------------------------------------------------------- 1


def test_the_cancelled_status_and_fields_exist():
    assert LinkRequest.Status.CANCELLED == "cancelled"
    assert LinkRequest.Status.CANCELLED.label == "Cancelled"
    for model, names in (
        (LinkRequest, ("cancelled_at", "cancelled_by")),
        (Occurrence, ("cancelled_at", "cancelled_by", "cancel_reason")),
    ):
        for name in names:
            field = model._meta.get_field(name)
            if name == "cancel_reason":
                assert isinstance(field, models.TextField) and field.blank
            else:
                assert field.null
            if name == "cancelled_by":
                assert field.remote_field.on_delete is models.PROTECT
                assert field.remote_field.related_name == "+"
            assert field.verbose_name and field.help_text


def _raw_update(sql, params):
    with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(sql, params)


def test_a_cancelled_request_must_have_been_booked_and_say_when(zoom02):
    booking = zl42(zoom02)
    waiting = make_request(first_date=date(2026, 11, 2))
    # No cancelled_at.
    _raw_update("UPDATE zoom_linkrequest SET status = 'cancelled' WHERE id = %s", [booking.pk])
    # Never booked: no account, no link.
    _raw_update(
        "UPDATE zoom_linkrequest SET status = 'cancelled', cancelled_at = %s WHERE id = %s",
        [FROZEN_NOW, waiting.pk],
    )
    # The legal shape passes.
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE zoom_linkrequest SET status = 'cancelled', cancelled_at = %s WHERE id = %s",
            [FROZEN_NOW, booking.pk],
        )


def test_a_cancelled_class_must_say_why(zoom02):
    occurrence = zl42(zoom02).occurrences.first()
    _raw_update(
        "UPDATE zoom_occurrence SET cancelled_at = %s, cancel_reason = '' WHERE id = %s",
        [FROZEN_NOW, occurrence.pk],
    )
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE zoom_occurrence SET cancelled_at = %s, cancel_reason = 'x' WHERE id = %s",
            [FROZEN_NOW, occurrence.pk],
        )


# --------------------------------------------------------------------------- 2


def test_a_cancelled_class_is_not_booked_and_frees_the_account(zoom02, it_user):
    booking = zl42(zoom02)
    before = zoom02.upcoming_classes().count()
    assert before == 8
    wed7 = cancel_class(booking, at(7, 8, 30), it_user)

    assert wed7.cancelled_at == FROZEN_NOW and wed7.cancelled_by == it_user
    assert wed7.cancel_reason == "The school is closed."
    assert wed7 not in Occurrence.objects.booked()
    assert Occurrence.objects.booked().count() == 7
    assert zoom02.upcoming_classes().count() == before - 1
    assert HostAccount.objects.with_upcoming().get(pk=zoom02.pk).upcoming_count == 7
    # Its slots are gone; the other seven keep theirs.
    assert not HostSlot.objects.filter(occurrence=wed7).exists()
    assert HostSlot.objects.filter(host_account=zoom02).count() == 7 * 36
    # The timetable no longer shows it.
    day = Occurrence.objects.for_timetable(at(7, 0), at(8, 0))
    assert wed7 not in day
    # The stop-booking count (brief 008) is one lower too.
    errors = zoom02.stop_booking_errors(is_active=False, is_paid=True)
    assert "still has 7 booked classes" in errors["is_active"]
    # A waiting request inside that class's time now finds Zoom 02 free.
    waiting = make_request(first_date=date(2026, 10, 7), start=time(9, 0), end=time(10, 0))
    [(account, clashes)] = HostAccount.objects.filter(pk=zoom02.pk).availability_for(
        waiting.occurrences.all()
    )
    assert account == zoom02 and clashes == []


# --------------------------------------------------------------------------- 3 and 4


@pytest.mark.parametrize(
    ("now", "can_cancel", "cancellable", "running_start"),
    [
        (FROZEN_NOW, True, 8, None),
        (at(5, 9), False, 7, at(5, 8, 30)),  # Mon 5 Oct's class is in progress
        (at(6, 10), True, 7, None),
    ],
)
def test_the_cancel_rules_of_zl42_at_three_moments(
    zoom02, now, can_cancel, cancellable, running_start
):
    """Criterion 3's table, first three rows."""
    booking = zl42(zoom02)
    assert booking.can_cancel_booking(now) is can_cancel
    found = booking.cancellable_classes(now)
    assert len(found) == cancellable
    assert [o.starts_at for o in found] == sorted(o.starts_at for o in found)
    running = booking.class_in_progress(now)
    assert (running.starts_at if running else None) == running_start
    assert booking.status_after_cancel(now) == "approved"  # nothing is cancelled yet


@pytest.mark.parametrize(
    ("now", "kept"),
    [
        (FROZEN_NOW, []),
        (at(5, 9), [at(5, 8, 30)]),  # a class in progress stays
        (at(8, 10), [at(5, 8, 30)]),  # Wed 7 Oct was cancelled, so it isn't kept
        (at(29, 9), [at(day, 8, 30) for day in (5, 12, 14, 19, 21, 26, 28)]),
    ],
)
def test_the_kept_classes_are_the_booked_ones_that_have_started(
    zoom02, it_user, django_assert_num_queries, now, kept
):
    """Review round 1, SF2: the classes a whole cancel leaves alone, soonest first. Together
    with ``cancellable_classes`` they cover every booked class, never one twice."""
    booking = zl42(zoom02)
    cancel_class(booking, at(7, 8, 30), it_user)
    booking.refresh_from_db()
    classes = list(booking.occurrences.all())
    with django_assert_num_queries(0):  # given the classes, the rule asks nothing more
        found = booking.kept_classes(now, occurrences=classes)
        cancellable = booking.cancellable_classes(now, occurrences=classes)
    assert [o.starts_at for o in found] == kept
    booked = {o.pk for o in classes if o.cancelled_at is None}
    assert {o.pk for o in found} | {o.pk for o in cancellable} == booked
    assert not {o.pk for o in found} & {o.pk for o in cancellable}
    # Without a list it reads the classes itself, with the same answer.
    assert booking.kept_classes(now) == found


def test_a_request_that_was_never_booked_keeps_no_classes(zoom02):
    assert make_request().kept_classes(at(29, 9)) == []


def test_after_cancelling_the_seven_left_on_tuesday_the_booking_is_cancelled(
    zoom02, it_user, monkeypatch
):
    """Criterion 3's fourth row: the held Mon 5 Oct class keeps its account and slots."""
    booking = zl42(zoom02)
    now = at(6, 10)
    monkeypatch.setattr("django.utils.timezone.now", lambda: now)
    for occurrence in booking.cancellable_classes(now):
        cancel_class(booking, occurrence.starts_at, it_user)
    booking.refresh_from_db()
    assert booking.status_after_cancel(now) == "cancelled"
    assert booking.status == "cancelled" and booking.cancelled_at == now
    held = booking.occurrences.get(starts_at=at(5, 8, 30))
    assert held.cancelled_at is None and held.host_account == zoom02
    assert HostSlot.objects.filter(occurrence=held).count() == 36
    assert booking.can_cancel_booking(now) is False


def test_after_cancelling_one_class_the_booking_stays_approved(zoom02, it_user):
    """Criterion 3's last row."""
    booking = zl42(zoom02)
    cancel_class(booking, at(7, 8, 30), it_user)
    booking.refresh_from_db()
    assert booking.status_after_cancel() == "approved"
    assert booking.status == "approved"
    assert len(booking.cancellable_classes()) == 7


def test_status_after_cancel_counts_only_classes_not_cancelled_and_not_ended(zoom02, it_user):
    booking = zl42(zoom02)
    now = at(6, 10)
    classes = list(booking.occurrences.all())
    for occurrence in classes[1:]:  # everything but the held Mon 5 Oct class
        occurrence.cancelled_at = now
    assert booking.status_after_cancel(now, occurrences=classes) == "cancelled"
    classes[-1].cancelled_at = None
    assert booking.status_after_cancel(now, occurrences=classes) == "approved"


@pytest.mark.parametrize(
    "status", [LinkRequest.Status.WAITING, LinkRequest.Status.REJECTED, "cancelled"]
)
def test_a_request_that_is_not_approved_is_never_cancellable(zoom02, it_user, status):
    if status == "cancelled":
        booking = zl42(zoom02)
        result = services.cancel(booking.pk, by=it_user, reason="Closed.")
        assert result.outcome == services.Outcome.CANCELLED
        link_request = LinkRequest.objects.get(pk=booking.pk)
        assert link_request.status == "cancelled"
    else:
        link_request = make_request()
        if status == LinkRequest.Status.REJECTED:
            link_request.reject(it_user, "No.")
    assert link_request.can_cancel_booking() is False
    assert link_request.cancellable_classes() == []


def test_cancelling_a_booking_never_changes_a_class_that_has_started(zoom02, it_user, monkeypatch):
    booking = zl42(zoom02)
    monkeypatch.setattr("django.utils.timezone.now", lambda: at(6, 10))
    result = services.cancel(booking.pk, by=it_user, reason="Closed.")
    assert result.outcome == services.Outcome.CANCELLED
    assert len(result.cancelled) == 7 and result.remaining == []
    held = booking.occurrences.get(starts_at=at(5, 8, 30))
    assert held.cancelled_at is None and held.host_account == zoom02
    assert HostSlot.objects.filter(occurrence=held).count() == 36
    assert HostSlot.objects.count() == 36
    booking.refresh_from_db()
    assert booking.status == "cancelled"
    assert (booking.cancelled_at, booking.cancelled_by) == (at(6, 10), it_user)


def test_the_blocked_messages_come_from_the_model(zoom02, it_user, monkeypatch):
    booking = zl42(zoom02)
    assert booking.cancel_booking_blocked_message(at(5, 9)) == (
        "Mon 5 Oct 2026, 8:30 am to 11:30 am is in progress. Cancel the rest of this booking "
        "after it ends at 11:30 am."
    )
    assert booking.cancel_booking_blocked_message(FROZEN_NOW) is None
    mon5 = booking.occurrences.get(starts_at=at(5, 8, 30))
    assert mon5.cancel_blocked_message(at(5, 9)) == (
        "That class has already started, so it can't be cancelled."
    )
    wed7 = cancel_class(booking, at(7, 8, 30), it_user)
    assert wed7.cancel_blocked_message() == "That class was already cancelled."
    booking.refresh_from_db()
    monkeypatch.setattr("django.utils.timezone.now", lambda: at(29, 12))
    assert booking.cancel_booking_blocked_message() == (
        "There are no classes left to cancel in this booking."
    )


# --------------------------------------------------------------------------- 9 queue


def test_the_queue_has_a_cancelled_tab_counted_in_one_query(
    zoom02, it_user, django_assert_num_queries, monkeypatch
):
    assert QUEUE_TABS[-2:] == (("cancelled", "Cancelled"), ("all", "All"))
    older = zl42(zoom02)
    services.cancel(older.pk, by=it_user, reason="Closed.")
    newer = booked_on(make_request(first_date=date(2026, 11, 2)), zoom02, meeting_id="81234560000")
    monkeypatch.setattr("django.utils.timezone.now", lambda: FROZEN_NOW + timedelta(hours=1))
    services.cancel(newer.pk, by=it_user, reason="Closed.")
    make_request()
    with django_assert_num_queries(1):
        counts = LinkRequest.objects.tab_counts()
    assert counts == {"waiting": 1, "approved": 0, "rejected": 0, "cancelled": 2, "all": 3}
    assert list(LinkRequest.objects.visible_to_it().for_tab("cancelled")) == [newer, older]


# --------------------------------------------------------------------------- 20 the window


@pytest.mark.parametrize(
    ("other", "other_account", "cancelled", "opens"),
    [
        (None, False, False, (8, 0)),
        ((time(6, 30), time(8, 15)), False, False, (8, 15)),
        ((time(6, 0), time(7, 45)), False, False, (8, 0)),
        ((time(6, 30), time(8, 15)), False, True, (8, 0)),
        ((time(6, 30), time(8, 15)), True, False, (8, 0)),
    ],
)
def test_the_start_window(zoom02, it_user, other, other_account, cancelled, opens):
    assert Occurrence.START_WINDOW_MINUTES == 30
    booking = booked_on(make_request(first_date=date(2026, 10, 5)), zoom02)
    if other:
        account = make_account("Zoom 09") if other_account else zoom02
        earlier = booked_on(
            make_request(first_date=date(2026, 10, 5), start=other[0], end=other[1]),
            account,
            meeting_id="81234569999",
        )
        if cancelled:
            services.cancel(earlier.pk, by=it_user, reason="Closed.")
    [occurrence] = booking.occurrences.all()
    assert occurrence.start_window() == (at(5, *opens), at(5, 11, 30))
    assert occurrence.opens_after_other_class() is (opens != (8, 0))


# --------------------------------------------------------------------------- 21 the state


@pytest.mark.parametrize(
    ("now", "state", "class_start"),
    [
        (FROZEN_NOW, "too_early", at(5, 8, 30)),
        (at(5, 7, 59), "too_early", at(5, 8, 30)),
        (at(5, 8, 0), "ready", at(5, 8, 30)),  # exactly opens_at
        (at(5, 11, 29), "ready", at(5, 8, 30)),
        (at(5, 11, 30), "too_early", at(7, 8, 30)),  # exactly ends_at: not ready
        (at(7, 8, 10), "ready", at(7, 8, 30)),
        (at(28, 11, 30), "ended", at(28, 8, 30)),
        (at(29, 9), "ended", at(28, 8, 30)),
    ],
)
def test_the_start_state(zoom02, now, state, class_start):
    booking = zl42(zoom02)
    found, occurrence = booking.start_state(now)
    assert found == state
    assert occurrence.starts_at == class_start


def test_the_start_state_of_a_one_off_at_its_end_is_ended(zoom02):
    booking = booked_on(make_request(first_date=date(2026, 10, 5)), zoom02)
    assert booking.start_state(at(5, 11, 30))[0] == "ended"


def test_the_start_state_skips_cancelled_classes_and_knows_a_cancelled_booking(
    zoom02, it_user, monkeypatch
):
    booking = zl42(zoom02)
    cancel_class(booking, at(5, 8, 30), it_user)
    booking.refresh_from_db()
    state, occurrence = booking.start_state(at(5, 8, 10))
    assert (state, occurrence.starts_at) == ("too_early", at(7, 8, 30))
    services.cancel(booking.pk, by=it_user, reason="Closed.")
    booking.refresh_from_db()
    assert booking.start_state(at(7, 8, 10)) == ("cancelled", None)


# --------------------------------------------------------------------------- 32 permission


def test_the_review_permission_has_its_new_name_and_the_migration_reverses():
    new = "Can approve, reject, reschedule or cancel Zoom link requests"
    old = "Can approve or reject Zoom link requests"
    assert LinkRequest._meta.permissions == [("review_linkrequest", new)]
    permission = Permission.objects.get(codename="review_linkrequest")
    assert permission.name == new
    migration = import_module("apps.zoom.migrations.0007_review_permission_name")
    migration.use_old_name(django_apps, None)
    permission.refresh_from_db()
    assert permission.name == old
    migration.use_new_name(django_apps, None)
    permission.refresh_from_db()
    assert permission.name == new


# --------------------------------------------------------------------------- 40 and 44


def test_a_reveal_record_holds_no_key(zoom02, it_user):
    pattern = re.compile(r"password|secret|host_key|hostkey|key|token|start_url", re.IGNORECASE)
    names = [field.name for field in HostKeyReveal._meta.get_fields()]
    assert sorted(names) == ["host_account", "id", "shown_at", "shown_by"]
    assert not [name for name in names if pattern.search(name)]
    for name in ("host_account", "shown_by"):
        assert HostKeyReveal._meta.get_field(name).remote_field.on_delete is models.PROTECT
    assert HostKeyReveal._meta.get_field("host_account").remote_field.related_name == (
        "key_reveals"
    )
    assert HostKeyReveal._meta.get_field("shown_at").auto_now_add


def test_the_last_reveal_and_the_count(zoom02, it_user, superuser, monkeypatch):
    assert zoom02.last_key_reveal() is None and zoom02.key_reveal_count() == 0
    services.reveal_host_key(zoom02, by=it_user)
    monkeypatch.setattr("django.utils.timezone.now", lambda: FROZEN_NOW + timedelta(minutes=5))
    services.reveal_host_key(zoom02, by=superuser)
    last = zoom02.last_key_reveal()
    assert (last.shown_by, last.shown_at) == (superuser, FROZEN_NOW + timedelta(minutes=5))
    assert zoom02.key_reveal_count() == 2
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM zoom_hostkeyreveal")
        dump = repr(cursor.fetchall())
    assert "8421973" not in dump


def test_the_account_docstring_states_the_amended_rule():
    """Criterion 45: the backend's part of the "write-only" amendment."""
    text = " ".join(HostAccount.__doc__.split())
    assert (
        "A host key is never shown back on the account's pages or in any list or email. An IT "
        "desk member can show it on its own page as a fallback, and every time it's shown is "
        "recorded."
    ) in text
    assert "write-only: it" not in text


def test_booked_classes_of_a_real_approval_are_counted_once(account, it_user):
    """``BOOKED`` still counts an ordinary approval (a regression guard for criterion 2)."""
    link_request = book(make_request(), account, it_user)
    assert list(Occurrence.objects.booked()) == list(link_request.occurrences.all())
    assert link_request.occurrences.get().starts_at == datetime(2026, 10, 5, 3, 0, tzinfo=UTC)
