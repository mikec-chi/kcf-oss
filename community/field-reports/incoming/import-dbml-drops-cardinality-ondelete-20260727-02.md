# Field report — import-dbml drops relationship cardinality and on_delete

```yaml
<!-- kcf-field-report:v1 -->
id: import-dbml-drops-cardinality-ondelete-20260727-02
kcfVersion: 1.11.0
commit: 98468f5
phase: model
area: source-fidelity
construct: kcf import-dbml (relationship import)
severity: medium
title: import-dbml preserves ref direction but discards cardinality and on_delete from [ref: ... , delete: ...]
observation: >
  A dbml.org ref like "account_id uuid [ref: > accounts.id, delete: cascade]" carries
  a many-to-one cardinality and a cascade delete. import-dbml correctly infers
  COMPOSITION vs ASSOCIATION (it uses delete:cascade to pick COMPOSITION), but the
  resulting relationship has cardinality:None and no on_delete qualifier — so both the
  multiplicity and the cascade semantics are dropped.
evidence:
  commands:
    - kcf import-dbml kcf-oss/tests/fixtures/source/crm.dbml --id CrmFixture --namespace crm --output ir.json
    - "python -c \"import json;print([{'k':r['rootKind'],'card':r.get('cardinality')} for r in json.load(open('ir.json'))['relationships']])\""
  diagnostics:
    - "relationship contacts->accounts: rootKind=COMPOSITION, cardinality=None (source was [ref: > , delete: cascade])"
  snippet: |
    Table contacts {
      id uuid [pk]
      account_id uuid [ref: > accounts.id, delete: cascade]   // many-to-one + cascade
    }
    // imported relationship: COMPOSITION contacts->accounts, cardinality=None, no on_delete
impact: >
  Downstream codegen can't distinguish one-to-many (master-detail grid / child tab) from
  one-to-one (single embedded panel), and loses cascade/orphan semantics — the RELATIONSHIP
  algebra defines cardinality/roles, so this is capturable, just not captured on import.
suggestedChange: >
  Populate the relationship `cardinality` (from the ref operator > / < / -) and carry
  on_delete as a qualifier during import; surface both so UI/backend generation can use them.
workaround: >
  Hand-add `cardinality one to many` (and roles) to composition relationships after import.
domainSanitized: true
```
