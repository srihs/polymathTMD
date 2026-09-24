`design/c-broadsheet/`

# Direction C — Broadsheet

**Concept.** Broadsheet sets the desk like a well-printed school notice: a ruled
masthead across the top, a single generous column of text you can actually read,
and a thin "On this page" index running down the side so long records stay
navigable without scrolling blind. It has no boxes, no shadows and no rounded
corners — structure comes entirely from rules, indents and the space between
things, the way a page of print does.

**Who it suits.** Anoma runs the office and lives in printed lists, letters and
registers; Ruwan reads the device record before signing a purchase off. Both are
reading people rather than dashboard people, and both are looking for one fact in a
page of facts. Broadsheet gives them the largest body text of the five (18px on a
66-character measure), headings that actually rank, and a record page whose four
sections are listed in the margin so "warranty" is one click, not one scroll.
Because it draws with rules instead of cards, a page printed from it looks like the
screen, which matters in a school that still puts paper in a file.

---

## 1. Navigation model

**Desktop (≥1080px): a ruled masthead with breadcrumbs, plus an "On this page"
section index beside the column.**

- Masthead, full bleed, `--surface` on the `--bg` paper:
  - Row 1, 64px: crest chip 34px + `Polymath College` in Newsreader 22px at the
    left; `Nimali Perera · ICT Technician` and a `Sign out` POST button at the
    right; a 2px `--ink` rule under the row.
  - Row 2, 56px: the four navigation labels in Source Sans 3 17px, 32px apart,
    left-aligned under the wordmark; `Raise a request` is the last, set in
    `--brand` with a 2px underline so it reads as the action without becoming a
    button; a 1px `--rule` line under the row.
  - Row 3, 40px: breadcrumbs, e.g. `Devices › IT-0142`, 16px `--muted`, with `›`
    as text. **This row exists only where there is depth to show** — that is, on
    `device.html` alone. `Home`, `Requests`, `Raise a request` and `Design kit`
    are reached in one step from the masthead, so a breadcrumb there would repeat
    the navigation label and spend 40px saying nothing. The masthead is therefore
    **123px on those four pages** (66 + 57) and **160px on the device record**.
- Content: a two-column grid — 680px article column at the left of a centred
  1040px band, then a 40px gutter, then a 240px sticky slot. On `dashboard.html`,
  `device.html`, `request-form.html` and `ui-kit.html` that slot is a
  `<nav aria-label="On this page">` index listing the page's `<h2>`s as anchor
  links, with a 2px `--brand` bar marking the current one. On `requests.html` there
  are no sections to index, so the same slot becomes a sticky `<aside>` headed
  `Filter and sort`, holding `Status`, `How urgent`, `Who is on it`, `Sort` and
  `Clear the filters`. Putting the apparatus in the margin is what keeps the queue's
  chrome out of the reading column — the queue page's article column runs
  `<h1>` → lead → search → count → rows and nothing else.
- Current page: `aria-current="page"`, the label in `--ink` bold with a 3px
  `--brand` underline; all others `--muted` with no underline until hover.
- `Design kit` sits in the footer rule line with the college name.

**Phone (<1080px): sticky masthead with a horizontally scrolling navigation strip.**

- 56px masthead: crest chip + `Polymath College`, and a 48px `Sign out` icon
  button with a visible word beside it at ≥360px.
- Directly under it, a 56px strip that scrolls sideways, holding all four labels as
  48px-tall text links with 20px of padding; `Raise a request` is pinned at the
  **left** of the strip (so it is the first thing under the thumb when the strip is
  at its start) and carries a `--brand` underline. The strip has
  `scroll-snap-type: x proximity`, `overflow-x: auto`, and a 1px `--rule` under it.
  All four items are always present in the DOM and reachable by Tab regardless of
  scroll position; the current one is scrolled into view with `scroll-margin-inline`
  in CSS, not with script.
- The breadcrumb line sits under the strip at 15px, and again only on
  `device.html`.
- The "On this page" index becomes a `<details>` titled `On this page`, placed
  directly under the `<h1>`, closed by default. On `requests.html` the margin
  `<aside>` becomes a `<details>` titled `Filter and sort`, placed under the search
  field, closed by default — the same content in the same order as the desktop
  margin, so the two widths are one component.

**With JavaScript off.** The strip is a CSS overflow container, the index and the
filter panel are `<details>`, the breadcrumbs are links, and the filters are a
`<form method="get">` with its own `Apply` button: everything works. `app.js` only
adds the scrollspy highlight on the desktop index.

---

## 2. Wireframes

