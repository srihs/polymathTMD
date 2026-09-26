"""The request detail's availability with Zoom (brief 006, criteria 13 and 15-20): the Zoom
states per account, the context contract (G1, G2, G3, G6), the deadline, the 60-second cache
and the no-transaction rule. Most tests steer ``FakeProvider``; the cache and the query-count
tests use the live provider against mocked Zoom."""

import pickle
import threading
import time as clock
from datetime import UTC, date, datetime, time, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import resolve, reverse
from django.utils import timezone

from apps.zoom import services
from apps.zoom.models import LinkRequest
from apps.zoom.providers import (
    BusyTime,
    FakeProvider,
    ProviderError,
    ZoomAuthFailed,
    ZoomBusy,
    ZoomMissingScope,
    ZoomRejected,
    ZoomUnavailable,
    ZoomUserNotFound,
)

from . import zoommock as zm
from .conftest import COLOMBO, FROZEN_NOW, book, make_account, make_request

pytestmark = pytest.mark.django_db


def _busy(day, start, end, topic="Old booking", meeting_id="700", agenda=""):
    return BusyTime(
        datetime.combine(day, start, tzinfo=COLOMBO).astimezone(UTC),
        datetime.combine(day, end, tzinfo=COLOMBO).astimezone(UTC),
        topic,
        meeting_id,
        agenda,
    )


def _detail(client, link_request):
    response = client.get(reverse("zoom:detail", args=[link_request.pk]))
    assert response.status_code == 200
    return response.context


def _entries(context):
    return {entry["account"].label: entry for entry in context["availability"]}


@pytest.fixture
def four(account):
    """Zoom 01 free, Zoom 02 busy in Zoom, Zoom 03 unchecked, Zoom 04 not connected."""
    busy = make_account("Zoom 02", sort_order=2)
    unchecked = make_account("Zoom 03", sort_order=3)
    unconnected = make_account("Zoom 04", sort_order=4)
    return account, busy, unchecked, unconnected


@pytest.fixture
def reviewer_only(db):
    """Can review requests but not change accounts, so gets no fix links (G1)."""
    user = get_user_model().objects.create_user(username="reviewer", password="pw")
    user.user_permissions.add(Permission.objects.get(codename="review_linkrequest"))
    return user


# --------------------------------------------------------------------------- 15 states


def test_each_account_has_a_zoom_state_and_only_a_checked_free_one_is_offered(it_client, four):
    free, busy, unchecked, unconnected = four
    link_request = make_request(weekdays="1,3", last_date=date(2026, 10, 28))
    later = _busy(date(2026, 10, 12), time(9, 0), time(10, 0), "Grade 11 revision", "701")
    second = _busy(date(2026, 10, 5), time(11, 0), time(12, 0), "<b>Late</b>", "702")
    first = _busy(date(2026, 10, 5), time(8, 0), time(9, 0), "", "703")
    FakeProvider.busy = {busy.pk: [later, second, first]}  # reverse order on purpose (G2)
    FakeProvider.unavailable = {unchecked.pk: ZoomBusy()}
    FakeProvider.not_connected = {unconnected.pk}

    context = _detail(it_client, link_request)
    entries = _entries(context)

    assert {label: e["zoom_state"] for label, e in entries.items()} == {
        "Zoom 01": "checked",
        "Zoom 02": "checked",
        "Zoom 03": "unavailable",
        "Zoom 04": "not_connected",
    }
    assert [e["is_free"] for e in context["availability"]] == [True, False, False, False]
    assert {label: e["zoom_problem"] for label, e in entries.items()} == {
        "Zoom 01": "",
        "Zoom 02": "",
        "Zoom 03": "Zoom is busy right now.",
        "Zoom 04": "",
    }
    clashes = entries["Zoom 02"]["zoom_clashes"]
    occurrences = context["occurrences"]
    assert [(c["occurrence"], c["busy"]) for c in clashes] == [
        (occurrences[0], first),
        (occurrences[0], second),
        (occurrences[2], later),
    ]
    assert entries["Zoom 02"]["busy_count"] == 2
    assert entries["Zoom 02"]["clashes"] == []
    assert all(e["account_edit_allowed"] is True for e in context["availability"])
    assert all(e["has_host_key"] is (e["account"] == free) for e in context["availability"])

    assert context["free_count"] == 1
    assert context["checks_zoom"] is True
    assert context["zoom_checked_at"] == FROZEN_NOW
    assert context["all_unchecked"] is False
    choices = context["approve_form"].fields["host_account"].widget.choices
    assert [choice[0].value for choice in choices] == [free.pk]
    # No lookup was made for the account that isn't connected.
    assert sorted(FakeProvider.busy_calls) == sorted([free.pk, busy.pk, unchecked.pk])


