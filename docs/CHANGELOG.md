# Changelog

Newest first. One entry per task. Each entry lists user-visible changes, then technical notes.

## 2026-09-24 — 004: The approved design becomes the app's theme

- Sign-in and Home now use the client-approved look: a purple sidebar, a top bar, a page title
  and breadcrumb row, and a settings panel for colour mode, page width, sidebar size and sidebar
  colour. The app opens light with the purple sidebar even if the device prefers dark; dark mode
  stays one click away, in the settings panel or the top bar's colour-mode button, and the choice
  is remembered in that browser.
- The top bar's search field and notifications bell are visible, matching the approved look, but
  say plainly that they aren't ready yet: the search field reads "Search is coming soon" and can't
  be typed into or submitted, and the bell's panel says "No notifications yet." Both arrive for
  real with the Zoom link request feature (task 005).
- The sidebar only lists pages that exist today: Home, plus Admin for staff. Home is a single
  "Hello, {name}" card; no made-up figures, requests or devices are shown.
- Sign-in now matches the approved concept exactly: the concept's help text, a full-width
  password field, no show/hide button, and no "Forgot your password" line (owner correction,
  D18 — "login page design is different than the concept", resolved as "Match the concept
  exactly"). Kept on purpose, as the owner asked: the error announcement (with its curly
  apostrophe), focus moving to the password box after a wrong password, username autofocus on
  first load, and the empty-fields check.
- Technical notes:
  - **Files:** `templates/base.html` is now the f-desk document and shell, split into partials
    under `templates/partials/` (`sidebar.html`, `topbar.html`, `top_search.html`,
    `notifications.html`, `user_menu.html`, `colour_mode_button.html`, `messages.html`,
    `footer.html`, `settings_dialog.html`, `icons.html`), each included with
    `{% include … with … only %}`. `templates/registration/login.html` and `templates/core/home.html`
    are ported to the new look. `templates/partials/icon_templates.html` (the old JS toast
    template) is deleted.
  - `static/css/style.css`, `static/js/app.js` are replaced, and `static/js/theme-init.js` is new:
    it applies a saved layout choice before first paint and publishes the four settings' allowed
    values and defaults once, as `window.tmdLayout`, so `app.js` has no second copy.
  - Icons switch from inlined Solar Bold Duotone to one Feather sprite (MIT), `partials/icons.html`.
    Fonts switch from Nunito/Nunito Sans/Cinzel to IBM Plex Sans (SIL OFL 1.1).
  - CSS tokens are now role-named (no value in a token's name) and type sizes are in `rem` with
    unitless line heights, so the browser's font-size preference works; layout geometry stays in
    `px`. Colour literals live only in the first `:root` palette block, checked by a test.
  - `apps/accounts/models.py`: `User.initials` (a read-only model property, no migration), used
    for the user menu's avatar.
  - Django `messages` now render through one partial, in the page flow directly under the title
    row (not a floating toast), because that works with JS off and doesn't cover content on a
    phone.
  - **Owner correction (D18), after this task's first close:** `registration/login.html`'s form
    column was rebuilt to follow `design/f-desk/login.html` exactly. Removed: the show/hide JS
    block from `static/js/app.js`, `.field__row`/`.signin__help` from `static/css/style.css`, and
    the now-unused `eye` symbol from `partials/icons.html`. `docs/design/password-field.md` and
    its Design-section rows are marked superseded, since the app no longer has a show/hide
    control.
  - No settings, env var, dependency or route changed.
  - Tests: 83 passing (up from 36; 76 at this task's first close, then 7 more for D18), covering
    the shell markup, the CSS token and `rem` rules, the search/notifications placeholders,
    `User.initials`, and the concept-exact sign-in markup. Three existing `apps/core/tests.py`
    tests were deliberately rewritten to match text content rather than exact markup, because the
    sign-out button and Admin link now carry an icon; every `apps/accounts/tests.py` test is
    unchanged.
  - Verified PASS (83 tests, dev and prod stacks) and reviewed APPROVE; see
    `docs/tasks/004-app-theme-f-desk.md`, including its D18 owner-correction record.
  - Follow-ups recorded for brief 005: the shell assumes a signed-in user, so the public Zoom
    request form must either override `{% block body %}` like `login.html` does, or branch on
    `user.is_authenticated` in `topbar.html`/`sidebar.html`; wire the search field to a real form
    and give the bell real content, or record why not; port `.tag` and check it renders at 10.5px
    (the client's own choice, held from task 003).

## 2026-09-24 — 003: Look-alike of the client's reference layout

- The client asked for the Technology Management Desk to look and work like a specific admin
  template of theirs: the same typeface, the same sidebar-and-top-bar shell, light and dark mode,
  and a layout settings panel. `design/f-desk/` is a new static prototype built to that shape, in
  the Polymath crest purple, so the client can compare it side by side with their own reference
  template before anything is ported into the app.
- It shows the same six screens and sample school content as directions `a`–`e` (sign in, home,
  requests list, device record, raise-a-request form, design kit), re-dressed with a collapsible
  grouped sidebar, a top bar (search, notifications, user menu), a page-title and breadcrumb row,
  cards, a footer, and a settings panel for colour mode, page width, sidebar size and sidebar
  colour.
- It is built from scratch: nothing was copied from the client's reference template, only observed
  and measured. What's different from that template is recorded in full in the task brief's "What
  the client will notice" list (`docs/tasks/003-reference-lookalike-prototype.md` → Review →
  Round 2); in short, it is sparser (no sparklines, promo cards or illustrations), everything is a
  little taller for easier tapping, and the settings panel offers four choices instead of seven.
- Directions `a`–`e` were not selected; they stay in `design/` unchanged, as a record.
- Technical notes:
  - Folder: `design/f-desk/` (`login.html`, `dashboard.html`, `requests.html`, `device.html`,
    `request-form.html`, `ui-kit.html`, `style.css`, `theme-init.js`, `app.js`, `README.md`,
    `assets/`, `screenshots/`). Design spec: `docs/design/directions/f.md`.
  - No CSS/JS framework or component library (decision D2): plain CSS grid, flexbox and custom
    properties; `<details>`/`<summary>` for the sidebar's expandable group and the dropdowns; a
    `<dialog>` for the settings panel; `:target` plus `inert` for the phone drawer (D14); native
    scrolling instead of a third-party scrollbar; one inline SVG chart instead of a charting
    library.
  - Text sizes match the client's reference template, including 10.5px status tags — the owner's
    deliberate choice over a larger-text floor (D9). WCAG AA contrast (4.5:1 text, 3:1 non-text)
    holds in both light and dark mode and on all three sidebar tones.
  - Porting into `templates/` and `static/` is a follow-up brief (004) and does not start until the
    client has approved this prototype against their reference template (D13).
  - Verified PASS (44/44 fidelity rows against the reference template, after one fix cycle and
    re-verification) and reviewed APPROVE (round 2); see
    `docs/tasks/003-reference-lookalike-prototype.md`.
  - Follow-ups recorded for brief 004: switch sizes from `px` to `rem`; rename value-named tokens
    (for example `--space-52px`) to role-named ones; add `{# … #}` purpose-and-context header
    comments to every template; fix the settings panel's "Icons only" option not staying synced
    after a menu-button collapse; check content reflow at 320px as well as 400px.

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
