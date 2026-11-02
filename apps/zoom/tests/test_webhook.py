"""Brief 013, the webhook endpoint ``zoom:webhook`` (criteria 3-12, 17, 20 and 21).

Every call is a signed POST through Django's test ``Client`` (criterion 23), and Zoom's
``GET /meetings/{id}`` is mocked. Logging is asserted on the app's own loggers (``apps.*``)
only, per the main session's ruling on criteria 4 and 5: Django's own ``django.request`` line
for a 4xx answer is expected and allowed. The thread tests are in ``test_sync_race.py``.
"""

import inspect
import logging
import re
from datetime import date
from pathlib import Path
from unittest import mock

import pytest
import responses
from django.conf import settings as django_settings
from django.core import mail
from django.db import connection
from django.http import HttpRequest
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import resolve, reverse

from apps.zoom import services, webhooks
from apps.zoom.models import LinkRequest, Occurrence, ZoomEvent

from . import synckit as kit
from . import zoommock as zm
from .conftest import booked_on, make_account, make_request

pytestmark = pytest.mark.django_db
at = kit.at


def _app_records(caplog, level=logging.WARNING):
    return [r for r in caplog.records if r.name.startswith("apps.") and r.levelno >= level]


@pytest.fixture
def zoom02(settings, db):
    account = make_account("Zoom 02", sort_order=2)
    kit.connect(account)
    return account


@pytest.fixture
def live02(settings, http_mock, zoom02):
    settings.ZOOM_PROVIDER = "zoom"
    zm.add_token(http_mock)
    return zoom02


# --------------------------------------------------------------------------- 3 URL and method


def test_the_address_is_one_per_connection(zoom02):
    assert reverse("zoom:webhook", args=["zoom-02"]) == "/zoom/webhooks/zoom-02/"
    view = resolve("/zoom/webhooks/zoom-02/").func
    assert getattr(view, "csrf_exempt", False) is True
    assert "default" in getattr(view, "_non_atomic_requests", set())


def test_get_is_405(client, zoom02):
    assert client.get(kit.webhook_url()).status_code == 405


def test_the_webhook_is_the_only_view_without_csrf_protection():
    apps_dir = Path(django_settings.BASE_DIR) / "apps"
    found = [
        (str(path.relative_to(apps_dir)), len(re.findall(r"\bcsrf_exempt\b", path.read_text())))
        for path in apps_dir.rglob("*.py")
        if "tests" not in path.parts
    ]
    assert [(name, n) for name, n in found if n] == [("zoom/views.py", 1)]


def test_other_posts_still_need_a_csrf_token(it_user, zoom02):
    booking = kit.zl42(zoom02)
    waiting = make_request(first_date=date(2026, 11, 2))
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(it_user)
    assert csrf_client.post(reverse("zoom:approve", args=[waiting.pk])).status_code == 403
    assert csrf_client.post(reverse("zoom:cancel", args=[booking.pk])).status_code == 403
    token = services.start_token(booking)
    assert Client(enforce_csrf_checks=True).post(
        reverse("zoom:start", args=[token])
    ).status_code == (403)
    assert csrf_client.post(reverse("zoom:sync", args=[booking.pk])).status_code == 403


def test_a_signed_call_needs_no_csrf_token_or_sign_in(zoom02):
    response = kit.post(Client(enforce_csrf_checks=True), kit.validation_event())
    assert response.status_code == 200


# --------------------------------------------------------------------------- 4 refused first


@pytest.mark.parametrize("slug", ["zoom-99", "zoom-03"])
def test_a_name_with_no_webhook_secret_is_404_and_logs_nothing_above_info(
    client, settings, zoom02, caplog, slug
):
    kit.connect(zoom02, extra={"zoom-03": ""})
    caplog.set_level(logging.DEBUG)
    response = kit.post(client, kit.meeting_event(), slug=slug)
    assert response.status_code == 404
    assert _app_records(caplog) == []
    assert ZoomEvent.objects.count() == 0


def test_over_256_kb_is_413_before_the_body_is_read(client, zoom02):
    with mock.patch.object(
        HttpRequest, "body", new_callable=mock.PropertyMock, side_effect=AssertionError("read")
    ):
        response = kit.post(
            client, kit.meeting_event(), headers={"CONTENT_LENGTH": str(256 * 1024 + 1)}
        )
    assert response.status_code == 413


