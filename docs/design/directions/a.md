`design/a-ledger/`

# Direction A — Ledger

**Concept.** Ledger is the ICT technician's day on one screen: a quiet slate-paper
console where every request, count and due date is a line in a book you can read
without scrolling. It earns its density from restraint — hairlines instead of
boxes, one chroma (the crest purple) instead of a palette, and numbers set in a
mono face so columns line up like a register.

**Who it suits.** Nimali is the only technician on site. Her problem is not
learning the software, it is holding eight open jobs in her head while a teacher
stands at the ICT Room door. Ledger answers that by never hiding anything: the
sidebar shows how many requests are waiting before she clicks, the whole queue of
eight fits above the fold, and every status is a word plus an icon so she can scan
a column rather than read it. Nothing is behind a menu, a hover or a tab — for a
non-technical colleague borrowing her screen, everything that exists is on the
page with a label on it.

---

## 1. Navigation model

**Desktop (≥1024px): persistent left sidebar with grouped sections and live counts.**

- 248px fixed sidebar, full height, sticky, its own scroll. Slate `--surface-2`
  panel against the white content column, separated by a 1px `--line` rule (no
  shadow).
- Top of the sidebar: crest chip 32px + wordmark `Polymath College` over the
  small line `Technology Management Desk`.
- Group 1 label `Work` → `Home`, `Requests` (count pill `6`), `Devices`.
- Group 2 label `Start` → `Raise a request` (the one filled purple button in the
  sidebar, full width, 48px tall).
- Bottom of the sidebar: `NP Nimali Perera / ICT Technician`, then `Design kit`
  and a `Sign out` button in a POST form.
- The current item is marked three ways: `aria-current="page"`, a 3px purple bar
  on its left edge, and a purple bold label. Never colour alone.
- Group labels are real `<h2 class="nav-group-title">` inside `<nav aria-label="Main">`.

**Phone (<1024px): fixed bottom tab bar, icon + word.**

- Four tabs, 25% each, 56px tall plus the safe-area inset: `Home`, `Requests`
  (count badge), `Devices`, `Raise a request`. Icons 22px above a 13px word.
- A 52px top bar keeps the crest chip, the page name and a `Menu` link that is a
  plain anchor to `#utility`, a section at the end of the document holding the
  person, `Design kit` and `Sign out`. No JavaScript is involved.
- `Raise a request` is the rightmost tab, under the right thumb, and is the only
  tab with a filled purple background.

**With JavaScript off.** Everything above is CSS and anchors: the sidebar, the tab
bar, the counts and the current-page marking are all server-rendered in the
prototype's static HTML. No navigation depends on a script.

---

## 2. Wireframes