def test_the_fix_link_flag_is_false_without_the_change_permission(client, four, reviewer_only):
    _, busy, unchecked, unconnected = four
    FakeProvider.busy = {busy.pk: [_busy(date(2026, 10, 5), time(9, 0), time(10, 0))]}
    FakeProvider.unavailable = {unchecked.pk: ZoomUnavailable()}
    FakeProvider.not_connected = {unconnected.pk}
    client.force_login(reviewer_only)
    context = _detail(client, make_request())
    states = {e["zoom_state"] for e in context["availability"]}
    assert states == {"checked", "unavailable", "not_connected"}
    assert all(e["account_edit_allowed"] is False for e in context["availability"])


@pytest.mark.parametrize(
    ("error", "sentence"),
    [
        (ZoomUnavailable(), "No answer from Zoom."),
        (ZoomBusy(), "Zoom is busy right now."),
        (ZoomAuthFailed(), "Zoom didn't accept this account's connection details."),
        (ZoomMissingScope(), "The Zoom app for this account is missing a permission."),
        (ZoomUserNotFound(), "Zoom has no user with this account's sign-in email."),
        (ZoomRejected(300), "Zoom error 300."),
    ],
)
def test_zoom_problem_is_the_reason_as_a_sentence(it_client, account, error, sentence):
    FakeProvider.unavailable = {account.pk: error}
    [entry] = _detail(it_client, make_request())["availability"]
    assert (entry["zoom_state"], entry["zoom_problem"], entry["is_free"]) == (
        "unavailable",
        sentence,
        False,
    )


def test_a_class_busy_in_both_places_counts_once(it_client, account, it_user):
    book(make_request(start=time(9, 0), end=time(10, 0), class_name="Holder"), account, it_user)
    link_request = make_request()
    FakeProvider.busy = {account.pk: [_busy(date(2026, 10, 5), time(10, 0), time(11, 0))]}
    [entry] = _detail(it_client, link_request)["availability"]
    assert len(entry["clashes"]) == 1 and len(entry["zoom_clashes"]) == 1
    assert entry["busy_count"] == 1


# --------------------------------------------------------------------------- 13 known meetings


def test_a_meeting_the_app_booked_is_not_shown_twice(it_client, account, it_user):
    holder = book(make_request(start=time(9, 0), end=time(10, 0), class_name="Holder"), account)
    link_request = make_request()
    FakeProvider.busy = {
        account.pk: [
            _busy(date(2026, 10, 5), time(9, 0), time(10, 0), meeting_id=holder.meeting_id)
        ]
    }
    [entry] = _detail(it_client, link_request)["availability"]
    assert len(entry["clashes"]) == 1
    assert entry["zoom_clashes"] == []


def test_this_requests_marker_is_never_a_clash_but_anothers_is(it_client, account):
    link_request = make_request()
    other = LinkRequest(pk=link_request.pk + 1000)
    FakeProvider.busy = {
        account.pk: [
            _busy(
                date(2026, 10, 5),
                time(9, 0),
                time(10, 0),
                "Leftover",
                "801",
                agenda=link_request.zoom_marker,
            ),
            _busy(
                date(2026, 10, 5),
                time(10, 0),
                time(11, 0),
                "Someone else's",
                "802",
                agenda=other.zoom_marker,
            ),
        ]
    }
    [entry] = _detail(it_client, link_request)["availability"]
    assert [c["busy"].meeting_id for c in entry["zoom_clashes"]] == ["802"]


