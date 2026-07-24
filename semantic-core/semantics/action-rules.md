# Action and Data-Operation Semantic Rules

### Why this layer is required

Grammar stacks commonly contain record actions, assignments, rules, functions,
transformations, mappings, validation and inference stages, training pipelines,
integration routes, process tasks, collection operations, device commands,
control actions, and user-interaction bindings.

These are not semantically interchangeable. A validator MUST classify each
operation along independent axes rather than treating every construct named
`action` as equivalent.

### Canonical action classification

An action contract has the following semantic fields. A grammar construct may
provide them directly, through generic properties, through annotations, or by
unambiguous inference from the construct kind. If a field cannot be inferred
reliably, the model MUST declare it.

| Field | Allowed values | Meaning |
| --- | --- | --- |
| `effect` | `query`, `command`, `transform` | Whether the operation only reads, changes observable state, or derives data |
| `operation` | CRUD or collection operation listed below | Specific operation performed |
| `scope` | `record`, `set`, `batch`, `stream`, `window` | Cardinality/execution scope |
| `input-cardinality` | `zero`, `one`, `optional-one`, `many`, `stream` | Expected input cardinality |
| `output-cardinality` | `zero`, `one`, `optional-one`, `many`, `stream` | Produced result cardinality |
| `target` | qualified entity, dataset, collection, stream, device, or resource | Object read or affected |
| `selection` | key, predicate, relation, window, or `all` | How target members are selected |
| `mutation` | fields or state transitions changed | Observable change |
| `transaction` | `none`, `required`, `requires-new`, `supports` | Transaction participation |
| `atomicity` | `atomic`, `per-record`, `best-effort` | Failure boundary for multi-item work |
| `idempotency` | `idempotent`, `non-idempotent`, `conditional` | Whether repetition has the same intended effect |
| `consistency` | project-defined consistency level | Read/write visibility guarantee |
| `concurrency` | `none`, `optimistic`, `pessimistic`, `serialized` | Concurrent update policy |
| `authorization` | permission/policy reference | Required authority |
| `audit` | event/evidence reference or policy | Required audit behavior |

Recommended representation using existing generic properties:

```text
action UpdateCustomer {
  entity = crm.Customer;
  operation = "update";
  scope = "record";
  effect = "command";
  idempotency = "conditional";
  concurrency = "optimistic";
  transaction = "required";
  authorization = "crm.Customer.update";
}
```

An implementation MAY provide a typed annotation profile instead, but the
meaning and validation rules MUST remain equivalent.

### Record CRUD operations

The canonical individual-record operations are:

| Operation | Required effect | Required semantic behavior |
| --- | --- | --- |
| `create` | `command` | Produces one new identity; rejects or resolves identity collisions |
| `read` | `query` | Selects by a unique key and produces zero or one record |
| `replace` | `command` | Replaces the complete mutable record representation |
| `update` | `command` | Changes declared fields on exactly one selected record |
| `patch` | `command` | Applies an explicit partial-change document to one record |
| `delete` | `command` | Removes, archives, or tombstones one selected record according to policy |
| `upsert` | `command` | Creates or updates according to a declared conflict/identity key |
| `exists` | `query` | Produces a boolean for a unique-key selection |

Record-operation rules:

- `action.record.target`: A record CRUD action MUST target exactly one entity or
  record-shaped resource.
- `action.record.key`: `read`, `replace`, `update`, `patch`, and `delete` MUST
  provide a selection that is provably unique. A non-unique predicate makes the
  operation set-scoped.
- `action.record.create-input`: `create` MUST provide every required,
  noncomputed field not supplied by a default or generation policy.
- `action.record.create-output`: `create` MUST return or emit the created
  identity unless the execution profile explicitly defines asynchronous
  identity delivery.
- `action.record.create-readonly`: `create` MUST NOT accept client assignments
  to computed, generated, or unauthorized read-only fields.
- `action.record.replace-complete`: `replace` MUST supply every required mutable
  field. Omitted optional fields MUST follow an explicit clear/preserve policy.
- `action.record.update-fields`: `update` MUST declare which fields may change
  and MUST NOT mutate fields outside that set.
- `action.record.patch-format`: `patch` MUST declare its patch dialect and MUST
  validate every path, operation, and value type.
- `action.record.delete-policy`: `delete` MUST identify hard-delete,
  soft-delete, archive, or tombstone behavior and MUST respect relation/retention
  policies.
- `action.record.upsert-key`: `upsert` MUST identify a stable conflict key and
  MUST define behavior when more than one existing record matches.
