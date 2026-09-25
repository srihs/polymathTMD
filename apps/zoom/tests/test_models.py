"""Model-layer rules for Zoom link requests (brief 005, criteria 5, 8, 16, 20, 22, 28-29,
34, 38a, 45-47, 60, 65)."""

import re
from datetime import UTC, date, datetime, time, timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, models, transaction
from django.db.models import ProtectedError
from django.test.utils import CaptureQueriesContext

from apps.zoom.models import (
    HostAccount,
    HostSlot,
    InvalidTransition,
    LinkRequest,
    Occurrence,
    queue_tab,
)
from apps.zoom.validators import format_phone, normalise_phone

from .conftest import FROZEN_NOW, book, make_account, make_request

pytestmark = pytest.mark.django_db

# --------------------------------------------------------------------------- phone (criterion 8)


@pytest.mark.parametrize(
    ("typed", "stored"),
    [
        ("077 123 4567", "+94771234567"),
        ("0771234567", "+94771234567"),
        ("077-123-4567", "+94771234567"),
        ("(077) 123 4567", "+94771234567"),
        ("+94 77 123 4567", "+94771234567"),
        ("94771234567", "+94771234567"),
        ("0094771234567", "+94771234567"),
        ("011 234 5678", "+94112345678"),
        ("+44 20 7946 0958", "+442079460958"),
    ],
)
def test_phone_is_normalised_to_e164(typed, stored):
    assert normalise_phone(typed) == stored


@pytest.mark.parametrize("typed", ["12345", "077 123 456a", "+94 77", "0771234567890123", ""])
def test_bad_phone_numbers_are_refused_with_the_pinned_message(typed):
    with pytest.raises(ValidationError) as caught:
        normalise_phone(typed)
    assert caught.value.messages == [
        "Type a phone number we can call, like 077 123 4567 or +94 77 123 4567."
    ]


@pytest.mark.parametrize(
    ("stored", "shown"),
    [
        ("+94771234567", "+94 77 123 4567"),
        ("+94112345678", "+94 11 234 5678"),
        ("+442079460958", "+442079460958"),
    ],
)
def test_phone_display_form(stored, shown):
    assert format_phone(stored) == shown
    assert LinkRequest(requester_phone=stored).requester_phone_display == shown


# --------------------------------------------------------------------------- schedule (criterion 5)


def test_reference_is_zl_and_pk_padded_to_four_digits():
    assert LinkRequest(pk=42).reference == "ZL-0042"
    assert LinkRequest(pk=12345).reference == "ZL-12345"
    assert LinkRequest().reference == ""


def test_one_off_class_is_stored_in_utc():
    link_request = make_request()
    [occurrence] = link_request.occurrences.all()
    assert occurrence.starts_at == datetime(2026, 10, 5, 3, 0, tzinfo=UTC)
    assert occurrence.ends_at == datetime(2026, 10, 5, 6, 0, tzinfo=UTC)


def test_weekly_monday_and_wednesday_makes_eight_classes():
    link_request = make_request(weekdays="1,3", last_date=date(2026, 10, 28))
    days = [
        o.starts_at.astimezone(FROZEN_NOW.tzinfo).date().day for o in link_request.occurrences.all()
    ]
    assert days == [5, 7, 12, 14, 19, 21, 26, 28]


def test_weekly_first_class_is_the_next_ticked_day():
    link_request = LinkRequest(
        repeat="weekly",
        weekdays="1,3",
        first_date=date(2026, 10, 6),
        last_date=date(2026, 10, 28),
        start_time=time(8, 30),
        end_time=time(11, 30),
    )
    assert link_request.occurrence_dates()[0] == date(2026, 10, 7)


def test_schedule_summary_weekly_and_once():
    weekly = LinkRequest(
        repeat="weekly",
        weekdays="1,3",
        first_date=date(2026, 10, 5),
        last_date=date(2026, 10, 28),
        start_time=time(8, 30),
        end_time=time(11, 30),
    )
    assert weekly.schedule_summary == (
        "Every Monday and Wednesday, 8:30 am to 11:30 am, "
        "from Mon 5 Oct to Wed 28 Oct 2026 (8 classes)"
    )
    once = LinkRequest(
        repeat="once", first_date=date(2026, 10, 5), start_time=time(8, 30), end_time=time(11, 30)
    )
    assert once.schedule_summary == "Once, on Mon 5 Oct 2026, 8:30 am to 11:30 am"


