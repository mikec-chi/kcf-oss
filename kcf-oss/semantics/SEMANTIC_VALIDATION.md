# KCF Semantic Validation Specification

## Validation pipeline

A conforming analyzer MUST run these phases in order:

1. Lex and parse textual KCF into a source-mapped authoring AST.
2. Load the semantic profile, dependency closure, module lock, and version graph.
3. Desugar and normalize the authoring AST into canonical semantic IR.
4. Validate the IR against its declared JSON Schema.
5. Build scopes and stable semantic identities.
6. Resolve names, primary kinds, traits, and specializations.
7. Resolve relationship definitions, assertions, and instances.
8. Validate endpoints, cardinality, qualifiers, time, and dimension constraints.
9. Derive inverses, inheritance, transitive implications, and other permitted
   reasoning while recording provenance.
10. Resolve runtime capability contracts and bindings.
11. Build validation, reasoning, and execution plans.
12. Verify that selected emitters support every required semantic element.

Diagnostics MUST identify severity, stable rule ID, module, source location,
subject, message, related declarations, and a correction when known. Missing
external registries or runtime information must be reported as `unavailable`,
not silently treated as valid.

This document is the normative human/LLM-readable rule specification.
`build_semantic_rules.py` combines its stable-ID rules with stack-neutral rules
from `../semantic-core` and emits `semantic-rules.json`. KCF has no DBML build
dependency. KCF-local wording may refine a neutral rule without changing its
owner. The JSON catalogue is governed by `semantic-rules.schema.json`; analyzer
diagnostics MUST use IDs from that catalogue and declare their enforcement
status, phase, handler when automated, and legacy aliases when applicable.

## Universal concept rules

- `kcf.concept.identity`: Every grammar definition, domain assertion, and
  runtime instance MUST have stable identity within its layer.
- `kcf.concept.primary-kind`: A concept MUST have exactly one primary kind
  unless an approved semantic bridge explicitly supports a composite case.
- `kcf.concept.kind-compatible`: Specialization MUST preserve or legally
  refine primary kind.
- `kcf.concept.layer`: Grammar definitions, domain assertions, runtime
  instances, and emitted artifacts MUST NOT be conflated.
- `kcf.concept.reference`: Every semantic reference MUST resolve exactly once
  to a visible construct of the required kind and compatible version.
- `kcf.concept.trait`: Applied traits MUST be permitted by the concept kind
  and all trait constraints MUST hold.
- `kcf.concept.abstract`: Abstract or non-instantiable constructs MUST NOT
  have runtime instances.
- `kcf.concept.cardinality`: Attribute and relationship values MUST satisfy
  declared lower and upper bounds.
- `kcf.concept.provenance`: Derived, promoted, corrected, or governed
  semantics MUST retain source, evidence, and approval provenance.
- `kcf.concept.version`: Breaking semantic changes require a new major
  version; compatible additions require a minor version; clarifications require
  a patch version.

## Profile and extension rules

- `kcf.profile.import`: Profile imports MUST exist, be version-compatible,
  and have an acyclic dependency graph except for declared type-only cycles.
- `kcf.profile.required`: Every required construct MUST be present.
- `kcf.profile.prohibited`: Prohibited constructs MUST not appear directly or
  through an unapproved specialization.
- `kcf.profile.relationship`: Profile relationship restrictions MUST be at
  least as strict as the underlying definition.
- `kcf.profile.term`: Lexical mappings MUST resolve, be locale-aware when
  needed, and surface ambiguous mappings rather than selecting silently.
- `kcf.extension.point`: Extensions MUST use a declared extension point and
  obey its compatibility/governance policy.
- `kcf.extension.ownership`: Extensions MUST NOT redefine constructs owned by
  another dimension.
- `kcf.extension.promotion`: Runtime discoveries promoted into grammar
  semantics require evidence, review, version impact analysis, and approval.

## Relationship algebra rules

