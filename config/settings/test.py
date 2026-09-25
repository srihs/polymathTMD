"""Settings for the test suite (pytest).

Tests run against MySQL: Django creates and drops a ``test_<MYSQL_DATABASE>`` database.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-only-not-secret")
# A fixed, obviously fake Fernet key (32 bytes of "test-only-fernet-key-not-secret!",
# URL-safe base64) so tests need no .env value. It never protects real host keys.
os.environ.setdefault("HOST_KEY_ENCRYPTION_KEYS", "dGVzdC1vbmx5LWZlcm5ldC1rZXktbm90LXNlY3JldCE=")

from .base import *  # noqa: E402, F403

DEBUG = False
ALLOWED_HOSTS = ["testserver"]

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
# Tests always use the fake Zoom provider, whatever .env or the container says.
ZOOM_PROVIDER = "fake"
# Tests assert the default (REMOTE_ADDR only) unless they override it.
TRUSTED_PROXY_COUNT = 0
WHITENOISE_AUTOREFRESH = True  # don't expect a collected staticfiles/ dir
