# Field report — assess could warn on EVENTs that no work produces (unrealizable events)

```yaml
<!-- kcf-field-report:v1 -->
id: assess-warn-producerless-events-20260727-07
kcfVersion: 1.11.0
commit: c031be6
phase: assess
area: analyzer
construct: kcf assess (event reachability)
severity: low
title: assess does not flag EVENTs with zero CAUSATION producers, so declared-but-unreachable events pass silently
observation: >
  An EVENT can be declared with no incoming CAUSATION edge (no work produces it). The
  model compiles valid/ready and assess reports no gap, but such an event can never be
  emitted by any generated app — it is dead. In the exercised model two events were
  declared with zero producers and went unnoticed until an app-level audit.
evidence:
  commands:
    - kcf assess model-ir.json      # reports ready, no mention of producer-less events
    - "python -c \"...count EVENTs not targeted by any CAUSATION relationship...\"  # -> 2"
  diagnostics:
    - "(none — assess is silent on producer-less events)"
  snippet: |
    event Won;                      # declared
    # ...but no  relationship { kind causation; SomeWork -> Won; }  anywhere
    # -> valid/ready, yet nothing can ever emit `Won`.
impact: >
  Modelers accumulate aspirational events that no behavior produces; codegen has nothing
  to wire them to, so they become silent dead weight and a false sense of coverage.
suggestedChange: >
  Add an ADVISORY assess check (recommendation, never an error — consistent with the
  advisory-metadata pattern): "EVENT <x> has no CAUSATION producer; nothing can emit
  it." Symmetric to the existing reachability checks. Keep it non-blocking.
workaround: >
  Audit the IR for EVENTs absent from the CAUSATION target set after authoring.
domainSanitized: true
```