- `kcf.relationship.root-kind`: Every relationship MUST specialize exactly
  one root kind: classification, composition, association, identity,
  participation, dependency, transformation, causation, ordering, or governance.
- `kcf.relationship.endpoint`: Source and target MUST satisfy kind, concept,
  trait, and runtime predicate constraints.
- `kcf.relationship.canonical`: One canonical direction MUST be stored;
  inverse traversal MUST be derived from the declared inverse.
- `kcf.relationship.inverse`: Forward and inverse verbs MUST express the same
  relationship with reversed roles.
- `kcf.relationship.symmetry`: A symmetric relationship MUST accept swapped
  endpoints and equivalent meaning. A bidirectional relationship need not be
  symmetric.
- `kcf.relationship.transitivity`: Transitive inference is allowed only when
  explicitly declared and valid for the relationship mode.
- `kcf.relationship.cardinality`: Assertions and runtime instances MUST obey
  source and target cardinalities.
- `kcf.relationship.temporal`: Effective and runtime validity intervals MUST
  be well-formed and compatible with endpoint validity.
- `kcf.relationship.condition`: Conditions MUST be boolean and true in the
  relevant context before an assertion/instance is applicable.
- `kcf.relationship.polarity`: Negative, prohibitive, or opposing relations
  MUST not be treated as positive facts.
- `kcf.relationship.strength`: Strength/confidence values MUST be in the
  configured range and MUST NOT be interpreted as certainty without warrant.
- `kcf.relationship.classification`: Classification and identity MUST remain
  distinct.
- `kcf.relationship.participation`: Participation and governance MUST remain
  distinct.
- `kcf.relationship.dependency`: Dependency MUST NOT imply causation.
- `kcf.relationship.association`: Association is a descriptive fallback and
  MUST NOT absorb relationships with a more precise root kind.
- `kcf.relationship.ordering`: Ordering MUST declare its dimension, such as
  workflow, temporal, version, or priority.
- `kcf.relationship.reification`: Reify a relationship only when it needs
  independent state, evidence, qualifiers, history, or runtime behavior.

## Entity rules

- Entity identities and attribute names MUST be unique and typed.
- Composition and identity graphs MUST be acyclic where required.
- References and collection memberships MUST resolve and satisfy cardinality.
- A mutation MUST identify its subject and declarative changes.
- Mutation values MUST type-check; preconditions and postconditions MUST be
  boolean; emitted events MUST resolve.
- Mutation retries MUST obey declared idempotency.
- Required invariants MUST hold before and after every committed mutation.
- CRUD APIs are emitter choices. They MUST preserve identity, mutation,
  composition, membership, archive, provenance, and validation semantics.

## Actor and organization rules

- `organization.kind`: Every organization declaration MUST use a supported
  organization kind.
- `organization.parent.reference`: An organizational parent MUST resolve to an
  organizational concept.
- `organization.hierarchy.acyclic`: Organizational parent relationships MUST be
  acyclic.
- `organization.member.reference`: Members, roles, authority domains, owned
  subjects, and accountability subjects MUST resolve.
- `organization.reporting.reference`: Reporting endpoints MUST resolve to Actor
  or Organizational concepts.
- `organization.reporting.temporal`: Reporting validity intervals MUST be
  well-formed.
- `organization.escalation.path`: Escalation paths MUST contain at least two
  resolvable, nonrepeating endpoints.
- `organization.accountability.distinct`: Responsibility, accountability,
  ownership, authority, and reporting MUST remain distinct semantics.
- Actor kind MUST be one of the permitted human, role, collective, system,
  agent, machine, or external categories.
- Roles, capabilities, skills, authority, responsibility, accountability, and
  membership references MUST resolve to the correct kinds.
- Authority conditions and validity MUST hold at execution time.
- Required skills/capabilities do not alone authorize work; current authority,
  availability, resource constraints, state, policy, and tool availability must
  also pass.
- Responsibility and accountability MUST remain distinct.
- Reporting and escalation graphs MUST not contain unintended cycles.
- Organization structure and collective actor identity SHOULD be separate when
  they require different runtime behavior.

