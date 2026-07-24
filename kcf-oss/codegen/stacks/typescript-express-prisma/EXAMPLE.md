# Single-shot example — TypeScript + Express + Prisma + PostgreSQL

This realizes the reference `business-application` model in this stack. Imitate
its layering and idioms; substitute the target model's concepts, attributes,
lifecycle, and action contract.

## Input (excerpt of the KCF IR)

```jsonc
// concept customer.Customer: identity customerId:UUID, required name:String, optional email:String
// lifecycle CustomerLifecycle: Active->Suspended, Suspended->Active, Active->Archived (terminal Archived)
// action customer.UpdateCustomer: update/record, selection=identity, mutate=[name],
//   idempotency=conditional, atomicity=atomic, concurrency=optimistic,
//   authorization=customer.CustomerUpdatePolicy
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

## Coverage self-audit
```
Coverage self-audit  (tier: backend, stack: typescript-express-prisma)
- concept customer.Customer        → realized: Prisma Customer model + columns
- action  customer.UpdateCustomer  → realized: service.updateCustomer ($transaction,
      conditional idempotency, updateMany version guard, mutate={name})
- lifecycle CustomerLifecycle      → realized: CustomerState enum + assertTransition guard
- policy customer.CustomerUpdatePolicy → realized: requirePolicy Express middleware
- OpenAPI/Swagger                  → realized: /openapi.json + swagger-ui at /docs (all routes registered)
- experience / design              → out-of-tier: frontend owns these
dropped: []
```
