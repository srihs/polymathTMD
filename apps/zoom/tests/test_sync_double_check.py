"""Brief 013, criterion 31 (review round 1, S1; owner: "Double-check with Zoom"; D17).

Zoom answers ``404`` code 3001 both for a meeting that was deleted and for one that belongs to
another Zoom account. So a 3001 is believed only once Zoom confirms, on the same connection,
that the account's host user exists (``GET /users/{email}``, 006's Check connection call).
Otherwise the booking "couldn't be checked": nothing is cancelled, flagged or emailed, from
any trigger (the webhook, the button and the nightly command).

Against the live provider with Zoom's answers mocked (criterion 23).
"""

from io import StringIO

import pytest
import requests
from django.contrib.messages import constants as levels
from django.contrib.messages import get_messages
from django.core import mail
from django.core.management import CommandError, call_command
from django.test import Client, RequestFactory
from django.urls import reverse

from apps.zoom import services
from apps.zoom.models import LinkRequest, Occurrence, ZoomEvent
from apps.zoom.providers import ZoomUnavailable, ZoomUserNotFound

from . import synckit as kit
from .conftest import make_account

pytestmark = pytest.mark.django_db

USER_NOT_FOUND_FLASH = (
    "We couldn't check with Zoom: Zoom has no user with this account's sign-in email. Ask "
    "whoever manages the Zoom accounts to press Check connection for Zoom 02, then try again."
)
NO_ANSWER_FLASH = "We couldn't check with Zoom: no answer from Zoom. Try again in a few minutes."


@pytest.fixture
def zoom02(settings, http_mock, db):
    account = make_account("Zoom 02", sort_order=2)
    kit.live(settings, http_mock, account)
    settings.ALLOWED_HOSTS = ["testserver", "tmd.polymath.edu.lk"]
    return account


def _gone_but(http_mock, *, status=200, error=None):
    """The meeting ``GET`` answers 3001; the host-user check answers as given."""
    kit.add_meeting(http_mock, status=404, user_found=False)
    kit.add_user(http_mock, status=status, error=error)


def _reconcile(booking):
    request = RequestFactory().get("/", HTTP_HOST="tmd.polymath.edu.lk", secure=True)
    return services.reconcile(booking, request=request)


def _nothing_changed(booking):
    booking.refresh_from_db()
    assert booking.status == LinkRequest.Status.APPROVED and booking.cancelled_at is None
    assert not Occurrence.objects.filter(cancelled_at__isnull=False).exists()
    assert booking.zoom_attention == ""
    assert mail.outbox == []


def _run_command():
    out = StringIO()
    try:
        call_command("sync_zoom_bookings", stdout=out)
    except CommandError as exc:
        return out.getvalue().splitlines(), exc
    return out.getvalue().splitlines(), None


# --------------------------------------------------------------------------- the wrong account


def test_a_3001_from_the_wrong_account_cancels_nothing(zoom02, http_mock, it_user):
    booking = kit.zl42(zoom02)
    _gone_but(http_mock, status=404)
    result = _reconcile(booking)
    assert result.outcome == services.PROVIDER_FAILED
    assert isinstance(result.error, ZoomUserNotFound)
    assert result.cancelled == [] and not result.emailed
    _nothing_changed(booking)
    [user_call] = kit.user_gets(http_mock)
    assert user_call.request.url == kit.zm.API + "/users/zoom02@polymath.example"


def test_the_wrong_account_s_3001_is_503_on_the_webhook_with_no_row(zoom02, http_mock, it_user):
    booking = kit.zl42(zoom02)
    _gone_but(http_mock, status=404)
    assert kit.post(Client(), kit.meeting_event()).status_code == 503
    assert ZoomEvent.objects.count() == 0
    _nothing_changed(booking)


def test_the_wrong_account_s_3001_shows_the_pinned_flash(zoom02, http_mock, it_client):
    booking = kit.zl42(zoom02)
    _gone_but(http_mock, status=404)
    response = it_client.post(reverse("zoom:sync", args=[booking.pk]))
    assert response.status_code == 302
    messages = [(m.level, str(m)) for m in get_messages(response.wsgi_request)]
    assert messages == [(levels.ERROR, USER_NOT_FOUND_FLASH)]
    _nothing_changed(booking)


def test_the_wrong_account_s_3001_is_a_couldn_t_be_checked_line(zoom02, http_mock, it_user):
    booking = kit.zl42(zoom02)
    _gone_but(http_mock, status=404)
    lines, failed = _run_command()
    assert lines == [
        f"{booking.reference} (Zoom 02): couldn't be checked: Zoom has no user with this "
        "account's sign-in email.",
        "Checked 1 booking: 0 changed, 0 need a look, 1 couldn't be checked.",
    ]
    assert failed is not None and failed.returncode == 1
    _nothing_changed(booking)


# --------------------------------------------------------------------------- the check failing


def test_a_failed_user_check_cancels_nothing_from_any_trigger(zoom02, http_mock, it_client):
    booking = kit.zl42(zoom02)
    timeout = requests.exceptions.ReadTimeout("slow")

    _gone_but(http_mock, error=timeout)
    result = _reconcile(booking)
    assert result.outcome == services.PROVIDER_FAILED
    assert isinstance(result.error, ZoomUnavailable)
    assert result.error.user_message == "no answer from Zoom"
    _nothing_changed(booking)

    _gone_but(http_mock, error=timeout)
    assert kit.post(Client(), kit.meeting_event()).status_code == 503
    assert ZoomEvent.objects.count() == 0

    _gone_but(http_mock, error=timeout)
    response = it_client.post(reverse("zoom:sync", args=[booking.pk]))
    assert [(m.level, str(m)) for m in get_messages(response.wsgi_request)] == [
        (levels.ERROR, NO_ANSWER_FLASH)
    ]

    _gone_but(http_mock, error=timeout)
    lines, failed = _run_command()
    assert lines[0] == f"{booking.reference} (Zoom 02): couldn't be checked: No answer from Zoom."
    assert failed.returncode == 1
    _nothing_changed(booking)


# --------------------------------------------------------------------------- a real deletion


def test_a_real_deletion_still_cancels_every_remaining_class(zoom02, http_mock, it_user):
    booking = kit.zl42(zoom02)
    _gone_but(http_mock, status=200)
    result = _reconcile(booking)
    assert result.outcome == "changed" and len(result.cancelled) == 8
    booking.refresh_from_db()
    assert booking.status == LinkRequest.Status.CANCELLED and booking.cancelled_in_zoom
    assert [m.to for m in mail.outbox] == [["nimal@example.com"]]
    assert len(kit.user_gets(http_mock)) == 1


def test_a_normal_answer_makes_no_user_check(zoom02, http_mock):
    booking = kit.zl42(zoom02)
    kit.add_meeting(http_mock, kit.booking_series(booking))
    assert _reconcile(booking).outcome == "no_change"
    assert kit.user_gets(http_mock) == []
    assert len(kit.gets(http_mock)) == 1
