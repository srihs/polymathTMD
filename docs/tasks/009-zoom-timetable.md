# 009 — Zoom timetable: a wall-calendar month of classes, with a day view

<!-- One brief per task. Each section has exactly one owner agent; agents write only their own section.
     The workflow itself is defined in CLAUDE.md → "Agent workflow". -->

**Status:** Done <!-- Planned | Blocked: questions | In progress | Verifying | In review | Done -->

## Requirement
<!-- owner: tmd-planner — the user's words verbatim, then a one-paragraph interpretation -->

> so there should be a place where we can configure the zoom accounts, and view of the month in a timetable format.

The owner chose the shape on 2026-09-25 (Q6): **"Wall calendar"**.

**Reading.** This brief covers the second half of the requirement, **"view of the month in a timetable format"**. The first half, configuring the Zoom accounts, is brief 008.

IT desk staff get a **Zoom timetable** page. It shows one calendar month as a **wall calendar**: weeks run **Monday to Sunday**, following the Sri Lanka and ISO 8601 convention, and each day has a box. Each box lists that day's classes with their start time, class name and Zoom account. A class that is still waiting for IT has no account yet, so it shows a `Waiting for IT` tag, with an icon and a word, in place of the account. Each class links to its request.

When a day holds more classes than fit, the box shows the first three and a `+N more` link. The link opens a **day view** listing every class that day. The day number in each box opens the same day view.

Previous and next month are links carrying the month in the URL. A GET form narrows the calendar to one account. Boxes for days outside the month are left empty.

On a phone, the same page becomes a day-by-day list showing only days that have classes. The page is fully server-rendered, works without JavaScript, meets WCAG AA and runs a fixed number of queries. It is read-only: nothing is booked, moved or changed here.

## Scope
<!-- owner: tmd-planner — In scope / Out of scope bullets -->

**Place in the order:** 008 → 010 → **009** (see the split table in `docs/tasks/008-zoom-accounts.md`). 009 depends only on 005, apart from one link from 008's accounts list (criterion 21).

**In scope (009)**

- **`apps/zoom`:** a new module, `apps/zoom/timetable.py` (month arithmetic, week layout and grouping, all pure functions), plus two `OccurrenceQuerySet` methods, one `HostAccountQuerySet` method, two views and two URLs.
- **Month page, `zoom:timetable`** (`zoom.review_linkrequest`, in the shell):
  - month navigation with `?month=YYYY-MM`;
  - the account filter, `?account=<pk>`;
  - the Mon–Sun week grid of day boxes, with a cap of 3 entries per box and a `+N more` link;
  - a summary line and empty states;
  - a phone list layout.
- **Day view, `zoom:timetable_day`:** every class on one date, with previous and next day, a link back to the month, and the same account filter.
- **Sidebar:** a `Timetable` item in `Zoom links`, between `Link requests` and `Zoom accounts`.
- **Contextual links:** `See it on the timetable` on an approved request's detail page, and `Timetable` on each row of 008's accounts list.

**Out of scope (009)**

