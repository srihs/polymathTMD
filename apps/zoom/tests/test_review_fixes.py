"""Review round 1 fixes (brief 005): secrets masked in error reports (SF1), the shared date and
time filters (SF3), and the join-link check that refuses a backslash host trick (nit)."""

import sys
from datetime import UTC, date, datetime, time
from unittest import mock

import pytest
from django.core.signals import got_request_exception
from django.template import Context, Template
from django.urls import reverse
from django.views.debug import ExceptionReporter

from apps.zoom import models, services
from apps.zoom.forms import JOIN_URL_INVALID, ApproveForm

from .conftest import make_account, make_request

pytestmark = pytest.mark.django_db
HOST_KEY = "8421973"
NEW_KEY = "7654321"


# --------------------------------------------------------------------------- SF1


def _frame_vars(reporter, function):
    frame = next(f for f in reporter.get_traceback_data()["frames"] if f["function"] == function)
    return dict(frame["vars"])


def test_approving_never_decrypts_a_host_key(account, it_user):
    """Brief 011, criterion 27: ``approve()`` doesn't call ``get_host_key()`` at all."""
    with mock.patch.object(
        models.HostAccount, "get_host_key", side_effect=AssertionError("decrypted")
    ):
        result = services.approve(make_request().pk, account_id=account.pk, by=it_user)
    assert result.outcome == services.Outcome.APPROVED
    assert not hasattr(result, "host_key")
    assert not hasattr(services.Outcome, "HOST_KEY_UNREADABLE")
    assert not hasattr(services, "HOST_KEY_UNREADABLE")


def test_error_report_after_decryption_masks_the_host_key(account, it_user):
    """Brief 011, criterion 43: the key is decrypted only in ``reveal_host_key``, masked there.

    The reveal's record is made to fail after decryption, so the traceback runs through the
    frame that holds the key; the view's own frame is checked in ``test_host_key_reveal.py``.
    """
    with (
        mock.patch.object(models.HostKeyReveal.objects, "create", side_effect=RuntimeError("boom")),
        pytest.raises(RuntimeError) as caught,
    ):
        services.reveal_host_key(account, by=it_user)
    reporter = ExceptionReporter(None, caught.type, caught.value, caught.tb)

    assert "*****" in _frame_vars(reporter, "reveal_host_key")["plain"]
    assert HOST_KEY not in reporter.get_traceback_html()
    assert HOST_KEY not in reporter.get_traceback_text()


@pytest.mark.parametrize("page", ["zoom:account_edit", "zoom:account_add"])
def test_error_report_of_the_account_forms_masks_a_typed_host_key(
    client, superuser, monkeypatch, page
):
    """Brief 008, criterion 24: the old admin test, rewritten against the in-app pages.

    The account's save raises after the form has validated and ``set_host_key`` has run, so
    the typed key has passed through the view, the form and the model on its way to the report.
    """
    account = make_account(host_key=HOST_KEY)
    reports = []

    def capture(sender, request, **kwargs):
        reports.append(ExceptionReporter(request, *sys.exc_info()))

    def fail(*args, **kwargs):
        raise RuntimeError("database went away")

    if page == "zoom:account_add":
        url = reverse(page)
        label, email = "Zoom 02", "zoom02@polymath.example"
    else:
        url = reverse(page, args=[account.pk])
        label, email = account.label, account.email
    monkeypatch.setattr(models.HostAccount, "save", fail)
    got_request_exception.connect(capture)
    client.raise_request_exception = False
    client.force_login(superuser)
    try:
        response = client.post(
            url,
            {
                "label": label,
                "email": email,
                "is_paid": "on",
                "is_active": "on",
                "sort_order": 0,
                "notes": "",
                "host_key": NEW_KEY,
            },
        )
    finally:
        got_request_exception.disconnect(capture)
    assert response.status_code == 500
    [reporter] = reports
    html = reporter.get_traceback_html()
    text = reporter.get_traceback_text()
    assert "host_key" in html  # the parameter is listed, its value masked
    assert "*****" in html and "*****" in text
    for secret in (NEW_KEY, HOST_KEY):
        assert secret not in html
        assert secret not in text


