# IR construct cookbook — a worked realization of every tail construct

The stack `EXAMPLE.md` files realize the **mainstream** model end to end. This
cookbook covers **everything else** — the quantitative, knowledge, and cross-cutting
dimensions grammar-stack 1.11.0 made authorable — so a codegen LLM has a concrete
target for each, not just a table row.

**How to read it.** Each entry gives the **IR shape** (real normalized field names)
and then the realization in each tier: **Backend** (the reference idiom is
FastAPI + SQLModel; the other backend stacks map the same way), **Frontend** (React +
the OpenAPI client), and **Platform** (NetSuite SDF). One canonical doc — not three —
so the three tiers can't drift apart. Pull an entry in **only when a real model uses
that construct**; realize what the IR declares (`realized`), don't invent.

Every construct here is exercised by a committed, analyzer-valid reference model
(named per section) — see `README.md` → *Reference models*.

---

## A. Rich core (variants of constructs the stack examples show only in part)

### A1 · Rich EVENT that drives a lifecycle — `quantitative`/`entity-rich` idiom
```jsonc
// concept EVENT + { eventKind, affectsLifecycle[], severity, correlationKeys[],
//                   matchCondition, expectedness, trigger }
{ "kind":"EVENT", "eventKind":"THRESHOLD", "affectsLifecycle":["shop.OrderLife"],
  "severity":"high", "correlationKeys":["orderId"], "matchCondition":"order.total > order.creditLimit" }
```
- **Backend** — append-only event table/outbox (immutable); a detector that raises the
  event when `matchCondition` holds; **`affectsLifecycle` ⇒ emitting the event drives
  that lifecycle's transition through its guard** (not an ad-hoc status write);
  `correlationKeys` → indexed columns; `severity`/`expectedness` → columns + alerting.
- **Frontend** — activity feed / timeline with a `severity` badge, grouped by the
  correlation key; no write path (events are server-emitted).
- **Platform (NetSuite)** — an append-only event-log `customrecordtype` (role: CREATE
  only) written in a User Event `afterSubmit`; `affectsLifecycle` → a Workflow Action
  that fires the guarded state transition; `severity` → a field + a saved-search alert.

### A2 · Rich LIFECYCLE — state `entry`/`exit`/`invariant`, transition `trigger`/`guard`/`effect`
```jsonc
{ "states":[{"name":"Active","entry":["onEnter"],"exit":["onExit"],"invariant":"balance >= 0"}],
  "transitions":[{"from":"Active","to":"Suspended","trigger":"SuspendWork","guard":"balance == 0","effect":"NotifyWork"}] }
```
- **Backend** — `entry`/`exit` → hooks run inside the transition tx; `invariant` →
  checked on every write while in that state; `guard` → boolean precondition on the
  transition (reject if false); `effect` → a side-effect (enqueue `NotifyWork`) run
  post-commit.
- **Frontend** — offer only transitions whose `guard` can currently pass; show the
  `invariant` as a live validation on the detail view.
- **Platform** — SuiteFlow states carry entry/exit **actions** and transition
  **conditions** (`guard`) + **actions** (`effect`) natively; mirror the guard in the
  `beforeSubmit` script so RESTlet/CSV changes are checked too.

### A3 · Entity-embedded `mutation` — `entity-rich`
```jsonc
{ "id":"SubmitOrder", "operation":"update", "scope":"record", "selection":"identity",
  "atomicity":"atomic", "concurrency":"optimistic", "versionField":"version", "idempotency":"conditional",
  "mutates":["status"], "changes":[{"target":"status","from":"Draft","to":"Submitted"}],
  "preconditions":["order has at least one line"], "postconditions":["order status is Submitted"],
  "emits":["shop.OrderSubmitted"] }
```
- **Backend** — a single-record method: check `preconditions`, enforce the
  `from`→`to` `change` (reject if current != `from`), write only `mutates`, bump
  `versionField` under optimistic concurrency, assert `postconditions`, then `emit`.
  A `mutation` is a stricter `update` action — realize it with the same contract rigor.