## Work and action rules

- `action.contract.incomplete`: Every Action contract MUST declare effect,
  operation, scope, target, input/output cardinality, and command idempotency;
  fields required by its selected operation/scope MUST also be present.
- Action, decision, task, activity, process, capability, and step MUST retain
  their distinct meanings.
- Work subjects, performers, inputs, outputs, outcomes, resources, tools, rules,
  events, and temporal references MUST resolve by kind.
- Preconditions MUST hold before execution; completion and postconditions MUST
  hold before successful completion.
- Failure conditions MUST produce declared failure behavior, evidence, and any
  required compensation.
- Output production MUST NOT be treated as Intent/outcome achievement without an
  explicit success evaluation.
- Process step references and transitions MUST resolve; required terminal states
  must be reachable; invalid deadlocks/livelocks must be reported.
- Capability is an ability to achieve an outcome, skill is competence, tool is
  actuation, actor supplies agency, and work is the performed activity.

### Record, set, and transformation semantics

- Record actions MUST declare target identity and whether they create, read,
  replace, update, patch, delete, upsert, archive, assign a reference, or manage
  membership.
- Record update/delete selections MUST be provably unique; nonunique selection
  is a set operation.
- Set mutations MUST declare an explicit predicate/key set/partition or `all`,
  atomicity, partial-failure behavior, concurrency policy, and result shape.
- An omitted selection on bulk update/delete is invalid; explicit `all` should
  require impact review or approval.
- Collection operations such as select, project, filter, map, flat-map,
  distinct, sort, group, aggregate, join, union, intersect, except, window,
  sample, partition, and deduplicate MUST validate input/output schemas,
  cardinality, boundedness, ordering, equality, and grain.
- Transformations MUST provide field-level lineage, required-target coverage,
  type/unit/cardinality compatibility, null/error behavior, loss declarations,
  identity behavior, classification propagation, determinism, and version
  compatibility.
- Pure transformations MUST keep persistence, messaging, command dispatch, and
  other side effects outside the transformation or declare an explicit effect
  boundary.
- Retriable commands MUST be idempotent, conditionally idempotent with a stable
  key, or protected by duplicate suppression/compensation.
- Cross-system actions MUST NOT claim atomicity that their implementations cannot
  provide; use saga, outbox, compensation, or reconciliation semantics.

## Event rules

- `kcf.event.immutable`: Historical event facts MUST be immutable;
  corrections require a new event, supersession, reconciliation, or provenance
  update that preserves the original observation.
- Event subjects, sources, observers, correlation keys, triggers, lifecycle
  effects, and evidence MUST resolve.
- Occurrence time and detection time MUST be distinguished and temporally valid.
- Historical event facts are immutable. Corrections MUST use correction events,
  superseding observations, reconciled facts, or provenance/confidence updates.
- Derived events MUST preserve derivation and causal provenance.
- Duplicate delivery, ordering, correlation, and late-arrival behavior MUST be
  explicit where runtime delivery is nondeterministic.

## Process orchestration rules

- `process.single-initial`: Each executable process MUST have exactly one
  effective start node after profile composition.
- `process.final`: Each executable process MUST contain at least one end
  node or a declared nonterminating-service policy.
- `process.state-unique`: Process node identities MUST be unique in their
  process scope.
- `process.transition-endpoints`: Every process flow and boundary event
  MUST reference nodes declared in its process.
- `process.reachability`: Every required process node and at least one end
  node MUST be reachable from the effective start.
- Gateways MUST declare deterministic evaluation/priority where outgoing
  conditions can overlap; parallel joins MUST define synchronization behavior.
- Called processes, lane performers, intermediate events, compensations,
  timeouts, and boundary handlers MUST resolve to compatible semantic kinds.

## Integration profile rules

- `integration.endpoint`: Endpoint adapter references and route endpoints
  MUST resolve within the integration model.
