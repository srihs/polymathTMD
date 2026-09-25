# 008 — Zoom accounts: manage host accounts in the app, and take Zoom out of the Django admin

<!-- One brief per task. Each section has exactly one owner agent; agents write only their own section.
     The workflow itself is defined in CLAUDE.md → "Agent workflow". -->

**Status:** Done <!-- Planned | Blocked: questions | In progress | Verifying | In review | Done -->

## Requirement
<!-- owner: tmd-planner — the user's words verbatim, then a one-paragraph interpretation -->

> so there should be a place where we can configure the zoom accounts, and view of the month in a timetable format.

The owner's project rule, given while this brief was being planned (2026-09-25):

> a project rule, we dont use Djangoadmin. we should have our own screens and datamodels to handle the requirements

**Reading.** The requirement asks for two things. This brief covers the first: **a place to configure the Zoom accounts**. The month timetable is brief **009**.

Today the Zoom host accounts from brief 005 are managed only in the Django admin. `HostAccount` holds a name, the Zoom sign-in email, a paid flag, an in-use flag, an order, a credential set, an encrypted host key and notes. The project rule means the admin can't be that place any more.

This brief adds a **Zoom accounts** screen inside the normal f-desk shell, for **everyone in the IT desk** (owner, Q1). There they can:

- list the accounts;
- add an account and change its details;
- set, replace or remove its host key;
- take it out of use, or put it back into use.

The host key stays **write-only**, with every brief-005 protection:

- it's encrypted at rest;
- a key someone typed is never echoed back;
- it's masked in error reports;
- no screen ever shows a saved key, even partly.

Accounts are never deleted. An account **can't** be taken out of use, or marked as free, while it still has booked classes from now onwards (owner, Q2). The page says how many are booked and what to do instead. Past classes don't count.

The brief also takes everything Zoom-related out of the Django admin. `apps/zoom/admin.py` and its tests go, and every screen, message and document that says "in the admin" is reworded. Staff users, roles, and removing `django.contrib.admin` itself are brief **010**.

## Scope
<!-- owner: tmd-planner — In scope / Out of scope bullets -->

**How the requirement and the rule are split, in build order:**

| Brief | What | Depends on |
|---|---|---|
| **008 (this)** | The in-app **Zoom accounts** screens (list, add, change) for the IT desk. Host keys are write-only. Taking an account out of use is refused while it has booked classes. The sidebar gets a new item. **The Zoom models leave the Django admin** (`apps/zoom/admin.py` is deleted), and every "in the admin" message is reworded | 005 (Done) |
| **010** | **Staff and access**: in-app screens to add staff users, set their passwords, give them roles and switch them off, for superusers and a new `Staff managers` role. Then **`django.contrib.admin` is removed entirely** (`docs/tasks/010-staff-and-access.md`) | 008 |
| **009** | **Zoom timetable**: a wall-calendar month grid (Mon–Sun weeks) of booked and waiting classes, plus a day view (`docs/tasks/009-zoom-timetable.md`) | 005; the cross-link from the accounts list needs 008 |

- **Order:** **008 → 010 → 009**. All three edit `partials/sidebar.html`, so they're built one after another. Their designer steps can run ahead.
- **Briefs 006 and 007:** 006 (the live Zoom API) and 007 (the spreadsheet import) keep their numbers.
- **New brief 011:** **Cancel a booking** (owner, Q3). It's a go-live prerequisite, recorded under D11.
- **Migration numbering:** 008 adds `zoom/0003` and `zoom/0004`. Whichever brief lands later renumbers its own migrations onto the latest.

**Go-live prerequisites (recorded here for the docs writer and the README):**

1. Brief 007 imports the future spreadsheet bookings. This is brief 005's gate.
2. Brief 011 **"Cancel this booking"** exists (owner, Q3). Until then, a wrong or unneeded approval can't be undone in the app. From 008 onwards, an account with a booking also can't be taken out of use until that class is over (Q2).

**No Django admin: every current use, and where it goes**

| Where | Current use | Replaced by | Brief |
|---|---|---|---|
| `apps/zoom/admin.py` | `HostAccountAdmin`: list, add and change; host key via `HostAccountKeyAdminForm`; `sensitive_post_parameters` on `changeform_view`. `LinkRequestAdmin`: view and delete, with an `Occurrence` inline | Host accounts: the in-app Zoom accounts screens (this brief). Viewing requests: the in-app queue and detail (already built). Deleting requests: **nothing now**. Brief 011 adds "Cancel this booking" (Q3) | 008 |
| `apps/zoom/tests/test_admin.py` | 8 admin tests (criteria 47 and 62 of 005) | Deleted. Their protections are re-proved against the in-app screens (criteria 8, 12–15, 24) | 008 |
| `apps/zoom/tests/test_review_fixes.py::test_error_report_of_the_admin_change_form_masks_a_typed_host_key` | Posts to `admin:zoom_hostaccount_change` | Rewritten against `zoom:account_edit` (criterion 24) | 008 |
| `apps/zoom/tests/test_views.py::test_full_flow_never_logs_the_host_key_or_encryption_keys` | Changes a key through `admin:zoom_hostaccount_change` | Rewritten to use `zoom:account_edit` (criterion 24) | 008 |
| `apps/zoom/views.py` `APPROVED_EMAIL_FAILED` | "…An administrator can give them the host key from the admin." | New copy (criterion 25) | 008 |
| `apps/zoom/services.py`, the host-key-unreadable message (005, criterion 64) | "…type it again in the admin, then approve." | New copy (criterion 25) | 008 |
| `templates/zoom/detail.html` | "No paid Zoom accounts are set up. An administrator can add them in the admin." | New copy (criterion 25) | 008 |
| `apps/zoom/management/commands/rotate_host_keys.py` output | "Type those keys again in the admin." | New copy (criterion 25) | 008 |
| `apps/zoom/models.py` (docstrings, the `help_text` of `host_key_encrypted`), `apps/zoom/crypto.py` (docstring) | Say "managed only in the admin" and "set it … in the admin" | Reworded. The `help_text` change goes into migration `0003` | 008 |
| `apps/zoom/migrations/0002_it_desk_group.py` docstring | "A superuser adds IT staff to this group in the admin" | **Left as it is.** Applied migrations are history | none |
| `README.md` (host accounts, host keys, a leaked key, lost encryption keys) | "…in the admin", "admin change form" | Reworded to point to the Zoom accounts page (docs writer) | 008 |
| `.env.example` (the comment on `HOST_KEY_ENCRYPTION_KEYS`) | "re-typing all host keys in the admin" | "…on the Zoom accounts page" (`tmd-devops`) | 008 |
| `apps/accounts/admin.py` | `UserAdmin`: users, passwords, groups, the active and superuser flags | Staff and access | 010 |
| The default `auth.Group` admin | Groups and their permissions | Fixed roles, created by migrations. There's no group editor | 010 |
| `config/urls.py` | `admin.site` header lines, `path("admin/", …)` | Removed | 010 |
| `config/settings/base.py` `DJANGO_APPS` | `"django.contrib.admin"` | Removed. `auth`, `contenttypes`, `sessions` and `messages` stay | 010 |
| `templates/partials/sidebar.html` | `Administration` → `Admin` (`admin:index`), shown when `user.is_staff` | `Administration` → `Staff and access`, gated by a permission | 010 |
| `apps/core/tests.py` (3 admin-link tests; 2 sidebar tests naming `admin:index`) | Assert the Admin link for staff | Rewritten | 010 |
| `README.md` / `CLAUDE.md` `createsuperuser` | The way into the admin | Kept only to create the first account | 010 |
| `is_staff` | Means "may open the admin" | No longer meaningful. No screen reads or sets it | 010 |

**In scope (008)**

- **`apps/zoom` only** (D1).
- **Screens** (the shell), gated by Django's built-in model permissions on `HostAccount`, all of which are **added to the `IT desk` group** (Q1, D2):
  - `Zoom accounts`: the list of accounts, showing each one's type, whether it's in use, whether a host key is saved, and its upcoming classes;
  - `Add a Zoom account`;
  - `Change {name}`: the account's fields, and the host key (set, replace or remove; write-only). The in-use and paid ticks are refused while there are upcoming classes (Q2).
- **Model:**
  - `HostAccount.host_key_changed_at` / `host_key_changed_by` (D3);
  - `set_host_key(plain, *, by=None)` records who changed the key and when;
  - `HostAccount.clean()` normalises the email;
  - the stop-booking rule lives on the model;
  - a QuerySet method for the list's figures;
  - `OccurrenceQuerySet.upcoming()`.
- **Data migration:** `IT desk` gets `zoom.view_hostaccount`, `zoom.add_hostaccount` and `zoom.change_hostaccount`.
- **The Zoom models leave the admin** (see the inventory above).
- **Sidebar:** a `Zoom accounts` item in `Zoom links`, with `aria-current` set per view name (D9).

**Out of scope (008)**

- Staff users, roles and removing `django.contrib.admin` itself (010).
- Deleting accounts (D4).
- Cancelling, moving or re-assigning booked classes (brief 011, Q3). While classes are booked, Q2's block stands.
- Editing `credential_set` (D5). Brief 006 adds it to this screen.
- Checking a host key against Zoom.
- Any change to the approval flow, the approval email, `bookable()` or the availability rules.
- The timetable (009).
- A full change history. There's "last set at / by" for keys (D3), and nothing more.

## Acceptance criteria
<!-- owner: tmd-planner — numbered, observable, testable -->

**Terms.** These carry over from brief 005:

- its frozen "now" of **Mon 28 Sep 2026, 10:00** Asia/Colombo, and its way of freezing time;
- "plain user";
- its rule on pinned copy.

This brief adds or changes:

- **IT user:** an active user whose only permissions come from the `IT desk` group. After this brief, that's `zoom.review_linkrequest` plus the three host-account permissions.
- **Key-less viewer:** a **test-only** user holding just `zoom.view_hostaccount`. It proves each screen checks its own permission.
- **Upcoming class** of an account: an `Occurrence` that `booked()` returns (its request is `approved`), with `host_account` set to that account and `ends_at > now`. A class that's in progress counts as upcoming. A class that has ended doesn't.

### Permissions and navigation

1. **The IT desk role (Q1).** After `migrate`, the group `IT desk` holds exactly these four permissions:
   - `zoom.review_linkrequest`;
   - `zoom.view_hostaccount`;
   - `zoom.add_hostaccount`;
   - `zoom.change_hostaccount`.

   It doesn't hold `delete_hostaccount`, and there's no group named `Zoom account managers`.

   The migration is reversible: reversing it removes exactly those three permissions from the group. Running it twice leaves no duplicates.

   Brief 005's criterion 18 ("exactly one permission") is amended deliberately, and its test is updated to match.
2. **Access.**

   | Page | Anonymous | Plain user (with or without `is_staff`) | Key-less viewer | IT user, superuser |
   |---|---|---|---|---|
   | `zoom:accounts` | Redirect to `accounts:login?next=…` | 403 | 200 | 200 |
   | `zoom:account_add` | Redirect to login | 403 | 403 | 200 |
   | `zoom:account_edit` | Redirect to login | 403 | 403 | 200 |

   The key-less viewer's list has no `Add a Zoom account` button, and its account names aren't links.
3. **Sidebar.**
   - The `Zoom links` group (`id="nav-zoom"`) renders when the user has `zoom.review_linkrequest` **or** `zoom.view_hostaccount`. Its items, in order:
     - `Link requests` → `zoom:queue`, which needs `review_linkrequest`;
     - `Zoom accounts` → `zoom:accounts`, which needs `view_hostaccount`.

     Brief 009 inserts `Timetable` between them. An IT user sees both items.
   - **`aria-current="page"`:**
     - `Zoom accounts` carries it on `zoom:accounts`, `zoom:account_add` and `zoom:account_edit`;
     - `Link requests` carries it only on `zoom:queue`, `zoom:detail`, and the approve and reject re-renders;
     - `Home` carries it on none of these pages.
   - `Administration` stays last.
   - Brief 005's criterion 19 ("holds one item") is amended deliberately, and `test_sidebar_zoom_group.py` is updated to match.

### The list: `zoom:accounts`

4. **Page and table.**
   - The h1 is `Zoom accounts`, the `<title>` is `Zoom accounts · {site name}`, and the breadcrumb is `Home › Zoom accounts`.
   - The table has a `<caption>` and `<th scope>` headers, with these columns in order:
     1. `Name`: links to `zoom:account_edit` for users with `change_hostaccount`;
     2. `Zoom sign-in email`;
     3. `Type`: a tag, `Paid` or `Free (40-minute limit)`;
     4. `In use`: a tag with an icon and a word, `In use` or `Not in use`;
     5. `Host key`: an icon and a word, `Saved` or `Not saved`;
     6. `Upcoming classes`: the count and `Next: {Mon 28 Sep 2026}, {9:00 am}`, or `None booked`.
   - Accounts in use come first, then the rest, each ordered by `sort_order`, then `label`.
   - The list isn't paged.
5. **Upcoming figures.** The test account has:
   - an approved class on Sun 27 Sep 2026, 09:00–11:00 (ended);
   - an approved class on Mon 28 Sep, 09:00–11:00 (in progress at 10:00);
   - an approved class on Mon 5 Oct 2026, 08:30–11:30;
   - classes from a `waiting` request and a `rejected` request.

   Its row shows `2` and `Next: Mon 28 Sep 2026, 9:00 am`. An account with no upcoming classes shows `None booked`.
6. **Query budget.** The list takes the same number of SQL queries with 2 accounts as with 15 accounts that have 3 upcoming classes each. The test uses `django_assert_num_queries` or an equivalent.
7. **Empty.** With no accounts, the page shows `No Zoom accounts yet.`. Users with `add_hostaccount` also see the `Add a Zoom account` button.
8. **No key material.** The list, rendered for a superuser, contains neither the plaintext host key nor `gAAAAA`.

### Add: `zoom:account_add`

9. **Form.**
   - The h1 is `Add a Zoom account`, and the breadcrumb is `Home › Zoom accounts › Add a Zoom account`.
   - Each field has a `<label for>` and an `id="<name>-help"` hint wired through `aria-describedby`:
     - `label` `Name`;
     - `email` `Zoom sign-in email`, `type="email"`;
     - `is_paid` `Paid account`, ticked by default;
     - `is_active` `In use`, ticked by default;
     - `sort_order` `Order`;
     - `notes` `Notes`;
     - `host_key` `Host key`, empty, with `autocomplete="off"`, `inputmode="numeric"` and `spellcheck="false"`.
   - There's no `credential_set` field (D5).
   - The button reads `Add the account`.
