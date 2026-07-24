# Stack-Neutral Semantic Rules

## Schema and representation

- `stack.schema.valid`: A machine-readable model or manifest MUST conform to its declared versioned schema before deeper semantic validation.

### Modules, imports, and versions

- `stack.module.known`: Every model module MUST be declared in
  `grammar-stack.json`.
- `stack.start.valid`: The configured start production MUST exist.
- `stack.import.declared`: Every external grammar reference MUST use a declared
  import.
- `stack.import.resolved`: Every imported module and production MUST exist.
- `stack.import.acyclic`: The module import graph MUST be acyclic, except for an
  explicitly documented type-only cycle supported by the resolver.
- `stack.import.alias-unique`: Import aliases MUST be unique in a model.
- `stack.version.compatible`: Referenced module and construct versions MUST
  satisfy the importing model's supported version range.
- `stack.version.deprecated`: Use of a deprecated construct SHOULD produce a
  warning and identify its replacement.

### Names and scopes

- `stack.name.unique`: Names MUST be unique among declarations of conflicting
  kinds in the same lexical scope.
- `stack.name.reserved`: Reserved keywords MUST NOT be used as identifiers.
- `stack.name.qualified-resolved`: A qualified name MUST resolve to exactly one
  accessible declaration.
- `stack.name.kind-compatible`: A reference MUST resolve to the construct kind
  required by its position. For example, a role reference cannot resolve to an
  entity.
- `stack.name.visibility`: A reference MUST NOT access a declaration outside
  its permitted or exported scope.
- `stack.name.shadowing`: Shadowing an imported or enclosing declaration SHOULD
  produce a warning unless explicitly annotated as intentional.
- `stack.name.unused`: Unreferenced private declarations SHOULD produce a
  warning.

### Types and values

- `stack.type.known`: Every declared type MUST resolve to a primitive, alias,
  enum, schema, entity, or other valid type declaration.
- `stack.type.alias-acyclic`: Type aliases MUST NOT form a cycle.
- `stack.type.assignment`: Assigned and default values MUST be compatible with
  the destination type.
- `stack.type.operator`: Operators MUST accept the operand types supplied and
  MUST produce the type expected by the surrounding expression.
- `stack.type.condition-boolean`: Conditions, guards, filters, and transition
  predicates MUST evaluate to boolean.
- `stack.type.nullability`: A required value MUST NOT receive a null or missing
  value. Optionality and cardinality MUST be preserved through mappings.
- `stack.type.enum-member`: An enum value MUST belong to its declared enum.
- `stack.type.collection`: Collection element types and cardinalities MUST be
  compatible in assignments, mappings, and bindings.
- `stack.value.range`: Numeric values MUST satisfy applicable minimum, maximum,
  positivity, percentage, probability, capacity, duration, and count ranges.
- `stack.value.finite`: Numeric values used for execution, thresholds, weights,
  or probabilities MUST be finite.
- `stack.value.unit-compatible`: Compared, added, assigned, or mapped quantities
  MUST use compatible units. Conversions MUST be explicit when units differ.
- `stack.value.default-valid`: Defaults MUST satisfy the same validation rules
  as runtime values.

### References and ownership

- `stack.reference.resolved`: Every reference MUST resolve to exactly one
  declaration.
- `stack.reference.no-dangling`: Removing or deprecating a declaration MUST NOT
  leave dangling references.
- `stack.reference.direction`: Source, target, input, output, from, and to
  references MUST point in the direction required by the construct.
- `stack.ownership.single`: A construct with a single-owner relationship MUST
  have exactly one owner.
- `stack.ownership.boundary`: A grammar MUST reference, rather than redefine, a
  construct owned by another grammar. Each consuming stack MUST publish its
  concrete ownership map and validate every cross-module boundary against it.

### Graphs

- `stack.graph.endpoint-resolved`: Every edge endpoint MUST resolve to a node in
  the graph or to an explicitly permitted external endpoint.
- `stack.graph.edge-unique`: Duplicate equivalent edges SHOULD be rejected or
  warned unless parallel edges are meaningful and explicitly distinguished.
- `stack.graph.reachability`: Required terminal nodes MUST be reachable from a
  valid entry node.
- `stack.graph.unreachable`: Unreachable nodes SHOULD produce warnings.
- `stack.graph.dead-end`: A nonterminal executable node without an outgoing path
  SHOULD produce a warning or error according to the graph kind.
- `stack.graph.cycle-policy`: Cycles MUST be rejected in graphs declared
  acyclic. Cycles in executable graphs MUST have an explicit exit or termination
  condition.
- `stack.graph.no-self-edge`: Self-edges MUST be rejected unless the construct
  explicitly supports them.

### Ordering, time, and schedules

- `stack.order.unique`: Explicit indexes, priorities, sequence numbers, and
  ordering keys MUST be unique within their containing scope.
- `stack.order.contiguous`: Stage indexes SHOULD be contiguous unless sparse
  ordering is explicitly supported.
- `stack.time.duration`: Durations, intervals, timeouts, backoffs, retention
  periods, and windows MUST be nonnegative; execution intervals and timeouts
  that must advance time MUST be greater than zero.
- `stack.time.schedule-valid`: Schedule expressions MUST parse according to the
  configured schedule dialect and MUST identify a time zone when interpretation
  would otherwise be ambiguous.
- `stack.time.window-compatible`: Windows, sampling frequencies, retention, and
  aggregation intervals MUST be mutually compatible.

### Security, governance, and observability

- `stack.security.authorization`: An executable action MUST have an applicable
  authorization rule or an explicit public/system exemption.
- `stack.security.least-privilege`: Granted permissions SHOULD be no broader
  than required by referenced actions.
- `stack.security.boundary`: Data or control crossing a trust boundary MUST have
  an applicable security control.
- `stack.security.secret`: Secrets and credentials MUST NOT appear as literal
  scalar values; they MUST be references to protected secret material.
- `stack.governance.owner`: Governed production constructs SHOULD identify an
  accountable owner.
- `stack.governance.audit`: Security-sensitive, approval, policy, and automated
  actions SHOULD identify an audit or evidence path.
- `stack.observability.failure`: Executable integrations, pipelines, and
  deployments SHOULD define failure reporting and operational observability.
