# Single-shot example — FastAPI + SQLModel + PostgreSQL

This realizes the reference `business-application` model in this stack. Imitate
its layering and idioms; substitute the target model's concepts, attributes,
lifecycle, and action contract.

## Input (excerpt of the KCF IR)

```jsonc
// concept customer.Customer
{ "id": "customer.Customer", "kind": "ENTITY",
  "attributes": [
    { "name": "customerId", "type": "UUID", "role": "identity" },
    { "name": "name", "type": "String", "role": "required" },
    { "name": "email", "type": "String", "role": "optional" } ] }
// lifecycle CustomerLifecycle for customer.Customer
{ "subject": "customer.Customer", "initial": "Active",
  "states": ["Active","Suspended","Archived"], "terminal": ["Archived"],
  "transitions": [["Active","Suspended"],["Suspended","Active"],["Active","Archived"]] }
// action customer.UpdateCustomer
{ "id": "customer.UpdateCustomer", "operation": "update", "scope": "record",
  "target": "customer.Customer", "selection": "identity", "mutate": ["name"],
  "idempotency": "conditional", "atomicity": "atomic", "concurrency": "optimistic",
  "authorization": "customer.CustomerUpdatePolicy" }
// concept customer.ServiceAgent (ACTOR) · customer.UpdateCustomerWork (WORK)
{ "id": "customer.ServiceAgent", "kind": "ACTOR" }
{ "id": "customer.UpdateCustomerWork", "kind": "WORK" }
// event customer.CustomerUpdated (immutable)
{ "id": "customer.CustomerUpdated", "kind": "EVENT", "mutable": false }
// relationships: actor→work, work→entity
{ "id": "agent-performs-update", "rootKind": "PARTICIPATION",
  "source": "customer.ServiceAgent", "target": "customer.UpdateCustomerWork" }
{ "id": "update-changes-customer", "rootKind": "TRANSFORMATION",
  "source": "customer.UpdateCustomerWork", "target": "customer.Customer" }
// actions: create / read / delete (record scope)
{ "id": "customer.CreateCustomer", "operation": "create", "scope": "record", "output": "one" }
{ "id": "customer.GetCustomer",    "operation": "read",   "scope": "record", "selection": "identity" }
{ "id": "customer.DeleteCustomer", "operation": "delete", "scope": "record", "output": "zero" }
// command customer.UpsertCustomer
{ "id": "customer.UpsertCustomer", "operation": "upsert", "scope": "record",
  "selection": "identity", "idempotency": "conditional", "atomicity": "atomic",
  "authorization": "customer.CustomerUpdatePolicy" }
// command customer.BulkUpdateCustomers
{ "id": "customer.BulkUpdateCustomers", "operation": "bulk-update", "scope": "set",
  "selection": "predicate", "input": "many", "output": "many",
  "atomicity": "best-effort", "concurrency": "optimistic",
  "authorization": "customer.CustomerUpdatePolicy" }
// collectionTransform customer.ActiveCustomers
{ "id": "customer.ActiveCustomers", "operation": "filter",
  "inputSchema": "Customer", "outputSchema": "Customer",
  "predicate": "customer status is Active", "bounded": true }
// rule customer.CustomerUpdateConstraint (CONSTRAINT)
{ "id": "customer.CustomerUpdateConstraint", "ruleKind": "CONSTRAINT",
  "condition": "email is present when a customer is Active",
  "appliesTo": ["customer.Customer"], "authority": "customer.ServiceAgent" }
// policy customer.CustomerUpdatePolicy
{ "id": "customer.CustomerUpdatePolicy", "authority": "customer.ServiceAgent",
  "rules": ["customer.CustomerUpdateConstraint"], "defaultConflict": "deny-overrides" }
```

## Output

### `models.py`
```python
import uuid
from enum import Enum
from sqlmodel import SQLModel, Field


class CustomerState(str, Enum):
    Active = "Active"
    Suspended = "Suspended"
    Archived = "Archived"


# Only declared transitions are legal (from CustomerLifecycle).
CUSTOMER_TRANSITIONS: set[tuple[CustomerState, CustomerState]] = {
    (CustomerState.Active, CustomerState.Suspended),
    (CustomerState.Suspended, CustomerState.Active),
    (CustomerState.Active, CustomerState.Archived),
}


class Customer(SQLModel, table=True):
    # customerId is the IR identity attribute → primary key.
    customerId: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str                                   # required
    email: str | None = None                    # optional
    state: CustomerState = Field(default=CustomerState.Active)
    version: int = Field(default=1)             # optimistic-concurrency token
```

