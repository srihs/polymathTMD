"""Brief 012 on committed data: the order of a move's work (criterion 8) and moves racing with
each other, with an approval and with a cancel (criterion 17 a-c).

Like ``test_cancel_race.py``, these commit real rows on their own connections through the
``committed`` fixture, which deletes exactly what it made, so every thread sees the others'
commits. Zoom is mocked through the project-wide ``responses`` mock, which covers every thread.
The races are made deterministic where the brief's outcome depends on who goes first: a
provider that pauses inside the first move's transaction holds it there until the second has
started waiting for the locks.
"""

import json
import threading
import time
from datetime import UTC, date, datetime
from datetime import time as clock
from unittest import mock

import pytest
import responses
from django.core import mail
from django.db import connection
from django.test import RequestFactory

from apps.zoom import services
from apps.zoom.models import LinkRequest, Occurrence
from apps.zoom.providers import FakeProvider
from apps.zoom.services import Outcome

from . import zoommock as zm
from .conftest import COLOMBO, booked_on
from .test_cancel_race import _setup
from .test_race import (  # noqa: F401  (committed is a fixture)
    _run_together,
    _tracked_request,
    committed,
)

MEETING = "81234567890"
REASON = "The school is closed for the sports meet."


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


def _logged(log):
    """Record every SQL statement, HTTP call and commit, in order, into ``log``."""

    def record_sql(execute, sql, params, many, context):
        log.append(("SQL", sql))
        return execute(sql, params, many, context)

    real_commit = connection.commit

    def commit():
        log.append(("COMMIT", ""))
        return real_commit()

    return (
        connection.execute_wrapper(record_sql),
        mock.patch.object(connection, "commit", side_effect=commit),
    )


def _index(log):
    def first(predicate, start=0):
        return next(i for i, entry in enumerate(log) if i >= start and predicate(entry))

    def sql(*words):
        return lambda entry: entry[0] == "SQL" and all(word in entry[1] for word in words)

    def http(text):
        return lambda entry: entry[0] == "HTTP" and text in entry[1]

    return first, sql, http


def _answer(log, method, status=204, body=""):
    def reply(request):
        log.append(("HTTP", f"{method} {request.url}"))
        return status, {}, body

    return reply


# --------------------------------------------------------------------------- 8 order of work


def test_a_move_asks_zoom_then_locks_writes_patches_then_commits(committed, settings, http_mock):  # noqa: F811
    user, account = _setup(committed, settings, http_mock, live=True)
    booking = _weekly(committed, account, "Race M1")
    target = booking.occurrences.get(starts_at=at(7, 8, 30))
    log = []
    list_body = '{"meetings": [], "next_page_token": ""}'
    http_mock.add_callback(
        responses.GET, zm.meetings_url(account.email), callback=_answer(log, "LIST", 200, list_body)
    )
    http_mock.add_callback(responses.PATCH, zm.meeting_url(MEETING), callback=_answer(log, "PATCH"))
    sql_wrapper, commit_patch = _logged(log)
    with sql_wrapper, commit_patch:
        result = services.move_class(
            booking.pk, target.pk, starts_at=at(8, 9), ends_at=at(8, 12), by=user
        )
    assert result.outcome == Outcome.MOVED, result.message

    first, sql, http = _index(log)
    listed = first(http("LIST"))
    lock_request = first(sql("FROM `zoom_linkrequest`", "FOR UPDATE"))
    lock_account = first(sql("FROM `zoom_hostaccount`", "FOR UPDATE"))
    lock_classes = first(sql("FROM `zoom_occurrence`", "FOR UPDATE"))
    recheck = first(sql("FROM `zoom_occurrence`", "FOR UPDATE"), lock_classes + 1)
    delete_slots = first(sql("DELETE FROM `zoom_hostslot`"))
    insert_slots = first(sql("INSERT INTO `zoom_hostslot`"))
    update_class = first(sql("UPDATE `zoom_occurrence`"))
    [patch] = [i for i, entry in enumerate(log) if entry[0] == "HTTP" and "PATCH" in entry[1]]
    [commit_at] = [i for i, entry in enumerate(log) if entry[0] == "COMMIT"]
    assert listed < lock_request < lock_account < lock_classes < recheck
    assert recheck < delete_slots < insert_slots < update_class < patch < commit_at
    # The list was fresh (no preview cache) and spanned the new times.
    [list_call] = zm.calls_of(http_mock, "GET", "/meetings")
    assert list_call.request.url.startswith(zm.meetings_url(account.email))


