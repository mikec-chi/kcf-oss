# 06 - Behavior, Actions, Processes, and Lifecycles

## Gate

Approve executable meaning before implementation design.

## Prompt

```text
Model [DOMAIN] behavior using WORK, ACTION, EVENT, LIFECYCLE, and RULE.

For every Action contract declare:

- stable identity;
- effect: query, command, or transform;
- operation;
- record, set, batch, stream, or window scope;
- target;
- explicit selection;
- input and output cardinality;
- input, output, and mutations;
- preconditions, postconditions, and failures;
- transaction and atomicity;
- concurrency policy;
- idempotency and retry behavior;
- authorization;
- audit and evidence;
- timeout, partial failure, and compensation.

For every collection transformation declare input/output schemas, keys,
predicate, order, window, boundedness, determinism, grain, equality, null/error
behavior, and field lineage.

Separately model:

- immutable Events;
- Lifecycle states, initial/terminal states, transitions, guards, and effects;
- Work process starts, ends, steps, gateways, flows, calls, lanes, and boundary
  events;
- Rule applicability, effects, priority, exceptions, and conflict resolution.

Lifecycle state evolution and Work process control flow must remain separate.

Produce:

- [PROJECT_ROOT]/domain/05-behavior.json
- [PROJECT_ROOT]/domain/05-behavior-review.md

The phase passes only when every command is authorized and retry-safe, every
bulk mutation has explicit selection and atomicity, and lifecycle/process
reachability has been reviewed.
```

