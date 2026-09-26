# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Polymath TMD (Technology Management Desk) is a Django 5.2 LTS app for Polymath College. It uses server-rendered Django templates (HTML5), plain CSS and vanilla JS with no build step, MySQL 8.4, and runs in Docker. The product requirements are delivered in stages, so check `docs/` (when present) before assuming scope.

## Working rules (set by the project owner)

- **Every task goes through subagents.** The main session orchestrates: it delegates, passes results between agents and reports to the user. It does not write app code, templates or config itself, even for a one-line fix. See "Agent workflow" below.
- **A task isn't done until it's verified.** `tmd-test-verifier` runs the checks under "Verify a change" and reports the actual output. A FAIL sends the task back to the owning agent; it's never marked done.
- **Code is documented.** Every module, class and non-trivial function gets a docstring that explains *why*, not what. Every template starts with a `{# … #}` comment naming its purpose and the context variables it expects. Update `README.md` when commands, env vars or setup change.
- **No Django admin.** The app doesn't use `django.contrib.admin`. Every requirement gets its own in-app screens, built in the f-desk shell with views, forms and templates like any other page, and its own data models. Staff never have to open `/admin/`.
- **MVT and the Django design philosophies** apply, as follows:
  - **Model:** business rules and data invariants live on models, managers and querysets (`clean()`, custom QuerySet methods), not in views or templates.
  - **View:** thin. Parse the request, call the model layer, choose a template, return a response. Prefer generic class-based views plus `ModelForm` when they fit. Views never build HTML strings.
  - **Template:** presentation only. No queries beyond iterating over context, and no business decisions. Shared markup goes in `templates/partials/` and is included with `{% include … with … only %}`.
  - **DRY:** every concept lives in one place:
    - Env config is read only in `config/settings/base.py`.
    - Design tokens are defined only in section 1's `:root` blocks of `static/css/style.css` (1a–1e); colour literals live only in the first, 1a palette block. Use `var(--…)`, never raw hex.
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
  - **Less code:** use what Django ships (auth, generic views, forms, messages — not the admin; see above) before writing your own. Every new dependency needs a reason in the task notes.

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
2. `pytest --create-db` (inside the dev container). Parallel agents share `test_polymath_tmd`, so never run `--create-db` at the same time as another agent — one run's `--create-db` drops the database out from under the other and produces false failures (tasks 008 and 010).
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
    - `accounts`: the custom `User` model (`AUTH_USER_MODEL = "accounts.User"`) plus login and logout wired to Django's auth views (logout is POST-only), and, from task 010, the **Staff and access** screens (`accounts:staff`, `staff_add`, `staff_edit`, `staff_password`) and `accounts:password_change` for everyone. Roles are plain `auth.Group`s, fixed by migrations (`IT desk`, `Staff managers`); there's no screen for creating or editing one. The access rules live on `User`, not in views or templates: `can_give_role(actor, group)` (a role can only be given or removed by someone who already holds all of its rights, or by a superuser), `granted_permissions()` (a person's roles' permissions plus their own, read from the roles even when they're switched off, so an inactive peer can't be re-enabled through a stale "no permissions" reading), `can_be_managed_by(actor)` (who may open or change a given person) and `access_change_error(*, actor, is_active, is_superuser)` (the self-lockout and last-superuser guards). Nobody is deleted; `is_active=False` switches a person off.
    - `core`: the home page, the `tmd_site_name` context processor, `HealthCheckMiddleware`, and `apps/core/mixins.py`'s `SignedInPermissionMixin` (task 010) — the shared "anonymous → sign in, signed in without the permission → 403" gate that both `zoom` and `accounts` views use, so apps still don't import each other's views. The context-processor key is prefixed because Django's auth views (`LoginView` and friends) inject their own `site_name` from `get_current_site()`, which would silently override an unprefixed key of the same name.
    - `zoom`: Zoom link requests, task 005; live Zoom connection, task 006. A public request → a verified email → the IT queue → conflict-free host assignment → the link email. `providers.py` is a swappable interface: `fake` for dev/tests, `manual` as a production fallback that can't see meetings made directly in Zoom (it raises the deploy warning `zoom.W001`), and `zoom`, the live provider, for production once every paid account is connected. `apps/zoom/zoom_api.py` is the only module that talks HTTP to Zoom — the only importer of `requests`, holding the fixed hosts, the Server-to-Server OAuth token cache, timeouts and the error mapping. Host keys are stored Fernet-encrypted at rest, never in plaintext; Zoom credentials never touch the database at all (env only, task 006 D2). `services.approve()` retries once on a MySQL deadlock, so call it only outside an open `transaction.atomic()` block — nesting one breaks the retry's savepoint (review round 2, nit 1). With the `zoom` provider, `approve()` also asks Zoom whether the chosen account is free *before* taking any locks, and makes exactly one `POST` create call while holding them, with a compensating `DELETE` and a marker-based clean-up (`agenda` carries `Polymath TMD ZL-{pk:04d}`) if anything fails afterwards (task 006 D6). The IT queue (`templates/zoom/queue.html`, `detail.html`) and the Zoom accounts screens (`zoom:accounts`, `zoom:account_add`, `zoom:account_edit`, task 008) are both in-app; `apps/zoom/admin.py` is gone. The Zoom timetable (`zoom:timetable`, `zoom:timetable_day`, task 009) is a read-only month/day view of booked and waiting classes; its month arithmetic, week layout and grouping are pure functions with no database access in `apps/zoom/timetable.py`, so the views stay thin and each page runs a fixed number of queries. `HostAccount.stop_booking_errors()` locks both the account and its booked `Occurrence`/`LinkRequest` rows (`select_for_update(of=("self", "link_request"))`) before checking them, so the check stays correct even if the isolation level ever becomes REPEATABLE READ (task 008, review round 1). Joining `IT desk` is done on `accounts`' Staff and access page (task 010), same as any other role.
