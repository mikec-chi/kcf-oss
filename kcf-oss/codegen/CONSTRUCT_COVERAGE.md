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

## Core structural constructs

| IR construct | Backend | Frontend |
|---|---|---|
| `concept` **ENTITY** + `attribute` (identity/required/optional/type/default) | ✅ table/model + CRUD; `identity`→PK, `required`→NOT NULL, `default`→column default | ✅ list + detail + form; `type`→input widget, `required`→validation, `identity`→read-only key |
| `concept` **ACTOR** | ✅ auth principal / role subject (maps to org roles + policies) | ✅ current-user context; role-gated components |
| `concept` **EVENT** | ✅ append-only event table / domain event / outbox (immutable) | ✅ activity feed / timeline / notifications (read-only) |
| `concept` **INFORMATION** (`informationKind`, confidentiality, freshness, completeness) | ✅ document/record/message store; `confidentiality`→access control; freshness/completeness columns | ✅ document viewer/editor; confidentiality badge; freshness indicator |
| `concept` **RESOURCE** + `allocations` | ✅ resource entities + allocation records | ✅ resource browser / allocation UI |
| `concept` **ORGANIZATIONAL** + `organizations` (unit/team/position, reporting, authorityDomains) | ✅ org tables + reporting edges → **RBAC scoping** | ✅ org switcher, member/role management, scope selector |
| `relationship` (`rootKind`: composition/association/participation/governance/transformation/identity/dependency/causation/ordering/classification) | ✅ FK / join table; composition→cascade, governance→authz link, participation→membership | ✅ navigation, nested/related lists, selectors (association→picker) |
| `lifecycle` + `transition` | ✅ status column + transition guard (reject undeclared transitions) | ✅ state badge + controls that offer **only the transitions legal from the current state** |

## Behavioral constructs

| IR construct | Backend | Frontend |
|---|---|---|
| `action` **record CRUD** (`scope: record`; `operation`: create/read/replace/update/patch/delete/upsert/exists/query/count) | ✅ one endpoint+handler per operation (create→POST, read/exists/count→GET, replace→PUT, patch/update→PATCH, delete→DELETE, upsert→idempotent PUT), enforcing the **full** contract (idempotency/atomicity/concurrency/authorization/retry/mutations) | ↔ create form / detail+list / edit form (mutate-set only) / delete control — each calls the matching operation; passes the concurrency token; UX-gates on authorization |
| `action` **set / bulk** (`scope: set|batch|stream`; `bulk-*`, `synchronize`; `selection: keys/predicate/partition`) | ✅ batch endpoint honoring `atomicity` (atomic vs per-record) and the selection | ↔ multi-select bulk action calling it |
| `action` **transform** + `collectionTransforms` (select/project/filter/map/group/aggregate/join/union/intersect/window/…) | ✅ query/aggregate endpoint (or SQL view/query) computing exactly that operation; honors `deterministic`/`bounded` | ✅ filtered/grouped/summary views + KPI tiles bound to it |
| `processes` / `plans` (WORK) | ➰ workflow/orchestration; long-running → **task queue** (Celery / BullMQ / Django-Q) | ✅ task list, workflow-step UI, status views |
| `rule` (`ruleKind` CONSTRAINT/PERMISSION/PROHIBITION/OBLIGATION/DERIVATION/DECISION/…, `mode`, `priority`, `conflict`) | ✅ CONSTRAINT→validator, PERMISSION/PROHIBITION→authz, OBLIGATION→required step, DERIVATION→computed field, DECISION→policy eval | ↔ mirror CONSTRAINT for instant feedback; gate UI on PERMISSION/PROHIBITION (server is source of truth) |
| `policies` (authority, rules, `defaultConflict`) | ✅ authorization policy engine with conflict resolution | ↔ consume decisions; render allowed/denied affordances |

## Knowledge & analytical constructs

| IR construct | Backend | Frontend |
|---|---|---|
| `reasoning`, `assertions`, `identityResolutions`, `knowledgeQueries` | ✅ inference/derivation services + query endpoints (org-knowledge) | ✅ insight panels, query builders, resolved-identity views |
| `analytics` extension | ➰ reporting endpoints / materialized views | ✅ dashboards, charts, KPI tiles (needs a charting lib) |
| `concept` **MEASURE** | ✅ computed metric values + instrumentation | ✅ KPI tiles / sparklines |
| `concept` **INTENT** | ➰ goals/outcomes as targets for processes/metadata | ✅ goal & progress displays |
| `concept` **REASONING** / `ai` extension | ➰ inference endpoints / model-serving hooks | ✅ recommendation & explanation panels |
| `concept` **LOGIC** / **MATH** | ✅ expression validators / computed values | ↔ show derived values; mirror simple checks |
| `concept` **TEMPORAL** (validFrom/validTo, bitemporal) | ✅ validity columns + as-of queries + scheduling | ✅ date pickers, as-of view, validity display |
| `concept` **SPATIAL** | ➰ geo types — needs **PostGIS** + geo binding (GeoAlchemy2 / GeoDjango / prisma geometry) | ✅ maps (needs a map lib) |

## Cross-cutting extension objects

| IR construct | Backend | Frontend |
|---|---|---|
| `integration` | ✅ external clients/adapters + inbound contract | ↔ calls backend, which owns integrations |
| `security` | ✅ authn/authz config, controls, secrets policy | ↔ enforce login; render permitted actions only |
| `lineage` | ✅ provenance/audit columns, data-lineage records | ✅ provenance/history views |
| `architecture` | ✅ deployment/module structure (informational) | ⬚ n/a |
| `experience` | ⬚ **out-of-tier** (frontend owns UX) | ✅ **primary driver**: screens, flows, navigation |
| `design` | ⬚ **out-of-tier** | ✅ theming / design tokens / component styling |
| `emitters`, `runtimeRequirements`, `runtimeBindings` | ✅ runtime wiring / deployment metadata | ⬚ n/a |
| pattern arrays, `modules`, `profiles`, `moduleVersions` | ✅ inform which constructs must exist (proof context) | ✅ same (informs which views/flows must exist) |

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
