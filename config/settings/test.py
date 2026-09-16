"""Settings for the test suite (pytest).

Tests run against MySQL: Django creates and drops a ``test_<MYSQL_DATABASE>`` database.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-only-not-secret")

from .base import *  # noqa: E402, F403

DEBUG = False
ALLOWED_HOSTS = ["testserver"]

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
WHITENOISE_AUTOREFRESH = True  # don't expect a collected staticfiles/ dir
