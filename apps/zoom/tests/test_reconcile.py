"""Brief 013, ``services.reconcile()``: bringing a booking into line with Zoom (criteria 13-17
and 28), against the live provider with Zoom's answers mocked (criterion 23).

Each rule of criterion 14's table has a test here, through the real lock-and-write path; the
comparison itself is also tested on its own in ``test_sync_models.py``. The requester and IT
emails are rendered from the real templates. That no transaction is open while Zoom is asked
(criterion 13) is tested on committed data in ``test_sync_race.py``.
"""

from datetime import timedelta
from unittest import mock

import pytest
from django.core import mail
from django.db import OperationalError, connection
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext

from apps.zoom import services
from apps.zoom.models import (
    CANCELLED_IN_ZOOM_REASON,
    HostSlot,
    LinkRequest,
    Occurrence,
    ZoomEvent,
)
from apps.zoom.providers import ManualProvider, ZoomBusy, ZoomDailyLimit

from . import synckit as kit
from .conftest import FROZEN_NOW, make_account

pytestmark = pytest.mark.django_db
at = kit.at


@pytest.fixture
def zoom02(settings, http_mock, db):
    account = make_account("Zoom 02", sort_order=2)
    kit.live(settings, http_mock, account)
    settings.ALLOWED_HOSTS = ["testserver", "tmd.polymath.edu.lk"]
    return account


@pytest.fixture
def it_desk(it_user):
    """An IT desk member, so the needs-a-look email has someone to go to."""
    return it_user


def _request():
    return RequestFactory().get("/", HTTP_HOST="tmd.polymath.edu.lk", secure=True)


def _reconcile(booking):
    return services.reconcile(booking, request=_request())


def _requester_mail():
    return [m for m in mail.outbox if m.to == ["nimal@example.com"]]


def _it_mail():
    return [m for m in mail.outbox if m.to != ["nimal@example.com"]]


# --------------------------------------------------------------------------- 13 ask first


def test_zoom_is_asked_once_with_a_get_and_never_changed(zoom02, http_mock):
    booking = kit.zl42(zoom02)
    kit.add_meeting(http_mock, kit.booking_series(booking))
    result = _reconcile(booking)
    assert result.outcome == "no_change"
    calls = [c.request for c in http_mock.calls if "/oauth/" not in c.request.url]
    assert [(r.method, r.url) for r in calls] == [("GET", kit.zm.meeting_url(kit.MEETING))]


# --------------------------------------------------------------------------- 14 the table


def test_a_whole_meeting_deleted_in_zoom_cancels_the_booking(zoom02, http_mock, it_desk):
    booking = kit.zl42(zoom02)
    LinkRequest.objects.filter(pk=booking.pk).update(zoom_attention="Old sentence.")
    kit.add_meeting(http_mock, status=404)
    result = _reconcile(booking)

    assert result.outcome == "changed" and len(result.cancelled) == 8 and result.moved == []
    booking.refresh_from_db()
    assert booking.status == LinkRequest.Status.CANCELLED
    assert booking.cancelled_at == FROZEN_NOW and booking.cancelled_by is None
    assert booking.cancelled_in_zoom
    assert booking.zoom_attention == ""  # criterion 28
    classes = list(booking.occurrences.all())
    assert all(o.cancelled_in_zoom for o in classes)
    assert {o.cancel_reason for o in classes} == {CANCELLED_IN_ZOOM_REASON}
    assert not HostSlot.objects.filter(occurrence__link_request=booking).exists()
    [email] = _requester_mail()
    assert result.emailed and _it_mail() == []
    assert email.subject == f"Cancelled: {booking.reference} Grade 11 Physics"
    assert (
        f"Your Zoom booking {booking.reference} for Grade 11 Physics was cancelled directly in "
        "Zoom." in email.body
    )
    assert "Reason: Cancelled directly in Zoom." in email.body
    assert "If you didn't expect this, reply to the IT desk." in email.body
    assert "The IT desk has" not in email.body


