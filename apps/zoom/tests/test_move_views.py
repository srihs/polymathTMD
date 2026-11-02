"""Brief 012, the view layer: the two move pages, their access and 404s, the redirects when there's
nothing to move, the forms (G2's date limits, the request form's time widgets), the context
contract (G1, G4, G5), the flashes and the detail page's new values (criteria 4-6, 9, 16, 22's
context and 27).

The page templates are the conftest stubs, so most tests pin status codes, redirects, messages
and context. Criterion 27's test renders the real ``detail.html`` and ``move_form.html``.
"""

import html as html_module
import re
from datetime import date, datetime, time

import pytest
from django.contrib.messages import get_messages
from django.core import mail
from django.urls import resolve, reverse

from apps.zoom import services
from apps.zoom.forms import LinkRequestForm, MoveClassForm, MoveSeriesForm
from apps.zoom.models import HostSlot, LinkRequest
from apps.zoom.providers import BusyTime, FakeProvider, ZoomBusy

from .conftest import COLOMBO, FROZEN_NOW, booked_on, make_account, make_request
from .test_sidebar_zoom_group import _real_templates

pytestmark = pytest.mark.django_db


def at(day, hour, minute=0):
    return datetime(2026, 10, day, hour, minute, tzinfo=COLOMBO)


