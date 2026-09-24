# Flash messages (Django `messages`)

Origin: brief 004, D9 and criterion 15. This changes f-desk's `.flash` (f.md §7.7) for the app. Partial: `templates/partials/messages.html`, included in `base.html` directly after `.titlebar`, inside `<main>`.

**Why it is in the page flow and not a fixed toast:**
- without JS, a fixed toast can't be closed and covers content on phones;
- in the flow, it is read straight after the page's `<h1>`.

## Anatomy

- The container is `<div class="flashes">`: a column with a 12px gap and 24px margin below. It renders only when there are messages.
- There is one `<div class="flash flash--{family}" role="status|alert" data-flash>` per message. Each one contains:
  - a 20px icon (`aria-hidden`);
  - `<p class="flash__text">{{ message }}</p>` (auto-escaped);
  - `<button class="button button--quiet button--icon" type="button" data-flash-close hidden>` with an `x` icon and visually hidden `Close this message`.

| Django level | Family | Icon | Icon colour | Role |
|---|---|---|---|---|
| `success` | `ok` | `check-circle` | `--c-ok-text` | `status` |
| `info`, `debug` | `note` | `info` | `--c-note-text` | `status` |
| `warning` | `warn` | `alert-triangle` | `--c-warn-text` | `status` |
| `error` | `bad` | `alert-octagon` | `--c-bad-text` | `alert` |

**Tokens.**
- `.flash`: `--c-surface` background, 1px `--c-border`, `--radius`, `--c-shadow-pop`, padding 12px 16px.
- Layout: flex, gap 12px, align centre.
- Text: `--fs-body`, `--c-text`.
- Position: `position: static`, width auto.

**States.** Shown, or closed (JS removes the element and focuses `<main>`). No timeout. No `Undo`: f-desk's `data-flash-undo` isn't ported.

**Copy rule.** The text says the outcome in words and, for problems, what to do next (`We couldn't send the request. Check your connection and try again.`). The icon is a second cue, never the only one.
