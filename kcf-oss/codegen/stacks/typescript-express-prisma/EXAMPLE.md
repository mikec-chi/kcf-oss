# Single-shot example — TypeScript + Express + Prisma + PostgreSQL

This realizes the reference `business-application` model in this stack. Imitate
its layering and idioms; substitute the target model's concepts, attributes,
lifecycle, and action contract.

## Input (excerpt of the KCF IR)

```jsonc
// concept customer.Customer: identity customerId:UUID, required name:String, optional email:String
// actor customer.ServiceAgent (auth principal / role)
// work  customer.UpdateCustomerWork; event customer.CustomerUpdated (immutable)
// relationship agent-performs-update:  PARTICIPATION   ServiceAgent -> UpdateCustomerWork
// relationship update-changes-customer: TRANSFORMATION UpdateCustomerWork -> Customer
// lifecycle CustomerLifecycle: Active->Suspended, Suspended->Active, Active->Archived (terminal Archived)
// action customer.UpdateCustomer: update/record, selection=identity, mutate=[name],
//   idempotency=conditional, atomicity=atomic, concurrency=optimistic,
//   authorization=customer.CustomerUpdatePolicy
// action customer.CreateCustomer: create/record, atomicity=atomic
// action customer.GetCustomer:    read/record,  selection=identity
// action customer.DeleteCustomer: delete/record, selection=identity, idempotency=conditional
// action customer.UpsertCustomer: upsert/record, selection=identity, idempotency=conditional, atomicity=atomic
// action customer.BulkUpdateCustomers: bulk-update/set, selection=predicate, input=many, output=many,
//   atomicity=best-effort, concurrency=optimistic
// collectionTransform customer.ActiveCustomers: filter, in=Customer out=Customer,
//   predicate="customer status is Active", bounded=true
// rule customer.CustomerUpdateConstraint: kind=CONSTRAINT, "email is present when a customer is Active",
//   applies-to=Customer, authority=ServiceAgent
// policy customer.CustomerUpdatePolicy: authority=ServiceAgent, rule=CustomerUpdateConstraint,
//   default-conflict=deny-overrides
```

## Output

### `prisma/schema.prisma`
```prisma
enum CustomerState {
  Active
  Suspended
  Archived
}

model Customer {
  customerId String        @id @default(uuid())   // IR identity attribute
  name       String                               // required
  email      String?                              // optional
  state      CustomerState @default(Active)
  version    Int           @default(1)            // optimistic-concurrency token
}

// Transactional outbox for the immutable event customer.CustomerUpdated.
// Rows are append-only — never updated or deleted (event immutable).
model OutboxEvent {
  id        String   @id @default(uuid())
  type      String                               // e.g. "customer.CustomerUpdated"
  payload   Json
  createdAt DateTime @default(now())
}
```

### `src/dto.ts`
```typescript
import { z } from "zod";

// selection=identity; only `name` is in the action's mutate set.
export const UpdateCustomerRequest = z.object({
  customerId: z.string().uuid(),
  name: z.string().min(1),
  expectedVersion: z.number().int(),
});
export type UpdateCustomerRequest = z.infer<typeof UpdateCustomerRequest>;

export interface CustomerResponse {
  customerId: string; name: string; email: string | null;
  state: string; version: number;
}
```

### `src/lifecycle.ts`
```typescript
import { CustomerState } from "@prisma/client";

// From CustomerLifecycle — only declared transitions are legal.
const CUSTOMER_TRANSITIONS = new Set([
  `${CustomerState.Active}->${CustomerState.Suspended}`,
  `${CustomerState.Suspended}->${CustomerState.Active}`,
  `${CustomerState.Active}->${CustomerState.Archived}`,
]);

export function assertTransition(from: CustomerState, to: CustomerState): void {
  if (from !== to && !CUSTOMER_TRANSITIONS.has(`${from}->${to}`)) {
    throw new HttpError(422, `illegal transition ${from} -> ${to}`);
  }
}

export class HttpError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
```

