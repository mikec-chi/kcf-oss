# Field report — nav should sub-group transactional entities by the process whose works transform them

```yaml
<!-- kcf-field-report:v1 -->
id: codegen-nav-group-transactions-by-process-20260727-08
kcfVersion: 1.11.0
commit: 8c18022
phase: codegen
area: codegen
construct: process (WORK/BPMN) + navigation
severity: medium
title: Codegen guidance derives nav from category + aggregate-structure, but not from `process`, so transactional entities render as one flat, unreadable list
observation: >
  The pack already derives navigation from two emergent structures: `category`
  (master/transactional/config groups) and COMPOSITION aggregate-structure (pure
  parts become subtabs, roots become top-level nav). But it has no convention for
  the third axis a real app needs: WHICH business flow a transactional record
  belongs to. Result: every transactional entity lands in one flat "Transactions"
  list mixing unrelated flows (lead pipeline, solutioning, onboarding, governance,
  delivery), which is hard to make sense of once there are more than a handful.
  The grammar already models the missing structure — top-level `process` (BPMN)
  sequences `WORK`s, and works `TRANSFORMATION`-transform entities — so the grouping
  is derivable, not a new tag.
evidence:
  commands:
    - kcf compile model.kcf -o ir.json --validate   # ir.processes[] present
    - "# derive: process -> its works (node.activity / node.triggeredBy) -> the"
    - "#         entities those works TRANSFORMATION-transform -> nav sub-group"
  diagnostics:
    - "flat list of N transactional entities with no sub-structure vs N/k labelled process groups"
  snippet: |
    process OrderFulfillment {
      start Placed triggered-by PlaceOrderWork;
      step Pick: PickWork; step Ship: ShipWork; end Done;
      flow Placed -> Pick; flow Pick -> Ship; flow Ship -> Done;
    }
    relationship r1 { kind transformation; PlaceOrderWork -> Order; }
    relationship r2 { kind transformation; ShipWork      -> Shipment; }
    # => nav: "Order Fulfillment" group contains Order, Shipment. Entities no work
    #    transforms directly inherit their COMPOSITION whole, else an ASSOCIATION
    #    target (a LineItem follows its Order; an Activity follows its Opportunity).
impact: >
  Every non-trivial app: as soon as a domain has more than one business process, the
  transactional menu becomes a flat dumping ground. The information to fix it is
  already in the IR (processes + transformation edges); only the codegen convention
  is missing, so each generator reinvents (or omits) it.
suggestedChange: >
  Add a codegen convention (CONSTRUCT_COVERAGE.md + a worked EXAMPLE), symmetric to the
  aggregate-structure nav already documented: group transactional entities by the
  `process` whose works transform them; derive each entity's group as
  process -> works(node.activity/triggeredBy) -> TRANSFORMATION targets; for entities
  no work reaches, inherit the COMPOSITION whole first, then an ASSOCIATION target;
  fall back to an "Other" group. Purely structural — no new grammar/IR field.
workaround: >
  Implemented in the generated frontend: a derived `PROCESS_OF`/`PROCESS_ORDER` map
  drives sub-groups under the transactional nav; models with no `process` fall back to
  the existing flat list.
domainSanitized: true
```

## Triage result — ACCEPTED, fixed

Fixed in the codegen pack (docs/prompt only — no grammar/IR/analyzer change). `COOKBOOK.md`
§F gains a **"Sub-group transactional entities by process"** convention, symmetric to the
existing aggregate-structure nav rule: group each transactional entity by the `process`
whose works `TRANSFORMATION`-transform it (process → works via `node.activity`/`triggered-by`
→ transformation targets); an entity no work reaches inherits its `COMPOSITION` whole, else
an `ASSOCIATION` target, else an "Other" group; a model with no `process` keeps the existing
flat list (no regression). Cross-referenced from `CONSTRUCT_COVERAGE.md` (the `category`
grouping note + the `experience` nav row) and `system-prompt.md` rule 5. Purely structural —
derivable from the IR, no new field.
