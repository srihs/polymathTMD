"""Approving with the live Zoom provider (brief 006, criteria 9, 21-31, 32c and 33): the order
of work, the create, every failure's rollback and message, and the compensating delete."""

import json
import logging
from datetime import UTC, date, datetime
from unittest import mock

import pytest
import requests
import responses
from django.contrib.messages import get_messages
from django.core import mail, serializers
from django.core.cache import cache
from django.db import OperationalError, connection
from django.urls import reverse

from apps.zoom import services
from apps.zoom.models import HostAccount, HostSlot, LinkRequest, Occurrence
from apps.zoom.providers import BusyTime, FakeProvider, ManualProvider, ZoomUnavailable

from . import zoommock as zm
from .conftest import COLOMBO, make_account, make_request

pytestmark = pytest.mark.django_db

SAME_MOMENT = "Someone else was approving at the same moment. Nothing was booked. Try again."


@pytest.fixture
def live(settings, account):
    """Zoom 01, connected, with a token and an empty meeting list registered."""
    settings.ZOOM_PROVIDER = "zoom"
    zm.connect(settings, account)
    return account


@pytest.fixture
def zoom_up(http_mock, live):
    zm.add_token(http_mock)
    return http_mock


def _approve(client, link_request, account):
    return client.post(
        reverse("zoom:approve", args=[link_request.pk]), {"host_account": account.pk}
    )


def _nothing_booked(link_request):
    link_request.refresh_from_db()
    assert link_request.status == LinkRequest.Status.WAITING
    assert link_request.meeting_id == "" and link_request.host_account is None
    assert not HostSlot.objects.exists()
    assert not link_request.occurrences.filter(host_account__isnull=False).exists()
    assert mail.outbox == []


def _posts(mock):
    return zm.calls_of(mock, "POST", "/meetings")


def _deletes(mock):
    return zm.calls_of(mock, "DELETE")


def _zoom_tables_dump():
    models = [HostAccount, LinkRequest, Occurrence, HostSlot]
    return "".join(serializers.serialize("json", m.objects.all()) for m in models)


def _weekly():
    return make_request(weekdays="1,3", last_date=date(2026, 10, 28))


def _starts(link_request):
    return [o.starts_at.strftime("%Y-%m-%dT%H:%M:%SZ") for o in link_request.occurrences.all()]


# --------------------------------------------------------------------------- 21 order of work


def test_zoom_is_asked_fresh_before_any_lock_and_the_create_comes_after_the_booking(
    zoom_up, live, it_user, settings
):
    other = make_account("Zoom 02", sort_order=2)
    zm.connect(settings, live, other)
    link_request = make_request()
    # A cached preview for the chosen account must not stand in for the approval's lookup.
    services.remember_preview(live, services.class_window(link_request.occurrences.all()), [])
    log = []

    def listing(request):
        log.append(("HTTP", "GET list", request.url))
        return 200, {}, json.dumps({"meetings": [], "next_page_token": ""})

    def create(request):
        log.append(("HTTP", "POST create", request.url))
        return 201, {}, json.dumps(zm.created_body())

    def record_sql(execute, sql, params, many, context):
        log.append(("SQL", " ".join(sql.split())))
        return execute(sql, params, many, context)

    zoom_up.add_callback("GET", zm.meetings_url(live.email), callback=listing)
    zoom_up.add_callback("GET", zm.meetings_url(other.email), callback=listing)
    zoom_up.add_callback("POST", zm.meetings_url(live.email), callback=create)

    with connection.execute_wrapper(record_sql):
        result = services.approve(link_request.pk, account_id=live.pk, by=it_user)
    assert result.outcome == services.Outcome.APPROVED

    def first(predicate):
        return next(i for i, entry in enumerate(log) if predicate(entry))

    def sql(fragment):
        return lambda entry: entry[0] == "SQL" and fragment in entry[1]

    listed = [entry for entry in log if entry[:2] == ("HTTP", "GET list")]
    assert [entry[2].split("/users/")[1].split("/")[0] for entry in listed] == [live.email]
    list_at = first(lambda e: e[:2] == ("HTTP", "GET list"))
    first_lock = first(sql("FOR UPDATE"))
    assert list_at < first_lock

    def locking(table):
        return lambda e: e[0] == "SQL" and f"FROM `{table}`" in e[1] and "FOR UPDATE" in e[1]

    lock_request = first(locking("zoom_linkrequest"))
    lock_account = first(locking("zoom_hostaccount"))
    lock_classes = first(locking("zoom_occurrence"))
    update_classes = first(sql("UPDATE `zoom_occurrence`"))
    insert_slots = first(sql("INSERT INTO `zoom_hostslot`"))
    [create_at] = [i for i, e in enumerate(log) if e[:2] == ("HTTP", "POST create")]
    update_request = first(sql("UPDATE `zoom_linkrequest`"))
    assert lock_request == first_lock
    assert lock_request < lock_account < lock_classes < update_classes < insert_slots < create_at
    assert create_at < update_request
    # After the request's UPDATE, the only statement is the commit (a savepoint release here,
    # because the test itself runs inside a transaction).
    assert [e[1].split()[0] for e in log[update_request + 1 :]] == ["RELEASE"]


