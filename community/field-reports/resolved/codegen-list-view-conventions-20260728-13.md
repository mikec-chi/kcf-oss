# Field report — list views need standard data-grid conventions: hide identity columns, sortable headers, faceted filters

```yaml
<!-- kcf-field-report:v1 -->
id: codegen-list-view-conventions-20260728-13
kcfVersion: 1.11.0
commit: 1cd0475
phase: codegen
area: codegen
construct: frontend UI (list view)
severity: medium
title: The generated list view should apply standard data-grid conventions — drop identity/UUID columns, sortable column headers, and faceted filters — all derivable from the registry
observation: >
  The generated list/table view falls short of a usable enterprise grid in three
  domain-agnostic ways: (1) it renders the identity (UUID) column, which is long, low-value,
  and wastes horizontal space when rows are already click-through to the record; (2) columns
  are not sortable; (3) there is only a global text search, no per-column filtering. All three
  are derivable from the entity registry (field.identity / idField, field.type, enum options,
  hasLifecycle) with no domain knowledge and no grammar/IR change.
evidence:
  commands:
    - "# list columns include the UUID identity; headers are static; only a global search box exists"
  diagnostics:
    - "identity column shows a 36-char UUID per row; no column is sortable; no facet filters"
  snippet: |
    // registry already carries what's needed:
    //   field.identity / meta.idField  -> exclude from columns
    //   field.type == boolean, optionsFor(entity,field) != null, meta.hasLifecycle('state')
    //     -> categorical => a facet filter (options = distinct values present in the data)
    // conventions:
    //   columns  = first N non-identity, non-freetext fields (+ lifecycle state)
    //   sort     = click header to sort asc/desc, with an indicator
    //   filter   = free-text search + faceted dropdowns for categorical columns
    //   paginate = page the filtered+sorted rows
  impact: >
    Every generated app's primary browse surface: without these it reads as a skeleton table.
    They are the baseline expectations of a list/grid (NetSuite/Salesforce/Airtable all have
    them) and are fully model-derivable, so they should be a codegen convention, not per-app work.
suggestedChange: >
  Document a list-view convention in the codegen pack (CONSTRUCT_COVERAGE.md / frontend EXAMPLE):
  exclude identity columns (and free-text blobs) from the grid; make column headers sortable
  (toggle asc/desc, show the active sort); provide a filter bar = free-text search + faceted
  dropdowns for categorical columns (enum via the value set, boolean, lifecycle state), with
  options taken from the data; paginate the result. All derived from the registry; no grammar/IR
  change. Pairs with the human-label convention (companion report) for the column headers.
workaround: >
  Implemented in the generated frontend's list component: dropped identity/idField columns,
  click-to-sort headers with an indicator, and a filter bar (search + faceted selects whose
  options are the distinct values in the dataset).
domainSanitized: true
```

## Triage result — ACCEPTED, fixed

Landed as codegen guidance (registry-derived; no grammar/IR/analyzer change).
`kcf-oss/codegen/system-prompt.md` now carries non-negotiable **rule 13 (standard data-grid
conventions)**: the generated list view (a) excludes the identity/UUID and free-text columns
(rows click through to the record), (b) has sortable column headers with an active-sort
indicator, (c) offers a filter bar = free-text search + faceted filters for every categorical
column (enum value set / boolean / guarded lifecycle `state`, options taken from the data), and
(d) paginates the result. Column headers use the rule-12 humanized labels. Mirrored in
`design-system-default.md` (Tables/lists convention), `codegen/CONSTRUCT_COVERAGE.md` (ENTITY
frontend cell), and `generate-frontend.md`. All derived from the entity registry — no domain
knowledge and no contract touch.
