# Field report — design page `section`s can't bind fields, so record field-grouping can't be model-driven

```yaml
<!-- kcf-field-report:v1 -->
id: grammar-design-sections-cannot-bind-fields-20260728-10
kcfVersion: 1.11.0
commit: 1cd0475
phase: model
area: grammar-gap
construct: design (page sections) / experience
severity: low
title: A design page `section` is a bare name with no field assignment, so a NetSuite-style grouped record layout (titled field-groups) cannot be expressed in the model
observation: >
  Real enterprise record screens group an entity's fields into titled sections ("Primary
  Information", "Classification", "Financials", "System"). The grammar has `design { page P {
  view V; section Header; } }`, but a `section` is only a NAME — it cannot list which of the
  entity's attributes belong to it. So the codegen has no model signal for field grouping and
  must fall back to a heuristic (group by field role). The intent is authorable at the page
  level but not down to the field, so the record layout can't be driven by the model.
evidence:
  commands:
    - kcf compile model.kcf -o ir.json --validate
    - "python -c \"import json;print(json.load(open('ir.json'))['design']['pages'])\""
    - "# -> [{'id':'AccountPage','view':'AccountView','sections':['Header']}] — sections are bare strings"
  diagnostics:
    - "ir.design.pages[].sections is a string[]; no field membership; model-ir schema leaves pages open"
  snippet: |
    design {
      design-system Baseline { token Primary: color = "#1f5c99"; }
      page OrderPage {
        view OrderView;
        section Header;            // <- just a name; cannot say which fields live here
        // desired: section "Primary" { field name; field status; }
        //          section "Amounts" { field total; field tax; }
      }
    }
    # Codegen can render titled field-groups, but only by heuristic — the modeler cannot
    # state the grouping even though the domain knows it.
impact: >
  Any app wanting a grouped record layout (most enterprise UIs): the grouping is guessed by
  the generator rather than declared, so it can't reflect domain-meaningful sections and can't
  be reviewed/versioned as part of the model. The page-level `section` reads like it should
  carry fields but doesn't.
suggestedChange: >
  Extend the `design` page `section` (or add a record-layout construct) so a section can
  enumerate the entity attributes it contains (and optionally order/columns), projecting into
  `ir.design.pages[].sections[]` as objects `{ id, fields: [...] }` rather than bare strings.
  Codegen then renders model-declared field-groups, with the by-role heuristic as the fallback
  when a page declares none. Grammar/IR change → route via a Grammar RFC + VERSIONING (additive:
  a section may remain a bare string; the object form is opt-in).
workaround: >
  The generated frontend groups fields by a domain-agnostic heuristic (Primary / Details /
  Amounts / Flags / Dates / System) into titled field-group cards — a reasonable default, but
  not the domain's own sectioning.
domainSanitized: true
```