# --------------------------------------------------------------------------- 22 one-off, 9 token


def test_a_one_off_approval_makes_the_meeting_and_keeps_only_what_it_should(
    zoom_up, live, it_client, caplog
):
    link_request = make_request(class_name="Grade 11 Physics")
    zm.add_listing(zoom_up, live.email)
    zm.add_create(zoom_up, live.email)
    with caplog.at_level(logging.DEBUG):
        response = _approve(it_client, link_request, live)

    assert response.status_code == 302
    [post] = _posts(zoom_up)
    assert zm.body(post) == {
        "topic": "Grade 11 Physics",
        "type": 2,
        "start_time": "2026-10-05T08:30:00",
        "timezone": "Asia/Colombo",
        "duration": 180,
        "agenda": f"Polymath TMD {link_request.reference}",
        "settings": {"auto_recording": "none"},
    }
    link_request.refresh_from_db()
    assert link_request.status == LinkRequest.Status.APPROVED
    assert (link_request.meeting_id, link_request.join_url, link_request.passcode) == (
        str(zm.MEETING_ID),
        zm.JOIN_URL,
        zm.PASSCODE,
    )
    assert list(link_request.occurrences.values_list("zoom_occurrence_id", flat=True)) == [""]
    [message] = mail.outbox
    # Brief 011, criterion 28: the host key is in no email any more.
    assert zm.JOIN_URL in message.body and "8421973" not in message.body

    dump = _zoom_tables_dump()
    flashes = " ".join(str(m) for m in get_messages(response.wsgi_request))
    logged = " ".join(record.getMessage() for record in caplog.records)
    for where in (dump, flashes, logged, message.body):
        assert zm.START_URL not in where
        for secret in zm.SECRETS:
            assert secret not in where
    for raw in cache._cache.values():
        assert zm.TOKEN.encode() not in raw


# --------------------------------------------------------------------------- 23, 24 weekly


def test_a_weekly_approval_stores_zooms_occurrence_ids(zoom_up, live, it_user):
    link_request = _weekly()
    zm.add_listing(zoom_up, live.email)
    zm.add_create(zoom_up, live.email, occurrences=_starts(link_request))
    result = services.approve(link_request.pk, account_id=live.pk, by=it_user)
    assert result.outcome == services.Outcome.APPROVED
    [post] = _posts(zoom_up)
    sent = zm.body(post)
    assert (sent["type"], sent["start_time"]) == (8, "2026-10-05T08:30:00")
    assert sent["recurrence"] == {
        "type": 2,
        "repeat_interval": 1,
        "weekly_days": "2,4",
        "end_times": 8,
    }
    ids = list(
        link_request.occurrences.order_by("starts_at").values_list("zoom_occurrence_id", flat=True)
    )
    assert ids == [str(1_759_633_200_000 + n) for n in range(8)]


DATES_DIFFER = (
    "Zoom scheduled different dates from this request, so the meeting was removed from Zoom and "
    "nothing was booked. Tell whoever looks after the system."
)


@pytest.mark.parametrize("change", ["one_fewer", "moved"])
def test_zoom_dates_that_differ_remove_the_meeting_and_book_nothing(
    zoom_up, live, it_client, change
):
    link_request = _weekly()
    starts = _starts(link_request)
    if change == "one_fewer":
        starts = starts[:-1]
    else:
        starts[3] = starts[3].replace("T03:00", "T03:30")
    zm.add_listing(zoom_up, live.email)
    zm.add_create(zoom_up, live.email, occurrences=starts)
    zm.add_delete(zoom_up)

    response = _approve(it_client, link_request, live)
    assert response.status_code == 200
    assert response.context["approve_error"] == DATES_DIFFER
    [delete] = _deletes(zoom_up)
    assert delete.request.url.startswith(zm.meeting_url(zm.MEETING_ID))
    _nothing_booked(link_request)