def test_the_key_cleaning_method_masks_its_locals():
    """Brief 005 review round 2, nit 2: the typed key is masked in ``clean_host_key`` too."""
    from apps.zoom.forms import HostAccountForm

    form = HostAccountForm(data={"host_key": NEW_KEY})
    form.cleaned_data = {"host_key": NEW_KEY}
    # ``ord`` is a builtin, so it fails on the key without adding a Python frame that would
    # hold it; the only frame with the key is the form's own.
    with (
        mock.patch("apps.zoom.forms.validate_host_key", ord),
        pytest.raises(TypeError) as caught,
    ):
        form.clean_host_key()
    reporter = ExceptionReporter(None, caught.type, caught.value, caught.tb)
    assert "*****" in _frame_vars(reporter, "clean_host_key")["value"]
    assert NEW_KEY not in reporter.get_traceback_html()
    assert NEW_KEY not in reporter.get_traceback_text()


def test_the_host_key_validator_masks_its_argument():
    """Nit 2's second half: ``validate_host_key``'s own argument is masked too."""
    from django.core.exceptions import ValidationError

    from apps.zoom.validators import validate_host_key

    # Built at run time: the report quotes source lines, and a literal would show up there.
    typed = "84219" + "a3"
    with pytest.raises(ValidationError) as caught:
        validate_host_key(typed)
    reporter = ExceptionReporter(None, caught.type, caught.value, caught.tb)
    # The test's own frame holds ``typed`` unmasked, so only the validator's frame is checked.
    validator_vars = _frame_vars(reporter, "validate_host_key")
    assert "*****" in validator_vars["value"]
    assert typed not in str(validator_vars)


def test_set_host_key_and_crypto_frames_are_masked(settings):
    account = models.HostAccount(label="Zoom 01")
    with (
        mock.patch("apps.zoom.crypto._cipher", side_effect=RuntimeError("boom")),
        pytest.raises(RuntimeError) as caught,
    ):
        account.set_host_key(HOST_KEY)
    reporter = ExceptionReporter(None, caught.type, caught.value, caught.tb)
    assert "*****" in _frame_vars(reporter, "set_host_key")["plain"]
    assert "*****" in _frame_vars(reporter, "encrypt")["plain"]
    assert HOST_KEY not in reporter.get_traceback_html()


# --------------------------------------------------------------------------- SF3


def _render(source, **context):
    return Template("{% load zoom_format %}" + source).render(Context(context))


def test_filters_share_the_python_formats_and_show_colombo_time():
    starts = datetime(2026, 10, 5, 3, 0, tzinfo=UTC)  # 8:30 am in Colombo
    assert _render("{{ d|class_date }}, {{ d|class_time }}", d=starts) == "Mon 5 Oct 2026, 8:30 am"
    assert _render("{{ d|class_date }}", d=date(2026, 10, 7)) == "Wed 7 Oct 2026"
    assert _render("{{ t|class_time }}", t=time(12, 0)) == "12:00 pm"
    assert _render("{{ t|class_time }}{{ t|class_date }}", t=None) == ""
    assert models.class_date(starts) == "Mon 5 Oct 2026"
    assert models.class_time(starts) == "8:30 am"


def test_occurrence_line_uses_the_same_formats():
    occurrence = make_request().occurrences.get()
    rendered = _render(
        "{{ o.starts_at|class_date }}, {{ o.starts_at|class_time }} to {{ o.ends_at|class_time }}",
        o=occurrence,
    )
    assert rendered == str(occurrence) == "Mon 5 Oct 2026, 8:30 am to 11:30 am"


# --------------------------------------------------------------------------- join-link nit


@pytest.mark.parametrize(
    ("link", "ok"),
    [
        ("https://us02web.zoom.us/j/12345678901", True),
        ("https://zoom.us/j/12345678901?pwd=abc", True),
        ("https://evil.example\\.zoom.us/j/1", False),
        ("https://evil.example\\@us02web.zoom.us/j/1", False),
        ("https://zoom.us.evil.example/j/1", False),
        ("http://us02web.zoom.us/j/1", False),
        ("https://us02web.zoom.us /j/1", False),
    ],
)
def test_join_link_must_be_an_https_zoom_link(account, link, ok):
    form = ApproveForm(
        data={"host_account": account.pk, "join_url": link, "meeting_id": "12345678901"},
        free_accounts=[account],
        needs_manual_details=True,
    )
    assert form.is_valid() is ok
    if not ok:
        assert form.errors["join_url"] == [JOIN_URL_INVALID]
