"""Brief 011 on committed data: the order of a cancel's work (criterion 10) and cancels racing
with each other and with an approval (criterion 16 a-c).

Like ``test_race.py`` and ``test_zoom_race.py``, these commit real rows on their own
connections, outside the usual per-test transaction, through the ``committed`` fixture, which
deletes exactly what it made. The brief asks for ``transaction=True`` thread tests "as in 005
criterion 38 and 006 criterion 32"; those tests use ``committed`` instead, because
``transaction=True``'s flush would wipe the ``IT desk`` group the data migration made, which
later ``--reuse-db`` runs rely on. Same effect: every thread sees the others' commits.
Zoom is mocked through the project-wide ``responses`` mock, which covers every thread.
"""

import threading
import time
from datetime import date, datetime
from unittest import mock

import pytest
import responses
from django.contrib.messages import get_messages
from django.core import mail
from django.db import connection
from django.test import Client, RequestFactory
from django.urls import reverse

from apps.zoom import services
from apps.zoom.models import LinkRequest, Occurrence
from apps.zoom.providers import FakeProvider
from apps.zoom.services import Outcome

from . import zoommock as zm
from .conftest import COLOMBO, booked_on
from .test_race import (  # noqa: F401  (committed is a fixture)
    _run_together,
    _tracked_account,
    _tracked_request,
    _tracked_user,
    committed,
)

MEETING = "81234567890"
REASON = "The school is closed for the sports meet."


def at(day, hour, minute=0):
    return datetime(2026, 10, day, hour, minute, tzinfo=COLOMBO)


@pytest.mark.django_db
def test_committed_rows_go_to_the_test_database():
    assert connection.settings_dict["NAME"].startswith("test_")


def _setup(committed, settings=None, http_mock=None, *, live=False):  # noqa: F811
    user = _tracked_user(committed, username="race-it", password="pw", email="race@x.example")
    from django.contrib.auth.models import Group

    user.groups.add(Group.objects.get(name="IT desk"))
    account = _tracked_account(committed, "Race 02", host_key="8421973")
    if live:
        settings.ZOOM_PROVIDER = "zoom"
        zm.connect(settings, account)
        zm.add_token(http_mock)
    return user, account


def _weekly(committed, account, name):  # noqa: F811
    link_request = _tracked_request(
        committed,
        weekdays="1,3",
        first_date=date(2026, 10, 5),
        last_date=date(2026, 10, 28),
        class_name=name,
        email="nimal@example.com",
    )
    return booked_on(link_request, account)


def _canceller(link_request_id, user, occurrence_id=None, provider=None):
    def job():
        result = services.cancel(
            link_request_id, occurrence_id=occurrence_id, by=user, reason=REASON, provider=provider
        )
        if result.outcome == Outcome.CANCELLED:
            services.send_cancelled_email(
                RequestFactory().get("/", HTTP_HOST="testserver"),
                result.link_request,
                result.cancelled,
                result.remaining,
                REASON,
            )
        return result

    return job


# --------------------------------------------------------------------------- 10 order of work


def test_a_whole_cancel_locks_writes_calls_zoom_then_commits(committed, settings, http_mock):  # noqa: F811
    user, account = _setup(committed, settings, http_mock, live=True)
    booking = _weekly(committed, account, "Race A")
    log = []

    def zoom_delete(request):
        log.append(("HTTP", f"DELETE {request.url}"))
        return 204, {}, ""

    http_mock.add_callback(responses.DELETE, zm.meeting_url(MEETING), callback=zoom_delete)

    def record_sql(execute, sql, params, many, context):
        log.append(("SQL", sql))
        return execute(sql, params, many, context)

    real_commit = connection.commit

    def commit():
        log.append(("COMMIT", ""))
        return real_commit()

    with (
        connection.execute_wrapper(record_sql),
        mock.patch.object(connection, "commit", side_effect=commit),
    ):
        result = services.cancel(booking.pk, by=user, reason=REASON)
    assert result.outcome == Outcome.CANCELLED

    def first(predicate):
        return next(index for index, entry in enumerate(log) if predicate(entry))

    def sql(*words):
        return lambda entry: entry[0] == "SQL" and all(word in entry[1] for word in words)

    lock_request = first(sql("FROM `zoom_linkrequest`", "FOR UPDATE"))
    lock_account = first(sql("FROM `zoom_hostaccount`", "FOR UPDATE"))
    lock_classes = first(sql("FROM `zoom_occurrence`", "FOR UPDATE"))
    update_classes = first(sql("UPDATE `zoom_occurrence`"))
    delete_slots = first(sql("DELETE FROM `zoom_hostslot`"))
    update_request = first(sql("UPDATE `zoom_linkrequest`"))
    [zoom] = [index for index, entry in enumerate(log) if entry[0] == "HTTP"]
    [commit_at] = [index for index, entry in enumerate(log) if entry[0] == "COMMIT"]
    assert lock_request < lock_account < lock_classes
    assert lock_classes < update_classes < delete_slots < update_request < zoom < commit_at
    # Nothing reached Zoom before the locks, and the token fetch came after them too.
    token = [c for c in http_mock.calls if c.request.url == zm.TOKEN_URL]
    assert len(token) == 1 and len(zm.calls_of(http_mock, "DELETE")) == 1


# --------------------------------------------------------------------------- 16 (a)


