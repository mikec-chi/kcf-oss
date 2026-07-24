# 08 - Integration, Security, and Lineage Profiles

## Gate

Approve cross-cutting operational semantics before producing the unified IR.

## Prompt

```text
Apply the selected INTEGRATION, SECURITY, and LINEAGE profiles to [DOMAIN].

Integration must cover:

- adapters, protocols, serialization, and authentication;
- endpoints and Action-linked contracts;
- input/output schemas and field mappings;
- routes and event bridges;
- timeout, retry, correlation, ordering, duplicate delivery, late arrival,
  error handling, compensation, and reconciliation.

Security must cover:

- assets and classification;
- threats, vectors, actors, and targets;
- risks, likelihood, impact, level, and overrides;
- controls, coverage, evidence, owners, and implementations;
- mitigation, transfer, avoidance, or governed acceptance;
- authorization and least privilege;
- trust boundaries and crossing controls;
- classification propagation and declassification policy.

Lineage, binding, and cost must cover:

- concept and field lineage;
- contributing sources, transformations, and executions;
- semantic, data, metric, action, visual, and runtime bindings;
- binding uniqueness and schema compatibility;
- lineage cycles and governed iterative computations;
- finite, nonnegative, unit-compatible costs and allocation periods.

Produce [PROJECT_ROOT]/domain/07-operational-profiles.json.

The phase passes only when high risks have governed treatments, trust crossings
have controls, retrying integrations are safe, and required derived artifacts
have lineage.
```