@pytest.mark.parametrize("junk", ["not a class", 7, ["a", "list"]])
def test_an_unreadable_occurrence_in_zooms_answer_removes_the_meeting_and_books_nothing(
    zoom_up, live, it_client, junk
):
    """Review round 2, SF1: Zoom made the meeting, so an occurrence list this code can't read
    must fall back to "no dates" and criterion 24's removal, not a 500 that strands it."""
    link_request = _weekly()
    body = zm.created_body(occurrences=_starts(link_request))
    body["occurrences"][2] = junk
    zm.add_listing(zoom_up, live.email)
    zm.add_create(zoom_up, live.email, body=body)
    zm.add_delete(zoom_up)

    response = _approve(it_client, link_request, live)
    assert response.status_code == 200
    assert response.context["approve_error"] == DATES_DIFFER
    [delete] = _deletes(zoom_up)
    assert delete.request.url.startswith(zm.meeting_url(zm.MEETING_ID))
    _nothing_booked(link_request)


# --------------------------------------------------------------------------- 25 recording


def test_a_recorded_class_asks_zoom_for_cloud_recording(zoom_up, live, it_user):
    link_request = make_request(wants_recording=True)
    zm.add_listing(zoom_up, live.email)
    zm.add_create(zoom_up, live.email)
    services.approve(link_request.pk, account_id=live.pk, by=it_user)
    assert zm.body(_posts(zoom_up)[0])["settings"] == {"auto_recording": "cloud"}


# --------------------------------------------------------------------------- 26 clash at approval


def test_a_meeting_made_in_zoom_since_the_page_loaded_stops_the_approval(zoom_up, live, it_client):
    link_request = make_request()
    zm.add_listing(zoom_up, live.email)  # the page load: nothing in Zoom yet
    zm.add_listing(
        zoom_up,
        live.email,
        [zm.scheduled(701, "2026-10-05T02:30:00Z", 60, topic="Grade 11 revision")],
    )
    assert it_client.get(reverse("zoom:detail", args=[link_request.pk])).context["free_count"] == 1

    response = _approve(it_client, link_request, live)
    assert response.status_code == 409
    assert response.context["approve_error"] == (
        "Zoom 01 has a meeting in Zoom at an overlapping time: Grade 11 revision, "
        "Mon 5 Oct 2026 at 8:00 am. Choose another free account."
    )
    assert _posts(zoom_up) == []
    _nothing_booked(link_request)
    # The re-render shows the fresh answer, not the page load's cached one.
    [entry] = response.context["availability"]
    assert entry["is_free"] is False and len(entry["zoom_clashes"]) == 1
    assert response.context["approve_form"] is None


def test_a_meeting_with_no_topic_is_named_plainly(zoom_up, live, it_user):
    link_request = make_request()
    zm.add_listing(zoom_up, live.email, [zm.scheduled(701, zm.CLASS_START, 30, topic="")])
    result = services.approve(link_request.pk, account_id=live.pk, by=it_user)
    assert "overlapping time: a meeting with no name, Mon 5 Oct 2026 at 8:30 am." in result.message


# --------------------------------------------------------------------------- 27 leftovers


def test_a_leftover_from_a_failed_attempt_is_removed_before_the_create(zoom_up, live, it_client):
    link_request = make_request()
    leftover = zm.scheduled(777, zm.CLASS_START, 180, agenda=link_request.zoom_marker)
    zm.add_listing(zoom_up, live.email, [leftover])
    zm.add_delete(zoom_up, 777)
    zm.add_create(zoom_up, live.email)

    response = _approve(it_client, link_request, live)
    assert response.status_code == 302
    order = [(c.request.method, c.request.url.split("?")[0]) for c in zoom_up.calls]
    assert ("DELETE", zm.meeting_url(777)) in order
    delete_at = order.index(("DELETE", zm.meeting_url(777)))
    create_at = order.index(("POST", zm.meetings_url(live.email)))
    assert delete_at < create_at
    assert len(_posts(zoom_up)) == 1


