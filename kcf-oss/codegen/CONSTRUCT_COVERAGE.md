# IR construct coverage — what each tier generates

This is the audit that keeps code generation honest: **every** construct in
`model-ir-v1` is accounted for, mapped either to a representation in the target
tier or explicitly declared *out-of-tier* (it belongs to the other tier) — never
silently dropped. It is the reference the system prompt and the coverage
self-audit are checked against.

The reference `business-application` model exercises the mainstream constructs end
to end — entity + attributes, actor, work, event, relationships, lifecycle, the
full action set (create / read / update / delete / **upsert** / **bulk-update**), a
**data-transformation** (`ActiveCustomers` filter), a **rule** (CONSTRAINT
validator), and a **policy** (deny-overrides engine) — so each stack's single-shot
example *demonstrates* every one of them with concrete code and an exhaustive
self-audit. The longer tail (SPATIAL, TEMPORAL, MEASURE, the knowledge dimension,
organization) is mapped below and pulled in **only when a model uses it**.

Two tiers:

- **backend** — persistence, the action contract, rules/policies, events,
  organization/authority, and an **OpenAPI/Swagger interface by default** (the
  contract the frontend connects to).
- **frontend** — screens, forms, lists, lifecycle controls, dashboards, and
  role-gated UI, generated **against the backend's OpenAPI** and calling it for
  everything the server owns.

Legend: ✅ owns · ➰ partial/optional (needs the noted add-on) · ↔ delegates to the
other tier (calls the API / enforced server-side) · ⬚ out-of-tier.

> **These dimensions are now first-class in the authoring surface** (grammar-stack
> 1.11.0): events carry `eventKind`/`trigger`/`affectsLifecycle`/`severity`/
> `correlationKeys`/occurrence-detection time/`matchCondition`; measures carry
> `unit`/`aggregation`/`scale`/`threshold`/`target`; temporal/spatial/intent/logic/
> math carry their fields; and the cross-cutting sections (`integration`, `security`,
> `lineage`, `architecture`, `experience`, `design`, `analytics`, `ai`) are authored
> as top-level blocks that land in `ir[<section>]`. **Realize whatever the IR
> declares** — when these fields are present they are declared meaning, not inferred,
> so treat them as `realized`, never `enriched`.

## Core structural constructs

| IR construct | Backend | Frontend |
|---|---|---|
| `concept` **ENTITY** + `attribute` (identity/required/optional/type/default) | ✅ table/model + CRUD; `identity`→PK, `required`→NOT NULL, `default`→column default | ✅ list + detail + form; `type`→input widget, `required`→validation, `identity`→read-only key |
| `concept` **ACTOR** | ✅ auth principal / role subject (maps to org roles + policies) | ✅ current-user context; role-gated components |
| `concept` **EVENT** (`eventKind`, `trigger`, `affectsLifecycle`, `severity`, `expectedness`, `correlationKeys`, occurrence/detection time, `matchCondition`) | ✅ append-only event table / domain event / outbox (immutable); `eventKind`→event type; **`affectsLifecycle`→emitting the event drives the named lifecycle transition** (through the lifecycle guard, not an ad-hoc status write); `trigger`→source binding; `correlationKeys`→correlation columns + index; `severity`/`expectedness`→columns + alerting; `matchCondition`→the detection predicate | ✅ activity feed / timeline / notifications; severity badges; correlation grouping |
| `concept` **INFORMATION** (`informationKind`, confidentiality, freshness, completeness) | ✅ document/record/message store; `confidentiality`→access control; freshness/completeness columns | ✅ document viewer/editor; confidentiality badge; freshness indicator |
| `concept` **RESOURCE** + `allocations` | ✅ resource entities + allocation records | ✅ resource browser / allocation UI |
| `concept` **ORGANIZATIONAL** + `organizations` (unit/team/position, reporting, authorityDomains) | ✅ org tables + reporting edges → **RBAC scoping** | ✅ org switcher, member/role management, scope selector |
| `relationship` (`rootKind`: composition/association/participation/governance/transformation/identity/dependency/causation/ordering/classification) + qualifiers (`cardinality`/`source-role`/`target-role`/`on-delete`) | ✅ FK / join table; composition→cascade, governance→authz link, participation→membership; **`on-delete`** (cascade/restrict/detach/archive/set-null/no-action) → the FK delete rule | ✅ navigation driven by **`cardinality`**: one-to-many→a related-list **grid/tab** (labeled by **`target-role`**), one-to-one→an inline **panel**; association→picker |
| `lifecycle` + `transition` | ✅ status column + transition guard (reject undeclared transitions) | ✅ state badge + controls that offer **only the transitions legal from the current state** |

