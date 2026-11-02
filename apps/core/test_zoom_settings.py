"""Platform tests for the Zoom settings and plumbing (owned by tmd-devops).

They pin what the zoom app relies on but doesn't own: the env files, compose and logging, and
the project-wide network block (brief 006, criteria 7 and 45). From brief 015 Zoom credentials
are typed in the app and stored encrypted in the database, so these tests now pin that the
old env path is *gone* (criteria 36-39): no settings, variables, compose `env_file` or example
file for them, and SQL parameters (which now carry connection values) never logged.
The zoom app's model, checks, client and provider are tested in apps/zoom/tests/.
"""

import logging
import os
import re
import subprocess
import sys
import threading

import pytest
import requests
from django.conf import settings

# Built from parts so this file never matches its own scan (brief 015, criterion 26).
OLD_PREFIX = "ZOOM_" + "S2S"
OLD_LIST = "ZOOM_" + "CREDENTIAL"
NEEDLES = (OLD_PREFIX, OLD_LIST)
CREDENTIALS_FILE = "zoom-" + "credentials.env"
# The ignore files keep their line for a stray copy, under this comment (brief 015, D12).
RETIRED_COMMENT = (
    "# Retired by brief 015 (Zoom credentials are typed in the app). "
    "Kept so a stray copy is never committed or copied into the image."
)


def _text(path):
    return path.read_text(encoding="utf-8")


def _comment_above(path, marker):
    """The run of `#` lines straight above the first line starting with ``marker``, joined."""
    lines = _text(path).splitlines()
    index = next(i for i, line in enumerate(lines) if line.strip().startswith(marker))
    block = []
    while index > 0 and lines[index - 1].strip().startswith("#"):
        index -= 1
        block.insert(0, lines[index].strip())
    return " ".join(block)


def _scanned_files():
    """Every text file criterion 36's scan covers, skipping bytecode caches."""
    base = settings.BASE_DIR
    roots = [base / "apps", base / "config", base / "docker"]
    files = [p for root in roots for p in root.rglob("*") if p.is_file()]
    files = [p for p in files if "__pycache__" not in p.parts and p.suffix != ".pyc"]
    singles = ["compose.yaml", "compose.dev.yaml", "Dockerfile", ".env.example"]
    return files + [base / name for name in singles]


# --------------------------------------------------------------------------- brief 015, 36
def test_base_settings_hold_no_env_credential_code():
    text = _text(settings.BASE_DIR / "config" / "settings" / "base.py")
    gone = [
        "ZoomCredentials",
        OLD_LIST + "_PARTS",
        OLD_LIST + "_OPTIONAL_PARTS",
        "zoom_credential_env_prefix",
        "read_zoom_credentials",
        OLD_LIST + "_SETS",
        OLD_PREFIX + "_SECRETS",
        OLD_LIST + "_MISSING",
        "dataclass",
    ]
    assert [name for name in gone if name in text] == []


def test_no_settings_attribute_names_zoom_credentials():
    names = [name for name in dir(settings) if any(n in name for n in NEEDLES)]
    assert names == []


def test_no_zoom_credential_variable_is_named_anywhere_on_the_platform():
    """Criterion 36's scan: apps/, config/, docker/, compose files, Dockerfile, .env.example."""
    offenders = []
    for path in _scanned_files():
        try:
            lines = _text(path).splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, 1):
            if any(needle in line for needle in NEEDLES):
                offenders.append(f"{path.relative_to(settings.BASE_DIR)}:{number}")
    assert offenders == []


def test_encryption_keys_comment_covers_connection_secrets_and_backups():
    path = settings.BASE_DIR / "config" / "settings" / "base.py"
    comment = _comment_above(path, "HOST_KEY_ENCRYPTION_KEYS = ")
    assert "Zoom connection" in comment
    assert "backup" in comment
    assert "rotate_encryption_keys" in comment


# --------------------------------------------------------------------------- brief 015, 37
def test_the_credentials_example_file_is_gone():
    assert not (settings.BASE_DIR / (CREDENTIALS_FILE + ".example")).exists()


def test_compose_loads_no_credentials_file():
    text = _text(settings.BASE_DIR / "compose.yaml")
    assert "env_file" not in text
    assert "zoom-" + "credentials" not in text


@pytest.mark.parametrize("name", [".gitignore", ".dockerignore"])
def test_ignore_files_keep_the_retired_credentials_line(name):
    lines = [line.strip() for line in _text(settings.BASE_DIR / name).splitlines()]
    assert CREDENTIALS_FILE in lines
    assert lines[lines.index(CREDENTIALS_FILE) - 1] == RETIRED_COMMENT


# --------------------------------------------------------------------------- brief 015, 38
def test_env_example_lists_the_zoom_provider():
    text = _text(settings.BASE_DIR / ".env.example")
    assert re.search(r"^#\s+zoom\s+-", text, re.MULTILINE)
    comment = _comment_above(settings.BASE_DIR / ".env.example", "ZOOM_PROVIDER=")
    assert "Zoom connections page" in comment
    assert "zoom-" + "credentials" not in text


def test_env_example_says_what_the_encryption_keys_cover():
    comment = _comment_above(settings.BASE_DIR / ".env.example", "HOST_KEY_ENCRYPTION_KEYS=")
    assert "host keys" in comment
    assert "Zoom connection" in comment
    assert "apart from database backups" in comment
    assert "rotate_encryption_keys" in comment


def test_compose_comment_on_the_encryption_keys():
    comment = _comment_above(settings.BASE_DIR / "compose.yaml", "HOST_KEY_ENCRYPTION_KEYS:")
    assert comment.count("#") == 1, "one line"
    assert "Zoom connection secrets" in comment
    assert "apart from the DB" in comment


# --------------------------------------------------------------------------- prod refusal
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


# --------------------------------------------------------------------------- logging
def test_urllib3_logs_nothing_below_warning():
    assert settings.LOGGING["loggers"]["urllib3"]["level"] == "WARNING"
    assert logging.getLogger("urllib3").getEffectiveLevel() == logging.WARNING


def test_sql_is_never_logged_with_its_parameters():
    """Brief 015, D15: SQL parameters now carry Zoom connection IDs and ciphertexts."""
    assert settings.LOGGING["loggers"]["django.db.backends"]["level"] == "INFO"
    assert logging.getLogger("django.db.backends").getEffectiveLevel() >= logging.INFO


# --------------------------------------------------------------------------- brief 006, 45
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
