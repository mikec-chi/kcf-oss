# Field report — codegen emits only one event per command, dropping a work's other CAUSATION targets

```yaml
<!-- kcf-field-report:v1 -->
id: codegen-causation-events-under-emitted-20260727-06
kcfVersion: 1.11.0
commit: c031be6
phase: codegen
area: codegen
construct: event (CAUSATION work -> event)
severity: medium
title: A command realizing a work emits only its primary CAUSATION event, silently dropping the work's other event targets
observation: >
  A WORK can have multiple CAUSATION edges to EVENTs (it both does its thing and raises
  a notification). Codegen realizes the work as a command that emits exactly ONE event
  (the "primary" one), dropping the rest. In the exercised model, the approve-stage
  command emits nothing at all (owes a result-notification event) and the convert
  command emits only its primary event (drops a "created" notification). Downstream
  consumers of the dropped events never fire.
evidence:
  commands:
    - "grep -n 'E.emit' app/service.py     # 6 emits, one per command"
    - "# IR: 13 CAUSATION work->event edges; several works have 2 targets, only 1 emitted"
  diagnostics:
    - "ApproveWork -> ResultNotification (CAUSATION in IR) but approve command emits nothing"
    - "ConvertWork -> {ConvertedEvent, CreatedNotification}; command emits only ConvertedEvent"
  snippet: |
    work ApproveWork { ... }
    event Approved; event ApprovalNotification;
    relationship r1 { kind causation; ApproveWork -> Approved; }
    relationship r2 { kind causation; ApproveWork -> ApprovalNotification; }
    # Codegen -> approve command emits (at most) one of these, not both.
impact: >
  Any model where a work causes more than one event (a common "do X and notify"
  pattern): event-driven integrations wired to the secondary events are silently dead
  in the generated app, with no error to signal the drop.
suggestedChange: >
  Codegen should emit ALL EVENTs that are CAUSATION targets of the work a command
  realizes (iterate relationships where rootKind==CAUSATION and source==work), not a
  single heuristic "primary". Document the 1-command -> N-events mapping and show a
  multi-event work in an EXAMPLE.
workaround: >
  In the generated service, add the missing E.emit(...) calls for each CAUSATION target
  of the command's work.
domainSanitized: true
```

## Triage result — ACCEPTED, fixed

Fixed in the codegen pack: system-prompt **rule 11** — a command realizing a WORK
emits **all** events that are `CAUSATION` targets of that work (iterate relationships
where `rootKind == CAUSATION` and `source ==` the work), not a single "primary".