def test_a_real_body_over_256_kb_is_413(client, zoom02):
    event = kit.meeting_event()
    event["padding"] = "x" * (256 * 1024)
    assert kit.post(client, event).status_code == 413
    assert ZoomEvent.objects.count() == 0


# --------------------------------------------------------------------------- 5 signature


def test_a_signed_event_is_accepted(client, zoom02):
    response = kit.post(client, kit.meeting_event("meeting.created"))
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"headers": {"HTTP_X_ZM_REQUEST_TIMESTAMP": None}}, "missing"),
        ({"headers": {"HTTP_X_ZM_SIGNATURE": None}}, "missing"),
        ({"headers": {"HTTP_X_ZM_REQUEST_TIMESTAMP": "12a4"}}, "missing"),
        ({"ts": kit.NOW_TS - 301}, "stale"),
        ({"ts": kit.NOW_TS + 301}, "stale"),
        ({"secret": kit.OTHER_SECRET}, "bad signature"),
        ("one character off", "bad signature"),
        ("one byte changed", "bad signature"),
    ],
)
def test_every_refusal_is_401_empty_with_one_warning(client, zoom02, caplog, change, reason):
    caplog.set_level(logging.DEBUG)
    event = kit.meeting_event()
    raw = kit.as_bytes(event)
    if change == "one character off":
        good = kit.signature(raw)
        sig = good[:-1] + ("0" if good[-1] != "0" else "1")
        response = kit.post(client, raw, sig=sig)
    elif change == "one byte changed":
        sig = kit.signature(raw)
        response = kit.post(client, raw.replace(b"meeting.deleted", b"meeting.deletee"), sig=sig)
    else:
        response = kit.post(client, raw, **change)
    assert response.status_code == 401 and response.content == b""
    [record] = _app_records(caplog)
    assert record.levelno == logging.WARNING
    assert record.getMessage() == f"Zoom webhook call to zoom-02 refused: {reason}"
    assert ZoomEvent.objects.count() == 0


def test_the_window_is_300_seconds_either_way(client, zoom02):
    for ts in (kit.NOW_TS - 300, kit.NOW_TS + 300):
        assert kit.post(client, kit.validation_event(), ts=ts).status_code == 200


def test_a_body_signed_with_another_sets_secret_is_refused(client, settings, zoom02):
    kit.connect(zoom02, extra={"zoom-03": kit.OTHER_SECRET})
    response = kit.post(client, kit.meeting_event(), slug="zoom-02", secret=kit.OTHER_SECRET)
    assert response.status_code == 401


# --------------------------------------------------------------------------- 6 URL validation


def test_url_validation_answers_exactly_with_one_query_and_no_http(client, zoom02, http_mock):
    """013 criterion 6 as amended by 015 criterion 27: the one lookup of the connection."""
    token = "qgg8vlvZRS6UYooatFL8Aw"
    with CaptureQueriesContext(connection) as queries:
        response = kit.post(client, kit.validation_event(token))
    assert response.status_code == 200 and response["Content-Type"] == "application/json"
    import hashlib
    import hmac

    expected = hmac.new(kit.WEBHOOK_SECRET.encode(), token.encode(), hashlib.sha256).hexdigest()
    assert response.json() == {"plainToken": token, "encryptedToken": expected}
    assert list(response.json()) == ["plainToken", "encryptedToken"]
    assert len(queries) == 1 and len(http_mock.calls) == 0
    assert "zoom_zoomconnection" in queries[0]["sql"]
    assert ZoomEvent.objects.count() == 0


@pytest.mark.parametrize(
    "token", ["v0:1790000000:{}", "", "a" * 257, "spaces here", "ä", 12345, None]
)
def test_a_validation_token_outside_the_safe_characters_is_400(client, zoom02, token):
    event = kit.validation_event()
    event["payload"]["plainToken"] = token
    response = kit.post(client, event)
    assert response.status_code == 400
    assert kit.WEBHOOK_SECRET.encode() not in response.content


def test_an_unsigned_validation_is_refused(client, zoom02):
    response = kit.post(client, kit.validation_event(), headers={"HTTP_X_ZM_SIGNATURE": None})
    assert response.status_code == 401