- `action.record.exists-output`: `exists` MUST return boolean and MUST NOT expose
  record data as a side effect.
- `action.record.not-found`: Read/mutation operations MUST define not-found
  behavior: empty result, domain error, or idempotent success where appropriate.
- `action.record.precondition`: Version, state, ownership, and business
  preconditions MUST be checked before mutation.
- `action.record.postcondition`: Mutations MUST establish declared field,
  relation, lifecycle, and invariant postconditions.

### Set-oriented CRUD and bulk operations

Set operations target zero or more records selected by a predicate, relation,
explicit key set, partition, or the explicit token `all`. Canonical operations
are `query`, `count`, `bulk-create`, `bulk-update`, `bulk-patch`, `bulk-delete`,
`bulk-upsert`, and `synchronize`.

- `action.set.explicit-scope`: A set operation MUST declare `scope = "set"` or
  another collection scope. It MUST NOT masquerade as record CRUD.
- `action.set.selection-required`: Bulk update/patch/delete MUST specify a
  selection. Absence of a selection MUST be an error; selecting every record
  requires an explicit `all` selection.
- `action.set.unbounded-warning`: An unbounded or `all` mutation SHOULD produce a
  high-severity warning and MAY require explicit approval.
- `action.set.query-pure`: `query` and `count` MUST have `effect = "query"` and
  MUST NOT mutate modeled state.
- `action.set.input-shape`: Bulk input records MUST have a uniform compatible
  schema unless the operation explicitly supports tagged variants.
- `action.set.output-shape`: Results MUST declare whether they return affected
  records, keys, count, per-item outcomes, or no value.
- `action.set.atomicity`: A set mutation MUST declare `atomic`, `per-record`, or
  `best-effort` atomicity.
- `action.set.partial-failure`: Nonatomic operations MUST expose per-item success
  and failure results and MUST define retry behavior.
- `action.set.order`: An operation whose result/effect depends on order MUST
  declare a stable ordering and tie-breaker.
- `action.set.pagination`: Large/unbounded queries MUST declare or inherit
  pagination, streaming, or bounded materialization behavior.
- `action.set.limit`: Limits MUST be positive; limits without deterministic order
  SHOULD produce a warning.
- `action.set.concurrency`: Bulk mutations MUST define conflict handling when
  records can change between selection and mutation.
- `action.set.invariants`: Entity and cross-record invariants MUST hold at the
  declared atomicity boundary.
- `action.set.cascade`: Bulk delete/update cascades MUST be bounded, authorized,
  and consistent with the consuming stack's declared relation ownership.
- `action.set.synchronize`: Synchronization MUST declare source of truth,
  identity matching, create/update/delete behavior, and conflict precedence.
- `action.set.bulk-upsert`: Bulk upsert MUST define duplicate input-key behavior
  and conflicts among concurrently processed items.

### Collection queries and relational/set operations

Canonical collection operations are:

- `select` or `project`: choose fields/expressions;
- `filter`: retain items satisfying a boolean predicate;
- `map`: produce one output per input;
- `flat-map`: produce zero or more outputs per input;
- `distinct`: remove duplicates using declared equality/key semantics;
- `sort`: order by declared keys and directions;
- `group`: partition by key;
- `aggregate`: reduce a group/collection to summary values;
- `join`: combine two collections using keys/predicate and join kind;
- `union`: combine compatible collections;
- `intersect`: retain values present in both collections;
- `except`: remove values present in another collection;
- `window`: partition an ordered or streaming collection by time/count/session;
- `sample`: select a subset under a declared sampling method;
- `partition`: distribute by key or policy;
- `deduplicate`: choose a survivor among items sharing an identity/key.

Validation rules:

- `action.collection.input-schema`: Every collection operation MUST receive a
  known item schema or type.
- `action.collection.field-resolution`: Referenced fields MUST exist at the
  current pipeline stage, not merely in the original source.
- `action.collection.output-schema`: The validator MUST derive or verify the
  output schema after each operation.
- `action.collection.purity`: A collection transformation SHOULD be pure. Any
  external state mutation MUST be declared as a command/effect boundary.
- `action.collection.filter-boolean`: Filter predicates MUST evaluate to boolean.
- `action.collection.map-cardinality`: `map` MUST preserve item count;
  `flat-map` MUST declare zero-to-many output cardinality.
- `action.collection.projection-unique`: Projected output field names MUST be
  unique.
- `action.collection.equality`: Distinct/intersect/except/deduplicate MUST define
  or infer equality/key semantics compatible with the item type.