10. **Create.** A valid POST with host key `8421973`:
    - creates the account, with the email trimmed and lower-cased;
    - stores a **raw column** `host_key_encrypted` (read with `connection.cursor()`) that starts with `gAAAAA` and doesn't contain `8421973`;
    - sets `host_key_changed_at` to now and `host_key_changed_by` to the user;
    - redirects (302) to `zoom:accounts` with the message `Added {label}.`

    A valid POST with no host key gives `has_host_key == False` and `host_key_changed_at is None`.
11. **Validation.** Each invalid POST returns 200 and saves nothing. The exact field errors:

    | Input | Field | Error |
    |---|---|---|
    | empty name | `label` | `Type a short name for the account, like Zoom 01.` |
    | the same name as another account, in any letter case (`zoom 01` when `Zoom 01` exists) | `label` | `Another Zoom account already has this name. Choose a different one.` |
    | bad email | `email` | `Type the email address this Zoom account signs in with, like zoom01@polymath.edu.lk.` |
    | the same email as another account, in any letter case | `email` | `Another Zoom account already signs in with this email address.` |
    | host key `12345`, `12ab567` or `12345678901` | `host_key` | `A Zoom host key is 6 to 10 digits.` |
    | negative or non-numeric order | `sort_order` | Django's default message is acceptable |

    The error summary uses `zoom/partials/error_summary.html` with the lead `We couldn't save this account yet.`, following brief 005's criterion 7 pattern. (Brief 010 moves that partial to `templates/partials/`.)
12. **A typed key is never echoed back.** When the form re-renders with errors, every typed value is kept **except** the host key:
    - the `host_key` input is empty;
    - the typed key appears nowhere in the response body;
    - when a key had been typed, the field shows `For your safety, the host key you typed wasn't kept. Type it again.`

    This is a deliberate exception to "keep what the user typed" (D7).

### Change: `zoom:account_edit`

13. **Form.**
    - The h1 is `Change {label}`, and the breadcrumb is `Home › Zoom accounts › {label}`.
    - Criterion 9's fields are prefilled from the account, **except** the host key.
    - A read-only state line shows one of:
      - `Host key saved on {Mon 28 Sep 2026} by {user}` (with `by {user}` left out when `host_key_changed_by` is null);
      - `Host key saved`, when `host_key_changed_at` is null (keys saved before this brief);
      - `No host key saved`.
    - The key input is labelled `New host key`, with the help `Leave it empty to keep the saved key.` When no key is saved, the help is `Type the 6 to 10 digits from the account's Zoom profile.`
    - The checkbox `remove_host_key` (`Remove the saved host key`) appears only when a key is saved.
    - The button reads `Save changes`.
    - For every user, superusers included, the response contains neither the plaintext key nor `gAAAAA`.
14. **Saving.**

    | POST | Result | Message |
    |---|---|---|
    | New key empty, Remove unticked | `host_key_encrypted` unchanged byte for byte; `host_key_changed_*` unchanged | `Saved {label}.` |
    | New key `7654321` | Re-encrypted; `get_host_key() == "7654321"`; `host_key_changed_at` = now; `host_key_changed_by` = user | `Saved {label}. The new host key goes out with the next approved link.` |
    | Remove ticked, new key empty | Key cleared; `host_key_changed_*` = now and user | `Saved {label}. Its host key was removed.` |
    | New key typed **and** Remove ticked | Nothing saved; field error on `host_key` | `Type a new host key or tick Remove, not both.` |

    Every success redirects (302) to `zoom:accounts`. An unknown pk returns 404.
15. **Unreadable saved key.** When the stored key can't be decrypted with the configured keys:
    - the page still returns 200;
    - the state line reads `A host key is saved, but it can't be read with the current encryption keys. Type it again.`;
    - saving a new key replaces it.

### Taking an account out of use is blocked while classes are booked (Q2)

16. **Model.**
    - `HostAccount.upcoming_classes(now=None)` returns this account's upcoming classes, ordered by `starts_at`. It's built on `OccurrenceQuerySet.upcoming(now=None)` (`ends_at > now`), chained after `booked()`.
    - `HostAccount.stop_booking_errors(*, is_active, is_paid, now=None) -> dict[str, str]` returns criterion 17's field errors, or `{}`.
    - The "bookable = in use and paid" condition is defined once and shared with `bookable()`.
17. **The block.** A POST that unticks `is_active` or `is_paid` on an account with at least one upcoming class is refused:
    - **Nothing is saved**, including any other field that changed.
    - The response is 200, and it keeps every typed value except a host key (criterion 12).
    - It shows the error summary (criterion 11's lead). Each unticked field gets its own error, word for word:

    | Unticked | Field | Error (12 upcoming classes, the first on Mon 28 Sep 2026 and the last on Wed 28 Oct 2026) |
    |---|---|---|
    | `is_active` | `is_active` | `Zoom 03 still has 12 booked classes, from Mon 28 Sep 2026 to Wed 28 Oct 2026. It can be taken out of use once the last one has finished.` |
    | `is_paid` | `is_paid` | `Zoom 03 still has 12 booked classes, from Mon 28 Sep 2026 to Wed 28 Oct 2026. It can be marked as free once the last one has finished.` |
    | both | both fields | the two errors above |

    With exactly one upcoming class, on Mon 5 Oct 2026, the words become `still has 1 booked class, on Mon 5 Oct 2026. It can be taken out of use once it has finished.`, and the same pattern applies to `marked as free`.

    When brief 011 adds cancelling, it amends this copy to add "or cancel them" (D11).
18. **What doesn't block.**
    - **Ended classes don't block.** An account whose only approved classes have ended (the test's class on 27 Sep 09:00–11:00, as of 28 Sep 10:00) can be taken out of use, or marked free, in one POST.
    - **Waiting requests don't block.** A waiting or rejected request's classes never block.
    - **Ticking back always saves.** Ticking `In use` and `Paid` again always saves in one POST, and the account is `bookable()` again, offered in a waiting request's availability.
    - **After a successful stop:**
      - the account is absent from `bookable()` and from availability;
      - its `Occurrence`, `HostSlot` and `LinkRequest` rows are unchanged;
      - no email is sent.
19. **No race with approval.** The edit view's check and save run in one transaction, with the account row locked by `select_for_update()`. `services.approve()` locks the same row before it books, so a class can't be approved on an account in the moment it's being taken out of use.
    - The upcoming-classes read inside the check is also a **locking read** (`select_for_update()` on the booked `Occurrence` rows, with the count, first and last dates computed in Python from the locked rows). This follows brief 005's D5: under MySQL's REPEATABLE READ, a plain read could come from a snapshot taken before the lock was granted, and miss an approval committed a moment earlier.
    - The test captures the SQL of a stop-booking POST and asserts that it contains a `SELECT … FOR UPDATE` on `zoom_hostaccount` and one on `zoom_occurrence`, both before the `UPDATE`.
    - The lock order is only `HostAccount`, so it can't form a cycle with `approve()`, which locks `LinkRequest` and then `HostAccount`.
20. **No delete.**
    - No accounts page has a delete button or link, and no `zoom` URL name contains `delete`.
    - `on_delete=PROTECT` is unchanged. A model test asserts that deleting an account with bookings raises `ProtectedError`.

### Model

21. **Recording who set a key.**
    - `set_host_key(plain, *, by=None)` sets `host_key_changed_at = timezone.now()` and `host_key_changed_by = by` whenever it stores a new key or clears a saved one.
    - Clearing when nothing is saved changes neither field.
    - `rotate_host_key()` and `manage.py rotate_host_keys` change neither field. The rotation test is extended to check this.
    - The field types:
      - `host_key_changed_by`: `FK(AUTH_USER_MODEL, on_delete=SET_NULL, null=True, blank=True, related_name="+", editable=False)`;
      - `host_key_changed_at`: `DateTimeField(null=True, blank=True, editable=False)`.
    - Brief 005's criterion 46 secret-name test passes.
22. **Email and uniqueness.**
    - `HostAccount.clean()` trims and lower-cases `email`.
    - Criterion 11's uniqueness checks are case-insensitive for `label` and `email`. They run through `validate_unique` or `clean()`, never by catching `IntegrityError`.

### The Zoom models leave the Django admin

23. **No Zoom admin.**
    - `apps/zoom/admin.py` doesn't exist, and no module under `apps/zoom/` imports `django.contrib.admin` (a pytest source scan checks this).
    - `reverse("admin:zoom_hostaccount_changelist")` and `reverse("admin:zoom_linkrequest_changelist")` raise `NoReverseMatch`.
    - `apps/zoom/tests/test_admin.py` is deleted.