- `integration.protocol`: Endpoint operation, address, serialization,
  authentication, and payload mapping MUST be compatible with the adapter
  protocol.
- `integration.contract.schema`: Contract inputs and outputs MUST be compatible with
  the referenced Action contract and Information schemas.
- `integration.mapping.coverage`: Required target fields MUST have a source mapping,
  default, or explicit omission policy.
- `integration.retry.idempotency`: A retrying integration MUST require idempotency,
  duplicate suppression, compensation, or another declared safety mechanism.
- Routes and event bridges MUST define correlation, ordering, timeout,
  late-arrival, duplicate-delivery, and failure behavior where applicable.

## Security profile rules

- `security.risk.references`: Each risk MUST reference a declared threat and asset.
- `security.risk.level`: Risk level MUST agree with the configured likelihood and
  impact method unless an authorized, justified override is recorded.
- `security.risk.mitigation`: High or critical risk MUST have mitigation, transfer,
  avoidance, or governed acceptance with an owner and expiry/review date.
- `stack.security.authorization`: Every executable command MUST have an
  applicable authorization rule or an explicit public/system exemption.
- `stack.security.boundary`: Every data/control crossing of a trust boundary
  MUST have an applicable security control.
- `stack.security.least-privilege`: Runtime bindings and emitted permissions
  MUST grant only the capabilities and data scope required by the action.
- Asset classifications MUST propagate through mappings, transformations,
  derived Information, analytics, AI features, and emitted artifacts unless an
  approved declassification rule applies.

## Lineage, binding, and cost rules

- `action.transform.field-lineage`: Every transformed target field MUST identify
  its contributing source fields, transformation, and execution provenance.
- `lineage.cycle`: Lineage MUST be acyclic unless a documented iterative
  computation defines convergence, termination, and provenance behavior.
- `lineage.complete`: Every derived dataset, metric, model output, report,
  decision, and automated action SHOULD have a lineage path to its origins.
- `lineage.binding.unique`: A target declared single-source MUST not have
  conflicting active bindings.
- `lineage.binding.schema`: Bound source and target schemas, field types, units,
  cardinalities, and classifications MUST be compatible.
- `lineage.cost.nonnegative`: Cost amounts and rates MUST be finite, nonnegative,
  unit-compatible, and attached to a subject and allocation period where needed.

## Emitter-profile rules

- `experience.flow.entry`: Every experience flow MUST declare an entry that resolves to a node in that flow.
- `experience.flow.transition`: Every experience-flow transition source and target MUST resolve to nodes in the containing flow.

- `architecture.reference.kind`: Architecture service, interface, topology, node,
  boundary, artifact, environment, and capability references MUST resolve to
  compatible kinds.
- `architecture.deployment.complete`: Required runtime services MUST have compatible
  deployment targets or an explicit external-runtime declaration.
- `experience.app.reference`: Experience application entries, views, flows,
  components, and layouts MUST resolve.
- `experience.action.invoke`: UI/experience actions MUST resolve to Action contracts
  applicable to the bound subject; hiding UI never replaces authorization.
- `experience.view.kind`: A declared experience view `kind` MUST be one of the known
  view kinds (list, form, tree, chart, dashboard, map, kanban, gantt, custom); a view
  with no kind keeps default list/detail behaviour (RFC-15).
- `experience.view.binding`: A view's KIND-specific binding MUST resolve, either declared
  on the view or inferable from the bound entity's existing semantics (chart→MEASURE,
  kanban→LIFECYCLE, gantt→TEMPORAL start/end, tree→self-COMPOSITION, map→SPATIAL,
  dashboard→tiles, custom→registered renderer); list/form/tree/map/kanban/gantt need a
  resolvable bound entity (RFC-15).
- `experience.flow.reachability`: Required experience-flow nodes and a terminal route
  MUST be reachable from the declared entry.
- `design.design-system.unique`: Design token, breakpoint, pattern, and constraint
  identities MUST be unique in their design-system scope.