def test_the_marker_matches_its_own_reference_only():
    link_request = LinkRequest(pk=1234)
    assert link_request.zoom_marker == "Polymath TMD ZL-1234"
    assert link_request.agenda_has_marker("Made by Polymath TMD ZL-1234.")
    assert not link_request.agenda_has_marker("Polymath TMD ZL-12345")
    assert not link_request.agenda_has_marker("")
    assert LinkRequest(pk=42).zoom_marker == "Polymath TMD ZL-0042"


# --------------------------------------------------------------------------- 17 nothing checked


def test_when_no_account_could_be_checked_nothing_can_be_approved(it_client, four):
    free, busy, unchecked, unconnected = four
    FakeProvider.unavailable = {a.pk: ZoomUnavailable() for a in (free, busy, unchecked)}
    FakeProvider.not_connected = {unconnected.pk}
    context = _detail(it_client, make_request())
    assert context["all_unchecked"] is True
    assert context["approve_form"] is None
    assert context["reject_form"] is not None
    assert context["has_started"] is False
    assert context["zoom_checked_at"] is None
    assert context["free_count"] == 0


def test_a_started_request_keeps_has_started_when_nothing_was_checked(it_client, account):
    """G3: the page shows the started notice first, so ``has_started`` must be there."""
    FakeProvider.unavailable = {account.pk: ZoomBusy()}
    started = make_request(first_date=date(2026, 9, 28), start=time(9, 0), end=time(11, 0))
    context = _detail(it_client, started)
    assert (context["has_started"], context["all_unchecked"], context["approve_form"]) == (
        True,
        True,
        None,
    )


def test_checked_but_none_free_is_not_all_unchecked(it_client, account):
    FakeProvider.busy = {account.pk: [_busy(date(2026, 10, 5), time(9, 0), time(10, 0))]}
    context = _detail(it_client, make_request())
    assert (context["all_unchecked"], context["free_count"], context["approve_form"]) == (
        False,
        0,
        None,
    )


def test_no_accounts_at_all_is_not_all_unchecked(it_client):
    context = _detail(it_client, make_request())
    assert (context["availability"], context["all_unchecked"]) == ([], False)


# --------------------------------------------------------------------------- 18 manual mode


def test_manual_mode_asks_nothing_and_every_entry_is_off(it_client, account, settings, http_mock):
    settings.ZOOM_PROVIDER = "manual"
    zm.connect(settings, account)
    context = _detail(it_client, make_request())
    [entry] = context["availability"]
    assert (entry["zoom_state"], entry["zoom_clashes"], entry["zoom_problem"]) == ("off", [], "")
    assert entry["is_free"] is True and entry["account_edit_allowed"] is True
    assert context["checks_zoom"] is False
    assert context["zoom_checked_at"] is None and context["all_unchecked"] is False
    assert len(http_mock.calls) == 0


# --------------------------------------------------------------------------- 19 speed and freshness


def test_an_account_with_no_answer_by_the_deadline_is_unavailable(it_client, account, monkeypatch):
    monkeypatch.setattr(services, "PREVIEW_DEADLINE_SECONDS", 0.2)
    FakeProvider.delay = 1.0
    started = clock.monotonic()
    [entry] = _detail(it_client, make_request())["availability"]
    assert clock.monotonic() - started < 0.9  # the page didn't wait for the slow answer
    assert (entry["zoom_state"], entry["zoom_problem"]) == ("unavailable", "No answer from Zoom.")


def test_at_most_six_lookups_run_at_once(account):
    for number in range(2, 10):
        make_account(f"Zoom {number:02d}", sort_order=number)
    running, most, lock = [0], [0], threading.Lock()

    class Counting(FakeProvider):
        def busy_times(self, **kwargs):
            with lock:
                running[0] += 1
                most[0] = max(most[0], running[0])
            clock.sleep(0.2)
            with lock:
                running[0] -= 1
            return []

    link_request = make_request()
    result = services.availability(
        link_request, link_request.occurrences.all(), provider=Counting()
    )
    assert len(result.entries) == 9
    assert all(entry["zoom_state"] == "checked" for entry in result.entries)
    assert most[0] == 6


def test_an_unexpected_failure_in_a_lookup_fails_closed(it_client, account):
    class Broken(FakeProvider):
        def busy_times(self, **kwargs):
            raise KeyError("start_time")

    link_request = make_request()
    result = services.availability(link_request, link_request.occurrences.all(), provider=Broken())
    [entry] = result.entries
    assert (entry["zoom_state"], entry["is_free"]) == ("unavailable", False)