### 2.1 `dashboard.html` — desktop 1440

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ [skip to main content]                                                               │
│ ▣  Polymath College                              Nimali Perera · ICT Technician      │
│    Technology Management Desk                                        [ Sign out ]    │
│ ══════════════════════════════════════════════════════════════════════════════════════│ 2px
│  Home     Requests     Devices     Raise a request                                   │
│  ────                                          ─────────────────                     │
│ ──────────────────────────────────────────────────────────────────────────────────── │ 1px
├──────────────────────────────────────────────────────────────────────────────────────┤
│        ┌──────────────── 680px ────────────────┐  ┌──── 240px ────┐                  │
│        │ Home                                  │  │ On this page  │                  │
│        │ Friday 11 September 2026. Here is     │  │ ▌What needs   │  sticky index    │
│        │ what needs doing today.               │  │  doing        │                  │
│        │ ───────────────────────────────────── │  │  Requests to  │                  │
│        │ What needs doing                      │  │  work on      │                  │
│        │                                       │  │  Devices to   │                  │
│        │  6   requests open                    │  │  watch        │                  │
│        │  2   are urgent                   ⚑   │  │  Requests     │                  │
│        │  1   raised today                     │  │  raised in    │                  │
│        │  3   devices due back next week       │  │  the last     │                  │
│        │  2   devices in repair            🔧  │  │  five school  │                  │
│        │ 128  devices in the register          │  │  days         │                  │
│        │  34  out on loan                      │  │  Things you   │                  │
│        │ ───────────────────────────────────── │  │  can do       │                  │
│        │ Requests to work on                   │  └───────────────┘                  │
│        │ REQ-2048   ⚑ Urgent    ↻ In progress  │                                     │
│        │ Projector in Lab 2 shows a blue screen│   rows separated by 1px rules only  │
│        │ Suresh Kumara · Fri 11 Sep, 8:15 am   │   — no card, no fill                │
│        │ ───────────────────────────────────── │                                     │
│        │ REQ-2047   ⚑ Normal    ★ New          │                                     │
│        │ Laptop will not connect to the staff  │                                     │
│        │ Wi-Fi · Dilani Fernando               │                                     │
│        │ ───────────────────────────────────── │                                     │
│        │ … two more …          See all requests→                                     │
│        │ ═══════════════════════════════════════│                                     │
│        │ Devices to watch                      │                                     │
│        │ IT-0087  Epson EB-X51 projector       │                                     │
│        │          🔧 In repair · Science Block │                                     │
│        │ ───────────────────────────────────── │                                     │
│        │ … two more …   Open the device record→│                                     │
│        │ ═══════════════════════════════════════│                                     │
│        │ Requests raised in the last five      │                                     │
│        │ school days                           │                                     │
│        │  Mon  ██████████         1            │  horizontal ruled bars              │
│        │  Tue  ████████████████████  2         │                                     │
│        │  Wed  │  0                            │  a zero is a labelled empty bar     │
│        │  Thu  ██████████         1            │                                     │
│        │  Fri  ██████████         1            │                                     │
│        │  Mon 1 · Tue 2 · Wed 0 · Thu 1 · Fri 1│  the text alternative, always shown │
│        │ ═══════════════════════════════════════│                                     │
│        │ Things you can do                     │                                     │
│        │ [ Raise a request ]  Go to the requests│                                     │
│        │                      queue · Open the  │                                     │
│        │                      device record     │                                     │
│        └───────────────────────────────────────┘                                     │
│ ──────────────────────────────────────────────────────────────────────────────────── │
│  Polymath College · Technology Management Desk                          Design kit    │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 `dashboard.html` — phone 400

```
┌──────────────────────────────────────┐
│ [skip to main content]               │
│ ▣ Polymath College        [ Sign out]│  56px, sticky
│ ─────────────────────────────────────│
│ ‹ Raise a request │ Home │ Requests ›│  56px strip, scrolls sideways
│ ─────────────────────────────────────│
│ Home                                 │  breadcrumb 15px
├──────────────────────────────────────┤
│ Home                                 │  h1 34px Newsreader
│ Friday 11 September 2026. Here is    │  lead 19px
│ what needs doing today.              │
│ ▸ On this page                       │  <details>, 48px
│ ═════════════════════════════════════│
│ What needs doing                     │  h2 24px
│   6  requests open                   │  56px rows, 1px rules
│   2  are urgent                  ⚑   │
│   1  raised today                    │
│   3  devices due back next week      │
│   2  devices in repair           🔧  │
│ 128  devices in the register         │
│  34  out on loan                     │
│ ═════════════════════════════════════│
│ Requests to work on                  │
│ REQ-2048  ⚑ Urgent                   │  ruled rows, 112px
│ Projector in Lab 2 shows a blue      │
│ screen                               │
│ ↻ In progress · Suresh Kumara        │
│ ─────────────────────────────────────│
│ … three more …                       │
│ See all requests →                   │
│ ═════════════════════════════════════│
│ Devices to watch  … three rows …     │
│ ═════════════════════════════════════│
│ Requests raised in the last five     │
│ school days                          │
│  Mon ████████    1                   │  bars keep the horizontal form
│  Tue ████████████████ 2              │
│  Wed │  0                            │
│  Thu ████████    1                   │
│  Fri ████████    1                   │
│  Mon 1 · Tue 2 · Wed 0 · Thu 1 ·     │
│  Fri 1                               │
│ ═════════════════════════════════════│
│ Things you can do                    │
│ [ Raise a request                 ]  │  52px
│ Go to the requests queue →           │
│ Open the device record →             │
│ ─────────────────────────────────────│
│ Polymath College · Technology        │
│ Management Desk        Design kit    │
└──────────────────────────────────────┘
```

### 2.3 `requests.html` — desktop 1440

**This wireframe replaces the earlier one.** The `Search and filters` and
`The queue` headings are gone, the filter controls have moved into the margin
`<aside>`, and the breadcrumb row is gone from this page — the three bands that
were pushing the queue below the fold.

