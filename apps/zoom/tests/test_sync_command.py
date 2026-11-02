"""Brief 013, ``manage.py sync_zoom_bookings`` (criteria 19 and 28; Design D.6).

Zoom is the fake provider, steered per meeting with ``FakeProvider.meeting_states``. Each
pinned line form and both rendered summaries are checked, and the exit code.
"""

from datetime import date
from io import StringIO
from unittest import mock

import pytest
from django.core import mail
from django.core.management import CommandError, call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.zoom import services
from apps.zoom.models import LinkRequest
from apps.zoom.providers import FakeProvider, ZoomBusy, read_meeting_state

from . import synckit as kit
from .conftest import make_account

pytestmark = pytest.mark.django_db
at = kit.at


@pytest.fixture
def zoom02(settings, db):
    account = make_account("Zoom 02", sort_order=2)
    kit.connect(settings, account)
    return account


def _run():
    out = StringIO()
    try:
        call_command("sync_zoom_bookings", stdout=out)
    except CommandError as exc:
        return out.getvalue().splitlines(), exc
    return out.getvalue().splitlines(), None


def _zoom_has(booking, **changes):
    FakeProvider.meeting_states[booking.meeting_id] = read_meeting_state(
        kit.booking_series(booking, **changes)
    )


def _one_off_as_is(booking):
    occurrence = booking.occurrences.get()
    FakeProvider.meeting_states[booking.meeting_id] = read_meeting_state(
        kit.single_detail(occurrence.starts_at, meeting_id=booking.meeting_id)
    )


def test_copied_and_emailed(zoom02):
    booking = kit.zl42(zoom02)
    _zoom_has(
        booking,
        deleted=[at(7, 8, 30)],
        moved={at(12, 8, 30): (at(13, 9), 180), at(14, 8, 30): (at(15, 9), 180)},
    )
    lines, failed = _run()
    assert lines == [
        f"{booking.reference} (Zoom 02): 1 class cancelled, 2 moved. Emailed the requester.",
        "Checked 1 booking: 1 changed, 0 need a look, 0 couldn't be checked.",
    ]
    assert failed is None


def test_only_moved_names_the_classes(settings, zoom02):
    zoom03 = make_account("Zoom 03", sort_order=3)
    kit.connect(settings, zoom02, zoom03)
    booking = kit.zl43(zoom03)
    FakeProvider.meeting_states[booking.meeting_id] = read_meeting_state(
        kit.single_detail(at(6, 9))
    )
    lines, _ = _run()
    assert lines[0] == f"{booking.reference} (Zoom 03): 1 class moved. Emailed the requester."


def test_copied_but_the_email_failed(zoom02):
    booking = kit.zl42(zoom02)
    _zoom_has(booking, deleted=[at(7, 8, 30)])
    with mock.patch.object(services, "send_cancelled_email", return_value=False):
        lines, _ = _run()
    assert lines[0] == (
        f"{booking.reference} (Zoom 02): 1 class cancelled. The email to the requester didn't send."
    )


def test_needs_a_look_then_still_needs_a_look(zoom02, it_user):
    booking = kit.zl42(zoom02)
    _zoom_has(booking, extra=[(at(8, 9), 180)])
    lines, _ = _run()
    assert lines == [
        f"{booking.reference} (Zoom 02): needs a look. Emailed the IT desk.",
        "Checked 1 booking: 0 changed, 1 needs a look, 0 couldn't be checked.",
    ]
    lines, _ = _run()
    assert lines[0] == f"{booking.reference} (Zoom 02): still needs a look. No new email."
    assert len(mail.outbox) == 1


def test_copied_and_needs_a_look(zoom02, it_user):
    booking = kit.zl42(zoom02)
    _zoom_has(booking, moved={at(12, 8, 30): (at(13, 9), 180)}, extra=[(at(8, 9), 180)])
    lines, _ = _run()
    assert lines[0] == (
        f"{booking.reference} (Zoom 02): 1 class moved, and needs a look. Emailed the requester "
        "and the IT desk."
    )


def test_copied_and_needs_a_look_with_the_requester_email_failed(zoom02, it_user):
    booking = kit.zl42(zoom02)
    _zoom_has(booking, moved={at(12, 8, 30): (at(13, 9), 180)}, extra=[(at(8, 9), 180)])
    with mock.patch.object(services, "send_moved_email", return_value=False):
        lines, _ = _run()
    assert lines[0] == (
        f"{booking.reference} (Zoom 02): 1 class moved, and needs a look. Emailed the IT desk. "
        "The email to the requester didn't send."
    )


