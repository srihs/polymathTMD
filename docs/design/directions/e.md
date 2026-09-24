`design/e-workbench/`

# Direction E — Workbench

**Concept.** Workbench is the two-handed screen: a dark plum command bar with the
search box at its centre sits over two panes — the list you are working through on
the left, the record you are working on at the right — so a technician never loses
the queue to open a job. On a phone the two panes become a stack: the list, then the
record with a `Back to the list` link at the top, which is the same mental model
one screen at a time.

**Who it suits.** Nimali's real task is not "look at a request", it is "work down
the queue without forgetting where she was". Two panes make the queue permanent:
she reads REQ-2048, deals with it, and REQ-2047 is already under her eye. The
search box is in the chrome rather than on a page because the fastest route to
`IT-0142` for someone holding a device with a sticker on it is to type the sticker.
The dark chrome earns its place practically: it separates "where I am in the
system" from "what I am reading", so the white record pane is the only bright thing
on the screen and the eye goes there first — useful on a shared machine in a room
with the lights on.

---

## 1. Navigation model

**Desktop (≥1080px): a search-led command bar over a two-pane master–detail layout.**

- 64px command bar, `--chrome` fill, full bleed, fixed:
  - Left: crest chip 30px + `Polymath College` in Sora 15px.
  - **Centre, and the widest thing in the bar: the search field**, 520px, 44px
    tall, `--chrome-2` fill with a 1px `--chrome-line` border, a 20px search icon,
    the visible label `Search requests` (visually hidden at ≥1080px, where the
    placeholder plus the icon carry it, and shown as text below 1080px), placeholder
    `Reference, words, or a person's name, e.g. projector or REQ-2048`, and the hint
    `Press / to search` in `--chrome-muted` at its right end. It is a
    `<form method="get" action="requests.html">`, so it works with no script at all.
  - Right: the four navigation items as compact 44px icon+word links —
    `Home`, `Requests` (with `6`), `Devices` — then `Raise a request` as a filled
    `--brand` button, then a 36px `NP` avatar linking to the utility menu.
- Below the bar, a 40px breadcrumb/context strip on `--canvas` holding
  `Requests › REQ-2048` and, at its right, the pane controls (`Sort`, `Showing 8 of
  8 requests`).
- **The two panes**, filling the rest of the viewport height, each scrolling
  independently:
  - **List pane**, 480px, `--surface` with a 1px `--line` right border. 480 is not
    a round number chosen for looks: at 16px it gives the pane 448px of content,
    which sets the longest request title in the Content contract
    (`Tablet needed for the Grade 5 reading class on Monday`, 52 characters) on one
    line with room to spare. A pane that wraps its titles has rows of two different
    heights, which is what breaks both the rhythm and the row count. It holds
    the queue on `requests.html`, the day's work on `dashboard.html`, the record's
    sections on `device.html`, and the form's four sections on
    `request-form.html`. The selected item carries a 4px `--brand` left edge,
    `--brand-tint` fill and `aria-current="true"`.
  - **Record pane**, the rest, `--canvas` background with one `--surface` card per
    section, 720px measure inside it.
- Current page in the bar: `aria-current="page"`, `--brand-bright` label and a 3px
  `--brand-bright` underline sitting on the bar's bottom edge.

**Phone (<1080px): a pane stack, with the menu at the end of the document.**

- 56px bar: crest chip, the page name, and a `Menu` link — a plain anchor to
  `#menu`, a navigation block at the **end** of every page holding the four labels
  as 56px rows, the person, `Design kit` and `Sign out`. This is the classic
  no-script pattern: the menu is content, the link is a jump, and there is no
  overlay, no trap and no state.
- Under the bar, a 48px `Search requests` field (full width, the same form).
- The panes stack: `requests.html` shows the list; opening a request shows the
  record with `← Back to the list` as the first thing under the bar, at 56px.
  `device.html` shows its section list first, then each section.
- `Raise a request` is a 56px `--brand` button pinned directly under the search
  field on every page, so it is one thumb-reach away without scrolling to `#menu`.

**With JavaScript off.** The search form submits, the `#menu` anchor jumps, the
panes are two columns that become two stacked sections, and every list item is a
link. `app.js` adds the `/` shortcut, in-place filtering and the pane-swap
without a reload — none of which the task needs.

---

## 2. Wireframes

