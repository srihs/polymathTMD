"""Brief 012, criterion 30: a move form left open never overwrites someone else's move.

Two people act on committed rows (the ``committed`` fixture, as the race tests use), because the
point is what one person's **page** showed against what another person's move committed: user A
opens a move page, user B moves the same class (or the series) through ``services``, then A
presses the button on the old page. A must be refused with criterion 29's 1a or 1b naming B's
time, with no Zoom call of any kind, no write and no email; the page comes back with A's typed
values and a fresh ``shown``, and pressing again then works. A class cancelled meanwhile is left
out, not refused.

The one-class case runs against the live provider behind the project-wide ``responses`` mock, so
"no Zoom call" is literally zero HTTP calls. The series cases use the fake provider, whose
recorded calls (``busy_calls``, ``patched``) stand for Zoom.
"""

from datetime import date, datetime
from datetime import time as clock

import pytest
import responses
from django.core import mail
from django.db import connection
from django.test import Client
from django.urls import reverse

from apps.zoom import services
from apps.zoom.models import LinkRequest
from apps.zoom.providers import FakeProvider
from apps.zoom.services import Outcome

from . import zoommock as zm
from .conftest import COLOMBO, booked_on
from .test_cancel_race import _setup
from .test_race import (  # noqa: F401  (committed is a fixture)
    _tracked_request,
    _tracked_user,
    committed,
)

MEETING = "81234567890"


def at(day, hour, minute=0):
    return datetime(2026, 10, day, hour, minute, tzinfo=COLOMBO)


@pytest.mark.django_db
def test_committed_rows_go_to_the_test_database():
    assert connection.settings_dict["NAME"].startswith("test_")


def _weekly(committed, account, name):  # noqa: F811
    return booked_on(
        _tracked_request(
            committed,
            weekdays="1,3",
            first_date=date(2026, 10, 5),
            last_date=date(2026, 10, 28),
            class_name=name,
            email="nimal@example.com",
        ),
        account,
    )


def _people(committed):  # noqa: F811
    """User A (signed in on a browser) and user B, both on the IT desk."""
    from django.contrib.auth.models import Group

    user_a, account = _setup(committed)
    user_b = _tracked_user(committed, username="race-it-b", password="pw")
    user_b.groups.add(Group.objects.get(name="IT desk"))
    browser = Client()
    browser.force_login(user_a)
    return user_a, user_b, account, browser


def _shown(response):
    return response.context["form"]["shown"].value()


# --------------------------------------------------------------------------- one class


def test_a_stale_one_class_form_is_refused_then_works_again(committed, settings, http_mock):  # noqa: F811
    user_a, user_b, account, browser = _people(committed)
    settings.ZOOM_PROVIDER = "zoom"
    zm.connect(account)
    zm.add_token(http_mock)
    zm.add_listing(http_mock, account.email, [])
    http_mock.add(responses.PATCH, zm.meeting_url(MEETING), status=204)
    booking = _weekly(committed, account, "Race S1")
    target = booking.occurrences.get(starts_at=at(7, 8, 30))
    url = reverse("zoom:move_class", args=[booking.pk, target.pk])

    page = browser.get(url)  # A opens the form
    assert page.status_code == 200
    old_shown = _shown(page)

    moved = services.move_class(  # B moves the same class meanwhile
        booking.pk, target.pk, starts_at=at(8, 9), ends_at=at(8, 12), by=user_b
    )
    assert moved.outcome == Outcome.MOVED, moved.message
    calls_before = len(http_mock.calls)

    typed = {"date": "2026-10-09", "start_time": "10:00", "end_time": "11:00"}
    response = browser.post(url, {**typed, "shown": old_shown})

    assert response.status_code == 409
    assert response.context["move_error"] == (
        "Someone else moved this class a moment ago. It's now Thu 8 Oct 2026, 9:00 am to "
        "12:00 pm. We didn't make your change. If it still needs to move, check the time in the "
        "form and press the button again."
    )
    form = response.context["form"]
    assert {name: form[name].value() for name in typed} == typed  # A's typed values kept
    assert len(http_mock.calls) == calls_before  # no Zoom call of any kind
    assert mail.outbox == []
    target.refresh_from_db()
    assert (target.starts_at, target.ends_at, target.moved_by) == (at(8, 9), at(8, 12), user_b)
    # The re-render shows B's time and signs it, so pressing again acts on it.
    assert response.context["occurrence"].starts_at == at(8, 9)
    fresh = _shown(response)
    assert fresh != old_shown
    assert services.read_move_shown(fresh) == {
        target.pk: (int(at(8, 9).timestamp()), int(at(8, 12).timestamp()))
    }

    again = browser.post(url, {**typed, "shown": fresh})
    assert again.status_code == 302, again.context and again.context["move_error"]
    target.refresh_from_db()
    assert (target.starts_at, target.moved_by) == (at(9, 10), user_a)
    assert len(mail.outbox) == 1


