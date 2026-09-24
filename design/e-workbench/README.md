# Direction E — Workbench

Static prototype for the Polymath College **Technology Management Desk**. Open any
page straight from the file system; the only external resource is Google Fonts.

**Concept.** Workbench is the two-handed screen: a dark plum command bar with the
search box at its centre sits over two panes — the list you are working through on
the left, the record you are working on at the right — so a technician never loses
the queue to open a job. On a phone the two panes become a stack: the list, then the
record with a "Back to the list" link at the top, which is the same mental model one
screen at a time.

## Pages

| File | What it is |
|---|---|
| `login.html` | Sign in — the one screen where the dark chrome fills a whole half |
| `dashboard.html` | Home — today's figures and actions in the list pane, the requests to work on in the record pane |
| `requests.html` | Requests — the queue with search, filters, sort and pagination beside the request preview |
| `device.html` | Devices — the `IT-0142` record: section index on the left, four sections on the right |
| `request-form.html` | Raise a request — the guided form, with its section index and both buttons beside it |
| `ui-kit.html` | Design kit — every component in every state, on the light surface and on the chrome |

The `Devices` navigation item opens the single `IT-0142` record. A device register
list is deliberately not prototyped: `requests.html` already proves the list, filter,
sort, status and empty-state patterns a register would reuse.

## Fonts

Google Fonts, loaded once in each page's `<head>`:

| Family | Weights | Used for |
|---|---|---|
| **Sora** | 600, 700 | The wordmark `Polymath College` (700), all headings (h1 700, h2 and h3 600), button labels (600), the avatar initials |
| **Work Sans** | 400, 500, 600, 400 italic | Body and prose (400, 16/26), lead paragraphs (18/28), help text (15/22), list-row titles (500), form labels and badge words (600), command-bar links (500), the quoted request text (the only italic) |
| **JetBrains Mono** | 500 | Anything you might read out loud: references (`REQ-2048`), tags (`IT-0142`), dates, money (`Rs 285,000`), serials, and the dashboard figures at 28px |

The wordmark is Sora 700: 15/20 in the command bar, 30/36 on the sign-in screen.

Scale: h1 30/38 (26/32 on phone), h2 21/28, h3 17/24, body 16/26, lead 18/28,
label 16/22, help 15/22, badge 14/18, mono 15/20, figure 28/32, quote 17/28.
Measure: 720px in the record pane, 640px for the form, 480px for the list pane.

## Palette

Derived from the crest in `logo.png`. `#722A82` is `hsl(289, 51%, 34%)`. Workbench
builds **two** families from it. The chrome is the crest hue driven down in lightness
(`hsl(289, 38%, 15%)` for the bar, `hsl(289, 30%, 22%)` for its inset surfaces), so
the dark furniture is the crest colour in shadow, not a generic black. The content
canvas goes the other way: cool neutrals at 220° with no purple in them, so the white
record pane reads as paper against the plum. The one bright purple, `--brand-bright`
at L 74%, exists only for the current-page marker and icons **on** the chrome, where
`--brand` itself would be too dark to see.

| Token | Hex | Derivation from the crest |
|---|---|---|
| `--brand` | `#722A82` | The crest, unmodified |
| `--brand-strong` | `#55205F` | Crest hue at L 25% |
| `--brand-hover` | `#5E236C` | Crest hue at L 28% — primary button hover (L −6%) |
| `--brand-active` | `#4A1B55` | Crest hue at L 22% — primary button active (L −12%) |
| `--brand-bright` | `#D79BE6` | Crest hue at L 74% — only on the chrome |
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
| `--ok` / `--ok-tint` | `#0D6154` / `#E2F1EE` | Fixed, Good, In store |
| `--warn` / `--warn-tint` | `#7E5A05` / `#F8EFD9` | Waiting on someone, In repair, Needs repair |
| `--danger` / `--danger-tint` | `#AB1F45` / `#FBE6EB` | Urgent, Out of service, errors |
| `--info` / `--info-tint` | `#0A5A7A` / `#E2EFF5` | New, Issued |
| `--focus` | `#722A82` | Focus ring on light surfaces |
| `--focus-on-chrome` | `#D79BE6` | Focus ring inside the bar |