- `design.scale.order`: Ordered numeric scales and breakpoints MUST be finite,
  unique, and strictly increasing.
- `design.page.binding`: Page/view/section bindings MUST resolve to compatible
  Experience constructs.
- `analytics.binding.kind`: Analytics visual, metric, filter, and action bindings
  MUST resolve both endpoints to compatible kinds.
- `ai.feature.keys`: AI feature identities and keys MUST be unique and resolve
  in the applicable feature schema.
- `ai.feature.target`: A training target MUST name a declared feature and MUST
  be excluded from inputs where inclusion would create leakage.
- `ai.pipeline.order`: AI pipeline steps MUST be uniquely ordered and every
  input MUST exist before use.
- `ai.serving.model`: Served models MUST resolve to deployable governed model
  versions.
- `ai.serving.capacity`: Serving capacity and concurrency values MUST be
  positive and compatible with the deployment runtime.

## Lifecycle rules

- `lifecycle.single-initial`: Every executable lifecycle MUST have exactly one effective initial state after profile composition.
- `lifecycle.final`: Every terminating lifecycle MUST declare at least one terminal state; intentionally nonterminating lifecycles MUST declare that policy explicitly.

- State names MUST be unique; exactly one initial state and at least one terminal
  state are required.
- Transition endpoints, triggers, required work, effects, entry behavior, and
  exit behavior MUST resolve.
- Guards and invariants MUST be boolean and valid for the governed concept kind.
- Every reachable nonterminal state SHOULD have a viable outgoing transition.
- Lifecycle state evolution MUST remain distinct from workflow/process steps.

## Rule and logic rules

- Rule applicability targets and effects MUST resolve.
- Conditions and predicates MUST type-check and evaluate to boolean.
- Permissions allow, prohibitions block, obligations require, recommendations
  influence, and discretion permits authorized judgment; runtimes MUST preserve
  these different effects.
- Conflicts MUST be resolved by declared priority, specificity, authority,
  effective date, exception hierarchy, or explicit strategy, never evaluation
  order.
- Quantifiers and modal operators MUST use a declared domain and interpretation.
- Formula/function types and arity MUST be valid; mathematical dependencies must
  obey cycle and termination policies.
- Probabilities/confidence MUST be in range and probability distributions must
  normalize within declared tolerance.

## Information rules

- `information.kind`: Every information declaration MUST use a supported
  information kind.
- `information.reference`: Information subjects, authors, sources, audiences,
  schemas, freshness policies, reviewers, evidence, and access policies MUST
  resolve.
- `information.temporal`: Information validity intervals MUST be well-formed.
- `information.provenance`: Governed information MUST identify a source,
  evidence, or source document and its recording time.
- `knowledge.ingestion.trace`: Extracted knowledge MUST record source document,
  source location, extraction method, extraction model, confidence, recording
  time, and human review.
- `knowledge.access.policy`: Classified or confidential knowledge MUST reference
  an applicable access policy.
- Schema field names MUST be unique, typed, and cardinality-valid.
- Subject, author, source, audience, schema, and provenance references MUST
  resolve.
- Representation MUST support the schema and intended audience/runtime.
- Confidentiality, trust, freshness, completeness, and effective period MUST be
  enforced and propagated.
- A managed agreement Entity, its Information document, and extracted Rule
  clauses MUST remain distinct concepts linked by relationships.

## Resource rules

- `kcf.resource.capacity`: Concurrent allocations and reservations MUST NOT
  exceed available resource capacity under the active scheduling policy.
- Capacity, quantity, cost, and allocation values MUST be finite, nonnegative,
  and unit-compatible.
- Allocations MUST reference valid resources and consumers and must not exceed
  available capacity under applicable concurrency/reservation policy.
- Consumption, reservation, release, replenishment, contention, and sharing
  semantics MUST be consistent with resource kind.
- Resource definitions and physical/scheduled resource instances MUST remain
  distinct.

