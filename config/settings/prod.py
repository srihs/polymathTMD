"""Production settings.

Everything sensitive comes from the environment, but it is read in base.py (the only
place ``env(...)`` is called); this module only turns those values into production policy.
"""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import ALLOWED_HOSTS, USE_HTTPS, ZOOM_PROVIDER

DEBUG = False

# base.py defaults ALLOWED_HOSTS to an empty list. In production that would answer every
# request with 400 while /healthz/ (which skips host validation) still reports healthy, so
# fail at start-up instead.
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("Set ALLOWED_HOSTS for production.")

# The fake provider emails links on the .invalid TLD that can't reach a meeting. The zoom.E001
# deploy check reports it, but nothing runs check --deploy at start-up, so refuse to start.
if ZOOM_PROVIDER == "fake":
    raise ImproperlyConfigured(
        "The fake Zoom provider can't run in production. Set ZOOM_PROVIDER=zoom "
        "(or manual, the fallback)."
    )

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# HTTPS & cookies, all driven by the one USE_HTTPS flag (read in base.py).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = USE_HTTPS
SESSION_COOKIE_SECURE = USE_HTTPS
CSRF_COOKIE_SECURE = USE_HTTPS
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Email settings (EMAIL_*, DEFAULT_FROM_EMAIL) are read in base.py; the default backend there
# is SMTP, which is what production uses.
