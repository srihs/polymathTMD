# Polymath TMD — Technology Management Desk

A Django web app with server-rendered HTML templates and vanilla JavaScript. There is no front-end build step.

## Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.13 |
| Framework | Django 5.2 LTS |
| Templates | Django templates (HTML5), in `templates/` |
| Front end | Plain CSS (`static/css/style.css`) and vanilla JS (`static/js/theme-init.js`, `static/js/app.js`), ported from the client-approved `design/f-desk/` prototype |
| Fonts | IBM Plex Sans, weights 300/400/500/600 (Google Fonts, SIL OFL 1.1) |
| Database | MySQL 8.4 LTS (utf8mb4), driver `mysqlclient` |
| Static files | WhiteNoise (compressed, cache-busted in production) |
| Config | `django-environ`, reading `.env` |
| Auth | Django auth with a custom `accounts.User` model |
| App server | Gunicorn |
| Containers | Docker (multi-stage `Dockerfile`) and Docker Compose |
| Tests / lint | pytest + pytest-django, Ruff |

## Third-party notices

- **IBM Plex Sans**, loaded from Google Fonts — SIL Open Font License 1.1.
- **Feather icons** (https://feathericons.com), inlined as one SVG sprite in `templates/partials/icons.html` — MIT licence, © 2013–2017 Cole Bemis.

## Layout

```
config/            project settings (base / dev / test / prod), urls, wsgi, asgi
apps/accounts/     custom User model, login and logout
apps/core/         home page, /healthz/ middleware, site context
templates/         base.html, registration/login.html, partials/
static/            css/, js/, img/
docker/            entrypoint.sh, mysql/init/ (first-run MySQL setup)
design/            reference HTML prototypes (not served, not in the image)
requirements/      base.txt, dev.txt, prod.txt
Dockerfile         dev and prod image targets
compose.yaml       web (gunicorn) + db (MySQL)
compose.dev.yaml   overlay: runserver with live reload, source mounted
```

## Setting up `.env`

```powershell
copy .env.example .env
```

Fill in `SECRET_KEY`, `MYSQL_PASSWORD` and `MYSQL_ROOT_PASSWORD`. You can generate each value with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Don't use `$` in any value. Docker Compose and django-environ both read it as the start of a variable.

Django and the MySQL container both read the `MYSQL_*` values, so you only set the password in one place. `DB_HOST` and `DB_PORT` tell Django where MySQL is when it runs outside Docker. Inside Docker, compose sets `DB_HOST=db`.

## Running with Docker

**Development** (live reload; your code is mounted into the container):

```powershell
docker compose -f compose.yaml -f compose.dev.yaml up --build
docker compose -f compose.yaml -f compose.dev.yaml exec web python manage.py createsuperuser
```

**Production-like** (Gunicorn, hashed static files, security settings on):

```powershell
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
```

Open http://localhost:8010/. The port comes from `WEB_PORT` in `.env`; the default is 8000.

Migrations run when the web container starts (`DJANGO_MIGRATE=1`). Database data is kept in the `mysqldata` volume, and uploads in the `media` volume.

The scripts in `docker/mysql/init/` run only when the `mysqldata` volume is first created. They let the app user create the `test_polymath_tmd` database that the tests use. If you change `MYSQL_DATABASE` or `MYSQL_USER` later, run `docker compose down -v` to recreate the volume. This deletes the data.

Useful commands (with the dev overlay, add `-f compose.yaml -f compose.dev.yaml` after `docker compose`):

```powershell
docker compose logs -f web                              # follow logs
docker compose exec web python manage.py makemigrations  # new migrations (dev overlay)
docker compose exec web pytest                           # tests (dev overlay)
docker compose exec db mysql -u polymath -p polymath_tmd  # database shell
docker compose down                                      # stop (data kept)
docker compose down -v                                   # stop and DELETE database and media volumes
```

## Running without Docker (Windows PowerShell)

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements\dev.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Django still needs MySQL. Start just the database with `docker compose -f compose.yaml -f compose.dev.yaml up -d db` (published on `127.0.0.1:3306`), or point `DB_HOST`/`DB_PORT` at another MySQL server. The MySQL user needs rights on `test_<MYSQL_DATABASE>` for `pytest`.

```powershell
pytest                 # run tests
ruff check .           # lint
ruff format .          # format
```

## Deploying the image

The `prod` target (the default for `docker build .`) runs as a non-root user and includes the collected static files. It also has a `HEALTHCHECK` on `/healthz/`.

Set these environment variables on the host:

| Variable | Notes |
|---|---|
| `SECRET_KEY` | Required |
| `ALLOWED_HOSTS` | e.g. `tmd.example.com` |
| `CSRF_TRUSTED_ORIGINS` | e.g. `https://tmd.example.com` |
| `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD` | Database name and login |
| `DB_HOST`, `DB_PORT` | MySQL server address (default `127.0.0.1:3306`) |
| `USE_HTTPS` | Keep `True` behind TLS. Your proxy must send `X-Forwarded-Proto`. Use `False` only for local runs without TLS. |
| `WEB_CONCURRENCY` | Number of Gunicorn workers (default 3) |

If you run more than one web replica, set `DJANGO_MIGRATE=0` on the replicas. Then run `python manage.py migrate` once as a separate job.
