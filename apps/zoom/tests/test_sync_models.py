"""Brief 013, the model layer: where a change came from (criterion 27), the needs-a-look flag
and its clearing (15, 28), ``ZoomEvent`` (11, 29's aggregate), the webhook-secret question
(29), ``zoom.W002`` (2), reading Zoom's meeting (13) and the comparison rules (14), which are
pure and tested here without the database's locks or Zoom.
"""

import re
from datetime import timedelta
from unittest import mock

import pytest
from django.db import ProgrammingError, connection
from django.test.utils import CaptureQueriesContext

from apps.zoom import checks as zoom_checks
from apps.zoom import services, sync
from apps.zoom.models import (
    CANCELLED_IN_ZOOM_REASON,
    HostAccount,
    LinkRequest,
    Occurrence,
    ZoomEvent,
    webhook_secret_set_for,
)
from apps.zoom.providers import (
    MeetingState,
    ZoomClass,
    ZoomUnavailable,
    read_meeting_state,
)

from . import synckit as kit
from .conftest import FROZEN_NOW, make_account

pytestmark = pytest.mark.django_db
at = kit.at


@pytest.fixture
def zoom02(db):
    return make_account("Zoom 02", sort_order=2)


# --------------------------------------------------------------------------- 27 where from


@pytest.mark.parametrize(
    ("when", "who", "expected"),
    [(False, False, False), (True, False, True), (True, True, False), (False, True, False)],
)
def test_the_zoom_properties_need_a_time_and_no_person(it_user, zoom02, when, who, expected):
    booking = kit.zl42(zoom02)
    occurrence = booking.occurrences.first()
    moment = FROZEN_NOW if when else None
    person = it_user if who else None
    occurrence.moved_at, occurrence.moved_by = moment, person
    occurrence.cancelled_at, occurrence.cancelled_by = moment, person
    booking.cancelled_at, booking.cancelled_by = moment, person
    with CaptureQueriesContext(connection) as queries:
        found = (occurrence.moved_in_zoom, occurrence.cancelled_in_zoom, booking.cancelled_in_zoom)
    assert found == (expected, expected, expected)
    assert len(queries) == 0


def test_attention_lines_are_the_non_empty_lines(zoom02):
    booking = kit.zl42(zoom02)
    assert booking.zoom_attention_lines == []
    booking.zoom_attention = "First sentence.\n\nSecond sentence."
    assert booking.zoom_attention_lines == ["First sentence.", "Second sentence."]


# --------------------------------------------------------------------------- 28 never outlives


def test_cancelling_a_flagged_booking_in_the_app_clears_its_flag(zoom02, it_user):
    booking = kit.zl43(zoom02)
    LinkRequest.objects.filter(pk=booking.pk).update(zoom_attention="Something.")
    result = services.cancel(booking.pk, by=it_user, reason="Closed.")
    assert result.outcome == services.Outcome.CANCELLED
    booking.refresh_from_db()
    assert booking.status == LinkRequest.Status.CANCELLED and booking.zoom_attention == ""


def test_cancelling_one_class_keeps_the_flag_while_classes_remain(zoom02, it_user):
    booking = kit.zl42(zoom02)
    LinkRequest.objects.filter(pk=booking.pk).update(zoom_attention="Something.")
    wed7 = booking.occurrences.get(starts_at=at(7, 8, 30))
    services.cancel(booking.pk, occurrence_id=wed7.pk, by=it_user, reason="Closed.")
    booking.refresh_from_db()
    assert booking.zoom_attention == "Something."


def test_the_sweep_clears_only_approved_bookings_with_nothing_left_in_one_update(zoom02):
    held = kit.zl43(zoom02, meeting_id="81111111111", first_date=at(21, 0, month=9).date())
    still_on = kit.zl42(zoom02)
    LinkRequest.objects.update(zoom_attention="Something.")
    with CaptureQueriesContext(connection) as queries:
        cleared = LinkRequest.objects.clear_stale_attention()
    assert cleared == 1
    assert len(queries) == 1 and queries[0]["sql"].startswith("UPDATE")
    held.refresh_from_db()
    still_on.refresh_from_db()
    assert held.zoom_attention == "" and still_on.zoom_attention == "Something."


# --------------------------------------------------------------------------- 11 ZoomEvent


def test_a_zoom_event_keeps_no_body_header_url_or_token():
    names = {field.name for field in ZoomEvent._meta.get_fields()}
    assert names == {
        "id",
        "slug",
        "event",
        "body_sha256",
        "event_ts",
        "received_at",
        "outcome",
        "link_request",
    }
    for name in names:
        assert not re.search(r"body$|header|url|token|secret|signature", name)
    assert {value for value, _ in ZoomEvent.Outcome.choices} == {
        "changed",
        "no_change",
        "needs_a_look",
        "ignored",
        "not_ours",
    }
    field = ZoomEvent._meta.get_field("link_request")
    assert field.null and field.remote_field.on_delete.__name__ == "SET_NULL"


