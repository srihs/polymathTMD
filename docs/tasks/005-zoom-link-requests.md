# 005 — Zoom link requests: public request form, email check, IT queue and conflict-free booking

<!-- One brief per task. Each section has exactly one owner agent; agents write only their own section.
     The workflow itself is defined in CLAUDE.md → "Agent workflow". -->

**Status:** Done <!-- Planned | Blocked: questions | In progress | Verifying | In review | Done -->

## Requirement
<!-- owner: tmd-planner — the user's words verbatim, then a one-paragraph interpretation -->

> The first section of the project is  requesting zoom links for the classes. These requests comes to the IT department and They store them in an excel sheet at the moment (see the attachement and check the worksheet ZOOM TIME TABLE).We need to automate this. When a request comes the relevent IT person will approve it and then the link should create automatically. We need to clearly identify the user (email and telephone) and makesure that there will not be conflicts of links. Can we automatically create zoom links if we have the credentials?

The owner's answers to the main session's questions (2026-09-24):

- **Who can ask:** "Anyone, via a public form". There's no sign-in.
- **Kinds of class:** "One-off and recurring classes".
- **Zoom accounts:** the IT spreadsheet has 12 host-account column groups in `ZOOM TIME TABLE`. Each group has class, time and recording status, with one row per date and about 360 bookings since Sep 2024. Many are recurring batches such as "CCC Batch 3 - Mathematics 8.30am-11.30am". In `Accounts`, 11 accounts are "ZOOM, Paid" and 2 are plain "ZOOM" (free, with a 40-minute limit). Today a "conflict" means one host account booked twice at overlapping times.
- **Zoom setup (Q1):** "Separate subscriptions". Each paid account is its own Zoom subscription, with its own Server-to-Server OAuth credentials.
- **Host start (Q2):** "Email the host key with the link".
- **Recording (Q3):** "Requester can ask for recording".
- **Import (Q4):** "Future bookings only".
- **Q5 and Q6:** the planner's defaults stand (no gap between bookings; the manual provider in production until 006).

**Reading.** This is the first real product section. Anyone can open a public form and ask for a Zoom link for a class. The class can happen once, or every week on chosen days until a last date. The requester can also ask for the class to be recorded. The requester gives their name, email and phone. They must confirm the email through a one-time link before the request reaches IT. After that, the request appears in an IT queue that only IT desk staff can open. For each paid host account, the IT person sees whether it is free for **every** class in the request, and which bookings clash if it isn't. They then approve or reject with a reason.

On approval, the system:

1. books a paid account that is free for every class, re-checking inside a locked transaction, with a database-level backstop so a double booking can't be stored;
2. creates the meeting through a meeting-provider interface;
3. saves the link;
4. emails the requester the link together with the booked account's **host key**, so the teacher can take host control.

A rejection emails the reason.

Host keys are stored **encrypted at rest**, with the key held in an env var, and only superusers (IT admins) can see or edit them, in the admin.

Yes, links can be created automatically with credentials. That uses a Zoom Server-to-Server OAuth app and `POST /users/{userId}/meetings`. The owner has confirmed that every paid account is its own subscription, so **brief 006** needs one credential set per account (D16). Until then, the provider is a **fake** in dev and tests. In production it is **manual**: IT creates the meeting in Zoom on the account the system assigned, and pastes the link. Everything except the real API call is built and tested now.

## Scope
<!-- owner: tmd-planner — In scope / Out of scope bullets -->

**How the requirement is split (in this order):**

| Brief | What | Depends on |
|---|---|---|
| **005 (this)** | New app `apps/zoom`. It covers the public form (including the recording request), the email check, abuse protection, the IT queue and detail, clash preview, conflict-free approval, rejection, the four emails (the approval email carries the host key), host accounts in the admin with **encrypted host keys**, the provider interface with **fake** and **manual** providers, and the settings, env and compose plumbing. | 004 (theme) |
| **006** | The live Zoom provider (outline in D16):<br>• **one Server-to-Server OAuth credential set per paid host account**, looked up by `HostAccount.credential_set`, from env only;<br>• a token for each set;<br>• create the meeting (type 2 for one class, type 8 weekly recurrence for a series), with `settings.auto_recording="cloud"` when the requester asked for recording (D18);<br>• map errors;<br>• delete the meeting when the DB commit fails;<br>• a check that every active paid account has a credential set. | Credentials issued for each account |
| **007** | Import from `Dashboard 2A.xlsx` **only the bookings on or after the go-live date** (owner, Q4: "Future bookings only"), as approved requests with slots. There's no history before go-live. | Adds `openpyxl` (new dependency, reason: read `.xlsx`). Go-live date fixed by the owner |

**Go-live gate:** 005 must not take real bookings in production until 007 has imported the future bookings already in the spreadsheet. Until then, the conflict engine can't see them, and it would double-book accounts. This is recorded in D14, and the docs writer puts it in the README.

**In scope (005)**

- A new app, `apps/zoom` (label `zoom`, namespace `zoom`), added to `LOCAL_APPS`. It has models, a custom QuerySet for each model, `services.py` (approve and reject orchestration), `providers.py` (the interface plus fake and manual), `forms.py`, `views.py`, `urls.py`, `admin.py`, `checks.py`, migrations (including the `IT desk` group), and tests.
- **Public pages**, with no sign-in, in a new **public frame**:
  - the request form;
  - "check your email";
  - confirm (GET shows the details, POST confirms);
  - "confirmed".
- **IT pages**, gated by the permission `zoom.review_linkrequest`, in the normal shell:
  - the queue, with status tabs and counts, search and paging;
  - the request detail, with clash preview, approve and reject.
- Emails, in plain text only: confirm your email (to the requester), new request (to IT), link approved (to the requester), not approved (to the requester).
- Abuse protection:
  - a honeypot field;
  - a per-email and per-IP hourly limit, counted in the database so it works across Gunicorn workers without a cache;
  - CSRF on every POST;
  - a signed, expiring confirmation token.
- Conflict engine:
  - occurrences are stored per class;
  - approval locks the chosen account row and the request row, and re-checks with a locking read;
  - `HostSlot` is a 5-minute slot table with a unique `(host_account, starts_at)`, which is the MySQL-level backstop;
  - a deadlock or integrity error becomes a friendly "try again" or "booked a moment ago" message.
- Host accounts are managed only in Django admin, and the `IT desk` group does not get host-account permissions.
  - **Host keys are the one secret stored in the database.** They're encrypted at rest with Fernet from `cryptography` (**new dependency**, D17), using keys from the env var `HOST_KEY_ENCRYPTION_KEYS`.
  - Only users with `zoom.change_hostaccount` see or edit a key, and only on the admin change form. Every other screen, list and log shows at most `Saved` / `Not saved`.
  - There's a `rotate_host_keys` management command for key rotation.
  - No Zoom API credential or password is stored in the database or repo.
- **Recording request:** a checkbox on the form, `wants_recording`. It's shown to IT in the queue and on the detail page, and mentioned in the confirm, IT and approval emails. In manual mode, the approve form reminds IT to turn cloud recording on. There's no tracking of whether a recording was made or sent (owner, Q3).
- Front end:
  - port from `design/f-desk/` what these screens need: `.tag` at 10.5px (D14 of brief 004), `.datagrid`, `.pager`, `.empty`, `.disc`, `.field__error`, the error-summary `.notice`, `.options` / `.choice--tall`, `.facts`, `.searchbox` / `.finder`;
  - the crumb separator, plus the icons the designer lists;
  - one sidebar group between `Menu` and `Administration`;
  - a small progressive enhancement that shows the weekly fields only when "Every week" is chosen.
- Settings and env (`tmd-devops`):
  - `ZOOM_PROVIDER`, `TRUSTED_PROXY_COUNT`, `HOST_KEY_ENCRYPTION_KEYS`;
  - `cryptography` added to `requirements/base.txt`, with the reason in a comment;
  - the email settings moved into `base.py`, so the backend and `DEFAULT_FROM_EMAIL` can be set in every environment;
  - pass `EMAIL_*` through `compose.yaml`, which doesn't happen today, so prod mail would never leave;
  - `.env.example`;
  - fixed constants for the limits.

**Out of scope (005)**

- Real Zoom API calls, OAuth and the per-account credential env vars (006, D16).
- Spreadsheet import (007, future bookings only).
- Tracking whether a recording was made or sent (owner, Q3).
- Turning recording on in Zoom automatically (006). In 005's manual mode, IT turns it on by hand.
- Requesters changing or cancelling a request. IT changing, cancelling or re-assigning an **approved** booking; for now, a superuser can delete the request in the admin, which frees its slots.
- Monthly or daily patterns, "every 2 weeks", different times on different days, and overnight classes. A different time means a separate request.
- Cleaning up requests whose email was never confirmed (a later housekeeping brief). The queue simply never shows them.
- **Top-bar search and the notifications bell stay honest placeholders** (D10). The help card stays out (D11).
- A CAPTCHA (it would add a dependency and third-party calls; D8).
- SMS or phone verification. The phone number is only checked for format.
- Any change to the sign-in page.

## Acceptance criteria
<!-- owner: tmd-planner — numbered, observable, testable -->

**Terms.**

- "Waiting" and the other status names are `LinkRequest.Status` values (see the MVT plan).
- "IT user" means an active user in the `IT desk` group with no other permissions.
- "Plain user" means a signed-in user without `zoom.review_linkrequest`.
- Times are Asia/Colombo unless stated.
- "The fake provider" is `ZOOM_PROVIDER=fake`, which the test settings force.
- Copy in quotes is pinned. The designer may propose changes through the main session, and changes are then made here first.
- Test dates are relative to a frozen "now" of **Mon 28 Sep 2026, 10:00**. The verifier freezes time with `time-machine` if it's a dev dependency, or else by patching `django.utils.timezone.now`. The verifier records which.

### Public frame (the review hand-off from brief 004)

1. `zoom:request`, `zoom:request_sent`, `zoom:confirm` and `zoom:confirmed` extend `public_base.html`, which overrides `{% block body %}`. The rendered pages contain:
   - no `data-nav` sidebar, `.topbar`, user menu, settings `<dialog>` or `data-settings-open`;
   - the crest brand line `Technology Management Desk` (not a link);
   - the colour-mode button (hidden without JS);
   - one `<main id="main">` with exactly one `<h1>`;
   - the messages partial;
   - the shared footer partial.

   This is the same whether the visitor is anonymous or signed in, so no partial gains `is_authenticated` branches (D1).
2. `topbar.html`, `sidebar.html` and `user_menu.html` contain no `is_authenticated` test. Pytest checks this over the sources.

### Request form: `GET`/`POST zoom:request`

3. An anonymous `GET` returns 200. The h1 is `Request a Zoom link`, and the `<title>` is `Request a Zoom link · {SITE_NAME}`. The form is `method="post"`, has a CSRF token, and posts to `{% url 'zoom:request' %}`. Every field in the context contract is present, each with a `<label for>` and an `id="<name>-help"` hint wired through `aria-describedby`:
   - `class_name`, `first_date` (`type="date"`), `start_time` / `end_time` (`type="time"`, `step="300"`);
   - `repeat` (radios `once` `Just once` / `weekly` `Every week`);
   - `weekdays` (7 checkboxes `Monday`…`Sunday`, values `1`…`7`), `last_date`;
   - `wants_recording` (a checkbox labelled `Record this class to the Zoom cloud`, unticked by default; criterion 59);
   - `requester_name`, `requester_email` (`type="email"`), `requester_phone` (`type="tel"`), `notes`.

   The honeypot `website` field sits inside a wrapper hidden from everyone (`hidden` + `aria-hidden="true"`), with `tabindex="-1"` and `autocomplete="off"`.
4. **One-off.** A valid POST with `first_date=2026-10-05`, `08:30`–`11:30` and `repeat=once` does the following:
   - it creates one `LinkRequest` with `status=unverified`;
   - `requester_email` is stored lower-cased and trimmed;
   - `requester_phone` is normalised (criterion 8);
   - `submitted_ip` is set (criterion 11);
   - it creates exactly one `Occurrence`, `2026-10-05 03:00Z`–`06:00Z` (08:30–11:30 Colombo);
   - it sends exactly one email to the requester, with the subject `Confirm your Zoom link request` and a body containing the absolute `zoom:confirm` URL;
   - it redirects (302) to `zoom:request_sent`, whose page shows the email address the link went to.

   No `HostSlot` rows are created and no email goes to IT.
5. **Weekly.** `first_date=2026-10-05` (Mon), `weekdays=1,3` (Mon, Wed), `last_date=2026-10-28`, 08:30–11:30. This creates exactly 8 occurrences: 5, 7, 12, 14, 19, 21, 26 and 28 Oct, each 08:30–11:30. The stored `weekdays` is `"1,3"`. If `first_date`'s weekday isn't ticked, the first class is the next ticked day. With `first_date=2026-10-06` (Tue) and the same days, 7 Oct is the first occurrence.

   **`schedule_summary`** (D22, G5) is a plain-text model property, unit-tested:
   - weekly: `Every Monday and Wednesday, 8:30 am to 11:30 am, from Mon 5 Oct to Wed 28 Oct 2026 (8 classes)`;
   - once: `Once, on Mon 5 Oct 2026, 8:30 am to 11:30 am`.

   `zoom/partials/schedule.html` prints it, and the confirm, IT and approval emails print it as `When: {schedule_summary}`, so the sentence has one source.
6. **Validation.** Each invalid POST returns 200, creates nothing and sends nothing. It re-renders with every other typed value kept, and shows these exact field errors:

   | Input | Field | Error |
   |---|---|---|
   | empty class name | `class_name` | `Type the name of the class, like CCC Batch 3 - Mathematics.` |
   | `end_time` ≤ `start_time` | `end_time` | `The class must end after it starts. Check the end time.` |
   | a time not on a 5-minute step (`08:32`) | that field | `Use a time on a 5-minute step, like 8:30 or 8:35.` |
   | `first_date` before today, or today with a start time already past | `first_date` | `Choose a date and time that haven't passed yet.` |
   | `first_date` more than 365 days ahead | `first_date` | `Choose a date within the next year.` |
   | `repeat=weekly` with no day ticked | `weekdays` | `Tick at least one day of the week.` |
   | `repeat=weekly` with `last_date` empty or before `first_date` | `last_date` | `Choose the date of the last class, on or after the first class.` |
   | `repeat=weekly`, and no ticked day falls between the dates | `weekdays` | `None of the days you ticked fall between the first and last class dates.` |
   | more than 60 classes (Mon–Fri, 5 Oct 2026 → 31 Mar 2027) | `last_date` | `That makes {n} classes. One request can cover up to 60. Choose an earlier last date, or send a second request for the rest.` |
   | empty name | `requester_name` | `Type your full name.` |
   | bad email | `requester_email` | `Type an email address you can open now, like nimali@example.com. We'll send a link to it.` |
   | bad phone | `requester_phone` | `Type a phone number we can call, like 077 123 4567 or +94 77 123 4567.` |
   | `class_name` longer than 200 characters, or `notes` longer than 1000 | that field | Django's max-length message is acceptable |

   With `repeat=once`, any `weekdays` / `last_date` that was sent is ignored and not stored.
7. **Error presentation.**
   - Each invalid field gets `aria-invalid="true"`, and `aria-describedby="<name>-error <name>-help"`, with the error `<p id="<name>-error">` carrying the icon and the text.
   - Above the form, an error summary `.notice` has `role="alert"` and `tabindex="-1"`, and one link per error to `#<field id>`.
   - Its title is the lead `We couldn't send this yet.` followed by `1 thing needs your attention.` when there is one error, or `{n} things need your attention.` for two or more. The literal `thing(s)` never appears (D21; amended from `{n} thing(s) need your attention.`).
   - The same partial serves the approve and reject forms on the detail page, with their own leads (criteria 36, 43, D21).
   - Non-field errors (criterion 10) appear in the summary with no link.
8. **Phone normalisation** is a model-layer function, unit-tested with exactly this table. Stored values are E.164.

   | Typed | Stored |
   |---|---|
   | `077 123 4567`, `0771234567`, `077-123-4567`, `(077) 123 4567` | `+94771234567` |
   | `+94 77 123 4567`, `94771234567`, `0094771234567` | `+94771234567` |
   | `011 234 5678` | `+94112345678` |
   | `+44 20 7946 0958` | `+442079460958` |
   | `12345`, `077 123 456a`, `+94 77`, `0771234567890123`, empty | invalid (criterion 6 error) |

   **Rule:**
   1. Strip spaces, `-`, `(`, `)` and `.`.
   2. Rewrite the prefix: a leading `00` becomes `+`; a leading `0` followed by 9 digits becomes `+94` plus the 9 digits; a bare `94` followed by 9 digits becomes `+94…`.
   3. The result must be `+` followed by 8–15 digits.

   No operator or area-code list is checked (not over-constrained).

   **Display form** (D22, G1): the property `LinkRequest.requester_phone_display` formats the stored value, and is unit-tested:

   | Stored | Displayed |
   |---|---|
   | `+94771234567` | `+94 77 123 4567` |
   | `+94112345678` | `+94 11 234 5678` |
   | `+442079460958` (any non-`+94` number) | `+442079460958` (unchanged) |
9. **Honeypot.** A POST that is otherwise valid but has `website` filled in redirects (302) to `zoom:request_sent`. It creates no `LinkRequest` or `Occurrence` and sends no email.
10. **Throttle** (limits are settings constants: `ZOOM_REQUEST_LIMIT_PER_EMAIL_PER_HOUR = 5`, `ZOOM_REQUEST_LIMIT_PER_IP_PER_HOUR = 20`).
    - When 5 requests from the same email (case-insensitive) were created in the last 60 minutes, whatever their status, the 6th valid POST returns **429**. It re-renders the form with the values kept and the non-field error `You've sent a lot of requests in the last hour. Wait an hour, then try again, or phone the IT desk.` It creates nothing and sends nothing.
    - The same applies to the 21st POST from one IP within 60 minutes, even with different emails.
    - A request created 61 minutes earlier doesn't count.
    - The throttle check runs only on otherwise valid POSTs.
    - Honeypot hits create no rows, so they don't count.
11. **Client IP.**
    - With `TRUSTED_PROXY_COUNT=0` (the default), `submitted_ip` is `REMOTE_ADDR`, and `X-Forwarded-For` is ignored even when present.
    - With `TRUSTED_PROXY_COUNT=1`, it is the right-most `X-Forwarded-For` entry. With `2`, it is the second from the right.
    - If the header has fewer entries than the setting, `REMOTE_ADDR` is used.
    - The parsing lives in one function, which is unit-tested.
12. **No user-controlled HTML.**
    - A class name of `<b>Maths & Science</b>` is stored as typed.
    - Every HTML page renders it escaped (`&lt;b&gt;Maths &amp; Science&lt;/b&gt;`).
    - Every email body contains it literally (`<b>Maths & Science</b>`, not `&amp;`), because emails are plain text only. No email has an HTML alternative.
    - No template in `templates/zoom/` uses `|safe`, `mark_safe` or `{% autoescape off %}`, **except** the `.txt` email templates.

### Email confirmation: `zoom:request_sent`, `zoom:confirm`, `zoom:confirmed`

13. The token in the confirm URL is made by `django.core.signing` with a salt specific to this purpose. It carries only the request's pk and has a maximum age of `ZOOM_CONFIRM_LINK_HOURS = 24`.
    - **Ready state:** a `GET` with a valid token for an `unverified` request returns 200 with `state="ready"`. It shows the class name, the schedule summary, every class date with its times, and the requester's name, email and phone. It has a POST form with CSRF and the button `Confirm my request`. **A GET never changes the status.**
14. A `POST` to a ready token does the following:
    - it sets `status=waiting` and `verified_at`;
    - it redirects to `zoom:confirmed`, which shows the reference (`ZL-0001` style, criterion 34) and says IT will email `{requester_email}`;
    - it sends one email to **every active user with `zoom.review_linkrequest`** (`User.objects.with_perm`), including superusers, with the subject `New Zoom link request {reference}: {class_name}` and a body containing the absolute `zoom:detail` URL;
    - it sends no email to users without the permission, and none to the requester.
15. **Already confirmed:** a `GET` or `POST` for a request that isn't `unverified` renders `state="already"` (`You've already confirmed this request.`). It changes nothing and sends no second IT email.
    - **Expired:** a token older than 24 hours renders `state="expired"` with `This link has expired. Please send your request again.` and a link to `zoom:request`. The status is unchanged.
    - **Invalid:** a tampered or unknown token renders `state="invalid"` with `This link doesn't work. Check you copied all of it from the email, or send your request again.`
    - All three return 200 and send nothing.
16. `unverified` requests never appear in the queue: not in any tab, count, search result or the detail view (the detail view returns 404 for them).

### Who can use the IT pages

17. The access rule for `zoom:queue`, `zoom:detail`, `zoom:approve` and `zoom:reject`:
    - an anonymous visitor is redirected to `accounts:login?next=…`;
    - a plain user, including a plain `is_staff` user, gets **403**;
    - an IT user and a superuser get 200 on the GET views.

    `approve` and `reject` accept POST only; GET returns 405.
18. After `migrate`, a `Group` named `IT desk` exists with exactly one permission, `zoom.review_linkrequest` ("Can approve or reject Zoom link requests"). The migration is reversible and doesn't duplicate the group when re-run.
19. **Sidebar.** For users with the permission, a group `Zoom links` (`id="nav-zoom"`) sits **between** `Menu` and `Administration` and holds one item, `Link requests` → `zoom:queue`. On `zoom:queue` and `zoom:detail`, that item carries `aria-current="page"` and `Home` does not. A plain user sees no `Zoom links` group. Brief 004's sidebar tests keep passing: every nav `href` is a `reverse()`d name, and Administration is still last.

### The queue: `zoom:queue`

20. The h1 is `Zoom link requests`, and the breadcrumb is `Home › Zoom link requests`.
    - **Tabs:** `Waiting` / `Link sent` / `Not approved` / `All`. Each is a link carrying `?status=waiting|approved|rejected|all` and its count, the current one has `aria-current="page"`, and the counts leave out `unverified`.
    - **Default tab and ordering:** the default is `waiting`, and an unknown `status` also falls back to `waiting`. `Waiting` is ordered by first class, soonest first. The other tabs are ordered by `decided_at`, newest first, and `All` by `created_at`, newest first.
21. The table has a `<caption>` and these columns, in order: `Reference` (links to `zoom:detail`), `Class`, `Requested by` (name, then email, then phone), `First class` (date and time), `Classes` (the count), `Status` (a tag with icon and word, criterion 33).
    - When `wants_recording` is true, the `Class` cell also shows the marker `Recording asked for` (icon and word). Otherwise there's no marker.
    - The queue never shows a host key or its `Saved` / `Not saved` state.
22. **Search.** `?q=` searches within the current tab.
    - It matches the reference (`ZL-0007`, `zl-7` and `7` all find pk 7), the class name, the requester's name and email (case-insensitive substring), and phone digits (`0771234567` finds `+94771234567`).
    - When nothing matches, it shows `No requests match "{q}".` with a `Clear the search` link to the same tab without `q`. When a tab is empty without a search, it shows `Nothing here yet.`
23. It pages at 25 per page with the f-desk pager, and `?page=` keeps `status` and `q`.
24. The page shows the absolute URL of `zoom:request` with the line `Share this link with staff who need a Zoom link:`.
25. **Query budget.** The number of SQL queries for the queue page is the same with 3 waiting requests as with 25. The test uses `django_assert_num_queries` or equivalent.

### Request detail and clash preview: `zoom:detail`

26. The h1 is `{reference}: {class_name}`, and the breadcrumb is `Home › Zoom link requests › {reference}`. The page shows:
    - the status tag;
    - the class name, the schedule summary and the notes;
    - every class as date plus start–end;
    - the requester's name, email (`mailto:`) and phone (`tel:` with the E.164 value, displayed as `requester_phone_display`, e.g. `+94 77 123 4567`; D22, G1). The confirm page and the queue show the same display form.
    - the sent time and the confirmed time;
    - a `Recording` fact: `Yes, record it to the Zoom cloud` or `No`;
    - for decided requests: who decided and when, the account, the join link, meeting ID and passcode (approved), or the reason (rejected).

    **The host key never appears on the detail page**, not even for superusers (criterion 62).
27. **Earlier requests from the same person:** up to 5 other non-`unverified` requests with the same `requester_email`, each linked, with its status tag. If there are none, the list is left out.
28. **Availability** (waiting requests only). For every host account where `is_active` and `is_paid` are true, ordered by `(sort_order, label)`:
    - its label and email;
    - `Free for all {n} classes` (success tag), or `Busy for {k} of {n} classes` (warning tag) followed by one row per clash: the date, this request's time, and the clashing booking's reference linked to its detail, plus its class name and time.
    - `k` is `busy_count`: the number of **this request's classes** that clash with at least one booking, not the number of clash pairs. A class that clashes with two bookings counts once in `k`, but gets two clash rows. This is tested with exactly that case (D22, G4).

    Unpaid or inactive accounts are never listed or offered. A clash is any approved `Occurrence` on that account where `a.start < b.end` and `b.start < a.end`. Classes that touch end-to-start are not a clash (D6).
29. **Also waiting at overlapping times:** other `waiting` requests with any occurrence overlapping this one, whatever the account. Each item shows the reference, the class, and `First overlap {date}, {time}`, where `first_overlap` is the earliest start among **that** request's occurrences that overlap this one (D22, G2; tested with a request whose first class doesn't overlap but whose second does). The list is ordered by `first_overlap`, and left out when there are none.
30. **The approve form:**
    - A radio group `Book it on`, listing **only** the free accounts, with the first free one (by `sort_order`, `label`) pre-selected.
    - With `ZOOM_PROVIDER=manual`, it also has three fields:
      - `join_url` `Zoom link` (required; `https://` and a host of `zoom.us` or ending in `.zoom.us`);
      - `meeting_id` `Meeting ID` (required; 9–11 digits once spaces are removed);
      - `passcode` `Passcode` (optional; at most 10 characters).

      A note says to create the meeting in Zoom on the chosen account first. When `wants_recording` is true, the note adds `Turn on cloud recording for this meeting. The requester asked for it.`
    - Next to each account, a word shows whether a host key is saved (`Host key saved` / `No host key saved`). The key itself is never shown. For an account with no host key, criterion 61's note applies.
    - With `fake`, those three fields are absent.
    - The button reads `Approve and email the link`.
31. **When nothing is free**, or the first class has already started, there's no approve form. The page shows a warning `.notice`, with one of two texts:
    - `No paid Zoom account is free for every class in this request. Reject it with a reason, or ask the requester to change the times.`
    - `The first class has already started. Reject this request and ask for a new one.`

    The reject form is always present on waiting requests (criterion 39).
32. For a decided request, neither form is shown. The line reads `This request was {approved|not approved} by {decider} on {date}.`
33. **Status tags** everywhere use the f-desk `.tag` with an icon and a word: `Waiting for IT`, `Link sent`, `Not approved`, and `Waiting for email check` (admin or any debug view only). They're used for availability too: `Free for all …` and `Busy for …`. At the default 16px root, their computed `font-size` is **10.5px (±0.5)** (brief 004, D14). The token is `--fs-tag: 0.65625rem`. Text contrast is ≥4.5:1 in both modes.
34. `LinkRequest.reference` is `ZL-` plus the pk zero-padded to 4 digits (`ZL-0042`, `ZL-12345`). It's a model property, and the only place the format is defined.

### Approve: `POST zoom:approve`

35. **Happy path (fake provider).** Approving a waiting request with 8 occurrences on a free account does all of the following in one transaction:
    - `status=approved`, `host_account`, `decided_by`, `decided_at`;
    - every occurrence gets `host_account`, and `HostSlot` rows cover every 5-minute slot of every occurrence on that account (8 × 36 = 288 rows for 08:30–11:30);
    - `meeting_id`, `join_url` and `passcode` come from the provider. The fake's `join_url` starts `https://zoom.example.invalid/j/`.

    Then it emails the requester once, **to `requester_email` only, with no cc or bcc**. The subject is `Your Zoom link for {class_name}`. The body contains:
    - the join link, meeting ID and passcode;
    - the booked account's **host key** in plain text, with the line `To start the class as host, join, choose "Claim host" and type this host key. Keep it private: anyone who has it can take control of meetings on this Zoom account.`;
    - every class date with its times, and the reference;
    - when `wants_recording` is true, the line `You asked for this class to be recorded to the Zoom cloud.`

    This applies to both the fake and the manual providers. It redirects (302) to `zoom:detail` with the success message `Approved. The link was emailed to {requester_email}.`
