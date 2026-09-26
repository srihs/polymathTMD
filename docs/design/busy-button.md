# Busy submit button (`data-busy-text`)

Origin: brief 006 (live Zoom connection). `Approve and email the link` now waits for Zoom (a fresh lookup, then the create: usually 1 to 3 seconds, about 30 at worst), and `Check connection` makes three Zoom calls. For any full-page POST that calls another service and can take more than a second or two.

**Why it's new:** nothing in the app says "we're working on it" after a submit. Without it, a non-technical user sees nothing happen and presses again, or leaves. The server is already safe against double submits (brief 006, criterion 32). This is only about reassurance and clear feedback. It is an **enhancement only**: with no JS, the form posts normally and the browser shows its own loading indicator.

## Anatomy

```html
<form method="post" action="…" data-busy-form>
  …
  <div class="form-actions">
    <button class="button button--primary" type="submit" data-busy-text="Making the meeting in Zoom…">Approve and email the link</button>
    <p class="visually-hidden" role="status" data-busy-status></p>
  </div>
</form>
```

- `data-busy-form` goes on the `<form>`.
- `data-busy-text` goes on the one submit button whose text changes.
- `data-busy-status` is an empty, visually hidden live region inside the same form. It is always in the markup, so screen readers register it before it gets text.
- When the button sits outside the form it submits (it uses the `form="…"` attribute, as `Check connection` does), `data-busy-form` still goes on the `<form>`. The JS finds the button through `form.querySelector('[data-busy-text]')` **or** `document.querySelector('[form="' + form.id + '"][data-busy-text]')`. The live region then sits beside the button.

## Behaviour (`app.js`, one small block, hooks only)

1. On the form's `submit` event:
   - if the form is already marked busy (`form.dataset.busy === "true"`), call `preventDefault()` and stop, so a second press does nothing;
   - otherwise set `form.dataset.busy = "true"`, set `aria-disabled="true"` on the button, replace the button's **text** (keep any icon) with `data-busy-text`, and write the same text into `[data-busy-status]`.
   - Don't set the `disabled` attribute: a disabled button loses focus, and the screen reader's position with it.
2. On `pageshow` with `event.persisted` (the user comes back through the browser's back/forward cache): restore the original text, remove `aria-disabled`, empty the status and clear `data-busy`.
3. There's no timeout and no spinner. The next page (a redirect or a re-render) replaces everything.

## Values

| Part | Spec |
|---|---|
| Button, busy | the same colours and size as its idle variant (`.button--primary` or `.button--secondary`). `cursor: progress`. No opacity change, because the text change is the cue and the contrast has to stay AA |
| CSS selector | `.button[aria-disabled="true"] { cursor: progress; }` (next to the other `.button` rules in section 5d) |
| Live region | `.visually-hidden`, `role="status"` (polite) |
| Motion | none, so nothing is needed for `prefers-reduced-motion` |

## States

| State | Button text | `aria-disabled` | Status region |
|---|---|---|---|
| Idle | its label, e.g. `Approve and email the link` | absent | empty |
| Busy | `data-busy-text`, e.g. `Making the meeting in Zoom…` | `true` | the same text |
| Back from bfcache | idle again | absent | empty |

## Copy rule

The busy text says what the system is doing, in the user's words, as a present-tense phrase ending in `…`. It is never just `Loading…` or `Please wait…`.

## Used by

| Page | Button | `data-busy-text` |
|---|---|---|
| `zoom/detail.html` | `Approve and email the link` | `Making the meeting in Zoom…` when `checks_zoom`; `Approving…` otherwise |
| `zoom/account_form.html` | `Check connection` | `Checking with Zoom…` |