```
│ ▣  Polymath College                              Nimali Perera · ICT Technician      │  66  (row 1 + 2px rule)
│    Technology Management Desk                                        [ Sign out ]    │
│ ══════════════════════════════════════════════════════════════════════════════════════│
│  Home     Requests     Devices     Raise a request                                   │  57  (row 2 + 1px rule)
│           ────────                             ─────────────────                     │
│ ──────────────────────────────────────────────────────────────────────────────────── │
│                                                                                      │  36  page-head top padding
│        ┌──────────────── 680px ────────────────┐  ┌──── 240px ────┐                  │
│        │ Requests                              │  │ Filter and    │  52  h1 44/52
│        │                                       │  │ sort          │  12  gap
│        │ Everything staff have asked us to fix.│  │ ───────────── │  64  lead 20/32 ×2
│        │ Open the ones marked urgent first.    │  │ Status        │  18  gap
│        │                                       │  │ [All        ⌄]│
│        │ Search requests                       │  │ How urgent    │  24  label 16/24
│        │                                       │  │ [All        ⌄]│   6  gap
│        │ [ Reference, words, or a person's   🔍]│  │ Who is on it  │  48  field
│        │                                       │  │ [Anyone     ⌄]│  18  gap
│        │ Showing 8 of 8 requests               │  │ Sort          │  24  count 17/24
│        │ ───────────────────────────────────── │  │ [Newest     ⌄]│  13  gap + 1px rule
│        │ REQ-2048        ⚑ Urgent   ↻ In progr.│  │               │ ─── first row top: 438
│        │ Projector in Lab 2 shows a blue screen│  │ Clear the     │ 109  ruled row
│        │ Suresh Kumara · Nimali Perera ·       │  │ filters       │
│        │ Fri 11 Sep 2026, 8:15 am              │  │               │
│        │ ───────────────────────────────────── │  │ (sticky, top  │
│        │ REQ-2047        ⚑ Normal   ★ New      │  │  offset 123)  │ 109  row top: 547
│        │ Laptop will not connect to the staff  │  └───────────────┘
│        │ Wi-Fi                                 │
│        │ Dilani Fernando · Nobody yet ·        │
│        │ Thu 10 Sep 2026, 11:20 am             │
│        │ ───────────────────────────────────── │
│        │ REQ-2046 … ◷ Waiting on someone       │                                 109  top: 656
│        │ ───────────────────────────────────── │
│        │ REQ-2045 … ★ New                      │                                 109  top: 765
│        │ ───────────────────────────────────── │
│        │ REQ-2044 … ✔ Fixed                    │                                 109  top: 874  ← 5th row
│ ─ ─ ─ ─│─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  900px fold
│        │ REQ-2043 · REQ-2042 · REQ-2041        │                                 983, 1092, 1201
│        │  ‹ Previous        1        Next ›    │
│        └───────────────────────────────────────┘
```

**Vertical budget at 1440×900 — build to these numbers.**

| Band | Height | Cumulative |
|---|---|---|
| Masthead row 1 + 2px `--ink` rule | 66 | 66 |
| Masthead row 2 + 1px `--rule` line | 57 | 123 |
| Page-head top padding | 36 | 159 |
| `<h1>` `Requests`, 44/52 | 52 | 211 |
| gap | 12 | 223 |
| Lead, 20/32, two lines | 64 | 287 |
| gap | 18 | 305 |
| `Search requests` label, 16/24 | 24 | 329 |
| gap | 6 | 335 |
| Search field | 48 | 383 |
| gap | 18 | 401 |
| `Showing 8 of 8 requests`, 17/24 | 24 | 425 |
| gap + 1px `--rule` | 13 | 438 |
| **First request row starts** | — | **438** |

Row pitch is **108–112px** (18px padding, a 24px reference/urgency/status line, a
30px sentence line, a 24px metadata line, 18px padding, 1px rule). At 109px the
five row tops are 438 · 547 · 656 · 765 · 874, and the sixth is at 983 — five rows
above the fold with 26px of margin.

The tolerance, so the builder can check rather than guess: with a 109px pitch the
first row top must land between **355px and 463px**. If the measured row count is
not 5, adjust the page-head top padding (the one band with slack) and re-measure;
do not change the row pitch, which is what gives this direction its reading
comfort.

The margin `<aside>` is sticky with a 123px top offset (the masthead height) and
holds the three filters, the sort control and `Clear the filters` stacked at 44px
each — it is 328px tall, shorter than the five rows beside it, so it never sets the
page height.

Broadsheet's queue is a `<table>` in the markup — it is tabular data — but it is
**styled as ruled rows**, with the column names carried in visually hidden spans
inside each cell and `<th scope="col">` headers in a visually hidden `<thead>`. The
`Sort` control in the margin is the visible affordance instead of clickable
headers, so nothing depends on a small target.

The queue has no heading of its own: the `<h1>` `Requests` names it, and
`Showing 8 of 8 requests` is the only line between the search field and the first
row. The `<table>` carries `id="queue"` so the second skip link can reach it.

### 2.4 `requests.html` — phone 400

```
┌──────────────────────────────────────┐
│ ▣ Polymath College        [ Sign out]│
│ ‹ Raise a request │ Home │ Requests ›│
├──────────────────────────────────────┤
│ Requests                             │
│ Everything staff have asked us to    │
│ fix. Open the ones marked urgent     │
│ first.                               │
│ Search requests                      │
│ [ Reference, words, or a person's  🔍]│  52px
│ ▸ Filter and sort                    │  48px <details>
│ ═════════════════════════════════════│
│ Showing 8 of 8 requests              │
│ ─────────────────────────────────────│
│ REQ-2048            ⚑ Urgent         │  132px ruled rows
│ Projector in Lab 2 shows a blue      │
│ screen                               │
│ ↻ In progress                        │
│ Suresh Kumara · Nimali Perera        │
│ Fri 11 Sep 2026, 8:15 am             │
│ ─────────────────────────────────────│
│ … seven more …                       │
│ ‹ Previous    1    Next ›            │
└──────────────────────────────────────┘
```

### 2.5 `device.html` — desktop / phone