def test_a_signed_body_that_isn_t_an_event_is_400(client, zoom02, caplog):
    caplog.set_level(logging.DEBUG)
    assert kit.post(client, b"not json").status_code == 400
    assert kit.post(client, b"[1, 2]").status_code == 400
    assert kit.post(client, {"payload": {}}).status_code == 400
    # Review round 1, S2 (criterion 10, D18): an event with no ``payload`` object is a 400
    # before the account check, never a 401 with a misleading ``wrong account`` line.
    for payload in ("missing", "a string", ["a", "list"], None):
        body = {"event": "meeting.deleted", "event_ts": 1}
        if payload != "missing":
            body["payload"] = payload
        assert kit.post(client, body).status_code == 400, payload
    assert not [r for r in _app_records(caplog) if "wrong account" in r.getMessage()]
    assert ZoomEvent.objects.count() == 0


# --------------------------------------------------------------------------- 7 the account


def test_an_event_from_another_zoom_account_is_401(client, zoom02, caplog):
    caplog.set_level(logging.DEBUG)
    response = kit.post(client, kit.meeting_event(account_id="someone-elses-account"))
    assert response.status_code == 401
    [record] = _app_records(caplog)
    assert record.getMessage() == "Zoom webhook call to zoom-02 refused: wrong account"
    assert "someone-elses-account" not in caplog.text and kit.ACCOUNT_ID not in caplog.text


# --------------------------------------------------------------------------- 8, 9 repeats, ignored


def test_a_repeat_is_200_with_no_zoom_call_no_change_and_no_email(client, live02, http_mock):
    booking = kit.zl42(live02)
    kit.add_meeting(http_mock, kit.booking_series(booking, deleted=[at(7, 8, 30)]))
    event = kit.meeting_event()
    assert kit.post(client, event).status_code == 200
    assert len(mail.outbox) == 1 and len(kit.gets(http_mock)) == 1
    with CaptureQueriesContext(connection) as queries:
        assert kit.post(client, event).status_code == 200
    assert len(kit.gets(http_mock)) == 1 and len(mail.outbox) == 1
    assert not [q for q in queries if q["sql"].split()[0] in ("UPDATE", "INSERT", "DELETE")]
    assert ZoomEvent.objects.count() == 1


@pytest.mark.parametrize("name", ["recording.completed", "meeting.created", "meeting.started"])
def test_other_events_are_recorded_ignored(client, live02, http_mock, name):
    kit.zl42(live02)
    assert kit.post(client, kit.meeting_event(name)).status_code == 200
    row = ZoomEvent.objects.get()
    assert (row.event, row.outcome, row.slug) == (name, "ignored", "zoom-02")
    assert kit.gets(http_mock) == []


def test_the_manual_provider_records_meeting_events_ignored_and_asks_zoom_nothing(
    client, settings, zoom02, http_mock
):
    settings.ZOOM_PROVIDER = "manual"
    booking = kit.zl42(zoom02)
    response = kit.post(client, kit.meeting_event("meeting.deleted"))
    assert response.status_code == 200
    assert list(ZoomEvent.objects.values_list("outcome", flat=True)) == ["ignored"]
    assert len(http_mock.calls) == 0
    booking.refresh_from_db()
    assert booking.status == LinkRequest.Status.APPROVED
    assert not Occurrence.objects.filter(cancelled_at__isnull=False).exists()


def test_an_event_with_no_meeting_id_is_ignored(client, live02):
    event = kit.meeting_event()
    del event["payload"]["object"]["id"]
    assert kit.post(client, event).status_code == 200
    assert ZoomEvent.objects.get().outcome == "ignored"


# --------------------------------------------------------------------------- 10 status codes


def test_a_handled_event_is_200_and_its_row_holds_the_outcome(client, live02, http_mock):
    booking = kit.zl42(live02)
    kit.add_meeting(http_mock, kit.booking_series(booking, deleted=[at(7, 8, 30)]))
    event = kit.meeting_event()
    response = kit.post(client, event)
    assert response.status_code == 200 and response.content == b""
    row = ZoomEvent.objects.get()
    assert (row.outcome, row.link_request_id, row.event) == (
        "changed",
        booking.pk,
        "meeting.deleted",
    )
    assert row.body_sha256 == webhooks.body_sha256(kit.as_bytes(event))
    assert row.event_ts == event["event_ts"] and row.received_at is not None


