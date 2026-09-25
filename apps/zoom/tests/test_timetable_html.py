"""HTML-level checks for the Zoom timetable's real templates (brief 009, verifier-added).

``apps/zoom/tests/conftest.py`` stubs ``zoom/timetable*.html`` for the view-layer tests in
``test_timetable.py``, so those tests pin the context contract but not the markup a person or
a screen reader actually sees. This file renders the real templates (as ``test_accounts.py``
and ``test_sidebar_zoom_group.py`` do for their pages) and checks the page frame, the month
navigation, the table's semantics and the three-months-of-rows case, the day box heading and
today marker, an entry's visible and accessible text (booked and waiting, escaped), the
"+N more" link, the summary and empty-state copy, the day view's ``month_url``-built links, and
the two contextual links (criteria 20, 21) that only the real templates render.
"""

import re
from datetime import date, time
from html import unescape

import pytest
from django.urls import reverse

from apps.zoom.models import LinkRequest

from .conftest import make_account, make_request
from .test_accounts import _user_with
from .test_sidebar_zoom_group import _real_templates
from .test_timetable import MONTH_URL, add_class, day_url

pytestmark = pytest.mark.django_db


# =========================================================================== month page frame (3)


def test_month_page_frame(it_client, settings):
    _real_templates(settings)
    html = it_client.get(MONTH_URL).content.decode()
    assert "<title>Zoom timetable, September 2026 · " in html
    assert '<h1 class="page-heading">Zoom timetable</h1>' in html
    assert '<span aria-current="page">Zoom timetable</span>' in html
    assert '<h2 class="box__title" id="month-title">September 2026</h2>' in html


# =========================================================================== month navigation (5)


def test_month_navigation_links_and_accessible_names_on_the_current_month(it_client, settings):
    """On September 2026 (the frozen now's month): prev/next hrefs and hidden names;
    ``This month`` is left out because the page is already on the current month."""
    _real_templates(settings)
    html = it_client.get(MONTH_URL).content.decode()
    assert f'href="{MONTH_URL}?month=2026-08"' in html
    assert f'href="{MONTH_URL}?month=2026-10"' in html
    assert 'Previous month<span class="visually-hidden">, August 2026</span>' in html
    assert 'Next month<span class="visually-hidden">, October 2026</span>' in html
    assert ">This month<" not in html


def test_this_month_link_appears_off_the_current_month_and_keeps_the_account(it_client, settings):
    _real_templates(settings)
    account = make_account("Zoom 01")
    html = it_client.get(MONTH_URL, {"month": "2026-10", "account": account.pk}).content.decode()
    assert f'href="{MONTH_URL}?account={account.pk}">This month</a>' in html
    assert f"?month=2026-09&amp;account={account.pk}" in html
    assert f"?month=2026-11&amp;account={account.pk}" in html


# =========================================================================== the table (6, 22)


def test_table_caption_and_column_headers(it_client, settings):
    _real_templates(settings)
    html = it_client.get(MONTH_URL).content.decode()
    assert (
        '<caption class="visually-hidden">Zoom classes in September 2026, by week, '
        "Monday to Sunday.</caption>" in html
    )
    heads = re.findall(
        r'<th scope="col" role="columnheader" aria-colindex="[1-7]">(.*?)</th>', html, re.S
    )
    assert len(heads) == 7
    joined = "".join(heads)
    assert re.findall(r'<span aria-hidden="true">(\w+)</span>', joined) == [
        "Mon",
        "Tue",
        "Wed",
        "Thu",
        "Fri",
        "Sat",
        "Sun",
    ]
    assert re.findall(r'<span class="visually-hidden">(\w+)</span>', joined) == [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]


@pytest.mark.parametrize(
    ("month_value", "rows"),
    [("2026-09", 5), ("2027-02", 4), ("2026-11", 6)],
)
def test_month_grid_has_the_right_number_of_week_rows(it_client, settings, month_value, rows):
    """Criterion 6, through the real table: September 2026 (5), February 2027 (4),
    November 2026 (6)."""
    _real_templates(settings)
    html = it_client.get(MONTH_URL, {"month": month_value}).content.decode()
    tbody = re.search(r"<tbody.*?</tbody>", html, re.S).group(0)
    assert tbody.count('<tr role="row">') == rows


def test_out_of_month_cells_are_empty(it_client, settings):
    _real_templates(settings)
    html = it_client.get(MONTH_URL).content.decode()
    # aria-colindex (review round 1, SF1) is checked in full by test_timetable.py.
    assert re.search(
        r'<td role="cell" aria-colindex="[1-7]" class="cal__day cal__day--out"></td>', html
    )


# =========================================================================== day box heading (7)


