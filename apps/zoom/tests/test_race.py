"""Concurrent approvals (brief 005, criterion 38b and 38c).

Two threads, each with its own MySQL connection, approve at the same moment. The data has to
be committed for the other connection to see it, so these tests don't run inside the usual
per-test transaction. They also avoid ``transaction=True``: its flush at teardown would wipe the
``IT desk`` group created by the data migration, which later ``--reuse-db`` runs rely on.
Instead they unblock the database, commit their own rows through the ``_tracked_*`` factories
(each row is registered for cleanup the instant it's created, not batched at the end of setup),
and delete exactly those rows afterwards, plus a fixed-prefix backstop sweep (SF5, review
round 1).

pytest-django sets the test database up only when some collected test has a ``django_db``
mark, and nothing here has one. Run on its own, this module would therefore write to the
*development* database. ``committed`` refuses to run unless the connection points at a
``test_`` database, and ``test_committed_rows_go_to_the_test_database`` (marked) makes sure
the test database is set up whenever this module is collected (brief 006, found while
adding ``test_zoom_race.py``).
"""

import threading
import time
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.db import connection, transaction
from django.test import RequestFactory

from apps.zoom import services
from apps.zoom.models import HostAccount, HostSlot, LinkRequest
from apps.zoom.providers import FakeProvider
from apps.zoom.services import Outcome

from .conftest import make_account, make_request


@pytest.fixture
def committed(django_db_setup, django_db_blocker):
    """Real commits on the test database, cleaned up afterwards.

    Rows are registered the instant each one is committed (see the ``_tracked_*`` factories
    below), not batched at the end of a multi-step setup. That way, if a later step in the
    same setup raises, the rows already committed by earlier steps are still known and get
    cleaned up. The ``finally`` block also sweeps by the fixed "Race " class-name/label
    prefix and the "race-it" username as a backstop, in case a row is ever created without
    going through a tracked factory (review round 1, SF5).
    """
    created = {"requests": [], "accounts": [], "users": []}
    assert connection.settings_dict["NAME"].startswith("test_"), (
        "committed rows must go to the test database; collect a django_db-marked test too"
    )
    with django_db_blocker.unblock():
        try:
            yield created
        finally:
            LinkRequest.objects.filter(pk__in=created["requests"]).delete()
            HostAccount.objects.filter(pk__in=created["accounts"]).delete()
            get_user_model().objects.filter(pk__in=created["users"]).delete()
            # Backstop: catches anything a partial setup committed but never registered.
            LinkRequest.objects.filter(class_name__startswith="Race ").delete()
            HostAccount.objects.filter(label__startswith="Race ").delete()
            get_user_model().objects.filter(username="race-it").delete()
            connection.close()


@pytest.mark.django_db
def test_committed_rows_go_to_the_test_database():
    """Its mark makes pytest-django set up the test database for this module's tests."""
    assert connection.settings_dict["NAME"].startswith("test_")


def _run_together(*jobs):
    """Start every job at the same instant on its own thread and connection."""
    barrier = threading.Barrier(len(jobs))
    results = [None] * len(jobs)
    errors = []

    def run(index, job):
        try:
            barrier.wait(timeout=10)
            results[index] = job()
        except Exception as exc:  # surfaced in the main thread below
            errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=run, args=(i, job)) for i, job in enumerate(jobs)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert not errors, errors
    return results


def _approver(link_request, account, user):
    def job():
        result = services.approve(link_request.pk, account_id=account.pk, by=user)
        if result.outcome == Outcome.APPROVED:
            services.send_approved_email(
                RequestFactory().get("/"), result.link_request, result.host_key
            )
        return result

    return job


def _tracked_request(committed, **kwargs):
    """Create a ``LinkRequest`` and register its pk for cleanup the instant it's committed.

    Registering immediately, rather than after every row in a setup has been created, is what
    lets an aborted setup's earlier rows still get cleaned up (SF5).
    """
    link_request = make_request(**kwargs)
    committed["requests"].append(link_request.pk)
    return link_request


def _tracked_account(committed, *args, **kwargs):
    account = make_account(*args, **kwargs)
    committed["accounts"].append(account.pk)
    return account


def _tracked_user(committed, **kwargs):
    user = get_user_model().objects.create_user(**kwargs)
    committed["users"].append(user.pk)
    return user


def _setup(committed):
    user = _tracked_user(committed, username="race-it", password="pw")
    account = _tracked_account(committed, "Race 01", host_key="8421973")
    return user, account