def test_one_row_per_connection_and_body():
    ZoomEvent.objects.create(slug="zoom-02", event="x", body_sha256="a" * 64, outcome="ignored")
    ZoomEvent.objects.create(slug="zoom-03", event="x", body_sha256="a" * 64, outcome="ignored")
    from django.db import IntegrityError, transaction

    with pytest.raises(IntegrityError), transaction.atomic():
        ZoomEvent.objects.create(slug="zoom-02", event="y", body_sha256="a" * 64, outcome="x")


def test_last_received_at_is_the_newest_event_for_the_name_in_one_query(monkeypatch):
    assert ZoomEvent.objects.last_received_at("zoom-02") is None
    for minutes, slug in ((0, "zoom-02"), (5, "zoom-02"), (9, "zoom-03")):
        moment = FROZEN_NOW + timedelta(minutes=minutes)
        monkeypatch.setattr("django.utils.timezone.now", lambda moment=moment: moment)
        ZoomEvent.objects.create(
            slug=slug, event="x", body_sha256=f"{minutes:064d}", outcome="ignored"
        )
    with CaptureQueriesContext(connection) as queries:
        found = ZoomEvent.objects.last_received_at("zoom-02")
    assert found == FROZEN_NOW + timedelta(minutes=5)
    assert len(queries) == 1


# --------------------------------------------------------------------------- 29 the question


def test_webhook_secret_set_reads_settings_only(settings):
    kit.connect(settings, extra={"zoom-03": kit.credentials("zoom-03", secret="")})
    with CaptureQueriesContext(connection) as queries:
        found = [webhook_secret_set_for(name) for name in ("zoom-02", "zoom-03", "zoom-99", "")]
    assert found == [True, False, False, False]
    assert len(queries) == 0


# --------------------------------------------------------------------------- 2 zoom.W002

W002 = (
    "{label}'s Zoom connection has no webhook secret, so changes made directly in Zoom to its "
    "meetings aren't seen here."
)


def test_w002_warns_for_each_connected_paid_account_without_a_secret(settings, zoom02):
    zoom03 = make_account("Zoom 03", sort_order=3)
    make_account("Zoom 04", sort_order=4)  # no connection at all: E004's, not W002's
    make_account("Zoom 05", sort_order=5, is_paid=False)
    kit.connect(settings, zoom02, extra={"zoom-03": kit.credentials("zoom-03", secret="")})
    zoom03.credential_set = "zoom-03"
    zoom03.save()
    settings.ZOOM_PROVIDER = "zoom"
    found = zoom_checks.check_webhook_secrets(databases=["default"])
    assert [(w.id, w.msg) for w in found] == [("zoom.W002", W002.format(label="Zoom 03"))]
    assert "test-webhook-secret" not in str(found)


@pytest.mark.parametrize("provider", ["fake", "manual"])
def test_w002_is_silent_without_the_zoom_provider(settings, zoom02, provider):
    kit.connect(settings, zoom02, secret="")
    settings.ZOOM_PROVIDER = provider
    assert zoom_checks.check_webhook_secrets(databases=["default"]) == []


def test_w002_needs_the_database_tag_and_is_quiet_before_the_table_exists(settings, zoom02):
    kit.connect(settings, zoom02, secret="")
    settings.ZOOM_PROVIDER = "zoom"
    assert zoom_checks.check_webhook_secrets(databases=None) == []
    with mock.patch.object(
        HostAccount.objects, "bookable", side_effect=ProgrammingError(1146, "doesn't exist")
    ):
        assert zoom_checks.check_webhook_secrets(databases=["default"]) == []


def test_w002_is_registered_with_the_database_tag():
    from django.core.checks import registry

    assert zoom_checks.check_webhook_secrets in registry.registry.get_checks(
        include_deployment_checks=False
    )
    assert "database" in zoom_checks.check_webhook_secrets.tags


# --------------------------------------------------------------------------- 13 reading Zoom


def test_a_scheduled_meeting_is_one_class():
    state = read_meeting_state(kit.single_detail(at(6, 9), 180))
    assert state == MeetingState(False, (ZoomClass(at(6, 9), at(6, 12), ""),))


def test_a_series_keeps_its_classes_and_names_its_deleted_ones():
    detail = kit.series_detail([("2", at(7, 8, 30), 120)], deleted=[("1", at(5, 8, 30))])
    state = read_meeting_state(detail)
    assert state == MeetingState(
        True, (ZoomClass(at(7, 8, 30), at(7, 10, 30), "2"),), frozenset({"1"})
    )
    assert "start_url" not in repr(state) and "zoom.us" not in repr(state)


