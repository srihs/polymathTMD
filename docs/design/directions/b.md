`design/b-parchment/`

# Direction B — Parchment

**Concept.** Parchment is the calm end of the range: one warm, unhurried column of
paper with a single job on it at a time, sized so that a teacher who opens it twice
a term never has to work out where to look. It carries the crest's purple as a
quiet plum on a parchment ground, and it buys its clarity with white space rather
than with lines, boxes or density.

**Who it suits.** Dilani teaches Grade 6B and uses this system perhaps four times a
term, usually while a class is waiting. For her the enemy is not missing
information, it is a screen with forty things on it. Parchment shows her one
question at a time in 18px type on a warm ground that does not glare in a bright
classroom, makes every tappable thing 56px so it works with a finger and a stylus
and a shaky hand alike, and states the next step in a sentence under every heading.
Its dashboard is a hub of five large cards, each one a job with a verb on it, so
the first screen after signing in is a menu of things to do rather than a report to
interpret.

---

## 1. Navigation model

**Desktop (≥900px): a top bar carrying the four labels; no sidebar; one centred column.**

- 72px top bar, `--surface` fill, one 1px `--line` rule along the bottom, no shadow
  until the page is scrolled (then a 1px rule only — never a drop shadow).
- Left: crest chip 36px + wordmark `Polymath College` in Fraunces, with
  `Technology Management Desk` in 13px Karla beneath it.
- Centre: the four labels as text links, 17px, 24px apart, each with 20px of
  vertical padding so the hit area is 56px tall. `Raise a request` is the last one
  and is a filled plum button, not a link.
- Right: `Nimali Perera` with a 40px circular avatar, which is a link to the
  utility section; beside it `Sign out` as a quiet button in a POST form.
- Current page: `aria-current="page"`, the label in `--brand-strong` semibold, and
  a 3px plum underline sitting 6px under the text. `Design kit` lives in the
  footer, not the bar.
- Content: one column, `max-width: 760px`, centred, 48px page gutters. Nothing is
  ever placed in a second column on this direction — that restriction is the
  direction.

**Phone (<900px): a `<details>` "Menu" panel under a slim top bar.**

- 64px top bar: crest chip, the page name, and a 56px `Menu` button that is the
  `<summary>` of a `<details>` element. Open, it pushes the page down and shows the
  four labels as full-width 56px rows with a 24px duotone icon each, then a rule,
  then `Nimali Perera`, `Design kit`, `Sign out`.
- `Raise a request` is *also* pinned as a full-width 56px plum button directly
  under the top bar on `dashboard.html` and `requests.html`, and as the last item in
  every page's footer, so it is always within one thumb reach without opening the
  menu.
- The menu is a real `<details>`; it opens and closes with no JavaScript, keeps its
  state through a page load, and is announced as a disclosure.

**With JavaScript off.** Identical. `app.js` only adds closing the menu when a link
inside it is clicked, and nothing depends on that.

---

## 2. Wireframes

### 2.1 `dashboard.html` — desktop 1440

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ [skip to main content]                                                               │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ ▣ Polymath College       Home   Requests   Devices  [ + Raise a request ]   ◕ Nimali │
│   Technology Mgmt Desk   ────                                               Sign out │
├──────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│                    ┌────────────────── 760px ──────────────────┐                     │
│                    │ Home                                      │  h1 40px Fraunces   │
│                    │ Friday 11 September 2026. Here is what    │  lead 19px          │
│                    │ needs doing today.                        │                     │
│                    │                                           │                     │
│                    │ What needs doing                          │  h2 26px            │
│                    │ ┌───────────────────────────────────────┐ │                     │
│                    │ │  6  requests open                     │ │  one row per figure │
│                    │ │  2  are urgent                    ⚑   │ │  64px, 1px rule     │
│                    │ │  1  raised today                      │ │  between rows       │
│                    │ │  3  devices due back next week        │ │                     │
│                    │ │  2  devices in repair            🔧   │ │                     │
│                    │ │ 128 devices in the register           │ │                     │
│                    │ │ 34  out on loan                       │ │                     │
│                    │ └───────────────────────────────────────┘ │                     │
│                    │                                           │                     │
│                    │ Things you can do                         │  h2                 │
│                    │ ┌─────────────────┐ ┌───────────────────┐ │  card hub, 2-up     │
│                    │ │ ✎ (32px icon)   │ │ ◇ (32px icon)     │ │  180px tall         │
│                    │ │ Raise a request │ │ Go to the         │ │                     │
│                    │ │ Tell us what is │ │ requests queue    │ │                     │
│                    │ │ wrong and we    │ │ Work through the  │ │                     │
│                    │ │ will pick it up.│ │ 6 open requests.  │ │                     │
│                    │ └─────────────────┘ └───────────────────┘ │                     │
│                    │ ┌─────────────────┐ ┌───────────────────┐ │                     │
│                    │ │ ▤               │ │ ✋                 │ │                     │
│                    │ │ Open the device │ │ See devices due   │ │                     │
│                    │ │ record          │ │ back              │ │                     │
│                    │ │ IT-0142, the    │ │ 3 are due back    │ │                     │
│                    │ │ Grade 6B laptop.│ │ next week.        │ │                     │
│                    │ └─────────────────┘ └───────────────────┘ │                     │
│                    │                                           │                     │
│                    │ Requests to work on                       │  h2                 │
│                    │ ┌───────────────────────────────────────┐ │                     │
│                    │ │ REQ-2048               ⚑ Urgent       │ │  156px card rows    │
│                    │ │                                       │ │  (three lines here: │
│                    │ │                                       │ │   no raiser·date)   │
│                    │ │ Projector in Lab 2 shows a blue screen│ │                     │
│                    │ │ ↻ In progress · Nimali Perera         │ │                     │
│                    │ ├───────────────────────────────────────┤ │                     │
│                    │ │ REQ-2047               ⚑ Normal       │ │                     │
│                    │ │ Laptop will not connect to the staff  │ │                     │
│                    │ │ Wi-Fi · ★ New · Nobody yet            │ │                     │
│                    │ └───────────────────────────────────────┘ │                     │
│                    │ See all requests →                        │                     │
│                    │                                           │                     │
│                    │ Devices to watch                          │  h2                 │
│                    │ … three 96px rows …                       │                     │
│                    └───────────────────────────────────────────┘                     │
│ ──────────────────────────────────────────────────────────────────────────────────── │
│      Polymath College · Technology Management Desk        Design kit   Sign out      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