### 2.1 `dashboard.html` — desktop 1440

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ [skip to main content]                                                               │
├──────────────────────────────────────────────────────────────────────────────────────┤
│▣ Polymath  [🔍 Reference, words, or a person's name…      Press / to search ] ⌂Home  │  64px
│  College                                                    ◇Requests 6  ▤Devices    │  --chrome
│                                                             [+ Raise a request] (NP) │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ Home                                                          Friday 11 September 2026│  40px strip
├──────────────────────── 480px ─────────────┬─────────────────────────────────────────┤
│ What needs doing                   │  Requests to work on                            │
│ ───────────────────────────────────│  ┌────────────────────────────────────────────┐ │
│ ▌6    requests open                │  │ REQ-2048   ⚑ Urgent    ↻ In progress        │ │
│  2    are urgent               ⚑   │  │ Projector in Lab 2 shows a blue screen      │ │
│  1    raised today                 │  │ Suresh Kumara · Nimali Perera ·             │ │
│  3    devices due back next week   │  │ Fri 11 Sep 2026, 8:15 am                    │ │
│  2    devices in repair        🔧  │  │ "The projector switches on, then the screen │ │
│ 128   devices in the register      │  │  goes blue after about a minute. It happened│ │
│  34   out on loan                  │  │  in period 2 and period 4 on Tuesday. The   │ │
│ ───────────────────────────────────│  │  lamp hours show 3,180."                    │ │
│ Things you can do                  │  └────────────────────────────────────────────┘ │
│ [ + Raise a request            ]   │  ┌────────────────────────────────────────────┐ │
│ [ Go to the requests queue     ]   │  │ REQ-2047   ⚑ Normal    ★ New                │ │
│ [ Open the device record       ]   │  │ Laptop will not connect to the staff Wi-Fi  │ │
│ ───────────────────────────────────│  └────────────────────────────────────────────┘ │
│ Devices to watch                   │  … two more …                                   │
│ IT-0087  🔧 In repair              │  See all requests →                             │
│ Epson EB-X51 projector             │                                                 │
│ ───────────────────────────────────│                                                 │
│ IT-0056  🔧 In repair              │                                                 │
│ HP LaserJet M404 printer           │                                                 │
│ ───────────────────────────────────│                                                 │
│ IT-0142  ✋ Due Mon 21 Sep 2026     │                                                 │
│ Dell Latitude 3540 laptop          │                                                 │
│ Open the device record →           │                                                 │
└────────────────────────────────────┴─────────────────────────────────────────────────┘
```

The list pane is the day's summary; the record pane is what she would act on first,
opened already. Workbench shows **no chart** — the pane pair is the direction's
information design, and a five-bar chart would take space the second pane needs.

### 2.2 `dashboard.html` — phone 400

```
┌──────────────────────────────────────┐
│ [skip to main content]               │
│ ▣  Home                       Menu ↓ │  56px --chrome, "Menu" = anchor to #menu
├──────────────────────────────────────┤
│ [🔍 Reference, words, or a person's ]│  48px
│ [ + Raise a request              ]   │  56px --brand
├──────────────────────────────────────┤
│ Home                                 │  h1 30px
│ Friday 11 September 2026. Here is    │
│ what needs doing today.              │
│ ──────────────────────────────────── │
│ What needs doing                     │
│   6   requests open                  │  52px rows, 1px rules
│   2   are urgent                 ⚑   │
│   1   raised today                   │
│   3   devices due back next week     │
│   2   devices in repair          🔧  │
│ 128   devices in the register        │
│  34   out on loan                    │
│ ──────────────────────────────────── │
│ Requests to work on                  │
│ ┌──────────────────────────────────┐ │
│ │ REQ-2048        ⚑ Urgent         │ │  112px
│ │ Projector in Lab 2 shows a blue  │ │
│ │ screen                           │ │
│ │ ↻ In progress · Nimali Perera    │ │
│ └──────────────────────────────────┘ │
│ … three more … See all requests →    │
│ ──────────────────────────────────── │
│ Devices to watch  … three rows …     │
│ ──────────────────────────────────── │
│ Things you can do                    │
│ [ Go to the requests queue       ]   │
│ [ Open the device record         ]   │
│ ══════════════════════════════════════│
│ #menu                                │  the nav block, end of document
│ ⌂  Home                              │  56px rows
│ ◇  Requests                      (6) │
│ ▤  Devices                           │
│ +  Raise a request                   │
│ ──────────────────────────────────── │
│ NP Nimali Perera · ICT Technician    │
│ ▦  Design kit                        │
│ [ Sign out ]                         │
│ Polymath College · Technology        │
│ Management Desk                      │
└──────────────────────────────────────┘
```

### 2.3 `requests.html` — desktop 1440

```
│▣ Polymath  [🔍 Reference, words, or a person's name…      Press / to search ] ⌂Home  │
│                                                       ◇Requests 6 ▤Devices [+Raise] │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ Requests › REQ-2048            Sort [ Newest first ⌄ ]     Showing 8 of 8 requests   │
├───────────────────────── 480px ────────────┬─────────────────────────────────────────┤
│ Requests                                   │ REQ-2048                                │
│ Everything staff have asked us to fix.     │ Projector in Lab 2 shows a blue screen  │
│ Open the ones marked urgent first.         │ ⚑ Urgent   ↻ In progress                │
│ [Status      ⌄]  [How urgent          ⌄]   │ ┌─────────────────────────────────────┐ │
│ [Who is on it                          ⌄]  │ │ Raised by     Suresh Kumara         │ │
│ ───────────────────────────────────────────│ │ About which   IT-0087 Epson EB-X51  │ │
│▌REQ-2048                        ⚑ Urgent   │ │ device        projector             │ │  top: 350
│ Projector in Lab 2 shows a blue screen     │ │ Where         Science Block Lab 2   │ │
│ ↻ In progress · Fri 11 Sep 2026            │ │ Who is on it  Nimali Perera         │ │
│ ───────────────────────────────────────────│ │ Raised        Fri 11 Sep 2026,      │ │
│ REQ-2047                        ⚑ Normal   │ │               8:15 am               │ │  top: 437
│ Laptop will not connect to the staff Wi-Fi │ └─────────────────────────────────────┘ │
│ ★ New · Thu 10 Sep 2026                    │ What they told us                       │
│ ───────────────────────────────────────────│ "The projector switches on, then the    │
│ REQ-2046                        ⚑ Normal   │  screen goes blue after about a minute. │  top: 524
│ Printer jams on every second page          │  It happened in period 2 and period 4   │
│ ◷ Waiting on someone · Tue 8 Sep 2026      │  on Tuesday. The lamp hours show 3,180."│
│ ───────────────────────────────────────────│                                         │
│ REQ-2045                      ⚑ Can wait   │ [ Open the device record ]              │  top: 611
│ Tablet needed for the Grade 5 reading class│                                         │
│ ★ New · Tue 8 Sep 2026                     │   ← the longest title in the contract,  │
│ ───────────────────────────────────────────│     52 characters, still one line       │
│ REQ-2044                        ⚑ Normal   │                                         │  top: 698
│ Interactive panel pen is not writing       │                                         │
│ ✔ Fixed · Mon 7 Sep 2026                   │                                         │
│ ───────────────────────────────────────────│                                         │
│ REQ-2043                        ⚑ Normal   │                                         │  top: 785
│ No sound from the speakers in the ICT Room │                                         │
│ ⛁ Closed · Fri 4 Sep 2026                  │                                         │
│ ───────────────────────────────────────────│                                         │
│ REQ-2042                        ⚑ Urgent   │                                         │  top: 872
│ Cannot sign in to the report system        │                                         │
│ ✔ Fixed · Thu 3 Sep 2026                   │                                         │
│─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  900px fold
│ REQ-2041 …                                 │                                         │  top: 959
│ ‹ Previous    1    Next ›                  │                                         │
└────────────────────────────────────────────┴─────────────────────────────────────────┘
```

**The list-pane row, band by band.** The row is a fixed **87px** because nothing in
it wraps:

| Band | Height |
|---|---|
| Padding top | 10 |
| Reference (JetBrains Mono 15/20) with the urgency chip (24px pill) at the right | 24 |
| gap | 2 |
| Title, Work Sans 16/24, **one line** at the 448px content width | 24 |
| gap | 2 |
| Status badge (24px pill) with `· ` and the date beside it | 24 |
| Padding bottom | 10 |
| 1px `--line` rule | 1 |
| **Row** | **87** |

The title never wraps because the pane is 480px, not 400px — that one change is what
makes the row deterministic. Do **not** reach 87px by truncating the title with an
ellipsis: the sentence saying what is wrong is the most useful thing in the row, and
clipping it would be the one place this direction failed the people it is for. The
badges stay at 24px with 14px text, and the row as a whole is the 87px target, well
past the 44px floor.

**Vertical budget at 1440×900 — build to these numbers.**

| Band | Height | Cumulative |
|---|---|---|
| Command bar + 1px rule | 65 | 65 |
| Context strip + 1px rule | 41 | 106 |
| Pane-head top padding | 20 | 126 |
| `<h1>` `Requests`, 30/38 | 38 | 164 |
| gap | 8 | 172 |
| Lead, 18/28, two lines | 56 | 228 |
| gap | 16 | 244 |
| Filter row 1 — `Status` and `How urgent` side by side | 44 | 288 |
| gap | 8 | 296 |
| Filter row 2 — `Who is on it`, full pane width | 44 | 340 |
| gap + 1px `--line` rule | 10 | 350 |
| **First list-pane row starts** | — | **350** |

Row tops are then 350 · 437 · 524 · 611 · 698 · 785 · 872, and the eighth is at
959 — **seven rows above the fold, with 28px of margin on the seventh.**

The tolerance, so the builder can check rather than guess: with an 87px pitch the
first row must start between **291px and 377px** for the count to be exactly 7. If
the measured count is not 7, adjust the pane-head top padding and the gaps above;
do not change the row.

Three selects stacked one per line cost 132px and pushed the queue down; two rows
of filters cost 96px and read just as plainly, because each select still carries its
own visible label above it.

The record pane is the request preview, built only from the text the Content
contract provides for `REQ-2048`.

### 2.4 `requests.html` — phone 400

```
LIST PANE (default)                     RECORD PANE (after tapping a row)
┌──────────────────────────────────┐   ┌──────────────────────────────────┐
│ ▣  Requests             Menu ↓   │   │ ▣  Requests             Menu ↓   │
│ [🔍 Reference, words, or a …    ]│   │ ← Back to the list               │  56px
│ [ + Raise a request           ]  │   ├──────────────────────────────────┤
├──────────────────────────────────┤   │ REQ-2048                         │
│ Requests                         │   │ Projector in Lab 2 shows a blue  │
│ Everything staff have asked us   │   │ screen                           │
│ to fix. Open the ones marked     │   │ ⚑ Urgent   ↻ In progress         │
│ urgent first.                    │   │ Raised by    Suresh Kumara       │
│ ▸ Filter and sort                │   │ About which  IT-0087 Epson       │
│ Showing 8 of 8 requests          │   │ device       EB-X51 projector    │
│ ────────────────────────────────  │   │ Where        Science Block Lab 2 │
│ REQ-2048          ⚑ Urgent       │   │ Who is on it Nimali Perera       │
│ Projector in Lab 2 shows a blue  │   │ Raised       Fri 11 Sep 2026,    │
│ screen                           │   │              8:15 am             │
│ ↻ In progress · Fri 11 Sep 2026  │   │ What they told us                │
│ ────────────────────────────────  │   │ "The projector switches on,     │
│ REQ-2047          ⚑ Normal       │   │  then the screen goes blue after │
│ …                                │   │  about a minute. …"              │
│ … six more …                     │   │ [ Open the device record ]       │
│ ‹ Previous   1   Next ›          │   │ ← Back to the list               │
│ #menu block                      │   │ #menu block                      │
└──────────────────────────────────┘   └──────────────────────────────────┘
```

### 2.5 `device.html` — desktop / phone

```
DESKTOP                                                   PHONE
│ Devices › IT-0142                                       ┌──────────────────────┐
├────────── 480px ──────┬────────────────────────────────┐│ ▣ Devices    Menu ↓  │
│ IT-0142               │ Where this device is           ││ [🔍 …              ] │
│ Dell Latitude 3540    │ ┌────────────────────────────┐ ││ [+ Raise a request ] │
│ laptop                │ │ Who has it   Dilani Fernando│ │├──────────────────────┤
│ ✋ Issued  ✔ Good      │ │ Where        Grade 6B       │ ││ IT-0142 — Dell       │
│ ──────────────────────│ │              Classroom      │ ││ Latitude 3540 laptop │
│ On this record        │ │ Given out    Tue 25 Aug 2026│ ││ Laptop · Issued to   │
│▌Where this device is  │ │ Due back     Mon 21 Sep 2026│ ││ Dilani Fernando ·    │
│ What it cost and how  │ │ Last checked Thu 3 Sep 2026 │ ││ Grade 6B Classroom   │
│ long it is covered    │ └────────────────────────────┘ ││ ✋ Issued  ✔ Good     │
│ Requests about this   │ What it cost and how long it is││ [+ Raise a request   │
│ device            (2) │ covered                        ││   about this device ]│
│ What has happened to  │ ┌────────────────────────────┐ ││ [ Mark it returned ] │
│ it                (5) │ │ Value     Rs 285,000        │ ││ ▸ On this record     │
│ ──────────────────────│ │ Bought    14 Feb 2024       │ ││ Where this device is │
│ [ + Raise a request   │ │ Warranty  13 Feb 2027       │ ││ …5 rows…             │
│   about this device ] │ │ Serial    5CG4113XYZ        │ ││ What it cost and how │
│ [ Mark it returned ]  │ └────────────────────────────┘ ││ long it is covered   │
│                       │ Requests about this device     ││ …4 rows…             │
│                       │  REQ-2047 ★ New …              ││ Requests about this  │
│                       │  REQ-1902 ⛁ Closed …           ││ device  …2 rows…     │
│                       │ What has happened to it        ││ What has happened to │
│                       │  ● Thu 10 Sep 2026, 11:20 am   ││ it  …5 entries…      │
│                       │  │ Dilani Fernando             ││ #menu block          │
│                       │  │ Raised REQ-2047 — will not  │└──────────────────────┘
│                       │  │ connect to the staff Wi-Fi  │
│                       │  ● … four more, newest first   │
└───────────────────────┴────────────────────────────────┘
```

The list pane here is the record's own section index with counts — the same pane
component, a different list. Selecting a section scrolls the record pane and marks
the item; with JavaScript off the items are `#anchor` links and the browser does it.

### 2.6 `request-form.html` — desktop / phone

```
│ Raise a request                                                                 │
├────────── 480px ──────┬─────────────────────────────────────────────────────────┤
│ What you are filling  │ ┌─ 640px ───────────────────────────────────────────┐   │
│ in                    │ │ ⚠ We couldn't send this yet — 2 things need your  │   │
│▌About the problem  1–4│ │   attention                                       │   │
│ How soon you need   5 │ │   • What is wrong?                                │   │
│ it                    │ │   • Where is it?                                  │   │
│ Anything to show us 6 │ └───────────────────────────────────────────────────┘   │
│ Who is asking       7 │ About the problem                                       │
│ ──────────────────────│ What is it about?                                       │
│ Your name             │ Pick the device, or choose "Not about a particular      │
│ Nimali Perera         │ device".                                                │
│ (nimali.p)            │ [ IT-0142 — Dell Latitude 3540 laptop              ⌄ ]  │  48px
│ ──────────────────────│ What is wrong?                                          │
│ [ Send the request ]  │ One short line, for example "Projector will not turn on".│
│ [ Cancel ]            │ [                                                     ]  │  2px danger
│                       │ ⚠ Type a short description of the problem, for example  │
│  (the two buttons are │   "Projector will not turn on".                         │
│   repeated at the foot│ Tell us more                                            │
│   of the form pane    │ …                                                       │
│   as well)            │ How soon you need it                                    │
│                       │ ( ) Can wait   It can wait until next week.              │
│                       │ (•) Normal     I need it in the next day or two.         │
│                       │ ( ) Urgent     A class or the office is stopped right now│
│                       │ Anything to show us   /   Who is asking                  │
│                       │ [ Send the request ]   [ Cancel ]                        │
└───────────────────────┴─────────────────────────────────────────────────────────┘
```

On phone the two panes stack: the section list becomes a `<details>` titled
`What you are filling in`, closed by default, and the form follows in one column
with 56px controls; `Send the request` and `Cancel` appear once, at the foot.

### 2.7 `login.html` and `ui-kit.html`

- **`login.html`** — the only place the dark chrome fills a whole screen: a 50/50
  split. The left half is `--chrome` carrying the crest at 104px, `Polymath
  College` in Sora 30px, `Vivere Disce ~ Learn to Live` in Work Sans 17px
  `--chrome-muted`, and a faint 1px grid at 32px. The right half is `--surface`
  with `Welcome back`, the sub-line, the two fields at 52px, and `Sign in` as a
  full-width 56px `--brand` button. Below 760px the dark half becomes a 180px band
  across the top and the form fills the rest; the crest drops to 64px.
- **`ui-kit.html`** — the list pane holds the component families as an index, the
  record pane shows the specimens, so the kit demonstrates the direction's own
  navigation. Every specimen appears twice where it matters: once on `--surface`
  and once on `--chrome`, because this is the direction with two surface families.
  The focus ring is shown on both. The colour table gives swatch, token, hex,
  checked-against pair and ratio.

---

## 3. Type

Google Fonts: `Sora` (600, 700) · `Work Sans` (400, 500, 600) ·
`JetBrains Mono` (500).

| Role | Family / weight | Size / line-height | Notes |
|---|---|---|---|
| Wordmark `Polymath College` | Sora 700 | 15/20 in the bar, 30/36 on login | |
| h1 | Sora 700 | 30/38 desktop, 26/32 phone, `-0.015em` | |
| h2 | Sora 600 | 21/28 | |
| h3 | Sora 600 | 17/24 | |
| Body / prose | Work Sans 400 | 16/26 | |
| Lead paragraph | Work Sans 400 | 18/28 | |
| List-pane row title | Work Sans 500 | 16/24 | |
| Form label | Work Sans 600 | 16/22 | |
| Help text | Work Sans 400 | 15/22 | |
| Button | Sora 600 | 16/20 | |
| Command-bar link | Work Sans 500 | 15/20 | |
| Badge / chip word | Work Sans 600 | 14/18 | |
| Reference, tag, date, money, serial | JetBrains Mono 500 | 15/20, tabular numerals | `REQ-2048`, `IT-0142`, `Rs 285,000`, `5CG4113XYZ` |
| Figure number | JetBrains Mono 500 | 28/32 | |
| Quoted text from a request | Work Sans 400 italic | 17/28 | The only italic in the system |

Measure: 72 characters in the record pane (720px at 16px), 640px for the form, and
the 480px list pane runs at 16px with its title on a single line.

---

## 4. Palette

Derivation. `#722A82` is `hsl(289, 51%, 34%)`. Workbench builds **two** families
from it. The chrome is the crest hue driven down in lightness —
`hsl(289, 38%, 15%)` for the bar and `hsl(289, 30%, 22%)` for its inset surfaces —
so the dark furniture is literally the crest colour in shadow, not a generic black.
The content canvas goes the other way: neutrals at 220°, a cool grey with no purple
in it, so the white record pane reads as paper against the plum. The one bright
purple, `--brand-bright` at L 74%, exists only for the current-page marker and
icons **on** the chrome, where `--brand` itself would be too dark to see.

| Token | Hex | Derivation |
|---|---|---|
| `--brand` | `#722A82` | The crest, unmodified |
| `--brand-strong` | `#55205F` | Crest hue at L 25% |
| `--brand-bright` | `#D79BE6` | Crest hue at L 74% — only on `--chrome` |
| `--brand-tint` | `#F3EAF5` | Crest hue at L 95% |
| `--chrome` | `#241428` | Crest hue at S 38% L 15% — command bar, login panel |
| `--chrome-2` | `#37203D` | Crest hue at S 30% L 22% — the search field inside the bar |
| `--chrome-line` | `#4A3350` | Crest hue at L 26% — dividers on the chrome |
| `--chrome-ink` | `#F4EEF6` | Crest hue at L 95% — text on the chrome |
| `--chrome-muted` | `#B9A8BE` | Crest hue at S 16% L 70% — secondary text on the chrome |
| `--ink` | `#151A24` | Cool 222° at L 11% |
| `--muted` | `#565E6E` | Cool 222° at L 38% |
| `--line` | `#D9DEE7` | Cool 222° at L 88% — hairlines |
| `--line-strong` | `#848C9C` | Cool 222° at L 56% — control borders |
| `--canvas` | `#F4F6F9` | Cool 220° at L 97% — the record pane ground |
| `--surface` | `#FFFFFF` | Cards and the list pane |
| `--surface-2` | `#E9EDF3` | Cool 220° at L 94% — hover and selected fills |
| `--ok` | `#0D6154` | Fixed, Good, In store |
| `--ok-tint` | `#E2F1EE` | |
| `--warn` | `#7E5A05` | Waiting on someone, In repair, Needs repair |
| `--warn-tint` | `#F8EFD9` | |
| `--danger` | `#AB1F45` | Urgent, Out of service, errors |
| `--danger-tint` | `#FBE6EB` | |
| `--info` | `#0A5A7A` | New |
| `--info-tint` | `#E2EFF5` | |
| `--focus` | `#722A82` | On light surfaces |
| `--focus-on-chrome` | `#D79BE6` | `--brand-bright`, for focus inside the bar |

**Contrast pairs** (expected values; recompute and print them in the folder README):

| Pair | Ratio | Needs |
|---|---|---|
| `--ink` on `--surface` | 17.4:1 | 4.5 |
| `--ink` on `--canvas` | 16.1:1 | 4.5 |
| `--muted` on `--surface` | 6.5:1 | 4.5 |
| `--chrome-ink` on `--chrome` | 15.3:1 | 4.5 |
| `--chrome-muted` on `--chrome` | 7.8:1 | 4.5 |
| `--brand-bright` on `--chrome` (current item, icons) | 8.0:1 | 4.5 |
| `--surface` on `--brand` (primary button) | 8.9:1 | 4.5 |
| `--brand` on `--surface` | 8.9:1 | 4.5 |
| `--line-strong` on `--surface` (field border) | 3.4:1 | 3.0 |
| `--ok` / `--warn` / `--danger` / `--info` on `--surface` | ≥6:1 each | 4.5 |
| Each functional colour on its own tint | ≥5:1 | 4.5 |
| `--focus` on `--canvas` | 8.1:1 | 3.0 |
| `--focus-on-chrome` on `--chrome` | 8.0:1 | 3.0 |

`--line` (1.4:1) and `--chrome-line` (1.6:1) are decorative dividers only. The
`Raise a request` button inside the dark bar keeps `--brand` fill with white text
(8.9:1 internally) and a 1px `--brand-bright` border so its edge is visible against
`--chrome` at 3.9:1.

**This is not a dark theme.** Only the command bar, the phone bar and the login
panel are dark; every content surface is light, and there is no theme toggle.

---

## 5. Space, radius, depth

- **Space, 4px base with a tight middle:** `--s1 4` `--s2 8` `--s3 12` `--s4 16`
  `--s5 20` `--s6 32` `--s7 40`. The extra 20px step is what lets the two panes stay
  compact without feeling cramped. Card padding `--s5`; pane padding `--s4`;
  section gap `--s6`.
- **Radius:** `--r-sm 6px` (fields, chips, rows), `--r-md 10px` (cards, buttons),
  `--r-lg 10px` (modal). Two curves only.
- **Depth:** the panes are separated by 1px `--line`, not shadow.
  `--shadow-raise: 0 1px 2px rgba(21,26,36,.06)` on record-pane cards only;
  `--shadow-pop: 0 12px 32px rgba(21,26,36,.20)` for the modal and the toast. The
  command bar has no shadow — its own darkness is the separation.
- **Grid:** the shell is `grid-template-columns: 480px 1fr` at ≥1080px and one
  column below. Inside the record pane, a 720px measure with 32px gutters.

---

## 6. Components

| Component | Treatment |
|---|---|
| Primary button | `--brand` fill, white label, `--r-md`, 48px tall (56px on phone), padding `12px 22px`. Hover L −6%; active L −12%. Inside the chrome it also carries a 1px `--brand-bright` border. |
| Secondary button | `--surface` fill, 1px `--line-strong` border, `--ink` label, same metrics. On the chrome: transparent fill, 1px `--chrome-muted` border, `--chrome-ink` label. |
| Quiet button | No border, `--brand` label (or `--brand-bright` on the chrome), underline on hover, 48px hit area. |
| Destructive button | `--danger` fill, white label, 40px away from the primary. |
| Icon-only button | 48×48, `aria-label` required; only the search clear and the toast/modal close. |
| Busy button | `Sending…` + 18px spinner, `aria-busy="true"`, width locked. |
| Search field (chrome) | 44px, `--chrome-2` fill, 1px `--chrome-line` border, `--r-sm`, `--chrome-ink` text, `--chrome-muted` placeholder. Focus: 3px `--focus-on-chrome` ring with a 2px `--chrome` offset. |
| Field (content) | 48px, `--surface`, 1px `--line-strong`, `--r-sm`, 16px text. Focus: 3px `--focus` ring, 2px offset. Error: 2px `--danger` border plus the message. |
| Label / help | Label 16px semibold above; help 15px `--muted` between label and field, `aria-describedby`. |
| List-pane row | A fixed 87px on desktop (10px padding, a 24px reference-and-urgency band, a 24px title line that never wraps in the 480px pane, a 24px status band, 10px padding, 1px rule) and 112px on phone, where the title is allowed two lines. 1px `--line` between rows, no card. Selected: 4px `--brand` left edge, `--brand-tint` fill, `aria-current="true"`. Hover: `--surface-2`. |
| Record-pane card | `--surface`, `--r-md`, `--shadow-raise`, 20px padding, on the `--canvas` ground. |
| Fact list | `<dl>` with the term 15px `--muted` in a 150px column and the value 16px `--ink`; values that are references or money set in JetBrains Mono. |
| Status badge | 26px, `--r-sm`, tint fill, 1px hue border, 18px icon + 14px word. |
| Urgency chip | Same shell, transparent fill, 1px `--line-strong`. |
| Timeline item | 10px `--brand` filled circle on a 1px `--line` rail; date in JetBrains Mono, who in Work Sans 500, what in Work Sans 400. |
| Alert | `--r-md` card, tint fill, 1px hue border, 3px left edge in the hue, 20px icon, Sora 17px title, 16px body. |
| Toast | Bottom-right above the record pane on desktop, bottom-centre on phone. `--chrome` fill, `--chrome-ink` text, `--r-md`, `--shadow-pop`, `Undo` and `Close`. `role="status"`, 8s, pauses on hover/focus. |
| Modal | 500px, `--surface`, `--r-lg`, `--shadow-pop`; `role="dialog" aria-modal="true"`. |
| Empty state | Inside the list pane: 48px icon in `--line-strong`, `<h2>`, one sentence, one 48px button, 40px of air. The record pane then shows its own line, `Choose a request from the list to see it here.` |
| Pagination | Fixed at the foot of the list pane, 48px targets. |
| Avatar | 36px circle, `--chrome-2` fill, `--chrome-ink` initials `NP` in Sora; on light surfaces, `--brand-tint` fill with `--brand-strong` initials. |
| Icons | **Solar Broken**, inline SVG, `currentColor`. 20px in the bar and rows, 18px in badges, 24px in alerts, 48px in empty states. |

**Status vocabulary — identical in every direction:** `New` star ·
`In progress` refresh-circle · `Waiting on someone` clock-circle ·
`Fixed` check-circle · `Closed` archive · `In store` box · `Issued` hand-holding ·
`In repair` wrench · `Out of service` close-circle · `Good` check-circle ·
`Needs repair` danger-triangle · `Can wait` hourglass · `Normal` flag ·
`Urgent` fire (the crest's torch flame). Icon **and** word, always, on both the
light and the dark surface.

---

## 7. Charts

**None.** The second pane is where a chart's screen space goes. The seven figures
are read as sentences in the list pane.

---

## 8. Density intent

Workbench is **medium–high**: dense in the list pane, comfortable in the record
pane. At 1440×900 the chrome above the first queue row is **350px** (65px command
bar + 41px context strip + 138px pane head + 96px two filter rows + 10px rule and
gap); list-pane rows are a fixed **87px**, so **7 request rows start above 900px**.
The band-by-band budget and the row anatomy are in §2.3; build to them, measure, and
state the measured number in the folder `README.md`.

A first attempt at this page put the list pane at 400px and stacked three filter
selects, which wrapped two of the first seven titles onto a second line and cost
132px of chrome — six rows, tying Signpost. The pane is now 480px so no contract
title wraps, and the filters take two rows instead of three. That keeps the ladder
**b 3 < c 5 < d 6 < e 7 < a 8** and, more to the point, it is what the direction
was claiming all along: a queue you can work down without losing your place needs
to show more of the queue than the direction built for big, unmissable controls.

---

## 9. States

| State | What the user sees |
|---|---|
| Default | As drawn: the list pane with a row selected, the record pane showing it. |
| Loading | Two async-feeling moments, both enhancement-only. Filtering: the context strip's count becomes `Finding requests…` with an 18px spinner in an `aria-live="polite"` region. Swapping panes: the record pane shows three 16px `--surface-2` placeholder bars for at most 200ms; with JavaScript off there is a normal page load instead. |
| Empty (`requests.html?demo=empty`) | The list pane shows `No requests match what you chose` / `Try clearing the filters, or search for a different word.` / `[ Clear the filters ]`; the record pane shows `Choose a request from the list to see it here.` in `--muted`. Search text and filters keep the user's choices. |
| Validation errors (`request-form.html?demo=errors`) | The danger alert at the top of the form pane lists the two fields as links; the section list marks `About the problem` with a `⚠` and the count `2`. Each field keeps its value, gets `aria-invalid="true"`, a 2px `--danger` border and its message. Focus moves to the alert. |
| Server error | Danger alert above the form: `We couldn't save that just now` / `Nothing you typed has been lost. Wait a moment and press "Send the request" again.` |
| Success | Toast `Request sent. We gave it the number REQ-2049.` with `Undo`, and the same sentence as a success alert at the top of the record pane on the page landed on. |
| Sign-in error (`login.html?demo=error`) | Danger alert on the light half, above the fields: `We couldn't sign you in` / `That username or password didn't match. Try again, or ask the office to reset it.` `nimali.p` stays; focus goes to the password field. |
| No permission (`device.html?demo=denied`) | The record pane shows the panel: 48px lock icon, `You can't open this page`, `This page is for ICT staff. Ask Nimali Perera in the ICT Room, or raise a request and we will help.`, `[ + Raise a request ]`. The list pane and the command bar stay, so nothing is lost. |

---

## 10. Copy — use these words exactly

The wording is identical in all five directions. In full, so this file stands alone:

**Global** — wordmark `Polymath College`; sub-line `Technology Management Desk`;
navigation `Home` · `Requests` · `Devices` · `Raise a request`; utility
`Nimali Perera`, `ICT Technician`, `Design kit`, `Sign out`; skip link
`Skip to main content`. Direction-specific chrome words: `Menu` (the anchor to
`#menu`), `Press / to search`, `← Back to the list`, `On this record`,
`What you are filling in`, `Choose a request from the list to see it here.`,
`What they told us`.

**`login.html`** — `Welcome back` / `Sign in to the Technology Management Desk.` /
`Username` + `The name the school gave you, like nimali.p` / `Password` +
`Passwords are case sensitive.` / `Sign in` / `We couldn't sign you in` +
`That username or password didn't match. Try again, or ask the office to reset it.` /
`Polymath College · Technology Management Desk`. The dark half also carries
`Vivere Disce ~ Learn to Live`, the motto as it is written on the crest artwork.

**`dashboard.html`** — `<h1>` `Home`; lead
`Friday 11 September 2026. Here is what needs doing today.`; `<h2>`s
`What needs doing`, `Things you can do`, `Requests to work on`,
`Devices to watch`; figures worded `6 requests open` · `2 are urgent` ·
`1 raised today` · `3 devices due back next week` · `2 devices in repair` ·
`128 devices in the register` · `34 out on loan`; links `See all requests`,
`Open the device record`, `Go to the requests queue`.

**`requests.html`** — `<h1>` `Requests`; lead
`Everything staff have asked us to fix. Open the ones marked urgent first.`;
`Search requests` + `Reference, words, or a person's name, e.g. projector or REQ-2048`;
filters `Status` (`All statuses` + the five) · `How urgent` (`All`, `Can wait`,
`Normal`, `Urgent`) · `Who is on it` (`Anyone`, `Nobody yet`, `Nimali Perera`,
`Ruwan Jayasuriya`); sort `Newest first`, `Most urgent first`, `Oldest first`;
`Showing 8 of 8 requests`; field names `Reference`, `What is wrong`, `Raised by`,
`Status`, `How urgent`, `Who is on it`, `Raised`; empty
`No requests match what you chose` /
`Try clearing the filters, or search for a different word.` / `Clear the filters`.
The record pane's fact labels are `Raised by`, `About which device`, `Where`,
`Who is on it`, `Raised`.

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

**Strings the Content contract settles, and that are easy to get wrong**

| Where | Text |
|---|---|
| First option of `What is it about?` | `Choose a device` |
| First option of `Where is it?` | `Choose a room` |
| `REQ-1902` in `Requests about this device` | `Battery replaced under warranty` |
| `REQ-2047` in the same list | `Laptop will not connect to the staff Wi-Fi` |
| A request nobody has picked up | `Nobody yet` |
| Result line in the empty state | `Showing 0 of 8 requests` |
| The devices figure | `3 devices due back next week` — the week after the one we are in, never the current one |

**Dates and weekdays.** Today is **Friday 11 September 2026** everywhere. Copy each
date and its weekday from the contract together, and never write a weekday that
does not match its date: REQ-2048 raised `Fri 11 Sep 2026, 8:15 am`; REQ-2047
`Thu 10 Sep 2026, 11:20 am`; REQ-2045 `Tue 8 Sep 2026, 7:35 am`; IT-0142 given out
`Tue 25 Aug 2026`, returned to the ICT Store `Fri 21 Aug 2026, 3:05 pm`, battery
replaced `Fri 12 Jun 2026, 9:30 am`, last checked `Thu 3 Sep 2026`; the history
entry for REQ-2047 is dated `Thu 10 Sep 2026, 11:20 am`.

**Sample rows** come verbatim from the Content contract in
`docs/tasks/002-design-directions.md`, including the `REQ-2048` quotation.

---

## 11. Accessibility

- **Landmarks:** `<header>` (command bar) containing `<nav aria-label="Main">` and
  the search `<form role="search">`; `<main id="main">` wrapping both panes, with
  the list pane as `<nav aria-label="Requests">` on `requests.html` and a `<section>`
  elsewhere; `<nav aria-label="Menu" id="menu">` at the end of the document on
  phone; `<footer>`.
- **Headings:** one `<h1>` per page. On two-pane pages the `<h1>` lives at the top
  of the **list** pane (it names the page — `Requests`), and each record-pane
  section is an `<h2>`. The list pane's own section titles are `<h2>` too, so the
  outline reads `Requests` → `Filter and sort` → `The queue` → the record sections.
  No level is skipped.
- **Skip links:** `Skip to main content` first; a second, `Skip to the record`,
  appears at ≥1080px and jumps past the list pane — the one place in the five
  directions where a person would otherwise Tab through 8 rows to reach the content.
- **Search:** `<form role="search">` with a real `<label for="q">Search requests</label>`
  (visually hidden at ≥1080px) and the `Press / to search` hint in an element
  referenced by `aria-describedby`. The `/` shortcut does nothing when focus is
  already in a text field.
- **Form wiring:** `<label for>`; help `<p id="…-help">` then error
  `<p id="…-error">` in `aria-describedby`; `aria-invalid="true"` on failed fields;
  `<fieldset>` + `<legend>How urgent is it?</legend>`; error summary
  `role="alert" tabindex="-1"`, focused on load, links moving focus to the field.
- **Pane swapping:** when `app.js` swaps the record pane without a page load, it
  moves focus to the record pane's `<h2>` and announces the change in a polite live
  region. With JavaScript off it is an ordinary page load and the browser handles
  focus. On phone, `← Back to the list` returns focus to the row that was opened.
- **Focus ring:** 3px `--focus` with a 2px `--surface` offset on light surfaces; 3px
  `--focus-on-chrome` with a 2px `--chrome` offset inside the bar. Both are in the
  ui-kit, shown on their own surface.
- **Dialogs and redirects:** the modal traps focus, Escape closes, focus returns to
  `Mark it returned`; after a redirect focus goes to the `<h1>`.
- **Touch targets:** phone rows 112px; bar controls 48px; the `Menu` anchor 48×48;
  fields 48–56px; `← Back to the list` 56px full width. Adjacent targets are at
  least 8px apart, and `Cancel` is 24px from `Send the request`.
- **Colour is never alone:** icon + word for every status, condition and urgency, on
  both the dark and the light surface; the selected list row is marked by a 4px edge
  and `aria-current`, not only by its tint.

---

## 12. Motion

Quick, and only where a pane changes.

- Pane swap: the record pane cross-fades in 140ms `ease-out`. Nothing slides —
  a slide would imply a direction the layout does not have.
- Hover and focus: 120ms colour transitions.
- Toast: fade + 10px rise, 200ms; out 140ms.
- Modal: backdrop fade 140ms, panel fade 160ms.
- The `/` shortcut focuses the search box with no animation at all.
- Reduced motion: the standard block sets every duration to `.01ms`,
  `animation-iteration-count: 1` and `scroll-behavior: auto`; the pane swap then
  happens instantly and the live-region announcement still fires.

---

## 13. Progressive enhancement

**Plain HTML, full page load:** the command-bar search (`<form method="get"
action="requests.html">`), the four navigation links, the phone `Menu` anchor and
its end-of-document block, the pane stack as ordinary links between pages and
anchors, the filter/sort form with its own `Apply` button, the request form,
sign-out, pagination, and the modal as a `<dialog>` with a link-to-section
fallback. Every list row is a link with a real `href`.

**`app.js` adds:** the `/` shortcut, in-place filtering with the live count,
swapping the record pane without a reload (with focus moved and announced), hiding
`Apply` once scripting exists, toast rendering, `?demo=` switching, focusing the
error summary, and the modal focus trap. Hooks are `data-*` attributes only.

---

## 14. Demo hooks

`login.html?demo=error` · `request-form.html?demo=errors` ·
`requests.html?demo=empty` · `?demo=toast` on any app page ·
`device.html?demo=denied`. Prototype-only; never carried into application templates.

---

## 15. Skills the builder should load

`split-layout-technical` (its two-panel discipline, inset rules and metadata
rails — but each pane here has a working job, not an atmospheric one) ·
`nested-container-clean-agency` · `interaction-design:navigation-patterns` ·
`interaction-design:search-ux` · `inclusive-interaction:keyboard-navigation` ·
`interaction-design:state-machine` (the request and device lifecycles shown on the
record pane) · `ui-design:dark-mode-design` (for the chrome only — the content
stays light) · `cognitive-accessibility:plain-language-design` ·
`solar-duotone-bold` (use the **Broken** weight of the same family).
