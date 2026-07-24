# 07 - Supporting Dimensions

## Gate

Complete all selected dimensional semantics before normalization.

## Prompt

```text
Complete the [DOMAIN] model for every selected supporting dimension.

When `organizational-knowledge` is selected, explicitly model organization
hierarchy, reporting and escalation, governed information, policies, reasoning,
epistemic assertions, valid/recorded time, identity reconciliation, extraction
provenance, access policies, and knowledge-query assumptions.

Model and validate:

- Information schemas, representations, classifications, provenance,
  freshness, completeness, trust, and audience;
- Actor capabilities, skills, tools, authority, responsibility,
  accountability, and availability;
- Resources, capacities, allocations, reservations, quantities, units, cost,
  and contention;
- Temporal intervals, schedules, calendars, deadlines, recurrence, time zones,
  and daylight-saving behavior;
- Spatial locations, containment, jurisdiction, coordinates, geometry, routes,
  distance, and capacity;
- Organization structures, memberships, reporting, escalation, and authority;
- Intent desired states, success/failure conditions, stakeholders, horizons,
  priorities, and tradeoffs;
- Measures, units, scales, grain, calculations, thresholds, targets, and
  tolerance;
- Reasoning propositions, evidence, assumptions, alternatives,
  contradictions, confidence, and inference provenance;
- Logic and Math typing, domains, arity, termination, probability, aggregation,
  and optimization constraints.

Produce [PROJECT_ROOT]/domain/06-supporting-semantics.json.

The phase passes only when all selected dimensions have complete references,
types, units, provenance, and applicable invariants.
```
