# Field report — the metagrammar advertises `metadata { label; description }` but the compiler rejects it, and attributes have no label surface

```yaml
<!-- kcf-field-report:v1 -->
id: grammar-no-authorable-label-description-20260728-12
kcfVersion: 1.11.0
commit: 1cd0475
phase: model
area: grammar-gap
construct: concept/attribute metadata (label, description)
severity: medium
title: Human label/description is not authorable — the metagrammar shows a metadata label/description block the reference compiler does not parse, and attributes accept no label at all
observation: >
  There is no way to give a concept or attribute a human label/description in the model, so
  a domain term the identifier can't convey (acronyms like TIN/BIR/PCAB, phrasings like
  "PO→SO TAT (days)") cannot override a codegen-derived label. Worse, this is also a
  doc↔parser drift: the core metagrammar advertises a metadata block WITH label/description,
  but the reference compiler rejects both that block and any attribute-level label block.
evidence:
  commands:
    - "kcf compile has-attr-label.kcf   # ParseError: expected ';', found '{'  (attribute block)"
    - "kcf compile has-meta-label.kcf   # ParseError: expected identifier, found '{'  (metadata block)"
  diagnostics:
    - "grammars/core/KCF-v1.0-Semantic-Metagrammar.ebnf:103-104 -> metadata = '{' ['label' ':' string ';'] ['description' ':' string ';'] ... '}'"
    - "compiler/parser.py rejects both `attr: T { label: ... }` and `metadata { label: ... }`"
    - "IR attribute objects carry only {name,type,required,identity,default} — no label/description"
  snippet: |
    entity Widget {
      identity id: UUID;
      required tinNumber: String { label: "TIN"; }      // rejected by parser
      metadata { label: "Gadget"; description: "..."; }   // rejected by parser
    }
    # Neither the attribute label block nor the metagrammar's metadata{label} parses.
impact: >
  Any model whose domain labels differ from their identifiers (most real domains have
  acronyms/regulatory terms): the UI label can only be code-derived and can't be corrected in
  the model. And the metagrammar overstating the implemented surface is a trust/drift issue.
suggestedChange: >
  Implement authorable, ADVISORY `label` and `description` on both concepts and attributes
  (reconciled/ignored by the analyzer like other advisory metadata), projecting to
  `concept.label/description` and `attribute.label/description` in the IR; codegen uses them as
  the label, falling back to the humanize() derivation. Align the reference compiler with the
  metagrammar's metadata block (or correct the metagrammar). Grammar/IR + compiler change →
  Grammar RFC + VERSIONING (additive; labels optional, derivation remains the default).
workaround: >
  Codegen derives labels from identifiers (see the companion codegen report); domain acronyms
  are carried in a small stack-side acronym set until model labels exist.
domainSanitized: true
```

## Triage result — ACCEPTED — routed to a Grammar RFC (contract change)

Confirmed on both counts. (1) The doc↔parser drift is real: the metagrammar's `metadata`
production (`grammars/core/KCF-v1.0-Semantic-Metagrammar.ebnf:103-104`) advertises
`metadata { label; description; … }` and is wired into the *meta* definitions (`concept-kind-def`,
`trait-def`, `profile-def`), but **not** into entity/attribute authoring — `parse_concept`'s
catch-all treats an unknown keyword as a scalar metadata pair, so an entity `metadata { … }`
block and an attribute `attr: T { label: … }` block both fail to parse. (2) There is genuinely
no authorable human label/description on concepts or attributes.

Per the field-report routing (`community/field-reports/README.md`) and the one rule for core
changes (`CLAUDE.md`), a grammar/IR + compiler change **must not** land silently — it goes
through a Grammar RFC + a VERSIONING decision. Registered as **RFC-10** in
`docs/IR-ROADMAP.md`: an additive, advisory `label`/`description` on concepts and attributes
(analyzer-ignored like other advisory metadata) projecting to `concept.label/description` and
`attribute.label/description`, plus reconciling the reference compiler with the metagrammar's
`metadata` block at the entity/attribute level (or correcting the metagrammar if the block is
not intended there). The **default UX is unaffected in the meantime** — codegen already derives
labels via `humanize()` (rule 12, companion report `20260728-11`); model labels, once landed,
simply override the derivation. No silent grammar/IR/analyzer contract change was made here.