def test_a_series_move_adds_the_read_back_and_the_deletes_before_the_commit(
    committed,  # noqa: F811
    settings,
    http_mock,
):
    user, account = _setup(committed, settings, http_mock, live=True)
    booking = _weekly(committed, account, "Race M2")
    mon12 = booking.occurrences.get(starts_at=at(12, 8, 30))
    services.cancel(
        booking.pk, occurrence_id=mon12.pk, by=user, reason=REASON, provider=FakeProvider()
    )
    log = []
    zm.add_listing(http_mock, account.email, [])
    http_mock.add_callback(responses.PATCH, zm.meeting_url(MEETING), callback=_answer(log, "PATCH"))
    starts = [at(day, 9) for day in (5, 7, 12, 14, 19, 21, 26, 28)]
    series = json.dumps(
        {
            "id": int(MEETING),
            "occurrences": [
                {
                    "occurrence_id": f"90{i}",
                    "start_time": start.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    # Zoom sends each class's length; the read-back checks ends too (c. 32).
                    "duration": 180,
                    "status": "available",
                }
                for i, start in enumerate(starts)
            ],
        }
    )
    http_mock.add_callback(
        responses.GET, zm.meeting_url(MEETING), callback=_answer(log, "GET", 200, series)
    )
    http_mock.add_callback(
        responses.DELETE, zm.meeting_url(MEETING), callback=_answer(log, "DELETE")
    )
    sql_wrapper, commit_patch = _logged(log)
    with sql_wrapper, commit_patch:
        result = services.move_series(booking.pk, start_time=clock(9), end_time=clock(12), by=user)
    assert result.outcome == Outcome.MOVED, result.message

    first, sql, http = _index(log)
    update_classes = first(sql("UPDATE `zoom_occurrence`"))
    update_request = first(sql("UPDATE `zoom_linkrequest`"))
    [patch] = [i for i, e in enumerate(log) if e[0] == "HTTP" and "PATCH" in e[1]]
    gets = [i for i, e in enumerate(log) if e[0] == "HTTP" and e[1].startswith("GET")]
    deletes = [i for i, e in enumerate(log) if e[0] == "HTTP" and "DELETE" in e[1]]
    [commit_at] = [i for i, e in enumerate(log) if e[0] == "COMMIT"]
    assert len(gets) == 1 and len(deletes) == 1 and "occurrence_id=902" in log[deletes[0]][1]
    assert update_classes < update_request < patch < gets[0] < deletes[0] < commit_at


# --------------------------------------------------------------------------- 17 (a)


def test_two_moves_of_one_class_commit_one_time(committed):  # noqa: F811
    user, account = _setup(committed)
    booking = _weekly(committed, account, "Race M3")
    target = booking.occurrences.get(starts_at=at(7, 8, 30))
    # Both pages showed the class at its old time (criterion 30's ``shown``).
    shown = services.read_move_shown(LinkRequest.move_fingerprint([target]))
    holding, release = threading.Event(), threading.Event()
    results, errors = {}, []

    class PausingProvider(FakeProvider):
        """Holds the first move inside its transaction, at the Zoom update, until released."""

        def update_occurrence(self, **kwargs):
            holding.set()
            if not release.wait(timeout=20):
                raise AssertionError("the test never released the first move")
            return super().update_occurrence(**kwargs)

    def run(name, **kwargs):
        try:
            results[name] = services.move_class(
                booking.pk, target.pk, by=user, shown=shown, **kwargs
            )
        except Exception as exc:  # surfaced in the main thread below
            errors.append(exc)
        finally:
            connection.close()

    first = threading.Thread(
        target=run,
        args=("first",),
        kwargs={"starts_at": at(8, 9), "ends_at": at(8, 12), "provider": PausingProvider()},
    )
    second = threading.Thread(
        target=run, args=("second",), kwargs={"starts_at": at(9, 9), "ends_at": at(9, 12)}
    )
    first.start()
    try:
        assert holding.wait(timeout=20), errors
        second.start()
        time.sleep(0.5)  # the second move is now waiting for the request's lock
        assert "second" not in results, "the second move didn't wait for the first's locks"
    finally:
        release.set()
        first.join(timeout=60)
        second.join(timeout=60)
    assert not errors, errors
    assert results["first"].outcome == Outcome.MOVED
    assert results["second"].outcome == Outcome.CONFLICT
    assert results["second"].message.startswith("Someone else moved this class a moment ago")
    assert [p["starts_at"] for p in FakeProvider.patched] == [at(8, 9)]
    target.refresh_from_db()
    assert (target.starts_at, target.ends_at) == (at(8, 9), at(8, 12))


