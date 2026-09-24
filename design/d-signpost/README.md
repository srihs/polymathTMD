# Direction D — Signpost

Static prototype of the Polymath College Technology Management Desk in the
**Signpost** direction. Open any page straight from the file system; nothing is
served and nothing is built. The direction brief is
`docs/design/directions/d.md`; the task brief is `docs/tasks/002-design-directions.md`.

## Concept

Signpost treats every part of the screen as a labelled, bordered thing you can
point at: 2px frames around each panel, a left rail whose items carry an icon and
its word, and controls chunky enough that nobody has to wonder whether they are a
button. It is the highest-contrast direction of the five, near-black plum ink on
white inside crisp frames, and it trades elegance for certainty on purpose.

## Pages

| File | What it is |
|---|---|
| `login.html` | Sign in — one framed panel, dead centre |
| `dashboard.html` | `Home` — seven framed figure tiles, the open requests, the devices to watch, the main actions |
| `requests.html` | `Requests` — the helpdesk queue: search, filters, sort, eight framed rows, pagination, empty state |
| `device.html` | `Devices` — the `IT-0142` record: holder, cost and cover, linked requests, dated history, the "Mark it returned" confirmation |
| `request-form.html` | `Raise a request` — the guided form in four numbered framed steps, with its error state |
| `ui-kit.html` | `Design kit` — every component in every state, the type scale, the colour table, the spacing scale, the focus ring |

The device register *list* is deliberately not prototyped (task decision D8): the
`Devices` item opens the single record, because `requests.html` already proves the
list, filter, sort, status and empty-state patterns a register would reuse.

## Fonts

Google Fonts is the only external resource.

| Family | Weights | Used for |
|---|---|---|
| **Space Grotesk** | 500, 700 | Headings (h1 34/40, h2 22/28, h3 18/26), buttons (18/24), nav tile words (13/16 on the rail, 15/18 on a phone), figure numbers (40/44, tabular), panel labels, and the **wordmark** `Polymath College` (700, 15/18, uppercase, 0.04em tracking; 11/14 on the rail) |
| **Atkinson Hyperlegible** | 400, 700 | Body 17/28, lead 19/30, row titles and form labels 18/26 bold, help and metadata 16/24, badge and chip words 15/20 bold |

Atkinson Hyperlegible was drawn for low vision: its letterforms are
distinguishable at a glance, which is the point of this direction. Nothing is set
below 13px, and 13px is used only for the four rail words (the tile's accessible
name is the same word).

## Palette

Every colour is a token in `:root` of `style.css` and is used only through
`var(--…)`. Derivation starts from the crest purple `#722A82`, which is
`hsl(289 51% 34%)`: the ink is the same hue pushed to L 10%, so the 2px frames that
cover the page read as brand rather than grey furniture; the neutrals are the same
hue at 12–16% saturation; the functional colours are set darker than usual
(L 20–36%) because they sit inside thick borders where a pale hue would look weak.

| Token | Hex | Derived from the crest |
|---|---|---|
| `--brand` | `#722A82` | The crest, unmodified |
| `--brand-strong` | `#3F1649` | Crest hue at L 22% — pressed state, link colour, text on tint |
| `--brand-tint` | `#EFE2F2` | Crest hue at L 93% — current nav tile, chosen radio tile, avatar |
| `--ink` | `#16101A` | Crest hue at S 30% L 10% — every 2px frame, all body text, the toast |
| `--muted` | `#4E4654` | Crest hue at S 12% L 34% — help text and metadata |
| `--frame-soft` | `#B8ADC0` | Crest hue at L 72% — rules **inside** an already-framed panel, the urgency chip shell, the dashed empty-state frame; never the edge of a control |
| `--bg` | `#F4F1F6` | Crest hue at S 14% L 96% — page canvas |
| `--surface` | `#FFFFFF` | Panels and fields |
| `--surface-2` | `#E8E3EE` | Crest hue at L 92% — hover and pressed fills, read-only fields |
| `--ok` / `--ok-tint` | `#0A5A25` / `#E2F1E6` | Fixed, Good, In store |
| `--warn` / `--warn-tint` | `#93380A` / `#F9E9DE` | Waiting on someone, In repair, Needs repair — the torch-flame orange, darkened |
| `--danger` / `--danger-tint` | `#A30F20` / `#FBE5E7` | Urgent, Out of service, errors |
| `--info` / `--info-tint` | `#0D3E9E` / `#E3EAFA` | New, Issued |
| `--focus` | `#722A82` | The 4px focus ring on light surfaces |
| `--focus-on-dark` | `#FFFFFF` | The focus ring on the ink-filled toast, where the crest purple would reach only 2.11:1 |

