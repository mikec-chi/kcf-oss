# `default` preset — the brand-neutral baseline

The `default` design-system preset **is** the baseline in
[`../design-system-default.md`](../design-system-default.md): a neutral slate + single calm
accent, comfortable density, system font stack, WCAG-AA contrast, light/dark. It is applied
whenever no other preset is selected and no model `design` block is declared.

See [`../design-system-default.md`](../design-system-default.md) for the full token set and
component conventions — this file is the registry entry that names it as the `default`
preset; the tokens/conventions are not duplicated here so the baseline has one source.

- **Tokens**: the complete set in `../design-system-default.md`.
- **Component & layout conventions**: comfortable density; filled/bordered/destructive
  buttons at `--radius-md`; label-above-input forms; zebra list rows with the data-grid
  conventions (system-prompt rule 13); semantic-color status badges; humanized labels
  (system-prompt rule 12).

To standardize on a different look org-wide, select another preset from
[`README.md`](README.md) as a generation setting; model `design` tokens still override
brand values on top of whichever preset is active.
