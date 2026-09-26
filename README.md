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
apps/accounts/     custom User model, login/logout, Staff and access screens, password change
apps/core/         home page, /healthz/ middleware, site context, shared view mixins
apps/zoom/         Zoom link requests: public form, IT queue, conflict-free booking
templates/         base.html, public_base.html, registration/, partials/, accounts/, zoom/
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

Fill in `SECRET_KEY`, `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD` and `HOST_KEY_ENCRYPTION_KEYS` (required — it encrypts Zoom host keys at rest; see "Zoom link requests" below). Generate `SECRET_KEY` and the MySQL passwords with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

and `HOST_KEY_ENCRYPTION_KEYS` with:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Back it up somewhere safe: losing every key means re-typing every host account's key on the Zoom
accounts page.

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

`createsuperuser` is only for creating the very first account on a new install. There is no
Django admin — add everyone else on the **Staff and access** page once you've signed in; see
"Staff and access" below.

Open http://localhost:8010/. The port comes from `WEB_PORT` in `.env`; the default is 8000.

The prod image refuses to start with `ZOOM_PROVIDER=fake` (a typical dev `.env` setting). To run
the prod stack locally, override the provider rather than editing `.env`:

```powershell
$env:ZOOM_PROVIDER = "manual"; docker compose up -d --build
```

Set it to `zoom` instead once you want to test against real Zoom credentials. Put those in
`zoom-credentials.env`, next to `.env`, first — see "Connecting an account to Zoom" below. That
file is git-ignored and never baked into the image; `web` loads it through `env_file`, whether or
not the file exists.

**Security note:** builds made before 2026-09-25 could copy `Dashboard 2A.xlsx` (which holds Zoom
host keys) into the image, because `.dockerignore` didn't exclude it. Rebuild any image built
before that date, and rotate any Zoom host keys it could have reached. The spreadsheet itself stays
on disk — it's git-ignored, excluded from the Docker build context, and never read by the app (task
006); see "Zoom link requests" below.

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