```
DESKTOP                                                PHONE
│ Devices › IT-0142       (the only page with a breadcrumb row)
│                                                     ┌──────────────────────┐
│  ┌────────── 680px ──────────┐ ┌─── 240px ───┐      │ ▣ Polymath  [Sign out]│
│  │ IT-0142 — Dell Latitude   │ │ On this page│      │ ‹ Raise… │ Home │ …  ›│
│  │ 3540 laptop               │ │ ▌Where this │      │ Devices › IT-0142    │
│  │ Laptop · Issued to Dilani │ │  device is  │      │                      │
│  │ Fernando · Grade 6B       │ │  What it    │      ├──────────────────────┤
│  │ Classroom                 │ │  cost and   │      │ IT-0142 — Dell       │
│  │ ✋ Issued   ✔ Good         │ │  how long   │      │ Latitude 3540 laptop │
│  │ [ Raise a request about   │ │  it is      │      │ Laptop · Issued to   │
│  │   this device ]           │ │  covered    │      │ Dilani Fernando ·    │
│  │  Mark it returned         │ │  Requests   │      │ Grade 6B Classroom   │
│  │ ══════════════════════════│ │  about this │      │ ✋ Issued  ✔ Good     │
│  │ Where this device is      │ │  device     │      │ [ Raise a request    │
│  │  Who has it   Dilani F.   │ │  What has   │      │   about this device ]│
│  │  Where        Grade 6B    │ │  happened   │      │  Mark it returned    │
│  │  Given out    Tue 25 Aug  │ │  to it      │      │ ▸ On this page       │
│  │  Due back     Mon 21 Sep  │ └─────────────┘      │ ═════════════════════│
│  │  Last checked Thu 3 Sep   │                      │ Where this device is │
│  │ ══════════════════════════│                      │ …5 ruled rows…       │
│  │ What it cost and how long │                      │ What it cost and how │
│  │ it is covered             │                      │ long it is covered   │
│  │  Value        Rs 285,000  │                      │ …4 ruled rows…       │
│  │  Bought       14 Feb 2024 │                      │ Requests about this  │
│  │  Warranty     13 Feb 2027 │                      │ device               │
│  │  Serial       5CG4113XYZ  │                      │ …2 ruled rows…       │
│  │ ══════════════════════════│                      │ What has happened to │
│  │ Requests about this device│                      │ it                   │
│  │  REQ-2047  ★ New …        │                      │ …5 dated entries…    │
│  │  REQ-1902  ⛁ Closed …     │                      └──────────────────────┘
│  │ ══════════════════════════│
│  │ What has happened to it   │
│  │  Thu 10 Sep 2026, 11:20 am│   date set in Newsreader italic, hanging left;
│  │  Dilani Fernando          │   the entry indented 24px against a 1px rule
│  │  Raised REQ-2047 — will   │
│  │  not connect to the staff │
│  │  Wi-Fi                    │
│  │  ─────────────────────────│
│  │  … four more …            │
│  └───────────────────────────┘
```

### 2.6 `request-form.html` — desktop / phone

The article column narrows to 560px for the form (a shorter measure than the prose,
because a field the width of a paragraph invites an essay). The "On this page"
index lists the four `<h2>`s so a long form can be jumped through.

```
│ (no breadcrumb row — "Raise a request" is a masthead item)      │
│  ┌──────── 560px ────────┐  ┌─── 240px ───┐                     │
│  │ Raise a request       │  │ On this page│                     │
│  │ Tell us what is wrong.│  │ ▌About the  │                     │
│  │ We will pick it up    │  │  problem    │                     │
│  │ from the ICT Room.    │  │  How soon   │                     │
│  │ ┌───────────────────┐ │  │  you need it│                     │
│  │ │ ⚠ We couldn't send│ │  │  Anything to│                     │
│  │ │   this yet — 2    │ │  │  show us    │                     │
│  │ │   things need your│ │  │  Who is     │                     │
│  │ │   attention       │ │  │  asking     │                     │
│  │ │  • What is wrong? │ │  └─────────────┘                     │
│  │ │  • Where is it?   │ │    2px danger rule on its left edge, │
│  │ └───────────────────┘ │    no fill                           │
│  │ ══════════════════════│                                      │
│  │ About the problem     │                                      │
│  │ What is it about?     │  label 17px Source Sans 3 semibold   │
│  │ Pick the device, or   │  help 16px italic Newsreader         │
│  │ choose "Not about a   │                                      │
│  │ particular device".   │                                      │
│  │ [                  ⌄] │  48px, 1px underline-style field     │
│  │ What is wrong?        │                                      │
│  │ One short line, for   │                                      │
│  │ example "Projector    │                                      │
│  │ will not turn on".    │                                      │
│  │ [                    ]│  2px danger underline when invalid   │
│  │ ⚠ Type a short        │                                      │
│  │   description of the  │                                      │
│  │   problem, for example│                                      │
│  │   "Projector will not │                                      │
│  │   turn on".           │                                      │
│  │ … fields 3 and 4 …    │                                      │
│  │ ══════════════════════│                                      │
│  │ How soon you need it  │                                      │
│  │ ( ) Can wait          │  56px rows                           │
│  │ (•) Normal            │                                      │
│  │ ( ) Urgent            │                                      │
│  │ … sections 3 and 4 …  │                                      │
│  │ [ Send the request ]  │                                      │
│  │   Cancel              │  quiet link-button, 24px away        │
│  └───────────────────────┘                                      │
```

Fields in Broadsheet are **underline fields**: no box, a 1px `--rule-strong` line
under a 48px area, going 2px `--brand` on focus and 2px `--danger` on error, with
`--surface` fill so the target area is obvious. The `ui-kit.html` page shows this
side by side with its focus and error states so the treatment is unambiguous.

### 2.7 `login.html` and `ui-kit.html`

- **`login.html`** — a title page. The masthead rule runs across the top, the crest
  sits at 104px centred, `Welcome back` is Newsreader 44px, the sub-line is 19px,
  and the two underline fields sit in a 380px column with 32px between them. A 2px
  rule closes the block above the `Sign in` button. No card, no shadow, no border —
  only the paper and the rules. Phone: crest 76px, everything full width minus 24px.
- **`ui-kit.html`** — the article column with one `<h2>` per component family and
  the "On this page" index listing all of them. Each specimen sits between two 1px
  rules with a Newsreader-italic caption naming the class and its tokens. The colour
  table gives swatch, token, hex, the pair checked and the ratio.

---

## 3. Type