### Entity metadata — `mutability` and `category`

Two advisory metadata tags on an entity steer generation (neither is a primitive;
both live in `concept.metadata`):

- `mutability "read-only"` → reference/immutable entity: skip write endpoints and
  CRUD forms; render read-only views. Exempt from CRUD/set coverage.
- `category master|transactional|reference|config` → the data-management role, a
  UI/topology driver: **master** → reference pickers across the app + a stewardship/
  admin CRUD surface; **transactional** → high-volume paginated lists + workflow/
  lifecycle UI; **config** → a settings screen; **reference** → static lookups
  (usually also read-only). It is advisory provenance the analyzer reconciles against
  the entity's shape (a `master` tag on a TRANSFORMATION target that emits events is
  flagged) — so treat it as guidance, and if it is absent, infer the grouping from the
  shape rather than inventing a tag. A frontend may group navigation by `category`
  (Master data / Transactions / Configuration) instead of a flat entity list.

### Rich example — an event that drives a lifecycle

When the model declares the rich fields, realize them literally. For example this IR:

```json
{ "id": "OrderBreached", "qualifiedName": "shop.OrderBreached", "mutable": false,
  "eventKind": "THRESHOLD", "affectsLifecycle": ["shop.OrderLife"],
  "correlationKeys": ["orderId"], "severity": "high",
  "matchCondition": "order.total > order.creditLimit" }
```

