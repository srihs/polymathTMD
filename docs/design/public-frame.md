# Public frame (`templates/public_base.html`)

Origin: brief 005, D1 and criterion 1. Used by every page a visitor can open without signing in (the Zoom request form, "check your email", confirm, confirmed). It extends `base.html` and overrides `{% block body %}`, so the document, skip link and icon sprite still come from `base.html`.

**Why a separate frame:** the shell's sidebar, top bar, user menu and layout settings mean nothing to a member of the public. It is one frame for anonymous and signed-in visitors alike, so no partial branches on `is_authenticated`.

## Anatomy

```
div.public
  header.public__head
    p.public__brand      crest-chip 28px (alt="") + "Technology Management Desk" (text, not a link)
    div.public__mode     partials/colour_mode_button.html (hidden without JS)
  main#main.public__main tabindex="-1"
    h1.public__title     {% block heading %}
    partials/messages.html
    {% block content %}  pages usually start with p.public__lead
  partials/footer.html   (.page-foot)
```

Landmarks: header (`banner`), `main`, footer (`contentinfo`). No `<nav>`.

## Tokens and values

| Part | Spec |
|---|---|
| `.public` | `min-height: 100vh`, flex column. Background `--c-surface-2` at ≥768px, `--c-surface` below |
| `.public__head` | `position: relative`, flex, centred, `min-height: var(--topbar-h)`, padding `0 var(--space-4)` |
| `.public__brand` | the same values as `.signin__brandline` (group the selectors, don't repeat values): 14.4px/600 `--c-heading`, gap 8px, crest 28px, radius `--radius` |
| `.public__mode` | absolute, top and right `var(--space-3)`; the button is 44×44 (share the `.signin__mode .icon-button` rule) |
| `.public__main` | `flex: 1`, `width: 100%`, `max-width: calc(var(--form-w) + 2 * var(--page-pad-x))`, centred, `margin-bottom: var(--space-8)`, `padding: var(--page-pad-x)`. At ≥768px: `--c-surface`, 1px `--c-border`, `--radius` (a card on the grey page) |
| `.public__main` below 768px | no border or radius, padding `var(--space-5)`, margin-bottom 0. Below 360px: padding `var(--space-4)` |
| `.public__title` | `--fs-title` (17.5px) / `--fw-medium`, `--lh-tight`, `--c-heading`, left-aligned, margin-bottom `var(--space-3)` |
| `.public__lead` | `--c-muted`, margin-bottom `var(--space-6)` |
| Footer | the shell's `.page-foot`, unchanged |
| `.public__title--centre` | `text-align: center`; used with a centred `.disc` above it on the one-message pages ("Check your email", "Request confirmed"). The body text on those pages stays left-aligned for reading |
| `.public__disc` | wrapper that centres the `.disc--64` and gives it `margin: 0 auto var(--space-4)` |

Contrast: all pairs are existing ones (f.md §9.5): heading on surface 12.44 / 8.96; muted on surface 5.61 / 5.26.

## States

- Light and dark follow `data-theme` like every page. The colour-mode button appears only with JS.
- `main` receives focus from the skip link; it has no visible outline (`main:focus` rule already exists).

## Reflow

No horizontal scroll at 320px: the column is fluid below `--form-w`, the brand line wraps, and the mode button sits in the head's corner, clear of the brand text (the head gets `padding-right: calc(var(--target) + var(--space-3))` below 768px so the words never run under the button).
