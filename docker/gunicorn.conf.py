"""Gunicorn settings for the prod image: an access log that never records a start token.

Why this file exists: a class start link, ``/zoom/start/<token>/`` (brief 011), is a signed,
working link that starts the class as its host. Gunicorn's access log writes the request line,
the path and the Referer of every request to ``docker compose logs web``, so each open of the
start page would leave a usable host link in the logs. ``HiddenStartTokenLogger`` swaps the
token for ``[hidden]`` before the line is formatted. Every other path is logged as usual.
The rule itself, ``hide_start_token``, is defined once, in ``config/log_filters.py``,
which Django's ``LOGGING`` uses as well.

Only the logger lives here. The bind address, control socket and log targets stay on the
Dockerfile's ``CMD`` line, where they're visible at a glance (command-line flags override this
file anyway). The Dockerfile passes this file with ``--config``. ``logger_class`` accepts the
class object itself, so ``docker/`` doesn't have to be an importable package.
"""

import sys
from pathlib import Path

from gunicorn.glogging import Logger

# Gunicorn reads this file before it adds the project to sys.path for the WSGI app, so add the
# project root (/app) here to make ``config`` importable. log_filters.py doesn't import Django.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.log_filters import hide_start_token  # noqa: E402


class HiddenStartTokenLogger(Logger):
    """Gunicorn's logger with start tokens removed from every access-log atom.

    Every string atom is rewritten, not just ``%(r)s``, so any future ``access_log_format`` is
    covered too. That includes the path (``U``), the Referer (``f`` and ``{referer}i``, which
    are set when the start page's own form posts back), the raw URI and path environ atoms, and
    the response headers. On a start path the query string atom is emptied, since it has no
    other use there.
    """

    def atoms(self, resp, req, environ, request_time):
        atoms = super().atoms(resp, req, environ, request_time)
        on_start_path = hide_start_token(environ.get("PATH_INFO")) != environ.get("PATH_INFO")
        for key, value in atoms.items():
            atoms[key] = hide_start_token(value)
        if on_start_path:
            atoms["q"] = ""
            atoms["{query_string}e"] = ""
        return atoms


logger_class = HiddenStartTokenLogger
