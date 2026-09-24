# Password field with show/hide (superseded)

> **Superseded on 2026-09-24. The app does not have this component.**
>
> The owner said "login page design is different than the concept" and chose "Match the concept exactly". The sign-in page now follows `design/f-desk/login.html`, which has no Show/Hide button. The password is a plain `.field` with `.input` at full width, so `.field__row` and the `eye` symbol were removed.
>
> This spec is kept as a record. If a later brief (for example, a "set password" form) wants show/hide, it must reopen this with the owner first.

Origin: brief 004, D-7 (sign-in). This builds on f.md §7.5 fields. It was used on `registration/login.html`, and was planned for any later "set password" form.

## Anatomy

- `.field` contains:
  - `label.field__label`;
  - `p.field__help#password-help`, **above** the control;
  - `div.field__row`, containing the input and the button.
- `.field__row`: flex, gap 8px, align stretch. `.input` has `flex: 1; min-width: 0`.
- The button is `button.button.button--secondary`, `type="button"`, `data-toggle-password="password"`, `aria-pressed="false"`, `hidden`. It holds the `eye` icon at 16px and a `<span>` with the word `Show` (`Hide` when pressed). It is 44px tall.

Without JS the button stays `hidden`, and the input fills the row.

## States

| State | Input | Button |
|---|---|---|
| Masked (default) | `type="password"` | `Show`, `aria-pressed="false"` |
| Shown | `type="text"` | `Hide`, `aria-pressed="true"` |
| Invalid | `aria-invalid="true"`, 2px `--rule-strong` border in `--c-bad-text` | unchanged |
| Focus | f.md §7.5 focus | `--c-focus` ring, 2px offset |

Focus stays on the button when it toggles. The typed value is kept.

## Fit

At the 320px viewport the sign-in column is 260px wide. The button is about 84px, which leaves about 168px for the input. At 264px (desktop) it leaves about 172px.