- **`/healthz/`** isn't a URL route. `apps.core.middleware.HealthCheckMiddleware` sits *first* in `MIDDLEWARE` and answers before host validation, the HTTPS redirect and sessions, so Docker and load-balancer probes work over plain HTTP with any Host header. Keep it first.
- **Templates** live in the project-level `templates/`, namespaced by app (`templates/core/…`). Auth templates live in `templates/registration/`. `base.html` is the document and the page shell, split into partials under `templates/partials/` and pulled in with `{% include … with … only %}` (sidebar, top bar, search placeholder, notifications, user menu, colour-mode button, messages, footer, settings dialog, icon sprite). A page fills the `heading`, `breadcrumb` and `content` blocks; the shell itself is only ever defined in `base.html`. The shell assumes a signed-in user (sidebar, user menu); a public page drops it by overriding `{% block body %}`, as `login.html` does, or by extending `templates/public_base.html` (task 005), the shared frame for pages with no sign-in (the Zoom request form and its confirmation pages). A new sidebar section adds itself as a group in `partials/sidebar.html`, between `Menu` and `Administration` (which always stays last) — no context processor, no nav registry. The sidebar include takes `perms` (task 005) so a group can gate itself on a permission.
  - **Shared form partials** (`templates/partials/error_summary.html`, `field.html`, `field_error.html`, `choice_group_head.html`, `check_field.html`) are used by every app that renders a form — `zoom` and, from task 010, `accounts`. They moved out of `templates/zoom/partials/` in task 010 because `accounts` mustn't reach into `zoom`'s folder; a template outside `zoom` never includes anything from `templates/zoom/partials/`. `field.html` never writes a `value` for a password widget, so no page can leak a typed password by forgetting to guard it itself, and its help is a `<div>` (Django's password rules are a `<ul>`, which can't sit inside a `<p>`).
  - **`templates/403.html`** (task 010) is the one refusal page for every section: Django's default `handler403` renders it for any `PermissionDenied`, so no view sets it. It picks its own frame, `base.html` for a signed-in user or `public_base.html` otherwise, and never renders the exception text.
