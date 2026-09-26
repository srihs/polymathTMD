"""The Zoom HTTP client (brief 006, criteria 8-11 and 45): hosts, timeouts, the token and its
cache, the one retry, the error mapping, and that nothing secret is logged or reported."""

import base64
import logging
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
import requests
import responses
from django.views.debug import ExceptionReporter
from urllib3.exceptions import ProtocolError

from apps.zoom import zoom_api
from apps.zoom.errors import (
    ProviderError,
    ZoomAuthFailed,
    ZoomBusy,
    ZoomMissingScope,
    ZoomRejected,
    ZoomUnavailable,
    ZoomUserNotFound,
)
from apps.zoom.providers import ZoomProvider

from . import zoommock as zm
from .conftest import make_account, make_request

ZOOM_APP = Path(__file__).resolve().parents[1]
USER_URL = zm.API + "/users/zoom01@polymath.example"


def _client():
    return zoom_api.ZoomClient(zm.credentials())


# --------------------------------------------------------------------------- 45 network block


def test_an_unregistered_zoom_call_never_leaves_the_machine():
    with pytest.raises(requests.exceptions.ConnectionError):
        requests.get("https://api.zoom.us/v2/users/x", timeout=1)


def test_the_client_turns_a_blocked_call_into_no_answer_from_zoom(http_mock):
    with pytest.raises(ZoomUnavailable) as caught:
        _client().get("/users/x")
    assert caught.value.user_message == "no answer from Zoom"
    assert [call.request.url for call in http_mock.calls] == [zm.TOKEN_URL]


# --------------------------------------------------------------------------- 8 hosts and timeouts


def test_every_call_is_https_to_a_fixed_zoom_host_with_timeouts(http_mock):
    zm.add_token(http_mock)
    http_mock.add(responses.GET, USER_URL, json={"type": 2})
    zm.add_listing(http_mock, "zoom01@polymath.example")
    http_mock.add(responses.POST, zm.meetings_url("zoom01@polymath.example"), json={}, status=201)
    http_mock.add(responses.DELETE, zm.meeting_url(123), status=204)

    client = _client()
    client.get("/users/zoom01@polymath.example")
    client.paged("/users/zoom01@polymath.example/meetings", {}, "meetings")
    client.post("/users/zoom01@polymath.example/meetings", {"topic": "x"})
    client.delete("/meetings/123")

    assert len(http_mock.calls) == 5
    for call in http_mock.calls:
        parts = urlsplit(call.request.url)
        assert parts.scheme == "https"
        assert parts.netloc in {"zoom.us", "api.zoom.us"}
        if parts.netloc == "api.zoom.us":
            assert parts.path.startswith("/v2/")
        assert call.request.req_kwargs["timeout"] == (5, 15)
        assert call.request.req_kwargs["verify"] is True


def test_the_hosts_are_module_constants_not_settings():
    assert zoom_api.TOKEN_URL == "https://zoom.us/oauth/token"
    assert zoom_api.API_BASE == "https://api.zoom.us/v2"
    assert zoom_api.TIMEOUT == (5, 15)


def _zoom_source_files():
    return [path for path in ZOOM_APP.rglob("*.py") if "tests" not in path.parts]


def test_no_insecure_http_or_disabled_certificate_checks_in_the_zoom_app():
    """Criterion 8's source scan. Test files are left out: they hold ``http://testserver``."""
    for path in _zoom_source_files():
        text = path.read_text(encoding="utf-8")
        assert "verify=False" not in text, path
        assert "http://" not in text, path


def test_only_zoom_api_imports_requests():
    for path in _zoom_source_files():
        if path.name == "zoom_api.py":
            continue
        text = path.read_text(encoding="utf-8")
        assert "import requests" not in text and "from requests" not in text, path


def test_redirects_are_not_followed(http_mock):
    zm.add_token(http_mock)
    http_mock.add(
        responses.GET, USER_URL, status=302, headers={"Location": "https://evil.example/"}
    )
    with pytest.raises(ZoomRejected):
        _client().get("/users/zoom01@polymath.example")
    assert [urlsplit(c.request.url).netloc for c in http_mock.calls] == ["zoom.us", "api.zoom.us"]


