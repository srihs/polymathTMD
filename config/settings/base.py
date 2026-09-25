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
# Which meeting provider makes the links (brief 005, D4): "manual" (IT pastes the link it
# made in Zoom) or "fake" (dev/tests only; links on the .invalid TLD). The zoom app's
# system checks reject any other value, and reject "fake" under check --deploy.
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

# --------------------------------------------------------------------------- Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "{asctime} {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