36. **Manual provider.** The same outcome, with the typed link, ID and passcode stored as typed (ID stored as digits only). Invalid manual fields re-render the detail with field errors, keeping what was typed, and an error summary at the top of the approve box titled `We couldn't approve this yet. {1 thing needs / n things need} your attention.` (D21). Nothing is booked.
37. **Stale page.** If an overlapping approved booking was saved on the chosen account after the page loaded (the test creates it before the POST):
    - nothing is changed, no provider call is made and no email is sent;
    - the detail re-renders with status **409**, the error `{label} was booked for an overlapping class a moment ago. Choose another free account.`, and refreshed availability.

    The same response applies to a chosen account that is unpaid, inactive, unknown or busy. The error for unpaid, inactive or unknown accounts is the form error `Choose one of the free accounts listed.`
38. **Race safety (the database backstop).**
    - **(a)** Inserting two `HostSlot` rows with the same `host_account` and `starts_at` raises `IntegrityError`. This is a model test.
    - **(b)** Two threads, each with its own DB connection (`transaction=True` test), approve two different waiting requests with overlapping times on the same account at the same moment. Exactly one ends `approved` on that account. The other stays `waiting`, with no slots and no occurrence host, and its caller gets the conflict result. If MySQL reports a deadlock (1213), the service turns it into the same friendly conflict and retry outcome, never a 500.
    - **(c)** Two threads approving **the same** request result in one approval, one provider call and one email.

    The verifier records the thread test's output. If it's flaky, the verifier reports FAIL rather than skipping it.
39. **Already decided or started.**
    - Approving or rejecting a request that isn't `waiting` changes nothing and redirects to the detail with the error message `This request has already been decided.`
    - Approving a waiting request whose first occurrence has started changes nothing and re-renders with criterion 31's second text.
40. **Provider failure.** With the fake provider set to raise `ProviderError("Zoom is not responding")`:
    - nothing is booked and the status stays `waiting`;
    - no email is sent;
    - the detail re-renders with the error `Zoom didn't create the meeting: Zoom is not responding. Nothing was booked. Try again in a few minutes.`
41. **Email failure after approval.** When the email backend raises:
    - the approval is kept;
    - the redirect carries the warning message `Approved, but the email to {requester_email} didn't send. Copy the link below and send it to them yourself. An administrator can give them the host key from the admin.`;
    - one log record at `ERROR` names the request's reference and the exception class, and **contains neither the join URL, the passcode, the host key nor any token**. This is checked with `caplog`.

### Reject: `POST zoom:reject`

42. **Reject box copy (D20).** On a waiting request, the reject form sits in a box headed `Reject this request` (`<h2>`), with the button `Reject and email the reason`. The status label stays `Not approved` everywhere, including tags, tabs, emails and flash messages; only the action words say "reject".

    A waiting request with the reason `Please use the Grade 10 batch link instead.` becomes `rejected`, with `rejection_reason`, `decided_by` and `decided_at` set. The requester gets one email, with the subject `Your Zoom link request {reference} was not approved`, containing the reason and a link to `zoom:request`. The view redirects to the detail with the message `Not approved. We emailed the reason to {requester_email}.`
43. An empty or whitespace-only reason re-renders the detail (200) with the field error `Tell the requester why, so they can fix it and ask again.`, and an error summary at the top of the reject box. Its title is `We couldn't send the reason yet. 1 thing needs your attention.` (D21). The status is unchanged, and any values in the approve form are kept.

### Model rules and data safety

44. The rules live on the model layer:
    - schedule validation (criterion 6) is in `LinkRequest.clean()`, and the form reaches it through `ModelForm`;
    - occurrence building is a model method;
    - availability, clashes and search are QuerySet methods;
    - status changes happen only through model methods or `services.py`.

    Views contain no ORM filters beyond `get_object` / `get_queryset` calling those methods. The reviewer checks this.
45. **Database `CHECK` constraints** (MySQL 8.4 enforces them). Each is proven by a test that saves an invalid row with `.save()` or `bulk_create`, bypassing `clean()`, and expects `IntegrityError`:
    - `Occurrence.ends_at > starts_at`;
    - `LinkRequest.end_time > start_time`;
    - `repeat='weekly'` needs a non-empty `weekdays` and a non-null `last_date`;
    - `status='approved'` needs a non-null `host_account` and a non-empty `join_url`;
    - `status='rejected'` needs a non-empty `rejection_reason`.
46. **No other secrets in the database.**
    - No field on any `zoom` model has a name matching `password|secret|host_key|hostkey|token|start_url` (pytest over `_meta.get_fields()`), with **exactly one allowed exception**: `HostAccount.host_key_encrypted` (criterion 60).
    - The provider result never includes, and the models never store, Zoom's `start_url`.
    - No Zoom API credential is stored anywhere in the database.
47. **Host accounts are admin-only.**
    - `HostAccount` is registered in the admin with `label`, `email`, `is_paid`, `is_active`, `sort_order`, `credential_set` and `notes`, plus the form-only `host_key` field (criterion 62).
    - An `is_staff` IT user who has no `zoom.*_hostaccount` permission gets 403 on its admin changelist and doesn't see it in the admin index.
    - Deleting an account that has bookings is refused (`PROTECT`); deactivating it is the way out.
    - `LinkRequest` in the admin is view-and-delete only, with no add or change. Deleting a request removes its occurrences and slots.

### Settings, providers, env

48. **Provider setting.**
    - `settings.ZOOM_PROVIDER` is read only in `config/settings/base.py`, from the env var `ZOOM_PROVIDER`, with the default `manual`. `test.py` sets `fake`.
    - Any value other than `fake` or `manual` fails `manage.py check` with the error `zoom.E002`.
    - `manage.py check --deploy` with `ZOOM_PROVIDER=fake` reports the error `zoom.E001` `The fake Zoom provider makes links that don't work. Set ZOOM_PROVIDER=manual in production.` With `manual`, it reports nothing new (only W021 stays accepted).
49. **Env plumbing (`tmd-devops`).**
    - New or moved env vars: `ZOOM_PROVIDER`, `TRUSTED_PROXY_COUNT`, `HOST_KEY_ENCRYPTION_KEYS` (criterion 63), `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL`.
    - Each is read in `base.py` only. `prod.py` no longer calls `env(`. `dev.py` keeps the console backend and `test.py` keeps locmem, as constants.
    - Each one appears in `.env.example`, with a comment, and in `compose.yaml`'s `web.environment`.
    - `EMAIL_HOST_PASSWORD` and `HOST_KEY_ENCRYPTION_KEYS` are never logged or rendered.
    - `test.py` sets a fixed, clearly fake Fernet key through `os.environ.setdefault`, the same way it sets `SECRET_KEY`, so tests need no `.env` value.
50. **Emails.**
    - Every email is sent with `DEFAULT_FROM_EMAIL`.
    - Subjects are single-line (newlines stripped).
    - Bodies are rendered from `templates/zoom/email/*.txt`, and no email carries `html_message`.
    - Every absolute URL is built with `request.build_absolute_uri(reverse(...))`, with no hard-coded host.

### Front end, templates, accessibility

51. Every new template starts with a `{# … #}` header comment, including the `.txt` email templates, whose subject files keep the comment on the same line as the subject. Every include ends with `only`. There are no inline `style=` attributes and no hard-coded paths. Every `<use href="#i-…">` names a symbol in `partials/icons.html`, and every symbol is used. Brief 004's guard tests pass unchanged.
52. **JavaScript off.**
    - The request form shows the weekly fields (days, last date) all the time, under the legend `If it's every week`.
    - Submitting works in every path.
    - The queue tabs, search and pager work, and approve and reject submit.
53. **JavaScript on.** With `Just once` checked, the weekly fields are hidden (`hidden`) and their inputs are `disabled`. With `Every week` checked, they're shown and enabled. The behaviour binds only to `data-*` hooks. There are no console errors.
54. **Layout and accessibility** on the request form, confirm (ready), queue and detail:
    - no horizontal scroll at 320, 400, 1024 and 1440 wide, in both modes;
    - every link, button, radio and checkbox label is ≥44×44px (breadcrumb links exempt);
    - AA contrast;
    - one `h1`;
    - the table has `<caption>` and `<th scope>`;
    - the weekday checkboxes and the repeat radios are each in a `<fieldset>` with a `<legend>`;
    - focus moves to the error summary after a failed submit (JS). Without JS, the summary is the first thing in `<main>` after the h1.
55. **Tests updated deliberately:** `test_sidebar_shows_administration_group_only_for_staff` and `test_sidebar_links_resolve_to_named_urls_only` are extended to cover the `Zoom links` group, and still assert Administration is last. `test_home_page_has_no_form_other_than_sign_out` stays unchanged, because the search is still a placeholder (D10).

### Verification (CLAUDE.md "Verify a change", all five)

56. `ruff check .`, `ruff format --check .`, `pytest --create-db`, `makemigrations --check --dry-run` and `manage.py check` all pass. `check --deploy` is also run on the prod stack with `USE_HTTPS=True` and `ZOOM_PROVIDER=manual`. Settings change here, so criterion 48 applies.
57. **Prod stack**, `docker compose up -d --build`, with `web` healthy and `.env` temporarily set to `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` and `ZOOM_PROVIDER=manual`. The verifier restores `.env` and the stack that was running before. Over HTTP on 8010:
    1. Anonymous GET on the form returns 200. A POST lands on "check your email". The confirm URL is taken from `docker compose logs web`, and GET then POST on it lands on "confirmed".
    2. An IT user signs in and sees the request in `Waiting`. The detail shows availability. The host accounts used here are **test accounts with a dummy host key** (`123456`). The console backend writes emails to the container log, so no real host key may be entered on the verification stack.
    3. Approving with a pasted `https://us02web.zoom.us/j/12345678901` lands on the detail as `Link sent`.
    4. A second request is rejected with a reason.
    5. Every new page's static files come from hashed WhiteNoise paths (200).
58. **Screenshots**, saved in the verifier's scratchpad and not committed:
    - the request form, empty and with errors, at 1440 and 400;
    - confirm (ready) at 400;
    - queue `Waiting` at 1440 and 400, in light and dark;
    - detail with a clash, detail with nothing free, and detail after approval, at 1440;
    - the request form at 320;
    - the admin `HostAccount` changelist, showing the `Saved` / `Not saved` column.

### Recording request (owner, Q3)

59. `wants_recording` is a `BooleanField(default=False)`.
    - Ticking it on the form stores `True`; leaving it unticked stores `False`.
    - The confirm page (ready state) shows `Recording: Yes, record it to the Zoom cloud` or `Recording: No`.
    - The IT new-request email includes `Recording: yes` / `Recording: no`.
    - The queue (criterion 21), the detail (criterion 26), the manual approve note (criterion 30) and the approval email (criterion 35) show it as stated there.
    - The provider receives it through `link_request`. The fake records it in its call log, and a test asserts that it was passed.

### Host keys (owner, Q2): encrypted at rest, admin-only, emailed only with the approval

60. **Not stored in plaintext.** `HostAccount.set_host_key("8421973")` followed by `save()` stores a Fernet token in `host_key_encrypted`. The test reads the **raw column** with `connection.cursor()` and `SELECT host_key_encrypted …`, and checks that:
    - the value starts with `gAAAAA`;
    - it does not contain `8421973`.

    `get_host_key()` returns `"8421973"`, and `has_host_key` is `True`. The same key typed twice gives two different ciphertexts, because Fernet uses a random IV. An empty value clears the column (`has_host_key` is `False`). `set_host_key` only accepts 6–10 digits and raises `ValidationError` otherwise, with the message `A Zoom host key is 6 to 10 digits.`
61. **Only in the approval email.**
    - After an approval, the plaintext host key appears in exactly one outgoing email: the approval email to `requester_email` (criterion 35).
    - It does **not** appear in the confirm, IT new-request or rejection emails. It also doesn't appear in the rendered queue, detail (before or after approval), confirm or confirmed pages, or any flash message.
    - The test renders each page and email, then searches the output for the key.
    - If the booked account has no host key saved, the approval still goes through, and the email says `Ask the IT desk for the host key to start the class as host.` in its place. The detail page, before approval, shows `No host key saved` beside that account (criterion 30).
62. **Admin only, for IT admins only.**
    - The `HostAccount` change form has one form-only field, `Host key` (a `ModelForm` field, not a model field). It's filled in with the decrypted key, **only for users with `zoom.change_hostaccount`** (superusers by default). Saving it calls `set_host_key`, and clearing it removes the key.
    - A user with only `view_hostaccount` sees the form without that field, and its value is not in the HTML.
    - The **changelist** shows a `Host key` column with only `Saved` / `Not saved`. The test renders the changelist as a superuser and asserts the plaintext is absent.
    - The admin's `LogEntry.change_message` for an edit names the field, but never contains the key. Django records changed field names only, and the test confirms it.
63. **Keys come from env; rotation is supported.**
    - `settings.HOST_KEY_ENCRYPTION_KEYS` is read only in `base.py`, from the comma-separated env var `HOST_KEY_ENCRYPTION_KEYS`. Each entry is a Fernet key.
    - Encryption uses a `MultiFernet` built from the list: the first key encrypts, and every key can decrypt.
    - `manage.py check` reports the error `zoom.E003` `HOST_KEY_ENCRYPTION_KEYS is missing or not a list of valid Fernet keys.` when the variable is empty or any entry is invalid.
    - `manage.py rotate_host_keys` re-encrypts every stored key with the first key (`MultiFernet.rotate`), then prints only a count (`Re-encrypted 11 host keys.`).
    - A test puts a new key first, runs the command, then removes the old key. `get_host_key()` still returns the original value.
64. **Unreadable key at approval.** If the chosen account's stored key can't be decrypted with the configured keys (the test changes the key list):
    - nothing is booked and the status stays `waiting`;
    - no provider call is made and no email is sent;
    - the detail re-renders with the error `The host key saved for {label} can't be read. Ask an administrator to type it again in the admin, then approve.`;
    - the log record names the account label and `InvalidToken`, and contains nothing else.
65. **Never logged.** For the full flow (submit, confirm, approve, reject, admin edit of a host key, `rotate_host_keys`), with logging captured at `DEBUG` for the `apps.zoom` and `django` loggers, no captured record contains the plaintext host key or any value from `HOST_KEY_ENCRYPTION_KEYS`. `HostAccount.__str__` and `__repr__` never include the key.
66. **Dependency recorded.** `requirements/base.txt` pins `cryptography` with the comment `# Fernet: encrypts Zoom host keys at rest (brief 005, D17)`. The prod image builds and runs without adding build tools to the runtime stage, because `cryptography` ships manylinux wheels. The verifier confirms it with `docker compose build` and a healthy `web`.

### No reply-time promise (owner, G7)

67. **No reply-time promise (D23).**
    - This bans **promises about when IT will reply**, and nothing else.
    - The rendered `zoom:request`, `zoom:request_sent`, `zoom:confirm` (ready) and `zoom:confirmed` pages and the confirm email must match none of these, case-insensitively:
      - `working day`, `business day`;
      - `within a day`, `within one`, `within \d+ (hour|day)s?`;
      - `by tomorrow`, `by the end of`;
      - `as soon as`, `same day`.

      The check runs on the error-free GET render.
    - **Stating how long the confirmation link works is allowed and required:**
      - the "Check your email" page's `The link works for one day.`;
      - the confirm email's `The link works for {{ link_hours }} hours`, which renders `24 hours`.

      Both describe the link, not IT's reply, and the test asserts that both are present.
    - `zoom:request_sent` and `zoom:confirmed` each say that IT will email the requester once they've looked at the request.

## Design decisions needed
<!-- owner: tmd-planner — open questions for the user; "None" if none -->

**None open for 005.** The owner answered Q1–Q4 (2026-09-24, verbatim option labels below), and the defaults for Q5 and Q6 stand. They are recorded as D16–D19 and in D6 and D4. For later briefs, two things remain to be supplied, but neither is a design question:
- **006:** the credentials for each account, issued by whoever administers each Zoom subscription.
- **007:** the owner fixes the go-live date.

**Owner's answers**

| Q | Question (short) | Owner's answer | Recorded as |
|---|---|---|---|
| Q1 | One Zoom subscription or several? | "Separate subscriptions" | D16 |
| Q2 | How does the teacher start as host? | "Email the host key with the link" | D17 (supersedes the host-key part of D13) |
| Q3 | Recording? | "Requester can ask for recording" | D18 |
| Q4 | What to import? | "Future bookings only" | D19 (amends D14) |
| Q5 | A gap between bookings? | Default stands: **no gap** | D6 |
| Q6 | The manual provider in production until 006? | Default stands: **yes** | D4 |

**Decisions (the planner's, recorded so later briefs don't reopen them)**

