# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Polymath TMD (Technology Management Desk) is a Django 5.2 LTS app for Polymath College. It uses server-rendered Django templates (HTML5), plain CSS and vanilla JS with no build step, MySQL 8.4, and runs in Docker. The product requirements are delivered in stages, so check `docs/` (when present) before assuming scope.

## Working rules (set by the project owner)

- **Every task goes through subagents.** The main session orchestrates: it delegates, passes results between agents and reports to the user. It does not write app code, templates or config itself, even for a one-line fix. See "Agent workflow" below.
- **A task isn't done until it's verified.** `tmd-test-verifier` runs the checks under "Verify a change" and reports the actual output. A FAIL sends the task back to the owning agent; it's never marked done.
- **Code is documented.** Every module, class and non-trivial function gets a docstring that explains *why*, not what. Every template starts with a `{# … #}` comment naming its purpose and the context variables it expects. Update `README.md` when commands, env vars or setup change.
- **MVT and the Django design philosophies** apply, as follows:
  - **Model:** business rules and data invariants live on models, managers and querysets (`clean()`, custom QuerySet methods), not in views or templates.
  - **View:** thin. Parse the request, call the model layer, choose a template, return a response. Prefer generic class-based views plus `ModelForm` when they fit. Views never build HTML strings.
  - **Template:** presentation only. No queries beyond iterating over context, and no business decisions. Shared markup goes in `templates/partials/` and is included with `{% include … with … only %}`.
  - **DRY:** every concept lives in one place:
    - Env config is read only in `config/settings/base.py`.
    - Design tokens are defined only in `:root` of `static/css/style.css`; use `var(--…)`, never raw hex.
    - URLs are only referenced by name (`{% url 'app:name' %}`, `reverse()`). Never hard-code paths.
    - Page chrome is only defined in `templates/base.html`.
  - **Loose coupling:**
    - Each app owns its `urls.py` with an `app_name` namespace.
    - Apps don't import each other's views.
    - Templates don't know URL shapes.
    - JS binds to `data-*` attributes, not CSS classes or DOM structure.
  - **No hidden magic:**
    - No signals for business logic; call the logic explicitly.
    - No new context processors for page-specific data.
    - No `import *` outside settings modules.
    - No monkey-patching.
  - **Less code:** use what Django ships (auth, admin, generic views, forms, messages) before writing your own. Every new dependency needs a reason in the task notes.

## Agent workflow

The agents are defined in `.claude/agents/`. Their definitions hold role details, file ownership and preloaded skills. Agents coordinate only through the task brief `docs/tasks/NNN-slug.md`, created from `docs/tasks/_template.md`, and each writes only its own section of it.

| Step | Agent | Produces |
|---|---|---|
| 1 | `tmd-planner` | Brief: scope, testable acceptance criteria, MVT plan, **context contract**, agent plan |
| 2 | `tmd-ui-designer` (any UI change) | Design section: layout, components, states, copy, accessibility |
| 3 | `tmd-devops` / `tmd-django-backend` / `tmd-frontend` | The change, plus Implementation notes. Backend and frontend may run in parallel once the context contract is fixed. |
| 4 | `tmd-test-verifier` | Verification: PASS/FAIL with evidence. FAIL: return to step 3 with the report. |
| 5 | `tmd-code-reviewer` (read-only) | Review: APPROVE / CHANGES REQUESTED. The main session writes it into the brief. Changes: return to step 3, then step 4 again. |
| 6 | `tmd-docs-writer` | README / CLAUDE.md / `docs/CHANGELOG.md` updates, and closes the brief |

Orchestration rules for the main session:

- **Delegate with a pointer.** Pass each agent the brief path plus the relevant output of the previous step, not a paraphrase.
- **Skip only the planner or designer steps, and only for:** dependency bumps, docs-only edits, or fixes to a failing check inside an open task. Verification (step 4) is never skipped.
- **Open questions go to the user.** If an agent returns open questions (Status `Blocked: questions`), ask the user before continuing.
- **Report outcomes as they are.** Tell the user the verifier's and reviewer's verdicts; don't soften them.
- **Commit only when the user asks.**

## Commands

The Docker dev overlay is the normal way to work. Add `-f compose.yaml -f compose.dev.yaml` to every `docker compose` command that targets the dev stack.

```powershell
# dev stack: runserver with live reload, source bind-mounted, MySQL published on 127.0.0.1:3306
docker compose -f compose.yaml -f compose.dev.yaml up -d --build
docker compose -f compose.yaml -f compose.dev.yaml exec web python manage.py makemigrations
docker compose -f compose.yaml -f compose.dev.yaml exec web python manage.py createsuperuser

# production-like stack (gunicorn, prod settings, hashed static files)
docker compose up -d --build
```

The app is served on `WEB_PORT` from `.env`. On this machine that's **8010**, because host port 8000 belongs to another project's container that must not be stopped.

