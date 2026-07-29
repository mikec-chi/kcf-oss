# Field report — generated UIs render raw identifiers as labels; the pack should derive human labels by default

```yaml
<!-- kcf-field-report:v1 -->
id: codegen-humanize-identifiers-into-ui-labels-20260728-11
kcfVersion: 1.11.0
commit: 1cd0475
phase: codegen
area: codegen
construct: frontend UI (field/entity/enum labels)
severity: medium
title: Codegen should humanize identifiers into Title-Case UI labels by default (firstName → "First Name"), instead of showing raw identifiers
observation: >
  A generated frontend shows attribute/entity/enum identifiers verbatim in the UI — form
  field labels, table headers, record labels, nav items, state badges all read as
  "firstName", "isActive", "annualRevenue", "opportunityNumber", "OpportunityStageApproval",
  "QualifiedOpportunity". Identifiers are for code, not end users. There is no codegen
  convention that turns them into human labels, so every generated app looks unfinished.
  The transform is deterministic and domain-agnostic (split camelCase/snake_case + letter→
  digit boundaries, Title-Case, upper-case known acronyms), so it belongs in the stack UI
  kit and should apply on every generation.
evidence:
  commands:
    - "# form/detail/list render f.name (e.g. 'annualRevenue') directly as the label"
  diagnostics:
    - "firstName -> shown as 'firstName' (want 'First Name')"
    - "stageId -> 'stageId' (want 'Stage ID'); OpportunityStageApproval -> want 'Opportunity Stage Approval'"
  snippet: |
    // humanize(id): camelCase/snake -> Title Case, acronyms upper-cased
    "firstName"                -> "First Name"
    "annualRevenue"            -> "Annual Revenue"
    "stageId"                  -> "Stage ID"
    "QualifiedOpportunity"     -> "Qualified Opportunity"    # enum / lifecycle state
    "OpportunityStageApproval" -> "Opportunity Stage Approval"
  impact: >
    Every generated frontend, for every model: without a label convention the UI shows code
    identifiers to users. It is the single most visible "skeleton" tell, and the fix is one
    domain-agnostic helper applied uniformly.
suggestedChange: >
  Add a UI-label convention to the codegen pack (CONSTRUCT_COVERAGE.md / frontend EXAMPLE): a
  stack `humanize(identifier)` helper (camelCase/snake split, letter→digit boundaries,
  Title-Case, configurable acronym set) applied to field labels, column headers, entity/nav
  labels, and enum/lifecycle-state values. A model-declared label (see the companion
  grammar report) overrides the derivation. No grammar/IR change for the default.
workaround: >
  Implemented `humanize()` + `fieldLabel/entityLabel/valueLabel` in the generated frontend and
  wired them through the form, detail, list, nav, related tabs, and state badges.
domainSanitized: true
```

## Triage result — ACCEPTED, fixed

Landed as codegen guidance (no grammar/IR/analyzer change). `kcf-oss/codegen/system-prompt.md`
now carries non-negotiable **rule 12 (humanize identifiers into UI labels)**: a single
deterministic, domain-agnostic `humanize()` helper (split camelCase/snake_case + letter→digit
boundaries, Title-Case, upper-case a configured acronym set) applied uniformly to field labels,
column headers, detail fields, entity/nav labels, and lifecycle-state badges — so no raw
identifier ever reaches the UI (`firstName`→"First Name", `stageId`→"Stage ID"). Reinforced in
`design-system-default.md` (Labels convention), `codegen/CONSTRUCT_COVERAGE.md` (ENTITY frontend
cell), and `generate-frontend.md` (instruction). The derivation is the **default**; a
model-declared human label will override it once labels are authorable — routed as **RFC-10**
in `docs/IR-ROADMAP.md` (companion report `20260728-12`).
