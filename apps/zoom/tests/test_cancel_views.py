"""Brief 011, the view layer: the cancel pages, the detail and queue additions, the public start
page, the host-key reveal and the change page's reveal line (criteria 5-9, 12, 15, 22-26, 29-31,
41-44 and 47's context).

The page templates are the conftest stubs, so these tests pin status codes, redirects,
messages, headers and the context contract. The tests that search rendered pages for a start
URL or a host key use the real templates, so anything the markup prints is searched too.
"""

import logging
import sys
from datetime import date, datetime
from unittest import mock

import pytest
import responses
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.core import mail, serializers
from django.core.cache import cache
from django.core.signals import got_request_exception
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import resolve, reverse
from django.views.debug import ExceptionReporter

from apps.zoom import crypto, services
from apps.zoom.forms import CancelForm
from apps.zoom.models import (
    HostAccount,
    HostKeyReveal,
    HostSlot,
    LinkRequest,
    Occurrence,
)
from apps.zoom.providers import FakeProvider, ZoomBusy, ZoomMeetingNotFound

from . import zoommock as zm
from .conftest import COLOMBO, FROZEN_NOW, booked_on, make_account, make_request
from .test_sidebar_zoom_group import _real_templates

pytestmark = pytest.mark.django_db
HOST_KEY = "8421973"
MEETING = "81234567890"


def at(day, hour, minute=0):
    return datetime(2026, 10, day, hour, minute, tzinfo=COLOMBO)