def test_a_class_deleted_in_zoom_is_cancelled_here(zoom02, http_mock):
    booking = kit.zl42(zoom02)
    kit.add_meeting(http_mock, kit.booking_series(booking, deleted=[at(7, 8, 30)]))
    result = _reconcile(booking)

    [cancelled] = result.cancelled
    assert cancelled.starts_at == at(7, 8, 30)
    wed7 = Occurrence.objects.get(pk=cancelled.pk)
    assert wed7.cancelled_at == FROZEN_NOW and wed7.cancelled_by is None
    assert wed7.cancel_reason == CANCELLED_IN_ZOOM_REASON
    assert not wed7.slots.exists()
    booking.refresh_from_db()
    assert booking.status == LinkRequest.Status.APPROVED and booking.cancelled_at is None
    [email] = _requester_mail()
    assert (
        f"1 class of your Zoom booking {booking.reference} for Grade 11 Physics was cancelled "
        "directly in Zoom." in email.body
    )
    assert "The IT desk has" not in email.body
    assert "If you didn't expect this, reply to the IT desk." in email.body


def test_a_class_missing_from_zoom_is_cancelled_here(zoom02, http_mock):
    booking = kit.zl42(zoom02)
    kit.add_meeting(http_mock, kit.booking_series(booking, missing=[at(28, 8, 30)]))
    result = _reconcile(booking)
    assert [o.starts_at for o in result.cancelled] == [at(28, 8, 30)]


def test_a_class_moved_in_zoom_to_a_free_time_is_moved_here(zoom02, http_mock):
    booking = kit.zl42(zoom02)
    kit.add_meeting(http_mock, kit.booking_series(booking, moved={at(12, 8, 30): (at(13, 9), 180)}))
    result = _reconcile(booking)

    assert result.outcome == "changed" and result.cancelled == []
    [move] = result.moved
    assert (move.old_start, move.old_end) == (at(12, 8, 30), at(12, 11, 30))
    moved = Occurrence.objects.get(pk=move.occurrence.pk)
    assert (moved.starts_at, moved.ends_at) == (at(13, 9), at(13, 12))
    assert moved.moved_at == FROZEN_NOW and moved.moved_by is None and moved.moved_in_zoom
    assert moved.host_account_id == zoom02.pk
    assert moved.zoom_occurrence_id == kit.occurrence_id(at(12, 8, 30))  # the same class in Zoom
    assert {s.starts_at for s in moved.slots.all()} == {
        at(13, 9) + timedelta(minutes=5 * i) for i in range(36)
    }
    booking.refresh_from_db()
    assert booking.zoom_attention == ""
    [email] = _requester_mail()
    assert email.subject == f"Class times changed: {booking.reference} Grade 11 Physics"
    assert (
        f"The time of 1 class in your Zoom booking {booking.reference} for Grade 11 Physics was "
        "changed directly in Zoom." in email.body
    )
    assert "Was: Mon 12 Oct 2026, 8:30 am to 11:30 am" in email.body
    assert "Now: Tue 13 Oct 2026, 9:00 am to 12:00 pm" in email.body
    assert "If the new time doesn't work for you, reply to the IT desk." in email.body
    assert "The IT desk has" not in email.body


def test_a_one_off_moved_in_zoom_is_moved_here(zoom02, http_mock):
    booking = kit.zl43(zoom02)
    kit.add_meeting(http_mock, kit.single_detail(at(6, 9)), meeting_id=kit.ONE_OFF_MEETING)
    result = _reconcile(booking)
    [move] = result.moved
    assert (move.occurrence.starts_at, move.occurrence.ends_at) == (at(6, 9), at(6, 12))
    [email] = _requester_mail()
    assert (
        f"The time of 1 class in your Zoom booking {booking.reference} for Staff briefing was "
        "changed directly in Zoom." in email.body
    )


