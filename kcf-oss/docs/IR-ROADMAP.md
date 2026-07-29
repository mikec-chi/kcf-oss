# IR roadmap — the `needs-ir-extension` rules

The semantic-rule catalogue contains **89 rules** that `kcf automation-report` classes
`needs-ir-extension` (see per-rule reasons in
[`semantics/automation-triage-overrides.json`](../semantics/automation-triage-overrides.json)).
They are **not** an analyzer backlog: they cannot be mechanically enforced against
*today's* IR because the IR has no field to express what they require. This document is
the explicit product decision the review asked for — for each theme, whether it is:

- an **IR-RFC candidate** — the requirement is genuinely part of KCF's normative
  semantics, so the grammar/IR (`model-ir-v1`) should gain fields to express it, after
  which the rule becomes mechanically enforceable (a Grammar RFC per
  [`docs/EXTENDING.md`](EXTENDING.md) + a [`docs/VERSIONING.md`](VERSIONING.md) decision); or
- **downstream guidance** — the requirement is implementation/operational advice, not an
  enforceable property of a domain *model*, so it should read as codegen-pack guidance
  or a runtime concern, not an analyzer rule. These are candidates to reclassify out of
  `manual-review` entirely.

Until an RFC lands, a `needs-ir-extension` rule stays in the catalogue as documented,
honestly-labelled, **unenforced** normative intent — it does not pretend to be checked.

## IR-RFC candidates

> RFC-1…RFC-8 derive from the `needs-ir-extension` analyzer rules above. **RFC-10 and
> RFC-11 originate from community field reports** (`community/field-reports/`), not the
> automation catalogue — the same routing applies: an additive grammar/IR change lands only
> via a Grammar RFC + VERSIONING decision, never a silent change.

### RFC-1 — an IR type system (12 rules)
`stack.type.assignment/collection/condition-boolean/known/nullability/operator`,
`stack.value.finite/unit-compatible`, `stack.time.duration/window-compatible`,
plus it unblocks the collection/transform themes below.

The IR has no first-class type system: attribute `type` is a bare string, and there is
no representation of unit compatibility, nullability at use sites, operator operand
types, or boolean-valued conditions. A typed IR (primitive/alias/enum/schema/entity
types + units + nullability + an expression type) would make these checkable. **The
single highest-leverage extension** — several other themes depend on it.

### RFC-2 — transformation lineage & typed field mapping (19 rules)
`action.transform.*` (10) and `action.collection.*` (9).

Transforms and collection pipelines carry `inputs`/`outputs` at the identity level but
no **field-level** lineage or typed mapping, so type/unit/null/totality/loss/equality/
cardinality checks have nothing to read. Depends on RFC-1. Extension: per-field source→
target mapping with transformation + declared totality/null behavior.

### RFC-3 — action field-level I/O contracts (23 rules)
`action.record.*` (9), `action.invoke.*` (7), `action.set.*` (7).

Actions declare an operation/scope/target and coarse cardinalities, but not the
**field-level** input/output shape, the required-field set, patch dialect, pagination/
result shape, or the invocation contract an invoked action resolves to. Extension: an
action I/O contract (provided fields, returned shape, selection key, pagination).

### RFC-4 — action execution semantics (7 rules)
`action.concurrency.version/lost-update`, `action.transaction.required`,
`action.idempotency.conditional`, `action.retry.bound/classification`,
`action.transaction.external` *(external is partly a runtime fact — see guidance)*.

No fields for an optimistic version/comparison token, a declared "requires atomicity",
an idempotency key/condition, or a retry backoff/failure-classification policy.
Extension: an execution-semantics block on state-changing actions.