## Temporal and spatial rules

- Time intervals require start <= end; duration must agree with start/end;
  recurrence and schedule syntax must be valid.
- Business calendars, time zones, deadlines, grace periods, and calculations
  MUST resolve and handle daylight-saving ambiguity.
- Spatial containment MUST be acyclic; adjacency SHOULD be symmetric unless
  direction is explicitly meaningful.
- Coordinates and geometry MUST be valid for their coordinate reference system.
- Routes must connect valid locations and satisfy via, jurisdiction, movement,
  capacity, and distance constraints.
- Temporal and spatial primitives are values; business deadlines, calendars,
  locations, jurisdictions, and routes are semantic concepts.

## Intent and measure rules

- Intent desired state, success, and failure conditions MUST be boolean and
  noncontradictory.
- Stakeholders, measures, time horizon, and tradeoff references MUST resolve.
- Priorities and tradeoff weights must use one declared comparison policy.
- Measure subjects, units, calculations, periods, thresholds, targets, and
  tolerances MUST resolve and be type/unit-compatible.
- Scale type must permit the selected aggregation and comparison.
- Ratio/percentage measures must handle zero denominators explicitly.
- Produced outputs and achieved outcomes MUST be evaluated separately.

## Reasoning rules

- `reasoning.complete`: Reasoning MUST declare kind, proposition, and method;
  inference and fact claims MUST include supporting premises or evidence.
- `reasoning.reference`: Premises, evidence, contradictions, alternatives,
  reviewers, and access policies MUST resolve.
- `reasoning.confidence`: Reasoning confidence MUST be in `[0,1]`.
- `reasoning.contradiction`: Contradictions MUST reference a distinct reasoning
  or assertion identity and remain visible rather than overwriting either claim.
- Proposition, premises, evidence, conclusions, assumptions, contradictions, and
  alternatives MUST resolve or type-check.
- Deductive conclusions require entailment; inductive conclusions require
  supporting observations; abductive conclusions are plausible explanations;
  causal conclusions require causal semantics; probabilistic conclusions require
  calibrated confidence.
- Confidence MUST be in `[0,1]` and retain method/evidence provenance.
- Contradictory claims MUST be surfaced rather than silently overwritten.
- Inference MUST record rule, inputs, method, time, and confidence provenance.

## Organizational knowledge rules

- `rule.complete`: Rules MUST declare kind, condition, and at least one effect.
- `rule.reference`: Rule applicability, effects, authority, exceptions,
  evidence, reviewers, and access policies MUST resolve.
- `rule.policy.authority`: Every policy authority MUST resolve to an Actor or
  Organizational concept.
- `rule.policy.members`: Every rule selected by a policy MUST resolve to a Rule
  concept.
- `rule.conflict.strategy`: Potentially conflicting permission, prohibition, or
  obligation rules over the same subject MUST declare a deterministic conflict
  strategy.
- `knowledge.assertion.subject`: Every knowledge assertion subject MUST resolve.
- `knowledge.assertion.status`: Every assertion MUST retain an explicit
  epistemic status: asserted, inferred, disputed, superseded, retracted, or
  unknown.
- `knowledge.assertion.provenance`: Asserted, inferred, or disputed statements
  MUST record evidence or a source document, recording time, and reviewer when
  produced by automated extraction.
- `knowledge.assertion.temporal`: Assertion valid-time intervals MUST be
  well-formed and distinct from recording time.
- `knowledge.assertion.inference`: Inferred assertions MUST reference the
  reasoning that derived them.
- `knowledge.assertion.supersession`: Supersession MUST reference an existing,
  distinct assertion while preserving the superseded statement.
- `knowledge.assertion.contradiction`: Contradiction links MUST resolve to
  distinct assertions; contradictory assertions MUST coexist for review.
- `knowledge.identity.canonical`: Every identity resolution MUST reference one
  canonical concept.
- `knowledge.identity.ambiguity`: The same alias or external identity MUST NOT
  resolve to multiple active canonical concepts.
