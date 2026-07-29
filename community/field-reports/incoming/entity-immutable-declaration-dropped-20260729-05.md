# Field report — `immutable;` on an entity parses and is then discarded; the projection is gated on EVENT

```yaml
<!-- kcf-field-report:v1 -->
id: entity-immutable-declaration-dropped-20260729-05
kcfVersion: 1.11.0
commit: 549b566
phase: compile
area: analyzer
construct: immutable-decl (compiler/normalizer.py)
severity: medium
title: An entity declaring `immutable;` compiles clean but the flag appears nowhere in the IR, so it exempts nothing and silently means nothing
observation: >
  `concept-member` in the authoring grammar includes `immutable-decl`, so `immutable;`
  is legal inside any concept body, entity included. It parses without complaint.

  The normalizer only projects it for events. `normalizer.py:153` opens
  `if concept["kind"] == "EVENT":` and the `"mutable": not
  declaration.values.get("immutable", False)` line sits inside that branch. For an
  ENTITY the parsed value is read by nothing and written nowhere: the compiled concept
  has no `immutable` field, no `mutable` field, no `traits` entry, and `metadata`
  containing only what other lines put there.

  So an author marking an append-only ledger `immutable;` gets a clean compile, a valid
  model, and zero effect. It does not exempt the entity from any coverage obligation
  (`_is_exempt` in coverage_report.py:201-208 looks at `metadata.mutability`,
  `metadata.readOnly`, `metadata.category`, and `concept.traits` — none of which the
  declaration sets), it does not reach a generator, and it produces no warning telling
  the author their declaration was inert.

  The working encoding turns out to be `mutability "read-only";`, which is a *metadata*
  line rather than the dimension declaration the grammar advertises. Nothing in the
  authoring surface points you from one to the other.
evidence:
  commands:
    - kcf compile immutable-entity.kcf -o ir.json --validate    # exit 0, no diagnostics
    - "python -c \"import json;c=[x for x in json.load(open('ir.json'))['concepts'] if x['kind']=='ENTITY'][0];print(json.dumps(c,indent=2))\""
    - "python -c \"import re,pathlib;s=pathlib.Path('kcf-oss/compiler/normalizer.py').read_text();print('EVENT-gated:', 'if concept[\\\"kind\\\"] == \\\"EVENT\\\"' in s)\""
  diagnostics:
    - "(none — exit 0, and no warning that the declaration had no effect)"
  snippet: |
    kcf model M profile operational-system {
      namespace m;
      entity Ledger {
        identity id: UUID generated;
        required amount: Decimal;
        category transactional;
        immutable;                 // <- parses, then vanishes
      }
      // ... obligation-complete remainder omitted
    }
    // Compiled concept, verbatim:
    //   {"id":"Ledger","qualifiedName":"m.Ledger","kind":"ENTITY","references":[],
    //    "attributes":[...],"metadata":{"category":"transactional"}}
    // No `immutable`, no `mutable`, no `traits`. Replacing the line with
    // `mutability "read-only";` DOES land in metadata and DOES exempt.
impact: >
  Two costs. First, silent no-op: an author states a real, load-bearing fact about the
  data — these records are never modified — and the model does not carry it, so
  downstream code generation is free to emit update and delete paths for an append-only
  ledger. Second, it makes coverage exemption unreachable through the surface that looks
  like the right one: the entity keeps attracting write and lifecycle obligations, which
  pushes the author toward exactly the over-modeling that
  coverage-over-modeling-20260727-01 was resolved to prevent.
suggestedChange: >
  Either project it or reject it — the current middle ground is the harmful option.
  Preferred: move the `immutable` read out of the EVENT-gated branch and project it for
  any concept kind, as `metadata.mutability = "read-only"` (so `_is_exempt` and the
  category reconciliation pick it up for free with no contract change) or as a first-class
  `immutable: true` plus a matching clause in `_is_exempt`.
  If entity-level immutability is deliberately out of scope, make the parser reject
  `immutable-decl` outside EVENT and remove it from `concept-member` in the grammar, so
  the authoring surface stops advertising a declaration that does nothing.
  Either way, a general guard is worth having: assert that every value the parser stores
  is read by the normalizer for at least one concept kind. A parsed-but-never-projected
  field is invisible by construction.
workaround: >
  Use `mutability "read-only";` instead of `immutable;` on entities. It lands in
  `metadata`, exempts the write obligations via `_is_exempt`, and is what the coverage
  evaluators actually read.
domainSanitized: true
```

## Notes for triage

Reproduced on `mikec-chi/kcf-oss@549b566`, grammar-stack 1.11.0, Python 3.12.10 on
Windows. The snippet is the whole reproducer; swapping the one line changes the outcome.

Found while transcoding a structured source in which three entities were explicitly
tagged immutable (append-only ledgers). The obvious encoding compiled clean and did
nothing, which cost a round of debugging to notice — there is no signal at all that the
declaration was dropped.

Related: `lifecycle-obligation-ignores-exempt-20260729-06`, filed alongside this one.
Even with the working `mutability "read-only"` encoding, the lifecycle obligation still
recommends a lifecycle for those entities, because its evaluator does not consult
`_is_exempt`. The two together are why an immutable ledger cannot currently be modelled
without leaving a coverage gap open.
