"""Helpers for tests that talk to a mocked Zoom (brief 006, D17). Not a test module.

Replies are registered on the project-wide ``responses`` mock (the ``http_mock`` fixture in the
root ``conftest.py``), which is always on, so an unregistered URL raises instead of reaching the
network. Never use ``@responses.activate`` or a separate ``RequestsMock`` here.

Every credential value is obviously fake and distinctive, so a test can search any output for
it. The Colombo class of the default ``make_request()`` (Mon 5 Oct 2026, 8:30 to 11:30 am) is
03:00 to 06:00 UTC.
"""

import json
from urllib.parse import parse_qs, urlsplit

import responses

from apps.zoom import zoom_api
from config.settings.base import ZoomCredentials

SLUG = "zoom-test"
ACCOUNT_ID = "test-account-id-3141"
CLIENT_ID = "test-client-id-2718"
CLIENT_SECRET = "test-client-secret-1618"
TOKEN = "test-access-token-0577"
SECOND_TOKEN = "test-access-token-0999"
SECRETS = (ACCOUNT_ID, CLIENT_ID, CLIENT_SECRET, TOKEN, SECOND_TOKEN)

API = zoom_api.API_BASE
TOKEN_URL = zoom_api.TOKEN_URL

MEETING_ID = 81234567890
JOIN_URL = "https://us02web.zoom.us/j/81234567890?pwd=join-secret-4242"
PASSCODE = "Pa55-7788"
START_URL = "https://us02web.zoom.us/s/81234567890?zak=start-secret-9393"

CLASS_START = "2026-10-05T03:00:00Z"  # Mon 5 Oct 2026, 8:30 am in Colombo


def credentials(slug=SLUG):
    return ZoomCredentials(
        slug=slug, account_id=ACCOUNT_ID, client_id=CLIENT_ID, client_secret=CLIENT_SECRET
    )


def connect(settings, *accounts, slug=SLUG):
    """Give the server a credential set called ``slug`` and point ``accounts`` at it."""
    settings.ZOOM_S2S_SECRETS = {slug: credentials(slug)}
    settings.ZOOM_CREDENTIAL_SETS = [slug]
    for account in accounts:
        account.credential_set = slug
        account.save(update_fields=["credential_set"])


def add_token(mock, token=TOKEN, *, expires_in=3600, status=200):
    body = {"access_token": token, "token_type": "bearer", "expires_in": expires_in}
    mock.add(responses.POST, TOKEN_URL, json=body if status == 200 else {}, status=status)


def meetings_url(email):
    return API + zoom_api.user_path(email, "meetings")


def meeting_url(meeting_id):
    return API + zoom_api.meeting_path(meeting_id)


def add_listing(mock, email, meetings=(), *, status=200, body=None):
    """One page of ``GET /users/{email}/meetings``."""
    if body is None:
        body = {"meetings": list(meetings), "next_page_token": ""} if status == 200 else {}
    mock.add(responses.GET, meetings_url(email), json=body, status=status)


def scheduled(meeting_id, start, minutes, topic="Old booking", agenda=""):
    return {
        "id": meeting_id,
        "type": 2,
        "start_time": start,
        "duration": minutes,
        "topic": topic,
        "agenda": agenda,
        "join_url": f"https://us02web.zoom.us/j/{meeting_id}",
    }


def created_body(meeting_id=MEETING_ID, occurrences=None):
    """Zoom's answer to a create, with the ``start_url`` that must never be kept."""
    body = {
        "id": meeting_id,
        "join_url": JOIN_URL,
        "password": PASSCODE,
        "start_url": START_URL,
        "topic": "ignored",
    }
    if occurrences is not None:
        body["occurrences"] = [
            {
                "occurrence_id": str(1_759_633_200_000 + index),
                "start_time": start,
                "duration": 180,
                "status": "available",
            }
            for index, start in enumerate(occurrences)
        ]
    return body


def add_create(mock, email, *, status=201, body=None, **kwargs):
    if body is None:
        body = created_body(**kwargs) if status in (200, 201) else {"code": 300}
    mock.add(responses.POST, meetings_url(email), json=body, status=status)


def add_create_for(mock, email, requests_by_marker):
    """A create reply that fits whichever request is being approved, found by its agenda.

    For tests where the winner of a race isn't known in advance: a weekly request gets its own
    classes back as Zoom's occurrences, a one-off gets none.
    """

    def reply(request):
        sent = json.loads(request.body)
        link_request = requests_by_marker[sent["agenda"]]
        starts = None
        if sent["type"] == 8:
            starts = [
                occurrence.starts_at.strftime("%Y-%m-%dT%H:%M:%SZ")
                for occurrence in link_request.occurrences.all()
            ]
        return 201, {}, json.dumps(created_body(occurrences=starts))

    mock.add_callback(responses.POST, meetings_url(email), callback=reply)


def add_delete(mock, meeting_id=MEETING_ID, *, status=204):
    mock.add(responses.DELETE, meeting_url(meeting_id), status=status)


def calls_of(mock, method=None, path_end=None):
    """The recorded calls, optionally filtered by method and the end of the URL path."""
    found = []
    for call in mock.calls:
        request = call.request
        if method and request.method != method:
            continue
        if path_end and not urlsplit(request.url).path.endswith(path_end):
            continue
        found.append(call)
    return found


def query(call):
    return {key: values[-1] for key, values in parse_qs(urlsplit(call.request.url).query).items()}


def body(call):
    return json.loads(call.request.body)


def zoom_error(code):
    return {"code": code, "message": "RAW-ZOOM-TEXT with test-client-secret-1618"}