- `action.collection.order-total`: A required deterministic sort MUST provide a
  total order or stable tie-breaker.
- `action.collection.group-key`: Group keys MUST be hashable/comparable under the
  execution profile and output grouping keys MUST be retained or deliberately
  discarded.
- `action.collection.aggregate-type`: Aggregate functions MUST support the input
  type and define empty-input behavior.
- `action.collection.aggregate-grain`: Measures MUST declare their output grain;
  combining different grains without an explicit reaggregation is invalid.
- `action.collection.join-inputs`: Both join inputs and join fields MUST resolve.
- `action.collection.join-type`: Join key types, units, null semantics, and
  cardinalities MUST be compatible.
- `action.collection.join-fanout`: Many-to-many or otherwise fanout-producing
  joins SHOULD require an explicit expected-cardinality declaration.
- `action.collection.set-compatibility`: Union/intersect/except inputs MUST have
  compatible schemas and equality semantics.
- `action.collection.window`: Windows MUST define type, size/gap, ordering/time
  field, time zone, lateness/watermark policy for streams, and emission policy.
- `action.collection.sample`: Sampling MUST define method, valid size/rate, seed
  or nondeterminism policy, and stratification keys where applicable.
- `action.collection.partition`: Partition keys MUST exist and partitioning MUST
  preserve required grouping/order guarantees.
- `action.collection.dedup-survivor`: Deduplication MUST define identity key and
  deterministic survivor selection.
- `action.collection.boundedness`: Operations that require full materialization
  (for example global sort) MUST NOT run on an unbounded stream without a window
  or other bound.

### Data-processing transformations

A transformation converts data shape, type, value, representation, or grain.
It is distinct from CRUD even if its output is later persisted.

- `action.transform.source-target`: Source and target schemas/types MUST resolve.
- `action.transform.totality`: A transformation MUST declare whether it is total
  or how unsupported/invalid inputs are handled.
- `action.transform.field-lineage`: Every output field MUST trace to source
  fields, constants, generated values, or an explicitly opaque computation.
- `action.transform.required-coverage`: Every required target field MUST be
  mapped, defaulted, generated, or computed.
- `action.transform.type`: Field transformations MUST produce values compatible
  with target types, constraints, units, and cardinality.
- `action.transform.loss`: Narrowing, truncating, rounding, dropping, lossy
  encoding, or many-to-one conversion MUST be declared and SHOULD warn.
- `action.transform.null`: Null/missing/error behavior MUST be declared for each
  transformation that can fail or lose presence information.
- `action.transform.identity`: Transformations used for synchronization/upsert
  MUST preserve or explicitly remap identity.
- `action.transform.classification`: Security/privacy classification MUST
  propagate unless a validated declassification, masking, anonymization, or
  aggregation rule applies.
- `action.transform.unit`: Unit changes MUST use an explicit valid conversion.
- `action.transform.time`: Time conversions MUST preserve instant/local-time
  semantics and explicitly handle time zones and daylight-saving ambiguity.
- `action.transform.determinism`: Deterministic transformations MUST not depend
  on undeclared time, randomness, environment, or mutable external state.
- `action.transform.reproducibility`: Nondeterministic transformations SHOULD
  record seeds, versions, parameters, and execution context when reproducibility
  matters.
- `action.transform.version`: Transformation/schema versions MUST be compatible;
  migrations MUST define supported source and destination versions.
- `action.transform.reversibility`: If a transformation claims reversibility,
  round-trip validation MUST show that required information is preserved.
- `action.transform.side-effect`: Persistence, messaging, command dispatch, and
  external calls MUST be modeled separately from the pure transformation or
  explicitly declared as effects.

### Action invocation and composition

- `action.invoke.resolved`: Every invoked action MUST resolve to one canonical
  action contract.
- `action.invoke.input`: Supplied arguments MUST cover required inputs exactly
  once and match names, types, cardinalities, units, and classifications.
- `action.invoke.output`: Consumers MUST handle the declared output shape,
  including optional, many, stream, and per-item failure results.
- `action.invoke.precondition`: The caller MUST establish or explicitly handle
  action preconditions.
- `action.invoke.authorization`: The caller's actor/role/system MUST be
  authorized for the action, target, scope, and selection.
- `action.invoke.scope`: A record-oriented caller MUST NOT invoke a set mutation
  accidentally through an ambiguous reference.
- `action.invoke.effect-context`: A query-only context MUST NOT invoke a command.
  A pure transform MUST NOT invoke an undeclared stateful effect.
- `action.invoke.transaction`: Nested action transaction requirements MUST be
  compatible; impossible propagation combinations MUST be errors.
