# Single-shot example — React + TypeScript + TanStack Query + OpenAPI client

This realizes the reference `business-application` model as a **frontend**, bound
to a backend generated from the same model (any of the backend stacks). Imitate
its layering and idioms; substitute the target model's entities, actions,
lifecycle, and permissions. The API layer is generated from the backend's
OpenAPI — never hand-rolled.

## Inputs

- **KCF IR** (meaning + UX intent): `customer.Customer` (identity customerId,
  required name, optional email); `CustomerLifecycle` (Active↔Suspended,
  Active→Archived); action `customer.UpdateCustomer` (mutate=[name],
  concurrency=optimistic, authorization=customer.CustomerUpdatePolicy).
- **Backend OpenAPI**: exposes `POST /actions/UpdateCustomer` and a `Customer`
  read resource (from the backend stack's `/openapi.json` or `/api/schema`).

## Output

### `src/api/client.ts` (generated types → typed client)
```typescript
// 1. Generate types from the backend contract (build step, not hand-written):
//    npx openapi-typescript http://localhost:8000/openapi.json -o src/api/schema.d.ts
import createClient from "openapi-fetch";
import type { paths } from "./schema";

export const api = createClient<paths>({ baseUrl: import.meta.env.VITE_API_URL });
```

### `src/api/customers.ts` (TanStack Query hooks over the client)
```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";

export function useCustomer(customerId: string) {
  return useQuery({
    queryKey: ["customer", customerId],
    queryFn: async () => {
      const { data, error } = await api.GET("/customers/{customerId}", {
        params: { path: { customerId } },
      });
      if (error) throw error;
      return data;
    },
  });
}

// command action → useMutation; passes the concurrency token; invalidates on success.
export function useUpdateCustomer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { customerId: string; name: string; expectedVersion: number }) => {
      const { data, error, response } = await api.POST("/actions/UpdateCustomer", { body });
      if (response.status === 409) throw new Error("This record changed — reload and retry.");
      if (error) throw error;
      return data;
    },
    onSuccess: (_d, vars) => qc.invalidateQueries({ queryKey: ["customer", vars.customerId] }),
  });
}
```

### `src/lib/lifecycle.ts` (offer only legal transitions — from the IR)
```typescript
// Mirrors CustomerLifecycle transitions. Derived from the IR, not invented.
const TRANSITIONS: Record<string, string[]> = {
  Active: ["Suspended", "Archived"],
  Suspended: ["Active"],
  Archived: [],                       // terminal
};
export const allowedTransitions = (state: string): string[] => TRANSITIONS[state] ?? [];
```

### `src/features/customer/CustomerDetail.tsx`
```tsx
import { useCustomer, useUpdateCustomer } from "../../api/customers";
import { allowedTransitions } from "../../lib/lifecycle";
import { useAuth } from "../../lib/auth";
import { useState } from "react";

export function CustomerDetail({ customerId }: { customerId: string }) {
  const { data: customer, isLoading } = useCustomer(customerId);
  const update = useUpdateCustomer();
  const { can } = useAuth();
  const [name, setName] = useState("");

  if (isLoading || !customer) return <p>Loading…</p>;
  const mayUpdate = can("customer.CustomerUpdatePolicy");   // UX gate; server enforces

  return (
    <section>
      <h2>{customer.name}</h2>
      {/* lifecycle state as a badge + only the legal transitions */}
      <span className="badge">{customer.state}</span>
      {allowedTransitions(customer.state).map((to) => (
        <button key={to} disabled={!mayUpdate}>→ {to}</button>
      ))}

      {/* edit form submits ONLY the mutate-listed field (name) + the version */}
      <form onSubmit={(e) => {
        e.preventDefault();
        update.mutate({ customerId, name, expectedVersion: customer.version });
      }}>
        <input value={name} onChange={(e) => setName(e.target.value)}
               defaultValue={customer.name} aria-label="name" />
        <button type="submit" disabled={!mayUpdate || update.isPending}>Save</button>
      </form>
      {update.error && <p role="alert">{(update.error as Error).message}</p>}
    </section>
  );
}
```

### `src/features/customer/CustomerList.tsx`
```tsx
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";

export function CustomerList() {
  const { data } = useQuery({
    queryKey: ["customers"],
    queryFn: async () => (await api.GET("/customers")).data ?? [],
  });
  return (
    <table>
      <thead><tr><th>Name</th><th>State</th></tr></thead>
      <tbody>{data?.map((c) => (
        <tr key={c.customerId}><td>{c.name}</td><td>{c.state}</td></tr>
      ))}</tbody>
    </table>
  );
}
```

### `test/customerDetail.test.tsx`
```tsx
import { describe, it, expect } from "vitest";
import { allowedTransitions } from "../src/lib/lifecycle";

describe("lifecycle UI", () => {
  it("offers only transitions legal from the current state", () => {
    expect(allowedTransitions("Active")).toEqual(["Suspended", "Archived"]);
    expect(allowedTransitions("Archived")).toEqual([]);   // terminal → no controls
  });
});
```

## Coverage self-audit
```
Coverage self-audit  (tier: frontend, stack: react-typescript-openapi)
- concept customer.Customer        → realized: CustomerList + CustomerDetail + edit form
- action  customer.UpdateCustomer  → delegated: POST /actions/UpdateCustomer via generated
      client (sends expectedVersion; 409 surfaced); server owns the contract
- lifecycle CustomerLifecycle      → realized: state badge + only-legal-transition controls
- policy customer.CustomerUpdatePolicy → realized(UX): can(...) gates controls; delegated: server enforces
- concept ACTOR / auth             → realized: useAuth current-user context + permission gate
- persistence / action contract     → out-of-tier: backend owns; called via generated client
- experience                       → realized: list/detail/edit flow, navigation
- design                           → realized: minimal component styling (swap in your design system)
dropped: []
```