Parchment shows **no chart**. The seven figures are read as a sentence each
(`6 requests open`), which is the same information with less to decode.

### 2.2 `dashboard.html` — phone 400

```
┌──────────────────────────────────────┐
│ [skip to main content]               │
│ ▣  Home                   [ Menu ▾ ] │  64px
├──────────────────────────────────────┤
│ [ + Raise a request              ]   │  56px plum, full width
├──────────────────────────────────────┤
│ Home                                 │  h1 32px
│ Friday 11 September 2026. Here is    │  lead 18px
│ what needs doing today.              │
│                                      │
│ What needs doing                     │
│ ┌──────────────────────────────────┐ │
│ │  6   requests open               │ │  64px rows, 1px rules
│ │  2   are urgent              ⚑   │ │
│ │  1   raised today                │ │
│ │  3   devices due back next week  │ │
│ │  2   devices in repair       🔧  │ │
│ │ 128  devices in the register     │ │
│ │ 34   out on loan                 │ │
│ └──────────────────────────────────┘ │
│                                      │
│ Things you can do                    │
│ ┌──────────────────────────────────┐ │  cards stack 1-up
│ │ ✎  Raise a request               │ │  136px
│ │    Tell us what is wrong and we  │ │
│ │    will pick it up.              │ │
│ ├──────────────────────────────────┤ │
│ │ ◇  Go to the requests queue      │ │
│ │    Work through the 6 open       │ │
│ │    requests.                     │ │
│ ├──────────────────────────────────┤ │
│ │ ▤  Open the device record        │ │
│ │ ✋  See devices due back          │ │
│ └──────────────────────────────────┘ │
│                                      │
│ Requests to work on                  │
│ … two 182px card rows …              │
│ See all requests →                   │
│                                      │
│ Devices to watch                     │
│ … three 112px rows …                 │
│ ──────────────────────────────────── │
│ Polymath College · Technology        │
│ Management Desk                      │
│ Design kit   [ Sign out ]            │
│ [ + Raise a request              ]   │  repeated at the foot
└──────────────────────────────────────┘
```

Open menu state (the `<details>` expanded) pushes everything below it down:

```
│ ▣  Home                   [ Menu ▴ ] │
│ ┌──────────────────────────────────┐ │
│ │ ⌂  Home                          │ │  56px rows
│ │ ◇  Requests                  (6) │ │
│ │ ▤  Devices                       │ │
│ │ ✎  Raise a request               │ │
│ │ ───────────────────────────────  │ │
│ │ ◕  Nimali Perera, ICT Technician │ │
│ │ ▦  Design kit                    │ │
│ │ [ Sign out ]                     │ │
│ └──────────────────────────────────┘ │
```

### 2.3 `requests.html` — desktop 1440

