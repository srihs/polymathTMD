"""Hides class start tokens from every log line (a platform helper next to the settings).

Why: a class start link, ``/zoom/start/<token>/`` (brief 011), is a signed, working link that
starts the class as its host, and it has no expiry. Several loggers write request paths:
- Django's ``django.request`` writes ``Not Found: <path>`` and ``Internal Server Error: <path>``;
- ``django.security.*`` writes lines such as ``Forbidden (CSRF cookie not set.): <path>``;
- ``django.server`` (runserver) writes the request line;
- Gunicorn's access log writes the request line and the Referer.

Without this module, each of those lines could hold a usable host link in
``docker compose logs web``.

This is the one definition of the rule. ``LOGGING`` in ``base.py`` attaches
``HideStartTokenFilter`` to its handlers, and ``docker/gunicorn.conf.py`` imports
``hide_start_token`` for the access log. The file lives here because the platform owns it and
because gunicorn loads it before Django starts, so it must not import Django.
``apps/core/test_log_filters.py`` ties the typed prefix to ``reverse("zoom:start")``.
"""

import logging
import re
from urllib.parse import unquote

HIDDEN_START_PATH = "/zoom/start/[hidden]/"

# The prefix followed by everything up to whitespace or a quote: the token, the trailing slash
# and any ``?query``. Unanchored, so it also matches inside a full URL, a Referer, a
# script-name prefix, or the middle of a message. It is typed out rather than reversed because
# gunicorn loads this module before Django starts.
_START_PATH = re.compile(r"/zoom/start/[^\s\"']*")


def hide_start_token(value):
    """Return ``value`` with any start token replaced, or unchanged when it holds none.

    The match is also made on the percent-decoded text. Logs show the raw request target, but
    Django routes the decoded path, so ``/zoom/st%61rt/<token>/`` still reaches the start view
    and must be hidden too. Only a string that holds a start path is rewritten (and
    decoded), so every other log line keeps its original bytes.
    """
    if not isinstance(value, str):
        return value
    decoded = unquote(value)
    if not _START_PATH.search(decoded):
        return value
    return _START_PATH.sub(HIDDEN_START_PATH, decoded)


class HideStartTokenFilter(logging.Filter):
    """Rewrites a record's message and traceback text so no start token reaches a handler.

    The filter is attached to handlers, not loggers. Python applies a logger's filters only to
    records created on that logger, not to records that propagate up from child loggers.
    ``django.security.<ExceptionName>`` loggers are named at run time, so only a handler
    filter reliably sees all of them.

    The message is merged with its args only when the merged text holds a token, and then
    ``args`` is cleared. Every other record keeps lazy ``%`` formatting. The record is always
    kept, because the aim is to redact, not to drop.

    Filters run outside ``Handler.handle()``'s error handling, so an exception here would reach
    the code that made the log call. A malformed call, such as a wrong ``%s`` count, must
    still end as logging's own "--- Logging error ---" report from ``emit()``, as it did
    without this filter. So any failure leaves the record untouched and lets it through
    (review round 2).
    """

    def filter(self, record):
        try:
            original = record.getMessage()
            message = hide_start_token(original)
            exc_text = record.exc_text
            if record.exc_info and not exc_text:
                # Formatter.format() reuses a cached exc_text, so caching the redacted text
                # here keeps a token inside an exception message out of the traceback too.
                exc_text = logging.Formatter().formatException(record.exc_info)
            exc_text = hide_start_token(exc_text)
        except Exception:
            return True
        if message != original:
            record.msg, record.args = message, ()
        record.exc_text = exc_text
        return True