def test_schedule_summary_keeps_both_years_across_new_year_and_says_1_class():
    across = LinkRequest(
        repeat="weekly",
        weekdays="1,3,5",
        first_date=date(2026, 12, 28),
        last_date=date(2027, 1, 4),
        start_time=time(12, 0),
        end_time=time(13, 5),
    )
    assert across.schedule_summary == (
        "Every Monday, Wednesday and Friday, 12:00 pm to 1:05 pm, "
        "from Mon 28 Dec 2026 to Mon 4 Jan 2027 (4 classes)"
    )
    single = LinkRequest(
        repeat="weekly",
        weekdays="7",
        first_date=date(2026, 10, 4),
        last_date=date(2026, 10, 4),
        start_time=time(8, 30),
        end_time=time(9, 0),
    )
    assert single.schedule_summary.endswith("from Sun 4 Oct to Sun 4 Oct 2026 (1 class)")


def test_class_count_matches_the_listed_dates():
    link_request = LinkRequest(
        repeat="weekly",
        weekdays="1,2,3,4,5",
        first_date=date(2026, 10, 5),
        last_date=date(2027, 3, 31),
    )
    assert link_request.class_count() == len(link_request.occurrence_dates()) == 128


def test_has_started_compares_the_first_class_with_now():
    link_request = LinkRequest(
        repeat="once", first_date=date(2026, 9, 28), start_time=time(9, 55), end_time=time(11, 0)
    )
    assert link_request.has_started()
    link_request.start_time = time(10, 5)
    assert not link_request.has_started()


# --------------------------------------------------------------------------- transitions


def test_mark_verified_moves_unverified_to_waiting_once():
    link_request = make_request(status=LinkRequest.Status.UNVERIFIED)
    link_request.mark_verified()
    link_request.refresh_from_db()
    assert link_request.status == LinkRequest.Status.WAITING
    assert link_request.verified_at == FROZEN_NOW
    with pytest.raises(InvalidTransition):
        link_request.mark_verified()


def test_reject_needs_a_reason_and_a_waiting_request(it_user):
    link_request = make_request()
    with pytest.raises(ValidationError):
        link_request.reject(it_user, "   ")
    link_request.reject(it_user, "  Use the Grade 10 link.  ")
    link_request.refresh_from_db()
    assert link_request.status == LinkRequest.Status.REJECTED
    assert link_request.rejection_reason == "Use the Grade 10 link."
    assert link_request.decided_by == it_user
    with pytest.raises(InvalidTransition):
        link_request.reject(it_user, "again")


# --------------------------------------------------------------------------- constraints (45, 38a)


def _expect_integrity_error(callable_):
    with pytest.raises(IntegrityError), transaction.atomic():
        callable_()


def test_occurrence_must_end_after_it_starts():
    link_request = make_request()
    start = datetime(2026, 10, 6, 3, 0, tzinfo=UTC)
    _expect_integrity_error(
        lambda: Occurrence.objects.bulk_create(
            [Occurrence(link_request=link_request, starts_at=start, ends_at=start)]
        )
    )


def test_request_must_end_after_it_starts():
    _expect_integrity_error(lambda: make_request(start=time(9, 0), end=time(9, 0)))


def test_weekly_request_needs_days_and_a_last_date():
    link_request = make_request()
    link_request.repeat = "weekly"
    _expect_integrity_error(link_request.save)


def test_approved_request_needs_account_and_link():
    link_request = make_request()
    link_request.status = LinkRequest.Status.APPROVED
    _expect_integrity_error(link_request.save)


def test_rejected_request_needs_a_reason():
    link_request = make_request()
    link_request.status = LinkRequest.Status.REJECTED
    _expect_integrity_error(link_request.save)


def test_two_slots_on_one_account_at_the_same_time_are_refused(account):
    occurrence = make_request().occurrences.get()
    start = occurrence.starts_at
    HostSlot.objects.create(host_account=account, starts_at=start, occurrence=occurrence)
    _expect_integrity_error(
        lambda: HostSlot.objects.create(
            host_account=account, starts_at=start, occurrence=occurrence
        )
    )


