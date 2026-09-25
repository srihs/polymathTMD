# Month calendar (`.cal`)

Origin: brief 009, the Zoom timetable: a wall-calendar month of classes, weeks Monday to Sunday, plus a day view that lists every class on one date. Use it for any "what is booked on which day" view of one month.

**Why a new component:** the month is two-dimensional data (this weekday, in this week), so it is a real `<table>`. But `.datagrid` is built for one record per row, and its phone layout turns each row into a labelled card. Here one row is a week of seven boxes, each with its own heading and list of links, and the phone layout has to become a list of days, not a list of weeks. `.worklist` and `.avail` are single-column lists. Nothing fits, so this note defines one block, `.cal`, with three parts: the navigation bar (`.cal-nav`), the month grid (`.cal`), and the day list (`.cal-list`). All three share the entry link, `.cal__entry`.

## Tokens

New tokens go in the first `:root` block of `static/css/style.css`, in the layout-geometry group:

| Token | Value | Used for |
|---|---|---|
| `--cal-day-min` | `120px` | Minimum height of a day box on desktop, so a quiet week still looks like a calendar row |
| `--cal-num` | `28px` | The round "today" marker behind the day number |
| `--cal-time-w` | `11em` | Day list: the time-range column |
| `--cal-ref-w` | `6.5em` | Day list: the reference column |

Everything else reuses existing tokens: `--c-primary-soft`, `--c-primary-text`, `--c-primary`, `--c-on-primary`, `--c-surface`, `--c-surface-2`, `--c-border`, `--c-control`, `--c-warn-text`, `--c-heading`, `--c-text`, `--fs-help`, `--fs-body`, `--fw-semibold`, `--fw-medium`, `--lh-tight`, `--space-1` to `--space-4`, `--radius-sm`, `--rule`, `--nav-bar`, `--target`, `--tab-h`, `--focus-width`.

## 1. Navigation bar (`.cal-nav`)

A row of links that move by month (or by day, on the day view). They are plain links that load a new page.

```html
<nav class="cal-nav" aria-label="Choose a month">
  <ul class="cal-nav__list" role="list">
    <li><a class="button button--secondary" href="…?month=2026-08"><svg class="icon" aria-hidden="true" focusable="false"><use href="#i-chevron-left"></use></svg>Previous month<span class="visually-hidden">, August 2026</span></a></li>
    <li><a class="button button--quiet" href="…">This month</a></li>   <!-- only when not on the current month -->
    <li><a class="button button--secondary" href="…?month=2026-10">Next month<span class="visually-hidden">, October 2026</span><svg class="icon" aria-hidden="true" focusable="false"><use href="#i-chevron-right"></use></svg></a></li>
  </ul>
</nav>
```

| Part | Spec |
|---|---|
| `.cal-nav__list` | flex, `flex-wrap: wrap`, gap `var(--space-2)`, no list style, margin 0, padding 0 |
| Links | the existing `.button` classes, which are 44px tall. Previous and next use `button--secondary`; the middle link (`This month`, or `Back to October 2026` on the day view) uses `button--quiet` |
| Below 600px | `.cal-nav` takes the full width of the box head. The list becomes a two-column grid (`repeat(2, minmax(0, 1fr))`): previous in column 1 and next in column 2 on the first row. The middle link spans both columns on a second row (`grid-column: 1 / -1`, `order: 1`). Each link fills its cell (`width: 100%`) |

## 2. Month grid (`.cal`)

```html
<table class="cal" role="table" aria-colcount="7">
  <caption class="visually-hidden">Zoom classes in September 2026, by week, Monday to Sunday.</caption>
  <thead role="rowgroup">
    <tr role="row">
      <th scope="col" role="columnheader" aria-colindex="1"><span aria-hidden="true">Mon</span><span class="visually-hidden">Monday</span></th>
      …
    </tr>
  </thead>
  <tbody role="rowgroup">
    <tr role="row">
      <td role="cell" aria-colindex="1" class="cal__day cal__day--out"></td>                <!-- 31 Aug: outside the month, nothing inside -->
      <td role="cell" aria-colindex="2" class="cal__day">                                   <!-- a day with classes -->
        <div class="cal__head">
          <h3 class="cal__date"><a class="cal__date-link" href="…/2026/9/1/"><time datetime="2026-09-01"><span class="cal__date-extra">Tue </span><span class="cal__num">1</span><span class="cal__date-extra"> Sep</span></time></a></h3>
        </div>
        <ul class="cal__entries" role="list">
          <li><a class="cal__entry" href="…">…</a></li>
        </ul>
        <a class="cal__more" href="…/2026/9/1/"><span aria-hidden="true">+2 more</span><span class="visually-hidden">2 more classes on Tue 1 Sep</span></a>
      </td>
      <td role="cell" aria-colindex="3" class="cal__day cal__day--empty">…head only…</td>  <!-- in the month, no classes -->
      …                                                                                    <!-- every th and td gets aria-colindex, 1 (Monday) to 7 (Sunday) -->
      <td role="cell" aria-colindex="7" class="cal__day cal__day--today" aria-current="date">
        <div class="cal__head">
          <h3 class="cal__date">…</h3>
          <span class="tag tag--brand">Today</span>
        </div>
        …
      </td>
    </tr>
  </tbody>
</table>
```

