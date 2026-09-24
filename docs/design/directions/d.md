`design/d-signpost/`

# Direction D — Signpost

**Concept.** Signpost treats every part of the screen as a labelled, bordered thing
you can point at: 2px frames around each panel, a left rail whose items carry an
icon **and** its word, and controls chunky enough that nobody has to wonder whether
they are a button. It is the highest-contrast direction of the five — near-black
plum ink on white inside crisp frames — and it trades elegance for certainty on
purpose.

**Who it suits.** A school has a shared staffroom machine with a smeared screen, a
projector-lit office, and colleagues who have been told once, in July, how the
system works. Signpost is built for that: nothing is a floating card that might or
might not be pressable, no meaning is carried by a tint, every navigation item says
its name next to its picture, and every target is at least 56px. The corner
brackets and 2px borders are not decoration — they draw the boundary of each region
so a person who is scanning, not reading, can see where one thing stops and the
next begins (Law of Common Region, applied literally). Pressing a button moves it
2px and collapses its hard shadow, so a tap gives an unmistakable physical answer.

---

## 1. Navigation model

**Desktop (≥1024px): a narrow left rail, icon and word, beside framed content panels.**

- 96px rail, full height, `--surface` fill, 2px `--ink` border on its right edge
  only. Not collapsible — the direction's rule is that nothing hides.
- Top of the rail: the crest at 44px, with `Polymath College` beneath it in Space
  Grotesk 11px on two lines. (The crest is never scaled below 28px and carries no
  filter, blend or opacity.)
- Four rail items, each a 96×88 framed tile: 28px outline icon over its word at
  13px, centred. `Home`, `Requests` (with a `6` counter badge in the top-right
  corner of the tile), `Devices`, `Raise a request`. The last tile is filled
  `--brand` with white content, so the action reads as the action even at 96px wide.
- Bottom of the rail: a 44px `NP` initials tile linking to the utility block, the
  `Design kit` tile, and a `Sign out` tile inside a POST form.
- Current item: `aria-current="page"`, a 4px `--brand` bar down the tile's left
  edge, `--brand-tint` fill and the word in bold. Three signals, none of them
  colour alone.
- Content: framed panels on a 12-column grid, 20px gutters, 1200px max, each panel a
  2px `--ink` border with `--corner` L-brackets at its four corners and a 3px hard
  offset shadow (no blur).

**Phone (<1024px): an always-visible 2×2 framed navigation grid under the header.
There is no menu to open.**

- 64px header: crest chip 32px, `Polymath College`, and a 56px `Sign out` button.
- Directly beneath it, a 2×2 grid of framed nav tiles, each 100% ÷ 2 wide and 72px
  tall, with a 28px icon and the word: `Home` · `Requests (6)` · `Devices` ·
  `Raise a request`. The `Raise a request` tile is filled `--brand` and sits
  bottom-right — the corner nearest a right thumb. The grid scrolls away with the
  page; a 64px `Raise a request` button repeats at the foot of every page so it is
  never more than a scroll-to-bottom away.
- Nothing about this is scripted: the grid is four links in a CSS grid. There is no
  menu, no drawer, no sheet, and therefore no state to get stuck in.

**With JavaScript off.** Everything above is static markup; no navigation mechanism
in this direction needs a script at any width.

---

## 2. Wireframes