def test_two_overlapping_requests_on_one_account_only_one_wins(committed):
    user, account = _setup(committed)
    first = _tracked_request(
        committed, weekdays="1,3", last_date=date(2026, 10, 28), class_name="Race A"
    )
    second = _tracked_request(
        committed, first_date=date(2026, 10, 7), class_name="Race B"
    )  # overlaps Wed 7

    results = _run_together(_approver(first, account, user), _approver(second, account, user))

    outcomes = sorted(result.outcome for result in results)
    assert outcomes == sorted([Outcome.APPROVED, Outcome.CONFLICT]), [r.message for r in results]
    winner, loser = (first, second) if results[0].outcome == Outcome.APPROVED else (second, first)
    winner.refresh_from_db()
    loser.refresh_from_db()
    assert winner.status == LinkRequest.Status.APPROVED and winner.host_account == account
    assert loser.status == LinkRequest.Status.WAITING
    assert not loser.occurrences.filter(host_account__isnull=False).exists()
    assert not HostSlot.objects.filter(occurrence__link_request=loser).exists()
    assert len(FakeProvider.calls) == 1
    assert len(mail.outbox) == 1


def test_two_approvals_of_the_same_request_make_one_booking_and_one_email(committed):
    user, account = _setup(committed)
    link_request = _tracked_request(committed, class_name="Race C")

    results = _run_together(
        _approver(link_request, account, user), _approver(link_request, account, user)
    )

    assert sorted(r.outcome for r in results) == sorted([Outcome.APPROVED, Outcome.ALREADY_DECIDED])
    assert len(FakeProvider.calls) == 1
    assert len(mail.outbox) == 1
    assert HostSlot.objects.filter(host_account=account).count() == 36


@pytest.mark.parametrize("isolation", ["READ COMMITTED", "REPEATABLE READ"])
def test_taking_an_account_out_of_use_sees_an_approval_that_committed_while_it_waited(
    committed, isolation
):
    """Brief 008 criterion 19, review round 1 B1: the stop check must see a just-approved class.

    Django runs MySQL sessions at READ COMMITTED (its default ``isolation_level``), where every
    statement reads the latest committed rows, so the gap below can't open today. It opens at
    REPEATABLE READ, MySQL's own default, which a settings change could bring back, so the test
    runs at both: the fix must hold whatever the isolation level. Only the edit's connection is
    switched; ``connection.close()`` in the ``committed`` fixture ends that session setting.

    The interleaving the reviewer found, on two real connections:

    1. the edit's transaction takes its REPEATABLE READ snapshot with an ordinary read (under
       ``ATOMIC_REQUESTS`` the login and permission queries do this), while the request is
       still waiting;
    2. ``approve()``, on its own thread, locks the request and the account and books the
       classes on the account, then pauses inside the provider call, still holding the locks;
    3. the edit asks for the account lock (as ``HostAccountUpdateView.get_object`` does) and
       has to wait;
    4. ``approve()`` is let go and commits, so the edit gets the lock;
    5. the edit's check must see the class. If ``zoom_linkrequest`` isn't read with a locking
       read, its status comes from the step-1 snapshot (``waiting``), the join drops the class,
       and the account would be taken out of use with a class booked on it.
    """
    user, account = _setup(committed)
    link_request = _tracked_request(committed, class_name="Race D")
    holding, release = threading.Event(), threading.Event()
    results, errors = [], []

    class PausingProvider(FakeProvider):
        """Pauses ``approve()`` inside its transaction, after the booking, before commit."""

        def create_meeting(self, **kwargs):
            holding.set()
            if not release.wait(timeout=20):
                raise AssertionError("the test never released approve()")
            return super().create_meeting(**kwargs)

    def approver():
        try:
            results.append(
                services.approve(
                    link_request.pk, account_id=account.pk, by=user, provider=PausingProvider()
                )
            )
        except Exception as exc:  # surfaced in the main thread below
            errors.append(exc)
        finally:
            connection.close()

    thread = threading.Thread(target=approver)
    with connection.cursor() as cursor:
        cursor.execute(f"SET SESSION TRANSACTION ISOLATION LEVEL {isolation}")
    try:
        with transaction.atomic():
            # 1. The snapshot: the request is still waiting.
            status = LinkRequest.objects.values_list("status", flat=True).get(pk=link_request.pk)
            assert status == LinkRequest.Status.WAITING
            # 2. approve() books the account and holds its lock.
            thread.start()
            assert holding.wait(timeout=20), errors
            # 4. is scheduled now, so it happens while 3. waits for the lock.
            threading.Timer(0.5, release.set).start()
            started = time.monotonic()
            # 3. The edit locks the account, as the change view does on POST.
            locked = HostAccount.objects.select_for_update().get(pk=account.pk)
            waited = time.monotonic() - started
            # 5. The check.
            stop_errors = locked.stop_booking_errors(is_active=False, is_paid=True)
    finally:
        release.set()
        thread.join(timeout=60)

    assert not errors, errors
    assert [result.outcome for result in results] == [Outcome.APPROVED]
    assert waited >= 0.25, "the edit never waited for approve(), so the race wasn't exercised"
    assert set(stop_errors) == {"is_active"}, (
        "the stop check missed a class approved while it waited for the account lock"
    )
    assert "Race 01 still has 1 booked class" in stop_errors["is_active"]
