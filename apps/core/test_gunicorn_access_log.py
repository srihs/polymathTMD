"""Platform tests for the prod image's access-log filter, docker/gunicorn.conf.py (tmd-devops).

A class start link (brief 011) is a working host link, so the access log must never hold one;
every other path must still be logged as it arrives. The rule itself (and its tie to
``reverse("zoom:start")``) is tested in test_log_filters.py; these cover gunicorn's use of it.
Gunicorn is a prod dependency that doesn't
install on Windows, so on a host .venv these tests skip; the dev container runs them.
"""

import importlib.util
from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.conf import settings

pytest.importorskip("gunicorn")

from gunicorn.config import Config  # noqa: E402


def _load_conf():
    """Load the config file by path: docker/ isn't a package, and gunicorn loads it the same way."""
    path = settings.BASE_DIR / "docker" / "gunicorn.conf.py"
    spec = importlib.util.spec_from_file_location("tmd_gunicorn_conf", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _access_line(raw_uri, *, referer="-"):
    """Format one access-log line with gunicorn's default format, as the prod image does."""
    conf = _load_conf()
    cfg = Config()
    cfg.set("logger_class", conf.logger_class)
    logger = cfg.logger_class(cfg)
    path, _, query = raw_uri.partition("?")
    environ = {
        "REQUEST_METHOD": "GET",
        "RAW_URI": raw_uri,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "SERVER_PROTOCOL": "HTTP/1.1",
        "REMOTE_ADDR": "172.18.0.1",
        "HTTP_REFERER": referer,
    }
    resp = SimpleNamespace(status="200 OK", headers=[], sent=512)
    req = SimpleNamespace(headers=[("REFERER", referer)])
    atoms = logger.atoms(resp, req, environ, timedelta(milliseconds=5))
    return cfg.access_log_format % logger.atoms_wrapper_class(atoms)


def test_prod_image_uses_the_hiding_logger():
    assert '"--config", "docker/gunicorn.conf.py"' in (settings.BASE_DIR / "Dockerfile").read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize(
    "raw_uri",
    ["/zoom/start/abc.def/", "/zoom/start/abc.def/?next=x", "/zoom/st%61rt/abc.def/"],
)
def test_start_token_is_hidden(raw_uri):
    line = _access_line(raw_uri, referer="http://localhost:8010/zoom/start/abc.def/")
    assert "abc.def" not in line
    assert "next=x" not in line
    assert '"GET /zoom/start/[hidden]/ HTTP/1.1"' in line
    assert '"http://localhost:8010/zoom/start/[hidden]/"' in line


def test_other_paths_are_logged_unchanged():
    line = _access_line("/zoom/requests/?status=waiting", referer="http://localhost:8010/")
    assert '"GET /zoom/requests/?status=waiting HTTP/1.1"' in line
    assert '"http://localhost:8010/"' in line