def test_a_move_onto_a_booked_time_is_not_copied_and_needs_a_look(zoom02, http_mock, it_desk):
    booking = kit.zl42(zoom02)
    other = kit.zl43(zoom02, first_date=at(13, 0).date(), name="Grade 10 Chemistry")
    kit.add_meeting(http_mock, kit.booking_series(booking, moved={at(12, 8, 30): (at(13, 9), 180)}))
    result = _reconcile(booking)

    line = (
        "The class on Mon 12 Oct 2026, 8:30 am was moved in Zoom to Tue 13 Oct 2026, 9:00 am to "
        f"12:00 pm, but Zoom 02 already has {other.reference} Grade 10 Chemistry then, so it "
        "wasn't moved here."
    )
    assert result.outcome == "needs_a_look" and result.attention == [line]
    assert result.attention_changed and result.it_emailed and not result.emailed
    assert result.moved == [] and result.cancelled == []
    assert Occurrence.objects.filter(starts_at=at(12, 8, 30), link_request=booking).exists()
    booking.refresh_from_db()
    assert booking.zoom_attention_lines == [line]
    assert _requester_mail() == []
    [email] = _it_mail()
    assert email.to == ["kasun@polymath.example"]
    assert email.subject == f"Needs a look: {booking.reference} was changed in Zoom"
    assert line in email.body
    assert f"https://tmd.polymath.edu.lk/zoom/requests/{booking.pk}/" in email.body


def test_a_class_added_in_zoom_needs_a_look_and_changes_nothing(zoom02, http_mock, it_desk):
    booking = kit.zl42(zoom02)
    kit.add_meeting(http_mock, kit.booking_series(booking, extra=[(at(8, 9), 180)]))
    result = _reconcile(booking)
    assert result.attention == [
        "Zoom has a class on Thu 8 Oct 2026, 9:00 am to 12:00 pm that isn't booked here."
    ]
    assert result.outcome == "needs_a_look" and result.copied == 0
    assert len(_it_mail()) == 1 and _requester_mail() == []


def test_a_time_that_can_t_be_booked_here_is_not_copied(zoom02, http_mock, it_desk):
    booking = kit.zl42(zoom02)
    kit.add_meeting(
        http_mock, kit.booking_series(booking, moved={at(12, 8, 30): (at(12, 9, 2), 180)})
    )
    result = _reconcile(booking)
    assert result.moved == []
    assert result.attention == [
        "The class on Mon 12 Oct 2026, 8:30 am was moved in Zoom to Mon 12 Oct 2026, 9:02 am to "
        "12:02 pm, but that time can't be booked here, so it wasn't moved here."
    ]


def test_only_a_topic_change_is_no_change_with_no_write_and_no_email(zoom02, http_mock):
    booking = kit.zl42(zoom02)
    detail = kit.booking_series(booking)
    detail["topic"] = "Renamed in Zoom"
    kit.add_meeting(http_mock, detail)
    with CaptureQueriesContext(connection) as queries:
        result = _reconcile(booking)
    assert result.outcome == "no_change" and not result.emailed
    writes = [q["sql"] for q in queries if q["sql"].split()[0] in ("UPDATE", "INSERT", "DELETE")]
    assert writes == []
    assert mail.outbox == []


def test_held_classes_stay_as_they_were(zoom02, http_mock, monkeypatch):
    booking = kit.zl42(zoom02)
    monkeypatch.setattr("django.utils.timezone.now", lambda: at(8, 9))
    kit.add_meeting(
        http_mock,
        kit.booking_series(booking, moved={at(5, 8, 30): (at(5, 9), 180)}, deleted=[at(7, 8, 30)]),
    )
    result = _reconcile(booking)
    assert result.outcome == "no_change"
    assert not Occurrence.objects.filter(cancelled_at__isnull=False).exists()
    assert not Occurrence.objects.filter(moved_at__isnull=False).exists()


# --------------------------------------------------------------------------- 15-16 the flag