# --------------------------------------------------------------------------- series


def _b_moves_the_series(booking, user_b):
    return services.move_series(booking.pk, start_time=clock(9), end_time=clock(12), by=user_b)


def _b_moves_one_listed_class(booking, user_b):
    wed14 = booking.occurrences.get(starts_at=at(14, 8, 30))
    return services.move_class(
        booking.pk, wed14.pk, starts_at=at(14, 13), ends_at=at(14, 14), by=user_b
    )


@pytest.mark.parametrize(
    ("b_moves", "times_now"),
    [
        (_b_moves_the_series, "9:00 am to 12:00 pm"),
        # A one-class move on its own day leaves the booking's times as they were; the series
        # page still showed that class at its old time, so A is still refused.
        (_b_moves_one_listed_class, "8:30 am to 11:30 am"),
    ],
    ids=["b-series", "b-one-class"],
)
def test_a_stale_series_form_is_refused_then_works_again(committed, b_moves, times_now):  # noqa: F811
    user_a, user_b, account, browser = _people(committed)
    booking = _weekly(committed, account, "Race S2")
    url = reverse("zoom:move_series", args=[booking.pk])

    old_shown = _shown(browser.get(url))
    assert b_moves(booking, user_b).outcome == Outcome.MOVED
    before = (list(FakeProvider.busy_calls), list(FakeProvider.patched))
    stored = sorted(booking.occurrences.values_list("pk", "starts_at", "ends_at", "moved_by"))

    typed = {"start_time": "13:00", "end_time": "14:00"}
    response = browser.post(url, {**typed, "shown": old_shown})

    assert response.status_code == 409
    assert response.context["move_error"] == (
        "Someone else changed the time of the remaining classes a moment ago. They're now "
        f"{times_now}. We didn't make your change. If they still need a different time, check "
        "the times in the form and press the button again."
    )
    form = response.context["form"]
    assert {name: form[name].value() for name in typed} == typed
    assert (list(FakeProvider.busy_calls), list(FakeProvider.patched)) == before
    assert mail.outbox == []
    after = sorted(booking.occurrences.values_list("pk", "starts_at", "ends_at", "moved_by"))
    assert after == stored

    again = browser.post(url, {**typed, "shown": _shown(response)})
    assert again.status_code == 302, again.context and again.context["move_error"]
    booking = LinkRequest.objects.get(pk=booking.pk)
    assert (booking.start_time, booking.end_time) == (clock(13), clock(14))
    assert len(mail.outbox) == 1


# --------------------------------------------------------------------------- 33 a failed submit


