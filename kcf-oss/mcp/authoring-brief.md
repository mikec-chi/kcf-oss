# KCF authoring brief — write a `.kcf` model

A compact reference for drafting a first-pass model. The `.kcf` text compiles to
the semantic IR; use the `compile`/`assess` tools to check it and iterate. You do
**not** need a perfect model — reach a *valid* one, then enrich.

## Skeleton

```kcf
kcf model <Name> profile <preset> {
  namespace <ns>;

  entity <Entity> {
    identity <field>: <Type>;        // primary/natural key (required)
    required <field>: <Type>;
    optional <field>: <Type>;
    // mutability "read-only";        // mark reference/immutable entities (exempts CRUD)
  }

  actor  <Actor> { }                 // a principal / role
  event  <Event> immutable;          // an immutable fact
  work   <Work> { }                  // a process/activity

  relationship <name>: <ROOTKIND> <Source> -> <Target> strength 1.0;

  lifecycle <Name> for <Entity> {
    initial <State>;
    state <State>;
    terminal <State>;
    transition <State> -> <State>;   // [ using <ActionRef> ]
  }

  command <Name> {                   // also: query <Name> { } / transform <Name> { }
    operation <op>;                  // create|read|update|patch|delete|upsert|exists|count|bulk-update|...
    scope <scope>;                   // record | set | batch | stream
    target <Entity>;
    selection <kind>;                // identity | predicate | keys | all
    input <card>;                    // zero | one | optional-one | many
    output <card>;
    mutate <field>;                  // fields a command may change (repeatable)
    idempotency conditional;         // required for commands
    atomicity atomic;                // atomic | per-record | best-effort
    concurrency optimistic;          // optional: optimistic | pessimistic | serialized
    authorization <ns>.<Policy>;     // required for command/transform effects
  }

  collection <Name> {                // a data-transformation (effect: transform)
    operation project;               // select|project|filter|map|group|aggregate|join|union|...
    inputSchema <Entity>;
    outputSchema <View>;
    // key <k>;  grain <g>;  predicate <cond>;  bounded true;
  }
}
```

## Vocabulary

- **profiles**: `business-application`, `operational-system`,
  `organizational-knowledge`, `event-driven-system`, `ai-application`,
  `analytics-platform`.
- **concept keywords**: `entity`, `actor`, `work`, `event`, `resource` (plus
  organizational-knowledge: `information`, `rule`, `policy`, `reasoning`,
  `organization`).
- **relationship rootKinds**: `CLASSIFICATION`, `COMPOSITION`, `ASSOCIATION`,
  `IDENTITY`, `PARTICIPATION`, `DEPENDENCY`, `TRANSFORMATION`, `CAUSATION`,
  `ORDERING`, `GOVERNANCE`.
- **action operations**: record CRUD `create/read/replace/update/patch/delete/
  upsert/exists/query/count`; set/bulk `bulk-create/bulk-update/bulk-patch/
  bulk-delete/bulk-upsert/synchronize`; other `invoke/emit/allocate/release`.

## What "good enough" means

- **Required** (must fix to be `ready`): every entity has an `identity`; every
  command/transform declares `authorization`; claimed patterns are modeled;
  concept traits resolve to declared roles.
- **Recommended** (enrichment — realize or let the generator fill): full CRUD, a
  set/bulk op, a lifecycle, and a data-transformation per entity.
- Generation needs only a **valid** model (no analyzer errors). Run `assess` to
  see the split, then fix required gaps first.

## Synthetic gap-fills (provenance)

When you propose knowledge to fill a *recommended* gap from general domain
knowledge (rather than something the user stated), tag it so it stays
distinguishable from fact — never assert it bare. Provenance uses the grammar's
own `knowledge-metadata` on knowledge constructs (`information`, `rule`, `policy`,
`reasoning`, `assertion`):

```kcf
assertion PaymentImpliesInvoice {
  subject Payment; predicate "settles"; object-ref Invoice;
  status inferred;                 // inferred → flips to asserted on approval
  extraction-method llm;           // marks it synthetic (the review queue keys on this)
  extraction-model "claude-opus-4-8";
  confidence 0.9;                  // 0..1 — ≥0.8 is offered for bulk approval
  evidence NONE;                   // cite reasoning, or leave explicitly empty
}
```

Then: `compile` → `review_queue` (tiers fills into a **bulk** chunk for one-click
mass approval and a **review** chunk for individual decisions) →
`confirm_synthetic` (stamps `reviewed-by`/`recorded-at`, flips `inferred`→
`asserted`, or drops rejects). Do not set `reviewed-by`/`recorded-at` yourself —
approval sets them. Structural gaps (CRUD/lifecycle/set-op) are usually just added
as plain `command`/`lifecycle` constructs and need no provenance tag.

## Tips

- One concept has one primary kind; connect cross-dimensional meaning with
  `relationship`s, not by making a concept two things.
- Events are immutable — corrections are new events, not edits.
- Reference data synced from elsewhere → `mutability "read-only";` (exempts it
  from the CRUD/set recommendations).
- Don't invent fields/statuses the domain didn't state; ask the user if unsure.