def test_day_box_heading_accessible_text_and_today_marker(it_client, settings):
    """Criterion 7: the h3's visible number and hidden weekday/month; today's marker."""
    _real_templates(settings)
    html = it_client.get(MONTH_URL).content.decode()
    assert '<time datetime="2026-09-01">' in html
    assert (
        '<span class="cal__date-extra">Tue </span><span class="cal__num">1</span>'
        '<span class="cal__date-extra"> Sep</span>' in html
    )
    assert html.count('aria-current="date"') == 1
    assert '<span class="tag tag--brand">Today</span>' in html


# =========================================================================== entries (8)


def test_entry_accessible_name_for_a_booked_class(it_client, settings):
    _real_templates(settings)
    account = make_account("Zoom 03")
    booked = add_class(account, date(2026, 9, 29), time(8, 30), time(11, 30))
    html = it_client.get(MONTH_URL).content.decode()
    ref = booked.link_request.reference
    assert (
        f'<span class="cal__time">8:30 am<span class="visually-hidden"> to 11:30 am, '
        f"{ref},</span></span>" in html
    )
    assert '<span class="cal__account">Zoom 03</span>' in html


def test_entry_shows_the_waiting_tag_with_icon_and_word_instead_of_an_account(it_client, settings):
    _real_templates(settings)
    add_class(day=date(2026, 9, 29), start=time(9, 0), end=time(10, 0))
    html = it_client.get(MONTH_URL).content.decode()
    assert '<span class="tag tag--warn"><svg class="icon" aria-hidden="true"' in html
    assert '<use href="#i-clock">' in html
    assert "Waiting for IT" in html
    assert '<span class="cal__account">' not in html


def test_class_name_is_escaped_never_rendered_as_markup(it_client, settings):
    _real_templates(settings)
    account = make_account("Zoom 01")
    add_class(account, date(2026, 9, 29), name="A & B <script>alert(1)</script>")
    html = it_client.get(MONTH_URL).content.decode()
    assert "<script>alert(1)</script>" not in html
    assert "A &amp; B &lt;script&gt;alert(1)&lt;/script&gt;" in html


# =========================================================================== +N more (9)


def test_overflow_link_text_and_accessible_name_plural(it_client, settings):
    _real_templates(settings)
    account = make_account("Zoom 01")
    for n in range(5):
        add_class(account, date(2026, 10, 7), time(8 + n, 0), time(8 + n, 55))
    html = it_client.get(MONTH_URL, {"month": "2026-10"}).content.decode()
    assert '<span aria-hidden="true">+2 more</span>' in html
    assert '<span class="visually-hidden">2 more classes on Wed 7 Oct</span>' in html


def test_overflow_link_accessible_name_singular(it_client, settings):
    _real_templates(settings)
    account = make_account("Zoom 01")
    for n in range(4):
        add_class(account, date(2026, 10, 7), time(8 + n, 0), time(8 + n, 55))
    html = it_client.get(MONTH_URL, {"month": "2026-10"}).content.decode()
    assert '<span aria-hidden="true">+1 more</span>' in html
    assert '<span class="visually-hidden">1 more class on Wed 7 Oct</span>' in html


# =========================================================================== summary line (12)


def test_summary_line_pluralisation_and_waiting_wording(it_client, settings):
    _real_templates(settings)
    account = make_account("Zoom 01")
    add_class(account, date(2026, 9, 29))
    add_class(day=date(2026, 9, 30))
    add_class(day=date(2026, 9, 30), start=time(12, 0), end=time(13, 0))
    html = it_client.get(MONTH_URL).content.decode()
    assert "1 booked class and 2 waiting for IT in September 2026." in html


def test_summary_line_omits_waiting_when_there_is_none(it_client, settings):
    _real_templates(settings)
    account = make_account("Zoom 01")
    add_class(account, date(2026, 9, 29))
    add_class(account, date(2026, 9, 30), time(12, 0), time(13, 0))
    html = it_client.get(MONTH_URL).content.decode()
    assert '<p class="result-line">2 booked classes in September 2026.</p>' in html


def test_summary_line_filtered(it_client, settings):
    _real_templates(settings)
    account = make_account("Zoom 03")
    add_class(account, date(2026, 9, 29))
    html = it_client.get(MONTH_URL, {"account": account.pk}).content.decode()
    assert "1 booked class on Zoom 03 in September 2026." in html


def test_summary_line_zero_booked_still_names_the_waiting_count(it_client, settings):
    """D.3: 0 booked and some waiting still uses the combined line, not the empty one."""
    _real_templates(settings)
    make_account("Zoom 01")
    add_class(day=date(2026, 9, 29))
    add_class(day=date(2026, 9, 30))
    html = it_client.get(MONTH_URL).content.decode()
    assert "0 booked classes and 2 waiting for IT in September 2026." in html


