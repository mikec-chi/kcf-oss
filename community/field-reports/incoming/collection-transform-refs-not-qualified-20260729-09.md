# Field report — `collectionTransforms.inputSchema` is not namespace-qualified, unlike every other entity reference in the IR

```yaml
<!-- kcf-field-report:v1 -->
id: collection-transform-refs-not-qualified-20260729-09
kcfVersion: 1.11.0
commit: 549b566
phase: codegen
area: tooling
construct: collectionTransforms.inputSchema / outputSchema (compiler/normalizer.py)
severity: low
title: collectionTransforms carries bare local entity names while actions/lifecycles/relationships all carry namespace-qualified ones, so a generator resolving refs uniformly silently drops the transform
observation: >
  Every entity reference in the IR is namespace-qualified — except the two on a
  collection transform.

      concepts[].qualifiedName    "eam.StockLedgerEntry"
      actions[].target            "eam.DocumentSeries"
      lifecycles[].subject        "eam.StructuralChangeRequest"
      relationships[].source      "eam.Building"
      collectionTransforms[].inputSchema   "StockLedgerEntry"     <- bare
      collectionTransforms[].outputSchema  "StockCard"            <- bare

  The cause looks incidental rather than intended: `normalizer.py:409-410` only renames
  the authoring keys —

      if "input" in transform and "inputSchema" not in transform:
          transform["inputSchema"] = transform.pop("input")

  — where the sibling reference paths run their value through the namespace qualifier.
  The authoring text is identical in shape either way (`inputSchema StockLedgerEntry;`
  mirrors `target Item;`), so nothing at the source level explains the difference.

  `collectionTransforms` entries also carry only `id`, no `qualifiedName`, while
  concepts, rules and policies carry both. So the collection is doubly inconsistent:
  its own identity is unqualified and so are its references.

  This is quiet rather than loud. A code generator that resolves entity references the
  same way everywhere — which is the reasonable implementation — looks up
  `"StockLedgerEntry"` in a map keyed by qualified name, misses, and skips the
  transform. Nothing errors. `kcf assess` still reports the model ready, coverage still
  counts `coverage.model.transformation` satisfied, and the realization manifest can
  still claim the transform is realized. The endpoint just never gets generated.
evidence:
  commands:
    - kcf compile m.kcf -o ir.json --validate
    - "python -c \"import json;ir=json.load(open('ir.json'));t=ir['collectionTransforms'][0];print(t['inputSchema'], '| concept:', ir['concepts'][0]['qualifiedName'], '| action target:', ir['actions'][0]['target'])\""
    - "grep -n 'inputSchema' kcf-oss/compiler/normalizer.py   # 409-410: renamed, not qualified"
  diagnostics:
    - "(none — the model compiles, validates and assesses ready; the inconsistency is only visible to a consumer resolving the reference)"
  snippet: |
    kcf model M profile operational-system {
      namespace m;
      entity LedgerEntry { identity id: UUID generated; required qty: Decimal; }
      entity Card { identity id: UUID generated; required qty: Decimal;
                    category reference; mutability "read-only"; }
      collection CardRollup {
        operation aggregate;
        inputSchema LedgerEntry;      // same shape as `target Item;` elsewhere
        outputSchema Card;
        grain "per item";
        bounded true;
      }
      // ... obligation-complete remainder omitted
    }
    // Compiled:
    //   concepts[0].qualifiedName            == "m.LedgerEntry"
    //   collectionTransforms[0].inputSchema  == "LedgerEntry"     <- not "m.LedgerEntry"
impact: >
  Affects code generation, which is the IR's whole purpose as a handoff contract. A
  generator either special-cases this one collection or silently drops every collection
  transform; we hit the second and only noticed because a test asserted the endpoint
  existed. It also weakens the realization manifest: `verify-realization` matches on
  identity strings, so a manifest can claim `StockCardRollup` is realized while the
  generator never resolved its source entity. The blast radius is small (two constructs
  in our model) but the failure is silent, which is what makes it worth fixing.
suggestedChange: >
  Qualify `inputSchema`/`outputSchema` in `normalizer.py` the way the sibling reference
  paths do, and emit a `qualifiedName` for each `collectionTransforms` entry so its own
  identity matches the convention used by concepts/rules/policies. Both are IR-shape
  changes, so they need a `model-ir-v1` compatibility note — a consumer keyed on the
  bare name today would need the qualified form.
  If the bare form is deliberate, the schema description for these two fields should say
  so explicitly, since the surrounding convention reads the other way.
  Either way a cheap invariant would have caught it: assert that every field the IR
  schema documents as an entity reference resolves against `concepts[].qualifiedName`.
  That is one test and it covers the whole class, not just this collection.
workaround: >
  A resolver that accepts either form: try the reference as-is, then fall back to
  matching the local part of each concept's qualified name.
domainSanitized: true
```

## Notes for triage

Reproduced on `mikec-chi/kcf-oss@549b566`, grammar-stack 1.11.0, Python 3.12.10 on
Windows.

Found while generating a FastAPI backend from a 721-identity IR: the transform endpoints
were missing from `/openapi.json` even though the manifest was ready to declare them
realized. Severity is `low` because the construct count affected is small and the
workaround is two lines — but the *silence* is the reportable part, and it is the same
shape as `import-dbml-silent-noop-20260727-01`: the pipeline reports success while
quietly producing less than the model specifies.

Sixth report in the 2026-07-29 batch; the other five are in this PR.