### 2.1 `dashboard.html` — desktop 1440

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ [skip to main content]                                                               │
├────────┬─────────────────────────────────────────────────────────────────────────────┤
│  ▣     │ ┌─ ─────────────────────────────────────────────────────────────────── ─┐   │
│Polymath│ ⌐                                                                       ¬   │
│College │ │ Home                                            Friday 11 Sep 2026    │   │
│        │ │ Friday 11 September 2026. Here is what needs doing today.             │   │
│┌──────┐│ ⌊                                                                       ⌋   │
││ ⌂    ││ └─ ─────────────────────────────────────────────────────────────────── ─┘   │
││ Home ││                                                                             │
│└──────┘│ What needs doing                                                            │
│▌┌─────┐│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   framed tiles, 2px border, │
│ │ ◇  6││ ⌐         ¬ ⌐         ¬ ⌐         ¬ ⌐         ¬   3px hard shadow           │
│ │Requ.││ │   6     │ │   2  ⚑  │ │   1     │ │   3     │                             │
│ └─────┘│ │requests │ │are      │ │raised   │ │devices  │                             │
│ ┌─────┐│ │open     │ │urgent   │ │today    │ │due back │                             │
│ │ ▤   ││ ⌊         ⌋ ⌊         ⌋ ⌊         ⌋ ⌊ this wk ⌋                             │
│ │Devi.││ └─────────┘ └─────────┘ └─────────┘ └─────────┘                             │
│ └─────┘│ ┌─────────┐ ┌─────────┐ ┌─────────┐                                         │
│ ┌─────┐│ │   2 🔧  │ │  128    │ │   34    │                                         │
│ │  +  ││ │devices  │ │devices  │ │out on   │                                         │
│ │Raise││ │in repair│ │in the   │ │loan     │                                         │
│ │a req││ │         │ │register │ │         │                                         │
│ └─────┘│ └─────────┘ └─────────┘ └─────────┘                                         │
│        │                                                                             │
│        │ ┌─ Requests to work on ──────────────────────┐ ┌─ Devices to watch ───────┐ │
│        │ ⌐                                            ¬ ⌐                          ¬ │
│        │ │ REQ-2048  ⚑ Urgent      ↻ In progress      │ │ IT-0087 Epson EB-X51     │ │
│        │ │ Projector in Lab 2 shows a blue screen     │ │ 🔧 In repair             │ │
│        │ │ ─────────────────────────────────────────  │ │ ──────────────────────── │ │
│        │ │ REQ-2047  ⚑ Normal      ★ New              │ │ IT-0056 HP LaserJet      │ │
│        │ │ Laptop will not connect to the staff Wi-Fi │ │ 🔧 In repair             │ │
│        │ │ ─────────────────────────────────────────  │ │ ──────────────────────── │ │
│        │ │ REQ-2046  ⚑ Normal      ◷ Waiting on someone│ │ IT-0142 Dell Latitude   │ │
│        │ │ Printer jams on every second page          │ │ ✋ Due Mon 21 Sep 2026    │ │
│        │ │ ─────────────────────────────────────────  │ │                          │ │
│        │ │ REQ-2045  ⚑ Can wait    ★ New              │ │ [ Open the device        │ │
│        │ │ Tablet needed for the Grade 5 reading class│ │   record ]               │ │
│        │ ⌊ [ See all requests ]                       ⌋ ⌊                          ⌋ │
│        │ └────────────────────────────────────────────┘ └──────────────────────────┘ │
│        │                                                                             │
│        │ ┌─ Things you can do ─────────────────────────────────────────────────────┐ │
│        │ │ [ + Raise a request ]  [ Go to the requests queue ]  [ Open the device  │ │
│        │ │                                                        record ]         │ │
│        │ └─────────────────────────────────────────────────────────────────────────┘ │
│ ───────│                                                                             │
│ NP     │                                                                             │
│ Design │                                                                             │
│ kit    │                                                                             │
│[Sign   │                                                                             │
│  out]  │                                                                             │
└────────┴─────────────────────────────────────────────────────────────────────────────┘
```

`⌐ ¬ ⌊ ⌋` mark the 18px L-brackets at each panel corner. Signpost shows **no chart**
— the seven figures are seven framed tiles, which is the same information in the
same visual language as everything else on the page.

### 2.2 `dashboard.html` — phone 400

```
┌──────────────────────────────────────┐
│ [skip to main content]               │
│ ▣ Polymath College      [ Sign out ] │  64px
├──────────────────────────────────────┤
│ ┌────────────────┐┌────────────────┐ │
│ │ ⌂              ││ ◇          (6) │ │  72px nav tiles, always visible,
│ │ Home           ││ Requests       │ │  2px borders, 2px gap
│ └────────────────┘└────────────────┘ │
│ ┌────────────────┐┌────────────────┐ │
│ │ ▤              ││ +              │ │
│ │ Devices        ││ Raise a request│ │  filled --brand, bottom-right
│ └────────────────┘└────────────────┘ │
├──────────────────────────────────────┤
│ ┌──────────────────────────────────┐ │
│ │ Home                             │ │  framed page-head panel
│ │ Friday 11 September 2026. Here   │ │
│ │ is what needs doing today.       │ │
│ └──────────────────────────────────┘ │
│ What needs doing                     │  h2 22px
│ ┌───────────────┐┌─────────────────┐ │
│ │  6            ││  2          ⚑   │ │  100px framed tiles, 2-up
│ │  requests open││  are urgent     │ │
│ └───────────────┘└─────────────────┘ │
│ ┌───────────────┐┌─────────────────┐ │
│ │  1            ││  3              │ │
│ │  raised today ││  devices due    │ │
│ │               ││  back next week │ │
│ └───────────────┘└─────────────────┘ │
│ ┌───────────────┐┌─────────────────┐ │
│ │  2        🔧  ││ 128             │ │
│ │  devices in   ││ devices in the  │ │
│ │  repair       ││ register        │ │
│ └───────────────┘└─────────────────┘ │
│ ┌──────────────────────────────────┐ │
│ │ 34  out on loan                  │ │
│ └──────────────────────────────────┘ │
│ ┌─ Requests to work on ────────────┐ │
│ │ REQ-2048        ⚑ Urgent         │ │  framed panel, ruled inside
│ │ Projector in Lab 2 shows a blue  │ │
│ │ screen                           │ │
│ │ ↻ In progress                    │ │
│ │ ──────────────────────────────── │ │
│ │ … three more …                   │ │
│ │ [ See all requests           ]   │ │
│ └──────────────────────────────────┘ │
│ ┌─ Devices to watch ───────────────┐ │
│ │ … three rows …                   │ │
│ │ [ Open the device record     ]   │ │
│ └──────────────────────────────────┘ │
│ [ + Raise a request              ]   │  64px, repeated at the foot
│ ──────────────────────────────────── │
│ Nimali Perera · ICT Technician       │
│ Design kit                           │
└──────────────────────────────────────┘
```

### 2.3 `requests.html` — desktop 1440

```
│  (rail) │ ┌─ ────────────────────────────────────────────────────────────────── ─┐   │
│         │ │ Requests                                                             │   │
│         │ │ Everything staff have asked us to fix. Open the ones marked urgent   │   │
│         │ │ first.                                                               │   │
│         │ └──────────────────────────────────────────────────────────────────────┘   │
│         │ ┌─ Find a request ────────────────────────────────────────────────────┐    │
│         │ │ Search requests                                                     │    │
│         │ │ [ Reference, words, or a person's name, e.g. projector or REQ-2048 ]│    │  56px
│         │ │ Status              How urgent          Who is on it                │    │
│         │ │ [ All statuses  ⌄ ] [ All          ⌄ ]  [ Anyone           ⌄ ]      │    │  56px
│         │ │ Sort [ Newest first ⌄ ]                    [ Clear the filters ]    │    │
│         │ └─────────────────────────────────────────────────────────────────────┘    │
│         │ Showing 8 of 8 requests                                                    │
│         │ ┌──────────────────────────────────────────────────────────────────────┐   │
│         │ │ REQ-2048  ⚑ Urgent   ↻ In progress                                   │   │  88px framed
│         │ │ Projector in Lab 2 shows a blue screen                               │   │  row + 12px gap
│         │ │ Suresh Kumara · Nimali Perera · Fri 11 Sep 2026, 8:15 am             │   │
│         │ └──────────────────────────────────────────────────────────────────────┘   │
│         │ ┌──────────────────────────────────────────────────────────────────────┐   │
│         │ │ REQ-2047  ⚑ Normal   ★ New                                           │   │
│         │ │ Laptop will not connect to the staff Wi-Fi                           │   │
│         │ │ Dilani Fernando · Nobody yet · Thu 10 Sep 2026, 11:20 am             │   │
│         │ └──────────────────────────────────────────────────────────────────────┘   │
│         │ … six more, each its own frame …                                           │
│         │ [ ‹ Previous ]   1   [ Next › ]                                            │
```

Every request is its own frame. There is no table and no zebra striping in
Signpost: a row is a region with a border, which is the whole idea.

### 2.4 `requests.html` — phone 400

```
┌──────────────────────────────────────┐
│ ▣ Polymath College      [ Sign out ] │
│ ┌──────────┐┌──────────┐             │
│ │⌂ Home    ││◇ Requests│             │  the same 2×2 grid, always there
│ └──────────┘└──────────┘             │
│ ┌──────────┐┌──────────┐             │
│ │▤ Devices ││+ Raise a │             │
│ └──────────┘└ request ─┘             │
├──────────────────────────────────────┤
│ ┌──────────────────────────────────┐ │
│ │ Requests                         │ │
│ │ Everything staff have asked us   │ │
│ │ to fix. Open the ones marked     │ │
│ │ urgent first.                    │ │
│ └──────────────────────────────────┘ │
│ ┌─ Find a request ─────────────────┐ │
│ │ Search requests                  │ │
│ │ [ Reference, words, or a person's│ │  56px
│ │ ▸ Filter and sort                │ │  56px <details>
│ └──────────────────────────────────┘ │
│ Showing 8 of 8 requests              │
│ ┌──────────────────────────────────┐ │
│ │ REQ-2048          ⚑ Urgent       │ │  132px framed row
│ │ Projector in Lab 2 shows a blue  │ │
│ │ screen                           │ │
│ │ ↻ In progress                    │ │
│ │ Suresh Kumara                    │ │
│ │ Fri 11 Sep 2026, 8:15 am         │ │
│ └──────────────────────────────────┘ │
│ … seven more …                       │
│ [ ‹ Previous ]  1  [ Next › ]        │
│ [ + Raise a request              ]   │
└──────────────────────────────────────┘
```

### 2.5 `device.html` — desktop / phone

```
DESKTOP                                              PHONE
│(rail)│ ┌─ ───────────────────────────────────┐    ┌──────────────────────┐
│      │ │ IT-0142 — Dell Latitude 3540 laptop │    │ ▣ Polymath  [Sign out]│
│      │ │ Laptop · Issued to Dilani Fernando ·│    │ ┌───────┐┌──────────┐│
│      │ │ Grade 6B Classroom                  │    │ │⌂ Home ││◇ Requests││
│      │ │ [ ✋ Issued ]  [ ✔ Good ]            │    │ └───────┘└──────────┘│
│      │ │ [ + Raise a request about this      │    │ ┌───────┐┌──────────┐│
│      │ │   device ]   [ Mark it returned ]   │    │ │▤ Devi.││+ Raise a ││
│      │ └─────────────────────────────────────┘    │ └───────┘└ request ─┘│
│      │ ┌─ Where this ──┐ ┌─ What it cost and ──┐  ├──────────────────────┤
│      │ │ device is     │ │ how long it is      │  │ ┌──────────────────┐ │
│      │ │ Who has it    │ │ covered             │  │ │ IT-0142 — Dell   │ │
│      │ │  Dilani F.    │ │ Value  Rs 285,000   │  │ │ Latitude 3540    │ │
│      │ │ Where         │ │ Bought 14 Feb 2024  │  │ │ laptop           │ │
│      │ │  Grade 6B     │ │ Warranty            │  │ │ Laptop · Issued  │ │
│      │ │  Classroom    │ │  13 Feb 2027        │  │ │ to Dilani F. ·   │ │
│      │ │ Given out     │ │ Serial              │  │ │ Grade 6B Class.  │ │
│      │ │  Tue 25 Aug   │ │  5CG4113XYZ         │  │ │ [✋ Issued][✔Good]│ │
│      │ │ Due back      │ │                     │  │ │ [ + Raise a      │ │
│      │ │  Mon 21 Sep   │ │                     │  │ │   request about  │ │
│      │ │ Last checked  │ │                     │  │ │   this device ]  │ │
│      │ │  Thu 3 Sep    │ │                     │  │ │ [ Mark it        │ │
│      │ └───────────────┘ └─────────────────────┘  │ │   returned ]     │ │
│      │ ┌─ Requests about this device ──────────┐  │ └──────────────────┘ │
│      │ │ REQ-2047  ★ New   Laptop will not …   │  │ ┌─ Where this ─────┐ │
│      │ │ ──────────────────────────────────────│  │ │ …5 rows…         │ │
│      │ │ REQ-1902  ⛁ Closed  Battery replaced… │  │ └──────────────────┘ │
│      │ └───────────────────────────────────────┘  │ ┌─ What it cost ───┐ │
│      │ ┌─ What has happened to it ─────────────┐  │ │ …4 rows…         │ │
│      │ │ ■ Thu 10 Sep 2026, 11:20 am           │  │ └──────────────────┘ │
│      │ │ │ Dilani Fernando                     │  │ ┌─ Requests about ─┐ │
│      │ │ │ Raised REQ-2047 — will not connect  │  │ │ …2 rows…         │ │
│      │ │ │ to the staff Wi-Fi                  │  │ └──────────────────┘ │
│      │ │ ■ … four more, newest first           │  │ ┌─ What has ───────┐ │
│      │ └───────────────────────────────────────┘  │ │ …5 entries…      │ │
                                                    │ └──────────────────┘ │
                                                    │ [ + Raise a request ]│
                                                    └──────────────────────┘
```

### 2.6 `request-form.html` — desktop / phone

Each `<h2>` section is its own framed panel, so the form reads as four steps that
happen to be on one page — a shape that helps people who lose their place.

```
│(rail)│ ┌─ ─────────────────────────────────────────┐
│      │ │ Raise a request                           │
│      │ │ Tell us what is wrong. We will pick it up │
│      │ │ from the ICT Room.                        │
│      │ └───────────────────────────────────────────┘
│      │ ┌─ ⚠ We couldn't send this yet — 2 things ─┐   4px danger frame,
│      │ │   need your attention                    │   danger-tint fill
│      │ │   1. What is wrong?                      │
│      │ │   2. Where is it?                        │
│      │ └──────────────────────────────────────────┘
│      │ ┌─ 1. About the problem ────────────────────┐  600px panel
│      │ │ What is it about?                         │
│      │ │ Pick the device, or choose "Not about a   │
│      │ │ particular device".                       │
│      │ │ [ IT-0142 — Dell Latitude 3540 laptop ⌄ ] │  56px, 2px border
│      │ │ What is wrong?                            │
│      │ │ One short line, for example "Projector    │
│      │ │ will not turn on".                        │
│      │ │ [                                       ] │  3px danger border
│      │ │ ⚠ Type a short description of the problem,│
│      │ │   for example "Projector will not turn on"│
│      │ │ Tell us more                              │
│      │ │ [                                       ] │
│      │ │ Where is it?                              │
│      │ │ [ Choose a room                       ⌄ ] │
│      │ └───────────────────────────────────────────┘
│      │ ┌─ 2. How soon you need it ─────────────────┐
│      │ │ ┌───────────────────────────────────────┐ │  each option is its own
│      │ │ │ ( ) Can wait                          │ │  72px framed tile
│      │ │ │     It can wait until next week.      │ │
│      │ │ └───────────────────────────────────────┘ │
│      │ │ ┌───────────────────────────────────────┐ │
│      │ │ │ (•) Normal                            │ │  selected: 3px --brand
│      │ │ │     I need it in the next day or two. │ │  frame + --brand-tint
│      │ │ └───────────────────────────────────────┘ │
│      │ │ ┌───────────────────────────────────────┐ │
│      │ │ │ ( ) Urgent                            │ │
│      │ │ │     A class or the office is stopped  │ │
│      │ │ │     right now.                        │ │
│      │ │ └───────────────────────────────────────┘ │
│      │ └───────────────────────────────────────────┘
│      │ ┌─ 3. Anything to show us ──┐ ┌─ 4. Who is ─┐
│      │ │ Add a photo               │ │  asking     │
│      │ │ Optional. A photo of the  │ │ Your name   │
│      │ │ screen or the error helps │ │ We will     │
│      │ │ us a lot.                 │ │ reply to    │
│      │ │ [ Choose a photo ]        │ │ you.        │
│      │ │  No file chosen           │ │ Nimali      │
│      │ └───────────────────────────┘ │ Perera      │
│      │                               │ (nimali.p)  │
│      │                               └─────────────┘
│      │ [ Send the request ]        [ Cancel ]
```

On phone every panel is full width, the two short panels stack, and the buttons are
64px full-width with `Send the request` first and 20px between them.

### 2.7 `login.html` and `ui-kit.html`

- **`login.html`** — one 440px framed panel, 3px `--ink` border, 6px hard offset
  shadow, dead centre on the `--bg`. Crest 88px above `Welcome back`. The two fields
  are 56px with 2px borders; `Sign in` is a 64px full-width `--brand` button. The
  footer line sits below the frame. Phone: the frame goes full width minus 16px
  gutters; crest 64px; nothing else changes.
- **`ui-kit.html`** — the rail, then one framed panel per component family with its
  name as the frame's label, each specimen on a 20px grid. Because this direction's
  whole argument is the frame, the kit shows the frame at its three weights (2px
  panel, 3px emphasis, 4px alert) side by side. The colour table gives swatch,
  token, hex, checked-against pair and ratio.

---

## 3. Type

Google Fonts: `Space Grotesk` (500, 700) · `Atkinson Hyperlegible` (400, 700).

Atkinson Hyperlegible was drawn for low vision: its letterforms are
distinguishable at a glance, which is the point of this direction. Space Grotesk's
flat terminals and wide counters keep the headings sitting square inside the frames.

| Role | Family / weight | Size / line-height | Notes |
|---|---|---|---|
| Wordmark `Polymath College` | Space Grotesk 700 | 15/18, `.04em`, uppercase | Rail, header, login |
| h1 | Space Grotesk 700 | 34/40 desktop, 28/34 phone | |
| h2 / panel label | Space Grotesk 700 | 22/28 desktop, 20/26 phone | Sits on the frame's top edge |
| h3 | Space Grotesk 500 | 18/26 | |
| Body / prose | Atkinson Hyperlegible 400 | 17/28 | |
| Lead paragraph | Atkinson Hyperlegible 400 | 19/30 | |
| Row title | Atkinson Hyperlegible 700 | 18/26 | |
| Form label | Atkinson Hyperlegible 700 | 18/26 | Larger than most directions, on purpose |
| Help text | Atkinson Hyperlegible 400 | 16/24 | |
| Button | Space Grotesk 700 | 18/24 | |
| Nav tile word | Space Grotesk 700 | 13/16 desktop rail, 15/18 phone grid | |
| Badge / chip word | Atkinson Hyperlegible 700 | 15/20 | |
| Metadata | Atkinson Hyperlegible 400 | 16/24 `--muted` | |
| Figure number | Space Grotesk 700 | 40/44, tabular numerals | |

Nothing is set below 13px, and 13px is used only for the four rail words, which are
also available as the tile's accessible name. Measure is capped at 70 characters.

---

## 4. Palette

Derivation. `#722A82` is `hsl(289, 51%, 34%)`. Signpost keeps the hue for the brand
and pushes its **ink** to `hsl(288, 30%, 10%)` — a near-black that is still the
crest's colour, so the 2px frames that cover the page read as brand, not as grey
furniture. The neutrals are the same hue at 12–16% saturation, and the functional
colours are set darker than the other four directions (L 20–36%) because they sit
inside thick borders where a pale hue would look weak.

| Token | Hex | Derivation |
|---|---|---|
| `--brand` | `#722A82` | The crest, unmodified |
| `--brand-strong` | `#3F1649` | Crest hue at L 22% — pressed state, text on tint |
| `--brand-tint` | `#EFE2F2` | Crest hue at L 93% |
| `--ink` | `#16101A` | Crest hue at S 30% L 10% — every 2px frame |
| `--muted` | `#4E4654` | Crest hue at S 12% L 34% |
| `--frame-soft` | `#B8ADC0` | Crest hue at L 72% — inner rules inside a panel |
| `--bg` | `#F4F1F6` | Crest hue at S 14% L 96% |
| `--surface` | `#FFFFFF` | Panels and fields |
| `--surface-2` | `#E8E3EE` | Crest hue at L 92% — hover and pressed fills |
| `--ok` | `#0A5A25` | Fixed, Good, In store |
| `--ok-tint` | `#E2F1E6` | |
| `--warn` | `#93380A` | Waiting on someone, In repair, Needs repair |
| `--warn-tint` | `#F9E9DE` | |
| `--danger` | `#A30F20` | Urgent, Out of service, errors |
| `--danger-tint` | `#FBE5E7` | |
| `--info` | `#0D3E9E` | New |
| `--info-tint` | `#E3EAFA` | |
| `--focus` | `#722A82` | 4px ring, thicker than the other directions |

**Contrast pairs** (expected values; recompute and print them in the folder README):

| Pair | Ratio | Needs |
|---|---|---|
| `--ink` on `--surface` | 18.7:1 | 4.5 |
| `--ink` on `--bg` | 16.8:1 | 4.5 |
| `--ink` on `--brand-tint` | 14.9:1 | 4.5 |
| `--muted` on `--surface` | 9.0:1 | 4.5 |
| `--surface` on `--brand` (primary button) | 8.9:1 | 4.5 |
| `--brand` on `--surface` | 8.9:1 | 4.5 |
| `--ink` frame on `--surface` (2px border) | 18.7:1 | 3.0 |
| `--brand-strong` on `--brand-tint` | ≥11:1 | 4.5 |
| `--ok` on `--surface` | 8.4:1 | 4.5 |
| `--warn` on `--surface` | 7.5:1 | 4.5 |
| `--danger` on `--surface` | 7.9:1 | 4.5 |
| `--info` on `--surface` | 9.5:1 | 4.5 |
| Each functional colour on its own tint | ≥5:1 | 4.5 |
| `--focus` on `--bg` | 8.4:1 | 3.0 |

`--frame-soft` (2.2:1) is used only for rules **inside** an already-framed panel,
never as the boundary of a control.

---

## 5. Space, radius, depth

- **Space, 10px base:** `--s1 10` `--s2 20` `--s3 30` `--s4 40` `--s5 60` `--s6 80`.
  Only one sub-step exists, `--s0 4`, for the gap between an icon and its word.
  Panel padding `--s2`; panel-to-panel `--s2`; section-to-section `--s4`.
- **Radius:** `--r-sm 8px` (fields, chips, tiles), `--r-md 14px` (panels, buttons),
  `--r-lg 14px` (modal — the same, because the system has only two curves). The
  frame is always drawn at the radius, so corners look cut rather than soft.
- **Depth: hard offset shadows with no blur** — `--shadow-hard: 3px 3px 0
  var(--ink)` on panels, buttons and nav tiles; `--shadow-hard-lg: 6px 6px 0
  var(--ink)` on the login frame and the modal. Pressing a button sets
  `transform: translate(2px, 2px)` and `--shadow-hard: 1px 1px 0`, so the press is
  visible without any colour change. There is no blurred shadow anywhere in this
  direction.
- **Corner brackets:** 18px L-brackets drawn with background gradients at the four
  corners of every major panel, in `--ink`, 2px thick. One size, everywhere.
- **Grid:** 12 columns, 20px gutters, 1200px max, 96px rail outside the grid, page
  gutters 20px desktop / 16px phone.

---

## 6. Components

| Component | Treatment |
|---|---|
| Primary button | `--brand` fill, white label, 2px `--ink` border, `--r-md`, `--shadow-hard`, **56px** tall (64px on phone), padding `16px 28px`. Press: translate 2px and shadow to 1px. |
| Secondary button | `--surface` fill, 2px `--ink` border, `--ink` label, same metrics and press behaviour. |
| Quiet button | No border, no shadow, `--brand-strong` label with a 2px underline; 56px hit area. |
| Destructive button | `--danger` fill, white label, 2px `--ink` border. Never within 40px of the primary. |
| Icon-only button | 56×56, 2px border, `aria-label` required; used only for the toast's and modal's `Close`. |
| Busy button | `Sending…` + 20px spinner, `aria-busy="true"`, shadow flattened to 1px to read as held down. |
| Field | 56px, `--surface`, **2px `--ink` border**, `--r-sm`, 17px text, 16px padding. Focus: 4px `--focus` ring, 2px offset. Error: 3px `--danger` border, `--danger-tint` fill, plus the `⚠` message. |
| Label / help | Label 18px bold above the field; help 16px `--muted` between label and field, `aria-describedby`. |
| Radio / checkbox | Each option is a 72px framed tile containing a 24px control, its word in 18px bold and its sentence in 16px. Selected: 3px `--brand` frame, `--brand-tint` fill and a check mark **in addition to** the radio dot. |
| Panel | 2px `--ink` border, `--r-md`, `--shadow-hard`, 20px padding, corner brackets, and a label sitting on the top edge in a `--surface` notch. |
| Request row | Its own framed panel, 88px desktop / 132px phone, with `--surface-2` fill on hover and a 4px `--brand` left edge when it is the current row. |
| Stat tile | Framed panel, 40px number, 17px sentence. The urgent tile carries the `⚑` icon and a 4px `--danger` top edge. |
| Status badge | 32px, `--r-sm` (8px — not a pill), 2px border in the functional hue, tint fill, 20px outline icon + word. |
| Urgency chip | Same shell with a `--frame-soft` border instead of a coloured one, so status stays dominant. |
| Timeline item | 12px `--brand` filled square node on a 2px `--ink` rail; each entry is a small framed block with 20px padding. |
| Alert | Framed panel with a 4px border in the functional hue and its tint as fill, a 24px icon, title in Space Grotesk 20px, body 17px. |
| Toast | Bottom-centre, `--ink` fill, `--surface` text, 2px `--surface` border, `--shadow-hard-lg`, `Undo` and `Close` as 56px buttons. `role="status"`, 8s, pauses on hover/focus. |
| Modal | 520px framed panel, `--shadow-hard-lg`, 30px padding; buttons side by side with 40px between them. `role="dialog" aria-modal="true"`. |
| Empty state | A framed panel with a dashed 2px `--frame-soft` border (the only dashed line in the system, which is what marks it as "nothing here yet"), a 56px icon, `<h2>`, one sentence and one 56px button. |
| Pagination | `‹ Previous` and `Next ›` as framed 56px buttons at the two ends, the page number between them. |
| Avatar | 44px `--r-sm` tile, 2px `--ink` border, `--brand-tint` fill, `NP` in Space Grotesk 700. |
| Icons | **Solar Outline**, 2px strokes, inline SVG, `currentColor`. 28px in nav tiles, 20px inline, 24px in alerts, 56px in empty states. Thick strokes to match the frames. |

**Status vocabulary — identical in every direction:** `New` star ·
`In progress` refresh-circle · `Waiting on someone` clock-circle ·
`Fixed` check-circle · `Closed` archive · `In store` box · `Issued` hand-holding ·
`In repair` wrench · `Out of service` close-circle · `Good` check-circle ·
`Needs repair` danger-triangle · `Can wait` hourglass · `Normal` flag ·
`Urgent` fire (the crest's torch flame). Icon **and** word, always.

---

## 7. Charts

**None.** Signpost's figures are framed tiles. A chart would introduce a second
visual language — areas of colour with no border — into a system whose whole claim
is that every region is bounded and labelled.

---

## 8. Density intent

Signpost is **medium**: big targets, but no wasted column. At 1440×900 the chrome
above the first request row is ~320px (100px page-head panel + 190px find panel +
30px count line); rows are 88px with a 12px gap, so **6 request rows start above
900px**. State this number in the folder `README.md`.

---

## 9. States

| State | What the user sees |
|---|---|
| Default | As drawn. |
| Loading | The enhanced filter replaces the count line with `Finding requests…` and a 20px spinner in an `aria-live="polite"` region; the list panel keeps its frame so the page does not reflow. |
| Empty (`requests.html?demo=empty`) | The list is replaced by the dashed-frame empty panel: `No requests match what you chose` / `Try clearing the filters, or search for a different word.` / `[ Clear the filters ]`. The find panel above keeps every choice the user made. |
| Validation errors (`request-form.html?demo=errors`) | A 4px `--danger`-framed alert panel above the first section: `We couldn't send this yet — 2 things need your attention`, with numbered links to the two fields. Each field keeps its value, gets `aria-invalid="true"`, a 3px `--danger` border and its message. Focus moves to the alert. |
| Server error | The same panel above the form: `We couldn't save that just now` / `Nothing you typed has been lost. Wait a moment and press "Send the request" again.` |
| Success | Toast `Request sent. We gave it the number REQ-2049.` with `Undo`, and the same sentence as a success-framed alert panel at the top of the page landed on. |
| Sign-in error (`login.html?demo=error`) | A 4px `--danger`-framed alert inside the login frame: `We couldn't sign you in` / `That username or password didn't match. Try again, or ask the office to reset it.` `nimali.p` stays in the username box; focus goes to the password box. |
| No permission (`device.html?demo=denied`) | A framed panel where the record would be: 56px lock icon, `You can't open this page`, `This page is for ICT staff. Ask Nimali Perera in the ICT Room, or raise a request and we will help.`, `[ + Raise a request ]`. The rail and the nav grid stay. |

---

## 10. Copy — use these words exactly

The wording is identical in all five directions. In full, so this file stands alone:

**Global** — wordmark `Polymath College`; sub-line `Technology Management Desk`;
navigation `Home` · `Requests` · `Devices` · `Raise a request`; utility
`Nimali Perera`, `ICT Technician`, `Design kit`, `Sign out`; skip link
`Skip to main content`; panel label on the queue filters `Find a request`.

**`login.html`** — `Welcome back` / `Sign in to the Technology Management Desk.` /
`Username` + `The name the school gave you, like nimali.p` / `Password` +
`Passwords are case sensitive.` / `Sign in` / `We couldn't sign you in` +
`That username or password didn't match. Try again, or ask the office to reset it.` /
`Polymath College · Technology Management Desk`.

**`dashboard.html`** — `<h1>` `Home`; lead
`Friday 11 September 2026. Here is what needs doing today.`; `<h2>`s
`What needs doing`, `Requests to work on`, `Devices to watch`,
`Things you can do`; figures worded `6 requests open` · `2 are urgent` ·
`1 raised today` · `3 devices due back next week` · `2 devices in repair` ·
`128 devices in the register` · `34 out on loan`; buttons/links
`See all requests`, `Open the device record`, `Go to the requests queue`,
`Raise a request`.

**`requests.html`** — `<h1>` `Requests`; lead
`Everything staff have asked us to fix. Open the ones marked urgent first.`;
`Search requests` + `Reference, words, or a person's name, e.g. projector or REQ-2048`;
filters `Status` (`All statuses` + the five) · `How urgent` (`All`, `Can wait`,
`Normal`, `Urgent`) · `Who is on it` (`Anyone`, `Nobody yet`, `Nimali Perera`,
`Ruwan Jayasuriya`); sort `Newest first`, `Most urgent first`, `Oldest first`;
`Showing 8 of 8 requests`; visually hidden field names `Reference`,
`What is wrong`, `Raised by`, `Status`, `How urgent`, `Who is on it`, `Raised`;
empty `No requests match what you chose` /
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
`Tell us what is wrong. We will pick it up from the ICT Room.`; panel labels
`1. About the problem`, `2. How soon you need it`, `3. Anything to show us`,
`4. Who is asking` — the `<h2>` text itself is `About the problem`,
`How soon you need it`, `Anything to show us`, `Who is asking`, with the number in
a separate span so the heading text matches the other directions; the seven fields
with labels, help text and options exactly as listed in the task brief's Content
contract; buttons `Send the request`, `Cancel`; errors
`Type a short description of the problem, for example "Projector will not turn on".`
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
`docs/tasks/002-design-directions.md`.

---

## 11. Accessibility

- **Landmarks:** `<header>` (phone header), `<nav aria-label="Main">` (rail on
  desktop, 2×2 grid on phone — one element, restyled, not two copies),
  `<main id="main">`, `<nav aria-label="Utility">`, `<footer>`.
- **Headings:** one `<h1>`; `<h2>` for each panel, and the panel's visible label
  **is** that `<h2>`, so the frame and the outline agree; `<h3>` only in ui-kit.
- **Skip link** first in the tab order, visible on focus, to `#main`.
- **Rail and grid items** are links with text, not icon-only buttons; the counter
  badge is inside the link and reads `Requests, 6 open`.
- **Form wiring:** `<label for>`; help `<p id="…-help">` then error
  `<p id="…-error">` in `aria-describedby`; `aria-invalid="true"` on failed fields;
  `<fieldset>` + `<legend>How urgent is it?</legend>` for the three framed radio
  tiles, each option's sentence inside its own `<label>`; error summary
  `role="alert" tabindex="-1"` focused on load, its links moving focus to the field.
- **Focus ring:** 4px `--focus` with a 2px `--surface` offset — the thickest of the
  five, because this direction's borders are already 2px and a thin ring would be
  lost against them. Never removed.
- **Dialogs and redirects:** the modal traps focus, Escape closes it, focus returns
  to `Mark it returned`; after a redirect focus goes to the `<h1>`.
- **Touch targets:** phone nav tiles 72px tall by ~192px wide; buttons 64px; fields
  56px; rows 132px; pagination 56px. Minimum gap between adjacent targets is 12px,
  and `Cancel` is 40px from `Send the request` because this direction's controls are
  large enough to mis-hit if crowded.
- **Colour is never alone:** icon + word for every status, condition and urgency;
  the selected radio tile changes border width and adds a check mark as well as
  colour; the pressed button moves.
- **Forced colours:** every frame is a real `border`, not a shadow or an image, so
  Windows High Contrast mode keeps the whole layout intact.

---

## 12. Motion

Physical, short and mechanical.

- Button press: `translate(2px, 2px)` with the shadow collapsing, 90ms
  `cubic-bezier(.2,0,.4,1)`. Release returns in 120ms.
- Hover: fill change only, 120ms.
- Toast: 8px rise + fade, 180ms.
- Modal: backdrop fade 120ms, panel fade 140ms with no scale.
- No page transitions, no scroll effects, no looping animation.
- Reduced motion: the standard block sets every duration to `.01ms` and
  `animation-iteration-count: 1`; the press state then changes the shadow only, with
  no translate, so the feedback survives without movement.

---

## 13. Progressive enhancement

**Plain HTML, full page load:** the rail and the phone nav grid (plain links), the
filter/sort `<form method="get">` with its own `Apply` button, the phone
`<details>` filter panel, the request form, sign-out, pagination, and the modal as a
`<dialog>` whose fallback is a link to a confirmation section at the foot of the
page.

**`app.js` adds:** in-place filtering and the live count line, hiding `Apply` once
scripting exists, toast rendering and dismissal, `?demo=` switching, focusing the
error summary, and the modal focus trap. Hooks are `data-*` attributes only.

---

## 14. Demo hooks

`login.html?demo=error` · `request-form.html?demo=errors` ·
`requests.html?demo=empty` · `?demo=toast` on any app page ·
`device.html?demo=denied`. Prototype-only; never carried into application templates.

---

## 15. Skills the builder should load

`framed-grid-layout` (its parent grid, single line weight and L-bracket technique —
re-derive the tokens around the crest purple) ·
`high-contrast-skeuomorphic-clean` (its tactile press and layered-surface thinking,
**inverted to light mode**: this direction has no dark shell) · `corner-diagonals` ·
`container-lines` · `inclusive-interaction:touch-target-design` ·
`ui-design:law-of-common-region` · `ui-design:von-restorff-effect` (the one filled
purple tile) · `cognitive-accessibility:plain-language-design` ·
`solar-duotone-bold` (use the **Outline** weight of the same family).