- `action.invoke.failure`: Callers MUST handle or propagate declared failure
  modes.
- `action.invoke.timeout-cancel`: Remote/long-running actions SHOULD define
  timeout and cancellation behavior.
- `action.invoke.recursion`: Recursive action invocation MUST be explicitly
  allowed and have a bounded/terminating strategy.
- `action.compose.order`: Sequential dependencies MUST be ordered; independent
  actions MAY run concurrently only when their read/write sets do not conflict.
- `action.compose.compensation`: Multi-step, nontransactional commands SHOULD
  define compensation or reconciliation behavior.
- `action.compose.saga`: Saga-like flows MUST define forward actions,
  compensations, durable state, retry policy, and terminal failure behavior.

### Transactions, concurrency, retries, and events

- `action.transaction.required`: Multi-record invariants requiring atomicity MUST
  execute in a compatible transaction boundary.
- `action.transaction.external`: A transaction MUST NOT claim atomicity across
  systems that cannot provide it; use compensation/outbox/reconciliation
  semantics instead.
- `action.concurrency.version`: Optimistic concurrency MUST identify a version or
  comparison token and define conflict behavior.
- `action.concurrency.lost-update`: Read-modify-write actions MUST prevent or
  explicitly accept lost updates.
- `action.idempotency.create`: Retriable create/bulk-create/upsert operations MUST
  use a stable idempotency or identity key.
- `action.idempotency.delete`: Delete SHOULD be idempotent under its not-found
  policy.
- `action.idempotency.conditional`: Conditionally idempotent actions MUST state
  the condition/key that makes repetition safe.
- `action.retry.classification`: Retry policies MUST distinguish transient from
  permanent failures.
- `action.retry.bound`: Retries MUST be bounded and use a valid backoff policy.
- `action.retry.side-effects`: Retrying a non-idempotent command without duplicate
  suppression or compensation MUST be an error.
- `action.event.commit-order`: Events describing state changes MUST be emitted
  only if the corresponding change commits, using an outbox/equivalent guarantee
  when required.
- `action.event.payload`: Event payloads MUST reflect the declared before/after
  semantics and MUST obey classification/minimization policies.
- `action.event.duplicate`: Event consumers MUST declare duplicate-handling when
  delivery can be at least once.
- `action.audit.mutation`: Record and set mutations SHOULD capture actor, target,
  selection or identity, time, outcome, and correlation identifier.

### Safety and authorization for destructive actions

- `action.destructive.explicit`: Delete, bulk-delete, destructive replace,
  command, firmware, and control actions MUST be explicitly classified as
  destructive where applicable.
- `action.destructive.authorization`: Destructive actions MUST require a
  specific permission; generic read/write permission is insufficient under a
  strict profile.
- `action.destructive.scope`: Destructive set actions MUST expose the evaluated
  target count or preview when technically feasible.
- `action.destructive.confirmation`: Human-facing destructive bulk actions SHOULD
  require confirmation proportional to impact.
- `action.destructive.retention`: Deletion MUST respect retention, legal hold,
  audit, security, and archival rules.
- `action.destructive.recovery`: Recovery, rollback, backup, or irreversibility
  MUST be declared for material destructive actions.
- `action.device.safety`: Device commands and control actions MUST validate
  target capability, current state, interlocks, permissives, range, units,
  acknowledgment, timeout, and fail-safe behavior.

### Action semantic completeness

- `action.contract.incomplete`: Every action-like construct MUST declare or unambiguously resolve all fields required to validate its effect, operation, scope, target, input/output shape, authorization, failure behavior, and applicable transaction semantics.

The validator MUST issue `action.contract.incomplete` when an action-like
construct cannot be assigned all fields needed to validate its behavior. At a
minimum:

- Every operation needs `effect`, `operation`, `scope`, target, input shape, and
  output shape.
- Every command needs mutation/effect description, authorization, failure
  behavior, and idempotency classification.
- Every set mutation needs selection, atomicity, partial-failure, and concurrency
  behavior.
- Every transformation needs source/target schemas, cardinality behavior,
  required-field coverage, lineage, null/error behavior, and side-effect
  classification.
- Every remote or asynchronous invocation needs timeout, retry, delivery,
  duplicate, correlation, and completion semantics.
- Every destructive or operational command needs impact, safety/retention, and
  recovery semantics.

If the grammar construct does not provide explicit syntax for these fields, the
validator MUST read them from recognized properties, annotations, an imported
action profile, or a referenced canonical action. It MUST NOT guess CRUD scope
from an action's name alone.
