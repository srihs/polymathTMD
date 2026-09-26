"""Platform tests for brief 011's IT_DESK_PHONE setting (owned by tmd-devops).

They pin the plumbing criterion 47 relies on: the value is read from the environment in one
place only (config/settings/base.py, like every other env value), defaults to empty, and is
passed through by both the Docker stack and the documented .env template. Whether a value is a
readable phone number (zoom.E006) and how it's shown belong to the zoom app and are tested in
apps/zoom/tests/.
"""

import re

from django.conf import settings

BASE_SETTINGS = settings.BASE_DIR / "config" / "settings" / "base.py"


def test_it_desk_phone_is_read_in_base_with_an_empty_default():
    text = BASE_SETTINGS.read_text(encoding="utf-8")
    assert re.search(r'^IT_DESK_PHONE = env\("IT_DESK_PHONE", default=""\)$', text, re.MULTILINE)
    assert isinstance(settings.IT_DESK_PHONE, str)


def test_it_desk_phone_env_is_read_only_in_base_settings():
    """Criterion 47's source scan: no other module reads IT_DESK_PHONE from the environment."""
    env_read = re.compile(r"os\.environ|getenv\(|\benv(\.\w+)?\(")
    offenders = []
    roots = [settings.BASE_DIR / "apps", settings.BASE_DIR / "config"]
    for path in [p for root in roots for p in root.rglob("*.py")]:
        if path == BASE_SETTINGS:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "IT_DESK_PHONE" in line and env_read.search(line):
                offenders.append(f"{path.relative_to(settings.BASE_DIR)}:{number}")
    assert not offenders, offenders


def test_compose_passes_it_desk_phone_to_web_with_an_empty_default():
    # Compose doesn't hand .env to the container wholesale, so a missing line here would
    # silently leave the start page without a number in Docker.
    text = (settings.BASE_DIR / "compose.yaml").read_text(encoding="utf-8")
    assert re.search(r"^\s+IT_DESK_PHONE: \$\{IT_DESK_PHONE:-\}\s*$", text, re.MULTILINE)


def test_env_example_documents_it_desk_phone_without_a_value():
    lines = (settings.BASE_DIR / ".env.example").read_text(encoding="utf-8").splitlines()
    assert "IT_DESK_PHONE=" in lines
    comment = lines[lines.index("IT_DESK_PHONE=") - 1]
    assert comment.startswith("# ")
    assert "011 234 5678" in "\n".join(lines)