### `schemas.py`
```python
import uuid
from sqlmodel import SQLModel


class UpdateCustomerRequest(SQLModel):
    customerId: uuid.UUID        # selection = identity
    name: str                    # only `name` is in the action's mutate set
    expectedVersion: int         # optimistic concurrency


class CustomerResponse(SQLModel):
    customerId: uuid.UUID
    name: str
    email: str | None
    state: str
    version: int
```

### `service.py`
```python
from fastapi import HTTPException
from sqlmodel import Session, select

from .models import Customer, CustomerState, CUSTOMER_TRANSITIONS
from .schemas import UpdateCustomerRequest, CustomerResponse


def transition(current: CustomerState, target: CustomerState) -> None:
    """Guard from CustomerLifecycle: reject undeclared transitions."""
    if current != target and (current, target) not in CUSTOMER_TRANSITIONS:
        raise HTTPException(422, f"illegal transition {current} -> {target}")


def update_customer(session: Session, cmd: UpdateCustomerRequest) -> CustomerResponse:
    """Realizes customer.UpdateCustomer.

    scope=record, selection=identity, mutate={name},
    idempotency=conditional, atomicity=atomic, concurrency=optimistic.
    Authorization is enforced by the router dependency, not here.
    """
    with session.begin():                                   # atomicity=atomic
        customer = session.get(Customer, cmd.customerId)    # selection=identity
        if customer is None:
            raise HTTPException(404, "customer not found")

        # idempotency=conditional: a no-op request neither errors nor bumps version.
        if customer.name == cmd.name:
            return _to_response(customer)

        # concurrency=optimistic: single guarded UPDATE; 0 rows => stale.
        result = session.exec(
            select(Customer)
            .where(Customer.customerId == cmd.customerId)
            .where(Customer.version == cmd.expectedVersion)
        ).one_or_none()
        if result is None:
            raise HTTPException(409, "version conflict")

        result.name = cmd.name          # only the mutate-listed field
        result.version += 1
        session.add(result)
    session.refresh(result)
    return _to_response(result)


def _to_response(c: Customer) -> CustomerResponse:
    return CustomerResponse(customerId=c.customerId, name=c.name, email=c.email,
                            state=c.state.value, version=c.version)
```

### `api.py`
```python
from fastapi import APIRouter, Depends
from sqlmodel import Session

from .db import get_session
from .security import require_policy
from .schemas import UpdateCustomerRequest, CustomerResponse
from . import service

router = APIRouter()


# authorization = customer.CustomerUpdatePolicy, enforced before the handler.
@router.post("/actions/UpdateCustomer", response_model=CustomerResponse,
             dependencies=[Depends(require_policy("customer.CustomerUpdatePolicy"))])
def update_customer(cmd: UpdateCustomerRequest, session: Session = Depends(get_session)):
    return service.update_customer(session, cmd)
```

### `tests/test_update_customer.py`
```python
import uuid
import pytest
from fastapi import HTTPException

from app.models import Customer, CustomerState
from app.schemas import UpdateCustomerRequest
from app import service


def test_update_happy_path(session):
    c = Customer(name="Acme", version=1)
    session.add(c); session.commit()
    out = service.update_customer(session, UpdateCustomerRequest(
        customerId=c.customerId, name="Acme Holdings", expectedVersion=1))
    assert out.name == "Acme Holdings" and out.version == 2


def test_stale_version_conflicts(session):
    c = Customer(name="Acme", version=3)
    session.add(c); session.commit()
    with pytest.raises(HTTPException) as e:
        service.update_customer(session, UpdateCustomerRequest(
            customerId=c.customerId, name="New", expectedVersion=1))
    assert e.value.status_code == 409


def test_illegal_lifecycle_transition():
    from app.service import transition
    with pytest.raises(HTTPException):
        transition(CustomerState.Archived, CustomerState.Active)  # not declared
```

### `main.py` (app + Swagger by default)
```python
from fastapi import FastAPI
from .api import router

# FastAPI serves Swagger UI at /docs and the OpenAPI document at /openapi.json
# out of the box — this IS the contract the frontend binds to. Typed request
# bodies + response_model on every route keep that document complete.
app = FastAPI(title="CustomerService", version="1.0.0")
app.include_router(router)
```

---

The rest of the model (the newer constructs) reuses these same idioms. Each
piece below is short but concrete — the deep contract reasoning stays on
`UpdateCustomer` above.

