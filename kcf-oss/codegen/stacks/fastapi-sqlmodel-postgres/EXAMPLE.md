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

## Coverage self-audit
```
Coverage self-audit  (tier: backend, stack: fastapi-sqlmodel-postgres)
- concept customer.Customer        → realized: Customer SQLModel table + columns
- action  customer.UpdateCustomer  → realized: service.update_customer (atomic tx,
      conditional idempotency, optimistic version guard, mutate={name})
- lifecycle CustomerLifecycle      → realized: CustomerState enum + transition() guard
- policy customer.CustomerUpdatePolicy → realized: require_policy router dependency
- OpenAPI/Swagger                  → realized: FastAPI /docs + /openapi.json (all actions + resources)
- experience / design              → out-of-tier: frontend owns these
dropped: []
```
