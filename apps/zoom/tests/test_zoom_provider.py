"""The live Zoom provider against mocked Zoom (brief 006, criteria 12, 14, 22, 23, 25, 36 and
49): what counts as busy, the create body, the delete, and the connection check's calls."""

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
import responses

from apps.zoom.providers import (
    PROVIDERS,
    BusyTime,
    FakeProvider,
    ManualProvider,
    ZoomNotConnected,
    ZoomProvider,
    ZoomUnavailable,
    zoom_weekly_days,
)

from . import zoommock as zm
from .conftest import make_account, make_request

pytestmark = pytest.mark.django_db

ZOOM_APP = Path(__file__).resolve().parents[1]
EMAIL = "zoom01@polymath.example"
WINDOW = (datetime(2026, 10, 5, 3, 0, tzinfo=UTC), datetime(2026, 10, 5, 6, 0, tzinfo=UTC))


@pytest.fixture
def zoom_account(settings):
    account = make_account("Zoom 01", host_key="8421973")
    zm.connect(settings, account)
    return account


# --------------------------------------------------------------------------- 1, 14


def test_the_providers_are_exactly_fake_manual_and_zoom():
    assert list(PROVIDERS) == ["fake", "manual", "zoom"]


@pytest.mark.parametrize(("iso", "zoom"), [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 1)])
def test_iso_weekdays_map_to_zooms_numbering(iso, zoom):
    assert zoom_weekly_days(str(iso)) == str(zoom)


def test_monday_and_wednesday_are_two_and_four():
    assert zoom_weekly_days("1,3") == "2,4"


def test_only_the_manual_provider_is_blind_to_zoom():
    assert (FakeProvider.checks_zoom, ManualProvider.checks_zoom, ZoomProvider.checks_zoom) == (
        True,
        False,
        True,
    )


# --------------------------------------------------------------------------- 12 busy times


def test_busy_times_lists_dated_meetings_across_pages_and_expands_series(http_mock, zoom_account):
    zm.add_token(http_mock)
    url = zm.meetings_url(EMAIL)
    page_one = [
        zm.scheduled(101, "2026-10-05T02:30:00Z", 120, topic="Revision"),  # 8:00-10:00
        {"id": 555, "type": 8, "topic": "Series (listing)", "start_time": "2026-10-05T04:00:00Z"},
        {"id": 556, "type": 3, "topic": "No fixed time"},
        {
            "id": 557,
            "type": 4,
            "topic": "PMI",
            "start_time": "2026-10-05T03:30:00Z",
            "duration": 60,
        },
        {"id": 558, "type": 1, "topic": "Instant", "start_time": "2026-10-05T03:30:00Z"},
    ]
    page_two = [
        zm.scheduled(102, "2026-10-05T02:00:00Z", 60, topic="Touches the start"),  # ends 03:00
        zm.scheduled(103, "2026-10-05T06:00:00Z", 30, topic="Touches the end"),  # starts 06:00
        {"id": 104, "type": 2, "topic": "No start"},
        {"id": 555, "type": 8, "topic": "Series again", "start_time": "2026-10-12T04:00:00Z"},
    ]
    http_mock.add(
        responses.GET,
        url,
        json={"meetings": page_one, "next_page_token": "page-2"},
        match=[responses.matchers.query_param_matcher({"type": "scheduled", "page_size": "300"})],
    )
    http_mock.add(
        responses.GET,
        url,
        json={"meetings": page_two, "next_page_token": ""},
        match=[
            responses.matchers.query_param_matcher(
                {"next_page_token": "page-2"}, strict_match=False
            )
        ],
    )
    http_mock.add(
        responses.GET,
        zm.meeting_url(555),
        json={
            "id": 555,
            "type": 8,
            "topic": "Grade 10 series",
            "agenda": "Polymath TMD ZL-0007",
            "duration": 45,
            "occurrences": [
                {
                    "occurrence_id": "1",
                    "start_time": "2026-10-05T03:15:00Z",
                    "duration": 45,
                    "status": "available",
                },
                {
                    "occurrence_id": "2",
                    "start_time": "2026-10-05T05:00:00Z",
                    "duration": 45,
                    "status": "deleted",
                },
                {"occurrence_id": "3", "start_time": "2026-10-12T03:15:00Z", "status": "available"},
            ],
        },
    )

    busy = ZoomProvider().busy_times(host_account=zoom_account, start=WINDOW[0], end=WINDOW[1])

    assert busy == [
        BusyTime(
            datetime(2026, 10, 5, 2, 30, tzinfo=UTC),
            datetime(2026, 10, 5, 4, 30, tzinfo=UTC),
            "Revision",
            "101",
            "",
        ),
        BusyTime(
            datetime(2026, 10, 5, 3, 15, tzinfo=UTC),
            datetime(2026, 10, 5, 4, 0, tzinfo=UTC),
            "Grade 10 series",
            "555",
            "Polymath TMD ZL-0007",
        ),
    ]
    assert all(item.starts_at.tzinfo is UTC for item in busy)
    # The series is read once, however often it is listed; nothing else is read.
    assert len(zm.calls_of(http_mock, "GET", "/meetings/555")) == 1
    assert len(zm.calls_of(http_mock, "GET", "/meetings")) == 2


