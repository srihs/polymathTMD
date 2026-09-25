# Form section (`.formsection`)

Origin: brief 005, the public Zoom request form (`The class`, `When`, `About you`). For any long form that splits into a few named groups.

**Why a new component:** `.options` legends are label-sized (14px/500) because they introduce one question. A section groups several questions and needs to read one step up, without being a heading (a legend keeps the group's name attached to every field inside it for screen readers, and the page outline stays h1 → content).

## Anatomy

```html
<fieldset class="formsection">
  <legend class="formsection__title">The class</legend>
  …fields…
</fieldset>
```

## Values

| Part | Spec |
|---|---|
| `.formsection` | `min-width: 0; margin: 0 0 var(--space-6); padding: var(--space-5) 0 0; border: 0; border-top: var(--rule) solid var(--c-border)` |
| First section | no top border or padding when it is the form's first child (`.formsection:first-of-type`) |
| `.formsection__title` | `float: left; width: 100%; margin-bottom: var(--space-4); padding: 0;` `--fs-card-title` (15.4px) / `--fw-medium`, `--lh-tight`, `--c-heading`. The float makes the legend sit inside the fieldset's box like normal text instead of on its border |
| After the legend | the first child needs `clear: both` (use `.formsection__title + * { clear: both }`) |

Contrast: `--c-heading` on `--c-surface` 12.44 (light) / 8.96 (dark). The rule is decorative.

## States

None of its own. Fields inside keep their own error states. A section with errors isn't styled differently: each field says what's wrong.

## Related modifiers on the ported `.options` (defined with it, listed here so they live in one place)

| Modifier | Spec | Used for |
|---|---|---|
| `.options--group` | a bordered sub-group inside a section: `padding: var(--space-4); border: var(--rule) solid var(--c-border); border-radius: var(--radius)`; its `legend` keeps the `.options legend` style with `padding: 0 var(--space-1)` so it sits on the border | `If it's every week` (weekdays + last date) |
| `.options__list--two` | `grid-template-columns: repeat(2, minmax(0, 1fr))` at ≥600px, one column below | `Just once` / `Every week` |
| `.options__list--four` | `repeat(4, minmax(0, 1fr))` at ≥600px, `repeat(2, …)` below | the seven weekdays |
| `.options__list--stack` | one column at every width | `Book it on` (host accounts) |

## Nesting

A `.formsection` may hold `.options` fieldsets (radio or checkbox groups). Don't nest a `.formsection` in another.