**Where the crest purple is on every page:** the page's one filled primary action — the
`Raise a request` button in the command bar on `requests.html` and `ui-kit.html`; on
`dashboard.html` (`Raise a request` under `Things you can do`), `device.html` (`Raise a
request about this device`) and `request-form.html` (`Send the request`) the content
primary carries it and the bar's copy drops to the chrome secondary treatment, so no
page shows two filled buttons — the selected row's edge and tint in the list pane, the current
breadcrumb link, headings' timeline dots and figure numbers on `dashboard.html`, the
`Sign in` button on `login.html`, and the focus ring everywhere. The chrome itself
is the crest hue at low lightness.

### Contrast — computed (WCAG 2 relative luminance), not estimated

| Pair | Ratio | Needs | Result |
|---|---|---|---|
| `--ink` on `--surface` | 17.43:1 | 4.5 | pass |
| `--ink` on `--canvas` | 16.10:1 | 4.5 | pass |
| `--muted` on `--surface` | 6.52:1 | 4.5 | pass |
| `--muted` on `--canvas` | 6.02:1 | 4.5 | pass |
| `--muted` on `--surface-2` (muted badge) | 5.55:1 | 4.5 | pass |
| `--chrome-ink` on `--chrome` | 15.27:1 | 4.5 | pass |
| `--chrome-muted` on `--chrome` | 7.80:1 | 4.5 | pass |
| `--chrome-ink` on `--chrome-2` (search text) | 12.81:1 | 4.5 | pass |
| `--chrome-muted` on `--chrome-2` (search placeholder) | 6.55:1 | 4.5 | pass |
| `--brand-bright` on `--chrome` (current item, icons) | 8.06:1 | 4.5 | pass |
| `--brand-bright` on `--chrome-2` | 6.77:1 | 4.5 | pass |
| `--surface` on `--brand` (primary button) | 8.86:1 | 4.5 | pass |
| `--surface` on `--brand-hover` | 10.86:1 | 4.5 | pass |
| `--surface` on `--brand-active` | 13.30:1 | 4.5 | pass |
| `--brand` on `--surface` | 8.86:1 | 4.5 | pass |
| `--brand` on `--canvas` | 8.19:1 | 4.5 | pass |
| `--brand` on `--brand-tint` (brand badge) | 7.56:1 | 4.5 | pass |
| `--brand-strong` on `--brand-tint` (light avatar) | 10.18:1 | 4.5 | pass |
| `--line-strong` on `--surface` (field border) | 3.38:1 | 3.0 | pass |
| `--line-strong` on `--canvas` (read-only field border) | 3.12:1 | 3.0 | pass |
| `--brand-bright` on `--brand` (button edge on the chrome) | 4.10:1 | 3.0 | pass |
| `--chrome-muted` on `--brand` | 3.97:1 | 3.0 | pass |
| `--ok` on `--surface` | 7.36:1 | 4.5 | pass |
| `--warn` on `--surface` | 6.27:1 | 4.5 | pass |
| `--danger` on `--surface` | 6.97:1 | 4.5 | pass |
| `--surface` on `--danger` (destructive button) | 6.97:1 | 4.5 | pass |
| `--info` on `--surface` | 7.62:1 | 4.5 | pass |
| `--ok` on `--ok-tint` | 6.32:1 | 4.5 | pass |
| `--warn` on `--warn-tint` | 5.47:1 | 4.5 | pass |
| `--danger` on `--danger-tint` | 5.85:1 | 4.5 | pass |
| `--info` on `--info-tint` | 6.49:1 | 4.5 | pass |
| `--focus` on `--canvas` | 8.19:1 | 3.0 | pass |
| `--focus` on `--surface` | 8.86:1 | 3.0 | pass |
| `--focus-on-chrome` on `--chrome` | 8.06:1 | 3.0 | pass |