def test_couldn_t_be_checked_names_the_booking_and_exits_1(zoom02):
    booking = kit.zl42(zoom02)
    FakeProvider.meeting_states[booking.meeting_id] = ZoomBusy()
    lines, failed = _run()
    assert lines == [
        f"{booking.reference} (Zoom 02): couldn't be checked: Zoom is busy right now.",
        "Checked 1 booking: 0 changed, 0 need a look, 1 couldn't be checked.",
    ]
    assert failed is not None and failed.returncode == 1


def test_a_lock_race_prints_its_pinned_line_counts_in_f_and_exits_1(zoom02):
    """Criterion 19's lock-race line (review round 1, S3)."""
    booking = kit.zl42(zoom02)
    _zoom_has(booking)
    race = services.ReconcileResult(services.LOCK_RACE, booking)
    with mock.patch.object(services, "reconcile", return_value=race):
        lines, failed = _run()
    assert lines == [
        f"{booking.reference} (Zoom 02): couldn't be checked: Someone else was changing this "
        "booking at the same moment.",
        "Checked 1 booking: 0 changed, 0 need a look, 1 couldn't be checked.",
    ]
    assert failed is not None and failed.returncode == 1


def test_a_lock_race_from_two_changes_in_a_row_is_the_same_line(zoom02):
    """Criterion 30's second fingerprint mismatch reaches the command as ``LOCK_RACE``."""
    booking = kit.zl42(zoom02)
    _zoom_has(booking)
    with mock.patch.object(
        services, "_reconcile_once", side_effect=services.BookingChangedMeanwhile()
    ):
        lines, failed = _run()
    assert lines[0] == (
        f"{booking.reference} (Zoom 02): couldn't be checked: Someone else was changing this "
        "booking at the same moment."
    )
    assert lines[-1] == "Checked 1 booking: 0 changed, 0 need a look, 1 couldn't be checked."
    assert failed.returncode == 1
    assert len(FakeProvider.state_calls) == 2  # asked once more, then gave up


def test_the_it_email_failing_ends_the_line_with_its_own_sentence(zoom02, it_user, settings):
    """Criterion 19's ``The email to the IT desk didn't send.`` (review round 1, S3)."""
    settings.EMAIL_BACKEND = "apps.zoom.tests.test_sync_command.FailingBackend"
    booking = kit.zl42(zoom02)
    _zoom_has(booking, extra=[(at(8, 9), 180)])
    lines, failed = _run()
    assert lines == [
        f"{booking.reference} (Zoom 02): needs a look. The email to the IT desk didn't send.",
        "Checked 1 booking: 0 changed, 1 needs a look, 0 couldn't be checked.",
    ]
    assert failed is None
    booking.refresh_from_db()
    assert len(booking.zoom_attention_lines) == 1  # the flag is kept for the page to show


def test_one_booking_s_error_never_stops_the_run(zoom02, caplog):
    """Criterion 19, review round 1, N3: a ``RuntimeError`` in one booking of three."""
    bookings = [
        kit.zl43(zoom02, meeting_id=f"8123456{day:04d}", first_date=date(2026, 10, day))
        for day in (5, 6, 7)
    ]
    for booking in bookings:
        _one_off_as_is(booking)
    real = services.reconcile

    def reconcile(link_request, **kwargs):
        if link_request.pk == bookings[1].pk:
            raise RuntimeError("boom with Grade 11 Physics")
        return real(link_request, **kwargs)

    with mock.patch.object(services, "reconcile", side_effect=reconcile):
        lines, failed = _run()
    assert lines == [
        f"{bookings[1].reference} (Zoom 02): couldn't be checked: RuntimeError.",
        "Checked 3 bookings: 0 changed, 0 need a look, 1 couldn't be checked.",
    ]
    assert failed is not None and failed.returncode == 1
    assert len(FakeProvider.state_calls) == 2  # the other two were still checked
    errors = [r for r in caplog.records if r.name.startswith("apps.") and r.levelname == "ERROR"]
    assert [r.getMessage() for r in errors] == [
        f"Checking {bookings[1].reference} with Zoom failed: RuntimeError"
    ]
    assert "boom" not in caplog.text


