# Organizational Knowledge in KCF

KCF `1.3.0` can represent governed organizational knowledge as first-class,
source-mapped semantic IR. Use the `organizational-knowledge` preset when the
model must combine organization structure, people and roles, information,
policies, reasoning, evidence, temporal history, identity reconciliation,
security, and graph publication.

## What is first-class

- `organization` records kind, parent, membership, roles, authority domains,
  ownership, accountability, reporting, escalation, validity, and provenance.
- `information` records subject, author, source, audience, representation,
  confidentiality, freshness, completeness, document extraction, review,
  recording time, and access policy.
- `rule` and `policy` record conditions, effects, authority, applicability,
  normative mode, conflicts, exceptions, evidence, and validity.
- `reasoning` records propositions, premises, evidence, conclusions, method,
  confidence, assumptions, contradictions, and alternatives.
- `assertion` records statement subject, predicate, literal or referenced
  object, epistemic status, evidence, derivation, contradiction, supersession,
  valid time, recording time, classification, and access policy.
- `identity-resolution` records canonical identities, aliases, external IDs,
  equivalence, merges, splits, and retirement.
- `knowledge-query` makes open/closed-world, negation, inference, and temporal
  assumptions explicit.

## Authoring example

```kcf
kcf model KnowledgeBase profile organizational-knowledge {
  namespace example;

  actor Reviewer { }
  entity Procedure { identity procedureId: UUID; }
  work ExecuteProcedure { }

  rule AccessPolicy {
    kind PERMISSION;
    condition "requester is authorized";
    effect ExecuteProcedure;
    applies-to Procedure;
    authority Reviewer;
    mode PERMISSION;
    conflict deny-overrides;
  }

  information ProcedureManual {
    kind DOCUMENT;
    subject Procedure;
    author Reviewer;
    source Procedure;
    representation text;
    source-document "manual.pdf";
    source-location "section 2";
    extraction-method llm;
    extraction-model "extractor-v1";
    confidence 0.95;
    recorded-at "2026-07-22T12:00:00Z";
    reviewed-by Reviewer;
    classification Internal;
    access-policy AccessPolicy;
  }

  assertion ProcedureClaim {
    subject Procedure;
    predicate "documentedBy";
    object-ref ProcedureManual;
    status asserted;
    evidence ProcedureManual;
    recorded-at "2026-07-22T12:00:00Z";
    reviewed-by Reviewer;
    access-policy AccessPolicy;
  }

  knowledge-query CurrentProcedures {
    select ENTITY;
    where "documentedBy exists";
    world open;
    negation explicit;
    inference declared;
    temporal current;
  }
}
```

Compile and validate the organizational-knowledge model to a `ready` IR:

```powershell
python tools/kcf.py compile model.kcf --output model-ir.json --validate
python tools/kcf.py assess model-ir.json
```

The knowledge-graph emitter (JSON-LD / RDF / SHACL) that consumes this IR is part
of the separate commercial platform; KCF (open source) stops at the IR.

The graph emitter produces `model.jsonld`, RDF Turtle in `model.ttl`, SHACL
shapes in `shapes.ttl`, and a trace manifest.

## Knowledge governance

- Absence is not false under `world open`.
- Negation-as-failure requires `world closed`.
- Inferred assertions name their reasoning derivation.
- Contradictory and disputed assertions coexist; they are never silently
  overwritten.
- Corrections use supersession or retraction while preserving history.
- `validFrom`/`validTo` describe when knowledge applies; `recordedAt` describes
  when the system learned it.
- Automated extraction records document, location, method, model, confidence,
  recording time, and human reviewer.
- Classified or confidential knowledge names an access policy.
- Alias or external-ID collisions across canonical identities are errors.

`tests/domains/organizational-knowledge.kcf` is the normative domain trial.
