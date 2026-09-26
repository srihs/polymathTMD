"""Platform tests for config/log_filters.py and its use in LOGGING (tmd-devops).

A class start link (brief 011) is a working host link, so no log line may hold one. These tests
drive real requests through Django and read what the configured console handler writes: the
filter sits on the handler, so pytest's caplog, which adds its own unfiltered handler, can't
show the redaction.
"""

import io
import logging
import sys

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse

from config.log_filters import HideStartTokenFilter, hide_start_token

TOKEN = "abc.def"


@pytest.fixture
def console_log():
    """What the filtered root console handler writes during the test."""
    handler = next(
        h
        for h in logging.getLogger().handlers
        if any(isinstance(f, HideStartTokenFilter) for f in h.filters)
    )
    stream = io.StringIO()
    previous = handler.setStream(stream)
    yield stream
    handler.setStream(previous)


def test_the_typed_prefix_matches_the_start_url():
    """log_filters.py can't call reverse() (gunicorn loads it before Django), so it types the
    prefix. This fails if zoom:start moves, where the filter would otherwise stop matching."""
    assert hide_start_token(reverse("zoom:start", args=[TOKEN])) == "/zoom/start/[hidden]/"


@pytest.mark.parametrize(
    "text",
    [
        "Not Found: /zoom/start/abc.def/",
        "Not Found: /zoom/start/abc.def/?next=x",
        "Not Found: /zoom/st%61rt/abc.def/",
        "Invalid HTTP_HOST header: 'x'. Referer 'http://h/zoom/start/abc.def/'",
    ],
)
def test_hide_start_token_hides_the_token_the_query_and_the_encoded_form(text):
    hidden = hide_start_token(text)
    assert TOKEN not in hidden and "next=x" not in hidden
    assert "/zoom/start/[hidden]/" in hidden


def test_every_logging_handler_carries_the_filter():
    """A handler added later without the filter would write start tokens again."""
    for name, handler in settings.LOGGING["handlers"].items():
        assert "hide_start_token" in handler.get("filters", []), name


def test_runserver_request_lines_reach_the_filtered_console():
    """django.server writes the request line in dev. Django's default handler for it has no
    filter, so LOGGING sends it to the root console instead."""
    logger = logging.getLogger("django.server")
    assert logger.handlers == [] and logger.propagate


def test_a_traceback_holding_a_token_is_hidden():
    try:
        raise ValueError(f"bad /zoom/start/{TOKEN}/")
    except ValueError:
        record = logging.LogRecord(
            "django.request", logging.ERROR, __file__, 1, "Internal Server Error: %s",
            ("/zoom/start/abc.def/",), exc_info=sys.exc_info(),
        )  # fmt: skip
    HideStartTokenFilter().filter(record)
    assert TOKEN not in record.getMessage()
    assert TOKEN not in record.exc_text
    assert "ValueError: bad /zoom/start/[hidden]/" in record.exc_text


def test_a_malformed_log_call_does_not_raise_into_the_caller(console_log, capsys):
    """Filters run outside Handler.handle()'s try, so a filter that raised would crash the view
    or service that logged. The record must reach emit(), which reports it as logging always
    has, via handleError ("--- Logging error ---" on stderr)."""
    handler = next(
        h
        for h in logging.getLogger().handlers
        if any(isinstance(f, HideStartTokenFilter) for f in h.filters)
    )
    record = logging.LogRecord(
        "apps.zoom", logging.WARNING, __file__, 1, "two args %s %s", ("only one",), None
    )
    handler.handle(record)  # must not raise
    assert record.msg == "two args %s %s" and record.args == ("only one",)
    assert "--- Logging error ---" in capsys.readouterr().err


@pytest.mark.django_db
def test_a_404_on_a_start_path_logs_it_hidden(console_log):
    response = Client().get(reverse("zoom:start", args=[TOKEN]))
    assert response.status_code == 404
    output = console_log.getvalue()
    assert "WARNING django.request: Not Found: /zoom/start/[hidden]/" in output
    assert TOKEN not in output


@pytest.mark.django_db
def test_a_csrf_403_on_a_start_path_logs_it_hidden(console_log):
    response = Client(enforce_csrf_checks=True).post(reverse("zoom:start", args=[TOKEN]))
    assert response.status_code == 403
    output = console_log.getvalue()
    assert (
        "WARNING django.security.csrf: Forbidden (CSRF cookie not set.): /zoom/start/[hidden]/"
        in output
    )
    assert TOKEN not in output


@pytest.mark.django_db
def test_a_404_elsewhere_still_logs_its_path(console_log):
    response = Client().get("/no-such-page/abc.def/?q=1")
    assert response.status_code == 404
    assert "WARNING django.request: Not Found: /no-such-page/abc.def/" in console_log.getvalue()
