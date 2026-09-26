"""Settings shared by every environment."""

from dataclasses import dataclass, field
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SITE_NAME = env("SITE_NAME", default="Polymath TMD")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])  # prod.py refuses to start if empty
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# HTTPS policy flag, applied only by prod.py (redirect + secure cookies). TLS ends at a proxy
# that sends X-Forwarded-Proto. Set it to False only for a local run of the prod image.
USE_HTTPS = env.bool("USE_HTTPS", default=True)
# HSTS is only ever sent on HTTPS responses, so reading it here doesn't affect plain-HTTP dev.
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)

# --------------------------------------------------------------------------- Apps
# django.contrib.admin is deliberately absent (task 010, D10): users and roles are managed on
# the in-app Staff and access screens, and an installed admin would be a back door around their
# guards. contrib.auth stays; those screens are built on its users, groups and permissions.
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
]
LOCAL_APPS = [
    "apps.accounts",
    "apps.core",
    "apps.zoom",
]
INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS

MIDDLEWARE = [
    "apps.core.middleware.HealthCheckMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site",
            ],
        },
    },
]

# --------------------------------------------------------------------------- Database
# MySQL. The MYSQL_* variables are the same ones the MySQL container is created with.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        # 127.0.0.1, not "localhost": mysqlclient treats localhost as a Unix socket.
        "HOST": env("DB_HOST", default="127.0.0.1"),
        "PORT": env.int("DB_PORT", default=3306),
        "NAME": env("MYSQL_DATABASE"),
        "USER": env("MYSQL_USER"),
        "PASSWORD": env("MYSQL_PASSWORD"),
        "ATOMIC_REQUESTS": True,
        "CONN_MAX_AGE": env.int("DB_CONN_MAX_AGE", default=60),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        "TEST": {"CHARSET": "utf8mb4", "COLLATION": "utf8mb4_0900_ai_ci"},
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------------- Auth
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:home"
LOGOUT_REDIRECT_URL = "accounts:login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --------------------------------------------------------------------------- i18n
LANGUAGE_CODE = "en"
TIME_ZONE = env("TIME_ZONE", default="Asia/Colombo")
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------------- Static & media
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# --------------------------------------------------------------------------- Email
# Read here (not in prod.py) so every environment can pick its backend and sender.
# dev.py and test.py override EMAIL_BACKEND with constants (console / locmem).
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
# Secret: never log or render it.
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="tmd@localhost")

# --------------------------------------------------------------------------- Zoom link requests
# Which meeting provider makes the links (brief 005, D4; brief 006): "zoom" (the app makes the
# meeting through the Zoom API and checks Zoom for clashes; needs the credential sets below),
# "manual" (IT pastes the link it made in Zoom; the fallback) or "fake" (dev/tests only; links
# on the .invalid TLD). The zoom app's system checks reject any other value, and reject "fake"
# under check --deploy; prod.py refuses to start with "fake".
ZOOM_PROVIDER = env("ZOOM_PROVIDER", default="manual")
# How long the "confirm your email" link works, and the hourly abuse limits. The limits are
# counted in the database, so they hold across Gunicorn workers without a shared cache (D8).
ZOOM_CONFIRM_LINK_HOURS = 24
ZOOM_REQUEST_LIMIT_PER_EMAIL_PER_HOUR = 5
ZOOM_REQUEST_LIMIT_PER_IP_PER_HOUR = 20
# Number of reverse proxies in front of the app that append to X-Forwarded-For. 0 means trust
# only REMOTE_ADDR. Behind the TLS proxy set it to 1, or every visitor shares the proxy's IP
# and the per-IP limit blocks everyone (D8). Never set it higher than the real proxy count:
# clients could then spoof their IP.
TRUSTED_PROXY_COUNT = env.int("TRUSTED_PROXY_COUNT", default=0)
# Fernet keys that encrypt Zoom host keys at rest (D17), comma-separated. The first key
# encrypts; every key decrypts, which is how rotation works. Kept apart from SECRET_KEY so
# rotating SECRET_KEY never makes stored host keys unreadable. Secret: never log or render.
# No default: the zoom app's check zoom.E003 reports it when empty or invalid.
HOST_KEY_ENCRYPTION_KEYS = env.list("HOST_KEY_ENCRYPTION_KEYS", default=[])
# The IT desk's phone number, shown as a tap-to-call link on the public "start this class"
# page so a teacher whose link fails can reach someone (brief 011, criterion 47). Not a secret.
# Empty means the page says "contact the IT desk" with no number. A non-empty value must be
# a number the zoom app's phone rules can read (check zoom.E006), e.g. 011 234 5678.
IT_DESK_PHONE = env("IT_DESK_PHONE", default="")


