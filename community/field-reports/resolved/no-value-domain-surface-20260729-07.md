# Field report — the authoring grammar has no value-domain surface, so a source enumeration has no first-class home

> **Routing note:** `area: grammar-gap`. Per [`README.md`](../README.md) this routes to a
> **[Grammar RFC](../../../kcf-oss/docs/EXTENDING.md)** plus a
> **[VERSIONING](../../../kcf-oss/docs/VERSIONING.md)** decision, not a direct change.
> This report is the observation and the evidence for that decision; it deliberately does
> **not** propose a concrete grammar production.

```yaml
<!-- kcf-field-report:v1 -->
id: no-value-domain-surface-20260729-07
kcfVersion: 1.11.0
commit: 549b566
phase: model
area: grammar-gap
construct: attribute-decl / AUTHORING v1.2
severity: medium
title: There is no way to declare an attribute's allowed value set, so source enumerations survive only as prose a generator cannot check
observation: >
  `KCF-AUTHORING-v1.2.ebnf` has no enum, allowed-values, value-domain, or codelist
  production; a case-insensitive search for those terms returns nothing. `attribute-decl`
  offers a type, a cardinality, an optional default, and `{ qualifier }` where
  `qualifier = "generated" | identifier` — single bare identifiers, with no way to attach
  a list of permitted values.

  Sources routinely state these sets. A relational schema has CHECK constraints and
  lookup tables; a requirements document says "status is new, active, or retired"; the
  structured source we transcoded declared 9 enumerations and bound named fields to
  them. All of it is real, checkable domain knowledge, and none of it has a home.

  The available encodings each lose something different:
    - `required status: String;` — loses the domain entirely.
    - a free-form qualifier (`String enum_item_status`) — preserves the domain's
      *name* in `attributes[].qualifiers`, but not its members.
    - `proposition StatusValues { expression "status is one of a, b, c"; mode necessary; }`
      — preserves the members as a human-readable string, unparsed and unenforceable, and
      lands in `ir["propositions"]`, which `source-coverage` does not read (see
      source-coverage-blind-to-five-collections-20260729-04).
    - `rule ... { kind CLASSIFICATION; condition "..."; }` — same prose problem, and needs
      an `effect`/`applies-to`/`authority` the source has no basis for.

  We used the second and third together. The result is that a code generator sees the
  name of a value domain and a sentence describing it, and cannot emit a constraint, a
  DB enum, a TypeScript union, or a validation rule from either.
evidence:
  commands:
    - "grep -ciE 'enum|allowed-values|value-domain|codelist' kcf-oss/grammars/authoring/KCF-AUTHORING-v1.2.ebnf   # -> 0"
    - "grep -n 'attribute-decl\\|^qualifier' kcf-oss/grammars/authoring/KCF-AUTHORING-v1.2.ebnf"
    - kcf compile enum-attempt.kcf -o ir.json --validate
    - "python -c \"import json;print(json.load(open('ir.json'))['concepts'][0]['attributes'])\"   # qualifiers carry a name, never members"
  diagnostics:
    - "(none — every encoding above compiles clean; the loss is silent by construction)"
  snippet: |
    // The grammar productions, verbatim:
    //   attribute-decl = attribute-modifier, identifier, ":", qualified-name,
    //                    [ "=", scalar ], [ cardinality ], { qualifier }, ";" ;
    //   qualifier      = "generated" | identifier ;
    //
    // So the closest available encodings are:
    kcf model M profile operational-system {
      namespace m;
      entity Item {
        identity id: UUID generated;
        required status: String = "new" enum_item_status;   // name only, no members
      }
      proposition EnumItemStatus {                          // members as prose
        expression "item_status is one of new, active, retired";
        mode necessary;
      }
      // ... obligation-complete remainder omitted
    }
    // Neither encoding is machine-checkable, and the proposition is additionally
    // invisible to source-coverage.
impact: >
  Affects any model built from a real schema or specification, which is most of them —
  enumerations are one of the most common things a source states precisely. The cost is
  concentrated where KCF's value proposition is strongest: the IR is meant to be a
  contract a generator can build from without guessing, and here the generator must
  either guess the value set or drop the constraint. It also weakens the
  extraction-fidelity story, since a set stated exactly in the source becomes prose in
  the model.
suggestedChange: >
  None proposed — this is an RFC-shaped decision, not a patch, and it touches
  `attribute-decl`, the `model-ir-v1` attribute shape, the analyzer, and codegen
  guidance. The evidence above is offered as the input to that decision.
  Two things worth settling in the RFC, from the transcoding experience: whether a value
  domain is a named, reusable top-level construct (sources share one enumeration across
  many attributes — ours bound several fields to the same set) or an inline per-attribute
  list; and whether the members are opaque tokens or can carry a label and an ordering,
  since sources commonly supply both.
workaround: >
  Emit the domain name as a free-form attribute qualifier plus one `proposition` per
  enumeration carrying the members as a necessary-mode expression, and record the loss
  explicitly in the project's mapping notes so nobody downstream mistakes the prose for
  an enforced constraint.
domainSanitized: true
```

## Notes for triage

Reproduced on `mikec-chi/kcf-oss@549b566`, grammar-stack 1.11.0, Python 3.12.10 on
Windows.

Raised as a secondary note in the triage section of
`ordering-dimension-qualifier-catch-22-20260729-03`; filed separately because it is a
grammar-gap and therefore routes differently from the tooling reports in that batch.

Context: encountered while transcoding a 9-language DSL model family into KCF. Of
everything that did not survive the translation, this was the single largest fidelity
loss — the model reaches `ready: true` with 0 required gaps and full CRUD, and still
cannot say which values a status field may take.

## Triage result — ACCEPTED — routed to a Grammar RFC (contract change)

Confirmed: `KCF-AUTHORING-v1.2.ebnf` has no enum / allowed-values / value-domain / codelist
production, and `attribute-decl`'s `{ qualifier }` is bare identifiers, so a source enumeration
survives only as a qualifier *name* or an unparsed `proposition` string — neither
machine-checkable. This is a real, load-bearing part of a domain model, but it changes
`attribute-decl`, the `model-ir-v1` attribute shape, the analyzer, and codegen, so per the
field-report routing and the one rule for core changes it goes through a Grammar RFC + a
VERSIONING decision, never a silent change. Registered as **RFC-12** in `docs/IR-ROADMAP.md`,
carrying the report's two open design questions (named/reusable value domain vs inline list;
opaque tokens vs label+ordering). The companion source-coverage fix
(`source-coverage-blind-to-five-collections-20260729-04`) independently removes the secondary
loss the report noted — a value-domain `proposition` is now at least traceable. No grammar / IR
change was made here.