def test_busy_times_fails_closed_after_ten_pages(http_mock, zoom_account):
    zm.add_token(http_mock)
    zm.add_listing(http_mock, EMAIL, body={"meetings": [], "next_page_token": "always-more"})
    with pytest.raises(ZoomUnavailable):
        ZoomProvider().busy_times(host_account=zoom_account, start=WINDOW[0], end=WINDOW[1])


@pytest.mark.parametrize(
    "listed",
    [
        [zm.scheduled(101, "garbage", 60)],
        [zm.scheduled(101, 12345, 60)],
        ["not a meeting"],
        [zm.scheduled(101, "2026-10-05T02:30:00Z", 10**12)],
    ],
    ids=["text-time", "number-time", "not-an-object", "endless-duration"],
)
def test_an_answer_that_cant_be_read_is_zoom_unavailable(http_mock, zoom_account, listed):
    """Review round 1, SF1: never a bare ValueError, which approve() wouldn't catch."""
    zm.add_token(http_mock)
    zm.add_listing(http_mock, EMAIL, listed)
    with pytest.raises(ZoomUnavailable) as caught:
        ZoomProvider().busy_times(host_account=zoom_account, start=WINDOW[0], end=WINDOW[1])
    # Raised ``from None``, like every other Zoom failure: no parser frame in the report.
    assert caught.value.__cause__ is None and caught.value.__suppress_context__


def test_a_series_that_cant_be_read_is_zoom_unavailable(http_mock, zoom_account):
    zm.add_token(http_mock)
    zm.add_listing(http_mock, EMAIL, [{"id": 555, "type": 8, "topic": "Series"}])
    http_mock.add(
        responses.GET,
        zm.meeting_url(555),
        json={"id": 555, "type": 8, "occurrences": [{"start_time": "5 Oct, 8 am"}]},
    )
    with pytest.raises(ZoomUnavailable) as caught:
        ZoomProvider().busy_times(host_account=zoom_account, start=WINDOW[0], end=WINDOW[1])
    assert caught.value.__cause__ is None and caught.value.__suppress_context__


def test_every_zoom_call_closes_its_client(http_mock, zoom_account, monkeypatch):
    """Review round 1, nit: each call's ``requests.Session`` is released when it ends."""
    closed = []
    monkeypatch.setattr(
        "apps.zoom.zoom_api.ZoomClient.close", lambda client: closed.append(client.slug)
    )
    zm.add_token(http_mock)
    zm.add_listing(http_mock, EMAIL)
    zm.add_delete(http_mock, 777)
    provider = ZoomProvider()
    provider.busy_times(host_account=zoom_account, start=WINDOW[0], end=WINDOW[1])
    provider.delete_meeting(host_account=zoom_account, meeting_id="777")
    assert closed == [zm.SLUG, zm.SLUG]

    zm.add_listing(http_mock, EMAIL, status=503)
    with pytest.raises(ZoomUnavailable):
        provider.busy_times(host_account=zoom_account, start=WINDOW[0], end=WINDOW[1])
    assert closed == [zm.SLUG] * 3  # closed on the way out of a failure too


def test_a_zoom_meeting_with_no_topic_has_a_plain_name():
    """Review round 1, SF3: the page and criterion 26's message share this one fallback."""
    start = WINDOW[0]
    assert BusyTime(start, WINDOW[1], "", "1").display_topic == "a meeting with no name"
    assert BusyTime(start, WINDOW[1], "Revision", "1").display_topic == "Revision"


def test_busy_times_for_an_account_without_a_connection_makes_no_call(http_mock):
    account = make_account("Zoom 02")
    with pytest.raises(ZoomNotConnected):
        ZoomProvider().busy_times(host_account=account, start=WINDOW[0], end=WINDOW[1])
    assert len(http_mock.calls) == 0


def test_is_connected_follows_the_accounts_connection_state(settings, zoom_account):
    assert ZoomProvider().is_connected(zoom_account)
    zoom_account.credential_set = "zoom-other"
    assert not ZoomProvider().is_connected(zoom_account)


# --------------------------------------------------------------------------- 22, 23, 25, 49 create


def _create(http_mock, account, link_request, **created):
    zm.add_token(http_mock)
    zm.add_create(http_mock, account.email, **created)
    meeting = ZoomProvider().create_meeting(
        link_request=link_request,
        host_account=account,
        occurrences=list(link_request.occurrences.all()),
    )
    [call] = zm.calls_of(http_mock, "POST", "/meetings")
    return meeting, zm.body(call)


