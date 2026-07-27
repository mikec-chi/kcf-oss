# Field report — codegen leaves a status-like attribute unreconciled with the entity's lifecycle

```yaml
<!-- kcf-field-report:v1 -->
id: codegen-lifecycle-status-not-reconciled-20260727-03
kcfVersion: 1.11.0
commit: c031be6
phase: codegen
area: codegen
construct: lifecycle
severity: high
title: When an entity has both a status-like attribute and a lifecycle, codegen emits two divergent fields and metrics read the unguarded one
observation: >
  An entity is modeled with a free-string `status` attribute (type String, no enum)
  AND a LIFECYCLE whose states enumerate the same values (Open/Qualified/Won/...). The
  codegen pack realizes BOTH as separate columns: a lifecycle `state` (guarded by
  transition rules) and the original `status` (free string). On create, the Create
  schema carries `status` (set verbatim from input) while `state` defaults to the
  lifecycle's initial state — so the two fields diverge immediately. Worse, the MEASUREs
  key off `status`, i.e. the guarded state machine and the reported metrics operate on
  different fields.
evidence:
  commands:
    - "POST /actions/CreateEntity {\"status\":\"Won\"}   # -> stored status=Won, state=Open"
    - "GET  /queries/WinRate                              # -> breakdown counts status=='Won' = 1"
    - "POST /actions/AdvanceState {\"toState\":\"Won\"}   # correctly 422s illegal transitions on `state`"
  diagnostics:
    - "created status='Won' but state='Open' (fields diverge on create)"
    - "WinRate breakdown {won:1} for a record that passed zero lifecycle guards"
  snippet: |
    entity Order {
      attribute status : string { required; }     # free string, no enum
    }
    lifecycle OrderLifecycle {
      subject Order;
      initial Open;
      state Open; state Won terminal; state Lost terminal;
      transition Open -> Won using CloseWon;
    }
    measure WinRate { ... counts Order where status == "Won" ... }
    # Codegen -> columns `status` (free) AND `state` (guarded); create sets status
    # directly, WinRate reads status -> guards are bypassable for metric purposes.
impact: >
  Every model that has both a status-like attribute and a lifecycle over the same
  concept: the lifecycle-guard investment is undermined because create writes the
  unguarded field and measures read it, so metrics can be driven by values that never
  passed a transition rule. It also silently accepts out-of-vocabulary status strings
  (the attribute is a plain String; valid values live only in the lifecycle).
suggestedChange: >
  Codegen guidance should reconcile the two: when an attribute's value domain matches a
  lifecycle's states (or is the lifecycle subject's status field), map the lifecycle
  ONTO that single attribute (one column, guarded), OR validate/sync the attribute
  against the lifecycle on create/update, OR at minimum have measures read the guarded
  `state`. Document the chosen rule in CONSTRUCT_COVERAGE.md and show it in a stack
  EXAMPLE. Separately, an authoring-surface way to say "this attribute IS the lifecycle
  status" (or deriving it) would remove the ambiguity at the source.
workaround: >
  In the generated app, make business commands set both fields in lockstep and point
  measures at the guarded `state`; drop the free-string `status` from the Create schema.
domainSanitized: true
```