@pytest.mark.parametrize(
    "detail",
    [
        {"type": 3, "occurrences": []},  # recurring with no fixed time
        {"type": 1},  # instant
        {"type": 2, "start_time": "not a time"},
        {"type": 8, "occurrences": [{"start_time": "2026-10-05T03:00:00Z"}]},  # no ID
    ],
)
def test_a_meeting_with_no_dated_classes_to_compare_is_unavailable(detail):
    with pytest.raises(ZoomUnavailable):
        read_meeting_state(detail)


# --------------------------------------------------------------------------- 14 the rules


def _state(booking, *, moved=None, missing=(), deleted=(), extra=()):
    """``MeetingState`` for a weekly booking as stored, with changes (see ``booking_series``)."""
    return read_meeting_state(
        kit.booking_series(booking, moved=moved, missing=missing, deleted=deleted, extra=extra)
    )


def _compare(booking, state, now=FROZEN_NOW):
    classes = list(booking.occurrences.order_by("starts_at", "pk"))
    return sync.compare(booking, classes, state, now)


def test_a_meeting_gone_cancels_every_remaining_class(zoom02):
    booking = kit.zl42(zoom02)
    found = _compare(booking, None, now=at(7, 9))  # Mon 5 held, Wed 7 in progress
    assert [o.starts_at for o in found.cancel] == [
        at(day, 8, 30) for day in (12, 14, 19, 21, 26, 28)
    ]
    assert found.moves == [] and found.extra == []


def test_a_class_zoom_lists_as_deleted_is_cancelled(zoom02):
    booking = kit.zl42(zoom02)
    found = _compare(booking, _state(booking, deleted=[at(7, 8, 30)]))
    assert [o.starts_at for o in found.cancel] == [at(7, 8, 30)]


def test_a_class_zoom_no_longer_has_is_cancelled_when_nothing_else_is_odd(zoom02):
    booking = kit.zl42(zoom02)
    found = _compare(booking, _state(booking, missing=[at(26, 8, 30), at(28, 8, 30)]))
    assert [o.starts_at for o in found.cancel] == [at(26, 8, 30), at(28, 8, 30)]


def test_a_series_rebuilt_in_zoom_cancels_nothing_and_names_zoom_s_classes(zoom02):
    booking = kit.zl42(zoom02)
    every = [o.starts_at for o in booking.occurrences.all()]
    extra = [(start + timedelta(minutes=30), 180) for start in every]
    found = _compare(booking, _state(booking, missing=every, extra=extra))
    assert found.cancel == [] and found.moves == []
    assert [item.starts_at for item in found.extra] == [start for start, _ in extra]


def test_a_class_moved_in_zoom_is_found_by_its_id(zoom02):
    booking = kit.zl42(zoom02)
    found = _compare(booking, _state(booking, moved={at(12, 8, 30): (at(13, 9), 180)}))
    [(occurrence, item)] = found.moves
    assert occurrence.starts_at == at(12, 8, 30)
    assert (item.starts_at, item.ends_at) == (at(13, 9), at(13, 12))
    assert found.cancel == [] and found.extra == []


def test_a_class_whose_length_changed_is_a_move(zoom02):
    booking = kit.zl42(zoom02)
    found = _compare(booking, _state(booking, moved={at(14, 8, 30): (at(14, 8, 30), 120)}))
    [(occurrence, item)] = found.moves
    assert occurrence.starts_at == at(14, 8, 30) and item.ends_at == at(14, 10, 30)


def test_a_one_off_is_paired_with_its_single_meeting_whatever_its_time(zoom02):
    booking = kit.zl43(zoom02)
    found = _compare(booking, read_meeting_state(kit.single_detail(at(6, 9), 180)))
    [(occurrence, item)] = found.moves
    assert occurrence.starts_at == at(5, 8, 30) and item.starts_at == at(6, 9)


def test_a_class_added_in_zoom_is_extra_and_changes_nothing(zoom02):
    booking = kit.zl42(zoom02)
    found = _compare(booking, _state(booking, extra=[(at(8, 9), 180)]))
    assert found.cancel == [] and found.moves == []
    assert [(i.starts_at, i.ends_at) for i in found.extra] == [(at(8, 9), at(8, 12))]


def test_only_the_topic_changing_is_no_difference(zoom02):
    booking = kit.zl42(zoom02)
    detail = kit.booking_series(booking)
    detail.update(topic="A new name", agenda="New agenda", settings={"waiting_room": True})
    found = _compare(booking, read_meeting_state(detail))
    assert (found.cancel, found.moves, found.extra) == ([], [], [])