Re-run `pip install -r requirements\dev.txt` after pulling changes that add a dependency (for
example `cryptography`, added to encrypt Zoom host keys at rest) — an existing `.venv` doesn't pick
it up on its own.

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
| `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` | SMTP settings. Required, or prod mail (including Zoom link emails) never leaves the container |
| `ZOOM_PROVIDER` | `zoom` (production, once every paid account is connected) or `manual` (a fallback that can't see Zoom directly — `manage.py check --deploy` warns with `zoom.W001`). `fake` is dev only — the prod image refuses to start with it |
| `TRUSTED_PROXY_COUNT` | Reverse proxies in front of the app that add to `X-Forwarded-For`. `0` for a direct connection; `1` behind the TLS proxy |
| `HOST_KEY_ENCRYPTION_KEYS` | Required. Comma-separated Fernet key(s) that encrypt Zoom host keys at rest — see "Zoom link requests" below |

Zoom credentials (`ZOOM_CREDENTIAL_SETS` and the three `ZOOM_S2S_<NAME>_*` variables per account)
don't go in this table or in `compose.yaml`'s `web.environment` — they live in
`zoom-credentials.env`, git-ignored and loaded through `env_file`. See "Connecting an account to
Zoom" above.

If you run more than one web replica, set `DJANGO_MIGRATE=0` on the replicas. Then run `python manage.py migrate` once as a separate job.

## Staff and access

There is no Django admin. Everyone who can sign in, and what they're allowed to do, is managed
on the **Staff and access** page (`/accounts/staff/`), reached from the sidebar's
**Administration** group.

**Who can open it.** Two kinds of person:

- a **superuser** (`is_superuser=True`), created with `createsuperuser` or given full access by
  another superuser;
- anyone holding the **Staff managers** role, which carries Django's built-in `view_user`,
  `add_user` and `change_user` permissions.

**Roles are fixed.** `IT desk` and `Staff managers` are the two roles today, each created by a
migration with a fixed set of permissions. There's no screen for creating a role or changing what
one allows — a new role, if one is ever needed, arrives with the brief that needs it.

**"Only roles they hold."** A Staff manager who isn't a superuser can only give or take away a
role whose rights they already have themselves. In practice: **to let someone add people to the
`IT desk` role, the person doing the adding must be in `IT desk` themselves.** The same limit
applies to changing someone's details or resetting their password — a Staff manager can only
manage a person whose rights are a subset of their own, and never another Staff manager, a
superuser, or themselves (they can't change their own roles at all, so nobody can lock themselves
out).

Giving someone the **Staff managers** role is one-way for a non-superuser: once given, that
person is a Staff manager too, so the person who gave it can no longer open their record to take
it back. **Only a superuser can remove the Staff managers role.** Give it with care. A superuser
can give or remove any role, including their own, and can manage anyone, including other
superusers.

**Adding a person.** On **Staff and access**, use **Add a person**. Fill in their name, username
and work email, tick the roles they need, and type a **starting password** — Django's usual
password rules apply. Give the username and starting password to the person yourself (in person
or by phone); the system never emails it. They can change it afterwards from their own user menu.

**Switching someone off.** Nobody is deleted — people who leave are switched off instead, so the
record of what they approved or changed stays intact. Untick **Can sign in** on their **Change**
page to stop them signing in immediately, including any session they already have open; tick it
again to let them back in.

**Setting a new password for someone.** Open their **Change** page and choose **Set a new
password**. This signs them out everywhere immediately — give them the new password yourself, not
by email.

**Changing your own password.** Every signed-in user has **Change your password** in their user
menu (top right). This keeps you signed in; only your other sessions elsewhere are asked for the
new password.

**If you open a page you're not allowed to,** you'll see a plain "You can't open this page"
message instead of Django's bare 403, with a link back to Home and, if you're signed in, the
sidebar showing only what you can actually open.

## Zoom link requests

Anyone can ask for a Zoom link for a class at `/zoom/request/` — no sign-in needed. Share that URL
with staff who book classes. The IT queue that reviews requests is at `/zoom/requests/`, for
signed-in members of the `IT desk` group only.

**Giving IT staff access:** on the **Staff and access** page (see below), tick the `IT desk` role
for the person, or add them with it ticked. `IT desk` is created by a migration; it carries the
"Can approve or reject Zoom link requests" permission plus the three host-account permissions
below. They don't need full access. There is no Django admin any more; see "Staff and access" for
who can do this and what else it covers.

**Host accounts:** the sidebar's **Zoom links → Zoom accounts** item opens an in-app page
(`/zoom/accounts/`) for listing, adding and changing Zoom host accounts — there is no Django admin
for them any more. Anyone in the `IT desk` group can use it: the group's migration grants Django's
built-in `view_hostaccount`, `add_hostaccount` and `change_hostaccount` permissions, so no separate
role is needed. Mark the two free, 40-minute accounts `Paid account` unticked so the system never
books them; every other account is a paid Zoom subscription and gets offered to requesters.

A host key is **write-only**: type it once, on the account's `Change {name}` page, and it is never
shown again to anyone, on any screen — the list and the change page only ever say whether a key is
saved, and when and by whom it was last set. There's no way to delete an account. An account can't
be taken out of use, or marked as not paid, while it still has an upcoming (not-yet-finished)
approved class; the change page explains how many classes are booked and when the last one
finishes, so IT knows when the change will be possible.

**Timetable:** the sidebar's **Zoom links → Timetable** item (`/zoom/timetable/`) opens a
read-only month view for anyone in the `IT desk` group — the same access as the queue and the Zoom
accounts page. It shows one calendar month as a wall calendar, weeks running Monday to Sunday. Each
day's box lists that day's classes with their start time, class name and Zoom account, up to three,
then a `+N more` link that opens a **day page** listing every class that day; the day number also
opens that page. A class still waiting for IT approval has no account yet, so it's marked
`Waiting for IT` instead. An account filter narrows the month (and day) to one Zoom account —
filtering hides waiting classes, since they don't have an account to filter by — and `Previous
month` / `Next month` links move a month at a time, both keeping the filter. On a phone the same
page becomes a day-by-day list showing only the days that have classes. An approved request's
detail page carries a `See it on the timetable` link straight to its month and account, and the
Zoom accounts list has a `Timetable` link on every row. Nothing is booked, moved or cancelled from
the timetable — it's read-only.

### Zoom providers

`ZOOM_PROVIDER` picks how the app makes and checks meetings:

| Value | When to use | What it does |
|---|---|---|
| `zoom` | Production, once every paid account is connected (see below) | The app calls the real Zoom API. Before it offers or books an account it asks Zoom for that account's existing meetings, so it also sees bookings made directly in Zoom. On approval it creates the real meeting |
| `manual` | A fallback, and the default before `zoom` is switched on | The app can't see Zoom at all. IT creates the meeting in Zoom by hand and pastes its details into the approve form (below). `manage.py check --deploy` warns with `zoom.W001`, because this can double-book an account |
| `fake` | Development and tests only | Makes links that don't work. The prod image refuses to start with it (`zoom.E001`) |

### Connecting an account to Zoom

Each paid Zoom account needs its own Server-to-Server OAuth app, set up once by whoever
administers that Zoom subscription. **The scope names below are unconfirmed until the owner's live
check (task 006, criterion 48, step 8) — check them against the Marketplace before relying on this
list.**

1. Sign in at marketplace.zoom.us as the owner or an admin of that Zoom subscription. An admin's
   role needs the "Server-to-Server OAuth app" permission, under User Management → Roles.
2. **Develop → Build App → Server-to-Server OAuth App → Create.** Name it `Polymath TMD`.
3. On **App Credentials**, copy the **Account ID**, **Client ID** and **Client Secret**.
4. Fill in the required company and developer contact fields under **Information**.
5. Under **Scopes**, add exactly these, and nothing else *(unconfirmed, see above)*:
   - `meeting:write:meeting:admin` — create a meeting
   - `meeting:read:list_meetings:admin` — list a user's meetings
   - `meeting:read:meeting:admin` — view a meeting, for recurring occurrences
   - `meeting:delete:meeting:admin` — delete a meeting, for rollback and cancelling
   - `user:read:user:admin` — view a user, for the connection check

   If the app only offers classic scopes, use `meeting:write:admin`, `meeting:read:admin` and
   `user:read:admin` instead.
6. **Activate** the app.
7. In that subscription's Zoom settings, turn on **cloud recording** (requesters can ask for it),
   and set the account user's **host key** in their Zoom profile — type it on the Zoom accounts
   page as before. **Also check "Allow participants to join before host" and "Waiting room"**
   (Settings → Meeting): the app leaves both exactly as the account has them, and never turns
   either on or off. A teacher who has only the host key has to be let into the meeting before they
   can claim host, so join before host should be on and the waiting room off, unless someone who
   can admit them is always there.
8. On the server, copy `zoom-credentials.env.example` to `zoom-credentials.env`, next to `.env`.
   It's git-ignored and never baked into the image. Add the account's slug to
   `ZOOM_CREDENTIAL_SETS` (for example `zoom-01`), then set `ZOOM_S2S_ZOOM_01_ACCOUNT_ID`,
   `ZOOM_S2S_ZOOM_01_CLIENT_ID` and `ZOOM_S2S_ZOOM_01_CLIENT_SECRET`.
9. Recreate `web` (`docker compose up -d`) so it reads the file.
10. On the Zoom accounts page, set that account's **Zoom connection name** to the slug, save, then
    press **Check connection**.
11. Once every paid account works: run `python manage.py check_zoom_connections` and
    `python manage.py check --database default`, then set `ZOOM_PROVIDER=zoom` in `.env` and
    recreate `web`.

**Rotating a secret:** regenerate it on the app's App Credentials page in Zoom, update
`zoom-credentials.env`, recreate `web`, then press **Check connection** again. The two free
accounts need no app — they're never booked.

**Checking connections from the command line:** `python manage.py check_zoom_connections` checks
every active paid account at once (handy after rotating a secret). It prints one line per account
(`{label}: works` or `{label}: {problem}`) and exits with a non-zero status if any account fails.
No line ever prints a secret, a token or an account ID.

**If Zoom can't be reached, the app fails closed.** It never guesses whether an account is free. An
account it couldn't check shows as "Couldn't check with Zoom" or "Not connected to Zoom" on the
request detail page and isn't offered; if the check fails partway through approving, nothing is
booked, and IT sees a plain message saying what happened and what to try next.

**Rules to follow:**

- **Always schedule classes in Zoom with a date and time.** The app can only see dated, scheduled
  meetings — never an instant meeting, a no-fixed-time recurring meeting, or one on a Personal
  Meeting ID (PMI). A class booked directly in Zoom on one of those won't stop the app double-booking it.
- **Check each account's own "join before host" and "waiting room" settings** (Settings → Meeting
  in Zoom) — the app never changes either; see setup step 7 above.
- **A meeting made directly in Zoom now counts as busy.** With `ZOOM_PROVIDER=zoom`, the app asks
  Zoom for every scheduled meeting on an account before offering or booking it, not only the
  bookings it made itself.

**Known limits:**

- Instant meetings, no-fixed-time recurring meetings and PMI meetings aren't seen as busy — always
  schedule dated meetings.
- Whether a teacher with only the host key can get into a meeting depends on that account's own
  "join before host" and "waiting room" settings; the app leaves both alone.
- Changes made directly in Zoom to a meeting the app created — moving it, or deleting it or one of
  its classes — aren't seen by the app. It keeps treating the class as booked, so an account can
  look busy when it isn't. That errs on the side of caution. Cancelling a booking from the app
  (task 011) is the supported way to free it.
- There's a gap of a second or two between the app checking Zoom and creating the meeting: a
  meeting typed into Zoom by hand in that window is accepted.
- An account's recurring series are read one at a time. An account with many of them (20 or more)
  can miss the availability check's 8-second deadline and show "Couldn't check with Zoom" — safe,
  but can be annoying; approving itself has no such deadline.
- The timetable (`/zoom/timetable/`) shows only bookings the app made; meetings that exist only in
  Zoom don't appear there.
- The `recurrence.end_times` cap of 60 classes per series is unconfirmed against Zoom's current API
  docs until the owner's live check (task 006, criterion 48, step 9). If Zoom's limit is now lower,
  that's a blocker to report, not something to route around silently.

**Manual mode, the fallback:** with `ZOOM_PROVIDER=manual`, the app can't see meetings in Zoom at
all. When IT approves a request, they first create the meeting in Zoom on the account the system
assigned, turn on cloud recording by hand if the requester asked for it, then paste the join link,
meeting ID and passcode into the approve form. The system then emails the requester the link
together with that account's host key, so the teacher can claim host control.
`manage.py check --deploy` warns with `zoom.W001` whenever `manual` is set, because it can't see
meetings made directly in Zoom and so can double-book them.

**Go-live gate:** don't point real requesters at the public form in production yet, until both of
these are done:

1. `ZOOM_PROVIDER=zoom` is running in production, with every active paid Zoom account connected —
   `python manage.py check_zoom_connections` passes, and `python manage.py check --database default`
   reports no `zoom.E004`.
2. A later brief (011), "Cancel this booking", adds a way to cancel a wrong or unneeded approval.
   Until then a mistaken approval can't be undone in the app — including, from brief 008 onwards,
   that an account with a booking can't be taken out of use until that class is over.

**If a host key leaks** (a forwarded email, a shared mailbox, a compromised account): change it in
Zoom first, then re-type it on that account's Zoom accounts page (`Change {name}` → New host key).
The old key stops working the moment you change it in Zoom.

**Rotating `HOST_KEY_ENCRYPTION_KEYS`:** put a new key first in the comma-separated list, restart,
run `python manage.py rotate_host_keys` (re-encrypts every stored key with the new one and prints
only a count), then remove the old key and restart.