24. **Secrets, re-proved in the app.** These tests replace brief 005's admin parts of criteria 62 and 65. The flow under test:
    1. submit, confirm, approve and reject (as in 005);
    2. add an account with a key;
    3. an invalid re-render with a typed key;
    4. change the key on `zoom:account_edit`;
    5. remove the key;
    6. run `rotate_host_keys`.

    Across that flow:
    - With `DEBUG` logging captured for `apps.zoom` and `django`, no record contains a plaintext key or any value of `HOST_KEY_ENCRYPTION_KEYS`.
    - No stored `messages` entry contains a key.
    - The add and change views wrap `dispatch` in `sensitive_post_parameters("host_key")`. The rewritten error-report test makes the change view's save raise. It asserts that the `ExceptionReporter` HTML and text mask the typed key (`*****`) and never contain it.
    - `set_host_key` keeps `@sensitive_variables("plain")`. `__str__` and `__repr__` still leave the key out.
    - Every accounts page (list, add, change, every error state including criterion 17's) renders without the plaintext key and without `gAAAAA`.
25. **The "in the admin" copy is gone.** Pinned:

    | Where | New text | Amends |
    |---|---|---|
    | Approval email failed (flash) | `Approved, but the email to {email} didn't send. Copy the link below and send it to them yourself. The host key is in the Zoom account's profile in Zoom.` | 005, criterion 41 |
    | Host key unreadable at approval | `The host key saved for {label} can't be read. Ask someone in the IT desk to type it again on the Zoom accounts page, then approve.` | 005, criterion 64 |
    | Detail page with no paid accounts | `No paid Zoom accounts are set up yet.`, then an `Add a Zoom account` → `zoom:account_add` link for users with `add_hostaccount`. Other users see `Ask someone in the IT desk to add them.` | 005, detail page |
    | `rotate_host_keys`, unreadable keys | `… Type those keys again on the Zoom accounts page.` | 005, criterion 63 |

    - The tests that pinned the old texts are updated deliberately.
    - A pytest check finds no case-insensitive `\bin the admin\b` or `admin change form` in `apps/zoom/**/*.py` (outside `migrations/`) or in `templates/zoom/**`.

### Front end, templates, accessibility

26. **Template rules.**
    - Each new or changed template starts with a `{# … #}` header naming its context.
    - Every include ends with `only`.
    - There are no inline `style=` attributes and no hard-coded paths.
    - Every `<use href="#i-…">` names a symbol in the sprite, and every symbol in the sprite is used.
    - The guard tests from briefs 004 and 005 pass unchanged.
27. **Works without JavaScript:** the list, add, change, the stop-booking error and the error summary. Any enhancement binds only to `data-*` attributes, and there are no console errors.
28. **Layout and accessibility** on the list, add and change pages:
    - no horizontal page scroll at 320, 400, 1024 and 1440 px, in both colour modes;
    - below 768px, the list becomes one card per row (the queue's datagrid pattern);
    - targets are at least 44×44 px;
    - WCAG AA;
    - one `h1` per page;
    - the table has a `<caption>` and `<th scope>`;
    - tags show an icon plus a word;
    - after a failed submit, focus moves to the error summary (with JS). Without JS, the summary is the first thing in `<main>` after the h1.
29. **Thin views.** The rules live on the model layer:
    - setting and tracking a host key: `set_host_key`;
    - email normalisation: `clean()`;
    - the list's figures: `HostAccountQuerySet.for_management()`;
    - upcoming classes: `upcoming_classes` and `upcoming()`;
    - the Q2 rule: `stop_booking_errors`.

    Views have no ORM filters beyond `get_queryset` and `get_object` calling these. The reviewer checks this.

### Verification (CLAUDE.md "Verify a change", all five)

30. `ruff check .`, `ruff format --check .`, `pytest --create-db`, `makemigrations --check --dry-run` and `manage.py check` all pass. No settings change in this brief. If any settings file is touched, `check --deploy` runs too.
31. **Prod stack.** The verifier starts it with `ZOOM_PROVIDER=manual docker compose up -d --build`, waits for `web` to be healthy, and works over HTTP on port 8010:
    1. An IT user adds a **test** account with the dummy key `123456` (never a real key).
    2. They change it, replace the key, and remove the key.
    3. They try to take out of use an account that has a future approved class. It's refused with criterion 17's error, and what they typed is kept.
    4. They take out of use an account with no bookings. The account is no longer offered on a waiting request's detail page.
    5. `/admin/zoom/hostaccount/` returns 404.
    6. Static files come from hashed paths and return 200.

    The verifier then restores the stack that was running before.

    **Screenshots** (in the scratchpad, not committed):
    - the list at 1440 and 400, in light and dark;
    - add with errors at 1440;
    - change with a saved key at 1440;
    - the stop-booking error at 400.

## Design decisions needed
<!-- owner: tmd-planner — open questions for the user; "None" if none -->

**None open.** The owner answered Q1–Q3 on 2026-09-25. The answers to Q4, Q4b and Q5 are recorded in brief 010, and Q6 in brief 009.

**Owner's answers**

| Q | Question (short) | Owner's answer | Recorded as |
|---|---|---|---|
| Q1 | Who may manage Zoom accounts? | **Everyone in IT desk.** There's no separate role | D2 |
| Q2 | Take an account out of use while it has bookings? | **Block it.** Classes from now onwards block. Past classes don't. Keep what was typed | D8 |
| Q3 | What replaces the admin's "delete a link request"? | **A later "Cancel this booking" brief**, as a go-live prerequisite. There's no delete now | D11 |

**Decisions**

- **D1: The screens stay in `apps/zoom`.** `HostAccount` belongs there.
- **D2: Everyone in IT desk manages accounts (owner, Q1), using Django's built-in model permissions added to the `IT desk` group.** The three permissions are `view_hostaccount`, `add_hostaccount` and `change_hostaccount`. `review_linkrequest` isn't reused, and no custom "manage" permission is added.
  - **Why built-in, not reuse:** the owner sees the same effect either way. Separate permissions keep the screens honest about what they guard. If the owner later wants only some IT staff to handle accounts, that's a role change in brief 010's Staff and access, with no code change. The built-in permissions already exist and come from `django.contrib.auth`, not the admin, so they survive the admin's removal. That's less code than a custom permission.
  - **No delete:** the group gets no `delete_` permission (D4).
  - **Amends:** brief 005's criterion 18 ("`IT desk` holds exactly one permission").
  - **Risk the owner accepts:** every desk member can replace a host key, and a wrong key goes out in later approval emails. D3's "saved on … by …" line shows who changed it.
- **D3: No partial key hints.** Two visible digits of a 6-digit key cut the guesses from 1,000,000 to 10,000. The page shows **when and by whom** a key was last set instead (`host_key_changed_at` and `host_key_changed_by`). After the admin is gone, no `LogEntry` exists, so these fields are the only record of a key change.
- **D4: No hard delete in the app.** `PROTECT` already refuses accounts with bookings. Once the admin is gone, nothing deletes accounts. That's intended.
- **D5: `credential_set` isn't on the form in 008.** It's blank for every account, and nothing reads it until brief 006, which adds it to this screen along with its check `zoom.E004`.
- **D6: One form class, `HostAccountForm`,** serves both add and change, so the host-key rules are defined once. The two 005 admin form classes are deleted along with `admin.py`.
- **D7: A typed key isn't kept when the form re-renders with errors.** This is a deliberate exception to "keep what the user typed". Putting a secret back into the HTML would expose it to the browser cache, "view source" and screenshots. The note on the field says why it's gone.
- **D8: Block, don't warn (owner, Q2).**
  - **Refused:** taking an account out of use, or marking it free, while it has **upcoming** classes. That means booked classes that haven't ended yet (`ends_at > now`), so a class in progress counts.
  - **Allowed:** ended classes never block, and waiting requests hold no account, so they never block either.
  - **The rule** is `HostAccount.stop_booking_errors()` on the model. The form's `clean()` calls it on the account row, which the view locks in the same transaction (criterion 19), so it can't race an approval.
  - **Copy:** the error says how many classes are booked, over which dates, and when the change becomes possible.
  - **Consequence the owner should know:** until brief 011 exists, an account whose Zoom subscription ends early can't be taken out of use while it still has classes. IT has to wait for the last one to finish.
  - *This replaces the earlier draft's warn-and-confirm step. The `confirm_stop` field and `stop_warning` context are dropped.*
- **D9: The sidebar marks the current item by view name, not by namespace.** Brief 005 used `current_ns == "zoom"`, which would mark `Link requests` on the accounts pages too. The sidebar now compares `current` against explicit view names. `current_ns` stays as a parameter.
- **D10: Host keys can't be read anywhere any more.** Brief 005 let superusers read them in the admin (criterion 62). Now a key leaves the system only in the approval email. If that email failed, the key is in the account's Zoom profile, as criterion 25's copy says. "Send the approval email again" is a follow-up for the changelog.
- **D11: Brief 011, "Cancel this booking", is a go-live prerequisite (owner, Q3).** It adds an in-app way to cancel an approved request, or one of its classes, with a `cancelled` status. Cancelling frees the account's slots, emails the requester and, after brief 006, deletes the Zoom meeting. It also amends criterion 17's copy to add "or cancel them". The README's go-live gate lists it alongside brief 007. Until then, there's no replacement for the admin's "delete a request", and production isn't taking real bookings anyway (brief 005's gate).

## MVT plan
<!-- owner: tmd-planner -->

### Models

In `apps/zoom/models.py`, with two migrations:

- `0003_hostaccount_host_key_changed`: adds the two fields, and changes the `help_text` of `host_key_encrypted` to "Set it on the Zoom accounts page.";
- `0004_it_desk_manages_host_accounts`: a data migration (D2).

**`HostAccount`, new fields:**

| Field | Type | Notes |
|---|---|---|
| `host_key_changed_at` | `DateTimeField(null=True, blank=True, editable=False)` | When a key was last stored or removed |
| `host_key_changed_by` | `FK(AUTH_USER_MODEL, SET_NULL, null=True, blank=True, related_name="+", editable=False)` | Who did it |

**`HostAccount`, new or changed methods:**

- `set_host_key(plain, *, by=None)`: unchanged behaviour, plus it records the change (criterion 21). It keeps `@sensitive_variables("plain")`.
- `clean()`: trims and lower-cases `email`.
- `host_key_state` (a property): `"saved"`, `"saved_legacy"`, `"unreadable"` or `"none"`. It tries to decrypt, then throws the plaintext away at once.
- `upcoming_classes(now=None)`: `Occurrence.objects.booked().filter(host_account=self).upcoming(now).order_by("starts_at", "pk")`.
- `stop_booking_errors(*, is_active, is_paid, now=None) -> dict[str, str]`: criterion 17. When the new flags keep the account bookable, or there are no upcoming classes, it returns `{}` without querying further. Otherwise it runs one locking read, `upcoming_classes(now).select_for_update().values_list("starts_at", flat=True)` (criterion 19), then takes the count, first and last dates in Python and builds the messages with `class_date`.
- **A shared definition of "bookable":** a module-level `BOOKABLE = Q(is_active=True, is_paid=True)`, used by `bookable()`, plus a small `is_bookable_with(is_active, is_paid)` helper used by `stop_booking_errors`.
- **The class docstring** changes to "Managed on the Zoom accounts page by the IT desk (brief 008)".

**QuerySets:**

- `HostAccountQuerySet.with_upcoming(now=None)`: annotates `upcoming_count` (a `Count`) and `next_class_start` (a `Min`) over booked occurrences with `ends_at > now`. One query.
- `HostAccountQuerySet.for_management()`: `with_upcoming()`, ordered by `-is_active`, `sort_order`, `label`.
- `OccurrenceQuerySet.upcoming(now=None)`: `filter(ends_at__gt=now or timezone.now())`.

**Uniqueness:** `label` and `email` are already `unique=True`, and the `utf8mb4_0900_ai_ci` collation compares case-insensitively. **The backend proves this with a test.** If it doesn't hold, the backend adds an `iexact` check in `clean()`. The form's unique messages come from criterion 11.

**Data migration `0004`** follows `0002_it_desk_group`'s pattern:

1. `get_or_create` the `hostaccount` content type and the three model permissions, with Django's default names.
2. `get_or_create` the group `IT desk`.
3. `group.permissions.add(...)` the three permissions.

The reverse removes the three permissions from the group.

### URLs and views

The URLs live in `apps/zoom/urls.py`. Each view uses `LoginRequiredMixin` + `PermissionRequiredMixin`, the same split as `ReviewerRequiredMixin`. A small base mixin sets `permission_required` per view.

| Name | Path | View | Template | Permission |
|---|---|---|---|---|
| `zoom:accounts` | `zoom/accounts/` | `HostAccountListView(ListView)`, queryset `HostAccount.objects.for_management()`, `context_object_name = "accounts"`, no paging | `zoom/accounts.html` | `zoom.view_hostaccount` |
| `zoom:account_add` | `zoom/accounts/add/` | `HostAccountCreateView(CreateView)`, `form_class = HostAccountForm`, `user` passed to the form, success → `zoom:accounts` plus a message | `zoom/account_form.html` | `zoom.add_hostaccount` |
| `zoom:account_edit` | `zoom/accounts/<int:pk>/edit/` | `HostAccountUpdateView(UpdateView)`. `get_object` reads the account with `select_for_update()` on POST (criterion 19; the request is already atomic through `ATOMIC_REQUESTS`). The message depends on what changed (criterion 14) | `zoom/account_form.html` | `zoom.change_hostaccount` |

- The add and change views are decorated with `method_decorator(sensitive_post_parameters("host_key"), name="dispatch")`.
- The messages `APPROVED_EMAIL_FAILED` (views) and the unreadable-key message (services) change to criterion 25's copy.
- `detail.html` gains `can_add_account` (bool).

**`HostAccountForm(ModelForm)`** (`apps/zoom/forms.py`):

- **Model fields:** `label`, `email`, `is_paid`, `is_active`, `sort_order`, `notes`.
- **Form-only fields:**
  - `host_key`: `CharField(required=False, max_length=10)`, rendered as a `TextInput` with the attributes in criterion 9, **always rendered empty**. After an invalid bind, its bound value is blanked, and `self.key_was_typed` (a bool) is set.
  - `remove_host_key`: `BooleanField(required=False)`, removed in `__init__` when no key is saved.
- **`__init__(…, user=None)`.**
- **`clean()`:**
  - applies the "not both" rule;
  - when `self.instance.pk` is set, adds each item of `self.instance.stop_booking_errors(is_active=…, is_paid=…)` with `add_error(field, message)`.
- **`save()`:** calls `set_host_key(value, by=user)`, or `set_host_key("", by=user)` for Remove, then saves. It sets `self.key_changed` and `self.key_removed` so the view can pick the message.
- **Error messages:** those in criterion 11.

**Information architecture** (`ux-strategy:information-architecture`):

```
SHELL (signed in)
Home                                    [Menu]
[Zoom links]                            IT desk (review_linkrequest OR view_hostaccount)
├── Link requests      zoom:queue       review_linkrequest   (brief 005)
│   └── ZL-0042 …      zoom:detail
├── (Timetable)        zoom:timetable   review_linkrequest   (brief 009 inserts it here)
└── Zoom accounts      zoom:accounts    view_hostaccount
    ├── Add a Zoom account      zoom:account_add    add_hostaccount
    └── Change Zoom 03          zoom:account_edit   change_hostaccount
[Administration]                        today: is_staff → Admin; brief 010: Staff and access
```

- **Labels:** the group keeps `Zoom links`. The pages name the task (`Add a Zoom account`, `Change {name}`). The states use everyday words: `In use` / `Not in use`, `Paid` / `Free (40-minute limit)`, `Saved` / `Not saved`.
- **Wayfinding:** the sidebar item, the breadcrumb and the h1 agree. Nothing is more than two levels below Home.
- **Contextual links:**
  - request detail (no paid accounts) → `Add a Zoom account`;
  - account row → `Timetable` (brief 009).

### Context contract
<!-- The only coupling between backend and frontend: template → exact context variables and their types -->

**Everywhere:** as in brief 005: `tmd_site_name`, `user`, `perms`, `request`, `messages` and `csrf_token`.

**`partials/sidebar.html`:** the parameters are unchanged (`current`, `current_ns`, `user`, `perms`).

- The group shows when `perms.zoom.review_linkrequest or perms.zoom.view_hostaccount`.
- `Link requests` is current when `current` is `zoom:queue`, `zoom:detail`, `zoom:approve` or `zoom:reject`.
- `Zoom accounts` is current when `current` is `zoom:accounts`, `zoom:account_add` or `zoom:account_edit`.
- `Zoom accounts` gets one new icon, chosen by the designer.

**`zoom/accounts.html`** (`HostAccountListView`):

| Variable | Type | Notes |
|---|---|---|
| `accounts` | list of `HostAccount` | `pk`, `label`, `email`, `is_paid`, `is_active`, `has_host_key`, plus the annotations `upcoming_count` (int) and `next_class_start` (an aware datetime or `None`). Never `host_key_encrypted` |
| `can_add` | bool | `zoom.add_hostaccount` |
| `can_change` | bool | Account names link to `zoom:account_edit` |
| `can_review` | bool | `zoom.review_linkrequest`. Brief 009 uses it for the per-row `Timetable` link |

**`zoom/account_form.html`** (`HostAccountCreateView` and `HostAccountUpdateView`):

| Variable | Type | Notes |
|---|---|---|
| `form` | `HostAccountForm` | `label`, `email`, `is_paid`, `is_active`, `sort_order`, `notes`, `host_key` (always empty), `remove_host_key` (only when a key is saved), `form.key_was_typed` (bool). Criterion 17's errors arrive as ordinary field errors on `is_active` and `is_paid` |
| `account` | `HostAccount` or `None` | `None` on add. On change: `label`, `has_host_key`, `host_key_changed_at`, `host_key_changed_by` (a User or `None`) |
| `is_add` | bool | Chooses the h1, breadcrumb and button |
| `host_key_state` | str | `"saved"`, `"saved_legacy"`, `"unreadable"` or `"none"` |

- **`zoom/detail.html`:** gains `can_add_account` (bool).
- **Formatting:** dates and times use the `zoom_format` filters.

### Placement and reuse

- **`apps/zoom`:**
  - `models.py`, `forms.py` (`HostAccountForm`), `views.py` (3 views and a mixin), `urls.py` (3 routes);
  - `services.py` and `rotate_host_keys.py` (copy changes), `crypto.py` (docstring);
  - migrations `0003` and `0004`;
  - **`admin.py` is deleted.**
- **Tests:**
  - new: `tests/test_accounts.py`;
  - deleted: `test_admin.py`;
  - deliberate edits: `test_review_fixes.py`, `test_views.py`, `test_services.py`, `test_sidebar_zoom_group.py`, and the criterion 18 test for the `IT desk` group.
- **`templates/`:**
  - new: `zoom/accounts.html` and `zoom/account_form.html`;
  - changed: `zoom/detail.html`, `partials/sidebar.html`, `partials/icons.html`;
  - reused: the error summary, `partials/crumb.html`, and the datagrid, tag, notice, box, options and choice components.
- **`static/`:** CSS only if the designer needs it. No JS.
- **`.env.example`:** the comment rewording (`tmd-devops`).
- **Reused from Django:** `ListView`, `CreateView`, `UpdateView`, `ModelForm`, the auth mixins, model permissions and `Group`, `messages`, `sensitive_post_parameters` / `sensitive_variables`, and `select_for_update`.
- **Not built:**
  - a delete view, key hints or a key reveal;
  - a custom permission or a separate role;
  - a confirmation step, any JS, or new settings.
- **New dependencies:** none.

## Agent plan
<!-- owner: tmd-planner — ordered steps; mark steps that can run in parallel -->

1. **`tmd-ui-designer`:** the Design section. It covers:
   - the list, desktop and phone;
   - the add and change form;
   - the host-key block;
   - how the stop-booking errors look on the `In use` and `Paid` ticks;
   - the tags, the icon and the empty state;
   - the reworded line on the detail page.
2. **In parallel, after the Design section** (the context contract is fixed):
   - **2a. `tmd-django-backend`:** the model, the migrations, the form, the views and URLs, the copy changes, deleting `admin.py` and `test_admin.py`, rewriting the admin-based tests, and the tests. Criteria 1–2, 4–6, 10–25 and 29.
   - **2b. `tmd-frontend`:** the templates, the `detail.html` line, the sidebar, the icons and the CSS. Criteria 3, 7–9, 12–13, 17 (the markup) and 26–28.
   - **2c. `tmd-devops`:** the comment in `.env.example`.
3. **`tmd-test-verifier`:** criteria 1–31. A FAIL goes back to 2a, 2b or 2c.
4. **`tmd-code-reviewer`:** a read-only review, focused on:
   - host-key handling;
   - the Q2 block and its row lock;
   - thin views and the permission matrix;
   - that nothing in `apps/zoom` still depends on the admin.

   If it requests changes, go back to step 2, then step 3.
5. **`tmd-docs-writer`:** updates these files, then closes the brief:
   - **README:**
     - the Zoom accounts page;
     - who can use it (the IT desk);
     - that host keys can't be read anywhere, and what to do if a key leaks;
     - the Q2 rule;
     - the go-live prerequisites (007 and **011**).
   - **CLAUDE.md:** the `zoom` app bullet.
   - **`docs/CHANGELOG.md`:** the follow-ups, which are "send the approval email again" (D10) and brief 011 (D11).

**Order:** 008 → 010 → 009. The designers for 010 and 009 may work while 008 is in steps 2–5.

## Design
<!-- owner: tmd-ui-designer — layout + wireframes, components (existing classes), states, copy, accessibility, progressive enhancement -->

Built inside the approved f-desk direction. Every class named below already exists in `static/css/style.css` or in the brief-005 component notes (`docs/design/form-section.md`, `status-tabs.md`, `availability-list.md`, `flash-messages.md`). **No new component, no CSS change and no JS change.** There's one new template partial (`zoom/partials/account_tag.html`, D.4) and four new sprite icons (D.5).

### D.1 The list: `zoom/accounts.html`

**Structure, top to bottom, inside `<main>`:**

1. `.titlebar`: h1 `Zoom accounts`, crumbs `Home › Zoom accounts` (`partials/crumb.html`, `current=True`).
2. `partials/messages.html` (the success flashes from add and change land here).
3. One `.box`:
   - `.box__head`: `h2.box__title` `Accounts ({n})`, where `{n}` is `accounts|length`. When `can_add`, the head's second child is `a.button.button--primary` → `zoom:account_add`, holding the `plus` icon (`aria-hidden`) and `Add a Zoom account`. `.box__head` is already flex with `space-between` and `wrap`, so the button sits at the right on desktop and wraps under the title on phones.
   - `.box__body`:
     - `p.box__lead`: `Classes can be booked only on accounts that are paid and in use. For safety, saved host keys are never shown.`
     - `.datagrid-wrap` > `table.datagrid` with `role="table"` and the other explicit roles, copied from `queue.html` so the phone cards still read as a table.
     - Or, with no accounts, the `.empty` state (D.1 States).

**Desktop (≥ 992px, 1440 shown):**

```
┌────────────┬───────────────────────────────────────────────────────────────────────────────┐
│ Menu       │ Zoom accounts                                           Home › Zoom accounts  │
│  Home      │ ┌───────────────────────────────────────────────────────────────────────────┐ │
│ ZOOM LINKS │ │ ✓ Added Zoom 05.                                                      (x) │ │  flash, only after a redirect
│  Link req. │ └───────────────────────────────────────────────────────────────────────────┘ │
│ ▌Zoom acc. │ ┌───────────────────────────────────────────────────────────────────────────┐ │
│            │ │ Accounts (5)                                       [ + Add a Zoom account ] │ │  box head
│ ADMINISTR. │ ├───────────────────────────────────────────────────────────────────────────┤ │
│  Admin     │ │ Classes can be booked only on accounts that are paid and in use. For      │ │  box lead (muted)
│            │ │ safety, saved host keys are never shown.                                  │ │
│            │ │ Name     Zoom sign-in email      Type         In use       Host key   Upcoming classes     │
│            │ │ ───────────────────────────────────────────────────────────────────────── │ │
│            │ │ Zoom 01  zoom01@polymath.edu.lk  [▭ Paid]     [✓ In use]   [⚷ Saved]  2 booked             │
│            │ │                                                                       Next: Mon 28 Sep 2026, 9:00 am │
│            │ │ Zoom 03  zoom03@polymath.edu.lk  [▭ Paid]     [✓ In use]   [△ Not saved] None booked       │
│            │ │ Zoom 07  zoom07@polymath.edu.lk  [◷ Free (40-minute limit)] [‖ Not in use] [⚷ Saved] None booked │
│            │ └───────────────────────────────────────────────────────────────────────────┘ │
└────────────┴───────────────────────────────────────────────────────────────────────────────┘
```

**Phone (< 768px, 400 shown):** the ported datagrid card pattern. Each row becomes a bordered card, and each cell shows its `span.datagrid__label` (`aria-hidden`) at `--row-label-w` beside the value. The `Add` button wraps under `Accounts (5)` at its natural width.

```
┌──────────────────────────────────────┐
│ ☰  (top bar)                         │
│ Zoom accounts                        │
│ Home › Zoom accounts                 │
│ ┌──────────────────────────────────┐ │
│ │ Accounts (5)                     │ │
│ │ [ + Add a Zoom account ]         │ │
│ ├──────────────────────────────────┤ │
│ │ Classes can be booked only on …  │ │
│ │ ┌──────────────────────────────┐ │ │
│ │ │ Name       Zoom 01  (link)   │ │ │
│ │ │ Sign-in    zoom01@polymath.  │ │ │
│ │ │ email      edu.lk            │ │ │
│ │ │ Type       [▭ Paid]          │ │ │
│ │ │ In use     [✓ In use]        │ │ │
│ │ │ Host key   [⚷ Saved]         │ │ │
│ │ │ Upcoming   2 booked          │ │ │
│ │ │ classes    Next: Mon 28 Sep  │ │ │
│ │ │            2026, 9:00 am     │ │ │
│ │ └──────────────────────────────┘ │ │
│ │ ┌──────────────────────────────┐ │ │
│ │ │ Name       Zoom 03 …         │ │ │
└──────────────────────────────────────┘
```

**Table markup, column by column** (criterion 4's order; the phone label is the `datagrid__label` text):

| # | `<th scope="col">` | Cell | Phone label |
|---|---|---|---|
| 1 | `Name` | `<th scope="row" role="rowheader">`. When `can_change`: `a.datagrid__ref.tap-link` → `zoom:account_edit account.pk`, content `<span class="visually-hidden">Change </span>{{ account.label }}`, so a screen reader's link list reads "Change Zoom 01". Otherwise: `span.datagrid__ref` with the label and no link. Add `.break-anywhere` | `Name` |
| 2 | `Zoom sign-in email` | `span.break-anywhere` with `account.email`. It isn't a `mailto:` link: nobody emails a Zoom account | `Sign-in email` |
| 3 | `Type` | `account_tag.html` with `kind="type"` (D.4) | `Type` |
| 4 | `In use` | `account_tag.html` with `kind="use"` | `In use` |
| 5 | `Host key` | `account_tag.html` with `kind="key"` | `Host key` |
| 6 | `Upcoming classes` | When `upcoming_count > 0`: `span.datagrid__stack` holding `span.datagrid__strong` `{n} booked`, then `<span>Next: <time datetime="{{ next_class_start\|date:'c' }}">{{ next_class_start\|class_date }}</time>, {{ next_class_start\|class_time }}</span>`. When it's 0: `span.text-muted` `None booked` | `Upcoming classes` |

- `<caption class="visually-hidden">`: `Zoom accounts, those in use first`.
- Keep the ported `.datagrid th { white-space: nowrap }`. The email column wraps through `.break-anywhere`, so the table fits at 1024px beside the sidebar without scrolling sideways.

**States (list):**

| State | What shows |
|---|---|
| Default | The box, with the lead and the table |
| Empty (`accounts` is empty) | The box head still shows `Accounts (0)` and, when `can_add`, the Add button. In place of the lead and table: `.empty` > `span.disc.disc--64` (the `layers` icon) + `<h3>No Zoom accounts yet.</h3>` (h3 because it sits under the box's h2; it looks the same as the queue's empty heading) + `<p>`. The `<p>` reads `Add the paid Zoom accounts the school uses, so IT can book classes on them.` when `can_add`, or `Ask someone in the IT desk to add them.` otherwise. The empty state has no second button: the one in the box head is the only Add action on the page |
| Key-less viewer (`view` only) | The same page, with no Add button and names as plain text (criterion 2) |
| After a successful add or change | The redirect lands here with the flash (D.6) above the box |
| Loading | None. It's a full page load with no async parts |
| No permission / signed out | Handled by the view: 403, or a redirect to sign-in (criterion 2). See gap G6 |

### D.2 Add and change: `zoom/account_form.html` (one template, `is_add` chooses the words)

**Structure, top to bottom, inside `<main>`:**

1. `.titlebar`:
   - **Add:** h1 `Add a Zoom account`; crumbs `Home › Zoom accounts › Add a Zoom account`; `<title>` `Add a Zoom account`.
   - **Change:** h1 `Change {saved_label}`; crumbs `Home › Zoom accounts › {saved_label}`; `<title>` `Change {saved_label}`.
   - The h1 is wrapped in `span.break-anywhere`, as `detail.html` does. `saved_label` is the stored name, not what was just typed (gap G3).
2. `zoom/partials/error_summary.html` with `form=form lead="We couldn't save this account yet." only`. It renders only after a failed POST and is the first thing after the title row, because no flashes exist on a re-render.
3. One `.box` with no head (the h1 already names the page) > `.box__body` > `.box__form` (640px) > `<form method="post" novalidate>` holding `{% csrf_token %}`, three `fieldset.formsection` blocks and `.form-actions`.

**Field order = form order = error-summary order** (gap G1). The summary walks `{% for field in form %}`, so the form must declare the fields in the order they appear on screen:

| Section (`legend.formsection__title`) | Field | Rendered with | Label (pinned) | Help (`id="<name>-help"`) |
|---|---|---|---|---|
| **The account** | `label` | `zoom/partials/field.html` with `narrow=True` | `Name` | `A short name IT uses for this account, like Zoom 01.` |
| | `email` | `field.html` | `Zoom sign-in email` | `The email address this account signs in to Zoom with.` |
| | `notes` | `field.html` (textarea) | `Notes` | `Optional. Anything IT should remember, like who pays for it or when it renews.` |
| **Booking** | *(change only, see the booked-classes note below)* | `.notice.notice--note` | | |
| | `is_paid` | the `.check` pattern from `request_form.html`'s `wants_recording` (below) | `Paid account` | `Free Zoom accounts end meetings after 40 minutes, so only paid accounts can be booked.` |
| | `is_active` | `.check` pattern | `In use` | `Untick it to stop new bookings on this account. Nothing is deleted, and you can tick it again later.` |
| | `sort_order` | `field.html` with `narrow=True` | `Order` | `Lower numbers are suggested first when several accounts are free.` |
| **Host key** | *(change only, the state line)* | `.notice`, see D.3 | | |
| | *(only when `form.key_was_typed`)* | `.notice.notice--warn`, see D.3 | | |
| | `host_key` | `field.html` with `narrow=True` | Add: `Host key`. Change: `New host key` | See D.3 |
| | `remove_host_key` (only when present on the form) | `.check` pattern | `Remove the saved host key` | `Tick this if the saved key is wrong and you don't have the new one yet. Approval emails will then tell the requester to ask the IT desk for the host key.` |

- **Where the copy lives:** all label and help text lives on the form (`labels` / `help_texts`, or set in `__init__` for the host-key help that depends on the state). `field.html` only prints `field.label` and `field.help_text`, so the form is the only source.
- **The `.check` pattern (for `is_paid`, `is_active` and `remove_host_key`):** `div.field` > `label.check[for]` (the input first, then `{{ field.label }}`) > `p.field__help.check__help#<name>-help` > `zoom/partials/field_error.html`. With an error, the input gets `aria-invalid="true"` and `aria-describedby="<name>-error <name>-help"`; otherwise `aria-describedby="<name>-help"`. That's exactly `request_form.html` lines 18–22.
- **Widget attributes (gap G5), set on the form's widgets so `field.html` prints them:**
  - `label`: `autocomplete="off"`, plus the model's `maxlength`.
  - `email`: `type="email"`, `autocomplete="off"`, `spellcheck="false"`. Without `off`, browsers offer the signed-in IT person's own address.
  - `sort_order`: `type="number"`, `min="0"`, `step="1"`, `inputmode="numeric"`.
  - `host_key`: `autocomplete="off"`, `inputmode="numeric"`, `spellcheck="false"`, `maxlength="10"` (criterion 9). It's a plain text input, not `type="password"`, so the person can check the digits they typed on their own screen. It's always rendered with no `value`.
- **Booked-classes note (change only, gap G4).** It prevents Q2's error rather than only reporting it. It shows as the first child of the **Booking** section when `upcoming_count > 0` **and** neither `is_paid` nor `is_active` has an error (on the stop-booking re-render, the field errors say the same thing more precisely). The markup is `.notice.notice--note`, with the `info` icon (`aria-hidden`) and `p`:
  - one class: `{saved_label} has 1 booked class, on {Mon 5 Oct 2026}. It must stay paid and in use until that class has finished.`
  - more: `{saved_label} has {n} booked classes. The next one is on {Mon 28 Sep 2026}. It must stay paid and in use until the last one has finished.`

  Dates use `class_date`. With no `upcoming_count` in the context, the note is simply not rendered.
- **`.form-actions`:**
  - `button.button.button--primary[type=submit]`: `Add the account` (add) / `Save changes` (change);
  - `a.button.button--quiet` → `zoom:accounts`: `Cancel`.

  Below 600px both are full width (the existing `.form-actions .button` rule).

**Desktop (1440, change, a key saved, no errors):**

```
Change Zoom 03                                   Home › Zoom accounts › Zoom 03
┌────────────────────────────────────────────────────────────────────────────┐
│  ┌──── .box__form, 640px ─────────────────────────┐                         │
│  │ The account                                     │                         │
│  │ Name                                            │                         │
│  │ A short name IT uses for this account, like …   │                         │
│  │ [Zoom 03            ]                           │                         │
│  │ Zoom sign-in email                              │                         │
│  │ The email address this account signs in to …    │                         │
│  │ [zoom03@polymath.edu.lk                      ]  │                         │
│  │ Notes                                           │                         │
│  │ Optional. Anything IT should remember, …        │                         │
│  │ [                                            ]  │                         │
│  │ ─────────────────────────────────────────────── │                         │
│  │ Booking                                         │                         │
│  │ ┌ i  Zoom 03 has 12 booked classes. The next ─┐ │  notice--note           │
│  │ │    one is on Mon 28 Sep 2026. It must stay …│ │                         │
│  │ └─────────────────────────────────────────────┘ │                         │
│  │ [x] Paid account                                │                         │
│  │     Free Zoom accounts end meetings after …     │                         │
│  │ [x] In use                                      │                         │
│  │     Untick it to stop new bookings on this …    │                         │
│  │ Order                                           │                         │
│  │ Lower numbers are suggested first when …        │                         │
│  │ [ 30         ]                                  │                         │
│  │ ─────────────────────────────────────────────── │                         │
│  │ Host key                                        │                         │
│  │ ┌ ✓  Host key saved on Mon 21 Sep 2026 by ────┐ │  notice--ok (state line)│
│  │ │    Nimal Perera                             │ │                         │
│  │ └─────────────────────────────────────────────┘ │                         │
│  │ New host key                                    │                         │
│  │ Leave it empty to keep the saved key.           │                         │
│  │ [            ]                                  │                         │
│  │ [ ] Remove the saved host key                   │                         │
│  │     Tick this if the saved key is wrong and …   │                         │
│  │                                                 │                         │
│  │ [ Save changes ]  Cancel                        │                         │
│  └─────────────────────────────────────────────────┘                         │
└────────────────────────────────────────────────────────────────────────────┘
```

**Phone (400, the stop-booking error, criterion 17):**

```
┌──────────────────────────────────────┐
│ Change Zoom 03                       │
│ Home › Zoom accounts › Zoom 03       │
│ ┌ ⬣ We couldn't save this account ─┐ │  error summary, focused (JS)
│ │   yet. 1 thing needs your        │ │
│ │   attention.                     │ │
│ │   • Zoom 03 still has 12 booked  │ │  link → #id_is_active
│ │     classes, from Mon 28 Sep …   │ │
│ └──────────────────────────────────┘ │
│ ┌──────────────────────────────────┐ │
│ │ The account                      │ │
│ │ … (typed values kept)            │ │
│ │ ──────────────────────────────── │ │
│ │ Booking                          │ │  (no booked-classes note: the error says it)
│ │ [x] Paid account                 │ │
│ │     Free Zoom accounts end …     │ │
│ │ [ ] In use                       │ │  kept as the user left it
│ │     Untick it to stop new …      │ │
│ │ (!) Zoom 03 still has 12 booked  │ │  .field__error, alert-circle + words
│ │     classes, from Mon 28 Sep     │ │
│ │     2026 to Wed 28 Oct 2026. It  │ │
│ │     can be taken out of use once │ │
│ │     the last one has finished.   │ │
│ │ Order …                          │ │
│ │ ──────────────────────────────── │ │
│ │ Host key …                       │ │
│ │ [      Save changes      ]       │ │  full width < 600px
│ │ [         Cancel         ]       │ │
│ └──────────────────────────────────┘ │
└──────────────────────────────────────┘
```

### D.3 The host-key block (the **Host key** section)

**1. State line (change only).** It's a `.notice` with an icon (`aria-hidden`) and one `p`. It has **no** `role` and **no** `data-error-summary`: it's page content, not an alert, and it must not take focus.

| `host_key_state` | Notice | Icon | Text (pinned by criteria 13 and 15) |
|---|---|---|---|
| `"saved"` | `notice--ok` | `check-circle` | `Host key saved on {account.host_key_changed_at\|class_date} by {account.host_key_changed_by}`. Leave out ` by {…}` when `host_key_changed_by` is `None`. The user prints as it does on `detail.html` (`{{ user }}`) |
| `"saved_legacy"` | `notice--ok` | `check-circle` | `Host key saved` |
| `"none"` | `notice--warn` | `alert-triangle` | `No host key saved` as `p.notice__title`, then `p`: `Until one is saved, approval emails tell the requester to ask the IT desk for the host key.` |
| `"unreadable"` | `notice--bad` | `alert-octagon` | `A host key is saved, but it can't be read with the current encryption keys. Type it again.` |

On **add** there's no state line: nothing can be saved yet.

**2. "Your key wasn't kept" note (criterion 12, D7).** When `form.key_was_typed` is true, render `div.notice.notice--warn#host_key-note` with the `alert-triangle` icon and `p` `For your safety, the host key you typed wasn't kept. Type it again.`, directly above the `host_key` field. The input's `aria-describedby` then becomes `host_key-note host_key-help`, or `host_key-error host_key-note host_key-help` when the key itself has an error. This is the one place `field.html`'s generated `aria-describedby` isn't enough. **The frontend writes the `host_key` field out in the template** (same markup as `field.html`, plus the extra id) rather than adding a parameter to the shared partial.

**3. The input.**

| Page / state | Label | Help (form `help_text`) |
|---|---|---|
| Add | `Host key` | `Optional. The 6 to 10 digits from the Profile page of this account in Zoom. You can add it later.` |
| Change, `saved` / `saved_legacy` | `New host key` | `Leave it empty to keep the saved key.` (pinned) |
| Change, `unreadable` | `New host key` | `Leave it empty to keep the saved key.` The state line above already asks for a new one |
| Change, `none` | `New host key` | `Type the 6 to 10 digits from the account's Zoom profile.` (pinned) |

- **Errors** come from the form, under the input as `.field__error`: `A Zoom host key is 6 to 10 digits.` and `Type a new host key or tick Remove, not both.`
- The input is always empty. On an error re-render, the `.field__error` and the "wasn't kept" note both show. The error still says what was wrong with the key the person typed.

**4. Remove.** `remove_host_key` is shown only when the form has the field (a key is saved, including `unreadable`), using the `.check` pattern (D.2). With JS off or on, both controls stay enabled. The "not both" rule is enforced by the server (criterion 14). No JS disables one when the other is used, because the brief adds no JS.

### D.4 Tags: `zoom/partials/account_tag.html` (new partial, not a new component)

This follows `zoom/partials/status_tag.html`. The tone, icon and word for each account state are chosen **here and nowhere else**. Call it with `kind` (`"type"`, `"use"` or `"key"`) and `on` (bool: `account.is_paid`, `account.is_active` or `account.has_host_key`).

| `kind` | `on` | Class | Icon | Word |
|---|---|---|---|---|
| `type` | true | `tag tag--brand` | `credit-card` | `Paid` |
| `type` | false | `tag tag--warn` | `clock` | `Free (40-minute limit)` |
| `use` | true | `tag tag--ok` | `check-circle` | `In use` |
| `use` | false | `tag tag--plain` | `pause-circle` | `Not in use` |
| `key` | true | `tag tag--plain` | `key` | `Saved` |
| `key` | false | `tag tag--warn` | `alert-triangle` | `Not saved` |

- **Why these tones:**
  - `Paid` is a category rather than a status, so it takes the brand tone, not a status colour.
  - `Free` and `Not saved` are the two things that stop, or weaken, a booking, so they take the warning tone.
  - `Saved` and its `key` icon match what `detail.html` already shows beside each account.
- All the pairs are the existing tag tokens, with contrast checked at 10.5px in brief 005 (`availability-list.md`, `status-tabs.md`).
- The word is always present, and the icon and colour only repeat it.

### D.5 Sidebar and icons

- **`partials/sidebar.html`:** the `Zoom links` group, `id="nav-zoom"`, renders when `perms.zoom.review_linkrequest or perms.zoom.view_hostaccount`. Each item is wrapped in its own permission check:
  - `Link requests` (`video`) → `zoom:queue`. It's current when `current` is in `zoom:queue`, `zoom:detail`, `zoom:approve` or `zoom:reject`.
  - `Zoom accounts` (**`layers`**, a stack of accounts) → `zoom:accounts`. It's current when `current` is in `zoom:accounts`, `zoom:account_add` or `zoom:account_edit`.

  Update the header comment to drop the "`current_ns == "zoom"` marks Link requests" wording (D9). The current item's look is the existing `aria-current="page"` style (bar plus weight).
- **`partials/icons.html`:** add four Feather symbols, `i-layers`, `i-plus`, `i-credit-card` and `i-pause-circle`, and extend its header comment ("Brief 008 added …"). Each one is used, which keeps the sprite guard test passing. `layers` was picked to avoid the likely choices of the parallel briefs (a calendar for 009's timetable, people for 010's staff).

### D.6 Feedback, copy and states (all pages)

**Success flashes** (`messages.success`, so the `ok` family with `check-circle` and `role="status"`). They show on `zoom:accounts` after the redirect:

| Action | Flash (pinned, criteria 10 and 14) |
|---|---|
| Add | `Added {label}.` |
| Change, key untouched | `Saved {label}.` |
| Change, new key | `Saved {label}. The new host key goes out with the next approved link.` |
| Change, key removed | `Saved {label}. Its host key was removed.` |

**Validation errors.** The field messages are pinned in criteria 11, 14 and 17, and none contains a typed key. The page shows the summary (`We couldn't save this account yet. {n} thing(s) need(s) your attention.`), one link per invalid field, and a `.field__error` under each field. Every typed value is kept except the host key (D.3).

**Other states:**

| State | Behaviour |
|---|---|
| Unknown account (`pk`) | 404 (Django's page) |
| Server error while saving | A plain 500. `ATOMIC_REQUESTS` rolls back everything, so nothing is half-saved. No custom copy in this brief |
| The approval race (criterion 19) | Nothing is visible: the save waits for `approve()`'s lock, then either saves or shows the criterion-17 error |
| Loading | None |
| No permission | 403 / login redirect, per criterion 2 (see G6) |

**`zoom/detail.html`, the reworded line (criterion 25).** It goes in the `Which accounts are free` box, in place of the current `box__lead`:

- with `can_add_account`: `<p class="box__lead">No paid Zoom accounts are set up yet. <a class="tap-link" href="{% url 'zoom:account_add' %}">Add a Zoom account</a></p>`;
- otherwise: `<p class="box__lead">No paid Zoom accounts are set up yet. Ask someone in the IT desk to add them.</p>`.

`.box__lead` is muted text, and the link keeps the ported link colour and underline. `.tap-link` makes it 44px on phones. Also drop "the admin" from the header comment if it mentions it.

### D.7 Accessibility

- **Landmarks and headings:**
  - The landmarks come from the shell, unchanged: `nav[aria-label=Main]`, `main#main`, `nav[aria-label=Breadcrumb]`.
  - **List:** h1 `Zoom accounts` → h2 `Accounts ({n})` → (empty only) h3.
  - **Form:** h1 only. The three sections are `fieldset` / `legend` (`.formsection`), so each field's group name is read with it, and the outline stays h1 → content. One h1 per page.
- **Table:** a visually hidden `<caption>`, `th scope="col"` for each column and `th scope="row"` for the name. The explicit `role` attributes are kept so the phone cards still read as a table. `datagrid__label` is `aria-hidden` (the cell's column header already names it).
- **Label, help and error wiring:** every control has a `<label for>`. Help is `#<name>-help` and errors are `#<name>-error`. An invalid control gets `aria-invalid="true"` and `aria-describedby="<name>-error <name>-help"`, with the error first so it's heard first. The host key adds `host_key-note` (D.3). Checkbox errors sit under their help, inside the same `.field`.
- **Focus:**
  - **After a failed POST:** `app.js`'s existing `[data-error-summary]` hook focuses and scrolls to the summary. Each summary link moves focus to its field (`#id_is_active`, `#id_host_key`, …). Without JS, the summary is the first thing after the title row.
  - **After a successful redirect:** normal page-load focus. The flash is the first content after the h1, and its Close button (JS) returns focus to `<main>`, as in brief 004.
  - **Tab order on the list:** crumbs → `Add a Zoom account` → each row's name link, top to bottom.
  - **Tab order on the form:** Name → Sign-in email → Notes → Paid account → In use → Order → (New) host key → Remove → Save / Add → Cancel. That's the visual order, because the form's field order matches it (G1).
  - The notices (the state line, the booked-classes note, the "wasn't kept" note) aren't focusable and aren't live regions.
- **Touch targets:**
  - `.button` is 44px tall. `.check` rows have `min-height: var(--target)`, and the whole label is the target.
  - The name links are `.tap-link` (44px below 768px).
  - The crumb links are padded to 44px on phones (existing CSS). The sidebar links are already 44px or more.
- **Status is never colour alone:** every tag and notice has an icon plus words, and errors have `alert-circle` plus words and a 2px border on text inputs.
- **Reflow:** 320px reflow and no sideways page scroll at 320, 400, 1024 and 1440 in both modes. The cards stack below 768px, and `.break-anywhere` covers long emails and names.

### D.8 Progressive enhancement

- **With plain HTML and full page loads, everything works:** the list, the empty state, add, change, the host-key set, replace and remove, every error including the stop-booking one, the summary links (fragment links) and the flashes (without a Close button).
- **What `app.js` adds, using only hooks that already exist:**
  - it focuses the error summary (`data-error-summary`);
  - it shows the flashes' Close button (`data-flash`, `data-flash-close`);
  - it runs the sidebar drawer.
- **No new `data-*` hooks and no new JS.**

### Gaps in the context contract (backend to add or confirm)

- **G1 — Field order.** Declare `HostAccountForm` fields as `label, email, notes, is_paid, is_active, sort_order, host_key, remove_host_key`. The error summary and the tab order both follow this order.
- **G2 — Copy on the form.** The labels and help texts in D.2 and D.3 are set on `HostAccountForm`, including the host-key help that depends on add/change and `host_key_state`. The model's old `help_text` (e.g. "like the heading in the old spreadsheet") isn't shown.
- **G3 — `saved_label` (str), new, on change.** The account's **stored** label, for the h1, breadcrumb, `<title>` and booked-classes note. On an invalid POST, `UpdateView`'s `self.object` is the form's instance, which `construct_instance` has already overwritten with the typed (possibly empty or duplicate) name. `account.label` would then show what was typed. On add, it's unused.
- **G4 — `upcoming_count` (int) and `next_class_start` (aware datetime or `None`), new, on change.** They drive the booked-classes note (D.2) that prevents the Q2 error. They can come from `HostAccount.objects.with_upcoming()` or `account.upcoming_classes()`. They're read-only facts: the locking read in `stop_booking_errors` stays the authority. If the backend declines this, the frontend leaves the note out and nothing else changes.
- **G5 — Widget attributes** as listed in D.2, set on the form's widgets.
- **G6 — No-permission page (not for this brief).** The app has no `403.html`, so a plain user sees Django's bare "403 Forbidden". It's the same today for brief 005's queue. A shared, plain-language 403 page (`You don't have access to this page. Ask someone in the IT desk if you need it.`) fits brief 010 (Staff and access). It's noted here, not added.
- **Confirmation for the backend:** criterion 17's messages use the account's label. Build them from the stored label, which is what `self.instance.label` is inside `form.clean()`: `construct_instance` runs after `clean()`.

## Implementation notes
<!-- owners: tmd-devops, tmd-django-backend, tmd-frontend — one sub-heading each: files changed, contract deviations, migrations, new deps (with reason), self-check output -->

### tmd-devops

- **Files changed:** `.env.example` only. The `HOST_KEY_ENCRYPTION_KEYS` comment now reads "…losing every key means re-typing all host keys on the Zoom accounts page." (it's wrapped onto two lines to stay within the file's width). This is a comment-only change: the variable, its default and the rotation steps are the same.
- **Other devops files checked** for admin wording: `compose*.yaml`, `Dockerfile`, `docker/**`, `config/settings/**`, `requirements/**` and `pyproject.toml`. None needs a change in 008. `"django.contrib.admin"` in `base.py` `DJANGO_APPS` is left alone because brief 010 removes it. The `mysqladmin` in the compose healthcheck is the MySQL tool, not the Django admin.
- **New env vars / dependencies / settings:** none. No `check --deploy` run is needed.
- **Operational steps:** none. No rebuild is needed because `.env.example` isn't read at runtime and nobody's local `.env` changes.
- **Self-check:** `docker compose config --quiet` passed for the prod stack and the dev stack. I didn't rebuild the image or run `pytest --create-db`, because a comment in `.env.example` can't affect either. Backend and frontend (2a/2b) may still be changing `apps/zoom`, so a test run now wouldn't tell us anything about this change. Step 3 covers the full check.

### tmd-django-backend

**Files changed**

- **`apps/zoom/models.py`:**
  - `BOOKABLE_FLAGS` / `BOOKABLE` / `is_bookable_with()`: the one definition of "bookable", used by `bookable()` and by the stop rule;
  - `HostAccountQuerySet.with_upcoming()` and `for_management()`;
  - `OccurrenceQuerySet.upcoming()`;
  - `HostAccount`: `host_key_changed_at` / `host_key_changed_by`, `clean()` (email trim and lower-case), `set_host_key(plain, *, by=None)` (records the change, still `@sensitive_variables("plain")`), `host_key_state`, `upcoming_classes()`, `stop_booking_errors()`, the criterion-17 copy constants;
  - docstrings and `help_text` reworded away from the admin.
- **`apps/zoom/forms.py`:** `HostAccountForm` (D6, G1, G2, G5), plus the criterion 11/12/14 copy constants.
- **`apps/zoom/views.py`:** `AccountPermissionMixin`, `HostAccountListView`, `HostAccountFormViewMixin`, `HostAccountCreateView`, `HostAccountUpdateView`; `can_add_account` in the detail context; the `APPROVED_EMAIL_FAILED` copy (criterion 25).
- **`apps/zoom/urls.py`:** `accounts`, `account_add`, `account_edit`.
- **`apps/zoom/validators.py`:** `validate_host_key` is now `@sensitive_variables("value")` (the second half of 005 review nit 2).
- **`apps/zoom/services.py`**, **`crypto.py`**, **`management/commands/rotate_host_keys.py`:** criterion 25 copy and docstrings.
- **Deleted:** `apps/zoom/admin.py`, `apps/zoom/tests/test_admin.py`.
- **Migrations:** `0003_hostaccount_host_key_changed.py` (generated, reviewed: two `AddField`s and the `help_text` `AlterField`) and `0004_it_desk_manages_host_accounts.py` (data migration, with a reverse function).
- **Tests:**
  - new: `apps/zoom/tests/test_accounts.py` (criteria 2, 4–25);
  - deliberately edited:
    - `conftest.py`: stubs for the two new templates;
    - `test_views.py`: criterion 1's group test, the 0004 migration test, the criterion 25 copy, and the full-flow logging test rewritten against `zoom:account_add` / `zoom:account_edit`;
    - `test_review_fixes.py`: the error-report test rewritten against both account pages, plus the nit-2 tests;
    - `test_services.py`: the criterion 25 copy, and a rotation test for criterion 21;
    - `test_models.py`: the secret-name test (see deviation 5);
    - `test_sidebar_zoom_group.py`: criterion 3, against the real templates.

**Context contract, as implemented**

- **`zoom/accounts.html`:** `accounts` (the `for_management()` queryset; each row has `upcoming_count` and `next_class_start`), `can_add`, `can_change` and `can_review`. Exactly as in the contract.
- **`zoom/account_form.html`:**
  - `form`;
  - `account` (`None` on add);
  - `is_add`;
  - `host_key_state` (`"none"` on add);
  - and on change only, G3 and G4: `saved_label`, `upcoming_count` (int) and `next_class_start`. All three are captured in `get_object()` from the stored row, before `construct_instance` overwrites it.
  - `form.key_was_typed` is set on every bind. After an invalid bind, `host_key` is removed from the bound data, so `form.host_key.value()` is `None`.
- **`zoom/detail.html`:** `can_add_account`.
- **No names were changed.**

**Deviations and decisions (please check in review)**

1. **Only a tick being removed is refused.** `stop_booking_errors()` reports a field only when the stored value is `True` and the new one is `False`. An account that's already out of use, and has upcoming classes from older data, can still have its notes or order saved. Without this, such an account could never be edited. There's also one unpinned wording case, 2 or more classes that all fall on one date: `…still has {n} booked classes, on {date}. It can be … once the last one has finished.` This avoids "from X to X".
2. **`with_upcoming()` uses two correlated subqueries** built from `Occurrence.objects.booked().upcoming()`, not `Count`/`Min` over a join. The "booked" and "upcoming" rules stay defined once, and it's still one query (criterion 6 is tested).
3. *(Superseded by review round 1, B1: the read now also locks `zoom_linkrequest`. See "Review round 1 fixes" below.)* **The locking read is `select_for_update(of=("self",))`.** It locks only the `zoom_occurrence` rows (`FOR UPDATE OF zoom_occurrence`). A plain `FOR UPDATE` would also lock the joined `zoom_linkrequest` rows after the account. `approve()` takes those locks in the opposite order, so the two could deadlock. The criterion 19 test asserts the account lock, then the occurrence lock, then the `UPDATE`, and that no `zoom_linkrequest` table is named in the `OF`.
4. **`validate_host_key` is masked too.** Nit 2 named both the `clean_host_key` local and the validator's argument. `clean_host_key`, `clean`, `full_clean` and `save` on the form all mask their key-holding locals.
5. **Brief 005's criterion 46 secret-name test was amended.** The brief pins the field names `host_key_changed_at` / `_by`, which match that test's `host_key` pattern. The test now allows exactly those two by name, next to `host_key_encrypted`, so any other secret-looking field still fails.
6. **Case-insensitive uniqueness comes from the collation, as the MVT plan expected.** The test proves it: `zoom 01` / `ZOOM01@…` are refused through `validate_unique`, with the criterion 11 messages set as `unique` error messages on the form. No `iexact` check was needed.
7. **`sensitive_post_parameters("host_key")`** wraps `dispatch` on both concrete views, not on the shared mixin, so it's visible where the brief says.
8. **Success messages use the label as just saved**, so a rename flashes the new name.

**Dependencies and settings:** none. No settings, templates, CSS, JS or Docker files were touched.

**Self-check output** (dev container)

- `ruff format .`: 1 file reformatted, then `ruff format --check .`: "72 files already formatted".
- `ruff check .`: "All checks passed!"
- `pytest --create-db`: **391 passed**.
- `pytest apps/zoom`: **285 passed**. This includes the real-template tests for the sidebar and for "no key material on any accounts page" (criteria 8, 13, 24), run against the frontend's templates as they are now.
- `python manage.py makemigrations --check --dry-run`: "No changes detected".
- `python manage.py check`: "System check identified no issues (0 silenced)."
- The frontend's `apps/core` failure (`NoReverseMatch: 'accounts'`) is cleared now that the routes exist. It's included in the 391.

**Review round 1 fixes**

- **B1, the stop-booking locking read** (`apps/zoom/models.py`, `HostAccount.stop_booking_errors`):
  - **Fix:** it now reads `upcoming_classes().select_related("link_request").only("starts_at", "link_request__id").select_for_update(of=("self", "link_request"))`, which runs as `FOR UPDATE OF zoom_occurrence, zoom_linkrequest`. The `select_related` is required, because Django accepts `of=("link_request",)` only for a relation the query follows. `values_list` can't be combined with it, so the dates are read from the (narrowed) instances.
  - **Docstring:** rewritten. It covers why both tables are locked, and why locking the requests after the account can't deadlock with `approve()` (the reviewer's argument).
  - **Finding: the bug can't happen with today's settings, only at REPEATABLE READ.** Django's MySQL backend sets each session to **READ COMMITTED** (`connection.isolation_level == "read committed"`; `@@transaction_isolation` is `READ-COMMITTED` for the session, `REPEATABLE-READ` globally). At READ COMMITTED every statement takes a fresh snapshot. So under the current settings the review's interleaving doesn't lose the class: the unlocked join reads the status as committed when the statement starts, and that is after `approve()` committed. The bug is real at REPEATABLE READ, MySQL's own default, which one `OPTIONS["isolation_level"]` change would bring back. The fix makes the check correct at either level. The same reasoning is behind the brief-005 comment on `availability_for(lock=True)`; that code already locks every row it reads, so it needs no change.
  - **Test inverted:** `test_accounts.py::test_the_stop_check_and_save_run_under_locks_taken_before_the_update` now requires the lock SQL to end with ``FOR UPDATE OF `zoom_occurrence`, `zoom_linkrequest` ``, and asserts that `zoom_linkrequest` **is** in the `OF`.
  - **Two-connection test:** `test_race.py::test_taking_an_account_out_of_use_sees_an_approval_that_committed_while_it_waited`, parametrised over `READ COMMITTED` and `REPEATABLE READ`. It reproduces the review's sequence on two real connections:
    1. The edit opens a transaction and takes its snapshot with a plain read of the request while the request is still `waiting`.
    2. `approve()` runs on a thread with a pausing provider. It holds the request and account locks, with the classes already on the account.
    3. The edit asks for the account lock, as `get_object` does, and blocks. The test asserts that it waited at least 0.25 s.
    4. A timer lets `approve()` commit.
    5. The test asserts that `stop_booking_errors(is_active=False, …)` reports `Race 01 still has 1 booked class`.
  - **Proof:** on the **old code**, the `REPEATABLE READ` case **failed** (`assert set() == {'is_active'}`: the check missed the class) and the `READ COMMITTED` case passed, which matches the finding above. On the **fix**, both pass, 5 runs out of 5.
  - **Test pattern:** it reuses the file's `committed` fixture, tracked factories, `Race ` cleanup and thread pattern. It deliberately does **not** use `transaction=True`, although the round-1 instruction asked for it. The file's docstring explains why: its teardown flush wipes the `IT desk` group from the data migration, which later `--reuse-db` runs rely on. The tests commit for real and clean up exactly what they made, which is what `transaction=True` would otherwise provide. Only the edit's connection is switched to REPEATABLE READ, and `connection.close()` in the fixture ends that session setting.
- **Nit 1** (`stop_booking_errors`): it now returns `{}` without a query unless the **stored** flags are bookable. Only bookable → not bookable is refused, and the error still goes on each tick being removed. New test: `test_an_account_that_was_not_bookable_can_lose_its_other_tick`, for stored out-of-use and stored free. It covers the model (no queries) and the POST (302, both unticked).
- **Nit 2** (`0004_it_desk_manages_host_accounts.py`): the reverse now uses `_existing_permissions()`, a `Permission.objects.filter(…)` lookup, and never creates a content type or permission. The forward helper is renamed `_get_or_create_permissions`, and the module docstring says why. New test: `test_views.py::test_host_account_permission_migration_reverse_creates_nothing`. `makemigrations --check` is unaffected because the operations are unchanged.
- **Nit 3** (`views.py`): new `SignedInPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin)` is the one gate. `ReviewerRequiredMixin` now subclasses it and only sets the permission. It's kept by name because brief 009 names it. `AccountPermissionMixin` is removed, and the account views use the base directly with their own `permission_required`. Behaviour is unchanged, and the criterion-2 access tests pass.
- **Nit 4** (`test_models.py`): renamed to `test_no_field_name_looks_like_a_secret_except_the_host_key_and_its_change_record`.
- **Nit 5** (`models.py`): a comment above `HostAccount.label` says that the case-insensitive uniqueness of the name and email relies on `utf8mb4_0900_ai_ci`. It's pinned by `--collation-server` in `compose.yaml` and by `DATABASES["default"]["TEST"]["COLLATION"]` in `config/settings/base.py`.
- **Context contract:** unchanged. **Migrations:** none added; 0004 edited in its reverse function only. **Dependencies and settings:** none.
- **Self-check (dev container):**
  - `ruff format .`: "72 files left unchanged".
  - `ruff check .`: "All checks passed!".
  - `ruff format --check .`: "72 files already formatted".
  - `pytest --create-db`: **398 passed, 0 failed**. That's 393 plus 5: 2 race cases, 2 nit-1 cases and 1 migration test.
  - `makemigrations --check --dry-run`: "No changes detected".
  - `manage.py check`: "System check identified no issues (0 silenced)."

### tmd-frontend

**Files changed**

- **New:**
  - `templates/zoom/accounts.html`: the list (D.1), including the default, key-less viewer and empty states;
  - `templates/zoom/account_form.html`: add and change (D.2, D.3);
  - `templates/zoom/partials/account_tag.html`: D.4;
  - `templates/zoom/partials/check_field.html`: the `.check` checkbox pattern.
- **Changed:**
  - `templates/partials/sidebar.html`: the group shows for `review_linkrequest` **or** `view_hostaccount`, and each item checks its own permission. `Zoom accounts` uses `i-layers`. `aria-current` is set by view name (D9), and the header comment is updated;
  - `templates/partials/icons.html`: adds `i-layers`, `i-plus`, `i-credit-card` and `i-pause-circle` (Feather), and the header comment is extended;
  - `templates/zoom/detail.html`: criterion 25's line, gated on `can_add_account`, and the header comment names it;
  - `templates/zoom/request_form.html`: `wants_recording` now uses `check_field.html`. The markup is the same as before.
- **CSS:** one selector in section 2's base headings, where `h2 {` becomes `h2, .empty h3 {`. There's no new token and no colour literal.
- **JS:** none. The existing `data-error-summary`, `data-flash` and `data-nav` hooks do the work.

**Spec deviations**

1. **New partial `zoom/partials/check_field.html`.** The design said "one new partial". The `.check` markup now appears on two pages (request form and account form) and three times on the account form, so CLAUDE.md's "two or more pages → partial" rule applies. `request_form.html` was switched to it with identical output. The rendered markup is the same as D.2's `.check` pattern.
2. **CSS: `.empty h3`.** The design said "no CSS change", but D.1 wants the empty state's h3 to "look the same as the queue's empty heading". Only `h2` carries that style, so without the selector the h3 would render in the body colour and weight. That's why I added the selector to the existing `h2` rule rather than duplicating it.
3. **The list box is a `<section aria-labelledby="accounts-title">`,** as on `detail.html`, rather than a bare `div.box`. This names the region after its h2 and costs no extra markup.
4. **`saved_label|default:account.label`** in the h1, `<title>`, breadcrumb and booked-classes note. The template uses the contract's `saved_label` (G3). The fallback only keeps the page readable if the backend omits the key; it must still provide `saved_label` for the invalid-POST case.

**Context contract, as used (and gaps)**

- **List:** `accounts` (each needs `pk`, `label`, `email`, `is_paid`, `is_active`, `has_host_key`, `upcoming_count` and `next_class_start`), `can_add` and `can_change`. `can_review` is accepted but unused until brief 009.
- **Form:**
  - `form` fields in G1 order, plus `form.key_was_typed`. `remove_host_key` is rendered only when the field exists on the form.
  - `account`: `host_key_changed_at` and `host_key_changed_by`.
  - `is_add`, `host_key_state` and `saved_label` (G3).
  - `upcoming_count` and `next_class_start` (G4, optional: the note is left out when they're absent or 0). The note is also hidden when `is_paid` or `is_active` has an error.
- **Host key input:** written out in the template with no `value`, ever. Its attributes come from `form.host_key.field.widget.attrs` (G5), with `type` and `value` skipped. `maxlength="10"` comes from `CharField(max_length=10)`. The `aria-describedby` order is `host_key-error host_key-note host_key-help`, as D.3 and D.7 specify.
- **Detail:** `can_add_account`.
- **For the backend:**
  - the labels and help texts all come from the form (G2);
  - the host-key label and help change with add/change and `host_key_state` (D.3's table), set in `__init__`;
  - the typed key must be blanked from the bound data after an invalid bind. The template never prints `form.host_key.value()`, so the key can't leak from here either way.
- **No new gaps.**

**Self-check output**

- **Template render check (all states), passed.**
  - **How it ran:** in the dev container, through the real template engine. The backend's routes weren't in yet, so a scratch URLconf added the contract's three route names (`zoom:accounts`, `zoom:account_add`, `zoom:account_edit`), and a stand-in form mirrored the contract (the G1 fields, the G2 copy, the G5 attributes, `key_was_typed`, and a stop-booking error on `is_active`).
  - **States rendered:** list, list for the key-less viewer, empty, empty for the key-less viewer, add, add with errors and a typed key, change in the `saved` / `saved` with no user / `saved_legacy` / `unreadable` / `none` states, change with the stop-booking error, and detail with and without `can_add_account`.
  - **Assertions, all passed:** the pinned copy, the `<title>`, one h1, the crumbs, `aria-current` on the right sidebar item (and not on `Link requests`), sidebar order, every `<use>` naming a defined symbol, no `style=`, the typed key (`8421973x`, `7654321`) absent from the body, `aria-describedby="host_key-error host_key-note host_key-help"`, the summary before the form, `is_active` left unticked on the stop-booking re-render, and no `/add/` or `/edit/` links for the key-less viewer. Output: `ALL RENDER CHECKS PASSED`.
- **`pytest --create-db` (dev container), full suite: blocked by in-progress backend work.** On the latest run, collection stopped at `apps/zoom/tests/test_review_fixes.py` (`No module named 'apps.zoom.admin'`, the backend's deletion). An earlier run hit `Unknown column host_key_changed_*` (the model has changed, but there's no `0003` migration yet).
- **`pytest apps/core`:** 77 passed, 1 failed.
  - The failure is `test_home_shows_admin_link_to_superuser`, with `NoReverseMatch: 'accounts'`. A superuser holds `view_hostaccount`, so the sidebar reverses `zoom:accounts`, which the backend hasn't routed yet. It clears once `apps/zoom/urls.py` has the three routes.
  - The guard subset (static references, icon sprite used and defined, colour literals, template rules) passed: 46 passed.
- **HTTP on 8010: not yet possible.** Every shell page for a superuser or IT user reverses `zoom:accounts`, so it waits on the backend's URLs. Step 3 exercises it.

## Verification
<!-- owner: tmd-test-verifier — verdict, criteria → tests table, checklist results, failures -->

**Verdict: PASS**

**Checklist ("Verify a change", CLAUDE.md):**

| Step | Result |
|---|---|
| `ruff check .` | ✅ All checks passed! |
| `ruff format --check .` | ✅ 72 files already formatted |
| `pytest --create-db` (dev container) | ✅ 393 passed (391 backend + 2 added by this verification) |
| `manage.py makemigrations --check --dry-run` | ✅ No changes detected |
| `manage.py check` | ✅ System check identified no issues (0 silenced) |
| `check --deploy` | n/a — no settings file touched in this brief (confirmed: `.env.example`'s comment is the only devops change) |
| Prod stack over HTTP on 8010 | ✅ see criterion 31 below |

**Tests added** (`apps/zoom/tests/test_accounts.py`), to close two gaps in the otherwise very thorough coverage — criterion 4's page chrome and table markup, and criterion 7's exact empty-state copy, neither of which was asserted against the real templates (the rest of the file uses `conftest.py`'s stub templates for speed):

- `test_list_page_chrome_and_table_markup_on_real_templates`: `<title>`, `<h1 class="page-heading">Zoom accounts</h1>`, the breadcrumb's current-page span, the table `<caption>`, and the six `<th scope="col">` headers in order.
- `test_empty_list_real_template_shows_pinned_copy_and_add_button`: `No Zoom accounts yet.`, the `Add a Zoom account` button, and `Accounts (0)`.

Both pass against the real templates and would fail if the pinned copy or markup regressed.

**Acceptance criteria → tests (spot-checked by reading the assertions and, for 1–2, 8, 10, 12, 17, 19, 20, 23–25, 31, by re-running the flow live against the dev/prod stacks):**

| # | Criterion | Test(s) / evidence | Result |
|---|---|---|---|
| 1 | IT desk role: exactly 4 permissions, reversible, idempotent | `test_it_desk_group_holds_exactly_the_review_and_host_account_permissions`, `test_it_desk_migration_is_idempotent_and_reversible`, `test_host_account_permission_migration_is_idempotent_and_reversible` | ✅ |
| 2 | Access matrix (anon/plain/viewer/IT) | `test_accounts.py` access-block tests (139–184); confirmed live: anon → `/accounts/login/?next=/zoom/accounts/`, plain user → 403, IT user → 200 with Add button | ✅ |
| 3 | Sidebar group/order/aria-current | `test_sidebar_zoom_group.py` (7 tests, real templates); confirmed live in screenshots (`Zoom accounts` current, bar+weight) | ✅ |
| 4 | List page/table structure | `test_list_page_chrome_and_table_markup_on_real_templates` (added); `test_list_puts_accounts_in_use_first_then_order_then_name` | ✅ |
| 5 | Upcoming figures | `test_upcoming_figures_count_booked_classes_that_have_not_ended` | ✅ |
| 6 | Query budget | `test_list_query_count_does_not_grow_with_accounts_or_classes` | ✅ |
| 7 | Empty state | `test_empty_list`, `test_empty_list_real_template_shows_pinned_copy_and_add_button` (added) | ✅ |
| 8 | No key material on the list | `test_no_accounts_page_shows_key_material`; confirmed live: no `gAAAAA`/plaintext in any response body | ✅ |
| 9 | Add form fields/labels/widgets | `test_add_form_fields_order_labels_and_widgets` | ✅ |
| 10 | Create | `test_adding_an_account_encrypts_the_key_and_records_who`, `test_adding_an_account_without_a_key`; confirmed live via raw-cursor read and HTTP add | ✅ |
| 11 | Validation messages | `test_invalid_add_saves_nothing_and_says_how_to_fix_it`, `test_uniqueness_ignores_letter_case_in_the_model_too` | ✅ |
| 12 | Typed key never echoed | `test_a_typed_key_is_never_sent_back`, `test_no_key_typed_means_no_note`; confirmed live in the add-with-errors screenshot | ✅ |
| 13 | Change form / state line | `test_change_form_context_and_host_key_copy`, `test_change_form_without_a_key_has_no_remove_box`, `test_host_key_state_covers_saved_legacy_none_and_unreadable` | ✅ |
| 14 | Saving (4 cases + message) | `test_saving_without_touching_the_key_keeps_it_byte_for_byte`, `test_saving_a_new_key_replaces_it_and_records_who`, `test_removing_the_key`, `test_a_new_key_and_remove_together_are_refused`; confirmed live: rename, replace, remove all gave the exact pinned flashes | ✅ |
| 15 | Unreadable saved key | `test_an_unreadable_key_still_opens_and_can_be_replaced` | ✅ |
| 16 | Model: `upcoming_classes`, `stop_booking_errors`, shared `BOOKABLE` | `test_bookable_is_defined_once_for_the_database_and_for_unsaved_flags`, `test_upcoming_classes_are_booked_not_ended_and_soonest_first` | ✅ |
| 17 | The block, exact copy | `test_stopping_bookings_is_refused_while_classes_are_booked`, `test_one_upcoming_class_is_worded_in_the_singular`, `test_the_message_uses_the_stored_name_not_the_typed_one`; confirmed live against Zoom 01 (2 upcoming classes): `Zoom 01 still has 2 booked classes, from Thu 15 Oct 2026 to Tue 20 Oct 2026. It can be taken out of use once the last one has finished.`, nothing saved, typed values kept | ✅ |
| 18 | What doesn't block | `test_an_account_already_out_of_use_can_still_be_edited`, `test_ended_waiting_and_rejected_classes_never_block`, `test_after_a_stop_the_account_is_not_offered_and_nothing_else_changes`; confirmed live: an unbooked test account was taken out of use in one POST and disappeared from a waiting request's availability | ✅ |
| 19 | Row locks, no race with approval | `test_the_stop_check_and_save_run_under_locks_taken_before_the_update` (asserts `FOR UPDATE` on `zoom_hostaccount` then `FOR UPDATE OF zoom_occurrence` then `UPDATE`, no `zoom_linkrequest` in the occurrence lock), `test_approval_refuses_an_account_taken_out_of_use` | ✅ |
| 20 | No delete | `test_no_zoom_url_deletes_anything`, `test_an_account_with_bookings_is_protected`; confirmed live: no delete link/button on any accounts page | ✅ |
| 21 | Recording who set a key | `test_set_host_key_records_when_and_who`, `test_new_fields_are_not_editable_and_forget_a_deleted_user`, `test_rotation_changes_neither_who_nor_when_a_key_was_set` (`test_services.py`) | ✅ |
| 22 | Email trim/lower-case, case-insensitive uniqueness | `test_clean_trims_and_lower_cases_the_email`, `test_uniqueness_ignores_letter_case_in_the_model_too` | ✅ |
| 23 | No Zoom admin | `test_the_zoom_models_are_not_in_the_django_admin`; confirmed live: `/admin/zoom/hostaccount/` → 404 for a staff superuser | ✅ |
| 24 | Secrets re-proved in the app | `test_error_report_of_the_account_forms_masks_a_typed_host_key` (both `zoom:account_add` and `zoom:account_edit`), `test_full_flow_never_logs_the_host_key_or_encryption_keys`, `test_no_accounts_page_shows_key_material`, `test_real_pages_render_for_the_unreadable_and_legacy_key_states`; confirmed live: no key material in any response body, and `docker compose logs web` had zero hits for the dummy keys used | ✅ |
| 25 | "In the admin" copy gone | `test_no_zoom_code_or_template_sends_people_to_the_admin`, `test_detail_page_knows_whether_the_user_may_add_an_account`; copy in `views.py`, `services.py`, `rotate_host_keys.py`, `detail.html` read directly and matches the pinned text | ✅ |
| 26 | Template rules | `apps/core/tests.py` guard tests (purpose comments, `only` on every include, no inline `style=`, no hard-coded paths, icon sprite fully used/defined) | ✅ |
| 27 | Works without JS | No new JS was added (`app.js`/`theme-init.js` unchanged); every view test above submits plain POSTs through the Django test client, which never executes JS, and passes | ✅ |
| 28 | Layout/accessibility | List and form templates read directly: `<caption>`, `th scope`, one `h1`, tags with icon+word; confirmed live at 1440/400 in light and dark (screenshots) — no horizontal scroll, cards-per-row below 768px, error summary first after the title row | ✅ |
| 29 | Thin views | `views.py` read directly: `HostAccountListView`/`CreateView`/`UpdateView` call only `get_queryset`/`get_object` on the manager methods named in the brief; no ad-hoc `.filter(...)` in the view layer | ✅ |
| 30 | Verify-a-change checklist | See table above | ✅ |
| 31 | Prod stack over HTTP | See below | ✅ |

**Criterion 31 detail (prod stack, `ZOOM_PROVIDER=manual docker compose up -d --build`, port 8010):**

1. IT user (`itverifier`, in `IT desk`) added a test account "Verifier Test 01" with dummy key `123456` → redirected to the list with `Added Verifier Test 01.`; no key material in the response.
2. Changed it (rename), replaced the key (`7654321`, flash: `Saved … The new host key goes out with the next approved link.`), then removed the key (flash: `Saved … Its host key was removed.`). The raw `host_key_encrypted` column read back empty after removal.
3. Tried to take "Zoom 01" (2 upcoming classes) out of use: refused with 200, the account unchanged in the DB, the exact pinned error, and every typed value kept (`is_paid` still checked, `is_active` correctly shown unticked as typed).
4. Took the unbooked test account out of use in one POST (succeeded); it then no longer appeared on a waiting request's "Which accounts are free" list.
5. `/admin/zoom/hostaccount/` → 404 for a staff superuser (a non-staff IT user instead gets redirected to `/admin/login/`, which is Django admin's own gate and outside this brief's scope).
6. Hashed static files (`/static/css/style.<hash>.css`, `/static/js/app.<hash>.js`) both returned 200.

Screenshots saved to the scratchpad (not committed): `list_1440_light.png`, `list_400_light.png`, `list_1440_dark.png`, `list_400_dark.png`, `add_errors_1440.png`, `change_saved_key_1440.png`, `stop_booking_error_400_viewport.png`. All match the design spec (D.1–D.3) closely, including tag tones/icons, the booked-classes notice, the host-key state notice, and the "wasn't kept" warning.

**Criterion 31's "no host key shown anywhere"**, explicitly re-checked: grepped `docker compose logs web` for the dummy keys used (`123456`, `7654321`) and for `gAAAAA` — zero matches. No page, redirect, or flash message in any of the flows above contained a key.

**Minor observation, not a defect:** a full-page (`captureBeyondViewport`) screenshot of the phone stop-booking error showed the sticky top bar rendered twice — a known headless-Chrome tiling artifact with `position: sticky` elements, not a product bug. A normal-viewport screenshot of the same page (`stop_booking_error_400_viewport.png`) is clean: the error summary is the first thing after the title row, as criterion 28 requires.

**Stack restored:** the dev overlay (`docker compose -f compose.yaml -f compose.dev.yaml up -d`) was running before this verification and has been restored; the shared `mysqldata` volume was never wiped (`down -v` was never used), and the dev database's pre-existing Zoom test data (4 accounts) is intact. The throwaway prod users (`verifier008`, `itverifier`, `plainverifier`) and the test account they created were deleted before restoring the stack.

## Re-verification (round 1 fixes)

**Verdict: PASS**

Scope: re-checking the backend's "Review round 1 fixes" (B1, the stop-booking locking read now covering `zoom_linkrequest`; nits 1–5) against the dev container, plus the specific requests in this round's brief: 5×`--create-db` and 2×`--reuse-db` runs of the new two-connection race test, a cleanup-survives-failure check on `test_race.py`, a spot-check that the test fails on the pre-fix code, and a re-run of the stop-booking pages on the prod image.

**Checklist ("Verify a change", CLAUDE.md):**

| Step | Result |
|---|---|
| `ruff check .` | ✅ All checks passed! |
| `ruff format --check .` | ✅ 72 files already formatted |
| `pytest --create-db` (dev container) | ✅ 398 passed |
| `manage.py makemigrations --check --dry-run` | ✅ No changes detected |
| `manage.py check` | ✅ System check identified no issues (0 silenced) |
| `check --deploy` | n/a — no settings file touched by the round-1 fixes |
| Prod stack over HTTP on 8010 | ✅ see below |

398 matches the backend's reported count (391 + the 2 nit-1 cases + 2 race parametrisations + 1 migration-reverse test = 398, 0 failed).

**Race test, run 5× with `--create-db` and 2× with `--reuse-db`:**

```
apps/zoom/tests/test_race.py::test_taking_an_account_out_of_use_sees_an_approval_that_committed_while_it_waited[READ COMMITTED]
apps/zoom/tests/test_race.py::test_taking_an_account_out_of_use_sees_an_approval_that_committed_while_it_waited[REPEATABLE READ]
```

All 5 `--create-db` runs and both `--reuse-db` runs passed both parametrisations (10 + 4 = 14 test results, 0 failures). Evidence: five consecutive `pytest --create-db -q` invocations of this test each printed `..` (2 passed), and two consecutive `pytest --reuse-db -q` invocations each printed `..` as well.

**Cleanup-survives-a-failing-test check.** Before touching anything, `race-it` users, `Race *`-labelled accounts and `Race *`-named requests were confirmed absent from the dev database. The `of=("self", "link_request"))` argument in `HostAccount.stop_booking_errors` (`apps/zoom/models.py`) was then temporarily reverted to `of=("self",))` — the pre-fix code — to force a real, reproducible test failure (see the next check for why this fails). With the code reverted:

- `pytest --create-db -rA apps/zoom/tests/test_race.py::test_taking_an_account_out_of_use_sees_an_approval_that_committed_while_it_waited` failed on `[REPEATABLE READ]` and passed on `[READ COMMITTED]`, as expected.
- A `manage.py shell` query for `username='race-it'`, `label__startswith='Race'` and `class_name__startswith='Race'` immediately afterwards returned **no rows** — the `committed` fixture's `finally` block (including its SF5 backstop sweep) ran and cleaned up despite the assertion failure.
- The same failing test was then run again with `pytest --reuse-db`, back to back, twice, to see whether a second failure on top of a "used" database behaves differently. Both repeats failed the same way (`REPEATABLE READ` only) and left the database clean afterwards (confirmed by the same query, again zero rows).

**Conclusion: the cleanup does survive a failing test**, at least for the ordinary case of an assertion failing inside the test process — every run above, pass or fail, left `race-it` / `Race *` rows at zero, including the case a `--reuse-db` run would be most sensitive to (residue from an immediately preceding failure). This is not a test-quality FAIL. The brief's own docstring for `test_race.py` already explains why the file avoids `transaction=True` (its flush would wipe the `IT desk` group that `--reuse-db` runs depend on) and instead commits and deletes its own rows plus a fixed-prefix backstop (review round 1, SF5); that design held up under direct testing. The backend's report of a leftover `race-it` user breaking an earlier `--reuse-db` run is consistent with a run made **before** the SF5 backstop existed (or with a run whose process was killed outright, which no in-process `finally` can protect against); it does not reproduce against the file as it stands now, so no code or test change follows from this check.

The `of=` argument was restored immediately after the failing runs above; `git diff apps/zoom/models.py` showed no diff afterwards, and the full suite (`pytest --create-db`, 398 passed) and both `--reuse-db` race-test parametrisations were re-run clean on the restored file.

**Spot-check: the race test fails on the pre-fix code.** Same revert as above (`of=("self",))`). Result:

```
FAILED apps/zoom/tests/test_race.py::...[REPEATABLE READ]
E   AssertionError: the stop check missed a class approved while it waited for the account lock
E   assert set() == {'is_active'}
PASSED apps/zoom/tests/test_race.py::...[READ COMMITTED]
```

This matches the backend's claim exactly: the bug only shows at `REPEATABLE READ` (MySQL's own default), and Django's `READ COMMITTED` session setting masks it on the code as it otherwise stands, which is the whole reason the brief asked for both isolation levels in one test.

**Prod stack over HTTP on 8010** (`ZOOM_PROVIDER=manual docker compose up -d --build`; `web` reported `healthy`):

1. A fresh throwaway superuser (`verifier008`) and an IT-desk user (`itverifier008`, added to the `IT desk` group) and a plain user (`plainverifier008`) were created for this round.
2. **Access matrix**, re-confirmed live: anonymous → 302 to `/accounts/login/?next=/zoom/accounts/…` for the list, add and edit pages; plain user → 403 on all three; IT user → 200 on all three.
3. **Added** a throwaway account "Verifier Test 008" with dummy key `123456` → 302 to the list with `Added Verifier Test 008.`; no key material in the response; the raw `host_key_encrypted` column (read via `connection.cursor()`) started with `gAAAAA` and contained neither `123456` nor the plaintext.
4. **Changed** it (renamed to "Verifier Test 008 Renamed", replaced the key with `7654321`): flash `Saved Verifier Test 008 Renamed. The new host key goes out with the next approved link.`; raw column re-encrypted, started with `gAAAAA`, did not contain `7654321`.
5. **Removed** the key: flash `Saved Verifier Test 008 Renamed. Its host key was removed.`; raw column read back as an empty string.
6. **Tried to take "Zoom 01" out of use** (2 real upcoming classes): POST returned 200 (not 302), the exact pinned copy — `Zoom 01 still has 2 booked classes, from Thu 15 Oct 2026 to Tue 20 Oct 2026. It can be taken out of use once the last one has finished.` — and a direct DB read afterwards showed `is_active` still `True` and every other field unchanged, confirming nothing was saved.
7. **Took the throwaway unbooked test account out of use** in one POST (302, saved) and confirmed on a real waiting request's detail page (`/zoom/requests/42/`) that the "Which accounts are free" list dropped from including it — the box read `3 of 3 paid accounts are free`, listing only Zoom 01/02/03.
8. `/admin/zoom/hostaccount/` → **404** for the superuser (a non-staff IT user instead gets redirected to `/admin/login/`, Django admin's own gate, outside this brief's scope — same finding as round 1).
9. Hashed static files (`/static/css/style.<hash>.css`, `/static/js/app.<hash>.js`) both returned 200.
10. The throwaway account and all three throwaway users were deleted from the prod database before restoring the dev stack.

**Stack restored:** the dev overlay (`docker compose -f compose.yaml -f compose.dev.yaml up -d`) was running before this round and has been restored; `mysqldata` was never wiped (`down -v` was never used); the dev database's pre-existing Zoom data is untouched. A final `pytest --reuse-db` on the restored dev stack ran clean (398 dots, no failures). `apps/zoom/models.py` carries no diff against the committed version.

## Review
<!-- owner: tmd-code-reviewer (written by the main session) — verdict, blockers, should-fix, nits -->

### Round 1 — 2026-09-25 (verifier PASS, 393 tests)

**Verdict: CHANGES REQUESTED.**

**Blocker**
- **B1: the stop-booking check can miss an approval that commits while the edit waits for the account lock.** The locking read is at `apps/zoom/models.py:412-416`. Owner: tmd-django-backend.
  - **Cause:** `select_for_update(of=("self",))` locks only `zoom_occurrence`, so MySQL reads the joined `zoom_linkrequest.status` from the transaction's snapshot. Under `ATOMIC_REQUESTS`, that snapshot is taken by the login and permission queries, before `get_object` asks for the account lock.
  - **How it happens:**
    1. `approve()` locks request R, then account A, books R's classes on A and marks R approved.
    2. The edit waits on A.
    3. `approve()` commits.
    4. The edit's read sees R's classes on A (those rows are read at their latest version), but still sees R as `waiting` (from the snapshot).
    5. The join drops those classes, so the check finds none. The account is taken out of use with a class booked on it, breaking criterion 19 and brief 005's D5.
  - **Why the deadlock concern doesn't apply:** while the edit holds A, it only reaches requests whose classes are already on A. R's classes are placed on A only after `approve()` holds A.
  - **Fix:**
    - Use `select_for_update(of=("self", "link_request"))`, or lock both tables.
    - Correct the docstring at `models.py:400-404`.
    - Invert the assertion at `tests/test_accounts.py:734`, which currently enshrines the bug.
    - Prove it with a two-connection test, or a manual two-session MySQL check by the verifier.

**Should fix:** none.

**Nits**
1. `models.py:409`: an account that is already out of use but still has upcoming classes is refused when Paid is unticked. It would be better to refuse only a change from bookable to not bookable.
2. `migrations/0004…:47`: the reverse uses `get_or_create`. Look the rows up with `filter` instead.
3. `views.py:424`: `AccountPermissionMixin` duplicates `ReviewerRequiredMixin` except for the permission. Share a base.
4. `tests/test_models.py:267`: the test name is out of date now that it allows three fields.
5. `models.py:238-248`: add a comment that case-insensitive uniqueness relies on the `utf8mb4_0900_ai_ci` collation, which is pinned in `compose.yaml:17` and `base.py:93`.

**Accepted as asked:**
- The rule refusing only removal of a currently-on tick.
- The lock order.
- The correlated subqueries.
- The three-name secret-field allowance.
- Case-insensitivity from the collation.
- `check_field.html`.
- The `h2, .empty h3` CSS change.
- The data migration's reverse.

**Host-key protections:** intact. That covers `sensitive_post_parameters` on both views, `sensitive_variables` on every method holding a key, the typed key dropped after an invalid submit, and no `value` on the input.

### Round 2 — 2026-09-25 (after the round-1 fixes; re-verification PASS, 398 tests)

**Verdict: APPROVE.** No blockers or should-fix items.

- **B1 was latent, not live.** Django's MySQL backend runs sessions at READ COMMITTED, so the missed class could only happen at REPEATABLE READ. That needs one settings change. The fix is kept:
  - `FOR UPDATE OF zoom_occurrence, zoom_linkrequest` (`models.py:430-436`).
  - The docstring's no-deadlock argument checks out, including a join driven from the status index.
- **The two-connection race test is sound** (`tests/test_race.py:160-241`):
  - It follows the exact interleaving.
  - `waited >= 0.25` proves the edit really waited for the lock.
  - It fails on the old code at REPEATABLE READ, as reproduced by the verifier.
  - Cleanup runs in `finally`, requests are deleted before accounts, and the isolation level is changed only on the edit's own connection.
  - Not using `transaction=True` is justified: its flush would wipe the `IT desk` group.
- **Nits 1–5 are fixed:**
  1. Only a change from bookable to not bookable is refused.
  2. The migration's reverse only looks rows up.
  3. There is one `SignedInPermissionMixin`.
  4. The test name is updated.
  5. The collation comment is added.
- **Nit (optional):** the `tests/test_race.py:1` module docstring could also mention brief 008's stop-check race.

## Docs
<!-- owner: tmd-docs-writer — files updated; closes Status -->

Verification was PASS (398 tests) and review round 2 was APPROVE, so this brief is closed.

**Files updated:**

- `README.md` — the "Zoom link requests" section: the Zoom accounts page and its sidebar location,
  that anyone in the `IT desk` group can add and change accounts (the three host-account permissions
  from migration 0004), that a host key is write-only and never shown again, that there's no delete,
  the Q2 stop-booking rule, that IT desk group membership and staff users are still managed in the
  admin until brief 010, and the leaked-key / key-rotation steps pointed at the Zoom accounts page.
  The go-live gate now lists both prerequisites (007 and 011).
- `CLAUDE.md` — Architecture → Current apps: the `zoom` bullet now says `apps/zoom/admin.py` is gone
  and host accounts are managed on in-app screens, records the one-sentence
  `stop_booking_errors`/`select_for_update(of=("self", "link_request"))` invariant, and notes that
  only staff users and the `IT desk` group remain in the admin until task 010.
- `docs/CHANGELOG.md` — new newest-first entry, 2026-09-25, "008: Zoom accounts page", with the
  user-visible changes, the migrations/permissions/race-test/nit-2 technical notes, and the three
  follow-ups (brief 011, resending the approval email, the optional `test_race` docstring nit).
- `docs/tasks/008-zoom-accounts.md` — this Docs section, and **Status** set to `Done`.

**Status: Done.**