def test_a_booking_whose_last_class_began_after_the_list_was_read_prints_nothing(
    zoom02, monkeypatch
):
    """N2 in the command: ``not_asked`` is neither a change nor a failure."""
    booking = kit.zl43(zoom02)
    _one_off_as_is(booking)
    not_asked = services.ReconcileResult(services.NOT_ASKED, booking, attention=["x"])
    with mock.patch.object(services, "reconcile", return_value=not_asked):
        lines, failed = _run()
    assert lines == ["Checked 1 booking: 0 changed, 0 need a look, 0 couldn't be checked."]
    assert failed is None


def test_twelve_bookings_summary(zoom02):
    bookings = [
        kit.zl43(zoom02, meeting_id=f"8123456{day:04d}", first_date=date(2026, 10, day))
        for day in range(5, 17)
    ]
    for booking in bookings:
        _one_off_as_is(booking)
    FakeProvider.meeting_states[bookings[0].meeting_id] = None
    FakeProvider.meeting_states[bookings[1].meeting_id] = None
    FakeProvider.meeting_states[bookings[2].meeting_id] = ZoomBusy()
    lines, failed = _run()
    assert lines[-1] == "Checked 12 bookings: 2 changed, 0 need a look, 1 couldn't be checked."
    assert len(lines) == 4 and failed.returncode == 1


def test_no_line_holds_a_class_name_an_email_or_a_link(zoom02, it_user):
    booking = kit.zl42(zoom02)
    _zoom_has(booking, deleted=[at(7, 8, 30)], extra=[(at(8, 9), 180)])
    lines, _ = _run()
    text = "\n".join(lines)
    for secret in ("Grade 11 Physics", "@", "http", "zoom.us", kit.MEETING):
        assert secret not in text


def test_only_bookings_with_classes_left_on_a_connected_account_are_checked(zoom02):
    unconnected = make_account("Zoom 09", sort_order=9)
    FakeProvider.not_connected = {unconnected.pk}
    kit.zl43(unconnected, meeting_id="81999999999")
    kit.zl43(zoom02, first_date=date(2026, 9, 21), meeting_id="81888888888")  # all held
    cancelled = kit.zl42(zoom02)
    LinkRequest.objects.filter(pk=cancelled.pk).update(
        status=LinkRequest.Status.CANCELLED, cancelled_at=at(1, 9)
    )
    lines, failed = _run()
    assert lines == ["Checked 0 bookings: 0 changed, 0 need a look, 0 couldn't be checked."]
    assert FakeProvider.state_calls == [] and failed is None


def test_the_manual_provider_checks_nothing(settings, zoom02):
    settings.ZOOM_PROVIDER = "manual"
    kit.zl42(zoom02)
    lines, failed = _run()
    assert lines == ["This system can't reach Zoom, so no bookings were checked."]
    assert failed is None


# --------------------------------------------------------------------------- 28 the sweep


def test_the_sweep_clears_a_flag_whose_classes_have_all_been_held_in_one_update(zoom02):
    finished = kit.zl43(zoom02, first_date=date(2026, 9, 21), meeting_id="81888888888")
    LinkRequest.objects.filter(pk=finished.pk).update(zoom_attention="Something.")
    with CaptureQueriesContext(connection) as queries:
        lines, _ = _run()
    finished.refresh_from_db()
    assert finished.zoom_attention == ""
    updates = [q["sql"] for q in queries if q["sql"].startswith("UPDATE")]
    assert len(updates) == 1 and "zoom_attention" in updates[0]
    assert lines == ["Checked 0 bookings: 0 changed, 0 need a look, 0 couldn't be checked."]
    assert mail.outbox == []


def test_the_sweep_keeps_the_flag_of_a_booking_with_classes_left(zoom02, it_user):
    booking = kit.zl42(zoom02)
    _zoom_has(booking, extra=[(at(8, 9), 180)])
    _run()
    booking.refresh_from_db()
    assert len(booking.zoom_attention_lines) == 1
    lines, _ = _run()
    booking.refresh_from_db()
    assert booking.zoom_attention_lines == [
        "Zoom has a class on Thu 8 Oct 2026, 9:00 am to 12:00 pm that isn't booked here."
    ]


class FailingBackend:
    """An email backend whose every send raises, as a mail server that refuses would."""

    def __init__(self, *args, **kwargs):
        pass

    def open(self):
        return True

    def close(self):
        pass

    def send_messages(self, messages):
        raise ConnectionRefusedError("mail server down")