def test_slots_cover_every_five_minutes_and_refuse_unaligned_times(account):
    occurrence = make_request().occurrences.get()
    assert len(HostSlot.covering(occurrence, account)) == 36
    occurrence.starts_at += timedelta(minutes=2)
    with pytest.raises(ValueError):
        HostSlot.covering(occurrence, account)


def test_host_account_with_bookings_cannot_be_deleted(account):
    book(make_request(), account)
    with pytest.raises(ProtectedError):
        account.delete()


def test_deleting_a_request_removes_its_classes_and_slots(account):
    link_request = book(make_request(), account)
    assert HostSlot.objects.count() == 36
    link_request.delete()
    assert Occurrence.objects.count() == 0
    assert HostSlot.objects.count() == 0


def test_no_field_name_looks_like_a_secret_except_the_host_key_and_its_change_record():
    """Brief 008 adds ``host_key_changed_at`` / ``_by``: when and by whom, never the key.

    They're allowed by name, so any other field that looks like a secret still fails.
    """
    pattern = re.compile(r"password|secret|host_key|hostkey|token|start_url", re.IGNORECASE)
    found = [
        f"{model.__name__}.{field.name}"
        for model in (HostAccount, LinkRequest, Occurrence, HostSlot)
        for field in model._meta.get_fields()
        if pattern.search(field.name)
    ]
    assert found == [
        "HostAccount.host_key_encrypted",
        "HostAccount.host_key_changed_at",
        "HostAccount.host_key_changed_by",
    ]
    assert not isinstance(HostAccount._meta.get_field("host_key_changed_at"), models.TextField)


# --------------------------------------------------------------------------- host keys (60, 65)


def test_host_key_is_stored_as_a_fernet_token_not_plaintext():
    account = make_account(host_key="8421973")
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT host_key_encrypted FROM zoom_hostaccount WHERE id = %s", [account.pk]
        )
        [raw] = cursor.fetchone()
    assert raw.startswith("gAAAAA")
    assert "8421973" not in raw
    account.refresh_from_db()
    assert account.get_host_key() == "8421973"
    assert account.has_host_key


def test_same_host_key_twice_gives_different_ciphertexts():
    first, second = HostAccount(), HostAccount()
    first.set_host_key("8421973")
    second.set_host_key("8421973")
    assert first.host_key_encrypted != second.host_key_encrypted


def test_empty_host_key_clears_it():
    account = make_account(host_key="8421973")
    account.set_host_key("")
    account.save()
    account.refresh_from_db()
    assert not account.has_host_key
    assert account.get_host_key() == ""


@pytest.mark.parametrize("bad", ["12345", "12345678901", "84219a3", "842 1973"])
def test_host_key_must_be_6_to_10_digits(bad):
    with pytest.raises(ValidationError) as caught:
        HostAccount().set_host_key(bad)
    assert caught.value.messages == ["A Zoom host key is 6 to 10 digits."]


def test_str_and_repr_never_include_the_host_key():
    account = make_account(host_key="8421973")
    assert "8421973" not in str(account)
    assert "8421973" not in repr(account)
    assert account.host_key_encrypted not in repr(account)


# --------------------------------------------------------------------------- querysets


def test_unverified_requests_are_invisible_to_it():
    hidden = make_request(status=LinkRequest.Status.UNVERIFIED)
    shown = make_request()
    visible = LinkRequest.objects.visible_to_it()
    assert list(visible) == [shown]
    assert hidden not in visible.search(hidden.reference)
    assert LinkRequest.objects.tab_counts() == {
        "waiting": 1,
        "approved": 0,
        "rejected": 0,
        "all": 1,
    }


def test_unknown_queue_tab_falls_back_to_waiting():
    assert queue_tab("nonsense") == "waiting"
    assert queue_tab(None) == "waiting"
    assert queue_tab("all") == "all"


def test_waiting_tab_is_ordered_by_first_class(it_user):
    later = make_request(first_date=date(2026, 10, 9))
    sooner = make_request(first_date=date(2026, 10, 6))
    assert list(LinkRequest.objects.visible_to_it().for_tab("waiting")) == [sooner, later]


