# Field report — import-dbml silently produces 0 entities on an unrecognized DBML dialect

```yaml
<!-- kcf-field-report:v1 -->
id: import-dbml-silent-noop-20260727-01
kcfVersion: 1.11.0
commit: 98468f5
phase: model
area: tooling
construct: kcf import-dbml
severity: high
title: import-dbml exits 0 with 0 entities when the source is a different DBML dialect (silent no-op)
observation: >
  `kcf import-dbml` targets the dbml.org "Table { ... [pk] }" syntax. When given a
  DBML file written in a different dialect that uses "entity { field ...: type }"
  blocks (a common project-specific DBML variant), the importer parses it, finds no
  "Table" declarations, and writes an IR with zero concepts and zero relationships —
  while exiting 0 and printing nothing. A user importing a real schema gets a silent
  empty model and no signal that nothing was captured.
evidence:
  commands:
    - kcf import-dbml other-dialect.dbml --id M --namespace m --output ir.json
    - "python -c \"import json;ir=json.load(open('ir.json'));print(len([c for c in ir['concepts'] if c['kind']=='ENTITY']))\"   # -> 0"
  diagnostics:
    - "(none — exit 0, no stdout, no warning)"
  snippet: |
    // A DBML dialect the importer does not recognize (entity/field, not Table/column):
    dbml model M {
      entity Account { field id: uuid { primary-key = true; } field name: string { required = true; } }
    }
    // -> imports to 0 entities, 0 relationships, silently.
impact: >
  High risk of silent data loss on adoption: someone points the importer at their
  real schema, sees a clean exit, and proceeds with an empty IR believing it worked.
suggestedChange: >
  Emit a warning (or non-zero exit) when a parsed DBML source yields 0 tables/entities,
  e.g. "import-dbml: parsed <file> but found 0 tables — is it dbml.org syntax?". Longer
  term, detect the dialect or document the accepted subset prominently in --help.
workaround: >
  Manually verify the imported IR entity count after every import.
domainSanitized: true
```


## Triage result — ACCEPTED, fixed

Reproduced. Fixed in this PR: the `kcf import-dbml` CLI handler (`tools/kcf.py`) and
`tools/import_dbml.py` now print a stderr warning naming the accepted dbml.org subset
and exit non-zero (2) **without** writing an empty model when 0 tables are parsed.
Domain-agnostic — only the table count is inspected.

Verified: `crm-module.dbml` (a non-dbml.org dialect) -> exit 2 + warning, no output
file; the dbml.org fixture still imports 3 entities at exit 0.