@pytest.fixture
def live_zoom(settings, account):
    settings.ZOOM_PROVIDER = "zoom"
    zm.connect(settings, account)
    return account


def test_two_loads_within_60_seconds_ask_zoom_once(it_client, live_zoom, http_mock, monkeypatch):
    zm.add_token(http_mock)
    zm.add_listing(http_mock, live_zoom.email, [zm.scheduled(701, zm.CLASS_START, 60)])
    link_request = make_request()

    first = _detail(it_client, link_request)
    assert len(zm.calls_of(http_mock, "GET", "/meetings")) == 1
    [entry] = first["availability"]
    assert entry["zoom_state"] == "checked" and len(entry["zoom_clashes"]) == 1

    monkeypatch.setattr(
        timezone, "now", lambda: (FROZEN_NOW + timedelta(seconds=59)).astimezone(UTC)
    )
    second = _detail(it_client, link_request)
    assert len(zm.calls_of(http_mock, "GET", "/meetings")) == 1
    assert second["zoom_checked_at"] == FROZEN_NOW  # the time Zoom was actually asked

    later = FROZEN_NOW + timedelta(seconds=61)
    monkeypatch.setattr(timezone, "now", lambda: later.astimezone(UTC))
    third = _detail(it_client, link_request)
    assert len(zm.calls_of(http_mock, "GET", "/meetings")) == 2
    assert third["zoom_checked_at"] == later

    # The cache holds busy times and topics only: never a token or a credential.
    for raw in cache._cache.values():
        for secret in zm.SECRETS:
            assert secret.encode() not in raw
        assert b"BusyTime" in raw or b"zoom" not in raw


def test_a_failed_lookup_is_not_cached(it_client, live_zoom, http_mock):
    zm.add_token(http_mock)
    zm.add_listing(http_mock, live_zoom.email, status=503)
    zm.add_listing(http_mock, live_zoom.email)
    link_request = make_request()
    assert _detail(it_client, link_request)["availability"][0]["zoom_state"] == "unavailable"
    assert _detail(it_client, link_request)["availability"][0]["zoom_state"] == "checked"


def test_the_cache_is_per_account_and_window(live_zoom):
    other = make_account("Zoom 02")
    window = (FROZEN_NOW, FROZEN_NOW + timedelta(hours=1))
    services.remember_preview(live_zoom, window, [])
    assert services._cached_preview(live_zoom, window) is not None
    assert services._cached_preview(other, window) is None
    assert (
        services._cached_preview(live_zoom, (window[0], window[1] + timedelta(minutes=5))) is None
    )
    live_zoom.email = "changed@polymath.example"
    assert services._cached_preview(live_zoom, window) is None


# --------------------------------------------------------------------------- 20 no transaction


def test_the_detail_and_reject_views_are_non_atomic():
    for name in ("zoom:detail", "zoom:approve", "zoom:reject"):
        view = resolve(reverse(name, args=[1])).func
        assert "default" in getattr(view, "_non_atomic_requests", set()), name


def test_the_query_count_does_not_depend_on_how_many_meetings_zoom_has(
    it_client, live_zoom, http_mock
):
    link_request = make_request()

    def count(meetings):
        cache.clear()
        http_mock.reset()
        zm.add_token(http_mock)
        zm.add_listing(
            http_mock,
            live_zoom.email,
            [zm.scheduled(900 + n, zm.CLASS_START, 30, topic=f"M{n}") for n in range(meetings)],
        )
        with CaptureQueriesContext(connection) as queries:
            context = _detail(it_client, link_request)
        assert len(context["availability"][0]["zoom_clashes"]) == meetings
        return len(queries)

    assert count(1) == count(50)


def test_provider_errors_are_what_the_preview_catches():
    assert issubclass(ZoomBusy, ProviderError) and issubclass(ZoomRejected, ProviderError)


def test_pickled_busy_times_carry_no_link(account):
    busy = _busy(date(2026, 10, 5), time(9, 0), time(10, 0))
    assert b"zoom.us" not in pickle.dumps(busy)