### `rules.py` — realizes rule `customer.CustomerUpdateConstraint`
```python
from dataclasses import dataclass

from .models import Customer, CustomerState


@dataclass
class ConstraintResult:
    decision: str          # "permit" | "deny"
    reason: str = ""


def customer_update_constraint(ctx: dict) -> ConstraintResult:
    """rule customer.CustomerUpdateConstraint (kind CONSTRAINT):
    'email is present when a customer is Active'. applies-to Customer,
    authority ServiceAgent. It is data-dependent, so it is a no-op until the
    candidate entity is known (ctx['customer']); the mutating commands supply
    it before persisting."""
    customer: Customer | None = ctx.get("customer")
    if customer is None:
        return ConstraintResult("permit")           # nothing to check yet
    if customer.state == CustomerState.Active and not customer.email:
        return ConstraintResult("deny", "Active customer must have an email")
    return ConstraintResult("permit")


# Rule registry keyed by qualified name — policies reference rules by this key.
RULES = {
    "customer.CustomerUpdateConstraint": customer_update_constraint,
}
```

### `security.py` — realizes policy `customer.CustomerUpdatePolicy` (+ actor `ServiceAgent`)
```python
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request

from .rules import RULES


@dataclass
class Principal:
    """Realizes actor customer.ServiceAgent — the authenticated principal/role."""
    subject: str
    role: str = "ServiceAgent"


def current_principal(request: Request) -> Principal:
    # A real deployment resolves this from a bearer token; ServiceAgent is the
    # only actor in this model.
    return Principal(subject=request.headers.get("x-user", "system"))


# Policy registry mirrors the IR `policies` block.
POLICIES: dict[str, dict] = {
    "customer.CustomerUpdatePolicy": {
        "authority": "ServiceAgent",
        "rules": ["customer.CustomerUpdateConstraint"],
        "defaultConflict": "deny-overrides",
    },
}


def evaluate_policy(policy_id: str, principal: Principal, ctx: dict) -> None:
    """Small policy engine. Gates on the policy's `authority`, then evaluates
    every referenced rule and combines the decisions with the policy's
    conflict strategy. deny-overrides: any DENY wins, order-independent."""
    policy = POLICIES[policy_id]
    if principal.role != policy["authority"]:                 # authority gate
        raise HTTPException(403, f"{policy_id}: requires {policy['authority']}")
    decisions = [RULES[r](ctx) for r in policy["rules"] if r in RULES]
    if policy["defaultConflict"] == "deny-overrides":
        denied = next((d for d in decisions if d.decision == "deny"), None)
        if denied is not None:
            raise HTTPException(422, f"{policy_id}: {denied.reason}")


def require_policy(policy_id: str):
    """FastAPI dependency wired by each command's `authorization`. At the router
    edge only the authority-level rules can be evaluated (no entity yet); the
    service re-invokes evaluate_policy with the resolved entity for the
    data-dependent constraint."""
    def _dep(principal: Principal = Depends(current_principal)):
        evaluate_policy(policy_id, principal, ctx={})
    return _dep
```

### `events.py` — realizes event `customer.CustomerUpdated` + the two relationships
```python
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)     # frozen == the event is `immutable` in the model
class CustomerUpdated:
    """event customer.CustomerUpdated (immutable). Also carries the model's
    relationships as data:
      - agent-performs-update (PARTICIPATION ServiceAgent -> UpdateCustomerWork): `agent`, `work`
      - update-changes-customer (TRANSFORMATION UpdateCustomerWork -> Customer): `customerId`"""
    customerId: uuid.UUID
    agent: str                                          # the ServiceAgent principal
    work: str = "customer.UpdateCustomerWork"
    occurredAt: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


AUDIT_LOG: list[CustomerUpdated] = []


def emit(event: CustomerUpdated) -> None:
    # A real deployment publishes to an outbox/broker; here we append to audit.
    AUDIT_LOG.append(event)
```

### `schemas.py` (additional request/response models)
```python
import uuid
from sqlmodel import SQLModel


class CreateCustomerRequest(SQLModel):       # action CreateCustomer
    name: str
    email: str | None = None


class UpsertCustomerRequest(SQLModel):       # command UpsertCustomer (selection=identity)
    customerId: uuid.UUID | None = None      # absent → create; present → update
    name: str
    email: str | None = None


class BulkItemResult(SQLModel):              # one row per input item (output many)
    customerId: uuid.UUID
    ok: bool
    version: int | None = None
    error: str | None = None
```