- **Frontend** — a single action button enabled only when `preconditions` + the `from`
  state hold; passes the concurrency token.
- **Platform** — a Workflow Action button (state `Draft`→`Submitted`) or a RESTlet
  `put`; the `beforeSubmit` guard enforces `from`/`guard`; `emits` → the event log.

### A4 · Full action-operation set (beyond CRUD/upsert/bulk-update)
`patch` → partial PATCH (only supplied fields); `replace` → PUT (full representation);
`exists`/`count` → HEAD/GET returning bool/number; `bulk-create/bulk-patch/bulk-delete/
bulk-upsert` → batch endpoints honoring `atomicity`; `synchronize` → a reconcile
endpoint (upsert-present + delete-absent against a supplied set); `emit` → publish a
declared event; `allocate`/`release` → reserve/free a RESOURCE (see C2). **Frontend**:
each maps to the matching control (bulk-select action, sync button). **Platform**: each
→ a RESTlet branch or a Map/Reduce for large sets.

### A5 · collectionTransform operations (beyond `filter`)
`project`/`map` → a SELECT shaping columns; `group`+`aggregate` → GROUP BY + rollup;
`join` → a joined view; `union`/`intersect` → set ops; `window` → windowed analytics.
Realize each as a query endpoint (or SQL view) honoring `deterministic`/`bounded`; it
appears in the OpenAPI. **Frontend**: grouped/summary tables + KPI tiles bound to it.
**Platform**: a `savedsearch` with the summary/formula, or an N/query.

### A6 · rule `kind` variants (beyond CONSTRAINT)
PERMISSION/PROHIBITION → authorization checks; OBLIGATION → a required step the
workflow must reach; DERIVATION → a computed/stored-generated field; DECISION → a
policy-engine evaluation; ELIGIBILITY → a gate predicate; CLASSIFICATION → a
categorizer; EXCEPTION → an override rule with higher `priority`. Honor `mode`,
`priority`, and `conflict`. **Frontend** mirrors PERMISSION/PROHIBITION for affordance
gating (server authoritative). **Platform**: `beforeSubmit`/workflow validations + role
permissions.

### A7 · relationship `rootKind` variants
composition → cascade FK/child table; association → nullable FK / join + picker;
participation → membership join; governance → an authz edge; transformation → a
provenance link (source→target); identity → a same-as/merge edge; dependency → an
ordering FK; causation → an event-link; ordering → a sequence column; classification →
a type/category FK. Realize the storage per kind; **Frontend** renders the matching
navigation (nested list, selector, breadcrumb).

---

## B. Quantitative & analytical dimensions — `quantitative`, `analytics-ai`

### B1 · MEASURE + `unit`
```jsonc
// concept MEASURE { conceptKind, subjects[], unit, scale, aggregation, target, tolerance }
// unit { dimension, symbol }
{ "kind":"MEASURE","conceptKind":"KPI","subjects":["shop.Sale"],"unit":"USD","scale":"ratio","aggregation":"sum","target":1000000,"tolerance":50000 }
```
- **Backend** — a computed metric: `aggregation`→a GROUP BY/rollup query or a
  materialized view over the subject; `unit`/`scale` travel on the value; `target`/
  `tolerance`/`threshold`→status bands + alerting. Expose a metric endpoint.
- **Frontend** — KPI tile / sparkline showing the `unit` and target/tolerance bands.
- **Platform** — a summary `savedsearch` (SUM/AVG) → a KPI/reminder or dashboard portlet.

### B2 · INTENT
```jsonc
{ "kind":"INTENT","conceptKind":"GOAL","desiredState":"revenue trends up","successes":["+10%"],
  "failures":["down 2 quarters"],"priority":1,"tradeoffs":[{"item":"Speed","against":"Quality","weight":0.6}],
  "timeHorizon":"shop.FiscalYear","stakeholders":["shop.Owner"],"measures":["shop.RevenueKPI"] }
```
- **Backend** — goals as target rows linked to their `measures` (progress = measure vs
  `desiredState`/`successes`); `tradeoffs` inform scoring, not enforcement.