**Where the crest purple is on every page:** the filled `Raise a request` tile in
the rail (and in the phone grid), the primary button, the current-item bar and
tint on the current nav tile, the counter badge on `Requests`, the timeline
nodes, the empty state icon, and the focus ring.

### Contrast ratios (WCAG 2.x, computed from the token values)

| Pair | Ratio | Needs | Result |
|---|---|---|---|
| `--ink` on `--surface` (body text; also the 2px frame as a non-text edge) | 18.70:1 | 4.5 / 3.0 | pass |
| `--ink` on `--bg` | 16.70:1 | 4.5 | pass |
| `--ink` on `--brand-tint` | 14.99:1 | 4.5 | pass |
| `--ink` on `--surface-2` | 14.83:1 | 4.5 | pass |
| `--muted` on `--surface` | 9.02:1 | 4.5 | pass |
| `--muted` on `--bg` | 8.06:1 | 4.5 | pass |
| `--muted` on `--surface-2` (the `Closed` badge) | 7.15:1 | 4.5 | pass |
| `--surface` on `--brand` (primary button, primary tile) | 8.86:1 | 4.5 | pass |
| `--brand` on `--surface` | 8.86:1 | 4.5 | pass |
| `--brand` on `--bg` | 7.92:1 | 4.5 | pass |
| `--brand` on `--brand-tint` (`In progress` badge, chosen radio frame) | 7.10:1 | 4.5 | pass |
| `--brand-strong` on `--brand-tint` (avatar) | 11.83:1 | 4.5 | pass |
| `--brand-strong` on `--surface-2` (link hover) | 11.71:1 | 4.5 | pass |
| `--surface` on `--brand-strong` (pressed primary) | 14.76:1 | 4.5 | pass |
| `--ok` on `--surface` | 8.39:1 | 4.5 | pass |
| `--ok` on `--ok-tint` | 7.18:1 | 4.5 | pass |
| `--warn` on `--surface` | 7.47:1 | 4.5 | pass |
| `--warn` on `--warn-tint` | 6.31:1 | 4.5 | pass |
| `--danger` on `--surface` | 7.94:1 | 4.5 | pass |
| `--danger` on `--danger-tint` | 6.60:1 | 4.5 | pass |
| `--surface` on `--danger` (destructive button) | 7.94:1 | 4.5 | pass |
| `--info` on `--surface` | 9.55:1 | 4.5 | pass |
| `--info` on `--info-tint` | 7.92:1 | 4.5 | pass |
| `--ink` on `--ok-tint` / `--warn-tint` / `--danger-tint` / `--info-tint` (alert body text) | 15.99 / 15.79 / 15.55 / 15.51:1 | 4.5 | pass |
| `--focus` on `--bg` | 7.92:1 | 3.0 | pass |
| `--focus` on `--surface` | 8.86:1 | 3.0 | pass |
| `--focus` on `--brand-tint` | 7.10:1 | 3.0 | pass |
| `--focus-on-dark` on `--ink` (toast) | 18.70:1 | 3.0 | pass |
| `--frame-soft` on `--surface` | 2.15:1 | — | not a control edge, so no requirement; listed for completeness |

No control border uses `--frame-soft`: fields, buttons, tiles, rows and panels are
all edged in `--ink` (18.70:1), so nothing needed darkening.

## Why it suits non-technical school staff

A school has a shared staffroom machine with a smeared screen, a projector-lit
office, and colleagues who were told once, in July, how the system works. Signpost
is built for that. Nothing is a floating card that might or might not be
pressable: every button has a 2px edge and a hard shadow, and pressing it visibly
moves it 2px, so a teacher who taps `Send the request` on the staffroom tablet
gets a physical answer that it registered. No meaning is carried by a tint alone:
`Urgent` is a flame and the word, `In repair` is a tool and the word, so Anoma in
the Admin Office can read the queue in greyscale on the old office monitor. Every
navigation item says its name next to its picture, on the rail and in the phone
grid, so there is never a mystery icon to decode and never a menu to find. The
form is four numbered framed steps on one page, so a Grade 6 teacher who is
interrupted mid-request can see at a glance where she was. Labels are 18px bold
and body text is 17px Atkinson Hyperlegible, which stays readable at the far end
of a lab bench. The corner brackets and 2px borders are not decoration: they draw
the boundary of each region so a person who is scanning, not reading, can see
where one thing stops and the next begins.

