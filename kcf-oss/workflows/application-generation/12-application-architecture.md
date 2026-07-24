# 12 - Application Architecture

## Gate

Approve how validated semantics map to the target technology before generating
code.

## Prompt

```text
Design the [DOMAIN] application from the validated model-ir.json and
08-runtime-contract.json, the runtime manifest, and approved emitter-support
matrix for this target stack:

[TECH_STACK]

Produce [PROJECT_ROOT]/app/generation-plan.md containing:

- architectural boundaries and components;
- capability and data ownership;
- services and internal modules;
- data stores, identity, consistency, and migration strategy;
- API, command, query, and event contracts;
- process/workflow execution;
- authorization and policy enforcement points;
- integration adapters and trust boundaries;
- lineage, audit, evidence, and observability;
- deployment topology and runtime dependencies;
- emitter support decisions;
- semantic identity to implementation-artifact mapping;
- expected reference-emitter artifacts and trace-manifest reconciliation;
- vertical slices and their implementation order;
- unsupported semantics and implementation compromises;
- risks requiring human approval.

Do not introduce a component, field, API, event, screen, or workflow without a
source semantic reason. Do not allow technology constraints to silently change
the model.

The phase passes only when every generated artifact category traces to the
validated IR, every semantic requirement has a planned realization, and each
approved degradation has an owner and acceptance criterion.
```