> **Vocabulary landed (additive, IR "1.1" extension).** `model-ir-v1` `$defs/action` now carries the
> executable-contract fields that these rules require: `expectedVersion` (optimistic-concurrency
> token → `action.concurrency.version/lost-update`), `idempotencyKey` (→ `action.idempotency.*`),
> `transactionBoundary` (→ `action.transaction.required`), plus `preconditions`/`postconditions`.
> They author as `expected-version`, `idempotency-key`, `transaction-boundary`, `precondition`,
> `postcondition` and flow end-to-end (see `tests/domains/executable-contract.kcf`). The fields are
> **optional and backward-compatible**, so no `irVersion` bump was forced (a formal `1.1.0` stamp is a
> `docs/VERSIONING.md` decision); the rules above are now *mechanically automatable* against the IR —
> each still needs an analyzer handler + invalid-fixture case to move to `automated`.

### RFC-5 — operational safety & composition (9 rules)
`action.destructive.recovery/retention/scope`, `action.device.safety`,
`action.compose.order/saga`, `action.event.commit-order/duplicate/payload`.

No representation of delete-behavior/retention/recovery, device interlocks/permissives,
saga forward/compensation composition, or event before/after (commit-order) semantics.
Extension(s): destructive-action policy, a saga/composition construct, and event
change-semantics.

> **Vocabulary partially landed (additive).** `$defs/action` now carries `deleteBehavior`, `retention`,
> `reversibility`, and `compensation` (author: `delete-behavior`, `retention`, `reversibility`,
> `compensation`) — unblocking `action.destructive.recovery/retention` and the forward/compensation
> half of `action.compose.saga`. Set/bulk safety gains `bulkLimit`/`bulkOrdering`/`bulkFailurePolicy`
> (author: `bulk-limit`, `bulk-ordering`, `bulk-failure`). Still **needing IR work**: device
> interlocks/permissives, saga ordering across multiple steps, and the event commit-order/duplicate/
> payload contract (an event-change-semantics block — the next slice).

### RFC-6 — relationship reasoning semantics (5 rules)
`kcf.relationship.canonical/condition/inverse/participation/transitivity`.

The relationship algebra stores edges but not the canonical-direction/inverse-derivation,
guard conditions, or declared-and-valid transitivity that these rules assume.
Extension: relationship reasoning qualifiers.

### RFC-7 — integration field mappings (4 rules)
`integration.contract.schema`, `integration.mapping.coverage`, `integration.protocol`,
`integration.retry.idempotency`.

The `integration` section has adapters/endpoints/routes but no field-level source→target
mapping or protocol/serialization contract to check coverage against.

### RFC-8 — specialization, traits & lineage schema (5 rules)
`kcf.concept.kind-compatible/trait/version`, `lineage.binding.schema`, `lineage.complete`.

Specialization kind-refinement, trait-permission constraints, per-construct version
compatibility, and lineage field-schema/derived-artifact completeness need declarations
the IR does not yet carry.

### RFC-10 — authorable human `label` / `description` on concepts & attributes (field report `20260728-12`)

