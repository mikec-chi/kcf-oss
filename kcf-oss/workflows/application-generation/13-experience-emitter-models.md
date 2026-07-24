# 13 - Experience and Emitter Models

## Gate

Approve technology-facing models before their code is generated.

## Prompt

```text
Derive only the emitter-profile models selected for [DOMAIN] from the validated
IR. These files are reviewed projection specifications, not alternate semantic
sources; do not add concepts or behavior that are absent from model.kcf.

ARCHITECTURE:
- systems, services, capabilities, interfaces, topology, deployments,
  environments, boundaries, and controls.

EXPERIENCE:
- applications, views, components, flows, entries, actions, state, and data
  bindings.

DESIGN:
- tokens, scales, breakpoints, patterns, responsive behavior, page designs,
  validation states, error states, accessibility, focus, and keyboard behavior.

ANALYTICS:
- datasets, transformations, semantic layers, dimensions, measures, reports,
  dashboards, filters, actions, lineage, classification, and grain.

AI:
- feature schemas, datasets, targets, transformations, models, metrics,
  pipelines, serving, drift, explainability, governance, lineage, and security.

KNOWLEDGE GRAPH:
- JSON-LD identities and types, RDF triples, SHACL constraints, statement-level
  provenance, epistemic status, valid/recorded time, identity reconciliation,
  access policy, and explicit query/inference assumptions.

Every Action binding must resolve to an approved Action contract. Every field,
metric, and feature must bind to a compatible semantic source. Security
classification and lineage must propagate. Hiding or disabling a UI element is
not authorization.

Produce profile-specific JSON and Markdown reviews under
[PROJECT_ROOT]/app/models/. For each projected element record its KCF identity,
source span, selected profile, target artifact, support classification, and any
approved degradation.

The phase passes only when profile references resolve and every technology-facing
model preserves the source semantics.
```