```
│                    ┌────────────────── 760px ──────────────────┐
│                    │ Requests                                  │  h1 40px
│                    │ Everything staff have asked us to fix.    │
│                    │ Open the ones marked urgent first.        │
│                    │                                           │
│                    │ Search requests                           │  label 17px
│                    │ [🔍 Reference, words, or a person's name, ]│  56px field
│                    │                                           │
│                    │ ▸ Filter and sort                         │  <details>, 56px
│                    │                                           │
│                    │ Showing 8 of 8 requests                   │
│                    │ ┌───────────────────────────────────────┐ │
│                    │ │ REQ-2048               ⚑ Urgent       │ │  188px card
│                    │ │ Projector in Lab 2 shows a blue screen│ │  + 16px gap
│                    │ │ ↻ In progress · Nimali Perera         │ │  top: 460
│                    │ │ Suresh Kumara · Fri 11 Sep 2026 8:15am│ │
│                    │ └───────────────────────────────────────┘ │
│                    │ ┌───────────────────────────────────────┐ │
│                    │ │ REQ-2047               ⚑ Normal       │ │  top: 664
│                    │ │ Laptop will not connect to the staff  │ │
│                    │ │ Wi-Fi                                 │ │
│                    │ │ ★ New · Nobody yet                    │ │
│                    │ │ Dilani Fernando · Thu 10 Sep, 11:20am │ │
│                    │ └───────────────────────────────────────┘ │
│                    │ ┌───────────────────────────────────────┐ │
│                    │ │ REQ-2046               ⚑ Normal       │ │  top: 868
│                    │ │ Printer jams on every second page     │ │
│                    │ │ ◷ Waiting on someone · Nimali Perera  │ │
│                    │ │ Anoma Silva · Tue 8 Sep 2026, 1:40 pm │ │
│ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│─└───────────────────────────────────────┘─│─ ─ 900px fold
│                    │ … five more, same anatomy …               │  4th card: 1072
│                    │  ‹ Previous      1       Next ›           │
│                    └───────────────────────────────────────────┘
```

**No table anywhere in Parchment.** The queue is a list of cards at every width,
and the card is a four-line object, which is why only three reach the fold — the
direction's intent, and the reason it sits at the bottom of the density ladder.

**The card's real height, so the spec and the build agree.** A 760px column gives
the card 712px of content, on which the longest title in the contract
(`Tablet needed for the Grade 5 reading class on Monday`) still sets on one line.
Its four bands are:

| Band | Height |
|---|---|
| Padding top | 24 |
| Reference (17/24) with the urgency chip (32px pill) beside it | 32 |
| gap | 8 |
| Title, Karla 700 19/26, one line | 26 |
| gap | 8 |
| Status badge (32px pill) with `· Who is on it` beside it | 32 |
| gap | 6 |
| `Raised by · Raised`, 15/22 | 22 |
| Padding bottom | 24 |
| 1px `--line` border, top and bottom | 2 |
| **Card** | **184** |

Build it at **188px** (184 plus 4px of slack for font-metric differences); anything
in 184–196 is correct. With the 16px gap the pitch is **204px**. The earlier figure
of 120px in this file was wrong — it could never have held four lines at 17–19px
with 24px padding, and the builder was right to report it.

**Vertical budget at 1440×900 — build to these numbers.**

| Band | Height | Cumulative |
|---|---|---|
| Top bar + 1px `--line` rule | 73 | 73 |
| Page-head top padding | 32 | 105 |
| `<h1>` `Requests`, 40/48 | 48 | 153 |
| gap | 12 | 165 |
| Lead, 19/30, two lines | 60 | 225 |
| gap | 24 | 249 |
| `Search requests` label, 17/24 | 24 | 273 |
| gap | 6 | 279 |
| Search field | 56 | 335 |
| gap | 16 | 351 |
| `Filter and sort` disclosure (closed) | 56 | 407 |
| gap | 16 | 423 |
| `Showing 8 of 8 requests`, 17/24 | 24 | 447 |
| gap | 13 | 460 |
| **First card starts** | — | **460** |

Card tops are then 460 · 664 · 868, and the fourth is at 1072 — **three cards above
the fold, with 32px of margin on the third.**

The tolerance, so the builder can check rather than guess: with a 204px pitch the
first card must start between **288px and 491px** for the count to be exactly 3. If
the measured count is not 3, adjust the page-head top padding and the four gaps
above — never the card, whose height is what this direction is arguing for.

### 2.4 `requests.html` — phone 400

```
┌──────────────────────────────────────┐
│ ▣  Requests               [ Menu ▾ ] │
├──────────────────────────────────────┤
│ [ + Raise a request              ]   │
├──────────────────────────────────────┤
│ Requests                             │
│ Everything staff have asked us to    │
│ fix. Open the ones marked urgent     │
│ first.                               │
│ Search requests                      │
│ [🔍 Reference, words, or a person's ]│  56px
│ ▸ Filter and sort                    │  56px <details>
│ Showing 8 of 8 requests              │
│ ┌──────────────────────────────────┐ │
│ │ REQ-2048            ⚑ Urgent     │ │  236px card (the title
│ │                                  │ │  and the metadata each
│ │                                  │ │  wrap to two lines at
│ │                                  │ │  400px)
│ │ Projector in Lab 2 shows a blue  │ │
│ │ screen                           │ │
│ │ ↻ In progress · Nimali Perera    │ │
│ │ Suresh Kumara                    │ │
│ │ Fri 11 Sep 2026, 8:15 am         │ │
│ └──────────────────────────────────┘ │
│ … cards, 16px apart …                │
│  ‹ Previous     1     Next ›         │
│ ──────────────────────────────────── │
│ footer + [ + Raise a request ]       │
└──────────────────────────────────────┘
```

