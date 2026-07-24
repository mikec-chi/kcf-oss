# Business-Pattern Profile Guide

Business-pattern presets encode reusable process and governance shapes rather
than industry labels. A profile supplies module closure, runtime capabilities,
required patterns, recommendations, and explicit anti-patterns.

## Selection

- Start with the preset matching the end-to-end business invariant, not the
  team name or implementation technology.
- Compose profiles when the model genuinely spans patterns. For example, a
  regulated customer service platform may use CRM, case management, and
  compliance-risk management together.
- Treat every required pattern as a modeling checklist. An `implements` claim
  means the necessary identities, states, actions, authority, evidence,
  temporal behavior, and failure handling exist in the model.
- Exclude a recommendation only when its absence is intentional and reviewed.
- Never weaken a prohibited pattern through composition. The resolver rejects
  direct required/prohibited conflicts.

## Common pattern families

| Profile | Required semantic spine |
| --- | --- |
| CRM | Party identity; account/contact roles; interaction history; consent; opportunity lifecycle; activity ownership |
| Order-to-cash | Product; quote; order lifecycle; reservation; shipment; invoice; payment |
| Procure-to-pay | Supplier; requisition; approval; purchase order; receipt; three-way match; payment |
| Case management | Case identity; classification; assignment; lifecycle; SLA; evidence; decision; escalation |
| Subscription billing | Plan; contract; entitlement; usage; billing cycle; invoice; dunning; renewal |
| Project delivery | Project; work breakdown; dependency; milestone; resource plan; risk; change; outcome |
| Workforce management | Worker; position; assignment; skill; capacity; schedule; delegation |
| Asset maintenance | Asset identity/location/condition; plan; work order; inspection; parts; downtime |
| Compliance and risk | Obligation; risk; control; test; evidence; exception; finding; remediation |
| Master data | Canonical identity; external IDs; match; merge/split; stewardship; sync; quality |
| Knowledge management | Taxonomy; content lifecycle; expertise; assertion; provenance; access; search |

## Validation contract

For each claimed pattern, validators and reviewers should verify:

1. Stable identities and role distinctions are explicit.
2. Lifecycles have legal initial, terminal, transition, and exception paths.
3. Record and collection actions declare scope, cardinality, authorization,
   idempotency, concurrency, and audit behavior.
4. Rules identify authority, applicability, priority/conflict behavior, and
   evidence.
5. Monetary, quantity, time, and service-level measures declare units and
   comparison semantics.
6. Cross-boundary messages declare correlation, versioning, retries, and
   reconciliation.
7. Assertions preserve provenance, epistemic status, valid time, and recording
   time.
8. Sensitive information has classification, access policy, retention, and
   purpose/consent semantics where applicable.
9. Exceptions, reversals, corrections, and compensations preserve history.
10. Emitters and runtime bindings preserve every required semantic capability.