def test_zoom_unreachable_is_503_and_keeps_no_row(client, live02, http_mock):
    kit.zl42(live02)
    kit.add_meeting(http_mock, status=503)
    assert kit.post(client, kit.meeting_event()).status_code == 503
    assert ZoomEvent.objects.count() == 0
    assert not Occurrence.objects.filter(cancelled_at__isnull=False).exists()


def test_any_other_failure_is_500_with_one_error_line_and_no_row(client, live02, caplog):
    booking = kit.zl42(live02)
    caplog.set_level(logging.DEBUG)
    with mock.patch.object(services, "reconcile", side_effect=RuntimeError("secret detail")):
        response = kit.post(client, kit.meeting_event())
    assert response.status_code == 500
    errors = [r for r in _app_records(caplog) if r.levelno >= logging.ERROR]
    assert [r.getMessage() for r in errors] == [
        f"A Zoom event for {booking.reference} on zoom-02 failed: RuntimeError"
    ]
    assert "secret detail" not in caplog.text
    assert ZoomEvent.objects.count() == 0


def test_the_parsed_event_is_masked_in_error_reports(rf, live02):
    """Criterion 20, review round 1, N1: ``handle_event``'s ``event`` holds join links."""
    import sys

    from django.views.debug import ExceptionReporter

    kit.zl42(live02)
    event = kit.meeting_event()
    with mock.patch.object(services, "_event_meeting_id", side_effect=RuntimeError("boom")):
        try:
            services.handle_event(kit.verified(), event, "c" * 64)
        except RuntimeError:
            info = sys.exc_info()
    reporter = ExceptionReporter(rf.post("/zoom/webhooks/zoom-02/"), *info)
    frames = reporter.get_traceback_frames()
    [frame] = [f for f in frames if f["function"] == "handle_event"]
    shown = dict(frame["vars"])
    assert shown["event"] == "********************"
    assert kit.JOIN_URL not in reporter.get_traceback_text()


def test_a_lock_race_is_500(client, live02):
    booking = kit.zl42(live02)
    lost = services.ReconcileResult(services.LOCK_RACE, booking)
    with mock.patch.object(services, "reconcile", return_value=lost):
        assert kit.post(client, kit.meeting_event()).status_code == 500


# --------------------------------------------------------------------------- 12 which booking


def test_a_meeting_with_no_booking_here_is_not_ours_with_no_zoom_call(client, live02, http_mock):
    assert kit.post(client, kit.meeting_event(meeting_id="85555555555")).status_code == 200
    assert ZoomEvent.objects.get().outcome == "not_ours"
    assert len(http_mock.calls) == 0


def test_a_booking_on_another_connection_is_never_touched(
    client, settings, live02, http_mock, caplog
):
    zoom03 = make_account("Zoom 03", sort_order=3)
    kit.connect(live02, extra={"zoom-03": "x"})
    kit.connect(zoom03, slug="zoom-03", secret="x")
    booking = kit.zl42(zoom03)
    caplog.set_level(logging.DEBUG)
    assert kit.post(client, kit.meeting_event()).status_code == 200
    assert ZoomEvent.objects.get().outcome == "not_ours"
    assert len(http_mock.calls) == 0
    booking.refresh_from_db()
    assert booking.status == LinkRequest.Status.APPROVED
    [warning] = _app_records(caplog)
    assert warning.getMessage() == (
        f"A Zoom event on zoom-02 named meeting {kit.MEETING}, which is booked on another "
        "connection's account; it wasn't touched."
    )


def test_a_waiting_or_rejected_request_is_never_matched(client, live02, http_mock):
    waiting = make_request(first_date=date(2026, 11, 2))
    LinkRequest.objects.filter(pk=waiting.pk).update(meeting_id=kit.MEETING)
    assert kit.post(client, kit.meeting_event()).status_code == 200
    assert ZoomEvent.objects.get().outcome == "not_ours"


# --------------------------------------------------------------------------- 17 echoes


def _booking_writes(queries):
    return [
        q["sql"]
        for q in queries
        if q["sql"].split()[0] in ("UPDATE", "INSERT", "DELETE")
        and "zoom_zoomevent" not in q["sql"]
    ]


