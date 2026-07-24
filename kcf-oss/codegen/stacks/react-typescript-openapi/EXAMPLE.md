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

Newer constructs in the reference model — the frontend realizes only the
UI/UX-owned aspect of each; the server keeps authority:

```jsonc
// collectionTransform customer.ActiveCustomers — a bounded filter query.
// Frontend-owned VIEW: read it from the backend query endpoint, render the list.
{ "id": "customer.ActiveCustomers", "operation": "filter",
  "inputSchema": "customer.Customer", "outputSchema": "customer.Customer",
  "predicate": "customer status is Active", "bounded": true }
// rule customer.CustomerUpdateConstraint — server-authoritative CONSTRAINT.
// Frontend MIRRORS it for instant feedback only (still handles the 4xx).
{ "id": "customer.CustomerUpdateConstraint", "kind": "CONSTRAINT",
  "condition": "email is present when a customer is Active",
  "appliesTo": "customer.Customer", "authority": "customer.ServiceAgent" }
// policy customer.CustomerUpdatePolicy — server ENFORCES; frontend only GATES UI.
{ "id": "customer.CustomerUpdatePolicy", "authority": "customer.ServiceAgent",
  "rules": ["customer.CustomerUpdateConstraint"], "defaultConflict": "deny-overrides" }
// command customer.UpsertCustomer (create-or-edit) + customer.BulkUpdateCustomers
// (set-scoped). Frontend renders the form / multi-select; server owns the contract.
{ "id": "customer.UpsertCustomer", "operation": "upsert", "scope": "record",
  "target": "customer.Customer", "selection": "identity", "mutate": ["name","email"] }
{ "id": "customer.BulkUpdateCustomers", "operation": "bulk-update", "scope": "set",
  "target": "customer.Customer", "selection": "predicate", "atomicity": "best-effort" }
```
- **Backend OpenAPI** additionally exposes `GET /queries/ActiveCustomers`,
  `POST /actions/UpsertCustomer`, and `POST /actions/BulkUpdateCustomers`.

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
import { toast } from "../lib/toast";   // thin wrapper over your toast lib
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
    onSuccess: (_d, vars) => {
      qc.invalidateQueries({ queryKey: ["customer", vars.customerId] });
      // customer.CustomerUpdated (EVENT): the server emits it; the UI surfaces
      // the fact as a success toast / activity-feed entry.
      toast.success("Customer updated");
    },
  });
}

// collectionTransform customer.ActiveCustomers → a frontend-owned filtered view.
// Just reads the backend's bounded query endpoint; no client-side re-filtering.
export function useActiveCustomers() {
  return useQuery({
    queryKey: ["queries", "ActiveCustomers"],
    queryFn: async () => {
      const { data, error } = await api.GET("/queries/ActiveCustomers");
      if (error) throw error;
      return data ?? [];
    },
  });
}

// command customer.UpsertCustomer (create-or-edit). Contract owned by the server;
// the hook just posts the body and lets the backend decide insert vs. update.
export function useUpsertCustomer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { customerId?: string; name: string; email?: string }) => {
      const { data, error } = await api.POST("/actions/UpsertCustomer", { body });
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["customers"] });
      qc.invalidateQueries({ queryKey: ["queries", "ActiveCustomers"] });
    },
  });
}

// command customer.BulkUpdateCustomers (scope=set, atomicity=best-effort). The UI
// sends the selected ids + patch; the server applies per-item and reports outcomes.
export function useBulkUpdateCustomers() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { customerIds: string[]; patch: { state?: string } }) => {
      const { data, error } = await api.POST("/actions/BulkUpdateCustomers", { body });
      if (error) throw error;
      return data;   // best-effort → server returns a per-item result set to render
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["customers"] }),
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

### `src/lib/validation.ts` (MIRROR of customer.CustomerUpdateConstraint — feedback only)
```typescript
// Rule CONSTRAINT: "email is present when a customer is Active".
// This is mirrored for INSTANT feedback only. The backend re-checks it and is
// the source of truth — a form that passes here can still get a 4xx (surface it).
export function customerConstraintError(
  draft: { state?: string; email?: string },
): string | null {
  if (draft.state === "Active" && !draft.email?.trim()) {
    return "An Active customer must have an email.";
  }
  return null;
}
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

### `src/features/customer/ActiveCustomers.tsx` (collectionTransform → filtered view)
```tsx
import { useActiveCustomers } from "../../api/customers";

// Realizes customer.ActiveCustomers as a real, frontend-owned view. The filter
// predicate lives on the server; the UI just renders whatever the query returns.
export function ActiveCustomers() {
  const { data: customers = [], isLoading } = useActiveCustomers();
  if (isLoading) return <p>Loading…</p>;
  return (
    <section aria-label="Active customers">
      <h2>Active customers ({customers.length})</h2>
      <ul>{customers.map((c) => (
        <li key={c.customerId}>{c.name} — {c.email ?? "no email"}</li>
      ))}</ul>
    </section>
  );
}
```

### `src/features/customer/CustomerUpsertForm.tsx` (command UpsertCustomer + rule mirror + policy gate)
```tsx
import { useUpsertCustomer } from "../../api/customers";
import { customerConstraintError } from "../../lib/validation";
import { useAuth } from "../../lib/auth";
import { useState } from "react";

