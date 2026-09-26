# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.13

# ------------------------------------------------------------------ base (runtime)
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

# libmariadb3 is the MySQL client library mysqlclient links against at runtime.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libmariadb3 \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 1000 app \
 && useradd --system --uid 1000 --gid app --home-dir /app --no-create-home app

WORKDIR /app

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
# Strip CRLF in case the script was checked out on Windows.
RUN sed -i 's/\r$//' /usr/local/bin/entrypoint.sh && chmod 755 /usr/local/bin/entrypoint.sh

ENTRYPOINT ["entrypoint.sh"]
EXPOSE 8000

# ------------------------------------------------------------------ build (compilers stay here)
FROM base AS build

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential pkg-config default-libmysqlclient-dev \
 && rm -rf /var/lib/apt/lists/* \
 && python -m venv /opt/venv

COPY requirements/ requirements/

FROM build AS build-prod
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements/prod.txt

FROM build AS build-dev
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements/dev.txt

# ------------------------------------------------------------------ dev
# Used by compose.dev.yaml: source is bind-mounted, runserver reloads on change.
FROM base AS dev

COPY --from=build-dev /opt/venv /opt/venv
COPY --chown=app:app . .
RUN mkdir -p /app/media && chown app:app /app/media

USER app
ENV DJANGO_SETTINGS_MODULE=config.settings.dev
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ------------------------------------------------------------------ prod (default)
FROM base AS prod

COPY --from=build-prod /opt/venv /opt/venv
COPY --chown=app:app . .

# Static files are baked into the image; the dummy values only satisfy settings import
# (collectstatic never connects to the database).
RUN SECRET_KEY=collectstatic-only ALLOWED_HOSTS=localhost \
    MYSQL_DATABASE=build MYSQL_USER=build MYSQL_PASSWORD=build \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    python manage.py collectstatic --noinput \
 && mkdir -p /app/media && chown app:app /app/media

USER app
ENV DJANGO_SETTINGS_MODULE=config.settings.prod

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz/', timeout=4)"]

# Worker count comes from WEB_CONCURRENCY (read by gunicorn itself).
# The control socket goes in /tmp because /app is read-only for the app user.
# docker/gunicorn.conf.py only swaps in a logger that hides class start tokens
# (/zoom/start/<token>/ is a working host link) from the access log (brief 011).
CMD ["gunicorn", "config.wsgi:application", "--config", "docker/gunicorn.conf.py", \
     "--bind", "0.0.0.0:8000", \
     "--control-socket", "/tmp/gunicorn.ctl", \
     "--access-logfile", "-", "--error-logfile", "-"]