- `knowledge.identity.transition`: Merged identities MUST name merge sources;
  split identities MUST name split targets; every referenced identity MUST
  resolve.
- `knowledge.query.policy`: Every knowledge query MUST declare world assumption,
  negation, inference, and temporal policies.
- `knowledge.query.negation`: Negation-as-failure is valid only under an explicit
  closed-world assumption.
- `knowledge.query.temporal`: An as-of query MUST declare its effective
  timestamp.
- `knowledge.bitemporal.recorded`: Governed assertions and extracted knowledge
  MUST distinguish valid time from recording time.
- `knowledge.graph.complete`: Graph emitters MUST preserve concepts,
  relationships, organizational knowledge, assertions, provenance, epistemic
  status, identity reconciliation, and query policy or report unsupported
  meaning.

## Compilation, runtime, and emitter rules

- `kcf.profile.pattern-required`: A model using a business-pattern profile MUST
  explicitly implement every required pattern and model the pattern's semantic
  obligations.
- `kcf.profile.pattern-prohibited`: A model MUST NOT implement a pattern
  prohibited by any selected profile.
- `kcf.profile.pattern-exclusion`: A required pattern MUST NOT be excluded;
  exclusions of recommended patterns SHOULD be explicit and reviewable.
- `kcf.emitter.unsupported`: An emitter MUST diagnose every semantic element
  it cannot preserve according to the configured error/warn/preserve policy;
  silent semantic loss is forbidden.
- Semantic analysis MUST resolve names, kinds, relationships, cardinality,
  constraints, visibility, and version compatibility before IR generation.
- Normalization MUST preserve identity, provenance, conditions, temporal
  semantics, and semantic deltas while expanding aliases/inverses/defaults.
- IR concepts/relationships MUST trace back to source declarations.
- Capability requirements must be derived from semantics, not guessed from
  emitter technology.
- Runtime bindings MUST satisfy capability input/output kinds, versions,
  preconditions, postconditions, side effects, idempotency, authorization,
  evidence, environment, and failure modes.
- Fallback bindings MUST preserve the same capability contract.
- Validation/reasoning/execution plan step order must be unique and dependency
  correct; execution compensation/failure paths must resolve.
- Emitters MUST declare supported semantics and MUST error, warn, or preserve an
  unsupported element according to policy. Silent semantic loss is forbidden.
- Registry entries require valid versions, locations, checksums when configured,
  dependencies, lifecycle status, and compatibility metadata.
- Dynamic loading MUST enforce dependency, version, trust, isolation, and
  extension-boundary policies.
- Generated packages should reference shared grammar modules instead of copying
  their definitions.

## Analyzer-enforced structural and reference rules

These rules are enforced directly by the semantic analyzer (`tools/semantic_analyzer.py`)
as enum-membership and reference-resolution checks per dimension. They are catalogued
here so the rule set documents the enforcement the analyzer already performs.