def test_the_echo_of_a_whole_cancel_made_here_changes_nothing(client, live02, http_mock, it_user):
    booking = kit.zl42(live02)
    zm.add_delete(http_mock, kit.MEETING)
    assert services.cancel(booking.pk, by=it_user, reason="Closed.").outcome == "cancelled"
    kit.add_meeting(http_mock, status=404)
    mail.outbox.clear()
    with CaptureQueriesContext(connection) as queries:
        assert kit.post(client, kit.meeting_event()).status_code == 200
    assert ZoomEvent.objects.get().outcome == "no_change"
    assert _booking_writes(queries) == [] and mail.outbox == []


def test_the_echo_of_a_class_cancel_made_here_changes_nothing(client, live02, http_mock, it_user):
    booking = kit.zl42(live02)
    wed7 = booking.occurrences.get(starts_at=at(7, 8, 30))
    http_mock.add(responses.DELETE, zm.meeting_url(kit.MEETING), status=204)
    services.cancel(booking.pk, occurrence_id=wed7.pk, by=it_user, reason="Closed.")
    kit.add_meeting(http_mock, kit.booking_series(booking, deleted=[at(7, 8, 30)]))
    mail.outbox.clear()
    with CaptureQueriesContext(connection) as queries:
        assert kit.post(client, kit.meeting_event()).status_code == 200
    assert ZoomEvent.objects.get().outcome == "no_change"
    assert _booking_writes(queries) == [] and mail.outbox == []


def test_the_echo_of_a_move_made_here_changes_nothing(client, live02, http_mock, it_user):
    booking = kit.zl42(live02)
    mon12 = booking.occurrences.get(starts_at=at(12, 8, 30))
    zm.add_listing(http_mock, live02.email)
    http_mock.add(responses.PATCH, zm.meeting_url(kit.MEETING), status=204)
    result = services.move_class(
        booking.pk, mon12.pk, starts_at=at(13, 9), ends_at=at(13, 12), by=it_user
    )
    assert result.outcome == "moved"
    kit.add_meeting(http_mock, kit.booking_series(booking))  # read after the move: new times
    mail.outbox.clear()
    with CaptureQueriesContext(connection) as queries:
        assert kit.post(client, kit.meeting_event("meeting.updated")).status_code == 200
    assert ZoomEvent.objects.get().outcome == "no_change"
    assert _booking_writes(queries) == [] and mail.outbox == []


# --------------------------------------------------------------------------- 20 nothing secret


def test_no_log_record_holds_a_secret_a_signature_the_body_or_a_link(
    client, live02, http_mock, caplog
):
    caplog.set_level(logging.DEBUG)
    booking = kit.zl42(live02)
    kit.add_meeting(http_mock, kit.booking_series(booking, deleted=[at(7, 8, 30)]))
    event = kit.meeting_event()
    raw = kit.as_bytes(event)
    sent_signatures = [kit.signature(kit.as_bytes(kit.validation_event())), kit.signature(raw)]
    kit.post(client, kit.validation_event())
    kit.post(client, raw)
    kit.post(client, raw, sig="v0=" + "0" * 64)
    services.reconcile(booking)
    text = "\n".join(record.getMessage() for record in caplog.records) + caplog.text
    for secret in (
        kit.WEBHOOK_SECRET,
        *sent_signatures,
        raw.decode(),
        kit.JOIN_URL,
        kit.START_URL,
        "zak=",
        zm.TOKEN,
    ):
        assert secret not in text


def test_the_view_and_the_verifier_mask_what_they_hold(client, zoom02):
    response = kit.post(client, kit.validation_event())
    assert response.wsgi_request.sensitive_post_parameters == "__ALL__"
    variables = inspect.getclosurevars(webhooks.verify).nonlocals["variables"]
    assert {"secret", "signature", "body"} <= set(variables)


# --------------------------------------------------------------------------- the emails' host


def test_the_requester_email_from_a_webhook_links_to_the_host_zoom_called(
    client, live02, http_mock
):
    booking = booked_on(
        make_request(
            first_date=date(2026, 10, 5), class_name="Staff briefing", email="nimal@example.com"
        ),
        live02,
        meeting_id=kit.ONE_OFF_MEETING,
    )
    kit.add_meeting(http_mock, status=404, meeting_id=kit.ONE_OFF_MEETING)
    kit.post(client, kit.meeting_event(meeting_id=kit.ONE_OFF_MEETING))
    [email] = mail.outbox
    assert "http://testserver/zoom/request/" in email.body
    booking.refresh_from_db()
    assert booking.status == LinkRequest.Status.CANCELLED