## Navigation model

**Desktop (1024px and wider): a persistent left vertical nav.** It is a **96px
rail**, ungrouped, full height and never collapsible: crest and wordmark at the
top, then four bordered tiles, each with the 28px icon stacked over its word —
`Home`, `Requests` (with a live `6` counter badge in the tile's top-right corner;
the link's name reads "Requests, 6 open"), `Devices`, `Raise a request` — the
last one filled crest purple, the only filled tile, so the action reads as the
action. The current tile has a 4px purple bar on its left edge, a tinted fill and
a bold word (three signals, none of them colour alone) and carries
`aria-current="page"`. The bottom of the rail holds the utility block: the `NP`
avatar tile, `Design kit`, and `Sign out` (a POST form). Content sits in framed
panels on a 12-column grid, 1200px wide at most. A left vertical nav is not
unique to this direction: Ledger also uses one, and both carry a count on
Requests. What separates the two is width (Ledger 248px, Signpost 96px), grouping
(Ledger's items sit under headings; Signpost's are ungrouped), item shape (a text
row versus a bordered icon-over-word tile) and framing (Signpost's content is in
2px framed panels).

**Phone (below 1024px): an always-visible 2×2 framed nav grid, docked under the
header — nothing to open.** The rail becomes a 64px header (crest chip and
wordmark) with the 2×2 grid of framed nav tiles beneath it, 72px tall, each an
icon and its word, with `Raise a request` filled purple in the bottom-right corner
nearest a right thumb. There is no menu, drawer or sheet, and therefore no state
to get stuck in; this phone mechanism is unique among the five directions. A slim
utility strip (`NP`, `Design kit`, `Sign out`) sits under the grid. The grid
scrolls away with the page; a 64px `Raise a request` button (secondary, so the
purple fill stays on the grid tile and the page's own primary action) repeats at
the foot of every page.

**With JavaScript off:** nothing changes. The rail and the grid are the same four
links restyled; the queue's filter form is a plain `<form method="get">` with its
own `Apply` button (hidden only once scripting is available); the phone filter
disclosure is a `<details>` that starts open without script; the request form
submits; sign out submits; the "Mark it returned" link goes to a confirmation
section at the foot of the device page instead of opening the `<dialog>`.

## Density

Medium: big targets, no wasted column. At 1440×900, the chrome above the first
request row is 390px and rows are 84px with a 12px gap, so **six request rows
start above the 900px fold** (row tops at 390, 486, 582, 678, 774 and 870px).

## Components

2px `--ink` frames at 14px radius with a 3px hard offset shadow (no blur anywhere);
18px L-brackets inset in the corners of every major panel; panel labels sitting
astride the top edge; 56px fields and buttons (64px on a phone); 72px framed radio
tiles that gain a 3px purple frame, a tint and a check mark when chosen; 32px
status badges with a 2px border in the functional hue, icon plus word; urgency
chips in the same shell with a soft border so status stays dominant; a dashed
frame only for the empty state; a 4px focus ring with a 2px offset. All of it is
in `ui-kit.html`.

**Icons** are Solar Outline, inlined once per page as an `<svg>` of `<symbol>`s
and placed with `<use>`, every `fill` in `currentColor`. Two mappings to note:
Solar has no wrench, so `In repair` uses Solar's `settings` gear (same family,
same weight, rather than a foreign icon); `Issued` uses Solar's `hand-shake`
(the hand-over) for the "hand-holding" slot.

## Skills used

Designer (`tmd-ui-designer`): `ux-strategy:information-architecture`,
`ui-design:design-screen`, `ui-design:visual-hierarchy`, `ui-design:type-system`,
`ui-design:color-palette`, `interaction-design:state-machine`,
`interaction-design:form-design`, `cognitive-accessibility:plain-language-design`,
`accessible-content:heading-structure`.

Builder (`tmd-frontend`): `framed-grid-layout` (parent grid, single line weight,
L-bracket technique, re-derived around the crest purple),
`high-contrast-skeuomorphic-clean` (the tactile press and layered-surface
thinking, inverted to light mode), `corner-diagonals`, `container-lines`,
`inclusive-interaction:touch-target-design`, `ui-design:law-of-common-region`,
`ui-design:von-restorff-effect` (the one filled purple tile),
`cognitive-accessibility:plain-language-design`, `accessible-content:form-labelling`.
Icon family: **Solar Outline** (Iconify `solar:*-outline`), the weight d.md
specifies; the preloaded Solar icon skill was consulted for the family's usage
rules (consistent sizes, icon always paired with a word) rather than for its
Duotone Bold weight.

## Demo hooks

These query strings switch a page into a state so it can be seen without a
server. **They are prototype-only and are never carried into `templates/`.**

| URL | State |
|---|---|
| `login.html?demo=error` | Sign-in error: the alert, `nimali.p` kept in the username box, both fields marked invalid, focus in the password box |
| `request-form.html?demo=errors` | Two validation errors with everything the user typed kept; the summary receives focus and its links move focus to the fields |
| `requests.html?demo=empty` | The empty state, with the filter choices that produced it (`Fixed` + `Nobody yet`) still showing |
| `dashboard.html?demo=toast`, `requests.html?demo=toast`, `ui-kit.html?demo=toast` | Success toast `Request sent. We gave it the number REQ-2049.` with `Undo`, plus the same sentence as a success alert on the page, and focus on the `<h1>` |
| `device.html?demo=toast` | Success toast `IT-0142 is back in the ICT Store.` with the matching alert |
| `device.html?demo=denied` | No permission: the heading and lead change, the record is replaced by the lock panel with a `Raise a request` button; the rail and grid stay |

Submitting the request form or the "Mark it returned" confirmation navigates with
`demo=toast`, so the success state is reachable by actually using the pages.

## Accessibility notes

- One `<h1>` per page, wording matched to the nav label; `<h2>` per panel (the
  panel's visible label *is* the `<h2>`); `<h3>` only inside `ui-kit.html`.
- Landmarks: `<header>`, `<nav aria-label="Main">`, `<main id="main">`,
  `<nav aria-label="Utility">`, `<footer>`, `role="search"` on the queue form. The
  skip link is the first focusable element on every page.
- Every field has a visible `<label for>`; help text and error text are linked
  with `aria-describedby` (help first); `aria-invalid="true"` only on failed
  fields; the urgency radios are a `<fieldset>` with a `<legend>`. The two
  form selects open on an empty-value prompt, `Choose a device` and
  `Choose a room`, so a missed choice can be reported as an error.
- Unassigned requests always read `Nobody yet`; the empty list reads
  `Showing 0 of 8 requests`. Dates follow the task brief's "Dates and weekdays"
  block (today is Friday 11 September 2026).
- Touch targets: tiles 72px tall on a phone, buttons 64px, fields 56px, rows
  132px, pagination 56px. **Exemption:** the 24px radio and checkbox inputs sit
  inside 72px framed `<label>` tiles, and the whole tile is the pointer target.
- Badge and chip words are 15px bold by the direction's type scale; all prose,
  labels, help and metadata are 16px or larger.
- Motion is short and mechanical (90–180ms) and the standard reduced-motion block
  removes it; the press state then changes the shadow only.
- Every frame is a real `border`, so Windows High Contrast mode keeps the layout.

## Screenshots

`screenshots/` holds the fifteen canonical full-page captures of the delivered HTML, taken with the web fonts loaded: `desktop-*.png` at 1440×900 and `mobile-*.png` at 400×844 for the six pages, plus the state captures `desktop-login--error.png`, `desktop-request-form--errors.png` and `desktop-requests--empty.png` at 1440×900.


## Files

`login.html` · `dashboard.html` · `requests.html` · `device.html` ·
`request-form.html` · `ui-kit.html` · `style.css` (eight numbered sections: tokens,
base and reset, icons, app shell and navigation, components, page-specific,
responsive, reduced motion and print) · `app.js` (one IIFE bound to `data-*`
hooks) · `assets/crest.png`, `assets/crest-chip.png`, `assets/favicon-32.png`
(binary copies of the crest cut-outs, never recoloured, filtered or stretched) ·
`screenshots/`.