`--line` (1.35:1 on white) and `--chrome-line` (1.56:1 on the chrome) are decorative
hairlines only. No control border was under 3:1, so no token needed darkening.
`--line-strong` on `--surface-2` is 2.88:1, which is why no control border ever sits
on `--surface-2`: the read-only field uses `--canvas` (3.12:1) instead.
The chrome secondary button (the bar's `Raise a request` on pages with a content
primary) uses pairs already in the table: `--chrome-ink` on `--chrome` 15.27:1 for the
label, `--chrome-muted` on `--chrome` 7.80:1 for its border, and `--chrome-ink` on
`--chrome-2` 12.81:1 for the hover fill. No new pair was needed.

The account menu under the avatar reuses the same chrome pairs: `--chrome-ink` on
`--chrome` 15.27:1 (name and links), `--chrome-muted` on `--chrome` 7.80:1 (the role
line and the panel border), `--brand-bright` on `--chrome` 8.06:1 (link icons) and
`--chrome-ink` on `--chrome-2` 12.81:1 (link hover). Where the panel overhangs the
`--canvas` strip below the bar its boundary is the `--chrome` fill, 16.09:1 on
`--canvas`; the 1px `--chrome-muted` border there is 2.06:1, an inner edge like
`--line`, not the thing that separates the panel from the page.

## Why it suits non-technical school staff