- Booking, moving, cancelling or approving from the timetable.
- A week view, an hour-by-hour time axis, or a "rows are days, columns are accounts" grid (Q6's option (a), not chosen; it could come later).
- Printing or export (PDF, `.xlsx`, `.ics`).
- A month-picker widget, because `<input type="month">` isn't supported in desktop Firefox or Safari.
- Unconfirmed, rejected or (after brief 011) cancelled requests.
- Recording status. A `Recording asked for` marker is the designer's choice, per criterion 8.
- Any model field or migration.

## Acceptance criteria
<!-- owner: tmd-planner — numbered, observable, testable -->

**Terms.**

- **Brief 005's rules apply:** its frozen now, **Mon 28 Sep 2026, 10:00** Asia/Colombo, and its pinned-copy rule. "IT user" is as defined in brief 008: `IT desk`, which holds `review_linkrequest` plus the three host-account permissions.
- A **booked class** is an `Occurrence` that `booked()` returns: its request is `approved` and `host_account` is set.
- A **waiting class** is an `Occurrence` whose request is `waiting`.
- An **entry** is a booked or waiting class shown on the page.
- **"The month"** runs from local midnight on the 1st up to, but not including, local midnight on the 1st of the next month, in Asia/Colombo.
- A class's **day** is the local date of its start (D3).

### Access and navigation

1. **Access.** This applies to both `zoom:timetable` and `zoom:timetable_day`:
   - an anonymous visitor is redirected to `accounts:login?next=…`;
   - a plain user, including one with `is_staff`, gets **403**;
   - an IT user or a superuser gets 200.
2. **Sidebar.**
   - `Timetable` → `zoom:timetable` sits in `Zoom links`, between `Link requests` and `Zoom accounts`. It shows only with `zoom.review_linkrequest`.
   - It carries `aria-current="page"` on `zoom:timetable` and `zoom:timetable_day`, and no other item does on those pages.
   - Brief 008's sidebar tests are extended deliberately.
3. **Month page frame.**
   - The h1 is `Zoom timetable`.
   - The `<title>` is `Zoom timetable, {September 2026} · {site name}`.
   - The breadcrumb is `Home › Zoom timetable`.
   - The month is an `<h2>`: `September 2026`.

### Choosing the month

4. **Month parameter.**
   - With no `month`, the page shows today's month in Colombo: **September 2026** under the frozen now.
   - `?month=2026-10` shows October 2026.
   - `2026-13`, `2026-1`, `abc`, an empty value, and anything outside `2000-01`…`2100-12` fall back to the current month. The page still returns 200 and shows no error message.
   - This logic is `timetable.parse_month(value, today)`, unit-tested with exactly these values.
5. **Month navigation.** These are plain links: `{% url 'zoom:timetable' %}` plus a query.
   - On September 2026:
     - `Previous month` → `?month=2026-08`;
     - `Next month` → `?month=2026-10`.
   - At the year boundary, `2026-12` gives next `2027-01`, and `2027-01` gives previous `2026-12`.
   - When `account` is set, the links keep `&account=<pk>`.
   - `This month` (no `month`, keeping `account`) shows only when the page isn't on the current month.
   - The accessible names include the target month, for example `Previous month, August 2026`.

### The calendar grid

6. **Weeks, Monday to Sunday.**
   - **The table:** a `<table>` whose `<caption>` reads `Zoom classes in September 2026, by week, Monday to Sunday.` Its header row has seven `<th scope="col">`: `Monday` … `Sunday`. They may be shown shortened (`Mon`), but the full name must be their accessible name.
   - **The rows:** one row per week, covering every day of the month. Days outside the month are **empty cells**: no date, no link and no entries (D2). Exact expectations:
     - **September 2026** has **5** rows. Row 1: Monday empty (31 Aug), Tuesday = 1 Sep. Row 5: 28, 29, 30 Sep, then Thursday to Sunday empty.
     - **February 2027** has **4** rows, Mon 1 Feb to Sun 28 Feb, with no empty cells.
     - **November 2026** has **6** rows. Row 1: Monday to Saturday empty, Sunday = 1 Nov. Row 6: Mon 30 Nov, then six empty cells.
   - **Where the logic lives:** `Month.weeks()` returns a list of 7-item lists of `date | None`. It's unit-tested with these three months.
7. **Day box.** Every day in the month is a cell containing:
   - an `<h3>` whose visible text is the day number. Its accessible text is `Tue 1 Sep`, which is `class_date` without the year: visible `1`, plus visually-hidden `Tue ` and ` Sep`, or the equivalent. It wraps a `<time datetime="2026-09-01">`. The heading is a link to `zoom:timetable_day` for that date, keeping `?account=` when it's set;
   - its entries, as a `<ul>`, or nothing when it has none.

   Today's box (28 Sep under the frozen now) carries `aria-current="date"` and shows the word `Today`.
8. **Entries.** Each entry is **one link** to `zoom:detail`.
   - **Visible text:** the start time (`8:30 am`, `class_time`), the class name (escaped), and the account `label` for a booked class. A waiting class shows the `Waiting for IT` status tag instead of an account, using the existing `zoom/partials/status_tag.html` (icon plus word).
   - **Accessible name:** it also includes the end time and the reference, for example `8:30 am to 11:30 am, ZL-0042, CCC Batch 3 - Mathematics, Zoom 03`, or `…, Waiting for IT`. The extra words are visually hidden.
   - **Order:** by start time, then pk.
   - **Excluded:** classes of `unverified` and `rejected` requests never appear.
   - **Recording:** a `Recording asked for` marker (`zoom/partials/recording_tag.html`) is the designer's choice.
9. **Too many for the box.** The cap is one constant, `timetable.DAY_BOX_LIMIT = 3`. The designer may change the number, but it lives only there.
   - A day with 3 entries or fewer shows them all.
   - A day with **n > 3** entries shows the first 3, then the link `+{n−3} more` → `zoom:timetable_day` for that date, keeping `account`. Its accessible name is `{n−3} more classes on Wed 7 Oct` (`1 more class on …` when it's one).
   - A test puts 5 entries on Wed 7 Oct 2026 and sees 3 entry links plus `+2 more`.
10. **Time zone edges.**
    - A booked class starting `2026-09-30 19:00Z` (1 Oct, 00:30 local time) appears in the **1 Oct** box of October, and not in September.
    - One starting `2026-08-31 18:30Z` (1 Sep, 00:00 local time) appears in the 1 Sep box.
    - One starting `2026-09-30 18:25Z` (30 Sep, 23:55 local time) appears on 30 Sep.
11. **Account filter.**
    - **The form:** a GET form with a `<select name="account">` labelled `Show`. The options are `All accounts` (empty value), then `HostAccount.objects.timetable_accounts(start, end)`: every `bookable()` account, plus any other account with a booked class in the month, ordered by `(sort_order, label)`. It has a hidden `month` input and a `Show` button.
    - **Filtering:** with `?account=<pk>`, only that account's booked classes appear, and **waiting classes are left out** because they hold no account (D1). The select keeps the choice.
    - **Bad values:** an unknown, non-numeric or deleted pk quietly falls back to all accounts, with 200.
    - **Accounts outside the list:** filtering to an existing account that isn't in the option list still works and shows its classes. There's nothing to show if none exist.
      - **The dropdown still shows it as chosen (OQ2, D9).** The view **appends** the account to `filter_accounts`, so the select lists it and marks it `selected`. No extra query is needed, because the view already fetched it to resolve the pk.
      - **Test:** filter to an out-of-use account with no classes in the month. Its `<option value="{pk}" selected>` is present exactly once. The query count stays equal to the in-list case.
      - **This rule is shared:** the day view (criterion 14) follows it too.
12. **Summary line** above the grid:
    - all accounts: `{n} booked classes and {w} waiting for IT in September 2026.`;
    - singular forms: `1 booked class`, `1 waiting for IT`;
    - when `w` is 0: `{n} booked classes in September 2026.`;
    - filtered: `{n} booked classes on {label} in September 2026.`
13. **Empty states.** The grid is still rendered with every day box. The line above it reads:
    - `No classes booked in September 2026.`;
    - filtered: `No classes booked on {label} in September 2026.`;
    - with no accounts at all: `No Zoom accounts are set up yet.`, plus a link `Add a Zoom account` → `zoom:account_add` for users with `zoom.add_hostaccount` (brief 008).

### The day view: `zoom:timetable_day`

14. **Page.**
    - **Address:** the path is `zoom/timetable/<int:year>/<int:month>/<int:day>/`. An impossible date (`2026/2/30`) or one outside 2000–2100 gives **404**. This is a path the app builds itself, not a query value.
    - **Headings:** the h1 is `Zoom classes on Wed 7 Oct 2026` (`class_date`), and the `<title>` matches.
    - **Breadcrumb:** `Home › Zoom timetable › Wed 7 Oct 2026`. The `Zoom timetable` crumb links to `month_url` (OQ1, D9). The view builds that string with `reverse("zoom:timetable")` plus a query:
      - unfiltered: `?month=2026-10`;
      - filtered: `?month=2026-10&account=<pk>`.

      The `Back to October 2026` link uses the same string. **Test:** both hrefs equal `month_url` in both cases. The template does no string building for it.
    - **Entries:** every entry of the day, with no cap, as an ordered list sorted by start time, then pk. Each is one link to `zoom:detail` showing:
      - the time range `8:30 am to 11:30 am`;
      - the reference;
      - the class name;
      - the account label, or the `Waiting for IT` tag.
    - **Links:**
      - `Previous day` and `Next day`, keeping `account`;
      - `Back to October 2026`, to the month, keeping `account`.
    - **Account filter:** the same form as criterion 11, with the same rules. Its options are the accounts for that date's month.
    - **Empty:** `No classes on Wed 7 Oct 2026.` (filtered: `No classes on {label} on Wed 7 Oct 2026.`).
15. **The two pages agree.** For any date, the day view lists exactly the entries the month box counts: the shown ones plus `more`. A test compares the two.

### What is never shown

16. **Private data is left out.** Neither page shows any of the following:
    - a host key, its `Saved` / `Not saved` state, or `gAAAAA`;
    - a requester's name, email or phone;
    - a join link, meeting ID or passcode.

    A pytest test renders a busy month and a busy day and asserts that each of these is absent.

### Model layer and performance

17. **Where the logic lives.**
    - `OccurrenceQuerySet.in_period(start, end)`: `starts_at` falls in `[start, end)`.
    - `OccurrenceQuerySet.for_timetable(start, end, account=None)`: `in_period`, limited to booked classes plus waiting classes (booked only when `account` is given). It uses `select_related("link_request", "host_account")` and is ordered by `starts_at`, `pk`. "Booked" is reused from `booked()`, not restated.
    - `HostAccountQuerySet.timetable_accounts(start, end)`: criterion 11's rule, in one query, reusing brief 008's shared bookable condition.
    - **`timetable.py`** holds pure functions with no database access:
      - `Month` (a frozen dataclass): `start` and `end` as aware local datetimes, `value`, `label`, `previous`, `next`, `weeks()`;
      - `parse_month`;
      - `DAY_BOX_LIMIT`;
      - `build_month(month, occurrences, today, limit)`, which returns the `weeks` structure in the context contract;
      - `day_entries(occurrences, day)`.

      They're unit-tested without the database, using unsaved `Occurrence` objects.
    - **Views only** parse the request, call these functions and render. The reviewer checks this.
18. **Query budget.** Each page runs the **same number of SQL queries** in these cases, with and without `?account=`:
    - 3 classes over 2 accounts;
    - 150 classes over 8 accounts, plus 10 waiting, including a day with 12 entries.

    The test uses `django_assert_num_queries` or an equivalent. The expected shape is one query for the filter's accounts and one for the classes, plus the shell's fixed queries.
19. **Scale.** A month with 400 classes renders in under 1 second on the dev stack. The verifier records `curl -w "%{time_total}"`. This is a sanity check, not a benchmark.

### Contextual links

20. On an `approved` request's detail page, `See it on the timetable` → `zoom:timetable?month=<month of its first class>&account=<its host account pk>`. Waiting and rejected requests don't show it.
21. On brief 008's accounts list, each row has `Timetable` → `zoom:timetable?account=<pk>`, shown only when `can_review` is true.

### Semantics, layout, accessibility

22. **A real table (D5).**
    - The grid is a `<table>`: rows are weeks, columns are weekdays, and each day box is a `<td>`.
    - It carries explicit ARIA table roles (`role="table"`, `rowgroup`, `row`, `columnheader`, `cell`), as the queue's datagrid does. That keeps the table semantics when CSS changes `display` for the phone layout.
    - Each in-month cell starts with its `<h3>` date (criterion 7), so screen-reader users can move from day to day by heading.
    - Empty cells outside the month contain nothing.
    - There's one `h1` per page.
23. **Desktop (768px and wider).**
    - Seven equal columns fill the content width, with **no horizontal scroll** at 1024 and 1440 in either colour mode.
    - Long class names **wrap**, breaking anywhere if they must. They're never cut off with an ellipsis.
    - Boxes in a row share the tallest box's height.
24. **Phone (below 768px): a day-by-day list** made by CSS from the same markup (D5):
    - the weekday header row, the empty cells outside the month, and the in-month days with **no entries** are hidden;
    - every remaining day becomes a stacked card, headed by its full date (`Tue 1 Sep`, visible);
    - its entries keep the same cap and `+N more` link.

    There's no horizontal scroll at 320 or 400. There's no second markup tree.
25. **Targets and contrast.**
    - These are at least 44×44 px:
      - each entry link, as a block, full box width, at least 44px tall;
      - the day-number link;
      - `+N more`;
      - the month and day navigation;
      - the `Show` select and button.
    - Contrast meets WCAG AA in both colour modes and on all three sidebar tones.
    - Today never relies on colour alone: it shows the word `Today`. Waiting entries show an icon and a word.
26. **Without JavaScript.** Every link, the filter form, the grid and the phone list work without JS. Any enhancement binds only to `data-*` hooks and is optional. There are no console errors.
27. **Template rules.**
    - `zoom/timetable.html` and `zoom/timetable_day.html` each start with a `{# … #}` header that names its context.
    - Includes end with `only`.
    - There are no inline `style=` attributes and no hard-coded paths.
    - Every icon used is in the sprite, and every sprite icon is used.
    - CSS uses only tokens from the first `:root` block, with no colour literals.
    - The guard tests from briefs 004, 005 and 008 pass unchanged.

### Verification (CLAUDE.md "Verify a change", all five)

28. `ruff check .`, `ruff format --check .`, `pytest --create-db`, `makemigrations --check --dry-run` (no migration expected) and `manage.py check` all pass.
29. **Prod stack.** The verifier starts it with `ZOOM_PROVIDER=manual docker compose up -d --build` and waits for `web` to be healthy. Over HTTP on 8010, an IT user:
    1. approves a test request;
    2. finds it in the right day box, with its account;
    3. sees a waiting request marked `Waiting for IT`;
    4. adds classes until a day overflows, then follows `+N more` to the day view;
    5. filters to one account;
    6. goes to the next month and back;
    7. opens an entry and reaches its detail page.

    Static files must be served from hashed paths with a 200. The verifier restores the previous stack afterwards.

    **Screenshots** (in the scratchpad, not committed):
    - a busy month at 1440, in light and dark;
    - the same month at 1024;
    - the phone list at 400 and 320;
    - the day view at 1440 and 400;
    - the month filtered to one account;
    - an empty month.

## Design decisions needed
<!-- owner: tmd-planner — open questions for the user; "None" if none -->

**None open.** The owner answered Q6 on 2026-09-25. Q1–Q5 are recorded in briefs 008 and 010.

**Owner's answer**

| Q | Question (short) | Owner's answer | Recorded as |
|---|---|---|---|
| Q6 | What shape should the month take? | **"Wall calendar":** a month grid of weeks (Mon–Sun), with day boxes listing time, class and account, pending classes marked with an icon and a word, and `+N more` to a day view. Falls back to a day-by-day list on narrow screens | D8 |

**Decisions**

- **D1: Waiting classes show in their day box, marked `Waiting for IT`, and are hidden when filtering to one account.** They don't hold an account yet (brief 005, D6), so an account filter can't include them. Seeing them beside booked classes is what IT needs before approving.
- **D2: Boxes for days outside the month are empty.** They have no dimmed dates. A greyed "1 Oct" in September's grid, with no classes in it, would suggest October has nothing booked, and each month has its own page anyway. Empty cells also disappear cleanly in the phone list.
- **D3: A class's day is its local start date in Asia/Colombo.** Classes are same-day (brief 005, criterion 6), so a class never spans two boxes. The month and day bounds are local midnights, converted to UTC for the query.
- **D4: Bad query values fall back quietly, and bad day paths give 404.** Query values come from links and a form, so silently showing the current month or all accounts is kinder than an error. A day-view path that isn't a real date is a broken address, so it gets 404.
- **D5: A real `<table>` with explicit ARIA roles, one markup tree, and a CSS reflow for phones.**
  - A month grid is two-dimensional data: every box is "this weekday, in this week". A table lets screen readers announce the weekday column with each box.
  - Headings on each date let people move from day to day.
  - The explicit roles keep that meaning when the phone layout changes `display`, which is the same technique the queue's datagrid uses.
  - A second, list-only markup tree was rejected: it would double the HTML and give the entries two sources of truth.
- **D6: The cap is 3 per box, and overflow goes to a day view on its own page, not an anchor.**
  - A page anchor would need every entry of the month rendered twice (once capped in the grid, once in full) or hidden content to jump to.
  - A day view is a small second page that reuses the same queries and grouping. It can be bookmarked, and on a phone it's the natural "open this day" screen.
  - The day number links there too, so every day has a way in, not only the busy ones.
- **D7: Same permission as the queue** (`zoom.review_linkrequest`). Every entry links to a request detail, which needs that permission. Since brief 008, every IT desk member has it, alongside the account permissions.
- **D9: The designer's OQ1 and OQ2, resolved by the main session on 2026-09-25: both "yes".**
  - **OQ1:** the day view gets `month_url`, a string built in the view with `reverse()` plus the month and account query. It's the same approach as `timetable_url` on the detail page. The crumb and `Back to …` use it, replacing Design D.2's `{% with %}` / `|add` / `stringformat` chain.
  - **OQ2:** when the filtered account isn't in the choosable set, the view appends it to `filter_accounts`, so the select shows it as selected. This replaces Design D.2's extra-`<option>` workaround.
  - **Why:** in both cases a small piece of logic moves out of the template and into the view. Templates stay presentation-only.
  - **Where it's pinned:** criteria 11 and 14.
- **D8: A wall calendar, weeks Monday to Sunday (owner, Q6).** Sri Lanka's calendars and ISO 8601 both start the week on Monday. This matches Python's `date.isoweekday()` and brief 005's ISO weekday numbering (1 = Monday). The spreadsheet-style option, with one row per day and one column per account, was not chosen. Filtering by account covers "is this account free on this day?".

## MVT plan
<!-- owner: tmd-planner -->

### Models

No fields, no migrations.

- **`OccurrenceQuerySet` (`apps/zoom/models.py`):**
  - `in_period(start, end)` → `filter(starts_at__gte=start, starts_at__lt=end)`.
  - `for_timetable(start, end, account=None)`:
    - without an account: `in_period(...)` filtered to (booked) OR (`link_request__status=WAITING`);
    - with an account: `booked().filter(host_account=account).in_period(...)`;
    - then `select_related("link_request", "host_account").order_by("starts_at", "pk")`.

    "Booked" is taken from `booked()`'s condition, for example as a shared `Q`, and isn't restated.
- **`HostAccountQuerySet.timetable_accounts(start, end)`:** accounts matching brief 008's shared bookable `Q`, OR having a booked occurrence in the period (use an `Exists` subquery). Ordered by `sort_order`, `label`. One query.
- **`apps/zoom/timetable.py`** (new and pure; docstrings explain *why*):
  - `DAY_BOX_LIMIT = 3`.
  - `Month`, a frozen dataclass with `year` and `month`, and these properties:
    - `start` / `end`: aware local midnights in `timezone.get_default_timezone()`;
    - `value` (`"2026-09"`), `label` (`"September 2026"`);
    - `previous`, `next`;
    - `contains(date)`;
    - `weeks() -> list[list[date | None]]` (Monday first, criterion 6).
  - `Month.for_date(d)`.
  - `parse_month(value, today) -> Month`.
  - `build_month(month, occurrences, today, limit=DAY_BOX_LIMIT) -> list[list[DayBox | None]]`. Groups by `timezone.localdate(o.starts_at)`.
  - `day_entries(occurrences, day) -> list[Occurrence]`.

### URLs and views

| Name | Path | View | Template | Permission |
|---|---|---|---|---|
| `zoom:timetable` | `zoom/timetable/` | `TimetableMonthView(ReviewerRequiredMixin, TemplateView)`: see below | `zoom/timetable.html` | `zoom.review_linkrequest` |
| `zoom:timetable_day` | `zoom/timetable/<int:year>/<int:month>/<int:day>/` | `TimetableDayView(ReviewerRequiredMixin, TemplateView)`: see below | `zoom/timetable_day.html` | `zoom.review_linkrequest` |

- **`TimetableMonthView`:**
  1. parses `month` and `account`;
  2. calls `timetable_accounts` and resolves the selected account from that list. If the pk isn't in the list, it runs one extra `filter(pk=…).first()`. That query runs in every case where a pk was given, so the count stays fixed per case;
  3. calls `for_timetable` and `build_month`;
  4. computes the counts in Python.
- **`TimetableDayView`:** builds the `date` (an invalid one raises `Http404`), uses `Month.for_date` for the filter's accounts, and calls `for_timetable` over that local day's `[00:00, next 00:00)`.
- **Also changed:**
  - the detail view's context gains `timetable_url` (criterion 20);
  - brief 008's list view already passes `can_review` (criterion 21).

**Information architecture** (`ux-strategy:information-architecture`):

```
SHELL (signed in)
[Zoom links]
├── Link requests   zoom:queue            review_linkrequest
│   └── ZL-0042 …   zoom:detail ──"See it on the timetable"──┐
├── Timetable       zoom:timetable        ◄───────────────────┘   ?month=YYYY-MM &account=<pk>
│   │   day number / "+N more" ──► zoom:timetable_day (Wed 7 Oct 2026)   prev/next day, back to month
│   └── entries (month and day) ──► zoom:detail
└── Zoom accounts   zoom:accounts ──row "Timetable"──► zoom:timetable?account=<pk>
[Administration]
```

- **Labels.** The sidebar says `Timetable`, the team's own word (the sheet was `ZOOM TIME TABLE`). The h1 says `Zoom timetable`. The day view names the date in its h1. `Waiting for IT` reuses brief 005's status wording.
- **Wayfinding.** The sidebar item, breadcrumb and h1 agree. The month or date is always in the h2 or h1 and in the `<title>`. The day view's breadcrumb leads back to its month. Neither page is more than two levels below Home.
- **Query state lives in the URL**, so a view can be bookmarked and shared.

### Context contract
<!-- The only coupling between backend and frontend: template → exact context variables and their types -->

**Everywhere:** as in brief 005.

**`partials/sidebar.html`:** no new parameters. `Timetable` shows when `perms.zoom.review_linkrequest` is set. It is current when `current` is `zoom:timetable` or `zoom:timetable_day`.

**Entry objects**, the same on both pages. Each entry is an `Occurrence` with:

- `starts_at`, `ends_at`: aware UTC; the template shows them with `class_time`;
- `host_account`: select_related; `label`; `None` for a waiting class;
- `link_request`: select_related; `pk`, `reference`, `class_name`, `wants_recording`, `status`, `get_status_display`.

Templates never follow any other relation.

**`zoom/timetable.html`** (`TimetableMonthView`):

| Variable | Type | Notes |
|---|---|---|
| `month` | `Month` | `value`, `label`, `start` |
| `previous_month`, `next_month` | `Month` | `.value` for links, `.label` for accessible names |
| `is_current_month` | bool | Hides `This month` when true |
| `weeks` | list of 7-item lists of `DayBox` dict or `None` | `None` means a day outside the month (an empty cell). `DayBox` is `{date: date, label: str ("Tue 1 Sep", class_date without year), is_today: bool, entries: list[Occurrence] (at most DAY_BOX_LIMIT, sorted), more: int (0 if none)}`. The day-view URL is built in the template: `{% url 'zoom:timetable_day' box.date.year box.date.month box.date.day %}` |
| `weekdays` | list[str] | `["Monday", …, "Sunday"]`, from `models.WEEKDAY_NAMES`, so the names aren't written out a second time |
| `filter_accounts` | list[`HostAccount`] | `pk`, `label`. The select's options, in order. **It always contains `selected_account` when one is set**: if the filtered account isn't in the choosable set, the view appends it (OQ2, D9, criterion 11). The template just marks the option whose `pk` equals `selected_account.pk` as `selected`, and does no membership logic |
| `selected_account` | `HostAccount` or `None` | |
| `show_waiting` | bool | `selected_account is None` |
| `booked_count`, `waiting_count` | int | For the summary line |
| `has_accounts` | bool | `False` gives criterion 13's "no accounts" state |
| `can_add_account` | bool | |

**`zoom/timetable_day.html`** (`TimetableDayView`):

| Variable | Type | Notes |
|---|---|---|
| `day` | date | |
| `day_label` | str | `class_date` with the year: `Wed 7 Oct 2026` |
| `previous_day`, `next_day` | date | Links: `{% url 'zoom:timetable_day' … %}` |
| `month` | `Month` | `.label` for the `Back to October 2026` text |
| `month_url` | str | **OQ1, D9.** Built in the view: `reverse("zoom:timetable")` + `?month={month.value}`, plus `&account={selected_account.pk}` when filtered. It's the `url` passed to `partials/crumb.html` for the `Zoom timetable` crumb, and the href of `Back to …` (criterion 14) |
| `entries` | list[Occurrence] | Every entry that day, sorted |
| `filter_accounts`, `selected_account`, `show_waiting` | as on the month page | The same append rule (OQ2) |

- **URLs** are built in the templates from `{% url %}` plus `?month=` / `&account=`, following the queue's pattern. The views build URL strings in only two places, both with `reverse()` plus a query string: `timetable_url` on the detail page, and `month_url` on the day view.
- **`zoom/detail.html`** gains `timetable_url` (str or `None`).

### Placement and reuse

- **`apps/zoom`:**
  - `models.py`: three QuerySet methods;
  - `timetable.py`: new;
  - `views.py`: two views, plus `timetable_url` on the detail view;
  - `urls.py`: two routes;
  - tests: `tests/test_timetable.py`, plus the deliberate sidebar-test edits.
- **`templates/`:**
  - new: `zoom/timetable.html`, `zoom/timetable_day.html`, and optionally `zoom/partials/timetable_entry.html`, so both pages render an entry from one place;
  - changed: `zoom/detail.html`, `zoom/accounts.html` (brief 008), `partials/sidebar.html`;
  - changed: `partials/icons.html`, which gains **Feather `calendar` (`i-calendar`)**, used by the sidebar's `Timetable` item and the empty day view (Design, "New icon"). Every other icon is already in the sprite (`chevron-left`, `chevron-right`, `clock`, `film`, and brief 008's `plus`).
- **`static/css/style.css`:**
  - **the new `.cal` component** (`.cal-nav`, `.cal`, `.cal__day…`, `.cal__entry…`, `.cal__more`, `.cal-list`, `.cal__ref`), specified in **`docs/design/month-calendar.md`**: the calendar grid, day boxes, entries, today, the phone reflow and the day list;
  - **four new tokens**, added to the layout-geometry group of the first `:root` block, and only there:

    | Token | Value | Used for |
    |---|---|---|
    | `--cal-day-min` | `120px` | Minimum height of a day box |
    | `--cal-num` | `28px` | The round "today" marker |
    | `--cal-time-w` | `11em` | Day list, time-range column |
    | `--cal-ref-w` | `6.5em` | Day list, reference column |

  - everything else uses existing tokens; there are no colour literals (criterion 27).
- **Reused:**
  - from brief 005: `ReviewerRequiredMixin`, `booked()`, `WEEKDAY_NAMES`, the `class_date` / `class_time` filters, `status_tag.html`, `recording_tag.html`, the datagrid's explicit-roles reflow technique, `.tag`, `.box`, `.notice`, `.empty` and `.pager`-style navigation;
  - from brief 008: the shared bookable condition;
  - `partials/crumb.html`.
- **Not built:** a JS calendar library, a month picker, an export, models, settings or dependencies.

## Agent plan
<!-- owner: tmd-planner — ordered steps; mark steps that can run in parallel -->

1. **`tmd-ui-designer`:** the Design section. It covers:
   - the desktop grid: weekday header, box anatomy (day-number heading, entries, `+N more`), today, empty out-of-month cells, and the waiting marker;
   - the month bar and the filter;
   - the summary and empty states;
   - the phone list;
   - the day view;
   - the sidebar icon.

   It confirms or changes `DAY_BOX_LIMIT`. **This step may run while 008 or 010 is still being built.**
2. **In parallel, once the Design section is in and 010 is Done** (they share the sidebar):
   - **2a. `tmd-django-backend`:** the QuerySet methods, `timetable.py`, both views and URLs, `timetable_url`, and the tests. Criteria 1, 4, 6 (data), 9–12, 14–21.
   - **2b. `tmd-frontend`:** both templates, the entry partial, the detail and accounts-list links, the sidebar item and icon, and the CSS. Criteria 2–3, 5, 7–8, 13, 22–27.
3. **`tmd-test-verifier`:** criteria 1–29. A FAIL goes back to 2a or 2b.
4. **`tmd-code-reviewer`:** reviews read-only. The focus:
   - the grid logic lives in `timetable.py`, and the views stay thin;
   - the fixed query count;
   - time zones and the Monday start;
   - no private data on either page;
   - table semantics through the reflow.

   Changes go back to step 2, then step 3.
5. **`tmd-docs-writer`:** updates the README (the timetable, who can see it, and the day view), the `zoom` bullet in CLAUDE.md and `docs/CHANGELOG.md`, then closes the brief.

## Design
<!-- owner: tmd-ui-designer — layout + wireframes, components (existing classes), states, copy, accessibility, progressive enhancement -->

### D.0 Summary

- **Both pages sit in the shell.** Each is one `.box`:
  - **Month page:** the box head holds the month `<h2>` and the month navigation. The body holds the account filter, the summary line and the calendar table.
  - **Day view:** the box head holds the day navigation. The body holds the same filter, a count line and the day list.
- **One new component, `.cal`,** is specified in `docs/design/month-calendar.md`. It covers the navigation bar, the month grid with its phone reflow, the entry link, and the day list. Everything else reuses existing classes: `.box`, `.button`, `.finder__search`, `.field`, `.input`, `.result-line`, `.empty`, `.disc`, `.tag`, `.tags`, `.tap-link`, `.visually-hidden`, and the `status_tag` and `recording_tag` partials.
- **`DAY_BOX_LIMIT` stays at 3.** At 1024px with the standard sidebar, a column is about 96px wide. Three entries plus `+N more` keep a busy week at about 300px tall, which is still readable on a laptop screen. Four entries would push one week past the screen height.
- **Recording marker:** it is shown **on the day view only**. A month box is too narrow for a second tag. The day view is where IT checks the details, and the tag is there.
- **New icon:** Feather `calendar` (`i-calendar`), used for the sidebar item and the empty day view. Existing icons are reused: `chevron-left`, `chevron-right`, `clock` (through `status_tag`), `film` (through `recording_tag`), and brief 008's `plus` for `Add a Zoom account`.
- **No JavaScript.** Nothing on either page needs it (D.6).

### D.1 Layout

**Content width at the tightest desktop size.** At 992–1024px the sidebar is fixed at 250px (standard width), which leaves about 680px inside the box, or about 96px per column. The table is therefore placed **flush in the box, with no `.box__body` side padding around it** (the body is split, see below). Its cells use `var(--space-1)` padding. The grid's outer border lines sit on the box's own border. With the compact or icon sidebar, and at 1440, the columns are simply wider. `table-layout: fixed` keeps all seven equal and prevents horizontal scroll (criterion 23).

**Box structure (month page).** Top to bottom:

1. `section.box` with `aria-labelledby="month-title"`.
2. `.box__head`: `h2.box__title#month-title` (the month), then `nav.cal-nav`.
3. `.box__body`: the filter form (wrapped in `.box__form` so the select keeps a readable width), then `p.result-line` (the summary or empty line). The `.result-line`'s bottom margin is dropped here with a `.box__body > :last-child { margin-bottom: 0 }`-style rule; the frontend picks the selector.
4. The `table.cal`, a **direct child of the box**, after `.box__body`. It has no padding wrapper.

#### Desktop (768px and wider), month page, 1440 wide, light mode

```
┌ sidebar ┐┌───────────────────────────────────────────────────────────────────────────────────────┐
│ Zoom    ││ Zoom timetable                                          Home › Zoom timetable          │ ← h1 + crumbs (shell)
│  links  │├───────────────────────────────────────────────────────────────────────────────────────┤
│ ▸ Link  ││┌─────────────────────────────────────────────────────────────────────────────────────┐│
│  reqs   │││ September 2026 (h2)             [‹ Previous month] [This month] [Next month ›]      ││ ← .box__head
│ ▸Timeta-││├─────────────────────────────────────────────────────────────────────────────────────┤│
│  ble ◀  │││ Show                                                                                ││ ← .box__body
│ ▸ Zoom  │││ Pick one account to see only its classes. Classes waiting for IT are hidden then …  ││
│  accts  │││ [ All accounts            ▾]  [ Show ]                                              ││
│         │││                                                                                     ││
│         │││ 42 booked classes and 3 waiting for IT in September 2026.                           ││ ← .result-line
│         ││├──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┤│
│         │││ Mon      │ Tue      │ Wed      │ Thu      │ Fri      │ Sat      │ Sun      ││ ← thead
│         ││├──────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤│
│         │││░░░░░░░░░░│ 1        │ 2        │ 3        │ 4        │ 5        │ 6        ││
│         │││░░░░░░░░░░│┃8:30 am  │┃4:00 pm  │          │          │┃8:30 am  │          ││
│         │││░░░░░░░░░░│┃CCC Batch│┃Grade 10 │          │          │┃A/L Phys-│          ││
│         │││░░(31 Aug,│┃3 - Maths│┃Science  │          │          │┃ics Revis│          ││
│         │││░░ empty) │┃Zoom 03  │┃Zoom 01  │          │          │┃ion      │          ││
│         │││░░░░░░░░░░│          │╎9:00 am ╎│          │          │┃Zoom 02  │          ││
│         │││░░░░░░░░░░│          │╎Grade 6 ╎│          │          │          │          ││
│         │││░░░░░░░░░░│          │╎[◷ Wait-╎│          │          │          │          ││
│         │││░░░░░░░░░░│          │╎ing for ╎│          │          │          │          ││
│         │││░░░░░░░░░░│          │╎ IT]    ╎│          │          │          │          ││
│         ││├──────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤│
│         │││ 7        │ 8 …      │          │          │          │          │          ││
│         │││┃7:30 am  │          │          │          │          │          │          ││
│         │││┃…  ×3    │          │          │          │          │          │          ││
│         │││ +2 more  │          │          │          │          │          │          ││ ← .cal__more
│         ││├──────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤│
│         │││ …        │          │          │          │          │          │          ││
│         ││├━━━━━━━━━━┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤│
│         │││(28) Today│ 29       │ 30       │░░░░░░░░░░│░░░░░░░░░░│░░░░░░░░░░│░░░░░░░░░░││ ← today: circle, word, top bar
│         │││┃8:30 am  │          │          │░░░░░░░░░░│░░░░░░░░░░│░░░░░░░░░░│░░░░░░░░░░││
│         ││└──────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘│
└─────────┘└───────────────────────────────────────────────────────────────────────────────────────┘
 ┃ = booked entry: primary-soft fill and left bar     ╎ = waiting entry: dashed outline, amber left bar, tag
 ░ = a day outside the month: flat surface-2 fill, nothing inside
```

- At **1024** (standard sidebar) it's the same grid with about 96px columns. The navigation buttons wrap under the h2 if they don't fit on one line (`.box__head` already wraps).
- **Row height:** every box is at least `--cal-day-min` (120px) tall, and all boxes in a week match the tallest (table behaviour, criterion 23).

#### Phone (below 768px), month page, 400 wide

The same markup, reflowed by CSS (criterion 24):

```
┌──────────────────────────────────────┐
│ ☰  (top bar)                          │
│ Zoom timetable                        │ h1
│ Home › Zoom timetable                 │
│┌────────────────────────────────────┐│
││ September 2026                     ││ h2
││ [‹ Previous month][ Next month › ] ││ 2-col grid, 44px
││ [          This month           ]  ││ only when not current
│├────────────────────────────────────┤│
││ Show                               ││
││ Pick one account to see only its … ││
││ [ All accounts                  ▾] ││ full width
││ [              Show             ]  ││ full width (finder__search <600)
││                                    ││
││ 42 booked classes and 3 waiting    ││
││ for IT in September 2026.          ││
││ ┌────────────────────────────────┐ ││
││ │ Tue 1 Sep                      │ ││ h3 link, 44px
││ │┃8:30 am                        │ ││ entry ≥56px
││ │┃CCC Batch 3 - Mathematics      │ ││
││ │┃Zoom 03                        │ ││
││ └────────────────────────────────┘ ││
││ ┌────────────────────────────────┐ ││
││ │ Wed 2 Sep                      │ ││
││ │┃4:00 pm                        │ ││ lines stack as on
││ │┃Grade 10 Science / Zoom 01     │ ││ desktop
││ │╎9:00 am / Grade 6             ╎│ ││
││ │╎[◷ Waiting for IT]            ╎│ ││
││ └────────────────────────────────┘ ││
││ ┌━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┐ ││
││ │ Mon 28 Sep  [Today]            │ ││ top bar + word
││ │┃8:30 am …                      │ ││
││ └────────────────────────────────┘ ││
│└────────────────────────────────────┘│
└──────────────────────────────────────┘
```

On phones:

- The weekday header is visually hidden. The empty out-of-month cells, and every in-month day without classes, are clipped with their contents hidden, never `display: none` (see "Column positions" under Accessibility).
- There's still no second markup tree.
- At **320** the cards simply get narrower. Names wrap anywhere. `.cal__time` doesn't wrap, and at 7 characters it fits.

#### Day view, desktop (1440)

```
│ Zoom classes on Wed 7 Oct 2026                    Home › Zoom timetable › Wed 7 Oct 2026 │
│┌──────────────────────────────────────────────────────────────────────────────────────┐│
││ [‹ Previous day]   [Back to October 2026]   [Next day ›]                              ││ .box__head (no h2)
│├──────────────────────────────────────────────────────────────────────────────────────┤│
││ Show / help / [ All accounts ▾] [ Show ]                                              ││
││ 5 classes on Wed 7 Oct 2026.                                                          ││ .result-line
││┃ 7:30 am to 9:30 am   ZL-0038  Grade 11 English                   Zoom 01          ┃││ .cal__entry--row
││┃ 8:30 am to 11:30 am  ZL-0042  CCC Batch 3 - Mathematics           Zoom 03 [▶ Rec…] ┃││   56px tall
││╎ 9:00 am to 10:00 am  ZL-0051  Grade 6 Tamil               [◷ Waiting for IT]       ╎││
││┃ …                                                                                   ┃││
│└──────────────────────────────────────────────────────────────────────────────────────┘│
```

- **Columns:** time `--cal-time-w`, reference `--cal-ref-w`, name `1fr`, then `.tags` (the account or the waiting tag, then the recording tag).
- **The day list stays inside `.box__body`,** padded. It doesn't need to be flush like the grid.

#### Day view, phone (400)

```
│ Zoom classes on Wed 7 Oct 2026        │
│ Home › Zoom timetable › Wed 7 Oct 2026│
│┌────────────────────────────────────┐│
││ [‹ Previous day ][  Next day ›    ] ││
││ [      Back to October 2026      ]  ││
│├────────────────────────────────────┤│
││ Show … [All accounts ▾] [Show]      ││ stacked
││ 5 classes on Wed 7 Oct 2026.        ││
││┃7:30 am to 9:30 am                  ││ one column per entry:
││┃ZL-0038                             ││ time, ref, name, tags
││┃Grade 11 English                    ││
││┃Zoom 01                             ││
││ …                                   ││
│└────────────────────────────────────┘│
```

### D.2 Components

| Where | Class / partial | New? |
|---|---|---|
| Page frame, h1, crumbs | shell blocks, `partials/crumb.html` | reused |
| Month / day box | `.box`, `.box__head`, `.box__title`, `.box__body`, `.box__form` | reused |
| Month / day navigation | `.cal-nav` + `.button--secondary` / `.button--quiet` | `.cal-nav` new (layout only) |
| Account filter | `form.finder__search` (`role="search"` is **not** used: it's a filter, not a search), `.field`, `.field__label`, `.field__help`, `select.input`, `.button--primary` | reused |
| Summary / empty line | `.result-line` | reused |
| Month grid, day box, entry, `+N more`, today | `.cal`, `.cal__day(--out/--empty/--today)`, `.cal__head`, `.cal__date`, `.cal__date-link`, `.cal__date-extra`, `.cal__num`, `.cal__entries`, `.cal__entry(--waiting)`, `.cal__more` | **new**, `docs/design/month-calendar.md` |
| Day list | `.cal-list`, `.cal__entry--row`, `.cal__ref` | **new**, same file |
| Waiting marker | `zoom/partials/status_tag.html` (`tag--warn`, `clock`, `Waiting for IT`) | reused |
| Recording marker (day view) | `zoom/partials/recording_tag.html` | reused |
| Today word | `.tag.tag--brand` with the text `Today` (no icon: it isn't a status) | reused |
| Empty day view | `.empty` + `.disc.disc--64` + `i-calendar` | reused (+ icon) |
| Contextual links | `.tap-link` | reused |

**One entry partial:** `zoom/partials/timetable_entry.html`, `with entry=<Occurrence> full=<bool> only`. `full=False` renders the month-box entry and `full=True` the day-list row. The markup of both is in the component note. Rules the partial owns:

- **Waiting or booked:** decided by `entry.link_request.status == "waiting"`, which adds `cal__entry--waiting` and renders `status_tag.html` with `status=entry.link_request.status label=entry.link_request.get_status_display`. Otherwise it shows `entry.host_account.label` in `.cal__account`.
- **Accessible name (month, criterion 8):** visible `{{ starts_at|class_time }}`, hidden ` to {{ ends_at|class_time }}, {{ reference }},`, visible name, hidden `,`, then the account or the tag. Keep a literal space or newline between the `<span>`s so the computed name reads `8:30 am to 11:30 am, ZL-0042, CCC Batch 3 - Mathematics, Zoom 03`.
- **`full=True`:** visible `{{ starts_at|class_time }} to {{ ends_at|class_time }}`, then the reference, the name, and `.tags` holding the account (or the waiting tag) plus `recording_tag.html` when `wants_recording`. Each of the first three is followed by a hidden `,`.
- **Escaping:** the class name is autoescaped and never `|safe`.

**Month-box markup order inside each in-month `<td>`:** `.cal__head` (`h3` date link, then the `Today` tag when `box.is_today`), then `ul.cal__entries` (only if `box.entries`), then `a.cal__more` (only if `box.more`).

**Date heading pieces.** The template builds these from `box.date`: `{{ box.date|date:"D" }} ` + `{{ box.date|date:"j" }}` + ` {{ box.date|date:"M" }}`. The first and last pieces are in `.cal__date-extra` (hidden on desktop, shown on phones). The number is in `.cal__num`. They all sit inside `<time datetime="{{ box.date|date:'Y-m-d' }}">`. This yields the accessible text `Tue 1 Sep` (criterion 7), which matches `box.label`. `box.label` is used for the `+N more` hidden text.

**Cell classes:** `None` → `<td role="cell" class="cal__day cal__day--out"></td>` with nothing inside, not even whitespace-only markup that matters. In-month without entries → add `cal__day--empty`. Today → add `cal__day--today` and `aria-current="date"`.

**Link query strings** follow the queue's inline pattern. Set `{% url 'zoom:timetable' as month_page_url %}` once at the top of the block. Don't call it `timetable_url`, which is the detail page's context name.

- **Month links:** `{{ month_page_url }}?month={{ previous_month.value }}{% if selected_account %}&amp;account={{ selected_account.pk }}{% endif %}`.
- **Day-box links:** `{% url 'zoom:timetable_day' … %}{% if selected_account %}?account={{ selected_account.pk }}{% endif %}`.
- **`This month`:** `{{ month_page_url }}{% if selected_account %}?account=…{% endif %}`.
- **The day view's `Zoom timetable` crumb:** `partials/crumb.html` takes a single `url` string. Build it with `{% with %}` and `|add`, turning the pk into a string first (`selected_account.pk|stringformat:"d"`), because `add` on a str and an int returns `""`. If the frontend finds that too awkward, see open question OQ1.

**Filter form markup (both pages):**

```html
<div class="box__form">
  <form class="finder__search" method="get" action="{{ this page's URL without query }}">
    <input type="hidden" name="month" value="{{ month.value }}">   <!-- month page only -->
    <div class="field">
      <label class="field__label" for="account">Show</label>
      <p class="field__help" id="account-help">…</p>
      <select class="input" id="account" name="account" aria-describedby="account-help">
        <option value="">All accounts</option>
        {% for a in filter_accounts %}<option value="{{ a.pk }}"{% if selected_account and a.pk == selected_account.pk %} selected{% endif %}>{{ a.label }}</option>{% endfor %}
      </select>
    </div>
    <button class="button button--primary" type="submit">Show</button>
  </form>
</div>
```

- **An account that isn't in `filter_accounts`** (criterion 11, last bullet): if `selected_account` is set but not among the options, add it as an extra `<option selected>` right after `All accounts`, so the select never shows a choice the page isn't displaying. The template can't test membership cheaply. Alternatively, the backend appends it to `filter_accounts` (OQ2).
- **When there's nothing to choose:** if `filter_accounts` is empty and `selected_account` is `None`, the whole form is left out.

**Sidebar:** `Timetable` with `i-calendar`, between `Link requests` and `Zoom accounts`, using the existing `.sidenav__link` markup.

**Contextual links:**

- **Detail page (criterion 20):** inside the `Booked on` `<dd>`, after the email, add `<br>` or a block `<span>` holding `<a class="tap-link" href="{{ timetable_url }}">See it on the timetable</a>`. Show it only `{% if timetable_url %}`.
- **Accounts list (criterion 21):** in brief 008's row actions, add `<a class="tap-link" href="{% url 'zoom:timetable' %}?account={{ account.pk }}">Timetable<span class="visually-hidden"> for {{ account.label }}</span></a>`, shown only `{% if can_review %}`. Brief 008's design owns the row layout. If it already has an action group, this link joins it in the same style as its siblings.

### D.3 States

**Month page.** The `.result-line` text is chosen in this order, and the first match wins:

| # | Condition | Line above the grid | Extra |
|---|---|---|---|
| 1 | `not has_accounts` | `No Zoom accounts are set up yet.` | If `can_add_account`: `a.button.button--secondary` with the `plus` icon, `Add a Zoom account` → `zoom:account_add`, placed after the line. Otherwise: ` Ask the person who manages Zoom accounts to add one.` in the same line. The grid still renders; waiting classes (which need no account) still show in it |
| 2 | `selected_account` and `booked_count == 0` | `No classes booked on {label} in September 2026.` | After it, `a.button.button--quiet`: `Show all accounts` → `?month={value}`. Waiting classes aren't shown while filtered (D1), so this is the only way back to them without using the select |
| 3 | no account, `booked_count == 0` and `waiting_count == 0` | `No classes booked in September 2026.` | none |
| 4 | `selected_account` | `{n} booked class{es} on {label} in September 2026.` | none |
| 5 | `waiting_count == 0` | `{n} booked class{es} in September 2026.` | none |
| 6 | otherwise | `{n} booked class{es} and {w} waiting for IT in September 2026.` | none |

With `booked_count == 0` and `waiting_count > 0` and no filter, row 6 applies: `0 booked classes and 2 waiting for IT in September 2026.` That's accurate, and it tells IT there's work to do.

**Grid states:**

| State | Look |
|---|---|
| Default | Day boxes with entries, as in D.1 |
| Busy day (> 3) | 3 entries, then `+{n} more` |
| Empty month / filtered to nothing | The full grid of empty boxes on desktop, each with its date link. On phones every day is hidden, so only the line (and `Show all accounts` when filtered) shows under the filter. That's intentional: the line says it all |
| Today in view | Today's box marked, per the component note. Other months have no marker |

**Other states:**

- **Loading:** none. The page is a single server render with no async parts.
- **Validation errors:** none. Bad `month` and `account` values fall back quietly (D4). There is no error message, and the select shows `All accounts` so the page doesn't contradict itself.
- **Success feedback:** none. The page is read-only.
- **Server error:** the app's standard 500 page.
- **No permission:** the standard 403 page. Anonymous visitors go to the sign-in page with `next` (criterion 1). The sidebar item is hidden without `review_linkrequest`.

**Day view:**

| State | Look |
|---|---|
| Default | `.result-line`: `{n} class{es} on Wed 7 Oct 2026.`, or `{n} class{es} on {label} on Wed 7 Oct 2026.` when filtered, using `entries|length`. Then the `.cal-list` |
| Empty | No `.result-line`. Instead, `.empty` shows `span.disc.disc--64` with `i-calendar`, then `<h2>No classes on Wed 7 Oct 2026.</h2>` and `<p>Use Previous day or Next day to look at other dates.</p>` |
| Empty, filtered | `<h2>No classes on {label} on Wed 7 Oct 2026.</h2>`, `<p>Classes waiting for IT are hidden while one account is chosen.</p>`, then `a.button.button--secondary` `Show all accounts` → this day's URL with no query |
| Impossible date | 404 (the standard page) |

### D.4 Copy

**Month page**

| Item | Text |
|---|---|
| `<title>` | `Zoom timetable, September 2026` (+ ` · {site}` from the shell) |
| h1 | `Zoom timetable` |
| Crumbs | `Home › Zoom timetable` |
| Sidebar | `Timetable` |
| h2 | `September 2026` |
| Navigation label (`aria-label`) | `Choose a month` |
| Previous | visible `Previous month`, hidden `, August 2026` |
| Current | `This month` |
| Next | visible `Next month`, hidden `, October 2026` |
| Filter label | `Show` |
| Filter help | `Pick one account to see only its classes. Classes waiting for IT are hidden then, because they don't have an account yet.` |
| First option | `All accounts` |
| Button | `Show` |
| Caption (visually hidden) | `Zoom classes in September 2026, by week, Monday to Sunday.` |
| Column heads | visible `Mon` … `Sun`, hidden `Monday` … `Sunday` (from `weekdays`; the short form is `{{ name|slice:":3" }}`) |
| Day heading | visible `1` (desktop) / `Tue 1 Sep` (phone), accessible `Tue 1 Sep` |
| Today | `Today` |
| Overflow | visible `+2 more`, accessible `2 more classes on Wed 7 Oct` / `1 more class on Wed 7 Oct` |
| Waiting | `Waiting for IT` (from `get_status_display`) |
| Summary / empty lines | as in D.3 |
| Clear the filter | `Show all accounts` |
| No accounts | `No Zoom accounts are set up yet.` + `Add a Zoom account`, or `Ask the person who manages Zoom accounts to add one.` |

**Day view**

| Item | Text |
|---|---|
| `<title>` and h1 | `Zoom classes on Wed 7 Oct 2026` |
| Crumbs | `Home › Zoom timetable › Wed 7 Oct 2026` |
| Navigation label | `Choose a day` |
| Previous | visible `Previous day`, hidden `, {{ previous_day|class_date }}` |
| Back | `Back to October 2026` |
| Next | visible `Next day`, hidden `, {{ next_day|class_date }}` |
| Filter | as on the month page |
| Count line | `5 classes on Wed 7 Oct 2026.` / `1 class on Zoom 03 on Wed 7 Oct 2026.` |
| Empty | `No classes on Wed 7 Oct 2026.` + `Use Previous day or Next day to look at other dates.` |
| Empty, filtered | `No classes on Zoom 03 on Wed 7 Oct 2026.` + `Classes waiting for IT are hidden while one account is chosen.` + `Show all accounts` |

**Elsewhere**

- **Detail page:** `See it on the timetable`.
- **Accounts list:** `Timetable` (+ hidden ` for Zoom 03`).

### D.5 Accessibility

**Headings and landmarks.**

- **Month page:** h1 `Zoom timetable` (shell) → h2 the month (box head) → h3 each in-month day. Out-of-month cells have no heading, so heading navigation (`H` / `3`) moves from day to day.
- **Day view:** h1 only. The empty state adds an h2.
- **Landmarks:** the shell's `main`, plus `nav aria-label="Choose a month"` / `"Choose a day"`. The filter is a plain `form`, not `role="search"`.
- **The month section:** a `section` with `aria-labelledby="month-title"`.

**Table (D5, criterion 22).**

- **Roles:** explicit roles on every level: `table`, `rowgroup`, `row`, `columnheader` and `cell`.
- **Caption:** a `<caption>` visually hidden with `.visually-hidden`. The h2 and summary line say the same thing visibly.
- **Column headers:** the visible short name is `aria-hidden`, and the full name sits in `.visually-hidden`. That way the accessible name is `Monday`, and a screen reader moving across a row announces "Tuesday, heading level 3, Tue 1 Sep".
- **Out-of-month cells** are empty `td`s.
- **Column positions (review round 1, SF1):** never `display: none` a calendar cell; clip it and hide its contents. On phones, out-of-month and empty days are hidden with the `.visually-hidden` clipping declarations, and their contents get `visibility: hidden` so a clipped date link can't take focus. `aria-colcount="7"` sits on the `table` and `aria-colindex` (`1` Monday to `7` Sunday) on every `th` and `td`. Why: `display: none` drops a cell from the accessibility tree, and Chrome takes a cell's column header from its position among the cells that remain, even with `aria-colindex` set, so `Tue 1 Sep` was announced under "Monday". The trade-off: a screen-reader user moving cell by cell meets a blank cell for each out-of-month or empty day.
- **Lists:** `role="list"` on `ul.cal__entries` and `ol.cal-list`, because `list-style: none` drops list semantics in Safari.
- **Today:** `aria-current="date"` goes on the `td`, and the visible `Today` word is in the text.

**Form wiring.**

- The `<label for="account">` and the help `id="account-help"` are joined with `aria-describedby`.
- The form has no validation, so there's no `aria-invalid`.
- The button submits: no auto-submit on change (WCAG 3.2.2).

**Keyboard and focus order (month page)** follows DOM order. It is the same as the reading order:

1. Shell (skip link, sidebar, top bar).
2. `Previous month`, then `This month` (if shown), then `Next month`.
3. The `Show` select, then the `Show` button.
4. The grid, week by week and Monday to Sunday within a week. For each day: the date link, then each entry link, then `+N more`.

Notes on focus:

- **Grid size:** a busy month is about 30 date links plus up to 4 links per day. The skip link and the h3s give fast ways past it.
- **Focus after navigation:** every control is a full page load, so focus starts at the top of the new page as usual. No focus management is needed, and there are no dialogs.
- **Day view order:** `Previous day`, `Back to …`, `Next day`, the select, `Show`, then the entries.

**Targets (criterion 25).**

| Control | Size |
|---|---|
| Entry links | full box width, `min-height: 44px` (56px on phones and in the day list) |
| Date links | at least 44×44 |
| `+N more` | full width, 44px tall |
| Navigation links | `.button`, 44px |
| Select | `.input`, 44px |
| `Show` button | `.button`, 44px |
| Detail and accounts links | `.tap-link`, 44px below 768px |

Adjacent entries have a 4px gap (`--space-1`), so the targets never overlap.

**Colour and status.**

- **Waiting:** shown by the `clock` icon plus `Waiting for IT`, and also by a dashed outline.
- **Today:** shown by the word, plus a circle and a bar.
- **Booked vs waiting** never relies on the fill colour alone.
- **Contrast pairs** are listed in the component note. The frontend must check both colour modes and all three sidebar tones. The grid doesn't use sidebar tokens, so the tones only affect the sidebar item.

**Zoom and text size.**

- Type is in `rem`. At 200% zoom (1440 → effectively 720px), the page switches to the phone list, which reflows without horizontal scroll (WCAG 1.4.10).
- Names wrap anywhere. Nothing is truncated.

### D.6 Progressive enhancement

- **Plain HTML does everything:**
  - month and day navigation are links;
  - the account filter is a GET form with a submit button;
  - the phone list is pure CSS on the same table.
- **`app.js` adds nothing** for this task, and needs no new `data-*` hooks. Two enhancements were considered and rejected:
  - auto-submitting the select on change: a keyboard user arrowing through options would trigger page loads (WCAG 3.2.2);
  - a JS popover for `+N more`: the day view is a real page by design (D6).

### D.7 Open questions for the backend and main session

- **OQ1 (small, optional).** The day view's `Zoom timetable` crumb needs one URL string with `?month=…&account=…`. `partials/crumb.html` takes only `url`. The `{% with %}` + `|add` + `stringformat` chain works but is fiddly. Should the day view's context add `month_url` (str), built with `reverse()` + query like `timetable_url` on the detail page? That's a contract change, so the planner or main session must agree. If the answer is no, the frontend uses the template chain described in D.2.
- **OQ2 (small).** Criterion 11's "account outside the list": the select should show the chosen account as selected even when it isn't in `filter_accounts`. Simplest for the template: when the view resolves a `selected_account` that isn't in the list, it **appends it to `filter_accounts`**, which costs no extra query. Otherwise the template needs a loop flag to detect membership. The designer's preference is the append, but it's the backend's call. The visible behaviour is the same either way.
- **Contract otherwise sufficient.** The day view's count line uses `entries|length`. The heading pieces come from `box.date`. `is_current_month`, `can_add_account` and `has_accounts` cover every state. No other fields are needed.

## Implementation notes
<!-- owners: tmd-devops, tmd-django-backend, tmd-frontend — one sub-heading each: files changed, contract deviations, migrations, new deps (with reason), self-check output -->

### tmd-django-backend

**Files changed**

- `apps/zoom/timetable.py` (new): the pure functions. `DAY_BOX_LIMIT = 3`, `Month` (frozen dataclass: `start`, `end`, `value`, `label`, `previous`, `next`, `contains`, `weeks()`, `for_date`), `parse_month`, `parse_day`, `parse_account_id`, `account_filter`, `day_bounds` / `local_midnight`, `entry_counts`, `DayBox` (a `TypedDict`, so it's still a dict), `build_month` and `day_entries`. None of them touch the database.
- `apps/zoom/models.py`:
  - `BOOKED`, one shared `Q` that `booked()` now uses;
  - `OccurrenceQuerySet.in_period` and `for_timetable`;
  - `HostAccountQuerySet.with_timetable_flag` and `timetable_accounts`.
- `apps/zoom/views.py`:
  - `month_page_url()`, the one place a timetable URL string is built, shared by `month_url` and `timetable_url`;
  - `TimetableContextMixin`, `TimetableMonthView` and `TimetableDayView`;
  - `timetable_url` in `ReviewContextMixin.review_context`, so the detail page and its error re-renders get it;
  - the module docstring.
- `apps/zoom/urls.py`: adds `zoom:timetable` (`zoom/timetable/`) and `zoom:timetable_day` (`zoom/timetable/<int:year>/<int:month>/<int:day>/`).
- `apps/zoom/tests/conftest.py`: stubs for `zoom/timetable.html` and `zoom/timetable_day.html`. The stubs follow every relation the contract allows (`link_request.reference` / `class_name` / `get_status_display`, `host_account.label`), so the query-count test would catch a missing `select_related`.
- `apps/zoom/tests/test_timetable.py` (new), 90 tests:
  - the pure functions, without the database: parse_month on criterion 4's exact values, the three months of criterion 6, the cap, the time-zone edges, ordering, account_filter;
  - the QuerySets;
  - access (1);
  - the month contract (4, 9–13), the day contract (14) and the two pages agreeing (15);
  - the query budget (18), with the stubs and again with the real templates;
  - `timetable_url` (20);
  - using the real templates: no private data (16) and the sidebar (2), which extends brief 008's sidebar tests. These skip only while `zoom/timetable*.html` doesn't exist. The frontend's files were already present, so they ran and passed.

**Context contract, as implemented.** Every variable in both tables is supplied with the name and type the contract gives. `timetable_url` is `str | None` on `zoom/detail.html`. Two notes on the implementation:

- **Accounts query (small deviation from the MVT plan's step 2, contract unchanged).** The plan had the view call `timetable_accounts()` and then run an extra `filter(pk=…).first()` when a pk was given. That can't meet criterion 18's "same count with and without `?account=`" together with criterion 11's "no extra query". Instead, the views run one query over **all** accounts through `with_timetable_flag(start, end)`, which annotates `on_timetable` (`BOOKABLE` OR `EXISTS` a booked class in the period). Then `timetable.account_filter()` does three things in Python:
  - it keeps the flagged accounts as the options;
  - it resolves `?account=` from the full list;
  - it appends the chosen account when it isn't an option (OQ2).

  The same list gives `has_accounts`. Result: every case is the shell's queries plus exactly 2 (accounts, classes), on both pages, with or without a filter, whether the filtered account is in the list or not. `timetable_accounts(start, end)` exists as criterion 17 names it (`with_timetable_flag(...).filter(on_timetable=True)`, one query) and is tested. Reading every account is fine because there are only a handful of them.
- **`booked_count` / `waiting_count`** come from `timetable.entry_counts()`: waiting is `status == waiting`, and everything else `for_timetable` returns is booked, so "booked" isn't restated.

**Brief references adjusted to the current code**

- `ReviewerRequiredMixin` is still in `apps/zoom/views.py`, built on `apps.core.mixins.SignedInPermissionMixin` (brief 010). The timetable views use it.
- Brief 008's "shared bookable condition" is `models.BOOKABLE`, and it is reused.

**Migrations:** none. `makemigrations --check` reports no changes.

**Dependencies and settings:** none.

**Self-check** (dev container, `polymath-tmd-web-1`):

```
ruff check .                          All checks passed!
ruff format --check .                 82 files already formatted
pytest --create-db                    664 passed in 43.42s
manage.py makemigrations --check --dry-run   No changes detected
manage.py check                       System check identified no issues (0 silenced).
```

#### Review round 1 fixes (SF2, nits 1–5)

**Files changed**

- `apps/zoom/tests/test_timetable.py`:
  - **SF2:** removed the `needs_real_templates` skipif and its four uses (privacy, real-template query count, both sidebar tests), plus the now-unused `Path` / `django_settings` imports. The module docstring now says those tests never skip.
  - **Nit 4:** two `parse_month` cases (full-width `２０２６-０９`, Arabic-Indic `٢٠٢٦-١٠`) and `test_non_ascii_digits_in_the_month_fall_back`, which requests `?month=２０２６-０９` and `?month=２０２６-１０` through the view and gets September (the current month).
  - **Nit 3:** `test_timetable_accounts_load_only_what_the_timetable_reads`. It checks that the SQL doesn't name `host_key_encrypted`, that `host_key_encrypted`, `email`, `notes` and `credential_set` are deferred, and that `label`, `sort_order` and `on_timetable` read with no extra query.
  - **SF1 markup test (asked for alongside):** `test_month_table_carries_column_count_and_index_on_every_cell`, run on 2026-09, 2026-11 and 2027-02 (5, 6 and 4 weeks). It checks `aria-colcount="7"` on `table.cal`, and that every row, the header and each week, has exactly 7 cells with `aria-colindex` 1 to 7 in order. The check covers out-of-month cells and empty cells. It uses `html.parser` rather than a regex, so attribute order doesn't matter.
- `apps/zoom/timetable.py`:
  - **Nit 4:** `_MONTH_VALUE` is `[0-9]`, not `\d`. A comment explains why.
  - **Nit 5:** `Month` is `@dataclass(frozen=True)`, without `order=True`. Nothing compared months with `<`. The docstring says so.
- `apps/zoom/models.py` (**nit 3**): `with_timetable_flag` adds `.only("pk", "label", "sort_order")`, and the docstring says why. I checked every template that reads these objects: `timetable_filter.html`, `timetable.html` and `timetable_day.html` read only `.pk` and `.label`, and nothing renders `{{ account }}` bare (`__str__` reads `email`). `for_timetable(account=selected)` uses only the pk. The query counts are unchanged; both fixed-count tests (stubs and real templates) pass.
- `apps/zoom/views.py`:
  - **Nit 1:** the empty `Zoom accounts` banner now sits directly above `HostAccountListView`, after the timetable section.
  - **Nit 2:** `TimetableContextMixin.account_filter()` returns `(all_accounts, filter_accounts, selected_account)` and no longer sets `self.all_accounts`. The month view uses `all_accounts` for `has_accounts`; the day view discards it.
- `apps/zoom/tests/test_timetable_html.py`: the verifier's file. I changed two patterns in it. `test_table_caption_and_column_headers` and `test_out_of_month_cells_are_empty` pinned the exact pre-SF1 `<th …>` / `<td …>` strings, so they failed once the frontend added `aria-colindex`. I widened each pattern to accept `aria-colindex="[1-7]"` and changed nothing else. **The verifier should confirm this edit.**

**Frontend's SF1 change:** it was already in `templates/zoom/timetable.html` when I ran the checks (`aria-colcount="7"` on the table, and `aria-colindex="{{ forloop.counter }}"` on each `th`, in-month `td` and out-of-month `td`). The new markup test ran against it and passed.

**Context contract:** unchanged. **Migrations:** none (`.only()` changes no schema). **Dependencies and settings:** none.

**Self-check** (dev container, `polymath-tmd-web-1`):

```
ruff check .                          All checks passed!
ruff format --check .                 83 files already formatted
pytest --create-db                    699 passed in 34.52s (was 692; +7 new, no skips)
manage.py makemigrations --check --dry-run   No changes detected
manage.py check                       System check identified no issues (0 silenced).
```

### tmd-frontend

**Files changed**

- **New templates:**
  - `templates/zoom/timetable.html`: the month page. It has one `section.box.box--cal`:
    - the head holds the h2 and `nav.cal-nav` (`Choose a month`);
    - `.box__body.cal-top` holds the filter and the D.3 summary or empty line, in first-match order, plus `Add a Zoom account` or `Show all accounts` where D.3 calls for it;
    - `table.cal` sits flush in the box, with explicit roles, a hidden caption, and `Mon` shown / `Monday` read for each weekday.
  - `templates/zoom/timetable_day.html`: the day view.
    - The crumb and `Back to {month}` both use `month_url` as given (D9). The template builds no string for either.
    - The day links keep `?account=`.
    - It shows the count line and `ol.cal-list`, or the `.empty` state (`i-calendar`, h2, and `Show all accounts` when filtered).
- **New partials:**
  - `templates/zoom/partials/timetable_entry.html`, `with entry full only`: the one entry link for both pages. The month box shows the start time, name and account, with the end time and reference hidden. The day row shows the time range, reference, name, `.tags` holding the account or the waiting tag, and the recording tag. Waiting is decided here from `link_request.status`.
  - `templates/zoom/partials/timetable_filter.html`, `with action month_value filter_accounts selected_account only`: the GET filter, shared by both pages. It only marks the option matching `selected_account.pk` as `selected`, relying on the backend's append (OQ2). A page leaves the form out when `filter_accounts` is empty and no account is chosen.
- **Changed templates:**
  - `templates/partials/sidebar.html`: `Timetable` (`i-calendar`) sits between `Link requests` and `Zoom accounts`. It is gated on `review_linkrequest` and current on `zoom:timetable` and `zoom:timetable_day`. The header comment is updated.
  - `templates/partials/icons.html`: adds Feather `calendar` (`i-calendar`). The header comment is updated.
  - `templates/zoom/detail.html`: `See it on the timetable` (`.tap-link`) goes after the email in the `Booked on` `<dd>`, only `{% if timetable_url %}`. The header comment names `timetable_url`.
  - `templates/zoom/accounts.html`: each row gets `Timetable<span class="visually-hidden"> for {label}</span>`, only `{% if can_review %}`. The header comment is updated.
- **`static/css/style.css`:**
  - **1b, layout geometry:** `--cal-day-min`, `--cal-num`, `--cal-time-w` and `--cal-ref-w`, each defined once, next to `--tab-h`.
  - **2, reset:** `select` joins `button, input, textarea` in the `font: inherit` / `color: inherit` rule. This filter is the app's first `<select>`.
  - **New 5q, Month calendar:** `.cal-nav__list`, `.cal-top`, `.box--cal`, `.cal`, `.cal th`, `.cal__day(--out, --today)`, `.cal__head`, `.cal__date`, `.cal__date-link`, `.cal__num`, `.cal__entries`, `.cal__entry(--waiting, --row)`, `.cal__time`, `.cal__name`, `.cal__account`, `.cal__entry .tag`, `.cal__more`, the inset focus rings, `.cal-list` and `.cal__ref`.
  - **8, Responsive:**
    - **`min-width: 768px`:** the grid's outer edges are dropped, and `.cal__date-extra` is visually hidden.
    - **`max-width: 767.98px`:** the table is reflowed into day cards. The weekday head is visually hidden. Out-of-month and empty days get `display: none`. `.cal__num` loses its circle, and entries are 56px tall.
    - **`max-width: 599.98px`:** the nav becomes a 2-column grid with the middle link on its own row (`.cal-nav__wide`), and the day row becomes one column.
- **`static/js/app.js`:** unchanged. No JS is needed (D.6).

**Spec deviations**

- **Where the tokens live.** The four tokens are in the **1b** `:root` block, the layout-geometry group, which is what the brief means. They are not in the 1a palette block, which the colour-literal test calls the "first `:root`" and which holds only colours. Each token is defined once.
- **`.cal th` gets a top border as well as the bottom one.** It draws the line between the summary line and the weekday row that D.1's wireframe shows.
- **`.box--cal { overflow: hidden }`.** It keeps the flush grid's corner cells inside the box's rounded border. Every focus ring in the grid is inset, so nothing is clipped.
- **`.cal__entry .tag` wraps (`white-space: normal`).** At 1024, a column is about 68px inside an entry, and `Waiting for IT` doesn't fit on one line. D.1's wireframe shows it wrapping.
- **Phone: `.cal__num` is plain inline for every day, not only today.** Otherwise the 28px minimum width puts gaps inside `Tue 1 Sep`.
- **Where the accounts-list link sits.** 008's table has no action column, so `Timetable` sits in the `Upcoming classes` cell, below the booked count or `None booked`. Both are now in one `.datagrid__stack`, so the phone card's label/value grid still has one value. D.2 leaves the row layout to 008; the existing 008 tests pass.
- **`Mathematic` / `s` wraps in a 1024px column** under `overflow-wrap: anywhere`. This is the spec's "break anywhere if they must" and is intended.

**Context contract gaps:** none. I used exactly the contract names. `show_waiting` is supplied but not needed: the copy keys off `selected_account`, as D.3 specifies. Both template headers say so.

**Note for the verifier (criterion 14, "both hrefs equal `month_url`").** In the rendered HTML, a filtered `month_url` appears autoescaped: `?month=2026-10&amp;account=3`. Compare the hrefs after unescaping, or compare against `escape(month_url)`.

**Self-check**

- **Stub renders.** I rendered both templates in the dev container with the backend's real `Month`, `build_month` and `day_entries` over unsaved `Occurrence` objects, covering these states:
  - month: all accounts; filtered and not the current month; filtered and empty; no accounts;
  - day: busy; empty; empty and filtered; waiting plus recording.

  What the renders showed:
  - `+2 more` on a 5-entry day, with the hidden text `2 more classes on Mon 7 Sep`;
  - `aria-current="date"` on the 28th;
  - the selected option, with the month links keeping `&amp;account=3`;
  - an escaped `<script>` class name.
- **Screenshots** (headless Edge, in the scratchpad):
  - 1440 light and dark, 1024, and the day view at 1440: seven equal columns, no horizontal scroll;
  - 320 and 400, loaded in iframes of exactly that width (headless Edge won't go below a 496px window): measured `scrollWidth` equals the viewport on both pages at both widths (318/318, 397/397).
- **Guard tests, no database** (`pytest apps/core/tests.py -k "static_reference or … or old_search"`): 59 passed. They cover static references, include `only`, inline styles, template header comments, the icon sprite in both directions, colour literals and rem sizes.
- **`pytest -p no:cacheprovider --reuse-db apps/zoom apps/core`** (dev container, after the backend's notes): **477 passed in 26.14s**. The timetable tests that run on the real templates (sidebar, private data) are included.
- **Live over HTTP on 8010 (dev stack),** using a temporary session for an existing reviewer, deleted afterwards:
  - `/zoom/timetable/` 200 (0.13s);
  - `?month=2026-10` 200;
  - `?month=abc&account=999` 200, falling back to September;
  - `/zoom/timetable/2026/9/28/` 200;
  - `/zoom/timetable/2026/2/30/` 404;
  - `/zoom/accounts/` 200, with the row `Timetable` links.

  The month page carries the `Timetable` sidebar item with `aria-current="page"`, `aria-current="date"`, and the line `No classes booked in September 2026.` (the dev DB has no classes).
- **Not run:** `pytest --create-db`, per the orchestrator's instruction, because parallel runs wipe each other's test database. That run, and the prod-stack check, are left to the verifier.

**Review round 1 fixes (SF1, tmd-frontend, 2026-09-25)**
- **`templates/zoom/timetable.html`:**
  - `aria-colcount="7"` on the table;
  - `aria-colindex="{{ forloop.counter }}"` (1–7) on every `th` and every `td`, out-of-month and empty cells included;
  - roles and caption unchanged;
  - header comment updated.
- **`static/css/style.css`, Responsive section (below 768px):** `.cal__day--out` and `.cal__day--empty` are now clipped with the `.visually-hidden` technique instead of `display:none`, and `.cal__day--empty > *` gets `visibility:hidden`.
- **Spec deviation, and why:**
  - The attributes alone did not fix the reported effect.
  - A Windows UI Automation check at 400px (headed Chromium, `--force-renderer-accessibility`) read the attributes-only markup like this:
    - `Tue 1 Sep`: GridItem column 1 (0-based, so the column index is now right), **but its column header was still `Monday`**. Chrome takes headers from a cell's position among the cells left in the tree, not from `aria-colindex`.
    - Adding `headers="wd-N"` changed nothing.
  - Only keeping the hidden cells in the accessibility tree gave `Tuesday`.
  - Hiding the empty days' contents means their date links leave no invisible focus stop.
  - The visual result matches D5 exactly: a list of only the days with classes, with no gaps. The desktop grid is unchanged (screenshots at 400px and 1280px).
  - The one side effect: someone moving cell by cell through the table with a screen reader now meets blank cells for empty days, as in any table. tmd-ui-designer may want to note this in `docs/design/month-calendar.md` with the SF1 line.
- **Final check,** with the real stylesheet and a stub September 2026 context (entries on 1 and 15 Sep):
  - UIA column headers: `Tue 1 Sep` gives `['Tuesday']`, and `Tue 15 Sep` (after an empty Monday 14) gives `['Tuesday']`.
  - Tab stops in the table are only `Tue 1 Sep` (63×44), its entry, `Tue 15 Sep` (72×44) and its entry.
- **Render check:** the stub context rendered in the dev container (exit 0), with `aria-colcount="7"` once and each `aria-colindex` 1–7 six times (1 header row plus 5 weeks).
- **Not done:**
  - The markup test the review asks for. The orchestrator said not to touch Python; it belongs in `apps/zoom/tests/test_timetable.py` and should assert `aria-colcount="7"` and, for the out-of-month cells of September 2026, `aria-colindex` 1 on the first `td`.
  - pytest was not run, per the orchestrator's instruction.

## Verification
<!-- owner: tmd-test-verifier — verdict, criteria → tests table, checklist results, failures -->

**Verdict: PASS**

**Tests added** (coverage gap: the backend's 90 tests pin the context contract against stub or
real templates for status codes, counts and private data, but nothing rendered the real
`zoom/timetable.html` / `timetable_day.html` markup for the page frame, navigation hrefs and
accessible names, the table's caption/column-header roles, the day-box heading and today
marker, an entry's accessible name (booked and waiting, with escaping), the `+N more` link, the
summary/empty-state copy, the day view's `month_url`-built crumb/back-link equality, and the two
contextual links). Added `apps/zoom/tests/test_timetable_html.py`, 28 tests, rendering the real
templates as `test_accounts.py` and `test_sidebar_zoom_group.py` already do for their pages.

| # | Criterion | Test(s) | Result |
|---|---|---|---|
| 1 | Access (anon → login, plain/staff → 403, IT/superuser → 200) | `test_anonymous_visitors_are_sent_to_sign_in`, `test_signed_in_users_without_the_permission_get_403`, `test_it_users_and_superusers_get_the_pages`; prod HTTP: 302/403/200 confirmed | ✅ |
| 2 | Sidebar `Timetable`, position, `aria-current` | `test_timetable_is_the_current_sidebar_item_between_requests_and_accounts`, `test_timetable_sidebar_item_needs_the_review_permission`; prod screenshot shows `aria-current="page"` on Timetable only | ✅ |
| 3 | Month page frame (h1, title, breadcrumb, h2) | `test_month_page_frame` (new) | ✅ |
| 4 | `parse_month` fallback values, `?month=` | `test_parse_month[…]` (12 cases), `test_month_page_supplies_the_context_contract`, `test_month_parameter_chooses_the_month_and_bad_values_fall_back`; prod `?month=abc&account=999` → 200, September, no error text | ✅ |
| 5 | Month navigation links/accessible names, `This month` | `test_month_navigation_links_and_accessible_names_on_the_current_month`, `test_this_month_link_appears_off_the_current_month_and_keeps_the_account` (new); prod prev/next hrefs confirmed | ✅ |
| 6 | Weeks Mon–Sun, table, caption, `<th scope="col">`, 5/4/6 rows | `test_weeks_of_september_2026_start_on_tuesday`, `test_weeks_of_february_2027_fill_four_rows_exactly`, `test_weeks_of_november_2026_take_six_rows`, `test_every_day_of_the_month_appears_once_and_in_its_weekday_column`, `test_table_caption_and_column_headers`, `test_month_grid_has_the_right_number_of_week_rows[…]` (new, real markup); prod: Sep 2026 = 5 rows, Nov 2026 = 6, Feb 2027 = 4 (curl) | ✅ |
| 7 | Day box: h3, `<time>`, accessible text, today marker | `test_build_month_marks_today_and_leaves_days_outside_empty`, `test_day_box_heading_accessible_text_and_today_marker`, `test_out_of_month_cells_are_empty` (new); prod screenshot shows the round "25 Today" marker | ✅ |
| 8 | Entries: visible/accessible name, order, exclusions, recording | `test_build_month_orders_by_start_then_pk`, `test_for_timetable_keeps_booked_and_waiting_only`, `test_entry_accessible_name_for_a_booked_class`, `test_entry_shows_the_waiting_tag_with_icon_and_word_instead_of_an_account`, `test_class_name_is_escaped_never_rendered_as_markup` (new) | ✅ |
| 9 | `DAY_BOX_LIMIT`, `+N more`, singular wording | `test_build_month_caps_each_box_and_counts_the_rest`, `test_build_month_boxes_with_room_have_no_more`, `test_a_busy_day_shows_three_and_counts_the_rest`, `test_overflow_link_text_and_accessible_name_plural`, `test_overflow_link_accessible_name_singular` (new); prod: 5-entry day shows 3 + "+2 more" → day view | ✅ |
| 10 | Time-zone edges (day = local start date) | `test_build_month_puts_classes_on_their_local_start_date`, `test_month_page_shows_classes_on_their_local_day`, `test_day_view_edges_of_the_local_day` | ✅ |
| 11 | Account filter, bad values, out-of-list account (D9) | `test_account_filter_offers_the_flagged_accounts_and_resolves_the_choice`, `test_account_filter_appends_a_chosen_account_that_isnt_an_option`, `test_account_filter_shows_one_accounts_booked_classes_only`, `test_bad_account_values_fall_back_to_all_accounts`, `test_filtering_to_an_account_outside_the_options_lists_it_once_at_the_same_cost`; prod D9 check: `?account=<out-of-use pk>` → `<option selected>` exactly once, "No classes booked on Verify Zoom Old in September 2026." | ✅ |
| 12 | Summary line, all forms | `test_summary_counts`, `test_summary_line_pluralisation_and_waiting_wording`, `test_summary_line_omits_waiting_when_there_is_none`, `test_summary_line_filtered`, `test_summary_line_zero_booked_still_names_the_waiting_count` (new) | ✅ |
| 13 | Empty states, incl. no-accounts + Add link | `test_no_accounts_at_all`, `test_has_accounts_counts_accounts_that_are_not_options`, `test_can_add_account_follows_the_add_permission`, `test_no_accounts_empty_state_with_add_link`, `test_no_accounts_empty_state_without_add_permission`, `test_filtered_to_nothing_shows_show_all_accounts_link` (new); prod empty-month screenshot | ✅ |
| 14 | Day view: address/404, headings, breadcrumb, `month_url` equality, links, filter, empty | `test_impossible_or_out_of_range_days_are_404`, `test_day_view_supplies_the_context_contract`, `test_day_view_filtered_keeps_the_account_in_month_url`, `test_day_view_filter_offers_that_months_accounts_and_appends_an_outside_one`, `test_day_view_frame_and_breadcrumb`, `test_day_view_crumb_and_back_link_both_equal_month_url_unfiltered`, `test_day_view_crumb_and_back_link_both_equal_month_url_filtered` (new); prod: unfiltered and filtered (`&amp;account=124`) both hrefs equal `month_url` after unescaping | ✅ |
| 15 | The two pages agree | `test_the_two_pages_agree` | ✅ |
| 16 | No private data | `test_neither_page_shows_private_data` | ✅ |
| 17 | Logic lives in `timetable.py`; views thin | pure-function tests run without the database; confirmed by reading `apps/zoom/views.py` (`TimetableMonthView`/`TimetableDayView` only parse, call `timetable.*`/queryset methods, and render) | ✅ |
| 18 | Fixed query count, small and large cases | `test_both_pages_run_a_fixed_number_of_queries`, `test_real_pages_run_a_fixed_number_of_queries` | ✅ |
| 19 | Scale: 400 classes < 1s, dev stack | Verifier-seeded 400 approved classes across September 2026 on the dev stack; `curl -w "%{time_total}"` on `/zoom/timetable/` (IT session) → **0.105s**, 200, "400 booked classes in September 2026." Data and account removed afterwards | ✅ |
| 20 | Detail page `See it on the timetable` | `test_approved_request_detail_links_to_its_month_and_account`, `test_weekly_request_links_to_the_month_of_its_first_class`, `test_waiting_and_rejected_requests_have_no_timetable_link`, `test_detail_page_shows_the_timetable_link_for_an_approved_request`, `test_detail_page_hides_the_timetable_link_for_a_waiting_request` (new); prod: link present with correct href on an approved request | ✅ |
| 21 | Accounts list `Timetable` link | `test_accounts_list_shows_timetable_link_for_reviewers`, `test_accounts_list_hides_timetable_link_without_review_permission` (new); prod accounts list shows a `Timetable` link per row (`?account=<pk>`) | ✅ |
| 22 | Real `<table>`, ARIA roles, one h1 | `test_table_caption_and_column_headers`, `test_out_of_month_cells_are_empty` (new); read `templates/zoom/timetable.html`: `role="table"`/`rowgroup`/`row`/`columnheader`/`cell` present throughout; one `h1` per page (shell block) | ✅ |
| 23 | Desktop: no h-scroll at 1024/1440, wrapping, equal row height | Playwright: `scrollWidth == clientWidth` at 1024 and 1440 (light and dark); screenshots `month_1024.png`, `month_1440_light.png`, `month_1440_dark.png`; `table-layout: fixed` and `overflow-wrap: anywhere` read in `style.css` | ✅ |
| 24 | Phone: day-by-day list, same markup | Playwright screenshot `month_400.png`: weekday header and empty/no-entry days hidden, each remaining day a stacked card with full date heading and the same cap/`+N more`; no second markup tree (same `templates/zoom/timetable.html`, CSS-only reflow in §8 of `style.css`) | ✅ |
| 25 | Targets ≥44px, contrast, today/waiting never colour-alone | Read CSS (`.cal__entry`, `.cal__date-link`, `.cal__more`, `.cal-nav` buttons, `.input`/`.button` all ≥44px); screenshots show "Today" word + circle/bar, "Waiting for IT" icon+word in both colour modes | ✅ |
| 26 | Works without JS | All controls are `<a>`/`<form method="get">`; `static/js/app.js` unchanged (confirmed via diff); no console-dependent behaviour exercised during the prod walkthrough | ✅ |
| 27 | Template rules (headers, `only`, no inline style, no hard-coded paths, sprite, tokens/no literals) | `test_template_starts_with_purpose_comment[zoom/timetable.html]`, `[zoom/timetable_day.html]`, `[zoom/partials/timetable_entry.html]`, `[zoom/partials/timetable_filter.html]`, `test_every_include_ends_with_only`, `test_no_inline_style_attributes_in_templates`, `test_no_hardcoded_paths_in_href_or_action_attributes`, `test_every_icon_use_references_a_defined_symbol_and_every_symbol_is_used`, `test_css_colour_literals_live_only_in_the_root_palette_block`, `test_css_custom_property_names_do_not_encode_their_value`, `test_css_font_sizes_are_rem_and_the_root_size_is_never_set` — all pass. **Observation (not a FAIL):** the four `--cal-*` tokens sit in the CSS's second `:root` block ("1b", next to `--tab-h`) rather than the first ("1a", the palette-only block the MVT plan names). `test_css_colour_literals_live_only_in_the_root_palette_block` only checks that colour literals stay inside the first `:root {}` — these four tokens are px/em lengths, not colours, so it doesn't apply to them either way, and it still passes. `test_css_custom_property_names_do_not_encode_their_value` doesn't check block location. No test or criterion enforces that *all* tokens (not just colours) sit in the first block, and the placement matches existing precedent — `--tab-h` and the rest of the layout-geometry group already live in the second block. Criterion 27's "CSS uses only tokens from the first `:root` block, with no colour literals" reads, in context, as "the tokens section" collectively (1a–1e), matching how the codebase already works; taken fully literally it would also indict `--tab-h` and `--space-*`, which predate this brief. | ✅ (with observation) |
| 28 | ruff / format / pytest --create-db / makemigrations / check | See checklist below | ✅ |
| 29 | Prod stack walkthrough, static files, screenshots | See "Prod stack" below | ✅ |

**Checklist**

- `ruff check .` — All checks passed!
- `ruff format --check .` — 83 files already formatted
- `pytest --create-db` (dev container) — **run twice**, plus once more after adding
  `test_timetable_html.py`: 664 / 664 / 692 passed, no skips, no flakes
- `manage.py makemigrations --check --dry-run` — No changes detected
- `manage.py check` — System check identified no issues (0 silenced)
- `manage.py check --deploy` (prod stack, `USE_HTTPS=True`) — one accepted warning only
  (`security.W021`, HSTS preload) — run even though this brief changes no settings, for extra
  assurance
- Prod HTTP on 8010 — see below

**Prod stack** (`ZOOM_PROVIDER=manual docker compose up -d --build`, `web` healthy)

A throwaway superuser (`verifier009`) and a plain user (`plain009`) exercised the pages; both,
and all seeded test data (3 accounts, 7 link requests), were deleted afterwards.

1. **Approved a test request** through `apps.zoom.services.approve()` with manual meeting
   details (the real path a live approval takes) → outcome `approved`.
2. **Found it in the right day box**, with its account (`Verify Zoom A`) shown.
3. **Saw a waiting request** marked `Waiting for IT` with the clock icon.
4. **Added 5 classes on one day** (30 Sep) → box showed 3 + `+2 more` → day view listed all 5,
   sorted by start time.
5. **Filtered to one account** (`?account=124`): only that account's booked classes showed, the
   waiting class was hidden, the select kept the choice, summary read "3 booked classes on
   Verify Zoom A in September 2026."
6. **Month navigation**: `?month=2026-08` (empty, full grid still rendered) and back to
   September; `?month=2026-11` (6 rows) and `?month=2027-02` (4 rows) confirmed the three
   row-count cases from criterion 6.
7. **Bad `?month`** (`abc`) → 200, fell back to September, no error text.
8. **D9 (criterion 11's last bullet)**: filtered to `Verify Zoom Old` (`is_active=False`, no
   classes that month) → `<option value="126" selected>` present exactly once, "No classes
   booked on Verify Zoom Old in September 2026."
9. **Day view's `month_url` breadcrumb and back link**: both hrefs, unescaped, equalled
   `month_url` unfiltered (`?month=2026-09`) and filtered (`?month=2026-09&account=124`).
10. **Impossible date** `/zoom/timetable/2026/2/30/` → 404.
11. **403** for the plain user on both pages; **302** to `accounts:login?next=…` for anonymous.
12. **Opened an entry** → reached its `zoom:detail` page; the detail page showed `See it on the
    timetable` with the expected href for the approved request.
13. **Accounts list**: every row showed a `Timetable` link (`?account=<pk>`).
14. **Static files**: `/static/css/style.567eacf1a1dd.css` (hashed) → 200.

**No horizontal scroll** at 320 and 400 (Playwright: `document.documentElement.scrollWidth ==
clientWidth` on the month page and the day view), and at 1024/1440.

**Screenshots** (scratchpad, not committed): `month_1440_light.png`, `month_1440_dark.png`,
`month_1024.png`, `month_400.png`, `month_320.png`, `day_1440.png`, `day_400.png`,
`month_filtered.png`, `month_empty.png`.

**Accessibility audit of the saved HTML**

- Every input (`account` select) has a `<label for="account">`.
- No validation state on this read-only page, so no `aria-describedby`/`aria-invalid` error
  wiring is needed (D.5 confirms none applies); the help text is joined with
  `aria-describedby="account-help"`.
- Headings run in order (h1 → h2 → h3 per day; day view h1 only), exactly one h1 per page.
- The shell's landmarks and skip link are present (unchanged from earlier briefs); `nav
  aria-label="Choose a month"` / `"Choose a day"` added.
- No new images; icons are `aria-hidden` SVGs with visible text alongside.
- Status is always icon + word: `Waiting for IT` (clock icon), `Today` (word, plus circle/bar).
- All buttons/links have accessible names, including hidden extra text for month/day nav and
  `+N more`.
- Targets read ≥44px throughout the screenshots and CSS.

**Restoring the stack:** the dev stack (`compose.yaml` + `compose.dev.yaml`) was running before
verification; it has been rebuilt and restarted the same way afterwards, with the `mysqldata`
volume kept. All throwaway users, accounts and requests (verifier009, plain009, the 3 "Verify
Zoom" accounts, and the 400 "Scale Class" classes used for criterion 19) were deleted from both
the prod and dev databases before switching back.

## Review
<!-- owner: tmd-code-reviewer (written by the main session) — verdict, blockers, should-fix, nits -->

### Round 1 — 2026-09-25 (verifier PASS, 692 tests ×3)

**Verdict: CHANGES REQUESTED.** There are no blockers.

**Should fix**

**SF1: the phone reflow can announce the wrong weekday.**
- **Where:** `templates/zoom/timetable.html:43,49,60`; `static/css/style.css:2854-2857`.
- **Cause:** below 768px, `display:none` on `.cal__day--out` and `.cal__day--empty` removes those cells from the accessibility tree. Screen readers then take a cell's column from its position among the cells that remain.
- **Effect:** `Tue 1 Sep` is announced under "Monday".
- **Fix:**
  - add `aria-colcount="7"` on the table;
  - add `aria-colindex` on every `th` and `td`, including the cells that get hidden;
  - add a markup test;
  - run a quick screen-reader check at 400px.
- **Owner:** tmd-frontend. tmd-ui-designer adds one line to `docs/design/month-calendar.md` (~line 128).

**SF2: leftover `skipif` in the test file.**
- **Where:** `apps/zoom/tests/test_timetable.py:756-761`.
- **Cause:** the `needs_real_templates` skip would silently skip the privacy (criterion 16), real-template query-count (criterion 18) and sidebar (criterion 2) tests if a template were renamed.
- **Fix:** remove the skip and its four uses.
- **Owner:** tmd-django-backend.

**Nits**
1. `views.py:450-453`: the Zoom accounts banner is empty and sits above the timetable banner, so `HostAccountListView` now falls under the timetable section. Reorder.
2. `views.py:479,515`: `account_filter()` passes `self.all_accounts` as a side effect. Return a tuple instead.
3. `models.py:194-200`: `with_timetable_flag` loads full `HostAccount` rows, including `host_key_encrypted`. Add `.only("pk","label","sort_order")`.
4. `timetable.py:39`: `\d` accepts Unicode digits. Use `[0-9]` or `re.ASCII`.
5. `timetable.py:56`: `order=True` on `Month` is unused.
6. `timetable.html:16`, `timetable_day.html:16,18`: prev and next links at the 2000 and 2100 limits lead to a fallback or a 404.
7. `style.css:2223,2885`: entry rows borrow `--tab-h`, following `month-calendar.md:134`.

**Answers to the main session's questions**
- **The flagged accounts query:** correct, and nothing leaks.
- **Asia/Colombo day boundaries and parsing:** correct.
- **`month_page_url()`:** respects "templates don't know URL shapes".
- **Token placement:** change the wording, not the CSS. The stylesheet header already says tokens live in section 1's `:root` blocks, and colour literals appear only in the first (1a palette) block. Hand-off to tmd-docs-writer: fix CLAUDE.md ("UI conventions → Tokens", "DRY") and criterion 27's wording.
- **Table semantics, `overflow:hidden` and inset focus rings:** good apart from SF1.
- **Privacy:** clean.

**Main-session ruling:**
- Nits 1–5 go to the backend with SF2.
- Nit 6 is accepted as a known limit, because nobody books classes in 1999 or 2101.
- Nit 7 is left until a row-height token exists.
- The token wording is fixed at close.

### Round 2 — 2026-09-25 (after the round-1 fixes; re-verification PASS, 699 tests ×2)

**Verdict: APPROVE.** No blockers or should-fix findings.

- **SF1 is fixed**, using clipping instead of `display:none` (`style.css:2853-2872`).
  - Nothing clipped can take focus. The contents of empty cells get `visibility:hidden`, which every descendant inherits.
  - Every `td` stays in the tree with its `aria-colindex`, so every day announces the correct weekday.
  - The rules sit inside the `max-width: 767.98px` block, so layout at 768px and wider is unaffected. The clipped 1px boxes can't cause horizontal scroll.
  - A week with no classes collapses to a row of zero height.
- **SF2 and nits 1–5:** confirmed fixed.

**Nits (optional)**
1. `docs/design/month-calendar.md:137`: leftover wording ("This replaces the `display: none` in the … row above"). Row 128 has already changed, so drop the sentence.
2. `timetable.html:49`: on phones, an empty "today" cell is clipped but keeps `aria-current="date"`. It could leave `aria-current` off when the day has no classes.
3. `models.py:200`: the `only()` inside `with_timetable_flag` is also inherited by `timetable_accounts()`. It's already documented and guarded by the query-count tests; this is a note for anyone reusing it later.

**Main-session ruling:** nit 1 is fixed at close (a docs-only change). Nits 2 and 3 are recorded as follow-ups.

### Re-verification (round 1 fixes) — 2026-09-25

**Verdict: PASS**

**Scope.** Re-ran the full "Verify a change" checklist (`pytest --create-db` twice) and the prod-stack walkthrough against the round-1 fixes: SF1 (`aria-colcount`/`aria-colindex` plus the visually-clipped, not `display:none`, phone reflow), SF2 (the `needs_real_templates` skip removed) and nits 1–5.

**Checklist**

| Check | Result |
|---|---|
| `ruff check .` | All checks passed! |
| `ruff format --check .` | 83 files already formatted |
| `pytest --create-db` (dev container), run 1 | **699 passed** in 29.83s, no skips |
| `pytest --create-db` (dev container), run 2 | **699 passed** in 35.40s, no skips, no flakes |
| `manage.py makemigrations --check --dry-run` | No changes detected |
| `manage.py check` | System check identified no issues (0 silenced) |
| `manage.py check --deploy` (prod, `USE_HTTPS=True`) | Only `security.W021` (accepted) |
| Prod HTTP on 8010 | See below |

**SF2 confirmed.** `grep -n "needs_real_templates\|skipif" apps/zoom/tests/test_timetable.py` returns nothing — the skip and its four uses are gone. The tests it used to guard (privacy, real-template query count, both sidebar tests) run unconditionally as part of the 699.

**Backend's edit to the verifier's own file, confirmed still strict.** `apps/zoom/tests/test_timetable_html.py::test_table_caption_and_column_headers` and `::test_out_of_month_cells_are_empty` were widened from a fixed `<th …>`/`<td …>` string to a regex that requires `aria-colindex="[1-7]"` — this still pins an exact, valid attribute value (not `.*` or presence-only), so a regression that dropped or mis-numbered the attribute would still fail the test. Read both tests directly; confirmed.

**SF1's own markup test.** `apps/zoom/tests/test_timetable.py::test_month_table_carries_column_count_and_index_on_every_cell`, parametrized over September 2026 (5 rows), November 2026 (6) and February 2027 (4), parses the real rendered table with `html.parser` and asserts `aria-colcount="7"` plus `aria-colindex` 1–7 in order on every row, header included, out-of-month and empty cells included. Ran and passed in both `pytest --create-db` runs.

**CSS, read directly.** `static/css/style.css:2854-2874`: below 768px, `.cal__day--out` and `.cal__day--empty` use the visually-hidden clip technique (`position:absolute; width/height:1px; overflow:hidden; clip-path:inset(50%)`), not `display:none`, keeping the `<td>` in the accessibility tree; `.cal__day--empty > *` gets `visibility:hidden`, removing the (now pointless) date link from focus and from the accessible name, without removing the cell itself. Matches the implementation notes exactly.

**Prod-stack walkthrough** (`ZOOM_PROVIDER=manual docker compose up -d --build`, `web` healthy; dev stack was running beforehand and was restored afterward with the same `docker compose -f compose.yaml -f compose.dev.yaml up -d --build`, `mysqldata` volume kept).

A throwaway superuser (`verifier009b`) and a plain user (`plain009b`), one host account (`Verify009 Zoom A`) and three requests (two approved via `services.approve()` with manual meeting details, one left waiting) were seeded on real future dates (Sat 26, Tue 29, Wed 30 Sep 2026 — "now" on the container is 25 Sep 2026) so the round-1 fix could be exercised with a genuine mix of populated and empty day cells. All were deleted afterward; confirmed zero rows remain.

1. **Access (criterion 1):** anonymous → 302 to `accounts:login?next=…` on both `zoom:timetable` and `zoom:timetable_day`; plain user (no `review_linkrequest`) → 403 on both; superuser → 200 on both.
2. **Bad `?month`/`?account` (criterion 4, D4):** `?month=abc&account=999` → 200, falls back to September, no error text.
3. **Impossible date (criterion 14):** `/zoom/timetable/2026/2/30/` → 404.
4. **Contextual links (criteria 20–21):** the day view's entry linked to `/zoom/requests/595/`; that detail page showed `See it on the timetable` → `/zoom/timetable/?month=2026-09&account=139` (matches the approved request's month and account); the accounts list showed 6 `Timetable` links.
5. **Static files:** `/static/css/style.83460a926118.css` (current hash, since the round-1 CSS changed) → 200.
6. **Screens at 1440** (`month_1440_light.png`, `month_1440_dark.png` — dark mode toggled through the app's own control, not OS `prefers-color-scheme`, which this app deliberately doesn't follow): 7 equal columns, today (25th) marked with the circle and the word `Today`, the booked entries on 26/29 and the waiting entry on 30 (dashed outline, clock icon, `Waiting for IT`) all visible, good contrast in both modes.
7. **Filtered month** (`month_filtered.png`, `?account=139`): only that account's 2 booked classes show; the waiting class on the 30th is correctly hidden; the select keeps the choice; summary reads "2 booked classes on Verify009 Zoom A in September 2026."
8. **Empty month** (`month_empty.png`, `?month=2026-08`): full 6-row grid still renders, "No classes booked in August 2026.", `This month` link shown (not on the current month).
9. **Day view** (`day_1440.png`, Tue 29 Sep): `Previous day`/`Back to September 2026`/`Next day`, the one entry as a row with time range, reference, name and account.

**400px — the round-1 fix itself, independently checked with real UI Automation** (headed Chromium, `--force-renderer-accessibility`, a CDP-emulated viewport confirmed to be exactly 400×900 via `window.innerWidth/innerHeight` before inspecting — an earlier attempt at a fixed `--window-size` left the actual viewport at the Chromium default 1280×720, which would have silently tested the desktop layout; corrected before drawing conclusions):

- **Weekday headers, Windows UI Automation (`System.Windows.Automation`, `GridItemPattern`).** The header row's own cells report `Monday`→column 0 … `Sunday`→column 6. Every day cell checked — both the "empty" ones (no visible name once their content is `visibility:hidden`, e.g. 1, 2, 8, 15, 25 Sep) and the populated ones — sits at the column matching its real weekday: `Sat 26 Sep`→5, `Tue 29 Sep`→1, `Wed 30 Sep`→2, and, listing every `DataItem` cell in each grid row by its `GridItemPattern` column, **every row has cells at columns 0,1,2,3,4,5,6 in order**, with no gaps or shifted columns. This is the exact defect SF1 fixed: previously, `display:none` on out-of-month/empty cells removed them from the tree and Chrome recomputed headers by position among what was left, misreporting e.g. `Tue 1 Sep` as under `Monday`. (`TableItemPattern.ColumnHeaderItems` itself returned empty for every cell in this Chromium build — Chrome doesn't populate that UIA property — so the column-index cross-check against the header row, the same technique the frontend's own self-check used, is the correct read.)
- **No horizontal scroll:** `document.documentElement.scrollWidth == clientWidth` at 400 (400/400) and 320 (320/320) on the month page, and 400/400 on the day view.
- **Clipped empty-day date links can't be reached by Tab.** Tabbed through the whole page (60 presses, cycle observed). Inside the calendar, the only stops were: `Previous month` → `Next month` → the `Show` select → the `Show` button → `Sat 26 Sep` (date link) → its entry → `Tue 29 Sep` (date link) → its entry → `Wed 30 Sep` (date link) → its entry → (cycles back to the skip link). None of the 27 empty or out-of-month days' date links — which exist in the DOM and stay in the accessibility tree per the CSS above — took a Tab stop, because their content is `visibility:hidden`. That matches D5's "an empty day's date link is hidden, so no invisible focus stop is left behind" exactly.
- **Screenshots:** `month_400.png` (weekday header row hidden, only the three days with classes shown as stacked cards, each headed by its full date, waiting entry with dashed outline), `month_320.png` (same, narrower, no truncation), `day_400.png`.

**1440px grid, re-confirmed correct** (see the screenshots above): seven equal columns, `table-layout: fixed`, no horizontal scroll (1440/1440), row heights matched within a week, today's marker and the waiting tag's icon+word both visible.

**Verdict: PASS.** SF1 and SF2 are both fixed and independently re-verified — SF1 by genuine Windows UI Automation against the real, running prod stack, not just by reading the code or trusting the frontend's earlier report. Nits 1–5 were confirmed present in the diff (`views.py`'s account-filter tuple return and banner ordering, `.only()` on the accounts query, the ASCII-only month regex, `order=True` dropped from `Month`) and covered by the corresponding new tests. All 699 tests pass, twice, with no skips. Checklist items 1–5 all pass. The dev stack was restored afterward and all throwaway data (2 users, 1 host account, 3 link requests, 3 occurrences) was deleted from the prod database before switching back.

## Docs
<!-- owner: tmd-docs-writer — files updated; closes Status -->

**Files updated**

- `README.md`: added a **Timetable** paragraph to "Zoom link requests" — where it is in the
  sidebar and who can see it (`IT desk`, same access as the queue and Zoom accounts), the Mon–Sun
  month calendar and what a day box shows, the day page, the account filter and previous/next
  month, waiting classes marked `Waiting for IT`, the `See it on the timetable` link on an approved
  request, and the `Timetable` link on the accounts list.
- `CLAUDE.md`:
  - the `zoom` bullet gained one clause: the timetable's month/day arithmetic, week layout and
    grouping are pure functions with no database access in `apps/zoom/timetable.py`, keeping the
    views thin and each page's query count fixed.
  - "UI conventions → Tokens" and the DRY bullet now say tokens are defined only in section 1's
    `:root` blocks of `static/css/style.css` (1a–1e), and colour literals only in the first, 1a
    palette block — matching the round-1 review's ruling on the token-placement question and how
    the codebase already works (`--tab-h` and the rest of layout-geometry have always lived in 1b).
  - Front end gained one line: never `display: none` a calendar or table cell in a responsive
    reflow; clip it instead (review round 1, SF1).
- `docs/design/month-calendar.md`: deleted the leftover sentence at the old line 137 ("This
  replaces the `display: none` in the … row above"), left stale once row 128 already read
  "clipped, contents hidden" (review round 2, nit 1).
- `docs/CHANGELOG.md`: added the newest-first entry "2026-09-25 — 009: Zoom timetable (month
  calendar)" — user-visible changes, then technical notes (no migrations, `timetable.py`, the
  two-query budget, the `aria-colindex`-plus-clipping rule, the four `--cal-*` tokens) and the
  round-2 follow-ups, including brief 011 as a go-live prerequisite.
- `docs/tasks/009-zoom-timetable.md` (this file): this Docs section, and Status set to Done.

**Clarification on criterion 27's wording.** Criterion 27 says "CSS uses only tokens from the
first `:root` block, with no colour literals." That's the planner's original wording and is left
unedited here, per instruction. The verifier's observation and the round-1 review both read it, in
context, as "the tokens section" collectively (1a–1e) for tokens generally, with the "no colour
literals" half applying specifically to the first, 1a palette block — which is what the shipped
CSS does, what the enforcing tests check, and what CLAUDE.md now says explicitly. Read fully
literally, criterion 27 would also indict `--tab-h` and `--space-*`, which predate this brief and
sit in 1b.

**Status: Done.** Verification: PASS (699 tests, two rounds, plus the prod-stack walkthrough and a
Windows UI Automation check at 400px). Review: round 2 APPROVE, with the main-session ruling on
nits recorded above in "Review".
