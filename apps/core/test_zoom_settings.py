"""Platform tests for brief 006's settings and plumbing (owned by tmd-devops).

They pin what the zoom app relies on but doesn't own: how credentials are read from the
environment and named (criterion 2), that Django masks them (criterion 3), the env files and
logging (criterion 7), and the project-wide network block (criterion 45). The zoom app's
checks, client and provider are tested in apps/zoom/tests/.
"""

import logging
import os
import re
import subprocess
import sys
import threading

import environ
import pytest
import requests
from django.conf import settings
from django.test import RequestFactory
from django.views.debug import ExceptionReporter, SafeExceptionReporterFilter

from config.settings.base import (
    ZoomCredentials,
    read_zoom_credentials,
    zoom_credential_env_prefix,
)

FAKE = ZoomCredentials(
    slug="zoom-test",
    account_id="test-account-id",
    client_id="test-client-id",
    client_secret="test-client-secret-value",
)


# --------------------------------------------------------------------------- criterion 2
def test_env_prefix_rule():
    assert zoom_credential_env_prefix("zoom-01") == "ZOOM_S2S_ZOOM_01"
    assert zoom_credential_env_prefix("main") == "ZOOM_S2S_MAIN"


def test_read_zoom_credentials_keeps_complete_sets_and_names_missing_variables(monkeypatch):
    monkeypatch.setenv("ZOOM_S2S_ZOOM_01_ACCOUNT_ID", "test-account-id")
    monkeypatch.setenv("ZOOM_S2S_ZOOM_01_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("ZOOM_S2S_ZOOM_01_CLIENT_SECRET", " test-client-secret ")
    monkeypatch.setenv("ZOOM_S2S_ZOOM_02_ACCOUNT_ID", "test-account-id")
    monkeypatch.setenv("ZOOM_S2S_ZOOM_02_CLIENT_ID", "   ")  # blank counts as missing
    monkeypatch.delenv("ZOOM_S2S_ZOOM_02_CLIENT_SECRET", raising=False)

    secrets, missing = read_zoom_credentials(environ.Env(), ["zoom-01", "zoom-02"])

    assert secrets == {
        "zoom-01": ZoomCredentials(
            slug="zoom-01",
            account_id="test-account-id",
            client_id="test-client-id",
            client_secret="test-client-secret",
        )
    }
    assert missing == {"zoom-02": ["ZOOM_S2S_ZOOM_02_CLIENT_ID", "ZOOM_S2S_ZOOM_02_CLIENT_SECRET"]}


def test_credentials_repr_shows_only_the_slug():
    text = repr(FAKE) + str(FAKE)
    assert "zoom-test" in text
    for value in (FAKE.account_id, FAKE.client_id, FAKE.client_secret):
        assert value not in text


def test_zoom_s2s_env_is_read_only_in_base_settings():
    """Criterion 2's source scan: env reads of ZOOM_S2S_* live in base.py alone."""
    env_read = re.compile(r"os\.environ|getenv\(|\benv(\.\w+)?\(")
    offenders = []
    roots = [settings.BASE_DIR / "apps", settings.BASE_DIR / "config"]
    for path in [p for root in roots for p in root.rglob("*.py")]:
        if path == settings.BASE_DIR / "config" / "settings" / "base.py":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "ZOOM_S2S_" in line and env_read.search(line):
                offenders.append(f"{path.relative_to(settings.BASE_DIR)}:{number}")
    assert not offenders, offenders


# --------------------------------------------------------------------------- criterion 3
def test_zoom_secrets_are_masked_in_error_reports(settings):
    settings.ZOOM_S2S_SECRETS = {"zoom-test": FAKE}
    settings.ZOOM_CREDENTIAL_SETS = ["zoom-test"]
    reporter_filter = SafeExceptionReporterFilter()
    safe = reporter_filter.get_safe_settings()

    assert safe["ZOOM_S2S_SECRETS"] == reporter_filter.cleansed_substitute
    # The list holds slugs only; if Django ever matches its name, it must be masked too.
    assert safe["ZOOM_CREDENTIAL_SETS"] in (["zoom-test"], reporter_filter.cleansed_substitute)


def test_debug_page_never_shows_zoom_credentials(settings):
    settings.ZOOM_S2S_SECRETS = {"zoom-test": FAKE}
    request = RequestFactory().get("/")
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        html = ExceptionReporter(request, *sys.exc_info()).get_traceback_html()
    for value in (FAKE.account_id, FAKE.client_id, FAKE.client_secret):
        assert value not in html


def test_prod_settings_refuse_the_fake_provider_and_name_zoom():
    env = {
        **os.environ,
        "ZOOM_PROVIDER": "fake",
        "ALLOWED_HOSTS": "localhost",
        "SECRET_KEY": "test-only-not-secret",
    }
    result = subprocess.run(
        [sys.executable, "-c", "import config.settings.prod"],
        cwd=settings.BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert "ZOOM_PROVIDER=zoom" in result.stderr


# --------------------------------------------------------------------------- criterion 7
def test_urllib3_logs_nothing_below_warning():
    assert settings.LOGGING["loggers"]["urllib3"]["level"] == "WARNING"
    assert logging.getLogger("urllib3").getEffectiveLevel() == logging.WARNING


def test_compose_loads_the_optional_credentials_file():
    text = (settings.BASE_DIR / "compose.yaml").read_text(encoding="utf-8")
    assert re.search(
        r"env_file:\s*\n\s*- path: \./zoom-credentials\.env\s*\n\s*required: false", text
    )
    # Listing them under `environment` would override the file with empty values.
    assert not re.search(r"^\s*(ZOOM_CREDENTIAL_SETS|ZOOM_S2S_\w+):", text, re.MULTILINE)


def test_credentials_file_is_git_ignored():
    lines = (settings.BASE_DIR / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "zoom-credentials.env" in {line.strip() for line in lines}


def test_credentials_example_names_every_variable_with_no_values():
    lines = (
        (settings.BASE_DIR / "zoom-credentials.env.example").read_text(encoding="utf-8")
    ).splitlines()
    assignments = [line for line in lines if line.strip() and not line.startswith("#")]
    names = [line.split("=", 1)[0] for line in assignments]
    prefix = zoom_credential_env_prefix("zoom-01")
    assert names == [
        "ZOOM_CREDENTIAL_SETS",
        f"{prefix}_ACCOUNT_ID",
        f"{prefix}_CLIENT_ID",
        f"{prefix}_CLIENT_SECRET",
    ]
    assert all(line.endswith("=") for line in assignments), "the example must hold no value"
    # One comment line straight above each variable.
    for line in assignments:
        assert lines[lines.index(line) - 1].startswith("# ")


def test_env_example_lists_the_zoom_provider():
    text = (settings.BASE_DIR / ".env.example").read_text(encoding="utf-8")
    assert re.search(r"^#\s+zoom\s+-", text, re.MULTILINE)


# --------------------------------------------------------------------------- criterion 45
def test_unregistered_http_call_is_blocked():
    with pytest.raises(requests.exceptions.ConnectionError):
        requests.get("https://api.zoom.us/v2/users/x", timeout=(5, 15))


def test_unregistered_http_call_is_blocked_in_a_worker_thread():
    errors = []

    def call():
        try:
            requests.get("https://api.zoom.us/v2/users/x", timeout=(5, 15))
        except requests.exceptions.ConnectionError as exc:
            errors.append(exc)

    worker = threading.Thread(target=call)
    worker.start()
    worker.join(timeout=30)
    assert len(errors) == 1


def test_registered_reply_is_served_and_recorded(http_mock):
    http_mock.get("https://api.zoom.us/v2/users/x", json={"type": 2})
    assert requests.get("https://api.zoom.us/v2/users/x", timeout=(5, 15)).json() == {"type": 2}
    assert [call.request.url for call in http_mock.calls] == ["https://api.zoom.us/v2/users/x"]