def _messages(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


@pytest.fixture
def zoom02(db):
    return make_account("Zoom 02", sort_order=2, host_key=HOST_KEY)


@pytest.fixture
def now_is(monkeypatch):
    def move(moment):
        monkeypatch.setattr("django.utils.timezone.now", lambda: moment)

    return move


def zl42(account, **kwargs):
    return booked_on(
        make_request(
            weekdays="1,3",
            first_date=date(2026, 10, 5),
            last_date=date(2026, 10, 28),
            class_name="Grade 11 Physics",
            email="nimal@example.com",
        ),
        account,
        **kwargs,
    )


def zl43(account):
    return booked_on(
        make_request(first_date=date(2026, 10, 5), class_name="Grade 10 Chemistry"),
        account,
        meeting_id="81234560000",
    )


def cancel_url(link_request):
    return reverse("zoom:cancel", args=[link_request.pk])


def class_url(link_request, occurrence):
    return reverse("zoom:cancel_class", args=[link_request.pk, occurrence.pk])


def wed7(booking):
    return booking.occurrences.get(starts_at=at(7, 8, 30))


# --------------------------------------------------------------------------- 5 access


def test_the_cancel_views_run_outside_the_request_transaction():
    for name, args in (("zoom:cancel", [1]), ("zoom:cancel_class", [1, 2]), ("zoom:start", ["x"])):
        view = resolve(reverse(name, args=args)).func
        assert "default" in getattr(view, "_non_atomic_requests", set())


def test_cancelling_needs_the_review_permission(client, plain_user, zoom02):
    booking = zl42(zoom02)
    for url in (cancel_url(booking), class_url(booking, wed7(booking))):
        for method in (client.get, client.post):
            response = method(url, {"reason": "x"})
            assert response.status_code == 302
            assert response.url.startswith(reverse("accounts:login"))
    client.force_login(plain_user)
    for url in (cancel_url(booking), class_url(booking, wed7(booking))):
        assert client.get(url).status_code == 403
        assert client.post(url, {"reason": "x"}).status_code == 403
    assert FakeProvider.deleted == []
    assert not Occurrence.objects.filter(cancelled_at__isnull=False).exists()


def test_the_cancel_pages_are_404_where_there_is_nothing_of_that_kind(it_client, zoom02):
    waiting = make_request(first_date=date(2026, 11, 2))
    rejected = make_request(first_date=date(2026, 11, 9))
    rejected.reject(None, "No.")
    booking = zl42(zoom02)
    one_off = zl43(make_account("Zoom 03"))
    for url in (
        cancel_url(waiting),
        cancel_url(rejected),
        class_url(waiting, waiting.occurrences.get()),
        class_url(booking, one_off.occurrences.get()),  # a class of another request
        class_url(one_off, one_off.occurrences.get()),  # a one-off is cancelled as a whole
        reverse("zoom:cancel_class", args=[booking.pk, 999999]),
    ):
        assert it_client.get(url).status_code == 404
        assert it_client.post(url, {"reason": "x"}).status_code == 404


# --------------------------------------------------------------------------- 6 nothing to do


@pytest.mark.parametrize("method", ["get", "post"])
def test_nothing_to_do_goes_back_to_the_detail_with_one_message(
    it_client, it_user, zoom02, now_is, method
):
    booking = zl42(zoom02)
    services.cancel(booking.pk, occurrence_id=wed7(booking).pk, by=it_user, reason="Closed.")
    FakeProvider.deleted.clear()
    mail.outbox.clear()
    mon5 = booking.occurrences.get(starts_at=at(5, 8, 30))
    send = getattr(it_client, method)
    cases = [
        (
            cancel_url(booking),
            "Mon 5 Oct 2026, 8:30 am to 11:30 am is in progress. Cancel the rest of this "
            "booking after it ends at 11:30 am.",
        ),
        (class_url(booking, mon5), "That class has already started, so it can't be cancelled."),
        (class_url(booking, wed7(booking)), "That class was already cancelled."),
    ]
    now_is(at(5, 9))
    for url, message in cases:
        it_client.cookies.pop("messages", None)  # only this request's message
        response = send(url, {"reason": "x"})
        assert response.status_code == 302
        assert response.url == reverse("zoom:detail", args=[booking.pk])
        assert _messages(response) == [message]
    now_is(at(29, 9))
    it_client.force_login(it_user)  # a month on, the first session has expired
    it_client.cookies.pop("messages", None)
    response = send(cancel_url(booking), {"reason": "x"})
    assert _messages(response) == ["There are no classes left to cancel in this booking."]
    assert FakeProvider.deleted == [] and mail.outbox == []


# --------------------------------------------------------------------------- 7 confirm page


def test_the_cancel_form_sets_its_own_widget_label_help_and_error():
    field = CancelForm().fields["reason"]
    assert (field.label, field.help_text, field.max_length) == (
        "Why is it cancelled?",
        "This goes in the email to the requester.",
        1000,
    )
    html = str(CancelForm()["reason"])
    assert html.startswith("<textarea") and 'rows="4"' in html and 'maxlength="1000"' in html
    assert CancelForm({"reason": "  "}).errors["reason"] == [
        "Tell the requester why it's cancelled."
    ]
    assert not CancelForm({"reason": "x" * 1001}).is_valid()


def test_a_reason_over_1000_characters_names_the_limit():
    """The over-length error (unpinned copy, backend's implementation notes) names the limit,
    rather than just failing validation, so a reason that's too long tells IT how to fix it."""
    assert CancelForm({"reason": "x" * 1001}).errors["reason"] == [
        "Keep the reason to 1000 characters or fewer."
    ]


def test_the_whole_booking_confirm_page_lists_what_goes_and_what_stays(it_client, zoom02, now_is):
    booking = zl42(zoom02)
    now_is(at(6, 10))
    response = it_client.get(cancel_url(booking))
    assert response.status_code == 200
    assert [t.name for t in response.templates][0] == "zoom/cancel_confirm.html"
    context = response.context
    assert context["link_request"] == booking and context["occurrence"] is None
    assert context["checks_zoom"] is True and context["cancel_error"] is None
    assert [o.starts_at for o in context["to_cancel"]] == [
        o.starts_at for o in booking.occurrences.all()[1:]
    ]
    assert [o.starts_at for o in context["kept"]] == [at(5, 8, 30)]
    assert isinstance(context["form"], CancelForm) and not context["form"].is_bound


def test_the_one_class_confirm_page(it_client, zoom02, settings):
    booking = zl42(zoom02)
    settings.ZOOM_PROVIDER = "manual"
    context = it_client.get(class_url(booking, wed7(booking))).context
    assert context["occurrence"] == wed7(booking)
    assert context["to_cancel"] == [wed7(booking)] and context["kept"] == []
    assert context["checks_zoom"] is False


def test_an_empty_reason_rerenders_with_the_error(it_client, zoom02):
    booking = zl42(zoom02)
    response = it_client.post(cancel_url(booking), {"reason": "   "})
    assert response.status_code == 200
    assert response.context["form"].errors["reason"] == ["Tell the requester why it's cancelled."]
    assert FakeProvider.deleted == []
    _still_booked(booking)


def _still_booked(booking):
    booking.refresh_from_db()
    assert booking.status == LinkRequest.Status.APPROVED
    assert not booking.occurrences.filter(cancelled_at__isnull=False).exists()


# --------------------------------------------------------------------------- 12 via the page


def test_a_zoom_refusal_rerenders_the_page_keeping_the_reason(it_client, zoom02):
    booking = zl42(zoom02)
    FakeProvider.delete_error = ZoomBusy()
    response = it_client.post(class_url(booking, wed7(booking)), {"reason": "Sports meet."})
    assert response.status_code == 200
    assert response.context["cancel_error"] == (
        "We couldn't cancel it in Zoom: Zoom is busy right now. Nothing was cancelled. "
        "Try again in a few minutes."
    )
    assert response.context["form"]["reason"].value() == "Sports meet."
    assert response.context["occurrence"] == wed7(booking)
    assert mail.outbox == []
    _still_booked(booking)


# --------------------------------------------------------------------------- 15 success


def test_cancelling_a_whole_booking_redirects_with_the_message_and_emails(it_client, zoom02):
    booking = zl42(zoom02)
    response = it_client.post(cancel_url(booking), {"reason": "The school is closed."})
    assert response.status_code == 302
    assert response.url == reverse("zoom:detail", args=[booking.pk])
    assert _messages(response) == ["Cancelled the booking. We emailed nimal@example.com."]
    assert FakeProvider.deleted == [(zoom02.pk, MEETING, None)]
    [message] = mail.outbox
    assert message.to == ["nimal@example.com"]
    booking.refresh_from_db()
    assert booking.status == "cancelled"
    assert HostSlot.objects.count() == 0


def test_cancelling_one_class_names_its_date(it_client, zoom02):
    booking = zl42(zoom02)
    target = wed7(booking)
    response = it_client.post(class_url(booking, target), {"reason": "Sports meet."})
    assert _messages(response) == [
        "Cancelled the class on Wed 7 Oct 2026. We emailed nimal@example.com."
    ]
    assert FakeProvider.deleted == [(zoom02.pk, MEETING, target.zoom_occurrence_id)]
    target.refresh_from_db()
    assert target.cancel_reason == "Sports meet."


def test_an_email_failure_keeps_the_cancel_and_warns(it_client, zoom02):
    booking = zl43(zoom02)
    with mock.patch(
        "django.core.mail.backends.locmem.EmailBackend.send_messages", side_effect=OSError
    ):
        response = it_client.post(cancel_url(booking), {"reason": "Closed."})
    assert response.status_code == 302
    [message] = list(get_messages(response.wsgi_request))
    assert message.level_tag == "warning"
    assert str(message) == (
        "Cancelled, but the email to nimali@example.com didn't send. Tell them yourself."
    )
    booking.refresh_from_db()
    assert booking.status == "cancelled"


def test_the_manual_provider_adds_delete_it_in_zoom_too(it_client, zoom02, settings):
    settings.ZOOM_PROVIDER = "manual"
    booking = zl43(zoom02)
    response = it_client.post(cancel_url(booking), {"reason": "Closed."})
    assert _messages(response) == [
        "Cancelled the booking. We emailed nimali@example.com. This system can't reach Zoom: "
        "delete it in Zoom too."
    ]


# --------------------------------------------------------------------------- 8 and 31 detail


def test_the_detail_of_an_approved_weekly_booking(it_client, zoom02):
    booking = zl42(zoom02)
    context = it_client.get(reverse("zoom:detail", args=[booking.pk])).context
    assert context["can_cancel_booking"] is True
    assert context["cancellable_ids"] == set(booking.occurrences.values_list("pk", flat=True))
    assert context["in_progress_id"] is None
    assert context["cancel_blocked_message"] is None
    token = services.start_token(booking)
    assert context["start_link"] == f"http://testserver/zoom/start/{token}/"


def test_the_detail_while_a_class_is_in_progress(it_client, zoom02, now_is):
    booking = zl42(zoom02)
    now_is(at(5, 9))
    context = it_client.get(reverse("zoom:detail", args=[booking.pk])).context
    mon5 = booking.occurrences.get(starts_at=at(5, 8, 30))
    assert context["can_cancel_booking"] is False
    assert context["in_progress_id"] == mon5.pk
    assert mon5.pk not in context["cancellable_ids"] and len(context["cancellable_ids"]) == 7
    assert context["cancel_blocked_message"] == (
        "Mon 5 Oct 2026, 8:30 am to 11:30 am is in progress. Cancel the rest of this booking "
        "after it ends at 11:30 am."
    )


def test_the_detail_of_a_one_off_has_no_class_links(it_client, zoom02):
    context = it_client.get(reverse("zoom:detail", args=[zl43(zoom02).pk])).context
    assert context["cancellable_ids"] == set() and context["can_cancel_booking"] is True


def test_the_detail_of_a_cancelled_booking(it_client, it_user, zoom02):
    booking = zl42(zoom02)
    services.cancel(booking.pk, by=it_user, reason="Closed.")
    context = it_client.get(reverse("zoom:detail", args=[booking.pk])).context
    assert context["link_request"].status == "cancelled"
    assert context["link_request"].cancelled_by == it_user
    assert context["can_cancel_booking"] is False
    assert context["cancellable_ids"] == set()
    assert context["cancel_blocked_message"] is None
    assert context["start_link"] is None
    assert context["timetable_url"] is None
    assert all(o.cancel_reason == "Closed." for o in context["occurrences"])


def _detail_queries(client, booking):
    with CaptureQueriesContext(connection) as queries:
        response = client.get(reverse("zoom:detail", args=[booking.pk]))
    assert response.status_code == 200
    return len(queries), response.content.decode()


def test_the_detail_runs_the_same_queries_however_many_classes_were_cancelled(
    it_client, it_user, zoom02, settings, django_user_model
):
    """Review round 1, SF1: each "Cancelled by …" line reads a user that the page has already
    joined in, so a booking with more cancelled classes costs no more queries. The real
    templates are used because they are what reads ``cancelled_by``."""
    _real_templates(settings)
    booking = zl42(zoom02)
    classes = list(booking.occurrences.all())
    services.cancel(booking.pk, occurrence_id=classes[1].pk, by=it_user, reason="Sports meet.")
    it_client.get(reverse("zoom:detail", args=[booking.pk]))  # settle the session first
    one_cancelled, html = _detail_queries(it_client, booking)
    assert html.count("Cancelled by") == 1

    # Three more classes, each cancelled by someone different, so no user is cached twice.
    for number, occurrence in enumerate(classes[2:5]):
        someone = django_user_model.objects.create_user(f"it.other{number}", password="x")
        services.cancel(booking.pk, occurrence_id=occurrence.pk, by=someone, reason="Holiday.")
    four_cancelled, html = _detail_queries(it_client, booking)
    assert html.count("Cancelled by") == 4
    assert four_cancelled == one_cancelled

    # The whole booking cancelled: the notice's "cancelled by" costs no query either.
    services.cancel(booking.pk, by=it_user, reason="The school is closed.")
    all_cancelled, html = _detail_queries(it_client, booking)
    assert "This booking was cancelled by" in html
    assert all_cancelled <= one_cancelled


def test_the_detail_with_the_manual_provider_has_no_start_link(it_client, zoom02, settings):
    settings.ZOOM_PROVIDER = "manual"
    context = it_client.get(reverse("zoom:detail", args=[zl42(zoom02).pk])).context
    assert context["start_link"] is None


def test_a_waiting_request_has_no_cancel_or_start_values(it_client, account):
    context = it_client.get(reverse("zoom:detail", args=[make_request().pk])).context
    assert context["can_cancel_booking"] is False and context["start_link"] is None
    assert context["cancel_blocked_message"] is None and context["cancellable_ids"] == set()


# --------------------------------------------------------------------------- 9 queue


def test_the_cancelled_tab(it_client, it_user, zoom02):
    booking = zl43(zoom02)
    services.cancel(booking.pk, by=it_user, reason="Closed.")
    response = it_client.get(reverse("zoom:queue"), {"status": "cancelled"})
    assert response.context["status"] == "cancelled"
    assert list(response.context["link_requests"]) == [booking]
    tab = next(t for t in response.context["tabs"] if t["value"] == "cancelled")
    assert tab == {"value": "cancelled", "label": "Cancelled", "count": 1, "current": True}


# --------------------------------------------------------------------------- 22-26 start page


START_KEYS = {
    "state",
    "link_request",
    "occurrence",
    "opens_at",
    "opens_after_other_class",
    "start_error",
    "start_error_still",
    "token",
    "it_desk_phone",
}


def start_url(booking):
    return reverse("zoom:start", args=[services.start_token(booking)])


def _keys(response):
    context = response.context
    return set(context.flatten() if hasattr(context, "flatten") else context.keys())


def _assert_private(response):
    assert "no-store" in response["Cache-Control"]
    assert response["Referrer-Policy"] == "no-referrer"


@pytest.mark.parametrize(
    ("moment", "state", "class_start"),
    [
        (FROZEN_NOW, "too_early", at(5, 8, 30)),
        (at(5, 8, 0), "ready", at(5, 8, 30)),
        (at(29, 9), "ended", at(28, 8, 30)),
    ],
)
def test_the_start_page_shows_each_state_without_asking_zoom(
    client, zoom02, now_is, settings, moment, state, class_start
):
    settings.IT_DESK_PHONE = "011 234 5678"
    booking = zl42(zoom02)
    now_is(moment)
    response = client.get(start_url(booking))
    assert response.status_code == 200
    _assert_private(response)
    context = response.context
    assert START_KEYS <= _keys(response)
    assert context["state"] == state and context["link_request"] == booking
    assert context["occurrence"].starts_at == class_start
    assert context["token"] == services.start_token(booking)
    assert context["it_desk_phone"] == {"display": "+94 11 234 5678", "tel": "+94112345678"}
    assert (context["start_error"], context["start_error_still"]) == (None, False)
    if state == "too_early":
        assert context["opens_at"] == at(5, 8, 0)
        assert context["opens_after_other_class"] is False
    else:
        assert context["opens_at"] is None
    assert FakeProvider.start_calls == []


def test_the_start_page_of_a_cancelled_booking(client, it_user, zoom02):
    booking = zl42(zoom02)
    services.cancel(booking.pk, by=it_user, reason="Closed.")
    for response in (client.get(start_url(booking)), client.post(start_url(booking))):
        assert response.status_code == 200
        _assert_private(response)
        assert (response.context["state"], response.context["occurrence"]) == ("cancelled", None)
        assert response.context["link_request"] == booking
        assert response.context["it_desk_phone"] is None
    assert FakeProvider.start_calls == []


@pytest.mark.parametrize("method", ["get", "post", "head"])
def test_an_invalid_start_link_is_a_404_page(client, zoom02, method):
    response = getattr(client, method)(reverse("zoom:start", args=["not-a-token"]))
    assert response.status_code == 404
    _assert_private(response)
    if method != "head":
        context = response.context
        assert START_KEYS <= _keys(response)
        assert context["state"] == "invalid"
        assert context["link_request"] is None and context["token"] is None


def test_pressing_start_in_the_window_redirects_to_zoom(client, zoom02, now_is, caplog):
    booking = zl42(zoom02)
    now_is(at(5, 8, 10))
    with caplog.at_level(logging.INFO, logger="apps.zoom"):
        response = client.post(start_url(booking), REMOTE_ADDR="198.51.100.4")
    assert response.status_code == 302
    assert response["Location"] == f"https://zoom.example.invalid/s/{MEETING}"
    _assert_private(response)
    assert FakeProvider.start_calls == [(zoom02.pk, MEETING)]
    [record] = caplog.records
    assert record.getMessage() == (
        f"Start link used for {booking.reference}, class Mon 5 Oct 2026 8:30 am, from 198.51.100.4"
    )


def test_pressing_start_too_early_calls_nothing(client, zoom02):
    booking = zl42(zoom02)
    response = client.post(start_url(booking))
    assert response.status_code == 200
    assert response.context["state"] == "too_early"
    assert FakeProvider.start_calls == []


@pytest.mark.parametrize(
    ("error", "message", "still"),
    [
        (ZoomBusy(), "We couldn't reach Zoom just now. Try again in a minute.", True),
        (ZoomMeetingNotFound(), "This class's meeting isn't in Zoom any more.", False),
    ],
)
def test_a_failed_start_rerenders_with_the_message(
    client, zoom02, now_is, settings, error, message, still
):
    booking = zl42(zoom02)
    now_is(at(5, 8, 10))
    FakeProvider.start_error = error
    response = client.post(start_url(booking))
    assert response.status_code == 200
    _assert_private(response)
    context = response.context
    assert (context["state"], context["start_error"], context["start_error_still"]) == (
        "ready",
        message,
        still,
    )
    assert context["it_desk_phone"] is None


def test_pressing_start_needs_a_csrf_token(zoom02, now_is):
    booking = zl42(zoom02)
    now_is(at(5, 8, 10))
    response = Client(enforce_csrf_checks=True).post(start_url(booking))
    assert response.status_code == 403
    assert FakeProvider.start_calls == []


def test_the_manual_provider_is_not_set_up(client, zoom02, now_is, settings):
    settings.ZOOM_PROVIDER = "manual"
    booking = zl42(zoom02)
    now_is(at(5, 8, 10))
    for response in (client.get(start_url(booking)), client.post(start_url(booking))):
        assert response.status_code == 200
        _assert_private(response)
        context = response.context
        assert context["state"] == "not_set_up"
        assert context["link_request"] == booking
        assert context["occurrence"].starts_at == at(5, 8, 30)
        assert context["token"] == services.start_token(booking)


def test_the_start_url_is_never_kept_anywhere(client, zoom02, now_is, settings, http_mock, caplog):
    """Criterion 24, with the live provider and a mocked Zoom, on the real templates."""
    _real_templates(settings)
    settings.ZOOM_PROVIDER = "zoom"
    zm.connect(settings, zoom02)
    zm.add_token(http_mock)
    secret = "https://us02web.zoom.us/s/81234567890?zak=SECRETZAK"
    http_mock.add(
        responses.GET,
        zm.meeting_url(MEETING),
        json={"id": int(MEETING), "start_url": secret, "join_url": zm.JOIN_URL},
    )
    booking = zl42(zoom02)
    now_is(at(5, 8, 10))
    loggers = ("apps.zoom", "django", "urllib3", "requests")
    with (
        caplog.at_level(logging.DEBUG, logger=loggers[0]),
        caplog.at_level(logging.DEBUG, logger=loggers[1]),
        caplog.at_level(logging.DEBUG, logger=loggers[2]),
        caplog.at_level(logging.DEBUG, logger=loggers[3]),
    ):
        page = client.get(start_url(booking))
        response = client.post(start_url(booking))
    assert response.status_code == 302 and response["Location"] == secret
    assert "SECRETZAK" not in page.content.decode()
    assert "SECRETZAK" not in response.content.decode()
    assert not any("SECRETZAK" in value for key, value in response.items() if key != "Location")
    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert "SECRETZAK" not in logged and logged  # something was logged, and not that
    models = [HostAccount, LinkRequest, Occurrence, HostSlot, HostKeyReveal]
    dump = "".join(serializers.serialize("json", m.objects.all()) for m in models)
    assert "SECRETZAK" not in dump
    assert not any(b"SECRETZAK" in value for value in cache._cache.values())
    assert not any("SECRETZAK" in str(m) for m in get_messages(response.wsgi_request))
    assert not any("SECRETZAK" in m.body for m in mail.outbox)


def test_the_start_page_renders_on_the_real_templates(client, zoom02, now_is, settings):
    """A smoke test: every state renders (no template error) with the real markup."""
    _real_templates(settings)
    booking = zl42(zoom02)
    for moment in (FROZEN_NOW, at(5, 8, 10), at(29, 9)):
        now_is(moment)
        assert client.get(start_url(booking)).status_code == 200
    assert client.get(reverse("zoom:start", args=["bad"])).status_code == 404


# --------------------------------------------------------------------------- 41-44 reveal


def reveal_url(account):
    return reverse("zoom:account_host_key", args=[account.pk])


@pytest.fixture
def viewer(db, django_user_model):
    user = django_user_model.objects.create_user(username="viewer", password="pw")
    user.user_permissions.add(Permission.objects.get(codename="view_hostaccount"))
    return user


def test_the_reveal_is_for_the_it_desk_only(plain_user, viewer, it_client, zoom02):
    client = Client()  # the ``client`` fixture is it_client itself, signed in
    response = client.post(reveal_url(zoom02))
    assert response.status_code == 302 and response.url.startswith(reverse("accounts:login"))
    for user in (plain_user, viewer):
        client.force_login(user)
        assert client.post(reveal_url(zoom02)).status_code == 403
    assert it_client.get(reveal_url(zoom02)).status_code == 405
    assert it_client.post(reverse("zoom:account_host_key", args=[999999])).status_code == 404
    assert HostKeyReveal.objects.count() == 0


def test_the_reveal_needs_a_csrf_token(it_user, zoom02):
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(it_user)
    assert csrf_client.post(reveal_url(zoom02)).status_code == 403
    assert HostKeyReveal.objects.count() == 0


def test_revealing_a_key_shows_it_and_records_who(it_client, it_user, zoom02, caplog):
    with caplog.at_level(logging.INFO, logger="apps.zoom"):
        response = it_client.post(reveal_url(zoom02))
    assert response.status_code == 200
    assert [t.name for t in response.templates][0] == "zoom/host_key_reveal.html"
    assert response.context["account"] == zoom02
    assert response.context["host_key"] == HOST_KEY
    _assert_private(response)
    [reveal] = HostKeyReveal.objects.all()
    assert (reveal.host_account, reveal.shown_by) == (zoom02, it_user)
    assert [r.getMessage() for r in caplog.records] == ["Host key for Zoom 02 shown to kasun.it"]
    # Each POST is a new, recorded reveal (a reload resends it).
    it_client.post(reveal_url(zoom02))
    assert HostKeyReveal.objects.count() == 2


def test_revealing_when_no_key_is_saved(it_client, zoom02):
    empty = make_account("Zoom 05")
    response = it_client.post(reveal_url(empty))
    assert response.status_code == 302
    assert response.url == reverse("zoom:account_edit", args=[empty.pk])
    _assert_private(response)
    assert _messages(response) == ["Zoom 05 has no host key saved."]
    assert HostKeyReveal.objects.count() == 0


def test_revealing_an_unreadable_key(it_client, zoom02, settings, caplog):
    from cryptography.fernet import Fernet

    settings.HOST_KEY_ENCRYPTION_KEYS = [Fernet.generate_key().decode()]
    with caplog.at_level(logging.DEBUG, logger="apps.zoom"):
        response = it_client.post(reveal_url(zoom02))
    assert response.status_code == 302
    assert response.url == reverse("zoom:account_edit", args=[zoom02.pk])
    _assert_private(response)
    assert _messages(response) == [
        "A host key is saved, but it can't be read with the current encryption keys. Type it again."
    ]
    assert HostKeyReveal.objects.count() == 0
    [record] = caplog.records
    assert record.levelno == logging.WARNING
    assert "Zoom 02" in record.getMessage() and "InvalidToken" in record.getMessage()


def test_the_key_is_on_the_reveal_page_and_nowhere_else(client, it_user, zoom02, settings, caplog):
    """Criterion 43, on the real templates, with DEBUG logging for apps.zoom and django."""
    _real_templates(settings)
    client.force_login(it_user)
    booking = zl42(zoom02)
    edit = reverse("zoom:account_edit", args=[zoom02.pk])
    with (
        caplog.at_level(logging.DEBUG, logger="apps.zoom"),
        caplog.at_level(logging.DEBUG, logger="django"),
    ):
        before = client.get(edit)
        reveal = client.post(reveal_url(zoom02))
        pages = [
            before,
            client.get(edit),
            client.get(reverse("zoom:accounts")),
            client.get(reverse("zoom:detail", args=[booking.pk])),
        ]
    assert reveal.status_code == 200
    assert reveal.content.decode().count(HOST_KEY) == 1
    for page in pages:
        assert page.status_code == 200
        assert HOST_KEY not in page.content.decode()
    assert not any(HOST_KEY in record.getMessage() for record in caplog.records)
    assert not any(HOST_KEY in str(m) for m in get_messages(reveal.wsgi_request))
    assert not any(HOST_KEY.encode() in value for value in cache._cache.values())
    assert mail.outbox == []
    dump = serializers.serialize("json", HostKeyReveal.objects.all())
    assert HOST_KEY not in dump


def test_an_error_after_decryption_in_the_view_masks_the_key(it_client, zoom02, monkeypatch):
    """Criterion 43: the view frame that holds the key is ``@sensitive_variables``."""
    reports = []

    def capture(sender, request, **kwargs):
        reports.append(ExceptionReporter(request, *sys.exc_info()))

    got_request_exception.connect(capture)

    def failing_render(request, template_name, context):
        raise RuntimeError("boom")

    monkeypatch.setattr("apps.zoom.views.render", failing_render)
    it_client.raise_request_exception = False
    try:
        response = it_client.post(reveal_url(zoom02))
    finally:
        got_request_exception.disconnect(capture)
    assert response.status_code == 500
    [reporter] = reports
    frame = next(f for f in reporter.get_traceback_data()["frames"] if f["function"] == "post")
    assert "*****" in dict(frame["vars"])["plain"]
    assert HOST_KEY not in reporter.get_traceback_html()
    assert HOST_KEY not in reporter.get_traceback_text()


def test_the_change_page_offers_the_reveal_and_says_who_looked(
    it_client, it_user, zoom02, monkeypatch
):
    edit = reverse("zoom:account_edit", args=[zoom02.pk])
    context = it_client.get(edit).context
    assert context["can_reveal_host_key"] is True
    assert (context["last_key_reveal"], context["key_reveal_count"]) == (None, 0)

    it_client.post(reveal_url(zoom02))
    it_client.post(reveal_url(zoom02))
    decrypts = []
    real = crypto.decrypt
    monkeypatch.setattr(crypto, "decrypt", lambda token: decrypts.append(1) or real(token))
    context = it_client.get(edit).context
    assert len(decrypts) == 1  # only 008's host_key_state
    assert context["last_key_reveal"].shown_by == it_user
    assert context["last_key_reveal"].shown_at == FROZEN_NOW
    assert context["key_reveal_count"] == 2
    assert HOST_KEY not in it_client.get(edit).content.decode()


def test_the_reveal_is_not_offered_without_a_readable_key_or_on_add(it_client, zoom02, settings):
    empty = make_account("Zoom 05")
    context = it_client.get(reverse("zoom:account_edit", args=[empty.pk])).context
    assert context["can_reveal_host_key"] is False
    context = it_client.get(reverse("zoom:account_add")).context
    assert context["can_reveal_host_key"] is False
    assert (context["last_key_reveal"], context["key_reveal_count"]) == (None, 0)
    from cryptography.fernet import Fernet

    settings.HOST_KEY_ENCRYPTION_KEYS = [Fernet.generate_key().decode()]
    context = it_client.get(reverse("zoom:account_edit", args=[zoom02.pk])).context
    assert context["can_reveal_host_key"] is False


def test_the_reveal_count_shows_even_after_the_key_is_removed(it_client, zoom02):
    it_client.post(reveal_url(zoom02))
    zoom02.set_host_key("")
    zoom02.save()
    context = it_client.get(reverse("zoom:account_edit", args=[zoom02.pk])).context
    assert context["can_reveal_host_key"] is False and context["key_reveal_count"] == 1


# --------------------------------------------------------------------------- 30 copy scan


def test_no_old_host_key_email_copy_is_left():
    """Criterion 30's scan, over the zoom app's Python (templates are the frontend's)."""
    from pathlib import Path

    root = Path(services.__file__).parent
    for path in root.rglob("*.py"):
        if "tests" in path.parts or "migrations" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        assert "goes out with the next approved link" not in text, path
        assert "tell the requester to ask the IT desk for the host key" not in text, path