def test_if_the_leftover_cant_be_removed_nothing_is_made(zoom_up, live, it_client):
    link_request = make_request()
    leftover = zm.scheduled(777, zm.CLASS_START, 180, agenda=link_request.zoom_marker)
    zm.add_listing(zoom_up, live.email, [leftover])
    zm.add_delete(zoom_up, 777, status=503)

    response = _approve(it_client, link_request, live)
    assert response.status_code == 200
    assert response.context["approve_error"] == (
        "We couldn't check Zoom 01's meetings in Zoom, so nothing was booked. "
        "No answer from Zoom. Try again in a few minutes."
    )
    assert _posts(zoom_up) == []
    _nothing_booked(link_request)


# --------------------------------------------------------------------------- 28 lookup fails

LASTING = (
    "Choose another free account, and ask whoever manages the Zoom accounts to press Check "
    "connection for Zoom 01."
)


@pytest.mark.parametrize(
    ("token_reply", "list_reply", "reason", "next_step"),
    [
        (
            None,
            {"body": requests.exceptions.ConnectionError()},
            "No answer from Zoom.",
            "Try again in a few minutes.",
        ),
        (None, {"status": 429}, "Zoom is busy right now.", "Try again in a few minutes."),
        ({"status": 401}, None, "Zoom didn't accept this account's connection details.", LASTING),
        (
            None,
            {"status": 400, "json": zm.zoom_error(4711)},
            "The Zoom app for this account is missing a permission.",
            LASTING,
        ),
        (
            None,
            {"status": 404, "json": zm.zoom_error(1001)},
            "Zoom has no user with this account's sign-in email.",
            LASTING,
        ),
        (None, {"status": 400, "json": zm.zoom_error(300)}, "Zoom error 300.", LASTING),
    ],
)
def test_if_zoom_cant_be_asked_at_approval_nothing_is_booked(
    http_mock, live, it_client, token_reply, list_reply, reason, next_step
):
    if token_reply:
        http_mock.add(responses.POST, zm.TOKEN_URL, **token_reply)
    else:
        zm.add_token(http_mock)
        http_mock.add(responses.GET, zm.meetings_url(live.email), **list_reply)
    link_request = make_request()

    response = _approve(it_client, link_request, live)
    assert response.status_code == 200
    assert response.context["approve_error"] == (
        f"We couldn't check Zoom 01's meetings in Zoom, so nothing was booked. {reason} {next_step}"
    )
    assert _posts(http_mock) == []
    _nothing_booked(link_request)


@pytest.mark.parametrize(
    "listed",
    [
        lambda marker: [zm.scheduled(701, "garbage", 60)],
        lambda marker: [zm.scheduled(701, "garbage", 60, agenda=marker)],  # even a leftover
        lambda marker: ["not a meeting"],
    ],
    ids=["other-meeting", "own-leftover", "not-an-object"],
)
def test_an_unreadable_zoom_answer_at_approval_is_criterion_28s_message(
    zoom_up, live, it_client, listed
):
    """Review round 1, SF1: ``start_time`` "garbage" stops the approval with the pinned
    message, never a 500, and makes nothing in Zoom."""
    link_request = make_request()
    zm.add_listing(zoom_up, live.email, listed(link_request.zoom_marker))

    response = _approve(it_client, link_request, live)
    assert response.status_code == 200
    assert response.context["approve_error"] == (
        "We couldn't check Zoom 01's meetings in Zoom, so nothing was booked. "
        "No answer from Zoom. Try again in a few minutes."
    )
    assert _posts(zoom_up) == [] and _deletes(zoom_up) == []
    _nothing_booked(link_request)


# --------------------------------------------------------------------------- 29 not connected


def test_an_account_that_isnt_connected_is_refused_without_asking_zoom(
    http_mock, settings, account, it_client
):
    settings.ZOOM_PROVIDER = "zoom"
    link_request = make_request()
    response = _approve(it_client, link_request, account)
    assert response.status_code == 409
    assert response.context["approve_error"] == (
        "Zoom 01 isn't connected to Zoom yet, so it can't be booked. Choose another free "
        "account, or set up its Zoom connection on the Zoom accounts page."
    )
    assert len(http_mock.calls) == 0
    _nothing_booked(link_request)


# --------------------------------------------------------------------------- 30 the create fails


