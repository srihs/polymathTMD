# Direction B — Parchment

Static prototype of the Polymath College Technology Management Desk. Open any
page straight from the file system; nothing needs a server. The direction brief is
[`docs/design/directions/b.md`](../../docs/design/directions/b.md); the task brief
is [`docs/tasks/002-design-directions.md`](../../docs/tasks/002-design-directions.md).

## Concept

Parchment is the calm end of the range: one warm, unhurried column of paper with a
single job on it at a time, sized so that a teacher who opens it twice a term never
has to work out where to look. It carries the crest's purple as a quiet plum on a
parchment ground, and buys its clarity with white space rather than lines, boxes or
density.

## Pages

| File | What it is |
|---|---|
| `login.html` | Sign in — a single 440px card on the parchment ground |
| `dashboard.html` | Home — seven figures as sentences, a hub of four jobs, requests and devices to watch |
| `requests.html` | Requests — search, a `Filter and sort` disclosure, eight request cards, pagination |
| `device.html` | Devices — the `IT-0142` record, its linked requests and timeline, the confirm-return dialog |
| `request-form.html` | Raise a request — seven fields in four sections, one field per row |
| `ui-kit.html` | Design kit — every component in every state, tokens, type, contrast |

The device register list is deliberately not prototyped: `Devices` opens the
single record (brief decision D8), because `requests.html` already proves the list,
filter, sort, status and empty-state patterns a register would reuse.

## Fonts

Google Fonts, the only external resource.

| Family | Weights | Used for |
|---|---|---|
| **Fraunces** (variable, optical size axis, `SOFT` at default) | 500, 600 | h1 40/48 (32/40 on phone), h2 26/34 (24/32), h3 20/28, figure numbers 30/34 tabular, the wordmark `Polymath College` 20/24 and `Welcome back` 36/44 on sign-in |
| **Karla** | 400, 500, 600, 700 | Body 17/28, lead 19/30, card titles 19/26 bold, labels 17/24 bold, help 16/24, buttons 17/24 bold, badge words 15/20 bold, small print 15/22, the current nav item at 600 |

The wordmark `Polymath College` is set in Fraunces 600. No text is uppercase.
Prose measure is capped at 66 characters; the content column is 760px.

## Palette

Derivation from the crest. `#722A82` is hsl(289, 51%, 34%). Parchment warms the
brand two degrees to 292° for its own plum steps, then builds the paper from the
complement side: neutrals at 30–40°, a warm oat, so a purple mark sits on warm
paper the way school stationery does and the screen does not glare in a bright
classroom. Meaning hues sit at 148 (ok) · 28 (warn) · 2 (danger) · 238 (info).

| Token | Hex | Derived from the crest |
|---|---|---|
| `--brand` | `#722A82` | The crest purple, unmodified |
| `--brand-strong` | `#5A2168` | Brand hue 292° at L 30% — text on plum tints, current nav item, links |
| `--brand-hover` | `#622470` | Brand at L −5% — primary button hover |
| `--brand-active` | `#511E5C` | Brand at L −10% — primary button pressed |
| `--brand-tint` | `#F0E4F2` | Brand hue at L 94% — selected choice rows, In progress badge, avatar |
| `--brand-line` | `#C8A5CF` | Brand hue at L 78% — timeline rail (decorative only) |
| `--ink` | `#2A231C` | Warm 30° at L 16% — text |
| `--muted` | `#6B6157` | Warm 30° at L 38% — secondary text |
| `--line` | `#DCD0BC` | Warm 36° at L 84% — hairlines, never a control border |
| `--line-strong` | `#91826E` | Warm 35° at L 50% — control borders (see note) |
| `--bg` | `#F5EEE2` | Parchment: warm 38° at L 95% |
| `--surface` | `#FBF7F0` | Warm 40° at L 98% — cards, fields, top bar |
| `--surface-2` | `#EBE2D2` | Warm 38° at L 87% — hover and pressed fills, read-only fields |
| `--ok` / `--ok-tint` | `#1C6B3A` / `#E2F0E4` | Fixed, Good, In store |
| `--warn` / `--warn-tint` | `#94540E` / `#F8E9D5` | Waiting on someone, In repair, Needs repair |
| `--danger` / `--danger-tint` | `#AE2A1E` / `#F8E3DF` | Urgent, Out of service, errors |
| `--danger-hover` | `#96241A` | Destructive button hover |
| `--info` / `--info-tint` | `#33409B` / `#E6E8F6` | New, Issued |
| `--focus` | `#5A2168` | The focus ring (`--brand-strong`) |