### 2.5 `device.html` — desktop / phone

```
DESKTOP (760px column)                     PHONE
┌────────────────────────────────────┐    ┌──────────────────────┐
│ ← Back to Devices                  │    │ ▣ Devices  [ Menu ▾ ]│
│ IT-0142 — Dell Latitude 3540 laptop│    ├──────────────────────┤
│ Laptop · Issued to Dilani Fernando │    │ ← Back to Devices    │
│ · Grade 6B Classroom               │    │ IT-0142 — Dell       │
│ [ ✋ Issued ]  [ ✔ Good ]           │    │ Latitude 3540 laptop │
│                                    │    │ Laptop · Issued to   │
│ [ + Raise a request about this     │    │ Dilani Fernando ·    │
│   device ]                         │    │ Grade 6B Classroom   │
│ [ Mark it returned ]               │    │ [✋ Issued] [✔ Good]  │
│                                    │    │ [ + Raise a request  │
│ Where this device is               │    │   about this device ]│
│ ┌────────────────────────────────┐ │    │ [ Mark it returned ] │
│ │ Who has it   Dilani Fernando   │ │    │ Where this device is │
│ │ Where        Grade 6B Classroom│ │    │ …rows, 56px each…    │
│ │ Given out    Tue 25 Aug 2026   │ │    │ What it cost and how │
│ │ Due back     Mon 21 Sep 2026   │ │    │ long it is covered   │
│ │ Last checked Thu 3 Sep 2026    │ │    │ …rows…               │
│ └────────────────────────────────┘ │    │ Requests about this  │
│ What it cost and how long it is    │    │ device               │
│ covered                            │    │ …2 cards…            │
│ ┌────────────────────────────────┐ │    │ What has happened to │
│ │ Value        Rs 285,000        │ │    │ it                   │
│ │ Bought       14 Feb 2024       │ │    │ …5 timeline items…   │
│ │ Warranty     13 Feb 2027       │ │    │ footer               │
│ │ Serial       5CG4113XYZ        │ │    └──────────────────────┘
│ └────────────────────────────────┘ │
│ Requests about this device         │
│ … two 156px cards …                │
│ What has happened to it            │
│ ○ Thu 10 Sep 2026, 11:20 am        │
│ │ Dilani Fernando                  │
│ │ Raised REQ-2047 — will not       │
│ │ connect to the staff Wi-Fi       │
│ ○ … four more, newest first        │
└────────────────────────────────────┘
```

### 2.6 `request-form.html` — desktop / phone

Same 760px column; the form is 640px inside it, one field per row, 32px between
fields, 56px between sections. Each `<h2>` sits on a 1px rule with 32px of air
above it. The error summary is a plum-bordered card at the top of the form.

```
│ Raise a request                              │
│ Tell us what is wrong. We will pick it up    │
│ from the ICT Room.                           │
│ ┌──────────────────────────────────────────┐ │
│ │ ⚠ We couldn't send this yet — 2 things   │ │
│ │   need your attention                    │ │
│ │   • What is wrong?                       │ │
│ │   • Where is it?                         │ │
│ └──────────────────────────────────────────┘ │
│ About the problem                            │
│ ──────────────────────────────────────────── │
│ What is it about?                            │  label 17px
│ Pick the device, or choose "Not about a      │  help 16px
│ particular device".                          │
│ [ IT-0142 — Dell Latitude 3540 laptop   ⌄ ]  │  56px
│                                              │
│ What is wrong?                               │
│ One short line, for example "Projector will  │
│ not turn on".                                │
│ [                                          ] │  56px, 2px danger border
│ ⚠ Type a short description of the problem,   │  error, 16px
│   for example "Projector will not turn on".  │
│ …                                            │
│ How soon you need it                         │
│ ──────────────────────────────────────────── │
│ ( ) Can wait     It can wait until next week.│  72px radio rows,
│ (•) Normal       I need it in the next day…  │  whole row clickable
│ ( ) Urgent       A class or the office is…   │
│ …                                            │
│ [ Send the request ]                         │  56px, full width of form
│ [ Cancel ]                                   │  56px, quiet
```

On phone the two buttons stack with 16px between them, `Send the request` first.

### 2.7 `login.html` and `ui-kit.html`

- **`login.html`** — the parchment ground fills the window; a single 440px card,
  no border, `--shadow-soft`, radius 28px, sits slightly above centre (42% from the
  top). The crest is 96px, centred, above `Welcome back` in Fraunces 36px. Fields
  are 56px. The footer line sits at the bottom of the window, not on the card.
  Phone: card is full-bleed with 20px gutters and no shadow, crest 72px.
- **`ui-kit.html`** — the same 760px column, one `<h2>` per family, each specimen
  on its own `--surface` card with a Karla caption underneath naming the class and
  its tokens. The colour table gives swatch, token, hex, checked-against and ratio.

---

## 3. Type

Google Fonts: `Fraunces` (500, 600; optical size 24, `SOFT` axis default) ·
`Karla` (400, 500, 700).