- **Frontend** — goal & progress cards (measure value vs success/failure thresholds).
- **Platform** — a Goal custom record linked to the measure saved search.

### B3 · TEMPORAL + `calendar`
```jsonc
// TEMPORAL { conceptKind, startValue, endValue, durationValue{value,unit}, recurrence, timezone, calendarRef, calculation }
// calendar { workingDays[], holidays[], timezone }
```
- **Backend** — validity/interval columns + as-of queries; `recurrence` (RFC5545) → a
  schedule expander; `calendarRef` → date math that skips non-working days/holidays.
- **Frontend** — date pickers + an as-of view; calendar-aware duration display.
- **Platform** — validity fields + a Scheduled Script honoring a holiday custom list.

### B4 · SPATIAL + `route`
```jsonc
// SPATIAL { conceptKind, geometry, containedIn, adjacentTo, jurisdiction }
// route { from, to, via[], distance{value,unit}, constraints[] }
```
- **Backend** — geo types via **PostGIS** + a geo binding (GeoAlchemy2/GeoDjango);
  `route` → an edge/segment table or a routing-service call over `from`/`to`/`via`.
- **Frontend** — map with geometry + a route/path overlay (needs a map lib).
- **Platform** — geolocation fields; a route custom record (from/to/via/distance).

### B5 · LOGIC — `proposition` / `predicate`
```jsonc
// proposition { expression, mode }        predicate { parameters[{name,type}], expression }
```
- **Backend** — `proposition`→a model-wide invariant/assertion validator (`mode`
  necessary ⇒ must always hold); `predicate`→a reusable boolean helper `is_x(params)`.
- **Frontend** — mirror simple predicates for instant feedback (server authoritative).
- **Platform** — a library-module function; `proposition` → a saved-search-backed check.

### B6 · MATH — `formula`/`function`/`optimize`/`distribution`/`simulation`
```jsonc
// math[] with mathKind; expression is an AST {op,left,right,ref}
{ "mathKind":"formula","result":"shop.Margin","expression":{"op":"-","left":{"ref":"price"},"right":{"op":"*","left":{"ref":"cost"},"right":{"ref":"qty"}}} }
```
- **Backend** — `formula`/`function`→pure computed values (evaluate the AST; `function`
  has `parameters`+`returnType`); `optimize`→a solver call (objective+variables+
  constraints, e.g. PuLP/OR-Tools); `distribution`→a sampler (family/params);
  `simulation`→a Monte-Carlo runner (`trials`/`seed`, over the referenced model).
- **Frontend** — show derived values; render distribution/sim summaries as charts.
- **Platform** — computed fields / a Suitelet running the calc; heavy sims → Map/Reduce.

---

## C. Knowledge & organizational dimensions — `analytics-ai`, `capability-skill`

### C1 · INFORMATION
```jsonc
{ "informationKind":"RECORD","representation":"json","recordedAt":"…","subjects":[…],"sources":[…],"confidentiality":"…","freshness":"…" }
```
- **Backend** — a document/record/message store; `confidentiality`→access control;
  `freshness`/`completeness`→columns + staleness checks. **Frontend** — a document
  viewer with confidentiality badge + freshness indicator. **Platform** — a File Cabinet
  doc or a custom record with a restricted role.

### C2 · RESOURCE + `allocation`
```jsonc
// RESOURCE { conceptKind, capacity }   allocation { resource, consumer, quantity, reservation?, validity? }
```
- **Backend** — resource rows with `capacity`; allocation rows (`quantity` to a
  `consumer`); enforce **Σ allocations ≤ capacity** (the analyzer checks this at model
  time; enforce it at runtime too). `allocate`/`release` actions mutate it.
- **Frontend** — a capacity/allocation board; disable over-allocation.
- **Platform** — a resource record + allocation child records; a saved search for load.

### C3 · ORGANIZATION + standalone `authority`
```jsonc
// organization { organizationKind, members[], roles[], reporting[], authorityDomains[] }
// authority { subject, target, mode, when[] }
```
- **Backend** — org tables + reporting edges → **RBAC scoping**; an `authority` registry
  (`subject` may `mode` on `target` `when` …) the policy engine resolves against.