Tests and lint run inside the dev container, or on the host from `.venv` as long as the dev stack's MySQL is up:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml exec web pytest                       # all tests
docker compose -f compose.yaml -f compose.dev.yaml exec web pytest apps/accounts/tests.py::test_login_with_valid_details_goes_home
.venv\Scripts\pytest apps/core/tests.py -k healthz                                        # host, single test
.venv\Scripts\pytest --create-db                                                           # after model/migration changes
.venv\Scripts\ruff check . ; .venv\Scripts\ruff format --check .
```

### Verify a change

Run all of these. Every one must pass before a task counts as done:

1. `ruff check .` and `ruff format --check .`
2. `pytest --create-db` (inside the dev container)
3. `python manage.py makemigrations --check --dry-run` (no missing migrations)
4. `python manage.py check`. When settings change, also run `docker compose exec -e USE_HTTPS=True web python manage.py check --deploy` on the prod stack. The local `.env` has `USE_HTTPS=False`, which causes irrelevant SSL and cookie warnings. `security.W021` (HSTS preload) is an accepted warning; any other warning fails the check.
5. For UI or HTTP changes, rebuild the prod stack (`docker compose up -d --build`), wait for `web` to be `healthy`, then exercise the affected pages over HTTP on `WEB_PORT`. The prod image catches failures the dev server hides; see "Static files" below.

## Architecture

- **`config/`** holds the project package.
  - **Settings:** split into `base` (everything shared, and the only place `env(...)` is read), `dev`, `test` and `prod`.
  - **Settings selection:**
    - `manage.py` defaults to `dev`.
    - `wsgi`/`asgi` and the prod image default to `prod`.
    - pytest forces `test` with `--ds` in `pyproject.toml`. That overrides the container's `DJANGO_SETTINGS_MODULE`; don't move it back to an ini key.
- **`apps/<name>/`** holds the local apps.
  - **Registration:** each has `AppConfig.name = "apps.<name>"` and `label = "<name>"`. Add new apps to `LOCAL_APPS` in `base.py`.
  - **Current apps:**
    - `accounts`: the custom `User` model (`AUTH_USER_MODEL = "accounts.User"`) plus login and logout wired to Django's auth views. Logout is POST-only.
    - `core`: the home page, the `tmd_site_name` context processor, and `HealthCheckMiddleware`. The key is prefixed because Django's auth views (`LoginView` and friends) inject their own `site_name` from `get_current_site()`, which would silently override an unprefixed key of the same name.
- **`/healthz/`** isn't a URL route. `apps.core.middleware.HealthCheckMiddleware` sits *first* in `MIDDLEWARE` and answers before host validation, the HTTPS redirect and sessions, so Docker and load-balancer probes work over plain HTTP with any Host header. Keep it first.
- **Templates** live in the project-level `templates/`, namespaced by app (`templates/core/…`). Auth templates live in `templates/registration/`. Everything extends `base.html`, which loads the fonts, `css/style.css`, the toast container, the shared icon `<template id="tpl-icons">` (`partials/icon_templates.html`, which `app.js` clones for toasts) and `js/app.js`.
- **Front end:**
  - **Origin:** `static/css/style.css` and `static/js/app.js` were copied from an earlier prototype, `design/v5-tasks/`, which the owner has since removed. `design/` now holds the prototypes for the five directions from task 002, plus `design/f-desk/`, task 003's clean-room look-alike of the client's own reference admin layout; it is reference only, not served and not in the image.
  - **JavaScript:** `app.js` is a single IIFE of progressive enhancements. Pages must work without it, and it finds elements by `data-*` hooks.
  - **Icons:** Solar Bold Duotone, inlined as SVG. `login.html` still inlines its icons, which is known duplication. New icons should be added once as a partial and included.
- **Database: MySQL only.** There's no SQLite fallback anywhere, tests included, and none should be added.
  - **Connection:** Django and the MySQL container read the same `MYSQL_DATABASE` / `MYSQL_USER` / `MYSQL_PASSWORD` values from `.env`. `DB_HOST` defaults to `127.0.0.1`; never use `localhost`, which mysqlclient treats as a Unix socket. Compose sets `DB_HOST=db` inside Docker.
  - **Connection options:** utf8mb4, `STRICT_TRANS_TABLES`, `ATOMIC_REQUESTS=True`, persistent connections with health checks.
  - **Test database:** tests create `test_<MYSQL_DATABASE>`. The app user only has rights on it because of `docker/mysql/init/10-test-database-grant.sh`, which runs **only when the `mysqldata` volume is first created**. If you rename the DB or user, you need `docker compose down -v`, which wipes the data.
  - **Timezone:** the MySQL image loads timezone tables, so date truncation in `TIME_ZONE` (Asia/Colombo) works.
- **Static files:**
  - **Prod storage:** prod uses WhiteNoise `CompressedManifestStaticFilesStorage`, and `collectstatic` runs at image build time.
  - **Missing files break pages:** a `{% static %}` reference to a file that doesn't exist is a **500 in prod** but works in dev. `apps/core/tests.py::test_every_static_reference_in_templates_exists` guards this; keep it passing.
- **Docker:**
  - **Dockerfile targets:** `base`, then `build` (compiles mysqlclient; build tools stay in this stage), then `dev` / `prod` (the default). Runtime needs only `libmariadb3`.
  - **Runtime user:** containers run as uid 1000 `app` with `/app` read-only, which is why Gunicorn's control socket lives in `/tmp`.
  - **Migrations:** `docker/entrypoint.sh` runs `migrate` when `DJANGO_MIGRATE=1`, which compose sets.
- **HTTPS in prod** is controlled by one flag, `USE_HTTPS`. It covers the SSL redirect and secure cookies, and TLS is expected at a proxy that sends `X-Forwarded-Proto`. Set it to `False` only for local runs of the prod image.

## Environment gotchas

- **Adding an env var:** add it to `base.py` (or `prod.py`), `.env.example` and the `web.environment` block in `compose.yaml`. Compose doesn't pass `.env` into the container wholesale.
- **No `$` in `.env` values.** Docker Compose and django-environ both treat it as variable interpolation. Generate secrets with `secrets.token_urlsafe`.
- **Quoting in Windows PowerShell 5.1:** it strips inner double quotes from arguments to native commands, which breaks `docker compose exec … sh -c '…"…"…'` and `python -c "…"`. Use the Bash tool, or a script file, for anything with nested quotes.
- **The dev and prod stacks share a compose project** (`polymath-tmd`) and service names. Starting one replaces the other's `web` and `db` containers; the volumes and data are kept. Note which stack was running and restore it afterwards.
- **In Git Bash on the host, `python` resolves to the Windows Store alias** and hangs. Use `py -3.13` or `.venv/Scripts/python.exe`.
- **Windows bind mounts** make every file look executable inside Linux containers. Shell scripts that images normally *source*, like the MySQL init scripts, get *executed* instead, so they must not rely on the parent script's functions.

## UI conventions

- **Users:** school staff, many of them non-technical. Organise screens around tasks (verbs), not data. Use plain everyday wording, say what to type in each field, and write errors that explain how to fix the problem while keeping what the user typed.
- **Touch and layout:** targets are 44–56px. Status colours (success, warning, danger, info) appear only on states, and always with an icon and a word.
- **Accessibility:** meet WCAG AA.
- **Current app tokens (provisional until a design direction is chosen):** the fonts, colours and other design tokens the app runs today live only in `:root` of `static/css/style.css` — that's the single source, not this file. Per the owner, this stylesheet and its templates are **not** inputs for the new design directions in task 002; they are what the chosen direction will replace.

## Oversight capture

This project is research data for a study on human oversight in agentic software development. The rules below tell you how to capture it; follow them exactly.

- **Recognise an oversight episode.** When the owner corrects you, rejects your approach, overrides a decision, or tells you that something you produced is wrong, that is an OVERSIGHT EPISODE.
- **Commit it on its own.** When the owner asks you to commit a resolved episode, commit that correction separately from feature work; do not fold it into a larger commit. The owner asks for every commit (see "Commit only when the user asks" under "Agent workflow").
- **End the commit message with four trailers**, after a blank line: `Oversight-Type`, `Oversight-Trigger`, `Oversight-Action`, `Oversight-Durable`. The allowed `Oversight-Type` values, the test for `Oversight-Durable: yes`, and every other mechanic are defined once, in `/oversight` (`.claude/commands/oversight.md`) — that is the normative source, so it isn't repeated here where it could drift out of sync. Use the command; don't assemble the trailers by hand.
- **Never rewrite that history.** Never squash, amend, rebase, cherry-pick or force-push a commit that carries an `Oversight-` trailer. That history is the dataset.
- **Never delete or overwrite a subagent definition, a CLAUDE.md section, or a file under `.claude/commands/`.** Change it and commit the change, so the evolution stays visible. Removing a section or command file outright is allowed only as its own commit whose message says why — never silently, and never folded into an unrelated change.
- **Log it.** After writing such a commit, append the matching row to `OVERSIGHT_LOG.md`.
- **Who runs this.** `OVERSIGHT_LOG.md` is research data, not application code, and committing is already a main-session job (see "Agent workflow"). The main session runs `/oversight` and makes both commits itself; it does not delegate that to a subagent. When an episode is `Oversight-Durable: yes` because it changes `CLAUDE.md`, a subagent definition, or a file under `.claude/commands/`, the owning agent (`tmd-docs-writer` for `CLAUDE.md`, `tmd-devops` for `.claude/commands/`) authors that change first; `/oversight` then only commits and logs it, it does not write the rule itself.
- **When unsure, ask.** If you're not sure whether something counts as an episode, ask the owner rather than guessing. A false entry is worse than a missing one.

The slash command `/oversight` (`.claude/commands/oversight.md`) is what actually runs the commit-and-log steps above; use it instead of doing them by hand.