@pytest.mark.parametrize(
    ("reply", "extra_401", "message"),
    [
        (
            {"body": requests.exceptions.ConnectionError()},
            False,
            "We couldn't make the meeting in Zoom: no answer from Zoom. Nothing was booked. "
            "Try again in a few minutes.",
        ),
        (
            {"body": requests.exceptions.ConnectTimeout()},
            False,
            "We couldn't make the meeting in Zoom: no answer from Zoom. Nothing was booked. "
            "Try again in a few minutes.",
        ),
        (
            {"status": 429},
            False,
            "We couldn't make the meeting in Zoom: Zoom is busy right now. Nothing was booked. "
            "Try again in a few minutes.",
        ),
        (
            {"status": 401, "json": {"code": 124}},
            True,
            "We couldn't make the meeting in Zoom: Zoom didn't accept this account's connection "
            f"details. Nothing was booked. {LASTING}",
        ),
        (
            {"status": 400, "json": zm.zoom_error(300)},
            False,
            f"We couldn't make the meeting in Zoom: Zoom error 300. Nothing was booked. {LASTING}",
        ),
    ],
)
def test_a_create_that_certainly_made_nothing(zoom_up, live, it_user, reply, extra_401, message):
    if extra_401:
        zm.add_token(zoom_up, zm.SECOND_TOKEN)
    link_request = make_request()
    zm.add_listing(zoom_up, live.email)
    zoom_up.add(responses.POST, zm.meetings_url(live.email), **reply)

    result = services.approve(link_request.pk, account_id=live.pk, by=it_user)
    assert (result.outcome, result.message) == (services.Outcome.PROVIDER_ERROR, message)
    _nothing_booked(link_request)
    # Certain failures get no clean-up: one list (before), no second list, no delete.
    assert len(zm.calls_of(zoom_up, "GET", "/meetings")) == 1
    assert _deletes(zoom_up) == []
    assert len(_posts(zoom_up)) == (2 if extra_401 else 1)


MAYBE = (
    "We couldn't make the meeting in Zoom: no answer from Zoom, so Zoom may have made it "
    "anyway. Nothing was booked here."
)


@pytest.mark.parametrize(
    "no_answer", [{"body": requests.exceptions.ReadTimeout()}, {"status": 502}]
)
@pytest.mark.parametrize("found", ["removed", "not_found", "list_failed", "delete_failed"])
def test_a_create_with_no_answer_is_cleaned_up_and_the_message_says_what_was_found(
    zoom_up, live, it_user, no_answer, found
):
    link_request = make_request()
    made = zm.scheduled(888, zm.CLASS_START, 180, agenda=link_request.zoom_marker)
    zm.add_listing(zoom_up, live.email)  # before the create
    if found == "list_failed":
        zm.add_listing(zoom_up, live.email, status=503)
    else:
        zm.add_listing(zoom_up, live.email, [] if found == "not_found" else [made])
    zm.add_delete(zoom_up, 888, status=503 if found == "delete_failed" else 204)
    zoom_up.add(responses.POST, zm.meetings_url(live.email), **no_answer)

    result = services.approve(link_request.pk, account_id=live.pk, by=it_user)
    assert result.outcome == services.Outcome.PROVIDER_ERROR
    endings = {
        "removed": " We found it in Zoom 01's Zoom account and removed it. Try again in a few "
        "minutes.",
        "not_found": " We didn't find it in Zoom 01's Zoom account. Try again in a few minutes. "
        "If it turns up there later, the next try removes it before making a new one.",
        "list_failed": " We couldn't check Zoom 01's Zoom account for it. Try again in a few "
        f"minutes. If a meeting for {link_request.reference} is there, the next try removes it "
        "before making a new one.",
    }
    endings["delete_failed"] = endings["list_failed"]
    assert result.message == MAYBE + endings[found]
    _nothing_booked(link_request)
    order = [(c.request.method, c.request.url.split("?")[0]) for c in zoom_up.calls]
    create_at = order.index(("POST", zm.meetings_url(live.email)))
    assert len(_posts(zoom_up)) == 1
    # One list before the create, and exactly one clean-up list after it.
    assert order[:create_at].count(("GET", zm.meetings_url(live.email))) == 1
    assert order[create_at:].count(("GET", zm.meetings_url(live.email))) == 1
    assert len(_deletes(zoom_up)) == (1 if found in ("removed", "delete_failed") else 0)


