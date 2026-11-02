"""Settings shared by every environment."""

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
# meeting through the Zoom API and checks Zoom for clashes; each account needs a Zoom connection
# saved in the database on the app's Zoom connections page, brief 015: there are no Zoom
# credential variables), "manual" (IT pastes the link it made in Zoom; the fallback) or "fake"
# (dev/tests only; links on the .invalid TLD). The zoom app's system checks reject any other
# value, and reject "fake" under check --deploy; prod.py refuses to start with "fake".
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
# Fernet keys that encrypt, at rest, Zoom host keys (brief 005, D17) and, from brief 015, each
# Zoom connection's Client Secret and webhook Secret Token, comma-separated. The first key
# encrypts; every key decrypts, which is how rotation works (manage.py rotate_encryption_keys
# re-encrypts every stored secret with the first key). Kept apart from SECRET_KEY so rotating
# SECRET_KEY never makes stored secrets unreadable. Secret: never log or render.
# Back these keys up apart from the database: a database backup plus these keys gives access
# to Zoom (create, change and delete meetings on every connected account), not only to host
# keys, and losing every key means retyping every secret (brief 015, D16, R1).
# No default: the zoom app's check zoom.E003 reports it when empty or invalid.
HOST_KEY_ENCRYPTION_KEYS = env.list("HOST_KEY_ENCRYPTION_KEYS", default=[])
# The IT desk's phone number, shown as a tap-to-call link on the public "start this class"
# page so a teacher whose link fails can reach someone (brief 011, criterion 47). Not a secret.
# Empty means the page says "contact the IT desk" with no number. A non-empty value must be
# a number the zoom app's phone rules can read (check zoom.E006), e.g. 011 234 5678.
IT_DESK_PHONE = env("IT_DESK_PHONE", default="")

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
        # still hold a working /zoom/start/<token>/ link (brief 011, review round 2), a
        # Zoom webhook body, which carries join links (brief 013, review round 1, N1), and
        # Zoom connection values: a database error's frame locals can hold an Account ID, a
        # Client ID or a stored secret's ciphertext (brief 015, review round 1, N5; D21).
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
        # At DEBUG, Django logs every SQL statement with its parameters, and from brief 015
        # those carry Zoom connection values (Account IDs, Client IDs and secret ciphertexts).
        # Pinned so LOG_LEVEL=DEBUG or a future logger tweak never writes them (D15).
        "django.db.backends": {"level": "INFO"},
    },
}
