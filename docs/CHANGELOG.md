# Changelog

Newest first. One entry per task. Each entry lists user-visible changes, then technical notes.

## 2026-09-24 — 002: Five design directions

- Five clickable prototype directions — Ledger, Parchment, Broadsheet, Signpost and Workbench — for the owner to browse and compare, in `design/`. Each has its own sign-in, home, requests list, device record, request form and design-kit page, at both desktop and phone sizes.
- All five show the same sample school content (the same people, devices and requests) so what differs between them is the design, not the data.
- `design/README.md` is the place to start: it indexes and compares all five in one table.
- Technical notes:
  - Folders: `design/a-ledger/`, `design/b-parchment/`, `design/c-broadsheet/`, `design/d-signpost/`, `design/e-workbench/`. Each is self-contained static HTML/CSS/JS, openable from `file://`, with no build step and no dependency on `static/` or `templates/`.
  - One direction brief per variation in `docs/design/directions/` (`a.md`–`e.md`), plus its own `README.md` indexing and comparing all five.
  - Decisions worth knowing: acceptance criterion 27 (five distinct desktop navigation mechanisms) was relaxed by decision D9 after `a` and `d` were both built as left-vertical navs; the full record, including that `d`'s `Requests` count badge was removed during round 1 to force a literal pass and then restored in round 2 once the reviewer flagged that the design had been edited to satisfy the measurement rather than the user, is in the brief's D9 section.
  - No `apps/`, `templates/`, `static/`, `config/`, `docker/`, compose, packaging or requirements file changed; no migrations. The app's current stylesheet (`static/css/style.css`) is untouched and stays the app's look until the owner picks a direction for it to replace.
  - Recorded follow-ups for whichever direction is ported or kept: e-workbench's phone layout puts the request queue below the stats and actions and needs its list/record panes split; b-parchment's `assets/crest.png` has no alpha channel and should be re-cut with one; and four non-blocking nits from review round 3 — a stray raw `2px` value in `e-workbench/style.css`'s box-shadow instead of a token, an inert `z-index` on `.utility__panel`, `docs/design/directions/README.md` describing d-signpost's rail with the wrong item count and tile size, and `e-workbench/ui-kit.html`'s open-state specimen repeating the "account menu" label.
  - Verified PASS (all 37 acceptance criteria, after three rounds of fixes) and reviewed APPROVE; see `docs/tasks/002-design-directions.md`.

## 2026-09-16 — 001: Fix the three findings from the foundation baseline verification

- The sign-in page's browser tab now reads "Sign in · Polymath TMD" instead of showing the server's address.
- After a failed sign-in attempt, screen readers announce the error message together with the field, not as a separate, easy-to-miss alert.
- The "Admin" link on the home page now shows only for staff members; other signed-in users no longer see a link they can't use.
- Technical notes:
  - **Root cause:** Django's `LoginView` injects its own `site_name` into the template context from `get_current_site()` (the request host, since `django.contrib.sites` isn't installed), which silently overrode the project's own `site_name` context processor.
  - **Fix:** renamed the context processor's key from `site_name` to `tmd_site_name` in `apps/core/context_processors.py`, and updated `templates/base.html` and `templates/core/home.html` to read the new key. A guard test (`apps/core/tests.py::test_no_template_reads_the_colliding_site_name_variable`) stops the old name from coming back.
  - `templates/registration/login.html`: both inputs' `aria-describedby` now includes `login-error` (before the existing help id) whenever `form.errors` is set.
  - `templates/core/home.html`: the "Admin" link is now wrapped in `{% if user.is_staff %}`.
  - `templates/base.html`, `templates/registration/login.html` and `templates/core/home.html` each gained a `{# … #}` header comment naming their purpose and expected context variables, per CLAUDE.md.
  - No settings, migrations, env vars or dependencies changed.
  - Verified PASS and reviewed APPROVE; see `docs/tasks/001-foundation-verification-fixes.md`. The review's nits are optional follow-ups, not required by this task: de-duplicate the `_title()` test helper (`apps/accounts/tests.py`, `apps/core/tests.py`), de-duplicate the Admin-link regex in `apps/core/tests.py`, and a possible later task to give `static/js/app.js`'s client-side empty-fields check the same `aria-describedby`/`aria-invalid` wiring.

## 2026-09-16 — Project foundation (before task briefs)

- A sign-in page in the Polymath College design, a placeholder home page, and the Django admin.
- Technical notes:
  - **Stack:** Django 5.2 LTS, MySQL 8.4 (utf8mb4) and WhiteNoise. The app runs in Docker (a `prod` Gunicorn image and a `dev` overlay with live reload) and answers liveness probes at `/healthz/`.
  - **Custom user model:** `accounts.User`.
  - **Brand images:** `static/img/crest.png`, `crest-chip.png` and `favicon-32.png` are generated from `logo.png`.
  - **Claude Code agent team:** added in `.claude/agents/`, and the task-brief workflow in `docs/tasks/`.