- **Frontend** — org switcher, member/role management, authority-scoped affordances.
- **Platform** — NetSuite roles/subsidiaries/departments; authority → role restrictions.

### C4 · REASONING + `assertion`
```jsonc
// reasoning { reasoningKind, proposition, method, confidence, premises[] }
// assertion { subject, predicate, objectRef|object, status, extractionMethod?, confidence? }
```
- **Backend** — inference/derivation services (HYPOTHESIS/INFERENCE/EXPLANATION);
  assertions as a fact table with **provenance** (`status` asserted/inferred/disputed,
  `confidence`) — inferred rows stay flagged until approved (see the synthetic-gap flow).
- **Frontend** — insight/explanation panels; a review queue for inferred assertions.
- **Platform** — a knowledge custom record with a status field + approval workflow.

### C5 · `identity-resolution` / `knowledge-query`
```jsonc
// identity-resolution { canonical, aliases[], sameAs[], status }
// knowledge-query { select, where, world(open|closed), negation, inference, temporal, asOf? }
```
- **Backend** — identity-resolution → a merge/same-as service producing a canonical id
  (dedup); knowledge-query → a query endpoint honoring `world` (open/closed-world),
  `negation`, `inference`, and `temporal` (`current`/`as-of`) policy.
- **Frontend** — merged-identity views; a query builder exposing the policy knobs.
- **Platform** — dedup via a scheduled Map/Reduce; queries via saved searches.

### C6 · `capability` / `skill`
```jsonc
// capability { requiresSkill[], implementedBy }   skill { level }
```
- **Backend** — capability/skill catalogue tables; `requiresSkill` gates who/what may
  perform the `implementedBy` action (capability-based authorization). **Frontend** —
  capability/skill pickers + gating. **Platform** — competency records + role mapping.

---

## D. Cross-cutting PROFILE blocks — `profiles` (each lands in `ir[section]`)

These are authored as top-level blocks and projected into `ir.<section>`. Realize the
ones present; note the others out-of-tier — never drop.

| Section | IR shape (keys) | Backend | Frontend | Platform |
|---|---|---|---|---|
| `integration` | `adapters/endpoints/routes/retryPolicies/eventBridges/mappings/errorPolicies` | external clients/adapters + inbound contracts; retry/idempotency per `retryPolicies` | ↔ calls backend | RESTlet/SuiteTalk + a Scheduled integration |
| `security` | `assets/threats/risks/controls/treatments/trustBoundaries` | authn/authz config, controls, secrets policy, boundary enforcement | ↔ login + permitted actions only | roles/permissions + restrictions |
| `lineage` | `lineages/bindings/costs/fieldLineage` | provenance/audit columns + data-lineage records | provenance/history views | System Notes + a lineage record |
| `architecture` | `services/interfaces/boundaries/topology/deployments` | deployment/module structure (informational) | ⬚ n/a | SDF project structure / bundles |
| `analytics` | `datasets/semanticLayers/reports/dashboards` | reporting endpoints / materialized views | dashboards, charts, KPI tiles | saved searches + dashboards |
| `ai` | `featureSets/datasets/models/pipelines/servings/governance` | model-serving hooks + feature store | recommendation/explanation panels | SuiteScript ML hooks / external call |
| `experience` | `apps/views/components/flows/bindings` | ⬚ out-of-tier | **primary**: screens/flows/nav | native custom forms |
| `design` | `designSystems/pages` | ⬚ out-of-tier | theming / design tokens | form/portlet styling |

---

## Coverage self-audit for cookbook realizations

When you realize a tail construct from this cookbook, still emit the per-generation
**coverage self-audit** (same as the stack examples): every construct present in the
model → `realized` / `delegated` / `out-of-tier` / `unsupported (reason)`, with
`dropped: []`. The one construct with no authoring path — **`plans`** — realize it if a
merged/direct IR provides it, but don't expect it from an authored `.kcf` (see
`CONSTRUCT_COVERAGE.md` → *Authoring-surface note*).