# --------------------------------------------------------------------------- 17 (b)


def _overlapping_booked(account):
    booked = list(Occurrence.objects.booked().filter(host_account=account))
    return [(a, b) for a in booked for b in booked if a.pk < b.pk and a.overlaps(b)]


def test_a_move_and_an_approval_into_the_same_time_never_overlap(committed):  # noqa: F811
    user, account = _setup(committed)
    booking = _weekly(committed, account, "Race M4")
    target = booking.occurrences.get(starts_at=at(7, 8, 30))
    approving = _tracked_request(
        committed,
        first_date=date(2026, 10, 8),
        start=clock(10),
        end=clock(11),
        class_name="Race M5",
    )

    def mover():
        return services.move_class(
            booking.pk, target.pk, starts_at=at(8, 9), ends_at=at(8, 12), by=user
        )

    def approver():
        return services.approve(approving.pk, account_id=account.pk, by=user)

    moved, approved = _run_together(mover, approver)

    outcomes = sorted([moved.outcome, approved.outcome])
    assert outcomes in (
        sorted([Outcome.MOVED, Outcome.CONFLICT]),
        sorted([Outcome.CONFLICT, Outcome.APPROVED]),
    ), (moved.message, approved.message)
    assert _overlapping_booked(account) == []


# --------------------------------------------------------------------------- 17 (c)


def test_a_move_and_a_cancel_of_one_class_at_once(committed):  # noqa: F811
    user, account = _setup(committed)
    booking = _weekly(committed, account, "Race M6")
    target = booking.occurrences.get(starts_at=at(7, 8, 30))
    request = RequestFactory().get("/", HTTP_HOST="testserver")

    def mover():
        result = services.move_class(
            booking.pk,
            target.pk,
            starts_at=at(8, 9),
            ends_at=at(8, 12),
            by=user,
            shown=services.read_move_shown(LinkRequest.move_fingerprint([target])),
        )
        if result.outcome == Outcome.MOVED:
            services.send_moved_email(request, result.link_request, result.moves)
        return result

    def canceller():
        result = services.cancel(booking.pk, occurrence_id=target.pk, by=user, reason=REASON)
        if result.outcome == Outcome.CANCELLED:
            services.send_cancelled_email(
                request, result.link_request, result.cancelled, result.remaining, REASON
            )
        return result

    moved, cancelled = _run_together(mover, canceller)

    target.refresh_from_db()
    committed_actions = [moved.outcome == Outcome.MOVED, cancelled.outcome == Outcome.CANCELLED]
    assert len(mail.outbox) == sum(committed_actions)
    if target.cancelled_at is None:
        # The move won and the cancel lost: it's moved and not cancelled.
        assert moved.outcome == Outcome.MOVED and target.starts_at == at(8, 9)
    else:
        # The cancel won: the move either lost with the pinned message, or went first.
        assert cancelled.outcome == Outcome.CANCELLED
        if moved.outcome != Outcome.MOVED:
            assert (moved.outcome, moved.message) == (
                Outcome.NOTHING_TO_DO,
                "That class was cancelled.",
            )
