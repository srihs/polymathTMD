# Five design directions — index

Task: [`docs/tasks/002-design-directions.md`](../../tasks/002-design-directions.md).
This file fixes the distinctness plan **before** any direction is written, so no two
directions can drift into look-alikes. Each row is settled; a builder may not change
a row's navigation model, type pairing or palette mood.

| # | Direction | Folder | Desktop navigation | Phone navigation | Headings / body (Google Fonts) | Palette mood | Density (request rows in first 900px) |
|---|---|---|---|---|---|---|---|
| a | **Ledger** | `design/a-ledger/` | Left vertical nav — a **248px sidebar**, items grouped under `Work` and `Start` headings, each carrying a live queue count, and the primary action as a full-width button inside it | Fixed bottom tab bar, icon + word | **Archivo** / **IBM Plex Sans** (+ IBM Plex Mono for references) | Cool slate paper, crest purple as the only chroma | High — **8** |
| b | **Parchment** | `design/b-parchment/` | Top bar with the four labels, one centred column, no sidebar | `<details>` "Menu" panel under a slim top bar | **Fraunces** / **Karla** | Warm parchment, oat and plum | Low — **3** |
| c | **Broadsheet** | `design/c-broadsheet/` | Masthead + breadcrumbs, with an "On this page" section nav beside the column | Sticky masthead with a horizontally scrolling nav strip | **Newsreader** / **Source Sans 3** | Soft lilac-tinted paper, near-black ink, rules not boxes | Low–medium — **5** |
| d | **Signpost** | `design/d-signpost/` | Left vertical nav — a **96px rail**, ungrouped, each item a bordered 96×88 tile with the icon stacked over its word and `Requests` carrying a count badge, against framed content panels | Always-visible 2×2 framed nav grid docked under the header (no menu to open) | **Space Grotesk** / **Atkinson Hyperlegible** | High-contrast white and near-black plum, 2px frames | Medium — **6** |
| e | **Workbench** | `design/e-workbench/` | Search-led command bar over a two-pane master–detail | Pane stack: "Menu" link jumps to the nav block at the end of the document; Back link returns to the list | **Sora** / **Work Sans** (+ JetBrains Mono for references) | Dark plum chrome against a cool light canvas | Medium–high — **7** |

**On desktop navigation, read the table as three mechanisms and one pair.** b, c and
e each use a genuinely different mechanism from every other direction: a horizontal
top bar over a single centred column; a ruled masthead with a section index running
beside the content; and a search-led command bar over two panes. **a and d share a
mechanism** — both are a persistent left-hand vertical nav whose items carry an icon
and a word, and neither collapses. They differ on **four of the six rows below** —
width, grouping, item shape and framing. On the other two they behave identically:
both surface the open request count as a live badge, and both put `Raise a request`
inside the nav as its only filled item. What separates them is real, but it is a
matter of degree and treatment, not of kind:

| | a — Ledger | d — Signpost |
|---|---|---|
| Width | 248px sidebar | 96px rail |
| Grouping | Two labelled groups, `Work` and `Start` | None; four items in a row |
| Item shape | A text row with the icon inline | A bordered 96×88 tile, icon stacked over the word |
| Live counts | **Both carry one.** `Requests` shows the open count as a badge in the sidebar row | **Both carry one.** `Requests` shows the open count as a badge on the rail tile |
| Primary action | **Both do the same thing.** `Raise a request` sits inside the nav as its only filled item — here a full-width button | **Both do the same thing.** `Raise a request` sits inside the nav as its only filled item — here a filled tile in the same rank as the other three |
| Treatment | One hairline against the content column | 2px frames and hard offset shadows |

This is stated plainly because the point of the set is to help the owner choose, and
a table that implied six mechanisms where there are five would make a and d look
further apart than they are. The two still read as different products at a glance —
a 96px tiled rail and a 248px grouped sidebar are not mistakable for one another —
but if the brief's intent is five mechanisms with no pair, d is the one to change,
and the cheapest honest change is to move its navigation off the left edge entirely.

The density ladder is **b 3 < c 5 < d 6 < e 7 < a 8**, a spread of five rows
between the least and the most dense. Each figure is the number of request rows
whose top is above 900px at a 1440×900 viewport, and each direction file gives the
band-by-band vertical budget that produces it, with the tolerance to check against.
Where a builder's measurement disagrees with a direction file, the measurement
wins and the file is corrected — the numbers here are the settled ones.

Every direction shares, without variation: the crest purple `#722A82` as the brand
hue, the four navigation labels `Home` · `Requests` · `Devices` · `Raise a request`,
the five request status words, all sample content, and the accessibility floor in
the task brief's **Design** section.

The only visual inputs to all five are `logo.png` and the three crest cut-outs in
`static/img/`. Every palette, type pairing, radius, shadow and component shape is
derived from those inputs inside its own direction.
