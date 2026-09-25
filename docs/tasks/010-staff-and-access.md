# 010 — Staff and access: manage staff users and roles in the app, and remove the Django admin

<!-- One brief per task. Each section has exactly one owner agent; agents write only their own section.
     The workflow itself is defined in CLAUDE.md → "Agent workflow". -->

**Status:** Done <!-- Planned | Blocked: questions | In progress | Verifying | In review | Done -->

## Requirement
<!-- owner: tmd-planner — the user's words verbatim, then a one-paragraph interpretation -->

> a project rule, we dont use Djangoadmin. we should have our own screens and datamodels to handle the requirements

(This was given while brief 008 was being planned, on 2026-09-25, alongside the requirement "so there should be a place where we can configure the zoom accounts, and view of the month in a timetable format.", which briefs 008 and 009 cover.)

**Reading.** Once brief 008 takes the Zoom models out of the Django admin, the admin still does three jobs. It creates staff users and sets their passwords. It puts users in groups (today only `IT desk`, which from 008 also manages Zoom accounts) and can edit what those groups allow. And it is the only place a staff member can change their own password.

This brief gives those jobs in-app screens, in an **Administration › Staff and access** section of the f-desk shell:

- a list of the people who can sign in;
- adding a person with a starting password;
- changing their details and **roles** (the existing groups, shown with what each one allows);
- switching someone off so they can't sign in;
- setting a new password for them;
- for everyone, "Change your password" in the user menu.

Roles stay fixed, created by migrations. There's no screen that invents groups or edits their permissions.

Then **`django.contrib.admin` is removed entirely**: from `INSTALLED_APPS`, the `admin/` route, `apps/accounts/admin.py`, the sidebar, the tests and the README. `django.contrib.auth` stays, because the rule is about screens, and auth's users, groups, permissions, password hashing and views are what these screens are built on.

`manage.py createsuperuser` stays, but only to create the very first account on a new install.

## Scope
<!-- owner: tmd-planner — In scope / Out of scope bullets -->

**Place in the sequence:** 008 → **010** → 009. See the split table and the full admin-use inventory in `docs/tasks/008-zoom-accounts.md` → Scope. This brief owns every inventory row marked 010.

**In scope (010)**

- **`apps/accounts`**, which owns `User` (D1). It gets:
  - `UserQuerySet` with the listing and guard queries, attached through a `UserManager` subclass;
  - rule methods on `User`;
  - forms, views, URLs and tests;
  - a data migration creating the role `Staff managers`;
  - a migration that removes what the admin left behind in the database (D6).
- **Screens** (the shell, `Administration` group), gated by Django's built-in model permissions on `accounts.User` (`view_user`, `add_user`, `change_user`):
  - `Staff and access`: the list;
  - `Add a person`;
  - `Change {name}`: name, username, email, roles, full access (superusers only), and the `Can sign in` flag;
  - `Set a new password for {name}`.
- **For every signed-in user:** `Change your password`, using Django's `PasswordChangeView`, linked from the user menu.
- **Guards**, as model-layer rules with tests:
  - only superusers can give or take full access, or change a superuser;
  - nobody can switch off their own sign-in or remove their own full access;
  - the last active superuser can't be switched off or lose full access.
- **Remove `django.contrib.admin`:**
  - `DJANGO_APPS` entry (`tmd-devops`);
  - `config/urls.py`: the `admin/` route and the `admin.site` header lines (`tmd-devops`);
  - `apps/accounts/admin.py`;
  - the sidebar's `Admin` link and its `is_staff` gate;
  - the admin-based tests in `apps/core/tests.py`;
  - README's admin steps (docs writer).