`role="list"` on the `ul` is needed because `list-style: none` makes Safari and VoiceOver drop list semantics.

### Desktop (768px and wider)

| Part | Spec |
|---|---|
| `.cal` | `width: 100%`, `table-layout: fixed` (seven equal columns whatever the content), `border-collapse: collapse`, `font-size: var(--fs-body)` |
| `th` | padding `var(--space-2) var(--space-2)`, left-aligned, `--fs-help`, `--fw-semibold`, `--c-heading`, bottom border 1px `--c-border` |
| `.cal__day` | `vertical-align: top`, `height: var(--cal-day-min)` (a table cell treats `height` as a minimum, and every box in the row grows to the tallest one), padding `var(--space-1)`, border 1px `--c-border`, `--c-surface` background. The grid's outer edge sits inside the box: the first and last columns drop their outer side borders, and the last row drops its bottom border |
| `.cal__day--out` | `--c-surface-2` background and no content. This is a flat fill with no hatching and no date (D2) |
| `.cal__day--empty` | Same as `.cal__day`: only the head shows |
| `.cal__head` | flex, `align-items: center`, gap `var(--space-2)`, `min-height: var(--target)` |
| `.cal__date` | margin 0, `font-size: var(--fs-body)`, `--fw-semibold`, `--lh-flat` |
| `.cal__date-link` | `display: inline-grid; place-items: center`, `min-width: var(--target)`, `min-height: var(--target)`, `--c-heading`, no underline. On hover the number is underlined. On focus it uses the global ring with an inset offset (`outline-offset: calc(var(--focus-width) * -1)`) so the next cell's border doesn't clip it |
| `.cal__date-extra` | Hidden on screen but read out, using the same declarations as `.visually-hidden`, scoped to 768px and wider. On phones it is shown inline, so the heading reads `Tue 1 Sep` |
| `.cal__num` | `display: inline-grid; place-items: center; min-width: var(--cal-num); height: var(--cal-num); border-radius: var(--radius-round)` |
| Today (`.cal__day--today`) | Three cues, and none relies on colour alone: <br>1. The word `Today` as `.tag.tag--brand`, next to the date. <br>2. The number in a filled circle: `.cal__num` gets a `--c-primary` background and `--c-on-primary` text. <br>3. A bar along the top edge of the box: `box-shadow: inset 0 var(--nav-bar) 0 var(--c-primary-text)` |
| `.cal__entries` | no list style, margin 0, padding 0, grid, gap `var(--space-1)` |
| `.cal__more` | `display: flex; align-items: center`, `min-height: var(--target)`, padding `0 var(--space-2)`, `--fs-help`, `--fw-semibold`, `--c-primary-text`, underlined. Inset focus ring |

### The entry link (`.cal__entry`), in a day box

One link per class. The whole block is the target: full box width and at least 44px tall.

```html
<a class="cal__entry" href="{% url 'zoom:detail' pk %}">
  <span class="cal__time">8:30 am<span class="visually-hidden"> to 11:30 am, ZL-0042,</span></span>
  <span class="cal__name">CCC Batch 3 - Mathematics<span class="visually-hidden">,</span></span>
  <span class="cal__account">Zoom 03</span>
</a>
```

For a waiting class, add the modifier `cal__entry--waiting` and replace `.cal__account` with `zoom/partials/status_tag.html` (`clock` icon plus `Waiting for IT`). Keep whitespace between the spans in the markup so the accessible name gets its spaces.

| Part | Spec |
|---|---|
| `.cal__entry` | `display: flex; flex-direction: column; align-items: flex-start`, gap `var(--space-1)`, `min-height: var(--target)`, padding `var(--space-1) var(--space-2)`, `border-radius: var(--radius-sm)`, `font-size: var(--fs-help)`, `line-height: var(--lh-tight)`, no underline, `color: var(--c-text)` |
| Booked (default) | background `--c-primary-soft`, plus a left bar `border-left: var(--nav-bar) solid var(--c-primary-text)` |
| `.cal__entry--waiting` | background `--c-surface`, border `var(--rule) dashed var(--c-control)`, left bar `var(--nav-bar) solid var(--c-warn-text)`. The meaning is carried by the tag's word and icon; the dashed outline is a second non-colour cue |
| `.cal__time` | `--fw-semibold`, `--c-heading`, `white-space: nowrap` |
| `.cal__name` | `overflow-wrap: anywhere`. It wraps and is never cut off with an ellipsis (criterion 23) |
| `.cal__account` | `--fw-medium`, `--c-text`, `overflow-wrap: anywhere` |
| Hover | `.cal__name` is underlined. The background doesn't change, which keeps it working in both modes |
| Focus | the global ring, inset (`outline-offset: calc(var(--focus-width) * -1)`) |