def test_the_flag_is_cleared_by_the_next_check_that_finds_nothing(zoom02, http_mock, it_desk):
    booking = kit.zl42(zoom02)
    kit.add_meeting(http_mock, kit.booking_series(booking, extra=[(at(8, 9), 180)]))
    _reconcile(booking)
    mail.outbox.clear()
    http_mock.replace(
        "GET", kit.zm.meeting_url(kit.MEETING), json=kit.booking_series(booking), status=200
    )
    result = _reconcile(booking)
    assert result.outcome == "no_change" and result.attention == []
    booking.refresh_from_db()
    assert booking.zoom_attention == ""
    assert mail.outbox == []  # clearing sends nothing


def test_the_same_sentences_again_send_no_second_it_email(zoom02, http_mock, it_desk):
    booking = kit.zl42(zoom02)
    kit.add_meeting(http_mock, kit.booking_series(booking, extra=[(at(8, 9), 180)]))
    first = _reconcile(booking)
    second = _reconcile(booking)
    assert first.attention_changed and not second.attention_changed
    assert second.outcome == "needs_a_look" and not second.it_emailed
    assert len(_it_mail()) == 1


def test_changed_sentences_email_it_again(zoom02, http_mock, it_desk):
    booking = kit.zl42(zoom02)
    kit.add_meeting(http_mock, kit.booking_series(booking, extra=[(at(8, 9), 180)]))
    _reconcile(booking)
    http_mock.replace(
        "GET",
        kit.zm.meeting_url(kit.MEETING),
        json=kit.booking_series(booking, extra=[(at(8, 9), 180), (at(9, 9), 180)]),
    )
    assert _reconcile(booking).it_emailed
    assert len(_it_mail()) == 2


def test_the_last_class_cancelled_in_zoom_clears_the_flag(zoom02, http_mock, monkeypatch):
    booking = kit.zl42(zoom02)
    LinkRequest.objects.filter(pk=booking.pk).update(zoom_attention="Something.")
    monkeypatch.setattr("django.utils.timezone.now", lambda: at(27, 9))  # only Wed 28 is left
    kit.add_meeting(http_mock, kit.booking_series(booking, deleted=[at(28, 8, 30)]))
    result = _reconcile(booking)
    assert [o.starts_at for o in result.cancelled] == [at(28, 8, 30)]
    booking.refresh_from_db()
    assert booking.status == LinkRequest.Status.CANCELLED and booking.zoom_attention == ""
    email = _requester_mail()[0]
    assert (
        f"Your Zoom booking {booking.reference} for Grade 11 Physics was cancelled directly "
        "in Zoom." in email.body
    )


def test_a_flagged_booking_with_classes_left_keeps_its_flag_when_still_true(zoom02, http_mock):
    booking = kit.zl42(zoom02)
    kit.add_meeting(http_mock, kit.booking_series(booking, extra=[(at(8, 9), 180)]))
    _reconcile(booking)
    _reconcile(booking)
    booking.refresh_from_db()
    assert len(booking.zoom_attention_lines) == 1


def test_copied_and_needs_a_look_together(zoom02, http_mock, it_desk):
    booking = kit.zl42(zoom02)
    kit.add_meeting(
        http_mock,
        kit.booking_series(booking, deleted=[at(7, 8, 30)], extra=[(at(8, 9), 180)]),
    )
    result = _reconcile(booking)
    assert result.outcome == "changed" and result.copied == 1 and result.needs_a_look
    assert result.emailed and result.it_emailed
    assert len(_requester_mail()) == 1 and len(_it_mail()) == 1


def test_a_failed_requester_email_is_reported_not_raised(zoom02, http_mock):
    booking = kit.zl42(zoom02)
    kit.add_meeting(http_mock, kit.booking_series(booking, deleted=[at(7, 8, 30)]))
    with mock.patch.object(services, "send_cancelled_email", return_value=False):
        result = _reconcile(booking)
    assert result.copied == 1 and not result.emailed


