# KCF Domain Authoring

The `AUTHORING` grammar is an ergonomic, source-controlled input language. The
compiler converts it into canonical normalized semantic IR; the analyzer and code
generation consume the IR rather than the authoring syntax directly.
The `.kcf` file is the editable source. Generated IR includes an embedded
`sourceMap` and must be regenerated after a source repair rather than edited by
hand.

```kcf
kcf model CustomerService profile business-application {
  namespace customer;

  entity Customer {
    identity customerId: UUID;
    required name: String;
  }

  event CustomerUpdated immutable;

  lifecycle CustomerLifecycle for Customer {
    initial Active;
    terminal Archived;
    transition Active -> Archived;
  }

  command ArchiveCustomer {
    operation update;
    scope record;
    target Customer;
    selection identity;
    input one;
    output one;
    mutate status;
    idempotency conditional;
    atomicity atomic;
    authorization customer.ArchivePolicy;
  }
}
```

Business-pattern profiles add explicit obligations. Claim each required pattern
only after its concepts, relationships, lifecycles, actions, policies, and
evidence have been modeled:

```kcf
kcf model CustomerOperations profile customer-relationship-management {
  namespace customer;
  implements party.identity;
  implements customer.account-contact;
  implements customer.interaction-history;
  implements customer.consent;
  implements sales.opportunity-lifecycle;
  implements activity.ownership;

  entity Customer {
    identity customerId: UUID;
  }
}
```

Use `excludes <pattern>;` only for a recommended pattern that is deliberately
out of scope. Required patterns cannot be excluded, and prohibited patterns
cannot be implemented. Pattern claims are conformance assertions, not substitutes
for the corresponding model content or review.

Compile and validate with:

```powershell
python tools/kcf.py compile model.kcf --output model-ir.json --validate
```

Supported declarations include semantic concepts, typed attributes, references,
traits, relationships, lifecycles, commands, queries, transformations,
collection operations, organizations, governed information, rules, policies,
reasoning, epistemic assertions, identity reconciliation, and knowledge-query
policies. Profile presets determine the complete module closure. Every compiled
declaration receives a source-map entry used by diagnostics.

As of grammar-stack 1.11.0 the authoring surface is comprehensive across all
sixteen dimension grammars plus the core ACTION/RELATIONSHIP algebra:

- **ENTITY** — identity (with `generated`), attributes (cardinality + qualifiers),
  `compose`, named `reference` (cardinality + inverse), embedded `collection`,
  inline `lifecycle`/`constraint` binding, and entity `mutation` blocks.
- **EVENT** — `kind`, subject/source/observer/trigger/affect-lifecycle/evidence,
  occurrence/detection time, correlation-key, severity, expectedness, match.
- **ACTOR** — kind, role/authority/responsible-for/accountable-for/member-of,
  availability, communication, plus top-level `authority` grants.
- **WORK** — performer/input/output/outcome, pre/post/completion/failure,
  requires-resource/tool, governed-by/triggered-by/emit/compensate-with/temporal,
  and top-level `process` (BPMN start/end/step/gateway/call/flow/boundary/lane).
- **MEASURE** — kind/subject/unit/scale/calculation/aggregation/period/threshold/
  target/tolerance, plus top-level `unit`.
- **LIFECYCLE** — state bodies (entry/exit/invariant), rich transitions
  (trigger/requires-work/guard/effect), governs-kind, invariants, temporal.
- **RESOURCE** — kind/capacity(+unit)/availability/location/owner/allocation- and
  reservation-policy/consumption/replenishment/cost, plus top-level `allocation`.
- **INTENT/TEMPORAL/SPATIAL/LOGIC/MATH** — the quantitative cluster: goals with
  tradeoffs; temporal fields + `calendar`; spatial fields + geometry + `route`;
  `proposition`/`predicate`; and `formula`/`function`/`optimize`/`distribution`/
  `simulation` with real math-expression ASTs.
- **Operational + emitter PROFILES** — authored as top-level blocks
  `integration { … }`, `security { … }`, `lineage { … }`, `architecture { … }`,
  `experience { … }`, `design { … }`, `analytics { … }`, `ai { … }`, each
  projecting into `ir[<section>]`.

AUTHORING v1.1 added the organizational-knowledge surface documented in
`ORGANIZATIONAL_KNOWLEDGE.md`. AUTHORING v1.2 adds enforceable business-pattern
claims. If a
selected profile requires semantics that cannot yet be expressed textually,
record the compiler gap explicitly and stop the generation gate; do not inject
unmapped fields into generated IR. Extend AUTHORING and its normalizer through a
reviewed grammar-stack change when that meaning must become first-class.

Authoring conveniences are syntax only. They must desugar into the canonical IR
without creating a second semantic identity or changing the meaning of KCF core
constructs.