### `src/service.ts`
```typescript
import { PrismaClient } from "@prisma/client";
import { UpdateCustomerRequest, CustomerResponse } from "./dto";
import { assertCustomerConstraint } from "./constraints";
import { emitCustomerUpdated } from "./events";
import { HttpError } from "./lifecycle";

const prisma = new PrismaClient();

// Realizes customer.UpdateCustomer.
// scope=record, selection=identity, mutate={name},
// idempotency=conditional, atomicity=atomic, concurrency=optimistic.
export async function updateCustomer(cmd: UpdateCustomerRequest): Promise<CustomerResponse> {
  return prisma.$transaction(async (tx) => {          // atomicity=atomic
    const current = await tx.customer.findUnique({ where: { customerId: cmd.customerId } });
    if (!current) throw new HttpError(404, "customer not found");

    // idempotency=conditional: no-op request neither errors nor bumps version.
    if (current.name === cmd.name) return toResponse(current);

    // concurrency=optimistic: guarded update; count 0 => stale version.
    const result = await tx.customer.updateMany({
      where: { customerId: cmd.customerId, version: cmd.expectedVersion },
      data: { name: cmd.name, version: { increment: 1 } },   // only mutate-listed field
    });
    if (result.count === 0) throw new HttpError(409, "version conflict");

    const updated = await tx.customer.findUniqueOrThrow({ where: { customerId: cmd.customerId } });
    assertCustomerConstraint(updated);                  // rule CustomerUpdateConstraint
    await emitCustomerUpdated(tx, updated);             // event customer.CustomerUpdated (in-tx outbox)
    return toResponse(updated);
  });
}

function toResponse(c: any): CustomerResponse {
  return { customerId: c.customerId, name: c.name, email: c.email, state: c.state, version: c.version };
}
```

### `src/routes.ts`
```typescript
import { Router } from "express";
import { UpdateCustomerRequest } from "./dto";
import { requirePolicy } from "./policy";
import { updateCustomer } from "./service";
import { HttpError } from "./lifecycle";

export const router = Router();

// authorization = customer.CustomerUpdatePolicy, enforced before the handler.
router.post("/actions/UpdateCustomer",
  requirePolicy("customer.CustomerUpdatePolicy"),
  async (req, res) => {
    try {
      const cmd = UpdateCustomerRequest.parse(req.body);
      res.json(await updateCustomer(cmd));
    } catch (e) {
      if (e instanceof HttpError) return res.status(e.status).json({ error: e.message });
      throw e;
    }
  });
```

### `test/updateCustomer.test.ts`
```typescript
import { describe, it, expect } from "vitest";
import { assertTransition, HttpError } from "../src/lifecycle";
import { CustomerState } from "@prisma/client";

describe("UpdateCustomer", () => {
  it("rejects an undeclared lifecycle transition", () => {
    expect(() => assertTransition(CustomerState.Archived, CustomerState.Active))
      .toThrowError(HttpError);            // Archived is terminal; transition not declared
  });
  // Integration tests (happy path, stale-version 409) run updateCustomer against a
  // test database seeded with a Customer at a known version.
});
```

### `src/openapi.ts` + `src/app.ts` (Swagger by default)
```typescript
// src/openapi.ts — build one OpenAPI 3 document from the zod schemas.
import { OpenAPIRegistry, OpenApiGeneratorV3 } from "@asteasolutions/zod-to-openapi";
import { UpdateCustomerRequest } from "./dto";

export const registry = new OpenAPIRegistry();
registry.registerPath({
  method: "post", path: "/actions/UpdateCustomer",
  request: { body: { content: { "application/json": { schema: UpdateCustomerRequest } } } },
  responses: { 200: { description: "updated customer" }, 409: { description: "version conflict" } },
});
export const openApiDocument = new OpenApiGeneratorV3(registry.definitions)
  .generateDocument({ openapi: "3.0.0", info: { title: "CustomerService", version: "1.0.0" } });
```
```typescript
// src/app.ts — serve the API + Swagger UI at /docs (the frontend's contract).
import express from "express";
import swaggerUi from "swagger-ui-express";
import { router } from "./routes";
import { openApiDocument } from "./openapi";

export const app = express();
app.use(express.json());
app.use(router);
app.get("/openapi.json", (_req, res) => res.json(openApiDocument));
app.use("/docs", swaggerUi.serve, swaggerUi.setup(openApiDocument));
```

