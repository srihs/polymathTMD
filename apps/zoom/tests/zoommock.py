"""Helpers for tests that talk to a mocked Zoom (brief 006, D17). Not a test module.

Replies are registered on the project-wide ``responses`` mock (the ``http_mock`` fixture in the
root ``conftest.py``), which is always on, so an unregistered URL raises instead of reaching the
network. Never use ``@responses.activate`` or a separate ``RequestsMock`` here.

Every credential value is obviously fake and distinctive, so a test can search any output for
it. The Colombo class of the default ``make_request()`` (Mon 5 Oct 2026, 8:30 to 11:30 am) is
03:00 to 06:00 UTC.

Brief 015: credentials live in ``ZoomConnection`` rows, not settings. ``connection()`` makes the
brief's "test connection" (``zoom-test``, Account ID ``test-account-id``, Client ID
``test-client-id``, client secret ``test-client-secret-value``) through the model's own
``set_credentials``, and ``connect()`` chooses it on accounts. ``credentials()`` is the plain
``ZoomCredentials`` of that connection, for client tests that need no database.
"""

import base64
import json
from urllib.parse import parse_qs, urlsplit

import responses
from django.test import override_settings
from responses import matchers

from apps.zoom import crypto, zoom_api
from apps.zoom.models import ZoomConnection
from apps.zoom.zoom_api import ZoomCredentials

SLUG = "zoom-test"
ACCOUNT_ID = "test-account-id"
CLIENT_ID = "test-client-id"
CLIENT_SECRET = "test-client-secret-value"
NEW_CLIENT_SECRET = "test-client-secret-renewed"
TOKEN = "test-access-token-0577"
SECOND_TOKEN = "test-access-token-0999"
SECRETS = (ACCOUNT_ID, CLIENT_ID, CLIENT_SECRET, NEW_CLIENT_SECRET, TOKEN, SECOND_TOKEN)

API = zoom_api.API_BASE
TOKEN_URL = zoom_api.TOKEN_URL

MEETING_ID = 81234567890
JOIN_URL = "https://us02web.zoom.us/j/81234567890?pwd=join-secret-4242"
PASSCODE = "Pa55-7788"
START_URL = "https://us02web.zoom.us/s/81234567890?zak=start-secret-9393"

CLASS_START = "2026-10-05T03:00:00Z"  # Mon 5 Oct 2026, 8:30 am in Colombo


def client_id_for(slug):
    """The test connection keeps ``CLIENT_ID``; any other gets its own (the column is unique)."""
    return CLIENT_ID if slug == SLUG else f"{CLIENT_ID}-{slug}"


def credentials(slug=SLUG, version=1):
    return ZoomCredentials(
        slug=slug,
        version=version,
        account_id=ACCOUNT_ID,
        client_id=client_id_for(slug),
        client_secret=CLIENT_SECRET,
    )


def connection(slug=SLUG, *, webhook_secret="", by=None):
    """The connection called ``slug``, made with the test values if it doesn't exist yet."""
    found = ZoomConnection.objects.filter(slug=slug).first()
    if found is not None:
        return found
    made = ZoomConnection(slug=slug)
    made.set_credentials(
        account_id=ACCOUNT_ID, client_id=client_id_for(slug), client_secret=CLIENT_SECRET, by=by
    )
    if webhook_secret:
        made.set_webhook_secret(webhook_secret, by=by)
    made.save()
    return made


def connect(*accounts, slug=SLUG, webhook_secret=""):
    """Make (or reuse) the connection ``slug`` and choose it on ``accounts``; return it."""
    chosen = connection(slug, webhook_secret=webhook_secret)
    for account in accounts:
        account.zoom_connection = chosen
        account.save(update_fields=["zoom_connection"])
    return chosen


# A second, obviously fake Fernet key ("other-test-only-fernet-key-32byt"): a value encrypted
# with it can't be read with the test settings' key, which is how "unreadable" is made.
OTHER_FERNET_KEY = "b3RoZXItdGVzdC1vbmx5LWZlcm5ldC1rZXktMzJieXQ="


def foreign_token(plain="test-unreadable-value"):
    """Ciphertext the configured keys can't read (a key removed before rotating, c. 6)."""
    with override_settings(HOST_KEY_ENCRYPTION_KEYS=[OTHER_FERNET_KEY]):
        return crypto.encrypt(plain)


def make_unreadable(connection, *, client=True, webhook=False):
    """Store ``connection``'s secrets under a key the server doesn't have."""
    fields = {}
    if client:
        fields["client_secret_encrypted"] = foreign_token()
    if webhook:
        fields["webhook_secret_encrypted"] = foreign_token()
    ZoomConnection.objects.filter(pk=connection.pk).update(**fields)
    connection.refresh_from_db()
    return connection


def basic_auth(client_id=CLIENT_ID, secret=CLIENT_SECRET):
    """The ``Authorization`` header a token request carries for these details (criterion 44)."""
    return "Basic " + base64.b64encode(f"{client_id}:{secret}".encode()).decode()


def add_token(mock, token=TOKEN, *, expires_in=3600, status=200, secret=None, client_id=None):
    """A token reply; with ``secret`` or ``client_id``, only for a request whose Basic auth
    carries them (criteria 24 and 44; the other one defaults to the test connection's)."""
    body = {"access_token": token, "token_type": "bearer", "expires_in": expires_in}
    match = []
    if secret is not None or client_id is not None:
        expected = basic_auth(client_id=client_id or CLIENT_ID, secret=secret or CLIENT_SECRET)
        match = [matchers.header_matcher({"Authorization": expected})]
    mock.add(
        responses.POST, TOKEN_URL, json=body if status == 200 else {}, status=status, match=match
    )


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
    return {"code": code, "message": f"RAW-ZOOM-TEXT with {CLIENT_SECRET}"}