def test_decided_tabs_are_newest_decision_first(it_user):
    first = make_request()
    second = make_request()
    first.reject(it_user, "No")
    LinkRequest.objects.filter(pk=first.pk).update(decided_at=FROZEN_NOW - timedelta(hours=1))
    second.reject(it_user, "No")
    assert list(LinkRequest.objects.visible_to_it().for_tab("rejected")) == [second, first]
    assert list(LinkRequest.objects.visible_to_it().for_tab("all")) == [second, first]


@pytest.mark.parametrize("query", ["ZL-{pk:04d}", "zl-{pk}", "{pk}"])
def test_search_by_reference(query):
    make_request()
    target = make_request(class_name="Other")
    found = LinkRequest.objects.visible_to_it().search(query.format(pk=target.pk))
    assert target in found


@pytest.mark.parametrize("query", ["mathem", "NIMALI", "nimali@EXAMPLE", "0771234567", "771234"])
def test_search_by_class_name_email_and_phone(query):
    target = make_request()
    other = make_request(
        class_name="Science",
        requester_name="Kasun",
        email="k@x.example",
        requester_phone="+94112345678",
    )
    found = list(LinkRequest.objects.visible_to_it().search(query))
    assert target in found
    assert other not in found


def test_recent_from_counts_the_last_hour_only():
    make_request(email="a@example.com")
    old = make_request(email="a@example.com")
    LinkRequest.objects.filter(pk=old.pk).update(created_at=FROZEN_NOW - timedelta(minutes=61))
    assert LinkRequest.objects.recent_from(email="A@Example.com").count() == 1
    assert LinkRequest.objects.recent_from(ip="127.0.0.1").count() == 1


def test_availability_marks_overlaps_not_touching_classes_and_skips_unbookable(account):
    busy = make_account("Zoom 02", sort_order=2)
    make_account("Free plan", is_paid=False)
    make_account("Retired", is_active=False)
    book(make_request(start=time(9, 0), end=time(12, 0), class_name="Clash"), busy)
    book(make_request(start=time(11, 30), end=time(12, 30), class_name="Touch"), account)

    mine = list(make_request().occurrences.all())
    rows = HostAccount.objects.availability_for(mine)
    assert [row[0] for row in rows] == [account, busy]
    assert rows[0][1] == []
    [(occurrence, other)] = rows[1][1]
    assert occurrence == mine[0]
    assert other.link_request.class_name == "Clash"


def test_availability_query_count_does_not_grow_with_classes(account):
    short = list(make_request().occurrences.all())
    long = list(make_request(weekdays="1,2,3,4,5", last_date=date(2026, 12, 31)).occurrences.all())
    with CaptureQueriesContext(connection) as few:
        HostAccount.objects.availability_for(short)
    with CaptureQueriesContext(connection) as many:
        HostAccount.objects.availability_for(long)
    assert len(few) == len(many) == 2


def test_overlapping_waiting_reports_that_requests_first_overlapping_class():
    mine = make_request(first_date=date(2026, 10, 7))  # Wed 7 Oct, 8:30-11:30
    # Other request: Mon 5 Oct (no overlap), then Wed 7 Oct 9:00 (overlap).
    other = make_request(
        first_date=date(2026, 10, 5),
        weekdays="1,3",
        last_date=date(2026, 10, 7),
        start=time(9, 0),
        end=time(10, 0),
    )
    make_request(first_date=date(2026, 10, 7), start=time(11, 30), end=time(12, 0))  # touches
    make_request(first_date=date(2026, 10, 7), status=LinkRequest.Status.UNVERIFIED)

    [found] = LinkRequest.objects.overlapping_waiting(mine)
    assert found == other
    assert found.first_overlap == datetime(2026, 10, 7, 3, 30, tzinfo=UTC)
    assert found.first_start == datetime(2026, 10, 5, 3, 30, tzinfo=UTC)


def test_earlier_requests_from_the_same_person_are_capped_at_five():
    for _ in range(6):
        make_request(email="nimali@example.com")
    make_request(email="nimali@example.com", status=LinkRequest.Status.UNVERIFIED)
    current = make_request(email="nimali@example.com")
    earlier = list(LinkRequest.objects.earlier_from_same_requester(current))
    assert len(earlier) == 5
    assert current not in earlier
    assert all(r.status != LinkRequest.Status.UNVERIFIED for r in earlier)