### `src/dto.ts` (additional command DTOs)
```typescript
import { z } from "zod";

// create/record — no version token; server assigns identity + initial version.
export const CreateCustomerRequest = z.object({
  name: z.string().min(1),
  email: z.string().email().optional(),
});
export type CreateCustomerRequest = z.infer<typeof CreateCustomerRequest>;

// upsert/record, selection=identity — caller supplies the identity to create-or-update.
export const UpsertCustomerRequest = z.object({
  customerId: z.string().uuid(),
  name: z.string().min(1),
  email: z.string().email().optional(),
});
export type UpsertCustomerRequest = z.infer<typeof UpsertCustomerRequest>;

// bulk-update/set — input=many; each item carries its own optimistic token.
export const BulkUpdateRequest = z.object({
  items: z.array(z.object({
    customerId: z.string().uuid(),
    name: z.string().min(1),
    expectedVersion: z.number().int(),
  })).min(1),
});
export type BulkUpdateRequest = z.infer<typeof BulkUpdateRequest>;
```

### `src/constraints.ts` (rule customer.CustomerUpdateConstraint — validator)
```typescript
import { HttpError } from "./lifecycle";

export interface CustomerCandidate { state?: string; email?: string | null; }

// rule customer.CustomerUpdateConstraint  (kind=CONSTRAINT, applies-to=Customer):
// "email is present when a customer is Active". Pure predicate — reused by the
// policy engine (policy.ts) and asserted by every mutating command.
export function customerConstraintHolds(c: CustomerCandidate): boolean {
  return !(c.state === "Active" && !c.email);
}

// Enforced inside CreateCustomer / UpdateCustomer / UpsertCustomer / BulkUpdateCustomers:
// reject an Active customer with no email.
export function assertCustomerConstraint(c: CustomerCandidate): void {
  if (!customerConstraintHolds(c))
    throw new HttpError(422, "CustomerUpdateConstraint: an Active customer must have an email");
}
```

### `src/policy.ts` (policy customer.CustomerUpdatePolicy — engine + auth middleware)
```typescript
import { RequestHandler } from "express";
import { customerConstraintHolds } from "./constraints";
import { HttpError } from "./lifecycle";

export type Decision = "permit" | "deny" | "not-applicable";
export interface PolicyContext {
  principal?: { role: string };                 // actor customer.ServiceAgent
  candidate?: { state?: string; email?: string | null };
}
export interface PolicyRule { id: string; evaluate(ctx: PolicyContext): Decision; }

// The policy's rule delegates to the same constraint predicate (single source of truth).
const CustomerUpdateConstraint: PolicyRule = {
  id: "customer.CustomerUpdateConstraint",
  evaluate(ctx) {
    if (!ctx.candidate) return "not-applicable";
    return customerConstraintHolds(ctx.candidate) ? "permit" : "deny";
  },
};

interface Policy { id: string; authority: string; rules: PolicyRule[]; combine: "deny-overrides"; }
const POLICIES: Record<string, Policy> = {
  "customer.CustomerUpdatePolicy": {
    id: "customer.CustomerUpdatePolicy",
    authority: "ServiceAgent",                  // authority=ServiceAgent
    rules: [CustomerUpdateConstraint],          // rule=CustomerUpdateConstraint
    combine: "deny-overrides",                  // default-conflict=deny-overrides
  },
};

// deny-overrides: any deny wins; else permit if any rule permits; else not-applicable.
export function evaluatePolicy(policyId: string, ctx: PolicyContext): Decision {
  const policy = POLICIES[policyId];
  if (!policy) throw new HttpError(500, `unknown policy ${policyId}`);
  if (ctx.principal?.role !== policy.authority) return "deny";      // authority gate
  const decisions = policy.rules.map((r) => r.evaluate(ctx));
  if (decisions.includes("deny")) return "deny";
  if (decisions.includes("permit")) return "permit";
  return "not-applicable";
}

// Authorization middleware referenced by the command routes.
export function requirePolicy(policyId: string): RequestHandler {
  return (req, res, next) => {
    const decision = evaluatePolicy(policyId, {
      principal: { role: req.header("x-role") ?? "" },
      candidate: { state: req.body?.state, email: req.body?.email },
    });
    if (decision === "deny") return res.status(403).json({ error: `denied by ${policyId}` });
    next();
  };
}
```