def test_held_classes_are_never_changed_and_never_extra(zoom02):
    booking = kit.zl42(zoom02)
    now = at(8, 9)  # Mon 5 and Wed 7 have been held
    state = _state(booking, moved={at(5, 8, 30): (at(5, 9), 180)}, deleted=[at(7, 8, 30)], extra=[])
    found = _compare(booking, state, now=now)
    assert (found.cancel, found.moves, found.extra) == ([], [], [])


def test_a_class_with_no_stored_id_is_matched_by_its_start(zoom02):
    booking = kit.zl42(zoom02, occurrence_ids=False)
    state = read_meeting_state(
        kit.series_detail(
            [(kit.occurrence_id(o.starts_at), o.starts_at, 180) for o in booking.occurrences.all()]
        )
    )
    found = _compare(booking, state)
    assert (found.cancel, found.moves, found.extra) == ([], [], [])


def test_cancelled_classes_claim_nothing_so_zoom_still_having_one_is_extra(zoom02, it_user):
    booking = kit.zl42(zoom02)
    wed7 = booking.occurrences.get(starts_at=at(7, 8, 30))
    Occurrence.objects.filter(pk=wed7.pk).update(
        cancelled_at=FROZEN_NOW, cancelled_by=it_user, cancel_reason="x"
    )
    state = read_meeting_state(
        kit.series_detail(
            [(o.zoom_occurrence_id, o.starts_at, 180) for o in booking.occurrences.all()]
        )
    )
    found = _compare(booking, state)
    assert [item.starts_at for item in found.extra] == [at(7, 8, 30)]
    assert found.cancel == [] and found.moves == []


def test_the_stored_reason_is_pinned():
    assert CANCELLED_IN_ZOOM_REASON == "Cancelled directly in Zoom."


# --------------------------------------------------------------------------- 21, 30 (round 1)


def test_classes_still_on_are_those_not_cancelled_and_not_ended(zoom02):
    booking = kit.zl42(zoom02)
    classes = list(booking.occurrences.order_by("starts_at"))
    classes[4].cancelled_at = FROZEN_NOW  # Mon 19 Oct
    now = at(12, 9)  # Mon 12 Oct, during its class
    on = booking.classes_still_on(now, occurrences=classes)
    assert on == [classes[2], classes[3], classes[5], classes[6], classes[7]]
    # in progress still counts, unlike remaining_classes; ended and cancelled ones don't
    assert classes[2] not in booking.remaining_classes(now, occurrences=classes)
    assert booking.status_after_cancel(now, occurrences=classes) == "approved"
    assert booking.classes_still_on(at(29, 9), occurrences=classes) == []
    assert booking.status_after_cancel(at(29, 9), occurrences=classes) == "cancelled"


def test_the_still_on_rule_is_written_once():
    """Criterion 21, review round 1, N4: one model method, used by cancel and reconcile."""
    from pathlib import Path

    from django.conf import settings

    rule = re.compile(r"cancelled_at is None and \w+\.ends_at > now")
    zoom_dir = Path(settings.BASE_DIR) / "apps" / "zoom"
    found = {
        str(path.relative_to(zoom_dir)): len(rule.findall(path.read_text(encoding="utf-8")))
        for path in zoom_dir.rglob("*.py")
        if "tests" not in path.parts
    }
    assert {name: n for name, n in found.items() if n} == {"models.py": 1}
    source = (zoom_dir / "services.py").read_text(encoding="utf-8")
    assert source.count("classes_still_on(") == 2  # cancel() and reconcile


def test_the_sync_fingerprint_is_the_status_and_each_class_s_times(zoom02):
    booking = kit.zl42(zoom02)
    classes = list(booking.occurrences.all())
    with CaptureQueriesContext(connection) as queries:
        first = booking.sync_fingerprint(classes)
    assert len(queries) == 0
    status, rows = first
    assert status == "approved" and len(rows) == 8
    assert [row[0] for row in rows] == sorted(o.pk for o in classes)
    assert rows[0][1:] == (classes[0].starts_at, classes[0].ends_at, None)
    assert booking.sync_fingerprint(list(reversed(classes))) == first  # order doesn't matter
    assert booking.sync_fingerprint() == first  # reads the classes when not given

    moved = list(booking.occurrences.all())
    moved[3].starts_at += timedelta(minutes=30)
    assert booking.sync_fingerprint(moved) != first
    cancelled = list(booking.occurrences.all())
    cancelled[3].cancelled_at = FROZEN_NOW
    assert booking.sync_fingerprint(cancelled) != first
    longer = list(booking.occurrences.all())
    longer[3].ends_at += timedelta(minutes=5)
    assert booking.sync_fingerprint(longer) != first
    booking.status = LinkRequest.Status.CANCELLED
    assert booking.sync_fingerprint(classes) != first