Nimali's real task is not "look at a request", it is "work down the queue without
forgetting where she was". Two panes make the queue permanent: she reads `REQ-2048`,
deals with it, and `REQ-2047` is already under her eye — no back button, no lost
place. For Dilani, Suresh or Anoma, who touch the desk a few times a term, the same
layout means the form they are filling in always has its own map beside it ("What you
are filling in", four short sections) and the two buttons are never below the fold.

The search box lives in the chrome rather than on a page because the fastest route
to a device for someone holding it, with the `IT-0142` sticker under their thumb, is
to type the sticker — from any screen, and on a phone it is the first thing under the
bar. The dark chrome earns its place practically: it separates "where I am in the
system" from "what I am reading", so the white record pane is the only bright thing
on the screen and the eye goes there first, which helps on a shared machine in a
classroom with the lights on. Every status is an icon plus a word, every error says
what to do next and keeps what was typed, every control is at least 44px, and the
`Menu` on a phone is a plain jump link to a list at the end of the page, so there is
nothing to learn and nothing that can get stuck.

## Navigation model

**Desktop (≥1080px).** A 64px command bar: crest chip and wordmark on the left, the
search field in the centre (`Press / to search`), then `Home`, `Requests` (with the
open count), `Devices`, the `Raise a request` button (filled `--brand` on the queue and the kit;
the chrome secondary — transparent, 1px `--chrome-muted` border, `--chrome-ink` label —
on the three pages that carry their own content primary) and the `NP` avatar. The
avatar is the `<summary>` of a `<details>` account menu: opening it drops a panel
under the bar with `Nimali Perera` / `ICT Technician`, `Design kit` and the `Sign out`
button, on the chrome tokens (`--chrome` fill, 1px `--chrome-muted` border,
`--chrome-ink` labels, 44px rows). It opens and closes natively; `app.js` adds
Escape (focus returns to the avatar), outside-click and focus-out closing. Under the bar a 40px context strip carries the
breadcrumb (`Requests › REQ-2048`) and, on the queue, the sort control and the result
line. Below that, two panes: a 480px list pane on the left (sticky, scrolls on its
own) and the record pane on the right. On the queue the filters are two 44px rows —
`Status` and `How urgent` side by side, then `Who is on it` — each select with its
visible label beside it. The current page is marked in the bar with
`aria-current="page"`, a brighter label and a 3px underline. A second skip link,
`Skip to the record`, jumps past the list pane.

**Phone (<1080px).** A 56px bar with the crest chip, the page name and a `Menu`
link. `Menu` is a plain anchor to `#menu`, a navigation block at the **end** of every
page with the four labels as 56px rows, the person, `Design kit` and `Sign out`.
Under the bar sit the search field and a 56px `Raise a request` button, so the main
action is always one thumb-reach away. It is filled on the dashboard (whose content
copy is hidden on phone) and the queue, and the chrome secondary on `device.html` and
`request-form.html`, where the content primary is the one filled button. The panes stack: on `requests.html` the list
comes first; opening a row shows the record with `Back to the list` at the top.

**With JavaScript off.** Everything above is plain HTML: the search form submits to
`requests.html`, the `Menu` anchor jumps, the account menu is a native `<details>`, the panes are two
stacked sections, every row is a link, the filter form has its own `Apply` button, the confirm dialog renders
inline at the foot of the device record, and both forms submit. `app.js` only adds
the `/` shortcut, in-place filtering with a live result line, the pane swap without a
reload, toasts, the modal focus trap and the demo hooks.

## Density

Medium–high: dense in the list pane, comfortable in the record pane. The list pane is
480px wide so that even the longest title in the contract sets on one line, which
makes every queue row a fixed 87px (112px minimum on a phone). At 1440×900, **7**
request rows start within the first 900px of `requests.html`, measured with the web
fonts loaded; the row tops are listed in the task brief's implementation notes.

## Skills used

Designer (`tmd-ui-designer`): `ux-strategy:information-architecture`,
`ui-design:design-screen`, `ui-design:visual-hierarchy`, `ui-design:type-system`,
`ui-design:color-palette`, `interaction-design:state-machine`,
`interaction-design:form-design`, `cognitive-accessibility:plain-language-design`,
`accessible-content:heading-structure`.

Builder (`tmd-frontend`): `split-layout-technical`, `nested-container-clean-agency`,
`interaction-design:navigation-patterns`, `interaction-design:search-ux`,
`inclusive-interaction:keyboard-navigation`, `interaction-design:state-machine`,
`ui-design:dark-mode-design` (for the chrome only — the content stays light),
`cognitive-accessibility:plain-language-design`, `accessible-content:form-labelling`.

Icons are the **Solar Broken** family from Iconify, the weight this direction
specifies; the preloaded `solar-duotone-bold` skill was not used, because its
Duotone Bold weight is not the one drawn here.

## Demo hooks

These switch a page into a state without a server. They are **prototype-only** and
are never carried into `templates/`.

| URL | State |
|---|---|
| `login.html?demo=error` | Sign-in error: the alert, `nimali.p` kept in the username box, focus on the password field |
| `request-form.html?demo=errors` | Two fields marked invalid, the summary alert focused, every other value kept |
| `requests.html?demo=empty` | Filters set to a combination that matches nothing; the empty state in the list pane, `Choose a request from the list to see it here.` in the record pane |
| `<any app page>?demo=toast` | The success toast `Request sent. We gave it the number REQ-2049.` with `Undo`, and the same sentence as an alert on the page |
| `device.html?demo=denied` | The no-permission panel in the record pane; the list pane and the bar stay |
| `device.html?demo=returned` | What the confirm dialog's `Yes, mark it returned` lands on: the toast and alert `IT-0142 is back in the ICT Store.` |

## Screenshots

`screenshots/` holds the fifteen canonical full-page captures, taken with the web
fonts loaded: `desktop-*.png` at 1440×900 and `mobile-*.png` at 400×844 for the six
pages, plus the state captures `desktop-login--error.png`,
`desktop-request-form--errors.png` and `desktop-requests--empty.png` at 1440×900.

## Files

`login.html` · `dashboard.html` · `requests.html` · `device.html` ·
`request-form.html` · `ui-kit.html` · `style.css` (eight numbered sections, every
value a token in `:root`) · `app.js` (one IIFE, `data-*` hooks only) ·
`assets/crest.png`, `assets/crest-chip.png`, `assets/favicon-32.png` (binary copies,
never recoloured or stretched) · `screenshots/`.