# --------------------------------------------------------------------------- Zoom connection
# One Zoom Server-to-Server OAuth app per paid subscription (brief 006, D2). Credentials come
# only from the environment: never the database, never the repo. In Docker they arrive through
# the git- and docker-ignored zoom-credentials.env (compose.yaml env_file), which is why none
# of these names is listed in web.environment: an entry there would override the file.
@dataclass(frozen=True)
class ZoomCredentials:
    """One credential set. Its repr names the slug only, so it can't leak into logs or reprs."""

    slug: str
    account_id: str = field(repr=False)
    client_id: str = field(repr=False)
    client_secret: str = field(repr=False)


# The three values each set needs, as (ZoomCredentials field, env var suffix).
ZOOM_CREDENTIAL_PARTS = (
    ("account_id", "ACCOUNT_ID"),
    ("client_id", "CLIENT_ID"),
    ("client_secret", "CLIENT_SECRET"),
)


def zoom_credential_env_prefix(slug):
    """The env var prefix for a set, the one naming rule: ``zoom-01`` gives ``ZOOM_S2S_ZOOM_01``.

    Slugs are lower-case with hyphens (the HostAccount.credential_set rule); env var names
    can't hold hyphens, so they become underscores.
    """
    return "ZOOM_S2S_" + slug.upper().replace("-", "_")


def read_zoom_credentials(environment, slugs):
    """Read each listed set's three variables, without judging them.

    Returns ``(secrets, missing)``: ``secrets`` maps each **complete** set's slug to its
    ZoomCredentials, and ``missing`` maps each incomplete slug to the missing variable
    **names** (never values). Nothing raises here: the zoom.E005 check reports empty lists,
    missing values, bad slugs and colliding names, so a broken set can't stop manage.py from
    printing a readable error.
    """
    secrets, missing = {}, {}
    for slug in slugs:
        prefix = zoom_credential_env_prefix(slug)
        values, absent = {}, []
        for attr, suffix in ZOOM_CREDENTIAL_PARTS:
            name = f"{prefix}_{suffix}"
            values[attr] = environment.str(name, default="").strip()
            if not values[attr]:
                absent.append(name)
        if absent:
            missing[slug] = absent
        else:
            secrets[slug] = ZoomCredentials(slug=slug, **values)
    return secrets, missing


# The slugs that have credentials, e.g. "zoom-01,zoom-02". An explicit list rather than a scan
# of every ZOOM_S2S_* variable, so E005 can name exactly what is missing (no hidden magic).
ZOOM_CREDENTIAL_SETS = [
    s.strip() for s in env.list("ZOOM_CREDENTIAL_SETS", default=[]) if s.strip()
]
# Secret. The name must keep "SECRET": Django's SafeExceptionReporterFilter masks any setting
# whose name matches it, so error pages and reports never show these values (criterion 3).
# ZOOM_CREDENTIAL_MISSING holds variable names only ({slug: [name, ...]}), for zoom.E005.
ZOOM_S2S_SECRETS, ZOOM_CREDENTIAL_MISSING = read_zoom_credentials(env, ZOOM_CREDENTIAL_SETS)

# --------------------------------------------------------------------------- Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "{asctime} {levelname} {name}: {message}", "style": "{"},
    },
    "filters": {
        # A class start link (/zoom/start/<token>/) is a working host link, and several Django
        # loggers write request paths. The filter goes on every handler, not on loggers,
        # because logger filters miss records that propagate from child loggers
        # (django.security.<Name>). See log_filters.py (brief 011, review round 1).
        "hide_start_token": {"()": "config.log_filters.HideStartTokenFilter"},
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "filters": ["hide_start_token"],
        },
        # Django's default, re-declared only to add the filter. It sends nothing while
        # ADMINS is unset. Don't set ADMINS without first revisiting the start-token
        # redaction of email bodies. The filter hides the subject, but the 500 email's
        # body (the request and the view's local variables, built by ExceptionReporter) can
        # still hold a working /zoom/start/<token>/ link (brief 011, review round 2).
        "mail_admins": {
            "class": "django.utils.log.AdminEmailHandler",
            "level": "ERROR",
            "filters": ["require_debug_false", "hide_start_token"],
        },
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
    "loggers": {
        # These replace Django's default handlers for these two loggers, which have no token
        # filter. Records now reach the filtered root console instead. A side effect: the
        # duplicate django.* lines that DEBUG runs used to print are gone.
        "django": {"handlers": ["mail_admins"], "level": "INFO"},
        # propagate must be explicit here, because dictConfig otherwise keeps Django's False.
        "django.server": {"handlers": [], "level": "INFO", "propagate": True},
        # urllib3 logs every request line at DEBUG, and Zoom's paths carry the host account's
        # email and meeting IDs. Pinned so LOG_LEVEL=DEBUG never writes them (brief 006, R3).
        "urllib3": {"level": "WARNING"},
    },
}
