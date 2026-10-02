"""Brief 012, criterion 34 (D22, the designer's D.14): Zoom's daily limit, wherever it's hit.

A daily-limit ``429`` raises ``ZoomDailyLimit`` on every Zoom call, not only the move's
``PATCH``. It's ``lasting`` (waiting a few minutes won't help), but the usual lasting next step
("press Check connection", "Waiting won't fix this") can't help either. So each caller checks
for it before ``lasting`` and says when to try again, in one shared sentence
(``services.daily_reset_sentence``). One test per caller, plus the approve page's account list
and the helper itself; each asserts criterion 34's rendered text exactly, at the frozen now
(Mon 28 Sep 2026, 10:00 Colombo), against a mocked Zoom answering with its documented
daily-limit wording.
"""

import html
from datetime import date, datetime

import pytest
import responses
from django.contrib.messages import constants as levels
from django.contrib.messages import get_messages
from django.template.loader import render_to_string
from django.urls import reverse

from apps.zoom import services
from apps.zoom.errors import ZoomDailyLimit
from apps.zoom.models import LinkRequest

from . import zoommock as zm
from .conftest import COLOMBO, booked_on, make_account, make_request
from .test_move_services import ZOOM_DAILY_TEXT

pytestmark = pytest.mark.django_db
MEETING = "81234567890"
RESET = "Try again after 5:30 am on Tue 29 Sep 2026."
# Zoom's daily-limit answer: the status, its documented message and the header value.
DAILY_429 = {
    "status": 429,
    "headers": {"X-RateLimit-Type": "Daily-limit"},
    "json": {"code": 429, "message": ZOOM_DAILY_TEXT},
}
# Criterion 34: words no daily message may hold. "another free account" is allowed only in
# approve's two messages, where another account really helps.
NEVER = ("Check connection", "Waiting won't fix this", "429", "rate limit", "quota", "UTC", "API")


def _plain(message, *, another_account=False):
    for word in NEVER:
        assert word.lower() not in message.lower(), word
    assert ("another free account" in message) is another_account
    assert ZOOM_DAILY_TEXT not in message and "maximum daily rate limit" not in message


@pytest.fixture
def zoom02(settings, http_mock):
    """Zoom 02 on the live provider, connected, with a token registered."""
    account = make_account("Zoom 02", sort_order=2)
    settings.ZOOM_PROVIDER = "zoom"
    zm.connect(settings, account)
    zm.add_token(http_mock)
    return account


def _booked(account):
    return booked_on(
        make_request(weekdays="1,3", first_date=date(2026, 10, 5), last_date=date(2026, 10, 28)),
        account,
    )


def _nothing_booked(link_request):
    link_request.refresh_from_db()
    assert link_request.status == LinkRequest.Status.WAITING and link_request.meeting_id == ""


# --------------------------------------------------------------------------- the helper


def test_the_daily_reset_sentence_is_p5s(monkeypatch):
    """P5's sentence from one helper; criterion 14's move message is built with it, unchanged."""
    assert services.daily_reset_sentence() == RESET
    early = datetime(2026, 9, 29, 2, 0, tzinfo=COLOMBO)  # Mon 28 Sep, 20:30 UTC
    assert services.daily_reset_sentence(early) == RESET
    after = datetime(2026, 9, 29, 6, 0, tzinfo=COLOMBO)  # past the reset: the next one
    assert services.daily_reset_sentence(after) == "Try again after 5:30 am on Wed 30 Sep 2026."

    pinned = (
        "Zoom's daily limit for changing Zoom 02's meetings is used up. Nothing was changed. "
        "Try again after 5:30 am on Tue 29 Sep 2026."
    )
    built = services.MOVE_DAILY_LIMIT.format(label="Zoom 02", reset=services.daily_reset_sentence())
    assert built == pinned
    assert services.move_failed_message(ZoomDailyLimit(), "Zoom 02") == pinned

    error = ZoomDailyLimit()
    assert error.user_message == "Zoom's daily limit for this account is used up"
    assert error.reason_sentence == "Zoom's daily limit for this account is used up."
    assert error.lasting is True


# --------------------------------------------------------------------------- 1a, 1b approve


def test_a_daily_limit_on_approves_create_says_when_to_try_again(zoom02, http_mock, it_user):
    link_request = make_request()
    zm.add_listing(http_mock, zoom02.email)
    http_mock.add(responses.POST, zm.meetings_url(zoom02.email), **DAILY_429)

    result = services.approve(link_request.pk, account_id=zoom02.pk, by=it_user)
    assert (result.outcome, result.message) == (
        services.Outcome.PROVIDER_ERROR,
        "We couldn't make the meeting in Zoom: Zoom's daily limit for this account is used up. "
        "Nothing was booked. Choose another free account, or wait for this one. Try again "
        "after 5:30 am on Tue 29 Sep 2026.",
    )
    _plain(result.message, another_account=True)
    assert zm.calls_of(http_mock, "DELETE") == []  # a certain refusal: nothing to clean up
    _nothing_booked(link_request)