def test_a_cancelled_and_a_moved_class_send_one_email_of_each_kind(zoom02, http_mock):
    booking = kit.zl42(zoom02)
    kit.add_meeting(
        http_mock,
        kit.booking_series(
            booking, deleted=[at(7, 8, 30)], moved={at(12, 8, 30): (at(13, 9), 180)}
        ),
    )
    result = _reconcile(booking)
    assert result.copied == 2 and result.emailed
    subjects = sorted(m.subject.split(":")[0] for m in _requester_mail())
    assert subjects == ["Cancelled", "Class times changed"]


def test_no_requester_or_it_email_carries_a_link_or_zoom_s_text(zoom02, http_mock, it_desk):
    booking = kit.zl42(zoom02)
    kit.add_meeting(
        http_mock,
        kit.booking_series(booking, deleted=[at(7, 8, 30)], extra=[(at(8, 9), 180)]),
    )
    _reconcile(booking)
    for email in mail.outbox:
        assert "zak=" not in email.body and "pwd=" not in email.body
        assert kit.START_URL not in email.body and kit.JOIN_URL not in email.body


# --------------------------------------------------------------------------- failures


def test_zoom_unreachable_changes_nothing(zoom02, http_mock):
    booking = kit.zl42(zoom02)
    kit.add_meeting(http_mock, status=503)
    result = _reconcile(booking)
    assert result.outcome == "provider_error" and result.error.user_message == "no answer from Zoom"
    assert not Occurrence.objects.filter(cancelled_at__isnull=False).exists()
    assert mail.outbox == []