Google Fonts: `Newsreader` (400, 500, 600, plus 400 italic) ·
`Source Sans 3` (400, 600, 700).

| Role | Family / weight | Size / line-height | Notes |
|---|---|---|---|
| Wordmark `Polymath College` | Newsreader 600 | 22/26, `letter-spacing:.005em` | Masthead and login |
| h1 | Newsreader 600 | 44/52 desktop, 34/42 phone | |
| h2 | Newsreader 600 | 28/36 desktop, 24/32 phone | |
| h3 | Newsreader 500 | 21/30 | |
| Body / prose | Source Sans 3 400 | **18/30** | The largest body text of the five |
| Lead paragraph | Source Sans 3 400 | 20/32 `--muted` | |
| Long text in a record | Source Sans 3 400 | 18/30 | |
| Timeline date | Newsreader 400 italic | 17/24 | Hangs left of the entry |
| Help text | Newsreader 400 italic | 16/24 | Italic marks it as the editor's aside |
| Form label | Source Sans 3 600 | 17/24 | |
| Button | Source Sans 3 700 | 17/22 | |
| Nav label | Source Sans 3 400/700 | 17/22 | Bold only for the current page |
| Table/row metadata | Source Sans 3 400 | 16/24 `--muted` | |
| Figure number | Newsreader 500 | 30/34, tabular numerals | |
| Section index | Source Sans 3 400 | 16/24 | |

Measure: 66 characters for prose (`--measure: 66ch`, which sets the 680px column at
18px), 560px for the form. Headings are never letterspaced and never uppercase.

---

## 4. Palette

Derivation. `#722A82` is `hsl(289, 51%, 34%)`. Broadsheet keeps the hue and drops
its saturation almost to nothing for the paper: every neutral is `hsl(285, 10–30%,
…)`, so the page is a lilac-grey cast of the crest rather than a separate colour.
Ink is the same hue at 12% lightness, which is why the type looks black but never
cold. Functional hues are placed far from 287° (158 · 40 · 348 · 202) so they can
never be mistaken for the brand.

| Token | Hex | Derivation |
|---|---|---|
| `--brand` | `#722A82` | The crest, unmodified |
| `--brand-strong` | `#4A1857` | Crest hue at L 24% |
| `--brand-tint` | `#F2E9F6` | Crest hue at L 95% |
| `--rule-brand` | `#C6B0D0` | Crest hue at L 76% — decorative |
| `--ink` | `#1A1420` | Crest hue at S 20% L 12% |
| `--muted` | `#5C5266` | Crest hue at S 10% L 36% |
| `--rule` | `#DCD2E4` | Crest hue at L 86% — 1px section rules |
| `--rule-strong` | `#8C8095` | Crest hue at S 14% L 54% — field underlines |
| `--bg` | `#F7F3FA` | Crest hue at S 30% L 97% — the paper |
| `--surface` | `#FFFFFF` | The article column and field areas |
| `--surface-2` | `#EFE8F4` | Crest hue at L 94% — hover and selected rows |
| `--ok` | `#0C5F46` | Fixed, Good, In store |
| `--ok-tint` | `#E3F1EB` | |
| `--warn` | `#7A5300` | Waiting on someone, In repair, Needs repair |
| `--warn-tint` | `#F7EEDC` | |
| `--danger` | `#A3244A` | Urgent, Out of service, errors |
| `--danger-tint` | `#FAE7EC` | |
| `--info` | `#0B5478` | New |
| `--info-tint` | `#E4EFF6` | |
| `--focus` | `#722A82` | |

**Contrast pairs** (expected values; recompute and print them in the folder README):

| Pair | Ratio | Needs |
|---|---|---|
| `--ink` on `--surface` | 18.0:1 | 4.5 |
| `--ink` on `--bg` | 16.4:1 | 4.5 |
| `--muted` on `--surface` | 7.3:1 | 4.5 |
| `--muted` on `--bg` | 6.7:1 | 4.5 |
| `--surface` on `--brand` (primary button) | 8.9:1 | 4.5 |
| `--brand` on `--surface` | 8.9:1 | 4.5 |
| `--brand` on `--bg` | 8.1:1 | 4.5 |
| `--brand-strong` on `--brand-tint` | ≥12:1 | 4.5 |
| `--rule-strong` on `--surface` (field underline) | 3.7:1 | 3.0 |
| `--ok` on `--surface` | 7.6:1 | 4.5 |
| `--warn` on `--surface` | 6.8:1 | 4.5 |
| `--danger` on `--surface` | 7.2:1 | 4.5 |
| `--info` on `--surface` | 8.2:1 | 4.5 |
| Each functional colour on its own tint | ≥5:1 | 4.5 |
| `--focus` on `--bg` | 8.1:1 | 3.0 |

`--rule` (1.4:1) and `--rule-brand` (2.2:1) are decorative hairlines. A field
underline always uses `--rule-strong` or darker.

---

## 5. Space, radius, depth

- **Space, 6px base:** `--s1 6` `--s2 12` `--s3 18` `--s4 24` `--s5 36` `--s6 54`
  `--s7 72`. Paragraph spacing 18px; rule-to-heading 36px; section-to-section 54px.
- **Radius: `0` everywhere.** The only exception is the 999px status pill, which
  earns its curve by being the one thing that is not text.
- **Depth: no shadows at all,** except a single `--shadow-pop:
  0 18px 48px rgba(26,20,32,.18)` on the modal and the toast, which sit above the
  page rather than on it. Everything else is separated by rules:
  `--rule-hair 1px`, `--rule-section 2px --ink`.
- **Grid:** 1040px band = 680 article + 40 gutter + 240 index, centred, with 48px
  page gutters. Below 1080px the index moves inline as a `<details>` and the
  article takes the full band.

---

## 6. Components