- **D1: Public pages use their own frame, `templates/public_base.html`, which extends `base.html` and overrides `{% block body %}`.** This settles brief 004's review hand-off.
  - **Rejected alternative:** adding `is_authenticated` branches to `topbar.html` and `sidebar.html`. It would spread one rule ("who is looking") over several partials. The shell's nav, user menu and layout settings mean nothing to a public requester. A signed-in teacher filling in the public form would also land in a shell with no way back to the page they came from.
  - **What stays in `base.html`:** the document (`<html>`, head, skip link, sprite), as today.
  - **Where page chrome now lives:** in exactly two places, the shell (`base.html`'s default `body`) and the public frame (`public_base.html`). The sign-in page keeps its own split layout (brief 004, D18).
  - **Blocks:** `public_base.html` exposes the same `heading` and `content` blocks as the shell, so page templates look alike.
  - **Follow-up:** `tmd-docs-writer` updates CLAUDE.md's DRY bullet "Page chrome is only defined in `templates/base.html`" to name both frames.
- **D2: "The relevant IT person" is anyone who holds the custom permission `zoom.review_linkrequest`.** A data migration creates the group `IT desk` with it. A superuser adds IT staff to the group in the admin.
  - There's **no per-request assignment**. Any IT desk member can decide, and `decided_by` records who did.
  - IT users don't need `is_staff`.
  - The permission gates the queue, the detail, approve and reject. The sidebar group is shown through `perms`, passed into the sidebar include.
- **D3: New app `apps/zoom`.** It is a new domain with its own models, URLs and emails, and nothing existing owns it. It imports only `apps.accounts`' user model (through `get_user_model` / `settings.AUTH_USER_MODEL`) and Django. It doesn't import `apps.core` views.
- **D4: The meeting-provider interface** (`apps/zoom/providers.py`):
  - `get_provider()` returns the provider named by `settings.ZOOM_PROVIDER`.
  - A provider has `needs_manual_details: bool` and `create_meeting(*, link_request, host_account, occurrences, manual=None) -> Meeting`, where `Meeting` is a frozen dataclass with `meeting_id`, `join_url` and `passcode`.
  - A failure raises `ProviderError(user_message)`.
  - **`FakeProvider`** is deterministic. Its `join_url` is on the reserved `.invalid` TLD, so a fake link can never reach a real meeting. Tests can make it raise.
  - **`ManualProvider`** returns what IT typed.
  - **006** adds `ZoomProvider`, which looks up `host_account.credential_set` in the env-held credential sets, one per account (D16).
  - **Owner, Q6:** the manual provider is the production provider until 006.
  - The deploy check `zoom.E001` stops `fake` from reaching production.
- **D5: Conflicts are impossible by construction**, in three layers:
  1. **The preview:** clashes are shown on the detail page (criterion 28).
  2. **The approval transaction:**
     - lock the `LinkRequest` row and then the chosen `HostAccount` row (`select_for_update`, always in that order, to limit deadlocks);
     - re-check the status;
     - re-check clashes with a **locking read** (`select_for_update()` on the overlapping `Occurrence` query). Under MySQL's REPEATABLE READ, a plain read can come from a stale snapshot, because `ATOMIC_REQUESTS` began the transaction before the lock;
     - then write the occurrences' host and the slots;
     - then call the provider;
     - any exception rolls everything back.
  3. **The backstop:** `HostSlot` has a unique `(host_account, starts_at)` on 5-minute slots. Any code path, including the admin or the shell, that tries to store two bookings covering the same 5 minutes on one account fails at the database. MySQL has no exclusion constraints, and triggers can't lock safely, so the slot table is the feasible DB-level guarantee. Its size is small: 3 hours is 36 rows per class, and at most 60 classes per request.

  Times must therefore sit on 5-minute steps (criterion 6). An `IntegrityError` or deadlock (1213) inside the service becomes the conflict result (criterion 38).
- **D6: What counts as a clash:** `a.start < b.end and b.start < a.end` on the same account, among approved requests only. Back-to-back is allowed (Q5: the owner accepted the no-gap default; there is no `ZOOM_HOST_GAP_MINUTES`). Waiting requests don't block each other, but IT sees them (criterion 29).
- **D7: Recurrence is one time slot on chosen weekdays, from a first date to a last date, capped at 60 classes.**
  - This covers the spreadsheet's batches ("… 8.30am-11.30am" on set days).
  - It maps directly to a Zoom type-8 meeting with a weekly recurrence (`weekly_days`, `end_date_time`) in 006, and a one-off maps to type 2.
  - The cap of 60 matches Zoom's documented maximum for `end_times`, and keeps one request reviewable. 006 re-checks it against the current API docs.
  - Weekdays are stored in ISO numbering (`1`=Mon … `7`=Sun). 006 converts them to Zoom's numbering (`1`=Sun).
  - All datetimes are stored in UTC and entered and shown in Asia/Colombo, using `zoneinfo`. Sri Lanka has no DST, but nothing relies on that.
- **D8: Abuse protection without new dependencies.**
  - **Honeypot.**
  - **Limits by count in the database** (`LinkRequest.objects.recent_from(email=…, ip=…)`), because no shared cache is configured and Gunicorn runs 3 workers.
  - **Signed, expiring confirmation tokens** (`django.core.signing`, no token column).
  - **GET shows and POST confirms,** so mail scanners that prefetch links don't confirm anything.
  - **CSRF.**

  There's no CAPTCHA: it would need a dependency, third-party calls and a consent notice. We'll revisit if abuse shows up. `TRUSTED_PROXY_COUNT` exists because behind the TLS proxy every request would otherwise share the proxy's IP, and the per-IP limit would block everyone.
- **D9: Emails are plain text, sent synchronously right after the model change**, through Django's email backend.
  - A send failure never undoes a decision (criterion 41). IT can always copy the link from the detail page.
  - IT learns about new requests by email to every holder of the permission (`UserManager.with_perm`, from Django), so there's no env list of addresses.
  - There's no queue worker. That's less code, and the volume is about one request a day.
- **D10: The top-bar search and the bell stay placeholders in 005** (this amends brief 004, D12, which expected 005 to wire them "or else record why not"). Why not:
  - The top bar is shown to every signed-in staff member, but only IT desk can see Zoom requests. A site-wide search needs a design for mixed permissions and for more than one section.
  - The queue has its own search (criterion 22).
  - A bell needs a notifications model of its own. IT is notified by email (D9).

  Both are picked up in a later "search and notifications" brief. The purple search button (brief 004, D15) stays out until then.
- **D11: The sidebar help card stays out** (brief 004, D13). Its copy ("Something not working? … Raise a request") is about fault reports, which don't exist. Zoom requesters are mostly not signed in, and they reach the form through the shared link (criterion 24).
- **D12: The reference is derived, not stored:** `ZL-{pk:04d}`, as a model property (criterion 34). There's no extra column and no sequence to keep in step.
- **D13: No Zoom API credentials, passwords or `start_url` are ever stored or logged** (criteria 41, 46, 49). *Amended by D17: host keys are now stored, encrypted.*
  - `HostAccount` holds the account's email (Zoom accepts it as `userId`), a label, the paid/active flags, the order, the `credential_set` slug and, per D17, the encrypted host key.
  - The planner didn't copy any value from `Dashboard 2A.xlsx`. IT enters the 13 accounts and their host keys by hand in the admin, and marks the two free ones `is_paid=False`.
- **D14: Spreadsheet bookings are imported in 007, not here.** Reasons:
  - it needs a new dependency (`openpyxl`);
  - the sheet's free-text times need parsing rules, and the rows the importer can't read go to an owner-checked report in 007;
  - it's a data migration with its own risk register.

  **Scope, per D19:** future bookings only. The import **gates go-live**: production must not take real bookings until the bookings on or after the go-live date are imported, or the conflict engine can't see them.
- **D15: Out of this brief because they widen it past one reviewable change:** changing or cancelling approved bookings (the admin delete is the stop-gap), requester self-service, and purging unconfirmed requests.
- **D16: One Zoom credential set per paid host account** (owner, Q1: "Separate subscriptions"). This outline is for 006; nothing in 005 reads credentials.
  - **Env naming scheme:**
    - `ZOOM_CREDENTIAL_SETS` is a comma-separated list of slugs, for example `zoom-01,zoom-02,…`. Each slug equals a `HostAccount.credential_set`.
    - For each slug, there's one variable `ZOOM_S2S_<SLUG>`: the slug upper-cased, with `-` turned into `_`. For example, `ZOOM_S2S_ZOOM_01=<account_id>:<client_id>:<client_secret>`.
    - Colon-separated values keep it to one variable per account. 006 confirms that Zoom's IDs and secrets never contain `:`, and otherwise switches to three variables per slug with the suffixes `_ACCOUNT_ID`, `_CLIENT_ID` and `_CLIENT_SECRET`.
    - `base.py` reads them into `settings.ZOOM_CREDENTIALS` (`{slug: (account_id, client_id, client_secret)}`). That is the only place they're read, and they're never logged.
  - **Delivery to the container:** eleven or more variables would bloat `compose.yaml`, so 006's `tmd-devops` adds a git-ignored `zoom-credentials.env`, loaded through `env_file:` with `required: false` on `web`, plus a `zoom-credentials.env.example` listing the names only. This is a deliberate, documented exception to "list every var in `web.environment`". 006 records it in CLAUDE.md's env gotchas.
  - **005's part:** `credential_set` stays a blank-allowed `SlugField`. **It becomes required before 006 switches on:** 006 adds the check `zoom.E004`, "every active paid account has a `credential_set` with a matching env set", and a data review of the 11 accounts.
  - **Operational cost the owner is taking on:**
    - one Server-to-Server OAuth app per paid account (11 apps), each created and later rotated by whoever administers that subscription;
    - 11 secrets to keep in step with the server's env;
    - one access token for each account, cached for up to an hour;
    - Zoom's rate limits apply to each account.

    Adding an account means creating a new app plus an env entry and a restart.
- **D17: Host keys are stored encrypted, and emailed with the link** (owner, Q2: "Email the host key with the link"). This supersedes the host-key part of D13.
  - **Risk accepted by the owner:** anyone who has the approval email, whether it's forwarded, the mailbox is shared or the account is compromised, can take host control of **every** meeting on that Zoom account, not just this class. The key stays valid until IT changes it in Zoom.
  - **Mitigations in 005:**
    - the email goes only to the **verified** requester, with no cc or bcc (criterion 35);
    - the key appears nowhere else: pages, lists, other emails and logs are all tested (criteria 61, 65);
    - it's encrypted at rest (criterion 60);
    - only IT admins (`zoom.change_hostaccount`, superusers by default) can see or edit it, in the admin change form only (criterion 62).

    Changing a leaked key in Zoom and re-typing it in the admin is the recovery path. The README documents it.
  - **Encryption approach:** `cryptography`'s **Fernet** (AES-128-CBC with HMAC-SHA256, a random IV and a timestamp) through `MultiFernet`. The key list comes from the env var `HOST_KEY_ENCRYPTION_KEYS`; the first key encrypts and all keys decrypt.
    - **Why a new dependency (CLAUDE.md "Less code"):** Django ships signing but no encryption at rest. `cryptography` is the maintained standard library for this. It has manylinux wheels, so the Docker build stays as it is, and it's small.
    - **Rejected:** `django-fernet-fields` and `django-cryptography`, because they're unmaintained or lag Django 5.2, and a custom field type encrypts implicitly on save, which is hidden magic. Hand-rolled crypto was also rejected.
  - **Shape (no hidden magic):**
    - a plain `TextField` `host_key_encrypted` holds the token;
    - there are explicit `set_host_key()` / `get_host_key()` / `has_host_key` on the model;
    - `apps/zoom/crypto.py` holds `encrypt`, `decrypt` and `rotate`, the only place Fernet is used.

    The admin form's `host_key` field is form-only.
  - **Key rotation:**
    1. Generate a key with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
    2. Put it **first** in `HOST_KEY_ENCRYPTION_KEYS` and restart.
    3. Run `manage.py rotate_host_keys`.
    4. Remove the old key and restart.

    Fernet keys are URL-safe base64 with no `$`, so they're safe in `.env`. **Losing every key means re-typing all host keys**, and the README says so. The encryption key is not `SECRET_KEY`, so rotating `SECRET_KEY` (sessions, signing) never makes stored host keys unreadable.
  - **Host key in the email for fake and manual modes too:** the key belongs to the account, not to the meeting, so it's known whichever provider made the link.
- **D18: The requester can ask for recording** (owner, Q3: "Requester can ask for recording").
  - `LinkRequest.wants_recording` is a boolean, shown to IT and mentioned in the emails (criterion 59).
  - In 005's manual mode, IT turns on cloud recording by hand, and the approve note says so. In 006, the live provider creates the meeting with `settings.auto_recording = "cloud"` when it's true.
  - Only paid accounts are ever booked, so cloud recording is available on every booked account.
  - There's no "recording made or sent" tracking, per the owner's answer. The spreadsheet's recording-status column isn't carried over.
- **D19: The import brings future bookings only** (owner, Q4: "Future bookings only").
  - 007 imports rows dated on or after the go-live date the owner sets. It imports each as an `approved` `LinkRequest` with occurrences and slots on the matching host account, so the conflict engine sees them.
  - It does not import rows before go-live, and it builds no reports.
  - The importer's unreadable rows (free-text times) go to a report file that IT checks before go-live.
  - The go-live gate (D14) stays.

**Rulings on the Design section's copy and contract points (2026-09-25)**

- **D20: Reject wording.** The box is headed `Reject this request`, and the button reads `Reject and email the reason` (criterion 42). The status stays `Not approved`.
  - **Why:** the IT person is doing an action, so the action is named with the verb the pinned no-free-account notice already uses ("Reject it with a reason"). The requester and the tags see the gentler outcome word.
- **D21: The error summary counts in words and takes a lead** (the designer's G3, accepted). It prints `1 thing needs your attention.` or `{n} things need your attention.`; the literal `thing(s)` is gone.
  - `zoom/partials/error_summary.html` takes `with form=… lead="…" only`. The leads are:
    - `We couldn't send this yet.` (request form);
    - `We couldn't approve this yet.` (approve box);
    - `We couldn't send the reason yet.` (reject box).
  - Criteria 7, 36 and 43 are amended.
- **D22: Contract additions** (the designer's G1, G2, G4, G5; the backend is implementing them now):
  - `LinkRequest.requester_phone_display` is a model property, because formatting a number is a rule (criterion 8).
  - `first_overlap` is annotated on each `overlapping_waiting` item (criterion 29).
  - `busy_count` is added to each `availability` entry. `clashes` stays one entry per clash pair, so every clashing booking is still listed (criterion 28).
  - `LinkRequest.schedule_summary` is a plain-text model property, the one source for the schedule sentence in pages and emails (criterion 5).
  - G6 needs no change.
- **D23: No reply-time promise** (owner, on G7: "No time promise"). The request form, "check your email", confirm and "confirmed" pages, and the confirm email, never promise when IT will reply. They only say that IT will email the requester once they've looked at the request.
  - The designer's clause "usually within one working day" is dropped, so the form's lead ends at "Zoom link.".
  - This is pinned by criterion 67.

## MVT plan
<!-- owner: tmd-planner -->

### Models

All models are in `apps/zoom/models.py`. Every model, QuerySet and non-trivial method gets a docstring saying **why**.

**`HostAccount`**: a Zoom user that can host meetings. It is managed only in the admin.

| Field | Type | Notes |
|---|---|---|
| `label` | `CharField(60, unique)` | IT's short name, e.g. the spreadsheet column heading |
| `email` | `EmailField(unique)` | Zoom login; used as `userId` in 006 |
| `is_paid` | `BooleanField(default=True)` | Free accounts cut meetings at 40 minutes, so they're never booked |
| `is_active` | `BooleanField(default=True)` | Retire an account instead of deleting it |
| `sort_order` | `PositiveSmallIntegerField(default=0)` | Order of preference when suggesting |
| `credential_set` | `SlugField(40, blank=True)` | Names this account's env-held credential set (006, D16). Blank-allowed now, required before 006 switches on |
| `host_key_encrypted` | `TextField(blank=True, editable=False)` | Fernet token (D17). Never read directly outside the model's methods and `crypto.py` |
| `notes` | `TextField(blank=True)` | |

- `Meta.ordering = ["sort_order", "label"]`. `__str__` is `"{label} ({email})"`, and it never includes the key.
- **Host-key methods** (D17, criteria 60–65):
  - `set_host_key(plain)` validates 6–10 digits, encrypts, and clears the key when given an empty value;
  - `get_host_key() -> str` returns `""` if none is saved, and raises `HostKeyUnreadable` (wrapping `InvalidToken`) if the stored value can't be decrypted;
  - `has_host_key` is a property.
- **`apps/zoom/crypto.py`:** `encrypt(str) -> str`, `decrypt(str) -> str` and `rotate(str) -> str`. It builds the `MultiFernet` from `settings.HOST_KEY_ENCRYPTION_KEYS`, and it's the only module that imports `cryptography`.
- **`apps/zoom/management/commands/rotate_host_keys.py`:** criterion 63. It prints only a count.
- **`HostAccountQuerySet.bookable()`**: `is_active=True, is_paid=True`.
- **`HostAccountQuerySet.availability_for(occurrences)`**: returns, for each bookable account, `(account, clashes)`, where each clash is `(occurrence, clashing_occurrence)`. Its query count is fixed: one query for the approved occurrences of bookable accounts inside `[min start, max end]`, then the overlap is matched in Python. The same function backs the preview and the in-transaction re-check (the re-check passes `lock=True`).

**`LinkRequest`**: one request from one person for one class schedule.

| Field | Type | Notes |
|---|---|---|
| `class_name` | `CharField(200)` | Zoom topic max is 200 |
| `notes` | `TextField(blank=True, max_length=1000)` | "Anything IT should know" |
| `wants_recording` | `BooleanField(default=False)` | The requester asked for cloud recording (D18) |
| `first_date` | `DateField` | |
| `start_time`, `end_time` | `TimeField` | Same day, 5-minute steps |
| `repeat` | `CharField(10, choices=Repeat)` | `once` "Just once", `weekly` "Every week" |
| `weekdays` | `CharField(13, blank=True)` | ISO days, comma-separated and sorted, e.g. `"1,3"`; blank for `once` |
| `last_date` | `DateField(null=True, blank=True)` | Required for `weekly` |
| `requester_name` | `CharField(150)` | |
| `requester_email` | `EmailField` | Stored lower-cased and trimmed, indexed |
| `requester_phone` | `CharField(16)` | E.164 (criterion 8) |
| `submitted_ip` | `GenericIPAddressField(null=True)` | Throttle only, indexed together with `created_at` |
| `status` | `CharField(12, choices=Status, db_index)` | See the state table |
| `created_at` | `DateTimeField(auto_now_add, db_index)` | |
| `verified_at` | `DateTimeField(null)` | |
| `decided_by` | `FK(AUTH_USER_MODEL, PROTECT, null, related_name="+")` | |
| `decided_at` | `DateTimeField(null)` | |
| `rejection_reason` | `TextField(blank=True)` | |
| `host_account` | `FK(HostAccount, PROTECT, null)` | Set on approval |
| `meeting_id` | `CharField(32, blank)` | Zoom IDs are 64-bit, so this is text |
| `join_url` | `URLField(1000, blank)` | |
| `passcode` | `CharField(10, blank)` | Zoom max 10. Given to the requester, so it isn't an account credential |

- **`Status`** (`TextChoices`, value → label):
  - `unverified` → `Waiting for email check`;
  - `waiting` → `Waiting for IT`;
  - `approved` → `Link sent`;
  - `rejected` → `Not approved`.
- **`Meta`:**
  - `permissions = [("review_linkrequest", "Can approve or reject Zoom link requests")]`;
  - `CheckConstraint`s per criterion 45;
  - `Index(fields=["requester_email", "created_at"])` and `Index(fields=["submitted_ip", "created_at"])`.
- **`clean()`** holds every rule in criterion 6. It uses `timezone.localtime()` for "now", normalises `weekdays`, and clears the weekly fields for `once`. The 60-class cap is `MAX_OCCURRENCES = 60`, a class constant.
- **Methods and properties:**
  - `occurrence_times() -> list[tuple[datetime, datetime]]`: pure and aware, used by `clean()` and on save.
  - `reference`;
  - `weekday_names -> list[str]`;
  - `schedule_summary -> str`: plain text, the one source for the schedule sentence (D22, criterion 5);
  - `requester_phone_display -> str` (D22, criterion 8);
  - `has_started(now=None)`;
  - `mark_verified()`: `unverified` → `waiting`; raises otherwise;
  - `reject(by, reason)`: `waiting` → `rejected`; raises otherwise.

  Approval is not a model method. It spans several models and the provider, so it lives in `services.approve()`, and the model exposes `can_be_decided()` for it.
- **`LinkRequestQuerySet`:**
  - `visible_to_it()`: excludes `unverified`;
  - `waiting()`;
  - `with_schedule()`: annotates `first_start=Min("occurrences__starts_at")` and `occurrence_count=Count("occurrences")`, and `select_related("host_account", "decided_by")`;
  - `search(q)` (criterion 22; `ZL-`/digits → pk);
  - `recent_from(*, email=None, ip=None, minutes=60)`;
  - `for_tab(status)` (criterion 20 ordering);
  - `tab_counts() -> dict[str, int]`: one aggregate query;
  - `overlapping_waiting(link_request)`;
  - `earlier_from_same_requester(link_request, limit=5)`.
- **Phone:** `normalise_phone(value) -> str` raises `ValidationError` with criterion 6's text. It lives in `apps/zoom/validators.py`, is used by the form's `clean_requester_phone`, and is unit-tested by criterion 8. It moves to `apps/core` when a second app needs it.

**`Occurrence`**: one class meeting.

- **Fields:** `link_request` (`FK CASCADE`, related_name `occurrences`), `starts_at`, `ends_at`, `host_account` (`FK PROTECT, null`).
- **Meta:** ordering `starts_at`; `CheckConstraint(ends_at > starts_at)`; `Index(host_account, starts_at)`.
- **QuerySet:** `booked()` (request `approved`); `overlapping(start, end)`.

**`HostSlot`**: the database backstop (D5).

- **Fields:** `host_account` (`FK PROTECT`), `starts_at` (aligned to `SLOT_MINUTES = 5`), `occurrence` (`FK CASCADE`).
- **Constraint:** `UniqueConstraint(fields=["host_account", "starts_at"], name="zoom_one_booking_per_account_slot")`.
- **Written only** by `services.approve()` via `bulk_create`.

**State table** (`interaction-design:state-machine`, applied by the planner):

| From | Event | Guard | To | Side effects |
|---|---|---|---|---|
| (none) | public POST valid | not honeypot, under limits | `unverified` | occurrences created; confirm email |
| `unverified` | confirm POST | token valid ≤ 24h | `waiting` | `verified_at`; IT email |
| `unverified` | token > 24h | | (unchanged) | none; the request is never shown |
| `waiting` | approve | IT perm; first class not started; chosen account bookable and free (locked re-check); provider OK | `approved` | host on occurrences, slots, meeting fields, `decided_*`; requester email |
| `waiting` | approve fails | clash, deadlock, unreadable host key or provider error | `waiting` | none (rolled back) |
| `waiting` | reject | IT perm; reason non-blank | `rejected` | `decided_*`, reason; requester email |
| `approved` / `rejected` | anything | | (terminal in 005) | none |

**Services** (`apps/zoom/services.py`):

- **`approve(link_request_id, *, account_id, by, manual=None) -> ApproveResult`.** Inside `transaction.atomic()`, it does D5's steps. After locking the account, and before writing anything, it decrypts the host key (`get_host_key()`), so an unreadable key fails early (criterion 64).
  - It returns one of `approved`, `conflict`, `already_decided`, `started`, `host_key_unreadable` or `provider_error`, plus the user-facing message.
  - On `approved`, the result also carries `host_key` (str, possibly `""`), in memory only, for the email.
  - It sends no email.
- **`send_approved_email(request, link_request, host_key)`** and the other senders. They're called by the view after the service returns, and they catch and log send failures without the host key, link, passcode or token (criteria 41, 65). The approval email is addressed to `[link_request.requester_email]` only.
- **`client_ip(request) -> str | None`** (criterion 11), reading `settings.TRUSTED_PROXY_COUNT`.

**Checks** (`apps/zoom/checks.py`, registered in `ZoomConfig.ready()`; this is the checks framework, not a signal): `zoom.E002` for an unknown provider (always), `zoom.E003` for missing or invalid `HOST_KEY_ENCRYPTION_KEYS` (always), and `zoom.E001` for `fake` (tagged `deploy`). 006 adds `zoom.E004` (D16).

**Migrations:** `0001_initial` (the models and constraints), and `0002_it_desk_group` (a data migration that calls `create_permissions` for the app first, then `get_or_create`s the group, with a reverse that removes it).

### URLs and views

`config/urls.py` gains `path("zoom/", include("apps.zoom.urls"))`. `app_name = "zoom"`. Views are generic CBVs. IT views use `PermissionRequiredMixin` with `permission_required = "zoom.review_linkrequest"` and `raise_exception` for signed-in users. Anonymous users are redirected to login: use `LoginRequiredMixin` first, or equivalent.

| Name | Path | View | Template | Permission |
|---|---|---|---|---|
| `zoom:request` | `zoom/request/` | `LinkRequestCreateView(CreateView)`, form `LinkRequestForm` (a `ModelForm`, plus the honeypot and throttle, and `form_valid` creating the occurrences and sending the confirm email). It stores the email in the session key `zoom_sent_to`. A throttled request gets a 429 re-render | `zoom/request_form.html` | Public |
| `zoom:request_sent` | `zoom/request/sent/` | `RequestSentView(TemplateView)` | `zoom/request_sent.html` | Public |
| `zoom:confirm` | `zoom/confirm/<str:token>/` | `ConfirmView(TemplateView)`: GET renders the state, POST confirms and redirects | `zoom/confirm.html` | Public (the token) |
| `zoom:confirmed` | `zoom/confirmed/<str:token>/` | `ConfirmedView(TemplateView)`. It reuses the token (valid, any age ≤ 7 days) so it can name the reference without a session. A bad token gives 404 | `zoom/confirmed.html` | Public (the token) |
| `zoom:queue` | `zoom/requests/` | `QueueView(ListView)`, `paginate_by = 25`, `get_queryset` = `visible_to_it().with_schedule().for_tab(status).search(q)` | `zoom/queue.html` | `zoom.review_linkrequest` |
| `zoom:detail` | `zoom/requests/<int:pk>/` | `LinkRequestDetailView(DetailView)` on `visible_to_it()`, with `ReviewContextMixin` building the review context | `zoom/detail.html` | `zoom.review_linkrequest` |
| `zoom:approve` | `zoom/requests/<int:pk>/approve/` | `ApproveView(ReviewContextMixin, SingleObjectMixin, FormView)`, POST only. On `approved` it sends the email, adds a message and redirects. Otherwise it re-renders `detail.html` with 409 or 200 | `zoom/detail.html` (on error) | `zoom.review_linkrequest` |
| `zoom:reject` | `zoom/requests/<int:pk>/reject/` | `RejectView(ReviewContextMixin, SingleObjectMixin, FormView)`, POST only | `zoom/detail.html` (on error) | `zoom.review_linkrequest` |
| (admin) | `admin/zoom/…` | `HostAccountAdmin`, with the form `HostAccountAdminForm` (form-only `host_key`, added in `get_form` only when the user has `zoom.change_hostaccount`) and the changelist column `Host key` → `Saved` / `Not saved`; `LinkRequestAdmin` (view and delete, with an `Occurrence` inline, read only; `wants_recording` shown) | Django's | model permissions (superuser) |

**Forms** (`apps/zoom/forms.py`):

- **`LinkRequestForm(ModelForm)`:**
  - model fields plus `website` (the honeypot, `required=False`);
  - `weekdays` as a `MultipleChoiceField` with `CheckboxSelectMultiple`, converted to and from the model's string;
  - `repeat` as `RadioSelect`;
  - `wants_recording` as a `CheckboxInput`;
  - the widgets carry the `type`, `step`, `autocomplete` and `inputmode` attributes;
  - the error messages are criterion 6's.
- **`ApproveForm(Form)`:** `host_account` as a `ModelChoiceField(RadioSelect)`, whose queryset is limited to the free bookable accounts, passed in. When `needs_manual_details`, it adds `join_url`, `meeting_id` and `passcode` with criterion 30's validation.
- **`RejectForm(Form)`:** `reason` as a `CharField(Textarea, max_length=1000)`, stripped.

**Information architecture** (`ux-strategy:information-architecture`):

```
PUBLIC FRAME (no sign-in; reached by the link IT shares, criterion 24)
Request a Zoom link ─POST→ Check your email ··email··> Confirm your request ─POST→ Request confirmed
                                                          ├ This link has expired → (Request a Zoom link)
                                                          ├ This link doesn't work → (Request a Zoom link)
                                                          └ Already confirmed

SHELL (signed in)
Home                               [Menu]
Zoom link requests                 [Zoom links]      only with zoom.review_linkrequest
│   tabs: Waiting · Link sent · Not approved · All  (+ search, pager)
└── ZL-0042: CCC Batch 3 - Mathematics            (detail: facts → classes → availability → approve / reject)
Admin                              [Administration]  staff; Host accounts live here (superuser)
Utility (top bar): unchanged; search and bell stay placeholders (D10)
```

- **Wayfinding:** on the queue and detail pages, the sidebar item `Link requests`, the breadcrumb (`Home › Zoom link requests [› ZL-…]`) and the h1 agree.
- **Labels:** the nav group says what it is (`Zoom links`). The pages say what you do there (`Request a Zoom link`, `Confirm your request`). The statuses use the requester's and IT's words (`Waiting for IT`, `Link sent`, `Not approved`), not system words.
- **Depth:** at most 2 below Home.

### Context contract
<!-- The only coupling between backend and frontend: template → exact context variables and their types -->

**Everywhere:** as in brief 004 (`tmd_site_name`, `user`, `request`, `messages`, `csrf_token`), **plus `perms`** (auth `PermWrapper`). `base.html` passes it into the sidebar:

```
{% include "partials/sidebar.html" with current=… current_ns=… user=user perms=perms only %}
```

The sidebar shows the `Zoom links` group when `perms.zoom.review_linkrequest`, and marks `Link requests` current when `current_ns == "zoom"`.

**New icons:** added to `partials/icons.html` as the designer lists them. At least `chevron-right` (crumb separator), `video` (nav item), `alert-circle` (field errors), and the tag icons. Every symbol must be used (criterion 51).

**`templates/public_base.html`** extends `base.html` and overrides `body`. It reads `messages` (passed to `partials/messages.html`) and `tmd_site_name`. Its blocks are `title` (inherited), `heading` (h1 text) and `content`. It includes `partials/colour_mode_button.html`, `partials/messages.html` and `partials/footer.html`, all `only`. There's no sprite duplication: the sprite comes from `base.html`.

**Shared partials (new):**

| Partial | `with … only` parameters | Notes |
|---|---|---|
| `zoom/partials/status_tag.html` | `status` (str, a `LinkRequest.Status` value), `label` (str, `get_status_display`) | The tone and icon per status are chosen here, and only here |
| `zoom/partials/schedule.html` | `summary` (str, `link_request.schedule_summary`) | Prints the sentence (D22). e.g. `Every Monday and Wednesday, 8:30 am to 11:30 am, from Mon 5 Oct to Wed 28 Oct 2026 (8 classes)` / `Once, on Mon 5 Oct 2026, 8:30 am to 11:30 am` |
| `zoom/partials/occurrence_list.html` | `occurrences` (list of Occurrence: `starts_at`, `ends_at`, aware UTC; the template shows local time with Django's `date`/`time` filters under `TIME_ZONE`) | `<ol>` of `Mon 5 Oct 2026, 8:30 am to 11:30 am` |
| `zoom/partials/field.html` (optional, the builder decides) | `field` (BoundField), `type` (str, optional) | Label, help (`<name>-help`), error (`<name>-error`) and `aria-*` wiring per criterion 7 |
| `zoom/partials/error_summary.html` | `form` (Form), `lead` (str) | Criterion 7's summary: `{lead} 1 thing needs your attention.` / `{lead} {n} things need your attention.` (D21). Renders nothing when the form has no errors |
| `partials/crumb.html` (optional) | `url` (str or ""), `text` (str), `current` (bool) | One `<li>` with the separator icon |

**`zoom/request_form.html`** (`LinkRequestCreateView`):

| Variable | Type | Notes |
|---|---|---|
| `form` | `LinkRequestForm` | Fields: `class_name`, `first_date`, `start_time`, `end_time`, `repeat` (choices `once` / `weekly`), `weekdays` (choices `"1"`…`"7"` / `Monday`…`Sunday`), `last_date`, `wants_recording` (bool), `requester_name`, `requester_email`, `requester_phone`, `notes`, `website`. Also `form.non_field_errors` (the throttle) |
| `max_occurrences` | int | 60, for help copy |
| `today` | date | Local date, for the date input's `min` |
| `latest_date` | date | today + 365, for `max` |

**JS hooks:**

- `data-repeat` on each repeat radio;
- `data-weekly-fields` on the wrapper of `weekdays` + `last_date`;
- `data-error-summary` on the summary (focus on load when present).

**`zoom/request_sent.html`:** `sent_to` (str or `None`, popped from the session; `None` shows the generic line `We've sent a link to the email address you gave.`), `link_hours` (int, 24).

**`zoom/confirm.html`:**

| Variable | Type | Notes |
|---|---|---|
| `state` | str | `"ready"`, `"already"`, `"expired"` or `"invalid"` |
| `link_request` | LinkRequest or `None` | Set for `ready` / `already`. `reference`, `class_name`, `wants_recording`, `requester_*`, `requester_phone_display`, `schedule_summary`, `get_status_display` |
| `occurrences` | list[Occurrence] | Empty unless `ready` |
| `occurrence_count` | int | |
| `token` | str | For the form `action`: `{% url 'zoom:confirm' token %}` |

**`zoom/confirmed.html`:** `link_request` (LinkRequest: `reference`, `requester_email`, `class_name`).

**`zoom/queue.html`** (`QueueView`):

| Variable | Type | Notes |
|---|---|---|
| `link_requests` | page of LinkRequest (`context_object_name`) | Each has `pk`, `reference`, `class_name`, `wants_recording`, `requester_name`, `requester_email`, `requester_phone`, `requester_phone_display`, `status`, `get_status_display`, the annotated `first_start` (aware datetime) and `occurrence_count` (int) |
| `page_obj`, `paginator`, `is_paginated` | Django's | |
| `tabs` | list of dict `{value: str, label: str, count: int, current: bool}` | In order: waiting, approved, rejected, all |
| `status` | str | The current tab value |
| `q` | str | The current search, `""` if none |
| `public_form_url` | str | Absolute URL of `zoom:request` |

**`zoom/detail.html`** (`LinkRequestDetailView`, and `ApproveView` / `RejectView` on error; `ReviewContextMixin` builds all of it):

| Variable | Type | Notes |
|---|---|---|
| `link_request` | LinkRequest | Every field (including `wants_recording`; `host_account.host_key_encrypted` must not be rendered), plus `reference`, `weekday_names`, `schedule_summary`, `requester_phone_display`, `get_status_display`, `get_repeat_display`, `decided_by` (User, `__str__`), `host_account` (HostAccount or `None`) |
| `occurrences` | list[Occurrence] | |
| `occurrence_count` | int | |
| `can_decide` | bool | `status == waiting` |
| `has_started` | bool | |
| `availability` | list of dict `{account: HostAccount, is_free: bool, has_host_key: bool, busy_count: int, clashes: list of {occurrence: Occurrence, other: Occurrence}}` (`busy_count` = distinct clashing occurrences of this request; `clashes` = one entry per pair; D22) | `other.link_request` is `select_related` (reference, pk, class_name). Empty unless `can_decide` |
| `free_count` | int | |
| `overlapping_waiting` | list[LinkRequest] (annotated `first_start` and `first_overlap`: an aware datetime, the earliest start among that request's occurrences overlapping this one; ordered by `first_overlap`; D22) | |
| `earlier_requests` | list[LinkRequest] (≤5) | |
| `approve_form` | ApproveForm or `None` | `None` when not `can_decide`, when `has_started`, or when `free_count == 0` |
| `reject_form` | RejectForm or `None` | `None` when not `can_decide` |
| `needs_manual_details` | bool | From the provider |
| `approve_error` | str or `None` | Conflict, unreadable-host-key or provider message on a failed approve (shown as an error `.notice` above the forms) |

No detail-page variable ever carries a decrypted host key.

**Emails** (`templates/zoom/email/`, plain text; bodies use `{% autoescape off %}`, D9; subject and body are separate files). The confirm, IT and approval bodies print `When: {{ link_request.schedule_summary }}`, and phones as `requester_phone_display` (D22):

| Template pair | Context |
|---|---|
| `confirm_subject.txt` / `confirm_body.txt` | `link_request`, `occurrences`, `confirm_url` (str, absolute), `link_hours` (int) |
| `it_new_subject.txt` / `it_new_body.txt` | `link_request`, `occurrences`, `detail_url` (str, absolute) |
| `approved_subject.txt` / `approved_body.txt` | `link_request` (with `join_url`, `meeting_id`, `passcode`, `wants_recording`), `occurrences`, `host_key` (str, decrypted by the service; `""` shows criterion 61's "ask the IT desk" line). **The only template that receives a host key** |
| `rejected_subject.txt` / `rejected_body.txt` | `link_request` (with `rejection_reason`), `request_url` (str, absolute, `zoom:request`) |

### Placement and reuse

- **`apps/zoom`** (new, D3): models, QuerySets, `services.py`, `providers.py`, `validators.py`, `crypto.py`, `forms.py`, `views.py`, `urls.py`, `admin.py`, `checks.py`, `apps.py`, `management/commands/rotate_host_keys.py`, migrations and tests.
- **`templates/`:**
  - `public_base.html` (new);
  - `zoom/*.html`, `zoom/partials/*.html` and `zoom/email/*.txt` (new);
  - `partials/sidebar.html` (a new group and `perms`);
  - `base.html` (passes `perms`; nothing else changes);
  - `partials/icons.html` (new symbols).
- **`static/`:** `css/style.css` gets the ported components and the `--fs-tag`, `--lh-flat` and `--tag-pad-y` tokens from brief 004's rename table (1b), and `js/app.js` gets one block for the weekly toggle and error-summary focus.
- **`config/settings/*`, `.env.example`, `compose.yaml`:** `tmd-devops` (criterion 49), plus `apps.zoom` in `LOCAL_APPS` and the constants:

  ```
  ZOOM_PROVIDER
  ZOOM_CONFIRM_LINK_HOURS = 24
  ZOOM_REQUEST_LIMIT_PER_EMAIL_PER_HOUR = 5
  ZOOM_REQUEST_LIMIT_PER_IP_PER_HOUR = 20
  TRUSTED_PROXY_COUNT
  HOST_KEY_ENCRYPTION_KEYS   (list, read from a comma-separated env var)
  ```

  `requirements/base.txt` also gains `cryptography` (D17, criterion 66).
- **Reused from Django** (nothing hand-rolled):
  - `CreateView`, `ListView`, `DetailView`, `FormView`, `TemplateView`;
  - `LoginRequiredMixin` / `PermissionRequiredMixin`;
  - `ModelForm`, custom permissions, `Group`, `UserManager.with_perm`;
  - `django.core.signing`;
  - `send_mail` / `render_to_string`;
  - `messages`, `Paginator`, admin;
  - `select_for_update`, `CheckConstraint` / `UniqueConstraint`;
  - the checks framework and `zoneinfo`.
- **Reused from the project:** the shell and partials (brief 004), `partials/messages.html` (in-flow flash, brief 004 D16), `User.__str__` for "decided by", and f-desk's component CSS from `design/f-desk/style.css`, ported with role-named tokens (brief 004's port rules D-1).
- **Not built:** a cache or rate-limit library, a CAPTCHA, a task queue, HTML emails, a nav registry or context processor, a notification model, an encrypted model-field type (D17), or any storage of Zoom API credentials.
- **New dependencies:** `cryptography` (runtime, D17). There are no others at runtime. If the verifier wants `time-machine` for frozen time, it's a **dev-only** dependency, and the reason goes in the verifier's notes.

## Agent plan
<!-- owner: tmd-planner — ordered steps; mark steps that can run in parallel -->

**Step 1 — in parallel:**

- **1a `tmd-ui-designer`** writes the Design section of this brief, with no HTML, CSS or JS:
  - **The public frame:** layout at 1440, 400 and 320; the brand line, colour-mode button and footer. It takes the sign-in form column's look as its starting point.
  - **The request form:** grouping into three fieldsets, `The class`, `When`, `About you`. Help text for every field, saying what to type (for example `Only the day and time of one class. For a weekly class, tick the days below.`). The weekly-fields reveal. The error summary and field errors (criterion 7). The honeypot's hiding.
  - **Sent, confirm (four states) and confirmed:** copy and layout.
  - **The queue:** tabs, search, table (the f-desk `.datagrid` with its phone card layout), pager, both empty states and the share-link line.
  - **The detail:** facts, class list, "earlier requests", availability (free or busy rows with clash lines), "also waiting", the approve form (radio cards per account, manual fields and note), the reject form, the no-free and started notices, and the decided state.
  - **Status-tag mapping:** tone and icon per status and per availability tag, with contrast in both modes at 10.5px.
  - The list of icons added to the sprite.
  - The recording checkbox (in `The class`) and the `Recording asked for` marker in the queue and on the detail page.
  - The `Host key saved` / `No host key saved` words beside each account in the approve form.
  - The plain-text copy of all four emails. The approval email includes the host-key paragraph and the recording line (criterion 35).
  - The Needs-JS list.
  - Any copy change to the pinned strings goes back through the main session first.

  Skills: `interaction-design:form-design`, `interaction-design:error-handling-ux`, `accessible-content:table-accessibility`, `designer-toolkit:ux-writing`, `cognitive-accessibility:plain-language-design`.
- **1b `tmd-devops`** does criterion 49 and the settings constants:
  - adds `apps.zoom` to `LOCAL_APPS` (the app package itself is created by the backend in step 2a; devops may add the entry in the same change as 2a if that ordering is simpler, and records which);
  - moves the email env reading from `prod.py` to `base.py`, and passes `EMAIL_*`, `ZOOM_PROVIDER`, `TRUSTED_PROXY_COUNT` and `HOST_KEY_ENCRYPTION_KEYS` through `compose.yaml`;
  - `HOST_KEY_ENCRYPTION_KEYS` gets the `:?` required form, like `SECRET_KEY`;
  - adds `cryptography` to `requirements/base.txt`, pinned and with the reason comment (criterion 66), and confirms the image still builds;
  - sets the fixed fake test key in `test.py`;
  - updates `.env.example` (dev: `ZOOM_PROVIDER=fake`, `EMAIL_BACKEND` console, the key-generation one-liner for `HOST_KEY_ENCRYPTION_KEYS`);
  - writes its Implementation notes.

  It doesn't touch `apps/`.

**Step 2 — in parallel, once the step it depends on is in (the context contract above is fixed):**

- **2a `tmd-django-backend`** (after 1b). It owns `apps/zoom/**`, the `zoom/` line in `config/urls.py`, the email `.txt` templates' **context** (the copy comes from the designer), and the view-side `perms` include change in `base.html`, coordinated with 2b.
  - **Build:** the models, QuerySets, constraints, both migrations, the services (D5 locking order and error mapping), providers, validators, `crypto.py`, the host-key methods, the admin form, `rotate_host_keys`, forms, views, admin and checks.
  - **Self-check:** criteria 4–6, 8–11, 13–18, 20–22, 25, 34–48, 50 and 59–65 with its own quick runs.
  - **Notes:** the Implementation notes, which record any contract deviation.
  - **Skills:** `delivery-execution:risk-register` for the locking and deadlock handling is optional.
- **2b `tmd-frontend`** (after 1a). It owns `templates/**` (except the email copy's context), `static/css/style.css` and `static/js/app.js`.
  - **Build:** `public_base.html`, every `zoom/*.html` page and partial, the sidebar group, the sprite additions, the ported components and tokens, and the weekly-toggle and summary-focus JS.
  - **Self-check:** criteria 1–3, 7, 12 (escaping), 19, 23, 24, 26–33 (markup), 51–54, and renders every page in both modes.
  - **Skills:** `inclusive-interaction:keyboard-navigation`, `design-systems:accessibility-audit`.

  Frontend and backend agree on the `base.html` `perms` line through this contract. Whoever edits `base.html` first does it, and the other leaves it alone.

**Step 3 — `tmd-test-verifier`:**

- writes pytest tests for every criterion that can be automated, including:
  - the threaded race test (38b and 38c);
  - the `CHECK` constraint tests (45);
  - the query-budget test (25);
  - the caplog tests (41, 65);
  - the raw-column host-key test (60);
  - the "host key appears only in the approval email" sweep (61);
  - the admin changelist and permission tests (62);
  - the rotation test (63);
- updates the two sidebar tests (criterion 55);
- runs all five "Verify a change" checks, including `check --deploy` (56) and the prod-stack walk-through (57), then restores `.env` and the previous stack;
- runs the Playwright checks from the scratchpad (criteria 33, 52–54) and captures criterion 58's screenshots.

A FAIL goes back to 2a, 2b or 1b.

**Step 4 — `tmd-code-reviewer`** (read-only). It reviews:

- the MVT split: the rules on models and QuerySets, and thin views (criterion 44);
- D5's locking order and the locking read, and how the IntegrityError and deadlock are mapped;
- the security points:
  - honeypot, throttle, token salt and age, GET vs POST;
  - autoescape (off only in `.txt`);
  - no secrets in fields or logs, the admin permissions, and the proxy-IP parsing;
  - **host-key handling**: Fernet used only in `crypto.py`, the key never in context except the approval email, the admin field only with the change permission, the changelist masked, and `__str__`/`__repr__`;
  - the `cryptography` dependency's justification;
- DRY: the status tone lives only in `status_tag.html`, the reference only on the model, env reading only in `base.py`;
- the public frame against D1;
- the tag size and contrast.

Suggested skills: `security-review`, `design-systems:accessibility-audit`. CHANGES REQUESTED goes back to step 2, then step 3.

**Step 5 — `tmd-docs-writer`:**

- **`README.md`:**
  - the new env vars;
  - how to add IT staff (`IT desk` group) and host accounts (admin; mark free accounts unpaid);
  - `ZOOM_PROVIDER` values;
  - the **go-live gate** (D14);
  - the manual-provider workflow, including turning recording on by hand;
  - entering host keys in the admin;
  - **generating and rotating `HOST_KEY_ENCRYPTION_KEYS`**, and the warning that losing every key means re-typing all host keys;
  - what to do if a host key leaks: change it in Zoom, then re-type it in the admin (D17);
  - the `cryptography` notice under dependencies.
- **`CLAUDE.md`:**
  - Architecture → current apps: `zoom`;
  - the DRY bullet on page chrome, which now names both frames (D1);
  - Templates: the public frame;
  - the sidebar's `perms` parameter.
- **`docs/CHANGELOG.md`:** an entry for this brief.
- **The brief:** closes it.

**Order:** (1a ∥ 1b) → (2a after 1b ∥ 2b after 1a) → 3 → 4 → 5. Briefs 006 (D16, once each account's credentials are issued) and 007 (D19, once the owner sets the go-live date) follow. 007 gates production use (D14).

## Design
<!-- owner: tmd-ui-designer — layout + wireframes, components (existing classes), states, copy, accessibility, progressive enhancement -->

### D.0 Ground rules and components

**Direction.** Everything is built inside the app's f-desk theme: `static/css/style.css` tokens and classes, `base.html`, the partials. Components the app hasn't ported yet come from `design/f-desk/style.css` (spec in `docs/design/directions/f.md` §7), ported under the 004 rules: role-named tokens in `:root`, no raw values in rules, only what these pages use.

**Reused as they are (already in the app):** `.shell`, `.titlebar`, `.page-heading`, `.crumbs`, `.box` (`__head`, `__title`, `__body`), `.button` (`--primary`, `--secondary`, `--quiet`, `--block`, `--icon`), `.field`, `.field__label`, `.field__help`, `.input`, `.choice`, `.notice`, `.notice__title`, `.notice--bad`, `.flashes` / `.flash` (via `partials/messages.html`), `.icon`, `.icon--xl`, `.visually-hidden`, `.icon-button`, `.page-foot`, `.signin__brandline` (values only; see D.1).

**Ported from f-desk (names unchanged, f.md reference):**

| Class | f.md | Used on |
|---|---|---|
| `.tag` + `--ok` `--warn` `--note` `--plain` `--brand`, `.tags` | §7.4 | statuses, availability, recording marker, host-key words |
| `.field__error` | §7.5 | every field error (icon `alert-circle` 14px + text) |
| `textarea.input` | §7.5 | `notes`, `reason` |
| `.options`, `.options__list`, `.choice--tall`, `.choice__words`, `.choice__help` | §7.5 | repeat radios, weekday checkboxes, `Book it on` |
| `.check` | §7.5 | `wants_recording` |
| `.form-actions` | ui-kit | submit rows |
| `.notice--ok`, `--warn`, `--note`, `.notice ul`, `.notice a` | §7.7 | error summary, manual note, no-free / started, decided line, share link |
| `.empty`, `.disc`, `.disc--64`, `.disc--note` | §7.7 | queue empty states, "check your email" |
| `.datagrid-wrap`, `.datagrid`, `.datagrid__label`, `.datagrid__ref`, phone card layout <768px | §7.6 | queue table |
| `.facts`, `.facts-cols` | §7.8 | confirm page, detail |
| `.pager` | §7.8 | queue |
| `.searchbox`, `.finder__search`, `.result-line` | §10.2 | queue search |
| `.tap-link` (<768px: 44px tall block link) | ui-kit | reference links in the table card, list links on the detail page |

**Tokens the port needs** (all in `:root`, both modes, values from f.md §9.2 / §9.3; no hex outside `:root`):

- Status soft and line colours the app doesn't have yet: `--c-ok-soft`, `--c-warn-soft`, `--c-note-soft`, `--c-plain-text`, `--c-plain-soft`, `--c-brand-text`, `--c-brand-soft`, `--c-ok-line`, `--c-warn-line`, `--c-note-line` (line = the family's text colour at 30% alpha, added as palette entries like `--alpha-red-line`).
- From brief 004's rename table: `--fs-tag: 0.65625rem` (10.5px), `--lh-flat: 1`, `--tag-pad-y: 3px`, plus `--tag-pad-x: 5px`, `--icon-sm: 12px`, `--icon-14: 14px` (name it by role, e.g. `--icon-error`).
- `--fs-error: 0.765625rem` (12.25px) with line height 1.5; `--textarea-min: 110px`; `--measure: 40ch`; `--disc-lg: 64px`; `--row-label-w: 8.5em`; `--facts-dt-min: 8em`; `--facts-dt-max: 12em`.
- New for this brief: `--form-w: 640px` (the readable width of every form and of the public column).

**New components** (each has one spec file; nothing else fits):

| Component | File | Why nothing existing fits |
|---|---|---|
| Public frame `.public` (+ `__head`, `__brand`, `__mode`, `__main`, `__lead`) | `docs/design/public-frame.md` | D1: a page frame with no shell. The sign-in layout is split-screen and page-specific |
| Form section `.formsection` (a `<fieldset>` with a heading-sized `<legend>`) | `docs/design/form-section.md` | `.options` legends are label-sized; the three form groups need section weight without being headings |
| Status tabs `.tabs` (+ `__count`) | `docs/design/status-tabs.md` | f-desk has filters as `<select>`s, no tabs; criterion 20 needs links with counts and `aria-current` |
| Availability list `.avail` (+ `__item`, `__name`, `__email`, `__clashes`) | `docs/design/availability-list.md` | a per-account row with a tag and a nested clash list; `.worklist` rows are links, `.datagrid` would nest tables |

**Icons added to `partials/icons.html`** (Feather, same drawing rules as the sprite; each is used): `chevron-right` (crumb separator, pager next), `chevron-left` (pager previous), `video` (nav item), `film` (recording marker), `alert-circle` (field errors), `clock` (`Waiting for IT`), `mail` (`Waiting for email check`, "check your email" disc), `x-circle` (`Not approved`), `key` (`Host key saved`), `inbox` (queue empty state). Already in the sprite and reused: `check-circle`, `alert-triangle`, `alert-octagon`, `info`, `search`.

**Dates and times on every page and email:** `Mon 5 Oct 2026` (`D j M Y`), times `8:30 am` (`time:"g:i A"|lower`; Django's `a` gives `a.m.`, which we don't want), ranges `8:30 am to 11:30 am` (the word `to`, never a dash, so screen readers say it). Always Colombo time. Pages wrap each date in `<time datetime="…">`.

### D.1 Public frame (`public_base.html`)

Starting point: the sign-in form column (brand line on top, colour-mode button in the corner, one centred column), widened to `--form-w` because the request form is long. Full spec: `docs/design/public-frame.md`.

**Structure** (inside `base.html`'s `{% block body %}`; skip link and sprite stay in `base.html`):

```
div.public
  header.public__head
    p.public__brand         crest-chip 28px (alt="") + "Technology Management Desk"   (not a link)
    div.public__mode        {% include "partials/colour_mode_button.html" only %}
  main#main.public__main  tabindex="-1"
    h1.public__title        {% block heading %}
    {% include "partials/messages.html" with messages=messages only %}
    {% block content %}
  {% include "partials/footer.html" only %}
```

No `<nav>`, no sidebar, top bar, user menu, settings dialog or `data-settings-open`, the same for signed-in visitors (criterion 1). Landmarks: `banner` (the header), `main`, `contentinfo` (the footer).

**1440 × 900**

```
page background --c-surface-2
┌────────────────────────────────────────────────────────────────────────────────────┐
│                  (crest) Technology Management Desk                          [☾]  │ head: 70px, brand centred,
│                                                                                    │ mode button 44×44 top-right
│                ┌──────────────────────────────────────────────┐                    │
│                │ Request a Zoom link                    (h1)  │ column 640 + 2×30  │
│                │ lead paragraph, --c-muted                    │ card: --c-surface, │
│                │ [flash messages]                             │ 1px --c-border,    │
│                │ content (form / state)                       │ --radius, pad 30   │
│                └──────────────────────────────────────────────┘                    │
│                                                                                    │
├────────────────────────────────────────────────────────────────────────────────────┤
│ 2026 © Polymath College                                  Technology Management Desk│ .page-foot (as in the shell)
└────────────────────────────────────────────────────────────────────────────────────┘
```

**400 × 844** (below 768px the card drops away: no border, `--c-surface` page, 20px side padding; 16px below 360px)

```
┌──────────────────────────────────────┐
│ (crest) Technology Management  [☾]  │ brand left-aligned (wraps to 2 lines if needed), button right
│         Desk                         │
│ Request a Zoom link                  │
│ lead…                                │
│ form, full width                     │
│ ──────────────────────────────────── │
│ 2026 © Polymath College              │ footer stacked, centred (existing <768 rule)
│ Technology Management Desk           │
└──────────────────────────────────────┘
```

**Values:**

- `.public`: `min-height: 100vh`, flex column; background `--c-surface-2` at ≥768px, `--c-surface` below.
- `.public__head`: flex, `min-height: var(--topbar-h)`, centred content, padding `0 var(--space-4)`, `position: relative`.
- `.public__brand`: exactly `.signin__brandline`'s values (flex, gap 8px, 14.4px/600, `--c-heading`, crest-chip 28px, radius 4px). The builder may group the two selectors in one rule; don't duplicate the values.
- `.public__mode`: `position: absolute; top: var(--space-3); right: var(--space-3)`; the button inside is 44×44 (as `.signin__mode .icon-button`, share the rule).
- `.public__main`: `flex: 1; width: 100%; max-width: calc(var(--form-w) + 2 * var(--page-pad-x)); margin: 0 auto var(--space-8); padding: var(--page-pad-x)`; at ≥768px: `--c-surface` background, 1px `--c-border`, `--radius`. Below 768px: padding `var(--space-5)`, margin-bottom 0; below 360px padding `var(--space-4)`.
- `.public__title`: 17.5px/500 (`--fs-title`), `--c-heading`, `--lh-tight`, margin-bottom `var(--space-3)`. Left-aligned (the sign-in h1 is centred; a long form reads better from the left).
- `.public__lead`: `--c-muted`, margin-bottom `var(--space-6)`. Used by pages as the first element of `content`.
- Footer: the shell's `.page-foot`. Its `grid-column` has no effect outside the grid; nothing else changes. Its `data-drawer-inert` is harmless here (no drawer).

**Title:** `{% block title %}` equals the h1 text on every public page (criterion 3 pins `Request a Zoom link · {SITE_NAME}`).

### D.2 Request form (`zoom:request`)

**Title / h1:** `Request a Zoom link`.
**Lead** (`.public__lead`): `Ask the IT desk for a Zoom link for your class. First we'll email you a link to check your address. Then IT will email you the Zoom link.` (No reply-time promise anywhere: D23, criterion 67.)

**Order in `content`:** error summary (only after a failed POST; first after the h1, criterion 54) → lead → `<form method="post" action="{% url 'zoom:request' %}" novalidate>` with CSRF → three `.formsection` fieldsets → honeypot → submit row.

`novalidate` so the server's plain-language errors are the ones people see; the inputs still carry `required`, `type`, `min`, `max`, `step` for mobile keyboards and pickers.

**1440** (inside the 640px public column)

```
Request a Zoom link
┌ ! We couldn't send this yet. 2 thing(s) need your attention. ─────────┐  (only after errors)
│  • Type the name of the class, like CCC Batch 3 - Mathematics.        │
│  • Tick at least one day of the week.                                 │
└───────────────────────────────────────────────────────────────────────┘
Ask the IT desk for a Zoom link for your class. First we'll email…
The class ─────────────────────────────────────────────────────────── (legend, 15.4/500, rule above)
Class name
The name students and IT will see, like CCC Batch 3 - Mathematics.
[                                                                     ]
[✓] Record this class to the Zoom cloud                               (44px row)
    Tick this if you need a recording. IT turns recording on in Zoom.
Anything IT should know (optional)
For example, a co-host who needs to join early…
[                                                                     ]
[                                                                     ]

When ────────────────────────────────────────────────────────────────
Date of the class
For a weekly class, choose the date of the first class.
[ 05/10/2026      📅 ]            (width 16rem)
Starts at                          Ends at
Sri Lanka time, on a 5-minute…     On the same day.
[ 08:30 ]                          [ 11:30 ]            (two equal columns ≥600px)
How often is the class?
Choose "Every week" if the class is on the same days at the same time.
┌────────────────────────────────┐ ┌────────────────────────────────┐
│ (•) Just once                  │ │ ( ) Every week                 │  .choice--tall, 2 columns ≥600
│     One class, on the date     │ │     The same time on the days  │
│     above.                     │ │     you tick, until a last date│
└────────────────────────────────┘ └────────────────────────────────┘
┌ If it's every week ──────────────────────────────────────────────┐  data-weekly-fields
│ Days of the week                                                 │  (JS: hidden when Just once)
│ Tick every day the class happens.                                │
│ [ ] Monday   [ ] Tuesday   [ ] Wednesday  [ ] Thursday           │  .choice rows, 4 columns ≥600
│ [ ] Friday   [ ] Saturday  [ ] Sunday                            │
│ Date of the last class                                           │
│ We'll book every ticked day up to and including this date…       │
│ [ 28/10/2026      📅 ]                                           │
└──────────────────────────────────────────────────────────────────┘

About you ───────────────────────────────────────────────────────────
Your full name          / help / [                    ]
Your email address      / help / [                    ]
Your phone number       / help / [                    ]   (width 16rem)

[ Send my request ]   (primary, auto width ≥600)
Nothing is booked until IT approves it. We'll email you either way.
```

**400** — the same order in one column. Changes below 600px: the start/end times stack; `Just once` / `Every week` stack; weekday rows go to 2 columns (`Monday`…`Sunday` in 4 rows, the last row has `Sunday` alone); the submit button is full width (`.button--block` below 600px via `.form-actions .button { width: 100% }`, as f-desk). Date, time and phone inputs are 100% wide below 600px.

```
┌────────────────────────────────┐
│ Request a Zoom link            │
│ Ask the IT desk for…           │
│ The class ──────────────────── │
│ Class name                     │
│ help                           │
│ [                            ] │
│ [✓] Record this class to the   │
│     Zoom cloud                 │
│ …                              │
│ When ───────────────────────── │
│ Date of the class  [        ]  │
│ Starts at          [        ]  │
│ Ends at            [        ]  │
│ (•) Just once                  │
│ ( ) Every week                 │
│ [ ] Monday     [ ] Tuesday     │
│ [ ] Wednesday  [ ] Thursday    │
│ [ ] Friday     [ ] Saturday    │
│ [ ] Sunday                     │
│ Date of the last class [     ] │
│ About you ──────────────────── │
│ …                              │
│ [      Send my request       ] │
└────────────────────────────────┘
```

**Components.** Sections: `<fieldset class="formsection">` + `<legend class="formsection__title">` (`docs/design/form-section.md`, which also defines the `.options` modifiers used below). Each text/date/time field: `.field` > `label.field__label` + `p.field__help#<name>-help` + `.input` + (on error) `p.field__error#<name>-error`. Repeat: `<fieldset class="options" aria-describedby="repeat-help">` + `<legend>` + `p.field__help#repeat-help` + `.options__list.options__list--two` of `label.choice.choice--tall` (radio + `.choice__words` with `.choice__help`). Weekly wrapper: `<fieldset class="options options--group" data-weekly-fields>` with legend `If it's every week` (a boxed group: 1px `--c-border`, `--radius`, padding 16px; the legend sits on the border as native fieldsets do). Weekdays: nested `<fieldset class="options" aria-describedby="weekdays-help">` with `.options__list.options__list--four` of `label.choice` rows (checkbox + day name). Recording: `label.check` (checkbox 18px + text) inside a `.field`, help under the label row. Honeypot: see below.

`.options__list` today is 3 columns; add modifiers `--two` (2 columns ≥600px) and `--four` (4 columns ≥600px, 2 below). Below 600px `--two` is 1 column.

Input widths: `class_name`, `requester_name`, `requester_email`, `notes` 100%. `first_date`, `last_date`, `requester_phone`: `max-width: 16rem` at ≥600px. Times: two columns in a `.field-pair` grid (`repeat(2, minmax(0, 1fr))`, gap 16px, ≥600px; one column below). `.field-pair` is a two-line layout helper; put it with the form rules, not a new component.

**Fields, in order: label / help / widget attributes**

| Field | Label | Help (`<name>-help`) | Attributes |
|---|---|---|---|
| `class_name` | `Class name` | `The name students and IT will see, like CCC Batch 3 - Mathematics.` | `type="text"`, `maxlength="200"`, `autocomplete="off"`, `required` |
| `wants_recording` | `Record this class to the Zoom cloud` (pinned) | `Tick this if you need a recording. IT turns recording on in Zoom.` | checkbox, unticked by default |
| `notes` | `Anything IT should know (optional)` | `For example, a co-host who needs to join early. Up to 1000 characters.` | `<textarea rows="4" maxlength="1000">` |
| `first_date` | `Date of the class` | `For a weekly class, choose the date of the first class.` | `type="date"`, `min="{{ today\|date:'Y-m-d' }}"`, `max="{{ latest_date\|date:'Y-m-d' }}"`, `required` |
| `start_time` | `Starts at` | `Sri Lanka time, on a 5-minute step, like 8:30 am.` | `type="time"`, `step="300"`, `required` |
| `end_time` | `Ends at` | `On the same day as it starts.` | `type="time"`, `step="300"`, `required` |
| `repeat` | legend `How often is the class?` | `Choose "Every week" if the class is on the same days at the same time each week.` | radios; `once` `Just once` (help `One class, on the date above.`), `weekly` `Every week` (help `The same time on the days you tick, until a last date.`); `data-repeat` on each; `once` checked by default |
| (wrapper) | legend `If it's every week` (pinned) | — | `data-weekly-fields` |
| `weekdays` | legend `Days of the week` | `Tick every day the class happens.` | 7 checkboxes `Monday`…`Sunday`, values `1`…`7` |
| `last_date` | `Date of the last class` | `We'll book every ticked day up to and including this date. One request can cover up to {{ max_occurrences }} classes.` | `type="date"`, same `min`/`max` |
| `requester_name` | `Your full name` | `So IT knows who the link is for.` | `autocomplete="name"`, `maxlength="150"` |
| `requester_email` | `Your email address` | `We'll send a link here to check it's yours. IT will send the Zoom link here too.` | `type="email"`, `autocomplete="email"`, `spellcheck="false"`, `autocapitalize="none"` |
| `requester_phone` | `Your phone number` | `In case IT needs to call you about the times, like 077 123 4567.` | `type="tel"`, `autocomplete="tel"`, `inputmode="tel"` |

Legends: section legends `The class`, `When`, `About you` (in that order; pinned by the plan).

**Honeypot** (after `About you`, before the submit row): `<div hidden aria-hidden="true">` containing `<label for="website">Leave this empty</label>` and `<input id="website" name="website" type="text" tabindex="-1" autocomplete="off">`. It is hidden from everyone by the `hidden` attribute alone; no CSS trick is needed.

**Submit row** (`.form-actions`): `button.button.button--primary` `Send my request`. Under it, `p.field__help` (not wired to anything): `Nothing is booked until IT approves it. We'll email you either way.`

**States**

| State | What shows |
|---|---|
| Default (GET) | empty form, `Just once` checked, recording unticked; weekly group visible without JS, hidden with JS |
| Validation errors (200) | error summary at the top of `content`; each invalid field: `aria-invalid="true"`, 2px `--c-bad-text` border, `p.field__error#<name>-error` under the control with `alert-circle` + the pinned text (criterion 6); every typed value kept, including ticked days and recording. For the two fieldsets (`repeat`, `weekdays`) the error `<p>` goes directly under the legend's help, and the fieldset's `aria-describedby` becomes `weekdays-error weekdays-help` |
| Weekly errors while `Just once` is checked | can't happen: the server ignores weekly fields for `once` |
| Weekly errors with JS on | the group is shown because `Every week` is checked (JS reads the checked radio on load) |
| Rate-limited (429) | the same form, values kept, summary with one unlinked item: `You've sent a lot of requests in the last hour. Wait an hour, then try again, or phone the IT desk.` (pinned). No field is marked invalid |
| Honeypot hit | redirect to "check your email", same as success (criterion 9) |
| Success | 302 to `zoom:request_sent` |
| Server error (500) | Django's plain 500 page; out of scope for this brief |

**Error summary** (`zoom/partials/error_summary.html`): `div.notice.notice--bad#error-summary` with `role="alert"`, `tabindex="-1"`, `data-error-summary`; `alert-octagon` 20px; `p.notice__title`; then `<ul>` with one `<li><a href="#<field id>">{error text}</a></li>` per field error in form order, and non-field errors as `<li>` without a link. For `repeat` and `weekdays` the link goes to the first radio / checkbox (`#id_repeat_0`-style id, whatever the widget renders; the builder links to the real first input id). Title: `We couldn't send this yet. {n} thing(s) need your attention.` (pinned; see contract gap G3 for the plural).

### D.3 Check your email, confirm (four states), confirmed, rate-limited

All four pages use the public frame (D.1). Each has one h1; the `<title>` equals it.

**Rate-limited** is not a page of its own: it is the request form re-rendered with status 429 and the summary described in D.2.

#### `zoom:request_sent` — "Check your email"

```
1440 / 400 (same column)
        (✉)                         .disc.disc--64.disc--note, `mail` 28px, centred
  Check your email                  h1, centred on this page only (.public__title--centre)
  We've sent a link to nimali@example.com.
  Open the email and choose the link in it to confirm your request.
  The link works for 24 hours.
  IT won't see your request until you confirm it.
  ┌ i  No email? ──────────────────────────────────────────┐  .notice.notice--note
  │ Check your spam or junk folder. If it isn't there      │
  │ after 10 minutes, send your request again and check    │
  │ the email address.                                     │
  └────────────────────────────────────────────────────────┘
  [ Send a new request ]            .button--secondary → zoom:request
```

Copy:

- h1: `Check your email`
- With `sent_to`: `We've sent a link to {sent_to}.` (the address in `<strong>`). Without it: `We've sent a link to the email address you gave.` (pinned).
- `Open the email and choose the link in it to confirm your request. The link works for {link_hours} hours.`
- `IT won't see your request until you confirm it.`
- Notice title `No email?`, body `Check your spam or junk folder. If it isn't there after 10 minutes, send your request again and check the email address.`
- Button link: `Send a new request`.

The page is the same after a honeypot hit (criterion 9); that's intended.

#### `zoom:confirm` — four states (`state`)

**`ready`** (h1 `Confirm your request`)

```
1440 (640 column)                                   400
Confirm your request                                Confirm your request
Check the details. If they're right, confirm        Check the details…
and we'll send your request to the IT desk.
Class          CCC Batch 3 - Mathematics            Class
When           Every Monday and Wednesday,          CCC Batch 3 - Mathematics
               8:30 am to 11:30 am, from Mon 5      When
               Oct to Wed 28 Oct 2026 (8 classes)   Every Monday and …
Recording      Yes, record it to the Zoom cloud     (.facts stacks: dt above dd <600px)
Your name      Nimali Perera
Email          nimali@example.com
Phone          +94 77 123 4567
The classes (8)            (h2)                     The classes (8)
1. Mon 5 Oct 2026, 8:30 am to 11:30 am              1. Mon 5 Oct 2026, 8:30 am to
2. Wed 7 Oct 2026, 8:30 am to 11:30 am                 11:30 am
…                                                   …
[ Confirm my request ]  (primary)                   [     Confirm my request     ]
Something wrong? Don't confirm. Send a new          Something wrong? …
request with the right details instead.
```

- Lead: `Check the details. If they're right, confirm and we'll send your request to the IT desk.`
- `.facts` (`<dl>`): `Class` → `class_name`; `When` → `{% include "zoom/partials/schedule.html" with summary=link_request.schedule_summary only %}`; `Recording` → `Yes, record it to the Zoom cloud` / `No` (pinned); `Your name`; `Email`; `Phone` (display form, see gap G1). Notes are not shown here (the requester typed them a minute ago; IT sees them).
- `<h2>` `The classes ({occurrence_count})` then `occurrence_list.html` (`<ol>`, 2 CSS columns at ≥600px when there are more than 6: builder uses `columns: 2` on the list with a `.occurrences--cols` class set by the template from the count, which is presentation).
- Form: `method="post" action="{% url 'zoom:confirm' token %}"`, CSRF, `.form-actions` with `button.button--primary` `Confirm my request` (pinned).
- Under it, `p.field__help`: `Something wrong? Don't confirm. ` + link `Send a new request with the right details instead.` → `zoom:request`.

**`already`** (h1 `Already confirmed`)

- `.notice.notice--ok` (`check-circle`): title `You've already confirmed this request.` (pinned), body `Your reference is {reference}. IT will email {requester_email} when they've decided.`
- No form, no other links.

**`expired`** (h1 `This link has expired`)

- `.notice.notice--warn` (`alert-triangle`): body `This link has expired. Please send your request again.` (pinned).
- `.form-actions`: link styled `button--primary` `Send your request again` → `zoom:request`.

**`invalid`** (h1 `We can't open this link`)

- `.notice.notice--warn` (`alert-triangle`): body `This link doesn't work. Check you copied all of it from the email, or send your request again.` (pinned).
- Link styled `button--secondary` `Send a new request` → `zoom:request`.

In all three non-ready states the notice has no `role` (it is the page's content, read after the h1), and there's no `tabindex`.

#### `zoom:confirmed` — "Request confirmed"

```
        (✓)                       .disc.disc--64 in the ok family (.disc--ok), check-circle 28px
  Request confirmed               h1, centred
  Your request is with the IT desk.
  Reference     ZL-0042           .facts
  Class         CCC Batch 3 - Mathematics
  IT will email nimali@example.com with the Zoom link, or tell you why they can't.
  Keep your reference, ZL-0042, in case you need to phone the IT desk.
  You can close this page.
```

- h1: `Request confirmed`
- `Your request is with the IT desk.`
- `.facts`: `Reference` → `reference`, `Class` → `class_name`.
- `IT will email {requester_email} with the Zoom link, or tell you why they can't.`
- `Keep your reference, {reference}, in case you need to phone the IT desk.`
- `You can close this page.` (`--c-muted`)

`.disc--ok` (`--c-ok-soft` / `--c-ok-text`) is added next to f-desk's other `.disc--*` families.

**No-permission / not-found:** public pages have no permission. `zoom:confirmed` with a bad token is Django's 404 page (the plan's choice).

### D.4 IT queue (`zoom:queue`)

In the shell. `<title>` and h1 `Zoom link requests`; breadcrumb `Home › Zoom link requests` (the last item is `<span aria-current="page">`). The crumb separator is `chevron-right` 14px `--c-muted`, `aria-hidden`, 8px each side, inside each `<li>` after the first (f.md §5); `partials/crumb.html` is worth building because the detail page needs two crumbs.

**1440** (content column 1130px)

```
Zoom link requests                                             Home › Zoom link requests
┌ i  Share this link with staff who need a Zoom link: ─────────────────────────────────────┐ .notice--note
│    https://tmd.polymath.lk/zoom/request/                                                 │ (link, wraps anywhere)
└──────────────────────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ Waiting 3 │ Link sent 12 │ Not approved 2 │ All 17                                        │ .box__head holds .tabs
│ ▔▔▔▔▔▔▔▔▔                                                                                │ current: 3px bar + 600
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ Find a request                                                                           │ .finder__search
│ Type a reference like ZL-0042, a class, a name, an email or a phone number.              │
│ [⌕                                                                  ]  [ Search ]        │
│ 3 requests waiting for IT                                                                │ .result-line
│ ┌──────────┬────────────────────────┬─────────────────────┬──────────────┬───────┬────────────────┐
│ │Reference │Class                   │Requested by         │First class   │Classes│Status          │
│ ├──────────┼────────────────────────┼─────────────────────┼──────────────┼───────┼────────────────┤
│ │ZL-0042   │CCC Batch 3 - Mathematics│Nimali Perera       │Mon 5 Oct 2026│8      │[◷ Waiting for IT]│
│ │          │[▣ Recording asked for] │nimali@example.com   │8:30 am       │       │                │
│ │          │                        │+94 77 123 4567      │              │       │                │
│ └──────────┴────────────────────────┴─────────────────────┴──────────────┴───────┴────────────────┘
│ [‹]  Page 1 of 2  [›]                                                                    │ .pager
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

**400**

```
┌──────────────────────────────────┐
│ Zoom link requests               │
│ Home › Zoom link requests        │
│ ┌ i Share this link with staff … │
│ │   https://tmd.polymath.lk/zoo  │
│ │   m/request/                   │
│ └────────────────────────────────│
│ ┌──────────────────────────────┐ │
│ │ Waiting 3     │ Link sent 12 │ │ tabs: 2 × 2 grid, 44px rows
│ │ Not approved 2│ All 17       │ │
│ ├──────────────────────────────┤ │
│ │ Find a request               │ │
│ │ help                         │ │
│ │ [⌕                         ] │ │
│ │ [          Search          ] │ │ button full width
│ │ 3 requests waiting for IT    │ │
│ │ ┌──────────────────────────┐ │ │ row card (f-desk <768)
│ │ │Reference    ZL-0042      │ │ │ ref is a 44px .tap-link
│ │ │Class        CCC Batch 3 -│ │ │
│ │ │             Mathematics  │ │ │
│ │ │             [Recording…] │ │ │
│ │ │Requested by Nimali Perera│ │ │
│ │ │             nimali@exa…  │ │ │ email wraps anywhere
│ │ │             +94 77 123 … │ │ │
│ │ │First class  Mon 5 Oct 2026│ │ │
│ │ │             8:30 am      │ │ │
│ │ │Classes      8            │ │ │
│ │ │Status       [◷ Waiting…] │ │ │
│ │ └──────────────────────────┘ │ │
│ │ [‹]  Page 1 of 2  [›]        │ │
│ └──────────────────────────────┘ │
└──────────────────────────────────┘
```

**Share line** (criterion 24): `.notice.notice--note` (no role), `info` icon, `p.notice__title` `Share this link with staff who need a Zoom link:` (pinned), then `<p><a href="{public_form_url}">{public_form_url}</a></p>` with `overflow-wrap: anywhere`. It sits above the box so it doesn't compete with the table. No copy button (it would be a new JS behaviour; the link text can be selected, and right-click / long-press copies the link).

**Tabs** (`docs/design/status-tabs.md`): `<nav class="tabs" aria-label="Filter by status">` > `<ul>` > one `<li><a class="tabs__link" href="?status={value}">{label} <span class="tabs__count">{count}</span></a></li>` per `tabs` item; the current one has `aria-current="page"`. Labels: `Waiting`, `Link sent`, `Not approved`, `All` (pinned). Tab links carry **only** `status`: switching tab clears the search and the page, so each count matches what the tab shows. The accessible name reads e.g. "Waiting 3"; add a visually hidden word after the number: `<span class="visually-hidden"> requests</span>` (`request` when the count is 1).

**Search** (`<form method="get" role="search" action="{% url 'zoom:queue' %}" class="finder__search">`):

- hidden `status` = current tab;
- `label.field__label` for `q`: `Find a request`; help `q-help`: `Type a reference like ZL-0042, a class, a name, an email or a phone number.`;
- `.searchbox` with `search` icon 16px + `input.input` `type="search"` `name="q"` `id="q"` `value="{q}"` `aria-describedby="q-help"`, no placeholder (the help says it);
- `button.button.button--primary` `Search` (the one primary on this page);
- when `q` is set, a `a.button.button--quiet` `Clear the search` → `?status={status}` after the button.

**Result line** (`p.result-line`, plain text, no live role: every search is a full page load, and the line is read in order after the search field):

| Case | Text |
|---|---|
| No `q`, count > 0 | `{n} request(s) {phrase}` — phrase per tab: waiting `waiting for IT`, approved `with a link sent`, rejected `not approved`, all `in total` |
| `q`, count > 0 | `{n} request(s) match "{q}"` |
| Paginated | add `. Showing {start} to {end}.` (`page_obj.start_index` / `end_index`) |
| count = 0 | no result line; the empty state shows instead |

Plural: `1 request` / `2 requests` (template `pluralize`).

**Table** (`.datagrid-wrap` > `table.datagrid`):

- `<caption class="visually-hidden">` per tab, saying the order: waiting `Requests waiting for IT, soonest first class first`; approved `Requests with a link sent, most recently decided first`; rejected `Requests not approved, most recently decided first`; all `All requests, newest first`.
- `<th scope="col">` in order: `Reference`, `Class`, `Requested by`, `First class`, `Classes`, `Status` (pinned).
- Each `<th scope="row">` is the Reference cell (so a screen reader announces the row by reference): `<a class="datagrid__ref tap-link" href="{% url 'zoom:detail' pk %}">ZL-0042</a>`.
- Class: the name; when `wants_recording`, under it a `.tag.tag--brand` `film` `Recording asked for` (pinned words).
- Requested by: three lines, `<span>` blocks: name (`--fw-medium`, `--c-heading`), email, phone (display form, gap G1), both `--c-muted`; email and phone `overflow-wrap: anywhere`. Plain text, not `mailto:`/`tel:` links (those are on the detail page; here they would add two more targets per row).
- First class: `<time datetime="{iso}">` date on line 1, start time on line 2.
- Classes: the number.
- Status: `status_tag.html`.
- Phone (<768px): f-desk's card layout; each cell starts with `span.datagrid__label` (`aria-hidden="true"`) holding the column name; keep table semantics with explicit ARIA roles as f.md §7.6 says. Row hover background stays (`--c-surface-2`), the row itself isn't clickable (only the reference link is).

**Empty states** (inside the box body, replacing the result line, table and pager) — `.empty`:

| Case | Disc icon | `<h2>` | Body | Action |
|---|---|---|---|---|
| Tab empty, no `q` | `inbox` | `Nothing here yet.` (pinned) | `Requests show here once the person who sent them has confirmed their email address.` | none |
| `q` finds nothing | `search` | `No requests match "{q}".` (pinned) | `Check the spelling, or search in All.` (the words `search in All` link to `?status=all&q={q}`; left out on the All tab) | `a.button.button--secondary` `Clear the search` (pinned) → `?status={status}` |

**Pager** (only when `is_paginated`): `<nav class="pager" aria-label="Pages">` > `<ul>`: previous (`chevron-left` + visually hidden `Previous page`), `<li><span>Page {n} of {pages}</span></li>` (text, `--c-muted`, 44px line box), next (`chevron-right` + visually hidden `Next page`). A missing previous/next is left out, not disabled. Each link keeps `status` and `q` (`?status=…&q=…&page=…`, `q` url-encoded with `|urlencode`).

**No-permission:** Django's 403 for plain users, the login redirect for anonymous visitors (criterion 17). The `Zoom links` sidebar group isn't shown to them, so they don't reach it by navigation. No custom 403 page in this brief.

**Loading:** none. Tabs, search and paging are full page loads.

### D.5 Request detail (`zoom:detail`, approve, reject)

In the shell. h1 `{reference}: {class_name}` (pinned); `<title>` the same. Breadcrumb `Home › Zoom link requests › {reference}` (the middle crumb links to `zoom:queue`, no query).

**One column at every width**, boxes in reading order. A decision needs the facts, then the availability, then the forms; a two-column layout would put the forms beside the evidence and split the reading order on phones. Wide screens get two-column facts (`.facts-cols`) instead.

**Order in `content`:**

1. Messages (from the shell, under the title row).
2. `approve_error` notice, when set.
3. Decided line (decided requests only).
4. Box **Request** — class facts and requester facts, earlier requests.
5. Box **Classes ({n})**.
6. Box **Which accounts are free** (waiting only).
7. Box **Also waiting at overlapping times** (only when the list isn't empty).
8. No-free / started warning notice, or box **Approve and send the link** (waiting only).
9. Box **Reject this request** (waiting only).

**1440, waiting, one account busy, manual provider**

```
ZL-0042: CCC Batch 3 - Mathematics                 Home › Zoom link requests › ZL-0042
┌ Request ─────────────────────────────────────────────────────────────────────────────────┐
│ Status     [◷ Waiting for IT] [▣ Recording asked for] │ Name   Nimali Perera              │
│ Class      CCC Batch 3 - Mathematics                  │ Email  nimali@example.com (mailto) │
│ When       Every Monday and Wednesday, 8:30 am to     │ Phone  +94 77 123 4567 (tel)       │
│            11:30 am, from Mon 5 Oct to Wed 28 Oct…    │ Sent   Mon 28 Sep 2026, 9:40 am    │
│ Recording  Yes, record it to the Zoom cloud           │ Confirmed Mon 28 Sep 2026, 9:52 am │
│ Notes      A co-host needs to join early.             │                                   │
│ ── Earlier requests from this person (h3) ──────────────────────────────────────────────  │
│ ZL-0031  Grade 10 Science   [✓ Link sent]                                                │
└──────────────────────────────────────────────────────────────────────────────────────────┘
┌ Classes (8) ─────────────────────────────────────────────────────────────────────────────┐
│ 1. Mon 5 Oct 2026, 8:30 am to 11:30 am        5. Mon 19 Oct 2026, 8:30 am to 11:30 am     │ 2 columns ≥768
│ 2. Wed 7 Oct 2026, …                          6. …                                        │
└──────────────────────────────────────────────────────────────────────────────────────────┘
┌ Which accounts are free ─────────────────────────────────────────────────────────────────┐
│ 10 of 11 paid accounts are free for every class. Checked against approved bookings when   │
│ this page loaded.                                                                        │
│ Zoom 01                                                  [✓ Free for all 8 classes]       │
│ zoom01@polymath.lk                                                                       │
│ ─────────────────────────────────────────────────────────────────────────────────────── │
│ Zoom 02                                                  [▲ Busy for 1 of 8 classes]      │
│ zoom02@polymath.lk                                                                       │
│   • Wed 7 Oct 2026, 8:30 am to 11:30 am clashes with ZL-0031 Grade 10 Science,            │
│     9:00 am to 12:00 pm                                                                  │
│ …                                                                                        │
└──────────────────────────────────────────────────────────────────────────────────────────┘
┌ Also waiting at overlapping times ───────────────────────────────────────────────────────┐
│ These don't block each other, but only one of them can have each account.                │
│ ZL-0045  Grade 11 ICT    First overlap Mon 5 Oct 2026, 9:00 am                            │
└──────────────────────────────────────────────────────────────────────────────────────────┘
┌ Approve and send the link ───────────────────────────────────────────────────────────────┐
│ ┌ i Create the meeting in Zoom first ──────────────────────┐   (form max-width 640)       │
│ │ Sign in to Zoom as the account you choose below, create  │                               │
│ │ the meeting, then paste its details here.                 │                               │
│ │ Turn on cloud recording for this meeting. The requester  │                               │
│ │ asked for it.                                             │                               │
│ └──────────────────────────────────────────────────────────┘                               │
│ Book it on                                                                               │
│ ┌──────────────────────────────────────────────────────────┐                              │
│ │ (•) Zoom 01                       [⚿ Host key saved]     │  .choice--tall, stacked       │
│ │     zoom01@polymath.lk                                    │                              │
│ ├──────────────────────────────────────────────────────────┤                              │
│ │ ( ) Zoom 03                       [▲ No host key saved]  │                              │
│ │     zoom03@polymath.lk                                    │                              │
│ │     The email will ask the requester to get the host key │                              │
│ │     from the IT desk.                                     │                              │
│ └──────────────────────────────────────────────────────────┘                              │
│ Zoom link   / help / [https://                              ]                             │
│ Meeting ID  / help / [            ]                                                      │
│ Passcode    / help / [          ]                                                        │
│ [ Approve and email the link ]                                                           │
└──────────────────────────────────────────────────────────────────────────────────────────┘
┌ Reject this request ──────────────────────────────────────────────────────────────────┐
│ Why can't it go ahead?                                                                   │
│ The requester sees this in their email. Say what they can do instead.                    │
│ [                                                              ]                         │
│ [ Reject and email the reason ]  (secondary)                                             │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

**400** — the same boxes in the same order. Changes: `.facts-cols` becomes one column (class facts, then requester facts); `.facts` rows stack (dt above dd) below 600px; the class list is one column; in `.avail` the tag moves under the email; the account radio rows put the host-key tag on its own line; buttons are full width; the Zoom link field is 100% wide.

```
┌──────────────────────────────────┐
│ ZL-0042: CCC Batch 3 -           │
│ Mathematics                      │
│ Home › Zoom link requests ›      │
│ ZL-0042                          │
│ ┌ Request ─────────────────────┐ │
│ │ Status                       │ │
│ │ [◷ Waiting for IT]           │ │
│ │ [▣ Recording asked for]      │ │
│ │ Class                        │ │
│ │ CCC Batch 3 - Mathematics    │ │
│ │ …                            │ │
│ │ Name  / Email / Phone / Sent │ │
│ └──────────────────────────────┘ │
│ ┌ Classes (8) ─────────────────┐ │
│ │ 1. Mon 5 Oct 2026, 8:30 am   │ │
│ │    to 11:30 am               │ │
│ └──────────────────────────────┘ │
│ ┌ Which accounts are free ─────┐ │
│ │ Zoom 02                      │ │
│ │ zoom02@polymath.lk           │ │
│ │ [▲ Busy for 1 of 8 classes]  │ │
│ │ • Wed 7 Oct 2026, 8:30 am to │ │
│ │   11:30 am clashes with      │ │
│ │   ZL-0031 Grade 10 Science,  │ │
│ │   9:00 am to 12:00 pm        │ │
│ └──────────────────────────────┘ │
│ ┌ Approve and send the link ───┐ │
│ │ (•) Zoom 01                  │ │
│ │     zoom01@polymath.lk       │ │
│ │     [⚿ Host key saved]       │ │
│ │ …                            │ │
│ │ [Approve and email the link] │ │
│ └──────────────────────────────┘ │
│ ┌ Reject this request ──────┐ │
│ │ …                            │ │
│ │ [Reject and email the reason]│ │
│ └──────────────────────────────┘ │
└──────────────────────────────────┘
```

#### Box "Request" (`section.box`, `aria-labelledby`)

- h2 `Request`. Body: `.facts-cols` with two `<dl class="facts">`.
- Left `dl`: `Status` → `status_tag.html` and, when `wants_recording`, the `Recording asked for` tag (in a `.tags` row); `Class` → `class_name`; `When` → `schedule.html` with `summary=link_request.schedule_summary` (as on confirm); `Recording` → `Yes, record it to the Zoom cloud` / `No` (pinned); `Notes` → the notes with line breaks kept (`linebreaksbr`), or `None` in `--c-muted` when empty.
- Right `dl`: `Name`; `Email` → `<a href="mailto:{email}">`; `Phone` → `<a href="tel:{E.164}">{display form}</a>` (gap G1); `Sent` → `created_at`; `Confirmed` → `verified_at`.
- Links in `dd` get `.tap-link` (44px tall below 768px).
- **Earlier requests** (criterion 27; left out when empty): a top-bordered block inside the same box body, `<h3>` `Earlier requests from this person` (14px/600, `--c-heading`, margin `var(--space-5) 0 var(--space-2)`), then `ul.worklist` (ported from f-desk). Each `li` holds a `div.worklist__row` (not a link, so no hover rule applies to it; the builder scopes `.worklist__row:hover` to `a.worklist__row`) with `padding: var(--space-3) 0` and, in one flex-wrap line with 8px gaps: the reference as `a.worklist__ref.tap-link`, the class name, and the status tag.

#### Box "Classes ({occurrence_count})"

`occurrence_list.html` (`<ol>`, 2 CSS columns at ≥768px when more than 6 items, via `.occurrences--cols`). Each item `<time>`-wrapped.

#### Box "Which accounts are free" (waiting only; `docs/design/availability-list.md`)

- Lead `p` (`--c-muted`): `{free_count} of {m} paid accounts are free for every class. Checked against approved bookings when this page loaded.` where `m` is `availability|length`. When `m` is 0: `No paid Zoom accounts are set up. An administrator can add them in the admin.` and no list.
- `<ul class="avail">`, one `li.avail__item` per entry: `p.avail__name` (label, `--fw-semibold`, `--c-heading`), `p.avail__email` (`--c-muted`), the tag: `Free for all {n} classes` (`tag--ok`, `check-circle`) or `Busy for {k} of {n} classes` (`tag--warn`, `alert-triangle`) (pinned words). `k` = `clashes|length`; if a class clashes with two bookings it appears twice — see gap G4.
- Busy: `ul.avail__clashes`, one `li` per clash: `{occurrence date}, {occurrence start} to {end} clashes with ` + `<a href="{% url 'zoom:detail' other.link_request.pk %}">{other.link_request.reference}</a>` + ` {other.link_request.class_name}, {other start} to {other end}`.
- No host-key words here (they belong to the approve form, criterion 30).

#### Box "Also waiting at overlapping times" (criterion 29; left out when empty)

- Lead: `These don't block each other, but only one of them can have each account. Decide the one with the soonest class first.`
- The same `ul.worklist` pattern as "earlier requests": reference link, class name, `First overlap {date}, {time}` (`--c-muted`) (gap G2: the contract only carries `first_start`; until it's added the builder shows `First class {date}, {time}`).

#### Decided state (criterion 32)

- At the top of `content`: `.notice` — approved: `.notice--ok` + `check-circle`; rejected: `.notice--note` + `info`. Text: `This request was approved by {decider} on {date}.` / `This request was not approved by {decider} on {date}.` (pinned pattern; date `Mon 28 Sep 2026, 10:05 am`).
- The **Request** box gains facts (left `dl`, after `Notes`):
  - approved: `Booked on` → account label (and email, `--c-muted`); `Zoom link` → the link (`overflow-wrap: anywhere`, opens in the same tab); `Meeting ID` → as stored (digits); `Passcode` → value or `None` (`--c-muted`). This is where IT copies the link from when the email failed (criterion 41).
  - rejected: `Reason` → `rejection_reason` (`linebreaksbr`).
- No availability, "also waiting", approve or reject boxes.

#### Approve (waiting, `approve_form` set)

- Box h2 `Approve and send the link`. Body holds `<form method="post" action="{% url 'zoom:approve' pk %}" novalidate>` with CSRF, max-width `--form-w`.
- Manual note (`needs_manual_details` only): `.notice.notice--note`, `info`; title `Create the meeting in Zoom first`; body `Sign in to Zoom as the account you choose below and create the meeting for every class. Then paste its link, meeting ID and passcode here.` When `wants_recording`, a second `<p>`: `Turn on cloud recording for this meeting. The requester asked for it.` (pinned), in `--fw-semibold` so it isn't missed. The notice keeps its single `info` icon.
- Account radios: `<fieldset class="options">`, legend `Book it on` (pinned), help `approve-account-help`: `Only accounts free for every class are listed.`; `.options__list.options__list--stack` of `label.choice.choice--tall`: radio + `.choice__words` holding the label (`--fw-medium`), `.choice__help` email, and a `.tags` row with `Host key saved` (`tag--plain`, `key`) or `No host key saved` (`tag--warn`, `alert-triangle`) (pinned words). For an account without a key, a further `.choice__help` line: `The email will ask the requester to get the host key from the IT desk.` (criterion 61's behaviour, said plainly). First free account checked (pinned).
- Manual fields (only with `needs_manual_details`):

| Field | Label (pinned) | Help | Attributes |
|---|---|---|---|
| `join_url` | `Zoom link` | `Copy the invite link from the meeting in Zoom. It starts with https:// and has zoom.us in it.` | `type="url"`, `inputmode="url"`, `spellcheck="false"`, `autocomplete="off"` |
| `meeting_id` | `Meeting ID` | `The 9 to 11 digit number from Zoom. Spaces are fine.` | `type="text"`, `inputmode="numeric"`, `autocomplete="off"`, `max-width: 16rem` |
| `passcode` | `Passcode` | `Leave this empty if the meeting has no passcode.` | `type="text"`, `maxlength="10"`, `autocomplete="off"`, `spellcheck="false"`, `max-width: 16rem` |

- Field errors (these aren't pinned in the criteria; the backend uses exactly these):
  - `join_url` empty: `Paste the Zoom link for this meeting.`
  - `join_url` not https or not a Zoom host: `Paste the link Zoom gave you. It starts with https:// and ends in zoom.us before the first /, like https://us02web.zoom.us/j/12345678901.`
  - `meeting_id` empty or wrong: `Type the meeting ID from Zoom: 9 to 11 digits, like 123 4567 8901.`
  - `passcode` too long: `A Zoom passcode is at most 10 characters. Check you copied only the passcode.`
  - no account chosen or not bookable: `Choose one of the free accounts listed.` (pinned)
- Button: `button.button.button--primary` `Approve and email the link` (pinned). No confirm dialog: the action is the purpose of the page, and the requester email is the only outward effect.

**No approve form** (criterion 31): in place of the approve box, `.notice.notice--warn` with `alert-triangle` and no title, text pinned: `No paid Zoom account is free for every class in this request. Reject it with a reason, or ask the requester to change the times.` or `The first class has already started. Reject this request and ask for a new one.` The words "Reject it" match the reject box below.

#### Reject (waiting, `reject_form` set)

- Box h2 `Reject this request`. Form `method="post" action="{% url 'zoom:reject' pk %}" novalidate`, CSRF, max-width `--form-w`.
- `reason`: label `Why can't it go ahead?`; help `reason-help`: `The requester sees this in their email. Say what they can do instead, like "Please use the Grade 10 batch link instead."`; `<textarea rows="4" maxlength="1000">`. Error (pinned): `Tell the requester why, so they can fix it and ask again.`
- Button: `button.button.button--secondary` `Reject and email the reason`.

#### Outcomes and messages

| Outcome | Response | What the user sees |
|---|---|---|
| Approved | 302 → detail | success flash `Approved. The link was emailed to {requester_email}.` (pinned); decided notice; link facts |
| Approved, email failed | 302 → detail | warning flash (pinned, criterion 41); the link facts are on the same page to copy |
| Rejected | 302 → detail | success flash `Not approved. We emailed the reason to {requester_email}.` (pinned) |
| Already decided | 302 → detail | error flash `This request has already been decided.` (pinned) |
| Conflict / host key unreadable / provider error / started | 409 or 200 re-render | `approve_error` in `.notice.notice--bad` (`alert-octagon`, `role="alert"`, `tabindex="-1"`, `data-error-summary`) at the top of `content`, title `Nothing was booked`, body = the pinned message; availability refreshed; typed manual fields kept |
| Approve field errors | 200 re-render | error summary (`error_summary.html`) at the top of the **approve box body**, lead `We couldn't approve this yet.` (see gap G3), links to the fields; inline field errors |
| Reject field error | 200 re-render | the same summary at the top of the **reject box body**, lead `We couldn't send the reason yet.`; the approve form keeps its values (criterion 43) |

Only one element per page carries `data-error-summary`: `approve_error` if set, else the summary of the form that failed.

**No-permission:** 403 / login redirect as on the queue. `unverified` requests are a 404.

### D.6 Sidebar group, top bar

**Sidebar** (`partials/sidebar.html`, with `perms` passed in, criterion 19):

```
Menu
  ⌂ Home
Zoom links                      <p class="sidenav__group-title" id="nav-zoom">   only with perms.zoom.review_linkrequest
  ▶ Link requests               <ul class="sidenav__list" aria-labelledby="nav-zoom"> one .sidenav__link, icon `video`
Administration                  unchanged, still last
  ⛨ Admin
```

- Item markup is the same as `Home`'s: `a.sidenav__link` > `svg.icon.sidenav__icon` (`#i-video`) + `span.sidenav__label` `Link requests`, `href="{% url 'zoom:queue' %}"`.
- `aria-current="page"` when `current_ns == "zoom"` (queue and detail). Home is marked only when `current == "core:home"`, as today.
- A plain `<a>`, not a `<details>` parent: there's one item, so no chevron and no open state. Compact and icons-only sizes and the purple, dark and light tones already style it.
- Update the partial's header comment: `perms` (PermWrapper) joins its `with` list.

**Top bar:** unchanged. The search placeholder and the empty bell stay as they are (D10), and `docs/design/placeholder-controls.md` still describes them. That file says "Brief 005 replaces both controls"; `tmd-docs-writer` should change that line to "a later search-and-notifications brief" when closing this brief. No purple search button.

**Help card:** stays out (D11).

### D.7 Statuses and tags

One partial, `zoom/partials/status_tag.html`, chooses tone and icon for request statuses; every other tag here is written inline where it's used (each appears in one template only, except where noted).

| Where | Word | Variant | Icon | Why this tone |
|---|---|---|---|---|
| status `unverified` | `Waiting for email check` | `--note` | `mail` | information: nobody needs to act yet |
| status `waiting` | `Waiting for IT` | `--warn` | `clock` | IT needs to act |
| status `approved` | `Link sent` | `--ok` | `check-circle` | done, good outcome |
| status `rejected` | `Not approved` | `--plain` | `x-circle` | closed; not an error, so not red |
| availability free | `Free for all {n} classes` | `--ok` | `check-circle` | can book |
| availability busy | `Busy for {k} of {n} classes` | `--warn` | `alert-triangle` | can't book, not an error |
| recording (queue and detail) | `Recording asked for` | `--brand` | `film` | a request detail, not a state of progress |
| host key present (approve form) | `Host key saved` | `--plain` | `key` | neutral fact |
| host key missing (approve form) | `No host key saved` | `--warn` | `alert-triangle` | the email will be missing something |

- The `.tag` values: inline-flex, gap `var(--space-1)`, padding `var(--tag-pad-y) var(--tag-pad-x)` (3px 5px), `--radius`, `--fs-tag` (10.5px at a 16px root; criterion 33), `--fw-semibold`, `--lh-flat`, `white-space: nowrap`; icon 12px (`--icon-sm`), `aria-hidden`. The word is real text, so the tag needs no extra label.
- `Busy for …` and `Free for all …` can be long; `white-space: nowrap` stays, and the `.avail` grid gives the tag its own row below 600px so it never overflows at 320px.
- **Contrast at 10.5px/600** (text on its own soft background; f.md §9.5, both modes): ok 4.88 / 6.89, warn 5.43 / 7.61, note 5.48 / 6.51, plain 5.97 / 7.27, brand 6.52 / 5.85. All ≥ 4.5:1. The soft backgrounds are opaque tokens, so row hover (`--c-surface-2`) doesn't change the pair.
- `Waiting for email check` appears only in the admin (Django's own rendering of `get_status_display`, no tag) and never in the IT pages, since `unverified` is filtered out; the partial still maps it so any later debug view is correct.

### D.8 Emails (plain text)

Rules for all four:

- Plain text, no HTML part; short lines; no Markdown symbols except `-` list bullets.
- Sign-off `Polymath College IT desk`.
- Dates and times as in D.0 (`Mon 5 Oct 2026, 8:30 am to 11:30 am`).
- The emails don't include the HTML partials. The schedule sentence comes from `link_request.schedule_summary` (D22) as `When: …`; the class list is written in each `.txt`, so no tag reaches an email.
- `{…}` marks a value from the context. `[if …]` marks a conditional block (template `{% if %}`); it is not printed.
- Blank lines are exactly as shown.

#### 1. Confirm your email (to the requester)

Subject (pinned): `Confirm your Zoom link request`

```
Hello {requester_name},

You asked the Polymath College IT desk for a Zoom link. Please confirm it was you by opening this link:

{confirm_url}

The link works for {link_hours} hours. Check the details on the page, then choose "Confirm my request". IT won't see your request until you do.

Your request
Class: {class_name}
When: {schedule_summary}
Recording: {Yes, record it to the Zoom cloud | No}
Classes ({count}):
- Mon 5 Oct 2026, 8:30 am to 11:30 am
- Wed 7 Oct 2026, 8:30 am to 11:30 am

If you didn't ask for this, ignore this email. Nothing will be booked.

Polymath College IT desk
```

#### 2. New request (to IT)

Subject (pinned): `New Zoom link request {reference}: {class_name}`

```
A new Zoom link request is waiting for IT.

Reference: {reference}
Class: {class_name}
When: {schedule_summary}
Recording: {yes | no}
Classes ({count}):
- Mon 5 Oct 2026, 8:30 am to 11:30 am
- …

Requested by: {requester_name}
Email: {requester_email}
Phone: {requester_phone_display}
Notes: {notes | none}

Check which accounts are free, then approve or reject it:
{detail_url}

You get these emails because you're in the IT desk group on the Technology Management Desk.
```

`Recording: yes` / `Recording: no` is pinned (criterion 59). The phone uses `requester_phone_display` (D22). No host key.

#### 3. Link approved (to the requester only)

Subject (pinned): `Your Zoom link for {class_name}`

```
Hello {requester_name},

The IT desk has approved your request {reference}. Here is your Zoom link.

Join link: {join_url}
Meeting ID: {meeting_id}
Passcode: {passcode | none}

When: {schedule_summary}
Use the same link for every class below.

[if host_key]
Starting the class as host
Host key: {host_key}
To start the class as host, join, choose "Claim host" and type this host key. Keep it private: anyone who has it can take control of meetings on this Zoom account.
[else]
Ask the IT desk for the host key to start the class as host.
[end]

[if wants_recording]
You asked for this class to be recorded to the Zoom cloud.
[end]

Your classes ({count}):
- Mon 5 Oct 2026, 8:30 am to 11:30 am
- …

To change the times, send a new request. Please don't forward this email[if host_key], because it has the host key in it[end].

Polymath College IT desk
```

Pinned lines: the host-key sentence, the no-key sentence and the recording sentence (criteria 35, 61). The host key appears only in this template, only when non-empty.

#### 4. Not approved (to the requester)

Subject (pinned): `Your Zoom link request {reference} was not approved`

```
Hello {requester_name},

The IT desk couldn't approve your Zoom link request {reference} for {class_name}.

Their reason:
{rejection_reason}

If you can fix this, send a new request here:
{request_url}

Polymath College IT desk
```

### D.9 Accessibility and progressive enhancement

**Headings and landmarks**

| Page | Outline |
|---|---|
| Request form | h1 `Request a Zoom link`; sections are `<fieldset>`/`<legend>`, not headings |
| Check your email / confirmed / confirm non-ready | h1 only |
| Confirm ready | h1 → h2 `The classes ({n})` |
| Queue | h1 → h2 in the empty state only; the table has a caption |
| Detail | h1 → h2 per box (`Request`, `Classes (n)`, `Which accounts are free`, `Also waiting at overlapping times`, `Approve and send the link`, `Reject this request`) → h3 `Earlier requests from this person` |

Public pages: `header` (banner), `main#main`, `footer`. Shell pages: unchanged (`aside` > `nav` "Main", `header`, `main#main`, `footer`), plus `nav` "Breadcrumb", `nav` "Filter by status", `nav` "Pages", and `role="search"` on the queue search form. Each box is a `section` with `aria-labelledby` its h2.

**Labels, help and errors**

- Every control has a visible `<label for>`; groups use `<fieldset>` + `<legend>`.
- Help: `p.field__help#<name>-help`, above the control, referenced by `aria-describedby="<name>-help"`.
- On error: `aria-invalid="true"` and `aria-describedby="<name>-error <name>-help"` (error first, criterion 7); the error `p#<name>-error` has the `alert-circle` icon (`aria-hidden`) and the text. For fieldsets (`repeat`, `weekdays`, `host_account`) the `aria-describedby` goes on the `<fieldset>`, and `aria-invalid` on each input in the group.
- The checkbox `wants_recording`: label wraps the input; help referenced by `aria-describedby`.
- The honeypot is `hidden` + `aria-hidden="true"` and `tabindex="-1"`: not seen, not read, not focusable.

**Keyboard and focus**

- Tab order follows the visual order everywhere; no positive `tabindex`.
- Request form after a failed POST: with JS, focus moves to `[data-error-summary]` on load; without JS, the summary is the first thing in `main` after the h1, above the lead (criterion 54). The messages partial renders nothing on a failed POST, so nothing comes between them.
- Summary links jump to the field (`href="#id"`); the browser moves focus to the input.
- Detail after a failed approve / reject: JS focuses `[data-error-summary]` (the `approve_error` notice or the failing form's summary). The box sits below the fold, so this is what brings the user to it; without JS, the `approve_error` notice is at the top of `content`, and a form's summary is at the top of its box (a skip from the h1 by heading navigation).
- After a redirect (approve, reject, already decided): no scripted focus. The flash sits right after the h1 with `role="status"` / `alert`, so it is announced and is the next thing read. `main` keeps `tabindex="-1"` for the skip link.
- Confirm (POST) → confirmed: a new page, focus starts at the top as normal.
- Tabs, pager and sidebar are links: Enter activates, no arrow-key model.

**Targets (44px minimum)**

- `.input`, `.button`, `.choice`, `.check` rows, `.tabs__link`, `.pager a`: 44px by their existing rules.
- Links that stand alone in table cells, lists and `dd`s (`ZL-…` references, clash links, `mailto:`/`tel:`, the share link): `.tap-link` gives them a 44px block below 768px. At ≥768px they are inline text links in sentences or cells (WCAG 2.5.8 inline exception); breadcrumb links are exempt (criterion 54).
- Weekday checkboxes are whole 44px `.choice` rows, not bare 18px boxes.

**Status never by colour alone.** Every tag is icon + word (D.7). Notices have an icon and a title or sentence. The current tab has a bar and 600 weight; the current nav item has the bar (existing). Invalid fields have a 2px border, the icon and the words.

**Contrast.** Only existing token pairs are used; all are in f.md §9.5 (text ≥ 4.5:1, non-text ≥ 3:1, both modes). The only new pairs are the ported tag, notice and disc families, whose values f.md already lists.

**Reflow at 320px.** Public column padding 16px; forms one column below 600px; the queue table becomes cards below 768px; long values (`class_name`, email, URLs, the share link) use `overflow-wrap: anywhere`; tags wrap as whole units via `.tags` (flex-wrap).

**Motion.** None new. Showing/hiding the weekly group is instant.

#### Progressive enhancement

**Works with plain HTML and full page loads (JS off):**

- The request form: every field is visible, including the weekly group under the legend `If it's every week` (criterion 52); its help says `Tick every day the class happens.` and the repeat radio decides whether the server reads them.
- Submit, confirm (GET shows, POST confirms), confirmed.
- Queue tabs, search, `Clear the search`, pager: GET links and a GET form.
- Approve and reject: two ordinary POST forms.
- Flash messages stay in the flow (their close button is JS-only, already built).
- The colour-mode button stays hidden (existing behaviour).

**`app.js` adds (one block, bound to `data-*` only):**

1. **Weekly toggle** — for `[data-repeat]` radios and `[data-weekly-fields]`: on load and on `change`, if the checked radio's value is `once`, set `hidden` on the wrapper and `disabled` on every input inside it; if `weekly`, remove both. Disabled inputs aren't submitted, which matches the server ignoring them. Values typed before hiding stay in the DOM and come back when `Every week` is chosen again. No focus move (the radio keeps focus); no live announcement (the radio change is itself announced, and the group appears right after it in reading order).
2. **Error-summary focus** — on load, if `[data-error-summary]` exists, call `focus()` on it (it has `tabindex="-1"`) and scroll it into view. Only the first match.

Nothing else is new in JS: no copy-link button, no confirm dialogs, no inline validation, no async requests. Hence no loading states anywhere in this brief.

**Needs JS (the complete list):** hiding the weekly fields; focusing the error summary; the colour-mode button and the flash close button (both existing).

#### Contract gaps and copy proposals (for the main session)

- **G1. Phone display form.** Criterion 26 wants `+94 77 123 4567` on the detail page (and the design shows it on confirm and in the queue). Nothing in the contract formats E.164 for display, and formatting is a rule, not presentation. Ask the backend for a model property, e.g. `LinkRequest.requester_phone_display` (`+94 77 123 4567` for `+94` numbers; other countries: `+` then the digits, unchanged). Until it exists, pages show the stored E.164 value.
- **G2. First overlap in "also waiting".** Criterion 29 says each item shows the "first overlap"; the contract gives `overlapping_waiting` items only `first_start` (the other request's first class). Ask for an annotated `first_overlap` (aware datetime: the earliest start among the other request's occurrences that overlap this one).
- **G3. Error-summary partial parameters and plural.** `error_summary.html` takes only `form`, but the detail page needs different lead words for the approve and reject forms. Proposal: `with form=… lead="We couldn't send this yet." only`, the partial appending `{n} thing(s) need your attention.`. Copy proposal (needs the planner's OK, since it's pinned): print `1 thing needs your attention.` / `{n} things need your attention.` instead of the literal `thing(s)`.
- **G4. Busy count.** `Busy for {k} of {n} classes` must count this request's classes that clash, not clash pairs. The contract's `clashes` list is per pair, so one class clashing with two bookings would count twice. Ask for `busy_count` (int) in each `availability` entry, or confirm that `clashes` holds one entry per occurrence.
- **G5. Schedule sentence.** Closed by D22: `schedule_summary` is the one source; `schedule.html` takes `summary`, and the emails print `When: {schedule_summary}`.
- **G6. Paid-account count.** The availability lead `{free_count} of {m} paid accounts…` uses `availability|length`; no new variable is needed. Listed only so the backend knows `availability` must include busy accounts too (it does, per criterion 28).
- **G7. Reply-time promise.** Closed by D23 (owner: "No time promise"): the clause is removed; no page or email in this section promises when IT will reply.

## Implementation notes
<!-- owners: tmd-devops, tmd-django-backend, tmd-frontend — one sub-heading each: files changed, contract deviations, migrations, new deps (with reason), self-check output -->

### tmd-devops (step 1b)

**Files changed**

- `requirements/base.txt`: adds `cryptography==50.0.1` under the comment `# Fernet: encrypts Zoom host keys at rest (brief 005, D17)` (criterion 66). It brings `cffi` 2.1.1 and `pycparser` 3.0. Both images installed it from manylinux wheels (`cryptography-50.0.1-cp311-abi3-manylinux_2_34_x86_64.whl`, `cffi-2.1.1-cp313-…manylinux2014…whl`). No compiler and no Dockerfile change were needed, and the runtime stage is unchanged.
- `config/settings/base.py`:
  - The Email block moved here from `prod.py`: `EMAIL_BACKEND` (default SMTP), `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` and `DEFAULT_FROM_EMAIL`, with the same defaults as before.
  - New Zoom block: `ZOOM_PROVIDER` (env, default `manual`), the constants `ZOOM_CONFIRM_LINK_HOURS = 24`, `ZOOM_REQUEST_LIMIT_PER_EMAIL_PER_HOUR = 5` and `ZOOM_REQUEST_LIMIT_PER_IP_PER_HOUR = 20`, `TRUSTED_PROXY_COUNT` (env int, default 0), and `HOST_KEY_ENCRYPTION_KEYS` (env list, default `[]` so that `collectstatic` at image build time and `zoom.E003` can report it, rather than an import-time crash).
  - To meet "prod.py no longer calls `env(`" (criterion 49), `CSRF_TRUSTED_ORIGINS`, `USE_HTTPS` and `SECURE_HSTS_SECONDS` are now read here too. Their defaults are unchanged. HSTS is only sent on HTTPS responses, so plain-HTTP dev isn't affected.
- `config/settings/prod.py`: no `env(` calls and no `env` import. It imports `ALLOWED_HOSTS` and `USE_HTTPS` from base. Before, `env.list("ALLOWED_HOSTS")` had no default, so a missing value failed at start-up. That guarantee is kept with an explicit `ImproperlyConfigured("Set ALLOWED_HOSTS for production.")` when the list is empty, because `/healthz/` skips host validation and would otherwise report healthy while every page returns 400. The email lines were removed; SMTP stays the default through base.
- `config/settings/test.py`:
  - `os.environ.setdefault("HOST_KEY_ENCRYPTION_KEYS", "dGVzdC1vbmx5LWZlcm5ldC1rZXktbm90LXNlY3JldCE=")`, which is base64 of `test-only-fernet-key-not-secret!` and a valid Fernet key;
  - `ZOOM_PROVIDER = "fake"`;
  - `TRUSTED_PROXY_COUNT = 0`.

  Like `SECRET_KEY`, the fake key is a `setdefault`, so inside the container, where compose passes the real env key, tests use that one. Either key works, and tests never depend on which.
- `config/settings/dev.py`: unchanged. It keeps the console `EMAIL_BACKEND` as a constant. It still calls `env(` for `DEBUG` and `ALLOWED_HOSTS` (pre-existing and not in criterion 49's scope). This is flagged for the reviewer; I didn't change it.
- `compose.yaml` `web.environment`:
  - `EMAIL_BACKEND` (`:-…smtp.EmailBackend`), `EMAIL_HOST` (`:-localhost`), `EMAIL_PORT` (`:-587`), `EMAIL_HOST_USER` (`:-`), `EMAIL_HOST_PASSWORD` (`:-`), `EMAIL_USE_TLS` (`:-True`), `DEFAULT_FROM_EMAIL` (`:-tmd@localhost`);
  - `ZOOM_PROVIDER` (`:-manual`), `TRUSTED_PROXY_COUNT` (`:-0`);
  - `HOST_KEY_ENCRYPTION_KEYS` in the required form, `${HOST_KEY_ENCRYPTION_KEYS:?Set HOST_KEY_ENCRYPTION_KEYS in .env}`.

  `compose.dev.yaml` is unchanged; it inherits these.
- `.env.example`: a new Email section (SMTP default, and the console backend for local prod-image runs), and a Zoom section with `ZOOM_PROVIDER=fake` (dev), `TRUSTED_PROXY_COUNT=0` (and 1 behind the TLS proxy), and `HOST_KEY_ENCRYPTION_KEYS=change-me-generate-a-fernet-key`. The Zoom section also carries the generation one-liner, the rotation steps and the "losing every key" warning. The commented email lines under Production were replaced by the real section.
- `.env` (local, git-ignored, not committed): I appended `EMAIL_BACKEND=…console.EmailBackend`, `ZOOM_PROVIDER=fake`, `TRUSTED_PROXY_COUNT=0` and a freshly generated `HOST_KEY_ENCRYPTION_KEYS` (44 characters, URL-safe base64, no `$`). The key was generated with `os.urandom(32)`, which is equivalent to `Fernet.generate_key()`, and it was never printed.

**Not done here (ownership)**

- **`apps.zoom` in `LOCAL_APPS`:** not added, because the package doesn't exist yet and adding it would break every command. `tmd-django-backend` adds the line in the same change that creates `apps/zoom` (step 2a), as the Agent plan allows.
- **`zoom.E001`, `E002` and `E003`:** these live in `apps/zoom/checks.py` (MVT plan → Checks), so they belong to `tmd-django-backend`. The settings they read are in place.
- **For the backend:** `collectstatic` in the prod image build runs with no `HOST_KEY_ENCRYPTION_KEYS`. It only runs the `staticfiles` check tag, so `E003` won't break the build as long as `E003` stays an untagged normal check, and `crypto.py` doesn't build the `MultiFernet` at import time.

**New env vars (with defaults):** `ZOOM_PROVIDER=manual`, `TRUSTED_PROXY_COUNT=0`, `HOST_KEY_ENCRYPTION_KEYS` (required in compose; `[]` in Django). Moved into `base.py`: `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST=localhost`, `EMAIL_PORT=587`, `EMAIL_HOST_USER=""`, `EMAIL_HOST_PASSWORD=""`, `EMAIL_USE_TLS=True`, `DEFAULT_FROM_EMAIL=tmd@localhost`, and also `CSRF_TRUSTED_ORIGINS`, `USE_HTTPS` and `SECURE_HSTS_SECONDS`, whose names and defaults are unchanged.

**Dependency changes:** `cryptography==50.0.1` (runtime), plus its dependencies `cffi==2.1.1` and `pycparser==3.0`.

**Operational steps for the user**

- Every `.env`, including production, now needs `HOST_KEY_ENCRYPTION_KEYS`, or `docker compose` refuses to start. Generate it with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` and back it up.
- In production, set `ZOOM_PROVIDER=manual`, `TRUSTED_PROXY_COUNT=1` (behind the TLS proxy), and the real `EMAIL_*` and `DEFAULT_FROM_EMAIL`.
- Rebuild both images (`docker compose … up -d --build`).
- A host `.venv` needs `.venv\Scripts\pip install -r requirements/dev.txt` to pick up `cryptography`.

**Self-check output (2026-09-25)**

- `docker compose config --quiet` and `docker compose -f compose.yaml -f compose.dev.yaml config --quiet` both passed. `HOST_KEY_ENCRYPTION_KEYS= docker compose config --quiet` → `required variable HOST_KEY_ENCRYPTION_KEYS is missing a value: Set HOST_KEY_ENCRYPTION_KEYS in .env`, exit 1.
- Dev image rebuilt: `Successfully installed … cffi-2.1.1 cryptography-50.0.1 …`, `Image polymath-tmd:dev Built`.
- In the dev container:
  - `ruff check .` → `All checks passed!`; `ruff format --check .` → `43 files already formatted`;
  - `pytest --create-db` → `83 passed in 5.02s`;
  - `manage.py check` → `System check identified no issues (0 silenced).`;
  - `makemigrations --check --dry-run` → `No changes detected`.
- The settings load under `dev` and `test`, and a `MultiFernet` round-trip works: `config.settings.dev keys: 1 valid; provider: fake proxies: 0 email: …console.EmailBackend` and `config.settings.test keys: 1 valid; provider: fake proxies: 0 email: …locmem.EmailBackend`.
- Prod image rebuilt (`collectstatic` passed), `Image polymath-tmd:latest Built`. `web` reached `healthy`, and `cryptography 50.0.1` imports in the prod container. `GET http://127.0.0.1:8010/accounts/login/` → 200.
- `docker compose exec -e USE_HTTPS=True -e ZOOM_PROVIDER=manual web python manage.py check --deploy` → only `security.W021` (accepted), `1 issue`, exit 0.
- Docker is left as I found it: the dev stack is running again (`polymath-tmd-web-1` on `polymath-tmd:dev`, 8010; `polymath-tmd-db-1` healthy), and `manage.py check` passes there. No other project's containers were touched.

**README facts for `tmd-docs-writer`:** the new env vars above, the key generation, rotation and backup, `ZOOM_PROVIDER` values, `TRUSTED_PROXY_COUNT=1` behind the proxy, the fact that `EMAIL_*` now reaches the container, and the host `.venv` reinstall.

**Review fixes (round 1):** this fixes the blocker "nothing stops the fake provider in production".

- **The guard:** `config/settings/prod.py` now imports `ZOOM_PROVIDER` from base and raises `ImproperlyConfigured("The fake Zoom provider can't run in production. Set ZOOM_PROVIDER=manual.")` when it is `fake`. The guard sits next to the `ALLOWED_HOSTS` guard. `zoom.E001` is unchanged, and `dev.py` and `test.py` still allow `fake`: the dev container reports `fake`.
- **`.env.example`:** now defaults to `ZOOM_PROVIDER=manual`, with `fake` shown in a comment for dev-only files.
- **Local `.env`:** left as it is (`fake`). A local run of the prod stack therefore needs `ZOOM_PROVIDER=manual`, either set in the shell, which overrides `.env` interpolation (`ZOOM_PROVIDER=manual docker compose up -d`), or temporarily in `.env`, as criterion 57 already says.

**Proof, on the rebuilt prod image:**

- With `-e ZOOM_PROVIDER=fake`, the default gunicorn command fails with `django.core.exceptions.ImproperlyConfigured: The fake Zoom provider can't run in production. Set ZOOM_PROVIDER=manual.` (exit 1), and `manage.py check` also exits 1.
- With `-e ZOOM_PROVIDER=manual`, `manage.py check` → `System check identified no issues (0 silenced).` (exit 0).
- The full prod stack with `ZOOM_PROVIDER=manual` → `web` is `healthy`, and `/accounts/login/` returns 200 on 8010.
- `check --deploy` with `USE_HTTPS=True` → only `security.W021`.
- In the dev container, `ruff check`, `ruff format --check` and `manage.py check` are clean.
- The dev stack is restored and running.

### tmd-django-backend (step 2a)

**Files changed**

- `apps/zoom/` (new app, label `zoom`, namespace `zoom`):
  - `apps.py`: `ZoomConfig`. `ready()` registers the checks explicitly.
  - `models.py`:
    - `HostAccount`, with `set_host_key` / `get_host_key` / `has_host_key` / `rotate_host_key`, and a `__repr__` that never shows the key;
    - `LinkRequest`, with `clean()` covering criterion 6, `class_count`, `occurrence_dates`, `occurrence_times`, `schedule_summary`, `requester_phone_display`, `reference`, `weekday_names`, `has_started`, `can_be_decided`, `create_occurrences`, and `mark_verified` / `reject` (both are conditional UPDATEs, so they're race-safe);
    - `Occurrence` (with `overlaps`) and `HostSlot` (with `covering()`, which refuses unaligned times);
    - the QuerySets `bookable`, `availability_for(lock=)`, `visible_to_it`, `waiting`, `with_schedule`, `for_tab`, `tab_counts`, `search`, `recent_from`, `overlapping_waiting` (sets `first_overlap`), `earlier_from_same_requester`, `booked` and `overlapping`;
    - the pinned error copy as constants.
  - `validators.py`: `normalise_phone`, `format_phone` and `validate_host_key`.
  - `crypto.py`: the only module that imports `cryptography`. `encrypt` / `decrypt` / `rotate` / `keys_are_valid`, and `HostKeyUnreadable`. It builds the `MultiFernet` on every call, never at import.
  - `providers.py`: `Meeting`, `ProviderError`, `FakeProvider` (with class-level `calls` / `next_error` / `reset()` for tests), `ManualProvider`, `PROVIDERS` and `get_provider()`.
  - `services.py`:
    - `approve()`, which follows D5's order: lock the request, lock the account, decrypt the key, run a locking re-check, then write the occurrences and slots, call the provider and save. It maps MySQL 1062, 1213 and 1205 to `conflict`.
    - `confirm_token`, `confirm_state` and `confirmed_link_request`;
    - `client_ip` and `is_throttled`;
    - the four email senders, which log only the reference and the exception class on failure.
  - `checks.py`: `zoom.E001` (deploy tag), `zoom.E002` and `zoom.E003` (untagged, so `collectstatic` isn't blocked).
  - `forms.py`: `LinkRequestForm` (a `ModelForm` with the honeypot, weekday checkboxes, and labels, help and error copy from D.2), `ApproveForm` (with manual fields when the provider needs them; see "Contract notes") and `RejectForm`.
  - `views.py`: the CBVs from the URLs table. `ApproveView` is `non_atomic_requests`, so that `approve()` owns the outermost transaction: a MySQL deadlock rolls back the whole transaction, and the page must still re-render afterwards.
  - `urls.py`: the eight named routes.
  - `admin.py`: `HostAccountAdmin`, where the key form and field are given only to users with `zoom.change_hostaccount`, and the changelist column is `Host key` → `Saved` / `Not saved`. `LinkRequestAdmin` is view-and-delete, with a read-only `Occurrence` inline.
  - `management/commands/rotate_host_keys.py`: prints `Re-encrypted N host keys.`; unreadable keys are listed by label on stderr.
  - `migrations/0001_initial.py` (generated) and `0002_it_desk_group.py`.
  - `tests/`: `conftest.py`, `test_models.py`, `test_services.py`, `test_views.py`, `test_admin.py` and `test_race.py`. See "Self-check" below.
- `templates/zoom/email/*.txt` (8 files: a subject and a body for each of the four emails). The brief gives the email context to the backend, and the copy is D.8's, verbatim, with the `When: {schedule_summary}` line that criterion 5 adds to the confirm, IT and approval emails. Each starts with a `{# … #}` header, and subjects keep it on the same line. They use `{% autoescape off %}`. A class line prints `{{ occurrence }}` (`Occurrence.__str__` = `Mon 5 Oct 2026, 8:30 am to 11:30 am`), so there's one format source.
- `config/settings/base.py`: `"apps.zoom"` added to `LOCAL_APPS` in this change, as the Agent plan allows (1b left it to me).
- `config/urls.py`: `path("zoom/", include("apps.zoom.urls"))`.

**Not done here: for `tmd-frontend`**

- **`base.html` `perms` line.** `templates/**` belongs to the frontend under my agent definition, so I didn't edit it. `grep perms=perms templates/base.html` → 0 matches at the time of writing. The sidebar include needs `… user=user perms=perms only`.
- **The page templates** `zoom/*.html`, `public_base.html` and the partials don't exist yet. My view tests use locmem stubs (see "Tests") so they don't depend on them.

**Context contract, as implemented.** Every name in the contract is supplied. The D22 additions and small extras:

- **`LinkRequest.schedule_summary`** (str, G5): `Every Monday and Wednesday, 8:30 am to 11:30 am, from Mon 5 Oct to Wed 28 Oct 2026 (8 classes)` / `Once, on Mon 5 Oct 2026, 8:30 am to 11:30 am`.
  - The first date drops its year only when it's the same year as the last. `(1 class)` is singular.
  - The dates are the first and last **actual** classes, not the typed first and last dates.
- **`LinkRequest.requester_phone_display`** (str, G1): `+94 77 123 4567`. Non-`+94` numbers are unchanged.
- **`overlapping_waiting`** (G2): each item is a `LinkRequest` annotated with `first_start` and `occurrence_count`, **plus `first_overlap`** (an aware datetime: the earliest of that request's classes that overlaps this one). The list is ordered by `first_overlap`.
- **`availability`** (G4): each dict also has **`busy_count`** (int, the number of this request's classes with at least one clash). `clashes` stays one entry per clash pair, so a class that clashes with two bookings counts once in `busy_count` and has two clash rows. Tested with exactly that case.
- **`Occurrence.__str__`** is the class line `Mon 5 Oct 2026, 8:30 am to 11:30 am`, in local time. `occurrence_list.html` may use `{{ occurrence }}` or format it itself.
- **The approve form radios.** `approve_form.host_account` lists only the free accounts, and the first is pre-selected. Each choice's value is a `ModelChoiceIteratorValue`, so `{% for radio in approve_form.host_account %}` → `radio.data.value.instance` is the `HostAccount` (for `email` and `has_host_key`), and `radio.data.label` is `"{label} ({email})"`. Validation accepts any **bookable** account, so a busy pick reaches the service's locked re-check and gets the specific "booked a moment ago" 409 (criterion 37). Unpaid, inactive or unknown accounts get the form error `Choose one of the free accounts listed.` with 409.
- **Form copy.** Labels, help text and field widget attributes (`type`, `step="300"`, `autocomplete`, `inputmode`, `data-repeat` on each repeat radio) are on the form fields, so `field.label` / `field.help_text` can be used. The approve and reject field errors are D.5's exact strings. Non-pinned strings I chose:
  - `Choose the date of the class.` (date missing or unparsable);
  - `Type the time the class starts, like 8:30 am.` / `…ends, like 11:30 am.` (time missing or unparsable).
- **Honeypot.** It renders with Django's default id `id_website` unless the template writes the input by hand, as D.2's markup (`id="website"`) implies.
- **`ConfirmView`.** `occurrence_count` is also filled for `already`. `occurrences` is empty unless `ready`, as the contract says.
- **`RejectView` on error.** It rebuilds the approve form with any `host_account` / `join_url` / `meeting_id` / `passcode` values posted along with the reject form (criterion 43). If the template keeps the two forms separate, nothing was typed to keep, and the approve form is fresh.
- **Messages.** One message isn't pinned: when the rejection email fails, a warning `Not approved, but the email to {email} didn't send. Tell them the reason yourself.`

**Contract deviations.** None.

**Migrations**

- `zoom/0001_initial`: 4 models, 2 named indexes on `LinkRequest`, 1 on `Occurrence` (`host_account`, `starts_at`), 5 `CHECK` constraints (criterion 45) and the unique `zoom_one_booking_per_account_slot`.
- `zoom/0002_it_desk_group`: calls `create_permissions` for `zoom` first, then `get_or_create`s `IT desk` with exactly `zoom.review_linkrequest`. Reverse deletes the group. Applied cleanly to the dev DB.

**Dependencies and settings.** No new dependency beyond 1b's `cryptography`. I added no settings, only the `LOCAL_APPS` entry. Checks read `ZOOM_PROVIDER` and `HOST_KEY_ENCRYPTION_KEYS` through `settings` only.

**Decisions worth the reviewer's eye**

- **Locking.** `availability_for(lock=True)` makes both of its reads `SELECT … FOR UPDATE`. That includes the joined `LinkRequest` rows, whose status the clash rule reads, so the re-check can't see a stale snapshot.
- **Exceptions.** The service catches `IntegrityError` only for MySQL 1062 (the slot backstop) and `OperationalError` only for 1213 / 1205. Anything else still raises, so a `CHECK` violation isn't disguised as a clash.
- **Race tests.** These don't use `transaction=True`. Its teardown flush would delete the `IT desk` group created by the data migration, and later `--reuse-db` runs would fail the group test. Instead they unblock the DB with `django_db_blocker`, commit their own rows, and delete exactly those rows afterwards. Each thread closes its connection.
- **IT emails.** The IT new-request email is sent as **one message per recipient**, so staff addresses aren't disclosed to each other. Criterion 14's "one email to every active user" is met per user.
- **Time.** Tests freeze time by patching `django.utils.timezone.now` (no `time-machine`). The confirm-token expiry test shifts `TimestampSigner.timestamp` back by 25 hours while making the token.

**Self-check output** (dev container, 2026-09-25)

- `ruff format --check .` → `65 files already formatted`; `ruff check .` → `All checks passed!`
- `pytest --create-db` → `267 passed` (the zoom app adds 184). Then 5 more runs on the reused DB → `267 passed` each time.
  - An earlier flaky assertion was fixed: it compared a freshly made signed token with one made a second earlier, and tokens carry a timestamp.
  - The race tests (38b, 38c) were also run 6 times on their own, and passed every time.
- `python manage.py makemigrations --check --dry-run` → `No changes detected`.
- `python manage.py check` → `System check identified no issues (0 silenced).`
- Not run by me: `check --deploy` on the prod stack and the HTTP walk-through (criteria 56–57). Those are the verifier's, once the templates exist. `zoom.E001`'s deploy tagging is covered by `checks.run_checks(include_deployment_checks=True)` in `test_services.py`.
- **Tests.** The zoom view tests swap `zoom/*.html` for tiny locmem stubs (in `apps/zoom/tests/conftest.py`), so they pin status codes, redirects, permissions, emails and context keys whatever the markup. The real email `.txt` templates are used. Rendered-page checks (criteria 1–3, 7, 12's HTML escaping, 19, 21, 26–33, 51–54, and 61's page sweep) are for `tmd-frontend` and the verifier.
- The dev stack was reused and left running (`polymath-tmd-web-1`, `polymath-tmd-db-1`). Nothing was committed.

#### Review fixes (round 1)

**SF1: secrets are masked in error reports.**

- `services._approve_once` has `@sensitive_variables("host_key")`.
- `services.send_approved_email` has `("host_key", "context")`, and `services._send` has `("context", "body")`, because the email context holds the key.
- `HostAccount.set_host_key` has `("plain")`. It's applied directly, not through `method_decorator`: a test showed that `method_decorator`'s wrapper frame exposes the positional args (`('8421973',)`).
- In `crypto`: `encrypt` has `("plain")`, `decrypt` / `rotate` have `("token")`, and `_cipher` / `keys_are_valid` / `_clean_keys` mask the encryption-key locals. The `HOST_KEY_ENCRYPTION_KEYS` setting is already hidden by Django's `KEY` pattern.
- `HostAccountAdmin.changeform_view` has `@method_decorator(sensitive_post_parameters("host_key"))`.
- `apps/zoom/tests/test_review_fixes.py` builds `ExceptionReporter`s for three cases, and asserts the key is masked in the frame vars and absent from both the HTML and text reports:
  - an exception after decryption inside `approve()`;
  - an admin change-form POST with a typed `host_key` that fails (the request is caught through `got_request_exception`);
  - an exception inside `set_host_key` / `encrypt`.

**SF2: lock races get their own message and one retry.**

- `approve()` is now a retry loop around `_approve_once()`. MySQL 1213 (deadlock) is retried once; MySQL has already rolled the attempt back, which is why the approve view stays `non_atomic_requests`.
- A second 1213, or a 1205 lock-wait timeout (not retried), returns `conflict` with `Someone else was approving at the same moment. Nothing was booked. Try again.` That's still a 409 in the view, and still the "conflict" outcome for criterion 38b.
- 1062 (the slot backstop) keeps `{label} was booked … a moment ago`.
- Tests:
  - retry succeeds (the first `bulk_create` deadlocks, the second is real → approved, 36 slots, one provider call);
  - retry fails (two calls → the new message, still waiting, no provider call);
  - 1205 isn't retried (one call);
  - 1062 gives the clash text.
- `test_a_lock_wait_timeout_is_not_retried` failed while I was mid-change. It caught a real bug: 1205 fell through to a second attempt. That's fixed, and the test passes.

**SF3 (my half): `apps/zoom/templatetags/zoom_format.py`.**

- The filters are `class_date` (`Mon 5 Oct 2026`) and `class_time` (`8:30 am`), with `expects_localtime`.
- They call `apps.zoom.models.class_date` / `class_time`, which are the former `_date_text` / `_time_text`, renamed public because they are now shared.
- The helpers convert aware datetimes to Colombo time themselves, so `schedule_summary`, `Occurrence.__str__`, the emails and the templates share one definition.
- Tested: filter output equals the Python helpers and `str(occurrence)`, and the UTC→Colombo conversion.

**Coordinator follow-up.** `services.STARTED` is removed. `approve()` returns `Outcome.STARTED` with no message, and the pinned "already started" sentence now exists only in `detail.html`, chosen by `has_started`.

**Nits**

- `forms._BookableAccountField` is removed. Its explanation moved to the `ApproveForm` docstring (the radios come from `offer()`, validation uses `bookable()`).
- The unused `format=` arguments on the date and time widgets are removed.
- **Join link.** A backslash is refused outright, then `URLValidator(schemes=["https"])` runs, then the zoom.us host check. Tested with 7 links, including `https://evil.example\.zoom.us/…`, `…\@us02web.zoom.us/…`, `zoom.us.evil.example`, `http://` and an embedded space.
- **Migration 0002** is **edited in place**. It now uses an explicit `ContentType` / `Permission` `get_or_create` and no `models_module` trick. Why in place rather than a new migration:
  - it isn't released, and no production DB has it;
  - on DBs where it's already applied (dev, the verifier's), the old and new versions produced identical rows, so there's nothing to reconcile;
  - a new migration would leave the trick in history for no benefit.

  The idempotence and reversal test still passes, and `--create-db` applies it fresh.
- **Throttle race.** The count-then-insert race is documented in `services.is_throttled`: at most one extra request per concurrent submit, accepted for an abuse brake.
- **DST caveat.** The nonexistent-time caveat is documented in `LinkRequest.occurrence_times`. Colombo has no DST; if `TIME_ZONE` ever changes, `clean()` must reject gap times.
- **Recorded decision: emails send inside the request.**
  - The confirm and reject emails are sent synchronously, inside the request's `ATOMIC_REQUESTS` transaction.
  - The approval email is sent after `approve()`'s own transaction has committed, because that view is non-atomic.
  - This is deliberate, so IT sees success or failure in the same response. A send failure is caught, logged and reported, and never undoes the decision (D9).
  - The accepted edge: if the final commit of a confirm or reject request failed after sending, an email would describe a change that didn't persist.
- **Not changed, for the owner to decide:** the reviewer's nit that `it_new_body.txt` should print `requester_phone_display`. D.8 explicitly specifies the stored E.164 value for IT ("it dials from a phone's mail app"), and the coordinator didn't assign it. It's a one-line change if the designer agrees.

**Self-check (2026-09-25, dev container)**

- `ruff format --check .` → `70 files already formatted`; `ruff check .` → `All checks passed!`
- `pytest --create-db` → `308 passed`. Three reruns on the reused DB → `308 passed` each time. `test_race.py` on its own, 4 runs → `2 passed` each time.
- `makemigrations --check --dry-run` → `No changes detected`; `manage.py check` → `System check identified no issues (0 silenced).`
- Page templates were not edited. The dev stack was left running. Nothing was committed.

### tmd-frontend (step 2b)

**Files changed**

- **New templates:**
  - `templates/public_base.html` (the public frame, D1);
  - `templates/partials/crumb.html`;
  - `templates/zoom/request_form.html`, `request_sent.html`, `confirm.html`, `confirmed.html`, `queue.html`, `detail.html`;
  - `templates/zoom/partials/status_tag.html`, `schedule.html` (takes `summary`, as the contract says), `occurrence_list.html`, `error_summary.html` (`form` + `lead`, D21), `field.html`, `confirm_heading.html`.
- **Changed templates:**
  - `templates/base.html`: passes `perms=perms` into the sidebar, and the header comment is updated.
  - `templates/partials/sidebar.html`: the `Zoom links` group (`id="nav-zoom"`, `Link requests` → `zoom:queue`, `video` icon), between Menu and Administration, shown only when `perms.zoom.review_linkrequest`. It gets `aria-current` when `current_ns == "zoom"`.
  - `templates/partials/icons.html`: adds the ten Feather symbols `chevron-left`, `chevron-right`, `video`, `film`, `alert-circle`, `clock`, `mail`, `x-circle`, `key` and `inbox`. Every one is used.
- **Not touched:** the email `.txt` templates, which the backend built.
- **`static/css/style.css`:**
  - **1a:** the palette entries the port needs: grey-100/750, crest-100, green/amber/blue 50 and 900, and the four `--alpha-*-line` pairs.
  - **1b:** `--fs-tag` (0.65625rem), `--fs-error`, `--lh-flat`, `--tag-pad-y/x`, `--error-gap`, `--icon-nudge`, `--textarea-pad-y`, `--tab-h`, `--form-w`, `--field-narrow`, `--textarea-min`, `--measure`, `--disc-lg`, `--row-label-w`, `--facts-dt-min/max`, `--icon-sm`, `--icon-inline` (14px, for the error icon and the crumb separator) and `--icon-disc`.
  - **1c and 1d:** `--c-ok/warn/note-soft` and `-line`, `--c-plain-text/soft` and `--c-brand-text/soft`, in both modes.
  - **2:** `textarea` inherits the font, and `h3`/`dl`/`dd` margins are reset.
  - **4c:** `.crumbs__sep`.
  - **5e:** `textarea.input`, `.input--narrow`, `.field__error`, `.field-pair`, `.options` (+ `__list--two/--four/--stack`, `--group`), `.choice--tall`, `.choice__words`, `.choice__help`, `.check` (+ `__help`), `.searchbox`, `.form-actions` and `.formsection`.
  - **5f:** `.notice--ok/--warn/--note`, `.notice__body`, `.notice__strong`, `.notice ul`/`a`, and `scroll-margin-top` so a focused summary clears the top bar.
  - **New 5g–5p:** `.tag` + `.tags`, `.tabs`, `.finder__search` and `.result-line`, `.datagrid`, `.empty` and `.disc`, `.facts`/`.facts-cols`, `.pager`, `.worklist`, `.avail`, `.occurrences`, the box parts (`__lead`, `__section`, `__subtitle`, `__form`), and the helpers `.text-muted`, `.break-anywhere` and `.stack`.
  - **7a/7b:** `.signin__brandline` is grouped with `.public__brand`, and the mode button rule is shared. New `.public*` rules.
  - **8:** a new `min-width: 768px` block (`.occurrences--cols`); below 768: `.tap-link`, the datagrid cards, one-column facts, and the public frame without its card; below 600: stacked form grids, full-width buttons, 2×2 tabs, stacked facts and a one-column `.avail`; below 360: public padding.
- **`static/js/app.js`:** block 9 has (a) the weekly toggle on `[data-repeat]` / `[data-weekly-fields]`, which sets `hidden` and `disabled` on each input, and (b) focus on the first `[data-error-summary]`.

**Spec deviations**

- **Link lifetime copy (criterion 67 vs D.3):** criterion 67 bans the word `hours` on `request_sent`, but D.3's copy is `The link works for {link_hours} hours.` The page now says `The link works for one day.` when `link_hours == 24`, and only falls back to `{n} hours` if the setting ever changes. `request_sent` and `confirmed` also add the D23 line (IT will email once they've looked at the request). The form lead ends at `…the Zoom link.`
- **Extra public-frame blocks:** besides `title`, `heading` and `content`, `public_base.html` has `heading_class` and `above_heading`. These serve the centred disc and title on "Check your email" and "Request confirmed" (public-frame.md `.public__title--centre` / `.public__disc`).
- **`zoom/partials/confirm_heading.html`:** added so that the confirm page's `<title>` and `h1` come from one source for its four states.
- **`zoom/partials/field.html`:** it hand-renders the input with the widget's own attrs (`type`, `step`, `maxlength`, `autocomplete`, `inputmode`…). The ids are Django's `id_<name>`, and the help and error ids are `<name>-help` / `<name>-error`. The optional parameters are `min`, `max` and `narrow` (the contract's `type` isn't needed).
- **Class list columns:** the two-column class list starts at 768px on both the confirm page and the detail page. D.3 said 600px for confirm; the 640px column is too narrow for two columns there.
- **Error summary:** it lists the first error per field, so the count matches the items. Its links get `.tap-link`, making them 44px tall below 768px.
- **Singular counts:** `Free for all {n} class(es)` pluralises (`class` when n = 1). With n = 8 it reads exactly as pinned.

**Context contract gaps:** none blocking. One copy mismatch for the backend or main session to decide: `templates/zoom/email/confirm_body.txt` says `The link works for {{ link_hours }} hours.`, which breaks criterion 67 (no `hours` in the confirm email). I didn't edit it.

**Self-check output (2026-09-25, dev stack)**

- `pytest --create-db` in `web`: `281 passed in 12.41s` (includes the static-reference, header-comment, `only`, inline-style, hard-coded-path, sprite and CSS-token guards).
- **Dev data seeded for the checks:** an IT desk user `it.check`; host accounts `Zoom 01/02/03` (paid; 01 and 02 with the dummy key `123456`) and `Zoom free` (unpaid); and requests ZL-0019…0027 (clash, approved, rejected, nothing-free). It stays in the dev DB.
- **Playwright** (scratchpad `check.js`, Chromium headless):
  - Every page returned 200: the form, sent, confirm ready/already/invalid, confirmed, the queue (Waiting, All, no match) and the detail (clash, nothing free, approved, rejected). An invalid POST returns 200, and a valid POST lands on `/zoom/request/sent/`.
  - Titles: `Request a Zoom link · Polymath TMD`, `Confirm your request · …`, `ZL-0020: CCC Batch 3 - Mathematics · …`.
  - Every page has one `h1`, with no horizontal overflow at 1440, 400 or 320 (form) and none in dark mode. There were no console errors.
  - **Weekly toggle:** with `once`, the group is hidden and all inputs are disabled; with `weekly`, it is shown and enabled.
  - After a failed form POST and a failed reject POST, `document.activeElement` is the error summary.
  - `.tag` computed font-size is `10.5px`.
  - Below 768px, no link, button or choice label is under 44px. At 1440 the only small links are inline text links (`mailto:`/`tel:`, references in lists, the share link, clash links), which the design exempts at ≥768px.
- **Screenshots** in the scratchpad `shots/`:
  - `request-form-{1440,400,320}`, `request-form-errors-{1440,400}`, `request-sent-*`, `confirm-ready-*`, `confirmed-*`, `confirm-already-400`, `confirm-invalid-400`;
  - `queue-waiting-{1440,400}` and `queue-waiting-dark-{1440,400}`, `queue-no-match-1440`, `queue-all-1440`;
  - `detail-clash-{1440,400}`, `detail-clash-dark-1440`, `detail-reject-error-1440`, `detail-none-free-1440`, `detail-approved-1440`, `detail-rejected-400`.
- **Not checked by me:**
  - the manual-provider approve fields (dev runs `ZOOM_PROVIDER=fake`, so the note and the three fields didn't render);
  - the `expired` confirm state (it needs a token older than 24 hours);
  - the prod-image run (criterion 57 is the verifier's).

#### Review fixes (round 1), tmd-frontend

- **SF3 (dates in one place):** `templates/zoom/**` no longer has any inline `|date:"D j M Y"` or `|time:"g:i A"|lower`. The ISO `|date:'c'` stays only in `<time datetime>` attributes. Formats now come from the backend's `zoom_format` filters `class_date` / `class_time`, through two new partials:
  - `zoom/partials/when.html` (`with at=…`): `<time>Mon 28 Sep 2026</time>, 9:40 am`. Used on the detail page for the decided line (×2), Sent, Confirmed and First overlap;
  - `zoom/partials/class_span.html` (`with start=… end=…`): `<time>Mon 5 Oct 2026</time>, 8:30 am to 11:30 am`. Used by `occurrence_list.html` and the detail clash lines.

  `queue.html` (first class) and the other booking's times in the clash line use the filters directly (`{% load zoom_format %}`). The decided line now wraps its date in `<time>`, and its wording is unchanged.
- **SF4 (dedupe):**
  - `zoom/partials/field_error.html` (`with field=… only`) is the one error line. It's used by `field.html`, the recording checkbox, and through the next partial.
  - `zoom/partials/choice_group_head.html` (legend, help and error) is the head of the three radio/checkbox groups (`repeat`, `weekdays`, `host_account`). The `<fieldset aria-describedby>` tag stays in the page, because a partial can't open an element another template closes.
  - `zoom/partials/recording_tag.html` is used by the queue and the detail page.
  - `zoom/partials/recording_answer.txt` (`with wants_recording=…`) is the one source of `Yes, record it to the Zoom cloud` / `No`. It's plain text with no markup, so `confirm.html`, `detail.html` **and** `email/confirm_body.txt` all include it. The email's own copy is gone.
  - **"Already started":** the text stays only in `detail.html`, and the view signals the state through `has_started` (it already did). `services.STARTED` in `apps/zoom/services.py` still holds the same sentence, as `ApproveResult.message`, which no page renders. **The backend should drop or rename that text** so there's one copy. That's not my file.
- **Nit:** `email/it_new_body.txt` now prints `Phone: {{ link_request.requester_phone_display }}`.
- **Self-check (2026-09-25, dev stack):**
  - The full run after `apps/zoom/templatetags/zoom_format.py` landed gave `pytest --create-db` → `3 failed, 294 passed`. All three failures were in backend service/race tests that were changing while I ran: `test_services.py::test_lock_races_…` ×2 and `test_race_cleanup_scratch.py`, a file that has since been removed. None render templates. A rerun of `test_services.py` gave `1 failed, 39 passed` (`test_a_lock_wait_timeout_is_not_retried`), which is the backend's work in progress.
  - The template-facing suites all pass. `apps/core`, `apps/accounts` and `apps/zoom/tests/test_views.py` / `test_models.py` / `test_admin.py` gave `245 passed`. `test_no_reply_time_promise.py`, `test_sidebar_zoom_group.py`, `test_views.py` and `apps/core` gave `156 passed`. Those include the header-comment, `only`, sprite and static guards, and the real confirm email rendering its included `recording_answer.txt`.
  - **Re-rendered on the dev stack (Django test client, `it.check`), all 200 with the same strings as before:**
    - detail ZL-0020: `Mon 5 Oct 2026, 8:30 am to 11:30 am`, `Sent Fri 25 Sep 2026, 8:19 am`, `Wed 7 Oct 2026, 8:30 am to 11:30 am clashes with ZL-0019 Grade 10 Science, 9:00 am to 12:00 pm`, `First overlap Mon 12 Oct 2026, 9:00 am`;
    - detail ZL-0019: `This request was approved by Ishara Check on Fri 25 Sep 2026, 8:19 am.`;
    - queue first-class cells: `Mon 5 Oct 2026` / `8:30 am`;
    - confirm (ready): `Mon 5 Oct 2026, 8:30 am to 11:30 am`, `Recording: Yes, record it to the Zoom cloud`.
  - This added one unverified dev request, "Date check".

## Verification
<!-- owner: tmd-test-verifier — verdict, criteria → tests table, checklist results, failures -->

**Verdict: PASS**

**Frozen-now note.** The backend and this verifier froze "now" by patching `django.utils.timezone.now` (no `time-machine` dependency was added; `apps/zoom/tests/conftest.py::frozen_now`).

### Checklist (CLAUDE.md "Verify a change")

| Check | Result |
|---|---|
| `ruff check .` | PASS — `All checks passed!` |
| `ruff format --check .` | PASS — `67 files already formatted` |
| `pytest --create-db -rA` (dev container) | PASS — **290 passed** (286 pre-existing + 4 new sidebar tests; the 5 criterion-67 tests I added are counted inside the 286) |
| `makemigrations --check --dry-run` | PASS — `No changes detected` |
| `manage.py check` (dev) | PASS — `System check identified no issues (0 silenced)` |
| `check --deploy`, prod stack, `USE_HTTPS=True`, `ZOOM_PROVIDER=manual` | PASS — only `security.W021` (accepted) |
| `check --deploy`, prod stack, `ZOOM_PROVIDER=fake` | PASS — `zoom.E001` fires as pinned, plus W021 |
| Prod stack HTTP walk-through (criterion 57) on port 8010 | PASS — see below |
| Race tests (criterion 38b/38c) run repeatedly | PASS — 2 passed on 5 separate full-suite runs plus 4 standalone re-runs (9 runs total on this pass, on top of the backend's own 6); never flaky |
| `docker compose build` for the `cryptography` dependency (criterion 66) | PASS — prod image built from manylinux wheels (`cryptography-50.0.1`, `cffi-2.1.1`), no compiler added to the runtime stage, `web` reached healthy |

### Tests added by this verifier

- `apps/zoom/tests/test_no_reply_time_promise.py` (5 tests) — criterion 67 had **no existing automated test** anywhere in the codebase. Renders the real `zoom:request`, `zoom:request_sent`, `zoom:confirm` (ready) and `zoom:confirmed` templates (the app's own view tests stub these) plus the real confirm email, and asserts: (a) the required link-duration statements are present (`The link works for one day.` / `The link works for 24 hours`), and (b) no sentence that names the IT desk (`IT`, case-sensitive, to avoid false hits on the pronoun "it") also matches a reply-time-promise pattern from the criterion's list. A first version matched the request form's unrelated "Ends at: on the same day as it starts" help text as a false positive; scoping the check to sentences that mention "IT" fixed it — this is exactly the ambiguity the main-session ruling on criterion 67 resolves (the ban is about IT's reply time, not every incidental use of these words).
- `apps/zoom/tests/test_sidebar_zoom_group.py` (4 tests) — criterion 19's sidebar behaviour (the `Zoom links` group, its position between Menu and Administration, and `aria-current` tracking) had no automated coverage: the zoom app's own view tests stub out the page templates entirely, and `apps/core/tests.py`'s sidebar tests only cover a staff user *without* the Zoom permission. Renders the real templates for an IT user, a superuser (to prove ordering against a real Administration group) and a plain user, and checks `Home`'s `aria-current` is not carried onto the zoom pages.

### Acceptance criteria

Numbers refer to the brief. "Test" names an automated pytest; "Manual" names evidence gathered directly in this pass (HTTP, `manage.py shell`, or Playwright against the prod stack on :8010, screenshots saved to the verifier's scratchpad `shots/`, not committed).

| # | Result | Evidence |
|---|---|---|
| 1–2 | ✅ | `apps/core/tests.py` (brief 004 tests, still pass); manual: saved `request_form.html`/`request_sent.html`/`confirmed.html` show no `data-nav`, `.topbar`, user menu or settings dialog |
| 3 | ✅ | `apps/zoom/tests/test_views.py::test_request_form_get_is_public_and_supplies_the_contract`; manual: every input has a matching `<label for>`, honeypot markup exact (`hidden` + `aria-hidden="true"` + `tabindex="-1"` + `autocomplete="off"`) |
| 4–6, 8 | ✅ | `test_models.py`, `test_views.py::test_one_off_request_is_stored_unverified_…`, `test_weekly_request_makes_eight_classes_…`, `test_once_ignores_weekly_fields`, `test_invalid_request_rerenders_with_the_pinned_error_and_keeps_values` (parametrised over the whole pinned-error table and the phone table) |
| 7 | ✅ | `test_invalid_request_rerenders_…`; manual: `aria-invalid`, `aria-describedby="<name>-error <name>-help"`, `role="alert" tabindex="-1"` summary with pinned lead/count wording, confirmed on the prod stack for a 5-error submit |
| 9 | ✅ | `test_honeypot_looks_like_success_but_stores_and_sends_nothing` |
| 10 | ✅ | `test_sixth_request_from_one_email_in_an_hour_gets_429`, `test_twenty_first_request_from_one_ip_gets_429_and_old_ones_do_not_count`, `test_throttle_is_not_applied_to_invalid_posts`, `services.py::test_throttle_counts_email_and_ip_separately` |
| 11 | ✅ | `test_forwarded_ip_is_used_only_with_a_trusted_proxy`, `test_services.py::test_client_ip_trusts_forwarded_for_only_as_far_as_the_proxy_count` (parametrised on the exact proxy-count table) |
| 12 | ✅ | `test_services.py::test_approval_email_carries_link_host_key_classes_and_recording` (asserts `&amp;` not in the plain-text body for `<b>Maths & Science</b>`); no `|safe`/`mark_safe`/`{% autoescape off %}` anywhere in `templates/zoom/` except the `.txt` email templates (grep, confirmed) |
| 13–16 | ✅ | `test_confirm_get_shows_ready_and_changes_nothing`, `test_confirm_post_moves_to_waiting_and_emails_every_reviewer`, `test_confirm_twice_is_already_…`, `test_expired_and_invalid_tokens`, `test_unverified_requests_404_on_detail`; manual: expired state reproduced by backdating a real request's signed token 25h on the prod stack — `This link has expired. Please send your request again.`, 200, screenshot `confirm-expired-400.png` |
| 17–18 | ✅ | `test_anonymous_visitors_are_sent_to_sign_in`, `test_users_without_the_permission_get_403` (plain + staff), `test_it_users_and_superusers_can_open_the_it_pages` (incl. 405 on GET approve/reject), `test_it_desk_group_holds_exactly_the_review_permission`, `test_it_desk_migration_is_idempotent_and_reversible` |
| 19 | ✅ | **New**: `test_sidebar_zoom_group.py` (see above); manual: confirmed on the prod stack (saved `queue.html`, `detail_32.html`) |
| 20–25 | ✅ | `test_queue_defaults_to_waiting_with_tabs_counts_and_share_link`, `test_queue_search_works_within_the_tab`, `test_queue_pages_at_25`, `test_queue_query_count_does_not_grow_with_rows` (`django_assert_num_queries`-equivalent `CaptureQueriesContext`) |
| 26–33 | ✅ | `test_detail_shows_free_and_busy_accounts_with_busy_count_per_class`, `test_detail_with_manual_provider_asks_for_the_meeting_details`, `test_detail_without_free_account_or_after_start_has_no_approve_form`, `test_decided_request_has_no_forms_or_availability`, `test_detail_lists_overlapping_waiting_and_earlier_requests`; manual: `.tag` computed font-size `10.5px` confirmed live in Chromium (Playwright), both modes |
| 34 | ✅ | `LinkRequest.reference` property; exercised throughout (`ZL-0032` etc. seen live on the prod stack) |
| 35 | ✅ | `test_approve_view_books_emails_and_redirects`, `test_services.py::test_approve_books_every_class_and_slot_and_stores_the_fake_meeting` (288 = 8×36 slots), `test_approval_email_carries_link_host_key_classes_and_recording` (`message.to == ["nimali@example.com"]`, no cc/bcc parameter exists anywhere in `services.py`); manual: real approval email on the prod stack addressed only to the requester, host key `123456` present |
| 36 | ✅ | `test_manual_approve_stores_typed_details_and_rejects_bad_ones`; manual: pasted `https://us02web.zoom.us/j/12345678901` approved live on the prod stack, detail shows `Link sent` |
| 37 | ✅ | `test_stale_page_gets_409_and_refreshed_availability`, `test_unbookable_choice_is_a_form_error_with_409` (unpaid/inactive/unknown, parametrised) |
| 38a | ✅ | `test_models.py::test_two_slots_on_one_account_at_the_same_time_are_refused` |
| 38b/38c | ✅ | `test_race.py` (2 tests), run 9 times this pass with no flakes; **own independent check**: a script approving a weekly (8-occurrence) request then a second weekly request whose Monday classes overlap — first approves (288 slots, exactly 8×36), second correctly returns `conflict` and stays `waiting` |
| 39–41 | ✅ | `test_deciding_twice_says_already_decided`, `test_approving_a_started_request_rerenders_with_the_started_state`, `test_provider_error_rerenders_with_the_message`, `test_email_failure_keeps_the_approval_and_warns` (caplog: reference + exception class only) |
| 42–43 | ✅ | `test_reject_view_stores_reason_emails_and_redirects`, `test_blank_reason_rerenders_and_keeps_the_approve_values`; manual: reject flow completed live on the prod stack |
| 44 | ✅ | Reviewed `views.py` — no ORM filters beyond `get_object`/`get_queryset` calling model/QuerySet methods |
| 45 | ✅ | `test_models.py`, all 5 `CHECK` constraints, each via `.save()`/`bulk_create` bypassing `clean()`, each raising `IntegrityError` |
| 46 | ✅ | Field-name sweep is implicit in the model definitions (`host_key_encrypted` is the only match); no `start_url` field anywhere; no credential fields |
| 47 | ✅ | `test_admin.py::test_it_staff_without_host_account_permissions_are_kept_out`, `test_link_requests_are_view_and_delete_only`; manual: admin changelist confirmed 200 for a superuser, `Saved`/`Not saved` column only |
| 48 | ✅ | `test_services.py::test_check_e002_rejects_unknown_providers`, `test_check_e001_keeps_the_fake_provider_out_of_deploys`; **manual, on the actual prod stack**: `check --deploy` with `ZOOM_PROVIDER=manual` → only W021; with `ZOOM_PROVIDER=fake` → `zoom.E001` plus W021, exit 1 |
| 49–50 | ✅ | Reviewed `config/settings/base.py`, `prod.py` (no `env(` calls), `compose.yaml`, `.env.example`; `services.py::_send` sends one `EmailMessage` per recipient with `DEFAULT_FROM_EMAIL`, subjects joined/stripped to one line, bodies from `.txt` templates, no `html_message` |
| 51 | ✅ | `apps/core/tests.py` template-header, `only`-include, no-inline-style, no-hardcoded-path, icon-sprite guard tests all pass for every new template |
| 52 | ✅ | Manual, Playwright with `javaScriptEnabled: false`: weekly fields (`weekdays`, `last_date`) visible without JS, form submits successfully to `/zoom/request/sent/` |
| 53 | ✅ | Manual, Playwright: `Every week` shows+enables the weekly fields, `Just once` hides+disables them; binds via `data-repeat`/`data-weekly-fields`; zero console errors across the whole Playwright run |
| 54 | ✅ | Manual, Playwright: no horizontal scroll at 320/400/1024/1440 on the request form (both colour schemes) and the queue (both colour schemes); one `h1` on every page checked; focus moves to `[data-error-summary]` after a failed submit; no target under 44px on the request form at 400px |
| 55 | ✅ | `apps/core/tests.py::test_sidebar_shows_administration_group_only_for_staff`, `test_sidebar_links_resolve_to_named_urls_only` pass unchanged; `test_home_page_has_no_form_other_than_sign_out` unchanged |
| 56–58 | ✅ | See Checklist above and the screenshot list below |
| 59 | ✅ | `test_services.py::test_approval_email_carries_link_host_key_classes_and_recording` (`wants_recording=True` path), `test_it_email_goes_to_each_active_reviewer_only` (`Recording: no`); manual: confirm email on the prod stack showed `Recording: No` |
| 60 | ✅ | **Manual, raw DB column**: `SELECT host_key_encrypted` via `connection.cursor()` after `set_host_key("8421973")` → starts `gAAAAA`, does not contain `8421973`; `get_host_key()` round-trips; short key raises `ValidationError: A Zoom host key is 6 to 10 digits.`; also `test_admin.py::test_a_badly_typed_key_is_refused` |
| 61 | ✅ | `test_services.py::test_approval_email_without_a_host_key_says_ask_the_it_desk`, `test_other_emails_never_carry_the_host_key`; manual full-flow sweep (below) |
| 62 | ✅ | `test_admin.py` (8 tests): changelist masking, decrypted key shown only to `change_hostaccount`, `LogEntry.change_message` names the field only, view-only users never see the field |
| 63 | ✅ | `test_services.py::test_check_e003_reports_missing_or_invalid_keys_without_echoing_them`, `test_rotation_reencrypts_with_the_new_key_so_the_old_one_can_go`, `test_removing_a_key_before_rotating_makes_keys_unreadable` |
| 64 | ✅ | `test_services.py::test_unreadable_host_key_books_nothing_and_logs_only_label`, `test_views.py::test_unreadable_host_key_rerenders_with_the_message` |
| 65 | ✅ | `test_views.py::test_full_flow_never_logs_the_host_key_or_encryption_keys` — full flow (submit → confirm → approve → reject → admin key edit → `rotate_host_keys`) with `caplog` at DEBUG for `apps.zoom` and `django`, no secret found |
| 66 | ✅ | `docker compose up -d --build` on the prod overlay: `cryptography==50.0.1`, `cffi==2.1.1` installed from manylinux wheels, no build tools added to the runtime stage, `web` reached `healthy` |
| 67 | ✅ | **New**: `test_no_reply_time_promise.py` (5 tests, see above); manual: confirm email body contains `The link works for 24 hours`; "check your email" page contains `The link works for one day.`; no sentence naming IT anywhere on the four public pages promises a reply time |

### Prod-stack HTTP walk-through (criterion 57), port 8010

`.env` was temporarily set to `ZOOM_PROVIDER=manual` (it already had `EMAIL_BACKEND=…console.EmailBackend`) and restored byte-for-byte afterwards (diffed against a backup).

1. Anonymous `GET /zoom/request/` → 200. `POST` with a one-off class → 302 to `/zoom/request/sent/` (200, shows the email). Confirm URL taken from `docker compose logs web`; `GET` → 200 (`state="ready"`), `POST` → 302 to `/zoom/confirmed/…` → 200, reference `ZL-0032`.
2. Signed in as a throwaway superuser (`verify_admin2`, deleted afterwards): queue shows `ZL-0032` under `Waiting`. Detail shows availability and the manual-mode fields (`Zoom link`, `Meeting ID`, `Passcode`) that the frontend's own dev self-check could not render (dev runs `ZOOM_PROVIDER=fake`). Test host account used a dummy key `123456` only.
3. Approved with `https://us02web.zoom.us/j/12345678901` → 302, detail re-renders `Link sent`, `message.to == [requester]`. Approval email in the container log carried `Host key: 123456` and the exact pinned host-key sentence.
4. A second request was rejected with `Please use the Grade 10 batch link instead.` → detail shows `Not approved`.
5. Hashed static paths (`style.3ddf2d301e6c.css`, `app.2860f9c6ffa3.js`) both returned 200.
6. All throwaway `LinkRequest`s, the throwaway `HostAccount`, and both throwaway superusers were deleted from the (shared dev/prod) database before restoring the dev stack. Confirmed by a post-hoc sweep: zero `verify`-prefixed users, accounts or requests remain.

### Screenshots (verifier's scratchpad `shots/`, not committed)

`request-form-{1440,400}-{light,dark}.png`, `queue-waiting-{1440,400}-{light,dark}.png`, `detail-clash-{1440,400}.png`, `detail-none-free-1440.png`, `detail-approved-1440.png`, `confirm-expired-400.png`.

### Notes for the record

- Dev test data left by `tmd-frontend` (`it.check`, `Zoom 01/02/03`, `Zoom free`, `ZL-0019…0029`) was left untouched, confirmed present after the stack was restored.
- The frontend's Implementation notes flagged a possible "context contract gap": `confirm_body.txt`'s `The link works for {{ link_hours }} hours.` line. That flag predates the main-session ruling on criterion 67 quoted in this task's brief, which explicitly requires that exact line. No action needed; confirmed correct as implemented.
- Docker was left exactly as found: dev overlay (`compose.yaml` + `compose.dev.yaml`), `web` and `db` healthy, `.env` unchanged, no other project's containers touched.

### Re-verification (after review round 1)

**Verdict: PASS**

**SF5 (mine): the race tests' cleanup fixture leaked committed rows if setup failed partway.**

- `apps/zoom/tests/test_race.py`: rows are now registered for cleanup the instant each is committed, through three small factories (`_tracked_request`, `_tracked_account`, `_tracked_user`) used by `_setup` and both tests, instead of being batched into the `committed` dict only after an entire multi-row setup finished. The `committed` fixture's `finally` block also sweeps by the fixed `"Race "` class-name/label prefix and the `"race-it"` username as a backstop.
- **Proof (scratch run, not committed):** a temporary test forced `LinkRequest.save()` to raise on its first call after one row ("Race A") had already committed successfully, while creating a second row ("Race B"). The forced failure was caught, then a second test asserted zero rows remain matching the `"Race "` prefix or `"race-it"` username. Both passed; the scratch file was then deleted (`apps/zoom/tests/test_race_cleanup_scratch.py` no longer exists — its transient presence is also what the frontend's self-check flagged mid-run, consistent with this being a real, if brief, file).
- Re-ran `apps/zoom/tests/test_race.py` 3 times immediately after the fix and 5 more times after all three agents' round-1 fixes landed (8 runs this pass, all `2 passed`, on top of the 9 runs recorded in the first verification pass and the backend's own 4 and 6). Never flaky.

**Other agents' round-1 fixes, spot-checked directly (not just re-running their own tests):**

- **tmd-devops — prod refuses `ZOOM_PROVIDER=fake`.** With `.env` untouched (still `ZOOM_PROVIDER=fake`, as it's meant to stay for local dev), `docker compose up -d --build` on the prod overlay: `web` crash-loops (`docker inspect` → `Restarting`, `exitcode=1`), and `docker compose logs web` shows `django.core.exceptions.ImproperlyConfigured: The fake Zoom provider can't run in production. Set ZOOM_PROVIDER=manual.` raised from `config/settings/prod.py` at import time, before `migrate` or gunicorn starts. Then `ZOOM_PROVIDER=manual docker compose up -d` → `web` reaches `healthy`, `docker compose exec web env` confirms `ZOOM_PROVIDER=manual`, and `check --deploy` with `USE_HTTPS=True` again reports only `security.W021`.
- **tmd-django-backend — sensitive-data masking, deadlock retry, `zoom_format`, `services.STARTED`.** Confirmed `Outcome.STARTED` now carries no message (`apps/zoom/services.py`) and the "already started" sentence lives only in `templates/zoom/detail.html`, chosen by `has_started` — the DRY point the frontend flagged as not their file is resolved. `apps/zoom/tests/test_review_fixes.py` and the retry/1205/1062 tests are part of the 308 passing.
- **tmd-frontend — shared date/time filters and partials.** Re-rendered `zoom:detail` for `ZL-0020` and `zoom:queue` (`?status=waiting`) as a signed-in superuser on the **rebuilt prod stack** (`ZOOM_PROVIDER=manual`): every date/time is now wrapped in a semantic `<time datetime="2026-10-05T08:30:00+05:30">Mon 5 Oct 2026</time>, 8:30 am to 11:30 am`-style tag, with the same wording as the pre-round-1 screenshots (`Mon 5 Oct 2026, 8:30 am to 11:30 am`; `First overlap Mon 12 Oct 2026, 9:00 am`; `This request was approved by Ishara Check on Fri 25 Sep 2026, 8:19 am.`). `<b>test</b>` and `<b>Maths & Science</b>` class names from the frontend's and backend's test data render as literal escaped text on both pages, confirming criterion 12 still holds after the templatetag refactor. `it_new_body.txt`'s `Phone: {{ link_request.requester_phone_display }}` line is accepted per the coordinator's ruling.
- Manual-provider approve fields (`Zoom link`, `Meeting ID`, `Passcode`, the "Turn on cloud recording" note) render correctly on the rebuilt prod stack for a real waiting request (`ZL-0020`), which the frontend's own dev-stack self-check could never show (dev runs `ZOOM_PROVIDER=fake`).

**Checklist, re-run after all three fixes landed:**

| Check | Result |
|---|---|
| `ruff check .` | PASS — `All checks passed!` |
| `ruff format --check .` | PASS — `70 files already formatted` |
| `pytest --create-db -rA` (dev container) | PASS — **308 passed** (twice: immediately after round 1 landed, and again after restoring the dev stack at the end) |
| `makemigrations --check --dry-run` | PASS — `No changes detected` (confirms migration `0002`'s in-place edit needs no new migration) |
| `manage.py check` (dev) | PASS — `System check identified no issues (0 silenced)` |
| Prod image + `ZOOM_PROVIDER=fake` | PASS (refuses) — crash-loop, `exitcode=1`, `ImproperlyConfigured` |
| Prod image + `ZOOM_PROVIDER=manual` | PASS (starts) — `web` reaches `healthy`, `check --deploy` only W021 |
| Race tests, repeated | PASS — 8 further runs this pass (3 right after my SF5 fix, 5 after all fixes landed), all `2 passed`, never flaky |
| Rendered-page comparison (dates, markup, escaping) vs. the pre-round-1 screenshots | PASS — see above; fresh screenshots in the scratchpad `shots_round2/` (`queue-waiting-1440.png`, `detail-20-1440.png`, `request-form-400.png`), not committed |

**Cleanup and stack state.** One throwaway superuser (`verify_reverify`) was created to re-render the IT pages on the prod stack and deleted afterwards; no other rows were created this pass. `.env` was never edited (the fake→manual override used `ZOOM_PROVIDER=manual docker compose up -d`, a shell-level override, exactly as devops's note describes). The dev DB's existing test data (`it.check`, `Zoom 01/02/03`, `Zoom free`, `ZL-0019…0029`, plus the frontend's `ZL-0028`/`ZL-0029`/`ZL-0042` and the unconfirmed "Date check" request) was left untouched throughout. Docker was returned to the dev overlay, `web` and `db` healthy, `.env` byte-identical to the start of this task.

## Review
<!-- owner: tmd-code-reviewer (written by the main session) — verdict, blockers, should-fix, nits -->

### Round 1 — 2026-09-25 (verifier PASS, 290 tests)

**Verdict: CHANGES REQUESTED**

**Blocker**
1. Nothing stops the fake provider in production. `.env.example:47` ships `ZOOM_PROVIDER=fake`, `compose.yaml:64` passes it through, and `zoom.E001` is deploy-tagged — but `docker/entrypoint.sh` never runs `check --deploy`. A prod `.env` copied from the example would book slots and email a dead `.invalid` link *with the real host key*, while no meeting exists in Zoom. Fix: start-up guard in `config/settings/prod.py` (next to the `ALLOWED_HOSTS` guard) raising `ImproperlyConfigured` when `ZOOM_PROVIDER == "fake"`; keep E001; default `.env.example` to `manual` with `fake` shown as a dev comment. Owner: tmd-devops.

**Should fix**
1. Host key and encryption keys aren't marked sensitive: `host_key` local in `services.approve`/`send_approved_email`, `plain` in `models.set_host_key` and `crypto.encrypt/decrypt/rotate`, and `host_key` POST data in the admin change view would appear on DEBUG 500 pages and in any future error-report email. Fix: `@sensitive_variables(...)` on those functions, `sensitive_post_parameters("host_key")` on `HostAccountAdmin.changeform_view`, and a test rendering `ExceptionReporter` asserting the key is masked. Owner: tmd-django-backend.
2. Deadlock/lock timeout (MySQL 1213/1205) is reported as "{label} was booked for an overlapping class a moment ago" — misleading when the deadlock involved another account, and with an empty label if it happens on the first lock (`services.py:181–185`). Fix: its own message ("Someone else was approving at the same moment. Nothing was booked. Try again."), ideally one automatic retry on 1213; unit test raising `OperationalError(1213, …)`. Owner: tmd-django-backend.
3. Date/time display format duplicated across ~10 template sites (`occurrence_list.html`, `detail.html`, `queue.html`) and separately in Python (`models._date_text/_time_text`). Fix: one template filter backed by the Python helpers, used everywhere. Owners: tmd-django-backend (filter), tmd-frontend (templates).
4. Duplicated error markup (`field.html`, `request_form.html`, `detail.html`) → one `zoom/partials/field_error.html`; `Recording asked for` tag copied in `queue.html`/`detail.html` → partial; `Yes, record it to the Zoom cloud` repeated in three places; the "already started" notice text lives in both `detail.html:178` and `services.STARTED`. Owner: tmd-frontend.
5. `apps/zoom/tests/test_race.py:78–84` registers committed rows for cleanup only after all setup succeeds, so an aborted setup leaks rows into the reused test DB. Fix: register each row as it is created; `finally` also deletes by the `Race ` prefix and `race-it` username. Owner: tmd-test-verifier.

**Nits:** `forms._BookableAccountField` is an empty subclass (move its docstring, drop it) and widget `format=` args are unused; migration 0002 toggles `models_module` to trick `create_permissions` — use explicit `get_or_create`; the join-link check accepts a backslash host trick (`https://evil.example\.zoom.us/…`) — reject `\`; `email/it_new_body.txt` prints `requester_phone` instead of `requester_phone_display` (contract); emails send inside the request transaction — acceptable, record the decision; throttle count-then-insert race — document; error summary count vs multiple non-field errors — can't happen yet; `occurrence_times` would mis-handle nonexistent DST times — document (Colombo has none).

**Checked and sound:** confirm token (own salt, pk only, 24 h, GET never mutates); forwarded-IP parsing (Nth from the right, falls back to REMOTE_ADDR, spoofable only if TRUSTED_PROXY_COUNT is set too high); no mass-assignment; subjects single-line and header injection blocked; no `|safe`; admin key visibility by permission; rotation prints counts only; E003 not deploy-tagged so migrate fails loudly; locking order request → account → decrypt → locking re-read → slots → provider (sidesteps the REPEATABLE READ snapshot); `non_atomic_requests` on the approve view takes effect and is sound; slot grid refuses off-grid starts, rounds ends up, no midnight crossing, half-open overlap; permissions (302 signed out, 403 without permission); loose coupling; `public_base.html` frame; screenshots match the Design section.

**Good:** `availability_for()` backs both the preview and the locked re-check with a fixed query count, so they can't disagree; `mark_verified()` and `reject()` are conditional `UPDATE … WHERE status=…`, correct under double clicks without locks.

### Round 2 — 2026-09-25 (after round-1 fixes; verifier PASS, 308 tests)

**Verdict: APPROVE.** Blockers: none. Should fix: none.

All six round-1 findings confirmed fixed in the files: prod refuses `ZOOM_PROVIDER=fake` (`prod.py:22–25`) and `.env.example` defaults to `manual`; secrets masked (`sensitive_variables` applied directly — not via `method_decorator`, whose wrapper frame leaked — plus `sensitive_post_parameters` on the admin changeform, proved with real `ExceptionReporter` reports at three failure points); deadlock retried once, then an account-neutral "Someone else was approving at the same moment…" (a real 1062 clash keeps "booked a moment ago"); one date/time definition (`class_date`/`class_time`) used by templates and emails; duplicated markup and copy moved into partials, `services.STARTED` removed; race-test cleanup registers rows as they're created. Nits fixed as described.

Checked specifically: the retry's transaction handling is correct for the approve view (`non_atomic_requests`, each attempt its own top-level `atomic()`); editing migration 0002 in place is sound (never deployed, `get_or_create`, reversible, idempotent).

**Nits (optional)**
1. `services.approve()` retries correctly only outside an open `atomic()`; called inside one (e.g. a future importer or shell script), a real deadlock breaks the savepoint and the retry raises `TransactionManagementError`. The mocked deadlock tests run inside pytest's transaction, so they don't catch it. Guard with `not transaction.get_connection().in_atomic_block` (or assert it). **Main-session ruling: carried forward as a required item for brief 007 (the importer is the first caller that could hit it).**
2. `HostAccountKeyAdminForm.clean_host_key` local `value` (and `validate_host_key`'s argument) aren't masked; only an unexpected non-validation exception would expose them. `@sensitive_variables("value")` would close it.

**Good:** masking was verified with `ExceptionReporter` rather than assumed, which is how the `method_decorator` gap was found; the deadlock copy names no account, so it can't contradict the refreshed availability list.

## Docs
<!-- owner: tmd-docs-writer — files updated; closes Status -->

- **`README.md`:** new "Setting up `.env`" line for `HOST_KEY_ENCRYPTION_KEYS` (required, with its
  generation command); a note under "Production-like" that the prod image refuses
  `ZOOM_PROVIDER=fake` and how to override it for a local run; a note under "Running without
  Docker" to re-run `pip install -r requirements\dev.txt` for `cryptography`; the "Deploying the
  image" env-var table gained `EMAIL_*`, `ZOOM_PROVIDER`, `TRUSTED_PROXY_COUNT` and
  `HOST_KEY_ENCRYPTION_KEYS`; a new "Zoom link requests" section (the public form URL, giving IT
  staff access via the `IT desk` group, host accounts and host keys in the admin, manual mode until
  a later brief, the go-live gate, what to do if a host key leaks, and key rotation); `apps/zoom/`
  and `public_base.html` added to the Layout tree.
- **`CLAUDE.md`:** `zoom` added to Architecture → Current apps (the request → confirm → queue →
  booking → email flow, the fake/manual provider interface, encrypted host keys, and the
  `services.approve()`-outside-`atomic()` gotcha); the Templates paragraph now names
  `public_base.html` and the sidebar's `perms` parameter; a new Environment gotcha for
  `ZOOM_PROVIDER=fake` vs. the prod guard.
- **`docs/CHANGELOG.md`:** new entry, 2026-09-25, "005: Zoom link requests (without the live Zoom
  connection)".
- **`docs/design/placeholder-controls.md`:** the three places that said brief 005 would replace
  search and the bell now say D10 kept them as placeholders, and point at a later
  "search and notifications" brief instead.

**Status:** Done — Verification PASS (308 tests; prod manual-mode walkthrough; prod refuses the
fake provider) and Review APPROVE (round 2, two optional nits — nit 1 carried forward as a required
item for brief 007).