| Role | Family / weight | Size / line-height | Notes |
|---|---|---|---|
| Wordmark `Polymath College` | Fraunces 600 | 20/24 | Top bar and login |
| h1 | Fraunces 600 | 40/48 desktop, 32/40 phone | |
| h2 | Fraunces 600 | 26/34 desktop, 24/32 phone | |
| h3 | Fraunces 500 | 20/28 | |
| Body / prose | Karla 400 | 17/28 | The most-read size in this direction |
| Lead paragraph | Karla 400 | 19/30 | |
| Card title | Karla 700 | 19/26 | |
| Form label | Karla 700 | 17/24 | |
| Help text | Karla 400 | 16/24 | |
| Button | Karla 700 | 17/24 | |
| Badge / chip word | Karla 700 | 15/20 | |
| Small print, footer | Karla 400 | 15/22 | Not used for instructions |
| Figure number | Fraunces 600 | 30/34, tabular numerals | |

No uppercase labels anywhere: Fraunces sets the headings and Karla says everything
else in sentence case, because full capitals slow down the readers this direction
is for. Measure is capped at 66 characters.

---

## 4. Palette

Derivation. `#722A82` is `hsl(289, 51%, 34%)`. Parchment warms the brand by two
degrees to 292° for its own plum steps, then builds the paper from the crest's
*complement side*: neutrals at 30–40°, a warm oat, because a purple mark on warm
paper is the oldest trick in school stationery and it stops the screen glaring in a
classroom with the blinds up. Functional hues sit at 148 · 28 · 2 · 238.

| Token | Hex | Derivation |
|---|---|---|
| `--brand` | `#722A82` | The crest, unmodified |
| `--brand-strong` | `#5A2168` | Brand hue 292° at L 30% — text on plum tints |
| `--brand-tint` | `#F0E4F2` | Brand hue at L 94% |
| `--brand-line` | `#C8A5CF` | Brand hue at L 78% — decorative |
| `--ink` | `#2A231C` | Warm 30° at L 16% |
| `--muted` | `#6B6157` | Warm 30° at L 38% |
| `--line` | `#DCD0BC` | Warm 36° at L 84% — hairlines |
| `--line-strong` | `#9A8C79` | Warm 34° at L 54% — control borders |
| `--bg` | `#F5EEE2` | Parchment: warm 38° at L 95% |
| `--surface` | `#FBF7F0` | Warm 40° at L 98% — cards |
| `--surface-2` | `#EBE2D2` | Warm 38° at L 87% — pressed and hover fills |
| `--ok` | `#1C6B3A` | Fixed, Good, In store |
| `--ok-tint` | `#E2F0E4` | |
| `--warn` | `#94540E` | Waiting on someone, In repair, Needs repair |
| `--warn-tint` | `#F8E9D5` | |
| `--danger` | `#AE2A1E` | Urgent, Out of service, errors |
| `--danger-tint` | `#F8E3DF` | |
| `--info` | `#33409B` | New |
| `--info-tint` | `#E6E8F6` | |
| `--focus` | `#5A2168` | `--brand-strong`, which holds on parchment |

**Contrast pairs** (expected values; recompute and print them in the folder README):

| Pair | Ratio | Needs |
|---|---|---|
| `--ink` on `--bg` | 13.4:1 | 4.5 |
| `--ink` on `--surface` | 14.5:1 | 4.5 |
| `--muted` on `--surface` | 5.7:1 | 4.5 |
| `--muted` on `--bg` | 5.2:1 | 4.5 |
| `--surface` on `--brand` (primary button) | 8.3:1 | 4.5 |
| `--brand` on `--surface` | 8.3:1 | 4.5 |
| `--brand-strong` on `--brand-tint` | 9.3:1 | 4.5 |
| `--line-strong` on `--surface` (field border) | 3.1:1 | 3.0 |
| `--ok` on `--ok-tint` | 5.5:1 | 4.5 |
| `--warn` on `--warn-tint` | 5.0:1 | 4.5 |
| `--danger` on `--danger-tint` | 5.5:1 | 4.5 |
| `--info` on `--info-tint` | 7.3:1 | 4.5 |
| `--focus` on `--bg` | ≥9:1 | 3.0 |

`--line` is a 1.4:1 hairline: decoration only, never a control border.

---

## 5. Space, radius, depth

- **Space, 8px base:** `--s1 8` `--s2 16` `--s3 24` `--s4 32` `--s5 48` `--s6 64`
  `--s7 96`. Nothing in this direction uses a gap smaller than 8px. Field-to-field
  32px, section-to-section 64px, page top padding 48px.
- **Radius:** `--r-sm 12px` (fields, chips), `--r-md 20px` (cards, buttons),
  `--r-lg 28px` (login card, modal). Soft throughout; no square corners.