Concepts and attributes have no authorable human **label**/**description**, so a domain
term an identifier can't convey (acronyms, regulatory phrasings) cannot override the
codegen-derived label. This is compounded by a **doc↔parser drift**: the metagrammar's
`metadata` production (`grammars/core/KCF-v1.0-Semantic-Metagrammar.ebnf:103-104`) advertises
`metadata { label; description; … }`, and it is wired into the *meta* definitions
(`concept-kind-def`, `trait-def`, `profile-def`, …) — but **not** into entity/attribute
authoring: `parse_concept`'s catch-all treats an unknown keyword as a scalar metadata pair,
so an entity-level `metadata { … }` block and an attribute-level `attr: T { label: … }`
block both fail to parse (`expected scalar/';' , found '{'`). So the surface reads as
advertised-but-unavailable where a modeler would reach for it.

Extension (additive, opt-in): an **advisory** `label`/`description` on both concepts and
attributes — analyzer-ignored like other advisory metadata — projecting to
`concept.label/description` and `attribute.label/description` in `model-ir-v1`. Codegen uses
them as the label, falling back to the `humanize()` derivation (codegen system-prompt
rule 12) when absent — which is why the *default* UX already shipped as a codegen convention
(field report `20260728-11`), independent of this RFC. Reconcile the reference compiler with
the metagrammar's `metadata` block at the entity/attribute level (or, if the block is not
intended there, correct the metagrammar so it stops advertising an unavailable surface).
Grammar/IR + compiler change → **Grammar RFC + VERSIONING** (additive; labels optional,
derivation remains the default; no `irVersion` break since the fields are optional).

### RFC-11 — design page `section`s that bind fields (model-driven record layout) (field report `20260728-10`)

A `design` page `section` is a bare **name** (`ir.design.pages[].sections` is a `string[]`),
so it cannot list which of an entity's attributes belong to it. A grouped record layout
(titled field-groups — "Primary Information", "Amounts", "System") therefore can't be
model-driven; codegen falls back to a by-role heuristic (Primary / Details / Amounts / Flags
/ Dates / System) that a modeler can't override or version.

Extension (additive, opt-in): let a `section` optionally enumerate the attributes it contains
(and optional order/columns), projecting into `ir.design.pages[].sections[]` as objects
`{ id, fields: [...] }` while a bare string stays valid. Codegen then renders model-declared
field-groups, keeping the by-role heuristic as the fallback when a page declares none. This
is the *structural* half that a design-system preset (codegen `design-systems/`) deliberately
does **not** cover — a preset skins field-groups but cannot invent them. Grammar/IR change →
**Grammar RFC + VERSIONING** (additive; the object form is opt-in, the string form unchanged).

## Downstream guidance (reclassify — not a model requirement)

These read like enforceable requirements but are implementation/operational/packaging
concerns. The recommendation is to move them to the codegen pack (`codegen/`) or
operational docs and drop the "MUST" framing:

- `stack.governance.audit` — audit/evidence path is an emitter/deployment concern
  (already advisory `SHOULD`).
- `stack.graph.dead-end` — executable-graph dead-ends are a runtime/emitter warning.
- `stack.name.visibility` — export/visibility is module-packaging (already partly
  `enforced-elsewhere` via `validate_stack.py`/`lint_stack.py`).
- `kcf.extension.point` — needs an extension **registry** (governance), not a model field.
- `kcf.profile.prohibited`, `kcf.profile.relationship` — profile-authoring guidance;
  prohibited **patterns** are already enforced (`kcf.profile.pattern-prohibited`).
- `action.transaction.external` — cross-system atomicity is a runtime fact, not
  IR-checkable.
- `action.record.precondition` / `action.invoke.precondition` — preconditions are
  authorable, but "the caller must **establish** them" is a runtime obligation.

## Stable identities for currently-anonymous items (RFC-9)

An identity-bearing item that declares no `qualifiedName`/`id`/`name` is accounted for
under a **position-based** fallback (`section#index`, e.g. `math#3`, `plans#1`). This
keeps accounting exhaustive — nothing disappears — but such identities are **not stable
across reordering or versions**, so a realization manifest that references them is not
cross-version trace-stable. `verify-realization` surfaces them in
`positionUnstableIdentities`.

Decision: the schema/analyzer should ultimately **require a stable identity** on every
identity-bearing item wherever practical (many tail sections are open objects with no
required `id`). Until then, the boundary is explicit:

- Accounting is exhaustive (position-based fallback guarantees nothing is dropped).
- Cross-version trace stability is **not** guaranteed for anonymous items.

## Realization evidence levels stay separated from executed behavior

Unrelated to the above, but reaffirmed here because it is a recurring claim boundary:
`kcf verify-realization` reports an **evidence level** and never claims behavioral
proof. The ladder is strictly:

`none` → `accounted` (declared, no repo) → `artifact-verified` (files exist) →
`symbol-verified` (named symbols present) → `test-present` (test files exist).

The higher levels — `test-executed`, `contract-tested`, `behavior-verified`,
`operationally-qualified` — require executing the generated system and are **downstream
of KCF-OSS**, which stops at the IR. The correct claim is *"the handoff is exhaustively
accounted for and structurally grounded,"* never *"the generated application faithfully
implements the model."*