def test_the_page_shows_the_create_failure_and_refreshed_availability(zoom_up, live, it_client):
    link_request = make_request()
    zm.add_listing(zoom_up, live.email)
    zoom_up.add(responses.POST, zm.meetings_url(live.email), status=429)
    response = _approve(it_client, link_request, live)
    assert response.status_code == 200
    assert response.context["approve_error"] == (
        "We couldn't make the meeting in Zoom: Zoom is busy right now. Nothing was booked. "
        "Try again in a few minutes."
    )
    assert response.context["availability"][0]["zoom_state"] == "checked"
    _nothing_booked(link_request)


def test_an_unreadable_zoom_time_in_the_clean_up_says_it_couldnt_check(zoom_up, live, it_user):
    """Review round 1, SF1, the 30(b) path: a bad ``start_time`` in the clean-up list is
    "couldn't check", not a 500, and nothing is deleted on the strength of it."""
    link_request = make_request()
    unreadable = zm.scheduled(888, "garbage", 180, agenda=link_request.zoom_marker)
    zm.add_listing(zoom_up, live.email)  # before the create
    zm.add_listing(zoom_up, live.email, [unreadable])  # the clean-up's list
    zoom_up.add(responses.POST, zm.meetings_url(live.email), body=requests.exceptions.ReadTimeout())

    result = services.approve(link_request.pk, account_id=live.pk, by=it_user)
    assert (result.outcome, result.message) == (
        services.Outcome.PROVIDER_ERROR,
        MAYBE + " We couldn't check Zoom 01's Zoom account for it. Try again in a few minutes. "
        f"If a meeting for {link_request.reference} is there, the next try removes it before "
        "making a new one.",
    )
    _nothing_booked(link_request)
    assert _deletes(zoom_up) == []


def test_the_clean_up_keeps_a_meeting_another_attempt_booked(zoom_up, live, it_user):
    """If another attempt approved the request meanwhile, its stored meeting is kept."""
    link_request = make_request()
    theirs = zm.scheduled(901, zm.CLASS_START, 180, agenda=link_request.zoom_marker)
    ours = zm.scheduled(902, zm.CLASS_START, 180, agenda=link_request.zoom_marker)
    zm.add_listing(zoom_up, live.email, [theirs, ours])
    zm.add_delete(zoom_up, 902)
    LinkRequest.objects.filter(pk=link_request.pk).update(
        status=LinkRequest.Status.APPROVED,
        meeting_id="901",
        host_account=live,
        join_url="https://x.zoom.us/j/901",
    )
    occurrences = list(link_request.occurrences.all())
    result = services._create_failed(
        ZoomUnavailable(maybe_done=True),
        link_request.pk,
        live,
        occurrences,
        services.get_provider(),
    )
    assert result.message.endswith(
        "We found it in Zoom 01's Zoom account and removed it. Try again in a few minutes."
    )
    assert [c.request.url.split("?")[0] for c in _deletes(zoom_up)] == [zm.meeting_url(902)]


# ------------------------------------------------------------------ 31 save fails after create


def test_a_failed_save_after_the_create_deletes_the_meeting_after_the_rollback(
    zoom_up, live, it_user
):
    link_request = make_request()
    log = []

    def record_sql(execute, sql, params, many, context):
        log.append(("SQL", sql.split()[0]))
        return execute(sql, params, many, context)

    def delete(request):
        log.append(("HTTP", "DELETE"))
        return 204, {}, ""

    zm.add_listing(zoom_up, live.email)
    zm.add_create(zoom_up, live.email)
    zoom_up.add_callback("DELETE", zm.meeting_url(zm.MEETING_ID), callback=delete)
    error = OperationalError(1205, "Lock wait timeout exceeded")
    with (
        mock.patch.object(LinkRequest, "save", side_effect=error),
        connection.execute_wrapper(record_sql),
    ):
        result = services.approve(link_request.pk, account_id=live.pk, by=it_user)

    assert (result.outcome, result.message) == (services.Outcome.CONFLICT, SAME_MOMENT)
    assert log.count(("HTTP", "DELETE")) == 1
    rollback = max(i for i, entry in enumerate(log) if entry == ("SQL", "ROLLBACK"))
    assert log.index(("HTTP", "DELETE")) > rollback
    _nothing_booked(link_request)