- **Depth:** one soft warm shadow, used on raised cards and the login card only —
  `--shadow-soft: 0 1px 2px rgba(42,35,28,.05), 0 8px 24px rgba(42,35,28,.06)`.
  A second, `--shadow-pop: 0 12px 40px rgba(42,35,28,.14)`, is for the modal and
  toast. Shadows are warm-tinted, never neutral black.
- **Grid:** no multi-column grid. One 760px column, with an optional 2-up card
  hub that collapses to 1-up below 720px.

---

## 6. Components

| Component | Treatment |
|---|---|
| Primary button | `--brand` fill, `--surface` label, `--r-md`, **56px** tall everywhere, padding `16px 28px`. Hover L −5%; active L −10% with no movement. |
| Secondary button | `--surface` fill, 2px `--line-strong` border, `--ink` label, 56px. |
| Quiet button | No fill, no border, `--brand-strong` label, underline on hover, 56px hit area. |
| Destructive button | `--danger` fill, white label, 56px, never adjacent to the primary without 24px of space. |
| Icon-only button | 56×56, `aria-label` required. Used only for `Close` on the toast and modal. |
| Busy button | `Sending…` with a 20px spinner, `aria-busy="true"`, width locked. |
| Field | 56px tall, `--surface` fill, 2px `--line-strong` border, `--r-sm`, 17px text, 16px padding. Focus: 3px `--focus` ring + 3px offset. Error: 3px `--danger` border and a 20px `⚠` before the message. |
| Label / help | Label 17px bold above; help 16px `--muted` below the label, above the field, linked with `aria-describedby`. |
| Radio / checkbox row | The whole 72px row is the label and the target: 24px control, 16px gap, title, then the option's own help sentence in `--muted`. Selected: `--brand-tint` fill and a 2px `--brand` border. |
| List row / request card | `--surface`, `--r-md`, 1px `--line`, 24px padding, 16px between cards. Four lines — reference + urgency chip, title, status + who is on it, raised by + raised — giving **188px** on the queue (see §2.3 for the band table) and 236px at 400px where the title and metadata wrap. On the dashboard and the device record the fourth line is dropped, giving **156px** (182px at 400px). Never specify this card by a single number: state which lines it holds, and the height follows. The reference is the link; the whole card is clickable through a stretched anchor. Hover: `--surface-2`, no lift. |
| Hub card | 180px, 32px duotone icon, Karla 19px title, 16px sentence, `--surface`, `--shadow-soft`. The whole card is a link. |
| Figure row | 64px, number in Fraunces 30px, the sentence beside it in Karla 17px, 1px `--line` between rows. |
| Status badge | 32px tall pill (`--r-sm` 12px), tint fill, 1px hue border, 20px duotone icon + word. |
| Urgency chip | Same pill, outline only, `--line-strong` border. |
| Timeline item | 12px `--brand` ring node (hollow circle) on a 2px `--brand-line` rail; 24px between items. |
| Alert | `--r-md` card with a 20px icon, tinted fill, 1px hue border. No coloured left bar — the icon and the heading carry it. |
| Toast | Bottom-centre, `--ink` fill, `--surface` text, `--r-md`, `--shadow-pop`, `Undo` and `Close`. `role="status"`, 8 seconds, pauses on hover/focus. |
| Modal | 520px, `--r-lg`, `--shadow-pop`, 32px padding, buttons stacked on phone. `role="dialog" aria-modal="true"`. |
| Empty state | 64px duotone icon in `--brand-line`, `<h2>`, one sentence, one 56px button, centred with 48px of air above and below. |
| Pagination | Three 56px targets, generous 16px gaps. |
| Avatar | 40px circle, `--brand-tint` fill, `--brand-strong` initials `NP`. |
| Icons | **Solar Bold Duotone**, inline SVG with `currentColor`; the duotone layer is the same path at `opacity=".32"`. 24px in navigation and rows, 32px on hub cards, 64px in empty states. |

**Status vocabulary — identical in every direction** (icon + word, never colour alone):
`New` star · `In progress` refresh-circle · `Waiting on someone` clock-circle ·
`Fixed` check-circle · `Closed` archive · `In store` box · `Issued` hand-holding ·
`In repair` wrench · `Out of service` close-circle · `Good` check-circle ·
`Needs repair` danger-triangle · `Can wait` hourglass · `Normal` flag ·
`Urgent` fire (the torch flame from the crest).

---

## 7. Charts

**None.** Parchment shows the seven dashboard figures as seven sentences and stops
there. A five-bar chart would be the most decorative thing on a page whose whole
argument is that nothing is decorative.

---

## 8. Density intent

Parchment is the **least dense** of the five, deliberately and by a clear margin.
At 1440×900 the chrome above the first request card is **460px** (73px bar + 187px
page head + 88px search + 72px filter disclosure + 40px count line and gaps), and
the card is 188px with a 16px gap — a 204px pitch — so **3 request cards start
above 900px**. The band-by-band budget is the table in §2.3; build to it, measure,
and state the measured number in the folder `README.md`.