### `src/events.ts` (event customer.CustomerUpdated — immutable outbox)
```typescript
import { Prisma } from "@prisma/client";

// event customer.CustomerUpdated (immutable): appended to a transactional outbox
// in the SAME tx as the state change, then never mutated (relayed by a separate poller).
export async function emitCustomerUpdated(
  tx: Prisma.TransactionClient,
  c: { customerId: string; version: number },
): Promise<void> {
  await tx.outboxEvent.create({
    data: {
      type: "customer.CustomerUpdated",
      payload: { customerId: c.customerId, version: c.version, occurredAt: new Date().toISOString() },
    },
  });
}
```

### `src/service.ts` (additional commands: Create / Get / Delete / Upsert / BulkUpdate)
```typescript
// Same PrismaClient instance + toResponse() helper as the UpdateCustomer walkthrough above.
import { CreateCustomerRequest, UpsertCustomerRequest, CustomerResponse } from "./dto";
import { assertCustomerConstraint } from "./constraints";
import { emitCustomerUpdated } from "./events";
import { HttpError } from "./lifecycle";

// customer.CreateCustomer — create/record, atomicity=atomic.
export async function createCustomer(cmd: CreateCustomerRequest): Promise<CustomerResponse> {
  return prisma.$transaction(async (tx) => {
    assertCustomerConstraint({ state: "Active", email: cmd.email ?? null });   // constraint
    const created = await tx.customer.create({ data: { name: cmd.name, email: cmd.email ?? null } });
    await emitCustomerUpdated(tx, created);
    return toResponse(created);
  });
}

// customer.GetCustomer — read/record, selection=identity (no mutation, no policy).
export async function getCustomer(customerId: string): Promise<CustomerResponse> {
  const c = await prisma.customer.findUnique({ where: { customerId } });
  if (!c) throw new HttpError(404, "customer not found");
  return toResponse(c);
}

// customer.DeleteCustomer — delete/record, idempotency=conditional (absent row => no-op, not an error).
export async function deleteCustomer(customerId: string): Promise<void> {
  await prisma.customer.deleteMany({ where: { customerId } });   // count 0 tolerated
}

// customer.UpsertCustomer — upsert/record, selection=identity, idempotency=conditional, atomicity=atomic.
export async function upsertCustomer(cmd: UpsertCustomerRequest): Promise<CustomerResponse> {
  return prisma.$transaction(async (tx) => {
    assertCustomerConstraint({ state: "Active", email: cmd.email ?? null });
    const row = await tx.customer.upsert({                       // idempotent create-or-update
      where:  { customerId: cmd.customerId },
      create: { customerId: cmd.customerId, name: cmd.name, email: cmd.email ?? null },
      update: { name: cmd.name, email: cmd.email ?? null, version: { increment: 1 } },
    });
    await emitCustomerUpdated(tx, row);
    return toResponse(row);
  });
}

// customer.BulkUpdateCustomers — bulk-update/set, input=many/output=many,
// atomicity=best-effort (per-record failure is isolated), concurrency=optimistic.
export interface BulkItem   { customerId: string; name: string; expectedVersion: number; }
export interface BulkResult { customerId: string; ok: boolean; error?: string; version?: number; }

export async function bulkUpdateCustomers(items: BulkItem[]): Promise<BulkResult[]> {
  const results: BulkResult[] = [];
  for (const item of items) {                                   // best-effort: NOT one big transaction
    try {
      // selection=predicate: each item selects its target by (identity, version).
      const r = await prisma.customer.updateMany({
        where: { customerId: item.customerId, version: item.expectedVersion },   // optimistic guard
        data:  { name: item.name, version: { increment: 1 } },
      });
      if (r.count === 0) { results.push({ customerId: item.customerId, ok: false, error: "not found or stale version" }); continue; }
      const row = await prisma.customer.findUniqueOrThrow({ where: { customerId: item.customerId } });
      results.push({ customerId: item.customerId, ok: true, version: row.version });
    } catch (e: any) {
      results.push({ customerId: item.customerId, ok: false, error: e.message });  // isolate, keep going
    }
  }
  return results;                                               // output=many (per-item outcomes)
}
```

