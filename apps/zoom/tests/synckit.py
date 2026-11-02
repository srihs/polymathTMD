"""Helpers for brief 013's tests: the test secret, signed webhook calls, and Zoom's meeting
answers. Not a test module.

- **The test secret** (the brief's Terms): connection ``zoom-02`` with
  ``webhook_secret="test-webhook-secret"`` in ``ZOOM_S2S_SECRETS``, through the ``settings``
  fixture. ``connect`` points accounts at it; ``live`` also switches to the ``zoom`` provider
  and registers a token, so ``GET /meetings/{id}`` goes to the project-wide HTTP mock.
- **A signed POST**: ``x-zm-request-timestamp`` is the frozen now in epoch seconds, and
  ``x-zm-signature`` is ``v0=`` plus the hex HMAC-SHA256 of ``v0:{ts}:{raw body}``.
- ZL-0042 is weekly (Mon and Wed, 5 to 28 Oct 2026, 8:30 to 11:30 am, 8 classes) and ZL-0043
  a one-off (Mon 5 Oct), as in briefs 011 and 012; both are stored as approved on the account
  with ``booked_on``, so no Zoom call is made to set them up.
"""

import hashlib
import hmac
import json
import re
from datetime import UTC, date, datetime

import responses
from django.urls import reverse

from config.settings.base import ZoomCredentials

from . import zoommock as zm
from .conftest import COLOMBO, FROZEN_NOW, booked_on, make_request

SLUG = "zoom-02"
WEBHOOK_SECRET = "test-webhook-secret"
OTHER_SECRET = "other-webhook-secret"
ACCOUNT_ID = zm.ACCOUNT_ID
MEETING = "81234567890"
ONE_OFF_MEETING = "81234560000"
START_URL = "https://us02web.zoom.us/s/81234567890?zak=start-secret-9393"
JOIN_URL = "https://us02web.zoom.us/j/81234567890?pwd=join-secret-4242"
NOW_TS = int(FROZEN_NOW.timestamp())


def at(day, hour, minute=0, month=10):
    return datetime(2026, month, day, hour, minute, tzinfo=COLOMBO)


def credentials(slug=SLUG, secret=WEBHOOK_SECRET, account_id=ACCOUNT_ID):
    return ZoomCredentials(
        slug=slug,
        account_id=account_id,
        client_id=zm.CLIENT_ID,
        client_secret=zm.CLIENT_SECRET,
        webhook_secret=secret,
    )


def connect(settings, *accounts, slug=SLUG, secret=WEBHOOK_SECRET, extra=None):
    """The server has connection ``slug`` (with ``secret``, maybe empty); ``accounts`` use it."""
    sets = {slug: credentials(slug, secret)}
    sets.update(extra or {})
    settings.ZOOM_S2S_SECRETS = sets
    settings.ZOOM_CREDENTIAL_SETS = list(sets)
    for account in accounts:
        account.credential_set = slug
        account.save(update_fields=["credential_set"])


def live(settings, http_mock, *accounts, **kwargs):
    """``connect`` plus the live ``zoom`` provider and a token reply."""
    connect(settings, *accounts, **kwargs)
    settings.ZOOM_PROVIDER = "zoom"
    zm.add_token(http_mock)


def zl42(account, **kwargs):
    return booked_on(
        make_request(
            weekdays="1,3",
            first_date=date(2026, 10, 5),
            last_date=date(2026, 10, 28),
            class_name="Grade 11 Physics",
            email="nimal@example.com",
            requester_name="Nimal Perera",
        ),
        account,
        meeting_id=MEETING,
        **kwargs,
    )


def zl43(account, *, meeting_id=ONE_OFF_MEETING, first_date=date(2026, 10, 5), name=None):
    return booked_on(
        make_request(
            first_date=first_date,
            class_name=name or "Staff briefing",
            email="nimal@example.com",
            requester_name="Nimal Perera",
        ),
        account,
        meeting_id=meeting_id,
    )


# --------------------------------------------------------------------------- signed calls


def signature(body, *, secret=WEBHOOK_SECRET, ts=NOW_TS):
    message = f"v0:{ts}:".encode() + body
    return "v0=" + hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def as_bytes(body):
    return body if isinstance(body, bytes) else json.dumps(body).encode()


def webhook_url(slug=SLUG):
    return reverse("zoom:webhook", args=[slug])


def post(client, body, *, slug=SLUG, secret=WEBHOOK_SECRET, ts=NOW_TS, sig=None, headers=None):
    """POST ``body`` to the webhook, signed as Zoom would unless ``sig``/``headers`` say not."""
    raw = as_bytes(body)
    sent = {
        "HTTP_X_ZM_REQUEST_TIMESTAMP": str(ts),
        "HTTP_X_ZM_SIGNATURE": sig if sig is not None else signature(raw, secret=secret, ts=ts),
    }
    sent.update(headers or {})
    sent = {name: value for name, value in sent.items() if value is not None}
    return client.post(webhook_url(slug), data=raw, content_type="application/json", **sent)


