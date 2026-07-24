# 15 - Semantic Test Generation

## Gate

Prove that the generated application preserves the validated semantics.

## Prompt

```text
Derive an executable semantic test suite from domain/model-ir.json,
domain/08-runtime-contract.json, semantics/semantic-rules.json,
semantics/coverage.json, and tests/fixtures/rules/fixture-index.json.

Generate tests for every applicable area:

- stable identities and reference resolution;
- primary-kind and trait constraints;
- relationship endpoints, roots, cardinality, conditions, time, inverses, and
  permitted inference;
- lifecycle and process uniqueness, guards, transitions, and reachability;
- Rule applicability, priority, exceptions, and conflicts;
- Action effect, selection, cardinality, pre/postconditions, atomicity,
  concurrency, retries, idempotency, authorization, audit, failure, and
  compensation;
- Event immutability, ordering, correlation, duplicates, and late arrival;
- Resource capacity, allocation, contention, and units;
- Information schemas, classification, provenance, freshness, and audience;
- integration mapping, retry, timeout, failure, and reconciliation;
- trust-boundary controls and least privilege;
- lineage, binding uniqueness, classification propagation, and cost;
- emitter unsupported-semantics behavior;
- runtime capability and version compatibility.

Include positive, negative, boundary, destructive-action, concurrency, retry,
partial-failure, and recovery cases.

Every test must record:

- source semantic identity;
- stable semantic rule ID;
- precondition and input;
- expected result;
- evidence produced;
- implementation artifact exercised.

Produce a coverage report identifying applicable rules without executable tests
and explain why each is unavailable or requires another test layer. Preserve the
catalogue enforcement classification; application tests may add evidence but
must not relabel a manual rule as fully automated without updating KCF's
catalogue coverage and conformance fixtures.

The phase passes only when all implemented semantics have traceable test
coverage and remaining unavailable coverage is explicit.
```