# --------------------------------------------------------------------------- 9 the token


def test_the_token_request_uses_basic_auth_and_sends_the_account_id_in_the_body(http_mock):
    zm.add_token(http_mock)
    http_mock.add(responses.GET, USER_URL, json={"type": 2})
    _client().get("/users/zoom01@polymath.example")

    token_call, api_call = http_mock.calls
    assert token_call.request.method == "POST"
    assert token_call.request.url == zm.TOKEN_URL  # nothing in the query string
    expected = base64.b64encode(f"{zm.CLIENT_ID}:{zm.CLIENT_SECRET}".encode()).decode()
    assert token_call.request.headers["Authorization"] == f"Basic {expected}"
    form = parse_qs(token_call.request.body)
    assert form == {"grant_type": ["account_credentials"], "account_id": [zm.ACCOUNT_ID]}
    assert api_call.request.headers["Authorization"] == f"Bearer {zm.TOKEN}"


def test_the_token_is_reused_until_300_seconds_before_it_expires(http_mock, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(zoom_api, "monotonic", lambda: clock[0])
    zm.add_token(http_mock, zm.TOKEN, expires_in=3600)
    zm.add_token(http_mock, zm.SECOND_TOKEN, expires_in=3600)
    http_mock.add(responses.GET, USER_URL, json={"type": 2})
    client = _client()

    client.get("/users/zoom01@polymath.example")
    clock[0] += 3299  # one second before the refresh point
    _client().get("/users/zoom01@polymath.example")  # another client, same process cache
    assert len(zm.calls_of(http_mock, "POST", "/oauth/token")) == 1

    clock[0] += 1
    client.get("/users/zoom01@polymath.example")
    assert len(zm.calls_of(http_mock, "POST", "/oauth/token")) == 2
    assert http_mock.calls[-1].request.headers["Authorization"] == f"Bearer {zm.SECOND_TOKEN}"


def test_an_api_401_fetches_one_new_token_and_retries_once(http_mock):
    zm.add_token(http_mock, zm.TOKEN)
    zm.add_token(http_mock, zm.SECOND_TOKEN)
    http_mock.add(responses.GET, USER_URL, json={"code": 124}, status=401)
    http_mock.add(responses.GET, USER_URL, json={"type": 2})

    assert _client().get("/users/zoom01@polymath.example") == {"type": 2}
    methods = [(c.request.method, urlsplit(c.request.url).netloc) for c in http_mock.calls]
    assert methods == [
        ("POST", "zoom.us"),
        ("GET", "api.zoom.us"),
        ("POST", "zoom.us"),
        ("GET", "api.zoom.us"),
    ]
    assert http_mock.calls[3].request.headers["Authorization"] == f"Bearer {zm.SECOND_TOKEN}"


def test_a_second_401_is_the_auth_error(http_mock):
    zm.add_token(http_mock, zm.TOKEN)
    zm.add_token(http_mock, zm.SECOND_TOKEN)
    http_mock.add(responses.GET, USER_URL, json={"code": 124}, status=401)
    with pytest.raises(ZoomAuthFailed):
        _client().get("/users/zoom01@polymath.example")
    assert len(http_mock.calls) == 4


def test_the_token_is_not_kept_in_the_client_or_its_repr(http_mock):
    zm.add_token(http_mock)
    http_mock.add(responses.GET, USER_URL, json={"type": 2})
    client = _client()
    client.get("/users/zoom01@polymath.example")
    assert repr(client) == "<ZoomClient: zoom-test>"
    assert zm.TOKEN not in repr(vars(client))


def test_the_client_releases_its_session_when_done(monkeypatch):
    """Review round 1, nit: ``close()`` and ``with`` both close the ``requests.Session``."""
    closed = []
    monkeypatch.setattr(requests.Session, "close", lambda session: closed.append(session))
    with _client() as client:
        assert closed == []
    assert closed == [client._session]
    client.close()  # a second close is harmless
    assert len(closed) == 2

    with pytest.raises(ZoomUnavailable), _client() as failing:
        raise ZoomUnavailable()
    assert closed[-1] is failing._session  # closed, and the error still propagates


# --------------------------------------------------------------------------- 10 error mapping


PHRASES = {
    ZoomUnavailable: "no answer from Zoom",
    ZoomBusy: "Zoom is busy right now",
    ZoomAuthFailed: "Zoom didn't accept this account's connection details",
    ZoomMissingScope: "the Zoom app for this account is missing a permission",
    ZoomUserNotFound: "Zoom has no user with this account's sign-in email",
}


@pytest.mark.parametrize(
    ("kind", "lasting"),
    [
        (ZoomUnavailable, False),
        (ZoomBusy, False),
        (ZoomAuthFailed, True),
        (ZoomMissingScope, True),
        (ZoomUserNotFound, True),
    ],
)
def test_the_lasting_flag_and_phrase_of_each_kind(kind, lasting):
    error = kind()
    assert error.lasting is lasting
    assert error.user_message == PHRASES[kind]
    assert str(error) == PHRASES[kind]


def test_zoom_rejected_is_lasting_and_names_the_code():
    error = ZoomRejected(300)
    assert (error.lasting, error.user_message) == (True, "Zoom error 300")


def test_a_plain_provider_error_is_temporary_and_certain():
    error = ProviderError("Zoom is not responding")
    assert (error.lasting, error.maybe_done) == (False, False)
    assert error.reason_sentence == "Zoom is not responding."


def _mock_get(http_mock, **kwargs):
    zm.add_token(http_mock)
    http_mock.add(responses.GET, USER_URL, **kwargs)


@pytest.mark.parametrize(
    ("reply", "kind", "phrase", "maybe_done"),
    [
        (
            {"body": requests.exceptions.ConnectionError()},
            ZoomUnavailable,
            PHRASES[ZoomUnavailable],
            False,
        ),
        (
            {"body": requests.exceptions.ConnectTimeout()},
            ZoomUnavailable,
            PHRASES[ZoomUnavailable],
            False,
        ),
        (
            {"body": requests.exceptions.ReadTimeout()},
            ZoomUnavailable,
            PHRASES[ZoomUnavailable],
            True,
        ),
        (
            {"body": requests.exceptions.ConnectionError(ProtocolError("Connection aborted."))},
            ZoomUnavailable,
            PHRASES[ZoomUnavailable],
            True,
        ),
        (
            {"status": 500, "json": zm.zoom_error(500)},
            ZoomUnavailable,
            PHRASES[ZoomUnavailable],
            True,
        ),
        ({"status": 503}, ZoomUnavailable, PHRASES[ZoomUnavailable], True),
        ({"status": 429, "json": zm.zoom_error(429)}, ZoomBusy, PHRASES[ZoomBusy], False),
        (
            {"status": 400, "json": zm.zoom_error(4711)},
            ZoomMissingScope,
            PHRASES[ZoomMissingScope],
            False,
        ),
        (
            {"status": 401, "json": zm.zoom_error(4700)},
            ZoomMissingScope,
            PHRASES[ZoomMissingScope],
            False,
        ),
        (
            {"status": 404, "json": zm.zoom_error(1001)},
            ZoomUserNotFound,
            PHRASES[ZoomUserNotFound],
            False,
        ),
        ({"status": 404, "json": zm.zoom_error(3001)}, ZoomRejected, "Zoom error 3001", False),
        ({"status": 400, "json": zm.zoom_error(300)}, ZoomRejected, "Zoom error 300", False),
        ({"status": 403, "body": "<html>no</html>"}, ZoomRejected, "Zoom error 403", False),
    ],
)
def test_api_failures_map_to_fixed_phrases(http_mock, reply, kind, phrase, maybe_done):
    _mock_get(http_mock, **reply)
    with pytest.raises(kind) as caught:
        _client().get("/users/zoom01@polymath.example")
    error = caught.value
    assert type(error) is kind
    assert (error.user_message, str(error), error.maybe_done) == (phrase, phrase, maybe_done)
    assert error.__suppress_context__ or error.__context__ is None
    for leak in (*zm.SECRETS, "RAW-ZOOM-TEXT", "http", "zoom01@"):
        assert leak not in str(error)


def test_a_scope_error_is_not_retried(http_mock):
    _mock_get(http_mock, status=401, json=zm.zoom_error(4711))
    with pytest.raises(ZoomMissingScope):
        _client().get("/users/zoom01@polymath.example")
    assert len(http_mock.calls) == 2  # the token and one call


@pytest.mark.parametrize(
    ("reply", "kind"),
    [
        ({"status": 400, "json": {"reason": "invalid_client"}}, ZoomAuthFailed),
        ({"status": 401, "json": {"reason": "invalid_client"}}, ZoomAuthFailed),
        ({"status": 429}, ZoomBusy),
        ({"status": 502}, ZoomUnavailable),
        ({"body": requests.exceptions.ReadTimeout()}, ZoomUnavailable),
        ({"status": 200, "json": {"no_token": True}}, ZoomUnavailable),
    ],
)
def test_token_failures(http_mock, reply, kind):
    http_mock.add(responses.POST, zm.TOKEN_URL, **reply)
    with pytest.raises(kind) as caught:
        _client().get("/users/zoom01@polymath.example")
    # A failed token fetch never reached the API, so it can't have made anything.
    assert caught.value.maybe_done is False
    assert len(http_mock.calls) == 1


def test_there_is_no_automatic_retry_on_429_5xx_or_timeouts(http_mock):
    for reply in ({"status": 429}, {"status": 500}, {"body": requests.exceptions.ReadTimeout()}):
        http_mock.reset()
        zm.add_token(http_mock)
        http_mock.add(responses.POST, zm.meetings_url("z@polymath.example"), **reply)
        with pytest.raises(ProviderError):
            _client().post("/users/z@polymath.example/meetings", {"topic": "x"})
        assert len(zm.calls_of(http_mock, "POST", "/meetings")) == 1


def test_a_delete_of_a_meeting_zoom_no_longer_has_counts_as_done(http_mock):
    zm.add_token(http_mock)
    http_mock.add(responses.DELETE, zm.meeting_url(123), status=404, json=zm.zoom_error(3001))
    _client().delete("/meetings/123")


# --------------------------------------------------------------------------- paging


def test_paging_follows_next_page_token_up_to_ten_pages(http_mock):
    zm.add_token(http_mock)
    url = zm.meetings_url("z@polymath.example")
    for page in range(1, 4):
        http_mock.add(
            responses.GET,
            url,
            json={"meetings": [{"id": page}], "next_page_token": "" if page == 3 else f"p{page}"},
        )
    items = _client().paged("/users/z@polymath.example/meetings", {"page_size": 300}, "meetings")
    assert [item["id"] for item in items] == [1, 2, 3]
    tokens = [zm.query(call).get("next_page_token") for call in zm.calls_of(http_mock, "GET")]
    assert tokens == [None, "p1", "p2"]


def test_more_than_ten_pages_fails_closed(http_mock):
    zm.add_token(http_mock)
    http_mock.add(
        responses.GET,
        zm.meetings_url("z@polymath.example"),
        json={"meetings": [{"id": 1}], "next_page_token": "more"},
    )
    with pytest.raises(ZoomUnavailable):
        _client().paged("/users/z@polymath.example/meetings", {}, "meetings")
    assert len(zm.calls_of(http_mock, "GET")) == 10


# ---------------------------------------------------------------- 11 nothing secret logged


@pytest.mark.django_db
def test_nothing_secret_is_logged_or_in_any_error(http_mock, settings, caplog):
    account = make_account("Zoom 01", host_key="8421973")
    zm.connect(settings, account)
    link_request = make_request()
    occurrences = list(link_request.occurrences.all())
    provider = ZoomProvider()
    raised = []

    for name in ("apps.zoom", "django", "urllib3", "requests"):
        caplog.set_level(logging.DEBUG, logger=name)
    caplog.set_level(logging.DEBUG)

    zm.add_token(http_mock)
    zm.add_listing(http_mock, account.email, [zm.scheduled(1, zm.CLASS_START, 60)])
    provider.busy_times(
        host_account=account, start=occurrences[0].starts_at, end=occurrences[0].ends_at
    )
    zm.add_create(http_mock, account.email)
    meeting = provider.create_meeting(
        link_request=link_request, host_account=account, occurrences=occurrences
    )
    assert zm.START_URL not in repr(meeting) and zm.PASSCODE not in repr(meeting)
    zm.add_delete(http_mock)
    provider.delete_meeting(host_account=account, meeting_id=meeting.meeting_id)

    failures = [
        {"status": 500},
        {"status": 429},
        {"status": 400, "json": zm.zoom_error(4711)},
        {"status": 404, "json": zm.zoom_error(1001)},
        {"status": 400, "json": zm.zoom_error(300)},
        {"body": requests.exceptions.ReadTimeout()},
    ]
    for reply in failures:
        http_mock.reset()
        zm.add_token(http_mock)
        http_mock.add(responses.GET, zm.meetings_url(account.email), **reply)
        with pytest.raises(ProviderError) as caught:
            provider.busy_times(
                host_account=account,
                start=occurrences[0].starts_at,
                end=occurrences[0].ends_at,
            )
        raised.append(caught.value)
    http_mock.reset()
    zm.add_token(http_mock, status=401)
    zoom_api.reset_token_cache()
    with pytest.raises(ZoomAuthFailed) as caught:
        provider.check_connection(account)
    raised.append(caught.value)

    forbidden = (*zm.SECRETS, "Basic ", "Bearer ", zm.JOIN_URL, zm.PASSCODE, zm.START_URL)
    texts = [record.getMessage() for record in caplog.records] + [str(e) for e in raised]
    for text in texts:
        for secret in forbidden:
            assert secret not in text, (secret, text)


def _raise_inside_the_token_fetch():
    """Keeps every credential out of the test's own frame, whose locals a report would show."""
    zoom_api.ZoomClient(zm.credentials()).get("/users/zoom01@polymath.example")


def test_an_error_report_from_inside_the_token_fetch_masks_the_secret(http_mock):
    http_mock.add(responses.POST, zm.TOKEN_URL, status=401, json={"reason": "invalid_client"})
    try:
        _raise_inside_the_token_fetch()
    except ZoomAuthFailed:
        report = ExceptionReporter(None, *sys.exc_info())
        text = report.get_traceback_text()
        frames = report.get_traceback_frames()
    else:
        pytest.fail("the token fetch should have raised")

    for secret in zm.SECRETS:
        assert secret not in text
    [fetch] = [frame for frame in frames if frame["function"] == "_fetch_token"]
    shown = dict(fetch["vars"])
    for name in ("credentials", "auth", "data", "response"):
        assert shown[name] == "********************", name
    # requests' own frames (with the prepared headers) never make it into the report.
    assert not [frame for frame in frames if "requests" in frame["filename"].split("/")[-2:]]


def test_sensitive_variables_mark_every_function_holding_a_secret_or_token():
    for function in (
        zoom_api.ZoomClient.__init__,
        zoom_api.ZoomClient.paged,
        zoom_api.ZoomClient._json,
        zoom_api.ZoomClient._call,
        zoom_api.ZoomClient._send,
        zoom_api.ZoomClient._token,
        zoom_api.ZoomClient._drop_token,
        zoom_api.ZoomClient._fetch_token,
        ZoomProvider._client,
        ZoomProvider.busy_times,
        ZoomProvider.create_meeting,
    ):
        assert function.__code__.co_name == "sensitive_variables_wrapper", function
