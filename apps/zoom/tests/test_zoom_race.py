"""Brief 006 on committed data: approvals racing with the live provider (criterion 32 a, b) and
no transaction held open while Zoom is asked (criterion 20).

Like ``test_race.py``, these tests commit real rows on their own connections, outside the
usual per-test transaction (and without ``transaction=True``, whose flush would wipe the
``IT desk`` group). So this module has no module-wide ``django_db`` mark: it uses the
``committed`` fixture from ``test_race.py``, which unblocks the database and deletes exactly
what it made. The one marked test below makes pytest-django set up the test database even
when this module runs on its own; ``committed`` refuses to run without it.
Zoom is mocked through the project-wide ``responses`` mock, which covers every thread.
"""

from datetime import date

import pytest
from django.contrib.auth.models import Group
from django.core import mail
from django.db import connection, connections
from django.urls import reverse

from apps.zoom.models import HostSlot, LinkRequest
from apps.zoom.services import Outcome

from . import zoommock as zm
from .test_race import (  # noqa: F401  (committed is a fixture)
    _approver,
    _run_together,
    _tracked_account,
    _tracked_request,
    _tracked_user,
    committed,
)


@pytest.mark.django_db
def test_committed_rows_go_to_the_test_database():
    assert connection.settings_dict["NAME"].startswith("test_")


def _live(committed, settings, http_mock, label="Race 01"):  # noqa: F811
    user = _tracked_user(committed, username="race-it", password="pw")
    account = _tracked_account(committed, label, host_key="8421973")
    settings.ZOOM_PROVIDER = "zoom"
    zm.connect(settings, account)
    zm.add_token(http_mock)
    zm.add_listing(http_mock, account.email)
    return user, account


def test_two_approvals_of_one_request_make_one_zoom_meeting(committed, settings, http_mock):  # noqa: F811
    """Criterion 32 (a): the request's row lock lets only one attempt reach the create."""
    user, account = _live(committed, settings, http_mock)
    link_request = _tracked_request(committed, class_name="Race F")
    zm.add_create(http_mock, account.email)

    results = _run_together(
        _approver(link_request, account, user), _approver(link_request, account, user)
    )

    assert sorted(r.outcome for r in results) == sorted([Outcome.APPROVED, Outcome.ALREADY_DECIDED])
    assert len(zm.calls_of(http_mock, "POST", "/meetings")) == 1
    assert len(mail.outbox) == 1
    link_request.refresh_from_db()
    assert link_request.meeting_id == str(zm.MEETING_ID)


def test_two_overlapping_requests_on_one_account_make_one_zoom_meeting(
    committed,  # noqa: F811
    settings,
    http_mock,
):
    """Criterion 32 (b): the loser is stopped by the locked database re-check before Zoom."""
    user, account = _live(committed, settings, http_mock)
    first = _tracked_request(
        committed, weekdays="1,3", last_date=date(2026, 10, 28), class_name="Race G"
    )
    second = _tracked_request(committed, first_date=date(2026, 10, 7), class_name="Race H")
    zm.add_create_for(
        http_mock, account.email, {first.zoom_marker: first, second.zoom_marker: second}
    )

    results = _run_together(_approver(first, account, user), _approver(second, account, user))

    outcomes = sorted(result.outcome for result in results)
    assert outcomes == sorted([Outcome.APPROVED, Outcome.CONFLICT]), [r.message for r in results]
    assert len(zm.calls_of(http_mock, "POST", "/meetings")) == 1
    loser = second if results[0].outcome == Outcome.APPROVED else first
    loser.refresh_from_db()
    assert loser.status == LinkRequest.Status.WAITING
    assert not HostSlot.objects.filter(occurrence__link_request=loser).exists()
    assert len(mail.outbox) == 1


def test_no_transaction_is_open_while_zoom_is_asked(committed, client, settings, http_mock):  # noqa: F811
    """Criterion 20: the detail view is non-atomic, so the request's connection is idle."""
    user = _tracked_user(committed, username="race-it", password="pw")
    user.groups.add(Group.objects.get(name="IT desk"))
    account = _tracked_account(committed, "Race 06", host_key="8421973")
    link_request = _tracked_request(committed, class_name="Race E")
    settings.ZOOM_PROVIDER = "zoom"
    zm.connect(settings, account)
    request_connection = connections["default"]
    seen = []

    def listing(request):
        seen.append(request_connection.in_atomic_block)
        return 200, {}, '{"meetings": [], "next_page_token": ""}'

    zm.add_token(http_mock)
    http_mock.add_callback("GET", zm.meetings_url(account.email), callback=listing)
    client.force_login(user)
    response = client.get(reverse("zoom:detail", args=[link_request.pk]))
    assert response.status_code == 200
    assert seen == [False]
    assert response.context["availability"][0]["zoom_state"] == "checked"