def test_two_cancels_of_one_class_make_one_delete_and_one_email(committed, settings, http_mock):  # noqa: F811
    user, account = _setup(committed, settings, http_mock, live=True)
    booking = _weekly(committed, account, "Race B")
    target = booking.occurrences.get(starts_at=at(7, 8, 30))
    zm.add_delete(http_mock, MEETING)
    clients = []
    for _ in range(2):
        client = Client()
        client.force_login(user)
        clients.append(client)
    url = reverse("zoom:cancel_class", args=[booking.pk, target.pk])

    responses_ = _run_together(*[lambda c=c: c.post(url, {"reason": REASON}) for c in clients])

    assert [r.status_code for r in responses_] == [302, 302]
    said = sorted(str(m) for r in responses_ for m in get_messages(r.wsgi_request))
    assert said == [
        "Cancelled the class on Wed 7 Oct 2026. We emailed nimal@example.com.",
        "That class was already cancelled.",
    ]
    assert len(zm.calls_of(http_mock, "DELETE")) == 1
    assert len(mail.outbox) == 1
    target.refresh_from_db()
    assert target.cancelled_at is not None


# --------------------------------------------------------------------------- 16 (b)


def _overlapping_booked(account):
    booked = list(Occurrence.objects.booked().filter(host_account=account))
    return [(a, b) for a in booked for b in booked if a.pk < b.pk and a.overlaps(b)]


def test_a_cancel_and_an_approval_at_the_same_time_never_overlap(committed):  # noqa: F811
    user, account = _setup(committed)
    cancelling = booked_on(
        _tracked_request(committed, first_date=date(2026, 10, 5), class_name="Race C"), account
    )
    approving = _tracked_request(
        committed,
        first_date=date(2026, 10, 5),
        start=datetime(2026, 10, 5, 9, 0).time(),
        end=datetime(2026, 10, 5, 10, 0).time(),
        class_name="Race D",
    )

    def approver():
        return services.approve(approving.pk, account_id=account.pk, by=user)

    cancel_result, approve_result = _run_together(_canceller(cancelling.pk, user), approver)

    assert cancel_result.outcome == Outcome.CANCELLED
    assert approve_result.outcome in (Outcome.APPROVED, Outcome.CONFLICT)
    assert _overlapping_booked(account) == []


def test_when_the_cancel_commits_first_the_approval_succeeds(committed):  # noqa: F811
    user, account = _setup(committed)
    cancelling = booked_on(
        _tracked_request(committed, first_date=date(2026, 10, 5), class_name="Race E"), account
    )
    approving = _tracked_request(
        committed,
        first_date=date(2026, 10, 5),
        start=datetime(2026, 10, 5, 9, 0).time(),
        end=datetime(2026, 10, 5, 10, 0).time(),
        class_name="Race F",
    )
    holding, release = threading.Event(), threading.Event()
    results, errors = {}, []

    class PausingProvider(FakeProvider):
        """Holds ``cancel()`` inside its transaction, at the Zoom delete, until released."""

        def delete_meeting(self, **kwargs):
            holding.set()
            if not release.wait(timeout=20):
                raise AssertionError("the test never released cancel()")
            return super().delete_meeting(**kwargs)

    def run(name, job):
        try:
            results[name] = job()
        except Exception as exc:  # surfaced in the main thread below
            errors.append(exc)
        finally:
            connection.close()

    cancel_thread = threading.Thread(
        target=run, args=("cancel", _canceller(cancelling.pk, user, provider=PausingProvider()))
    )
    approve_thread = threading.Thread(
        target=run,
        args=("approve", lambda: services.approve(approving.pk, account_id=account.pk, by=user)),
    )
    cancel_thread.start()
    try:
        assert holding.wait(timeout=20), errors
        started = time.monotonic()
        approve_thread.start()
        time.sleep(0.5)  # the approval is now waiting for the account's lock
        assert "approve" not in results, "the approval didn't wait for the cancel's locks"
    finally:
        release.set()
        cancel_thread.join(timeout=60)
        approve_thread.join(timeout=60)
    assert not errors, errors
    assert time.monotonic() - started >= 0.5
    assert results["cancel"].outcome == Outcome.CANCELLED
    assert results["approve"].outcome == Outcome.APPROVED, results["approve"].message
    assert _overlapping_booked(account) == []


# --------------------------------------------------------------------------- 16 (c)


def test_a_whole_cancel_and_a_class_cancel_at_once(committed, settings, http_mock):  # noqa: F811
    user, account = _setup(committed, settings, http_mock, live=True)
    booking = _weekly(committed, account, "Race G")
    target = booking.occurrences.get(starts_at=at(7, 8, 30))
    zm.add_delete(http_mock, MEETING)

    whole, one = _run_together(
        _canceller(booking.pk, user), _canceller(booking.pk, user, occurrence_id=target.pk)
    )

    assert whole.outcome == Outcome.CANCELLED
    assert one.outcome in (Outcome.CANCELLED, Outcome.NOTHING_TO_DO)
    deletes = zm.calls_of(http_mock, "DELETE")
    meeting_deletes = [c for c in deletes if "occurrence_id" not in zm.query(c)]
    class_deletes = [c for c in deletes if "occurrence_id" in zm.query(c)]
    assert len(meeting_deletes) == 1 and len(class_deletes) <= 1
    booking.refresh_from_db()
    assert booking.status == LinkRequest.Status.CANCELLED
    assert not booking.occurrences.filter(cancelled_at__isnull=True).exists()