- **Sidebar:** the `Administration` group now holds `Staff and access` and is gated by `perms.accounts.view_user`. It stays last.
- **A friendly 403 page, `templates/403.html`,** used by every section (D11, criterion 28; this also closes brief 008's design gap G6).
- **Shared form partials move to `templates/partials/`:**
  - which partials: `error_summary.html`, `field.html`, `field_error.html` and `choice_group_head.html`, moved from `zoom/partials/`;
  - `field.html` changes:
    - it never renders a password's value;
    - its help becomes a `<div>`;
  - one CSS rule is added, for lists inside help text.

  This is Design D.9 items 1–4, covered by criteria 29–30.

**Out of scope (010)**

- Deleting users (D4). People are switched off, never deleted: `LinkRequest.decided_by` is `PROTECT`, and the history of who decided what has to stay.
- Creating, renaming or deleting roles, or changing what a role allows (D3). A new role arrives with the brief that needs it, as a data migration.
- Invitation emails, "forgot your password" and self-service password reset (owner, Q4b; D9). The sign-in page stays exactly as approved in brief 004, D18.
- Per-user permissions that aren't roles. The screen assigns roles and full access, never single permissions.
- Profile fields beyond Django's (phone, department).
- Two-factor sign-in, sign-in auditing, and account lockout after failed attempts.
- An audit log of who changed whom. `last_login` and `date_joined` are shown; a history is a later brief if the owner wants one.

**Follow-ups (recorded, not in 010)**

- **One shared date format in `core` (Design Q-D2).** `accounts/partials/when.html` repeats brief 005's display format (`Mon 28 Sep 2026, 9:40 am`) with Django's `date` filters, because `accounts` mustn't load `zoom`'s `zoom_format` tag library. A later change moves `class_date` / `class_time` and their filters into `apps/core`, where both apps load them. The formats then have one source again. The docs writer lists this in `docs/CHANGELOG.md`.
  - **It also covers review round 1, nit 6:** `staff_form.html:53` has an inline `"D j M Y"` that repeats the format in `accounts/partials/when.html`. That fix is left for this follow-up and isn't needed to close 010.
- **The locked-role row markup in `staff_form.html` (review round 2, nits C and D; owner: `tmd-frontend`).** These are cosmetic and markup-only. Nothing is saved wrongly, and there's no behaviour or security effect.
  - **C:** at `staff_form.html:37`, a locked row puts the `choice__words` class on both its span and its label. Put it on one element only.
  - **D:** when a crafted POST is refused (criterion 32), the locked row shows the posted state instead of the stored one. Nothing is saved, but the row should show the person's stored state.

## Acceptance criteria
<!-- owner: tmd-planner — numbered, observable, testable -->

**Terms.**

- Brief 005's frozen "now" (**Mon 28 Sep 2026, 10:00**, Asia/Colombo) and its rule on pinned copy apply.
- **Staff manager:** an active user whose only permissions come from the `Staff managers` group.
- **Superuser:** `is_superuser=True`.
- **Plain user** and **IT user** are as defined in briefs 005 and 008. After 008, an IT user holds `zoom.review_linkrequest` and the three host-account permissions.
- **Name** means `User.__str__`: the full name, or the username if no name is set.

### Roles, access and navigation

1. **Role.** After `migrate`, a group named `Staff managers` exists with exactly `accounts.view_user`, `accounts.add_user` and `accounts.change_user`. It does not have `delete_user`. The migration is reversible and doesn't duplicate the group when run again. `IT desk` is unchanged: it keeps exactly the four permissions from brief 008, criterion 1. There's no `Zoom account managers` group (008, Q1).
2. **Access.**

   | Page | Anonymous | Plain user, IT user | Staff manager | Superuser |
   |---|---|---|---|---|
   | `accounts:staff` | Redirect to `accounts:login?next=…` | 403 | 200 | 200 |
   | `accounts:staff_add` | Redirect to login | 403 | 200 | 200 |
   | `accounts:staff_edit` (another user) | Redirect to login | 403 | 200 only when criterion 11 allows it; otherwise **403** (a superuser, another Staff manager, or anyone with rights the actor lacks) | 200 |
   | `accounts:staff_password` (another user) | Redirect to login | 403 | 200 only when criterion 11 allows it; otherwise **403** | 200 |
   | `accounts:staff_password` (your own pk) | Redirect to login | 403 | redirect (302) to `accounts:password_change` (criterion 34) | redirect (302) to `accounts:password_change` |
   | `accounts:password_change` | Redirect to login | 200 | 200 | 200 |
3. **Sidebar.**
   - The `Administration` group (`id="nav-admin"`) renders only with `perms.accounts.view_user`. It holds `Staff and access` → `accounts:staff`, which has `aria-current="page"` on `accounts:staff`, `staff_add`, `staff_edit` and `staff_password`.
   - A user with `is_staff=True` but no permissions sees **no** `Administration` group.
   - The group is still last, after `Zoom links`.
   - No template contains `admin:index` or reads `is_staff`. A pytest check over `templates/` enforces this.
4. **User menu.** Every signed-in user's menu has `Change your password` → `accounts:password_change`, between `Layout settings` and `Sign out`. It works without JS, because the menu is a `<details>`.

### The list: `accounts:staff`

5. **Page and table.**
   - The h1 is `Staff and access`, the title is `Staff and access · {site name}`, and the breadcrumb is `Home › Staff and access`.
   - The table has a `<caption>` and `<th scope>`, with these columns in order:
     - `Name`: a link to `accounts:staff_edit` when the viewer may change that person (criterion 11);
     - `Username`;
     - `Email`;
     - `Roles`: each group's name, plus `Full access` for superusers, with an icon and the word; `No roles` when there are none;
     - `Sign-in`: a tag with an icon and a word, `Can sign in` or `Switched off`;
     - `Last signed in`: the date and time, or `Never`.
   - Rows are ordered with people who can sign in first, then by last name, first name and username.
   - The list pages at 50 per page with the f-desk pager.
   - An `Add a person` button is shown to users with `add_user`.
6. **Query budget.** The list runs the same number of SQL queries for 3 people as for 40, each with two roles. It prefetches groups.

### Add: `accounts:staff_add`

7. **Form.**
   - The h1 is `Add a person`, and the breadcrumb is `Home › Staff and access › Add a person`.
   - Every field has a `<label for>` and a `-help` hint wired with `aria-describedby`:
     - `first_name` (`First name`);
     - `last_name` (`Last name`);
     - `username` (`Username`, help `They type this to sign in. Letters, numbers and @ . + - _ only.`);
     - `email` (`Work email`, `type="email"`, **required**, help `Emails about Zoom requests go here.`);
     - `groups` (`Roles`): one checkbox per existing group, ordered by name. Under each checkbox, its help lists that group's permission names, **sorted by name** (D3). The template draws them from the `roles` context list (G1, D12). A test checks that a group with two permissions shows both names, in order, beside its checkbox, and that the page's query count doesn't grow with the number of groups;
     - `is_superuser` (`Full access to everything`): **rendered only for superusers**;
     - `password1` and `password2` (`Starting password`, `Type it again`), with `autocomplete="new-password"`. The help lists Django's password rules.
   - **Widget attributes (G3), each checked in a test:**
     - `username` has **no** `autofocus`;
     - `first_name`, `last_name`, `username` and `email` have `autocomplete="off"`;
     - `username` and `email` have `autocapitalize="none"` and `spellcheck="false"`.
   - **Labels and help:** every label and help string is exactly as in the Design section's D.6 copy table, which is pinned like any criterion copy. That includes the help for `first_name` and `last_name`, which Django doesn't provide, and `password2`'s `Type it again` with its plain help line (G2).
   - `is_active` is not shown; new people can sign in.
   - The button reads `Add the person`.
8. **Create.** A valid POST creates the user with:
   - `is_active=True` and `is_staff=False`;
   - a hashed password (`check_password` passes, and the raw password isn't stored);
   - the ticked groups;
   - `is_superuser` only if a superuser ticked it.

   It redirects to `accounts:staff` with the message `Added {name}. Give them their username and starting password yourself, not by email.`
9. **Validation.** Each invalid POST returns 200, saves nothing, and keeps every typed value **except the two passwords**, which Django never renders back. The errors are:

   | Input | Field | Error |
   |---|---|---|
   | empty username, or bad characters | `username` | Django's message |
   | a username already taken, in any letter case | `username` | `A user with that username already exists.` (Django's) |
   | empty email | `email` | `Type their work email address. Emails about Zoom requests go to it.` |
   | an email another user has, in any letter case | `email` | `Someone else already uses this email address.` |
   | passwords that don't match | `password2` | Django's message |
   | a password that fails `AUTH_PASSWORD_VALIDATORS` | `password2` | Django's messages |

   The error summary's lead is `We couldn't save this person yet.`, rendered by `partials/error_summary.html` (criterion 29).
10. **A non-superuser can't grant full access.** A staff manager's form has no `is_superuser` field. A crafted POST with `is_superuser=on` still creates the user with `is_superuser=False`.

### Change: `accounts:staff_edit`

11. **Who may be changed** (*amended after review round 1, SF1; see D13 and criterion 34*). `User.can_be_managed_by(actor)` is true when:
    - the actor is a superuser; or
    - the target **is the actor** **and the actor has `accounts.change_user`**. They open their own change page within the limits of criterion 33. Criterion 2's table already implies this, because users without the right get 403 on every `staff_edit`. *(Amended after review round 2, nit B, to match `models.py`.)* Or:
    - all of these hold:
      - the actor has `accounts.change_user`;
      - the target isn't a superuser;
      - the target doesn't hold `accounts.change_user` (so isn't another Staff manager);
      - the target's granted permissions are a subset of `actor.get_all_permissions()`.

    The list links names, and the edit and password pages allow access, only when it's true (criterion 2).
12. **Form.**
    - The h1 is `Change {name}`, and the breadcrumb is `Home › Staff and access › {name}`.
    - It shows criterion 7's fields, minus the passwords. `is_active` is shown as `Can sign in`.
    - There's a link, `Set a new password`, to `accounts:staff_password`.
    - Read-only facts: `Added on {date_joined}` and `Last signed in {last_login | Never}`.
    - The button reads `Save changes`.
    - A valid POST saves and redirects to `accounts:staff` with `Saved {name}.`
13. **Guards.** Each of these re-renders with 200, saves nothing, and shows the exact field error:

    | Situation | Field | Error |
    |---|---|---|
    | A user unticks `Can sign in` on themselves | `is_active` | `You can't switch off your own sign-in. Ask someone else with Staff and access to do it.` |
    | A superuser unticks their own `Full access` | `is_superuser` | `You can't remove your own full access. Ask another person with full access to do it.` |
    | Switching off, or removing full access from, the **only** active superuser | that field | `{name} is the only person with full access. Give someone else full access first.` |
    | A staff manager posts `is_superuser` for anyone | (ignored) | The value is left unchanged, with no error. The field isn't in their form |

    These rules live on the model layer (`User` methods and `UserQuerySet.active_superusers()`), and the form's `clean()` calls them. Each rule has a unit test.
14. **Switching someone off.**
    - After `is_active=False` is saved, that person's sign-in fails with the login page's existing error.
    - A session they already had is refused: their next request to `zoom:queue` redirects to login.
    - Their past decisions (`LinkRequest.decided_by`) are unchanged.
    - Ticking `Can sign in` again restores sign-in.
    - No page has a delete button, and no `accounts` URL name contains `delete`.

### Passwords

15. **Setting a new password for someone else: `accounts:staff_password`.**
    - The h1 is `Set a new password for {name}`.
    - The page uses `StaffSetPasswordForm`, a thin subclass of Django's `SetPasswordForm` (D7 as amended). Its fields are `new_password1` and `new_password2`, with `autocomplete="new-password"`. `new_password2` is labelled `Type it again`, with the D.6 help line (G2).
    - On success:
      - the password is changed;
      - **that person's existing sessions stop working** (Django's session auth hash; the test signs them in first, then checks their next request redirects to login);
      - the page redirects to `accounts:staff_edit` with `Saved a new password for {name}. Give it to them yourself, not by email.`
    - Errors are Django's. Passwords are never rendered back.
16. **Changing your own password: `accounts:password_change`.**
    - The page uses Django's `PasswordChangeView` with `OwnPasswordChangeForm`, a thin subclass of `PasswordChangeForm` (D7 as amended), in the shell.
      - `old_password` is labelled `Your current password`, with the D.6 help line.
      - `new_password2` is labelled `Type it again` (G2).
      - The h1 is `Change your password`, and the breadcrumb is `Home › Change your password`.
    - On success, the user **stays signed in** (Django's `update_session_auth_hash`), and the page redirects to `core:home` with `Your password was changed.`
    - A wrong old password shows Django's error.
    - There's no separate "done" page; the message replaces it.
17. **No password leaks.**
    - `staff_add` and `staff_password` wrap `dispatch` in `sensitive_post_parameters()` (Django's `PasswordChangeView` already does).
    - With logging captured at `DEBUG`, no record from the add, set-password or own-password flows contains a typed password.
    - No response body contains a typed password, even on error re-renders.
    - **The shared field partial never echoes a password** (Design D.9 item 2). `partials/field.html` writes `value="…"` only when `field.widget_type != "password"`.
      - **Tests:** re-render each of the three password forms with errors, after posting a known password (`Tr0ub4dor-3xyz-Q`, which has no HTML-escaped characters, so a plain text search is reliable):
        - `staff_add`, with a mismatched `password2`;
        - `staff_password`, with a mismatch;
        - `password_change`, with a wrong old password.
      - **Expected:**
        - the response body doesn't contain `Tr0ub4dor-3xyz-Q` anywhere;
        - every `<input type="password">` in it has no `value` attribute.
      - **Source check:** a pytest check of `templates/partials/field.html` asserts the condition is present, so no password page can forget it.

### Roles are data, not screens

18. **Role list.**
    - The `Roles` checkboxes list every `Group` (`Group.objects.order_by("name")`, with permissions prefetched), so a group created by a later migration appears with no code change. A test creates a group in the test and sees its checkbox.
    - There's no URL for creating, renaming or deleting a group, or for editing its permissions (checked by a pytest scan of the URL names).

### The Django admin is gone

19. **Removal.** All of the following hold:
    - `"django.contrib.admin"` isn't in `INSTALLED_APPS`;
    - `GET /admin/` returns 404;
    - `reverse("admin:index")` raises `NoReverseMatch`;
    - `apps/accounts/admin.py` doesn't exist;
    - no module under `apps/` or `config/` imports `django.contrib.admin` (a pytest scan);
    - `config/urls.py` has no `admin.site` line.

    `django.contrib.auth`, `contenttypes`, `sessions` and `messages` remain.
20. **Leftovers in the database (D6).** A migration in `accounts`:
    - drops the table `django_admin_log` if it exists (`RunSQL("DROP TABLE IF EXISTS django_admin_log")`);
    - deletes the `ContentType` rows with `app_label="admin"`, which also removes their permissions and any group links to them.

    Its reverse is a no-op. It runs cleanly on a fresh test database, where the table never existed, and on the dev database, where it does. After `migrate` on the dev database, `SHOW TABLES LIKE 'django_admin_log'` returns nothing.
21. **Tests rewritten deliberately.** In `apps/core/tests.py`:
    - `test_home_hides_admin_link_from_non_staff`, `test_home_shows_admin_link_to_staff` and `test_home_shows_admin_link_to_superuser` are replaced by `Staff and access` equivalents (a staff manager or superuser sees it; an `is_staff` user without permissions doesn't);
    - `test_sidebar_links_resolve_to_named_urls_only` and `test_sidebar_shows_administration_group_only_for_staff` assert `accounts:staff`, not `admin:index`.

    `apps/zoom/tests/test_sidebar_zoom_group.py` passes unchanged, because `Administration` is still the group title. Test fixtures may keep setting `is_staff`, but no assertion depends on it.
22. **Bootstrap.** `manage.py createsuperuser` still works; it belongs to `django.contrib.auth`. The README describes it only as "create the first account on a new install; add everyone else on Staff and access". The README contains no `/admin/` path and no instruction to use the Django admin.

### Model layer, templates, accessibility

23. **Thin views.** The rules live on the model layer:
    - `User.can_be_managed_by(actor)`;
    - `User.can_grant_full_access(actor)`;
    - the self and last-superuser checks, as a `User` method returning the error or `None`;
    - `UserQuerySet.staff_list()` (ordering, `prefetch_related("groups")`);
    - `UserQuerySet.active_superusers()`.

    Views contain no ORM filters beyond `get_queryset` / `get_object` calling these. The manager stays a subclass of Django's `UserManager`, so `create_user` and `createsuperuser` keep working.
24. **Template rules.**
    - Every new template starts with a `{# … #}` header naming its context, and every include ends with `only`.
    - There are no inline styles and no hard-coded paths.
    - Every icon used is in the sprite, and every sprite icon is used.
    - Brief 004's and 005's guard tests pass.
    - The new templates are `templates/accounts/staff_list.html`, `staff_form.html` and `staff_password.html`, plus `templates/registration/password_change_form.html`, which uses the shell.
25. **Works without JavaScript, and meets the layout and accessibility bar** on every page in this brief:
    - no horizontal page scroll at 320, 400, 1024 and 1440 px, in both colour modes;
    - the list becomes a card per row below 768px;
    - targets are at least 44×44 px;
    - WCAG AA;
    - one h1;
    - the table has a `<caption>` and `<th scope>`;
    - the roles checkboxes sit in a `<fieldset>` with the `<legend>` `Roles`;
    - tags show an icon plus a word;
    - after a failed submit, focus moves to the error summary.

### Verification (CLAUDE.md "Verify a change", all five)

26. `ruff check .`, `ruff format --check .`, `pytest --create-db`, `makemigrations --check --dry-run` and `manage.py check` all pass. **Settings change**, so the verifier also runs `docker compose exec -e USE_HTTPS=True web python manage.py check --deploy` on the prod stack, started with `ZOOM_PROVIDER=manual`. Only `security.W021` is allowed.
27. **Prod stack walk-through** over HTTP on 8010 (the verifier restores the previous stack afterwards):
    1. A superuser, created with `createsuperuser`, adds a staff manager.
    2. The staff manager adds an `IT desk` person with a test password.
    3. That person signs in and sees `Link requests`, and doesn't see `Administration`.
    4. The staff manager sets them a new password. Their open session ends.
    5. The staff manager switches them off, and they can't sign in.
    6. The person changes their own password (before being switched off, in a separate run).
    7. `/admin/` returns 404, and static files are hashed and return 200.
    8. The `IT desk` person opens `/accounts/staff/` directly and gets the friendly 403 page from criterion 28, in the shell, on the prod image.

    **Screenshots** (in the scratchpad, not committed):
    - the list at 1440 and 400, in light and dark;
    - add with errors;
    - change, including a guard error;
    - set a new password;
    - change your password;
    - the 403 page at 1440 and 400.

### Added after the design review (2026-09-25)

These are appended rather than renumbered, because the Design section cites the numbers above. They are verified exactly like criteria 1–27.

28. **A friendly 403 page, for every section (D11).**
    - **Where it comes from:** `templates/403.html`. Django's default `handler403` renders it for any `PermissionDenied`, whatever the `DEBUG` setting. No URL or view changes are needed.
    - **What stays the same:**
      - the response status stays **403**;
      - the anonymous case is unchanged: the `LoginRequiredMixin` views still redirect to `accounts:login?next=…` (criterion 2, and briefs 005 and 008).
    - **Signed-in user without the permission.** The page renders in the **shell**, with the sidebar, top bar and user menu.
      - h1 `You can't open this page`, `<title>` `You can't open this page · {site name}`, breadcrumb `Home › You can't open this page`.
      - Body: `Your roles don't include this page. Ask someone who manages Staff and access to give you the role you need.`
      - A button `Go to Home` → `core:home`.
      - The sidebar shows only what that user can open, as it does on every page, so it doubles as "where you can go instead".
      - **Test:** an IT user GETs `accounts:staff`, and a plain user GETs `zoom:accounts`. Each gets 403 and a body containing the h1, the copy, the `Go to Home` link and `<nav class="sidenav__menu"`.
    - **Anonymous (defensive).** For a `PermissionDenied` that reaches a signed-out visitor, from any future view without the login mixin, the same template renders in the **public frame** (`public_base.html`, no sidebar).
      - It shows the same h1, then `Sign in to see this page.` and a `Sign in` link → `{% url 'accounts:login' %}?next={{ request.path|urlencode }}`.
      - **Test:** call `django.views.defaults.permission_denied` with an anonymous request. The body has no `data-nav` and does have the sign-in link.
    - **What never appears:** the exception message, the permission codename, or any word from it. A test raises `PermissionDenied("accounts.change_user")` and asserts that the string `accounts.change_user` is absent.
    - **Standards:** the template follows criterion 24's rules, and the page meets criterion 25's layout and accessibility bar.
    - **Out of scope:** CSRF failures keep Django's separate `403_csrf.html` path.
29. **The shared form partials move to `templates/partials/` (Design D.9 item 1).**
    - **New locations:** `error_summary.html`, `field.html`, `field_error.html` and `choice_group_head.html` exist under `templates/partials/`, and none of them remains under `templates/zoom/partials/`.
    - **No old paths:**
      - no template includes `zoom/partials/error_summary.html`, `zoom/partials/field.html`, `zoom/partials/field_error.html` or `zoom/partials/choice_group_head.html` (a pytest scan);
      - no template under `templates/accounts/` or `templates/registration/`, and not `templates/403.html`, references `zoom/` at all (D1).
    - **The move changes nothing for `zoom`:** brief 005's form, approve and reject criteria (7, 36, 43) and brief 008's form criteria keep passing unchanged.
30. **The field partial's help is a `<div>` (Design D.9 items 3 and 4).**
    - **The element:** `partials/field.html` renders help as `<div class="field__help" id="<name>-help">`. The class and id are unchanged, so every existing `aria-describedby` still resolves. The tests from briefs 005 and 008 that check `id="<name>-help"` pass unchanged.
    - **Valid HTML:** on `accounts:staff_add`, the password rules list (`<ul>`) sits inside `div#password1-help`. No page in this brief contains a `<ul>` inside a `<p>`: a test parses each page with `html.parser` and checks the ancestors of every `ul`.
    - **Styling:** `static/css/style.css` has the rule `.field__help ul`, using tokens only. Brief 004's colour-literal guard still passes.

### Added after review round 1, SF1 (2026-09-25): "Only roles they hold" (D13)

**Terms for this section.**

- **Granted permissions** of a user: `User.granted_permissions()`, the set of `"app_label.codename"` from their roles (`groups__permissions`) and their own `user_permissions`. It's computed **whether or not they can sign in**. This matters because Django's `get_all_permissions()` returns an empty set for inactive users, so a switched-off Staff manager would pass any "subset" check and become manageable (and re-enable-able) by a peer.
- **The actor's permissions:** `actor.get_all_permissions()`. The actor is signed in, so they're active.
- **Test set-up:** "SM" is a Staff manager who is **not** in `IT desk`. "SM+IT" is a Staff manager who **is** in `IT desk`.

31. **The rule lives on the model: `User.can_give_role(actor, group) -> bool`.** It's a static or class-level method, because it's about the actor and the group, not the target.
    - True when the actor is a superuser.
    - Otherwise, true exactly when the group's permissions (`"app_label.codename"`) are a subset of `actor.get_all_permissions()`.

    Unit tests with the real groups:

    | Actor | `IT desk` | `Staff managers` | A group with no permissions |
    |---|---|---|---|
    | SM | False | True | True |
    | SM+IT | True | True | True |
    | Superuser | True | True | True |

    The rule covers **giving and removing** a role alike (criterion 32).
32. **The roles field enforces it** (`StaffCreateForm` and `StaffChangeForm`, other people's records).
    - **Rendering:** each role the actor can't give is a **disabled** checkbox that keeps its current state: ticked if the person holds it, unticked if not. The designer should confirm how the disabled state looks. Under its permission names, it shows the reason:

      `You can't give or remove this role, because you don't have all its rights yourself.`

      Roles the actor can give render as normal checkboxes.
    - **`clean_groups`** works out the result like this:
      - roles the actor **can** give follow the POST;
      - roles the actor **can't** give keep their current state. Browsers don't submit disabled boxes, so leaving one out never counts as removing it.
    - **A crafted POST that adds a role the actor can't give** is refused. Nothing is saved, and the page shows the field error:

      `You can only give roles whose rights you have yourself.`

    - **Tests:**
      - SM adds a person, and `IT desk` is disabled and unticked. A crafted `groups=<IT desk pk>` POST gets the error, and no user is created.
      - SM+IT gives `IT desk` successfully.
      - Saving an unrelated change as SM+IT leaves every role unchanged.
      - **The defensive rule:** combined with criterion 34, a role the actor can't give is always unticked on another person's record. If the person's rights are a subset of the actor's, every role they hold can be given. So "keeps its current state" only matters if the roles change between loading the page and posting it. A unit test of `clean_groups` covers it with a bound form whose instance holds a role the actor can't give: the role survives a POST that leaves it out.
33. **A non-superuser can't change their own roles.**
    - **Rendering:** on the actor's own change page, the whole `groups` field is **disabled** (Django's `disabled=True`), so every box shows its current state and nothing posted for it counts. Above the boxes, inside the `Roles` fieldset, a note reads:

      `You can't change your own roles. Ask someone else with Staff and access, or someone with full access, to change them.`

    - **Tests:**
      - a Staff manager's crafted POST to their own record that unticks `Staff managers`, or ticks `IT desk`, saves the other fields but leaves their roles exactly as they were. There's no error, because the field is disabled;
      - they're still able to open `accounts:staff` afterwards.

      This settles the reviewer's open point: nobody can lock themselves out by unticking `Staff managers`.
    - **Superusers** may still change their own roles. Criterion 13's full-access and sign-in guards still apply to them.
34. **Who a non-superuser can open.** This follows criterion 11 as amended.
    - **SM** gets **403** on `staff_edit` and `staff_password` for:
      - another Staff manager;
      - a person in `IT desk`, because `IT desk`'s rights aren't a subset of SM's;
      - a superuser;
      - a **switched-off** Staff manager (the inactive-user trap in Terms).
    - **SM+IT** gets 200 for a plain `IT desk` person, and still 403 for another Staff manager.
    - **The list:** for people the actor can't manage, the name is plain text with no link, just as superusers are shown today (criterion 5).
    - **Opening your own record through the set-password page** (`staff_password` with your own pk) **redirects to `accounts:password_change`** for everyone, instead of letting the user reset their own password without the old one and sign themselves out. This is review round 1, nit 2.
35. **Still a fixed number of queries.** Checking who can be changed, and which roles can be given, must not add a query per row or per role.
    - The list's per-row `can_manage` works from `staff_list()`'s prefetches (`groups__permissions__content_type` and `user_permissions__content_type`) through `granted_permissions()`. Criterion 6's test is extended: 3 people vs 40, a mix of Staff managers, IT desk and plain users, viewed as SM. The query count is equal.
    - The add and change forms' role list (`roles`, D12) gets `can_give` from the prefetched `permissions__content_type`, and criterion 7's query test is extended to cover it.
    - `actor.get_all_permissions()` is Django's cached call: it runs once per request.

## Design decisions needed
<!-- owner: tmd-planner — open questions for the user; "None" if none -->

**None open.** The owner answered on 2026-09-25, taking the recommended default each time. Q1–Q3 are recorded in brief 008 and Q6 in brief 009. The designer's gaps and questions (Design D.11 and D.12) are resolved as follows:

- G1 → D12;
- G2 → D7, amended;
- G3 and G4 → the context contract;
- Q-D1 → D11 and criterion 28;
- Q-D2 → Scope → Follow-ups.

**Owner's answers**

| Q | Question (short) | Owner's answer | Recorded as |
|---|---|---|---|
| Q4 | Who adds staff users and gives them roles? | **An in-app screen, plus a role:** Staff and access, for superusers and a new `Staff managers` role. `createsuperuser` is only for creating the first account | D8 |
| Q4b | How does a new person get their first password? | **The person adding them types a starting password** | D9 |
| Q5 | Remove `django.contrib.admin` entirely? | **Yes, in this brief** | D10 |
| SF1 (review round 1) | How far can a Staff manager's power go? | **"Only roles they hold"** | D8 amendment, D13 |

- **D8 (owner, Q4):**
  - **Who uses Staff and access:** superusers and the new `Staff managers` role (criteria 1–2).
  - **Why a separate role:** the head of IT can then add people and give roles without having full access.
  - **Bootstrap:** `manage.py createsuperuser` creates only the first account on a new install.
  - **Rejected:** a management command, because it goes against "our own screens" and IT couldn't use it.
  - ***Amended after review round 1 (owner, SF1: "Only roles they hold"):*** a Staff manager's power is capped at their own rights:
    - they can give or remove only roles whose rights they already have;
    - they can't change their own roles;
    - they can't change, or set the password of, another Staff manager or anyone with rights they lack.

    Superusers can give anything. **So a head of IT who should give `IT desk` must also be in `IT desk`.** The README says so. See D13 and criteria 31–35.
- **D9 (owner, Q4b): the person adding someone types their starting password.**
  - Django's password rules apply.
  - The adder gives the password to the new person themselves, not by email.
  - The new person can change it under `Change your password`.
  - No email is needed.
  - The sign-in page stays exactly as brief 004 (D18) approved it, with no "forgot your password" link.
- **D10 (owner, Q5): `django.contrib.admin` is removed entirely in this brief.** That covers:
  - `INSTALLED_APPS`;
  - the `admin/` URL;
  - `apps/accounts/admin.py` (brief 008 already removes `apps/zoom/admin.py`);
  - the admin tests;
  - the leftover `django_admin_log` table (criteria 19–21).

  Keeping it installed would leave a back door that bypasses criterion 13's guards.

**Decisions (the planner's)**

- **D1: The screens live in `apps/accounts`,** which owns `User`. `apps/zoom` isn't imported. Roles are read as `Group` rows, so accounts never needs zoom's group names.
- **D2: Use Django's built-in model permissions on `User`** (`view_`, `add_`, `change_user`), which come from `django.contrib.auth` and survive the admin's removal. `delete_user` isn't used (D4).
- **D3: Roles are the existing `Group`s, fixed by migrations.** Each role's help text lists its permission names, so there's no description table and no coupling between apps. There's no group editor: every role so far has exactly the permissions its brief chose, and a screen for editing them would let someone quietly widen access outside any brief. If a permission name reads badly, the owning brief improves its `Meta.permissions` name.
- **D4: Nobody is deleted.** `LinkRequest.decided_by` is `PROTECT`, and "who approved this" has to keep an answer. Switching someone off (`is_active=False`) is the way out. Django's `ModelBackend` already refuses inactive users on sign-in and on every later request.
- **D5: `is_staff` stops meaning anything.** Its only job was letting someone into the admin. The field stays, because it belongs to `AbstractUser`, and removing it would mean a custom user base. No screen reads or sets it, and the sidebar no longer checks it. Its help text from Django still mentions the admin site, and that's accepted, because no screen shows it.
- **D6: Remove what the admin left in the database.** Uninstalling an app doesn't drop its table, so `django_admin_log` would stay with foreign keys to `accounts_user`. The migration drops it and deletes the stale `admin` content types. The admin's edit history is lost, and that's acceptable: production isn't live yet (brief 005's go-live gate), so it only holds dev edits.
- **D7: Use Django's password forms and views** (`UserCreationForm`, `SetPasswordForm`, `PasswordChangeView`) rather than writing our own. They already bring the validators, hashing, session invalidation and `sensitive_post_parameters`.
  - ***Amended after the design review (G2):*** thin subclasses are allowed: `StaffCreateForm`, `StaffSetPasswordForm(SetPasswordForm)` and `OwnPasswordChangeForm(PasswordChangeForm)`. They may change **labels, help text and widget attributes only**, set in `__init__`, to match the pinned D.6 copy.
  - **No logic changes:** they don't override `clean*`, `save`, validators or error messages.
  - **The reviewer checks this:** each subclass's body is `__init__` plus `Meta` only. `StaffCreateForm`'s own `clean_email` and its `actor` handling are the stated exceptions, from criteria 9–10.
- **D11: A friendly `403.html` in the shell, owned by this brief (Design Q-D1; also brief 008's design gap G6).**
  - **Why here:** this brief introduces the roles that decide who is refused, so it's the natural owner. The page applies to every section through Django's default `handler403`, with no code.
  - **Signed-in users** get the shell, with the sidebar shown, because:
    - they're signed in, so the shell's assumptions hold;
    - their sidebar lists only what they may open, which answers "where can I go instead";
    - a bare page would strand them.

    The one button is `Go to Home`. If the sidebar marks an item current (the denied URL's section), that item is one the user can see, so it still tells them where they are.
  - **Signed-out visitors** are redirected to sign in by every login-required view, as before. The public-frame variant only covers a `PermissionDenied` raised outside those views. The template picks its frame with `{% extends user.is_authenticated|yesno:"base.html,public_base.html" %}`, so there's one template and no view.
  - **Privacy:** the page never shows the exception text, because it could name a permission codename.
- **D13: No one can hand out more than they hold (owner, SF1).**
  - **The rule:** two model methods, with the forms and views only calling them (criteria 31 and 34):
    - `User.can_give_role(actor, group)`: the group's rights are a subset of the actor's own; superusers can always give;
    - the tightened `User.can_be_managed_by(actor)`.
  - **Why this shape:** the review found four paths. This rule closes three of them and narrows the fourth:
    - **Closed:** giving yourself `IT desk`, or any role you don't hold.
    - **Closed:** automatically holding roles a later brief adds.
    - **Closed:** resetting a peer's password and signing in as them.
    - **Narrowed, not closed:** handing out `Staff managers`. It's no longer free, but it isn't closed either. *(Corrected after review round 2, nit A.)*
      - **What still works:** a Staff manager holds every right in `Staff managers`, so they can still give that role to anyone whose rights are within their own. That's correct under the owner's rule.
      - **What blocks:** they can't give it to someone who holds more rights than they do.
      - **It's one-way:** once the person holds `accounts.change_user`, they're another Staff manager. The giver can no longer open their record (criteria 11 and 34), so they can't take the role back. **Only a superuser can remove `Staff managers` from someone.** The README says this plainly (see the docs step).

    The rule works without a list of role names in code, so a role added by a later brief is covered automatically.
  - **Giving and removing are treated the same.** A Staff manager without `IT desk` can't strip it from anyone either. The owner's intent is that only people who hold a role manage who has it.
  - **Other Staff managers are off limits to peers**, not just "people with more rights". Two Staff managers with equal rights could otherwise reset each other's passwords, and a password reset is the path to becoming someone else. A superuser manages Staff managers.
  - **Target rights come from their roles, not from `get_all_permissions()`.** Django's backend reports no rights for switched-off users, which would make a switched-off Staff manager look harmless and let a peer re-enable them. `User.granted_permissions()` reads the prefetched roles directly, so the query count stays fixed (criterion 35).
  - **Own roles are read-only for non-superusers.** This uses Django's own `disabled=True` field, so a crafted POST can't change them and no extra code is needed. It also removes the self-lockout the review raised: nobody can untick their own `Staff managers`.
  - **Copy:** the disabled-role reason, the own-roles note and the crafted-POST error are pinned in criteria 32–33. **The designer is asked to confirm the disabled checkbox's visual treatment and where the note sits, but not the words.** Text on disabled controls is exempt from WCAG contrast, but the reason and the note are ordinary text and must meet AA.
- **D12: `roles`, not `role_help` (Design G1, accepted).** A template can't index a dict by a variable without a custom filter, and a custom filter is more code than the fix. The view passes `roles`: a list in form order, one entry per role, with the tick box and its sorted permission names. It's built from the form's `groups` choices over the prefetched queryset, with no extra queries (criterion 7's test).

## MVT plan
<!-- owner: tmd-planner -->

### Models

In `apps/accounts/models.py`:

- **`UserQuerySet(models.QuerySet)`:**
  - `staff_list()`: `prefetch_related("groups")`, ordered by `-is_active`, `last_name`, `first_name`, `username`;
  - `active_superusers()`.
- **`UserManager(django.contrib.auth.models.UserManager.from_queryset(UserQuerySet))`,** set as `User.objects`. This produces an `AlterModelManagers` migration.
- **`User` methods:**
  - `can_be_managed_by(actor) -> bool`;
  - `can_grant_full_access(actor) -> bool` (the actor is a superuser);
  - `access_change_error(*, actor, is_active, is_superuser) -> dict[str, str]`, which returns criterion 13's field errors, or `{}`.
- **`User.clean()`:** trims and lower-cases `email` (criterion 9's uniqueness check is case-insensitive, enforced in the form's `clean_email` against `User.objects.filter(email__iexact=…)`). **Email stays non-unique at the database level**, because Django's `AbstractUser` defines it that way, and changing that is a migration with risk for existing rows. The uniqueness rule is in the form and tested.
- **Migrations:**
  - `0002_alter_user_managers`;
  - `0003_staff_managers_group` (a data migration following `zoom/0002`'s pattern);
  - `0004_remove_admin_leftovers` (criterion 20, D6). It depends on the latest `contenttypes` migration and, for ordering only, `auth`'s.

### URLs and views

In `apps/accounts/urls.py` (namespace `accounts`). All staff views use `LoginRequiredMixin` + `PermissionRequiredMixin` (anonymous users go to login, everyone else without permission gets 403). The edit and password views also deny access when `not target.can_be_managed_by(request.user)`, through `has_permission()`.

| Name | Path | View | Template | Permission |
|---|---|---|---|---|
| `accounts:staff` | `accounts/staff/` | `StaffListView(ListView)`, `paginate_by = 50`, queryset `User.objects.staff_list()` | `accounts/staff_list.html` | `accounts.view_user` |
| `accounts:staff_add` | `accounts/staff/add/` | `StaffCreateView(CreateView)`, `form_class = StaffCreateForm` | `accounts/staff_form.html` | `accounts.add_user` |
| `accounts:staff_edit` | `accounts/staff/<int:pk>/edit/` | `StaffUpdateView(UpdateView)`, `form_class = StaffChangeForm` | `accounts/staff_form.html` | `accounts.change_user` + `can_be_managed_by` |
| `accounts:staff_password` | `accounts/staff/<int:pk>/password/` | `StaffSetPasswordView(FormView)` with `StaffSetPasswordForm(user=target)` | `accounts/staff_password.html` | `accounts.change_user` + `can_be_managed_by` |
| `accounts:password_change` | `accounts/password/` | Django's `PasswordChangeView` (subclass with `SuccessMessageMixin`, `form_class = OwnPasswordChangeForm`, `success_url = reverse_lazy("core:home")`) | `registration/password_change_form.html` | signed in |

- `config/urls.py` loses `from django.contrib import admin`, both `admin.site` lines and `path("admin/", …)` (`tmd-devops`).
- `config/settings/base.py` loses `"django.contrib.admin"` (`tmd-devops`).
- **The 403 page needs no URL or view.** Django's default `handler403` renders `templates/403.html` (criterion 28, D11). `config/urls.py` doesn't set `handler403`.
- **`roles` context (D12):** `StaffCreateView` and `StaffUpdateView` add `roles` in `get_context_data`, from `context["form"]`. The logic is a small helper in `apps/accounts/forms.py`, `role_choices(bound_field) -> list[dict]`, unit-tested. It iterates `form["groups"]` and reads each choice's `choice.data["value"].instance.permissions.all()`. That works because `ModelChoiceIteratorValue.instance` holds the prefetched `Group`. It sorts the permission names.

**Forms** (`apps/accounts/forms.py`):

- **`StaffCreateForm(UserCreationForm)`:**
  - `Meta.fields`: `first_name`, `last_name`, `username`, `email`, `groups`, `is_superuser`.
  - `__init__(…, actor)`:
    - drops `is_superuser` unless `User.can_grant_full_access(actor)`;
    - sets D.6's labels and help, including `password2`'s (G2);
    - sets G3's widget attributes, and removes `username`'s `autofocus`, which `UserCreationForm` adds.
  - `groups` uses `CheckboxSelectMultiple` over `Group.objects.order_by("name").prefetch_related("permissions")`.
  - `email` is required, with `clean_email` enforcing case-insensitive uniqueness.
- **`StaffChangeForm(ModelForm)`:**
  - the same fields, labels and widget attributes (G3), plus `is_active`;
  - `clean()` merges `instance.access_change_error(actor=…, …)` into the field errors.
- **`StaffSetPasswordForm(SetPasswordForm)`** and **`OwnPasswordChangeForm(PasswordChangeForm)`:**
  - thin subclasses whose `__init__` only sets D.6's labels, help and `autocomplete` (D7, as amended);
  - no other overrides.

**Information architecture** (`ux-strategy:information-architecture`):

```
SHELL (signed in)
Home                                   [Menu]
[Zoom links]  Link requests · (Timetable, 009) · Zoom accounts      (brief 005 / 008)
[Administration]                       perms.accounts.view_user; always last
└── Staff and access        accounts:staff
    ├── Add a person                    accounts:staff_add
    └── Change Nimali Perera            accounts:staff_edit
        └── Set a new password for …    accounts:staff_password
User menu (top bar): Layout settings · Change your password (accounts:password_change) · Sign out
```

- **Labels:**
  - `Staff and access` names both halves of the job: who can sign in, and what they can do.
  - `Roles` is the everyday word for groups.
  - `Can sign in` / `Switched off` replace "active".
  - `Full access to everything` replaces "superuser".
- **Wayfinding:** the sidebar item, breadcrumb and h1 agree. At most three levels below Home, for the password page.

### Context contract
<!-- The only coupling between backend and frontend: template → exact context variables and their types -->

**Everywhere:** as in brief 005.

**`partials/sidebar.html`:** the parameters are unchanged. The `Administration` group shows when `perms.accounts.view_user`. `Staff and access` is current when `current` is `accounts:staff`, `accounts:staff_add`, `accounts:staff_edit` or `accounts:staff_password`. The `{% if user.is_staff %}` test and `admin:index` are removed.

**`partials/user_menu.html`:** the parameters are unchanged (`user`, `csrf_token`). It gains a link to `{% url 'accounts:password_change' %}`, labelled `Change your password`.

**`accounts/staff_list.html`** (`StaffListView`):

| Variable | Type | Notes |
|---|---|---|
| `people` | page of `User` (`context_object_name`) | Each has `pk`, `__str__`, `username`, `email`, `is_active`, `is_superuser`, `last_login` (aware datetime or `None`), `groups.all` (prefetched: `name`), and `can_manage` (bool, set by the view from `can_be_managed_by(request.user)` for each row; no queries) |
| `page_obj`, `paginator`, `is_paginated` | Django's | |
| `can_add` | bool | The viewer has `accounts.add_user` |

**`accounts/staff_form.html`** (`StaffCreateView` and `StaffUpdateView`):

| Variable | Type | Notes |
|---|---|---|
| `form` | `StaffCreateForm` or `StaffChangeForm` | Fields as in criteria 7 and 12. `is_superuser` is present only for superusers, and the password fields only on add. Labels, help and widget attributes (`autocomplete`, `autocapitalize`, `spellcheck`, no `autofocus`) are already set on the form (G2, G3), so the template renders them as given. `form.groups` is **not** looped over directly; use `roles` |
| `roles` | list of dict, in form order | One entry per role checkbox: `{"choice": BoundWidget (from form["groups"]: .tag, .choice_label, .id_for_label, .data.selected), "permissions": list[str] (that group's permission names, sorted), "can_give": bool (User.can_give_role(actor, group); always True for superusers)}`. Built from the prefetched groups with no extra queries (D12, G1, criterion 35). Replaces the earlier `role_help`. **When `can_give` is False**, the widget already renders `disabled` (the backend sets it per option), and the template prints criterion 32's reason under the permission names |
| `roles_read_only` | bool | True on a non-superuser's own change page (criterion 33). The whole field is disabled, and the template prints criterion 33's note inside the `Roles` fieldset, above the boxes. Per-role reasons are left out, because the note covers them all |
| `person` | `User` or `None` | `None` on add. On change: `__str__`, `date_joined`, `last_login`, `pk` (for the `Set a new password` link) |
| `is_add` | bool | Chooses the h1, the breadcrumb and the button |
| `user` | `User` (from the auth context processor, as everywhere) | **G4:** the template compares `person.pk == user.pk` for the `You` marker and the self-copy in the Password box. This is presentation only. The guards themselves are model rules (criterion 13) |

**`accounts/staff_password.html`:** `form` (`StaffSetPasswordForm`, with G2's labels and help), `person` (`User`: `__str__`, `pk`), and `user` (G4, the same comparison).

**`registration/password_change_form.html`:** `form` (`OwnPasswordChangeForm`, with G2's labels and help). Extends `base.html`, so it uses the shell.

**Widget attributes the backend sets (G3), as listed in the Design section D.11:**

- `username`: no `autofocus`, plus `autocapitalize="none"` and `spellcheck="false"`;
- `email`: `autocapitalize="none"` and `spellcheck="false"`;
- `first_name`, `last_name`, `username` and `email`: `autocomplete="off"`;
- password fields: `autocomplete="new-password"` (`current-password` for `old_password`).

**Shared partials (moved to `templates/partials/`, criteria 29–30):**

- `error_summary.html`: `with form=… lead=… only`, as in brief 005;
- `field.html`: `with field=… type=… only`. It never writes `value` for password widgets, and its help is `<div class="field__help" id="<name>-help">`;
- `field_error.html` and `choice_group_head.html`: parameters unchanged from brief 005.

**`403.html`** (Django's default `handler403`, criterion 28, D11):

- **Context:** the context processors' variables (`user`, `perms`, `request`, `messages`, `tmd_site_name`) plus Django's `exception` (str), which **must not be rendered**.
- **Frame:** it extends `base.html` for signed-in users and `public_base.html` otherwise, through `{% extends user.is_authenticated|yesno:"base.html,public_base.html" %}`.
- **Blocks:** it fills `title`, `heading`, `breadcrumb` (shell only) and `content`.

### Placement and reuse

- **`apps/accounts`:**
  - `models.py`, `forms.py` (new), `views.py` (new) and `urls.py`;
  - three migrations;
  - `tests.py`, or a split `tests/`;
  - **`admin.py` is deleted.**
- **`apps/core/tests.py`:** the deliberate rewrites from criterion 21.
- **`config/`:** `settings/base.py` and `urls.py` (`tmd-devops`).
- **`templates/`:**
  - new: `accounts/*.html`, `registration/password_change_form.html` and `403.html`;
  - moved from `zoom/partials/` to `partials/`: `error_summary.html`, `field.html`, `field_error.html` and `choice_group_head.html`. Every zoom template that includes them is updated, including brief 008's if it has landed (criterion 29);
  - changed: `partials/sidebar.html`, `partials/user_menu.html` and `partials/icons.html` (Design D.9: `users`, `lock`, `slash`; keep `shield`).
- **`static/css/style.css`:** one rule, `.field__help ul`, using tokens only (criterion 30).
- **Reused:**
  - from Django: `UserCreationForm`, `SetPasswordForm`, `PasswordChangeView` and `PasswordChangeForm` (thin label-only subclasses, D7), `UserManager`, `Group`, model permissions, `messages`, `SuccessMessageMixin`, `sensitive_post_parameters`, the default `handler403`, the generic views and the pager;
  - from the project: the shell, the public frame, the moved form partials, and the datagrid, tag, box and options components.
- **Not built:** a group editor, user delete, invitations, password reset, an audit log, a custom permission, or any new dependency.

## Agent plan
<!-- owner: tmd-planner — ordered steps; mark steps that can run in parallel -->

1. **`tmd-ui-designer`:** the Design section. It covers:
   - the list, as a table and as phone cards;
   - the add and change form, with the roles fieldset and each role's help;
   - the guard errors;
   - the set-password page and the change-your-password page;
   - the user-menu item;
   - the sidebar item and its icon.

   This step **may run while 008 is still in steps 2–5**, because it writes only to this brief.
2. **In parallel, after 008 is Done and the Design section is in:**
   - **2a. `tmd-django-backend`:** covers criteria 1–2, 5–6, 7 (the `roles` data and the G2/G3 form work), 8–23, and the 403 tests in 28.
     - The `accounts` model layer, the three migrations, and deleting `apps/accounts/admin.py`.
     - The forms: the thin label-only password subclasses (G2) and the widget attributes (G3).
     - The `roles` context and its helper (G1).
     - The views and URLs.
     - The tests, including the 403 tests and the password-leak tests in 17, plus the rewrites in `apps/core/tests.py`.
   - **2b. `tmd-frontend`:** covers criteria 3–4, 5, 7, 12, 15–17 (markup), 24–25, 28 (the template) and 29–30.
     - The templates, including `403.html`.
     - The sidebar, the user menu and the icons.
     - **The move of the four form partials to `templates/partials/`,** with every zoom include updated.
     - The field partial's password-value fix, and its help as a `<div>`.
     - The `.field__help ul` CSS rule.
   - **2c. `tmd-devops`:** removes `django.contrib.admin` from `base.py`, and the admin lines and route from `config/urls.py` (criterion 19, the settings and URL part).
3. **`tmd-test-verifier`:** criteria 1–30, including `check --deploy`, the prod-stack walk-through (with its step 8 for the 403 page), and a full re-run of brief 005's and 008's zoom tests after the partial move. A FAIL goes back to 2a, 2b or 2c.
4. **`tmd-code-reviewer`:** reviews read-only, with a focus on:
   - the guards (no privilege escalation, no self-lockout, the last superuser);
   - password handling;
   - that nothing depends on the admin any more;
   - thin views.

   Changes go back to step 2, then step 3.
5. **`tmd-docs-writer`:** updates these files, then closes the brief:
   - **README:** bootstrap with `createsuperuser` for the first account only; adding people and giving roles on Staff and access; the two roles (`IT desk`, `Staff managers`) and what each allows; switching people off instead of deleting them; "Change your password";
   - **CLAUDE.md:** the `accounts` app bullet; the sentence in the `zoom` bullet that says users and groups are still in the admin; `Administration` now gated by `accounts.view_user`;
   - **CLAUDE.md "Templates" bullet:** the shared form partials now live in `templates/partials/`, and `templates/403.html` is the one refusal page for every section.
   - **`docs/CHANGELOG.md`:** including the follow-up "one shared date format in `core`" (Scope → Follow-ups).
   - **README, after review round 1 (D8 amendment, D13):**
     - a Staff manager can give or remove only roles whose rights they already have, so **someone who should give `IT desk` must also be in `IT desk`**;
     - nobody but a superuser can change their own roles, or change another Staff manager;
     - a superuser gives any role;
     - **giving `Staff managers` is one-way (review round 2, nit A; D13):**
       - a Staff manager can give that role to anyone whose rights are within their own;
       - once given, that person is a Staff manager, so the giver can no longer open their record, and **only a superuser can take the role away**;
       - so give it with care.
     - **Changelog follow-ups:** review round 2, nits C and D (Scope → Follow-ups).

**Round-1 fix cycle (after review round 1, CHANGES REQUESTED).** This loops back to step 2, then steps 3 and 4.

- **R1. `tmd-ui-designer`** (small; can run in parallel with R2a): confirm the visual treatment only, not the pinned words, of:
  - a disabled role checkbox with its reason (criterion 32);
  - the own-roles note in the `Roles` fieldset (criterion 33);
  - a name shown as plain text in the list for people the actor can't manage (already the superuser pattern).

  Add it as a short D.13 in the Design section.
- **R2a. `tmd-django-backend`:**
  - **SF1:** criteria 31–35, and amended criteria 2 and 11:
    - `User.can_give_role`, `User.granted_permissions` and the tightened `can_be_managed_by`;
    - `staff_list()` prefetches;
    - `clean_groups`, per-option `disabled` on the roles widget, and `disabled=True` for the actor's own roles;
    - `roles` entries gain `can_give`, and the context gains `roles_read_only`;
    - the own-pk `staff_password` redirect;
    - tests for all of these.
  - **Nits:**
    - **1:** fix the `0004` docstring. Either operation order works because the admin model isn't installed. Mention the leftover `django_migrations` rows for `admin`.
    - **2:** the own-pk redirect, now pinned in criterion 34.
    - **3:** make `StaffFormViewMixin` stop relying on base-class order to get `self.person`. Set it in its own `get_object` / `setup`, or merge the two mixins.
    - **4:** normalise the email only on the model (`User.clean()`). Remove the copy in `forms.py`.
    - **5:** define the permission names once, in `models.py`. `views.py` imports them.
    - **7:** add `check_field.html` to `MOVED_PARTIALS` in `tests/test_admin_removed_and_403.py`.
- **R2b. `tmd-frontend`,** after R1 and the contract above:
  - render the disabled roles with the criterion 32 reason under each;
  - render the criterion 33 note when `roles_read_only`;
  - show plain-text names in the list where `can_manage` is false (probably already done).
- **Nit 6** isn't in this cycle. It goes to Scope → Follow-ups (the shared date format).
- **R3. `tmd-test-verifier`:** criteria 1–35 again, with the full suite. Then **R4. `tmd-code-reviewer`**, round 2, focused on SF1.

## Design
<!-- owner: tmd-ui-designer — layout + wireframes, components (existing classes), states, copy, accessibility, progressive enhancement -->

Built inside the chosen f-desk direction (`static/css/style.css`, task 004) and brief 005's shell patterns: the queue (`zoom/queue.html`) for the list, the approve/reject boxes (`zoom/detail.html`) for forms in the shell, and the public request form (`zoom/request_form.html`) for sectioned forms. The field anatomy follows the approved sign-in page: label, then help **above** the control, then the 44px `.input`, with no show/hide button (`docs/design/password-field.md` stays superseded).

**No new component.** Everything below uses existing classes. There are three small, generic additions: a partial move, one field-partial rule, and one CSS rule (D.9). None of them is a new component, so there's no new `docs/design/` file.

### D.1 Navigation: sidebar and user menu

**Sidebar position (exact).** The groups run in this order, top to bottom:

1. `Menu`: Home.
2. `Zoom links` (005/008/009): Link requests, Timetable, Zoom accounts.
3. **`Administration`**: **Staff and access**.

`Administration` comes directly **after** `Zoom links` and is **always the last group**. No brief places anything after it. A staff manager without Zoom permissions sees `Menu`, then `Administration`.

```
┌ sidenav ──────────────────────┐
│ [crest] Technology Mgmt Desk  │
│ MENU                          │
│  ⌂  Home                      │
│ ZOOM LINKS        (005/8/9)   │
│  ▭  Link requests             │
│  …  Timetable · Zoom accounts │
│ ADMINISTRATION   ← last       │
│  [users] Staff and access  ▌   │
└───────────────────────────────┘
```

- **Markup.** Replace the `{% if user.is_staff %}` block with `{% if perms.accounts.view_user %}`. It keeps `<p class="sidenav__group-title" id="nav-admin">Administration</p>` and `<ul class="sidenav__list" aria-labelledby="nav-admin">`. The one item is `<a class="sidenav__link" href="{% url 'accounts:staff' %}">`, with `<svg class="icon sidenav__icon">` using `#i-users` and `<span class="sidenav__label">Staff and access</span>`.
- **Current item.** It gets `aria-current="page"` when `current` is `accounts:staff`, `accounts:staff_add`, `accounts:staff_edit` or `accounts:staff_password`, compared by view name as in 008 D9. `accounts:password_change` marks **no** sidebar item, because it belongs to the user menu.
- **Header comment.** Update the partial's `{# … #}` header: `perms.accounts.view_user` now shows Administration, and `user.is_staff` is no longer read.

**User menu** (`partials/user_menu.html`). Add a new `<li>` between the `Layout settings` item and the `pop__rule` sign-out item:

```html
<li><a class="pop__link" href="{% url 'accounts:password_change' %}"><svg class="icon" aria-hidden="true" focusable="false"><use href="#i-lock"></use></svg>Change your password</a></li>
```

```
┌ Nimali Perera ▾ ───────────┐
│  ⫶ Layout settings  (JS)   │
│  [lock] Change your password│
│ ─────────────────────────  │
│  ⇥ Sign out                │
└────────────────────────────┘
```

- **Without JS.** `Layout settings` stays `hidden`, so `Change your password` is the first item. The menu is a `<details>`, so it opens and closes with no JS.
- **Header comment.** Add the new link to the partial's `{# … #}` header.

**Icons** (`partials/icons.html`). Add three Feather symbols and note them in the header comment:

| Symbol | Used for | Feather content (24×24, the sprite's usual stroke attributes) |
|---|---|---|
| `i-users` | the sidebar item `Staff and access` | `<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path>` |
| `i-lock` | the user-menu item `Change your password` | `<rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path>` |
| `i-slash` | the `Switched off` tag | `<circle cx="12" cy="12" r="10"></circle><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"></line>` |

- **`i-shield` stays in the sprite.** It loses the old `Admin` link and moves to the `Full access` tag (D.2). That keeps the rule that every sprite symbol is used.
- **`i-check-circle`** (for `Can sign in`) is already in the sprite.
- **Coordination with 008.** Brief 008 chooses its own icon for `Zoom accounts`. It should not also use `users`, or two neighbouring sidebar items would look the same. `server` or `monitor` would suit it.

### D.2 The list: `accounts/staff_list.html`

**Desktop (≥992px, sidebar beside the page):**

```
Staff and access                                   Home › Staff and access
┌ box ─────────────────────────────────────────────────────────────────────┐
│ People                                                  [ Add a person ] │ ← box__head: h2.box__title + button--primary (can_add)
├──────────────────────────────────────────────────────────────────────────┤
│ Select a name to change someone's details, roles or password. People     │ ← p.box__lead
│ who leave are switched off, not deleted.                                 │
│ Only someone with full access can change a person who has full access.  │
│                                                                          │
│ 12 people. Showing 1 to 12.                                              │ ← p.result-line
│ Name              Username     Email              Roles           Sign-in        Last signed in │
│ ───────────────────────────────────────────────────────────────────────────────────────────── │
│ Nimali Perera     nimali.p     nimali@…lk         IT desk         ✓ Can sign in  Mon 28 Sep 2026, 9:40 am │
│ You                                               Staff managers                                │
│ Ruwan Silva       ruwan.s      ruwan@…lk          ⛨ Full access   ✓ Can sign in  Never          │
│ (not a link for a staff manager)                                                                │
│ Kasun Fernando    kasun.f      kasun@…lk          No roles        ⊘ Switched off Fri 4 Sep 2026, 2:10 pm │
│                                                  ‹  Page 1 of 1  ›   (only when paginated)      │
└──────────────────────────────────────────────────────────────────────────┘
```

**Phone (≈400px, <768px): a card per row** (the datagrid's existing responsive mode). The box head wraps, so the button sits under the title:

```
Staff and access
Home › Staff and access
┌ box ───────────────────────────┐
│ People                         │
│ [ Add a person ]               │
├────────────────────────────────┤
│ Select a name to change …      │
│ 12 people. Showing 1 to 12.    │
│ ┌ card ──────────────────────┐ │
│ │ Name      Nimali Perera    │ │ ← th scope=row, 44px tap-link
│ │           You              │ │
│ │ Username  nimali.p         │ │
│ │ Email     nimali@polymath… │ │
│ │ Roles     IT desk          │ │
│ │           Staff managers   │ │
│ │ Sign-in   ✓ Can sign in    │ │
│ │ Last      Mon 28 Sep 2026, │ │
│ │ signed in 9:40 am          │ │
│ └────────────────────────────┘ │
│ ┌ card ─ … ──────────────────┐ │
└────────────────────────────────┘
```

**Structure and classes.** Copy the queue's markup pattern: `.datagrid` with explicit table roles, and `.datagrid__label` in every cell.

- **Box.** `<div class="box">`, containing:
  - `<div class="box__head">`, holding `<h2 class="box__title">People</h2>` and, **only if `can_add`**, `<a class="button button--primary" href="{% url 'accounts:staff_add' %}">Add a person</a>`;
  - `<div class="box__body">`, holding `p.box__lead`, `p.result-line`, `div.datagrid-wrap > table.datagrid`, then the `nav.pager`.
- **Caption.** `<caption class="visually-hidden">Everyone with a username for the desk. People who can sign in come first, then by last name.</caption>`
- **Columns** (criterion 5), each `<th scope="col" role="columnheader">`:
  1. **`Name`.** The cell is `<th scope="row" role="rowheader">`, holding a `.datagrid__label` and a `span.datagrid__stack`, which contains:
     - if `person.can_manage`: `<a class="tap-link datagrid__strong break-anywhere" href="{% url 'accounts:staff_edit' person.pk %}">{{ person }}</a>`;
     - otherwise: `<span class="datagrid__strong break-anywhere">{{ person }}</span>`. It is plain text, with no link and no hint;
     - if `person.pk == user.pk`: `<span class="text-muted">You</span>`.

     Use `.datagrid__strong`, not `.datagrid__ref`: the ref class is `nowrap`, and names must wrap at 320px. The link keeps the browser underline as its non-colour cue.
  2. **`Username`.** `<span class="break-anywhere">{{ person.username }}</span>`.
  3. **`Email`.** `<span class="break-anywhere">{{ person.email }}</span>`. When it's empty (only possible for accounts from `createsuperuser`), show `<span class="text-muted">None</span>`. It is **not** a `mailto:` link: this list is for managing access, and a link would add a second 44px target per row.
  4. **`Roles`.** A `span.datagrid__stack`, containing:
     - for superusers, first: `<span class="tag tag--brand"><svg class="icon" …><use href="#i-shield"></use></svg>Full access</span>`;
     - then one `<span>{{ group.name }}</span>` per `person.groups.all` (each on its own line: plain text, no tag, because a role isn't a status);
     - if there are neither: `<span class="text-muted">No roles</span>`.
  5. **`Sign-in`.** Either `<span class="tag tag--ok">` with `#i-check-circle` and `Can sign in`, or `<span class="tag tag--plain">` with `#i-slash` and `Switched off`. Switched off isn't a warning (it's a deliberate state), so it uses the neutral tone. The icon and the word carry the meaning.
  6. **`Last signed in`.** Either `{% include "accounts/partials/when.html" with at=person.last_login only %}`, or `<span class="text-muted">Never</span>`.
- **Pager.** The queue's `nav.pager aria-label="Pages"`, with links built from `{% url 'accounts:staff' %}?page=N` (no other query parameters). It shows only when `is_paginated`.

**`accounts/partials/when.html`** (new partial, not a component). One moment, shown the same way as brief 005's `zoom/partials/when.html` (`Mon 28 Sep 2026, 9:40 am`), without loading zoom's template tags (D1: accounts doesn't depend on zoom):

```django
<time datetime="{{ at|date:'c' }}">{{ at|date:"D j M Y" }}</time>, {{ at|time:"g:i" }} {{ at|date:"A"|lower }}
```

The `Added on` fact uses just the date part: `<time datetime="{{ person.date_joined|date:'c' }}">{{ person.date_joined|date:"D j M Y" }}</time>`.

### D.3 Add and change: `accounts/staff_form.html`

One template, driven by `is_add`. The form sits in one `.box` with a body only, inside `.box__form` (max 640px), like the approve form. Sections are `.formsection` fieldsets, as on the public request form.

**Add, desktop:**

```
Add a person                           Home › Staff and access › Add a person
┌ box ────────────────────────────────────────────────┐
│ ┌ box__form (≤640px) ─────────────────────────┐     │
│ │ [error summary, only after a failed save]   │     │
│ │ About them                                  │     │ ← legend.formsection__title
│ │ First name            Last name             │     │ ← .field-pair
│ │ Like Nimali. You can  Like Perera. Without  │     │
│ │ leave the names…      a name, the desk…     │     │
│ │ [__________]          [__________]          │     │
│ │ Username                                    │     │
│ │ They type this to sign in. Letters, …       │     │
│ │ [____________________]                      │     │
│ │ Work email                                  │     │
│ │ Emails about Zoom requests go here.         │     │
│ │ [____________________]                      │     │
│ │ ─────────────────────────────────────────── │     │
│ │ What they can do                            │     │
│ │ Roles                                       │     │ ← fieldset.options > legend
│ │ Tick every role they need. …                │     │
│ │ ┌─────────────────────────────────────────┐ │     │
│ │ │ ☐ IT desk                               │ │     │ ← label.choice.choice--tall
│ │ │   Can approve or reject Zoom link …     │ │     │   (one span.choice__help per
│ │ │   Can view host account                 │ │     │    permission name)
│ │ └─────────────────────────────────────────┘ │     │
│ │ ┌─────────────────────────────────────────┐ │     │
│ │ │ ☐ Staff managers                        │ │     │
│ │ │   Can add user                          │ │     │
│ │ │   Can change user · Can view user       │ │     │
│ │ └─────────────────────────────────────────┘ │     │
│ │ ☐ Full access to everything  (superusers)   │     │ ← label.check + p.check__help
│ │   They can do everything here, …            │     │
│ │ ─────────────────────────────────────────── │     │
│ │ Starting password                           │     │
│ │ Starting password                           │     │
│ │ • Your password can't be too similar …      │     │ ← div.field__help > ul
│ │ [____________________]                      │     │
│ │ Type it again                               │     │
│ │ [____________________]                      │     │
│ │                                             │     │
│ │ [ Add the person ]  Cancel                  │     │ ← .form-actions
│ └─────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────┘
```

**Change, desktop.** The same form, minus the password section, plus a `Sign-in` section, then a second box:

```
Change Nimali Perera                   Home › Staff and access › Nimali Perera
┌ box ────────────────────────────────────────────────┐
│ [error summary]                                     │
│ About them         (as on add)                      │
│ What they can do   (as on add)                      │
│ ─────────────────────────────────────────────────── │
│ Sign-in                                             │
│ ☑ Can sign in                                       │ ← label.check
│   Untick this to switch them off. …                 │ ← p.check__help
│   ⓘ You can't switch off your own sign-in. …        │ ← p.field__error (guard)
│ Last signed in   Mon 28 Sep 2026, 9:40 am           │ ← dl.facts
│ Added on         Mon 7 Sep 2026                     │
│                                                     │
│ [ Save changes ]  Cancel                            │
└─────────────────────────────────────────────────────┘
┌ box ────────────────────────────────────────────────┐
│ Password                                            │ ← h2.box__title
├─────────────────────────────────────────────────────┤
│ We never show passwords. If they've forgotten       │ ← p.box__lead
│ theirs, set a new one and give it to them yourself. │
│ [ Set a new password ]                              │ ← a.button.button--secondary
└─────────────────────────────────────────────────────┘
```

**Phone (≈400px).**

- `.field-pair` becomes one column below 600px (existing rule), so `First name` sits above `Last name`.
- Every `.input` is full width. The choice rows and the check rows keep their 44px minimum.
- `.form-actions` wraps, putting `Cancel` beside or under the button.
- The `.facts` grid stays two columns (label, then value). The facts column's minimum is 8em, which fits at 320px.
- There is no horizontal scroll: emails and usernames break through `overflow-wrap`, the same as `.input` values.

**Markup, in order.**

1. **Error summary.** `{% include "partials/error_summary.html" with form=form lead=… only %}` (D.9 move), as the first child of `.box__form`. The leads are in D.6.
2. **The form.** `<form method="post" action="" novalidate>` plus `{% csrf_token %}`. `action=""` posts back to the same named URL. The alternative is `{% url %}` with `person.pk`; either works, so the frontend picks one and uses it on both pages.
3. **`<fieldset class="formsection">` `About them`:**
   - `<div class="field-pair">`, containing the field partial for `form.first_name` and for `form.last_name`;
   - the field partial for `form.username`;
   - the field partial for `form.email`.
4. **`<fieldset class="formsection">` `What they can do`:**
   - **Roles.** `{% with field=form.groups %}<fieldset class="options" aria-describedby="[groups-error ]groups-help">`, then the `choice_group_head` partial (legend `Roles`, help, error), then `<div class="options__list options__list--stack">` with one row per choice:
     ```html
     <label class="choice choice--tall" for="{{ choice.id_for_label }}">
       <input type="checkbox" id="…" name="groups" value="{{ choice.data.value }}" {checked} {aria-invalid}>
       <span class="choice__words"><span>{{ choice.choice_label }}</span>
         {% for name in <that role's permission names> %}<span class="choice__help">{{ name }}</span>{% empty %}<span class="choice__help">This role doesn't allow anything yet.</span>{% endfor %}
       </span>
     </label>
     ```
     The permission names are one `choice__help` line each (the `choice__words` column gives them a 4px gap), sorted by name. See **gap G1** for how the template gets them.
   - **Full access.** Rendered only `{% if form.is_superuser %}`, following the 005 `wants_recording` pattern:
     ```html
     <div class="field">
       <label class="check" for="id_is_superuser"><input type="checkbox" id="id_is_superuser" name="is_superuser" {checked} aria-describedby="[is_superuser-error ]is_superuser-help" {aria-invalid}>Full access to everything</label>
       <p class="field__help check__help" id="is_superuser-help">…</p>
       {% include "partials/field_error.html" with field=form.is_superuser only %}
     </div>
     ```
5. **Add only: `<fieldset class="formsection">` `Starting password`.** The field partial for `form.password1`, then for `form.password2`. The partial must never echo a password (D.9).
6. **Change only: `<fieldset class="formsection">` `Sign-in`.**
   - `form.is_active`, marked up exactly like the full-access check above, with id `is_active-help` / `is_active-error`;
   - then `<dl class="facts">`, holding `<dt>Last signed in</dt><dd>{when | Never}</dd>` and `<dt>Added on</dt><dd>{date}</dd>`.

   The facts go after the checkbox because they describe sign-in. They are read-only, and a `<dl>` isn't a form control, so it doesn't break the fieldset.
7. **Actions.** `<div class="form-actions">` holding `<button class="button button--primary" type="submit">`, labelled `Add the person` or `Save changes`, then `<a class="button button--quiet" href="{% url 'accounts:staff' %}">Cancel</a>`.
8. **Change only: the Password box.** After the form's box: `<section class="box" aria-labelledby="password-title">`, holding `.box__head > h2.box__title#password-title` `Password`, then `.box__body` with `p.box__lead` and the link button (copy in D.6).
   - **Your own record** (`person.pk == user.pk`) gets different copy and a link to `accounts:password_change` instead of `accounts:staff_password`. Setting your own password through the staff screen would sign you out, because Django's session hash changes. Criterion 12's `Set a new password` link is unchanged for everyone else.

**Titles and breadcrumbs.**

| Page | `title` / h1 | Breadcrumb after Home |
|---|---|---|
| Add | `Add a person` | `Staff and access` (link to `accounts:staff`) › `Add a person` (current) |
| Change | `Change {{ person }}` | `Staff and access` (link) › `{{ person }}` (current) |

In the h1, wrap the name in `<span class="break-anywhere">`, as `detail.html` does.

### D.4 Set a new password for someone: `accounts/staff_password.html`

```
Set a new password for Nimali Perera
Home › Staff and access › Nimali Perera › New password
┌ box ──────────────────────────────────────────┐
│ ┌ box__form ─────────────────────────────────┐ │
│ │ [error summary]                            │ │
│ │ ┌ notice--note ──────────────────────────┐ │ │
│ │ │ ⓘ This signs them out everywhere.      │ │ │
│ │ │   Their old password stops working …   │ │ │
│ │ └────────────────────────────────────────┘ │ │
│ │ New password                               │ │
│ │ • Your password can't be …                 │ │
│ │ [____________________]                     │ │
│ │ Type it again                              │ │
│ │ Type the new password again, to check …    │ │
│ │ [____________________]                     │ │
│ │ [ Save the new password ]  Cancel          │ │
│ └────────────────────────────────────────────┘ │
└────────────────────────────────────────────────┘
```

- **Classes.**
  - `.box > .box__body > .box__form`;
  - the error summary;
  - `.notice.notice--note`, containing the `#i-info` icon at `icon--xl` and a `.notice__body` with `p.notice__title` and a `p`;
  - the field partial twice (`form.new_password1`, `form.new_password2`);
  - `.form-actions`, holding `button--primary` `Save the new password` and `button--quiet` `Cancel`, which goes to `accounts:staff_edit person.pk`.
- **Breadcrumb.** `Staff and access` (link) › `{{ person }}` (link to `accounts:staff_edit`) › `New password` (current). The h1 is longer than the crumb on purpose: the crumb names the step, and the h1 names whose password it is.
- **Phone.** One column, and the notice wraps. Nothing else changes.

### D.5 Change your password: `registration/password_change_form.html`

In the shell (`extends "base.html"`), with the same frame as D.4.

```
Change your password                     Home › Change your password
┌ box ──────────────────────────────────────────┐
│ ┌ box__form ─────────────────────────────────┐ │
│ │ [error summary]                            │ │
│ │ You'll stay signed in here. Anywhere else  │ │ ← p.box__lead
│ │ you're signed in will ask for the new one. │ │
│ │ Your current password                      │ │
│ │ The one you use to sign in now.            │ │
│ │ [____________________]                     │ │
│ │ New password                               │ │
│ │ • Your password can't be …                 │ │
│ │ [____________________]                     │ │
│ │ Type it again                              │ │
│ │ Type the new password again, to check …    │ │
│ │ [____________________]                     │ │
│ │ [ Change my password ]  Cancel             │ │
│ └────────────────────────────────────────────┘ │
└────────────────────────────────────────────────┘
```

- **Fields.** The field partial for `old_password`, `new_password1` and `new_password2`.
- **Actions.** `button--primary` `Change my password`, and `button--quiet` `Cancel`, which goes to `core:home`.
- **Breadcrumb.** `Change your password` (current).
- **Why the shell, not the sign-in split layout.** This is a task for someone already signed in, reached from the user menu. The sign-in page's field anatomy (label, help above, full-width 44px input, primary button) is reused. Its split brand panel isn't: that frame is for the one page with no shell.

### D.6 Copy (all of it)

**List (`accounts:staff`)**

| Where | Text |
|---|---|
| title / h1 | `Staff and access` |
| box title (h2) | `People` |
| button (`can_add`) | `Add a person` |
| lead | `Select a name to change someone's details, roles or password. People who leave are switched off, not deleted. Only someone with full access can change a person who has full access.` |
| result line | `{n} person.` / `{n} people.`, plus ` Showing {start} to {end}.` when paginated (`{{ n }} {{ n\|pluralize:"person,people" }}.`) |
| caption (hidden) | `Everyone with a username for the desk. People who can sign in come first, then by last name.` |
| columns | `Name` · `Username` · `Email` · `Roles` · `Sign-in` · `Last signed in` |
| your own row | `You`, under your name |
| roles | `Full access` (tag) · group names · `No roles` |
| sign-in tags | `Can sign in` · `Switched off` |
| no email | `None` |
| never signed in | `Never` |
| pager | `Page {n} of {total}`, with hidden `Previous page` / `Next page` |

**Add and change (`staff_form.html`).** Labels and help come from the form (the backend sets them). Where Django's text is kept, the table says so.

| Field / part | Label | Help (above the control) |
|---|---|---|
| section 1 | `About them` | |
| `first_name` | `First name` | `Like Nimali. You can leave the names empty.` |
| `last_name` | `Last name` | `Like Perera. Without a name, the desk shows their username.` |
| `username` | `Username` | `They type this to sign in. Letters, numbers and @ . + - _ only.` |
| `email` | `Work email` | `Emails about Zoom requests go here.` |
| section 2 | `What they can do` | |
| `groups` legend | `Roles` | `Tick every role they need. With no role, they can sign in but only see Home.` |
| each role | `{group.name}` | one line per permission name; `This role doesn't allow anything yet.` if it has none |
| `is_superuser` (superusers only) | `Full access to everything` | `They can do everything here, including changing other people with full access. Give this to as few people as possible.` |
| section 3 (add) | `Starting password` | |
| `password1` | `Starting password` | Django's rules list (`password_validators_help_text_html()`), as it is |
| `password2` | `Type it again` | `Type the same password again, to check for typos.` |
| section 3 (change) | `Sign-in` | |
| `is_active` | `Can sign in` | `Untick this to switch them off. They can't sign in until someone ticks it again. Their past work stays.` |
| facts | `Last signed in` · `Added on` | |
| buttons | `Add the person` / `Save changes` · `Cancel` | |
| Password box title | `Password` | |
| Password box, someone else | lead `We never show passwords. If they've forgotten theirs, set a new one and give it to them yourself.`, button `Set a new password` | |
| Password box, yourself | lead `To change your own password, use Change your password. You'll stay signed in.`, button `Change your password` | |
| error summary lead | add: `We couldn't save this person yet.` · change: `We couldn't save the changes yet.` | |
| success (flash, on the list) | add: `Added {name}. Give them their username and starting password yourself, not by email.` · change: `Saved {name}.` | |

The field errors are exactly as in criteria 9 and 13; Django's own messages stay unchanged. The summary title adds `1 thing needs your attention.` or `{n} things need your attention.` (the partial).

**Set a new password (`staff_password.html`)**

| Part | Text |
|---|---|
| title / h1 | `Set a new password for {name}` |
| crumb | `New password` |
| notice title | `This signs them out everywhere.` |
| notice text | `Their old password stops working straight away. Give them the new one yourself, not by email.` |
| `new_password1` | label `New password`, help = Django's rules list |
| `new_password2` | label `Type it again`, help `Type the new password again, to check for typos.` |
| buttons | `Save the new password` · `Cancel` |
| error summary lead | `We couldn't save the new password yet.` |
| success (flash, on the change page) | `Saved a new password for {name}. Give it to them yourself, not by email.` |

**Change your password (`password_change_form.html`)**

| Part | Text |
|---|---|
| title / h1 | `Change your password` |
| lead | `You'll stay signed in here. Anywhere else you're signed in will ask for the new password.` |
| `old_password` | label `Your current password`, help `The one you use to sign in now.` |
| `new_password1` | label `New password`, help = Django's rules list |
| `new_password2` | label `Type it again`, help `Type the new password again, to check for typos.` |
| buttons | `Change my password` · `Cancel` |
| error summary lead | `We couldn't change your password yet.` |
| success (flash, on Home) | `Your password was changed.` |

Django's own error texts stay, for example `Your old password was entered incorrectly. Please enter it again.` and `The two password fields didn't match.`, as criteria 15 and 16 require.

### D.7 States

| State | List | Add / change | Set new password | Change your password |
|---|---|---|---|---|
| **Default** | table, lead, `Add a person` if `can_add` | empty fields (add); saved values (change) | two empty fields | three empty fields |
| **Empty** | Can't happen: the viewer is always in the list. An out-of-range `?page=` is Django's 404 | n/a | n/a | n/a |
| **Loading** | none; every action is a full page load (no async) | same | same | same |
| **Validation error** | n/a | 200 re-render: the summary first (focused), each invalid field with `aria-invalid="true"`, and `p.field__error` (alert-circle + words) under it; for checkboxes, under the help. Typed values are kept **except the passwords**, which come back empty | same, with both password fields empty | same, with all three empty |
| **Guard error** (criterion 13) | n/a | shown like any field error, on `Can sign in` or `Full access to everything`, with the summary linking to that checkbox. The box shows what was posted, so the checkbox shows the state the user asked for next to the reason it was refused. Nothing is saved | n/a | n/a |
| **Server error** | Django's 500 page; `ATOMIC_REQUESTS` means nothing half-saves | same | same | same |
| **Success** | shows the add/change flashes after redirect (`flash--ok`, `role="status"`) | redirects to the list | redirects to the change page with its flash | redirects to Home with its flash |
| **No permission** | sidebar group hidden (`perms.accounts.view_user`); a direct URL gives 403 (criterion 2); anonymous users are sent to sign in with `next` | names the viewer can't manage aren't links; `is_superuser` isn't rendered for non-superusers | 403 for a superuser target when the viewer isn't one | any signed-in user |
| **Switched-off person** | `Switched off` tag; sorted after everyone who can sign in | the checkbox is unticked; ticking it and saving restores sign-in | still allowed (for example, set a password before switching them back on) | n/a (they can't sign in) |

### D.8 Accessibility

- **Landmarks and headings.** The shell provides `main#main`, the `Main` nav and the `Breadcrumb` nav, and each page has exactly one h1 (the `heading` block).
  - List: h1 `Staff and access` → h2 `People`.
  - Add: h1 only; the sections are `<fieldset>`/`<legend>`, not headings, as in `form-section.md`.
  - Change: h1 → h2 `Password`.
  - The two password pages: h1 only.
- **Tables.** A `<caption>` (visually hidden) and `<th scope="col">`. `Name` is `<th scope="row">`. The explicit `role` attributes stay, so the phone card layout still reads as a table.
- **Labels, help and errors.** The field partial wires it all:
  - `label for`;
  - `p#<name>-help`, or `div#<name>-help` (D.9);
  - `aria-describedby="<name>-help"`, which becomes `"<name>-error <name>-help"` with `aria-invalid="true"` when invalid.
  - Checkboxes (`is_active`, `is_superuser`) do the same by hand, as in 005's `wants_recording`.
  - The `Roles` group: `<fieldset class="options">`, whose `<legend>` is `Roles`, with `aria-describedby` on the fieldset and `aria-invalid` on each checkbox when invalid.
  - Each role's permission lines are inside its `<label>`, so they're part of that checkbox's name. This is the same as the host-account radios in 005.
- **Autocomplete and input hints** (set as widget attributes by the backend; see G3):
  - `first_name`, `last_name`, `username` and `email` on the staff forms: `autocomplete="off"`, because they describe someone else, not the viewer;
  - `username` and `email`: also `autocapitalize="none"` and `spellcheck="false"`;
  - all new-password fields: `autocomplete="new-password"`;
  - `old_password`: `autocomplete="current-password"`.
- **Autofocus.**
  - **None on the staff add and change forms.** Django's `UserCreationForm` puts `autofocus` on `username`, which would skip past `First name`, so the form must drop it.
  - `old_password` keeps Django's autofocus: it's the first field, and the page exists only to fill it.
  - After a failed submit, `app.js` moves focus to the error summary (`data-error-summary`), which is what criterion 25 asks for.
- **Focus after a redirect.** On success, the page loads normally: focus starts at the top of the document, the skip link comes first, and the `flash` (`role="status"`) is the first thing after the h1 in `main`. This matches brief 005.
- **Focus order.** DOM order is visual order. The staff form runs: fields top to bottom, then primary button, then `Cancel`, then (change) the `Set a new password` button. The list runs: `Add a person`, then the name links row by row, then the pager.
- **Touch targets.**
  - Buttons, inputs, `.choice` rows, `.check` rows and `.pop__link`: `--target`, 44px.
  - Name links: `.tap-link`, 44px below 768px.
  - Pager links: 44×44.
  - At ≥768px, the name links are inline text in a row at least 44px tall. This is the same trade-off as 005's queue reference links.
- **Status is never colour alone.**
  - `Can sign in`: check-circle plus the word;
  - `Switched off`: slash plus the word;
  - `Full access`: shield plus the word;
  - field errors: alert-circle plus the words;
  - the summary: alert-octagon plus the title.
- **Contrast.** Every colour pair is an existing, measured token pair: tags ok, plain and brand; `notice--note`; `notice--bad`; `--c-muted` help text. No new colours.
- **No password leaks in markup.** Password inputs never carry a `value` (D.9), in either colour mode or error state.

### D.9 Implementation notes for the frontend (generic changes, no new component)

1. **Move the shared form partials together.** The brief moves `zoom/partials/error_summary.html` to `templates/partials/error_summary.html`. The accounts templates also need `field.html`, `field_error.html` and `choice_group_head.html`, and D1 says accounts must not reach into zoom's folders. So **move all four** to `templates/partials/` and update every zoom template (and 008's, if it has landed) that includes them. It's the same DRY reason, and they're already generic.
2. **The field partial must never echo a password.** Today, `field.html` writes `value="{{ field.value }}"`, which on a bound `PasswordInput` would render the typed password (criterion 17). Add `and field.widget_type != "password"` to the value condition. This lives in the partial, so no password page can forget it.
3. **The field partial's help becomes a `<div class="field__help" id="<name>-help">`** (was `<p>`). Django's password help is a `<ul>`, and a `<ul>` inside a `<p>` is invalid HTML. The class and id are unchanged, so nothing else moves.
4. **One CSS rule**, in the forms section of `style.css`: `.field__help ul { margin: var(--space-1) 0 0; padding-left: var(--space-5); }`. The list gets the notice lists' indent and sits under the help text. It uses tokens only.
5. **The sprite:** add `users`, `lock` and `slash`, and keep `shield` (D.1).

### D.10 Progressive enhancement

- **With plain HTML and full page loads, everything works:**
  - the sidebar, and the user menu (`<details>`) with `Change your password`;
  - the list, the pager and every form: normal POST, then redirect, then a flash;
  - the error summary (its links are plain in-page anchors);
  - the checkboxes;
  - the Cancel links.
- **What `app.js` adds, through existing hooks only:**
  - `data-error-summary`: focuses the summary after a failed submit;
  - `data-flash-close`: shows the close button on flash messages;
  - `data-pop`: Escape and outside-click closing of the user menu;
  - `data-settings-open`: reveals `Layout settings`.
- **No new JS and no new `data-*` hooks.** There's no show/hide password button (`password-field.md` stays superseded; bringing it back needs the owner). There's no live password-strength meter, and no confirm dialog for switching someone off: the action is reversible, and the guards stop the dangerous cases.

### D.11 Gaps in the context contract (for the backend)

- **G1: `role_help` can't be read by a template.** The contract gives `role_help` as a dict keyed by group pk, but a Django template can't index a dict with a variable (`role_help[choice.data.value]`) without a custom filter. **Proposed replacement:** `roles`, a list of dicts in form order, each `{"choice": <BoundWidget from form["groups"]>, "permissions": list[str]}` (the permission names, sorted). The view builds it by walking `form["groups"]` and reading `choice.data["value"].instance.permissions.all()` from the prefetched queryset, so there are no extra queries. The template loops over `roles` instead of `form.groups`.
- **G2: Labels and help text on Django's password forms.** D.6 relabels three things:
  - `new_password2` becomes `Type it again`, with a plain help line;
  - `old_password` becomes `Your current password`, with a help line;
  - `password2` on `StaffCreateForm` gets the same treatment.

  This is text only, set in `__init__` of thin subclasses of `SetPasswordForm` and `PasswordChangeForm`, with no behaviour change. D7 says "as they are". If the planner wants D7 read strictly, keep Django's labels; the layout doesn't change.
- **G3: Widget attributes** for `StaffCreateForm` and `StaffChangeForm`:
  - remove `autofocus` from `username`;
  - set `autocomplete="off"` on the four detail fields;
  - set `autocapitalize="none"` and `spellcheck="false"` on `username` and `email`;
  - set every label and help string in the D.6 table (`first_name` and `last_name` get help; the model's defaults have none).
- **G4:** `person.pk == user.pk` is compared in the template in two places: the `You` marker, and the Password box's self copy. It's presentation-only, and `user` is already in every shell context, so nothing needs adding. It's listed so the reviewer isn't surprised.

### D.12 Open questions (none blocking)

- **Q-D1: a friendly 403 page.** A plain or IT user who opens a Staff and access URL directly gets Django's bare `403 Forbidden`. The design doesn't need one for this brief, because nobody sees a link they can't use. But a shell-styled `templates/403.html` would say what to do instead. Suggested copy: `You can't open this page` / `Your roles don't include it. Ask someone who manages Staff and access to add the role you need.` / button `Go to Home`. That page would cover every section, not only this one. Should it go in this brief, or its own?
- **Q-D2: DRY of the date format.** `accounts/partials/when.html` repeats brief 005's display format (`Mon 28 Sep 2026, 9:40 am`) with Django's `date` filters, because accounts mustn't load `zoom_format`. If the owner wants one source, a later change could move the format into `core` and have both apps use it.

### D.13 Role limits (review round 1, SF1; criteria 32–34)

This covers how things look and where they sit. The words are pinned in criteria 32–33 and are used exactly as written. There's still **no new component**. The only addition is one state rule and one element on the existing `.choice` (item 5), using tokens only.

**1. A role the viewer can't give** (`role.can_give` is false, on another person's record or on add).

```
Desktop and phone (the row is full width in both)
┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐  ← .choice.choice--tall, dashed border
  ▢ IT desk                                         ← native disabled checkbox (dimmed by the browser)
│   Can approve or reject Zoom link requests    │  ← .choice__help, unchanged
    Can view host account
│   [lock] You can't give or remove this role,  │  ← .choice__reason: lock icon + words,
    because you don't have all its rights            --c-text, wraps under its own first line
│   yourself.                                   │
└ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
┌─────────────────────────────────────────────┐
│ ☐ Staff managers                            │  ← a role they can give: unchanged
│   Can add user · Can change user · …        │
└─────────────────────────────────────────────┘
```

- **Markup.** The row is a `<div>`, not a `<label>`, so the reason stays **out** of the checkbox's name and becomes its description instead. Nothing on the row can be clicked, so losing the wrapping label costs nothing. The inner `<label>` takes `class="choice__words"` so the name and permission lines still stack.
  ```html
  <div class="choice choice--tall">
    <input type="checkbox" id="{{ choice.id_for_label }}" name="{{ field.html_name }}" value="{{ choice.data.value }}"{% if choice.data.selected %} checked{% endif %} disabled aria-describedby="{{ choice.id_for_label }}-reason"{% if field.errors %} aria-invalid="true"{% endif %}>
    <span class="choice__words">
      <label class="choice__words" for="{{ choice.id_for_label }}"><span>{{ choice.choice_label }}</span>{permission lines, exactly as today}</label>
      <span class="choice__reason" id="{{ choice.id_for_label }}-reason"><svg class="icon" aria-hidden="true" focusable="false"><use href="#i-lock"></use></svg><span>You can't give or remove this role, because you don't have all its rights yourself.</span></span>
    </span>
  </div>
  ```
- **The template writes `disabled` itself.** The rows are hand-written, not `choice.tag`, so the widget's own per-option `disabled` never reaches the page. The condition is `{% if roles_read_only or not role.can_give %} disabled{% endif %}`. The reason and the `<div>` row appear only when `not role.can_give and not roles_read_only`.
- **Its state.** The box shows what the person holds now: ticked or unticked (criterion 32). A ticked disabled row keeps the existing `.choice:has(input:checked)` purple border and tint, so "they have this" still reads at a glance.

**2. Your own roles** (`roles_read_only`, a non-superuser on their own change page).

```
Roles                                                   ← legend (partial)
Tick every role they need. With no role, …              ← p#groups-help (partial)
┌ notice--note ─────────────────────────────────────┐
│ [lock] You can't change your own roles. Ask        │  ← div#groups-note
│        someone else with Staff and access, or      │
│        someone with full access, to change them.   │
└────────────────────────────────────────────────────┘
┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐
  ☑ Staff managers           (purple tint: they hold it)
│   Can add user · …                                │
└ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐
  ▢ IT desk                  (no per-role reason)
│   Can approve or reject …                         │
└ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
```

- **Where it sits.** Inside the `Roles` fieldset: after the `choice_group_head` include, before `.options__list`. The field is disabled, so it can't show an error; the order is legend, help, note, boxes.
- **Markup.** `<div class="notice notice--note" id="{{ field.html_name }}-note">`, holding `<svg class="icon icon--xl" aria-hidden="true" focusable="false"><use href="#i-lock"></use></svg>` and `<div class="notice__body"><p>…criterion 33's note…</p></div>`. There's no `notice__title`, because the note is two short sentences. It uses the lock icon, not info, so it matches the per-role reason: lock means "you can't change this here".
- **The rows** keep the normal `<label class="choice choice--tall">` markup, plus `disabled`. There's no per-role reason and no per-input `aria-describedby`. The note covers them all (the contract).
- **Wiring.** The fieldset's `aria-describedby` becomes `"groups-note groups-help"` when `roles_read_only`, with the note first because it matters more.

**3. The refused crafted POST** (criterion 32's field error on `groups`).

- **Nothing new.** It's an ordinary field error on the `Roles` group, as in D.7:
  - the error summary (`We couldn't save this person yet.` or `We couldn't save the changes yet.`) is focused, and links to `#id_groups_0`;
  - `p#groups-error.field__error` (alert-circle plus the words) sits under the `Roles` help;
  - the fieldset's `aria-describedby` starts with `groups-error`;
  - every box, disabled ones included, gets `aria-invalid="true"`, so each row's border turns to the danger colour (dashed on the locked ones).
- **The summary link.** It may land on a disabled first box (`IT desk` sorts first). A disabled box can't take focus, but the browser still scrolls there, just under the error line, and the next Tab continues from that point. This is acceptable for a case that only a crafted request, or a role change mid-edit, can cause. No special handling.
- **Re-render.** The locked role shows its current state again (criterion 32), next to its reason, so the page explains itself.

**4. List rows for people the viewer can't manage.** Already built as in D.2, and it stays that way: `span.datagrid__strong.break-anywhere` with no link, no icon and no hint, the same as superusers. It's the same at phone width: the card's `Name` row shows plain text, and it isn't a tap target. The `You` marker is unchanged. Your own row is always a link (criterion 11).

**5. The one CSS addition** (forms section of `style.css`, next to `.choice__help`, tokens only):

```css
/* A choice the viewer can't change (brief 010, D.13). The words keep their
   full colours, so they hold AA; only the native control dims. The dashed
   border is the non-colour cue, and the lock icon and words say why. */
.choice:has(input:disabled) {
  border-style: dashed;
  cursor: default;
}

.choice__reason {
  display: flex;
  align-items: flex-start;
  gap: var(--space-1);
  margin-top: var(--space-1);
  color: var(--c-text);
  font-size: var(--fs-help);
  font-weight: var(--fw-regular);
  line-height: var(--lh-body);
}

.choice__reason .icon {
  width: var(--icon-inline);
  height: var(--icon-inline);
  margin-top: var(--icon-nudge);
}
```

**Contrast.**

- **Never use `opacity`, a grey-out or `color: GrayText` on a locked row or its words.** WCAG exempts only the disabled control itself. The name, permission lines, reason and note are ordinary text and must hold AA.
- **The pairs** are all existing tokens:
  - name: `--c-text` on `--c-surface`;
  - permission lines: `--c-muted` on `--c-surface`, about 5.6:1 light and 5.3:1 dark;
  - the reason: `--c-text`, not muted, so it reads above the permission lines. Its icon and `margin-top` set it apart as well;
  - on a ticked row: the existing checked-choice pairs on `--c-primary-soft`;
  - the note: `notice--note`, an existing measured pair.
- **The ticked state.** The native disabled checkbox is exempt. Its "held" state is also carried by the ticked row's tint and by the screen-reader state, so no one depends on the dimmed tick alone.

**What screen readers announce.**

- **A locked role**, in browse mode or on reaching it:
  > "IT desk, Can approve or reject Zoom link requests, Can view host account, check box, not checked, unavailable. You can't give or remove this role, because you don't have all its rights yourself."

  The name comes from the inner `<label>`, and the description from `aria-describedby`. The reason also sits in reading order right after the label, so it's read even where a screen reader skips descriptions.
- **Tab skips disabled boxes** (native `disabled`), so a keyboard user moves from the last role they can give straight to `Full access` or the next section. That's intended: there's nothing to do on a locked row. The reason is visible text, and it's read in reading order.
- **Your own page:** the note is read when entering the group, through the fieldset's description, and in reading order before the boxes. Each box then reads as "…, check box, checked, unavailable".

**Phone (≈400px, down to 320px).** Nothing changes in layout:

- rows are already full width (`options__list--stack`);
- the reason wraps under its own first line, with the lock pinned to the top line (`align-items: flex-start`);
- the note wraps inside the notice;
- the dashed border stays at `--rule`;
- no horizontal scroll.

The locked rows are not touch targets. The rows that can be ticked keep their 44px minimum.

**Progressive enhancement.** All of this is plain HTML and CSS. No JS, and no new `data-*` hooks. Without JS, disabled boxes aren't submitted, and `clean_groups` keeps their current state (criterion 32).

**Q-D3 (not blocking, copy only; for the owner).** The list's lead (D.6) still ends `Only someone with full access can change a person who has full access.` After D13, a Staff manager will also see plain, unlinked names for other Staff managers and for people with roles they lack, and the lead doesn't explain those. Suggested replacement for that last sentence: `If a name isn't a link, you can't change that person. Ask someone with full access.` It's true for every case, and no test pins the current sentence. Keep the current lead unless the owner agrees.

## Implementation notes
<!-- owners: tmd-devops, tmd-django-backend, tmd-frontend — one sub-heading each: files changed, contract deviations, migrations, new deps (with reason), self-check output -->

### tmd-devops (step 2c)

**Files changed**

- `config/settings/base.py`: `"django.contrib.admin"` is removed from `DJANGO_APPS` (criterion 19, D10). A comment above the list says why it's absent and why `contrib.auth` stays. `auth`, `contenttypes`, `sessions`, `messages`, `staticfiles` and `humanize` are unchanged.
- `config/urls.py`: removed `from django.contrib import admin`, both `admin.site.site_header` / `site_title` lines, and `path("admin/", admin.site.urls)`. Added a module docstring saying there's no admin route and that `403.html` comes from the default `handler403`, so no `handler403` is set. `settings.SITE_NAME` is still used, by `apps/core/context_processors.py`.
- `dev.py`, `test.py`, `prod.py`, `compose.yaml`, `compose.dev.yaml`, the `Dockerfile`, `docker/**`, `.env.example` and `requirements/**` don't mention the admin, so none of them changed.

**`django_admin_log` (criterion 20, D6).** The brief gives this to `tmd-django-backend` as the `accounts` migration `0004_remove_admin_leftovers`. It runs `RunSQL("DROP TABLE IF EXISTS django_admin_log")`, deletes `ContentType` rows with `app_label="admin"`, and has a no-op reverse. Devops has no settings or compose part in it:
- `DJANGO_MIGRATE=1` in `compose.yaml` makes the entrypoint apply it on the next start of either stack;
- no `down -v` or volume reset is needed, because it's an in-place `DROP TABLE IF EXISTS`.

When I finished, the migration hadn't landed yet (`apps/accounts/migrations/` held only `0001`). So the dev database still has the table until the backend's migration runs.

**No new env vars.** **No dependency changes.**

**Operational steps for the user**

- There's nothing extra to do. The next `up -d --build` of either stack runs the backend's migrations, including the drop.
- I rebuilt `polymath-tmd:latest` (the prod image) for the check below. The running stack is still the **dev** stack, as I found it.
- I restarted the dev `web` container once: `docker compose -f compose.yaml -f compose.dev.yaml restart web`. The reason was that runserver's autoreloader died with `LookupError: No installed app with label 'admin'` in the moment between the `base.py` edit and the `urls.py` edit, and didn't recover when `urls.py` was touched. Volumes and ports were untouched.

**Self-check output** (2026-09-25; the backend and frontend were still working in parallel)

- `docker compose config --quiet` gave `prod config OK`, and with the dev overlay `dev config OK`.
- `ruff check config` gave `All checks passed!`, and `ruff format --check config` gave `9 files already formatted`.
- Dev container:
  - `python manage.py check` gave `System check identified no issues (0 silenced).`
  - `python manage.py makemigrations --check --dry-run` gave `No changes detected`.
  - `reverse("admin:index")` raised `NoReverseMatch`.
- Over HTTP on 8010 (dev): `/healthz/` 200, `/admin/` 404, `/admin/login/` 404, `/accounts/login/` 200.
- **`check --deploy`, prod settings:**
  - Command: `docker compose build web`, then `ZOOM_PROVIDER=manual docker compose run --rm --no-deps -e USE_HTTPS=True -e DJANGO_MIGRATE=0 web python manage.py check --deploy`. This was a one-off container from the freshly built prod image, so the dev `web` the parallel agents are using wasn't replaced. `DJANGO_MIGRATE=0` kept it off the shared database.
  - Output: `System check identified 1 issue (0 silenced).` The one issue was `security.W021` (accepted), with exit 0. The same image reports `config.settings.prod` and `django.contrib.admin` not installed.
- **`pytest --create-db` (dev container, last snapshot): 5 failed, all others passed.** The five are exactly the criterion 21 rewrites that `tmd-django-backend` owns. Each fails with `NoReverseMatch: 'admin' is not a registered namespace`, which is the expected result of the removal:
  - `test_home_hides_admin_link_from_non_staff`;
  - `test_home_shows_admin_link_to_staff`;
  - `test_home_shows_admin_link_to_superuser`;
  - `test_sidebar_links_resolve_to_named_urls_only`;
  - `test_sidebar_shows_administration_group_only_for_staff`.

  Earlier snapshots failed more tests because the frontend's templates referenced `accounts:*` URLs before the backend had wired them. Those failures cleared while I was running.
- **For the verifier:** criterion 26's `check --deploy` is to be re-run on the real prod stack (`ZOOM_PROVIDER=manual docker compose up -d --build`) once 2a and 2b land, and so is criterion 27 step 7 (`/admin/` 404 on the prod image).

**For `tmd-docs-writer`:**

- The README's "Running with Docker" and "Deploying the image" facts are unchanged by this step.
- The README still points to the Django admin at lines 160–167, in the Zoom access text ("Giving IT staff access: in the Django admin…" and "user accounts are still managed in the Django admin…"). Criterion 22 needs those reworded.

### tmd-django-backend (step 2a)

**Files changed**

- `apps/accounts/models.py`: `UserQuerySet` (`staff_list()`, `active_superusers()`), `UserManager` (Django's `UserManager.from_queryset(UserQuerySet)`, so `create_user` / `createsuperuser` still work), and the `User` rules: `can_grant_full_access(actor)` (a static method, because the add form asks it before a target exists), `can_be_managed_by(actor)`, `access_change_error(*, actor, is_active, is_superuser) -> dict`, and `clean()`, which trims and lower-cases the email. The guard messages are module constants.
- `apps/accounts/forms.py` (new):
  - `StaffCreateForm(UserCreationForm)` and `StaffChangeForm(ModelForm)` share `StaffDetailsMixin`. It holds the D.6 labels and help, the G3 widget attributes (it also drops `username`'s `autofocus`), makes `email` required with the criterion 9 message, adds `clean_email`, sets `groups` to `CheckboxSelectMultiple` over `roles_queryset()`, and removes `is_superuser` unless the actor has full access.
  - `StaffChangeForm` adds `clean_username` (the username is unique in any letter case, as on add) and a `clean()` that turns `access_change_error()` into field errors.
  - `StaffSetPasswordForm` and `OwnPasswordChangeForm` contain only `__init__`, and it only sets labels and help (D7 as amended).
  - The `role_choices(bound_field)` helper builds the `roles` context (D12).
- `apps/accounts/views.py` (new):
  - `StaffListView`, `StaffCreateView`, `StaffUpdateView` and `StaffSetPasswordView`.
  - `OwnPasswordChangeView`, which is `SuccessMessageMixin` + Django's `PasswordChangeView`.
  - `ManagedPersonMixin.has_permission()` checks `change_user` first and `can_be_managed_by` second. So without the permission the answer is 403 before the target is looked up, and a missing target is 404 only for people allowed to manage.
  - `sensitive_post_parameters()` wraps `dispatch` on the add and set-password views.
- `apps/accounts/urls.py`: adds `password_change`, `staff`, `staff_add`, `staff_edit` and `staff_password`. There's no delete URL and no group URL.
- `apps/accounts/admin.py`: deleted.
- **`apps/core/mixins.py` (new): `SignedInPermissionMixin`, moved out of `apps/zoom/views.py`.** The brief doesn't name a home for a shared access mixin, so it goes in `core`, as the main session asked. `apps/zoom/views.py` now imports it from there, and its behaviour is unchanged. Apps still don't import each other's views.
- **Tests.** `apps/accounts/tests.py` became the package `apps/accounts/tests/`:
  - `test_sign_in.py`: the old file's content, unchanged;
  - `conftest.py`;
  - `test_staff_models.py`: criteria 1, 11, 13, 20 and 23. Each guard has its own unit test;
  - `test_staff_views.py`: criteria 2 and 5–18, including the password-leak, logging, `sensitive_post_parameters` and `field.html` source checks from 17;
  - `test_admin_removed_and_403.py`: criteria 19, 22 and 28. It also has scans for 29 and 30 (old partial paths, no `zoom/` in the accounts, registration and 403 templates, no `<ul>` inside a `<p>`, the `.field__help ul` rule), added because they're cheap and nobody else writes Python tests.
- `apps/core/tests.py`: the rewrites from criterion 21. There are three `Staff and access` link tests. The sidebar tests now assert `accounts:staff`. Three tests are new: the template scan from criterion 3 (no `admin:index`, no `is_staff`), `aria-current` on all four staff pages with `Administration` last, and the criterion 4 user-menu order.

**Context contract, as implemented.** No deviations.
- `staff_list.html` gets `people` (each row has `can_manage` set), `page_obj`, `paginator`, `is_paginated` and `can_add`.
- `staff_form.html` gets `form`, `roles` (a list of `{"choice": BoundWidget, "permissions": [sorted names]}`), `person` (`None` on add) and `is_add`.
- `staff_password.html` gets `form` and `person`. `password_change_form.html` gets `form`.
- **Bug found and fixed while wiring this up.** `UpdateView` names its object after the model, which here is `user`. That silently overwrote the auth context processor's `user`, so the shell and the G4 `person.pk == user.pk` check saw the person being edited instead of the viewer. `StaffFormViewMixin` now sets `context_object_name = "person"`. A test asserts that `context["user"]` is the viewer on the change page.
- **On change, `person` is the stored row.** The form edits a `copy.copy()` of it, so after a refused save the h1 and the guard message still name the person as saved, not as typed.

**Guards (criterion 13): decisions worth reviewing**
- When a field is guarded by both the self rule and the last-superuser rule, the self message wins. A signed-in superuser changing another superuser means two active superusers exist, so the last-superuser message can't be reached through the screens. It exists as a model rule and has unit tests (called with `actor=None`), and it protects any future caller.
- **Race protection.** The last-superuser check locks the whole active-superuser pool with `select_for_update()`, in pk order. Two superusers switching each other off at the same moment can't both succeed. The check therefore has to run inside a transaction; requests always do (`ATOMIC_REQUESTS`), and the docstring says so.
- **A staff manager's `is_superuser` POST is ignored.** The field isn't in their form, so the stored value is passed to the rule.

**Migrations**
- `0002_alter_user_managers`: generated, `AlterModelManagers`.
- `0003_staff_managers_group`: follows `zoom/0002`'s pattern. It uses `get_or_create` for the content type, the three permissions and the group; its reverse deletes the group.
- `0004_remove_admin_leftovers`:
  - it deletes the `admin` `ContentType` rows *first*, which cascades to their permissions and group links, and *then* runs `DROP TABLE IF EXISTS django_admin_log`. The order matters: on a database whose migration state still knows `LogEntry`, the cascade would otherwise hit a table that's already gone;
  - both reverses are no-ops;
  - it's been applied to the dev DB. `SHOW TABLES LIKE 'django_admin_log'` is empty, and no `admin` content types remain.

**Dependencies and settings:** none. Devops made the `INSTALLED_APPS` and `config/urls.py` changes.

**Self-check** (dev container, 2026-09-25, after the frontend's templates and devops's removal had landed)
- `ruff check .` gave `All checks passed!`, and `ruff format --check .` gave `79 files already formatted`.
- `pytest --create-db` gave **`526 passed`**.
- `python manage.py makemigrations --check --dry-run` gave `No changes detected`.
- `python manage.py check` gave `System check identified no issues (0 silenced)`.
- **Intermittent zoom failures, not caused by this change.** In 3 of about 8 full runs, a handful of `apps/zoom` tests failed or errored (for example `test_approve_refuses_an_overlapping_booking_on_the_same_account` and `test_queue_pages_at_25`). A different set failed each time, once with `apps/zoom` run on its own, and the next runs passed cleanly, including `-x` three times in a row.
  - I think the likely cause is other agents running pytest against the same `test_<db>` MySQL database while I was, since `--create-db` from one run drops the database under another. That's inferred, not proven.
  - No `apps/accounts` or `apps/core` test ever failed.
  - The verifier should re-run the suite when nothing else is running.

#### Review round 1 fixes (step R2a: SF1 / D13, criteria 2, 11, 31–35; nits 1–5 and 7)

**Files changed**

- **`apps/accounts/models.py`:**
  - `VIEW_USER_PERMISSION`, `ADD_USER_PERMISSION` and `CHANGE_USER_PERMISSION` are defined here, once. `views.py` imports them (nit 5).
  - `permission_labels(permissions)` is a module helper. It turns `Permission` rows into `"app_label.codename"`, the shape `get_all_permissions()` uses.
  - **`UserQuerySet.with_granted_permissions()`** prefetches `groups`, `groups__permissions__content_type` and `user_permissions__content_type`. `staff_list()` now builds on it (criterion 35).
  - **`User.can_give_role(actor, group)`** is static (criterion 31). A superuser can give any role. Anyone else can give a role only when its labels are a subset of `actor.get_all_permissions()`. With no actor, only a role with no permissions passes.
  - **`User.granted_permissions()`** returns the labels from the person's roles and their own `user_permissions`, whether or not they can sign in. It reads only the prefetches.
  - **`User.can_be_managed_by(actor)` is tightened** (criterion 11, amended):
    - a superuser can manage anyone;
    - anyone else needs `change_user`, and then can manage their own record, or someone who isn't a superuser, doesn't hold `change_user` in `granted_permissions()`, and whose granted permissions are a subset of the actor's.
- **`apps/accounts/forms.py`:**
  - `roles_queryset()` now prefetches `permissions__content_type`.
  - **`RoleCheckboxes(CheckboxSelectMultiple)`** marks each option in `locked` as `disabled`. Django can only disable a whole field.
  - `StaffDetailsMixin.set_up_staff_fields()` evaluates the roles once. It works out `givable_role_pks` with `User.can_give_role` and sets `widget.locked` to the rest. The widget renders from the same cached rows, so there's no extra query.
  - **`clean_groups`** (criterion 32):
    - a disabled field (your own roles) is returned as Django gives it;
    - otherwise, posting a role that can't be given and isn't already held raises `ROLE_NOT_YOURS`, the pinned copy;
    - the saved roles are `(posted ∩ givable) ∪ (held − givable)`.
  - **`StaffChangeForm.__init__`** sets `fields["groups"].disabled = True` and `roles_read_only = True` on a non-superuser's own record (criterion 33). `roles_read_only` defaults to `False` on the mixin.
  - `role_choices()` adds `can_give` to each entry, from `form.givable_role_pks`.
  - **`clean_email`** no longer trims or lower-cases (nit 4). `EmailField` already strips spaces, `iexact` ignores letter case, and `User.clean()`, run by the model form, stores the lower-cased form.
- **`apps/accounts/views.py`:**
  - **Constants come from `models.py`** (nit 5).
  - **`StaffFormViewMixin` no longer reads `self.person`** (nit 3). It adds `roles`, `roles_read_only` (from `form.roles_read_only`) and `is_add`. `StaffCreateView` sets `person=None`, and `StaffUpdateView` sets `person=self.person`, each in its own `get_context_data`. The result doesn't depend on base-class order.
  - `ManagedPersonMixin.person` loads through `User.objects.with_granted_permissions()`.
  - **Own-record redirect** (criterion 34, nit 2): on your own pk, `StaffSetPasswordView.get` / `post` redirect to `accounts:password_change`. They run after the mixin's permission check, so plain and IT users still get 403 there (criterion 2's table). A POST changes nothing.
- **`apps/accounts/migrations/0004_remove_admin_leftovers.py`: docstring only** (nit 1).
  - It now says either order works, because the admin isn't installed, so there's no `LogEntry` to cascade into.
  - It also notes that the `admin` rows in `django_migrations` stay on purpose. If the admin were ever reinstalled, it would need `migrate admin zero --fake`. No operation changed.
- **Tests:**
  - `tests/conftest.py`: new `desk_manager` ("SM+IT") and `desk_manager_client` fixtures.
  - `tests/test_staff_models.py`, new tests:
    - the criterion 31 table;
    - `can_be_managed_by` for SM and for SM+IT;
    - a switched-off Staff manager being off limits;
    - a directly granted permission counting;
    - `granted_permissions()` contents and its zero-query guarantee over `staff_list()` rows;
    - the prefetch lookups;
    - a view-only viewer managing nobody, including themselves.
  - `tests/test_only_roles_they_hold.py` (new) covers criteria 32–35 through the real views:
    - disabled, unticked `IT desk` for SM, and `can_give`;
    - a crafted add or change refused with the pinned error, saving nothing;
    - SM+IT giving `IT desk`, and an unrelated save as SM+IT leaving roles unchanged;
    - the `clean_groups` defensive unit test;
    - own roles read-only, with crafted untick / tick saving other fields, keeping roles and still opening `accounts:staff`;
    - a superuser changing their own roles;
    - SM 403 on edit and password for another SM, an IT person, a superuser and a switched-off SM;
    - a peer can't re-enable a switched-off SM;
    - SM+IT 200 / 403;
    - list links;
    - the own-pk redirect (GET and POST, SM and superuser) versus 403 for plain and IT users;
    - the list query count as SM (3 vs 40, mixed roles, some with a direct permission);
    - the add and change page query counts with `can_give`.
  - **`tests/test_staff_views.py`, re-targeted, not weakened.** Tests where an SM changed or reset an IT person now use the plain user as the target, or run as the desk manager where the target must be in `IT desk`:
    - switching off, which needs `zoom:queue`;
    - the set-password flows;
    - the password-leak and logging tests;
    - `sensitive_post_parameters`;
    - the add-with-`IT desk` test.

    In the list-context test, `kasun.it` is now `can_manage=False` for SM.
  - `test_a_role_made_in_the_test_gets_a_checkbox…` now finds the checkbox by id, and the label's text separately. The frontend's R2b markup wraps only the words in the label for a locked role, so the input is no longer inside it.
  - `tests/test_admin_removed_and_403.py`: `check_field.html` is added to `MOVED_PARTIALS` (nit 7).
  - `apps/core/tests.py::test_staff_and_access_is_current_on_every_staff_page_and_last` now opens edit and password for another user. On the superuser's own pk, `staff_password` now redirects.

**Context contract, as implemented. No deviation.**
- **`roles`:** each entry is `{"choice", "permissions", "can_give"}`.
- **`roles_read_only`:** a bool on add and change.
- **Disabled boxes, belt and braces:** a role that can't be given also carries `choice.data.attrs.disabled = True` (per-option, from the widget), and so does every box when the field is disabled. The frontend's hand-written rows write `disabled` themselves from `can_give` / `roles_read_only`, so they don't need it. `choice.tag` would render it if ever used.

**Decision worth reviewing**
- **Own record still needs `change_user`.** `can_be_managed_by` answers "yes, their own record" only to someone who has `change_user`. Criterion 11's bullet reads as if the self case stood alone, but criterion 2's table gives plain and IT users 403 on their own pk. The earlier test, where a view-only viewer has no linked names, also expects this. So someone with only `view_user` doesn't get a link on their own row.

**Migrations:** none added. `makemigrations --check` gives `No changes detected`.

**Dependencies and settings:** none.

**Self-check** (dev container, 2026-09-25; I was the only agent running pytest)
- `ruff check .` gave `All checks passed!`, and `ruff format --check .` gave `80 files already formatted`.
- `pytest --create-db` gave **`570 passed`**: the earlier 526, plus 44 new or parametrised cases. It was run three times, all green, with the frontend's R2b templates in place.
- `python manage.py makemigrations --check --dry-run` gave `No changes detected`.
- `python manage.py check` gave `System check identified no issues (0 silenced).`

### tmd-frontend (step 2b)

**Files changed**

- **Moved from `templates/zoom/partials/` to `templates/partials/` (criterion 29, D.9 item 1):** `error_summary.html`, `field.html`, `field_error.html`, `choice_group_head.html`, **and `check_field.html`**.
  - **Why `check_field.html` moved too, beyond the four named.** Brief 008 made it the shared checkbox pattern, and D.3 marks up `is_superuser` and `is_active` "exactly like" it, with the same label, `check__help`, error line and `aria-describedby` wiring. D1 forbids accounts templates from reaching into `zoom/`, so the choice was to copy it or move it. DRY says move. Its markup is unchanged, apart from the `field_error` include path.
  - Every include in `zoom/request_form.html`, `zoom/detail.html` and `zoom/account_form.html` (brief 008's) now points at `partials/…`, and so do the `Partials:` lists in their header comments. `templates/zoom/partials/` keeps only zoom-specific partials. No template references an old path.
- **`partials/field.html`:**
  - **Criterion 17:** the value is written only when `field.value is not None and field.widget_type != "password"`, and a `value` key in widget attrs is skipped too.
  - **Criterion 30:** the help is `<div class="field__help" id="<name>-help">`. The class and id are unchanged.
  - **Also changed:** a widget attribute set to `True` is now written bare, and one set to `False` is left out, as Django's own widgets do. Before, `old_password`'s `autofocus: True` would have rendered `autofocus="True"`. No existing form had a boolean attr, so zoom's markup is unchanged.
  - The header comment is updated.
- **Header comments only:** `partials/field_error.html`, `choice_group_head.html` and `error_summary.html`. They now say "shared by every app since brief 010".
- **New templates:**
  - `accounts/staff_list.html`;
  - `accounts/staff_form.html`, for add and change. The form posts to `{% url %}` (`staff_add`, or `staff_edit person.pk`), not `action=""`;
  - `accounts/staff_password.html`;
  - `accounts/partials/when.html`, as specified in D.2;
  - `registration/password_change_form.html`, in the shell;
  - `403.html`, using `{% extends user.is_authenticated|yesno:"base.html,public_base.html" %}`. The shell variant is a box with the lead and `Go to Home`. The public variant is `p.public__lead` plus a `Sign in` button-link to `{% url 'accounts:login' %}?next={{ request.path|urlencode }}`. `exception` is never rendered.
- **`partials/sidebar.html`:** the `Administration` group is gated by `perms.accounts.view_user`. It holds `Staff and access` (`#i-users`), with `aria-current` on the four staff view names, and it stays last. `user.is_staff` and `admin:index` are gone, and the header comment no longer mentions `is_staff`, so criterion 3's template scan can't trip on it.
- **`partials/user_menu.html`:** `Change your password` (`#i-lock`) sits between `Layout settings` and `Sign out`. The header comment is updated.
- **`partials/icons.html`:** adds `i-users`, `i-lock` and `i-slash`. `i-shield` stays, now used by the `Full access` tag. The header comment is updated.
- **`static/css/style.css`, 5e (Form fields):** one rule, `.field__help ul { margin: var(--space-1) 0 0; padding-left: var(--space-5); }`. It uses tokens only, and there's no new token.
- **`static/js/app.js`:** unchanged. The existing `data-error-summary`, `data-pop` and `data-flash-close` hooks cover these pages.

**Spec deviations**

- **`check_field.html` moved as a fifth partial,** as explained above. This goes beyond criterion 29's list of four, and doesn't conflict with it.
- **`Roles` cell for a superuser with no groups.** It shows only the `Full access` tag, not `Full access` plus `No roles`. D.2 says `No roles` appears only "if there are neither".
- **Everything else follows D.1 to D.9 as written.**

**Context contract gaps:** none left open.

- **Found while checking over HTTP, and already fixed by the backend (see its notes):** `UpdateView`'s default `context_object_name` (`user`) overwrote the viewer. On the change page, the user menu showed the edited person's initials and name, and G4's self copy showed for everyone. After the backend's `context_object_name = "person"` fix, I re-checked over HTTP: the other-person page shows `Set a new password`, and the user menu shows the viewer.
- **Flagged to the backend, and fixed in their test:** criterion 28's anonymous-403 check for "no `data-nav`" matched `data-nav-size` / `data-nav-tone` on `<html>`. The test now uses `\bdata-nav[\s>]`.

**Self-check output** (dev stack, 2026-09-25)

- **`pytest --create-db` (dev container):** 526 tests, all passed (`.` × 526, no `F` or `E`). This includes `test_every_static_reference_in_templates_exists`, the purpose-comment, include-`only`, inline-style, hard-coded-path, sprite and colour-literal guards, and every zoom form test after the partial move.
  - The run was started in a window where no other pytest was running, and checked for overlap while it ran (none).
  - Earlier runs that overlapped with other agents' runs showed random zoom errors on the shared `test_` database, like those the backend notes describe.
- **HTTP on 8010 (dev server).** Temporary users `fe010_*` (a superuser, a plain user, a target and a switched-off user) were created in the dev DB, then deleted afterwards (`(4, {'accounts.User': 4})`). Results:
  - `GET /accounts/staff/` → 200. One h1; the title `Staff and access · …`; `id="nav-admin"`; `Staff and access` has `aria-current="page"` with `#i-users`; `Add a person` is shown; the `Switched off` tag uses `#i-slash`; the user menu has `Change your password`.
  - `GET /accounts/staff/add/` → 200. `div#password1-help` contains the `<ul>`, `Full access to everything` is shown (superuser), and the password fields have `autocomplete="new-password"`.
  - Add, posted with mismatched passwords → 200:
    - the summary reads `We couldn't save this person yet.`, and `aria-invalid="true"` is set;
    - the username is kept (`value="fe010_new"`);
    - `Tr0ub4dor-3xyz-Q` is absent;
    - no `type="password"` input has a `value`.
  - `GET` change, another person → 200. `Set a new password`, `Can sign in` and `Added on` are shown. Change, yourself → 200, with the self copy `To change your own password…`.
  - Change yourself, posting with `Can sign in` unticked → 200, with the error `You can't switch off your own sign-in. …` and the summary `We couldn't save the changes yet.`
  - Set-password `GET` → 200, with the notice `This signs them out everywhere.` Posting a mismatch → 200, with `We couldn't save the new password yet.`, no leak and no password value.
  - `GET /accounts/password/` → 200, with `Your current password`. Posting a wrong old password → 200, with `We couldn't change your password yet.` and Django's error, no leak and no password value.
  - Plain user, `GET /accounts/staff/` and `/zoom/accounts/` → **403**. The page shows the h1 `You can't open this page`, the copy, `Go to Home` and `<nav class="sidenav__menu"`, with no `nav-admin`. Neither `accounts.change_user` nor `view_hostaccount` appears.
  - Plain user, Home → 200: no `Administration` group, and `Change your password` is in the menu.
  - Anonymous, `GET /accounts/staff/` → redirects to `/accounts/login/?next=/accounts/staff/`.
- **Anonymous 403 variant.** Rendered through the template with an `AnonymousUser`: the public frame with one h1, `Sign in to see this page.`, and `href="/accounts/login/?next=/accounts/staff/"`. No sidebar.
- **HTML structure.** A scratch `html.parser` pass over all eight rendered states found no `<ul>` inside a `<p>`, no password `value`, and exactly one h1 each.
- **Not done here; left to the verifier (criterion 27):** screenshots at 320, 400, 1024 and 1440 in both colour modes, and the prod-image walk-through.

#### Review round 1 fixes (step R2b: criteria 32–34 markup, D.13, Q-D3)

**Files changed**

- **`templates/accounts/staff_form.html`, the `Roles` group:**
  - **A role the viewer can't give** (`not role.can_give and not roles_read_only`): the row is `div.choice.choice--tall` rather than a label. The input has `disabled` and `aria-describedby="<id>-reason"` (plus `aria-invalid` when the field has errors). The inner `label.choice__words[for]` holds the name and permission lines, and `span.choice__reason#<id>-reason` follows it, holding `#i-lock` and criterion 32's words exactly. The box keeps `checked` from `choice.data.selected`.
  - **Your own roles** (`roles_read_only`): `div.notice.notice--note#groups-note` (`#i-lock` at `icon--xl`, `div.notice__body > p` with criterion 33's words exactly) sits after the `choice_group_head` include and before `.options__list`. Every row keeps the normal `label.choice` markup plus `disabled`. There are no per-role reasons and no per-input `aria-describedby`.
  - **The fieldset's `aria-describedby`** is `[groups-error ][groups-note ]groups-help`, so on your own page it's `groups-note groups-help`.
  - **The template writes `disabled` itself,** as D.13 says: the rows are hand-written, so the widget's per-option attribute never reaches the page.
  - The header comment now lists `can_give`, `roles_read_only` and the new partial.
- **`templates/accounts/partials/role_words.html` (new):** a role's name plus its `span.choice__help` permission lines (or `This role doesn't allow anything yet.`), `with name=… permissions=… only`. The normal and locked row shapes both need exactly this markup, so it's written once instead of twice in the loop.
- **`templates/accounts/staff_list.html`, Q-D3 (main-session decision):** the lead's last sentence is now `If a name isn't a link, you can't change that person. Ask someone with full access.` The row markup for unmanageable people (plain `span.datagrid__strong`) was already as D.13 item 4 describes, so it's unchanged.
- **`static/css/style.css`, 5e (Form fields), after `.choice__help`:** `.choice:has(input:disabled)` (dashed border, default cursor), `.choice__reason` and `.choice__reason .icon`, as in D.13 item 5. They use existing tokens only; there's no new token and no colour literal.
- **`static/js/app.js`:** unchanged. There's no new `data-*` hook, and everything is plain HTML and CSS.

**Spec deviations**

- **`flex: none` on `.choice__reason .icon`.** It isn't in D.13's CSS. Without it, the 14px lock can shrink in the flex row when the reason wraps on a 320px screen. It's layout only.
- **`role_words.html` is a new partial,** used only on this page, to avoid writing the name and permission lines twice. It isn't a component, and it has no CSS of its own.
- **D.6's lead copy:** the list lead no longer matches the D.6 table row (line "lead"). That's the Q-D3 decision; the docs writer may want to update D.6 when closing the brief.

**Context contract gaps:** none. `roles[*].can_give` and `roles_read_only` arrive as the contract says. The contract's note that "the widget already renders `disabled`" doesn't apply to hand-written rows. D.13 already covers this, and the template writes it.

**Self-check output** (dev stack, 2026-09-25; I didn't run `pytest --create-db`, to keep off the backend's shared test DB)

- **`pytest --reuse-db apps/accounts apps/core`** (dev container, after the backend's R2a notes landed) → **`278 passed in 11.25s`**. That covers the backend's new R2a tests against these templates, plus `test_every_static_reference_in_templates_exists` and the purpose-comment, include-`only`, inline-style, hard-coded-path, sprite and colour-literal guards, which also cover the new `role_words.html` partial.

- **In-process render (dev container, `manage.py shell`, test users created inside a rolled-back transaction), with the backend's live context:**
  - Add, as SM → 200. There's exactly one `div.choice.choice--tall` (IT desk), with `disabled aria-describedby="id_groups_0-reason"`, the reason span with that id, the full reason text and `#i-lock`. Staff managers stays a normal `label.choice`. The fieldset's `aria-describedby="groups-help"`, and there's no `groups-note`.
  - Change another plain person, as SM → 200. The same single locked row, and no note.
  - Change yourself, as SM → 200. `aria-describedby="groups-note groups-help"`; `div#groups-note` has criterion 33's exact text and `#i-lock`. Both boxes are `disabled` and Staff managers is `checked`. There's no `div.choice` row and no `choice__reason`.
  - Change another person, as a superuser → 200. Nothing is disabled, with no locked row and no note.
  - List → 200, with the new lead sentence.
- **HTTP on 8010 (dev server), with temporary users `r2bhttp_sm` (Staff manager) and `r2bhttp_t` (plain), deleted afterwards (`(3, {'accounts.User_groups': 1, 'accounts.User': 2})`):**
  - `GET /accounts/staff/` → 200, with the new lead sentence.
  - `GET /accounts/staff/add/` → 200, with the locked IT desk row and its reason.
  - `GET /accounts/staff/<other>/edit/` → 200, with the locked IT desk row and its reason.
  - `GET /accounts/staff/<self>/edit/` → 200, with `aria-describedby="groups-note groups-help"`, both inputs `disabled` (Staff managers `checked`), one `#groups-note`, and no `choice__reason`.
  - `GET /static/css/style.css` → 200, with the new rules present.

## Verification
<!-- owner: tmd-test-verifier — verdict, criteria → tests table, checklist results, failures -->

**Verdict: PASS**

**Intermittent zoom failures — settled.** `pytest --create-db` (dev stack, nothing else running) 3 times in a row: **526 passed** every time, no flakes. `pytest apps/zoom/tests/test_race.py` 3 more times: **4 passed** every time. This confirms the backend's and frontend's hypothesis: the sporadic zoom failures they saw were `test_polymath_tmd` being dropped/recreated by another agent's parallel `--create-db` run, not a real defect. No file is at fault; no owning agent to send this to.

**Coverage table (30/30 criteria, all covered by an automated test and independently exercised over HTTP on the prod image):**

| # | Criterion | Evidence |
|---|---|---|
| 1 | `Staff managers` role, exact perms, reversible/idempotent migration, `IT desk` unchanged | `test_staff_managers_role_holds_exactly_view_add_and_change_user`, `test_it_desk_role_is_unchanged_by_this_brief`, `test_staff_managers_migration_is_idempotent_and_reversible` |
| 2 | Access matrix per page/role | `test_anonymous_visitors_are_sent_to_sign_in`, `test_people_without_staff_permissions_get_403_except_own_password`, `test_staff_manager_opens_every_page_for_a_non_superuser`, `test_staff_manager_gets_403_for_a_superuser_target`, `test_superuser_opens_every_page_even_for_another_superuser`; walked live: anonymous → login redirect, IT user → 403 on `/accounts/staff/` |
| 3 | Sidebar gating, `aria-current`, order, no `admin:index`/`is_staff` | `test_sidebar_shows_administration_group_only_with_view_user`, `test_staff_and_access_is_current_on_every_staff_page_and_last`, `test_no_template_links_the_admin_or_reads_is_staff` |
| 4 | User menu `Change your password` placement, works without JS | `test_change_your_password_sits_between_layout_settings_and_sign_out`; `<details>` menu, no JS needed, confirmed in rendered HTML |
| 5 | List page/table structure, columns, ordering, pager | `test_list_context_orders_people_and_marks_who_the_viewer_may_change`, `test_list_pages_at_fifty`, `test_list_shows_roles_and_full_access_from_prefetched_groups`; screenshot `01-list-1440-light.png` |
| 6 | Query budget | `test_list_query_count_does_not_grow_with_people` |
| 7 | Add form fields, labels, help, widget attrs | `test_add_form_for_a_superuser_has_criterion_7_fields_and_copy`, `test_add_form_widget_attributes`, `test_roles_context_lists_every_group_by_name_with_sorted_permission_names`, `test_add_page_query_count_does_not_grow_with_roles`; screenshot `05-add-errors.png` |
| 8 | Create | `test_add_creates_a_person_who_can_sign_in_with_a_hashed_password` |
| 9 | Validation errors, values kept except passwords | `test_add_validation_errors_save_nothing_and_keep_typed_values`; live: mismatched-password add kept name/username/email, both password fields empty |
| 10 | Non-superuser can't grant full access | `test_add_form_for_a_staff_manager_has_no_full_access_field`, `test_staff_manager_cannot_grant_full_access_with_a_crafted_post`; live: staff manager's add form had 0 `#id_is_superuser` elements |
| 11 | `can_be_managed_by` | `test_superuser_can_manage_everyone`, `test_staff_manager_can_manage_everyone_except_superusers`, `test_people_without_change_user_manage_nobody` |
| 12 | Change form fields, facts, redirect+message | `test_change_form_has_criterion_12_fields_copy_and_context`, `test_change_saves_and_says_so` |
| 13 | Guards (self, last-superuser, ignored `is_superuser`) | `test_you_cannot_switch_off_your_own_sign_in`, `test_a_superuser_cannot_remove_their_own_full_access`, `test_the_only_superuser_cannot_switch_themselves_off`, `test_a_staff_managers_is_superuser_post_is_ignored_without_error`; live: superuser unticking own `Can sign in` → exact guard error, screenshot `12-change-guard-error.png` |
| 14 | Switch off: login fails, session refused, history kept, restorable, no delete | `test_switching_someone_off_ends_their_sign_in_and_session_but_not_their_history`, `test_there_is_no_delete_url_and_no_role_editor`, `test_no_staff_page_has_a_delete_button`; live: switched-off IT user's login attempt showed the login page's existing error, screenshot `09-login-after-switchoff.png` |
| 15 | Set-password page, session invalidation, redirect+message | `test_setting_a_new_password_signs_them_out_and_returns_to_their_page`, `test_set_password_errors_are_djangos`; live: staff manager set a new password for the IT person, their already-open session's next request to `/zoom/requests/` redirected to login |
| 16 | Own password change, stays signed in | `test_changing_your_own_password_keeps_you_signed_in`, `test_a_wrong_current_password_shows_djangos_error`; live: IT person changed their own password and their next request to `/zoom/requests/` was 200, not a login redirect |
| 17 | No password leaks | `test_no_password_comes_back_in_an_error_page`, `test_no_log_record_carries_a_typed_password`, `test_password_views_mark_every_post_parameter_sensitive`, `test_field_partial_never_writes_a_password_value`; live: posted `Tr0ub4dor-3xyz-Q` mismatched on add — absent from the response body, 0 password inputs carried a `value` |
| 18 | Role list is live, no group-editing URL | `test_a_role_made_in_the_test_gets_a_checkbox_with_its_permissions_in_order`, `test_there_is_no_delete_url_and_no_role_editor` |
| 19 | Admin removed | `test_admin_is_not_installed_but_auth_and_friends_are`, `test_admin_url_is_gone`, `test_no_admin_module_or_import_remains`; live on prod image: `/admin/` → 404, `/admin/login/` → 404 |
| 20 | `django_admin_log` dropped, content types removed | `test_admin_leftovers_are_gone_after_migrate`, `test_admin_leftovers_migration_removes_admin_content_types_and_their_links`, `test_admin_leftovers_migration_reverse_is_a_noop_and_drop_is_conditional`; confirmed directly on the prod MySQL database after `migrate`: `SHOW TABLES LIKE 'django_admin_log'` returned no rows |
| 21 | Deliberate core test rewrites | `test_home_hides_staff_and_access_from_an_is_staff_user_without_permissions`, `test_home_shows_staff_and_access_to_a_staff_manager`, `test_home_shows_staff_and_access_to_a_superuser`, `test_sidebar_links_resolve_to_named_urls_only`, `test_sidebar_shows_administration_group_only_with_view_user` all present in `apps/core/tests.py`; `apps/zoom/tests/test_sidebar_zoom_group.py` unaffected |
| 22 | `createsuperuser` bootstrap only | `test_createsuperuser_still_makes_the_first_account`; used live to create the walkthrough's superuser |
| 23 | Thin views / model-layer rules | Code read: `StaffListView.get_queryset` / `StaffCreateView` / `StaffUpdateView` call only `UserQuerySet`/`User` methods, no inline ORM filters |
| 24 | Template rules (headers, `only`, icons, no inline style/hardcoded paths) | `test_every_include_ends_with_only`, `test_no_inline_style_attributes_in_templates`, `test_no_hardcoded_paths_in_href_or_action_attributes`, `test_icons_partial_holds_the_only_symbol_elements`, `test_every_icon_use_references_a_defined_symbol_and_every_symbol_is_used`, `test_template_starts_with_purpose_comment` (parametrised over every new template) |
| 25 | No-JS/layout/a11y bar | Screenshots at 1440 and 400, both colour modes (`01`–`04`); phone card layout confirmed (`03`); `test_no_page_in_this_brief_puts_a_list_inside_a_paragraph`; focus-to-summary is the existing `data-error-summary` hook, unchanged |
| 26 | Verify-a-change checklist | see Checklist line below |
| 27 | Prod walk-through | see "Prod walk-through" below |
| 28 | Friendly 403 (shell + public frame, no leaked exception text) | `test_it_user_opening_staff_and_access_gets_the_friendly_403_in_the_shell`, `test_plain_user_opening_zoom_accounts_gets_the_friendly_403_in_the_shell`, `test_an_anonymous_refusal_uses_the_public_frame_with_a_sign_in_link`, `test_the_403_page_never_shows_the_exception_text`; live screenshots `10-403-1440.png`, `11-403-400.png` |
| 29 | Shared partials moved, no old-path includes, no zoom references from accounts/registration/403 | `test_shared_form_partials_live_in_partials_and_nothing_uses_the_old_paths`, `test_accounts_registration_and_403_templates_never_reference_zoom` |
| 30 | `field.html` help is a `<div>`, no `<ul>` in `<p>`, `.field__help ul` CSS rule | `test_no_page_in_this_brief_puts_a_list_inside_a_paragraph`, `test_field_help_list_css_rule_exists` |

**Checklist ("Verify a change"):**

- `ruff check .` → **All checks passed!**
- `ruff format --check .` → **79 files already formatted**
- `pytest --create-db` (dev container, isolated) → **526 passed**, 3 runs in a row, no flakes
- `manage.py makemigrations --check --dry-run` → **No changes detected**
- `manage.py check` → **System check identified no issues (0 silenced)**
- `manage.py check --deploy` on the prod stack (`ZOOM_PROVIDER=manual docker compose up -d --build`, `-e USE_HTTPS=True`) → **1 issue: `security.W021`** (accepted), exit clean otherwise
- prod HTTP walk-through on 8010 → **PASS**, see below

**Prod walk-through (criterion 27), all on the freshly built prod image, `ZOOM_PROVIDER=manual`, over HTTP on 8010:**

1. Superuser `v010super` (created with `createsuperuser`) added a staff manager `V010 StaffMgr` — flash `Added V010 StaffMgr. Give them their username and starting password yourself, not by email.`
2. The staff manager added an IT desk person `V010 ItPerson` with a test password — their add form correctly had no `is_superuser` field.
3. `V010 ItPerson` signed in: saw `Link requests` and `Zoom accounts`, did **not** see `Administration`.
4. The staff manager set them a new password. Their already-open session's next request (`/zoom/requests/`) redirected to `/accounts/login/?next=/zoom/requests/`.
5. In a separate run, before switch-off, `V010 ItPerson` signed in again with the new password and used `Change your password`: their next request to `/zoom/requests/` stayed 200 (session preserved), flash `Your password was changed.`
6. The staff manager then switched `V010 ItPerson` off — flash `Saved V010 ItPerson.` A sign-in attempt with their last password showed the login page's existing error, `We couldn't sign you in… That username or password didn't match…`.
7. `/admin/` → 404; `/admin/login/` → 404. Static files are hashed (`style.e3e24686b491.css`) and return 200.
8. `V010 ItPerson` (before switch-off) opened `/accounts/staff/` directly → **403**, the friendly page in the shell: h1 `You can't open this page`, the copy, `Go to Home`, sidebar shows only what they can open (`Link requests`, `Zoom accounts`, no `Administration`), no permission codename anywhere in the body.
9. `manage.py showmigrations accounts` on the prod container showed `0001`–`0004` all `[X]`. Direct MySQL query on the prod database confirmed `django_admin_log` doesn't exist.
10. All throwaway users (`v010super`, `v010staffmgr`, `v010it`) deleted from the prod database afterwards; confirmed none remain.

Brief 005's and 008's zoom pages were exercised as part of the same suite runs (the partial-move criterion 29's own test, plus the full `apps/zoom` test tree) and all pass unchanged.

**Screenshots saved** (scratchpad, not committed): `01-list-1440-light.png`, `02-list-1440-dark.png`, `03-list-400-light.png`, `04-list-400-dark.png`, `05-add-errors.png`, `06-set-password.png`, `07-change-your-password.png`, `08-change-form-before-guard.png`, `09-login-after-switchoff.png`, `10-403-1440.png`, `11-403-400.png`, `12-change-guard-error.png`.

**Stack restored:** the dev stack (`docker compose -f compose.yaml -f compose.dev.yaml up -d`) is running again, as found at the start (`DJANGO_SETTINGS_MODULE=config.settings.dev`, `WEB_PORT=8010`). No volumes were wiped. A final sanity `pytest` on the restored dev container passed clean.

**Nothing sent back.** No FAIL, no owning agent to route to.

## Re-verification (round 1 fixes)
<!-- owner: tmd-test-verifier -->

**Verdict: PASS**

**Scope.** Re-verifies the round-1 fix cycle (step R2a/R2b): amended criteria 2 and 11, new criteria 31–35, D.13, and the reviewer's nits 1–5 and 7. The full "Verify a change" checklist was re-run in full, not just the new material.

**Coverage table, amended and new criteria (all covered by an existing test; nothing needed adding):**

| # | Criterion | Evidence |
|---|---|---|
| 2 (amended) | Access matrix, incl. own-pk `staff_password` → 302 for SM/superuser, 403 for plain/IT | `test_anonymous_visitors_are_sent_to_sign_in`, `test_people_without_staff_permissions_get_403_except_own_password`, `test_staff_manager_opens_every_page_for_someone_they_may_manage`, `test_staff_manager_gets_403_for_a_superuser_target`, `test_superuser_opens_every_page_even_for_another_superuser`, `test_your_own_set_password_page_sends_you_to_change_your_password`, `test_your_own_set_password_page_is_still_403_without_staff_rights`; live on prod, see walk-through below |
| 11 (amended) | Tightened `can_be_managed_by`, incl. the switched-off-peer trap | `test_staff_manager_manages_only_people_whose_rights_they_hold`, `test_a_switched_off_staff_manager_is_still_off_limits_to_a_peer`, `test_desk_manager_manages_it_desk_people_but_not_other_staff_managers`, `test_a_permission_given_directly_counts_as_a_right_the_actor_must_hold`, `test_people_without_change_user_manage_nobody`, `test_superuser_can_manage_everyone` |
| 31 | `User.can_give_role`, the SM/SM+IT/superuser table | `test_can_give_role_only_when_the_actor_holds_all_its_rights` (parametrised over the exact table), `test_nobody_gives_a_role_with_rights_without_an_actor` |
| 32 | Disabled unticked locked role, `clean_groups`, crafted-POST refusal, defensive `clean_groups` unit test | `test_a_role_the_staff_manager_cant_give_is_a_disabled_unticked_box`, `test_a_superuser_can_give_every_role`, `test_a_crafted_post_giving_a_role_you_cant_give_is_refused`, `test_a_crafted_post_on_a_change_giving_a_role_you_cant_give_is_refused`, `test_desk_manager_gives_it_desk`, `test_desk_manager_saving_an_unrelated_change_leaves_every_role_unchanged`, `test_clean_groups_keeps_a_role_the_actor_cant_give_when_the_post_leaves_it_out`; live on prod, see below |
| 33 | Own roles disabled + note; crafted untick/tick keeps roles, no self-lockout; superuser exempt | `test_a_staff_managers_own_roles_are_read_only`, `test_a_crafted_post_to_your_own_roles_saves_the_rest_and_keeps_the_roles[unticks Staff managers]`, `test_a_crafted_post_to_your_own_roles_saves_the_rest_and_keeps_the_roles[ticks IT desk]`, `test_a_superuser_may_still_change_their_own_roles`; live on prod, see below |
| 34 | SM 403 on peer SM / IT person / superuser / switched-off SM; SM+IT 200 for IT person, still 403 for a peer SM; unlinked list rows; own-pk redirect | `test_staff_manager_gets_403_for_people_they_may_not_manage` (4 targets × 2 pages), `test_a_peer_cant_switch_a_switched_off_staff_manager_back_on`, `test_desk_manager_opens_it_desk_people_but_not_other_staff_managers`, `test_list_links_only_the_people_the_staff_manager_may_change`, `test_your_own_set_password_page_sends_you_to_change_your_password`, `test_your_own_set_password_page_is_still_403_without_staff_rights`; live on prod, see below |
| 35 | Fixed query count: list as SM (3 vs 40, mixed roles), add/change role list vs role count | `test_list_query_count_as_a_staff_manager_does_not_grow_with_people`, `test_role_list_query_count_does_not_grow_with_roles`, `test_granted_permissions_cost_no_queries_on_staff_list_rows`, `test_staff_list_prefetches_roles_permissions_and_own_permissions` |

Criteria 1–30 were re-checked against the full suite (unchanged behaviour) and against the coverage table already in this brief's Verification section; nothing there regressed.

**Nits from round 1, confirmed fixed in code:**
- Nit 1: `0004_remove_admin_leftovers.py` docstring now says either operation order works and notes the leftover `admin` `django_migrations` rows.
- Nit 2: `staff_password` on your own pk now redirects to `accounts:password_change` (criterion 34).
- Nit 3: `StaffFormViewMixin` no longer reads `self.person` from a sibling mixin; each view sets it in its own `get_context_data`. Confirmed by reading `apps/accounts/views.py`.
- Nit 4: the email is normalised only in `User.clean()` (`apps/accounts/models.py:110`); `forms.py`'s `clean_email` no longer trims/lower-cases.
- Nit 5: `VIEW_USER_PERMISSION`, `ADD_USER_PERMISSION`, `CHANGE_USER_PERMISSION` are defined once in `apps/accounts/models.py`; `views.py` imports them.
- Nit 7: `check_field.html` is in `MOVED_PARTIALS` in `apps/accounts/tests/test_admin_removed_and_403.py:162`.

**Checklist ("Verify a change"), re-run on the round-1 fixed code:**

- `ruff check .` (dev container) → **All checks passed!**
- `ruff format --check .` (dev container) → **80 files already formatted**
- `pytest --create-db` (dev container, isolated — no other agent running) → **570 passed**, run twice, identical both times, no flakes:
  - run 1: `570 passed in 30.94s`
  - run 2: `570 passed in 35.38s`
- `manage.py makemigrations --check --dry-run` → **No changes detected**
- `manage.py check` → **System check identified no issues (0 silenced)**
- `manage.py check --deploy` on the prod stack (`ZOOM_PROVIDER=manual docker compose up -d --build`, `-e USE_HTTPS=True`) → **1 issue: `security.W021`** (accepted per CLAUDE.md), otherwise clean
- prod HTTP walk-through on 8010 → **PASS**, see below

**Prod walk-through (this brief's "What to run" §3–6), freshly built prod image, `ZOOM_PROVIDER=manual`, over real HTTP on 8010 (curl with a cookie jar, plus Playwright for the screenshots — not the Django test client):**

Throwaway users: `v010rv_super` (superuser), `v010rv_sm` (SM, `Staff managers` only), `v010rv_smpeer` (a second SM), `v010rv_it` (IT desk only), `v010rv_smit` (SM+IT), `v010rv_plain` (no roles). All created and deleted through real requests to the running prod container.

1. **As SM (`v010rv_sm`), without IT desk:**
   - `GET /accounts/staff/add/` → IT desk renders as `<div class="choice choice--tall">` with `disabled`, `aria-describedby="id_groups_0-reason"`, and the exact reason `You can't give or remove this role, because you don't have all its rights yourself.`; `Staff managers` renders as a normal enabled `<label>`.
   - `GET /accounts/staff/160/edit/` (a plain user) → the same locked IT desk row.
   - Crafted `POST /accounts/staff/add/` with `groups=1` (IT desk) → **200**, field error `You can only give roles whose rights you have yourself.`, and no user named `v010rv_hacker` was created (confirmed directly against the database).
   - `GET /accounts/staff/156/edit/` (their own record) → `roles_read_only`: both checkboxes `disabled`, `aria-describedby="groups-note groups-help"`, the note `You can't change your own roles. Ask someone else with Staff and access, or someone with full access, to change them.`, no `choice__reason` anywhere on the page.
   - `GET /accounts/staff/` → the peer SM (`v010rv_smpeer`) and the IT desk person (`v010rv_it`) are listed as plain `<span class="datagrid__strong">` text with no `<a>` (checked directly in the response HTML).
   - `GET` and `POST /accounts/staff/158/edit/` and `/accounts/staff/158/password/` (the peer SM) and `/accounts/staff/157/edit/` and `.../157/password/` (the IT desk person) → **403** on all four.
   - `GET /accounts/staff/156/password/` (their own pk) → **302** to `/accounts/password/`.
2. **As SM+IT (`v010rv_smit`):**
   - `GET /accounts/staff/add/` → IT desk checkbox is a normal enabled `<label>`, not disabled.
   - `POST /accounts/staff/160/edit/` (the plain user) with `groups=1` → **302**; confirmed directly against the database that the plain user now holds `IT desk`.
3. **A switched-off SM can't be re-enabled by a peer:** the superuser switched `v010rv_smpeer` off (`is_active=False`, confirmed in the database). As SM (`v010rv_sm`): `GET /accounts/staff/158/edit/` → **403**; a crafted `POST` to the same URL with `is_active=on` → **403**, and the database still shows `is_active=False` afterwards.
4. **No password leak:** every captured response body and header from this walk-through (`grep -rl` across all saved `.html`/`.txt` files) contains no occurrence of the typed password `Tr0ub4dor-3xyz-Q`, and no `<input type="password" … value="…">` anywhere.
5. `manage.py check --deploy` (above) and `/admin/` → 404 (re-confirmed on this build).

**Screenshots saved** (scratchpad, not committed; Playwright, real login session, `tmd-layout` localStorage set for the theme):
- `locked-add-1440-light.png`, `locked-add-1440-dark.png`, `locked-add-400-light.png`, `locked-add-400-dark.png` — the add page's locked `IT desk` row, dashed border, lock icon + reason text, AA-contrast words in both modes, no horizontal scroll at 400px.
- `own-note-1440-light.png`, `own-note-1440-dark.png`, `own-note-400-light.png`, `own-note-400-dark.png` — the SM's own change page: the `notice--note` above the role boxes, both boxes disabled, `Staff managers` keeping its ticked purple tint, the Password box's self-copy and `Change your password` link.

**Accessibility spot-check on the saved HTML (D.13):** one `h1` on every page; the locked row's name comes from the inner `<label for>`; the reason is `aria-describedby`'d from the checkbox and also sits in reading order as visible text; the note's text is plain paragraph text (not on a disabled control), so it isn't exempt from AA and reads at normal contrast in both themes, confirmed visually in the screenshots; no colour-only cue — every locked/read-only state pairs the dashed border with the lock icon and words.

**Stack restored:** the dev stack (`docker compose -f compose.yaml -f compose.dev.yaml up -d`) is running again, as found at the start (`config.settings.dev`, MySQL published on `127.0.0.1:3306`, `WEB_PORT=8010`). No volumes were wiped. All six throwaway prod-database users were deleted before the stack was switched back (confirmed `0` remaining). A final `pytest` on the restored dev container passed clean (all green, no failures).

**Nothing sent back.** No FAIL, no owning agent to route to.

## Review
<!-- owner: tmd-code-reviewer (written by the main session) — verdict, blockers, should-fix, nits -->

### Round 1 — 2026-09-25 (verifier PASS, 526 tests ×3 isolated)

**Verdict: CHANGES REQUESTED.** Blockers: none.

**Should fix**

**SF1: a Staff manager can give any role to anyone, themselves included.** The owner decides the fix.
- **Where:** `forms.py:61-68, 115-117` lists every group. `models.py:111-120` limits them only by "not a superuser".
- **What a Staff manager can do today:**
  - tick `IT desk` on their own record, which gives them zoom review and account permissions;
  - give `Staff managers` to anyone;
  - automatically hold any role a later brief adds;
  - set a new password for any non-superuser, including another Staff manager, and then sign in as them (`views.py:106-121, 162-185`).
- **What is already safe:** full access can't be reached by any path.
- **What D8 is silent on:** whether this ceiling is intended. No test pins it.
- **Options:**
  - (a) Accept it explicitly: a D8 addendum, a README line and a test.
  - (b) Restrict it with `User.can_give_role(actor, group)`: a group's permissions must be a subset of the actor's own, and the form disables roles the actor can't give. This also stops a Staff manager who isn't in `IT desk` from giving `IT desk`.
- **Also undecided:** whether a Staff manager may untick their own `Staff managers` role. Doing so silently locks them out of Staff and access.

**Nits**
1. `migrations/0004…:5-8`: the docstring's reason for the operation order is wrong, because the admin model isn't installed, so there's no cascade. Say that either order works, and mention the leftover `django_migrations` admin rows.
2. `views.py:120-121`: the `staff_password` URL accepts your own pk, and saving there signs you out. Refuse it, or redirect to `accounts:password_change`.
3. `views.py:100`: `StaffFormViewMixin` depends on `self.person` from a sibling mixin, and works only because of base-class order.
4. The email is normalised both in `forms.py:128` and in `models.py:82`. Keep the model rule only.
5. Permission names are defined in `models.py:14` and in `views.py:39-40`. Keep them together in models.
6. `staff_form.html:53`: an inline `"D j M Y"` repeats the date format from `accounts/partials/when.html`. It's covered by the date-format follow-up.
7. `tests/test_admin_removed_and_403.py:156`: add `check_field.html` to `MOVED_PARTIALS`.

**Accepted:**
- The full-access gate, including crafted POSTs.
- The self-lockout and last-superuser guards, with the locked superuser pool.
- `sensitive_post_parameters`.
- No password in any response.
- Session invalidation through the auth hash.
- The `person` object name.
- `SignedInPermissionMixin` in core.
- The `field.html` changes, with no regression in brief 005 or 008.
- The `check_field.html` move.
- 403 frame selection via `yesno`.

### Round 2 — 2026-09-25 (after the round-1 fix cycle; re-verification PASS, 570 tests ×2)

**Verdict: APPROVE.** No blockers and no should-fix findings.

**SF1: closed, following the owner's "only roles they hold" rule.** No other way to gain rights remains. The reviewer checked each of these:
- a crafted POST on the add form;
- removing roles;
- a role with no permissions;
- a Staff manager who holds a user-level permission directly;
- a switched-off Staff manager;
- the read-only own record.

**Backend's own-record decision: agreed.** Your own record counts as manageable only if you have `change_user` (`models.py:188-191`), which matches the 403 rows in criterion 2's table.

**Round-1 nits:** 1–5 and 7 are confirmed fixed. Nit 6 stays with the date-format follow-up.

**Query counts:** confirmed fixed by `with_granted_permissions()`, with tests at 3 and at 40 people.

**New nits (all optional)**
- **A.** D13 (around lines 489-490) says handing out `Staff managers` freely is closed. That isn't quite true. A Staff manager can still give `Staff managers` to anyone whose rights are within their own. Once given, only a superuser can remove it. Correct the D13 text, and say this in the README. Owner: tmd-planner, then tmd-docs-writer.
- **B.** Amend criterion 11 so the own-record case also requires `change_user`, matching the code. Owner: tmd-planner.
- **C.** `staff_form.html:37`: the `choice__words` class appears on both the span and the label of a locked row. Owner: tmd-frontend.
- **D.** `staff_form.html:37`: when a crafted POST is refused, the locked row shows the posted state. Nothing is saved; rendering from the stored state would be tidier. Owner: tmd-frontend.

**Main-session ruling:** A and B are fixed in the brief and the README at close. C and D are recorded as follow-ups: they only change the markup, and fixing them now would mean another verification cycle.

## Docs
<!-- owner: tmd-docs-writer — files updated; closes Status -->

**Files updated:**

- `README.md`: removed every remaining mention of the Django admin and `/admin/` (the devops note's
  lines ~160–167); reworded `createsuperuser` as first-account bootstrap only in both the dev and
  production-like Docker sections; added a new **Staff and access** section (who can open it, roles
  are fixed, the "only roles they hold" rule including that giving `IT desk` needs holding it
  yourself, that only a superuser can undo giving someone `Staff managers`, adding a person and the
  starting password, switching someone off, setting a new password, "Change your password" in the
  user menu, and the "no access" page); updated the Zoom link requests section so giving `IT desk`
  points at Staff and access, not the admin; updated the `Layout` tree for `apps/accounts`,
  `apps/core` and `templates/`.
- `CLAUDE.md`: Architecture → Current apps — the `accounts` line now names the Staff and access
  screens and the four `User` rule methods (`can_give_role`, `granted_permissions`,
  `can_be_managed_by`, `access_change_error`); the `core` line now names `SignedInPermissionMixin`
  (`apps/core/mixins.py`); the `zoom` line's "still in the admin until task 010" sentence is
  replaced with a note that joining `IT desk` is done on Staff and access. Templates paragraph:
  added the shared form partials' new home in `templates/partials/` (including that `field.html`
  never writes a password value) and `templates/403.html` as the one refusal page for every
  section. Verify a change → step 2 now has a one-line warning that parallel agents sharing
  `test_polymath_tmd` must not run `pytest --create-db` at the same time.
- `docs/CHANGELOG.md`: new newest-first entry, 2026-09-25, "010: Staff and access; Django admin
  removed" — user-visible changes first, then migrations 0002–0004, the admin removal, the access
  rules living on `User`, the moved partials, the password-leak fix, `SignedInPermissionMixin`, and
  the follow-ups (nits C and D, the shared date format, brief 011).
- This brief: this section, and the Status line below.

**Left alone, on purpose:** D.6's copy table (the list lead row) still shows the sentence from
before the Q-D3 change; that's the designer's section (frontend's Q-D3 note flags it), not this
step's to fix.

**Status:** Done — Verification is PASS (570 tests, twice) and Review is APPROVE (round 2), with
nits A and B already folded into this brief and the README by the main session.