def meeting_event(name="meeting.deleted", meeting_id=MEETING, *, account_id=ACCOUNT_ID, ts=1):
    """A Zoom meeting event body. ``ts`` varies it, so two calls make two different bodies."""
    return {
        "event": name,
        "event_ts": 1_790_000_000_000 + ts,
        "payload": {
            "account_id": account_id,
            "object": {
                "id": int(meeting_id),
                "uuid": "abc==",
                "host_id": "host-1",
                "topic": "Grade 11 Physics",
                "join_url": JOIN_URL,
            },
        },
    }


def validation_event(token="qgg8vlvZRS6UYooatFL8Aw"):
    return {
        "event": "endpoint.url_validation",
        "event_ts": 1_790_000_000_000,
        "payload": {"plainToken": token},
    }


# --------------------------------------------------------------------------- Zoom's answers


def zoom_time(moment):
    """Zoom's ``2026-10-05T03:00:00Z`` for an aware datetime."""
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def occurrence_id(moment):
    return str(int(moment.timestamp() * 1000))


def series_detail(classes, *, deleted=(), meeting_id=MEETING):
    """``GET /meetings/{id}`` for a weekly series: ``classes`` is ``[(id, start, minutes)]``.

    It carries the join link and the ``start_url``, as Zoom's answer does, so tests can prove
    neither is ever logged or kept.
    """
    items = [
        {
            "occurrence_id": oid,
            "start_time": zoom_time(start),
            "duration": minutes,
            "status": "available",
        }
        for oid, start, minutes in classes
    ]
    items += [
        {"occurrence_id": oid, "start_time": zoom_time(start), "duration": 180, "status": "deleted"}
        for oid, start in deleted
    ]
    return {
        "id": int(meeting_id),
        "type": 8,
        "topic": "Grade 11 Physics",
        "duration": 180,
        "join_url": JOIN_URL,
        "start_url": START_URL,
        "occurrences": items,
    }


def booking_series(booking, *, moved=None, missing=(), deleted=(), extra=()):
    """Zoom's answer for a weekly booking as stored, with changes.

    ``moved``: ``{start: (new start, minutes)}``, keeping the class's ID. ``missing``: starts
    Zoom no longer has at all. ``deleted``: starts Zoom lists as deleted. ``extra``:
    ``[(start, minutes)]`` added in Zoom, with new IDs.
    """
    moved = moved or {}
    classes, gone = [], []
    for occurrence in booking.occurrences.filter(cancelled_at__isnull=True).order_by("starts_at"):
        start = occurrence.starts_at
        oid = occurrence.zoom_occurrence_id or occurrence_id(start)
        if start in missing:
            continue
        if start in deleted:
            gone.append((oid, start))
            continue
        new_start, minutes = moved.get(start, (start, 180))
        classes.append((oid, new_start, minutes))
    classes += [(occurrence_id(start), start, minutes) for start, minutes in extra]
    return series_detail(classes, deleted=gone, meeting_id=booking.meeting_id)


def single_detail(start, minutes=180, *, meeting_id=ONE_OFF_MEETING):
    return {
        "id": int(meeting_id),
        "type": 2,
        "topic": "Staff briefing",
        "start_time": zoom_time(start),
        "duration": minutes,
        "join_url": JOIN_URL,
        "start_url": START_URL,
    }


# ``GET /users/{email}``, the host-user check after a 3001 (criterion 31), for any account.
# ``[^/]+$`` keeps it from matching ``/users/{email}/meetings``.
USER_URL = re.compile(re.escape(zm.API + "/users/") + r"[^/]+$")


def add_user(http_mock, *, status=200, error=None):
    """Register Zoom's answer to the host-user check (criterion 31).

    ``status`` 200 (the user is there), 404 (code 1001, no such user on this connection), or
    ``error``: an exception for ``responses`` to raise, such as a read timeout.
    """
    if error is not None:
        http_mock.add(responses.GET, USER_URL, body=error)
    elif status == 404:
        http_mock.add(responses.GET, USER_URL, json=zm.zoom_error(1001), status=404)
    else:
        http_mock.add(responses.GET, USER_URL, json={"id": "host-1", "type": 2}, status=status)


def user_gets(http_mock):
    return [c for c in http_mock.calls if USER_URL.fullmatch(c.request.url.split("?")[0])]


def add_meeting(
    http_mock, body=None, *, meeting_id=MEETING, status=200, callback=None, user_found=True
):
    """Register Zoom's answer to ``GET /meetings/{id}``: a body, ``status`` 404 (gone), or any.

    A 404 is code 3001, and by default the host-user check that follows it finds the user, so
    the meeting really is gone (criterion 31). ``user_found=False`` registers nothing for that
    check, so the test registers its own answer with ``add_user``.
    """
    url = zm.meeting_url(meeting_id)
    if callback is not None:
        http_mock.add_callback(responses.GET, url, callback=callback)
    elif status == 404:
        http_mock.add(
            responses.GET, url, json={"code": 3001, "message": "Meeting does not exist"}, status=404
        )
        if user_found:
            add_user(http_mock)
    else:
        http_mock.add(responses.GET, url, json=body or {}, status=status)


def gets(http_mock, meeting_id=MEETING):
    return zm.calls_of(http_mock, "GET", f"/meetings/{meeting_id}")