def test_a_one_off_class_is_one_scheduled_meeting_with_exactly_this_body(http_mock, zoom_account):
    link_request = make_request(class_name="Grade 11 Physics", wants_recording=False)
    meeting, sent = _create(http_mock, zoom_account, link_request)

    assert sent == {
        "topic": "Grade 11 Physics",
        "type": 2,
        "start_time": "2026-10-05T08:30:00",
        "timezone": "Asia/Colombo",
        "duration": 180,
        "agenda": f"Polymath TMD ZL-{link_request.pk:04d}",
        "settings": {"auto_recording": "none"},
    }
    assert (meeting.meeting_id, meeting.join_url, meeting.passcode) == (
        str(zm.MEETING_ID),
        zm.JOIN_URL,
        zm.PASSCODE,
    )
    assert meeting.recurring is False and meeting.occurrence_ids == ()
    assert not hasattr(meeting, "start_url")
    assert zm.START_URL not in repr(meeting)


def test_a_weekly_class_is_one_series_starting_at_the_first_class(http_mock, zoom_account):
    link_request = make_request(weekdays="1,3", last_date=date(2026, 10, 28))
    starts_utc = [o.starts_at for o in link_request.occurrences.all()]
    meeting, sent = _create(
        http_mock,
        zoom_account,
        link_request,
        occurrences=[o.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ") for o in starts_utc],
    )
    assert len(starts_utc) == 8
    assert sent["type"] == 8
    assert sent["start_time"] == "2026-10-05T08:30:00"
    assert sent["recurrence"] == {
        "type": 2,
        "repeat_interval": 1,
        "weekly_days": "2,4",
        "end_times": 8,
    }
    assert meeting.recurring is True
    assert [start for start, _ in meeting.occurrence_ids] == starts_utc
    assert len({occurrence_id for _, occurrence_id in meeting.occurrence_ids}) == 8


def _keys(value):
    if isinstance(value, dict):
        for key, inner in value.items():
            yield key
            yield from _keys(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from _keys(inner)


@pytest.mark.parametrize("weekly", [False, True])
@pytest.mark.parametrize("recording", [False, True])
def test_only_auto_recording_is_set_and_zooms_other_defaults_are_left_alone(
    http_mock, zoom_account, weekly, recording
):
    """Criteria 25 and 49 (owner, Q1: "Keep Zoom's defaults")."""
    extra = {"weekdays": "1,3", "last_date": date(2026, 10, 28)} if weekly else {}
    link_request = make_request(wants_recording=recording, **extra)
    _, sent = _create(http_mock, zoom_account, link_request)
    assert sent["settings"] == {"auto_recording": "cloud" if recording else "none"}
    assert not {"join_before_host", "jbh_time", "waiting_room"} & set(_keys(sent))


def test_no_zoom_code_names_join_before_host_or_the_waiting_room():
    for path in ZOOM_APP.rglob("*.py"):
        if "tests" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for name in ("join_before_host", "jbh_time", "waiting_room"):
            assert name not in text, (name, path)


def test_an_answer_without_a_link_counts_as_no_answer(http_mock, zoom_account):
    link_request = make_request()
    zm.add_token(http_mock)
    zm.add_create(http_mock, zoom_account.email, body={"id": 1})
    with pytest.raises(ZoomUnavailable) as caught:
        ZoomProvider().create_meeting(
            link_request=link_request,
            host_account=zoom_account,
            occurrences=list(link_request.occurrences.all()),
        )
    assert caught.value.maybe_done is True


# --------------------------------------------------------------------------- delete


def test_delete_sends_no_reminder_and_can_name_one_class(http_mock, zoom_account):
    zm.add_token(http_mock)
    zm.add_delete(http_mock, 123)
    provider = ZoomProvider()
    provider.delete_meeting(host_account=zoom_account, meeting_id="123")
    provider.delete_meeting(host_account=zoom_account, meeting_id="123", occurrence_id="1759")
    first, second = zm.calls_of(http_mock, "DELETE")
    assert zm.query(first) == {"schedule_for_reminder": "false"}
    assert zm.query(second) == {"schedule_for_reminder": "false", "occurrence_id": "1759"}


# --------------------------------------------------------------------------- 36 the check's calls


def test_check_connection_proves_the_token_the_user_and_the_list_scope(http_mock, zoom_account):
    zm.add_token(http_mock)
    http_mock.add(responses.GET, zm.API + f"/users/{EMAIL}", json={"type": 2})
    zm.add_listing(http_mock, EMAIL)
    assert ZoomProvider().check_connection(zoom_account) == 2
    token, user, listing = http_mock.calls
    assert token.request.url == zm.TOKEN_URL
    assert user.request.url == zm.API + f"/users/{EMAIL}"
    assert listing.request.url.startswith(zm.meetings_url(EMAIL))
    assert zm.query(listing) == {"page_size": "1"}