def test_a_deadlock_after_the_create_is_retried_with_a_second_create(zoom_up, live, it_user):
    link_request = make_request()
    zm.add_listing(zoom_up, live.email)
    zm.add_create(zoom_up, live.email)
    zm.add_delete(zoom_up)
    real_save = LinkRequest.save
    calls = []

    def deadlock_once(self, *args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise OperationalError(1213, "Deadlock found when trying to get lock")
        return real_save(self, *args, **kwargs)

    with mock.patch.object(LinkRequest, "save", deadlock_once):
        result = services.approve(link_request.pk, account_id=live.pk, by=it_user)
    assert result.outcome == services.Outcome.APPROVED
    assert len(_posts(zoom_up)) == 2
    assert len(_deletes(zoom_up)) == 1
    link_request.refresh_from_db()
    assert link_request.status == LinkRequest.Status.APPROVED


def test_a_meeting_that_cant_be_saved_or_removed_is_named_for_it(zoom_up, live, it_client, caplog):
    link_request = make_request()
    zm.add_listing(zoom_up, live.email)
    zm.add_create(zoom_up, live.email)
    zm.add_delete(zoom_up, status=503)
    error = OperationalError(1205, "Lock wait timeout exceeded")
    with (
        mock.patch.object(LinkRequest, "save", side_effect=error),
        caplog.at_level(logging.DEBUG),
    ):
        response = _approve(it_client, link_request, live)

    assert response.status_code == 200
    assert response.context["approve_error"] == (
        f"Zoom made meeting {zm.MEETING_ID} on Zoom 01, but it couldn't be saved here or removed "
        "from Zoom. Delete that meeting in Zoom, then try again."
    )
    [record] = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert record.getMessage() == (
        f"Zoom meeting {zm.MEETING_ID} on Zoom 01 for {link_request.reference} couldn't be saved "
        "or removed: OperationalError"
    )
    _nothing_booked(link_request)


# --------------------------------------------------------------------------- 32c, 33


def test_approving_again_after_success_makes_no_call(zoom_up, live, it_client):
    link_request = make_request()
    zm.add_listing(zoom_up, live.email)
    zm.add_create(zoom_up, live.email)
    assert _approve(it_client, link_request, live).status_code == 302
    before = len(zoom_up.calls)
    response = _approve(it_client, link_request, live)
    assert response.status_code == 302
    assert [str(m) for m in get_messages(response.wsgi_request)][-1] == (
        "This request has already been decided."
    )
    assert len(zoom_up.calls) == before


def test_the_manual_provider_makes_no_http_call_on_any_path(
    http_mock, settings, account, it_client
):
    settings.ZOOM_PROVIDER = "manual"
    link_request = make_request()
    it_client.get(reverse("zoom:detail", args=[link_request.pk]))
    it_client.post(reverse("zoom:approve", args=[link_request.pk]), {"host_account": account.pk})
    it_client.post(
        reverse("zoom:approve", args=[link_request.pk]),
        {
            "host_account": account.pk,
            "join_url": "https://us02web.zoom.us/j/12345678901",
            "meeting_id": "12345678901",
            "passcode": "abc",
        },
    )
    link_request.refresh_from_db()
    assert link_request.status == LinkRequest.Status.APPROVED
    assert len(http_mock.calls) == 0
    assert ManualProvider().checks_zoom is False


def test_the_fake_provider_can_be_steered_to_a_zoom_clash(account, it_user):
    link_request = make_request()
    FakeProvider.busy = {
        account.pk: [
            BusyTime(
                datetime(2026, 10, 5, 9, 0, tzinfo=COLOMBO).astimezone(UTC),
                datetime(2026, 10, 5, 10, 0, tzinfo=COLOMBO).astimezone(UTC),
                "Held in Zoom",
                "123",
            )
        ]
    }
    result = services.approve(link_request.pk, account_id=account.pk, by=it_user)
    assert result.outcome == services.Outcome.CONFLICT
    assert result.message.startswith("Zoom 01 has a meeting in Zoom at an overlapping time: Held")
    assert FakeProvider.calls == []


def test_the_fake_provider_can_be_steered_to_a_create_with_no_answer(account, it_user):
    FakeProvider.next_error = ZoomUnavailable(maybe_done=True)
    link_request = make_request()
    result = services.approve(link_request.pk, account_id=account.pk, by=it_user)
    assert result.message.startswith(MAYBE)
    assert "We didn't find it in Zoom 01's Zoom account." in result.message