- **Front end:**
  - **Origin:** `static/css/style.css`, `static/js/app.js` and `static/js/theme-init.js` are ported from `design/f-desk/`, task 003's client-approved look-alike of the client's own reference admin layout, by task 004. `design/` also holds the five direction prototypes from task 002 (an earlier, unselected comparison) and `design/v5-tasks/`, the original prototype the app's front end started from, which the owner has since removed. `design/f-desk/` itself now stays frozen as the approved reference; none of `design/` is served or in the image.
  - **JavaScript:** `theme-init.js` loads in `<head>`, before `style.css` and without `defer`/`async`, so a saved layout applies before first paint. It owns the four layout settings (`theme`, `width`, `navSize`, `navTone`) — their allowed values and defaults — publishing them as `window.tmdLayout`; `app.js` reads them from there rather than keeping a second copy. The saved choice lives in `localStorage` under `tmd-layout`. `app.js` itself is a single IIFE of progressive enhancements loaded with `defer`; pages must work without it, and it finds elements by `data-*` hooks, never classes or tags.
  - **Icons:** Feather (MIT), inlined as one SVG sprite, `templates/partials/icons.html`, included once by `base.html` and holding only the symbols in use.
  - **Responsive reflow:** never hide a calendar or table cell with `display: none`; clip it instead (`.visually-hidden`-style clipping plus `visibility: hidden` on its contents), or a screen reader recomputes column headers from whatever cells remain (task 009, review round 1, SF1).
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
- **Exception: Zoom credentials.** `ZOOM_CREDENTIAL_SETS` and the three `ZOOM_S2S_<NAME>_*` variables per account (task 006 D2) are deliberately **not** in `web.environment`. Eleven-plus accounts would bloat `compose.yaml`, and `environment` entries take precedence over `env_file` anyway, so an interpolated placeholder there would blank out the real value. They live only in `zoom-credentials.env` (git-ignored, copied from `zoom-credentials.env.example`), loaded through `compose.yaml`'s `env_file: [{path: ./zoom-credentials.env, required: false}]`.
- **No `$` in `.env` values.** Docker Compose and django-environ both treat it as variable interpolation. Generate secrets with `secrets.token_urlsafe`.
- **Quoting in Windows PowerShell 5.1:** it strips inner double quotes from arguments to native commands, which breaks `docker compose exec … sh -c '…"…"…'` and `python -c "…"`. Use the Bash tool, or a script file, for anything with nested quotes.
- **The dev and prod stacks share a compose project** (`polymath-tmd`) and service names. Starting one replaces the other's `web` and `db` containers; the volumes and data are kept. Note which stack was running and restore it afterwards.
- **In Git Bash on the host, `python` resolves to the Windows Store alias** and hangs. Use `py -3.13` or `.venv/Scripts/python.exe`.
- **Windows bind mounts** make every file look executable inside Linux containers. Shell scripts that images normally *source*, like the MySQL init scripts, get *executed* instead, so they must not rely on the parent script's functions.
- **`ZOOM_PROVIDER`:** `config/settings/prod.py` refuses to start when it's `fake`, but the local `.env` sets `fake` for dev. Running the prod stack locally therefore needs an override, not a `.env` edit: `ZOOM_PROVIDER=manual docker compose up -d --build`. `manual` now raises the deploy warning `zoom.W001` (it can't see meetings made directly in Zoom), so `check --deploy` on the prod stack for real must be run with `ZOOM_PROVIDER=zoom` and a working credential set, not `manual`. `check --database default` also needs running whenever `zoom` is chosen, to catch `zoom.E004` (a paid account with no working Zoom connection) — it's a separate, database-tagged check from plain `check`.
- **No test ever reaches the network.** The root-level `conftest.py` starts an autouse `responses` mock for every test, so any unregistered `requests` call raises `ConnectionError` instead of leaving the machine. Register replies with `http_mock.add(...)` (or plain `responses.add(...)`, the same mock) and never with `@responses.activate` or `with responses.RequestsMock()` — either one stops the global mock for the rest of that test, defeating the block (task 006 criterion 45, D17).

## UI conventions

- **Users:** school staff, many of them non-technical. Organise screens around tasks (verbs), not data. Use plain everyday wording, say what to type in each field, and write errors that explain how to fix the problem while keeping what the user typed.
- **Touch and layout:** targets are 44–56px. Status colours (success, warning, danger, info) appear only on states, and always with an icon and a word.
- **Accessibility:** meet WCAG AA.
- **Tokens:** the client-approved f-desk look (task 004) is the app's real theme, not a placeholder. Every token lives only in section 1's `:root` blocks of `static/css/style.css` (1a–1e); colour literals (hex, `rgb(`, `hsl(`) appear nowhere else, and only in the first, 1a palette block — a test enforces both — and everywhere else reads `var(--…)`. Type sizes are in `rem`, with unitless line heights, so the browser's font-size preference works; layout geometry and touch targets stay in `px`. The client-approved defaults are light mode, purple sidebar, standard sidebar width, full page width; dark mode, boxed width and the other sidebar sizes/tones stay available through the layout settings panel and are never auto-followed from the device. Status is always shown with an icon plus a word, never colour alone. Text sizes follow the approved reference exactly (down to a 10.5px status tag, arriving with task 005), with AA contrast held at every size.

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