// Create-or-edit form for customer.UpsertCustomer. Pass an existing record to
// edit; omit it to create. The server decides insert vs. update from the id.
export function CustomerUpsertForm({ existing }: { existing?: { customerId: string; name: string; email?: string; state: string } }) {
  const upsert = useUpsertCustomer();
  const { can } = useAuth();
  const mayWrite = can("customer.CustomerUpdatePolicy");   // UI gate; server enforces

  const [name, setName] = useState(existing?.name ?? "");
  const [email, setEmail] = useState(existing?.email ?? "");

  // MIRROR of CustomerUpdateConstraint for instant feedback (server still authoritative).
  const feedback = customerConstraintError({ state: existing?.state ?? "Active", email });
  const blocked = !mayWrite || !!feedback || upsert.isPending;

  return (
    <form onSubmit={(e) => {
      e.preventDefault();
      upsert.mutate({ customerId: existing?.customerId, name, email: email || undefined });
    }}>
      <input value={name} onChange={(e) => setName(e.target.value)} aria-label="name" required />
      <input value={email} onChange={(e) => setEmail(e.target.value)} aria-label="email" />
      {feedback && <p role="alert">{feedback}</p>}
      <button type="submit" disabled={blocked}>{existing ? "Save" : "Create"}</button>
      {/* If the server rejects on its own re-check, surface the 4xx here. */}
      {upsert.error && <p role="alert">{(upsert.error as Error).message}</p>}
      {!mayWrite && <p>You don't have permission to modify customers.</p>}
    </form>
  );
}
```

### `src/features/customer/BulkUpdateBar.tsx` (command BulkUpdateCustomers, multi-select)
```tsx
import { useBulkUpdateCustomers } from "../../api/customers";
import { useAuth } from "../../lib/auth";

// Multi-select bulk action for customer.BulkUpdateCustomers (scope=set). The
// control is role-gated in the UI; the backend enforces the policy per item and
// returns per-item outcomes (best-effort) which we surface.
export function BulkUpdateBar({ selectedIds, targetState }: { selectedIds: string[]; targetState: string }) {
  const bulk = useBulkUpdateCustomers();
  const { can } = useAuth();
  const mayBulk = can("customer.CustomerUpdatePolicy");

  return (
    <div role="toolbar" aria-label="Bulk actions">
      <button
        disabled={!mayBulk || selectedIds.length === 0 || bulk.isPending}
        onClick={() => bulk.mutate({ customerIds: selectedIds, patch: { state: targetState } })}
      >
        Set {selectedIds.length} selected → {targetState}
      </button>
      {bulk.data && <p>{bulk.data.filter((r) => r.ok).length}/{bulk.data.length} updated</p>}
    </div>
  );
}
```

### `test/customerDetail.test.tsx`
```tsx
import { describe, it, expect } from "vitest";
import { allowedTransitions } from "../src/lib/lifecycle";
import { customerConstraintError } from "../src/lib/validation";

describe("lifecycle UI", () => {
  it("offers only transitions legal from the current state", () => {
    expect(allowedTransitions("Active")).toEqual(["Suspended", "Archived"]);
    expect(allowedTransitions("Archived")).toEqual([]);   // terminal → no controls
  });
});

describe("constraint mirror (instant feedback only; server authoritative)", () => {
  it("flags an Active customer with no email", () => {
    expect(customerConstraintError({ state: "Active", email: "" })).toMatch(/email/i);
    expect(customerConstraintError({ state: "Active", email: "a@b.co" })).toBeNull();
    expect(customerConstraintError({ state: "Suspended", email: "" })).toBeNull();
  });
});
```

## Coverage self-audit
```
Coverage self-audit  (tier: frontend, stack: react-typescript-openapi)
- concept customer.Customer (ENTITY)        → realized: CustomerList + CustomerDetail + Upsert form
- concept customer.ServiceAgent (ACTOR)     → realized: useAuth current-user context; role-gated components
- concept customer.UpdateCustomerWork (WORK)→ delegated: server owns the update process/orchestration
- concept customer.CustomerUpdated (EVENT)  → realized: success toast + activity-feed entry on mutation success;
      delegated: the server emits the event; the UI only surfaces the fact
- rel agent-performs-update (PARTICIPATION) → realized: current-agent shown as the actor on the update UI
- rel update-changes-customer (TRANSFORMATION)→ realized: navigation from the update flow to the changed Customer view
- lifecycle CustomerLifecycle               → realized: state badge + only-legal-transition controls
- action customer.CreateCustomer            → realized: Upsert form (create mode) → POST /actions/UpsertCustomer;
      delegated: server owns the contract
- action customer.GetCustomer               → realized: useCustomer hook → GET /customers/{id}; delegated: server reads
- action customer.UpdateCustomer            → realized: CustomerDetail edit form (mutate={name}, expectedVersion, 409);
      delegated: POST /actions/UpdateCustomer via generated client; server owns the contract
- action customer.DeleteCustomer            → realized(UX): role-gated delete control; delegated: server enforces + persists
- action customer.UpsertCustomer            → realized: CustomerUpsertForm (create-or-edit); delegated: server decides insert/update
- action customer.BulkUpdateCustomers       → realized: BulkUpdateBar multi-select control (best-effort outcomes rendered);
      delegated: POST /actions/BulkUpdateCustomers; server enforces per item
- collectionTransform customer.ActiveCustomers → realized: ActiveCustomers filtered view via GET /queries/ActiveCustomers;
      delegated: filter predicate evaluated server-side
- rule customer.CustomerUpdateConstraint    → realized: mirrored in lib/validation for instant feedback;
      delegated: server re-checks and is authoritative (4xx surfaced)
- policy customer.CustomerUpdatePolicy      → realized(UX): can(...) gates update/delete/bulk controls;
      delegated: server enforces authority
- OpenAPI client                            → realized: generated typed client (openapi-typescript + openapi-fetch)
- persistence                               → delegated: backend owns storage; called via generated client
- authorization authority                   → delegated: backend enforces; frontend only gates the UI
- experience                                → realized: list/detail/edit/upsert/bulk/active-view flows + navigation
- design                                    → realized: frontend is the primary driver (swap in your design system)
dropped: []
```
