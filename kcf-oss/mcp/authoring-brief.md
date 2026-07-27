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

## Beyond the basics (grammar-stack 1.11.0)

All 16 dimensions + the ACTION/RELATIONSHIP algebra are first-class in `.kcf`; the
full syntax is in [AUTHORING.md](../docs/AUTHORING.md). Reach for these when the
domain calls for them — when you declare them they're **realized**, not guessed:

```kcf
  // Rich event — classify it and let it drive a lifecycle:
  event OrderBreached {
    kind THRESHOLD;                  // OCCURRENCE|SIGNAL|OBSERVATION|EXCEPTION|THRESHOLD|SCHEDULED|EXTERNAL|DERIVED|CORRECTION|NORMAL
    trigger <ConceptRef>;
    affect-lifecycle <LifecycleRef>; // emitting the event drives that lifecycle's transition
    severity high; expectedness unexpected;
    correlation-key <field>;
    match "<condition>";
  }

  // Quantitative cluster:
  measure Revenue { kind FINANCIAL; unit USD; aggregation sum; scale ratio; }  // + period/threshold/target/tolerance
  temporal FiscalPeriod { ... }   calendar BusinessCalendar { ... }
  spatial Region { geometry POLYGON [ 0 0, 1 0, 1 1 ]; }   route SupplyRoute { ... }
  intent MaximizeMargin { ... }                       // goals + tradeoffs
  proposition AllPriced { expression "..."; }   predicate IsLate (x: UUID) { ... }        // LOGIC
  formula Margin { ... }   function UnitMargin (cost: Decimal, price: Decimal) -> Decimal { ... }  // MATH
  //   also: optimize / distribution / simulation

  // Cross-cutting PROFILE blocks — top-level; each lands in ir[<section>]:
  integration { ... }  security { ... }  lineage { ... }
  architecture { ... }  experience { ... }  design { ... }  analytics { ... }  ai { ... }
```

Richer core, too: lifecycle states take `entry`/`exit`/`invariant` and transitions
carry `trigger`/`guard`/`effect`; actors carry `role`/`authority`; work carries a
`process` (BPMN start/step/gateway/flow).

## Vocabulary

- **profiles**: `business-application`, `operational-system`,
  `organizational-knowledge`, `event-driven-system`, `ai-application`,
  `analytics-platform`.
- **concept keywords**: `entity`, `actor`, `work`, `event`, `resource`, `intent`,
  `measure`, `temporal`, `spatial`, `logic`, `math`; knowledge: `information`,
  `rule`, `policy`, `reasoning`, `organization`, `assertion`. Top-level dimension
  declarations: `lifecycle`, `relationship`, `command`/`query`/`transform`,
  `collection`, `calendar`, `route`, `proposition`/`predicate`,
  `formula`/`function`/`optimize`/`distribution`/`simulation`, `allocation`, `unit`,
  `authority`, `process`; and the profile blocks (`integration`/`security`/`lineage`/
  `architecture`/`experience`/`design`/`analytics`/`ai`).
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
- **Data-management nature** (optional, advisory): tag an entity's role with
  `category master | transactional | reference | config;` — a metadata line (same
  mechanism as `mutability`, lands in `metadata.category`). It is **advisory
  provenance, not a primitive**: KCF's real classification is the *shape*
  (lifecycle/event/transformation/mutability), and the analyzer **reconciles** your
  tag against that shape — flagging, e.g., an entity marked `master` that is a
  TRANSFORMATION target and emits events (likely `transactional`). Don't add a
  lifecycle or CRUD to an entity just to close a coverage gap — it distorts this
  shape signal. Generators use `category` for UI (master → reference pickers +
  stewardship/admin; transactional → high-volume list + workflow; config →
  settings; reference → static).
- Don't invent fields/statuses the domain didn't state; ask the user if unsure.