def _messages(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


@pytest.fixture
def zoom02(db):
    return make_account("Zoom 02", sort_order=2, host_key="8421973")


@pytest.fixture
def now_is(monkeypatch, it_client, it_user):
    """Move the clock, then sign in again: weeks ahead, the test session would have expired."""

    def move(moment):
        monkeypatch.setattr("django.utils.timezone.now", lambda: moment)
        it_client.force_login(it_user)

    return move


def _last_message(response):
    """The flash this response added. The stub pages never show (and so never use up) the
    flashes, so earlier ones in the same test are still queued."""
    return _messages(response)[-1]


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


def wed7(booking):
    return booking.occurrences.get(starts_at=at(7, 8, 30))


def class_url(booking, occurrence):
    return reverse("zoom:move_class", args=[booking.pk, occurrence.pk])


def series_url(booking):
    return reverse("zoom:move_series", args=[booking.pk])


GOOD_CLASS = {"date": "2026-10-08", "start_time": "09:00", "end_time": "12:00"}
GOOD_SERIES = {"start_time": "09:00", "end_time": "12:00"}


def class_post(occurrence, typed=GOOD_CLASS):
    """What the one-class page posts: the typed values plus its signed ``shown`` (criterion 30)."""
    return {**typed, "shown": LinkRequest.move_fingerprint([occurrence])}


def series_post(booking, typed=GOOD_SERIES):
    """What the series page posts: ``shown`` lists the remaining classes it showed."""
    return {**typed, "shown": LinkRequest.move_fingerprint(booking.remaining_classes())}


# --------------------------------------------------------------------------- 4 URLs and access


def test_the_urls_and_their_views_run_outside_the_request_transaction():
    assert reverse("zoom:move_class", args=[1, 2]) == "/zoom/requests/1/classes/2/move/"
    assert reverse("zoom:move_series", args=[1]) == "/zoom/requests/1/move/"
    for name, args in (("zoom:move_class", [1, 2]), ("zoom:move_series", [1])):
        view = resolve(reverse(name, args=args)).func
        assert "default" in getattr(view, "_non_atomic_requests", set())


def test_moving_needs_the_review_permission(client, plain_user, zoom02):
    booking = zl42(zoom02)
    urls = (class_url(booking, wed7(booking)), series_url(booking))
    for url in urls:
        for method in (client.get, client.post):
            response = method(url, GOOD_SERIES)
            assert response.status_code == 302
            assert response.url.startswith(reverse("accounts:login"))
    client.force_login(plain_user)
    for url in urls:
        assert client.get(url).status_code == 403
        assert client.post(url, GOOD_SERIES).status_code == 403
    assert FakeProvider.patched == []


def test_the_pages_are_404_for_what_cant_be_moved(it_client, zoom02, it_user):
    booking = zl42(zoom02)
    waiting = make_request(weekdays="1", first_date=date(2026, 11, 2), last_date=date(2026, 11, 9))
    other = zl43(make_account("Zoom 04"))
    cancelled = zl42(make_account("Zoom 03"))
    services.cancel(cancelled.pk, by=it_user, reason="Closed.")
    for url in (
        class_url(waiting, waiting.occurrences.first()),
        series_url(waiting),
        class_url(booking, other.occurrences.get()),  # not this request's class
        series_url(other),  # a one-off has no series
        class_url(cancelled, cancelled.occurrences.first()),
        series_url(cancelled),
    ):
        assert it_client.get(url).status_code == 404, url
        assert it_client.post(url, GOOD_CLASS).status_code == 404, url


def test_a_class_that_has_started_goes_back_with_the_reason(it_client, zoom02, now_is):
    booking = zl42(zoom02)
    now_is(at(7, 9))
    for method in (it_client.get, it_client.post):
        response = method(class_url(booking, wed7(booking)), GOOD_CLASS)
        assert response.status_code == 302
        assert response.url == reverse("zoom:detail", args=[booking.pk])
        assert _last_message(response) == "That class has already started, so it can't be moved."
    assert FakeProvider.busy_calls == [] and FakeProvider.patched == []


def test_a_cancelled_class_goes_back_with_that_class_was_cancelled(it_client, zoom02, it_user):
    booking = zl42(zoom02)
    target = wed7(booking)
    services.cancel(booking.pk, occurrence_id=target.pk, by=it_user, reason="Closed.")
    response = it_client.post(class_url(booking, target), GOOD_CLASS)
    assert response.status_code == 302
    assert _messages(response) == ["That class was cancelled."]


def test_a_series_in_progress_or_with_nothing_left_goes_back(it_client, zoom02, now_is):
    booking = zl42(zoom02)
    now_is(at(5, 9))
    response = it_client.get(series_url(booking))
    assert response.status_code == 302
    assert _messages(response) == [
        "Mon 5 Oct 2026, 8:30 am to 11:30 am is in progress. Change the time of the remaining "
        "classes after it ends at 11:30 am."
    ]
    now_is(at(28, 12))
    response = it_client.post(series_url(booking), GOOD_SERIES)
    assert response.status_code == 302
    assert _last_message(response) == "There are no classes left to change in this booking."
    assert FakeProvider.busy_calls == [] and FakeProvider.patched == []


# --------------------------------------------------------------------------- 5 the forms, G1, G4


def test_the_one_class_page_context(it_client, zoom02):
    booking = zl42(zoom02)
    target = wed7(booking)
    response = it_client.get(class_url(booking, target))
    assert response.status_code == 200
    context = response.context
    assert context["link_request"] == booking and context["occurrence"] == target
    assert context["remaining"] == [] and context["move_error"] is None
    assert context["checks_zoom"] is True
    assert context["timetable_url"] == f"/zoom/timetable/?month=2026-10&account={zoom02.pk}"
    form = context["form"]
    assert isinstance(form, MoveClassForm)
    initial = dict(form.initial)
    shown = initial.pop("shown")
    assert initial == {"date": date(2026, 10, 7), "start_time": time(8, 30),
                       "end_time": time(11, 30)}  # fmt: skip
    # Criterion 30: the page signs the class as it shows it.
    assert services.read_move_shown(shown) == {
        target.pk: (int(at(7, 8, 30).timestamp()), int(at(7, 11, 30).timestamp()))
    }


def test_the_series_page_context(it_client, zoom02, now_is):
    booking = zl42(zoom02)
    now_is(at(6, 12))  # Mon 5 is over: the first remaining class is Wed 7
    context = it_client.get(series_url(booking)).context
    assert context["occurrence"] is None
    assert [o.starts_at for o in context["remaining"]] == [
        at(day, 8, 30) for day in (7, 12, 14, 19, 21, 26, 28)
    ]
    assert isinstance(context["form"], MoveSeriesForm)
    initial = dict(context["form"].initial)
    shown = services.read_move_shown(initial.pop("shown"))
    assert initial == {"start_time": time(8, 30), "end_time": time(11, 30)}
    assert sorted(shown) == sorted(o.pk for o in context["remaining"])
    assert context["timetable_url"] == f"/zoom/timetable/?month=2026-10&account={zoom02.pk}"


def test_the_timetable_link_is_the_month_of_the_class(it_client, zoom02):
    booking = booked_on(
        make_request(first_date=date(2026, 11, 2), class_name="November"), zoom02, meeting_id="3"
    )
    context = it_client.get(class_url(booking, booking.occurrences.get())).context
    assert context["timetable_url"] == f"/zoom/timetable/?month=2026-11&account={zoom02.pk}"


def test_the_date_widget_carries_its_limits_and_the_times_their_step(zoom02):
    """G2: ``min`` today, ``max`` the last date 005 allows; the request form's time widgets."""
    form = MoveClassForm(occurrence=wed7(zl42(zoom02)))
    html = str(form["date"])
    assert 'type="date"' in html and 'min="2026-09-28"' in html and 'max="2027-09-28"' in html
    assert 'value="2026-10-07"' in html
    for name in ("start_time", "end_time"):
        rendered = str(form[name])
        assert 'type="time"' in rendered and 'step="300"' in rendered
        field, source = form.fields[name], LinkRequestForm.base_fields[name]
        assert (field.label, field.help_text) == (source.label, source.help_text)
        assert field.error_messages["required"] == source.error_messages["required"]
    assert form.fields["date"].label == "Date of the class"
    assert form.fields["date"].help_text == (
        "Any date within the next year. It doesn't have to be one of the booking's usual days."
    )
    # The request form's own widget is untouched.
    assert "min" not in LinkRequestForm.base_fields["start_time"].widget.attrs


def test_the_forms_ask_the_models_rules(zoom02):
    booking = zl42(zoom02)
    form = MoveClassForm(
        class_post(
            wed7(booking), {"date": "2026-10-07", "start_time": "08:30", "end_time": "11:30"}
        ),
        occurrence=wed7(booking),
    )
    assert not form.is_valid()
    assert form.non_field_errors() == [
        "That's the time it's already booked for. Choose a different time."
    ]
    form = MoveClassForm(
        class_post(
            wed7(booking), {"date": "2026-09-01", "start_time": "08:32", "end_time": "08:00"}
        ),
        occurrence=wed7(booking),
    )
    assert not form.is_valid()
    assert form.errors == {
        "date": ["Choose a date and time that haven't passed yet."],
        "start_time": ["Use a time on a 5-minute step, like 8:30 or 8:35."],
        "end_time": ["The class must end after it starts. Check the end time."],
    }
    form = MoveClassForm(class_post(wed7(booking), {}), occurrence=wed7(booking))
    assert not form.is_valid()
    assert form.errors == {
        "date": ["Choose the date of the class."],
        "start_time": ["Type the time the class starts, like 8:30 am."],
        "end_time": ["Type the time the class ends, like 11:30 am."],
    }
    series = MoveSeriesForm(
        series_post(booking, {"start_time": "12:00", "end_time": "09:00"}), link_request=booking
    )
    assert not series.is_valid()
    assert series.errors == {
        "end_time": ["The class must end after it starts. Check the end time."]
    }


def test_an_invalid_post_keeps_what_was_typed(it_client, zoom02):
    booking = zl42(zoom02)
    typed = {"date": "2026-10-08", "start_time": "09:02", "end_time": "12:00"}
    response = it_client.post(class_url(booking, wed7(booking)), class_post(wed7(booking), typed))
    assert response.status_code == 200
    form = response.context["form"]
    assert form.errors == {"start_time": ["Use a time on a 5-minute step, like 8:30 or 8:35."]}
    assert form["start_time"].value() == "09:02" and form["date"].value() == "2026-10-08"
    assert FakeProvider.patched == []


# --------------------------------------------------------------------------- 9 and 16 outcomes


def test_moving_one_class_redirects_with_the_flash_and_emails(it_client, zoom02, it_user):
    booking = zl42(zoom02)
    target = wed7(booking)
    response = it_client.post(class_url(booking, target), class_post(target))
    assert response.status_code == 302
    assert response.url == reverse("zoom:detail", args=[booking.pk])
    assert _messages(response) == [
        "Moved the class to Thu 8 Oct 2026, 9:00 am to 12:00 pm. We emailed nimal@example.com."
    ]
    [message] = mail.outbox
    assert message.subject == f"Class times changed: {booking.reference} Grade 11 Physics"
    target.refresh_from_db()
    assert (target.starts_at, target.moved_by) == (at(8, 9), it_user)


def test_changing_the_series_redirects_with_the_flash(it_client, zoom02):
    booking = zl42(zoom02)
    response = it_client.post(series_url(booking), series_post(booking))
    assert response.status_code == 302
    assert _messages(response) == [
        "Changed the time of 8 classes to 9:00 am to 12:00 pm. We emailed nimal@example.com."
    ]
    booking.refresh_from_db()
    assert booking.start_time == time(9)


def test_one_remaining_class_reads_as_one(it_client, zoom02, now_is):
    booking = zl42(zoom02)
    now_is(at(27, 12))
    response = it_client.post(series_url(booking), series_post(booking))
    assert _messages(response) == [
        "Changed the time of 1 class to 9:00 am to 12:00 pm. We emailed nimal@example.com."
    ]


def test_a_failed_email_is_a_warning(it_client, zoom02, settings):
    settings.EMAIL_BACKEND = "apps.zoom.tests.test_move_views.BrokenBackend"
    booking = zl42(zoom02)
    response = it_client.post(class_url(booking, wed7(booking)), class_post(wed7(booking)))
    assert _messages(response) == [
        "Moved, but the email to nimal@example.com didn't send. Tell them the new times yourself."
    ]


class BrokenBackend:
    """An email backend that always fails, for the warning flash."""

    def __init__(self, *args, **kwargs):
        pass

    def send_messages(self, messages):
        raise OSError("the mail server is down")


def test_the_manual_provider_says_change_it_in_zoom_too(it_client, zoom02, settings, http_mock):
    settings.ZOOM_PROVIDER = "manual"
    booking = zl42(zoom02)
    target = wed7(booking)
    assert it_client.get(class_url(booking, target)).context["checks_zoom"] is False
    response = it_client.post(class_url(booking, target), class_post(target))
    assert _messages(response) == [
        "Moved the class to Thu 8 Oct 2026, 9:00 am to 12:00 pm. We emailed nimal@example.com. "
        "This system can't reach Zoom: change it in Zoom too."
    ]
    assert len(http_mock.calls) == 0


def test_a_clash_shows_the_form_again_with_409(it_client, zoom02):
    booking = zl42(zoom02)
    FakeProvider.busy[zoom02.pk] = [BusyTime(at(8, 9), at(8, 10), "Staff briefing", "8555")]
    response = it_client.post(class_url(booking, wed7(booking)), class_post(wed7(booking)))
    assert response.status_code == 409
    assert response.context["move_error"] == (
        "Zoom 02 has a meeting in Zoom at that time: Staff briefing, Thu 8 Oct 2026 at 9:00 am. "
        "Choose another time."
    )
    assert response.context["form"]["date"].value() == "2026-10-08"
    # The facts show the stored time, fresh.
    assert response.context["occurrence"].starts_at == at(7, 8, 30)


def test_zoom_couldnt_be_asked_shows_the_form_again_with_200(it_client, zoom02):
    booking = zl42(zoom02)
    FakeProvider.unavailable[zoom02.pk] = ZoomBusy()
    response = it_client.post(series_url(booking), series_post(booking))
    assert response.status_code == 200
    assert response.context["move_error"].startswith(
        "We couldn't check Zoom 02's meetings in Zoom, so nothing was changed."
    )
    assert len(response.context["remaining"]) == 8


def test_a_zoom_failure_shows_the_form_again_with_200(it_client, zoom02):
    booking = zl42(zoom02)
    FakeProvider.update_errors = [ZoomBusy()]
    response = it_client.post(class_url(booking, wed7(booking)), class_post(wed7(booking)))
    assert response.status_code == 200
    assert response.context["move_error"] == (
        "We couldn't move it in Zoom: Zoom is busy right now. Nothing was changed. "
        "Try again in a few minutes."
    )
    assert mail.outbox == []


def test_zooms_daily_text_never_reaches_the_page(it_client, zoom02, settings, http_mock):
    """Criterion 14 on the real page: the daily-limit message, and none of Zoom's own words."""
    from . import zoommock as zm

    _real_templates(settings)
    settings.ZOOM_PROVIDER = "zoom"
    zm.connect(zoom02)
    zm.add_token(http_mock)
    zm.add_listing(http_mock, zoom02.email, [])
    http_mock.add(
        "PATCH",
        zm.meeting_url("81234567890"),
        status=429,
        headers={"X-RateLimit-Type": "Daily-limit-RAW-HEADER-8812"},
        json={
            "code": 429,
            "message": "You have reached the maximum daily rate limit for this API. "
            "RAW-ZOOM-TEXT-5521",
        },
    )
    booking = zl42(zoom02)
    target = wed7(booking)
    response = it_client.post(class_url(booking, target), class_post(target))
    assert response.status_code == 200
    page = html_module.unescape(response.content.decode())
    assert (
        "Zoom's daily limit for changing Zoom 02's meetings is used up. Nothing was changed. "
        "Try again after 5:30 am on Tue 29 Sep 2026." in " ".join(page.split())
    )
    assert "RAW-ZOOM-TEXT" not in page and "RAW-HEADER" not in page
    assert "maximum daily rate limit" not in page


def _marked_shown(occurrence):
    """A valid ``shown`` for the class that no fresh one can equal: it also lists a class that
    doesn't exist, which the stale check ignores. So a re-render that kept it is told apart from
    one that signed the rows again, even within the same second (criterion 33)."""
    from django.core import signing

    row = [
        occurrence.pk,
        int(occurrence.starts_at.timestamp()),
        int(occurrence.ends_at.timestamp()),
    ]
    return signing.dumps([row, [999_999_999, 0, 0]], salt=services.MOVE_SHOWN_SALT)


@pytest.mark.parametrize("failure", ["database clash", "zoom clash", "zoom error", "invalid"])
def test_a_failed_submit_keeps_the_posted_shown(it_client, zoom02, failure):
    """Criterion 33: only GET, the stale 409 and the 400 sign ``shown`` afresh. Every other
    re-render sends back exactly what was posted, so a failed submit never accepts someone
    else's move as seen (review round 1, B1)."""
    booking = zl42(zoom02)
    target = wed7(booking)
    typed = dict(GOOD_CLASS)
    status = 409
    if failure == "database clash":  # onto the booking's own Mon 5 Oct class
        typed = {"date": "2026-10-05", "start_time": "08:30", "end_time": "11:30"}
    elif failure == "zoom clash":
        FakeProvider.busy[zoom02.pk] = [BusyTime(at(8, 9), at(8, 10), "Staff briefing", "8555")]
    elif failure == "zoom error":
        FakeProvider.update_errors = [ZoomBusy()]
        status = 200
    else:
        typed = {**GOOD_CLASS, "end_time": "08:00"}
        status = 200
    posted = _marked_shown(target)
    response = it_client.post(class_url(booking, target), {**typed, "shown": posted})
    assert response.status_code == status
    assert response.context["form"]["shown"].value() == posted
    target.refresh_from_db()
    assert target.starts_at == at(7, 8, 30)


# --------------------------------------------------------------------------- 6 the detail page


def test_the_detail_offers_moves_on_an_approved_weekly_booking(it_client, zoom02, it_user):
    booking = zl42(zoom02)
    services.move_class(
        booking.pk, wed7(booking).pk, starts_at=at(7, 13), ends_at=at(7, 14), by=it_user
    )
    context = it_client.get(reverse("zoom:detail", args=[booking.pk])).context
    assert context["movable_ids"] == set(booking.occurrences.values_list("pk", flat=True))
    assert context["can_move_series"] is True
    assert context["checks_zoom"] is True
    moved = [o for o in context["occurrences"] if o.moved_at]
    assert [(o.moved_at, o.moved_by) for o in moved] == [(FROZEN_NOW, it_user)]


def test_a_one_off_has_its_class_movable_but_no_series(it_client, zoom02):
    booking = zl43(zoom02)
    context = it_client.get(reverse("zoom:detail", args=[booking.pk])).context
    assert context["movable_ids"] == {booking.occurrences.get().pk}
    assert context["cancellable_ids"] == set()
    assert context["can_move_series"] is False


def test_nothing_is_movable_while_waiting_or_cancelled_or_in_progress(
    it_client, zoom02, it_user, now_is
):
    waiting = make_request()
    context = it_client.get(reverse("zoom:detail", args=[waiting.pk])).context
    assert (context["movable_ids"], context["can_move_series"]) == (set(), False)
    cancelled = zl42(make_account("Zoom 03"))
    services.cancel(cancelled.pk, by=it_user, reason="Closed.")
    context = it_client.get(reverse("zoom:detail", args=[cancelled.pk])).context
    assert (context["movable_ids"], context["can_move_series"]) == (set(), False)
    booking = zl42(zoom02)
    now_is(at(5, 9))
    context = it_client.get(reverse("zoom:detail", args=[booking.pk])).context
    assert context["can_move_series"] is False
    assert len(context["movable_ids"]) == 7  # every class still to come, one by one
    now_is(at(29, 9))  # every class has been held
    context = it_client.get(reverse("zoom:detail", args=[booking.pk])).context
    assert (context["movable_ids"], context["can_move_series"]) == (set(), False)


def test_the_slots_follow_a_move_so_the_old_time_is_free(zoom02):
    booking = zl42(zoom02)
    target = wed7(booking)
    services.move_class(booking.pk, target.pk, starts_at=at(8, 9), ends_at=at(8, 12), by=None)
    assert not HostSlot.objects.filter(host_account=zoom02, starts_at=at(7, 8, 30)).exists()
    assert HostSlot.objects.filter(host_account=zoom02, starts_at=at(8, 9)).exists()
    assert LinkRequest.objects.get(pk=booking.pk).status == LinkRequest.Status.APPROVED


# --------------------------------------------------------------------------- 27 the series box


def _series_box(html):
    match = re.search(r'<section[^>]*aria-labelledby="move-series-title".*?</section>', html, re.S)
    assert match, "the series box is missing"
    return match.group(0)


LEAD_ZOOM = (
    "Moves every class still to come to a new time of day, on the same days, in Zoom too, and "
    "emails the requester. To move just one class, use Move this class in the list above."
)
LEAD_MANUAL = (
    "Moves every class still to come to a new time of day, on the same days, and emails the "
    "requester. To move just one class, use Move this class in the list above."
)


@pytest.mark.parametrize(("provider", "lead"), [("fake", LEAD_ZOOM), ("manual", LEAD_MANUAL)])
def test_the_series_box_lead_follows_checks_zoom_and_has_no_warning(
    it_client, zoom02, settings, provider, lead
):
    _real_templates(settings)
    settings.ZOOM_PROVIDER = provider
    booking = zl42(zoom02)
    html = it_client.get(reverse("zoom:detail", args=[booking.pk])).content.decode()
    box = _series_box(html)
    assert lead in " ".join(box.split())
    assert "Check Zoom for clashes first" not in box and "notice--warn" not in box


def test_the_manual_series_form_warns_to_check_zoom_first(it_client, zoom02, settings):
    _real_templates(settings)
    settings.ZOOM_PROVIDER = "manual"
    booking = zl42(zoom02)
    response = it_client.get(series_url(booking))
    assert response.status_code == 200
    assert "Check Zoom for clashes first" in response.content.decode()


def test_the_rendered_move_page_carries_the_date_limits_and_time_steps(it_client, zoom02, settings):
    """Criterion 5 on the real page: ``partials/field.html`` prints the widget's own attributes."""
    _real_templates(settings)
    booking = zl42(zoom02)
    html = it_client.get(class_url(booking, wed7(booking))).content.decode()
    date_input = re.search(r'<input[^>]*name="date"[^>]*>', html).group(0)
    assert 'min="2026-09-28"' in date_input and 'max="2027-09-28"' in date_input
    for name in ("start_time", "end_time"):
        time_input = re.search(rf'<input[^>]*name="{name}"[^>]*>', html).group(0)
        assert 'type="time"' in time_input and 'step="300"' in time_input
    assert f'href="/zoom/timetable/?month=2026-10&amp;account={zoom02.pk}"' in html


def test_the_rendered_move_page_prefills_the_current_date_and_times(it_client, zoom02, settings):
    """Criterion 5 / D.2.4: the fields are "filled in with the class's current values" on GET.

    A browser only honours a ``type=date``/``type=time`` input's ``value`` when it is valid
    HTML5 (``YYYY-MM-DD`` / ``HH:MM``). ``partials/field.html`` prints ``field.value`` straight
    into the attribute; for an unbound date/time field that is the raw ``date``/``time`` object,
    which Django's template engine then renders through the *display* formats (``DATE_FORMAT``/
    ``TIME_FORMAT``, e.g. "Oct. 7, 2026" / "7 a.m."), not the widget's own input format. A
    browser silently drops that value and shows the field empty, so IT sees a blank date and
    blank times instead of the class's current booking.
    """
    _real_templates(settings)
    booking = zl42(zoom02)
    html = it_client.get(class_url(booking, wed7(booking))).content.decode()
    date_input = re.search(r'<input[^>]*name="date"[^>]*>', html).group(0)
    assert 'value="2026-10-07"' in date_input, date_input
    for name, expected in (("start_time", "08:30"), ("end_time", "11:30")):
        time_input = re.search(rf'<input[^>]*name="{name}"[^>]*>', html).group(0)
        assert f'value="{expected}"' in time_input, time_input


# --------------------------------------------------------------------------- 28 the shared partial


def test_the_request_form_still_shows_typed_values_as_typed(client, settings):
    """Criterion 28's guard: 005's request form, bound and invalid, re-shows what was typed.

    ``partials/field.html`` now prints the widget's formatted value; a bound value must still be
    the raw text, even one that isn't a time at all (``25:99``), and the error must stay on it.
    """
    _real_templates(settings)
    typed = {"first_date": "2026-10-05", "start_time": "08:30", "end_time": "25:99"}
    response = client.post(reverse("zoom:request"), typed)
    assert response.status_code == 200
    html = response.content.decode()
    inputs = {
        name: re.search(rf'<input[^>]*name="{name}"[^>]*>', html).group(0)
        for name in ("first_date", "start_time", "end_time")
    }
    assert 'value="2026-10-05"' in inputs["first_date"], inputs["first_date"]
    assert 'value="08:30"' in inputs["start_time"], inputs["start_time"]
    assert 'value="25:99"' in inputs["end_time"], inputs["end_time"]
    assert 'aria-invalid="true"' in inputs["end_time"]


def test_the_move_forms_time_widgets_print_hours_and_minutes(zoom02):
    """An ``<input type=time>`` only takes ``HH:MM``, so the shared widgets carry that format."""
    booking = zl42(zoom02)
    for form in (
        MoveClassForm(occurrence=wed7(booking)),
        MoveSeriesForm(link_request=booking),
    ):
        assert 'value="08:30"' in str(form["start_time"])
        assert 'value="11:30"' in str(form["end_time"])


# --------------------------------------------------------------------------- 30 stale forms

OUT_OF_DATE = "This page is out of date. Reload it, check the times, then try again."


@pytest.mark.parametrize("kind", ["class", "series"])
@pytest.mark.parametrize("shown", ["missing", "empty", "edited", "other salt", "not a list"])
def test_a_missing_or_edited_shown_is_out_of_date(it_client, zoom02, kind, shown):
    """Criterion 30: no readable ``shown`` means a 400, a non-field error, and nothing done."""
    from django.core import signing

    booking = zl42(zoom02)
    target = wed7(booking)
    url, post = (
        (class_url(booking, target), class_post(target))
        if kind == "class"
        else (series_url(booking), series_post(booking))
    )
    good = post["shown"]
    post["shown"] = {
        "missing": None,
        "empty": "",
        "edited": good[:-2] + ("aa" if not good.endswith("aa") else "bb"),
        "other salt": signing.dumps([[target.pk, 0, 0]], salt="apps.zoom.start"),
        "not a list": signing.dumps("hello", salt="apps.zoom.move-shown"),
    }[shown]
    if post["shown"] is None:
        del post["shown"]
    response = it_client.post(url, post)
    assert response.status_code == 400
    form = response.context["form"]
    assert form.non_field_errors() == [OUT_OF_DATE]
    assert "shown" not in form.errors  # never an error on the hidden input
    assert form["start_time"].value() == "09:00"  # what was typed is kept
    # A fresh ``shown`` goes out with the page, so pressing again works.
    assert services.read_move_shown(form["shown"].value())
    assert FakeProvider.busy_calls == [] and FakeProvider.patched == []
    assert mail.outbox == []
    target.refresh_from_db()
    assert target.starts_at == at(7, 8, 30) and target.moved_at is None


def test_the_rendered_move_form_carries_shown_as_a_hidden_input(it_client, zoom02, settings):
    _real_templates(settings)
    booking = zl42(zoom02)
    target = wed7(booking)
    for url in (class_url(booking, target), series_url(booking)):
        html = it_client.get(url).content.decode()
        hidden = re.search(r'<input[^>]*name="shown"[^>]*>', html).group(0)
        assert 'type="hidden"' in hidden
        value = re.search(r'value="([^"]+)"', hidden).group(1)
        assert services.read_move_shown(value)


# --------------------------------------------------------------------------- 31 blocked series box

OFF_PATTERN = (
    "The class now on Thu 8 Oct 2026, 8:30 am to 11:30 am was moved to a different day, so the "
    "remaining classes can't be changed together. Move each class on its own instead, with Move "
    "this class."
)


def test_a_series_blocked_by_a_moved_day_is_explained_on_the_detail(
    it_client, zoom02, it_user, settings
):
    booking = zl42(zoom02)
    services.move_class(
        booking.pk, wed7(booking).pk, starts_at=at(8, 8, 30), ends_at=at(8, 11, 30), by=it_user
    )
    context = it_client.get(reverse("zoom:detail", args=[booking.pk])).context
    assert context["move_series_blocked"] == OFF_PATTERN
    assert context["can_move_series"] is False
    _real_templates(settings)
    html = it_client.get(reverse("zoom:detail", args=[booking.pk])).content.decode()
    box = _series_box(html)
    assert OFF_PATTERN in html_module.unescape(" ".join(box.split()))
    assert series_url(booking) not in html


def test_nothing_moved_means_no_blocked_note_and_the_usual_box(it_client, zoom02, settings):
    booking = zl42(zoom02)
    context = it_client.get(reverse("zoom:detail", args=[booking.pk])).context
    assert context["move_series_blocked"] is None
    assert context["can_move_series"] is True
    _real_templates(settings)
    html = it_client.get(reverse("zoom:detail", args=[booking.pk])).content.decode()
    box = _series_box(html)
    assert LEAD_ZOOM in " ".join(box.split())
    assert series_url(booking) in box


def test_a_class_in_progress_hides_the_box_and_has_no_blocked_note(
    it_client, zoom02, it_user, settings, now_is
):
    booking = zl42(zoom02)
    services.move_class(
        booking.pk, wed7(booking).pk, starts_at=at(8, 8, 30), ends_at=at(8, 11, 30), by=it_user
    )  # blocked by a moved day too, but "in progress" wins and hides the box
    now_is(at(5, 9))
    context = it_client.get(reverse("zoom:detail", args=[booking.pk])).context
    assert context["move_series_blocked"] is None and context["can_move_series"] is False
    _real_templates(settings)
    html = it_client.get(reverse("zoom:detail", args=[booking.pk])).content.decode()
    assert 'aria-labelledby="move-series-title"' not in html


def test_other_bookings_never_carry_a_blocked_note(it_client, zoom02, it_user):
    one_off = zl43(zoom02)
    waiting = make_request()
    for booking in (one_off, waiting):
        context = it_client.get(reverse("zoom:detail", args=[booking.pk])).context
        assert context["move_series_blocked"] is None