def test_an_invalid_post_keeps_the_stale_shown_so_the_next_post_is_refused(
    committed,  # noqa: F811
    settings,
    http_mock,
):
    """Criterion 33 (review round 1, B1): a form that fails validation keeps what A was shown.

    Before the fix every re-render signed the current rows into ``shown``, so A's invalid post
    quietly accepted B's move as "seen", and A's next, valid post undid it.
    """
    user_a, user_b, account, browser = _people(committed)
    settings.ZOOM_PROVIDER = "zoom"
    zm.connect(account)
    zm.add_token(http_mock)
    zm.add_listing(http_mock, account.email, [])
    http_mock.add(responses.PATCH, zm.meeting_url(MEETING), status=204)
    booking = _weekly(committed, account, "Race S4")
    target = booking.occurrences.get(starts_at=at(7, 8, 30))
    url = reverse("zoom:move_class", args=[booking.pk, target.pk])

    old_shown = _shown(browser.get(url))  # 1. A opens the form
    moved = services.move_class(  # 2. B moves the same class meanwhile
        booking.pk, target.pk, starts_at=at(8, 9), ends_at=at(8, 12), by=user_b
    )
    assert moved.outcome == Outcome.MOVED, moved.message
    calls_before = len(http_mock.calls)

    # 3. A posts an invalid time: the form error, and the posted shown back exactly as sent.
    invalid = browser.post(
        url, {"date": "2026-10-09", "start_time": "11:00", "end_time": "10:00", "shown": old_shown}
    )
    assert invalid.status_code == 200
    assert "end_time" in invalid.context["form"].errors
    assert _shown(invalid) == old_shown
    assert f'value="{old_shown}"' in str(invalid.context["form"]["shown"])  # the hidden input
    assert len(http_mock.calls) == calls_before

    # 4. A fixes the time and posts that re-rendered form: refused, B's move stands.
    typed = {"date": "2026-10-09", "start_time": "10:00", "end_time": "11:00"}
    response = browser.post(url, {**typed, "shown": _shown(invalid)})
    assert response.status_code == 409
    assert response.context["move_error"] == (
        "Someone else moved this class a moment ago. It's now Thu 8 Oct 2026, 9:00 am to "
        "12:00 pm. We didn't make your change. If it still needs to move, check the time in the "
        "form and press the button again."
    )
    assert len(http_mock.calls) == calls_before  # zero Zoom calls
    assert mail.outbox == []
    target.refresh_from_db()
    assert (target.starts_at, target.ends_at, target.moved_by) == (at(8, 9), at(8, 12), user_b)

    # 5. The 409 page's fresh shown names B's time, so pressing again works.
    again = browser.post(url, {**typed, "shown": _shown(response)})
    assert again.status_code == 302, again.context and again.context["move_error"]
    target.refresh_from_db()
    assert (target.starts_at, target.moved_by) == (at(9, 10), user_a)
    assert len(mail.outbox) == 1


def test_an_invalid_series_post_keeps_the_stale_shown_too(committed):  # noqa: F811
    """Criterion 33, the series form, refused with 1b after a failed submit."""
    user_a, user_b, account, browser = _people(committed)
    booking = _weekly(committed, account, "Race S5")
    url = reverse("zoom:move_series", args=[booking.pk])

    old_shown = _shown(browser.get(url))
    assert _b_moves_the_series(booking, user_b).outcome == Outcome.MOVED
    before = (list(FakeProvider.busy_calls), list(FakeProvider.patched))

    invalid = browser.post(url, {"start_time": "14:00", "end_time": "13:00", "shown": old_shown})
    assert invalid.status_code == 200
    assert "end_time" in invalid.context["form"].errors
    assert _shown(invalid) == old_shown

    typed = {"start_time": "13:00", "end_time": "14:00"}
    response = browser.post(url, {**typed, "shown": _shown(invalid)})
    assert response.status_code == 409
    assert response.context["move_error"] == (
        "Someone else changed the time of the remaining classes a moment ago. They're now "
        "9:00 am to 12:00 pm. We didn't make your change. If they still need a different time, "
        "check the times in the form and press the button again."
    )
    assert (list(FakeProvider.busy_calls), list(FakeProvider.patched)) == before
    assert mail.outbox == []
    booking = LinkRequest.objects.get(pk=booking.pk)
    assert (booking.start_time, booking.end_time) == (clock(9), clock(12))

    again = browser.post(url, {**typed, "shown": _shown(response)})
    assert again.status_code == 302, again.context and again.context["move_error"]
    assert len(mail.outbox) == 1


def test_a_class_cancelled_meanwhile_is_left_out_not_refused(committed):  # noqa: F811
    user_a, user_b, account, browser = _people(committed)
    booking = _weekly(committed, account, "Race S3")
    url = reverse("zoom:move_series", args=[booking.pk])
    wed14 = booking.occurrences.get(starts_at=at(14, 8, 30))

    old_shown = _shown(browser.get(url))
    cancelled = services.cancel(
        booking.pk,
        occurrence_id=wed14.pk,
        by=user_b,
        reason="Sports meet.",
        provider=FakeProvider(),
    )
    assert cancelled.outcome == Outcome.CANCELLED

    response = browser.post(url, {"start_time": "13:00", "end_time": "14:00", "shown": old_shown})

    assert response.status_code == 302, response.context and response.context["move_error"]
    wed14.refresh_from_db()
    assert wed14.cancelled_at is not None and wed14.starts_at == at(14, 8, 30)
    others = booking.occurrences.exclude(pk=wed14.pk)
    assert all(o.starts_at.astimezone(COLOMBO).time() == clock(13) for o in others)
    assert all(o.moved_by == user_a for o in others)