Backend realization (illustrative): an append-only `order_breached` outbox/event row
(`orderId` + a `severity` column, indexed on the correlation key); a detector that
raises the event when `matchCondition` holds; and — because `affectsLifecycle` names
`OrderLife` — **emitting the event drives that lifecycle's transition through its
guard** (reject if the transition isn't legal from the current state), rather than
writing the status field directly. `severity` feeds alerting. Frontend: the event
shows in the activity feed with a severity badge, grouped by `orderId`.

This is the pattern for every now-authorable field: the IR value is declared meaning
→ realize it (`realized`), don't treat it as an optional enrichment.

## Behavioral constructs

| IR construct | Backend | Frontend |
|---|---|---|
| `action` **record CRUD** (`scope: record`; `operation`: create/read/replace/update/patch/delete/upsert/exists/query/count) | ✅ one endpoint+handler per operation (create→POST, read/exists/count→GET, replace→PUT, patch/update→PATCH, delete→DELETE, upsert→idempotent PUT), enforcing the **full** contract (idempotency/atomicity/concurrency/authorization/retry/mutations) | ↔ create form / detail+list / edit form (mutate-set only) / delete control — each calls the matching operation; passes the concurrency token; UX-gates on authorization |
| `action` **set / bulk** (`scope: set|batch|stream`; `bulk-*`, `synchronize`; `selection: keys/predicate/partition`) | ✅ batch endpoint honoring `atomicity` (atomic vs per-record) and the selection | ↔ multi-select bulk action calling it |
| `action` **transform** + `collectionTransforms` (select/project/filter/map/group/aggregate/join/union/intersect/window/…) | ✅ query/aggregate endpoint (or SQL view/query) computing exactly that operation; honors `deterministic`/`bounded` | ✅ filtered/grouped/summary views + KPI tiles bound to it |
| `processes` / `plans` (WORK) | ➰ workflow/orchestration; long-running → **task queue** (Celery / BullMQ / Django-Q) | ✅ task list, workflow-step UI, status views |
| `rule` (`ruleKind` CONSTRAINT/PERMISSION/PROHIBITION/OBLIGATION/DERIVATION/DECISION/…, `mode`, `priority`, `conflict`) | ✅ CONSTRAINT→validator, PERMISSION/PROHIBITION→authz, OBLIGATION→required step, DERIVATION→computed field, DECISION→policy eval | ↔ mirror CONSTRAINT for instant feedback; gate UI on PERMISSION/PROHIBITION (server is source of truth) |
| `policies` (authority, rules, `defaultConflict`) | ✅ authorization policy engine with conflict resolution | ↔ consume decisions; render allowed/denied affordances |

> **Authoring-surface note — `plans`.** `plans` is a first-class IR construct (the
> analyzer validates step-index uniqueness; merge/migrate carry it) but it is the one
> construct **not yet exposed in the ergonomic `.kcf` authoring surface** — WORK
> choreography is authored today via `process`, and a `plan` reaches the IR only via a
> direct-IR/merge path. Realize `plans` when present; don't expect it from an authored
> `.kcf`. (Native `plan` authoring is tracked in the comprehensive-grammar work.)

## Knowledge & analytical constructs

| IR construct | Backend | Frontend |
|---|---|---|
| `reasoning`, `assertions`, `identityResolutions`, `knowledgeQueries` | ✅ inference/derivation services + query endpoints (org-knowledge) | ✅ insight panels, query builders, resolved-identity views |
| `analytics` extension | ➰ reporting endpoints / materialized views | ✅ dashboards, charts, KPI tiles (needs a charting lib) |
| `concept` **MEASURE** (`unit`, `aggregation`, `scale`, `period`, `threshold`, `target`, `tolerance`) | ✅ computed metric: `aggregation`→GROUP BY/rollup query or materialized view over `period`; `unit`/`scale` on the value; `threshold`/`target`→status + alerting | ✅ KPI tiles / sparklines with the `unit` and target/threshold bands |
| `concept` **INTENT** | ➰ goals/outcomes as targets for processes/metadata | ✅ goal & progress displays |
| `concept` **REASONING** / `ai` extension | ➰ inference endpoints / model-serving hooks | ✅ recommendation & explanation panels |
| **LOGIC** (`proposition`/`predicate`) / **MATH** (`formula`/`function`/`optimize`/`distribution`/`simulation`) | ✅ `proposition`→invariant/validator, `predicate`→boolean helper, `formula`/`function`→pure computed value, `optimize`→solver call (objective + constraints), `distribution`→sampler, `simulation`→Monte-Carlo runner (`trials`/`seed`) | ↔ show derived values; mirror simple predicates for instant feedback (server authoritative) |
| `concept` **TEMPORAL** (validFrom/validTo, bitemporal) + `calendars` | ✅ validity columns + as-of queries + scheduling; a `calendar` (timezone/working-days/holidays) → a business-day/holiday table + date arithmetic that honors it | ✅ date pickers, as-of view, validity display; calendar-aware date math |
| `concept` **SPATIAL** + `routes` | ➰ geo types — needs **PostGIS** + geo binding (GeoAlchemy2 / GeoDjango / prisma geometry); a `route` (from/to/via/distance) → an edge/segment table or a routing call | ✅ maps + route/path overlays (needs a map lib) |
| `concept` **capability** / **skill** + standalone `authority` | ✅ capability/skill catalogue tables + an authority registry the policy engine resolves against (who *can* do what) | ✅ capability/skill pickers; authority-scoped affordances |

## Cross-cutting extension objects

| IR construct | Backend | Frontend |
|---|---|---|
| `integration` | ✅ external clients/adapters + inbound contract | ↔ calls backend, which owns integrations |
| `security` | ✅ authn/authz config, controls, secrets policy | ↔ enforce login; render permitted actions only |
| `lineage` | ✅ provenance/audit columns, data-lineage records | ✅ provenance/history views |
| `architecture` | ✅ deployment/module structure (informational) | ⬚ n/a |
| `experience` | ⬚ **out-of-tier** (frontend owns UX) | ✅ **primary driver**: screens, flows, navigation. **Nav = aggregate roots only**; pure parts (COMPOSITION targets with no children and no independent inbound ref) render as **subtabs** on their parent's detail (parent = the COMPOSITION source), not as their own nav entry — see COOKBOOK §F. |
| `design` | ⬚ **out-of-tier** | ✅ theming / design tokens / component styling. **No `design` block declared → apply `design-system-default.md`** (brand-neutral, accessible baseline); declared tokens override it. |
| `emitters`, `runtimeRequirements`, `runtimeBindings` | ✅ runtime wiring / deployment metadata | ⬚ n/a |
| pattern arrays, `modules`, `profiles`, `moduleVersions` | ✅ inform which constructs must exist (proof context) | ✅ same (informs which views/flows must exist) |

## Platform target — NetSuite (SuiteCloud SDF + SuiteScript 2.1)

A **platform** stack (`tier: platform`) realizes the model as customizations *inside*
a SaaS platform that already owns the datastore, runtime, and default UI — so there
is **no OpenAPI/Swagger** deliverable and no persistence layer to build. The pack
emits platform-native objects + scripts, packaged for the platform's deployment
framework. Mapping for `netsuite-suitecloud-sdf` (see its `EXAMPLE.md`):

| IR construct | NetSuite realization |
|---|---|
| `concept` **ENTITY** + `attribute` | `customrecordtype` (SDF XML) + one `customrecordcustomfield` per attribute. Types: String→FREEFORMTEXT (email→EMAIL), Text→TEXTAREA, Integer→INTEGER, Decimal→FLOAT (money→CURRENCY), Boolean→CHECKBOX, DateTime→DATETIMETZ, Date→DATE, UUID→FREEFORMTEXT, reference→SELECT (`selectrecordtype`=target record) |
| `attribute` **identity** | NetSuite's internal `id` is automatic; the business identity → its own mandatory field, uniqueness enforced in a User Event `beforeSubmit` (no native unique constraint) |
| `concept` **ACTOR** | a `role` object (and/or employee); also the coarse gate for the policy |
| `concept` **EVENT** (immutable) | an append-only event-log `customrecordtype` (role granted CREATE only) written from a User Event `afterSubmit` |
| `lifecycle` + `transition` | a `customlist` of states + a status SELECT field, realized twice-in-agreement: a `workflow` (SuiteFlow) object for UI transitions **and** a `beforeSubmit` guard rejecting undeclared transitions (guards RESTlet/CSV changes) |
| `action` **record CRUD / upsert** | a RESTlet (SuiteScript 2.1): read/query→`get`, create→`post`, update/replace/patch/upsert→`put`, delete→`delete`. Optimistic concurrency via a `version` field; a command writes only its `mutate` fields; conditional idempotency = no-op on no-change; save is atomic per record |
| `action` **set / bulk** | a RESTlet `put`/`post` that iterates honoring `atomicity` (best-effort → per-item try/catch + per-item result); large sets → a Map/Reduce script |
| `action` **transform** + `collectionTransforms` | a `savedsearch` object (or N/query) with the predicate/summary; loaded via `search.load` where a script needs the rows |
| `rule` (CONSTRAINT/…) | validation in a User Event `beforeSubmit` (server, authoritative); simple ones mirrored in a Client Script `saveRecord`/`fieldChanged` for instant feedback |
| `policies` | a `role` object's record permissions (coarse) **plus** an in-script deny-overrides `evaluatePolicy()` module called before mutating (fine) |
| `processes`/`plans` (WORK) | SuiteFlow workflow (short) or a Scheduled / Map-Reduce script (long-running) |
| MEASURE / analytics | a `savedsearch` with summary/formula columns → KPI / reminder / dashboard portlet |
| `experience` / `design` | delegated to NetSuite-native custom forms unless the model declares them |
| deployment | an SDF **ACCOUNTCUSTOMIZATION** project (`manifest.xml` / `deploy.xml`) + a `scriptdeployment` per script; `suitecloud project:deploy` |

Everything is packaged as an SDF project; nothing is silently dropped — the platform
example's coverage self-audit gives every construct a `realized`/`delegated`
disposition with `dropped: []`, the same discipline as the backend/frontend tiers.

## Completeness verdict

**Backend tech stacks are complete enough.** FastAPI+SQLModel, TypeScript+Express+Prisma,
and Django+DRF each cover all backend-owned constructs above, over PostgreSQL, and
expose an OpenAPI/Swagger interface by default. Two constructs need a standard,
per-stack add-on the generator pulls in **only when the IR uses them**:

- **SPATIAL** → PostGIS + a geo binding (GeoAlchemy2 / GeoDjango / a Prisma
  geometry type).
- **long-running WORK** (`processes`/`plans` that aren't synchronous) → a task
  queue (Celery / BullMQ / Django-Q).

`experience` and `design` are correctly **out-of-tier** for a backend and are
realized by the frontend.

**Frontend tech stack is complete enough.** React + TypeScript + TanStack Query +
a generated OpenAPI client covers every frontend-owned construct by consuming the
backend's OpenAPI contract; `MEASURE`/`analytics` need a charting library and
`SPATIAL` a map library, pulled in only when present. Everything the server owns
(persistence, the full action contract, policy authority) is **delegated to the
backend API**, never re-implemented client-side.

This table is the checklist for the **coverage self-audit** every generation must
produce: each construct present in the model must appear as *realized*,
*delegated*, *out-of-tier*, or *unsupported (with reason)* — with `dropped: []`.

> **Valid is the gate; coverage is guidance.** You generate from a *valid* model
> (analyzer-clean: identities present, references resolve, action contracts
> complete). You do **not** need a fully `ready` model. `kcf assess` reports
> coverage gaps by level — `required` (e.g. missing identity) matter; the rest
> (CRUD, set/bulk, lifecycle, transformation) are *recommended* enrichment. When
> the IR declares an operation, realize it from this table. When a recommended
> operation is absent, you may add the standard version (e.g. missing CRUD on a
> mutable entity) — but flag it in the coverage self-audit as *enriched* rather
> than declared, so it stays reviewable.