### `service.py` (remaining commands + the ActiveCustomers query)
```python
import uuid

from .events import CustomerUpdated, emit
from .security import Principal, evaluate_policy
from .schemas import CreateCustomerRequest, UpsertCustomerRequest, BulkItemResult


def _enforce(customer: Customer, principal: Principal) -> None:
    """Re-run the authorization policy with the resolved entity so the
    data-dependent CustomerUpdateConstraint (email-when-Active) is checked
    before any write. deny-overrides means the whole write is rejected."""
    evaluate_policy("customer.CustomerUpdatePolicy", principal, {"customer": customer})


def create_customer(session: Session, cmd: CreateCustomerRequest,
                    principal: Principal) -> CustomerResponse:
    """action customer.CreateCustomer (create, record, atomic)."""
    customer = Customer(name=cmd.name, email=cmd.email)
    _enforce(customer, principal)
    with session.begin():
        session.add(customer)
    session.refresh(customer)
    return _to_response(customer)


def get_customer(session: Session, customer_id: uuid.UUID) -> CustomerResponse:
    """action customer.GetCustomer (read, selection=identity). No authorization."""
    customer = session.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(404, "customer not found")
    return _to_response(customer)


def delete_customer(session: Session, customer_id: uuid.UUID) -> None:
    """command customer.DeleteCustomer (delete, output=zero, idempotency=conditional):
    deleting an absent record is a success, not a 404."""
    customer = session.get(Customer, customer_id)
    if customer is not None:
        with session.begin():
            session.delete(customer)


def upsert_customer(session: Session, cmd: UpsertCustomerRequest,
                    principal: Principal) -> CustomerResponse:
    """command customer.UpsertCustomer (upsert, selection=identity, atomic,
    idempotency=conditional): create-or-update keyed on identity."""
    with session.begin():
        customer = session.get(Customer, cmd.customerId) if cmd.customerId else None
        if customer is None:                                   # insert branch
            customer = Customer(customerId=cmd.customerId or uuid.uuid4(),
                                name=cmd.name, email=cmd.email)
        else:                                                  # update branch
            customer.name, customer.email = cmd.name, cmd.email
            customer.version += 1
        _enforce(customer, principal)
        session.add(customer)
    session.refresh(customer)
    emit(CustomerUpdated(customerId=customer.customerId, agent=principal.subject))
    return _to_response(customer)


def bulk_update_customers(session: Session, cmds: list[UpdateCustomerRequest],
                          principal: Principal) -> list[BulkItemResult]:
    """command customer.BulkUpdateCustomers (bulk-update, scope=set, input/output
    many, atomicity=best-effort, concurrency=optimistic). Each item runs in its
    own transaction so one failure never aborts the batch; every item yields a
    result."""
    results: list[BulkItemResult] = []
    for cmd in cmds:
        try:
            out = update_customer(session, cmd)     # reuse the record command (per-item tx)
            emit(CustomerUpdated(customerId=cmd.customerId, agent=principal.subject))
            results.append(BulkItemResult(customerId=cmd.customerId, ok=True,
                                          version=out.version))
        except HTTPException as e:                  # best-effort: isolate + continue
            session.rollback()
            results.append(BulkItemResult(customerId=cmd.customerId, ok=False,
                                          error=str(e.detail)))
    return results


def list_active_customers(session: Session) -> list[CustomerResponse]:
    """collectionTransform customer.ActiveCustomers (operation=filter, bounded):
    filter Customer→Customer on 'status is Active'."""
    rows = session.exec(
        select(Customer).where(Customer.state == CustomerState.Active)
    ).all()
    return [_to_response(c) for c in rows]
```

### `api.py` (remaining routes + query endpoint)
```python
import uuid

from .security import Principal, current_principal
from .schemas import CreateCustomerRequest, UpsertCustomerRequest, BulkItemResult


@router.post("/actions/CreateCustomer", response_model=CustomerResponse,
             dependencies=[Depends(require_policy("customer.CustomerUpdatePolicy"))])
def create_customer(cmd: CreateCustomerRequest, session: Session = Depends(get_session),
                    principal: Principal = Depends(current_principal)):
    return service.create_customer(session, cmd, principal)


@router.get("/actions/GetCustomer/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: uuid.UUID, session: Session = Depends(get_session)):
    return service.get_customer(session, customer_id)


@router.delete("/actions/DeleteCustomer/{customer_id}", status_code=204,
               dependencies=[Depends(require_policy("customer.CustomerUpdatePolicy"))])
def delete_customer(customer_id: uuid.UUID, session: Session = Depends(get_session)):
    service.delete_customer(session, customer_id)


@router.put("/actions/UpsertCustomer", response_model=CustomerResponse,
            dependencies=[Depends(require_policy("customer.CustomerUpdatePolicy"))])
def upsert_customer(cmd: UpsertCustomerRequest, session: Session = Depends(get_session),
                    principal: Principal = Depends(current_principal)):
    return service.upsert_customer(session, cmd, principal)


@router.post("/actions/BulkUpdateCustomers", response_model=list[BulkItemResult],
             dependencies=[Depends(require_policy("customer.CustomerUpdatePolicy"))])
def bulk_update_customers(cmds: list[UpdateCustomerRequest],
                          session: Session = Depends(get_session),
                          principal: Principal = Depends(current_principal)):
    return service.bulk_update_customers(session, cmds, principal)


# collectionTransform customer.ActiveCustomers → a read/query endpoint that shows
# up in the OpenAPI document alongside the actions.
@router.get("/queries/ActiveCustomers", response_model=list[CustomerResponse])
def active_customers(session: Session = Depends(get_session)):
    return service.list_active_customers(session)
```