| Component | Treatment |
|---|---|
| Primary button | `--brand` fill, `--surface` label, **square**, 48px tall, padding `12px 24px`. Hover L −6%. Only one per page. |
| Secondary button | No fill, 2px `--ink` border, `--ink` label, 48px, square. |
| Quiet button / link | `--brand` text with a 1px underline that thickens to 2px on hover; 44px hit area through padding. `Cancel` is this. |
| Destructive button | 2px `--danger` border, `--danger` label, `--danger-tint` fill on hover. Kept 24px from the primary. |
| Icon-only button | 48×48, always `aria-label`ed; used only for search-clear. |
| Busy button | `Sending…`, 18px spinner, `aria-busy="true"`, width locked. |
| Field | Underline field: 48px area, `--surface` fill, 1px `--rule-strong` bottom border only. Focus: 2px `--brand` underline **and** a 3px `--focus` ring around the whole field area. Error: 2px `--danger` underline plus the message. |
| Label / help | Label 17px semibold; help in Newsreader italic 16px between label and field, wired with `aria-describedby`. |
| Row (request / device) | No card. 1px `--rule` above, 18px padding, reference and status on the first line, the sentence at 18px on the second, metadata 16px `--muted` on the third. Hover fills the row `--surface-2` edge to edge. |
| Fact list | `<dl>` with the term 16px `--muted` in a 140px left column and the value 18px `--ink`, one 1px rule per pair. |
| Status badge | 28px pill, 999px radius, tint fill, no border, 18px linear icon + word at 15px semibold. |
| Urgency chip | Text plus icon, no fill, no border — `⚑ Urgent` set in `--danger`, `⚑ Normal` and `⚑ Can wait` in `--muted`. Its weight, not a box, carries the difference. |
| Timeline item | The date hangs in the 140px left column in Newsreader italic; the entry sits against a 1px `--rule-brand` vertical line with 24px indent. No dots. |
| Alert | 2px left rule in the functional hue, no fill, 20px icon, `<h2>`-weight title in Newsreader 21px, body 18px. |
| Toast | Bottom-left, `--ink` fill, `--surface` text, square, `--shadow-pop`, with `Undo` and `Close`. `role="status"`, 8s, pauses on hover/focus. |
| Modal | 520px, square, `--surface`, 2px `--ink` border, `--shadow-pop`. `role="dialog" aria-modal="true"`. |
| Empty state | Centred between two 2px rules: 48px linear icon, `<h2>`, one sentence, one button, 54px of air above and below. |
| Pagination | `‹ Previous`, the number, `Next ›` on one ruled line, 48px targets, 24px apart. |
| Avatar | No avatar image: the person is set as text, `Nimali Perera · ICT Technician`. The ui-kit shows a 40px square `--brand-tint` initials block for the places a name is too long. |
| Icons | **Solar Linear**, 1.5px strokes, inline SVG, `currentColor`, 18px beside text, 20px in alerts, 48px in empty states. Light strokes suit a page made of rules. |