### Phone (below 768px): a list of days made from the same markup

| Part | Spec |
|---|---|
| `.cal`, `tbody`, `tr`, `td` | `display: block` (the explicit ARIA roles keep the table meaning) |
| `thead` | Visually hidden with the same declarations `.datagrid thead` uses |
| `.cal__day--out`, `.cal__day--empty` | clipped, contents hidden (see below) |
| `tr` | no border, no padding. A week whose days are all hidden collapses to nothing |
| `.cal__day` (remaining) | `height: auto`, padding `var(--space-3)`, border 1px `--c-border`, `--radius`, margin-bottom `var(--space-3)` |
| `.cal__date-extra` | Shown inline, so the heading reads `Tue 1 Sep` |
| `.cal__date-link` | `display: inline-flex; align-items: center; justify-content: flex-start`, `min-height: var(--target)`, `min-width: 0`, underlined |
| Today | Keeps the `Today` tag and the top bar. `.cal__num` drops its circle (`background: none; color: inherit; min-width: 0`), because a circle around one word of `Tue 28 Sep` reads oddly |
| `.cal__entry` | `min-height: var(--tab-h)` (56px), padding `var(--space-2) var(--space-3)` |
| Cap | Unchanged: the same `+N more` link |

**Never `display: none` a calendar cell; clip it and hide its contents.** Below 768px, hide those cells with the same clipping declarations as `.visually-hidden`, and give their contents `visibility: hidden` so a clipped date link can't take focus. Keep `aria-colcount="7"` on the `table` and `aria-colindex` `1` (Monday) to `7` (Sunday) on every `th` and `td`. Why: `display: none` removes a cell from the accessibility tree, and Chrome works out a cell's column header from its position among the cells that remain, even when `aria-colindex` is set, so `Tue 1 Sep` was announced under "Monday" (brief 009 review, SF1). A clipped cell stays in the tree, so every day keeps its own weekday. The trade-off: a screen-reader user moving cell by cell meets a blank cell for each out-of-month or empty day.

## 3. Day list (`.cal-list`), on the day view

Every class on one date, with no cap.

```html
<ol class="cal-list" role="list">
  <li><a class="cal__entry cal__entry--row" href="…">
    <span class="cal__time">8:30 am to 11:30 am<span class="visually-hidden">,</span></span>
    <span class="cal__ref">ZL-0042<span class="visually-hidden">,</span></span>
    <span class="cal__name">CCC Batch 3 - Mathematics<span class="visually-hidden">,</span></span>
    <span class="tags"><span class="cal__account">Zoom 03</span> {recording tag if asked for}</span>
  </a></li>
</ol>
```

| Part | Spec |
|---|---|
| `.cal-list` | no list style, margin 0, padding 0, grid, gap `var(--space-2)` |
| `.cal__entry--row` | `display: grid`, `grid-template-columns: var(--cal-time-w) var(--cal-ref-w) minmax(0, 1fr) auto`, `align-items: center`, gap `var(--space-4)`, `min-height: var(--tab-h)`, padding `var(--space-3) var(--space-4)`, `font-size: var(--fs-body)`. The booked and waiting looks are the same as in the grid |
| `.cal__ref` | `--fw-semibold`, `--c-heading`, `white-space: nowrap` |
| Below 600px | one column (`grid-template-columns: minmax(0, 1fr)`), gap `var(--space-1)`, in this order: time, reference, name, tags |

## States

| State | Look |
|---|---|
| Booked entry | primary-soft fill, primary left bar, account label |
| Waiting entry | surface fill, dashed outline, amber left bar, `Waiting for IT` tag (clock icon plus word) |
| Day with more than `DAY_BOX_LIMIT` entries | the first 3 entries, then `+N more` |
| Day with no entries | head only (desktop); hidden (phone) |
| Day outside the month | an empty flat `--c-surface-2` cell (desktop); hidden (phone) |
| Today | `Today` tag, number circle (desktop), top bar, `aria-current="date"` |
| Hover | name underlined; date and `+N more` underlined |
| Focus | 2px `--c-focus` ring, inset |

## Contrast

These come from the tokens, approximately. The verifier confirms them with a checker:

| Pair | Light | Dark |
|---|---|---|
| `--c-heading` on `--c-primary-soft` | about 11:1 | about 8:1 |
| `--c-text` on `--c-primary-soft` | about 11:1 | about 6:1 |
| `--c-on-primary` on `--c-primary` (today circle) | about 9:1 | about 9:1 |
| `--c-primary-text` on `--c-surface` (`+N more`) | 8.86 | 6.31 |
| `tag--warn`, `tag--brand` | 5.43 / 6.52 | 7.61 / 5.85 |
| Left bars and the dashed outline (non-text, 3:1) | `--c-primary-text`, `--c-warn-text` and `--c-control` all pass on their fills | pass |

## Behaviour

No JavaScript. Every control is a plain link or a GET form. Month, day and account all live in the URL, so any view can be bookmarked.
