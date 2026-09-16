# 001 — Fix the three findings from the foundation baseline verification

<!-- One brief per task. Each section has exactly one owner agent; agents write only their own section.
     The workflow itself is defined in CLAUDE.md → "Agent workflow". -->

**Status:** Done <!-- Planned | Blocked: questions | In progress | Verifying | In review | Done -->

## Requirement
<!-- owner: tmd-planner — the user's words verbatim, then a one-paragraph interpretation -->

> yes fix them

"Them" means these three findings from the baseline verification of the foundation (verifier's words, verbatim):

> 1. "Login page <title> is wrong on prod HTTP: `<title>Sign in · 127.0.0.1:8010</title>` (home is `Home · Polymath TMD`). Django's LoginView injects its own `site_name` context (= request host, since django.contrib.sites isn't installed), overriding the `site_name` context processor. Root cause apps/accounts/urls.py:8 (LoginView) + templates/base.html:6. Accessibility impact: WCAG 2.4.2 page titles; minor. Owner: tmd-django-backend."
> 2. "Accessibility audit (minor): after a failed login both inputs get aria-invalid="true" but the error message isn't linked via aria-describedby (it is announced via role="alert"). Owner: tmd-frontend (optional)."
> 3. "Home 'Admin' link is shown to every signed-in user, not just staff (out of scope for criteria). Owner: tmd-frontend/tmd-django-backend."

**Reading:** This is a small fix to the existing foundation, with no new screens or data. (1) Every page title must end with the configured `SITE_NAME` ("Polymath TMD"), including the login page. The cause is a name collision: Django's `LoginView.get_context_data()` sets `site` and `site_name` from `get_current_site()`, which is a `RequestSite` whose name is the request host. The view's context overrides a context processor with the same key. So the fix is to stop sharing that name, not to patch one view. (2) When the server re-renders the login form with errors, both inputs must point at the error alert through `aria-describedby`. Their existing help text must stay linked. (3) The "Admin" link on the home page should appear only to users who can actually open the admin, which Django decides with `is_active and is_staff`. Every signed-in user is already active, so the check is `user.is_staff`. Each fix gets a regression test so it stays fixed.

## Scope
<!-- owner: tmd-planner — In scope / Out of scope bullets -->

**In scope**
- Rename the project's site-name context variable to a key that Django does not use, and update every template that reads it (`templates/base.html`, `templates/core/home.html`).
- Add a docstring to `apps/core/context_processors.py` explaining *why* the key has a project prefix (the collision with auth views).
- Server-rendered login errors: add `login-error` to the `aria-describedby` of both inputs, keeping `username-help` / `password-help`.
- Home page: render the "Admin" link only for `user.is_staff`. The card footer must still look right when the link is missing.
- Add the `{# … #}` purpose/context header comment to the three templates this task touches (`base.html`, `registration/login.html`, `core/home.html`), as CLAUDE.md requires.
- Regression tests for all acceptance criteria.

**Out of scope**
- Installing `django.contrib.sites` or adding `SITE_ID` (rejected, see MVT plan).
- The client-side "Please fill in both boxes" path in `static/js/app.js`: it shows the alert but sets no `aria-invalid`/`aria-describedby`. That is a separate progressive-enhancement fix; note it in Implementation notes if it's worth a follow-up brief.
- The server-side alert text for empty fields (it currently says "didn't match" for any form error).
- Any change to admin access itself. Django's admin already turns away non-staff users; this task only hides the link.
- Moving login icons into partials (known duplication, tracked separately).
- Settings, env vars, Docker (no `tmd-devops` work).

## Acceptance criteria
<!-- owner: tmd-planner — numbered, observable, testable -->

Tests compare against `settings.SITE_NAME` instead of the literal "Polymath TMD", so they pass whatever the container env sets. The separator is the existing ` · ` (space, U+00B7, space).

**Page titles (issue 1)**
1. GET `accounts:login` (anonymous) returns 200, and the response contains `<title>Sign in · {SITE_NAME}</title>`. It does **not** contain the request host (`testserver` under the test client) inside `<title>`.
2. POST `accounts:login` with a wrong password re-renders (200) with `<title>Sign in · {SITE_NAME}</title>`.
3. GET `core:home` as a signed-in user contains `<title>Home · {SITE_NAME}</title>`, and the body still shows `{SITE_NAME} is set up and running.`
4. With `@override_settings(SITE_NAME="Example Desk")`, the login page title is `<title>Sign in · Example Desk</title>` and the home page title is `<title>Home · Example Desk</title>`. This proves the setting is the only source.
5. Regression guard: no file under `templates/` references the template variable `site_name` (regex `\bsite_name\b` finds no match; the new prefixed key doesn't match because `_` is a word character). This stops the colliding name from coming back when the password-reset views arrive.
6. On the rebuilt **prod** stack, `GET http://127.0.0.1:8010/accounts/login/` (use `reverse` or read the path from the running app; don't assume) returns HTML whose `<title>` is `Sign in · Polymath TMD` (or the `.env` `SITE_NAME`), not `Sign in · 127.0.0.1:8010`.

**Login error wiring (issue 2)**
7. GET `accounts:login` (no attempt yet): the username input's `aria-describedby` is exactly `username-help` and the password input's is exactly `password-help`. Neither references `login-error`, and neither has `aria-invalid`.
8. POST `accounts:login` with a wrong password: both inputs have `aria-invalid="true"`. The username input's `aria-describedby` space-separated tokens include both `login-error` and `username-help`, and the password input's include both `login-error` and `password-help`.
9. POST `accounts:login` with a wrong password: the element `id="login-error"` exists, has `role="alert"` and is not `hidden` (existing tests keep passing, so this is a regression check). Every id referenced by either input's `aria-describedby` exists in the page.
10. POST `accounts:login` with a wrong password still keeps the typed username (`value="nimali.p"`), so the existing test keeps passing.

**Admin link (issue 3)**
11. GET `core:home` as a signed-in user with `is_staff=False` returns 200, and the page contains no `<a>` whose `href` is `reverse("admin:index")` and no link text "Admin".
12. GET `core:home` as a signed-in user with `is_staff=True` contains an `<a>` with `href="{reverse('admin:index')}"` and the text "Admin".
13. GET `core:home` as a superuser made with `create_superuser` (which sets `is_staff=True`) shows the Admin link.
14. For both staff and non-staff users, the "Sign out" POST form to `accounts:logout` is still on the page (existing test `test_home_shows_sign_out_button_that_posts_to_logout` passes for a non-staff user).

**General**
15. `templates/base.html`, `templates/registration/login.html` and `templates/core/home.html` each start with a `{# … #}` comment on the first line, naming the purpose and the context variables they expect. Django comments create no node, so a comment before `{% extends %}` is allowed. The page still renders (criteria 1–3 prove it).
16. All checks under CLAUDE.md "Verify a change" pass: ruff check/format, `pytest --create-db`, `makemigrations --check --dry-run` (no migrations expected), `manage.py check`, and the prod-stack HTTP check for `/accounts/login/` (anonymous) and the home page (signed in as staff and as non-staff).

## Design decisions needed
<!-- owner: tmd-planner — open questions for the user; "None" if none -->

None. The decisions below follow from CLAUDE.md and Django's own behaviour, so they are recorded in the MVT plan rather than put to the user.

## MVT plan
<!-- owner: tmd-planner -->

### Models

No model, migration or settings changes.

### URLs and views

No new or changed routes. The existing routes affected by this task, for reference:

| Name | Path | View | Template | Permission |
|---|---|---|---|---|
| `accounts:login` | `login/` under the accounts include | `django.contrib.auth.views.LoginView` (`redirect_authenticated_user=True`), **unchanged** | `registration/login.html` | Anonymous |
| `core:home` | home (existing) | `apps.core.views.home`, **unchanged** | `core/home.html` | `login_required` |

### Context contract
<!-- The only coupling between backend and frontend: template → exact context variables and their types -->

**Every template (from the context processor `apps.core.context_processors.site`, registered in `base.py` under that dotted path, so no settings change):**

| Variable | Type | Source | Notes |
|---|---|---|---|
| `tmd_site_name` | `str` | `settings.SITE_NAME` | **Replaces `site_name`.** Project templates must not read `site_name`, because Django auth views overwrite it with the request host. |
| `user` | `User` / `AnonymousUser` | `django.contrib.auth.context_processors.auth` (existing) | Used for `user.is_staff` on home. |

**`templates/base.html`:** `tmd_site_name`. Title markup: `<title>{% block title %}{% endblock %} · {{ tmd_site_name }}</title>`.

**`templates/registration/login.html`** (from `LoginView`, unchanged): `form` (`AuthenticationForm`, which has `form.errors`), `next` (`str`), plus `tmd_site_name` via base. Django also adds `site` and `site_name`; the template must ignore them.

**`templates/core/home.html`:** `user` (authenticated `User`: `first_name`, `username`, `is_staff`), `tmd_site_name`. No new view context; the view is unchanged.

### Decisions and rejected alternatives

**Issue 1: chosen approach.** Rename the context processor's key from `site_name` to `tmd_site_name`, which is prefixed and owned by the project. This is one line in `apps/core/context_processors.py` plus the two template references. `settings.SITE_NAME` stays the single source. It fixes every Django view that injects `site_name` (today `LoginView`; later the password-reset views and emails) without touching those views. The prefix also avoids admin's `site_title`/`site_header` keys. The function name and its dotted path in `TEMPLATES` stay the same, so `base.py` is not edited.

Rejected alternatives:
- **Install `django.contrib.sites` and set the `Site` name.** This adds an app, `SITE_ID`, a migration and a data row. The name would then live in both the DB and `SITE_NAME`, which breaks DRY, and each environment's DB would have to be kept in sync.
- **Subclass `LoginView` and restore `site_name` in `get_context_data()`.** More code. It patches one view, so every future auth view needs the same override. It also leans on context-ordering knowledge, which counts as hidden magic.
- **`LoginView.as_view(extra_context={"site_name": ...})`.** Doesn't work: `LoginView.get_context_data()` applies its `site_name` *after* `ContextMixin` merges `extra_context`. It would also repeat the setting in a URLconf.
- **Hard-code "Polymath TMD" in `base.html`.** Breaks the env-driven `SITE_NAME`.

**Issue 2.** This is template-only. Add `login-error` to each input's `aria-describedby` **only when `form.errors`**, so a hidden alert is never referenced. Recommended order: `login-error` first, then the help id, so the fix instruction is read before the general hint. The designer confirms. `role="alert"` stays.

**Issue 3.** `{% if user.is_staff %}` around the link in `home.html`. `is_staff` is the flag that `AdminSite.has_permission()` checks (together with `is_active`, which every logged-in user already has under `ModelBackend`), and Django's own admin templates use the same idiom. Rejected: a view-computed `can_open_admin` flag from `admin.site.has_permission(request)`. It adds view code and context for a check Django already exposes on `user`, and the home view would need to import the admin site.

### Placement and reuse
- `apps/core/context_processors.py` (backend): the key rename and a docstring.
- `templates/base.html`, `templates/core/home.html`, `templates/registration/login.html` (frontend).
- Tests: title and guard tests in `apps/core/tests.py` (the existing `test_every_static_reference_in_templates_exists` shows the template-scan pattern to reuse). Login title and aria tests in `apps/accounts/tests.py` (reuse the `user` fixture and the `_login_error_tag` / regex-on-tag style).
- Reused as they are: Django `LoginView`, `AuthenticationForm`, the auth context processor's `user`, the `.card-foot` and `.link-arrow` styles. No new CSS classes, JS, partials or dependencies are expected.

## Agent plan
<!-- owner: tmd-planner — ordered steps; mark steps that can run in parallel -->

1. **`tmd-ui-designer`** (short): confirm the title format `Page · SITE_NAME`, the `aria-describedby` token order on error, and how `.card-foot` should look when only "Sign out" is present. It uses `justify-content: space-between`, so a single child sits at the start; say whether that's acceptable or which existing utility to use. No new copy.
2. **In parallel**, once the Design section is written (the context contract above is fixed):
   - **`tmd-django-backend`**: rename the key in `apps/core/context_processors.py`, add the module and function docstring, and write tests for criteria 1–5 and 7–14.
   - **`tmd-frontend`**: `base.html` title variable, `home.html` (`tmd_site_name` and the `is_staff` guard), `login.html` conditional `aria-describedby`, and the header comments (criterion 15).
   - Both changes must land before verification; neither passes on its own.
3. **`tmd-test-verifier`**: all checks in CLAUDE.md "Verify a change", including rebuilding the prod stack and checking criteria 6 and 16 over HTTP on port 8010. Restore whichever stack was running before. A FAIL goes back to step 2 with the report.
4. **`tmd-code-reviewer`** (read-only): APPROVE or CHANGES REQUESTED. Changes go back to step 2, then step 3.
5. **`tmd-docs-writer`**: update the CLAUDE.md Architecture line that names "the `site_name` context processor" to the new key and explain why it's prefixed. Add a `docs/CHANGELOG.md` entry, then close this brief.

`tmd-devops` is not needed: no settings, env or Docker changes.

## Design
<!-- owner: tmd-ui-designer — layout + wireframes, components (existing classes), states, copy, accessibility, progressive enhancement -->

This is a small fix. There are no new screens, components, CSS classes, JS or copy. Everything the user sees stays the same apart from the three points below. No `docs/design/` file is needed.

### 1. Page titles (confirmed)

**Format:** `{page name} · {tmd_site_name}`. The separator is space, U+00B7 middle dot, space, as in the current `base.html`. The page name goes first so that browser tabs, bookmarks, history and screen reader page announcements tell pages apart when the tab is narrow (WCAG 2.4.2).

| Page | `{% block title %}` | Rendered `<title>` (default env) |
|---|---|---|
| `registration/login.html`: first visit and after a failed attempt | `Sign in` | `Sign in · Polymath TMD` |
| `core/home.html` | `Home` | `Home · Polymath TMD` |

- The title stays the same after a failed login (criterion 2). Do not add an "Error:" prefix in this task.
- Every page must fill `{% block title %}`. An empty block would render ` · Polymath TMD` with a leading separator.
- The body line on home keeps its wording and only switches variable: `{{ tmd_site_name }} is set up and running. Screens will be added here as requirements come in.`

### 2. Login error wiring (decided)

**Markup on a server re-render with `form.errors`:**

| Input | `aria-invalid` | `aria-describedby` (exact order) |
|---|---|---|
| `#username` | `true` | `login-error username-help` |
| `#password` | `true` | `login-error password-help` |

**Markup on first visit (no `form.errors`):** `aria-describedby="username-help"` / `"password-help"` only. No `aria-invalid`, and `login-error` is never referenced. The alert still exists but is `hidden`, and an input must never point at hidden text.

**Why the error goes first:** screen readers read `aria-describedby` targets in the order the ids are listed. The error is new, specific and says what to do next ("Try again, or ask the office to reset it."). The help text is general and the user has already heard it. Putting the fix first means it is heard straight after the field name, before the user tabs away. It also matches the visual order: the alert sits above both fields.

**Focus after a failed login (keep the current behaviour):**
- `autofocus` stays on **`#password`** when `form.errors` is set, and on `#username` otherwise. The frontend doesn't change this.
- **Why:** the typed username is kept but the password box comes back empty, and a mistyped password is the most likely cause. The cursor is already where the user has to type again.
- **Why it matters here:** `role="alert"` content that is already in the page on load isn't reliably announced by every screen reader. With the new wiring, focusing the password field reads "Password, edit, invalid, We couldn't sign you in. That username or password didn't match. Try again, or ask the office to reset it. Passwords are case sensitive…", so the error is always heard.
- Keep `role="alert"` as well. It is a harmless extra route to the same message.
- Don't move focus to the alert. That would put focus on text that isn't interactive and add a Tab stop before the field that needs fixing.

**Unchanged:**
- Copy (alert title "We couldn't sign you in", alert text, labels, help text, buttons).
- Visual layout and the `.alert.alert-danger` icon + title.
- Tab order: Username, Password, Show, Sign in.

### 3. Home card footer: Admin link for staff only (decided)

Wrap **only** the `<a class="link-arrow">` in `{% if user.is_staff %}…{% endif %}`. Don't leave an empty wrapper, spacer or placeholder element behind. The footer keeps `.card-foot` as it is, with no inline style and no new utility.

```
Staff (desktop and ~400px phone: both fit on one row)
+--------------------------------------------------+
| Hello, Nimali                                    |   .card-head  h1
+--------------------------------------------------+
| Polymath TMD is set up and running. Screens ...  |   .card-body  p.muted
+--------------------------------------------------+
| Admin                            [ Sign out ]    |   .card-foot: a.link-arrow ... form > .btn.btn-secondary
+--------------------------------------------------+

Non-staff (desktop and phone)
+--------------------------------------------------+
| Hello, Nimali                                    |
+--------------------------------------------------+
| Polymath TMD is set up and running. Screens ...  |
+--------------------------------------------------+
| [ Sign out ]                                     |   .card-foot: single child sits at the start
+--------------------------------------------------+
```

**Why a start-aligned "Sign out" for non-staff is acceptable:**
- Each person only ever sees one version, so the button never jumps position for a given user.
- Start-aligned, it lines up with the heading and body text above it: one straight left edge and the shortest scan path.
- It needs no CSS change and no `margin-left:auto` inline style. Inline styles would add one-off layout that a later page shell will replace anyway.
- On phones `.card-foot` already wraps and uses the smaller padding (`style.css` mobile block). The 48px `.btn` and 44px `.link-arrow` targets are unchanged.

**States:** the signed-in staff and signed-in non-staff views are shown above. Anonymous users never see home (`login_required` redirects them to Sign in). No-permission case: non-staff users no longer see a link that would only take them to the admin login. Django still blocks them if they type the address, and that is out of scope.

**Accessibility:**
- Landmarks (`main#main`, skip link) and headings (single `h1`) are unchanged.
- For non-staff, the footer's only focus stop is "Sign out". For staff, the order is Admin, then Sign out, which matches the visual order.

### Progressive enhancement

All three fixes are server-rendered HTML and work without `app.js`. No JS changes. The client-side empty-fields check in `app.js` still doesn't set `aria-invalid`/`aria-describedby`. That's out of scope here (see Scope). If it gets a follow-up brief, it should use the same token order: `login-error` first, then the help id.

## Implementation notes
<!-- owners: tmd-devops, tmd-django-backend, tmd-frontend — one sub-heading each: files changed, contract deviations, migrations, new deps (with reason), self-check output -->

### tmd-django-backend

**Files changed**
- `apps/core/context_processors.py`: the key is now `tmd_site_name` (was `site_name`). Added module and function docstrings that explain the collision with the `site_name` that `LoginView` sets from `get_current_site()`. The function name and its dotted path are unchanged, so `config/settings/base.py` wasn't touched.
- `apps/core/tests.py`: module docstring, plus tests for:
  - the context processor's key: `test_site_context_processor_uses_prefixed_key`
  - criterion 3: `test_home_title_and_body_use_site_name`
  - criterion 4, login and home under `override_settings(SITE_NAME="Example Desk")`: `test_site_name_setting_is_the_only_source_of_page_titles`
  - criterion 5, `\bsite_name\b` over every file under `templates/`: `test_no_template_reads_the_colliding_site_name_variable`
  - criteria 11 and 14, non-staff: `test_home_hides_admin_link_from_non_staff`
  - criteria 12 and 14, staff: `test_home_shows_admin_link_to_staff`
  - criterion 13: `test_home_shows_admin_link_to_superuser`
- `apps/accounts/tests.py`: module docstring, plus tests for:
  - criterion 1: `test_login_title_uses_site_name_not_request_host`
  - criterion 2: `test_login_title_unchanged_after_wrong_password`
  - criterion 7: `test_login_inputs_describe_only_help_before_any_attempt`
  - criterion 8: `test_login_inputs_point_at_error_after_wrong_password`
  - criterion 9: `test_login_error_alert_and_described_ids_exist_after_wrong_password`
  - Criterion 10 is still covered by the existing `test_login_with_wrong_password_keeps_typed_username`.

**Test notes**
- Titles are compared against `escape(settings.SITE_NAME)`, never a literal.
- Criterion 8 checks that the tokens are present, as the criterion says, not their order. The designer's order (`login-error` first) is a template concern and isn't asserted.
- Criteria 6, 15 and 16 are for the verifier (prod HTTP check, template header comments, full checklist).

**Context contract:** implemented as written. Every template gets `tmd_site_name` (`str`, from `settings.SITE_NAME`), and the `site_name` key is gone. No view changes.

**Migrations:** none.

**Dependencies and settings:** none.

**Self-check** (dev overlay, run after the frontend templates had landed):
- `ruff check .`: All checks passed!
- `ruff format --check .`: 37 files already formatted (the first `ruff format .` reformatted one line in `apps/core/tests.py`)
- `pytest --create-db`: 25 passed
- `makemigrations --check --dry-run`: No changes detected
- `manage.py check`: no issues (0 silenced)
- Mutation check: with the key temporarily set back to `site_name`, 5 title and context tests failed as expected. The file was then restored and the run above repeated.
- Stack: I started the dev overlay for these checks, then restored the prod stack with `docker compose up -d --build`. `web` is `healthy` again.

### tmd-frontend

**Files changed**
- `templates/base.html`:
  - The title now reads `{{ tmd_site_name }}`.
  - Added the `{# … #}` header comment covering purpose, context, blocks and partials.
- `templates/registration/login.html`:
  - Added the header comment.
  - Both inputs now render `aria-describedby="{% if form.errors %}login-error {% endif %}username-help"` / `…password-help"`. The error id comes first, as the Design section specifies.
  - `aria-invalid` and `autofocus` are unchanged.
- `templates/core/home.html`:
  - Added the header comment.
  - The body line now uses `{{ tmd_site_name }}`.
  - Only the `<a class="link-arrow">` is wrapped in `{% if user.is_staff %}…{% endif %}`, with no leftover wrapper.
- No partials, CSS, JS or static files were added or changed.

**Spec deviations:** none. There are two implementation details the reviewer should know about:
- **Header comment placement.** Each header comment sits on line 1, on the *same line* as the first tag (`{% load static %}<!DOCTYPE html>` in `base.html`, `{% extends "base.html" %}` in the child templates). A newline after a `{# #}` comment is a text node. A text node before `{% extends %}` is still rendered, so the response would start with `\n` before `<!DOCTYPE html>`. My first attempt did this, and my render check caught it. Keeping them on one line leaves the output starting with `<!DOCTYPE html>` exactly as before.
- **Comment wording.** The comments avoid the literal token `site_name` because criterion 5's guard regex (`\bsite_name\b`) scans raw template text, comments included.

**Context contract gaps:** none. Only `tmd_site_name`, `user.is_staff`/`first_name`/`username`, `form.errors`, `form.username.value` and `next` are used.

**Follow-up (out of scope, as noted in Scope):** the client-side empty-fields path in `static/js/app.js` still sets neither `aria-invalid` nor `aria-describedby`. If it gets a follow-up brief, that brief should use the same token order (`login-error` first).

**Self-check output.** The prod stack was running when I started, and I didn't start or stop any stack. I ran everything in one-off `docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps web …` containers. Partway through, the stack was switched to dev by another agent.
- `pytest --create-db` (after the backend's context-processor rename and tests landed): `25 passed in 2.40s`.
- A throwaway Django test-client render check (kept in the session scratchpad, not added to the repo) passed. Its output:
  - GET login: `<title>Sign in · Polymath TMD</title>`; the username input has `aria-describedby="username-help" autofocus` and the password input has `aria-describedby="password-help"`. Neither has `aria-invalid`. The response starts with `<!DOCTYPE html>`.
  - POST login with a wrong password: same title. The username input has `value="nimali.p" aria-describedby="login-error username-help" aria-invalid="true"`. The password input has `aria-describedby="login-error password-help" aria-invalid="true" autofocus`. Every referenced id exists, and `#login-error` isn't hidden.
  - Home as non-staff: `<title>Home · Polymath TMD</title>` and the body line render. `.card-foot` holds only the Sign out form (`action="/accounts/logout/"`), with no `/admin/` link.
  - Home as staff: `.card-foot` holds `<a class="link-arrow" href="/admin/">Admin</a>` followed by the Sign out form.
- HTTP on the running dev stack: `GET http://127.0.0.1:8010/accounts/login/` returned `200`, with `<title>Sign in · Polymath TMD</title>` and `aria-describedby="username-help"` / `"password-help"`. The body starts with `<!DOCTYPE html>`.
- The prod-stack HTTP check (criteria 6 and 16) is deferred to `tmd-test-verifier`, because rebuilding the prod stack would have disrupted the backend agent.

## Verification
<!-- owner: tmd-test-verifier — verdict, criteria → tests table, checklist results, failures -->

**Verdict: PASS**

### Handoff points

- **Criterion 8 order.** The Design section fixes an exact token order (`login-error` first) as a decided contract, not a suggestion ("Recommended order... The designer confirms"), and it's independently observable and easy to regress silently (e.g. a future edit reordering the `{% if %}` could flip it back with criterion 8's presence-only test still green). Added `test_login_inputs_list_error_before_help_text` to `apps/accounts/tests.py`, asserting `_described_by(tag) == ["login-error", f"{input_id}-help"]` for both inputs after a failed login. Passed.
- **Criteria 6, 15, 16 (left to the verifier).** Criterion 6 confirmed over real prod HTTP on port 8010 (see below). Criterion 15 got a new test, `test_template_starts_with_purpose_comment` (parametrized over the three templates) in `apps/core/tests.py`, plus a manual read of each file confirming the comment content names purpose and context variables. Criterion 16 is the full checklist below.
- **Frontend's header-comment placement.** Confirmed over prod HTTP: `curl http://127.0.0.1:8010/accounts/login/` and the saved `home_*.html` files all start with `<!DOCTYPE html>` on byte 1, no leading newline.

### Acceptance criteria → tests

| # | Criterion | Test | Result |
|---|---|---|---|
| 1 | Login title uses `SITE_NAME`, not host | `apps/accounts/tests.py::test_login_title_uses_site_name_not_request_host` | ✅ |
| 2 | Login title unchanged after wrong password | `apps/accounts/tests.py::test_login_title_unchanged_after_wrong_password` | ✅ |
| 3 | Home title + body use `SITE_NAME` | `apps/core/tests.py::test_home_title_and_body_use_site_name` | ✅ |
| 4 | `override_settings(SITE_NAME=...)` drives both titles | `apps/core/tests.py::test_site_name_setting_is_the_only_source_of_page_titles` | ✅ |
| 5 | No template reads `site_name` | `apps/core/tests.py::test_no_template_reads_the_colliding_site_name_variable` | ✅ |
| 6 | Prod HTTP: login `<title>` on 8010 | Manual: `curl http://127.0.0.1:8010/accounts/login/` → `<title>Sign in · Polymath TMD</title>` | ✅ |
| 7 | No-attempt inputs describe only help | `apps/accounts/tests.py::test_login_inputs_describe_only_help_before_any_attempt` | ✅ |
| 8 | Failed-login inputs: `aria-invalid` + both ids present | `apps/accounts/tests.py::test_login_inputs_point_at_error_after_wrong_password`; order per Design confirmed by new `test_login_inputs_list_error_before_help_text` | ✅ |
| 9 | `#login-error` alert exists, `role="alert"`, not hidden; referenced ids exist | `apps/accounts/tests.py::test_login_error_alert_and_described_ids_exist_after_wrong_password` | ✅ |
| 10 | Typed username kept | `apps/accounts/tests.py::test_login_with_wrong_password_keeps_typed_username` (existing) | ✅ |
| 11 | Non-staff: no Admin link | `apps/core/tests.py::test_home_hides_admin_link_from_non_staff`; confirmed over prod HTTP (0 `link-arrow` matches for `verifier_nonstaff`) | ✅ |
| 12 | Staff: Admin link present | `apps/core/tests.py::test_home_shows_admin_link_to_staff`; confirmed over prod HTTP (`<a class="link-arrow" href="/admin/">Admin</a>` for `verifier_staff`) | ✅ |
| 13 | Superuser sees Admin link | `apps/core/tests.py::test_home_shows_admin_link_to_superuser` | ✅ |
| 14 | Sign-out form present for both roles | `apps/core/tests.py::test_home_hides_admin_link_from_non_staff` / `test_home_shows_admin_link_to_staff` (both assert `_has_logout_form`); `test_home_shows_sign_out_button_that_posts_to_logout` (existing) | ✅ |
| 15 | `{# … #}` header comment, line 1, on all three templates | New `apps/core/tests.py::test_template_starts_with_purpose_comment[base.html\|registration/login.html\|core/home.html]`; manual read confirms each names purpose + context vars | ✅ |
| 16 | Full CLAUDE.md checklist | See below | ✅ |

### Checklist

- `ruff check .` (dev container): **All checks passed!**
- `ruff format --check .` (dev container): **37 files already formatted**
- `pytest --create-db -rA` (dev container): **29 passed** (25 pre-existing/backend + 4 added by this verification: `test_login_inputs_list_error_before_help_text` and 3 parametrizations of `test_template_starts_with_purpose_comment`)
- `manage.py makemigrations --check --dry-run`: **No changes detected**
- `manage.py check`: **System check identified no issues (0 silenced)**
- `--deploy` check: **skipped — n/a.** No settings changed in this task (context-processor key rename + templates only), so CLAUDE.md's trigger for the deploy check ("When settings change") doesn't apply.
- Prod stack HTTP (rebuilt with `docker compose up -d --build`, `web` healthy):
  - Anonymous `GET /` → `302` to `/accounts/login/?next=/`.
  - `GET /accounts/login/` → `200`, `<title>Sign in · Polymath TMD</title>`, response starts with `<!DOCTYPE html>`.
  - Throwaway superuser `verifier_staff` (`createsuperuser --noinput` via `DJANGO_SUPERUSER_PASSWORD`) and a throwaway non-staff user `verifier_nonstaff` created via `manage.py shell`.
  - Logged in as `verifier_staff` → home `200`, `<title>Home · Polymath TMD</title>`, `.card-foot` contains `<a class="link-arrow" href="/admin/">Admin</a>` then the Sign out form.
  - Logged in as `verifier_nonstaff` → home `200`, same title, `.card-foot` has no `link-arrow` anywhere on the page, only the Sign out form.
  - POST wrong password as `verifier_staff` → `200`, title unchanged, `#username` has `aria-describedby="login-error username-help" aria-invalid="true"`, `#password` has `aria-describedby="login-error password-help" aria-invalid="true" autofocus`, `#login-error` has `role="alert"` and no `hidden`.
  - Both throwaway users deleted after saving the HTML (`home_staff.html`, `home_nonstaff.html`, `login_fail.html` in the verifier's scratchpad).
  - Stack restored: prod (`docker compose up -d`) is the stack that was running before verification started, and it's still running/healthy on 8010 now.

### Accessibility audit (saved logged-in HTML)

- Labels: `#username` and `#password` each have a matching `<label for>`. ✅
- Errors linked: on failure, both inputs carry `aria-invalid="true"` and `aria-describedby` includes `login-error`, which exists, has `role="alert"`, and isn't `hidden`. ✅
- Headings: home has exactly one `h1` ("Hello, …"). Login has one `h1` ("Welcome back"); the only `h2` ("Technology Management Desk") sits inside the `aria-hidden="true"` art panel, so it doesn't reach the accessibility tree — unchanged, pre-existing, out of scope. ✅
- Landmarks/skip link: `<a class="skip-link" href="#main">` and `<main id="main">` present on all three pages. ✅
- Images: crest has `alt="Polymath College crest"`; the decorative chip image has `alt=""` and sits in the `aria-hidden` panel. ✅
- Status + icon + word: the login error alert has an `aria-hidden` icon plus the title text "We couldn't sign you in" — unchanged by this task. ✅
- Buttons: "Sign in", "Sign out", and the password-visibility toggle (`<span>Show</span>`) all have visible text; the Admin link has visible text "Admin". ✅
- Touch targets: not re-measured — no CSS/layout changed in this task, `.btn`/`.link-arrow` sizing is unchanged from the audited baseline.

### Tests added
- `apps/accounts/tests.py::test_login_inputs_list_error_before_help_text`
- `apps/core/tests.py::test_template_starts_with_purpose_comment` (parametrized: `base.html`, `registration/login.html`, `core/home.html`)

### Mutation sanity
Re-verified the backend's own mutation check is still valid post-edit: `pytest --create-db` passes clean with all 29 tests (backend's 25 plus the 4 new/changed here); no product code was touched.

## Review
<!-- owner: tmd-code-reviewer (written by the main session) — verdict, blockers, should-fix, nits -->

**Verdict: APPROVE**

**Blockers:** none

**Should fix:** none

**Nits** (optional; owner tmd-django-backend unless noted):
- **Duplicated title helper:** `_title()` is defined in both `apps/accounts/tests.py:77` and `apps/core/tests.py:64`. Move it to one shared test-helper module before more title tests arrive.
- **Admin-link regex written three times:** `apps/core/tests.py:124`, `:148` and `:173`. Reuse `_admin_links()` or add a small `_admin_link(content)` helper.
- **Misplaced test:** `test_home_shows_admin_link_to_superuser` (`apps/core/tests.py:167`) sits under the "Template header comments" heading. Move it next to the other Admin-link tests.
- **Header test covers three templates:** CLAUDE.md asks for a header on every template, but the test (`apps/core/tests.py:155-158`) only checks three. A later task could scan all of `templates/`, once `partials/icon_templates.html` has a header.
- **Name guard reads every file:** the guard at `apps/core/tests.py:111` reads every file under `templates/`, which will crash on non-text files. Use `rglob("*.html")`, as the static-reference test does.
- **Long header comments** (owner tmd-frontend): the one-line headers at `templates/base.html:1`, `registration/login.html:1` and `core/home.html:1` are 300–400 characters. They're correct, since a line break would put whitespace before the doctype. Keep future headers shorter.

**Good:**
- **Cause fixed, not the symptom:** renaming the key fixes titles on every Django auth view, including future password-reset pages, without patching views. A guard test stops the old name from coming back.
- **Tests that would catch a real regression:** they compare against the setting, use `override_settings` to prove it's the only source, check that every `aria-describedby` id exists, and the backend ran a mutation check.

**Handoff for docs-writer:** `CLAUDE.md:104` still says "the `site_name` context processor".

## Docs
<!-- owner: tmd-docs-writer — files updated; closes Status -->

- `CLAUDE.md`: Architecture → "Current apps" → `core` bullet now names the `tmd_site_name` context processor (was `site_name`) and explains the prefix — Django's auth views inject their own `site_name` from `get_current_site()`, which would otherwise silently override it.
- `docs/CHANGELOG.md`: added the 2026-09-16 entry for this task (user-visible changes, then technical notes, including the reviewer's nits as optional follow-ups).
- `README.md`: not updated — no commands, env vars, setup or deployment steps changed.

Verification: PASS. Review: APPROVE. Status set to Done.