# =========================================================================== empty states (13)


def test_no_accounts_empty_state_with_add_link(it_client, settings):
    _real_templates(settings)
    html = it_client.get(MONTH_URL).content.decode()
    assert "No Zoom accounts are set up yet." in html
    assert "Ask the person" not in html
    assert f'href="{reverse("zoom:account_add")}"' in html
    assert "Add a Zoom account" in html


def test_no_accounts_empty_state_without_add_permission(client, settings):
    _real_templates(settings)
    reviewer = _user_with("review_linkrequest", username="reviewer2")
    client.force_login(reviewer)
    html = client.get(MONTH_URL).content.decode()
    assert "Ask the person who manages Zoom accounts to add one." in html
    assert "Add a Zoom account" not in html


def test_filtered_to_nothing_shows_show_all_accounts_link(it_client, settings):
    _real_templates(settings)
    account = make_account("Zoom 03")
    html = it_client.get(MONTH_URL, {"account": account.pk}).content.decode()
    assert "No classes booked on Zoom 03 in September 2026." in html
    assert f'href="{MONTH_URL}?month=2026-09">Show all accounts</a>' in html


# =========================================================================== day view (14)


def test_day_view_frame_and_breadcrumb(it_client, settings):
    _real_templates(settings)
    october_7 = date(2026, 10, 7)
    html = it_client.get(day_url(october_7)).content.decode()
    assert "<title>Zoom classes on Wed 7 Oct 2026 · " in html
    assert '<h1 class="page-heading">Zoom classes on Wed 7 Oct 2026</h1>' in html
    assert f'<a href="{MONTH_URL}?month=2026-10">Zoom timetable</a>' in html
    assert '<span aria-current="page">Wed 7 Oct 2026</span>' in html
    assert "Back to October 2026" in html


def test_day_view_crumb_and_back_link_both_equal_month_url_unfiltered(it_client, settings):
    """Criterion 14's test: both hrefs equal ``month_url``, unescaped, unfiltered."""
    _real_templates(settings)
    october_7 = date(2026, 10, 7)
    html = it_client.get(day_url(october_7)).content.decode()
    month_url = f"{MONTH_URL}?month=2026-10"
    hrefs = [unescape(h) for h in re.findall(r'href="([^"]*)"', html)]
    assert hrefs.count(month_url) == 2, hrefs


def test_day_view_crumb_and_back_link_both_equal_month_url_filtered(it_client, settings):
    """Criterion 14's test, filtered: both hrefs equal ``month_url`` after unescaping ``&amp;``."""
    _real_templates(settings)
    october_7 = date(2026, 10, 7)
    account = make_account("Zoom 01")
    html = it_client.get(day_url(october_7, account=account.pk)).content.decode()
    month_url = f"{MONTH_URL}?month=2026-10&account={account.pk}"
    hrefs = [unescape(h) for h in re.findall(r'href="([^"]*)"', html)]
    assert hrefs.count(month_url) == 2, hrefs


# =========================================================================== contextual links


def test_detail_page_shows_the_timetable_link_for_an_approved_request(it_client, settings):
    _real_templates(settings)
    account = make_account("Zoom 03")
    occurrence = add_class(account, date(2026, 11, 3))
    url = reverse("zoom:detail", args=[occurrence.link_request_id])
    html = it_client.get(url).content.decode()
    expected_href = f"{MONTH_URL}?month=2026-11&amp;account={account.pk}"
    assert f'<a class="tap-link" href="{expected_href}">See it on the timetable</a>' in html


def test_detail_page_hides_the_timetable_link_for_a_waiting_request(it_client, settings):
    _real_templates(settings)
    link_request = make_request(status=LinkRequest.Status.WAITING)
    url = reverse("zoom:detail", args=[link_request.pk])
    html = it_client.get(url).content.decode()
    assert "See it on the timetable" not in html


def test_accounts_list_shows_timetable_link_for_reviewers(it_client, settings):
    _real_templates(settings)
    account = make_account("Zoom 03")
    html = it_client.get(reverse("zoom:accounts")).content.decode()
    expected_href = f"{MONTH_URL}?account={account.pk}"
    assert (
        f'<a class="tap-link" href="{expected_href}">Timetable'
        '<span class="visually-hidden"> for Zoom 03</span></a>' in html
    )


def test_accounts_list_hides_timetable_link_without_review_permission(client, settings):
    _real_templates(settings)
    viewer = _user_with("view_hostaccount", username="viewer2")
    client.force_login(viewer)
    make_account("Zoom 03")
    html = client.get(reverse("zoom:accounts")).content.decode()
    assert "Timetable" not in html
