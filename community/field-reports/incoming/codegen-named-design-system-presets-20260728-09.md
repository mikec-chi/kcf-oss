# Field report — offer named design-system presets so look-and-feel is standardized across every generated app

```yaml
<!-- kcf-field-report:v1 -->
id: codegen-named-design-system-presets-20260728-09
kcfVersion: 1.11.0
commit: 1cd0475
phase: codegen
area: codegen
construct: design (design system) + codegen presets
severity: low
title: The pack ships one baseline theme (design-system-default.md); add named, selectable design-system presets so an org gets one standardized look across all generated apps
observation: >
  Look-and-feel is (correctly) out of the domain model — the pack applies
  `design-system-default.md` (brand-neutral) unless the model's `design` block overrides
  tokens. But there is exactly ONE preset. An org that wants every generated app to share
  a specific enterprise look (e.g. a dense, data-first "NetSuite-like" skin: hairline-bordered
  grid list views, underlined record subtabs, portlet dashboards, compact spacing, squared
  corners) has to hand-carry that as House-conventions overrides into every generation, or
  bake tokens into each model (which couples presentation to the domain). There is no
  first-class, named, swappable preset the generator can just apply everywhere.
evidence:
  commands:
    - "# today: design-system-default.md is the only baseline; overrides.md is per-run copy/paste"
    - "# desired: a preset registry the generator selects from as a generation setting"
  diagnostics:
    - "one baseline theme; no named alternative presets; standardization is manual per generation"
  snippet: |
    # A second preset, same shape as design-system-default.md:
    #   codegen/design-systems/netsuite.md  (tokens + component/layout conventions)
    # selected as a STACK/generation setting (applies to every app), e.g.
    #   generate-frontend.md: "Design system: netsuite"
    # and/or opted into per model without redefining it:
    #   design { design-system "netsuite" }     # model tokens still override brand values
    # Structure it decorates (grouped nav, COMPOSITION subtabs, MEASURE portlets,
    # master-detail) is already IR-derived — the preset is only the skin.
impact: >
  Every org standardizing UI across multiple generated apps. Without named presets, "make
  all our apps look like X" is repeated manual override work and drifts between apps; with
  them it is one selected setting, applied uniformly, model-agnostic.
suggestedChange: >
  Promote design systems to a small named registry under codegen/ (e.g.
  `design-systems/<name>.md`, with `default` as today's baseline). Let the active preset be a
  generation setting the generator reads (like a stack choice), applied to every app; a model
  MAY opt in via `design { design-system "<name>" }` and still override individual brand tokens.
  Document the preset contract (the token set + the component/layout conventions it standardizes)
  and show two presets over the SAME IR in an EXAMPLE, to make explicit that structure is
  model-derived and only the skin swaps. Purely codegen-guidance — no grammar/IR/analyzer change.
workaround: >
  Built a `design-system-netsuite.md` preset and applied it to the generated frontend as a
  one-line switch: the generator emits the preset's tokens into `tokens.css` (model design
  tokens layered on top as brand overrides) and stamps `<html data-design="netsuite">` to
  activate a scoped structural layer; flipping the preset name reverts to the default look.
domainSanitized: true
```