def test_a_deadlock_is_retried_once_without_asking_zoom_again(zoom02, http_mock):
    booking = kit.zl42(zoom02)
    kit.add_meeting(http_mock, kit.booking_series(booking, deleted=[at(7, 8, 30)]))
    real = services._reconcile_once
    calls = []

    def flaky(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise OperationalError(1213, "Deadlock found")
        return real(*args, **kwargs)

    with mock.patch.object(services, "_reconcile_once", side_effect=flaky):
        result = _reconcile(booking)
    assert result.outcome == "changed" and len(calls) == 2
    assert len(kit.gets(http_mock)) == 1


@pytest.mark.parametrize("codes", [(1213, 1213), (1205,)])
def test_a_second_deadlock_or_a_lock_wait_is_a_lock_race(zoom02, http_mock, codes):
    booking = kit.zl42(zoom02)
    kit.add_meeting(http_mock, kit.booking_series(booking))
    errors = [OperationalError(code, "lock") for code in codes]
    with mock.patch.object(services, "_reconcile_once", side_effect=errors):
        result = _reconcile(booking)
    assert result.outcome == "conflict"


def test_a_booking_with_nothing_left_asks_zoom_nothing(zoom02, http_mock, monkeypatch):
    booking = kit.zl43(zoom02)
    LinkRequest.objects.filter(pk=booking.pk).update(zoom_attention="Something.")
    monkeypatch.setattr("django.utils.timezone.now", lambda: at(5, 12))
    result = _reconcile(booking)
    assert result.outcome == services.NOT_ASKED and len(http_mock.calls) == 0  # N2
    booking.refresh_from_db()
    assert booking.zoom_attention == ""  # G3


def test_the_manual_provider_asks_zoom_nothing_and_clears_no_flag(zoom02, http_mock):
    booking = kit.zl42(zoom02)
    LinkRequest.objects.filter(pk=booking.pk).update(zoom_attention="Something.")
    result = services.reconcile(booking, provider=ManualProvider())
    assert result.outcome == services.NOT_ASKED and len(http_mock.calls) == 0  # N2
    assert not result.attention_changed and mail.outbox == []
    booking.refresh_from_db()
    assert booking.zoom_attention == "Something."  # not asking isn't "nothing to flag"


# --------------------------------------------------------------------------- 18's messages

EMAIL = "nimal@example.com"


def _result(booking, *, cancelled=0, moved=0, attention=(), emailed=True, **kwargs):
    return services.ReconcileResult(
        kwargs.pop("outcome", "changed"),
        booking,
        cancelled=[object()] * cancelled,
        moved=[object()] * moved,
        attention=list(attention),
        emailed=emailed,
        **kwargs,
    )


def test_every_check_message_is_pinned(zoom02):
    from django.contrib.messages import constants as levels

    booking = kit.zl42(zoom02)
    message = services.sync_message
    assert message(_result(booking, outcome="no_change")) == (
        levels.SUCCESS,
        "Checked with Zoom: this booking matches Zoom.",
    )
    assert message(_result(booking, cancelled=1)) == (
        levels.SUCCESS,
        f"Checked with Zoom: 1 change copied here. We emailed {EMAIL}.",
    )
    assert message(_result(booking, cancelled=2, moved=1)) == (
        levels.SUCCESS,
        f"Checked with Zoom: 3 changes copied here. We emailed {EMAIL}.",
    )
    assert message(_result(booking, moved=1, emailed=False)) == (
        levels.WARNING,
        f"Checked with Zoom: 1 change copied here, but the email to {EMAIL} didn't send. Tell "
        "them yourself.",
    )
    assert message(_result(booking, cancelled=2, attention=["x"])) == (
        levels.WARNING,
        f"Checked with Zoom: 2 changes copied here, and some changes need a look. We emailed "
        f"{EMAIL}.",
    )
    assert message(_result(booking, cancelled=2, attention=["x"], emailed=False)) == (
        levels.WARNING,
        "Checked with Zoom: 2 changes copied here, and some changes need a look. The email to "
        f"{EMAIL} didn't send, so tell them about the copied changes yourself.",
    )
    assert message(_result(booking, outcome="needs_a_look", attention=["x"])) == (
        levels.WARNING,
        "Checked with Zoom: some changes need a look.",
    )
    assert message(_result(booking, outcome="conflict")) == (
        levels.ERROR,
        "Someone else was changing this booking at the same moment. Nothing was changed. Try "
        "again.",
    )
    # N2: not asked is never "matches Zoom", even with a flag already on the booking.
    assert message(_result(booking, outcome=services.NOT_ASKED, attention=["x"])) == (
        levels.ERROR,
        "There are no classes left to check in this booking.",
    )


@pytest.mark.parametrize(
    ("error", "text"),
    [
        (
            ZoomBusy(),
            "We couldn't check with Zoom: Zoom is busy right now. Try again in a few minutes.",
        ),
        (
            services.ZoomAuthFailed(),
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
def test_the_couldn_t_check_message_has_p4_s_next_step(zoom02, error, text):
    from django.contrib.messages import constants as levels

    booking = kit.zl42(zoom02)
    result = services.ReconcileResult("provider_error", booking, error=error)
    assert services.sync_message(result) == (levels.ERROR, text)


def test_no_check_message_offers_another_account_or_jargon():
    for text in services.SYNC_MESSAGES:
        for word in ("another free account", "Waiting won't fix this", "429", "quota", "API"):
            assert word not in text


def test_reconcile_writes_the_event_row_with_its_changes(zoom02, http_mock):
    booking = kit.zl42(zoom02)
    kit.add_meeting(http_mock, kit.booking_series(booking, deleted=[at(7, 8, 30)]))
    record = services.EventRecord(kit.SLUG, "meeting.deleted", "b" * 64, 1)
    result = services.reconcile(booking, request=_request(), zoom_event=record)
    assert result.outcome == "changed"
    row = ZoomEvent.objects.get()
    assert (row.slug, row.event, row.outcome, row.link_request_id) == (
        kit.SLUG,
        "meeting.deleted",
        "changed",
        booking.pk,
    )
    again = services.reconcile(booking, request=_request(), zoom_event=record)
    assert again.outcome == "duplicate" and ZoomEvent.objects.count() == 1