**Note on `--line-strong`.** The direction file proposed `#9A8C79` (L 54%), which
is 3.07:1 on `--surface` but only 2.84:1 on `--bg`, and fields sit directly on the
parchment ground. As the direction file instructs for a control border under 3:1,
it was darkened one step to L 50%, `#91826E`.

### Contrast pairs

Computed with the WCAG 2 relative-luminance formula from the hex values in
`style.css` (`:root`), not estimated. Needs: 4.5:1 for text under 24px, 3:1 for
large text, meaning-bearing icons, control borders and the focus ring.

| Foreground | On | Ratio | Needs | Result |
|---|---|---|---|---|
| `--ink` | `--bg` | 13.43:1 | 4.5 | pass |
| `--ink` | `--surface` | 14.51:1 | 4.5 | pass |
| `--ink` | `--surface-2` | 12.05:1 | 4.5 | pass |
| `--muted` | `--surface` | 5.66:1 | 4.5 | pass |
| `--muted` | `--bg` | 5.24:1 | 4.5 | pass |
| `--muted` | `--surface-2` | 4.71:1 | 4.5 | pass |
| `--surface` | `--brand` (primary button label) | 8.30:1 | 4.5 | pass |
| `--brand` | `--surface` | 8.30:1 | 4.5 | pass |
| `--brand` | `--bg` | 7.69:1 | 4.5 | pass |
| `--brand` | `--bg` (64px empty-state icon) | 7.69:1 | 3.0 | pass |
| `--brand-strong` | `--brand-tint` | 9.22:1 | 4.5 | pass |
| `--brand-strong` | `--surface` | 10.62:1 | 4.5 | pass |
| `--brand-strong` | `--bg` | 9.83:1 | 4.5 | pass |
| `--line-strong` | `--surface` (field border) | 3.50:1 | 3.0 | pass |
| `--line-strong` | `--bg` (field border on the page) | 3.24:1 | 3.0 | pass |
| `--ok` | `--ok-tint` | 5.54:1 | 4.5 | pass |
| `--ok` | `--surface` | 6.12:1 | 4.5 | pass |
| `--warn` | `--warn-tint` | 4.98:1 | 4.5 | pass |
| `--warn` | `--surface` | 5.56:1 | 4.5 | pass |
| `--danger` | `--danger-tint` | 5.41:1 | 4.5 | pass |
| `--danger` | `--surface` | 6.24:1 | 4.5 | pass |
| `--danger` | `--bg` | 5.78:1 | 4.5 | pass |
| `--surface` | `--danger` (destructive button label) | 6.24:1 | 4.5 | pass |
| `--info` | `--info-tint` | 7.34:1 | 4.5 | pass |
| `--info` | `--surface` | 8.38:1 | 4.5 | pass |
| `--surface` | `--ink` (toast text) | 14.51:1 | 4.5 | pass |
| `--focus` | `--bg` | 9.83:1 | 3.0 | pass |
| `--focus` | `--surface` | 10.62:1 | 3.0 | pass |
| `--surface` | `--ink` (the ring's inner gap on a dark surface) | 14.51:1 | 3.0 | pass |

`--line` (1.43:1 on `--surface`) and `--brand-line` (2.02:1) are decoration only
and never carry a control edge or meaning.

**Where the brand colour appears on every page.** The filled plum `Raise a request`
button in the top bar (and pinned under it on phones), the current navigation
item's plum underline, the 36px crest chip beside the wordmark, every duotone
icon in navigation and on hub cards, the 64px empty-state icon, figure numbers in
`--brand-strong`, and the timeline rail. On `login.html` it is the 96px crest,
the wordmark and the
`Sign in` button. Each page has exactly one visually dominant primary action: the
plum button in the top bar on Home, Requests, Devices and the Design kit;
`Send the request` on the form (the nav button is the current item there);
`Sign in` on the sign-in page.

## Why it suits non-technical school staff

Dilani Fernando teaches Grade 6B and opens this system perhaps four times a term,
usually while a class is waiting. For her the enemy is not missing information; it
is a screen with forty things on it. Parchment puts one job on each screen, in one
column, so there is never a second place to look. Every heading is followed by a
sentence that says what to do next (`Tell us what is wrong. We will pick it up from
the ICT Room.`), and every field says what to type before she types it.

Everything she can tap is 56px tall, the whole radio row is the target, and the
whole request card is the link, so it works with a finger, a stylus, or a shaky
hand on the shared laptop in the staff room. The ground is warm parchment rather
than white, which stops the screen glaring in a classroom with the blinds up, and
body text is 17px Karla with 28px leading, which reads comfortably at arm's length.

The first screen after signing in is a menu of jobs with verbs on them, not a
report to interpret. The seven figures are sentences (`6 requests open`) instead of
a chart, so nothing needs decoding. Status is always an icon plus a word, errors say
what to do and keep what she typed, and the phone menu is a plain `Menu` button
that opens a list, with `Raise a request` pinned under the top bar so the most
common job is one thumb away without opening anything.

## Navigation model

**Desktop (900px and up).** A 72px top bar on `--surface` with a 1px rule beneath:
crest chip and wordmark on the left; `Home`, `Requests`, `Devices` as text links in
the centre with `Raise a request` as a filled plum button; `Nimali Perera` with her
avatar and a `Sign out` button on the right. The current page carries
`aria-current="page"` and a 3px plum underline. `Design kit` and a second
`Sign out` live in the footer's utility navigation. Content is one centred column,
760px wide, with 48px gutters. Nothing is ever placed in a second column.

**Phone (below 900px).** A 64px top bar with the crest chip, the page name and a
56px `Menu` button. `Menu` is the `<summary>` of a `<details>` element; open, it
pushes the page down and lists the four labels as 56px rows with a 24px duotone
icon each, then `Nimali Perera, ICT Technician`, `Design kit` and `Sign out`.
`Raise a request` is also pinned as a full-width plum button directly under the
top bar on Home and Requests, and repeated at the foot of every page, so it is
always within one thumb reach without opening the menu.

**With JavaScript off.** Identical. The menu is a native disclosure, the filter
panel is a native disclosure with its own `Apply` button, every form is a real
`<form>`, and `Mark it returned` is a link to a confirmation section at the foot
of the device page. `app.js` only adds: closing the menu after a link inside it is
followed, in-place filtering with the live `Showing N of 8 requests` line (and the
`Finding requests…` wait line), toast rendering and dismissal, the `<dialog>`
version of the confirm step with its focus trap, the busy `Sending…` button, the
`?demo=` hooks, and focusing the error summary.

## Density intent

Parchment is the least dense of the five, deliberately and by a clear margin. The
queue is a list of cards at every width, never a table, and the card is a
four-line object (reference + urgency chip, title, status + who is on it, raised
by + raised), built to the band table in the direction file: **188px** on the
queue with a 16px gap, a 204px pitch. On the dashboard and the device record the
fourth line is dropped and the card is **156px** (182px at 400px).

Measured in Chromium at 1440×900 with the web fonts loaded: the `requests.html`
chrome above the first card is 430px (top bar 73, page-head top padding 32, h1
48, lead 30 on one line, gaps 12 and 24, label 24 + 6, search field 56 + 16,
filter disclosure 56 + 16, count line 24 + 13), and the card tops are
**430 · 634 · 838 · 1042**, so **three request rows start above the 900px fold**,
with 62px of margin on the third. The direction file's budget puts the first
card at 460 (it allows for a two-line lead) with a tolerance of 288–491px for a
count of exactly three; 430 is inside it. At 400px wide the queue cards measure
240–270px as the title and metadata wrap.

## Components and tokens

Every colour, font, space, radius, shadow and duration is declared once in
`:root` of `style.css` and used through `var(--…)`; no raw colour appears outside
that block, and inline SVG uses `currentColor` for every fill. The stylesheet is
in eight numbered sections: 1 tokens, 2 base and reset, 3 icons, 4 app shell and
navigation, 5 components, 6 page-specific, 7 responsive, 8 reduced motion and
print. Spacing is an 8px scale (`--s1` 8 … `--s7` 96); radii are 12 / 20 / 28px;
the two shadows are warm-tinted (`rgba(42,35,28,…)`), never neutral black.

Icons are **Solar Bold Duotone**, with the duotone layer at opacity `.32`. Each
page defines the icons it uses once, in a visually hidden `<svg>` sprite of
`<symbol>`s directly after the skip link, and places them with `<use>`; `app.js`
clones from the same sprite for the toast and the wait line. The sprite is used
rather than a `<template>` so that every status icon still renders with JavaScript
off. The Solar set has no wrench, so `In repair` uses a wrench drawn on the same
24-unit grid in the same bold-duotone idiom.

## Accessibility

- Landmarks: `<header>`, `<nav aria-label="Main">`, `<main id="main">`,
  `<footer>` with `<nav aria-label="Utility">`; `role="search"` on the queue's
  search form. The skip link is the first focusable element on every page.
- One `<h1>` per page, matching the navigation label; `<h2>` per section; `<h3>`
  only inside `ui-kit.html` specimens.
- Every control has a visible `<label for>`; help text is linked with
  `aria-describedby`; in the error state `aria-invalid="true"` is set only on the
  failed fields and the error id is added after the help id. The urgency radios
  are a `<fieldset>` with a `<legend>`, each option's sentence inside its own
  `<label>`. The error summary is `role="alert" tabindex="-1"`, is focused on
  load, and its links move focus into the fields.
- Focus ring: 3px `--focus` outline with a 3px `--surface` gap on every focusable
  element, shown in the kit on a light and a dark surface.
- Touch: every interactive element is at least 44×44px at 390px wide and most are
  56px tall; `Cancel` is 24px from `Send the request`. Adjacent targets are at
  least 8px apart.
- Status, condition and urgency are always an icon plus a word.
- `@media (prefers-reduced-motion: reduce)` sets every animation and transition to
  `.01ms` and `scroll-behavior: auto`.
- The crest is never recoloured, filtered or stretched; `alt=""` where the
  wordmark names the college beside it, `alt="Polymath College crest"` in the kit.

## Skills used

Loaded by the builder (`tmd-frontend`) for this folder:
`clean-minimal-beige-light-mode`, `orange-clean-paper-saas` (layout rhythm only;
the accent is plum), `ui-design:spacing-system`, `ui-design:readable-measure`,
`interaction-design:onboarding-design`, `cognitive-accessibility:plain-language-design`,
`inclusive-interaction:touch-target-design`, `beautiful-shadows` (warm, lowest
end of its range), `solar-duotone-bold`, `accessible-content:form-labelling`,
`accessible-content:table-accessibility`, `accessible-content:heading-structure`,
`inclusive-interaction:keyboard-navigation`, `interaction-design:feedback-patterns`.

The designer (`tmd-ui-designer`) lists its own skills in
`docs/design/directions/b.md`.

## Demo hooks

These query strings switch a page into a state without a server. They are
**prototype-only** and are never carried into `templates/`.

| URL | State |
|---|---|
| `login.html?demo=error` | Sign-in error: `We couldn't sign you in`, `nimali.p` kept in the username box, focus on the password box |
| `request-form.html?demo=errors` | Two fields failed; everything else typed is kept; the summary alert is focused and links to each field |
| `requests.html?demo=empty` | The empty state: `No requests match what you chose` with `Clear the filters` |
| `dashboard.html?demo=toast` (any app page) | The success toast `Request sent. We gave it the number REQ-2049.` with `Undo`, plus the same sentence as a success alert at the top of the page |
| `device.html?demo=denied` | The no-permission card: `You can't open this page` |

Sending the form for real (with or without JavaScript) lands on
`dashboard.html?demo=toast`, so the success state is reachable through the real
flow as well.

## Screenshots

`screenshots/` holds the fifteen canonical full-page captures of the delivered HTML, taken with the web fonts loaded: `desktop-*.png` at 1440×900 and `mobile-*.png` at 400×844 for the six pages, plus the state captures `desktop-login--error.png`, `desktop-request-form--errors.png` and `desktop-requests--empty.png` at 1440×900.