### `src/queries.ts` (collectionTransform customer.ActiveCustomers — filter)
```typescript
import { PrismaClient, CustomerState } from "@prisma/client";
import { CustomerResponse } from "./dto";

const prisma = new PrismaClient();

// collectionTransform customer.ActiveCustomers: operation=filter, in=Customer out=Customer,
// predicate "customer status is Active", bounded=true (result set is capped).
const MAX_ROWS = 500;                                           // bounded=true
export async function activeCustomers(): Promise<CustomerResponse[]> {
  const rows = await prisma.customer.findMany({
    where: { state: CustomerState.Active },                     // predicate
    take: MAX_ROWS,
  });
  return rows.map((c) => ({
    customerId: c.customerId, name: c.name, email: c.email, state: c.state, version: c.version,
  }));
}
```

### `src/routes.ts` (additional endpoints)
```typescript
import { RequestHandler } from "express";
import { CreateCustomerRequest, UpsertCustomerRequest, BulkUpdateRequest } from "./dto";
import { createCustomer, getCustomer, deleteCustomer, upsertCustomer, bulkUpdateCustomers } from "./service";
import { activeCustomers } from "./queries";
// `router`, `requirePolicy`, and `HttpError` are the same imports as the UpdateCustomer route above.

// Small async adapter: map HttpError -> status, delegate the rest to Express.
const h = (fn: (req: any, res: any) => Promise<unknown>): RequestHandler => async (req, res, next) => {
  try { await fn(req, res); }
  catch (e) {
    if (e instanceof HttpError) return res.status(e.status).json({ error: e.message });
    next(e);
  }
};

router.post("/actions/CreateCustomer", requirePolicy("customer.CustomerUpdatePolicy"),
  h(async (req, res) => res.status(201).json(await createCustomer(CreateCustomerRequest.parse(req.body)))));

router.get("/actions/GetCustomer/:customerId",                 // read: no policy
  h(async (req, res) => res.json(await getCustomer(req.params.customerId))));

router.delete("/actions/DeleteCustomer/:customerId", requirePolicy("customer.CustomerUpdatePolicy"),
  h(async (req, res) => { await deleteCustomer(req.params.customerId); res.status(204).end(); }));

router.post("/actions/UpsertCustomer", requirePolicy("customer.CustomerUpdatePolicy"),
  h(async (req, res) => res.json(await upsertCustomer(UpsertCustomerRequest.parse(req.body)))));

// best-effort => 207 Multi-Status with per-item results (no all-or-nothing rollback).
router.post("/actions/BulkUpdateCustomers", requirePolicy("customer.CustomerUpdatePolicy"),
  h(async (req, res) => {
    const results = await bulkUpdateCustomers(BulkUpdateRequest.parse(req.body).items);
    res.status(207).json({ results });
  }));

// collectionTransform customer.ActiveCustomers — read/query endpoint (appears in Swagger).
router.get("/queries/ActiveCustomers", h(async (_req, res) => res.json(await activeCustomers())));
```

