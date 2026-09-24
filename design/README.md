# Design prototypes — index

This folder holds five design options for the Technology Management Desk.
Each one is a stand-alone set of web pages. They are reference material, not
the real application:

- They are **not served** by the app and are **not part of the Docker image**.
- Nothing under `apps/`, `templates/` or `static/` changed to make them.
- The owner picks one. Nobody has picked yet — this index is for comparing
  them, not for ranking them.
- Once a direction is chosen, its stylesheet becomes the app's real
  stylesheet (`static/css/style.css`) in a later piece of work. That has not
  happened yet.

Every direction shows the same six pages, filled with the same made-up
school data (see **Same content everywhere** below), so the only thing that
changes between them is the design.

## How to open them

Each prototype needs no server and no install. From the file browser, open
any of these six files inside a direction's folder, for example
`design/a-ledger/dashboard.html`:

- `login.html` — sign in
- `dashboard.html` — home
- `requests.html` — the list of help-desk requests
- `device.html` — one device's record
- `request-form.html` — the form for raising a request
- `ui-kit.html` — every button, field and badge the direction uses, in every
  state ("Design kit")

The pages link to each other through their navigation, so once one page is
open you can click through to the rest.

Some pages also read a `?demo=` web address to show a state that is hard to
reach by clicking around, such as a sign-in error or an empty list. For
example, opening `login.html?demo=error` shows the sign-in error message.
Each direction's own `README.md` lists its exact `?demo=` links. These links
only work in these prototype folders — they are never carried into the real
app.

**Note on the phone screenshots.** The `mobile-*.png` images in each
`screenshots/` folder capture the whole page, not just what shows on a phone
screen at once. Anything fixed in place while scrolling — a's bottom tab
bar, or b's and d's pinned "Raise a request" button — does not stay fixed in
these images: it can show at the top of the picture, or appear twice. To see
where these elements really sit, open the page in a browser window sized to
a phone (about 400px wide) rather than judging position from the
screenshot.

## Comparing the five

| # | Direction | Folder | Navigation model | Heading font | Body font | Palette mood | Rows above the fold | Chart | Who it suits |
|---|---|---|---|---|---|---|---|---|---|
| a | **Ledger** | [`a-ledger/`](a-ledger/) | Desktop: a 248px sidebar on the left, split into two groups ("Work" and "Start") with live count badges. Phone: a row of tabs at the bottom. | Archivo | IBM Plex Sans | Cool grey-blue paper, with the crest purple as the only strong colour | 8 | Yes | ICT staff juggling many jobs, who need everything on screen at once |
| b | **Parchment** | [`b-parchment/`](b-parchment/) | Desktop: a plain top bar with the four main links. Phone: a "Menu" button that opens a list. | Fraunces | Karla | Warm, paper-like cream, with a soft plum accent | 3 | No | Occasional users, such as teachers, who want one calm task per screen |
| c | **Broadsheet** | [`c-broadsheet/`](c-broadsheet/) | Desktop: a masthead with a small "On this page" list beside the text. Phone: a header with a sideways-scrolling strip of links. | Newsreader | Source Sans 3 | Pale lilac paper with near-black text, set out like a printed page | 5 | Yes | Staff who read carefully for one fact at a time, such as office staff |
| d | **Signpost** | [`d-signpost/`](d-signpost/) | Desktop: a 96px rail of framed tiles with a hard shadow, each showing an icon and its word, with no groups. Phone: a fixed grid of four link tiles, always visible. | Space Grotesk | Atkinson Hyperlegible | Bright white with near-black plum, inside bold 2px frames | 6 | No | Staff on a shared or well-worn screen who need big, unmistakable buttons |
| e | **Workbench** | [`e-workbench/`](e-workbench/) | Desktop: a dark search bar on top, with the list and the open record side by side. Phone: the list and the record stacked, with a "Back to the list" link. | Sora | Work Sans | A dark plum bar and side panel around a light, paper-white work area | 7 | No | IT staff working down a queue, who need the list and the record together |

"Rows above the fold" counts how many request rows show on the requests
page without scrolling, on a large desktop screen. A higher number means a
denser page; a lower number means a more spread-out page. "Chart" says
whether that direction draws the one bar chart of requests raised per day —
the other directions show the same numbers as plain sentences instead.

## The five directions, in plain words

**a — Ledger.** [`a-ledger/dashboard.html`](a-ledger/dashboard.html) ·
[screenshots](a-ledger/screenshots/). A quiet, dense console built for
someone who manages the whole queue by themselves. Every request, count and
due date sits on its own line, so nothing needs a scroll or a click to find.
Numbers line up in a mono typeface like a ledger book, and the crest purple
is the only strong colour on the page.

**b — Parchment.** [`b-parchment/dashboard.html`](b-parchment/dashboard.html) ·
[screenshots](b-parchment/screenshots/). A calm, spread-out design with one
job on each screen and lots of white space. It is aimed at someone who opens
the system only a few times a term and does not want to work out where to
look. The warm cream background and rounded cards feel more like paper than
software.

**c — Broadsheet.** [`c-broadsheet/dashboard.html`](c-broadsheet/dashboard.html) ·
[screenshots](c-broadsheet/screenshots/). Laid out like a well-printed
school notice: a ruled heading band, one wide column of readable text, and a
short "On this page" list for jumping to a section. There are no boxes or
shadows — the layout uses thin rules and space instead, the way a printed
page does.

**d — Signpost.** [`d-signpost/dashboard.html`](d-signpost/dashboard.html) ·
[screenshots](d-signpost/screenshots/). The boldest and clearest of the five.
Every panel and button sits inside a solid frame, so nothing looks
accidentally clickable or accidentally plain text. It uses the strongest
colour contrast of the five directions and the largest touch targets, aimed
at a shared or well-worn screen.

**e — Workbench.** [`e-workbench/dashboard.html`](e-workbench/dashboard.html) ·
[screenshots](e-workbench/screenshots/). Built for working through a queue
without losing your place: the list of requests and the open request sit
side by side on a desktop screen, with a dark search bar above them. On a
phone the two become a list, then a record, with a link back to the list.

## Same content everywhere

All five directions show the exact same sample school: the same staff
names, the same devices, the same help-desk requests and the same dates.
Only the design changes — the layout, the colours, the fonts, and how dense
or spread-out the page feels. This makes it possible to compare the five
directions on design alone, without the content getting in the way.

## How these were made

Before any page was built, one design brief was written for each direction,
setting its navigation, fonts, colours, components and layout in advance.
Those briefs are in
[`docs/design/directions/`](../docs/design/directions/) —
[`a.md`](../docs/design/directions/a.md),
[`b.md`](../docs/design/directions/b.md),
[`c.md`](../docs/design/directions/c.md),
[`d.md`](../docs/design/directions/d.md) and
[`e.md`](../docs/design/directions/e.md) — alongside
[`README.md`](../docs/design/directions/README.md), which lays out how the
five briefs were kept different from each other from the start.
