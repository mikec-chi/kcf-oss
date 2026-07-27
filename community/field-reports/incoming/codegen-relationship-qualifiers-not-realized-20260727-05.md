# Field report — codegen ignores COMPOSITION qualifiers (on-delete, required-parent), producing orphanable parts

```yaml
<!-- kcf-field-report:v1 -->
id: codegen-relationship-qualifiers-not-realized-20260727-05
kcfVersion: 1.11.0
commit: c031be6
phase: codegen
area: codegen
construct: relationship (COMPOSITION qualifiers)
severity: high
title: Generated backend drops COMPOSITION on-delete and existential-dependency, so parts orphan on parent delete and can be created parentless
observation: >
  A COMPOSITION relationship carries qualifiers (cardinality one-to-many, on-delete
  cascade). The IR preserves them (relationship.qualifiers), but the codegen realizes
  the relationship as a plain nullable FK: (a) the child FK is nullable, so a part can
  be created with no parent (orphan), and (b) deleting the parent does NOT cascade —
  the children remain as dangling rows. The declared on-delete and the existential
  dependency implied by COMPOSITION are both lost.
evidence:
  commands:
    - "POST /actions/CreateChild {}                 # no parentId -> 200, parentId=null (orphan part)"
    - "DELETE /actions/DeleteParent/{id}            # -> 204; child still queryable (not cascaded)"
    - "grep -n on_delete|cascade app/*.py           # -> no matches (qualifier never consulted)"
  diagnostics:
    - "child persists after parent delete despite on-delete cascade in the IR"
  snippet: |
    entity Parent { attribute name : string { required; } }
    entity Child  { attribute label : string { required; } }
    relationship Owns {
      kind composition;
      Parent -> Child { cardinality one-to-many; on-delete cascade; }
    }
    # Codegen -> Child.parentId nullable, no cascade; orphan + dangling both possible.
impact: >
  Any model using COMPOSITION with on-delete or a required part: the generated app
  violates the aggregate's integrity guarantees. Parts outlive their whole and can be
  created without one — the exact invariants COMPOSITION is meant to encode.
suggestedChange: >
  Codegen guidance for COMPOSITION should (1) make the child FK NOT NULL and required in
  the Create schema (a part cannot exist without its whole), and (2) realize `on-delete`
  (cascade -> delete children in the same tx; restrict -> block; set-null -> null the
  FK). Map these from relationship.qualifiers in CONSTRUCT_COVERAGE.md and show a worked
  cascade in a stack EXAMPLE.
workaround: >
  In the generated service.delete, cascade to composition children; make composition
  child FKs non-nullable and required in the Create schema.
domainSanitized: true
```