- `action.operation.unknown`: An action's operation MUST be a recognized value.
- `action.scope.unknown`: An action's scope MUST be a recognized value.
- `action.selection.unknown`: An action's selection MUST be a recognized value.
- `action.cardinality.unknown`: An action's input and output cardinalities MUST be recognized values.
- `action.atomicity.unknown`: An action's atomicity mode MUST be a recognized value.
- `action.concurrency.unknown`: An action's concurrency mode MUST be a recognized value.
- `kcf.concept.unknown-field`: An unrecognized concept field SHOULD be verified — it is captured as free metadata and may be a typo or an unsupported field.
- `kcf.entity.reference`: An entity reference target MUST resolve to a declared concept.
- `kcf.entity.collection`: An entity collection's element type MUST resolve.
- `kcf.entity.composition`: An entity composition target MUST resolve.
- `kcf.entity.constraint`: An entity constraint reference MUST resolve.
- `kcf.entity.lifecycle`: An entity's lifecycle reference MUST resolve.
- `kcf.entity.cardinality`: An entity attribute or relationship cardinality MUST be a recognized value.
- `kcf.entity.orphan`: An entity's orphan policy MUST be a recognized value.
- `kcf.entity.category-vocab`: An entity's data-management category SHOULD be a recognized vocabulary value.
- `kcf.entity.category-shape`: An entity's declared category SHOULD match the shape derived from its structure.
- `kcf.entity.containment-vocab`: An entity's containment tag SHOULD be a recognized vocabulary value.
- `kcf.entity.containment-shape`: An entity's declared containment role SHOULD match its derived structure.
- `kcf.relationship.directionality`: A relationship's directionality MUST be a recognized value.
- `kcf.relationship.infer`: A relationship's inference semantics MUST be a recognized value.
- `kcf.relationship.on-delete-vocab`: A relationship's on-delete qualifier SHOULD be a recognized vocabulary value.
- `kcf.relationship.unknown-qualifier`: An unrecognized relationship qualifier SHOULD be verified.
- `kcf.actor.kind`: An actor's kind MUST be a recognized value.
- `kcf.actor.communication`: An actor's communication reference MUST resolve.
- `kcf.work.kind`: A work's kind MUST be a recognized value.
- `kcf.event.kind`: An event's kind MUST be a recognized value.
- `kcf.event.expectedness`: An event's expectedness MUST be a recognized value.
- `kcf.lifecycle.governs-kind`: A lifecycle's governed concept kind MUST be a recognized value.
- `kcf.lifecycle.temporal`: A lifecycle's temporal reference MUST resolve.
- `kcf.resource.kind`: A resource's kind MUST be a recognized value.
- `kcf.resource.consumption`: A resource's consumption mode MUST be a recognized value.
- `kcf.resource.reference`: A resource reference MUST resolve.
- `kcf.measure.kind`: A measure's kind MUST be a recognized value.
- `kcf.measure.aggregation`: A measure's aggregation MUST be a recognized value.
- `kcf.measure.scale`: A measure's scale MUST be a recognized value.
- `kcf.unit.base`: A unit's base-unit reference MUST resolve.
- `kcf.temporal.duration`: A temporal duration unit MUST be a recognized value.
- `kcf.spatial.geometry`: A spatial geometry kind MUST be a recognized value.
- `kcf.spatial.route`: A spatial route reference MUST resolve.
- `kcf.authority.mode`: An authority's mode MUST be a recognized value.
- `kcf.capability.implemented-by`: A capability's implementation reference MUST resolve.
- `kcf.capability.requires-skill`: A capability's required-skill reference MUST resolve.
- `kcf.skill.requires`: A skill's prerequisite reference MUST resolve.
- `kcf.allocation.reference`: An allocation's references MUST resolve.
- `kcf.mutation.subject`: A mutation's subject MUST resolve.
- `kcf.mutation.emit`: A mutation's emitted event MUST resolve.
- `kcf.math.reference`: A math reference MUST resolve.
- `kcf.logic.mode`: A logic modal operator MUST be a recognized value.
- `kcf.process.node`: A process node reference MUST resolve.
- `kcf.process.boundary`: A process boundary MUST attach to a known node.
- `kcf.process.gateway`: A process gateway kind MUST be a recognized value.
- `kcf.process.lane`: A process lane performer MUST resolve.

## Minimum conformance

- **Level 1 - Structural:** modules, syntax, scopes, names, kinds, references.
- **Level 2 - Relational:** endpoint compatibility, cardinality, conditions,
  time, inverses, relationship reasoning.
- **Level 3 - Dimensional:** all applicable dimension invariants.
- **Level 4 - Executable:** IR, capability contracts, bindings, plans, emitters,
  evidence, authorization, failure and compensation behavior.
- **Level 5 - Governed:** profiles, versions, provenance, extension, semantic
  delta, and testing controls.

Production KCF models SHOULD satisfy Level 5. A validator MUST report the
highest completed level and every skipped or unavailable check.
