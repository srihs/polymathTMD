# Placeholder controls (top-bar search and bell before their feature exists)

Origin: brief 004, D12 and criteria 37–38. This applies to f-desk (`docs/design/directions/f.md`). Brief 005 (D10) kept both controls as placeholders: the Zoom link request queue got its own search, and IT is notified by email instead of a bell. A later "search and notifications" brief replaces them for real and can then delete this file.

**Why:** the client approved a top bar with a search field and a bell. The app has nothing to search and nothing to notify about yet. The controls stay visible to match the approved look, but they must be honest: nothing submits, nothing is counted, and each one says why it does nothing.

## Search placeholder (`partials/top_search.html`)

**Anatomy.** `<details class="pop topfind" data-pop>` contains:
- a summary (shown <992px only): the `search` icon and visually hidden `Search, not available yet`;
- `.topfind__panel`, containing:
  - `<label class="visually-hidden" for="top-search">Search</label>`;
  - `.topsearch`, containing the decorative `search` icon (`aria-hidden`) and `<input class="topsearch__input" type="search" id="top-search" readonly aria-disabled="true" placeholder="Search is coming soon" aria-describedby="top-search-note">`;
  - `<span class="visually-hidden" id="top-search-note">Search is coming soon.</span>` (the owner's wording, which replaces D12's original).

There is no `<form>`, no `name` and no button.

| Part | Spec |
|---|---|
| Field size | `--search-w` (19rem, 304px at default) × `--target` (44px) |
| Icon | 16px, `--c-muted`, 12px from the start edge, vertically centred |
| Padding | `0 12px 0 var(--search-pad-start)` (36px) |
| Surface | `--c-surface-2`, `1px dashed var(--c-control)`, `--radius` |
| Placeholder | `--c-muted`, `opacity: 1`, `--fs-body` |
| Cursor | `not-allowed` on the field |
| Hover | no change |
| Focus | border `--c-focus` (still dashed) + `--focus-width` solid `--c-focus` outline, 1px offset |
| Phone (<992px) | f-desk's fixed panel under the top bar, 12px from each side (8px below 360px), field 100% wide |

**Contrast.** Placeholder text: 5.32:1 (light, `#636779` on `#F8F9FA`) and 4.53:1 (dark, `#9CA3AD` on `#363A38`). Dashed border: 3.25:1 on the field, 3.43:1 on the top bar.

**States.** There is one state: unavailable. It is identical with JS on and off.

**A later brief replaces it with** f-desk's `<form class="topsearch" role="search" method="get">`: solid border, the purple submit button at the end, a real label and a real placeholder. Brief 005 (D10) left it as a placeholder on purpose: the Zoom queue has its own search (criterion 22), and a site-wide search still needs a design for mixed permissions across more than one section.

## Empty notifications (`partials/notifications.html`)

**Anatomy.** `<details class="pop" data-pop>` contains:
- the summary: `.icon-button` with the `bell` icon and visually hidden `Notifications, none yet`. There is no `.count`;
- `.pop__panel`, containing `<p class="pop__head">Notifications</p>` and `<p class="pop__note">No notifications yet.</p>`.

| Part | Spec |
|---|---|
| `.pop__note` | `--fs-body`, `--lh-body`, `--c-muted` (5.61:1 light, 5.26:1 dark), padding `0 16px 16px` |
| Links | none |
| Keyboard | as every `data-pop`: `Escape` and outside click close it and return focus to the summary (JS). It opens with JS off |

`.pop__note` stays useful once a later brief adds real notifications, as the empty state of a real list. Brief 005 (D10) left the bell as a placeholder: IT is notified about Zoom requests by email instead, and a notifications model is its own later brief.