**Status vocabulary — identical in every direction:** `New` star ·
`In progress` refresh-circle · `Waiting on someone` clock-circle ·
`Fixed` check-circle · `Closed` archive · `In store` box · `Issued` hand-holding ·
`In repair` wrench · `Out of service` close-circle · `Good` check-circle ·
`Needs repair` danger-triangle · `Can wait` hourglass · `Normal` flag ·
`Urgent` fire (the crest's torch flame). Icon **and** word, always.

---

## 7. The one chart

Broadsheet shows exactly one chart: **Requests raised in the last five school days**
(Mon 1 · Tue 2 · Wed 0 · Thu 1 · Fri 1).

- Form: **horizontal** bars, one per day, because the labels are words and a
  horizontal bar lets them be read normally at the start of each line.
- One series, so no legend. Each bar is `--brand`; the value sits at the end of the
  bar in `--ink`, not inside it. Tuesday is the only bar with a `--brand-strong`
  fill and it is the one directly labelled as the busiest day.
- **Wednesday is zero, and a zero must be visible.** A bar of no length reads as
  missing data, not as "no requests". Draw Wednesday as a 2px `--rule-strong` tick
  on the left baseline — an empty bar — with its value label `0` in `--muted` 16px
  at the same place the other days' numbers sit, just past the end of the bar. The
  day keeps its label and its row, so the week still reads as five days with one
  zero in it.
- Bars 16px tall, 12px apart, square ends, sitting against a 1px `--rule` baseline
  at the left. No gridlines, no axis box, no gradient, no 3-D.
- Inline SVG with `currentColor`, `role="img"`, `aria-label`
  `Requests raised: Monday 1, Tuesday 2, Wednesday 0, Thursday 1, Friday 1.` —
  this sentence is fixed by the Content contract; use it exactly, with no rewording.
- The text alternative `Mon 1 · Tue 2 · Wed 0 · Thu 1 · Fri 1` is printed under the
  bars for everyone, always.
- `--brand` on `--surface` is 8.9:1, far past the 3:1 a meaningful graphic needs.

---

## 8. Density intent

Broadsheet is **low–medium**: fewer rows than the working screens, more words in
each. At 1440×900 the chrome above the first queue row is **438px** — 123px
masthead (two rows; the breadcrumb row exists only on `device.html`), 182px page
head, 96px search block, 37px count line — and the row pitch is 108–112px, so
**5 request rows start above 900px**. The band-by-band budget is the table in §2.3;
build to it, measure, and state the measured number in the folder `README.md`.

This is the direction's ladder position: it sits between Parchment (4) and Signpost
(6), and it gets there by spending its space on the reading column rather than on
the filter apparatus, which lives in the margin.

---

## 9. States

| State | What the user sees |
|---|---|
| Default | As drawn. |
| Loading | The enhanced filter swaps the count line for `Finding requests…` with an 18px spinner, inside an `aria-live="polite"` region. Nothing else is async. |
| Empty (`requests.html?demo=empty`) | Between two 2px rules: `No requests match what you chose` / `Try clearing the filters, or search for a different word.` / `[ Clear the filters ]`. The search box and every filter keep the user's choices. |
| Validation errors (`request-form.html?demo=errors`) | `We couldn't send this yet — 2 things need your attention` in a 2px `--danger` left-ruled block with a link to each field. Each field keeps its value, gets `aria-invalid="true"`, a 2px `--danger` underline and its message. Focus moves to the summary. |
| Server error | Same treatment, above the form: `We couldn't save that just now` / `Nothing you typed has been lost. Wait a moment and press "Send the request" again.` |
| Success | Toast `Request sent. We gave it the number REQ-2049.` with `Undo`, plus the same sentence as a success alert at the top of the page landed on. |
| Sign-in error (`login.html?demo=error`) | `We couldn't sign you in` / `That username or password didn't match. Try again, or ask the office to reset it.` above the fields; `nimali.p` stays; focus to the password field. |
| No permission (`device.html?demo=denied`) | The article column carries only: 48px lock icon, `You can't open this page`, `This page is for ICT staff. Ask Nimali Perera in the ICT Room, or raise a request and we will help.`, `[ Raise a request ]`. The masthead and breadcrumbs stay. |

---

## 10. Copy — use these words exactly

The wording is identical in all five directions. In full, so this file stands alone:

**Global** — wordmark `Polymath College`; sub-line `Technology Management Desk`;
navigation `Home` · `Requests` · `Devices` · `Raise a request`; utility
`Nimali Perera`, `ICT Technician`, `Design kit`, `Sign out`; skip link
`Skip to main content`; section index title `On this page`.

**`login.html`** — `Welcome back` / `Sign in to the Technology Management Desk.` /
`Username` + `The name the school gave you, like nimali.p` / `Password` +
`Passwords are case sensitive.` / `Sign in` / `We couldn't sign you in` +
`That username or password didn't match. Try again, or ask the office to reset it.` /
`Polymath College · Technology Management Desk`.

**`dashboard.html`** — `<h1>` `Home`; lead
`Friday 11 September 2026. Here is what needs doing today.`; `<h2>`s
`What needs doing`, `Requests to work on`, `Devices to watch`,
`Requests raised in the last five school days`, `Things you can do`; figures worded
`6 requests open` · `2 are urgent` · `1 raised today` ·
`3 devices due back next week` · `2 devices in repair` ·
`128 devices in the register` · `34 out on loan`; links `See all requests`,
`Open the device record`, `Go to the requests queue`.

**`requests.html`** — `<h1>` `Requests`; lead
`Everything staff have asked us to fix. Open the ones marked urgent first.`; the
margin `<aside>` heading `Filter and sort` (the same words as the phone
`<details>`), and no other heading on the page; `Search requests` +
`Reference, words, or a person's name, e.g. projector or REQ-2048`; filters
`Status` (`All statuses` + the five) · `How urgent` (`All`, `Can wait`, `Normal`,
`Urgent`) · `Who is on it` (`Anyone`, `Nobody yet`, `Nimali Perera`,
`Ruwan Jayasuriya`); sort `Newest first`, `Most urgent first`, `Oldest first`;
`Showing 8 of 8 requests`; column names `Reference`, `What is wrong`, `Raised by`,
`Status`, `How urgent`, `Who is on it`, `Raised`; empty
`No requests match what you chose` /
`Try clearing the filters, or search for a different word.` / `Clear the filters`.

**`device.html`** — `<h1>` `IT-0142 — Dell Latitude 3540 laptop`; lead
`Laptop · Issued to Dilani Fernando · Grade 6B Classroom`; `<h2>`s
`Where this device is`, `What it cost and how long it is covered`,
`Requests about this device`, `What has happened to it`; buttons
`Raise a request about this device`, `Mark it returned`; modal
`Mark IT-0142 returned?` /
`This puts the laptop back in the ICT Store and clears the due-back date. You can give it out again at any time.` /
`Yes, mark it returned` · `No, keep it as it is`; toast
`IT-0142 is back in the ICT Store.`

**`request-form.html`** — `<h1>` `Raise a request`; lead
`Tell us what is wrong. We will pick it up from the ICT Room.`; `<h2>`s
`About the problem`, `How soon you need it`, `Anything to show us`,
`Who is asking`; the seven fields with labels, help text and options exactly as
listed in the task brief's Content contract; buttons `Send the request`, `Cancel`;
errors `Type a short description of the problem, for example "Projector will not turn on".`
and `Choose the room where we will find it.`; summary
`We couldn't send this yet — 2 things need your attention`; toast
`Request sent. We gave it the number REQ-2049.` with `Undo`.

**Strings the Content contract settles, and that are easy to get wrong.** These are
the planner's, now part of the contract; use them exactly.

| Where | Text |
|---|---|
| First option of `What is it about?` | `Choose a device`, then the eight devices, then `Not about a particular device` |
| First option of `Where is it?` | `Choose a room`, then the eight rooms |
| `REQ-1902` in `Requests about this device` | `Battery replaced under warranty` — render the row as `REQ-1902 · ⛁ Closed · Battery replaced under warranty · Fri 12 Jun 2026` |
| `REQ-2047` in the same list | `Laptop will not connect to the staff Wi-Fi` |
| A request nobody has picked up | `Nobody yet` |
| Result line in the empty state | `Showing 0 of 8 requests` |
| The devices figure | `3 devices due back next week` — the week after the one we are in, never the current one |

The filter selects keep their own first options from the contract — `All statuses`,
`All`, `Anyone` — and the sort select has no prompt option, because it always has a
value.

**Dates and weekdays.** Today is **Friday 11 September 2026** everywhere. Copy each
date and its weekday from the contract together, and never write a weekday that
does not match its date: REQ-2048 raised `Fri 11 Sep 2026, 8:15 am`; REQ-2047
`Thu 10 Sep 2026, 11:20 am`; REQ-2045 `Tue 8 Sep 2026, 7:35 am`; IT-0142 given out
`Tue 25 Aug 2026`, returned to the ICT Store `Fri 21 Aug 2026, 3:05 pm`, battery
replaced `Fri 12 Jun 2026, 9:30 am`, last checked `Thu 3 Sep 2026`; the history
entry for REQ-2047 is dated `Thu 10 Sep 2026, 11:20 am`. The one chart reads
`Mon 1 · Tue 2 · Wed 0 · Thu 1 · Fri 1`, with Wednesday drawn as a labelled empty
bar whose value label reads `0`, and the chart's text alternative fixed by the
contract as `Requests raised: Monday 1, Tuesday 2, Wednesday 0, Thursday 1, Friday 1.`

**Sample rows** come verbatim from the Content contract in
`docs/tasks/002-design-directions.md`.

---

## 11. Accessibility

- **Landmarks:** `<header>` (masthead) containing `<nav aria-label="Main">`;
  `<main id="main">`; `<nav aria-label="On this page">` (a sibling of the article,
  inside `<main>`); `<footer>` with `<nav aria-label="Utility">`.
- **Breadcrumbs** are `<nav aria-label="Breadcrumb">` with an `<ol>`, the last item
  marked `aria-current="page"` and not a link. They appear on `device.html` only,
  where there is a level to climb; the other pages are one step from the masthead
  and the `<h1>` already says where you are.
- **Headings:** one `<h1>`; `<h2>` per section; `<h3>` only inside ui-kit specimens.
  The "On this page" index is generated from exactly those `<h2>`s, so the visual
  index and the screen-reader outline are the same list. `requests.html` has no
  `<h2>` in its article column — the `<h1>` names the queue and the count line
  measures it — so its margin slot carries the `Filter and sort` `<aside>` instead
  of an index, and that `<aside>` has its own `<h2>`. An outline of one heading on a
  single-purpose list page is correct, not a gap.
- **Skip link** first, visible on focus, to `#main`. A second skip link, after the
  masthead, goes to `#queue` on `requests.html` — the `id` sits on the `<table>`,
  and it now also skips the margin filters, which is the point of having it.
- **Form wiring:** `<label for>`; help `<p id="…-help">` and error `<p id="…-error">`
  both in `aria-describedby`, in that order; `aria-invalid="true"` on failed fields
  only; `<fieldset>` + `<legend>How urgent is it?</legend>` for the radios with its
  help linked to the fieldset; error summary `role="alert" tabindex="-1"`, focused
  on load, links move focus to the field.
- **The queue table** keeps `<caption class="visually-hidden">Requests, newest
  first</caption>`, `<th scope="col">` headers and `<th scope="row">` on the
  reference, even though it is styled as ruled rows. `aria-sort` reflects the sort
  control.
- **The scrolling nav strip** never hides an item from the keyboard: all four are
  in the DOM, focusable, and `scroll-margin-inline: 24px` brings a focused item into
  view. It is not a carousel and has no arrows to press.
- **Focus ring:** 3px `--focus` with a 2px `--surface` offset. On underline fields
  the ring surrounds the whole 48px field area, not just the line.
- **Dialogs and redirects:** the modal traps focus, Escape closes, focus returns to
  `Mark it returned`; after a redirect focus is placed on the `<h1>`.
- **Touch targets:** nav strip items 48px tall by at least 88px wide; fields 48px;
  buttons 48px; rows 132px on phone; pagination 48px with 24px between. Inline links
  inside a sentence of prose are the only exemption and are underlined.
- **Colour is never alone:** icon + word on every status, condition and urgency;
  the urgency chip also changes weight, not only colour.

---

## 12. Motion

Print does not move, so almost nothing here does.

- Link and nav underlines grow from 1px to 2px in 150ms `ease-out`.
- The desktop section index marker slides between items in 180ms; without
  JavaScript it simply marks the anchor that was clicked.
- Toast: fade only, 200ms. Modal: fade only, 180ms.
- No hover lift, no scale, no parallax, no scroll-triggered reveal anywhere.
- Reduced motion: the standard block setting all durations to `.01ms`,
  `animation-iteration-count: 1`, `scroll-behavior: auto`.

---

## 13. Progressive enhancement

**Plain HTML, full page load:** masthead and strip navigation, breadcrumbs, the
`<details>` section index and filter panel, the filter/sort `<form method="get">`
with its own `Apply` button, the request form, sign-out, pagination, and the modal
as a `<dialog>` with a link-to-section fallback.

**`app.js` adds:** the scrollspy that marks the current `<h2>` in the desktop index;
in-place filtering with the live count line; hiding the `Apply` button once
scripting exists; toast rendering; `?demo=` switching; focusing the error summary;
the modal focus trap. Hooks are `data-*` attributes only.

---

## 14. Demo hooks

`login.html?demo=error` · `request-form.html?demo=errors` ·
`requests.html?demo=empty` · `?demo=toast` on any app page ·
`device.html?demo=denied`. Prototype-only; never carried into application templates.

---

## 15. Skills the builder should load

`editorial-tech` (its asymmetric column structure, rules and mono-style utility
labels — but keep the surfaces light; this direction has no dark panels) ·
`light-mode-paper-technical` · `ui-design:readable-measure` ·
`ui-design:typography-scale` · `accessible-content:heading-structure` ·
`accessible-content:table-accessibility` · `ux-strategy:information-architecture`
(for the "On this page" index) · `dataviz` (the one chart) ·
`cognitive-accessibility:plain-language-design` · `solar-duotone-bold` (use the
**Linear** weight of the same family).