### `src/openapi.ts` (additional registrations — new routes in Swagger)
```typescript
import { CreateCustomerRequest, UpsertCustomerRequest, BulkUpdateRequest } from "./dto";
// same `registry` as the UpdateCustomer registration above.

registry.registerPath({ method: "post", path: "/actions/CreateCustomer",
  request: { body: { content: { "application/json": { schema: CreateCustomerRequest } } } },
  responses: { 201: { description: "created" }, 422: { description: "constraint violation" } } });

registry.registerPath({ method: "get", path: "/actions/GetCustomer/{customerId}",
  responses: { 200: { description: "customer" }, 404: { description: "not found" } } });

registry.registerPath({ method: "delete", path: "/actions/DeleteCustomer/{customerId}",
  responses: { 204: { description: "deleted (idempotent)" } } });

registry.registerPath({ method: "post", path: "/actions/UpsertCustomer",
  request: { body: { content: { "application/json": { schema: UpsertCustomerRequest } } } },
  responses: { 200: { description: "created-or-updated" }, 422: { description: "constraint violation" } } });

registry.registerPath({ method: "post", path: "/actions/BulkUpdateCustomers",
  request: { body: { content: { "application/json": { schema: BulkUpdateRequest } } } },
  responses: { 207: { description: "per-item results (best-effort)" } } });

// The ActiveCustomers query endpoint — must be present in the OpenAPI doc.
registry.registerPath({ method: "get", path: "/queries/ActiveCustomers",
  responses: { 200: { description: "customers filtered to state=Active (bounded)" } } });
```

## Coverage self-audit
```
Coverage self-audit  (tier: backend, stack: typescript-express-prisma)
- concept  customer.Customer (ENTITY)               → realized: Prisma Customer model + columns
- concept  customer.ServiceAgent (ACTOR)            → realized: auth principal/role (x-role) checked by policy authority gate
- concept  customer.UpdateCustomerWork (WORK)       → realized: the update process — service.updateCustomer handler
- concept  customer.CustomerUpdated (EVENT, immut.) → realized: append-only OutboxEvent + emitCustomerUpdated (in-tx outbox)
- relationship agent-performs-update (PARTICIPATION)→ realized: ServiceAgent principal authorized before the update handler runs
- relationship update-changes-customer (TRANSFORM.) → realized: updateCustomer mutates Customer + emits CustomerUpdated
- lifecycle CustomerLifecycle                       → realized: CustomerState enum + assertTransition guard
- action   customer.CreateCustomer (create)         → realized: service.createCustomer ($transaction, constraint, event)
- action   customer.GetCustomer (read)              → realized: service.getCustomer (selection=identity, no policy)
- action   customer.UpdateCustomer (update)         → realized: service.updateCustomer (deep walkthrough — $transaction,
      conditional idempotency, updateMany version guard, mutate={name}, constraint, event)
- action   customer.DeleteCustomer (delete)         → realized: service.deleteCustomer (deleteMany, idempotency=conditional)
- action   customer.UpsertCustomer (upsert)         → realized: service.upsertCustomer (Prisma upsert, atomic, idempotent)
- action   customer.BulkUpdateCustomers (bulk-upd.) → realized: service.bulkUpdateCustomers (best-effort per-item, 207, optimistic)
- collectionTransform customer.ActiveCustomers (filter) → realized: queries.activeCustomers + GET /queries/ActiveCustomers (bounded)
- rule     customer.CustomerUpdateConstraint (CONSTRAINT) → realized: constraints.ts validator (assertCustomerConstraint)
- policy   customer.CustomerUpdatePolicy            → realized: policy.ts deny-overrides engine + requirePolicy middleware
- OpenAPI/Swagger                                   → realized: /openapi.json + swagger-ui at /docs (all routes incl. ActiveCustomers)
- experience / design                               → out-of-tier: frontend owns these
dropped: []
```
