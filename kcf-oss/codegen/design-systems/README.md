# Design-system presets — one selectable look across every generated app

Look-and-feel is deliberately **out of the domain model**: the IR carries *structure*
(entities, relationships, lifecycles, nav from aggregate roots, COMPOSITION subtabs,
MEASURE portlets, master-detail) and, optionally, a model's own `design` tokens. A
**design-system preset** is the *skin* the generator paints over that structure — a named,
swappable bundle of tokens + component/layout conventions. Selecting a different preset
changes only the appearance; the same IR produces the same screens, nav, and controls.

This is the fix for "make all our apps look like X": instead of hand-carrying House
Conventions overrides into every generation (which drifts app-to-app), an org picks **one
preset as a generation setting** and every generated frontend shares that standardized look.

## The registry

One preset = one file, `codegen/design-systems/<name>.md`:

| Preset | Look |
|---|---|
| [`default`](default.md) | The brand-neutral, accessible baseline (`../design-system-default.md`). Applied when nothing else is selected. |
| [`dense-enterprise`](dense-enterprise.md) | A dense, data-first skin: hairline-bordered grid list views, underlined record subtabs, portlet dashboards, compact spacing, squared corners. |

Add a preset by dropping another `<name>.md` with the same shape. Presets are **additive
and domain-agnostic** — a preset never references a domain concept, and adding one changes
no grammar / IR / analyzer contract.

## The preset contract (what every preset file declares)

A preset decorates structure the IR already fixes; it standardizes exactly two things:

1. **Tokens** — the same token set as [`../design-system-default.md`](../design-system-default.md)
   (color, typography, spacing, radius, border, shadow, motion, layout), emitted as CSS
   custom properties (or the stack's token mechanism) and referenced everywhere. A preset
   MAY add extra tokens, but MUST define the baseline set so any stack can consume it.
2. **Component & layout conventions** — the skin decisions that aren't a single token:
   list-view chrome (grid borders vs zebra), record layout (subtabs vs stacked sections),
   dashboard layout (portlets vs cards), density, control shape. These decorate the
   IR-derived structure; they never add or drop a screen, field, or control.

A preset MUST NOT encode domain meaning, per-model overrides, or anything that belongs in
the IR. If a look needs the *structure* to change (e.g. model-declared field groups), that
is a model/grammar concern, not a preset — see the design-section Grammar RFC in
[`../../docs/IR-ROADMAP.md`](../../docs/IR-ROADMAP.md).

## Selecting a preset (precedence, lowest → highest)

1. **`default`** — used when nothing else is selected.
2. **Generation setting** — the active preset for the run, set in the frontend prompt
   (`generate-frontend.md` → *Design system: `<name>`*). This is the org-wide standardizer:
   set it once and every app gets that look.
3. **Model `design` tokens** — if the model authors a `design { design-system … }` block,
   those token *values* override the preset's tokens (brand colors, spacing) while the
   preset's component/layout conventions still apply. Declared model design is meaning and
   always wins over a preset's default values.
4. **House Conventions** — a team's `overrides.md` still has the last word (as today).

> Selecting a preset by **name** is a generation setting, so it needs **no grammar change**.
> (Binding a *model* to a named preset — `design { design-system "dense-enterprise" }` as a
> reference rather than an inline definition — would need the design grammar to accept a
> preset reference; that is deliberately left to the design Grammar RFC and is not required
> for org-wide standardization, which the generation setting already delivers.)

## How the generator applies the active preset

- Emit the preset's tokens into the stack's token file (e.g. `tokens.css`), then layer any
  model `design` token values on top as brand overrides.
- Activate the preset's structural layer by stamping the preset name on the root
  (e.g. `<html data-design="dense-enterprise">`) and scoping the component/layout
  conventions to it, so flipping the preset name reverts cleanly to another look.
- Everything structural (which screens, which nav, which subtabs, which portlets) stays
  **IR-derived** and identical across presets. Prove it in the coverage self-audit: the
  disposition set does not change when the preset changes.