### 2.1 `dashboard.html` — desktop 1440

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [skip to main content]                                                                 │
├──────────────┬─────────────────────────────────────────────────────────────────────────┤
│ ▣ Polymath   │  Home                                                    Fri 11 Sep 2026│
│   College    │  Friday 11 September 2026. Here is what needs doing today.              │
│   Technology │ ───────────────────────────────────────────────────────────────────────│
│   Mgmt Desk  │  What needs doing                                                       │
│              │  ┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬────────┐ │
│ WORK         │  │  6      │  2      │  1      │  3      │  2      │  128    │  34    │ │
│ ▌● Home      │  │requests │are      │raised   │devices  │devices  │devices  │out on  │ │
│   ◇ Requests │  │open     │urgent   │today    │due back │in repair│in the   │loan    │ │
│        ( 6 ) │  │         │         │         │next week│         │register │        │ │
│   ▤ Devices  │  └─────────┴─────────┴─────────┴─────────┴─────────┴─────────┴────────┘ │
│              │ ───────────────────────────────────────────────────────────────────────│
│ START        │  Requests to work on                              See all requests →    │
│ ┌──────────┐ │  ┌─────────┬───────────────────────────────┬────────────┬─────────────┐ │
│ │+ Raise a │ │  │REQ-2048 │Projector in Lab 2 shows a…    │⚑ Urgent    │↻ In progress│ │
│ │  request │ │  │REQ-2047 │Laptop will not connect to…    │⚑ Normal    │★ New        │ │
│ └──────────┘ │  │REQ-2046 │Printer jams on every second…  │⚑ Normal    │◷ Waiting on…│ │
│              │  │REQ-2045 │Tablet needed for the Grade 5… │⚑ Can wait  │★ New        │ │
│              │  └─────────┴───────────────────────────────┴────────────┴─────────────┘ │
│              │ ───────────────────────────────────────────────────────────────────────│
│              │  Devices to watch          │  Requests raised in the last five school   │
│              │  ┌───────────────────────┐ │  days                                      │
│              │  │IT-0087 Epson EB-X51   │ │   2│     ▇                                 │
│              │  │  🔧 In repair         │ │   1│  ▇  ▇      ▇  ▇                       │
│              │  │IT-0056 HP LaserJet    │ │   0│        ·                              │
│              │  │  🔧 In repair         │ │    └──Mon─Tue─Wed─Thu─Fri──                │
│              │  │IT-0142 Dell Latitude  │ │            └ 0 (empty bar, labelled)       │
│              │  │  ✋ Due Mon 21 Sep     │ │                                            │
│              │  │  Open the device      │ │   Mon 1 · Tue 2 · Wed 0 · Thu 1 · Fri 1    │
│              │  │  record →             │ │                                            │
│              │  └───────────────────────┘ │                                            │
│ ─────────────│ ───────────────────────────────────────────────────────────────────────│
│ NP Nimali    │  Things you can do                                                      │
│    Perera    │  [ + Raise a request ]  [ Go to the requests queue ]  [ Open the device │
│    ICT Tech. │                                                         record ]        │
│ Design kit   │                                                                         │
│ [ Sign out ] │                                                                         │
└──────────────┴─────────────────────────────────────────────────────────────────────────┘
```

Content column: max 1120px, gutters 32px. The seven figures are one row of seven
tiles at 1440, wrapping to 4+3 below 1280.

### 2.2 `dashboard.html` — phone 400

```
┌──────────────────────────────────────┐
│ [skip to main content]               │
│ ▣  Home                        Menu ⌄│  52px top bar, "Menu" = anchor to #utility
├──────────────────────────────────────┤
│ Home                                 │  h1 26px
│ Friday 11 September 2026. Here is    │
│ what needs doing today.              │
│ ──────────────────────────────────── │
│ What needs doing                     │  h2
│ ┌────────────────┬─────────────────┐ │
│ │ 6              │ 2               │ │  2-up tiles, 88px tall
│ │ requests open  │ are urgent      │ │
│ ├────────────────┼─────────────────┤ │
│ │ 1              │ 3               │ │
│ │ raised today   │ devices due     │ │
│ │                │ back next week  │ │
│ ├────────────────┼─────────────────┤ │
│ │ 2              │ 128             │ │
│ │ devices in     │ devices in the  │ │
│ │ repair         │ register        │ │
│ ├────────────────┴─────────────────┤ │
│ │ 34  out on loan                  │ │
│ └──────────────────────────────────┘ │
│ ──────────────────────────────────── │
│ Requests to work on                  │
│ ┌──────────────────────────────────┐ │
│ │ REQ-2048        ⚑ Urgent         │ │  stacked rows, 96px
│ │ Projector in Lab 2 shows a blue  │ │
│ │ screen                           │ │
│ │ ↻ In progress · Nimali Perera    │ │
│ ├──────────────────────────────────┤ │
│ │ REQ-2047        ⚑ Normal         │ │
│ │ Laptop will not connect to the   │ │
│ │ staff Wi-Fi                      │ │
│ │ ★ New · Nobody yet               │ │
│ └──────────────────────────────────┘ │
│ See all requests →                   │
│ ──────────────────────────────────── │
│ Devices to watch                     │
│ … (three rows, same anatomy)         │
│ ──────────────────────────────────── │
│ Requests raised in the last five     │
│ school days   (bars + the same       │
│ Mon 1 · Tue 2 · Wed 0 · Thu 1 · Fri 1│
│ line underneath)                     │
│ ──────────────────────────────────── │
│ Things you can do                    │
│ [ + Raise a request            ]     │  full width, 52px
│ [ Go to the requests queue     ]     │
│ [ Open the device record       ]     │
│ ──────────────────────────────────── │
│ #utility  Nimali Perera / ICT Tech.  │
│ Design kit · [ Sign out ]            │
│                                      │
│         (96px spacer for the bar)    │
├──────┬──────┬──────┬────────────────┤
│  ⌂   │  ◇6  │  ▤   │      +         │  56px tab bar, fixed
│ Home │Reqs… │Devic…│ Raise a request│
└──────┴──────┴──────┴────────────────┘
```

Tab words are the full labels `Home`, `Requests`, `Devices`, `Raise a request`;
`Requests` wraps to one line at 13px, `Raise a request` takes the double-width
last cell.

### 2.3 `requests.html` — desktop 1440

```
┌──────────────┬─────────────────────────────────────────────────────────────────────────┐
│  (sidebar)   │ Requests                                                                │
│              │ Everything staff have asked us to fix. Open the ones marked urgent first.│
│              │ ┌─────────────────────────────────────────────────────────────────────┐ │
│              │ │ Search requests                                                     │ │
│              │ │ [🔍 Reference, words, or a person's name, e.g. projector or REQ-2048]│ │
│              │ │ Status [All statuses ⌄] How urgent [All ⌄] Who is on it [Anyone ⌄]  │ │
│              │ │ Sort [Newest first ⌄]                            [ Clear filters ]  │ │
│              │ └─────────────────────────────────────────────────────────────────────┘ │
│              │ Showing 8 of 8 requests                                                  │
│              │ ┌──────────┬──────────────────────────┬───────────┬────────┬──────────┬─│
│              │ │Reference │What is wrong             │Raised by  │Status  │How urgent│…│
│              │ ├──────────┼──────────────────────────┼───────────┼────────┼──────────┼─│
│              │ │REQ-2048  │Projector in Lab 2 shows  │Suresh     │↻ In    │⚑ Urgent  │…│  44px rows
│              │ │          │a blue screen             │Kumara     │progress│          │ │
│              │ │REQ-2047  │Laptop will not connect…  │Dilani F.  │★ New   │⚑ Normal  │…│
│              │ │REQ-2046  │Printer jams on every…    │Anoma Silva│◷ Wait… │⚑ Normal  │…│
│              │ │REQ-2045  │Tablet needed for the…    │Tharindu B.│★ New   │⚑ Can wait│…│
│              │ │REQ-2044  │Interactive panel pen is… │Dilani F.  │✔ Fixed │⚑ Normal  │…│
│              │ │REQ-2043  │No sound from the speakers│Ruwan J.   │⛁ Closed│⚑ Normal  │…│
│              │ │REQ-2042  │Cannot sign in to the…    │Suresh K.  │✔ Fixed │⚑ Urgent  │…│
│              │ │REQ-2041  │New toner cartridge…      │Anoma Silva│⛁ Closed│⚑ Can wait│…│
│              │ └──────────┴──────────────────────────┴───────────┴────────┴──────────┴─│
│              │  ‹ Previous   1                                             Next ›      │
└──────────────┴─────────────────────────────────────────────────────────────────────────┘
```

Columns at 1440: `Reference` 120 · `What is wrong` flexible · `Raised by` 160 ·
`Status` 150 · `How urgent` 130 · `Who is on it` 160 · `Raised` 190. The two
right-hand columns collapse below 1280 into a second line inside the row.

### 2.4 `requests.html` — phone 400

```
┌──────────────────────────────────────┐
│ ▣  Requests                    Menu ⌄│
├──────────────────────────────────────┤
│ Requests                             │
│ Everything staff have asked us to    │
│ fix. Open the ones marked urgent     │
│ first.                               │
│ Search requests                      │
│ [🔍 Reference, words, or a person's ]│  48px
│ ▸ Filter and sort                    │  <details>, closed by default
│ Showing 8 of 8 requests              │
│ ┌──────────────────────────────────┐ │
│ │ REQ-2048            ⚑ Urgent     │ │  card row, 104px
│ │ Projector in Lab 2 shows a blue  │ │
│ │ screen                           │ │
│ │ ↻ In progress                    │ │
│ │ Suresh Kumara · Fri 11 Sep 8:15am│ │
│ ├──────────────────────────────────┤ │
│ │ REQ-2047            ⚑ Normal     │ │
│ │ …                                │ │
│ └──────────────────────────────────┘ │
│  ‹ Previous    1    Next ›           │
│         (96px spacer)                │
├──────┬──────┬──────┬────────────────┤
│  ⌂   │  ◇6  │  ▤   │      +         │
└──────┴──────┴──────┴────────────────┘
```

The phone rows are `<li>` wrappers around the same data as the desktop table; the
table is `<table>` at ≥1024px and a definition-style card list below, built from
one markup source using `display:block` on `thead`/`td` at the breakpoint, with
the column name repeated in a visually hidden span in each cell.

### 2.5 `device.html` — desktop 1440 / phone 400

```
DESKTOP                                        PHONE
┌──────────┬──────────────────────────────┐   ┌──────────────────────┐
│ (sidebar)│ Devices ▸ IT-0142            │   │ ▣ Devices      Menu ⌄│
│          │ IT-0142 — Dell Latitude 3540 │   ├──────────────────────┤
│          │ laptop                       │   │ Devices ▸ IT-0142    │
│          │ Laptop · Issued to Dilani    │   │ IT-0142 — Dell       │
│          │ Fernando · Grade 6B Classroom│   │ Latitude 3540 laptop │
│          │ [✋ Issued] [✔ Good]          │   │ Laptop · Issued to   │
│          │ [ + Raise a request about    │   │ Dilani Fernando ·    │
│          │   this device ] [ Mark it    │   │ Grade 6B Classroom   │
│          │   returned ]                 │   │ [✋ Issued][✔ Good]   │
│          │ ─────────────┬───────────────│   │ [ + Raise a request  │
│          │ Where this   │ What it cost  │   │   about this device ]│
│          │ device is    │ and how long  │   │ [ Mark it returned ] │
│          │ Who has it   │ it is covered │   │ Where this device is │
│          │ Dilani F.    │ Value         │   │ …definition list…    │
│          │ Where        │ Rs 285,000    │   │ What it cost and how │
│          │ Grade 6B     │ Bought        │   │ long it is covered   │
│          │ Classroom    │ 14 Feb 2024   │   │ …definition list…    │
│          │ Given out    │ Warranty until│   │ Requests about this  │
│          │ Tue 25 Aug   │ 13 Feb 2027   │   │ device               │
│          │ Due back     │ Serial        │   │ …2 rows…             │
│          │ Mon 21 Sep   │ 5CG4113XYZ    │   │ What has happened    │
│          │ Last checked │               │   │ to it                │
│          │ Thu 3 Sep    │               │   │ …5 timeline items…   │
│          │ ─────────────┴───────────────│   │      (96px spacer)   │
│          │ Requests about this device   │   ├────┬────┬────┬──────┤
│          │ REQ-2047 ★ New   …           │   │ ⌂  │ ◇6 │ ▤  │  +   │
│          │ REQ-1902 ⛁ Closed …          │   └────┴────┴────┴──────┘
│          │ What has happened to it      │
│          │ │ Thu 10 Sep 2026, 11:20 am  │
│          │ ├ Dilani Fernando            │
│          │ │ Raised REQ-2047 — will not │
│          │ │ connect to the staff Wi-Fi │
│          │ ├ … four more, newest first  │
└──────────┴──────────────────────────────┘
```

The two fact panels are `<dl>`s side by side at desktop, stacked at phone. The
history is an `<ol>` with a 1px purple rail on the left and a 9px square node per
item — squares, not dots, to match the ledger geometry.

### 2.6 `request-form.html` — desktop 1440 / phone 400

```
DESKTOP                                        PHONE
┌──────────┬──────────────────────────────┐   ┌──────────────────────┐
│ (sidebar)│ Raise a request              │   │ ▣ Raise a req. Menu ⌄│
│          │ Tell us what is wrong. We    │   ├──────────────────────┤
│          │ will pick it up from the ICT │   │ Raise a request      │
│          │ Room.                        │   │ Tell us what is      │
│          │ ┌──────── 640px ───────────┐ │   │ wrong. We will pick  │
│          │ │ ⚠ We couldn't send this  │ │   │ it up from the ICT   │
│          │ │   yet — 2 things need    │ │   │ Room.                │
│          │ │   your attention         │ │   │ [error summary]      │
│          │ │   • What is wrong?       │ │   │ About the problem    │
│          │ │   • Where is it?         │ │   │ What is it about?    │
│          │ ├──────────────────────────┤ │   │ Pick the device, or  │
│          │ │ About the problem        │ │   │ choose "Not about a  │
│          │ │ What is it about?        │ │   │ particular device".  │
│          │ │ Pick the device, or…     │ │   │ [ select        ⌄ ]  │
│          │ │ [ IT-0142 — Dell …   ⌄ ] │ │   │ What is wrong?       │
│          │ │ What is wrong?           │ │   │ …                    │
│          │ │ One short line, for …    │ │   │ How soon you need it │
│          │ │ [                      ] │ │   │ ( ) Can wait         │
│          │ │ Tell us more             │ │   │ (•) Normal           │
│          │ │ [                      ] │ │   │ ( ) Urgent           │
│          │ │ [                      ] │ │   │ Anything to show us  │
│          │ │ Where is it?             │ │   │ [ Choose a photo   ] │
│          │ │ [ Choose a room      ⌄ ] │ │   │ Who is asking        │
│          │ ├──────────────────────────┤ │   │ Nimali Perera        │
│          │ │ How soon you need it     │ │   │ (nimali.p)           │
│          │ │ ( ) Can wait …           │ │   │ [ Send the request ] │
│          │ │ (•) Normal …             │ │   │ [ Cancel           ] │
│          │ │ ( ) Urgent …             │ │   │      (96px spacer)   │
│          │ ├──────────────────────────┤ │   ├────┬────┬────┬──────┤
│          │ │ Anything to show us      │ │   │ ⌂  │ ◇6 │ ▤  │  +   │
│          │ │ Who is asking            │ │   └────┴────┴────┴──────┘
│          │ ├──────────────────────────┤ │
│          │ │ [ Send the request ] [Cancel]│
│          │ └──────────────────────────┘ │
└──────────┴──────────────────────────────┘
```

One column, 640px measure, left-aligned inside the content column — never centred,
so the eye returns to the same left edge for every field.

### 2.7 `login.html` and `ui-kit.html`

- **`login.html`** — no app chrome. A 1px-ruled card, 420px wide, centred both
  ways on the `--bg` slate, with the crest at 72px above `Welcome back`. The page
  is not split; the slate field around the card carries a single faint 1px grid
  (12px) that stops 64px from the card, so the card reads as a page in a ledger.
  Footer line `Polymath College · Technology Management Desk` sits 32px below the
  card. On phone the card is full width minus 20px gutters, crest 56px.
- **`ui-kit.html`** — the same sidebar, then one `<h2>` per component family in
  the order given in the task brief, each family in a bordered 1px specimen strip
  with a mono caption naming the class and the tokens it uses. Colour tokens are
  shown as a table: swatch, token name, hex, the pair it is checked against, the
  ratio.

---

## 3. Type

Google Fonts: `Archivo` (600, 700) · `IBM Plex Sans` (400, 500, 600) ·
`IBM Plex Mono` (500). Load exactly these weights.

| Role | Family / weight | Size / line-height | Notes |
|---|---|---|---|
| Wordmark `Polymath College` | Archivo 700 | 17/20, `letter-spacing:.10em`, uppercase | Sidebar and login only |
| h1 | Archivo 700 | 30/36 desktop, 26/32 phone, `-0.01em` | |
| h2 | Archivo 600 | 20/26 | |
| h3 | Archivo 600 | 17/24 | |
| Body / prose | IBM Plex Sans 400 | 16/26 | Never below 16px |
| Table cell | IBM Plex Sans 400 | 16/22 | |
| Lead paragraph | IBM Plex Sans 400 | 18/28 | |
| Form label | IBM Plex Sans 600 | 16/22 | |
| Help text | IBM Plex Sans 400 | 15/22 | Sits under the label, above the field |
| Button | Archivo 600 | 16/20 | |
| Column header, nav group title, chip | IBM Plex Sans 600 | 13/16, `.06em`, uppercase | Labels only, never a sentence |
| Reference, tag, date, money, counts | IBM Plex Mono 500 | 15/20, `font-variant-numeric: tabular-nums` | `REQ-2048`, `IT-0142`, `Rs 285,000`, `5CG4113XYZ` |
| Figure number on a stat tile | IBM Plex Mono 500 | 34/38 | |

Measure: prose is capped at 68 characters (`--measure: 62ch`); the form column is
640px; the table may use the full 1120px content width.

---

## 4. Palette

Derivation. The crest purple `#722A82` is `hsl(289, 51%, 34%)`. Its hue, 289°, is
kept for every purple step and is bent **backwards** into the neutrals: Ledger's
greys are `hsl(230, 12–26%, …)`, a cool slate that is the crest hue pulled 59°
toward blue and drained of saturation, so the paper reads as a cool complement to
the mark rather than a tint of it. Functional colours are set at hues far from
289° (212 · 162 · 32 · 352) and at lightnesses that hold ≥4.5:1 on white.

| Token | Hex | Derivation |
|---|---|---|
| `--brand` | `#722A82` | The crest, unmodified |
| `--brand-strong` | `#4E1C59` | `--brand` at L 26% — text on purple tints |
| `--brand-tint` | `#F6EEF8` | `--brand` hue at L 96% |
| `--brand-line` | `#C9A7D1` | `--brand` hue at L 80% — decorative rules only |
| `--ink` | `#171A23` | slate 230° at L 12% |
| `--muted` | `#565E72` | slate 230° at L 39% |
| `--line` | `#D6DBE6` | slate 230° at L 87% — hairlines |
| `--line-strong` | `#858DA1` | slate 230° at L 60% — control borders |
| `--bg` | `#F3F5FA` | slate 230° at L 97% — the page |
| `--surface` | `#FFFFFF` | Content cards, table body |
| `--surface-2` | `#E9ECF4` | slate 230° at L 94% — sidebar, table head |
| `--info` | `#0F4C93` | New |
| `--info-tint` | `#E7F0FB` | |
| `--ok` | `#0B6B52` | Fixed, Good, In store |
| `--ok-tint` | `#E3F3EE` | |
| `--warn` | `#8A4B07` | Waiting on someone, In repair, Needs repair |
| `--warn-tint` | `#FBEFE0` | |
| `--danger` | `#A81436` | Urgent, Out of service, errors |
| `--danger-tint` | `#FBE7EB` | |
| `--focus` | `#722A82` | The focus ring is the brand |

**Contrast pairs** (recompute each with the WCAG formula and print the exact value
in the folder's `README.md`; every figure below is the value to expect):

| Pair | Ratio | Needs |
|---|---|---|
| `--ink` on `--surface` | 17.4:1 | 4.5 |
| `--ink` on `--bg` | 15.9:1 | 4.5 |
| `--ink` on `--surface-2` | 14.7:1 | 4.5 |
| `--muted` on `--surface` | 6.5:1 | 4.5 |
| `--muted` on `--bg` | 5.9:1 | 4.5 |
| `--surface` on `--brand` (primary button) | 8.9:1 | 4.5 |
| `--brand` on `--surface` (links, icons) | 8.9:1 | 4.5 |
| `--brand-strong` on `--brand-tint` | 11.3:1 | 4.5 |
| `--line-strong` on `--surface` (field border) | 3.3:1 | 3.0 |
| `--info` on `--info-tint` | 7.4:1 | 4.5 |
| `--ok` on `--ok-tint` | 5.6:1 | 4.5 |
| `--warn` on `--warn-tint` | 6.0:1 | 4.5 |
| `--danger` on `--danger-tint` | 6.3:1 | 4.5 |
| `--focus` ring on `--bg` | 8.1:1 | 3.0 |

`--line` (1.4:1) and `--brand-line` (2.1:1) are decorative hairlines only. No
control border, no icon that carries meaning and no text uses them.

---

## 5. Space, radius, depth

- **Space, 4px base:** `--s1 4` `--s2 8` `--s3 12` `--s4 16` `--s5 24` `--s6 32`
  `--s7 48` `--s8 64`. Card padding `--s5`; section gap `--s6`; table cell padding
  `--s3` `--s4`.
- **Radius:** `--r-sm 2px` (chips, inputs), `--r-md 4px` (cards, buttons),
  `--r-lg 6px` (modal). Nothing is rounder than 6px — the geometry is a ruled book.
- **Depth:** no shadow on static surfaces. Two shadows exist:
  `--shadow-pop: 0 1px 2px rgba(23,26,35,.10), 0 8px 24px rgba(23,26,35,.10)` for
  the modal and the toast only. Separation everywhere else is a 1px `--line` rule.
- **Grid:** 12 columns, 24px gutter, content max 1120px, page gutters 32px desktop
  / 20px phone.

---

## 6. Components

| Component | Treatment |
|---|---|
| Primary button | `--brand` fill, white label, `--r-md`, 44px tall (48px in the sidebar and on phone), padding `12px 20px`. Hover: L −6%. Active: L −12%, no movement. |
| Secondary button | `--surface` fill, 1px `--line-strong` border, `--ink` label, same metrics. |
| Quiet button / link button | No border, `--brand` label, underline on hover. 44px minimum hit area via padding. |
| Destructive button | `--danger` fill, white label. Never placed next to the primary without 24px between them. |
| Icon-only button | 44×44, always with `aria-label` **and** a `title`. Used only for `Clear the search box`. |
| Busy button | Label swaps to `Sending…`, a 16px spinner appears before it, `aria-busy="true"`, `disabled`. Width is locked before the swap so nothing reflows. |
| Field | 44px tall, `--surface` fill, 1px `--line-strong` border, `--r-sm`, 16px text, 12px horizontal padding. Focus: 3px `--focus` ring, 2px offset, border goes `--brand`. Error: 2px `--danger` border + `--danger-tint` fill at 0 … the tint fills only the 4px left edge, so colour is never the only signal. |
| Label / help | Label 16px semibold above the field; help 15px `--muted` between label and field, wired with `aria-describedby`. |
| Error message | Under the field, 15px `--danger`, prefixed by a 16px `!` icon and the word `Fix this:` is **not** used — the message itself is the instruction. |
| Table row | 44px, 1px `--line` bottom rule, hover `--surface-2`, no zebra striping. The whole row is a link target via a stretched anchor on the reference cell. |
| Card | `--surface`, 1px `--line`, `--r-md`, padding `--s5`. No shadow. |
| Stat tile | `--surface`, 1px `--line`, number in mono 34px `--ink`, words 15px `--muted` below. The urgent tile carries a `--danger` 3px top rule and the `⚑` icon, so it differs by shape as well as colour. |
| Status badge | 28px tall inline-flex, `--r-sm`, tint fill, 1px border in the same hue at L 80%, 16px icon + the word in 14px semibold. Icon and word always together. |
| Urgency chip | Same shell, outline only (transparent fill, 1px `--line-strong`) so it never competes with status. |
| Timeline item | 1px `--brand-line` vertical rail, 9px `--brand` square node, date in mono, then who, then what. |
| Alert | Full-width band, 4px left bar in the functional hue, tint fill, 20px icon, `<h2>`-level title 17px, body 16px. Four kinds: information, success, warning, danger. |
| Toast | Bottom-centre on phone, bottom-left above the sidebar on desktop. `--ink` fill, white text, 20px icon, an `Undo` button, and a `Close` button. `role="status"`, auto-dismiss 8s, pauses on hover and on focus. |
| Modal | 480px, `--surface`, `--r-lg`, `--shadow-pop`, 1px `--line`. Title `<h2>`, body, then `Yes, …` primary and `No, …` secondary with 24px between. `role="dialog" aria-modal="true"`, focus moves to the title, Escape closes, focus returns to the button that opened it. |
| Empty state | Centred in the list area, 48px outline icon in `--line-strong`, `<h2>`, one sentence, one primary button. |
| Pagination | `‹ Previous`, the page numbers, `Next ›`, each 44px tall, current page marked with `aria-current="page"` plus a 2px underline. |
| Avatar | 36px `--r-sm` square (never a circle), `--brand-tint` fill, `--brand-strong` initials `NP` in mono. |
| Icons | **Solar Bold**, inline SVG, `currentColor`, 20px in text, 22px in the tab bar, 24px in alerts. `aria-hidden="true" focusable="false"` when a word is beside them. |

**Status vocabulary — icon and word, identical in every direction:**

| Value | Icon (Solar Bold) | Colour token |
|---|---|---|
| `New` | star | `--info` |
| `In progress` | refresh-circle | `--brand` |
| `Waiting on someone` | clock-circle | `--warn` |
| `Fixed` | check-circle | `--ok` |
| `Closed` | archive | `--muted` |
| `In store` | box | `--ok` |
| `Issued` | hand-holding | `--info` |
| `In repair` | wrench | `--warn` |
| `Out of service` | close-circle | `--danger` |
| `Good` | check-circle | `--ok` |
| `Needs repair` | danger-triangle | `--warn` |
| `Can wait` | hourglass | `--muted` |
| `Normal` | flag | `--muted` |
| `Urgent` | fire | `--danger` |

The flame for `Urgent` is taken from the torch on the crest.

---

## 7. The one chart

Ledger shows exactly one chart: **Requests raised in the last five school days**
(Mon 1 · Tue 2 · Wed 0 · Thu 1 · Fri 1).

- Form: vertical bars — the job is magnitude across five ordered categories.
- One series, so no legend; the `<h2>` names it. Bars are `--brand`; Tuesday, the
  highest, is `--brand-strong` and carries its value label above the bar.
- **Wednesday is zero, and a zero must be visible.** A bar of no height reads as
  missing data, not as "no requests". Draw Wednesday as a 3px `--line-strong` tick
  on the baseline — an empty bar — with its value label `0` directly above the tick
  in `--muted` 13px, in the same position as every other day's number, so the five
  days read as one series with one zero in it.
  Every other day carries its number above its bar, so no value is inferred from
  height alone.
- Bars 28px wide, 12px apart, 4px rounded top corners only, sitting on a 1px
  `--line-strong` baseline. No gridlines, no y-axis ticks beyond the three whole
  numbers (0, 1, 2), no 3-D, no gradient.
- Built as inline SVG with `currentColor`, `role="img"` and an `aria-label` reading
  `Requests raised: Monday 1, Tuesday 2, Wednesday 0, Thursday 1, Friday 1.` —
  this sentence is fixed by the Content contract; use it exactly, with no rewording.
- The text alternative is printed beside it, always visible, not only for screen
  readers: `Mon 1 · Tue 2 · Wed 0 · Thu 1 · Fri 1`.
- `--brand` on `--surface` is 8.9:1, well past the 3:1 a meaningful graphic needs.

---

## 8. Density intent

Ledger is the **densest** of the five. Target at 1440×900: the chrome above the
first request row is ~236px (52px page head band + 96px filter panel + 48px result
line + 40px table head), rows are 44px, so **all 8 request rows start above 900px**.
State this number in the folder `README.md`.

---

## 9. States

| State | What the user sees |
|---|---|
| Default | As drawn above. |
| Loading | Only the JavaScript-enhanced filter is async-feeling. While it runs, the result line reads `Finding requests…` in `--muted` with a 16px spinner; it is an `aria-live="polite"` region, so the count that replaces it is announced. Nothing else has a loading state — the prototype is static HTML. |
| Empty (`requests.html?demo=empty`) | The table is replaced by the empty state: `No requests match what you chose` / `Try clearing the filters, or search for a different word.` / `[ Clear the filters ]`. The search box and filters stay on screen with the user's choices still in them. |
| Validation errors (`request-form.html?demo=errors`) | Danger alert at the top of the form: `We couldn't send this yet — 2 things need your attention`, with a list of two links to `#id_what_is_wrong` and `#id_where`. Each field keeps what the user typed, gets `aria-invalid="true"`, a 2px `--danger` border, and its message below, wired through `aria-describedby`. Focus moves to the alert on load. |
| Server error | Danger alert above the form: `We couldn't save that just now` / `Nothing you typed has been lost. Wait a moment and press "Send the request" again.` Every field keeps its value. |
| Success | Toast on the page you land on: `Request sent. We gave it the number REQ-2049.` with `Undo`. Also rendered as a success alert at the top of `dashboard.html` for anyone who dismisses the toast or has it time out. |
| Sign-in error (`login.html?demo=error`) | Danger alert above the fields: `We couldn't sign you in` / `That username or password didn't match. Try again, or ask the office to reset it.` The username box still holds `nimali.p`; the password box is cleared and takes focus. |
| No permission (`device.html?demo=denied`) | The content column is replaced by a bordered panel: 40px `--warn` lock icon, `<h2>` `You can't open this page`, body `This page is for ICT staff. Ask Nimali Perera in the ICT Room, or raise a request and we will help.`, and `[ + Raise a request ]`. The sidebar stays, so the person is not stranded. |

---

## 10. Copy — use these words exactly

**Global**

- Wordmark: `Polymath College`; under it, `Technology Management Desk`.
- Navigation: `Home` · `Requests` · `Devices` · `Raise a request`.
- Utility: `Nimali Perera`, `ICT Technician`, `Design kit`, `Sign out`.
- Skip link: `Skip to main content`.

**`login.html`**

| Element | Text |
|---|---|
| Heading | `Welcome back` |
| Sub-line | `Sign in to the Technology Management Desk.` |
| Label / help | `Username` / `The name the school gave you, like nimali.p` |
| Label / help | `Password` / `Passwords are case sensitive.` |
| Button | `Sign in` |
| Error title / body | `We couldn't sign you in` / `That username or password didn't match. Try again, or ask the office to reset it.` |
| Footer | `Polymath College · Technology Management Desk` |

**`dashboard.html`**

- `<h1>` `Home`. Lead: `Friday 11 September 2026. Here is what needs doing today.`
- `<h2>` `What needs doing`, then the seven figures worded exactly:
  `6 requests open` · `2 are urgent` · `1 raised today` ·
  `3 devices due back next week` · `2 devices in repair` ·
  `128 devices in the register` · `34 out on loan`.
- `<h2>` `Requests to work on`, link `See all requests`.
- `<h2>` `Devices to watch`, link `Open the device record`.
- `<h2>` `Requests raised in the last five school days`.
- `<h2>` `Things you can do`, buttons `Raise a request`,
  `Go to the requests queue`, `Open the device record`.

**`requests.html`**

- `<h1>` `Requests`. Lead: `Everything staff have asked us to fix. Open the ones marked urgent first.`
- Search label `Search requests`; placeholder `Reference, words, or a person's name, e.g. projector or REQ-2048`.
- Filters: `Status` (`All statuses`, `New`, `In progress`, `Waiting on someone`, `Fixed`, `Closed`) · `How urgent` (`All`, `Can wait`, `Normal`, `Urgent`) · `Who is on it` (`Anyone`, `Nobody yet`, `Nimali Perera`, `Ruwan Jayasuriya`).
- Sort: `Newest first` (default), `Most urgent first`, `Oldest first`.
- Result line: `Showing 8 of 8 requests`.
- Column headers: `Reference` · `What is wrong` · `Raised by` · `Status` · `How urgent` · `Who is on it` · `Raised`.
- Empty state: `No requests match what you chose` / `Try clearing the filters, or search for a different word.` / `Clear the filters`.

**`device.html`**

- `<h1>` `IT-0142 — Dell Latitude 3540 laptop`. Lead: `Laptop · Issued to Dilani Fernando · Grade 6B Classroom`.
- `<h2>` `Where this device is` · `<h2>` `What it cost and how long it is covered` ·
  `<h2>` `Requests about this device` · `<h2>` `What has happened to it`.
- Buttons: `Raise a request about this device` (primary), `Mark it returned` (secondary).
- Modal: `Mark IT-0142 returned?` / `This puts the laptop back in the ICT Store and clears the due-back date. You can give it out again at any time.` / `Yes, mark it returned` · `No, keep it as it is`. Toast after: `IT-0142 is back in the ICT Store.`

**`request-form.html`**

- `<h1>` `Raise a request`. Lead: `Tell us what is wrong. We will pick it up from the ICT Room.`
- `<h2>` `About the problem` (fields 1–4) · `<h2>` `How soon you need it` (field 5) ·
  `<h2>` `Anything to show us` (field 6) · `<h2>` `Who is asking` (field 7).

| # | Label | Help text | Control |
|---|---|---|---|
| 1 | `What is it about?` | `Pick the device, or choose "Not about a particular device".` | Select: the eight devices as `IT-0142 — Dell Latitude 3540 laptop`, plus `Not about a particular device` |
| 2 | `What is wrong?` | `One short line, for example "Projector will not turn on".` | Text input, required |
| 3 | `Tell us more` | `What happens, when it started, and what you already tried.` | Textarea, optional |
| 4 | `Where is it?` | `The room where we will find it.` | Select of the rooms |
| 5 | `How urgent is it?` | `Pick the one that fits. We look at urgent ones first.` | Radios `Can wait` (`It can wait until next week.`), `Normal` (`I need it in the next day or two.`), `Urgent` (`A class or the office is stopped right now.`); `Normal` preselected |
| 6 | `Add a photo` | `Optional. A photo of the screen or the error helps us a lot.` | File input |
| 7 | `Your name` | `We will reply to you.` | Read-only, `Nimali Perera (nimali.p)` |

- Buttons `Send the request` (primary) · `Cancel` (secondary).
- Errors: `What is wrong?` → `Type a short description of the problem, for example "Projector will not turn on".`; `Where is it?` → `Choose the room where we will find it.`; summary `We couldn't send this yet — 2 things need your attention`.
- Success toast: `Request sent. We gave it the number REQ-2049.` with `Undo`.

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

**Sample rows.** Take every person, device, request, date and amount **verbatim**
from the Content contract in `docs/tasks/002-design-directions.md`. Do not retype
from memory and do not add a name, room or figure that is not in that table.

---

## 11. Accessibility

- **Landmarks:** `<header>` (top bar on phone only), `<nav aria-label="Main">`
  (sidebar / tab bar), `<main id="main">`, `<nav aria-label="Utility">`,
  `<footer>`. One of each per page.
- **Headings:** one `<h1>` per page, matching the nav label that reached it
  (`Home`, `Requests`, `Raise a request`; `Devices` opens
  `IT-0142 — Dell Latitude 3540 laptop`, and its breadcrumb says `Devices`).
  `<h2>` for each section, `<h3>` only inside the ui-kit specimens. No level skipped.
- **Skip link** is the first focusable element, visible on focus, pointing at
  `#main`.
- **Form wiring:** `<label for>` on every control; help text in a `<p id="…-help">`
  linked by `aria-describedby`; the error message `<p id="…-error">` appended to the
  same `aria-describedby` list, so the screen reader reads label → help → error.
  `aria-invalid="true"` only on fields that actually failed. The radio group is a
  `<fieldset>` with `<legend>How urgent is it?</legend>` and its help text linked to
  the fieldset. The error summary is `role="alert" tabindex="-1"` and takes focus on
  load; each of its links moves focus to the field itself.
- **Focus order** follows the visual order: skip link → sidebar (or top bar) → main
  → utility. No positive `tabindex` anywhere.
- **Focus ring:** 3px `--focus` with a 2px white offset ring on every focusable
  element, so it is visible on `--surface`, on `--surface-2` and on the purple
  button alike (8.1:1 against the page). Never removed, never replaced by colour
  change alone.
- **Dialogs:** the `Mark it returned` modal traps focus, closes on Escape, and
  returns focus to `Mark it returned`. After the toast auto-dismisses, focus is
  untouched.
- **Redirects:** after a successful send, the landing page puts focus on its `<h1>`
  so the toast and the page name are both announced.
- **Touch targets:** every control is ≥44×44 at 400px — tab bar cells 56px, list
  rows 104px, buttons 52px, select/inputs 48px, pagination 44px. Adjacent targets
  are at least 8px apart; `Cancel` sits 24px from `Send the request`.
- **Tables:** `<caption class="visually-hidden">Requests, newest first</caption>`,
  `<th scope="col">` on every column header, `<th scope="row">` on the reference
  cell. Sort state is announced with `aria-sort`.
- **Colour is never alone:** every status, condition and urgency value is an icon
  plus its word. Greyscale the page and nothing is lost.

---

## 12. Motion

Fast and mechanical, because this is a working screen.

- Hover and focus colour changes: 120ms `linear`.
- Toast: slide up 12px + fade, 160ms `cubic-bezier(.2,0,.2,1)`; out 120ms.
- Modal: backdrop fade 120ms, panel fade only — no scale, no bounce.
- `<details>` filter panel on phone: no animation.
- Nothing loops, nothing moves on scroll, nothing parallaxes.
- Reduced motion:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .01ms !important;
    scroll-behavior: auto !important;
  }
}
```

---

## 13. Progressive enhancement

**Works with plain HTML and a full page load:** all navigation, the filter and
sort form (a `<form method="get">` with a `Apply` submit that is visually hidden
once JavaScript runs), the phone filter disclosure (`<details>`), the request form,
the sign-out form, pagination, the modal (a `<dialog>` with a fallback: without
JavaScript the `Mark it returned` button is a link to a confirmation section at the
bottom of the same page).

**`app.js` adds, and only adds:** filtering and sorting the table in place with the
live result line; clearing the search box; toast rendering and dismissal from
`?demo=toast`; `?demo=` state switching; focusing the error summary; the modal's
focus trap. Every hook is a `data-*` attribute. Nothing that a task needs is
JavaScript-only.

---

## 14. Demo hooks

`login.html?demo=error` · `request-form.html?demo=errors` ·
`requests.html?demo=empty` · `?demo=toast` on any app page ·
`device.html?demo=denied`. These are prototype-only switches and are never carried
into application templates.

---

## 15. Skills the builder should load

`technical-wireframe-info-layout` — for its annotation and linework discipline
only; ignore its dark monochrome surface, this direction is light-mode ·
`container-lines` · `number-details` · `ui-design:information-density` ·
`accessible-content:table-accessibility` · `interaction-design:search-ux` ·
`inclusive-interaction:keyboard-navigation` · `solar-duotone-bold` (use the **Bold**
weight, not the duotone) · `dataviz` (for the one chart) ·
`cognitive-accessibility:plain-language-design`.