def test_a_daily_limit_on_approves_look_up_says_when_to_try_again(zoom02, http_mock, it_client):
    link_request = make_request()
    http_mock.add(responses.GET, zm.meetings_url(zoom02.email), **DAILY_429)

    response = it_client.post(
        reverse("zoom:approve", args=[link_request.pk]), {"host_account": zoom02.pk}
    )
    assert response.status_code == 200
    message = response.context["approve_error"]
    assert message == (
        "We couldn't check Zoom 02's meetings in Zoom, so nothing was booked. Zoom's daily limit "
        "for this account is used up. Choose another free account, or wait for this one. Try "
        "again after 5:30 am on Tue 29 Sep 2026."
    )
    _plain(message, another_account=True)
    assert zm.calls_of(http_mock, "POST", "/meetings") == []
    _nothing_booked(link_request)


# --------------------------------------------------------------------------- 2 cancel


def test_a_daily_limit_on_cancel_says_when_to_try_again(zoom02, http_mock, it_user):
    booking = _booked(zoom02)
    http_mock.add(responses.DELETE, zm.meeting_url(MEETING), **DAILY_429)

    result = services.cancel(booking.pk, by=it_user, reason="Closed.")
    assert (result.outcome, result.message) == (
        services.Outcome.PROVIDER_ERROR,
        "We couldn't cancel it in Zoom: Zoom's daily limit for this account is used up. Nothing "
        "was cancelled. Try again after 5:30 am on Tue 29 Sep 2026.",
    )
    _plain(result.message)
    booking.refresh_from_db()
    assert booking.status == LinkRequest.Status.APPROVED
    assert not booking.occurrences.filter(cancelled_at__isnull=False).exists()


# --------------------------------------------------------------------------- 3 the move's look-up


def test_a_daily_limit_on_the_moves_look_up_says_when_to_try_again(zoom02, http_mock):
    booking = _booked(zoom02)
    wed7 = booking.occurrences.get(starts_at=datetime(2026, 10, 7, 8, 30, tzinfo=COLOMBO))
    http_mock.add(responses.GET, zm.meetings_url(zoom02.email), **DAILY_429)

    result = services.move_class(
        booking.pk,
        wed7.pk,
        starts_at=datetime(2026, 10, 8, 9, 0, tzinfo=COLOMBO),
        ends_at=datetime(2026, 10, 8, 12, 0, tzinfo=COLOMBO),
        by=None,
    )
    assert (result.outcome, result.message) == (
        services.Outcome.PROVIDER_ERROR,
        "We couldn't check Zoom 02's meetings in Zoom, so nothing was changed. Zoom's daily "
        "limit for this account is used up. Try again after 5:30 am on Tue 29 Sep 2026.",
    )
    _plain(result.message)
    assert zm.calls_of(http_mock, "PATCH") == []
    wed7.refresh_from_db()
    assert wed7.starts_at == datetime(2026, 10, 7, 8, 30, tzinfo=COLOMBO)


# --------------------------------------------------------------------------- 4 Check connection


def test_a_daily_limit_on_check_connection_says_when_to_try_again(zoom02, http_mock, it_client):
    http_mock.add(responses.GET, zm.API + f"/users/{zoom02.email}", **DAILY_429)

    response = it_client.post(reverse("zoom:account_check", args=[zoom02.pk]))
    assert response.status_code == 302
    message = list(get_messages(response.wsgi_request))[-1]
    assert (message.level, str(message)) == (
        levels.ERROR,
        "Couldn't check Zoom 02 with Zoom: Zoom's daily limit for this account is used up. Try "
        "again after 5:30 am on Tue 29 Sep 2026.",
    )
    assert "Waiting won't fix this" not in str(message)
    assert "Zoom error number" not in str(message)
    _plain(str(message))


# --------------------------------------------------------------------------- 5 the account list


def test_a_daily_limit_on_the_account_list_names_the_reason(zoom02, http_mock, it_client):
    """Row 5: no code change, the row prints the error's sentence under its own tag."""
    link_request = make_request()
    http_mock.add(responses.GET, zm.meetings_url(zoom02.email), **DAILY_429)

    response = it_client.get(reverse("zoom:detail", args=[link_request.pk]))
    assert response.status_code == 200
    [entry] = response.context["availability"]
    assert (entry["zoom_state"], entry["zoom_problem"], entry["is_free"]) == (
        "unavailable",
        "Zoom's daily limit for this account is used up.",
        False,
    )
    # The row itself, rendered with the real partial (the page template is stubbed here).
    row = html.unescape(
        render_to_string(
            "zoom/partials/avail_item.html",
            {"entry": entry, "total": response.context["occurrence_count"]},
        )
    )
    assert "Couldn't check with Zoom" in row
    assert "Zoom's daily limit for this account is used up. It can't be booked" in row
    _plain(entry["zoom_problem"])