This number was 4 in an earlier draft of this file, on a 120px card that could not
hold its own four lines. Three is the honest figure and the better one: Parchment's
whole claim is that it shows less per screen than any other direction, and at 3
against Broadsheet's 5, Signpost's 6, Workbench's 7 and Ledger's 8 the ladder is
unbroken and the spread between the least and the most dense is 5 rows.

---

## 9. States

| State | What the user sees |
|---|---|
| Default | As drawn. |
| Loading | The enhanced filter replaces the result line with `Finding requests…` and a 20px spinner inside an `aria-live="polite"` region. Nothing else is async. |
| Empty (`requests.html?demo=empty`) | Card list replaced by the empty state — 64px icon, `No requests match what you chose`, `Try clearing the filters, or search for a different word.`, `[ Clear the filters ]`. Search text and filter choices stay as the user left them. |
| Validation errors (`request-form.html?demo=errors`) | A danger alert card at the top: `We couldn't send this yet — 2 things need your attention` with links to the two fields; each field keeps its value, gets a 3px `--danger` border, `aria-invalid="true"` and its message under it. Focus moves to the alert. |
| Server error | Danger alert above the form: `We couldn't save that just now` / `Nothing you typed has been lost. Wait a moment and press "Send the request" again.` |
| Success | Toast `Request sent. We gave it the number REQ-2049.` with `Undo`; the same words also render as a success alert at the top of the page landed on. |
| Sign-in error (`login.html?demo=error`) | Danger alert inside the card, above the fields: `We couldn't sign you in` / `That username or password didn't match. Try again, or ask the office to reset it.` `nimali.p` stays in the username box; focus goes to the password box. |
| No permission (`device.html?demo=denied`) | A centred card: 48px lock icon, `You can't open this page`, `This page is for ICT staff. Ask Nimali Perera in the ICT Room, or raise a request and we will help.`, `[ + Raise a request ]`. |

---

## 10. Copy — use these words exactly

Identical to the copy block in `docs/design/directions/a.md` §10, which is the
single wording all five directions share. In full, so this file stands alone:

**Global** — wordmark `Polymath College`, sub-line `Technology Management Desk`;
navigation `Home` · `Requests` · `Devices` · `Raise a request`; utility
`Nimali Perera`, `ICT Technician`, `Design kit`, `Sign out`; skip link
`Skip to main content`.

**`login.html`** — `Welcome back` / `Sign in to the Technology Management Desk.` /
`Username` + `The name the school gave you, like nimali.p` / `Password` +
`Passwords are case sensitive.` / `Sign in` / error `We couldn't sign you in` +
`That username or password didn't match. Try again, or ask the office to reset it.` /
footer `Polymath College · Technology Management Desk`.

**`dashboard.html`** — `<h1>` `Home`; lead
`Friday 11 September 2026. Here is what needs doing today.`;
`<h2>` `What needs doing` with `6 requests open` · `2 are urgent` ·
`1 raised today` · `3 devices due back next week` · `2 devices in repair` ·
`128 devices in the register` · `34 out on loan`;
`<h2>` `Things you can do`; `<h2>` `Requests to work on` + `See all requests`;
`<h2>` `Devices to watch` + `Open the device record`.
Hub card sentences: `Tell us what is wrong and we will pick it up.` ·
`Work through the 6 open requests.` · `IT-0142, the Grade 6B laptop.` ·
`3 are due back next week.`

**`requests.html`** — `<h1>` `Requests`; lead
`Everything staff have asked us to fix. Open the ones marked urgent first.`;
`Search requests` + `Reference, words, or a person's name, e.g. projector or REQ-2048`;
filters `Status` (`All statuses` + the five) · `How urgent` (`All`, `Can wait`,
`Normal`, `Urgent`) · `Who is on it` (`Anyone`, `Nobody yet`, `Nimali Perera`,
`Ruwan Jayasuriya`); sort `Newest first`, `Most urgent first`, `Oldest first`;
`Showing 8 of 8 requests`; empty `No requests match what you chose` /
`Try clearing the filters, or search for a different word.` / `Clear the filters`.
Card field labels, visually hidden: `Reference`, `What is wrong`, `Raised by`,
`Status`, `How urgent`, `Who is on it`, `Raised`.

**`device.html`** — `<h1>` `IT-0142 — Dell Latitude 3540 laptop`; lead
`Laptop · Issued to Dilani Fernando · Grade 6B Classroom`; `<h2>`s
`Where this device is`, `What it cost and how long it is covered`,
`Requests about this device`, `What has happened to it`; buttons
`Raise a request about this device`, `Mark it returned`; modal
`Mark IT-0142 returned?` / `This puts the laptop back in the ICT Store and clears the due-back date. You can give it out again at any time.` /
`Yes, mark it returned` · `No, keep it as it is`; toast
`IT-0142 is back in the ICT Store.`

**`request-form.html`** — `<h1>` `Raise a request`; lead
`Tell us what is wrong. We will pick it up from the ICT Room.`; `<h2>`s
`About the problem`, `How soon you need it`, `Anything to show us`,
`Who is asking`; the seven fields with the labels, help text and options exactly as
listed in the task brief's Content contract; buttons `Send the request` and
`Cancel`; errors `Type a short description of the problem, for example "Projector will not turn on".`
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
| The hub card sentence | `3 are due back next week.` |