### `tests/test_new_commands.py`
```python
import uuid
import pytest
from fastapi import HTTPException

from app.models import Customer, CustomerState
from app.schemas import UpsertCustomerRequest, UpdateCustomerRequest
from app.security import Principal
from app import service

AGENT = Principal(subject="agent-1")


def test_constraint_rejects_active_without_email(session):
    # rule CustomerUpdateConstraint via deny-overrides policy: Active + no email.
    with pytest.raises(HTTPException) as e:
        service.upsert_customer(session, UpsertCustomerRequest(name="Acme"), AGENT)
    assert e.value.status_code == 422


def test_active_customers_query_filters(session):
    session.add(Customer(name="A", email="a@x.io", state=CustomerState.Active))
    session.add(Customer(name="B", state=CustomerState.Archived))
    session.commit()
    out = service.list_active_customers(session)
    assert [c.name for c in out] == ["A"]


def test_bulk_is_best_effort(session):
    ok = Customer(name="Keep", version=1); session.add(ok); session.commit()
    results = service.bulk_update_customers(session, [
        UpdateCustomerRequest(customerId=ok.customerId, name="Kept", expectedVersion=1),
        UpdateCustomerRequest(customerId=uuid.uuid4(), name="Ghost", expectedVersion=1),
    ], AGENT)
    # one success, one isolated failure — the batch is not aborted.
    assert [r.ok for r in results] == [True, False]
```

## Coverage self-audit
```
Coverage self-audit  (tier: backend, stack: fastapi-sqlmodel-postgres)
- concept customer.Customer (ENTITY)          → realized: Customer SQLModel table + columns
- concept customer.ServiceAgent (ACTOR)       → realized: Principal (role=ServiceAgent), current_principal
- concept customer.UpdateCustomerWork (WORK)  → realized: the update process (service.update_customer),
      also named on the CustomerUpdated event (work="customer.UpdateCustomerWork")
- concept customer.CustomerUpdated (EVENT, immutable) → realized: frozen CustomerUpdated dataclass, emit()
- relationship agent-performs-update (PARTICIPATION) → realized: event.agent (ServiceAgent → work)
- relationship update-changes-customer (TRANSFORMATION) → realized: event.customerId (work → Customer)
- lifecycle CustomerLifecycle                 → realized: CustomerState enum + transition() guard
- action customer.CreateCustomer (create)     → realized: service.create_customer + POST route
- action customer.GetCustomer (query/read)    → realized: service.get_customer + GET route
- action customer.UpdateCustomer (update)     → realized: service.update_customer (atomic tx,
      conditional idempotency, optimistic version guard, mutate={name}) — deep walkthrough above
- action customer.DeleteCustomer (delete)     → realized: service.delete_customer + DELETE route (conditional)
- action customer.UpsertCustomer (upsert)     → realized: service.upsert_customer + PUT route (create-or-update)
- action customer.BulkUpdateCustomers (bulk-update, set) → realized: service.bulk_update_customers +
      POST route, per-item transactions (best-effort), per-item BulkItemResult
- collectionTransform customer.ActiveCustomers (filter) → realized: service.list_active_customers +
      GET /queries/ActiveCustomers (bounded filter, in OpenAPI)
- rule customer.CustomerUpdateConstraint (CONSTRAINT) → realized: rules.customer_update_constraint validator,
      enforced by mutating commands via _enforce()
- policy customer.CustomerUpdatePolicy        → realized: security.evaluate_policy engine (deny-overrides)
      + require_policy dependency wired on every authorized route
- OpenAPI/Swagger                             → realized: FastAPI /docs + /openapi.json (all actions,
      the ActiveCustomers query, and response models)
- experience / design                         → out-of-tier: frontend owns these
dropped: []
```