**Dates and weekdays.** Today is **Friday 11 September 2026** everywhere. Copy each
date and its weekday from the contract together, and never write a weekday that
does not match its date: REQ-2048 raised `Fri 11 Sep 2026, 8:15 am`; REQ-2047
`Thu 10 Sep 2026, 11:20 am`; REQ-2045 `Tue 8 Sep 2026, 7:35 am`; IT-0142 given out
`Tue 25 Aug 2026`, returned to the ICT Store `Fri 21 Aug 2026, 3:05 pm`, battery
replaced `Fri 12 Jun 2026, 9:30 am`, last checked `Thu 3 Sep 2026`; the history
entry for REQ-2047 is dated `Thu 10 Sep 2026, 11:20 am`.

**Sample rows** come verbatim from the Content contract in
`docs/tasks/002-design-directions.md`. Do not retype from memory; do not add a
name, room or figure that is not in that table.

---

## 11. Accessibility

- **Landmarks:** `<header>` with the top bar, `<nav aria-label="Main">` inside it,
  `<main id="main">`, `<footer>` containing `<nav aria-label="Utility">`.
- **Headings:** one `<h1>` per page matching the nav label; `<h2>` per section;
  `<h3>` only inside ui-kit specimens. No level is skipped.
- **Skip link** first in the tab order, visible on focus, pointing at `#main`.
- **The phone menu** is `<details><summary>` — a native disclosure with its own
  expanded state; no `aria-expanded` bookkeeping, no focus trap, and Escape is not
  needed because the page is not covered.
- **Form wiring:** `<label for>`; help in `<p id="…-help">` joined by
  `aria-describedby`; error `<p id="…-error">` added to the same list;
  `aria-invalid="true"` only on failed fields. `How urgent is it?` is a `<fieldset>`
  with a `<legend>`, and each option's sentence is inside its `<label>` so it is
  read with the option. The error summary is `role="alert" tabindex="-1"`, focused
  on load, and its links move focus into the fields.
- **Focus ring:** 3px `--focus` with a 3px `--surface` offset, on every focusable
  element, including inside the plum button.
- **Dialogs:** the modal traps focus, Escape closes it, focus returns to
  `Mark it returned`. After a redirect, focus is set on the `<h1>` of the page
  landed on, so the toast and the page name are both heard.
- **Touch targets:** every interactive element is 56px tall; nothing is smaller
  than 44×44; adjacent targets are 16px apart, and `Cancel` is 24px from
  `Send the request`. The only exempt targets are links inside a sentence of prose,
  which are underlined and at least 44px tall through line-height padding.
- **Colour is never alone:** icon + word on every status, condition and urgency.

---

## 12. Motion

Slow, soft, and never more than a fade or a 4px move.

- Hover / focus: 200ms `ease-out` on colour only.
- `<details>` menu and filter panel: no height animation (it would jump on
  content of unknown height); the arrow rotates 180° in 200ms.
- Toast: fade + 8px rise, 240ms `cubic-bezier(.2,.7,.3,1)`; out 180ms.
- Modal: backdrop fade 200ms, panel fade + 6px rise 240ms.
- Card hover: no lift, no scale — only the fill changes.
- Reduced motion: the standard block that sets every duration to `.01ms`,
  `animation-iteration-count: 1` and `scroll-behavior: auto`.

---

## 13. Progressive enhancement

**Plain HTML, full page load:** the top-bar navigation, the phone `<details>` menu,
the filter/sort `<form method="get">` with its own `Apply` button, the request form,
sign-out, pagination, and the modal as a `<dialog>` whose no-JavaScript fallback is
a link to a confirmation section at the foot of the page.

**`app.js` adds:** in-place filtering with the live result line, the `Apply` button
being hidden once scripting is available, toast rendering and dismissal, `?demo=`
switching, focusing the error summary, the modal focus trap, and closing the phone
menu after a link inside it is followed. Hooks are `data-*` attributes only.

---

## 14. Demo hooks

`login.html?demo=error` · `request-form.html?demo=errors` ·
`requests.html?demo=empty` · `?demo=toast` on any app page ·
`device.html?demo=denied`. Prototype-only; never carried into application templates.

---

## 15. Skills the builder should load

`clean-minimal-beige-light-mode` (its warmth and its low-contrast structure —
re-derive every colour around the crest purple, do not use its sample hexes) ·
`orange-clean-paper-saas` (layout rhythm only; the accent is plum, not orange) ·
`ui-design:spacing-system` · `ui-design:readable-measure` ·
`interaction-design:onboarding-design` (the dashboard is a hub of jobs) ·
`cognitive-accessibility:plain-language-design` ·
`inclusive-interaction:touch-target-design` · `beautiful-shadows` (warm, at the
lowest end of its range) · `solar-duotone-bold`.
